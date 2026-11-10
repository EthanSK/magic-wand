#!/usr/bin/env python3
"""R20: finger guard, tighter and lighter key holder, shorter battery holder, walled XIAO holder.

Composes the frozen R16-R19 chain and edits none of it. Finger_Guard is new. Key_Carrier re-runs the R16 build with its
own ring bore and extra windows. Battery_Holder re-runs the R19 build with a nearer closed end. XIAO_Rod_Holder is the
R19 solid plus a wider ring band, side walls and corner cheeks; nothing is removed from it.
The guard's sloped faces are modelled as 0.2 mm steps on the print layer grid (print Z = y_rear - Y), so the
exported mesh is what the slicer cuts. Nothing here is a physical fit, comfort or strength result.
"""
import sys
sys.dont_write_bytecode = True
from functools import lru_cache
from pathlib import Path
import json, math, os
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
R19 = HERE.parent / 'carbon-rod-holders-r19-lightweight'
sys.path.insert(0, str(R19))
import holder19 as h19  # noqa: E402

base = h19.base; h18 = h19.h18; P = h19.P; S = h19.S; R16 = h19.R16; spaces16 = h19.spaces16
LOCAL = json.loads((HERE / 'parameters.json').read_text()); G = LOCAL['guard']; X20 = LOCAL['xiao']; K20 = LOCAL['key_holder']; B20 = LOCAL['battery']
box, cyl, union, mesh, sha, rect = h19.box, h19.cyl, h19.union, h19.mesh, h19.sha, h19.rect
ROD = P['rod']; BORE = ROD['clip_diameter'] / 2; CORRIDOR = base.CORRIDOR; ROUND = mf.JoinType.Round
PARTS = ['Key_Carrier', 'Battery_Holder', 'XIAO_Rod_Holder', 'Finger_Guard']; ANCHORED = list(PARTS)
UNCHANGED_R19 = ['Battery_End_Door', 'XIAO_Near_Keeper', *h19.SPACERS]


def xz(section, y0, y1):
    """Extrude an (x, z) outline along Y from y0 to y1."""
    return h18._xz(section, y0, y1)


def poly(points): return mf.CrossSection([base.ccw(points)])


# ---------------------------------------------------------------------------
# R7 clip ring with the opening angle as a parameter. At 30 degrees it is base.ring / base.arc_skirt.
# Both are built crown-up, as in R7; the guard mirrors them so the crown sits on its keel.
# ---------------------------------------------------------------------------
def clip_wall(root_wall):
    tip = ROD['clip_tip_wall']
    return lambda a: tip + (root_wall - tip) * ((math.sin(a) + 1) / 2) ** 2


def clip_ring(y0, y1, gap_deg, root_wall, bore=None):
    BORE = globals()['BORE'] if bore is None else bore
    gap = math.radians(gap_deg); wall = clip_wall(root_wall); width = y1 - y0; y = (y0 + y1) / 2
    angles = np.linspace(-math.pi / 2 + gap / 2, 3 * math.pi / 2 - gap / 2, 221); t = np.array([wall(a) for a in angles])
    outer = np.column_stack(((BORE + t) * np.cos(angles), (BORE + t) * np.sin(angles)))
    inside = np.column_stack((BORE * np.cos(angles[::-1]), BORE * np.sin(angles[::-1])))
    profile = mf.CrossSection([np.vstack((outer, inside))])
    for a, w in ((angles[0], t[0]), (angles[-1], t[-1])):
        profile += mf.CrossSection.circle(float(w / 2), 32).translate(((BORE + w / 2) * math.cos(a), (BORE + w / 2) * math.sin(a)))
    shape = mf.Manifold.extrude(profile, width).rotate((90, 0, 0)).translate((0, y + width / 2, 0))
    for sign in (-1, 1):
        edge = y + sign * width / 2
        shape -= mf.Manifold.cylinder(.25, BORE, BORE + .25, 64).rotate((-90 * sign, 0, 0)).translate((0, edge - sign * .25, 0))
    return shape


def clip_skirt(band_y0, band_y1, lead_sign, gap_deg, root_wall, root_phi_deg, k, skin, bore=None):
    """Arc lead-in below the free arms: a point at arc distance s from the tip starts k*s before the band."""
    BORE = globals()['BORE'] if bore is None else bore
    gap = math.radians(gap_deg); wall = clip_wall(root_wall); edge = band_y1 if lead_sign > 0 else band_y0
    angles = np.linspace(-math.pi / 2 + gap / 2, math.radians(root_phi_deg), 97)
    mids = np.array([BORE + wall(a) / 2 for a in angles])
    s = np.concatenate([[0.], np.cumsum(np.diff(angles) * (mids[1:] + mids[:-1]) / 2)])
    lead = np.maximum(k * s, .02); lead_max = float(lead[-1]); arms = []
    for sign in (1, -1):
        outer = [(sign * (BORE + wall(a)) * math.cos(a), (BORE + wall(a)) * math.sin(a)) for a in angles]
        inside = [(sign * BORE * math.cos(a), BORE * math.sin(a)) for a in angles[::-1]]
        prism = mf.Manifold.extrude(mf.CrossSection([base.ccw(outer + inside)]), lead_max)

        def warp(v, sign=sign):
            u, w, hgt = v[:, 0], v[:, 1], v[:, 2]
            a = np.arctan2(w, sign * u); r = np.hypot(u, w)
            t = np.array([wall(x) for x in a]); frac = np.clip(hgt / lead_max, 0, 1)
            new_r = BORE + (r - BORE) * (1 - frac * (1 - skin / t))
            return np.column_stack([sign * new_r * np.cos(a), new_r * np.sin(a), frac * np.interp(a, angles, lead)])
        arms.append(prism.warp_batch(warp).transform(np.array([[1, 0, 0, 0], [0, 0, lead_sign, edge], [0, 1, 0, 0]], dtype=float)))
    return union(arms), lead_max


# ---------------------------------------------------------------------------
# Finger guard
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def frame():
    """One wing in the XZ plane, +X side: its inner surface is the line through the chine that is tangent,
    below the rod, to the circle that keeps ring_clear_radius around the ring arms."""
    xg, zc, rc = G['gunwale_inner_x_mm'], G['chine_inner_z_mm'], G['ring_clear_radius_mm']
    a = xg * xg - rc * rc; b = -2 * xg * zc; c = zc * zc - rc * rc
    m = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a); alpha = math.atan(m)
    eu = np.array([math.cos(alpha), math.sin(alpha)]); en = np.array([math.sin(alpha), -math.cos(alpha)])
    t0 = rc * en; uc = (xg - t0[0]) / eu[0]; assert abs(t0[1] + uc * eu[1] - zc) < 1e-9
    w = G['rail_width_mm']; n = G['rails_per_side']; uk = (G['keel_half_x_mm'] - t0[0]) / eu[0]; ug = uc - G['gunwale_root_u_mm']
    clear = (ug - uk - n * w) / (n + 1); rails = [uk + (i + 1) * clear + (i + .5) * w for i in range(n)]
    edges = [uk] + [u + s * w / 2 for u in rails for s in (-1, 1)] + [ug]
    return dict(alpha=alpha, eu=eu, en=en, t0=t0, uc=uc, uk=uk, ug=ug, rails=rails, bay_clear=clear, bays=list(zip(edges[::2], edges[1::2])))


def wing_point(u, depth=0.):
    """Point on the +X wing: u along the wing from the tangent point, depth from the inner surface outward."""
    f = frame(); p = f['t0'] + u * f['eu'] + depth * f['en']; return float(p[0]), float(p[1])


def both(section): return section + section.mirror((1, 0))


@lru_cache(maxsize=1)
def envelope():
    """Everything inside the guard's outer skin: above both outer wing lines, apex rounded, cut at the gunwales."""
    f = frame(); t = G['face_thickness_mm']; xo = G['gunwale_outer_x_mm']; rho = G['apex_outer_radius_mm']
    p = wing_point(0., t); far = wing_point(70., t); apex = p[1] - p[0] * f['eu'][1] / f['eu'][0]
    region = poly([(0, apex), far, (far[0], 40.), (-far[0], 40.), (-far[0], far[1])]).offset(-rho, ROUND, 2., 96).offset(rho, ROUND, 2., 96)
    return region ^ rect(-xo, xo, -20, G['gunwale_top_z_mm'])


@lru_cache(maxsize=1)
def shell():
    """The whole V sheet between the gunwale outer faces."""
    f = frame(); p = wing_point(0.); far = wing_point(70.); apex = p[1] - p[0] * f['eu'][1] / f['eu'][0]
    inner = poly([(0, apex), far, (far[0], 40.), (-far[0], 40.), (-far[0], far[1])])
    return envelope() - inner


@lru_cache(maxsize=1)
def crown_band():
    """Wedge of keel under the rod that carries both ring crowns; guard() cuts the keel bore through it. Its edges
    stay square: rounded, they would meet the ring bore chamfers in a zero-angle cusp."""
    r = G['ring']; bond = math.radians(r['bond_half_angle_degrees']); L = 12.
    return mf.CrossSection.circle(G['ring_clear_radius_mm'] + .45, 128) ^ poly([(0, 0), (-L * math.sin(bond), -L * math.cos(bond)), (L * math.sin(bond), -L * math.cos(bond))])


@lru_cache(maxsize=1)
def members():
    """Members present in every layer: the keel, both gunwales and the rails. Every bay edge is square to the wing,
    so all six windows have the same clear width on the finger side."""
    f = frame(); t = G['face_thickness_mm']; w = G['rail_width_mm']; xg, xo, top = G['gunwale_inner_x_mm'], G['gunwale_outer_x_mm'], G['gunwale_top_z_mm']
    beyond = lambda u: poly([wing_point(u, -3.), wing_point(90., -3.), wing_point(90., t + 4.), wing_point(u, t + 4.)])      # the wing outboard of u
    keel = shell() - both(beyond(f['uk']))
    gunwale = (shell() ^ beyond(f['ug'])) + rect(xg, xo, wing_point(f['uc'])[1] - .2, top)
    rails = [poly([wing_point(u - w / 2), wing_point(u + w / 2), wing_point(u + w / 2, t), wing_point(u - w / 2, t)]) for u in f['rails']]
    return keel + both(mf.CrossSection.batch_boolean([gunwale] + rails, mf.OpType.Add))


def openings(width):
    """Arrow window sections of one layer: each bay open over `width`, centred."""
    t = G['face_thickness_mm']; cuts = []
    for ua, ub in frame()['bays']:
        c = (ua + ub) / 2; a, b = max(ua, c - width / 2), min(ub, c + width / 2)
        cuts.append(poly([wing_point(a, -.6), wing_point(b, -.6), wing_point(b, t + .6), wing_point(a, t + .6)]))
    return both(mf.CrossSection.batch_boolean(cuts, mf.OpType.Add))


def layer_key(k):
    """What a print layer holds, as a hashable key. Layer k spans Y y_rear-(k+1)*step .. y_rear-k*step."""
    step = G['layer_mm']; y_hi = G['y_rear_mm'] - k * step; y_lo = y_hi - step; yc = (y_hi + y_lo) / 2
    full = round(frame()['bay_clear'], 6)
    if G['y_rear_mm'] - yc < G['rear_rim_mm']: window = 0.
    else:
        w = 2 * (yc - (G['y_front_mm'] + G['front_rim_mm']))      # 45 degrees: 0.2 mm narrower each side per layer
        up = (G['y_rear_mm'] - yc) - G['rear_rim_mm']; g = G['rear_gusset_mm']
        if up < g: w = min(w, full - 2 * (g - up))                # rear root gussets: 45 degrees, narrowing as the print rises
        window = full if w >= full else (round(w, 6) if w >= G['arrow_min_opening_mm'] else 0.)
    d = yc - G['y_front_mm']; ro, ri = G['front_round_outer_mm'], G['front_round_inner_mm']
    inset_o = round(ro - math.sqrt(ro * ro - (ro - d) ** 2), 6) if d < ro else 0.
    inset_i = round(ri - math.sqrt(ri * ri - (ri - d) ** 2), 6) if d < ri else 0.
    t = G['prop_tab']; reach = G['gunwale_inner_x_mm'] - t['inner_x_mm']; t0, t1 = t['y_mm']
    if t0 - 1e-6 <= y_lo and y_hi <= t1 + 1e-6: tab = reach                       # the pad itself
    elif y_hi > t1: tab = max(0., reach - (y_hi - t1))                              # its 45-degree lead-in, grown from the gunwale
    else: tab = 0.
    return (window, inset_o, inset_i, round(tab, 6))


@lru_cache(maxsize=None)
def layer_section(key):
    window, inset_o, inset_i, tab = key; e = G['edge_radius_mm']; full = round(frame()['bay_clear'], 6)
    hull = members() if window == full else (shell() + members() if window == 0. else (shell() - openings(window)) + members())
    hull = hull.offset(-e, ROUND, 2., 32).offset(e, ROUND, 2., 32) + crown_band()     # rounds every convex edge that a finger or wire meets
    if inset_i: hull = hull.offset(-inset_i, ROUND, 2., 32)
    if inset_o: hull = hull ^ envelope().offset(-inset_o, ROUND, 2., 32)
    if tab:
        t = G['prop_tab']; xg = G['gunwale_inner_x_mm']; z0, z1 = t['z_mm']
        assert z1 < G['gunwale_top_z_mm'], 'The pad must end inside the gunwale height'
        hull += both(rect(xg - tab, xg + .6, z0, z1))
    return hull


@lru_cache(maxsize=1)
def guard_rings():
    r = G['ring']; k = 1 / math.tan(math.radians(P['arrow_ring']['lead_angle_degrees'])); skin = P['arrow_ring']['skin_thickness_mm']
    root_phi = 90. - (r['bond_half_angle_degrees'] - r['skirt_root_inside_bond_degrees'])
    skirt, lead = clip_skirt(*r['front_band_y_mm'], +1, r['gap_degrees'], r['root_wall_mm'], root_phi, k, skin)
    bands = clip_ring(*r['rear_band_y_mm'], r['gap_degrees'], r['root_wall_mm']) + clip_ring(*r['front_band_y_mm'], r['gap_degrees'], r['root_wall_mm'])
    return (bands + skirt).mirror((0, 0, 1)), lead


def keel_bore(y0=-40, y1=60): return cyl(G['keel_bore_radius_mm'], y0, y1).rotate((-90, 0, 0))
def layer_count(): return int(round((G['y_rear_mm'] - G['y_front_mm']) / G['layer_mm']))


@lru_cache(maxsize=1)
def guard_hull():
    """Everything rigid: the hull as runs of identical print layers, with the keel bore cut through."""
    step = G['layer_mm']; n = layer_count(); assert abs(n * step - (G['y_rear_mm'] - G['y_front_mm'])) < 1e-9, 'Guard length must be whole layers'
    keys = [layer_key(k) for k in range(n)]; pieces = []; start = 0
    for k in range(1, n + 1):
        if k == n or keys[k] != keys[start]:
            pieces.append(xz(layer_section(keys[start]), G['y_rear_mm'] - k * step, G['y_rear_mm'] - start * step)); start = k
    return union(pieces) - keel_bore()


@lru_cache(maxsize=1)
def guard():
    """Rigid hull plus the two spring rings, whose bore is never cut by a rigid-clearance cylinder."""
    return base.clean(guard_hull() + guard_rings()[0], 'Finger_Guard')


# ---------------------------------------------------------------------------
# Key holder: the R16 build with its own tighter rings and extra arrow windows
# ---------------------------------------------------------------------------
def key_windows():
    """Arrow windows, every point toward the nose (print-up): two through the socket-board level under each upper
    switch front, and one through each shoulder."""
    w = K20['front_window']; bottom = base.slab_bottom(); cuts = []
    arrow = lambda x0, x1, flat, rect_: [(x0, flat), (x1, flat), (x1, flat - rect_), ((x0 + x1) / 2, flat - rect_ - (x1 - x0) / 2), (x0, flat - rect_)]
    for (x, y), rot in zip(base.key_positions(), base.key_rotations()):
        if y == 0 and not w['lower_row']: continue       # no cuts through the lower row's board level
        flat, rect_ = (w['turned_flat_y_mm'], w['turned_rect_mm']) if rot % 360 == 180 else (w['flat_y_mm'], w['upper_row_rect_mm'])
        for sign in (1, -1):
            x0, x1 = sorted([sign * w['x_mm'][0], sign * w['x_mm'][1]])
            cuts.append(base.prism_xy([(x + px, y + py) for px, py in arrow(x0, x1, flat, rect_)], bottom - 1, base.PCB_Z + .01))
    sw = K20['shoulder_window']
    for sign in (1, -1):
        x0, x1 = sorted([sign * sw['x_mm'][0], sign * sw['x_mm'][1]]); cuts.append(base.prism_xy(arrow(x0, x1, sw['flat_y_mm'], sw['rect_mm']), bottom - 1, base.plate_top() + 1))
    return union(cuts)


@lru_cache(maxsize=4)
def key_carrier_build(bore_mm, windows):
    """holder16.carrier_raw and carrier, line for line, with the ring bore and the extra windows as arguments.
    key_carrier_build(7.9, False) must reproduce the accepted R16 solid; test_holder20.py checks that."""
    s = P['slab']; c = P['carrier_rings']; a = P['arrow_ring']; bottom = base.slab_bottom(); top = base.plate_top(); inner = bore_mm / 2
    slab = mf.Manifold.extrude(base.slab_outline(), top - bottom).translate((0, 0, bottom)); x_span = s['lower_half_x_mm'] + 2
    slab -= base.edge_round_x(-x_span, x_span, s['front_y_mm'], +1, top, -1, s['nose_top_radius_mm'])
    under = bottom + P['bay']['backplate_thickness_mm'] - P['bay']['backplate_thin_mm']
    slab -= base.edge_round_x(-x_span, x_span, s['front_y_mm'], +1, under, +1, s['nose_finger_radius_mm'])
    for sign in (1, -1): slab -= base.edge_round_y(s['front_y_mm'] - 1, s['lower_rear_y_mm'] + 1, sign * s['lower_half_x_mm'], -sign, top, -1, s['nose_top_radius_mm'])
    for (x, y), rot in zip(base.key_positions(), base.key_rotations()): slab -= base.bay_cuts(x, y, rot)
    slab -= base.thinning(base.key_positions(), base.key_rotations())
    if windows: slab -= key_windows()
    gap, root = ROD['clip_gap_degrees'], ROD['clip_root_wall']; k = 1 / math.tan(math.radians(a['lead_angle_degrees'])); m0, m1 = c['mid_band_y_mm']; r0, r1 = c['rear_band_y_mm']
    skirt, lead = clip_skirt(m0, m1, +1, gap, root, a['root_phi_degrees_above_equator'], k, a['skin_thickness_mm'], inner)
    saddle = base.saddle_xz(a['saddle_top_half_width_mm'], bottom + 1.0, a['saddle_bottom_z_mm'], *c['saddle_y_mm'])
    shape = (union([slab, saddle]) - base.corridor()) + clip_ring(m0, m1, gap, root, inner) + skirt + clip_ring(r0, r1, gap, root, inner)
    shape -= base.gap_cut(m0, m1 + lead); shape -= base.gap_cut(r0, r1); shape -= base.wire_bus(-80, 100)
    regions = dict(spaces16.regions('Key_Carrier')); regions['unloaded_clip_bore'] = cyl(inner, -40, 100).rotate((-90, 0, 0))
    return base.clean(spaces16.carve(shape, regions, f'carrier20:{bore_mm}:{windows}'), 'Key_Carrier')


def key_carrier(): return key_carrier_build(K20['ring_bore_mm'], True)


# ---------------------------------------------------------------------------
# Battery holder: the R19 build with its closed end 2.6 mm nearer the cell
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def battery_module():
    """Runs the unmodified R19 builder with two of its parameters swapped for the call, then puts them back."""
    saved = (h19.B19['plate_y_mm'], h19.CAGE['far_band_y_mm'])
    try:
        h19.B19['plate_y_mm'] = list(B20['plate_y_mm']); h19.CAGE['far_band_y_mm'] = list(B20['far_band_y_mm'])
        return h19.battery_module.__wrapped__()
    finally:
        h19.B19['plate_y_mm'], h19.CAGE['far_band_y_mm'] = saved


# ---------------------------------------------------------------------------
# XIAO holder: the R19 solid plus a 3.6 mm far ring, side walls and far-corner cheeks
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def sensor_holder():
    y0, y1 = X20['far_ring_band_y_mm']; assert y1 == S['far_band_y_mm'][1], 'The far ring must stay on the bed plane'
    ring = base.ring((y0 + y1) / 2, None, y1 - y0, ROD['sensor_clip_root_wall'])
    w = X20['wall']; c = X20['far_cheek']; extra = []
    for sign in (1, -1):
        xr = lambda a, b: (min(sign * a, sign * b), max(sign * a, sign * b))
        extra.append(box(*xr(*w['x_mm']), *w['y_mm'], w['bottom_z_mm'], w['top_z_mm']))
        extra.append(box(*xr(*c['x_mm']), *c['y_mm'], *c['z_mm']))
    return base.clean((h19.sensor_holder() + ring + union(extra)) - base.gap_cut(y0, y1), 'XIAO_Rod_Holder')


# ---------------------------------------------------------------------------
# References and working spaces
# ---------------------------------------------------------------------------
def read(path):
    m = trimesh.load_mesh(path); return mf.Manifold(mf.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32)))


@lru_cache(maxsize=1)
def carrier_r16():
    """The accepted R16 key holder, read from its bound export, for comparison."""
    record = json.loads((R16 / 'exports/manifest.json').read_text())['parts']['Key_Carrier']; path = R16 / 'exports/Key_Carrier-assembly.stl'
    assert sha(R16 / 'exports/Key_Carrier-SOURCE-REQUIRES-PREPARATION.stl') == record['stl_sha256'], 'R16 key holder export changed'
    solid = read(path); assert abs(solid.volume() - record['volume_mm3']) < .5, (solid.volume(), record['volume_mm3'])
    return solid


def socket_tabs(i):
    """The two metal terminals of key i's sourced socket (assembly frame), as boxes measured from the mesh sections."""
    (x, y), rot = base.key_positions()[i], base.key_rotations()[i]; z0, z1 = base.PCB_Z - 3.0, base.PCB_Z - 1.6
    local = [(-4.07, -2.27, 5.09, 6.77), (7.28, 9.08, 2.88, 4.56)]
    out = []
    for x0, x1, y0, y1 in local:
        if rot % 360 == 180: x0, x1, y0, y1 = -x1, -x0, -y1, -y0
        out.append((x + x0, x + x1, y + y0, y + y1, z0, z1))
    return out


def contact_envelopes():
    """Stated, unmeasured allowance around every terminal for solder and the wire leaving it."""
    a = G['assumed_allowances']; out = {}
    for i in range(len(base.key_positions())):
        (kx, _), tabs = base.key_positions()[i], socket_tabs(i)
        centre = sum(t[0] + t[1] for t in tabs) / 4
        for j, (x0, x1, y0, y1, z0, z1) in enumerate(tabs):
            end = a['solder_and_wire_beyond_tab_end_mm']; outward = 1 if (x0 + x1) / 2 > centre else -1
            x0, x1 = (x0, x1 + end) if outward > 0 else (x0 - end, x1)
            out[f'key_{i}_terminal_{j}'] = box(x0, x1, y0 - a['solder_and_wire_beside_tab_mm'], y1 + a['solder_and_wire_beside_tab_mm'], z0 - a['solder_and_wire_below_tab_mm'], z1)
    return out


def bought_parts():
    hw = base.seated_hardware(); so = base.seated_socket(); mx = spaces16.maximum_socket(); out = {}; a = G['assumed_allowances']
    for i, ((x, y), rot) in enumerate(zip(base.key_positions(), base.key_rotations())):
        out[f'key_{i}_switch'] = hw['switch'].rotate((0, 0, rot)).translate((x, y, base.PCB_Z))
        out[f'key_{i}_socket'] = so.rotate((0, 0, rot)).translate((x, y, base.PCB_Z))
        out[f'key_{i}_maximum_socket'] = mx.rotate((0, 0, rot)).translate((x, y, base.PCB_Z))
        b = out[f'key_{i}_maximum_socket'].bounding_box()
        edge = P['slab']['lower_half_x_mm'] + .3      # tape is pressed onto the backplate, so it cannot reach past the slab edge
        out[f'key_{i}_tape_and_wire_under_socket'] = box(max(b[0] - 1., -edge), min(b[3] + 1., edge), b[1] - .5, b[4] + .5, b[2] - a['tape_and_wire_below_socket_body_mm'], b[2] + .01)
    out['wire_bus'] = base.wire_bus(-80, 100)
    return out


def guard_spaces():
    """Spaces the guard itself must leave empty."""
    r = G['ring']; half = math.radians(r['wire_crossing_clear_half_angle_degrees']); L = 6.2; y0, y1 = G['y_front_mm'], G['y_rear_mm']; clear = frame()['bay_clear']; t = G['face_thickness_mm']
    _, lead = guard_rings(); free0 = r['front_band_y_mm'][1] + lead + .1; free1 = r['rear_band_y_mm'][0] - .1
    return {'unloaded_clip_bore': cyl(BORE, -40, 100).rotate((-90, 0, 0)),
            'rigid_rod_corridor_between_rings': cyl(CORRIDOR, free0, free1).rotate((-90, 0, 0)),
            'wire_crossing_sector_over_rod': xz(poly([(0, 0), (L * math.sin(half), L * math.cos(half)), (0, L), (-L * math.sin(half), L * math.cos(half))]), y0 - 1, y1 + 1),
            # The open bays themselves, 0.3 mm inside every edge and both wing surfaces.
            'six_windows_between_the_rails': xz(both(mf.CrossSection.batch_boolean([poly([wing_point(a + .3, .3), wing_point(b - .3, .3), wing_point(b - .3, t - .3), wing_point(a + .3, t - .3)]) for a, b in frame()['bays']], mf.OpType.Add)), y0 + G['front_rim_mm'] + clear / 2 + .3, y1 - G['rear_rim_mm'] - G['rear_gusset_mm'] - .3)}


def part_regions(name):
    """Working spaces of each R20 part in its assembly frame: the predecessor's list with the changed ones restated."""
    if name == 'Finger_Guard': return guard_spaces()
    if name == 'Key_Carrier':
        out = dict(spaces16.regions(name)); out['unloaded_clip_bore'] = cyl(K20['ring_bore_mm'] / 2, -40, 100).rotate((-90, 0, 0)); return out
    if name == 'Battery_Holder':
        out = {k: v for k, v in h19.regions(name).items() if k != 'clip_gap_far'}; out['clip_gap_far'] = base.gap_cut(*B20['far_band_y_mm']); return out
    assert name == 'XIAO_Rod_Holder', name
    out = {k: v for k, v in h19.regions(name).items() if not k.startswith('wire_exit_up_out') and k != 'board_travel'}; y0, y1 = X20['far_ring_band_y_mm']; w = X20['wall']; out['clip_gap_far'] = base.gap_cut(y0, y1)
    # Wire exits restated for the side walls: straight up from each pad inside the wall, then outward above it.
    half = S['board_outline_mm']['width'] / 2; top = h19.BOARD_TOP + h19.WIRE['exit_height_above_board_mm']; hw = h19.WIRE['corridor_width_mm'] / 2
    side = X20['board_travel_check_mm']['sideways']; t_ = h19.board_travel()
    out['board_travel_between_cheeks'] = union([h19.board_outline(dx, dy) for dx, dy in [(0., -(t_['near'] - .1)), (0., 0.), (0., t_['far'] - .1), (side, 0.), (-side, 0.), (side, t_['far'] - .1), (-side, t_['far'] - .1)]])
    for index, (sign, y, _) in enumerate(h19.pad_rows()):
        a, b = sorted([sign * (half - 1.8), sign * w['x_mm'][0]]); out[f'wire_up_from_pad_{index:02d}'] = box(a, b, y - hw, y + hw, h19.BOARD_TOP, top)
        a, b = sorted([sign * w['x_mm'][0], sign * h19.WIRE['outboard_x_mm'][1]]); out[f'wire_out_over_wall_{index:02d}'] = box(a, b, y - hw, y + hw, w['top_z_mm'] + .05, top)
    return out


def part_shapes(): return {'Key_Carrier': key_carrier(), 'Battery_Holder': battery_module(), 'XIAO_Rod_Holder': sensor_holder(), 'Finger_Guard': guard()}


def export():
    out = HERE / 'exports'; out.mkdir(exist_ok=True); records = {}; shapes = part_shapes(); r19 = json.loads((R19 / 'exports/manifest.json').read_text()); r16 = json.loads((R16 / 'exports/manifest.json').read_text())
    for name in PARTS:
        shape = shapes[name].simplify(.0001); m, o, tf = h18.to_print(shape, name); assert m.is_watertight and len(shape.decompose()) == 1, name
        m.export(out / (name + '-assembly.stl'))
        normal = mf.Manifold(mf.Mesh(np.asarray(np.round(o.vertices, 6), np.float32), np.asarray(o.faces, np.uint32))).simplify(.000001); assert normal.status() == mf.Error.NoError, name
        mesh(normal).export(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); final = trimesh.load_mesh(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); back = read(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')).transform(np.linalg.inv(tf)[:3, :])
        drift = float((back - shapes[name]).volume() + (shapes[name] - back).volume()); assert final.is_watertight and len(back.decompose()) == 1 and drift < .02, (name, 'exported mesh differs from the source solid', drift)
        records[name] = {'bounds_mm': m.bounds.tolist(), 'volume_mm3': m.volume, 'solid_PETG_g': m.volume / 1000 * base.r15.P['print']['density_g_cm3'], 'print_height_mm': float(final.bounds[1][2]), 'body_count': 1, 'watertight': True,
                         'stl_sha256': sha(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')), 'assembly_stl_sha256': sha(out / (name + '-assembly.stl')), 'print_to_assembly': np.linalg.inv(tf).tolist()}
    sources = [HERE / 'holder20.py', HERE / 'parameters.json', R19 / 'holder19.py', R19 / 'parameters.json', h18.HERE / 'holder18.py', h18.HERE / 'parameters.json', h19.R17 / 'holder17.py', h19.R17 / 'parameters.json', R16 / 'holder16.py', R16 / 'spaces16.py', R16 / 'parameters.json']
    manifest = {'revision': LOCAL['revision'], 'source_sha256': {os.path.relpath(p, HERE): sha(p) for p in sources}, 'parts': records, 'plate_parts': PARTS,
                'assembly_frame': 'Each part is in its own frame, rod axis along Y. Finger_Guard shares the Key_Carrier frame.',
                'unchanged_from_r19_stl_sha256': {n: r19['parts'][n]['stl_sha256'] for n in UNCHANGED_R19},
                'superseded_stl_sha256': {'Key_Carrier (R16)': r16['parts']['Key_Carrier']['stl_sha256'], 'Battery_Holder (R19)': r19['parts']['Battery_Holder']['stl_sha256'], 'XIAO_Rod_Holder (R19)': r19['parts']['XIAO_Rod_Holder']['stl_sha256']}, 'physical_fit_verified': False, 'physical_strength_verified': False, 'physical_comfort_verified': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print({n: (round(v['volume_mm3'], 1), round(v['solid_PETG_g'], 3), round(v['print_height_mm'], 2)) for n, v in records.items()}, 'was', {'Key_Carrier': round(r16['parts']['Key_Carrier']['volume_mm3'], 1), 'Battery_Holder': round(r19['parts']['Battery_Holder']['volume_mm3'], 1), 'XIAO_Rod_Holder': round(r19['parts']['XIAO_Rod_Holder']['volume_mm3'], 1)}, flush=True)


if __name__ == '__main__':
    export()
