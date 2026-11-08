#!/usr/bin/env python3
"""R16 repair: key carrier, battery cage/gate and XIAO holder after the R15 print failures.

Composes the frozen bought interfaces (Choc V1 switch/socket meshes, R7 spring-clip profile,
rod corridor, wire bus, board references) from the preserved R15 chain. All structure is
authored here. Print transforms are part of this revision. No removable CAD print helpers:
every clip ring that is not on the bed grows from a 45-degree arc lead-in skirt.
"""
from pathlib import Path
from functools import lru_cache
import json
import math
import os
import sys
import numpy as np
import trimesh
import manifold3d as mf

if __name__ == '__main__':
    sys.modules.setdefault('holder16', sys.modules[__name__])

HERE = Path(__file__).resolve().parent
R15 = HERE.parent / 'carbon-rod-holders-r15-tight-pyramid'


def _load_r15():
    # R15's modules import each other by their plain names (cad, deliverables,
    # working_spaces). Nothing in this directory uses those names.
    sys.path.insert(0, str(R15))
    try:
        import cad as r15_cad  # noqa: E402
        import working_spaces as r15_spaces  # noqa: E402
    finally:
        sys.path.remove(str(R15))
    return r15_cad, r15_spaces


r15, r15_spaces = _load_r15()
LOCAL = json.loads((HERE / 'parameters.json').read_text())
P = {**r15.P, **LOCAL, 'keys': {**r15.P['keys'], **LOCAL['key_layout']},
     'assembly': {**r15.P['assembly'], **LOCAL['assembly']}}
for name in ['box', 'rr', 'rib', 'cyl', 'tube_y', 'union', 'mesh', 'sha',
             'seated_hardware', 'ring', 'clip_gap', 'wire_bus', 'external_wire_route']:
    globals()[name] = getattr(r15, name)
SENSOR = r15.base.r7.r2.P['sensor']
ROD = P['rod']
CORRIDOR = (ROD['diameter'] + ROD['diametral_clearance']) / 2  # 4.2 mm rigid bore
PCB_Z = P['keys']['pcb_z']
PARTS = ['Key_Carrier', 'Battery_Holder', 'Battery_End_Gate', 'XIAO_Rod_Holder']


def corridor(y0=-80, y1=100):
    return cyl(CORRIDOR, y0, y1).rotate((-90, 0, 0))


def ccw(points):
    pts = [tuple(map(float, q)) for q in points]
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if area > 0 else pts[::-1]


def prism_xy(points, z0, z1):
    return mf.Manifold.extrude(mf.CrossSection([ccw(points)]), z1 - z0).translate((0, 0, z0))


def prism_xz(points, y0, y1):
    """Extrude a counter-clockwise XZ outline along Y."""
    solid = mf.Manifold.extrude(mf.CrossSection([ccw(points)]), y1 - y0)
    # extrude axes (u,v,w) -> (x,z,y): x=u, y=w+y0, z=v
    return solid.transform(np.array([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0]], dtype=float))


def bar_xy(p0, p1, width, z0, z1):
    """A straight bar between two XY points, square ends."""
    h = width / 2
    return mf.Manifold.batch_hull([box(p0[0] - h, p0[0] + h, p0[1] - h, p0[1] + h, z0, z1),
                                   box(p1[0] - h, p1[0] + h, p1[1] - h, p1[1] + h, z0, z1)])


def bar_yz(x0, x1, p0, p1, width):
    """A straight bar in the YZ plane between (y,z) points, spanning X x0..x1."""
    h = width / 2
    return mf.Manifold.batch_hull([box(x0, x1, p0[0] - h, p0[0] + h, p0[1] - h, p0[1] + h),
                                   box(x0, x1, p1[0] - h, p1[0] + h, p1[1] - h, p1[1] + h)])


def bar_xz(y0, y1, p0, p1, width):
    """A straight bar in the XZ plane between (x,z) points, spanning Y y0..y1."""
    h = width / 2
    return mf.Manifold.batch_hull([box(p0[0] - h, p0[0] + h, y0, y1, p0[1] - h, p0[1] + h),
                                   box(p1[0] - h, p1[0] + h, y0, y1, p1[1] - h, p1[1] + h)])


def edge_round_x(x0, x1, y_face, y_in, z_face, z_in, r):
    """Cutter that rounds the edge along X where the face y=y_face meets the face z=z_face.

    y_in/z_in are +1/-1 toward the material. The cutter removes the corner region
    outside a cylinder of radius r tangent to both faces.
    """
    cy, cz = y_face + y_in * r, z_face + z_in * r
    ys = sorted([y_face - y_in * 1.0, cy]); zs = sorted([z_face - z_in * 1.0, cz])
    block = box(x0, x1, ys[0], ys[1], zs[0], zs[1])
    cylinder = mf.Manifold.cylinder(x1 - x0 + 2, r, r, 96).rotate((0, 90, 0)).translate((x0 - 1, cy, cz))
    return block - cylinder


def edge_round_y(y0, y1, x_face, x_in, z_face, z_in, r):
    cx, cz = x_face + x_in * r, z_face + z_in * r
    xs = sorted([x_face - x_in * 1.0, cx]); zs = sorted([z_face - z_in * 1.0, cz])
    block = box(xs[0], xs[1], y0, y1, zs[0], zs[1])
    cylinder = mf.Manifold.cylinder(y1 - y0 + 2, r, r, 96).rotate((-90, 0, 0)).translate((cx, y0 - 1, cz))
    return block - cylinder


def teardrop(cx, cy, r, z0, z1):
    """A round hole whose -Y side ends in a 45-degree peak. These hole axes lie in the layer
    plane (Y is the layer axis), so the peak keeps the hole roof self-supporting in print."""
    t = r * math.sqrt(.5)
    return cyl(r, z0, z1, cx, cy) + prism_xy([(cx - t, cy - t), (cx + t, cy - t), (cx, cy - r * math.sqrt(2))], z0, z1)


# ---------------------------------------------------------------------------
# Arrow rings: R7 clip profile plus a self-supporting arc lead-in skirt.
# ---------------------------------------------------------------------------
def ring_profile(width, root_wall):
    p = ROD; inner = p['clip_diameter'] / 2
    gap = math.radians(p['clip_gap_degrees'])
    tip = p['clip_tip_wall']

    def thickness(angle):
        return tip + (root_wall - tip) * ((math.sin(angle) + 1) / 2) ** 2
    return inner, gap, thickness


def arc_skirt(band_y0, band_y1, lead_sign, width, root_wall, root_phi_deg, k, skin):
    """Lead-in skirt below (toward the bed) the free arms of a ring band.

    Each arm's leading face follows the arc: a point at arc distance s from the tip starts
    k*s before the band, so every print layer of the arm overhangs the previous one by at most
    the layer height (45 degrees for k=1). The radial thickness tapers from the local wall to
    `skin` at the leading edge, keeping the bore surface continuous. Built as one warped
    extrusion per arm, so there are no internal faces or films.
    """
    inner, gap, thickness = ring_profile(width, root_wall)
    edge = band_y1 if lead_sign > 0 else band_y0
    tip_angle = -math.pi / 2 + gap / 2          # right arm tip, measured from +X
    root_angle = math.radians(root_phi_deg)     # right arm root above the equator
    n = 96
    angles = np.linspace(tip_angle, root_angle, n + 1)
    mids = np.array([inner + thickness(a) / 2 for a in angles])
    s = np.concatenate([[0.], np.cumsum(np.diff(angles) * (mids[1:] + mids[:-1]) / 2)])
    lead = np.maximum(k * s, .02); lead_max = float(lead[-1])
    arms = []
    for sign in (1, -1):
        outer = [(sign * (inner + thickness(a)) * math.cos(a), (inner + thickness(a)) * math.sin(a)) for a in angles]
        inside = [(sign * inner * math.cos(a), inner * math.sin(a)) for a in angles[::-1]]
        prism = mf.Manifold.extrude(mf.CrossSection([ccw(outer + inside)]), lead_max)

        def warp(v, sign=sign):
            u, w, h = v[:, 0], v[:, 1], v[:, 2]
            a = np.arctan2(w, sign * u); r = np.hypot(u, w)
            t = np.array([thickness(x) for x in a]); frac = np.clip(h / lead_max, 0, 1)
            L = np.interp(a, angles, lead)
            new_r = inner + (r - inner) * (1 - frac * (1 - skin / t))
            return np.column_stack([sign * new_r * np.cos(a), new_r * np.sin(a), frac * L])
        arm = prism.warp_batch(warp)
        # extrude frame (u, w, h) -> assembly (x, y, z) = (u, edge + lead_sign*h, w)
        arms.append(arm.transform(np.array([[1, 0, 0, 0], [0, 0, lead_sign, edge], [0, 1, 0, 0]], dtype=float)))
    return union(arms), float(s[-1])


def arrow_ring(band_y0, band_y1, lead_sign, width=None, root_wall=None):
    """R7 clip band plus the arc lead-in skirt toward `lead_sign`. Returns (solid, skirt_length, y_range)."""
    width = width or ROD['ring_width']; root_wall = root_wall or ROD['clip_root_wall']
    a = P['arrow_ring']; k = 1 / math.tan(math.radians(a['lead_angle_degrees']))
    band = ring((band_y0 + band_y1) / 2, None, width, root_wall)
    skirt, s_root = arc_skirt(band_y0, band_y1, lead_sign, width, root_wall, a['root_phi_degrees_above_equator'], k, a['skin_thickness_mm'])
    L = k * s_root
    y_range = (band_y0, band_y1 + L) if lead_sign > 0 else (band_y0 - L, band_y1)
    return band + skirt, L, y_range


def gap_cut(y0, y1, width=None):
    """The straight 1 mm slot of the R7 clip gap, through the band and its skirt."""
    return box(-.5, .5, y0 - .1, y1 + .1, -9, 0)


def saddle_xz(top_half, top_z, bottom_z, y0, y1, max_half=None):
    """Fixed crown saddle: 45-degree flanks from the top half-width, then vertical sides to a flat bottom.

    The flat bottom covers the lead-in skirt's root layer; the sides stay narrow so sockets inserted
    from below beside the rod never meet it.
    """
    max_half = max_half or P['arrow_ring']['saddle_max_half_width_mm']
    knee = max(bottom_z, top_z - (max_half - top_half))
    pts = [(-top_half, top_z), (top_half, top_z), (max_half, knee), (max_half, bottom_z), (-max_half, bottom_z), (-max_half, knee)]
    return prism_xz(pts, y0, y1)


def clean(shape, label):
    """Keep the one real body; reject real detached chips, drop only numerical films."""
    bodies = shape.decompose(); keep = [b for b in bodies if b.volume() > .01]
    films = [b.volume() for b in bodies if b.volume() <= .01]
    assert len(keep) == 1, (label, [(round(b.volume(), 3), np.round(b.bounding_box(), 2).tolist()) for b in keep])
    assert sum(abs(v) for v in films) < .05, (label, films)
    return keep[0]


# ---------------------------------------------------------------------------
# Key carrier
# ---------------------------------------------------------------------------
def key_rotations():
    # The sourced socket hangs toward +X of its switch. Turn the upper-left key half a turn so
    # its socket sits outboard, clear of the rear ring saddle and its own straight insertion.
    return [0, 0, 0, 180, 0]


def key_positions():
    k = P['keys']
    return [(-k['pitch'], 0), (0, 0), (k['pitch'], 0), (-k['upper_half_spacing'], k['row_spacing']), (k['upper_half_spacing'], k['row_spacing'])]


def plate_top():
    b = P['bay']; return PCB_Z + b['plate_bottom_mm'] + b['plate_thickness_mm']


def slab_bottom():
    return PCB_Z - P['bay']['backplate_thickness_mm']


def slab_outline():
    s = P['slab']; r = s['plan_corner_radius_mm']
    lower = mf.CrossSection.square((2 * s['lower_half_x_mm'], s['lower_rear_y_mm'] - s['front_y_mm'])).translate((-s['lower_half_x_mm'], s['front_y_mm']))
    upper = mf.CrossSection.square((2 * s['upper_half_x_mm'], s['rear_y_mm'] - s['upper_front_y_mm'])).translate((-s['upper_half_x_mm'], s['upper_front_y_mm']))
    reach = s['lower_half_x_mm'] - s['upper_half_x_mm']
    rise = reach * math.tan(math.radians(s['shoulder_angle_degrees']))
    shoulders = []
    for sign in (1, -1):
        pts = [(sign * s['upper_half_x_mm'], s['lower_rear_y_mm'] - .01), (sign * s['lower_half_x_mm'], s['lower_rear_y_mm'] - .01),
               (sign * s['upper_half_x_mm'], s['lower_rear_y_mm'] + rise)]
        if sign < 0: pts = pts[::-1]
        shoulders.append(mf.CrossSection([pts]))
    outline = mf.CrossSection.batch_boolean([lower, upper] + shoulders, mf.OpType.Add)
    # Round the convex plan corners only; concave shoulder corners stay as modelled.
    return outline.offset(-r, mf.JoinType.Round).offset(r, mf.JoinType.Round)


def seated_socket():
    """The sourced hot-swap socket seated against the backplate underside like a 1.6 mm PCB."""
    return seated_hardware()['socket'].translate((0, 0, P['bay']['socket_body_top_shift_mm']))


def socket_pad(x, y, rot=0):
    """Backplate zone kept at full 1.6 mm thickness: the socket body, legs and boss holes."""
    return box(-4.8, 9.9, .4, 9.2, slab_bottom() - 2, slab_bottom() + 1).rotate((0, 0, rot)).translate((x, y, 0))


def thinning(positions, rotations):
    """Thin the backplate to 1.2 mm everywhere except under every key's socket pad."""
    b = P['bay']; bottom = slab_bottom(); depth = b['backplate_thickness_mm'] - b['backplate_thin_mm']
    zone = union([box(x - 9.5, x + 9.5, y - 9.5, y + 9.5, bottom - 1, bottom + depth) for x, y in positions])
    return zone - union([socket_pad(x, y, rot) for (x, y), rot in zip(positions, rotations)])


def bay_cuts(x, y, rot=0):
    """Everything removed from the slab for one key: opening, clip relief, backplate holes."""
    b = P['bay']; z0 = PCB_Z; top = plate_top(); bottom = slab_bottom()
    local = [rr(b['plate_opening_mm'], b['plate_opening_mm'], .2, z0 + b['plate_bottom_mm'] - .01, top + 1),
             rr(2 * b['clip_relief_half_x_mm'], 2 * b['clip_relief_half_y_mm'], .5, z0, z0 + b['plate_bottom_mm'] + .01)]
    cuts = [union(local).rotate((0, 0, rot))]
    # Backplate holes follow the turned key, but every teardrop peak points to global -Y (print up).
    for hx, hy, r in backplate_hole_centres(rot):
        cuts.append(teardrop(hx, hy, r, bottom - 1, z0 + 1))
    # One arrow-shaped lightening window beside the socket. It follows the socket side when the
    # key is turned, but its point always faces -Y so the window roof prints as a 45-degree peak.
    cuts.append(window_cut(rot, bottom - 1, z0 + 1))
    return union(cuts).translate((x, y, 0))


def window_outline(rot=0):
    """Plan outline of one lightening window in the key frame (before the key's translation)."""
    b = P['bay']; flip = -1 if rot % 360 == 180 else 1
    wx0, wx1 = b['lightening_window_mm']['x']; wy0, wy1 = b['lightening_window_mm']['y']; half = (wx1 - wx0) / 2
    if flip < 0:
        wx0, wx1 = -wx1, -wx0; wy0, wy1 = -wy1, -wy0
        # Mirrored, the flat edge faces the side-post hole's teardrop peak: set it back so the
        # ligament matches the unturned keys' 1.2 mm (verify16.py measures every key).
        wy1 -= b['lightening_window_turned_key_setback_mm']
    return [(wx0, wy1), (wx1, wy1), (wx1, wy0 + half), (wx0 + half, wy0), (wx0, wy0 + half)]


def window_cut(rot, z0, z1):
    return prism_xy(window_outline(rot), z0, z1)


def backplate_hole_centres(rot=0):
    """(x, y, radius) of every backplate hole in the key frame, as cut by bay_cuts."""
    b = P['bay']; flip = -1 if rot % 360 == 180 else 1
    holes = [(0., 0., b['centre_post_hole_mm'] / 2)] + [(sign * b['side_post_x_mm'], 0., b['side_post_hole_mm'] / 2) for sign in (1, -1)]
    holes += [(bx, by, b['socket_boss_hole_mm'] / 2) for bx, by in b['socket_boss_centres_mm']]
    return [(flip * hx, flip * hy, r) for hx, hy, r in holes]


@lru_cache(maxsize=1)
def carrier_rings():
    c = P['carrier_rings']; a = P['arrow_ring']
    mid, L, mid_range = arrow_ring(*c['mid_band_y_mm'], +1, c['ring_width_mm'])
    rear = ring(sum(c['rear_band_y_mm']) / 2, None, c['ring_width_mm'])
    return mid, rear, L, mid_range


@lru_cache(maxsize=1)
def carrier_raw():
    """The carrier before the final working-space carve (for diagnostics)."""
    s = P['slab']; c = P['carrier_rings']; a = P['arrow_ring']
    bottom = slab_bottom(); top = plate_top()
    slab = mf.Manifold.extrude(slab_outline(), top - bottom).translate((0, 0, bottom))
    # Smooth finger edge under the three lower keys: a small round at the cap side and a
    # large round where the index finger meets the underside. Outer ends get small rounds.
    x_span = s['lower_half_x_mm'] + 2
    slab -= edge_round_x(-x_span, x_span, s['front_y_mm'], +1, top, -1, s['nose_top_radius_mm'])
    under = bottom + P['bay']['backplate_thickness_mm'] - P['bay']['backplate_thin_mm']
    slab -= edge_round_x(-x_span, x_span, s['front_y_mm'], +1, under, +1, s['nose_finger_radius_mm'])
    for sign in (1, -1):
        slab -= edge_round_y(s['front_y_mm'] - 1, s['lower_rear_y_mm'] + 1, sign * s['lower_half_x_mm'], -sign, top, -1, s['nose_top_radius_mm'])
    for (x, y), rot in zip(key_positions(), key_rotations()):
        slab -= bay_cuts(x, y, rot)
    slab -= thinning(key_positions(), key_rotations())
    mid, rear, L, mid_range = carrier_rings()
    y0, y1 = c['saddle_y_mm']
    saddle = saddle_xz(a['saddle_top_half_width_mm'], bottom + 1.0, a['saddle_bottom_z_mm'], y0, y1)
    shape = union([slab, saddle]) - corridor()
    shape = shape + mid + rear
    shape -= gap_cut(mid_range[0], mid_range[1])
    shape -= gap_cut(*c['rear_band_y_mm'])
    shape -= wire_bus(-80, 100)
    return shape


@lru_cache(maxsize=1)
def carrier():
    import spaces16
    return clean(spaces16.carve(carrier_raw(), spaces16.regions('Key_Carrier'), 'carrier'), 'Key_Carrier')


# ---------------------------------------------------------------------------
# Battery cage and end gate
# ---------------------------------------------------------------------------
def cage_levels():
    c = P['cage']; zf = c['floor_z_mm']; r = c['reserve_mm']
    return {'floor_top': zf, 'floor_bottom': zf - c['floor_bar_thickness_mm'], 'roof_bottom': zf + r['thickness'],
            'roof_top': zf + r['thickness'] + c['bar_mm'], 'half_w': r['width'] / 2, 'half_l': r['length'] / 2}


def cell_shape(reserve=False):
    """Manufacturer maximum protected pack (default) or the printed reserve envelope."""
    c = P['cage']; lv = cage_levels()
    if reserve:
        r = c['reserve_mm']; return box(-lv['half_w'], lv['half_w'], -lv['half_l'], lv['half_l'], lv['floor_top'], lv['roof_bottom'])
    m = P['cell']['manufacturer_max_mm']
    return box(-m['width'] / 2, m['width'] / 2, -m['length'] / 2, m['length'] / 2, lv['floor_top'], lv['floor_top'] + m['thickness'])


def chevrons(z0, z1, xi, apex_ys, bar):
    pieces = []
    for ya in apex_ys:
        for sign in (1, -1):
            pieces.append(bar_xy((sign * xi, ya + xi), (0, ya), bar, z0, z1))
    return pieces


@lru_cache(maxsize=1)
def battery_module():
    c = P['cage']; lv = cage_levels(); a = P['arrow_ring']
    xi, xo = c['side_rail_x_mm']; bar = c['bar_mm']
    fb, ft, rb, rt = lv['floor_bottom'], lv['floor_top'], lv['roof_bottom'], lv['roof_top']
    near0, near1 = c['near_band_y_mm']; far0, far1 = c['far_band_y_mm']
    pieces = []
    # Central floor spine: saddle for both rings and the apex landing of every floor chevron.
    sp, sd = c['spine_half_x_mm'], c['saddle_half_x_mm']
    pieces.append(box(-sp, sp, near0, far1, fb, ft))
    pieces.append(box(-sd, sd, far0 - .5, far1, fb, ft))
    # Floor and roof chevron lattices, apexes pointing toward the gate/tip end.
    pitch = c['chevron_pitch_mm']
    floor_apexes = [y for y in np.arange(-13.5 - xi + pitch, 14.5, pitch)]
    pieces += chevrons(fb, ft, xi, floor_apexes, bar)
    roof_apexes = [y for y in np.arange(-13.0, 14.5 - xi, pitch)]
    pieces += chevrons(rb, rt, xi, roof_apexes, bar)
    # Side rails: bottom and top chords with 45-degree zigzag struts between them.
    guide_y0, guide_y1 = c['guide_y_mm']
    for sign in (1, -1):
        x0, x1 = sorted([sign * xi, sign * xo])
        pieces.append(box(x0, x1, guide_y0, far1, fb, ft))
        pieces.append(box(x0, x1, -13.0, far1, rb, rt))
        # Zigzag nodes from the gate end to the closed end plate, so the first strut printed
        # starts on the plate rather than as a square end in air; ~46 degrees.
        span = (c['end_plate_y_mm'][0] + bar / 2) - (-13.0 + bar / 2); count = int(round(span / (rb - ft - bar)))
        nodes = list(np.linspace(-13.0 + bar / 2, c['end_plate_y_mm'][0] + bar / 2, count + 1))
        for i, y in enumerate(nodes[:-1]):
            p0 = (y, ft + bar / 2 if i % 2 == 0 else rb - bar / 2)
            p1 = (nodes[i + 1], rb - bar / 2 if i % 2 == 0 else ft + bar / 2)
            pieces.append(bar_yz(x0, x1, p0, p1, bar))
        # Gate guides at the open end, led in at 45 degrees from the side rail.
        g0, g1 = c['guide_x_mm']
        lead = box(x0, x1, guide_y1, guide_y1 + (g1 - g0 - (xo - xi)), fb, rt)
        block = box(min(sign * g0, sign * g1), max(sign * g0, sign * g1), guide_y0, guide_y1, fb, rt)
        pieces.append(mf.Manifold.batch_hull([lead, block]))
        # Cell end stops at the closed end, outside the pouch reserve, centre left open.
        s0, s1 = c['stop_block_x_mm']
        pieces.append(box(min(sign * s0, sign * s1), max(sign * s0, sign * s1), lv['half_l'], c['end_plate_y_mm'][0] + .1, ft, ft + P['cell']['manufacturer_max_mm']['thickness']))
    # Closed end plate on the bed, with a pointed window.
    e0, e1 = c['end_plate_y_mm']
    plate = box(-xo, xo, e0, e1, fb, rt)
    plate -= prism_xz([(-4.2, 6.6), (4.2, 6.6), (4.2, 9.4), (0, 11.4), (-4.2, 9.4)], e0 - 1, e1 + 1)
    pieces.append(plate)
    shape = union(pieces) ^ box(-30, 30, near0, far1, -20, 30)
    # Slots for the sliding gate wedges, cut after the guide union so nothing refills them.
    sx = c['slot_x_centre_mm']; sw = c['slot_width_mm']; sy0, sy1 = c['gate_slot_y_mm']
    for sign in (1, -1):
        shape -= box(min(0, sign * (sx + sw / 2)), max(0, sign * (sx + sw / 2)), sy0, sy1, ft + .35, rt + 2)
        # The guide end cap closes over the slot as a short cantilever; chamfer its free inner top
        # corner where the gate's grab bar passes, so a sagging corner cannot bind the gate.
        ch = c['guide_cap_chamfer_mm']
        tri = [(sign * xi, rt + .01), (sign * (xi + ch), rt + .01), (sign * xi, rt - ch)]
        shape -= prism_xz(tri, guide_y0 - .1, sy0 + .05)
    # Rings: far band on the bed; near band with its lead-in skirt under the floor spine.
    near, L, near_range = arrow_ring(near0, near1, +1, ROD['ring_width'])
    far = ring((far0 + far1) / 2, None, ROD['ring_width'])
    # The floor saddle plate ends in a 45-degree point toward the far end, so its first printed
    # layer grows from the spine instead of starting as a flat shelf in air.
    end = near_range[1] + .3
    pieces_saddle = mf.Manifold.batch_hull([box(-sd, sd, near0, end, fb, ft), box(-sp, sp, near0, end + (sd - sp), fb, ft)])
    saddle = mf.Manifold.batch_hull([saddle_xz(sd, fb + .3, a['saddle_bottom_z_mm'], near0, end),
                                     saddle_xz(sp, fb + .3, a['saddle_bottom_z_mm'], near0, end + (sd - sp), max_half=sp + .01)]) + pieces_saddle
    shape = (shape + saddle) - corridor()
    shape = shape + near + far
    shape -= gap_cut(*near_range)
    shape -= gap_cut(far0, far1)
    shape -= wire_bus(-80, 100)
    shape -= wire_bus(-80, 100).mirror((1, 0, 0))
    import spaces16
    return clean(spaces16.carve(shape, spaces16.regions('Battery_Holder'), 'battery'), 'Battery_Holder')


def battery_gate(fitted=False):
    """Removable end bar: two sliding wedges, a top grab bar and two end-corner stubs.

    The wedges act on the guides, the stubs stop the cell at its end corners, and the centre
    stays open between the stubs for the protected lead end and its wires.
    """
    c = P['cage']; lv = cage_levels(); y0, y1 = c['gate_y_mm']
    half = c['gate_fitted_width_mm' if fitted else 'gate_relaxed_width_mm'] / 2
    lo = lv['floor_top'] + .5; hi = lo + 5.5
    pieces = []
    for sign in (1, -1):
        x = sign * c['slot_x_centre_mm']
        pts = [(x - .6, lo), (x + .6, lo), (x + half, lo + .8), (x + half, lo + 1.8), (x + .6, hi), (x - .6, hi), (x - half, lo + 1.8), (x - half, lo + .8)]
        profile = mf.CrossSection([pts]).offset(-.08, mf.JoinType.Round).offset(.08, mf.JoinType.Round)
        pieces.append(prism_xz([tuple(q) for q in profile.to_polygons()[0]], y0, y1))
        s0, s1 = c['gate_stub_x_mm']
        pieces.append(box(min(sign * s0, sign * s1), max(sign * s0, sign * s1), y0, y1, lv['floor_top'] + .4, lv['roof_bottom'] + .2))
    # Grab bar 0.2 mm above the cell top, 1.9 mm deep, standing 0.4 mm proud of the wedge tops.
    bar_z0 = lv['roof_bottom'] - .4; bar_z1 = hi + .4
    pieces.append(prism_xz(rounded_rect_xz(-c['slot_x_centre_mm'] - .6, c['slot_x_centre_mm'] + .6, bar_z0, bar_z1, .6), y0, y1))
    return union(pieces)


def rounded_rect_xz(x0, x1, z0, z1, r):
    return [tuple(q) for q in mf.CrossSection.square((x1 - x0 - 2 * r, z1 - z0 - 2 * r)).translate((x0 + r, z0 + r)).offset(r, mf.JoinType.Round).to_polygons()[0]]


# ---------------------------------------------------------------------------
# XIAO Sense rod holder
# ---------------------------------------------------------------------------
def board_outline(dx=0., dy=0., thickness=None, z0=None):
    """The official plain-outline board (rounded rectangle) at its nominal seat, shifted by (dx, dy)."""
    s = P['sensor']; bo = s['board_outline_mm']; z = SENSOR['board_z'] if z0 is None else z0
    t = SENSOR['board_thickness'] if thickness is None else thickness
    return rr(bo['width'], bo['length'], bo['corner_radius'], z, z + t).translate((dx, s['board_near_end_y_mm'] + bo['length'] / 2 + dy, 0))


def board_corner_centres():
    """Centres of the four corner arcs of the nominal board (x, y) and the arc radius."""
    s = P['sensor']; bo = s['board_outline_mm']; yn = s['board_near_end_y_mm']
    cx = bo['width'] / 2 - bo['corner_radius']; r = bo['corner_radius']
    return [(sx * cx, yy) for sx in (1, -1) for yy in (yn + r, yn + bo['length'] - r)], r


def near_stop_face():
    """y(x) of the near stop face for x > 0: the 45-degree line tangent to the near corner arc
    offset outward by the stop clearance. Mirror in X for the other side."""
    s = P['sensor']; (cx, cy), r = board_corner_centres()[0][0], board_corner_centres()[1]
    rc = r + s['stop_clearance_mm']
    return lambda x: x - cx + cy - math.sqrt(2) * rc


def board_travel(dx=0.):
    """Analytic free travel of the board (mm) from its nominal seat: lateral to the rails, axial
    toward the near V stops (reduced by any lateral offset) and toward the far stop faces."""
    s = P['sensor']; bo = s['board_outline_mm']; r = bo['corner_radius']; cx = bo['width'] / 2 - r
    lateral = s['rail_x_mm'][0] - bo['width'] / 2
    near = s['stop_clearance_mm'] * math.sqrt(2) - abs(dx)
    # The flat far stop faces (|X| >= cradle inner) meet the far corner arcs where they have receded
    # from the straight end; a lateral offset brings one arc's straighter part onto its face.
    xl = max(0., s['cradle_inner_x_mm'] - abs(dx) - cx)
    far = s['far_stop_y_mm'] - (s['board_near_end_y_mm'] + bo['length'] - r + math.sqrt(r * r - xl * xl))
    return {'lateral': lateral, 'near': near, 'far': far}


def board_travel_poses(margin=0., n_lateral=5, n_axial=5):
    """(dx, dy) poses covering the reachable board positions, `margin` inside the stops/rails."""
    lat = board_travel()['lateral'] - margin
    poses = []
    for dx in np.linspace(-lat, lat, n_lateral):
        t = board_travel(dx)
        for dy in np.linspace(-(t['near'] - margin), t['far'] - margin, n_axial):
            poses.append((float(dx), float(dy)))
    return poses


@lru_cache(maxsize=1)
def sensor_holder():
    s = P['sensor']; a = P['arrow_ring']; z = SENSOR['board_z']
    rx0, rx1 = s['rail_x_mm']; rz0, rz1 = s['rail_z_mm']; y0, y1 = s['y_mm']
    pieces = []
    bo = s['board_outline_mm']; yn = s['board_near_end_y_mm']; yf = yn + bo['length']
    inner = s['cradle_inner_x_mm']; zl = z - s['ledge_thickness_mm']; zs = z + s['stop_height_mm']
    under_near, under_far = s['ledge_under_board_mm']; tab_y0 = s['near_tab_y0_mm']
    for sign in (1, -1):
        xr = lambda a, b: (min(sign * a, sign * b), max(sign * a, sign * b))
        pieces.append(box(*xr(rx0, rx1), y0, y1, rz0, rz1))
        # Near end cradle. Ledge: 1.0 mm thick from the rail to |X| inner, from the tab's far
        # side to `under_near` mm under the board. It starts above open space, so it is led in at
        # 45 degrees from the rail (the lead runs under the board edge toward +Y).
        ledge = box(*xr(inner, rx0 + .1), tab_y0, yn + under_near, zl, z)
        sliver = box(*xr(rx0, rx0 + .1), tab_y0, yn + under_near + (rx0 - inner), zl, z)
        pieces.append(mf.Manifold.batch_hull([ledge, sliver]))
        # Near stop: a 45-degree face in plan, tangent to the board corner arc offset by the stop
        # clearance, so it prints at exactly 45 degrees and meets the rounded corner (the board's
        # straight end lies inside |X| 6.985). Both sides together form a self-centring V.
        face = near_stop_face()
        tab = [(sign * (rx0 + .1), face(rx0 + .1)), (sign * (rx0 + .1), tab_y0), (sign * inner, tab_y0), (sign * inner, face(inner))]
        pieces.append(prism_xy(tab, z, zs))
        # Far end cradle on the bed: ledge from `under_far` mm under the board end continuously to
        # the bed, and the stop block above the board plane outside the USB footprint.
        pieces.append(box(*xr(inner, rx0 + .1), yf - under_far, y1, zl, z))
        pieces.append(box(*xr(inner, rx0 + .1), s['far_stop_y_mm'], y1, z, zs))
        # End bars from the ring crowns to the rails. The far pair lies in its ring plane on the
        # bed. The near pair is the top of the print, so each bar is a 45-degree gusset: its rail
        # end reaches further toward the board and the bar grows from the rail layer by layer.
        (cx, cz), (bx, bz) = s['bar_crown_mm'], s['bar_rail_mm']
        fy0, fy1 = s['far_band_y_mm']; ny0, ny1 = s['near_band_y_mm']
        pieces.append(bar_xz(fy0, fy1, (sign * cx, cz), (sign * bx, bz), s['bar_width_mm']))
        flat = bar_xz(ny0, ny1, (sign * cx, cz), (sign * bx, bz), s['bar_width_mm'])
        reach = bx - cx; hw = s['bar_width_mm'] / 2
        root = box(min(sign * (rx0 + .05), sign * bx), max(sign * (rx0 + .05), sign * bx), ny0, ny1 + reach, bz - hw, bz + hw)
        root_tip = box(min(sign * rx0, sign * (rx0 + .05)), max(sign * rx0, sign * (rx0 + .05)), ny0, ny1 + reach + (bx - rx0), bz - hw, bz + hw)
        pieces.append(mf.Manifold.batch_hull([flat, root, root_tip]))
        # Mid-height diagonal strut from each rail down to the keel, below the board: it ties the
        # otherwise free-standing 21 mm rail columns and prints at about 47 degrees.
        (ax, ay, az), (kx_, ky, kz) = s['strut_rail_mm'], s['strut_keel_mm']; hw = s['strut_width_mm'] / 2
        pieces.append(mf.Manifold.batch_hull([box(sign * ax - hw, sign * ax + hw, ay - hw, ay + hw, az - hw, az + hw),
                                              box(sign * kx_ - hw, sign * kx_ + hw, ky - hw, ky + hw, kz - hw, kz + hw)]))
    # Keel over the rod joining both crowns, flared into the near saddle.
    kx = s['keel_x_mm']; kz0, kz1 = s['keel_z_mm']
    pieces.append(box(-kx, kx, y0, y1, kz0, kz1))
    near0, near1 = s['near_band_y_mm']; far0, far1 = s['far_band_y_mm']
    near, L, near_range = arrow_ring(near0, near1, +1, s['clip_width_mm'], ROD['sensor_clip_root_wall'])
    far = ring((far0 + far1) / 2, None, s['clip_width_mm'], ROD['sensor_clip_root_wall'])
    end = near_range[1] + .3; wide = a['saddle_max_half_width_mm']
    pieces.append(mf.Manifold.batch_hull([saddle_xz(kx, kz1, a['saddle_bottom_z_mm'], near0, end),
                                          saddle_xz(kx, kz1, a['saddle_bottom_z_mm'], near0, end + (wide - kx), max_half=kx + .01)]))
    shape = union(pieces) - corridor()
    shape = shape + near + far
    shape -= gap_cut(*near_range)
    shape -= gap_cut(far0, far1)
    return clean(shape, 'XIAO_Rod_Holder')


# ---------------------------------------------------------------------------
# References, parts and export
# ---------------------------------------------------------------------------
def references():
    refs = {}
    c = P['cap_clearance_screen']; hw = seated_hardware(); socket = seated_socket()
    for i, ((x, y), rot) in enumerate(zip(key_positions(), key_rotations())):
        refs[f'key_{i}_switch'] = hw['switch'].rotate((0, 0, rot)).translate((x, y, PCB_Z))
        refs[f'key_{i}_socket'] = socket.rotate((0, 0, rot)).translate((x, y, PCB_Z))
        refs[f'key_{i}_cap'] = rr(c['reference_width_mm'], c['reference_length_mm'], 1.4, PCB_Z + 6.1, PCB_Z + 9.1).translate((x, y, 0))
    refs['cell'] = cell_shape(); refs['cell_reserve'] = cell_shape(True)
    s = P['sensor']; bo = s['board_outline_mm']; bz = SENSOR['board_z']; bt = SENSOR['board_thickness']
    refs['pcb'] = board_outline()
    refs['usb'] = box(-4.6, 4.6, 18, 24.3, bz + 1, bz + 4.2)
    # USB-C plug overmould beyond the holder's far end (12.4 x 6.5 mm bodies are common; stated, not measured).
    refs['usb_plug_body'] = box(-6.3, 6.3, s['y_mm'][1] + .15, 45, bz - .7, bz + 6.0)
    # Top-side pad/solder access: the board footprint offset 0.25 mm, from the board top up 2.5 mm.
    refs['pad_access_top'] = rr(bo['width'] + .5, bo['length'] + .5, bo['corner_radius'] + .25, bz + bt, bz + bt + 2.5).translate((0, s['board_near_end_y_mm'] + bo['length'] / 2, 0))
    refs['wire'] = external_wire_route()
    refs['rod'] = tube_y(ROD['inside_diameter'] / 2, ROD['diameter'] / 2, -30, 60)
    return refs


def part_shapes():
    return {'Key_Carrier': carrier(), 'Battery_Holder': battery_module(),
            'Battery_End_Gate': battery_gate(), 'XIAO_Rod_Holder': sensor_holder()}


def print_rotation_degrees(name):
    # Every part prints with its +Y (assembly) face on the bed: rotate -90 about X.
    return -90


def battery_position(extra=0.):
    """Battery module origin along the rod: 8 mm beyond the carrier's tip end, gate toward the tip."""
    keys = carrier().bounding_box()
    battery = battery_module().rotate((0, 0, 180)).bounding_box()
    return keys[4] + P['assembly']['battery_end_clearance'] + extra - battery[1]


def xiao_position(extra=0.):
    """XIAO holder origin: 8 mm beyond the battery module's tip end, USB toward the tip."""
    battery = battery_module().rotate((0, 0, 180)).bounding_box()
    holder = sensor_holder().bounding_box()
    return battery_position() + battery[4] + P['assembly']['battery_end_clearance'] + extra - holder[1]


def export():
    out = HERE / 'exports'; out.mkdir(exist_ok=True); records = {}
    for name, shape in part_shapes().items():
        shape = shape.simplify(.0001)
        assert shape.status() == mf.Error.NoError, (name, shape.status())
        m = mesh(shape); assert m.is_watertight and len(m.split()) == 1, (name, len(m.split()))
        m.export(out / (name + '-assembly.stl'))
        rotation = trimesh.transformations.rotation_matrix(math.radians(print_rotation_degrees(name)), [1, 0, 0])
        oriented = m.copy(); oriented.apply_transform(rotation)
        shift = trimesh.transformations.translation_matrix(-oriented.bounds[0]); oriented.apply_transform(shift)
        normal = mf.Manifold(mf.Mesh(np.asarray(np.round(oriented.vertices, 6), np.float32), np.asarray(oriented.faces, np.uint32))).simplify(.000001)
        change = abs(normal.volume() - oriented.volume)
        assert normal.status() == mf.Error.NoError and change < .01, (name, change)
        mesh(normal).export(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        final = trimesh.load_mesh(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        assert final.is_watertight and len(final.split()) == 1, name
        records[name] = {'bounds_mm': m.bounds.tolist(), 'volume_mm3': m.volume,
                         'solid_PETG_g': m.volume / 1000 * r15.P['print']['density_g_cm3'],
                         'print_height_mm': float(final.bounds[1][2]),
                         'stl_float32_volume_change_mm3': change, 'body_count': 1, 'watertight': True,
                         'stl_sha256': sha(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')),
                         'print_to_assembly': np.linalg.inv(shift @ rotation).tolist()}
    import spaces16
    dependencies = [HERE / 'holder16.py', HERE / 'parameters.json', HERE / 'spaces16.py']
    previous = json.loads((R15 / 'exports/manifest.json').read_text())
    dependencies += [R15 / path for path in previous['source_sha256']]
    manifest = {'revision': P['revision'], 'source_sha256': {os.path.relpath(p, HERE): sha(p) for p in dependencies},
                'parts': records, 'physical_fit_verified': False, 'physical_strength_verified': False,
                'physical_comfort_verified': False, 'working_space_carve': spaces16.CARVE_LOG,
                'print_helpers': 'none; rings not on the bed use 45-degree arc lead-in skirts',
                'cell': P['cell'], 'cap_clearance_screen': P['cap_clearance_screen']}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print({n: (round(v['solid_PETG_g'], 2), round(v['print_height_mm'], 1)) for n, v in records.items()}, flush=True)


if __name__ == '__main__':
    export()
