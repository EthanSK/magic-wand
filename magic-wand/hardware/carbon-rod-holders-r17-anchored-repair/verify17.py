#!/usr/bin/env python3
"""Check the exported R17 meshes against the XIAO, cell, gate, rod and working spaces.

Geometric screening only: no claim of physical fit, friction, strength or fatigue.
"""
import json
import numpy as np
import trimesh
import manifold3d as mf
import holder17 as h

OUT = h.HERE / 'exports'


def read(path):
    m = trimesh.load_mesh(path)
    return mf.Manifold(mf.Mesh(np.asarray(m.vertices, dtype=np.float32), np.asarray(m.faces, dtype=np.uint32)))


def overlap(a, b):
    return max(0., float((a ^ b).volume()))


def box_(x0, x1, y0, y1, z0, z1):
    return h.box(x0, x1, y0, y1, z0, z1)


E_MODULUS = 2000.  # MPa: an assumed round figure for printed PETG, not a measurement.


def bow_screen(L_leg, leg_t, depth, span, bar_h, delta):
    """Cantilever leg plus a bar bowing under the end moment. Geometry-only stiffness estimate, never a measured force."""
    I_leg = depth * leg_t ** 3 / 12; I_bar = depth * bar_h ** 3 / 12; compliance = L_leg ** 3 / (3 * E_MODULUS * I_leg) + L_leg ** 2 * (span / 2) / (E_MODULUS * I_bar)
    force = delta / compliance; stress = force * L_leg * (leg_t / 2) / I_leg
    return {'assumed_modulus_MPa': E_MODULUS, 'deflection_mm': delta, 'estimated_force_N_each_leg': round(force, 2), 'estimated_leg_root_stress_MPa': round(stress, 1), 'estimated_leg_root_strain_percent': round(stress / E_MODULUS * 100, 2), 'status': 'Estimate from beam formulas with an assumed modulus; real force is unmeasured.'}


def arm_screen(L, t_, depth, delta):
    I = depth * t_ ** 3 / 12; force = 3 * E_MODULUS * I * delta / L ** 3; stress = force * L * (t_ / 2) / I
    return {'assumed_modulus_MPa': E_MODULUS, 'deflection_mm': delta, 'arm_length_mm': round(L, 3), 'arm_width_mm': round(t_, 3), 'estimated_force_N_each_arm': round(force, 2), 'estimated_root_stress_MPa': round(stress, 1), 'estimated_root_strain_percent': round(stress / E_MODULUS * 100, 2), 'status': 'Estimate from a cantilever formula with an assumed modulus; real force is unmeasured.'}


def islands(path, height):
    """Printed-island statistics per 0.2 mm layer of a print-frame mesh, from the first layer upward."""
    s = read(path); rows = []
    for z in np.arange(.1, height, .2):
        section = s.slice(float(z)); parts = [c.area() for c in section.decompose() if c.area() > .05]
        if parts: rows.append((round(float(z), 2), len(parts), round(min(parts), 3), round(sum(parts), 2)))
    return rows


def check():
    manifest = json.loads((OUT / 'manifest.json').read_text()); r16 = json.loads((h.R16 / 'exports/manifest.json').read_text())
    for path, digest in manifest['source_sha256'].items():
        assert h.sha(h.HERE / path) == digest, ('Stale source', path)
    solids = {name: read(OUT / (name + '-assembly.stl')) for name in manifest['parts']}
    assert manifest['unchanged_from_r16']['Key_Carrier'] == r16['parts']['Key_Carrier']['stl_sha256']
    assert h.sha(h.R16 / 'exports/Key_Carrier-SOURCE-REQUIRES-PREPARATION.stl') == manifest['unchanged_from_r16']['Key_Carrier'], 'R16 key carrier STL changed'
    report = {'manifest_sha256': h.sha(OUT / 'manifest.json'), 'checker_sha256': h.sha(h.HERE / 'verify17.py'), 'physical_fit_verified': False, 'physical_strength_verified': False}

    # 1. Every working space, for every part on this plate.
    spaces = {}
    for name, solid in solids.items():
        rows = {}
        for label, region in h.regions(name).items():
            if isinstance(region, h.spaces16.Swept):
                worst = max(overlap(solid, pose) for pose in region.poses()); rows[label] = {'poses': len(region), 'worst_pose_intersection_mm3': worst}; assert worst < .002, (name, label, worst)
            else:
                v = overlap(solid, region); rows[label] = {'intersection_mm3': v}; assert v < .002, (name, label, v)
        spaces[name] = rows
    report['working_spaces'] = spaces

    # 2. Rod interface: both clip bands of both modules are geometrically unchanged from R16.
    rod = {}
    for name, bands in {'Battery_Holder': [h.CAGE['near_band_y_mm'], h.CAGE['far_band_y_mm']], 'XIAO_Rod_Holder': [h.S['near_band_y_mm'], h.S['far_band_y_mm']]}.items():
        old = read(h.R16 / 'exports' / (name + '-assembly.stl')); new = solids[name]; rows = {}
        for y0, y1 in bands:
            # The free clip arms, below where the crown meets the saddle at Z 3.0; what joins the crown above that changed on purpose.
            tube = h.base.box(-5.75, 5.75, y0, y1, -5.75, 3.0) ^ h.cyl(5.75, -60, 60).rotate((-90, 0, 0))
            a = old ^ tube; b = new ^ tube; d = float((a - b).volume() + (b - a).volume())
            rows[f'{y0:g}..{y1:g}'] = {'symmetric_difference_mm3': round(d, 4), 'band_volume_mm3': round(a.volume(), 3)}; assert d < .05, (name, y0, y1, d)
        rod[name] = rows
    report['rod_interface_vs_r16'] = rod

    # 3. Battery: the cell, gate and channel.
    b = solids['Battery_Holder']; lv = h.base.cage_levels(); pack = h.base.cell_shape(); reserve = h.base.cell_shape(True); c = h.CAGE; G = h.GATE
    assert overlap(b, pack) < .002 and overlap(b, reserve) < .002
    fx = c['roof_flange_inner_x_mm']; half = h.P['cell']['manufacturer_max_mm']['width'] / 2
    r16_rows = islands(h.R16 / 'exports/Battery_Holder-SOURCE-REQUIRES-PREPARATION.stl', r16['parts']['Battery_Holder']['print_height_mm'])
    r17_rows = islands(OUT / 'Battery_Holder-SOURCE-REQUIRES-PREPARATION.stl', manifest['parts']['Battery_Holder']['print_height_mm'])
    def stats(rows):
        body = [r for r in rows if 4.0 <= r[0] <= 28.0]
        return {'layers_sampled_4_to_28_mm': len(body), 'max_islands': max(r[1] for r in body), 'median_islands': float(np.median([r[1] for r in body])),
                'smallest_island_mm2': min(r[2] for r in body), 'median_total_area_mm2': float(np.median([r[3] for r in body])), 'layers_at_one_island': sum(r[1] == 1 for r in body)}
    report['Battery_Holder'] = {'cell_clearance_flange_overlap_per_side_mm': round(half - fx, 3), 'solid_PETG_g': manifest['parts']['Battery_Holder']['solid_PETG_g'], 'r16_solid_PETG_g': r16['parts']['Battery_Holder']['solid_PETG_g'],
                                'printed_islands_r16': stats(r16_rows), 'printed_islands_r17': stats(r17_rows)}
    assert report['Battery_Holder']['printed_islands_r17']['max_islands'] == 1
    # The gate fits without touching the holder when relaxed in its seat; its bumps sit in the notches and clear the 45-degree cap.
    gate_relaxed = h.battery_gate(False); gate_flexed = h.battery_gate(True)
    assert overlap(b, gate_flexed) < .002, 'Flexed gate touches the holder'
    seated = overlap(b, gate_relaxed); assert seated < .002, ('Relaxed gate should clear the seat', seated)
    # How far the gate can move toward the cap and the +Y wall before it touches anything, and the bump depth felt on the way in.
    def first_touch(shape, d):
        for s in np.linspace(.0, 1.2, 61):
            if overlap(b, shape.translate((0, d * float(s), 0))) > .001: return round(float(s), 3)
        return None
    toward_cap_flexed = first_touch(gate_flexed, -1.); toward_cap_relaxed = first_touch(gate_relaxed, -1.); toward_wall = first_touch(gate_flexed, 1.)
    assert toward_cap_flexed and toward_cap_flexed >= .4 and toward_cap_relaxed >= .2, (toward_cap_flexed, toward_cap_relaxed)
    lifted = {f'{float(dz):.1f}': round(overlap(b, gate_relaxed.translate((0, 0, float(dz)))), 4) for dz in (0.5, 1.0, 1.5, 2.5, 4.0)}
    assert max(lifted.values()) > .02, lifted
    report['Battery_End_Gate'] = {'relaxed_seated_overlap_mm3': round(seated, 5), 'clearance_to_cap_ramp_with_legs_flexed_mm': toward_cap_flexed, 'free_travel_toward_cap_with_bump_in_notch_mm': toward_cap_relaxed, 'free_travel_toward_plus_y_wall_mm': toward_wall, 'bump_overlap_mm3_when_lifted_by_mm': lifted,
                                  'detent_bump_overlap_with_wall_mm': G['bump_overlap_mm'], 'leg_side_clearance_to_wall_mm': round(c['slot_x_centre_mm'] + c['slot_width_mm'] / 2 - (c['slot_x_centre_mm'] + G['leg_half_width_mm']), 3),
                                  'stiffness_screen': bow_screen(L_leg=lv['roof_bottom'] - .4 - G['detent_z_mm'], leg_t=2 * G['leg_half_width_mm'], depth=c['gate_y_mm'][1] - c['gate_y_mm'][0], span=2 * c['slot_x_centre_mm'], bar_h=lv['floor_top'] + .5 + 5.5 + .4 - (lv['roof_bottom'] - .4), delta=G['bump_overlap_mm']),
                                  'solid_PETG_g': manifest['parts']['Battery_End_Gate']['solid_PETG_g']}

    # 4. XIAO: board seat through its reachable poses, far fingers, and the top plate.
    x = solids['XIAO_Rod_Holder']; plate = h.retainer(True); plate_relaxed = h.retainer(False); r = h.RET; t = h.board_travel(); rows = {}
    for dx, dy in h.reachable_poses():
        assert overlap(x, h.board_outline(dx, dy)) < .002, (dx, dy)
    plane = x.slice(h.BZ - .02); (cx, cy), radius = h.base.board_corner_centres()[0][0], h.base.board_corner_centres()[1]
    worst = {}
    for dx, dy in h.reachable_poses():
        sec = h.board_outline(dx, dy).slice(h.BZ + .02)
        for sx, end, label in ((1, 'near', '+X near'), (-1, 'near', '-X near'), (1, 'far', '+X far'), (-1, 'far', '-X far')):
            limit = 8. if end == 'near' else 20.
            box = mf.CrossSection.square((12., 8.)).translate((0 if sx > 0 else -12., -2. if end == 'near' else 19.))
            area = (sec ^ plane ^ box).area(); worst[label] = min(worst.get(label, 99.), area)
    assert min(worst.values()) >= .3, worst
    # Stops engage just past the travel limits; rails do not locate the board.
    def collides(dx, dy): return overlap(x, h.board_outline(dx, dy))
    near_hit = collides(0., -(t['near'] + .2)); far_hit = collides(0., t['far'] + .2)
    assert near_hit > .01 and far_hit > .01, (near_hit, far_hit)
    # The plate clears the holder both flexed and relaxed in its seat; the bumps sit in the notches.
    assert overlap(x, plate) < .002, 'Flexed plate touches the holder'
    relaxed_seat = overlap(x, plate_relaxed); assert relaxed_seat < .002, ('Relaxed plate should clear its seat', relaxed_seat)
    pulled = {f'{d:.1f}': round(overlap(x, plate_relaxed.translate((0, -d, 0))), 4) for d in (.5, 1., 1.5, 2.5)}
    assert max(pulled.values()) > .02, pulled
    assert overlap(plate, h.board_outline()) < .002
    for comp in h.XO['components']:
        assert overlap(plate, h.component_box(comp)) < .002, comp
        assert overlap(x, h.component_box(comp)) < .002, comp
    # Fingers: bare board corners only; how much of the board they hold over at every reachable pose.
    fplan = mf.CrossSection.batch_boolean([plate.slice(float(np.mean(r['plate_z_mm']))) ^ mf.CrossSection.square((30., 7.)).translate((-15., -3.)),
                                           x.slice(float(np.mean(r['far_finger']['z_mm']))) ^ mf.CrossSection.square((30., 3.)).translate((-15., 20.5))], mf.OpType.Add)
    corners = {'+X near': (1, 'near'), '-X near': (-1, 'near'), '+X far': (1, 'far'), '-X far': (-1, 'far')}; hold = {}
    for dx, dy in h.reachable_poses():
        sec = h.board_outline(dx, dy).slice(h.BZ + .1)
        for label, (sx, end) in corners.items():
            box = mf.CrossSection.square((14., 8.)).translate((0 if sx > 0 else -14., -3. if end == 'near' else 18.)); area = (sec ^ fplan ^ box).area(); hold[label] = min(hold.get(label, 99.), area)
    assert min(hold.values()) >= .5, hold
    # Every wire route stays clear of the seated plate and of the plate along its whole removal travel.
    exits = {k: v for k, v in h.regions('XIAO_Rod_Holder').items() if k.startswith(('wire_exit', 'wire_run', 'castellation'))}
    route = h.regions('XIAO_Rod_Holder')['retainer_route']; wire_clear = {}
    for label, region in exits.items():
        v = max(overlap(pose, region) for pose in route.poses()); wire_clear[label] = round(v, 6); assert v < .002, (label, v)
    # Nothing printed anywhere over the pad rows above the rail top, on either part.
    w = h.WIRE; pad_lo, pad_hi = w['run_y_mm'][0] + 12.28, w['run_y_mm'][1]; over = box_(-40, 40, pad_lo, pad_hi, h.S['rail_z_mm'][1] + .001, 30)
    above_rail = overlap(x, over); seated_over = overlap(plate_relaxed, over); assert above_rail < .002 and seated_over < .002, (above_rail, seated_over)
    report['XIAO_Rod_Holder'] = {'official_board_mm': h.XO['outline'], 'pcb_thickness_from_official_step_mm': h.BT, 'rail_inner_half_width_mm': h.S['rail_x_mm'][0], 'side_allowance_per_side_mm': round(h.S['rail_x_mm'][0] - h.XO['outline']['width'] / 2, 3),
                                 'r16_side_allowance_per_side_mm': round(h.base.P['sensor']['rail_x_mm'][0] - h.XO['outline']['width'] / 2, 3), 'axial_travel_mm': {'to_near_V': round(t['near'], 3), 'to_far_stop_on_centre': round(t['far'], 3)},
                                 'minimum_ledge_contact_under_each_corner_mm2': {k: round(v, 3) for k, v in worst.items()}, 'board_poses': len(h.reachable_poses()), 'stop_engagement_0p2_past_travel_mm3': {'near': round(near_hit, 4), 'far': round(far_hit, 4)},
                                 'minimum_finger_overlap_over_board_corner_at_any_reachable_pose_mm2': {k: round(v, 3) for k, v in hold.items()},
                                 'material_over_pad_rows_above_rail_top_mm3': {'holder': round(above_rail, 6), 'seated_plate': round(seated_over, 6)},
                                 'pad_rows_assembly_y_mm': {'first_pad_starts': round(min(y - hw for _, y, hw in h.pad_rows()), 3), 'last_pad_ends': round(max(y + hw for _, y, hw in h.pad_rows()), 3)},
                                 'wire_exit_corridors_checked': len(exits), 'plate_removal_vs_every_wire_route_max_overlap_mm3': max(wire_clear.values()),
                                 'insertion': h.INSERTION, 'solid_PETG_g': manifest['parts']['XIAO_Rod_Holder']['solid_PETG_g']}
    report['XIAO_Top_Retainer'] = {'plate_underside_above_pcb_top_mm': round(r['plate_z_mm'][0] - h.BOARD_TOP, 3), 'far_finger_underside_above_pcb_top_mm': round(r['far_finger']['z_mm'][0] - h.BOARD_TOP, 3),
                                   'clearance_in_groove_mm': {'under_plate': round(r['plate_z_mm'][0] - r['groove']['floor_z_mm'], 3), 'over_plate': round(r['groove']['ceiling_z_mm'] - r['plate_z_mm'][1], 3), 'at_back_wall': round(r['groove']['back_x_mm'] - r['tab_x_mm'][1], 3)},
                                   'relaxed_seated_overlap_mm3': round(relaxed_seat, 5), 'bump_overlap_mm3_when_pulled_by_mm': pulled, 'detent_bump_overlap_with_wall_mm': r['spring']['bump_overlap_mm'],
                                   'stiffness_screen': arm_screen(L=r['spring']['bump_y_mm'] - r['spring']['slit_y_mm'][0], t_=r['tab_x_mm'][1] - r['spring']['slit_x_mm'][1], depth=r['plate_z_mm'][1] - r['plate_z_mm'][0], delta=r['spring']['bump_overlap_mm']),
                                   'contact_with_board': 'None at nominal. The plate and far fingers are stops above bare PCB corners; they bear only if the board lifts by more than 0.3 mm.',
                                   'solid_PETG_g': manifest['parts']['XIAO_Top_Retainer']['solid_PETG_g']}
    report['passed'] = True
    (OUT / 'geometry-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['Battery_End_Gate', 'XIAO_Rod_Holder', 'XIAO_Top_Retainer']}, indent=0)[:2600], flush=True)


if __name__ == '__main__':
    check()
