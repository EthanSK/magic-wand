#!/usr/bin/env python3
"""R18 repair after the physical R17 trial: easy-release anchors, one-tab battery door, spacers, stronger XIAO cradle.

Composes the frozen R16/R17 chain. New: the arrow roof and door on the battery, flat removable cell spacers,
and an XIAO tray with a fixed far hoop and a slide-in near keeper. Key_Carrier stays unchanged from R16.
"""
from functools import lru_cache
from pathlib import Path
import json, math, os, sys
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
R17 = HERE.parent / 'carbon-rod-holders-r17-anchored-repair'
R16 = HERE.parent / 'carbon-rod-holders-r16-repair'
sys.path[:0] = [str(R17), str(R16)]
import holder17 as h17  # noqa: E402
import spaces16  # noqa: E402

_R17_BATTERY = h17.battery_module; base = h17.base; P = h17.P; LOCAL = json.loads((HERE / 'parameters.json').read_text())
box, cyl, union, mesh, sha, prism_xz, prism_xy, bar_xz, saddle_xz, prism_yz = h17.box, h17.cyl, h17.union, h17.mesh, h17.sha, h17.prism_xz, h17.prism_xy, h17.bar_xz, h17.saddle_xz, h17.prism_yz
CAGE, S, RET, GATE, WIRE, INSERTION, XO, BZ, BT, BOARD_TOP = h17.CAGE, h17.S, h17.RET, h17.GATE, h17.WIRE, h17.INSERTION, h17.XO, h17.BZ, h17.BT, h17.BOARD_TOP
D, H, K, SP = LOCAL['door'], LOCAL['xiao'], LOCAL['keeper'], LOCAL['spacers']
SPACERS = {f"Battery_Spacer_{str(t).replace('.', 'p')}mm": t for t in SP['thickness_mm']}
PLATE = ['Battery_Holder', 'Battery_End_Door', 'XIAO_Rod_Holder', 'XIAO_Near_Keeper', *SPACERS]
NEW_PARTS = PLATE; ANCHORED = ['Battery_Holder', 'XIAO_Rod_Holder']; UNCHANGED = ['Key_Carrier']


def rect(x0, x1, y0, y1): return mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
def _xz(section, y0, y1):
    solid = mf.Manifold.extrude(section, y1 - y0)                   # (u, v, w) -> (x, y, z)
    return solid.transform(np.array([[1., 0, 0, 0], [0, 0, -1, y1], [0, 1, 0, 0]]))


@lru_cache(maxsize=1)
def battery_module():
    """R17 channel plus an arrow roof that closes the near end; the bar under it catches the door."""
    lv = base.cage_levels(); rb, rt = lv['roof_bottom'], lv['roof_top']; b = D['bridge']; f = CAGE['roof_flange_inner_x_mm']; y = b['front_y_mm']; a = b['arrow_start_y_mm']; ap = a - f
    arrow = prism_xy([(-12.2, y), (12.2, y), (12.2, ap + 1.2), (f + .4, ap + 1.2), (f + .4, a), (f, a), (0, ap), (-f, a), (-f - .4, a), (-f - .4, ap + 1.2), (-12.2, ap + 1.2)], rb, rt)
    shape = _R17_BATTERY() + arrow; hw = b['pocket_half_x_mm']
    shape -= box(-hw, hw, y - .5, b['pocket_back_y_mm'], rb - .05, b['pocket_ceiling_z_mm'])
    c = b['chamfer_start_z_mm']; run = rt - c
    shape -= prism_yz([(y - .5, c - .5), (y, c), (y + run, rt), (y + run, rt + 1), (y - .5, rt + 1)], -hw, hw)
    return base.clean(shape, 'Battery_Holder')


def battery_door(flexed=False, tooth_dy=0.):
    """One flat plate, no legs. Tooth on a sprung bar inside the outline; `flexed` drops the tooth, `tooth_dy` moves it as a bent-bar release check."""
    c = CAGE; y0, y1 = D['y_mm']; X = D['half_x_mm']; z0, z1 = D['z_mm']; w = c['wire_exit_clear_x_mm']; o = D['opening_top_z_mm']
    t0, t1 = D['tongue_z_mm']; root = D['tongue_root_x_mm']; tip = D['tongue_tip_x_mm']; sl = D['slit_mm']
    plan = mf.CrossSection([base.ccw([(-X + .6, z0), (X - .6, z0), (X, z0 + .6), (X, z1 - .6), (X - .6, z1), (-X + .6, z1), (-X, z1 - .6), (-X, z0 + .6)])])
    plan -= rect(-w, w, z0 - 1, o)
    plan -= rect(root, tip + sl, t1, t1 + sl); plan -= rect(tip, tip + sl, o - .1, t1 + sl); plan -= rect(root, -w + .01, t0 - sl, t0)
    a, b = D['window_x_mm']; plan -= rect(a, b, t1, D['window_top_z_mm']); plan += rect(D['tab_x_mm'][0], D['tab_x_mm'][1], t1 - .05, D['tab_top_z_mm'])
    door = _xz(plan, y0, y1)
    if not flexed:
        hw = D['tooth_half_x_mm']; door += prism_yz([tuple(p) for p in D['tooth_yz_mm']], -hw, hw).translate((0, tooth_dy, 0))
    return base.clean(door, 'Battery_End_Door')


def spacer(t):
    lv = base.cage_levels(); hw, hl = SP['half_x_mm'], SP['y_mm']; cx, cy = SP['protection_notch_half_x_mm'], SP['protection_end_y_mm']; z = lv['floor_top']
    plan = rect(-hw, hw, *hl).offset(-1.2, mf.JoinType.Round).offset(1.2, mf.JoinType.Round) - rect(-cx, cx, hl[0] - 1, cy)
    for i in range(round(t / .2)):      # Edge nicks: one per printed layer, so the thickness can be read by eye.
        plan -= mf.CrossSection.circle(.45, 16).translate(((i - (t / .2 - 1) / 2) * 2., hl[1]))
    return base.clean(mf.Manifold.extrude(plan, t).translate((0, 0, z)), f'spacer {t}')


@lru_cache(maxsize=1)
def sensor_holder():
    """A connected tray: rails, continuous web, keel. Far hoop fixed, near posts carry the keeper."""
    s = S; a = P['arrow_ring']; z = BZ; rx0, rx1 = s['rail_x_mm']; rz0, rz1 = s['rail_z_mm']; y0, y1 = s['y_mm']; bo = s['board_outline_mm']; yn = s['board_near_end_y_mm']; yf = yn + bo['length']; inner = s['cradle_inner_x_mm']
    zl = z - s['ledge_thickness_mm']; zs = z + s['stop_height_mm']; uf = s['ledge_under_board_mm'][1]; tab = s['near_tab_y0_mm']; limit = s['near_contact_limit_y_mm']; drop = s['lead_top_drop_mm']; lt = s['lead_thickness_mm']; ramp = s['ramp_length_mm']
    kx = s['keel_x_mm']; kz0, kz1 = s['keel_z_mm']; (ix, iz0, iz1), (ox, oz0, oz1) = H['web_inner_x_z_z'], H['web_outer_x_z_z']; hp = H['hoop']; r = RET; pieces = [box(-kx, kx, y0, y1, kz0, kz1)]
    for sign in (1, -1):
        xr = lambda p, q: (min(sign * p, sign * q), max(sign * p, sign * q))
        pieces.append(box(*xr(rx0, rx1), y0, y1, rz0, rz1))
        pieces.append(mf.Manifold.batch_hull([box(*xr(ix - .1, ix), y0, y1, iz0, iz1), box(*xr(ox - .1, ox), y0, y1, oz0, oz1)]))
        pieces.append(box(*xr(inner, rx0 + .1), tab, limit, zl, z))
        pieces.append(mf.Manifold.batch_hull([box(*xr(inner, rx0 + .1), limit - .01, limit, zl, z), box(*xr(inner, rx0 + .1), limit + ramp, limit + ramp + .01, z - drop - lt, z - drop)]))
        reach = rx0 - inner; top = z - drop; bot = top - lt
        pieces.append(mf.Manifold.batch_hull([box(*xr(inner, rx0 + .1), limit + ramp, limit + ramp + .01, bot, top), box(*xr(rx0, rx0 + .1), limit + ramp + reach, limit + ramp + reach + .01, bot, top)]))
        face = base.near_stop_face(); clip = s['near_stop_clip_y_mm']; px = min(rx0 + .1, clip - face(0.) if face(rx0 + .1) > clip else rx0 + .1)
        pieces.append(prism_xy([(sign * (rx0 + .1), clip), (sign * (rx0 + .1), tab), (sign * inner, tab), (sign * inner, face(inner)), (sign * px, clip)], z, zs))
        pieces.append(box(*xr(inner, rx0 + .1), yf - uf, y1, zl, z)); pieces.append(box(*xr(inner, rx0 + .1), s['far_stop_y_mm'], y1, z, zs))
        (cx, cz), (bx, bz) = s['bar_crown_mm'], s['bar_rail_mm']; fy0, fy1 = s['far_band_y_mm']; ny0, ny1 = s['near_band_y_mm']; bw = s['bar_width_mm']
        pieces.append(bar_xz(fy0, fy1, (sign * cx, cz), (sign * bx, bz), bw))
        pieces.append(bar_xz(ny0, ny1, (sign * cx, cz), (sign * bx, bz), bw))
        p = r['post']; fy0_, fy1_ = p['full_y_mm']; outer = p['outer_x_mm']; ptop = p['top_z_mm']; lead = p['lead_end_y_mm']
        pieces.append(box(*xr(rx0, outer), fy0_, fy1_, rz0, ptop))
        pieces.append(mf.Manifold.batch_hull([box(*xr(rx0, outer), fy1_ - .01, fy1_, rz0, ptop), box(*xr(rx0, rx1), lead, lead + .01, rz0, rz1)]))
        # Far hoop shoulder: stands on the bed in print, tied along the rail; bare board corner only.
        pieces.append(box(*xr(hp['shoulder_inner_x_mm'], rx1), hp['y_mm'][0], y1, hp['shoulder_under_z_mm'], hp['top_z_mm']))
        pieces.append(box(*xr(rx0 - .05, rx1), hp['y_mm'][0], y1, rz1 - .05, hp['shoulder_under_z_mm'] + .05))
    b0, b1 = hp['bar_y_mm']; u = hp['under_usb_z_mm']; t = hp['top_z_mm']; ax = hp['arrow_half_x_mm']; ay = hp['y_mm'][0]; ib = hp['shoulder_inner_x_mm'] + .1
    pieces.append(box(-ib, ib, b0, y1, u, t)); pieces.append(prism_xy([(-ax, b0 + .1), (ax, b0 + .1), (ax - (b0 + .1 - ay), ay), (-(ax - (b0 + .1 - ay)), ay)], u, t))
    rd = K['ridge']; c = rd['crest_y_mm']; zc = rd['crest_z_mm']; base_z = rd['base_z_mm']; run_p = zc - base_z
    pieces.append(prism_yz([(max(c - run_p, y0), base_z + max(0., y0 - (c - run_p))), (c, zc), (c + run_p, base_z), (max(c - run_p, y0), base_z)], -kx, kx))
    near0, near1 = s['near_band_y_mm']; far0, far1 = s['far_band_y_mm']
    near, L, nr = base.arrow_ring(near0, near1, +1, s['clip_width_mm'], P['rod']['sensor_clip_root_wall']); far = base.ring((far0 + far1) / 2, None, s['clip_width_mm'], P['rod']['sensor_clip_root_wall'])
    end = nr[1] + .3; wide = a['saddle_max_half_width_mm']
    pieces.append(mf.Manifold.batch_hull([saddle_xz(kx, kz1, a['saddle_bottom_z_mm'], near0, end), saddle_xz(kx, kz1, a['saddle_bottom_z_mm'], near0, end + (wide - kx), max_half=kx + .01)]))
    shape = union(pieces) - base.corridor(); shape = shape + near + far; shape -= base.gap_cut(*nr); shape -= base.gap_cut(far0, far1)
    g = r['groove']; p = r['post']
    for sign in (1, -1):
        xr = lambda a_, b_: (min(sign * a_, sign * b_), max(sign * a_, sign * b_))
        shape -= box(*xr(9., g['back_x_mm']), p['full_y_mm'][0] - 1., g['closed_end_y_mm'], g['floor_z_mm'], g['ceiling_z_mm'])
        shape -= box(*xr(9., g['lip_inner_x_mm']), p['full_y_mm'][0] - 1., p['lead_end_y_mm'] + 1., g['ceiling_z_mm'] - .01, p['top_z_mm'] + 1.)
    return base.clean(shape, 'XIAO_Rod_Holder')


def keeper(flexed=False):
    """Flat slide-in bar: ears in rigid grooves, broad paws over bare corners, one sprung tooth inside the outline."""
    r = RET; (tx0, tx1), (ty0, ty1) = r['tab_x_mm'], r['tab_y_mm']; (fx0, fx1), tip, root = r['finger_x_mm'], r['finger_tip_y_mm'], r['finger_root_y_mm']; z0, z1 = r['plate_z_mm']; f = K['front_y_mm']; bar = K['bar_y_mm']; ap = K['rear_apex_y_mm']; T = K['tongue']
    plan = [mf.CrossSection([base.ccw([(-tx0 - .1, bar[0]), (0, ap), (tx0 + .1, bar[0]), (tx0 + .1, bar[1]), (fx1, bar[1]), (fx1, f), (-fx1, f), (-fx1, bar[1]), (-tx0 - .1, bar[1])])])]
    for sign in (1, -1):
        a, b = sorted([sign * tx0, sign * tx1]); plan.append(rect(a, b, ty0, ty1)); a, b = sorted([sign * fx0, sign * fx1]); plan.append(rect(a, b, root, tip))
    outline = mf.CrossSection.batch_boolean(plan, mf.OpType.Add).offset(.3, mf.JoinType.Round).offset(-.6, mf.JoinType.Round).offset(.3, mf.JoinType.Round)
    (rt_, tp), (ty, ty_), sl = T['x_mm'], T['y_mm'], T['slit_mm']; front = rect(fx0 - .05, fx1, f, tip + 1);
    outline = outline - rect(rt_, tp + sl, ty - sl, ty) - rect(tp, tp + sl, ty - sl, f + 1)
    solid = mf.Manifold.extrude(outline, z1 - z0).translate((0, 0, z0)); solid -= box(rt_, tp, ty, f + 1, z0 - .1, T['thin_from_z_mm'])
    if not flexed:
        (a, b), (c, d), e = T['tooth_x_mm'], T['tooth_y_mm'], T['tooth_bottom_z_mm']; solid += box(a, b, c, d, e, T['thin_from_z_mm'] + .05)
    return base.clean(solid, 'XIAO_Near_Keeper')


h17.battery_module = battery_module; h17.battery_gate = battery_door; h17.sensor_holder = sensor_holder; h17.retainer = keeper


def part_shapes():
    return {'Battery_Holder': battery_module(), 'Battery_End_Door': battery_door(), 'XIAO_Rod_Holder': sensor_holder(), 'XIAO_Near_Keeper': keeper(), **{n: spacer(t) for n, t in SPACERS.items()}}


def board_outline(*a, **k): return h17.board_outline(*a, **k)
def board_travel(): return h17.board_travel()
def reachable_poses(n=5): return h17.reachable_poses(n)
def component_box(*a, **k): return h17.component_box(*a, **k)
def pad_rows(): return h17.pad_rows()
def board_y(v): return h17.board_y(v)
def battery_position(extra=0.): return h17.battery_position(extra)
def xiao_position(extra=0.): return h17.xiao_position(extra)


def regions(name):
    if name in ('Battery_Holder', 'XIAO_Rod_Holder'):
        return {k: v for k, v in h17.regions(name).items() if 'detent' not in k and 'spring' not in k}
    if name == 'XIAO_Near_Keeper':
        (a, b), (c, d), sl = K['tongue']['x_mm'], K['tongue']['y_mm'], K['tongue']['slit_mm']; z0, z1 = RET['plate_z_mm']
        return {'tongue_slit': box(a + .05, b + sl - .05, c - sl + .05, c - .05, z0 - 1, z1 + 1)}
    if name == 'Battery_End_Door':
        y0, y1 = D['y_mm']; t1 = D['tongue_z_mm'][1]; sl = D['slit_mm']
        return {'tongue_slit': box(D['tongue_root_x_mm'] + .05, D['window_x_mm'][0] - .05, y0 - 1, y1 + 1, t1 + .05, t1 + sl - .05)}
    return {}


def to_print(shape, name):
    m = mesh(shape)
    if name == 'XIAO_Near_Keeper': rot = trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])
    elif name == 'Battery_End_Door': rot = trimesh.transformations.rotation_matrix(math.radians(90), [1, 0, 0])
    elif name.startswith('Battery_Spacer'): rot = np.eye(4)
    else: rot = trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    o = m.copy(); o.apply_transform(rot); shift = trimesh.transformations.translation_matrix(-o.bounds[0]); o.apply_transform(shift)
    return m, o, shift @ rot


def export():
    out = HERE / 'exports'; out.mkdir(exist_ok=True); records = {}; shapes = part_shapes()
    for name in PLATE:
        shape = shapes[name].simplify(.0001); m, o, tf = to_print(shape, name); assert m.is_watertight and len(shape.decompose()) == 1, name
        m.export(out / (name + '-assembly.stl'))
        normal = mf.Manifold(mf.Mesh(np.asarray(np.round(o.vertices, 6), np.float32), np.asarray(o.faces, np.uint32))).simplify(.000001); assert normal.status() == mf.Error.NoError, name
        mesh(normal).export(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); final = trimesh.load_mesh(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); assert final.is_watertight, name
        records[name] = {'bounds_mm': m.bounds.tolist(), 'volume_mm3': m.volume, 'solid_PETG_g': m.volume / 1000 * base.r15.P['print']['density_g_cm3'], 'print_height_mm': float(final.bounds[1][2]), 'body_count': 1, 'watertight': True, 'stl_sha256': sha(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')), 'print_to_assembly': np.linalg.inv(tf).tolist()}
    r16 = json.loads((R16 / 'exports/manifest.json').read_text())
    manifest = {'revision': LOCAL['revision'], 'source_sha256': {os.path.relpath(p, HERE): sha(p) for p in [HERE / 'holder18.py', HERE / 'parameters.json', R17 / 'holder17.py', R17 / 'parameters.json', R16 / 'holder16.py', R16 / 'spaces16.py', R16 / 'parameters.json']}, 'parts': records, 'unchanged_from_r16': {'Key_Carrier': r16['parts']['Key_Carrier']['stl_sha256']}, 'plate_parts': PLATE, 'physical_fit_verified': False, 'physical_strength_verified': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print({n: (round(v['solid_PETG_g'], 2), round(v['print_height_mm'], 1)) for n, v in records.items()}, flush=True)


if __name__ == '__main__':
    export()
