#!/usr/bin/env python3
"""Geometry screening of the four R20 exports: guard clearances, slide-on route and fingertip probe; key holder, battery and
XIAO changes against their accepted predecessors; print layers of every part.

Reads the exported meshes, not the source solids. Every allowance for solder, wire and fingertips is a stated
assumption from parameters.json. Nothing here is a physical fit, comfort, force or fatigue result.
"""
import sys
sys.dont_write_bytecode = True
import json, math
import numpy as np, manifold3d as mf
from matplotlib.path import Path as MplPath
import holder20 as h

OUT = h.HERE / 'exports'; G = h.G; base = h.base; h19 = h.h19; ROUND = mf.JoinType.Round; LAYER = G['layer_mm']; DENSITY = base.r15.P['print']['density_g_cm3']
def ov(a, b): return max(0., float((a ^ b).volume()))
def gap(a, b, reach=8.): return round(float(a.min_gap(b, reach)), 3)


# ---------------------------------------------------------------------------
# Fingertip probe: a rigid ball rolled over everything from outside, on a voxel grid
# ---------------------------------------------------------------------------
VOXEL = .25


def raster(solid, xs, ys, zs):
    X, Y = np.meshgrid(xs, ys, indexing='ij'); pts = np.c_[X.ravel(), Y.ravel()]; occ = np.zeros((len(xs), len(ys), len(zs)), bool)
    for k, z in enumerate(zs):
        layer = np.zeros(len(pts), bool)
        for loop in solid.slice(float(z)).to_polygons():
            loop = np.asarray(loop); lo, hi = loop.min(0), loop.max(0); m = (pts[:, 0] >= lo[0]) & (pts[:, 0] <= hi[0]) & (pts[:, 1] >= lo[1]) & (pts[:, 1] <= hi[1])
            if m.any(): layer[m] ^= MplPath(loop).contains_points(pts[m])       # even-odd: holes are separate loops
        occ[:, :, k] = layer.reshape(len(xs), len(ys))
    return occ


def dilate(occ, radius):
    """Ball centres that would intersect material."""
    r = radius / VOXEL; n = int(math.ceil(r)); g = np.arange(-n, n + 1); bx, by, bz = np.meshgrid(g, g, g, indexing='ij'); ball = (bx * bx + by * by + bz * bz <= r * r).astype(np.float32)
    shape = [s + 2 * n for s in occ.shape]; out = np.fft.irfftn(np.fft.rfftn(occ.astype(np.float32), shape, axes=(0, 1, 2)) * np.fft.rfftn(ball, shape, axes=(0, 1, 2)), shape, axes=(0, 1, 2))
    return out[n:n + occ.shape[0], n:n + occ.shape[1], n:n + occ.shape[2]] > .5


def flood(free):
    """Free ball centres connected to the outside of the grid."""
    reach = np.zeros_like(free)
    for axis in range(3):
        for end in (0, -1):
            index = [slice(None)] * 3; index[axis] = end; reach[tuple(index)] = free[tuple(index)]
    count = -1
    while count != (count := int(reach.sum())):
        grown = reach.copy()
        grown[1:] |= reach[:-1]; grown[:-1] |= reach[1:]; grown[:, 1:] |= reach[:, :-1]; grown[:, :-1] |= reach[:, 1:]; grown[:, :, 1:] |= reach[:, :, :-1]; grown[:, :, :-1] |= reach[:, :, 1:]
        reach = grown & free
    return reach


def box_distance(points, b):
    lo, hi = np.array(b[:3]), np.array(b[3:]); d = np.maximum(np.maximum(lo - points, points - hi), 0.); return np.sqrt((d * d).sum(1))


def fingertip_probe(guard, body):
    """Smallest distance a rigid ball can come to each socket terminal, with and without the guard."""
    xs = np.arange(-36., 36.01, VOXEL); ys = np.arange(-16., 30.01, VOXEL); zs = np.arange(-15., 9.51, VOXEL)
    occ_bare = raster(body, xs, ys, zs); occ_guard = occ_bare | raster(guard, xs, ys, zs)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij'); targets = {}
    for i in range(len(base.key_positions())):
        for j, t in enumerate(h.socket_tabs(i)): targets[f'key_{i}_terminal_{j}'] = {'metal': (t[0], t[2], t[4], t[1], t[3], t[5])}
    for name, solid in h.contact_envelopes().items(): targets[name]['with_stated_solder_and_wire_allowance'] = tuple(solid.bounding_box())
    rows = {}
    for radius in G['assumed_allowances']['fingertip_probe_radii_mm']:
        row = {}
        for label, occ in (('bare_key_holder', occ_bare), ('with_guard', occ_guard)):
            reach = flood(~dilate(occ, radius)); centres = np.c_[X[reach], Y[reach], Z[reach]]
            row[label] = {name: {kind: round(float(box_distance(centres, b).min() - radius), 2) for kind, b in boxes.items()} for name, boxes in targets.items()}
        rows[f'{radius:g}'] = row
    return rows


# ---------------------------------------------------------------------------
# Print layers of an exported print-frame mesh
# ---------------------------------------------------------------------------
def inscribed(section):
    lo, hi = 0., 6.
    for _ in range(12):
        mid = (lo + hi) / 2
        if section.offset(-mid, ROUND).is_empty(): hi = mid
        else: lo = mid
    return 2 * lo


def layer_scan(solid):
    """Every layer against the one below: floating starts, growth beyond 45 degrees and how wide that growth is."""
    top = solid.bounding_box()[5]; n = int(round(top / LAYER)); prev = None; rows = []; floating = []; worst = {'width_mm': 0.}
    for k in range(n):
        sec = solid.slice((k + .5) * LAYER)
        if prev is not None:
            for part in sec.decompose():
                if part.area() > .02 and (part ^ prev.offset(.05, ROUND)).is_empty(): floating.append({'layer': k, 'area_mm2': round(part.area(), 3), 'bounds': [round(v, 2) for v in part.bounds()]})
            beyond = sec - prev.offset(LAYER + .03, ROUND)
            if beyond.area() > .01:
                for part in beyond.decompose():
                    if part.area() < .01: continue
                    w = inscribed(part); row = {'layer': k, 'print_z_mm': round((k + 1) * LAYER, 2), 'area_mm2': round(part.area(), 3), 'width_mm': round(w, 3), 'bounds': [round(v, 2) for v in part.bounds()]}; rows.append(row)
                    if w > worst['width_mm']: worst = row
        else: first = sec
        prev = sec
    return {'layers': n, 'first_layer_area_mm2': round(first.area(), 2), 'first_layer_islands': len([p for p in first.decompose() if p.area() > .02]), 'floating_starts': floating,
            'regions_growing_faster_than_45_degrees': len(rows), 'widest_such_region': worst, 'all_such_regions': rows}


def thin_scan(solid, width):
    """Material narrower than `width` in any layer: it would print as less than two beads."""
    top = solid.bounding_box()[5]; worst = 0.; where = None
    for k in range(int(round(top / LAYER))):
        sec = solid.slice((k + .5) * LAYER); thin = sec - sec.offset(-width / 2, ROUND).offset(width / 2 + .01, ROUND)
        if thin.area() > worst: worst = thin.area(); where = k
    return {'narrower_than_mm': width, 'largest_area_in_one_layer_mm2': round(worst, 3), 'layer': where}


# ---------------------------------------------------------------------------
# Stated-assumption screens
# ---------------------------------------------------------------------------
def ring_screen(width, root_wall, tip_from_far_pole_deg, bond_half_deg, k=0., skin=1.05, n=4000):
    """Castigliano tip compliance of one clip arm (mm/N * E): R7 wall profile, clamped at the bonded angle from the crown."""
    th = np.radians(np.linspace(180 - tip_from_far_pole_deg, bond_half_deg, n)); tip = h.ROD['clip_tip_wall']
    t = tip + (root_wall - tip) * ((np.cos(th) + 1) / 2) ** 2; rm = h.BORE + t / 2; s = np.cumsum(np.r_[0., np.abs(np.diff(th))] * rm)
    I = width * t ** 3 / 12 + (k * s) * (t - (t - skin) * .5) ** 3 / 12
    x, z = rm * np.sin(th), rm * np.cos(th); M = (x[0] - x) * math.cos(th[0]) - (z[0] - z) * math.sin(th[0])
    return float(np.trapezoid(M ** 2 / I, s)), float(s[-1])


def screens():
    r = G['ring']; f = h.frame(); ref, _ = ring_screen(2.4, 1.4, 15, 34)
    row = lambda c: round(ref / c, 2)
    rings = {'reference': 'R19 XIAO far ring (2.4 mm, plain, bonded 34 degrees from the crown) = 1.00',
             'r19_xiao_near_skirted': row(ring_screen(2.4, 1.4, 15, 43, 1.)[0]), 'r19_battery_far': row(ring_screen(3.6, 1.6, 15, 34)[0]), 'r19_battery_near_skirted': row(ring_screen(3.6, 1.6, 15, 43, 1.)[0]),
             'r20_xiao_far_3p6_if_fully_bonded_like_r19': row(ring_screen(3.6, 1.4, 15, 34)[0]),
             'r20_guard_rear_plain': row(ring_screen(r['width_mm'], r['root_wall_mm'], r['gap_degrees'] / 2, r['bond_half_angle_degrees'])[0]),
             'r20_guard_front_skirted': row(ring_screen(r['width_mm'], r['root_wall_mm'], r['gap_degrees'] / 2, r['bond_half_angle_degrees'], 1.)[0])}
    rings['pairs'] = {'r19_xiao_holder': round(1 + rings['r19_xiao_near_skirted'], 2), 'r19_battery_holder': round(rings['r19_battery_far'] + rings['r19_battery_near_skirted'], 2),
                      'r20_xiao_holder_upper_bound': round(rings['r20_xiao_far_3p6_if_fully_bonded_like_r19'] + rings['r19_xiao_near_skirted'], 2), 'r20_guard': round(rings['r20_guard_rear_plain'] + rings['r20_guard_front_skirted'], 2)}
    rings['status'] = 'Relative curved-beam screen, elastic, modulus cancels. Not a measured slide force, grip or fatigue life.'
    b, t = G['rail_width_mm'], G['face_thickness_mm']; span = (G['y_rear_mm'] - G['rear_rim_mm']) - (G['y_front_mm'] + G['front_rim_mm'] + f['bay_clear'] / 2)
    rail = {'free_span_mm': round(span, 2), 'section_mm': [b, t], 'bending_stress_MPa_per_N_at_midspan_fixed_ends': round(span / 8 * 6 / (b * t * t), 2), 'deflection_mm_per_N_assuming_2000_MPa': round(span ** 3 / (192 * 2000 * b * t ** 3 / 12), 4),
            'layer_direction': 'Rails run along the rod, so this bending acts across the printed layers: the weaker direction. Rims, wings and ring arms are loaded inside their layers.', 'status': 'Ideal-beam estimate with an assumed modulus. Layer bond strength is unmeasured.'}
    return {'rings_relative_stiffness': rings, 'rail': rail}


# ---------------------------------------------------------------------------
def sd(a, b): return float((a - b).volume() + (b - a).volume())
def grams(v): return round(v * DENSITY / 1000, 3)


def compare_layers(name, new, old):
    """A changed part may not start anything in air, and may not add a wider unsupported span than its accepted predecessor had."""
    a, b = layer_scan(new), layer_scan(old); assert not a['floating_starts'], (name, a['floating_starts'][:3])
    wide = lambda scan: sorted(round(r['width_mm'], 1) for r in scan['all_such_regions'] if r['width_mm'] > 1.05)
    assert a['widest_such_region']['width_mm'] <= b['widest_such_region']['width_mm'] + .05 and len(wide(a)) <= len(wide(b)), (name, wide(a), wide(b))
    a['predecessor'] = {k: b[k] for k in ('layers', 'first_layer_area_mm2', 'regions_growing_faster_than_45_degrees', 'widest_such_region')}; a['spans_wider_than_1_mm'] = {'r20': wide(a), 'predecessor': wide(b)}
    del a['all_such_regions']; return a


def thinnest(section, width=1.18):
    """Area of plastic narrower than `width` in a plan section."""
    return float((section - section.offset(-width / 2, ROUND).offset(width / 2 + .01, ROUND)).area())


def key_holder(K, old):
    k = h.K20; b = h.P['bay']; c = h.P['carrier_rings']; z_pcb = base.PCB_Z; bottom = base.slab_bottom(); top = base.plate_top(); z_relief = z_pcb + b['plate_bottom_mm']; inner = k['ring_bore_mm'] / 2
    removed, added = old - K, K - old; windows = h.key_windows(); lead = 12.; ring_zone = h.cyl(6.0, c['mid_band_y_mm'][0] - .3, c['rear_band_y_mm'][1] + .3).rotate((-90, 0, 0)) ^ h.box(-7, 7, -10, 40, -7, bottom + 1.05)
    stray_removed = float((removed - windows - ring_zone).volume()); stray_added = float((added - ring_zone).volume()); assert stray_removed < .01 and stray_added < .01, (stray_removed, stray_added)
    regions = h.part_regions('Key_Carrier')
    spaces = {n: round(max(ov(K, p) for p in v.poses()) if isinstance(v, h.spaces16.Swept) else ov(K, v), 6) for n, v in regions.items()}; assert max(spaces.values()) < .002, {n: v for n, v in spaces.items() if v >= .002}
    assert ov(K, h.cyl(inner + .04, c['mid_band_y_mm'][0] + .4, c['mid_band_y_mm'][1] - .4).rotate((-90, 0, 0))) > .5 and ov(K, h.cyl(inner + .04, c['rear_band_y_mm'][0] + .4, c['rear_band_y_mm'][1] - .4).rotate((-90, 0, 0))) > .5, 'ring bore is not the stated diameter'
    # Every new window keeps at least 1.19 mm of plastic all round, at mid board level and (shoulders) at plate level.
    ligament = {}
    for label, z in (('socket_board_level', (bottom + .4 + z_pcb) / 2), ('switch_plate_level', z_relief + .6)):
        sec = K.slice(z); wins = [w_ for w_ in windows.slice(z).decompose() if w_.area() > .5]; miss = [float(((w_.offset(1.19, ROUND) - w_) - sec).area()) for w_ in wins]
        assert max(miss) < .02, (label, miss); ligament[label] = {'windows': len(wins), 'largest_shortfall_of_a_1p19_mm_border_mm2': round(max(miss), 4)}
    lower_cut = float((removed ^ windows ^ h.box(-40, 40, -20, 7.0, -20, 40)).volume()); assert lower_cut < .01, ('the lower row must keep its R16 board level', lower_cut)
    thin = {'windows_keep_a_1p19_mm_border': ligament, 'cut_from_the_lower_row_mm3': round(lower_cut, 4)}
    levels = {'rings_saddle_and_lead_in_below_the_slab': (-20, bottom), 'socket_board_level': (bottom, z_pcb), 'clip_relief_level': (z_pcb, z_relief), 'switch_plate': (z_relief, top)}
    cut = lambda s_, a, c_: float((s_ ^ h.box(-40, 40, -20, 40, a, c_)).volume())
    by_level = {n: {'z_mm': [round(a, 2), round(c_, 2)], 'r16_solid_PETG_g': grams(cut(old, a, c_)), 'r20_solid_PETG_g': grams(cut(K, a, c_))} for n, (a, c_) in levels.items()}
    return {'solid_mm3': round(K.volume(), 1), 'solid_PETG_g': grams(K.volume()), 'r16_solid_PETG_g': grams(old.volume()), 'change_solid_PETG_g': grams(K.volume() - old.volume()),
            'ring_bore_mm': k['ring_bore_mm'], 'r16_ring_bore_mm': k['r16_ring_bore_mm'], 'nominal_squeeze_on_8_mm_rod_mm': {'r16': round(8 - k['r16_ring_bore_mm'], 2), 'r20': round(8 - k['ring_bore_mm'], 2)},
            'windows_added': {'under_upper_switch_fronts': 4, 'shoulders': 2, 'removed_mm3': round(float((removed ^ windows).volume()), 1)}, 'ring_change_mm3': {'added_inside_the_old_bore': round(float(added.volume()), 2), 'removed_from_the_outside': round(float((removed ^ ring_zone).volume() - (removed ^ ring_zone ^ windows).volume()), 2)},
            'change_outside_windows_and_rings_mm3': round(stray_removed + stray_added, 5), 'working_space_overlap_mm3': spaces, 'plastic_narrower_than_1p18_mm_by_level': thin, 'by_level': by_level,
            'why_3p85_mm_thick': 'Kailh Choc V1 needs a 1.2 mm plate whose top sits 2.2 mm above the board the housing rests on, and its hot-swap socket is made for a 1.6 mm board: 1.2 + 1.05 + 1.6 = 3.85 mm. None of the three can be thinner where a key sits. Away from the sockets the board level was already 1.2 mm.',
            'not_taken': 'Larger windows need new 12-15 mm flat bridges or thin the board level where the R15 key holder snapped. The saddle and rings are the twist load path and are left solid.',
            'status': 'Rod grip, twist friction and insertion force are unmeasured. The R16 key holder remains the fallback.'}


def battery(B, old):
    b = h.B20; cut = lambda s_, y0, y1: s_ ^ h.box(-40, 40, y0, y1, -20, 40); shift = b['r19_plate_y_mm'][0] - b['plate_y_mm'][0]; lv = base.cage_levels()
    same_bay = sd(cut(B, -30, b['far_band_y_mm'][0] - .6), cut(old, -30, b['far_band_y_mm'][0] - .6)); same_end = sd(cut(B, b['plate_y_mm'][0] + .05, 30), cut(old, b['r19_plate_y_mm'][0] + .05, 30).translate((0, -shift, 0)))
    assert same_bay < .01 and same_end < .01, (same_bay, same_end)
    regions = h.part_regions('Battery_Holder')
    spaces = {n: round(max(ov(B, p) for p in v.poses()) if isinstance(v, h.spaces16.Swept) else ov(B, v), 6) for n, v in regions.items()}; assert max(spaces.values()) < .002, {n: v for n, v in spaces.items() if v >= .002}
    door = h.read(h.R19 / 'exports/Battery_End_Door-assembly.stl'); cell = base.cell_shape(True); pack = base.cell_shape(); assert ov(B, door) < .002 and ov(B, pack) < .002
    stop = {'r20': round(ov(B, cell.translate((0, .6, 0))), 3), 'r19': round(ov(old, cell.translate((0, .6, 0))), 3)}; assert stop['r20'] >= stop['r19'] - .05 and stop['r20'] > .05, stop
    held = {d: round(ov(B, cell.translate(v)), 3) for d, v in {'+Z': (0, 0, .85), '-Z': (0, 0, -.1), '+X': (.75, 0, 0), '-X': (-.75, 0, 0)}.items()}; assert min(held.values()) > .05, held
    for n, t in h19.SPACERS.items(): assert ov(B, h19.spacer(t)) < .002, n
    bed = lambda s_, y: s_.rotate((90, 0, 0)).slice(y); bed_diff = float((bed(B, b['plate_y_mm'][1] - .1) - bed(old, b['r19_plate_y_mm'][1] - .1)).area() + (bed(old, b['r19_plate_y_mm'][1] - .1) - bed(B, b['plate_y_mm'][1] - .1)).area()); assert bed_diff < .01, bed_diff
    return {'solid_mm3': round(B.volume(), 1), 'solid_PETG_g': grams(B.volume()), 'r19_solid_PETG_g': grams(old.volume()), 'change_solid_PETG_g': grams(B.volume() - old.volume()), 'length_mm': round(B.bounding_box()[4] - B.bounding_box()[1], 2), 'r19_length_mm': round(old.bounding_box()[4] - old.bounding_box()[1], 2),
            'removed': f'{shift:g} mm of empty gap between the cell stop and the end frame', 'cell_stop_y_mm': lv['half_l'], 'cell_stop': 'end frame side posts, X 8.8-10.6 mm each side, where the two corner blocks were',
            'difference_from_r19_up_to_the_far_ring_mm3': round(same_bay, 5), 'difference_of_end_frame_and_ring_from_r19_moved_mm3': round(same_end, 5), 'bed_section_difference_from_r19_mm2': round(bed_diff, 6),
            'working_space_overlap_mm3': spaces, 'reserve_moved_0p6_mm_past_the_stop_overlap_mm3': stop, 'reserve_moved_sideways_or_vertically_overlap_mm3': held, 'door_and_all_three_spacers_overlap_mm3': 0.,
            'status': 'Identified from the phone photo as the closed end; no dimension was taken from the photo. Cell fit and door use the unchanged R19 geometry and are unverified on the shorter part.'}


def xiao(X, old):
    y0, y1 = h.X20['far_ring_band_y_mm']; o0, o1 = h.X20['r19_far_ring_band_y_mm']; w = h.X20['wall']; c = h.X20['far_cheek']; outer = h.BORE + h.ROD['sensor_clip_root_wall']; s = h.S; half = s['board_outline_mm']['width'] / 2
    tube = h.cyl(outer + .02, y0 - .02, y1 + .02).rotate((-90, 0, 0)); boxes = [tube]
    for sign in (1, -1):
        xr = lambda a, b_: (min(sign * a, sign * b_), max(sign * a, sign * b_)); boxes += [h.box(*xr(*w['x_mm']), *w['y_mm'], w['bottom_z_mm'], w['top_z_mm']), h.box(*xr(*c['x_mm']), *c['y_mm'], *c['z_mm'])]
    allowed = h.union(boxes); removed = float((old - X).volume()); stray = float(((X - old) - allowed).volume()); assert removed < .01 and stray < .01, (removed, stray)
    regions = h.part_regions('XIAO_Rod_Holder'); hw = h19.WIRE['corridor_width_mm'] / 2
    spaces = {n: round(max(ov(X, p) for p in v.poses()) if isinstance(v, h.spaces16.Swept) else ov(X, v), 6) for n, v in regions.items()}; assert max(spaces.values()) < .002, {n: v for n, v in spaces.items() if v >= .002}
    K = h.read(h.R19 / 'exports/XIAO_Near_Keeper-assembly.stl'); assert ov(X, K) < .002
    for comp in h19.XO['components']: assert ov(X, h19.component_box(comp)) < .002, comp
    # Board seat: free sideways travel at the seated position, and the axial travel R19 already had.
    def free(dx, dy): return ov(X, h19.board_outline(dx, dy)) < .002
    lo, hi = 0., 1.5
    for _ in range(12):
        mid = (lo + hi) / 2; lo, hi = (mid, hi) if free(mid, 0.) and free(-mid, 0.) else (lo, mid)
    lo_o, hi_o = 0., 1.5
    for _ in range(12):
        mid = (lo_o + hi_o) / 2; lo_o, hi_o = (mid, hi_o) if ov(old, h19.board_outline(mid, 0.)) < .002 else (lo_o, mid)
    t = h19.board_travel(); assert free(0, -(t['near'] - .1)) and free(0, t['far'] - .1) and .2 < lo < .4, (lo, t)
    keel = h.box(-s['keel_x_mm'] - .2, s['keel_x_mm'] + .2, -10, 30, 0, 9); arms = ((X - old) ^ tube) - keel; nearest = gap(arms, (old ^ h.box(-40, 40, -10, y0 - .05, -20, 40)) - keel, 4.)
    def contains(section, p):
        inside = False
        for loop in section.to_polygons(): inside ^= bool(MplPath(np.asarray(loop)).contains_point(p))
        return inside
    def bonded(yy):   # largest angle from the crown at which other plastic still touches the outside of the ring wall
        sec = X.rotate((90, 0, 0)).slice(float(yy)); far = 0.
        for a in np.arange(0, 120.5, .5):
            if contains(sec, (outer + .15) * np.array([math.sin(math.radians(a)), -math.cos(math.radians(a))])): far = float(a)
            else: break
        return far
    b_new, b_old = bonded((y0 + o0) / 2), bonded((o0 + o1) / 2); assert nearest >= .8 and b_new < b_old, (nearest, b_new, b_old)
    return {'solid_mm3': round(X.volume(), 1), 'solid_PETG_g': grams(X.volume()), 'r19_solid_PETG_g': grams(old.volume()), 'change_solid_PETG_g': grams(X.volume() - old.volume()), 'removed_from_r19_mm3': round(removed, 5), 'added_outside_ring_walls_and_cheeks_mm3': round(stray, 5),
            'side_walls': {'inner_face_x_mm': w['x_mm'][0], 'gap_to_board_edge_mm': round(w['x_mm'][0] - half, 2), 'top_above_board_top_mm': round(w['top_z_mm'] - h19.BOARD_TOP, 2), 'board_sits_this_deep_between_them_mm': round(w['top_z_mm'] - h19.BZ, 2), 'beside_pad_rows_y_mm': w['y_mm'], 'thickness_mm': round(w['x_mm'][1] - w['x_mm'][0], 2)},
            'far_corner_cheeks': {'inner_face_x_mm': c['x_mm'][0], 'gap_to_board_edge_mm': round(c['x_mm'][0] - half, 2), 'y_mm': c['y_mm'], 'last_pad_allowance_ends_y_mm': round(h19.board_y(h19.XO['castellation_v_centres'][-1]) + hw, 2)},
            'board_free_sideways_travel_each_way_mm': {'r20': round(lo, 2), 'r19_at_the_usb_end': round(lo_o, 2)}, 'board_axial_travel_mm': {'toward_near_stops': round(t['near'], 2), 'toward_far_stops': round(t['far'], 2)},
            'far_ring': {'band_y_mm': [y0, y1], 'width_mm': round(y1 - y0, 2), 'r19_width_mm': round(o1 - o0, 2), 'bore_mm': h.ROD['clip_diameter'], 'root_wall_mm': h.ROD['sensor_clip_root_wall'], 'crown_bonded_to_degrees_from_crown': {'added_1p2_mm_strip': b_new, 'r19_band_on_the_v_bars': b_old},
                         'free_arm_arc_degrees': {'added_1p2_mm_strip': 165 - b_new, 'r19_band_on_the_v_bars': 165 - b_old}, 'added_arms_to_nearest_other_plastic_mm': nearest, 'near_ring': 'unchanged: 2.4 mm band with its 45-degree print lead-in'},
            'working_space_overlap_mm3': spaces, 'keeper_and_component_overlap_mm3': 0.,
            'status': 'Wires must now rise 1.15 mm before turning outward. Real solder, wire and header sizes are unmeasured; board fit and keeper retention are unverified.'}


def check():
    manifest = json.loads((OUT / 'manifest.json').read_text()); rep = {'manifest_sha256': h.sha(OUT / 'manifest.json'), 'checker_sha256': h.sha(h.HERE / 'verify20.py'), 'physical_fit_verified': False, 'physical_comfort_verified': False, 'physical_strength_verified': False}
    for name in h.PARTS: assert h.sha(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')) == manifest['parts'][name]['stl_sha256'], (name, 'export does not match manifest')
    solid = {n: h.read(OUT / (n + '-assembly.stl')) for n in h.PARTS}; printed = {n: h.read(OUT / (n + '-SOURCE-REQUIRES-PREPARATION.stl')) for n in h.PARTS}
    Gd, C, B, X = solid['Finger_Guard'], solid['Key_Carrier'], solid['Battery_Holder'], solid['XIAO_Rod_Holder']
    old = {'Key_Carrier': h.carrier_r16(), 'Battery_Holder': h.read(h.R19 / 'exports/Battery_Holder-assembly.stl'), 'XIAO_Rod_Holder': h.read(h.R19 / 'exports/XIAO_Rod_Holder-assembly.stl')}
    old_printed = {'Key_Carrier': h.read(h.R16 / 'exports/Key_Carrier-SOURCE-REQUIRES-PREPARATION.stl'), 'Battery_Holder': h.read(h.R19 / 'exports/Battery_Holder-SOURCE-REQUIRES-PREPARATION.stl'), 'XIAO_Rod_Holder': h.read(h.R19 / 'exports/XIAO_Rod_Holder-SOURCE-REQUIRES-PREPARATION.stl')}
    bought = h.bought_parts(); contacts = h.contact_envelopes()

    rep['Key_Carrier'] = key_holder(C, old['Key_Carrier']); rep['Battery_Holder'] = battery(B, old['Battery_Holder']); rep['XIAO_Rod_Holder'] = xiao(X, old['XIAO_Rod_Holder'])

    # --- Guard: its own keep-clear spaces, then everything it sits beside --------------------------------------
    spaces = {k: round(ov(Gd, v), 6) for k, v in h.part_regions('Finger_Guard').items()}; assert max(spaces.values()) < .002, spaces
    seated = {'key_holder': {'overlap_mm3': round(ov(Gd, C), 6), 'smallest_gap_mm': gap(Gd, C)}, 'r16_key_holder': {'overlap_mm3': round(ov(Gd, old['Key_Carrier']), 6), 'smallest_gap_mm': gap(Gd, old['Key_Carrier'])}}
    for k, v in {**bought, **contacts}.items(): seated[k] = {'overlap_mm3': round(ov(Gd, v), 6), 'smallest_gap_mm': gap(Gd, v)}
    assert all(v['overlap_mm3'] < .002 for v in seated.values()), {k: v for k, v in seated.items() if v['overlap_mm3'] >= .002}
    lower = [k for k in seated if k.startswith(('key_0', 'key_1', 'key_2'))]
    obstacles = h.union([C, old['Key_Carrier'], *bought.values(), *contacts.values()]); pad = G['prop_tab']
    assert abs(seated['key_holder']['smallest_gap_mm'] - pad['gap_to_key_holder_mm']) < .02, seated['key_holder']
    # Slide-on from the handle end: the guard backed off toward the hand in 0.25 mm steps until it is clear of the key holder.
    steps = np.arange(.25, 19.01, .25); route = [ov(Gd.translate((0, -float(d), 0)), obstacles) for d in steps]; assert max(route) < .002, max(route)
    # Pushed home against the key holder's middle ring.
    lo, hi = 0., 1.
    for _ in range(12):
        mid = (lo + hi) / 2
        if ov(Gd.translate((0, mid, 0)), obstacles) > .002: hi = mid
        else: lo = mid
    sb = (Gd.translate((0, hi + .05, 0)) ^ obstacles).bounding_box()
    assert .2 < lo < .4 and max(abs(sb[0]), abs(sb[3])) < 6.2 and sb[2] > -6. and sb[4] > G['y_rear_mm'], ('the stop must be ring against ring', lo, sb)
    # Twist about the rod until a pad meets the key holder.
    twist = {}
    for sign in (1, -1):
        lo_a, hi_a = 0., 3.
        for _ in range(12):
            mid = (lo_a + hi_a) / 2
            if ov(Gd.rotate((0, sign * mid, 0)), obstacles) > .002: hi_a = mid
            else: lo_a = mid
        hit = (Gd.rotate((0, sign * (hi_a + .05), 0)) ^ obstacles).bounding_box()
        # The pad and its 45-degree lead-in share one top face; all of it must land on the plain underside in front of the socket pads (Y 0.4).
        assert pad['y_mm'][0] - .1 <= hit[1] and hit[4] <= .3 and min(abs(hit[0]), abs(hit[3])) > pad['inner_x_mm'] - .3, ('a wing must land on its pad first', sign, hit)
        twist[f'{sign:+d}'] = {'free_twist_degrees': round(lo_a, 2), 'first_contact_bounds_mm': [round(v, 2) for v in hit]}
    # Free spring arms against the rigid hull.
    # Measured from 10 degrees past the bonded crown, where an arm has left the keel's side face; nearer than that the distance is just the root.
    r = G['ring']; bond = math.radians(r['bond_half_angle_degrees'] + 10.); L = 12.
    arms = h.guard_rings()[0] - h.xz(h.poly([(0, 0), (-L * math.sin(bond), -L * math.cos(bond)), (L * math.sin(bond), -L * math.cos(bond))]), -20, 20)
    arm_gap = gap(arms, h.guard_hull()); assert arm_gap >= .6, arm_gap
    rep['Finger_Guard'] = {'solid_mm3': round(Gd.volume(), 1), 'solid_PETG_g': grams(Gd.volume()), 'bounds_mm': [round(v, 3) for v in Gd.bounding_box()],
                           'below_rod_axis_mm': round(-Gd.bounding_box()[2], 2), 'below_rod_surface_mm': round(-Gd.bounding_box()[2] - h.ROD['diameter'] / 2, 2), 'wider_than_key_holder_each_side_mm': round(Gd.bounding_box()[3] - h.P['slab']['lower_half_x_mm'], 2),
                           'wing_angle_degrees': round(math.degrees(h.frame()['alpha']), 2), 'bay_clear_width_mm': round(h.frame()['bay_clear'], 2), 'own_keep_clear_overlap_mm3': spaces, 'seated': seated,
                           'smallest_gap_to_lower_row_bought_parts_and_allowances_mm': min(seated[k]['smallest_gap_mm'] for k in lower),
                           'slide_on_route': {'steps_mm': [float(steps[0]), float(steps[-1]), .25], 'largest_overlap_mm3': round(max(route), 6), 'obstacles': 'R20 and R16 key holders, switches, largest sockets, tape and wire zones under sockets, terminal allowances'},
                           'pushed_home': {'free_travel_toward_tip_mm': round(lo, 2), 'stop_bounds_mm': [round(v, 2) for v in sb], 'stop': 'guard rear ring against the key holder middle ring'},
                           'twist_until_a_pad_bears': twist, 'free_arm_to_hull_gap_mm': arm_gap, 'ring_skirt_lead_mm': round(h.guard_rings()[1], 2), 'fits': 'the R20 key holder and the accepted R16 one'}

    # --- Fingertip probe -----------------------------------------------------------------------------------------
    rod = h.cyl(h.ROD['diameter'] / 2, -40, 60).rotate((-90, 0, 0)); body = h.union([C, rod] + [v for k, v in bought.items() if k.endswith(('_switch', '_socket'))])
    probe = fingertip_probe(Gd, body); low = {}
    for radius, row in probe.items():
        names = [n for n in row['with_guard'] if n.startswith(('key_0', 'key_1', 'key_2'))]
        low[radius] = {'bare_key_holder_smallest_clearance_to_allowance_mm': min(row['bare_key_holder'][n]['with_stated_solder_and_wire_allowance'] for n in names),
                       'with_guard_smallest_clearance_to_allowance_mm': min(row['with_guard'][n]['with_stated_solder_and_wire_allowance'] for n in names),
                       'with_guard_smallest_clearance_to_metal_mm': min(row['with_guard'][n]['metal'] for n in names),
                       'closest_with_guard': min(names, key=lambda n: row['with_guard'][n]['with_stated_solder_and_wire_allowance']), 'lower_row_with_guard': {n: row['with_guard'][n] for n in names}}
        # Screen: 1.0 mm for balls of 12 mm and up; 0.75 mm for the 10 mm ball, which is smaller than an adult fingertip.
        assert low[radius]['with_guard_smallest_clearance_to_allowance_mm'] >= (1.0 if float(radius) >= 6 else .75), (radius, low[radius])
    assert min(v['bare_key_holder_smallest_clearance_to_allowance_mm'] for v in low.values()) < .3, 'The bare key holder should show the reported contact'
    rep['fingertip_probe'] = {'method': f'Rigid ball rolled from outside over the key holder, rod, switches, sockets and guard on a {VOXEL} mm grid; clearance is centre distance minus radius, so a negative or near-zero value means the ball touches. Grid error about {VOXEL} mm.',
                              'lower_row_summary_by_ball_radius_mm': low, 'by_ball_radius_mm': probe,
                              'limits': 'A fingertip is soft and not a ball; hand size and solder height are unmeasured. The upper two keys sit forward of the guard and are not covered by it. The closest approaches are from the open rear, between the guard and the upper row, not from the hand side.'}

    # --- Print layers ----------------------------------------------------------------------------------------------
    guard_scan = layer_scan(printed['Finger_Guard']); guard_scan['thin'] = thin_scan(printed['Finger_Guard'], .8); assert not guard_scan['floating_starts'] and guard_scan['widest_such_region']['width_mm'] <= 1.05, guard_scan['widest_such_region']
    rep['print_layers'] = {'Finger_Guard': guard_scan, **{n: compare_layers(n, printed[n], old_printed[n]) for n in ('Key_Carrier', 'Battery_Holder', 'XIAO_Rod_Holder')}}
    rep['print_orientation'] = {'all': 'Rod axis vertical, as every ring in this family is printed, so ring arms are closed loops inside each layer.',
                                'Finger_Guard': 'Rear face (toward the tip) on the bed. Rear ring plain on the bed; front ring at the top on a 45-degree arc lead-in; the rounded finger edge is the last layer.',
                                'Key_Carrier': 'Unchanged from R16: tip edge on the bed, nose last. Every new window points toward the nose, so its roof is two 45-degree slopes.',
                                'Battery_Holder': 'Unchanged from R19: closed end on the bed. Same bed footprint; 13 layers shorter.', 'XIAO_Rod_Holder': 'Unchanged from R19: USB end on the bed. Walls grow from the fixed hoop lips; cheeks and the taller far ring start on the bed.'}

    rep['screens'] = screens()
    was = {n: grams(old[n].volume()) for n in old}; now = {n: grams(solid[n].volume()) for n in h.PARTS}
    rep['installed_mass_solid_PETG_g'] = {'r16_r19': was, 'r20': now, 'change_by_part': {n: round(now[n] - was.get(n, 0.), 3) for n in now}, 'three_revised_parts_change': round(sum(now[n] - was[n] for n in was), 3), 'finger_guard_added': now['Finger_Guard'],
                                          'net_change_with_guard': round(sum(now.values()) - sum(was.values()), 3), 'unchanged_and_not_counted': 'battery door, XIAO keeper, one cell spacer',
                                          'note': 'CAD solid at 1.27 g/cm3. Earlier sliced parts came out at about 0.90 to 0.93 of CAD solid. Tear-off pads and purge are not installed mass.'}
    rep['passed'] = True; (OUT / 'geometry-checks.json').write_text(json.dumps(rep, indent=2) + '\n')
    brief = {'mass': rep['installed_mass_solid_PETG_g'], 'key': {k: rep['Key_Carrier'][k] for k in ('change_solid_PETG_g', 'windows_added', 'ring_change_mm3', 'plastic_narrower_than_1p18_mm_by_level')}, 'battery': {k: rep['Battery_Holder'][k] for k in ('length_mm', 'r19_length_mm', 'reserve_moved_0p6_mm_past_the_stop_overlap_mm3')},
             'xiao': {k: rep['XIAO_Rod_Holder'][k] for k in ('side_walls', 'board_free_sideways_travel_each_way_mm', 'far_ring')}, 'guard_gap_min_lower_row': rep['Finger_Guard']['smallest_gap_to_lower_row_bought_parts_and_allowances_mm'], 'probe': low,
             'print': {n: {k: v[k] for k in ('first_layer_area_mm2', 'regions_growing_faster_than_45_degrees', 'widest_such_region')} for n, v in rep['print_layers'].items()}, 'twist': twist, 'pushed_home': rep['Finger_Guard']['pushed_home'], 'arm_gap': arm_gap, 'screens': rep['screens']}
    print(json.dumps(brief, indent=1), flush=True)


if __name__ == '__main__':
    check()
