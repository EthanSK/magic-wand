#!/usr/bin/env python3
"""R23 geometry checks -> exports/geometry-checks.json. Rigid CAD overlaps against the exported meshes; every stock
hardware size is a stated envelope from parameters.json. Not a physical fit, force or strength result."""
import sys
sys.dont_write_bytecode = True
import json, math
import numpy as np
import holder23 as h

h22, base = h.h22, h.base
OUT = h.OUT


def ov(a, b): return round(float((a ^ b).volume()), 4)


def keep_out_of_other_keys(new, old):
    added, removed = new - old, old - new
    regions = h22.spaces16.regions('Key_Carrier'); res = {}
    for i in (0, 2, 3, 4):
        s = h22.soldered_socket(i)
        poses = h22.slide_poses(i) if i in h22.G['slide_keys'] else h22.dogleg_poses(i)
        res[f'key_{i}'] = {
            'switch_overlap_new_vs_r22_mm3': [ov(new, regions[f'key_{i}_switch']), ov(old, regions[f'key_{i}_switch'])],
            'cap_travel_overlap_new_vs_r22_mm3': [ov(new, regions[f'key_{i}_cap_travel']), ov(old, regions[f'key_{i}_cap_travel'])],
            'soldered_route_max_overlap_new_vs_r22_mm3': [max(ov(new, s.translate(tuple(map(float, p)))) for p in poses), max(ov(old, s.translate(tuple(map(float, p)))) for p in poses)],
            'r23_edit_touching_route_mm3': max(ov(added + removed, s.translate(tuple(map(float, p)))) for p in poses)}
    zone = h.box(-11.5, 11.5, -19.5, 10.7, -1., 21.)
    outside = (added + removed) - zone
    return res, {'added_mm3': round(added.volume(), 2), 'removed_mm3': round(removed.volume(), 2),
                 'edit_volume_outside_centre_zone_mm3 (|X|<11.5, Y -19.5..10.7; residue is mesh re-triangulation)': round(outside.volume(), 4)}, regions


def main():
    new = h.read_new = h22.read(OUT / 'Key_Carrier-assembly.stl'); old = h.r22_carrier()
    others, edit, regions = keep_out_of_other_keys(new, old)
    body, plunger = h.switch(); module = h.union([h.board(), h.barrels(), body, plunger, h.plug()])
    slide = [ov(new, module.translate((0, -float(d), 0))) for d in np.arange(0, 30.01, .5)]
    rod = base.references()['rod']; cable = h.cable()
    seated = {
        'board_module_seated_overlap_mm3': slide[0],
        'board_module_front_slide_max_overlap_mm3 (30 mm, 0.5 mm steps, switch and plug attached, paddle off)': max(slide),
        'switch_lifted_0p4_seated_overlap_mm3': ov(new, h.switch(.4)[0]),
        'barrel_tip_to_guard_floor_mm': round(h.ZB - h.B['socket_barrel_protrusion_below_board_mm'] - h.Y['guard_floor_z_mm'][1], 3),
        'guard_floor_thickness_mm': round(h.Y['guard_floor_z_mm'][1] - h.Y['guard_floor_z_mm'][0], 3),
        'guard_floor_to_rod_corridor_mm': round(h.Y['guard_floor_z_mm'][0] - h.CORRIDOR, 3),
        'plug_bottom_to_rod_top_mm': round(h.ZB - h.B['plug_envelope']['below_board_mm'] - 4.0, 3),
        'plug_overlap_with_rod_mm3': ov(h.plug(), rod), 'cable_overlap_with_rod_mm3': ov(cable, rod), 'cable_overlap_with_carrier_mm3': ov(cable, new),
        'board_rear_end_to_upper_clip_reliefs_mm': round(10.65 - h.BOARD_REAR, 3),
        'board_side_clearance_to_channel_mm': round(h.Y['channel_half_x_mm'] - h.B['width_envelope_mm'] / 2, 3),
        'board_top_to_lip_underside_mm': round(h.Y['lip_underside_z_mm'] - h.ZT, 3),
        'lip_overlap_of_board_edge_mm': round(h.B['width_envelope_mm'] / 2 - h.Y['lip_inner_half_x_mm'], 3),
        'board_front_past_nose_mm': round(-8.3 - h.BOARD_FRONT, 2),
        'plug_front_past_nose_mm': round(-8.3 - (h.BOARD_FRONT + h.B['plug_envelope']['along_board_mm'][0]), 2),
        'cable_bend_front_past_nose_mm': round(-8.3 - min(p[1] for p in h.cable_points()) + h.B['cable_bundle_diameter_mm'] / 2, 2)}
    cheek_bores = h.teardrop_x(1.0, -12, 12, h.HG['axis_y_mm'], h.HG['axis_z_mm'], (-1, 0))
    paddles = {}
    for name, off in h.PD['variants'].items():
        poses = h.named_poses(off); rec = {'poses_deg': {k: round(v, 4) for k, v in poses.items()}}
        sweep = np.linspace(0, poses['released'], 9)
        rec['max_overlap_with_carrier_over_travel_mm3'] = max(ov(new, h.paddle_pose(a, off)) for a in sweep)
        rec['max_overlap_with_switch_body_nominal_mm3'] = max(ov(body, h.paddle_pose(a, off)) for a in sweep)
        rec['ridge_to_housing_at_stop_mm'] = round(h.STOP_PLUNGER - off - h.HOUSING_TOP, 3)
        rec['plunger_depression_at_stop_mm'] = round(h.PD['plunger_depression_at_stop_mm'] + off, 3)
        rec['stop_contact: overlap when pushed 0.05 mm past stop (mm3, >0 means skirts land on the webs)'] = ov(new, h.paddle_pose(-0.05 / 24 * 180 / math.pi, off))
        rec['neighbour_cap_travel_overlap_mm3'] = {f'key_{i}': max(ov(regions[f'key_{i}_cap_travel'], h.paddle_pose(a, off)) for a in sweep) for i in (0, 2, 3, 4)}
        rec['skirt_rear_gap_at_rest_mm'] = round(h.lift_at(7.0, h.PD['stop_surface_z_mm'], poses['rest_on_plunger']), 3)
        rec['pin_overlap_with_paddle_mm3'] = ov(h.hinge_pin(), h.paddle_pose(0, off)); rec['pin_overlap_with_carrier_mm3'] = ov(h.hinge_pin(), new)
        paddles[name] = rec
    yh = h.HG['axis_y_mm']; s0, s1 = h.PD['skirt_y_mm']
    def statics(yf, F=20.):
        r = yf - yh
        if yf >= s0: return {'press_y_mm': yf, 'stop_load_N': F, 'hinge_load_N': 0.0, 'note': 'press inside the skirt contact span'}
        return {'press_y_mm': yf, 'stop_load_N': round(F * r / (s0 - yh), 2), 'hinge_load_N': round(F * (1 - r / (s0 - yh)), 2)}
    import guard23
    final = new.rotate((-90, 0, 0)); guard = {}
    for name, (solid, stats, areas) in guard23.members().items():
        b = next(x for x in h22.G['beams'] if x['name'] == name)
        ys = [y for y, _ in areas if b['riser_corner_y_mm'] + .5 <= y <= b['root_y_mm'] - (h22.G['underside_ref_z_mm'] - h22.G['z0_mm']) - 1.0]
        member_final = final ^ solid.rotate((-90, 0, 0))
        span = [round(member_final.slice(-y).area(), 3) for y in ys]
        r22 = h22.beam_section(b, ys[len(ys) // 2]).area()
        guard[name] = {'side': 'right (+X)' if name.startswith('R') else 'left (-X)', 'free_span_y_mm': [min(ys), max(ys)],
                       'final_mesh_min_section_in_free_span_mm2': min(span), 'r22_nominal_section_mm2': round(r22, 3),
                       'growth_trimmed_unsupported_mm3': stats['trimmed_unsupported_mm3'], 'member_volume_in_final_mm3': round(member_final.volume(), 2)}
    report_guard = {'members': guard, 'section_mm': h.L['guard_reinforcement']['r23_section_mm'],
                    'layer_growth': 'Each 0.2 mm print layer (print Z = 26.9 - Y) grows at most 0.2 mm beyond the layer below (R22 guard_layers rule); unsupported excess is trimmed, not modelled.'}
    report = {'revision': h.L['revision'], 'guard_reinforcement': report_guard, 'carrier_edit': edit, 'other_keys_unchanged': others, 'stock_module': seated, 'paddles': paddles,
              'heights_mm': {'paddle_top': h.PD['plate_z_mm'][1], 'choc_cap_top_r22': round(base.PCB_Z + 9.1, 2), 'paddle_proud_of_choc_caps': round(h.PD['plate_z_mm'][1] - base.PCB_Z - 9.1, 2),
                             'housing_top_nominal': round(h.HOUSING_TOP, 2), 'plunger_free_nominal': round(h.PLUNGER_FREE, 2)},
              'existing_cutout_check': {'bay_opening_mm': 14.1, 'board_length_mm': h.B['length_nominal_mm'], 'fits': False,
                                        'rear_route': 'Blocked: upper-key clip reliefs from Y 10.65 at |X| >= 1.55, saddle solid at |X| < 4.96 from Z -4.75 to 11.12, keys 3/4 sockets from |X| 4.68. So the connector end goes forward.'},
              'statics_20N_stated_press': [statics(y) for y in (-14., -10., -7., 0., 6.)],
              'physical_fit_verified': False}
    (OUT / 'geometry-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report_guard['members']))
    print(report['carrier_edit'])
    print({k: (v['switch_overlap_new_vs_r22_mm3'][0], v['soldered_route_max_overlap_new_vs_r22_mm3'][0], v['cap_travel_overlap_new_vs_r22_mm3'][0], v['r23_edit_touching_route_mm3']) for k, v in others.items()})
    print({k: v for k, v in seated.items() if 'overlap' in k})
    print({n: (p['max_overlap_with_carrier_over_travel_mm3'], p['max_overlap_with_switch_body_nominal_mm3'], p['neighbour_cap_travel_overlap_mm3']) for n, p in paddles.items()})


if __name__ == '__main__':
    main()
