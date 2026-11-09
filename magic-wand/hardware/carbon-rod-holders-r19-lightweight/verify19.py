#!/usr/bin/env python3
"""Geometry screening of the R19 parts, routes and orientation. No claim of physical fit, force or fatigue."""
import json
import numpy as np, trimesh, manifold3d as mf
import holder19 as h

OUT = h.HERE / 'exports'
def read(p):
    m = trimesh.load_mesh(p); return mf.Manifold(mf.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32)))
def ov(a, b): return max(0., float((a ^ b).volume()))


def spring(L, b, t, d):
    I = b * t ** 3 / 12; F = 3 * 2000 * I * d / L ** 3
    return {'length_mm': L, 'width_mm': b, 'thickness_mm': t, 'deflection_mm': d, 'estimated_force_N': round(F, 2), 'estimated_root_strain_percent': round(1.5 * d * t / L ** 2 * 100, 2), 'status': 'Beam estimate, assumed 2000 MPa modulus; force is unmeasured.'}


def orientation(name):
    """Bed height, contact and steep down-facing area in the rod-clip bands, for each plausible pose."""
    m = trimesh.load_mesh(OUT / (name + '-assembly.stl')); rows = {}; band = h.CAGE['near_band_y_mm'] if name == 'Battery_Holder' else h.S['near_band_y_mm']
    poses = {'upright_far_end_on_bed (chosen)': ([0, 1, 0], -1), 'open_top_up': ([0, 0, 1], 1), 'open_top_down': ([0, 0, 1], -1), 'side_on_bed': ([1, 0, 0], 1)}
    centres = m.triangles_center; ring = (centres[:, 1] >= band[0]) & (centres[:, 1] <= band[1]) & (np.hypot(centres[:, 0], centres[:, 2]) < 6.2)
    for k, (axis, sign) in poses.items():
        up = np.array(axis, float) * sign; h_ = m.vertices @ up; low = h_.min(); steep = (m.face_normals @ up) < -np.cos(np.radians(45))
        off_bed = (m.triangles_center @ up) > low + .05
        rows[k] = {'height_mm': round(float(h_.max() - low), 2), 'clip_band_area_needing_support_mm2': round(float(m.area_faces[ring & steep & off_bed].sum()), 1), 'clip_arc_in_layer_plane': bool(abs(up[1]) > .9)}
    return rows


def interfaces(solids):
    """Windows around the parts the user has already fitted: in each, R19 must match the R18 mesh."""
    r18 = h.h18.HERE / 'exports'; old = {n: read(r18 / (n + '-assembly.stl')) for n in h.NEW_PARTS}; g = h.RET['groove']; p = h.RET['post']; s = h.S; hp = h.H['hoop']; rows = {}; b = h.D['bridge']
    windows = {'Battery_Holder': {'door_slot_+X (outer face excluded: R19 drops the unused R17 detent notch)': (10.7, 12.95, -16.4, -13.55, 6.3, 12.3), 'door_slot_-X (outer face excluded: R19 drops the unused R17 detent notch)': (-12.95, -10.7, -16.4, -13.55, 6.3, 12.3), 'door_catch_bar': (-3., 3., -13.8, -13.05, 10.8, 12.3)},
               'XIAO_Rod_Holder': {'near_cradle_groove_post_+X': (s['cradle_inner_x_mm'], 14.6, p['full_y_mm'][0], g['closed_end_y_mm'], 10.0, p['top_z_mm']), 'near_cradle_groove_post_-X': (-14.6, -s['cradle_inner_x_mm'], p['full_y_mm'][0], g['closed_end_y_mm'], 10.0, p['top_z_mm']),
                                   'board_ledges': (-10., 10., s['near_tab_y0_mm'], s['near_contact_limit_y_mm'], h.BZ - .4, h.BZ + .4), 'far_board_ledges': (-10., 10., 20.2, 22.5, h.BZ - .4, h.BZ + .4), 'hoop_shoulder_underside_+X': (hp['shoulder_inner_x_mm'], 12., 20.8, 23.3, hp['shoulder_under_z_mm'], hp['shoulder_under_z_mm'] + .3), 'hoop_shoulder_underside_-X': (-12., -hp['shoulder_inner_x_mm'], 20.8, 23.3, hp['shoulder_under_z_mm'], hp['shoulder_under_z_mm'] + .3)}}
    for name, table in windows.items():
        for label, w in table.items():
            win = h.box(*w); a = solids[name] ^ win; c = old[name] ^ win; d = float((a - c).volume() + (c - a).volume()); rows[f'{name}/{label}'] = round(d, 5); assert c.volume() > .05 and d < .05, (name, label, d, c.volume())
    return {'symmetric_difference_mm3': rows, 'status': 'Geometry match only, not a physical fit claim.'}


def board_underside_clearance(X):
    """Air between each XIAO pad row and whatever is below it, on both sides, against R18. Row 0 keeps R18's near-ledge lead."""
    old = read(h.h18.HERE / 'exports' / 'XIAO_Rod_Holder-assembly.stl'); hv = h.XO['pad_land_half_v']; under = h.BZ; rows = {}
    gap = lambda solid, x, y: min([under - float(t.position[2]) for t in solid.ray_cast((x, y, under - .005), (x, y, 1.)) if float(t.position[2]) < under] or [99.])
    for row, v in enumerate(h.XO['castellation_v_centres']):
        c = h.board_y(v); entry = {}
        for sign in (1, -1):
            pts = [(sign * x, c + d) for x in (7.5, 8.2, 8.89, 9.5, 9.95) for d in (-hv, -hv / 2, 0., hv / 2, hv)]
            news = [gap(X, a, b) for a, b in pts]; olds = [gap(old, a, b) for a, b in pts]; clear = [n for n, o in zip(news, olds) if o >= 1.]
            for p, n, o in zip(pts, news, olds): assert n >= min(1., o - .02), (row, sign, p, n, o)
            entry[f'{sign:+d}'] = {'smallest_gap_mm': round(min(news), 3), 'r18_smallest_gap_mm': round(min(olds), 3), 'smallest_gap_away_from_r18_near_ledge_lead_mm': round(min(clear), 3)}
        rows[str(row)] = {'pad_centre_y_mm': round(c, 3), **entry}
    added = (X - old) ^ h.union([h.box(min(s * 7., s * 9.95), max(s * 7., s * 9.95), h.board_y(v - hv), h.board_y(v + hv), 7.8, under) for v in h.XO['castellation_v_centres'] for s in (1, -1)])
    assert float(added.volume()) < .002, float(added.volume())
    return {'pad_rows': rows, 'material_added_since_r18_above_z_7p8_under_pads_mm3': round(float(added.volume()), 6), 'status': 'Probed at five X and five Y positions per pad. Every probe clears 1.0 mm, or matches R18 where the unchanged R18 near-ledge lead already sits closer (rows 0 and 1). Real solder height is unmeasured.'}


def battery_support(B):
    """Direct check that the open floor still locates the cell, cannot let a spacer fall through and gives the door something rigid."""
    lv = h.base.cage_levels(); pack = h.base.cell_shape(); cell = h.base.cell_shape(True); rows = {}
    for label, d in {'+Z': (0, 0, .85), '-Z': (0, 0, -.1), '+X': (.75, 0, 0), '-X': (-.75, 0, 0), '+Y_end_stop': (0, .6, 0)}.items(): rows[label] = round(ov(B, cell.translate(d)), 4); assert rows[label] > .05, (label, rows[label])
    plan = B.translate((0, 0, -(lv['floor_top'] - .05))).slice(0.) ^ mf.CrossSection.square((2 * lv['half_w'], lv['half_l'] + 13)).translate((-lv['half_w'], -13)); bay = mf.CrossSection.square((2 * lv['half_w'], lv['half_l'] + 13)).translate((-lv['half_w'], -13)); open_ = bay - plan; lo, hi = 0., 15.
    for _ in range(14):
        m = (lo + hi) / 2
        if open_.offset(-m, mf.JoinType.Round).is_empty(): hi = m
        else: lo = m
    roof = B.translate((0, 0, -(lv['roof_bottom'] + .05))).slice(0.) ^ bay
    assert 2 * lo <= 10.5, ('largest open circle under the cell', 2 * lo)
    return {'cell_reserve_moved_overlap_mm3': rows, 'floor_contact_area_at_cell_plane_mm2': round(float(plan.area()), 1), 'floor_contact_fraction_of_bay': round(float(plan.area() / bay.area()), 3), 'largest_open_circle_diameter_under_cell_mm': round(2 * lo, 2), 'roof_retaining_area_mm2': round(float(roof.area()), 1), 'note': 'Nothing under the pouch sits higher than the former floor plane. Pouch pressure and spacer sag are unmeasured.'}


def check():
    manifest = json.loads((OUT / 'manifest.json').read_text()); solids = {n: read(OUT / (n + '-assembly.stl')) for n in h.PLATE}; rep = {'manifest_sha256': h.sha(OUT / 'manifest.json'), 'checker_sha256': h.sha(h.HERE / 'verify19.py'), 'physical_fit_verified': False}
    spaces = {}
    for name in h.PLATE:
        rows = {}
        for label, region in h.regions(name).items():
            v = max(ov(solids[name], p) for p in region.poses()) if isinstance(region, h.spaces16.Swept) else ov(solids[name], region)
            rows[label] = round(v, 6); assert v < .002, (name, label, v)
        spaces[name] = rows
    rep['working_space_overlap_mm3'] = spaces
    for name, bands in {'Battery_Holder': [h.CAGE['near_band_y_mm'], h.CAGE['far_band_y_mm']], 'XIAO_Rod_Holder': [h.S['near_band_y_mm'], h.S['far_band_y_mm']]}.items():
        old = read(h.R16 / 'exports' / (name + '-assembly.stl'))
        for y0, y1 in bands:
            tube = h.box(-5.75, 5.75, y0, y1, -5.75, 3.) ^ h.cyl(5.75, -60, 60).rotate((-90, 0, 0)); d = float(((old ^ tube) - (solids[name] ^ tube)).volume() + ((solids[name] ^ tube) - (old ^ tube)).volume()); assert d < .05, (name, y0, d)
    B, X = solids['Battery_Holder'], solids['XIAO_Rod_Holder']; door, flexed = h.battery_door(), h.battery_door(True); K, Kf = h.keeper(), h.keeper(True); D = h.D
    assert ov(B, door) < .002 and ov(door, h.base.cell_shape(True)) < .002
    lift = {d: round(ov(B, door.translate((0, 0, d))), 4) for d in (.3, .5, .8)}; assert lift[.8] > .01, lift
    assert ov(B, flexed.translate((0, 0, 5))) < .002
    b_ = D['bridge']; sy0, sy1 = h.CAGE['gate_slot_y_mm']; dy0, dy1 = D['y_mm']; out, inn = dy0 - sy0, sy1 - dy1; assert out > 0 and inn > 0, (out, inn)
    tip = max(p[0] for p in D['tooth_yz_mm']); front = b_['front_y_mm']; floats = {}
    for p in (-out, 0., inn):      # Full permitted Y travel: catch, pouch clearance and bent-bar release at each extreme.
        seated = door.translate((0, p, 0)); catch = ov(B, seated.translate((0, 0, .3))); engage = tip + p - front; needed = engage + .05
        released = h.battery_door(tooth_dy=-needed).translate((0, p, 0)); route = max(ov(B, released.translate((0, 0, float(z)))) for z in np.linspace(0, 5, 26))
        back = b_['pocket_back_y_mm'] - (tip + p); pack = ov(seated, h.base.cell_shape())
        assert ov(B, seated) < .002 and catch > .05 and engage >= .2 and route < .002 and back >= .05 and pack < .002, (p, ov(B, seated), catch, engage, route, back, pack)
        floats[f'{p:+.2f}'] = {'seated_overlap_mm3': round(ov(B, seated), 5), 'tooth_overlap_lifted_0p3_mm3': round(catch, 4), 'tooth_engagement_y_mm': round(engage, 3), 'tooth_clearance_to_pocket_back_mm': round(back, 3), 'bar_deflection_needed_with_0p05_margin_mm': round(needed, 3), 'release_route_max_overlap_mm3': round(route, 5), 'catalogue_max_pack_overlap_mm3': round(pack, 5)}
    worst = max(v['bar_deflection_needed_with_0p05_margin_mm'] for v in floats.values()); tz0, tz1 = D['tongue_z_mm']; loaded = -D['tooth_half_x_mm'] - D['tongue_root_x_mm']
    rep['Battery_End_Door'] = {'free_legs': 0, 'release': 'Push the exposed centre tab toward the outside with a thumbnail from the cell side, then lift by the top bar.', 'seated_overlap_mm3': ov(B, door), 'tooth_overlap_when_lifted_mm3': lift, 'plate_thickness_mm': round(dy1 - dy0, 3), 'slot_float_y_mm': {'outward': round(out, 3), 'inward': round(inn, 3)}, 'y_float_checks': floats, 'release_check_scope': 'Tooth moved rigidly by the needed deflection; bar bending shape is not modelled.', 'spring': {**spring(loaded, tz1 - tz0, dy1 - dy0, worst), 'load_point': 'Root to the tooth edge nearest the root: the shortest loaded span, so the stiffest case.'}, 'side_clearance_in_slot_mm': round(13. - D['half_x_mm'], 3)}
    for n, t in h.SPACERS.items():
        assert ov(B, solids[n]) < .002, n; lv = h.base.cage_levels()
    rep['Battery_vertical_fit'] = {'reserve_height_mm': 4.9, 'catalogue_maximum_pack_mm': 4.3, 'nominal_code_thickness_mm': 4.0, 'remaining_gap_mm_by_spacer': {str(t): {'over_catalogue_max': round(4.9 - 4.3 - t, 2), 'over_nominal_code': round(4.9 - 4. - t, 2)} for t in h.SPACERS.values()}, 'status': 'The bought pack is unmeasured; negative means that spacer cannot fit a pack of that thickness.'}
    for dx, dy in h.reachable_poses(): assert ov(X, h.board_outline(dx, dy)) < .002
    assert ov(X, K) < .002 and ov(X, Kf) < .002 and ov(K, h.board_outline()) < .002
    for c in h.XO['components']: assert ov(K, h.component_box(c)) < .002 and ov(X, h.component_box(c)) < .002, c
    pull = {d: round(ov(X, K.translate((0, -d, 0))), 4) for d in (.1, .5, 1., 1.5)}; assert max(pull.values()) > .05, pull
    wires = {k: v for k, v in h.regions('XIAO_Rod_Holder').items() if k.startswith(('wire_exit', 'wire_run'))}; route = h.regions('XIAO_Rod_Holder')['retainer_route']; assert len(wires) >= 18
    for k, v in wires.items(): assert max(ov(p, v) for p in route.poses()) < .002, k
    hp = h.H['hoop']; rc = h.XO['components']['reset_button']; plane = X.slice(float(h.BOARD_TOP + 4)); sec = (mf.CrossSection.square((30, 30)).translate((-15, 10))) ^ plane
    rs = h.box(rc['u'][0] - .3, rc['u'][1] + .3, h.board_y(rc['v'][0]) - .3, h.board_y(rc['v'][1]) + .3, h.BOARD_TOP, 30) if hasattr(h, 'board_y') else None
    rs = rs or h.box(rc['u'][0] - .3, rc['u'][1] + .3, h.h17.board_y(rc['v'][0]) - .3, h.h17.board_y(rc['v'][1]) + .3, h.BOARD_TOP, 30); assert ov(X, rs) < .002 and ov(K, rs) < .002
    rep['XIAO_Rod_Holder'] = {'side_allowance_per_side_mm': 1.11, 'reset_open_from_above_with_0p3_margin_mm3_blocked': ov(X, rs), 'shoulder_to_reset_x_gap_mm': round(hp['shoulder_inner_x_mm'] - abs(rc['u'][0]), 2), 'shoulder_gap_over_pcb_mm': round(hp['shoulder_under_z_mm'] - h.BOARD_TOP, 2), 'hoop_gap_over_usb_shell_mm': round(hp['under_usb_z_mm'] - (h.BOARD_TOP + h.XO['components']['usb_c']['h']), 2), 'wire_exit_regions_checked': len(wires)}
    # The root-side tooth edge must clear too; a centre-load estimate understates
    # the stiffest beam case. This remains an unmeasured ideal-beam estimate.
    keeper_span = h.K['tongue']['tooth_x_mm'][0] - h.K['tongue']['x_mm'][0]
    rep['XIAO_Near_Keeper'] = {'tooth_overlap_when_pulled_mm3': pull, 'spring': spring(keeper_span, 2.0, 1.2, .35), 'ears_captured_by_rigid_grooves': True}
    section = lambda name, top: [c.area() for c in read(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')).slice(top).decompose() if c.area() > .05]
    rep['XIAO_body_islands_every_mm'] = {str(z): len(section('XIAO_Rod_Holder', float(z))) for z in range(4, 26, 3)}
    rep['orientation_comparison'] = {n: orientation(n) for n in h.ANCHORED}
    rep['R19_interfaces_unchanged_from_R18'] = interfaces(solids)
    rep['R19_battery_support'] = battery_support(B)
    rep['R19_board_underside_clearance'] = board_underside_clearance(X)
    rep['passed'] = True; (OUT / 'geometry-checks.json').write_text(json.dumps(rep, indent=2) + '\n'); print(json.dumps({k: rep[k] for k in ['Battery_End_Door', 'XIAO_Rod_Holder', 'XIAO_Near_Keeper', 'XIAO_body_islands_every_mm', 'orientation_comparison']})[:3000], flush=True)


if __name__ == '__main__':
    check()
