#!/usr/bin/env python3
"""R22: finger guard built into the key holder, curved shoulders, battery slot lead-in,
12-wire cable clip, and every matching keeper reprinted.

Composes the frozen R16-R21 chain and edits none of it. The row shift is applied to the shared R16 parameter
dictionary before any key, socket or working-space geometry is built, so the keys, bought parts, references and
routes all move together from the single `row_shift_mm` parameter.
The guard runners are modelled as 0.2 mm steps on the print-layer grid (print Z = rear_y - Y). Each layer is
grown only from material in the layer below (<= 0.2 mm, i.e. 45 degrees), so the exported mesh is what the
slicer cuts. Nothing here is a physical fit, comfort or strength result.
"""
import sys
sys.dont_write_bytecode = True
from functools import lru_cache
from pathlib import Path
import json, math, os, shutil
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
R20 = HERE.parent / 'carbon-rod-holders-r20-finger-guard'
R21 = HERE.parent / 'carbon-rod-holders-r21-cable-clip'
sys.path.insert(0, str(R20))
import holder20 as h20  # noqa: E402

h19 = h20.h19; h18 = h20.h18; base = h20.base; spaces16 = h20.spaces16; P = h20.P
R19 = h20.R19; R16 = h20.R16
assert P is base.P and spaces16.h is base, 'R22 relies on one shared R16 parameter dictionary'
LOCAL = json.loads((HERE / 'parameters.json').read_text()); K = LOCAL['key_holder']; G = LOCAL['guard']; B = LOCAL['battery']; C = LOCAL['cable_clip']
box, cyl, union, mesh, sha, rect, xz, poly = h19.box, h19.cyl, h19.union, h19.mesh, h19.sha, h19.rect, h20.xz, h20.poly
ROUND = mf.JoinType.Round

# ---------------------------------------------------------------------------
# Row shift: one parameter, applied before anything is built or cached.
# ---------------------------------------------------------------------------
SHIFT = K['row_shift_mm']
assert P['keys']['row_spacing'] == K['r16_row_spacing_mm'] == 17.8 and P['slab']['rear_y_mm'] == 26.9, 'R16 key parameters already changed'
assert spaces16.regions.cache_info().currsize == 0 and spaces16.maximum_socket.cache_info().currsize == 0
P['keys']['row_spacing'] = K['r16_row_spacing_mm'] - SHIFT
P['slab']['rear_y_mm'] = 26.9 - SHIFT
P['carrier_rings']['rear_band_y_mm'] = [23.3 - SHIFT, 26.9 - SHIFT]
P['carrier_rings']['saddle_y_mm'] = [9.0, 26.9 - SHIFT]
REAR = P['slab']['rear_y_mm']

NEW = ['Key_Carrier', 'Battery_Holder', 'Battery_End_Door_Easy_Trial', C['name']]
COPIED_R19 = ['Battery_End_Door', 'XIAO_Near_Keeper', *h19.SPACERS]
COPIED_R20 = ['XIAO_Rod_Holder']
PLATE = ['Key_Carrier', 'Battery_Holder', 'Battery_End_Door', 'Battery_End_Door_Easy_Trial', 'XIAO_Rod_Holder', 'XIAO_Near_Keeper', *h19.SPACERS, C['name']]
ANCHORED = ['Key_Carrier', 'Battery_Holder', 'XIAO_Rod_Holder', C['name']]
BUILD_LIST = {
    'Key_Carrier': 'R22 key holder with the built-in guard runners and curved shoulders. Supersedes the R20 key holder and the separate R20 Finger_Guard.',
    'Battery_Holder': 'R22 battery holder: the R20 holder plus a lead-in at the top of each door slot. Takes either door below.',
    'Battery_End_Door': 'Standard door, byte-identical to R19. Fits the R19, R20 and R22 battery holders. Try this first.',
    'Battery_End_Door_Easy_Trial': 'Trial door: the standard door with its centre catch tooth 0.15 mm shallower (hooks 0.25 mm instead of 0.4 mm). Easier in and out, holds less firmly. Use only if the standard door is still too stiff.',
    'XIAO_Rod_Holder': 'R20 XIAO holder, byte-identical copy (unchanged body; the board already sits almost flush).',
    'XIAO_Near_Keeper': 'R19 XIAO keeper, byte-identical, ORIGINAL-COMPATIBLE: fits the R19 and R20 XIAO holders (R20 never printed one). Slides over the near end of the board and holds it down.',
    'Battery_Spacer_0p4mm': 'R19 cell spacer, reprinted.', 'Battery_Spacer_0p6mm': 'R19 cell spacer, reprinted.', 'Battery_Spacer_0p8mm': 'R19 cell spacer, reprinted.',
    C['name']: 'R22 cable clip for the full harness (12 x 1.5 mm conductors). Supersedes the R21 4 mm clip.'}


def read(path):
    m = trimesh.load_mesh(path); return mf.Manifold(mf.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32)))


# ---------------------------------------------------------------------------
# Key holder slab: cosine shoulders and rounded top edges
# ---------------------------------------------------------------------------
def shoulder_x(y):
    """Half-width of the slab at Y on the shoulder; tangent to both straight side edges."""
    s = P['slab']; lo, up, y0, L = s['lower_half_x_mm'], s['upper_half_x_mm'], s['lower_rear_y_mm'], K['shoulder_curve']['length_mm']
    t = np.clip((np.asarray(y, float) - y0) / L, 0, 1); return up + (lo - up) * (1 + np.cos(np.pi * t)) / 2


def shoulder_max_slope():
    s = P['slab']; return (s['lower_half_x_mm'] - s['upper_half_x_mm']) * math.pi / (2 * K['shoulder_curve']['length_mm'])


@lru_cache(maxsize=1)
def slab_outline():
    s = P['slab']; r = s['plan_corner_radius_mm']; L = K['shoulder_curve']['length_mm']; y0 = s['lower_rear_y_mm']
    assert y0 + L <= s['rear_y_mm'] - 2 + 1e-9 and shoulder_max_slope() < 1, 'Shoulder must print at 45 degrees or less and end before the rear end'
    ys = np.linspace(y0, y0 + L, K['shoulder_curve']['samples']); right = list(zip(shoulder_x(ys).tolist(), ys.tolist()))
    pts = [(-s['lower_half_x_mm'], s['front_y_mm']), (s['lower_half_x_mm'], s['front_y_mm'])] + right + [(s['upper_half_x_mm'], s['rear_y_mm']), (-s['upper_half_x_mm'], s['rear_y_mm'])] + [(-x, y) for x, y in right[::-1]]
    return poly(pts).offset(-r, ROUND, 2., 96).offset(r, ROUND, 2., 96)


def rounded_slab(outline, z0, z1):
    """Prism with every top plan edge rounded: terraces of inward plan offsets, each inset to the round at its top."""
    r = K['top_edge_round_mm']; n = K['top_edge_round_steps']; pieces = [mf.Manifold.extrude(outline, z1 - r - z0).translate((0, 0, z0))]
    for i in range(1, n + 1):
        lo, hi = z1 - r + r * (i - 1) / n, z1 - r + r * i / n; e = r - math.sqrt(max(r * r - (hi - (z1 - r)) ** 2, 0.))
        pieces.append(mf.Manifold.extrude(outline.offset(-min(e, r - .02), ROUND, 2., 48), hi - lo).translate((0, 0, lo)))
    return union(pieces)


def carrier_regions(straight_for_all=False):
    """Key holder working spaces. Keys in `slide_keys` swap their straight-up loading for the sideways slide."""
    out = dict(spaces16.regions('Key_Carrier')); out['unloaded_clip_bore'] = cyl(K['ring_bore_mm'] / 2, -40, 100).rotate((-90, 0, 0))
    if straight_for_all: return out
    for i in G['slide_keys']:
        out.pop(f'key_{i}_socket_loading'); out.pop(f'key_{i}_maximum_socket_loading'); out[f'key_{i}_soldered_socket_slide'] = slide_route(i)
    for i in G['dogleg_keys']: out[f'key_{i}_soldered_socket_dogleg'] = spaces16.Swept(soldered_socket(i), dogleg_poses(i))
    for i in G['straight_soldered_keys']: out[f'key_{i}_soldered_socket_straight'] = spaces16.Swept(soldered_socket(i), [tuple(p) for p in spaces16.socket_route_below()])
    return out


def dogleg_poses(i):
    """Up from 6 mm below, held dogleg_outward_mm away from the rod so the stated solder allowance on the inner
    terminal passes beside the ring, then in at dogleg_level_dz_mm below the seat, then straight up."""
    x = base.key_positions()[i][0]; o = (1 if x > 0 else -1) * G['dogleg_outward_mm']; lv = G['dogleg_level_dz_mm']
    return [(o, 0., -dz) for dz in np.linspace(6., lv, 21)] + [(o * f, 0., -lv) for f in np.linspace(1, 0, 11)][1:] + [(0., 0., -dz) for dz in np.linspace(lv, 0, 11)][1:]


def soldered_socket(i):
    """Key i's maximum socket plus R20's stated solder-and-wire allowance on both terminals, seated, assembly frame."""
    (x, y), rot = base.key_positions()[i], base.key_rotations()[i]
    return union([spaces16.maximum_socket().rotate((0, 0, rot)).translate((x, y, base.PCB_Z))] + [v for k, v in h20.contact_envelopes().items() if k.startswith(f'key_{i}_')])


def slide_poses(i):
    """Sideways from the outer side, slide_lift_mm below the seat, then straight up onto the bosses."""
    x = base.key_positions()[i][0]; side = 1 if x > 0 else -1; L = G['slide_lift_mm']; T = G['slide_travel_mm']
    return [(side * d, 0., -L) for d in np.arange(T, 0, -.5)] + [(0., 0., -dz) for dz in np.linspace(L, 0, 7)]


def slide_route(i): return spaces16.Swept(soldered_socket(i), slide_poses(i))


def key_carrier_bands():
    lo = LOCAL['print']['local_recipe']['Key_Carrier_lower_band_r16_mm']
    return [LOCAL['print']['local_recipe']['Key_Carrier_upper_band_mm'], [round(lo[0] - SHIFT, 3), round(lo[1] - SHIFT, 3)]]


@lru_cache(maxsize=1)
def slab_cutters():
    """Every cut through the slab: key bays, backplate holes, lightening and arrow windows. Runners may not fill them."""
    return union([base.bay_cuts(x, y, rot) for (x, y), rot in zip(base.key_positions(), base.key_rotations())] + [h20.key_windows()])


def upper_left_socket_print_relief():
    relief = K['upper_left_socket_print_relief']
    x0, x1 = relief['x_mm']
    # Map the extruded YZ polygon into assembly coordinates, tapering along the print axis Y.
    return mf.Manifold.extrude(poly(relief['yz_profile_mm']), x1 - x0).transform(
        ((0, 0, 1, x0), (1, 0, 0, 0), (0, 1, 0, 0)))


@lru_cache(maxsize=1)
def carrier_base():
    """holder20.key_carrier_build line for line, with the R22 slab (curved shoulders, rounded top edges)."""
    s = P['slab']; c = P['carrier_rings']; a = P['arrow_ring']; bottom = base.slab_bottom(); top = base.plate_top(); inner = K['ring_bore_mm'] / 2; ROD = h20.ROD
    slab = rounded_slab(slab_outline(), bottom, top); x_span = s['lower_half_x_mm'] + 2
    under = bottom + P['bay']['backplate_thickness_mm'] - P['bay']['backplate_thin_mm']
    slab -= base.edge_round_x(-x_span, x_span, s['front_y_mm'], +1, under, +1, s['nose_finger_radius_mm'])
    for (x, y), rot in zip(base.key_positions(), base.key_rotations()): slab -= base.bay_cuts(x, y, rot)
    slab -= base.thinning(base.key_positions(), base.key_rotations())
    slab -= h20.key_windows()
    gap, root = ROD['clip_gap_degrees'], ROD['clip_root_wall']; k = 1 / math.tan(math.radians(a['lead_angle_degrees'])); m0, m1 = c['mid_band_y_mm']; r0, r1 = c['rear_band_y_mm']
    skirt, lead = h20.clip_skirt(m0, m1, +1, gap, root, a['root_phi_degrees_above_equator'], k, a['skin_thickness_mm'], inner)
    saddle = base.saddle_xz(a['saddle_top_half_width_mm'], bottom + 1.0, a['saddle_bottom_z_mm'], *c['saddle_y_mm'])
    shape = (union([slab, saddle]) - base.corridor()) + h20.clip_ring(m0, m1, gap, root, inner) + skirt + h20.clip_ring(r0, r1, gap, root, inner)
    shape -= base.gap_cut(m0, m1 + lead); shape -= base.gap_cut(r0, r1); shape -= base.wire_bus(-80, 100)
    carved = spaces16.carve(shape, carrier_regions(straight_for_all=True), 'carrier22:base')
    solid = base.clean(carved - upper_left_socket_print_relief(), 'Key_Carrier')
    assert abs(solid.bounding_box()[4] - REAR) < 1e-6, 'The rear face must be the print bed plane'
    return solid


# ---------------------------------------------------------------------------
# Guard runners, grown layer by layer
# ---------------------------------------------------------------------------
def soft(t, a):
    """C1 corner: 0 for t <= -a, t for t >= a, a parabola between. Returns (value, slope)."""
    if t <= -a: return 0., 0.
    if t >= a: return t, 1.
    return (t + a) ** 2 / (4 * a), (t + a) / (2 * a)


def beam_path(b, y):
    """(x, plan slope dx/dY, bottom z, dz/dY) of runner b at Y, or None outside it."""
    if y > b['root_y_mm']: return None
    z0, a = G['z0_mm'], G['blend_half_length_mm']; land = b['root_y_mm'] - (G['underside_ref_z_mm'] - z0)
    rear, sr = soft(y - land, a); front, sf = soft(b['riser_corner_y_mm'] - y, a); z = z0 + rear + front
    if y < b['riser_corner_y_mm'] and z >= G['end_inside_slab_z_mm']: return None
    pts = b['plan_y_x_mm']; ys = [p[0] for p in pts]; xs = [p[1] for p in pts]
    x = float(np.interp(y, ys[::-1], xs[::-1]))
    j = next((i for i in range(len(ys) - 1) if ys[i] >= y >= ys[i + 1]), len(ys) - 2); sx = (xs[j + 1] - xs[j]) / (ys[j + 1] - ys[j])
    return x, sx, z, sr - sf


def beam_section(b, y):
    p = beam_path(b, y)
    if p is None: return None
    x, sx, z, sz = p; assert abs(sx) <= G['max_plan_slope'] + 1e-9, (b['name'], 'plan slope over 45 degrees')
    assert not (abs(sx) > 1e-9 and abs(sz) > 1e-9), (b['name'], 'runner turns in plan and in height in the same layer')
    w = G['width_mm'] * math.sqrt(1 + sx * sx); hv = G['thickness_mm'] * math.sqrt(1 + sz * sz); r = G['section_round_mm']
    return rect(x - w / 2, x + w / 2, z, z + hv).offset(-r, ROUND, 2., 32).offset(r, ROUND, 2., 32)


def to_layer(m): return m.rotate((-90, 0, 0))     # (x, y, z) -> (x, z, -y): slice(-Y) is the XZ section at Y


@lru_cache(maxsize=1)
def guard_keepout():
    """Spaces the runners may not enter, as solids: straight-up columns of the keys that keep straight loading,
    the sideways slide corridors (from the lowered terminal allowance up), the external wire bus and the rod."""
    out = []; L = G['slide_lift_mm']; bottom = base.slab_bottom()
    for i in range(len(base.key_positions())):
        s = soldered_socket(i); plan = mf.CrossSection.batch_boolean([s.slice(z) for z in np.arange(4.4, 8.9, .1)], mf.OpType.Add).offset(.3, ROUND, 2., 32)
        if i in G['slide_keys']:
            x = base.key_positions()[i][0]; side = 1 if x > 0 else -1; zlo = s.bounding_box()[2] - L - .2
            sweep = mf.CrossSection.batch_boolean([plan.translate((side * d, 0)) for d in np.arange(0, G['slide_travel_mm'] + .01, .25)], mf.OpType.Add)
            out.append(mf.Manifold.extrude(sweep, bottom - zlo).translate((0, 0, zlo)))
        else:
            if i in G['dogleg_keys']:
                o = (1 if base.key_positions()[i][0] > 0 else -1) * G['dogleg_outward_mm']; plan = mf.CrossSection.batch_boolean([plan.translate((o * f, 0)) for f in np.linspace(0, 1, 6)], mf.OpType.Add)
            out.append(mf.Manifold.extrude(plan, bottom + 1 + 20).translate((0, 0, -20)))
    out.append(base.wire_bus(-80, 100))
    out.append(cyl(4.6, -40, 100).rotate((-90, 0, 0)))
    return union(out)


@lru_cache(maxsize=1)
def guard_layers():
    """Per print layer: desired runner section, then only what the layer below (holder or runner) supports."""
    step = .2; n = int(round((REAR - P['slab']['front_y_mm']) / step)); grow = step + 1e-3
    cb, cut, keep = to_layer(carrier_base()), to_layer(slab_cutters()), to_layer(guard_keepout())
    layers = []; prev = mf.CrossSection(); below = cb.slice(-(REAR - step / 2)); trimmed = 0.; desired = 0.
    for k in range(n):
        y_hi = REAR - k * step; y_lo = REAR - (k + 1) * step; yc = (y_hi + y_lo) / 2; here = cb.slice(-yc)
        parts = [s for s in (beam_section(b, yc) for b in G['beams']) if s is not None]
        if parts:
            want = mf.CrossSection.batch_boolean(parts, mf.OpType.Add) - cut.slice(-yc) - keep.slice(-yc)
            b = want.bounds(); window = rect(b[0] - 1, b[2] + 1, b[1] - 1, b[3] + 1)
            got = want ^ ((prev + below) ^ window).simplify(.002).offset(grow, ROUND, 2., 24)
            # Keep only what lies outside the holder (plus a 0.1 mm bond into it), so merged runner ends do not pile up.
            got = got - (here ^ window).offset(-.1, ROUND, 2., 24)
            got = mf.CrossSection.batch_boolean([q for q in got.decompose() if q.area() > .02], mf.OpType.Add) if got.area() > 0 else got
            outside = want - (here ^ window); desired += outside.area() * step; trimmed += max(0., (outside - got).area()) * step
        else: got = mf.CrossSection()
        layers.append((y_lo, y_hi, got)); prev = got; below = here
    return layers, {'desired_mm3': round(desired, 3), 'trimmed_unsupported_mm3': round(trimmed, 3)}


@lru_cache(maxsize=1)
def guard():
    # Tiny overlap joins adjacent sections robustly when the solids are fused.
    # The final carrier still runs its complete working-space check.
    seam = .001
    pieces = [xz(s, y0 - seam, y1 + seam) for y0, y1, s in guard_layers()[0] if s.area() > 0]
    return union(pieces)


@lru_cache(maxsize=1)
def key_carrier():
    solid = carrier_base() + guard(); before = solid.volume()
    carved = spaces16.carve(solid, carrier_regions(), 'carrier22:final'); removed = before - carved.volume()
    assert removed < .02, ('working spaces cut the runners or holder', removed, spaces16.CARVE_LOG['carrier22:final'])
    return base.clean(carved, 'Key_Carrier')


# ---------------------------------------------------------------------------
# Battery holder and doors
# ---------------------------------------------------------------------------
def slot_leadins():
    c = h19.CAGE; lv = base.cage_levels(); rt = lv['roof_top']; sx, sw = c['slot_x_centre_mm'], c['slot_width_mm']; sy1 = c['gate_slot_y_mm'][1]; wall_x = sx + sw / 2; d = B['slot_mouth_leadin']
    assert rt - d['height_z_mm'] >= h19.D['bridge']['pocket_ceiling_z_mm'] + .1, 'The lead-in must leave the hook face under the lip intact'
    return h19.prism_yz([(sy1 - .01, rt - d['height_z_mm']), (sy1 + d['depth_y_mm'], rt + .01), (sy1 + d['depth_y_mm'], rt + 3), (sy1 - .01, rt + 3)], -wall_x, wall_x)


@lru_cache(maxsize=1)
def battery_module():
    r20 = h20.battery_module(); rec = json.loads((R20 / 'exports/manifest.json').read_text())['parts']['Battery_Holder']
    assert abs(r20.volume() - rec['volume_mm3']) < .5, 'R20 battery holder not reproduced'
    return base.clean(r20 - slot_leadins(), 'Battery_Holder')


@lru_cache(maxsize=1)
def easy_door():
    door = read(R19 / 'exports/Battery_End_Door-assembly.stl'); b = door.bounding_box(); t = B['easy_door_trial']; hx = t['tooth_half_x_mm']
    assert abs(b[4] - -13.4) < 1e-4, b
    return base.clean(door - box(-hx, hx, b[4] - t['tooth_trim_mm'], b[4] + 1, b[2] - 1, b[5] + 1), 'Battery_End_Door_Easy_Trial')


# ---------------------------------------------------------------------------
# 12-wire cable clip (R21 figure-eight, resized), built flat in its own print frame
# ---------------------------------------------------------------------------
def wire_centres():
    L = C['layout']; out = [(L['outer_radius_mm'] * math.cos(math.radians(L['outer_step_degrees'] * i)), L['outer_radius_mm'] * math.sin(math.radians(L['outer_step_degrees'] * i))) for i in range(L['outer_count'])]
    out += [(L['inner_radius_mm'] * math.cos(math.radians(L['inner_start_degrees'] + L['inner_step_degrees'] * i)), L['inner_radius_mm'] * math.sin(math.radians(L['inner_start_degrees'] + L['inner_step_degrees'] * i))) for i in range(L['inner_count'])]
    return [(C['centres_mm'] + x, y) for x, y in out]


@lru_cache(maxsize=1)
def cable_clip():
    r7 = base.r15.base.r7; width = C['axial_width_mm']
    rod = r7.ring(0, C['rod_bore_mm'], width, C['rod_root_wall_mm']).rotate((-90, 0, 0)).translate((0, 0, width / 2)).rotate((0, 0, -90))
    inner = C['cable_bore_mm'] / 2; wall = C['cable_wall_mm']; cr = inner + wall / 2
    half_gap = math.asin((C['cable_entry_gap_mm'] + wall) / (2 * cr)); angles = np.linspace(half_gap, 2 * math.pi - half_gap, 240)
    outer = np.c_[(inner + wall) * np.cos(angles), (inner + wall) * np.sin(angles)]; inside = np.c_[inner * np.cos(angles[::-1]), inner * np.sin(angles[::-1])]
    section = mf.CrossSection([np.vstack((outer, inside))])
    for a in (angles[0], angles[-1]): section += mf.CrossSection.circle(wall / 2, 48).translate((cr * math.cos(a), cr * math.sin(a)))
    cable = mf.Manifold.extrude(section, width).translate((C['centres_mm'], 0, 0)); ch = C['cable_chamfer_mm']
    shape = rod + cable
    shape -= mf.Manifold.cylinder(ch, inner + ch, inner, 128).translate((C['centres_mm'], 0, 0))
    shape -= mf.Manifold.cylinder(ch, inner, inner + ch, 128).translate((C['centres_mm'], 0, width - ch))
    shape -= mf.Manifold.cylinder(width + 2, inner, inner, 128).translate((C['centres_mm'], 0, -1))       # the rod ring may not intrude into the cable bore
    return base.clean(shape, C['name'])


def cable_clip_pads():
    t, w = C['pad_thickness_mm'], C['tie_width_mm']; pieces = []
    for sign in (-1, 1):
        lo, hi = sorted((sign * 4.7, sign * 7.2)); pieces.append(box(3.2, 6.2, lo, hi, 0, t))
        lo, hi = sorted((sign * .8, sign * 4.9)); pieces.append(box(4.7 - w / 2, 4.7 + w / 2, lo, hi, 0, t))
    return mf.Manifold.batch_boolean(pieces, mf.OpType.Add)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def to_print(shape, name):
    m = mesh(shape)
    if name == 'XIAO_Near_Keeper': rot = trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])
    elif name.startswith('Battery_End_Door'): rot = trimesh.transformations.rotation_matrix(math.radians(90), [1, 0, 0])
    elif name.startswith('Battery_Spacer') or name.startswith('Cable_Clip'): rot = np.eye(4)
    else: rot = trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    o = m.copy(); o.apply_transform(rot); shift = trimesh.transformations.translation_matrix(-o.bounds[0]); o.apply_transform(shift)
    return m, o, shift @ rot


def export_new(name, shape, out):
    shape = shape.simplify(.0001); m, o, tf = to_print(shape, name); assert m.is_watertight and len(shape.decompose()) == 1, name
    m.export(out / (name + '-assembly.stl')); src = out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')
    normal = mf.Manifold(mf.Mesh(np.asarray(np.round(o.vertices, 6), np.float32), np.asarray(o.faces, np.uint32))).simplify(.000001); assert normal.status() == mf.Error.NoError, name
    mesh(normal).export(src); final = trimesh.load_mesh(src); back = read(src).transform(np.linalg.inv(tf)[:3, :])
    drift = float((back - shape).volume() + (shape - back).volume()); assert final.is_watertight and len(back.decompose()) == 1 and drift < .02, (name, 'exported mesh differs from the source solid', drift)
    return {'bounds_mm': m.bounds.tolist(), 'volume_mm3': m.volume, 'solid_PETG_g': m.volume / 1000 * base.r15.P['print']['density_g_cm3'], 'print_height_mm': float(final.bounds[1][2]), 'body_count': 1, 'watertight': True,
            'export_drift_mm3': round(drift, 5), 'stl_sha256': sha(src), 'assembly_stl_sha256': sha(out / (name + '-assembly.stl')), 'print_to_assembly': np.linalg.inv(tf).tolist()}


def copy_part(name, src_dir, out, anchored=False):
    rec = dict(json.loads((src_dir / 'exports/manifest.json').read_text())['parts'][name])
    for suffix in ['-SOURCE-REQUIRES-PREPARATION.stl', '-assembly.stl'] + (['-ANCHOR-REMOVE-AFTER-PRINT.stl'] if anchored else []):
        shutil.copyfile(src_dir / 'exports' / (name + suffix), out / (name + suffix))
    assert sha(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')) == rec['stl_sha256'], (name, 'copy differs')
    rec['copied_from'] = os.path.relpath(src_dir, HERE); return rec


def export(names=None):
    out = HERE / 'exports'; out.mkdir(exist_ok=True); path = out / 'manifest.json'
    old = json.loads(path.read_text()) if path.exists() else {}; records = dict(old.get('parts', {}))
    builders = {'Key_Carrier': key_carrier, 'Battery_Holder': battery_module, 'Battery_End_Door_Easy_Trial': easy_door, C['name']: cable_clip}
    for name in names or PLATE:
        if name in builders: records[name] = export_new(name, builders[name](), out)
        elif name in COPIED_R19: records[name] = copy_part(name, R19, out)
        elif name in COPIED_R20: records[name] = copy_part(name, R20, out, anchored=True)
        else: raise KeyError(name)
        if name == C['name']: records[name]['assembly_frame'] = 'Own frame: rod axis along Z at the origin, printed flat.'
        print(name, round(records[name]['volume_mm3'], 1), round(records[name]['solid_PETG_g'], 3), round(records[name]['print_height_mm'], 2), flush=True)
    if C['name'] in (names or PLATE):
        # The pads and main mesh must use the same print-origin shift.
        assembly_to_print = np.linalg.inv(np.asarray(records[C['name']]['print_to_assembly']))
        pads = cable_clip_pads().transform(assembly_to_print[:3, :])
        mesh(pads).export(out / (C['name'] + '-ANCHOR-REMOVE-AFTER-PRINT.stl'))
    sources = [HERE / 'holder22.py', HERE / 'parameters.json', R20 / 'holder20.py', R20 / 'parameters.json', R19 / 'holder19.py', R19 / 'parameters.json', h18.HERE / 'holder18.py', h18.HERE / 'parameters.json', h19.R17 / 'holder17.py', h19.R17 / 'parameters.json', R16 / 'holder16.py', R16 / 'spaces16.py', R16 / 'parameters.json']
    r20 = json.loads((R20 / 'exports/manifest.json').read_text()); r21 = json.loads((R21 / 'exports/manifest.json').read_text())
    manifest = {'revision': LOCAL['revision'], 'source_sha256': {os.path.relpath(p, HERE): sha(p) for p in sources}, 'parts': {n: records[n] for n in PLATE if n in records}, 'plate_parts': PLATE, 'anchored_parts': ANCHORED,
                'build_list': BUILD_LIST, 'row_shift_mm': SHIFT, 'row_spacing_mm': P['keys']['row_spacing'], 'key_positions_mm': base.key_positions(), 'key_rotations_degrees': base.key_rotations(), 'key_carrier_slow_bands_mm': key_carrier_bands(),
                'guard_layer_growth': guard_layers()[1] if 'Key_Carrier' in (names or PLATE) or 'guard_layer_growth' not in old else old['guard_layer_growth'],
                'assembly_frame': 'Each part in its own frame, rod axis along Y (cable clip: own flat frame, rod axis Z).',
                'superseded_stl_sha256': {'Key_Carrier (R20)': r20['parts']['Key_Carrier']['stl_sha256'], 'Finger_Guard (R20, separate; still fits R16/R20 key holders)': r20['parts']['Finger_Guard']['stl_sha256'], 'Battery_Holder (R20)': r20['parts']['Battery_Holder']['stl_sha256'], 'Cable_Clip_4mm (R21)': r21['parts']['Cable_Clip_4mm']['stl_sha256']},
                'physical_fit_verified': False, 'physical_strength_verified': False, 'physical_comfort_verified': False}
    path.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    export(sys.argv[1:] or None)
