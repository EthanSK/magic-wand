#!/usr/bin/env python3
"""R23: hybrid centre key. The lower-middle Choc seat of the exported R22 Key_Carrier becomes a slide-in seat for
the stock OP1 socket board (switch plugged in), with a rounded paddle on a 1.75 mm filament hinge pin.

Composition: the R22 Key_Carrier assembly mesh is read unchanged; R23 adds a local fill, barrel guard tub and two
hood cheeks, then cuts the board channel, barrel pocket and hinge bores. The four other keys and the rod rings
retain the R22 geometry. The six guard runners are grown along their R22 paths with a larger rounded section.
All board/switch/plug sizes are photo/catalogue envelopes (parameters.json) for the first fit trial.
Paddle geometry is modelled at the hard-stop pose; paddle_pose(angle) rotates it about the hinge (positive lifts
the rear edge). Nothing here is a physical fit, comfort, force or strength result.
"""
import sys
sys.dont_write_bytecode = True
from functools import lru_cache
from pathlib import Path
import json, math, hashlib
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
R22 = HERE.parent / 'carbon-rod-holders-r22-integrated-guard'
sys.path.insert(0, str(R22))
import holder22 as h22  # noqa: E402

base = h22.base
L = json.loads((HERE / 'parameters.json').read_text())
B, S, Y, H, HG, PD = L['stock_board_estimate'], L['switch_estimate'], L['layout'], L['hood'], L['hinge'], L['paddle']
OUT = HERE / 'exports'
SLAB_TOP = base.plate_top()            # 11.12
SLAB_BOTTOM = base.slab_bottom()       # 7.27
CORRIDOR = base.CORRIDOR               # 4.2


def box(x0, x1, y0, y1, z0, z1): return mf.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
def union(items): return mf.Manifold.batch_boolean(list(items), mf.OpType.Add)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh(m): return h22.mesh(m)
def vol(m): return float(m.volume())


def prism_yz(points, x0, x1):
    """Extrude a (y, z) polygon along X from x0 to x1."""
    sec = mf.CrossSection([base.ccw(points)])
    return mf.Manifold.extrude(sec, x1 - x0).transform(((0, 0, 1, x0), (1, 0, 0, 0), (0, 1, 0, 0)))


def bar_x(r, x0, x1, y, z, n=48): return mf.Manifold.cylinder(x1 - x0, r, r, n).rotate((0, 90, 0)).translate((x0, y, z))


def teardrop_x(r, x0, x1, y, z, peak):
    """Bore along X; its roof ends in a 45-degree peak towards `peak` (unit (dy, dz)) so it prints without a bridge."""
    phi = math.atan2(peak[1], peak[0]); d = r * math.sqrt(2)
    pts = [(y + r * math.cos(phi + q), z + r * math.sin(phi + q)) for q in (math.pi / 4, -math.pi / 4)]
    tri = prism_yz([pts[0], (y + d * math.cos(phi), z + d * math.sin(phi)), pts[1], (y, z)], x0, x1)
    return bar_x(r, x0, x1, y, z) + tri


# ---------------------------------------------------------------------------
# Stock hardware envelopes (assembly frame, seated)
# ---------------------------------------------------------------------------
YC = Y['middle_contact_y_mm']; ZB = Y['board_bottom_z_mm']; ZT = ZB + B['thickness_mm']
BOARD_REAR = YC + B['middle_contact_to_short_end_mm']; BOARD_FRONT = YC - B['middle_contact_to_connector_end_mm']
SW_HALF_X, SW_LEN, SW_H = S['body_mm'][0] / 2, S['body_mm'][1], S['body_mm'][2]
HOUSING_TOP = ZT + SW_H
PLUNGER_FREE = HOUSING_TOP + S['plunger_free_above_body_mm']
STOP_PLUNGER = PLUNGER_FREE - PD['plunger_depression_at_stop_mm']


def board(): w = B['width_envelope_mm'] / 2; return box(-w, w, BOARD_FRONT, BOARD_REAR, ZB, ZT)


def barrels():
    r = B['socket_barrel_envelope_diameter_mm'] / 2; p = B['socket_barrel_protrusion_below_board_mm']
    return union([mf.Manifold.cylinder(p + .01, r, r, 32).translate((0, YC + k * B['socket_pitch_mm'], ZB - p)) for k in (-1, 0, 1)])


def switch(lift=0.):
    body = box(-SW_HALF_X, SW_HALF_X, YC - SW_LEN / 2, YC + SW_LEN / 2, ZT + lift, HOUSING_TOP + lift)
    pw = S['plunger_width_x_mm'] / 2
    plunger = box(-pw, pw, YC - 1.2, YC + 1.2, HOUSING_TOP + lift - .01, PLUNGER_FREE + lift)
    return body, plunger


def plug():
    e = B['plug_envelope']; w = e['across_mm'] / 2
    return box(-w, w, BOARD_FRONT + e['along_board_mm'][0], BOARD_FRONT + e['along_board_mm'][1], ZB - e['below_board_mm'], ZB)


def cable_points():
    """Stated route: out of the plug along -Y, down the left of the rod and back along R22's external wire bus."""
    y0 = BOARD_FRONT + B['plug_envelope']['along_board_mm'][0]
    return [(0., y0, 6.9), (-1.5, y0 - 2.6, 6.6), (-4.6, y0 - 3.6, 5.0), (-7.0, y0 - 2.6, 2.6), (-7.0, y0 + 1.5, 2.0), (-7.0, -12.0, 2.0)]


def cable():
    r = B['cable_bundle_diameter_mm'] / 2; pts = cable_points(); segs = []
    for a, b in zip(pts, pts[1:]):
        segs.append(mf.Manifold.batch_hull([mf.Manifold.sphere(r, 24).translate(a), mf.Manifold.sphere(r, 24).translate(b)]))
    return union(segs)


def hinge_pin(): return bar_x(1.75 / 2, -H['cheek_x_mm'][1] - .3, H['cheek_x_mm'][1] + .3, HG['axis_y_mm'], HG['axis_z_mm'])


# ---------------------------------------------------------------------------
# Carrier
# ---------------------------------------------------------------------------
def r22_carrier(): return h22.read(R22 / 'exports/Key_Carrier-assembly.stl')


def rod_corridor(): return mf.Manifold.cylinder(140, CORRIDOR, CORRIDOR, 96).rotate((-90, 0, 0)).translate((0, 70, 0))


def cheek(sign):
    x0, x1 = H['cheek_x_mm']; f = H['cheek_front_y_mm']; zb = H['cheek_bottom_z_mm']; zt = H['cheek_top_z_mm']; y0 = -7.8
    # Top rises 45 degrees forward from the slab top (print up is -Y).
    rise_end = -8.3 - (zt - SLAB_TOP)
    pts = [(y0, zb), (y0, SLAB_TOP), (-8.3, SLAB_TOP), (rise_end, zt), (f, zt), (f, zb)]
    lo, hi = (x0, x1) if sign > 0 else (-x1, -x0)
    return prism_yz(pts, lo, hi)


def additions():
    fx, ft = Y['fill_half_x_mm'], Y['fill_top_z_mm']; tx = Y['guard_tub_half_x_mm']; fz = Y['guard_floor_z_mm'][0]
    # Fill the old Choc bay and its under-plate clip relief (|x| 7.8) up to the slab top; only the lips rise above it.
    fill = box(-7.9, 7.9, -8.3, 7.3, SLAB_BOTTOM, SLAB_TOP) + box(-fx, fx, -8.3, 9.0, SLAB_BOTTOM, SLAB_TOP) \
        + box(-fx, fx, -8.3, 9.0, SLAB_TOP - .01, ft)   # stops short of the upper sockets' routes (Y 9.5) and flanges (Y 10.3); R22 slab carries the rest
    # Barrel guard tub under the bay; its rear underside climbs at 45 degrees into the slab so it prints.
    tub = prism_yz([(-7.9, fz), (5.8, fz), (5.8 + (SLAB_BOTTOM + .1 - fz), SLAB_BOTTOM + .1), (-7.9, SLAB_BOTTOM + .1)], -tx, tx)
    return union([fill, tub, cheek(1), cheek(-1)])


def cuts():
    cx, lx, lz = Y['channel_half_x_mm'], Y['lip_inner_half_x_mm'], Y['lip_underside_z_mm']; rear = Y['channel_rear_y_mm']; px = Y['barrel_pocket_half_x_mm']
    chan = box(-cx, cx, -40, rear, ZB, lz) + box(-lx, lx, -40, rear, lz - .01, 40)
    pocket = box(-px, px, -40, 5.8, Y['guard_floor_z_mm'][1], ZB + .01)
    bores = teardrop_x(HG['bore_diameter_mm'] / 2, -H['cheek_x_mm'][1] - 1, H['cheek_x_mm'][1] + 1, HG['axis_y_mm'], HG['axis_z_mm'], (-1, 0))
    return union([chan, pocket, bores, rod_corridor()])


@lru_cache(maxsize=1)
def key_carrier():
    import guard23
    # Thicker R22 runners (same paths), then R22's working spaces re-carved so every Choc route stays as checked.
    grown = r22_carrier() + guard23.runners()
    carved = h22.spaces16.carve(grown, h22.carrier_regions(), 'carrier23:runners')
    solid = (carved + additions()) - cuts()
    return base.clean(solid, 'Key_Carrier_R23')


def export_guard_members():
    import guard23
    rec = {}
    for name, (solid, stats, areas) in guard23.members().items():
        path = OUT / 'guide' / f'guard_runner_{name}.stl'; mesh(solid).export(path)
        rec[name] = {'file': 'guide/' + path.name, 'volume_mm3': round(solid.volume(), 3), 'growth': stats,
                     'min_layer_section_mm2': min(a for _, a in areas), 'layers': len(areas), 'y_span_mm': [areas[-1][0], areas[0][0]]}
    rec['r22_min_section_mm2'] = guard23.r22_runner_sections()
    rec['carve_log'] = h22.spaces16.CARVE_LOG.get('carrier23:runners')
    (OUT / 'guard-members.json').write_text(json.dumps(rec, indent=2, default=str) + '\n')
    return rec


# ---------------------------------------------------------------------------
# Paddle (modelled at the hard-stop pose)
# ---------------------------------------------------------------------------
def rounded_plate(hx, y0, y1, z0, z1, r_plan=2.0, r_top=PD['top_round_mm'], steps=6):
    sec = mf.CrossSection.square((2 * hx, y1 - y0)).translate((-hx, y0)).offset(-r_plan, mf.JoinType.Round, 2., 48).offset(r_plan, mf.JoinType.Round, 2., 48)
    pieces = [mf.Manifold.extrude(sec, z1 - r_top - z0).translate((0, 0, z0))]
    for i in range(1, steps + 1):
        lo, hi = z1 - r_top + r_top * (i - 1) / steps, z1 - r_top + r_top * i / steps
        e = r_top - math.sqrt(max(r_top ** 2 - (hi - (z1 - r_top)) ** 2, 0.))
        pieces.append(mf.Manifold.extrude(sec.offset(-min(e, r_top - .02), mf.JoinType.Round, 2., 48), hi - lo).translate((0, 0, lo)))
    return union(pieces)


@lru_cache(maxsize=4)
def paddle(offset=0.):
    hx = PD['half_x_mm']; y0, y1 = PD['y_mm']; z0, z1 = PD['plate_z_mm']; ax0, ax1 = HG['paddle_arm_x_mm']; yh, zh = HG['axis_y_mm'], HG['axis_z_mm']
    plate = rounded_plate(hx, y0, y1, z0, z1)
    sx0, sx1 = PD['skirt_x_mm']; sy0, sy1 = PD['skirt_y_mm']; zs = PD['stop_surface_z_mm']
    skirts = union([box(s * sx0 if s > 0 else -sx1, sx1 if s > 0 else -sx0, sy0, sy1, zs, z0 + .2) for s in (1, -1)])
    arms = union([box(ax0 if s > 0 else -ax1, ax1 if s > 0 else -ax0, yh - 2.4, yh + 2.4, zh - 2.2, z0 + .2) for s in (1, -1)])
    rx = PD['ridge_half_x_mm']; ry0, ry1 = PD['ridge_y_mm']; rz = STOP_PLUNGER - offset
    ridge = box(-rx, rx, ry0, ry1, rz, z0 + .2)
    shape = plate + skirts + arms + ridge
    # Pin bore: the paddle prints top-down, so its print 'up' is assembly -Z; the bore roof peaks that way.
    shape -= teardrop_x(HG['bore_diameter_mm'] / 2, -hx - 1, hx + 1, yh, zh, (0, -1))
    return base.clean(shape, 'Centre_Paddle')


def pose_matrix(angle_deg):
    """3x4 affine: rotate about the hinge axis (X through (axis_y, axis_z)); positive lifts the paddle's rear edge."""
    a = math.radians(angle_deg); c, s = math.cos(a), math.sin(a); yh, zh = HG['axis_y_mm'], HG['axis_z_mm']
    Rm = np.array([[1, 0, 0], [0, c, -s], [0, s, c]]); t = np.array([0, yh, zh]) - Rm @ np.array([0, yh, zh])
    return np.hstack([Rm, t[:, None]])


def paddle_pose(angle_deg, offset=0.): return paddle(offset).transform(pose_matrix(angle_deg).tolist())


def lift_at(y, z, angle_deg):
    m = pose_matrix(angle_deg); return float((m @ np.array([0, y, z, 1.]))[2] - z)


def named_poses(offset=0.):
    """Angles (degrees) of the stated motion, from the nominal plunger at the middle contact."""
    yp, zp = YC, STOP_PLUNGER - offset
    def angle_for(dz):
        lo, hi = 0., 10.
        for _ in range(60):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if lift_at(yp, zp, mid) < dz else (lo, mid)
        return (lo + hi) / 2
    dep = PD['plunger_depression_at_stop_mm'] + offset
    pt = .3  # Omron D2F-class catalogue nominal pretravel; the actual OP1 switch value is unknown
    return {'released': angle_for(dep + PD['released_gap_mm']), 'rest_on_plunger': angle_for(dep), 'actuation_nominal': angle_for(dep - pt), 'hard_stop': 0.}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
PRINT_ROT = {'Key_Carrier': trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0]),   # R22 orientation: rear face on the bed
             'Centre_Paddle': trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])}           # top face on the bed


def write_checked_stl(model, path, shape, to_assembly):
    # Rounding at STL export can collapse seam triangles on the new cheeks.
    # Normalize on the written coordinate grid and check both saved frames.
    rounded = mf.Mesh(np.asarray(np.round(model.vertices, 6), np.float32),
                      np.asarray(model.faces, np.uint32))
    normal = mf.Manifold(rounded).simplify(.000001)
    assert normal.status() == mf.Error.NoError, (path.name, normal.status())
    mesh(normal).export(path)
    written = trimesh.load_mesh(path)
    returned = h22.read(path).transform(to_assembly[:3, :])
    drift = vol(returned - shape) + vol(shape - returned)
    assert written.is_watertight and len(returned.decompose()) == 1 and drift < .02, (path.name, drift)
    return written, round(drift, 6)


def export_part(name, shape, rot_key):
    shape = shape.simplify(.0001)
    model = mesh(shape)
    assembly = OUT / (name + '-assembly.stl')
    source = OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')
    m, assembly_drift = write_checked_stl(model, assembly, shape, np.eye(4))
    o = model.copy()
    rotation = PRINT_ROT[rot_key]
    o.apply_transform(rotation)
    translation = trimesh.transformations.translation_matrix(-o.bounds[0])
    o.apply_transform(translation)
    to_assembly = np.linalg.inv(translation @ rotation)
    back, print_drift = write_checked_stl(o, source, shape, to_assembly)
    return {'volume_mm3': round(m.volume, 3), 'solid_PETG_g': round(m.volume / 1000 * 1.27, 3), 'assembly_bounds_mm': np.round(m.bounds, 3).tolist(),
            'print_height_mm': round(float(back.bounds[1][2]), 3), 'stl_sha256': sha(source),
            'assembly_stl_sha256': sha(assembly), 'print_to_assembly': to_assembly.tolist(),
            'assembly_export_drift_mm3': assembly_drift, 'print_export_drift_mm3': print_drift}


def references():
    body, plg = switch()
    return {'op1_board_envelope': board(), 'op1_socket_barrels': barrels(), 'op1_switch_body': body, 'op1_switch_plunger_free': plg,
            'op1_white_plug_envelope': plug(), 'op1_pigtail_route': cable(), 'hinge_pin_1p75_filament': hinge_pin(), 'rod_y': base.references()['rod']}


def export():
    OUT.mkdir(exist_ok=True); (OUT / 'guide').mkdir(exist_ok=True); parts = {}
    parts['Key_Carrier'] = export_part('Key_Carrier', key_carrier(), 'Key_Carrier')
    export_guard_members()
    for name, off in PD['variants'].items(): parts[name] = export_part(name, paddle(off), 'Centre_Paddle')
    refs = {}
    for k, v in references().items(): mesh(v).export(OUT / 'guide' / (k + '.stl')); refs[k] = 'guide/' + k + '.stl'
    motion = {'schema': 'r23-centre-motion-1', 'units': 'mm/degrees',
              'axis': {'point_mm': [0, HG['axis_y_mm'], HG['axis_z_mm']], 'direction': [1, 0, 0], 'positive': 'lifts the rear edge'},
              'modelled_pose': 'hard_stop (angle 0)',
              'variants': {n: {'poses_deg': {k: round(a, 4) for k, a in named_poses(o).items()},
                               'matrices_3x4': {k: np.round(pose_matrix(a), 6).tolist() for k, a in named_poses(o).items()}} for n, o in PD['variants'].items()},
              'press_sequence': ['released', 'rest_on_plunger', 'actuation_nominal', 'hard_stop', 'actuation_nominal', 'rest_on_plunger', 'released'],
              'basis': 'Plunger depression at the stop is set by the ridge height, independent of where the plunger sits along the body. Released gap is a design value; pretravel 0.3 mm is the Omron D2F-class nominal, not the OP1 switch. There is no separate up-stop: at rest the paddle lies on the plunger.',
              'references': refs, 'physical_travel_verified': False}
    (OUT / 'centre-motion.json').write_text(json.dumps(motion, indent=2) + '\n')
    man = {'revision': L['revision'], 'parts': parts, 'r22_key_carrier_assembly_sha256': sha(R22 / 'exports/Key_Carrier-assembly.stl'),
           'source_sha256': {name: sha(HERE / name) for name in ('holder23.py', 'guard23.py', 'parameters.json')},
           'unchanged_r22_parts': 'Battery_Holder, Battery_End_Door, Battery_End_Door_Easy_Trial, XIAO_Rod_Holder, XIAO_Near_Keeper, Cable_Clip_12_Wire: use the R22 exports.',
           'loose_hardware': ['1.75 mm filament offcut ~22 mm as the hinge pin', 'optional tape across the board front onto the cheeks'],
           'physical_fit_verified': False}
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=2) + '\n')
    from assembly23 import build
    build(sys.modules[__name__])
    print(json.dumps(parts, indent=1), flush=True)


if __name__ == '__main__':
    import holder23
    holder23.export()
