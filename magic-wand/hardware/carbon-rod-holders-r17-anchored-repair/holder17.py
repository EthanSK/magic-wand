#!/usr/bin/env python3
"""R17 repair: continuous battery channel, wider XIAO holder with over-top retainer, base anchors.

Composes the frozen R16 chain. Key_Carrier is unchanged from R16. New here: the battery U-channel,
the sprung end gate, the XIAO holder and its removable top plate. Removable bed anchors are separate
labelled meshes (anchors17.py), never merged into a functional part.
"""
from functools import lru_cache
from pathlib import Path
import json
import math
import os
import sys
import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
R16 = HERE.parent / 'carbon-rod-holders-r16-repair'
sys.path.insert(0, str(R16))
import holder16 as base  # noqa: E402
import spaces16  # noqa: E402

LOCAL = json.loads((HERE / 'parameters.json').read_text())
P = base.P
box, rr, cyl, union, mesh, sha = base.box, base.rr, base.cyl, base.union, base.mesh, base.sha
prism_xz, prism_xy, bar_xz, saddle_xz = base.prism_xz, base.prism_xy, base.bar_xz, base.saddle_xz
CAGE = {**P['cage'], **LOCAL['cage']}
S = {**P['sensor'], **LOCAL['sensor']}
RET = LOCAL['retainer']
GATE = LOCAL['gate']
WIRE = LOCAL['wire_exit']
INSERTION = LOCAL['insertion']
XO = LOCAL['xiao_official_mm']
BZ = base.SENSOR['board_z']
BT = S['board_thickness_mm']
BOARD_TOP = BZ + BT
NEW_PARTS = ['Battery_Holder', 'Battery_End_Gate', 'XIAO_Rod_Holder', 'XIAO_Top_Retainer']
UNCHANGED = ['Key_Carrier']
REDESIGNED_GATE = 'Battery_End_Gate'
PLATE = ['Battery_Holder', 'Battery_End_Gate', 'XIAO_Rod_Holder', 'XIAO_Top_Retainer']


def prism_yz(points, x0, x1):
    """Extrude an outline given as (y, z) points along X."""
    solid = mf.Manifold.extrude(mf.CrossSection([base.ccw(points)]), x1 - x0)
    # extrude axes (u, v, w) -> (x, y, z) = (w + x0, u, v); a proper rotation.
    return solid.transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float))


class PoseSweep(spaces16.Swept):
    """A solid in several rigid poses given as 3x4 matrices; checked pose by pose, never unioned."""
    def __init__(self, solid, matrices):
        self.solid = solid; self.matrices = [np.asarray(m, float) for m in matrices]; self.offsets = np.zeros((len(self.matrices), 3)); self._box = None

    def __len__(self):
        return len(self.matrices)

    def poses(self):
        for m in self.matrices:
            yield self.solid.transform(m)

    def subtract_from(self, target):
        met = 0
        for pose in self.poses():
            if (target ^ pose).volume() > 1e-6: met += 1
            target = target - pose
        return target, met


# ---------------------------------------------------------------------------
# Battery: one connected wall loop per layer instead of an open lattice
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def battery_module():
    c = CAGE; lv = base.cage_levels(); a = P['arrow_ring']
    xi, xo = c['side_rail_x_mm']; fb, ft, rb, rt = lv['floor_bottom'], lv['floor_top'], lv['roof_bottom'], lv['roof_top']
    near0, near1 = c['near_band_y_mm']; far0, far1 = c['far_band_y_mm']
    guide_y0, guide_y1 = c['guide_y_mm']; start = c['wall_start_y_mm']; flange = c['roof_flange_inner_x_mm']
    sp, sd = c['spine_half_x_mm'], c['saddle_half_x_mm']
    # Floor: 1.2 mm over most of the width, the full 1.65 mm along the central load path to the rings.
    thin = ft - c['floor_thin_mm']; keel = c['floor_full_half_x_mm']
    pieces = [box(-xo, xo, guide_y0, far1, thin, ft), box(-keel, keel, guide_y0, far1, fb, ft), box(-sp, sp, near0, far1, fb, ft), box(-sd, sd, far0 - .5, far1, fb, ft)]
    for sign in (1, -1):
        x0, x1 = sorted([sign * xi, sign * xo]); f0, f1 = sorted([sign * flange, sign * xo])
        pieces.append(box(x0, x1, start, far1, thin, rt))
        pieces.append(box(f0, f1, start, far1, rb, rt))
        # Gate guides, led in at 45 degrees from the side wall exactly as R16.
        g0, g1 = c['guide_x_mm']
        lead = box(x0, x1, guide_y1, guide_y1 + (g1 - g0 - (xo - xi)), fb, rt)
        block = box(min(sign * g0, sign * g1), max(sign * g0, sign * g1), guide_y0, guide_y1, fb, rt)
        pieces.append(mf.Manifold.batch_hull([lead, block]))
        s0, s1 = c['stop_block_x_mm']
        pieces.append(box(min(sign * s0, sign * s1), max(sign * s0, sign * s1), lv['half_l'], c['end_plate_y_mm'][0] + .1, ft, ft + P['cell']['manufacturer_max_mm']['thickness']))
    e0, e1 = c['end_plate_y_mm']
    plate = box(-xo, xo, e0, e1, fb, rt)
    plate -= prism_xz([(-4.2, 6.6), (4.2, 6.6), (4.2, 9.4), (0, 11.4), (-4.2, 9.4)], e0 - 1, e1 + 1)
    pieces.append(plate)
    shape = union(pieces) ^ box(-30, 30, near0, far1, -20, 30)
    ch = c['flange_lead_chamfer_mm']
    for sign in (1, -1):
        # Rounded-off flange entry and inner edge so an inserted cell cannot catch on them.
        fx = sign * flange
        shape -= prism_xz([(fx, rb - .01), (fx + sign * ch, rb - .01), (fx, rb + ch)], start - 1, c['end_plate_y_mm'][0])
        x0, x1 = sorted([sign * flange, sign * xi])
        shape -= prism_yz([(start - .01, rb - .01), (start + ch, rb - .01), (start - .01, rb + ch)], x0, x1)
    sx = c['slot_x_centre_mm']; sw = c['slot_width_mm']; sy0, sy1 = c['gate_slot_y_mm']; wall_x = sx + sw / 2
    (rx, ry), ry1 = c['cap_ramp_start_xy_mm'], c['cap_ramp_end_y_mm']; lo_z = ft + .35; G = GATE
    for sign in (1, -1):
        shape -= box(min(0, sign * wall_x), max(0, sign * wall_x), sy0, sy1, lo_z, rt + 2)
        # The slot closes with a 45-degree ramp grown from the outer wall, not a flat patch over air.
        run = ry - ry1
        ramp = [(0, sy0 + .2), (sign * rx, sy0 + .2), (sign * rx, ry), (sign * (rx - run), ry1), (sign * (rx - run), ry1 - .6), (0, ry1 - .6)]
        shape -= base.prism_xy(ramp, lo_z, rt + 2)
        # Detent notch in the outer wall of the slot.
        dz = G['detent_z_mm']; depth = G['notch_depth_mm']
        notch = [(sign * (wall_x - .05), dz - .95), (sign * wall_x, dz - .9), (sign * (wall_x + depth), dz - .4), (sign * (wall_x + depth), dz + .4), (sign * wall_x, dz + .9), (sign * (wall_x - .05), dz + .95)]
        shape -= prism_xz(notch, sy0, sy1)
    # Shallow chevrons on the outside faces, cut after the walls are joined.
    ch_cfg = c['chevron']; d_ = ch_cfg['depth_mm']; hh = ch_cfg['half_height_mm']; run_ = ch_cfg['run_mm']; bd = ch_cfg['band_mm']; zc = ch_cfg['centre_z_mm']
    for ay in ch_cfg['apex_y_mm']:
        arm_up = [(ay, zc), (ay - run_, zc + hh), (ay - run_ - bd, zc + hh), (ay - bd, zc), (ay - run_ - bd, zc - hh), (ay - run_, zc - hh)]
        for sign in (1, -1):
            x0, x1 = sorted([sign * xo, sign * (xo - d_)])
            shape -= prism_yz(arm_up, x0 if sign > 0 else x0 - .01, x1 + .01 if sign > 0 else x1)
    near, L, near_range = base.arrow_ring(near0, near1, +1, P['rod']['ring_width'])
    far = base.ring((far0 + far1) / 2, None, P['rod']['ring_width'])
    end = near_range[1] + .3
    pieces_saddle = mf.Manifold.batch_hull([box(-sd, sd, near0, end, fb, ft), box(-sp, sp, near0, end + (sd - sp), fb, ft)])
    saddle = mf.Manifold.batch_hull([saddle_xz(sd, fb + .3, a['saddle_bottom_z_mm'], near0, end),
                                     saddle_xz(sp, fb + .3, a['saddle_bottom_z_mm'], near0, end + (sd - sp), max_half=sp + .01)]) + pieces_saddle
    shape = (shape + saddle) - base.corridor()
    shape = shape + near + far
    shape -= base.gap_cut(*near_range)
    shape -= base.gap_cut(far0, far1)
    shape -= base.wire_bus(-80, 100)
    shape -= base.wire_bus(-80, 100).mirror((1, 0, 0))
    return base.clean(spaces16.carve(shape, spaces16.regions('Battery_Holder'), 'battery'), 'Battery_Holder')


def battery_gate(fitted=False):
    """End bar with a free leg each side. `fitted` drops the detent bumps, as when flexed past the wall."""
    c = P['cage']; G = GATE; lv = base.cage_levels(); y0, y1 = c['gate_y_mm']; lo = lv['floor_top'] + .5; hi = lo + 5.5; half = G['leg_half_width_mm']; pieces = []
    for sign in (1, -1):
        x = sign * c['slot_x_centre_mm']; outer = sign * (c['slot_x_centre_mm'] + half)
        pieces.append(prism_xz(base.rounded_rect_xz(x - half, x + half, lo, hi, .2), y0, y1))
        if not fitted:
            dz = G['detent_z_mm']; tip = sign * (c['slot_x_centre_mm'] + half + G['bump_height_mm'])
            pieces.append(prism_xz([(outer, dz - .7), (tip, dz - .15), (tip, dz + .15), (outer, dz + .7), (sign * (c['slot_x_centre_mm'] + .2), dz + .7), (sign * (c['slot_x_centre_mm'] + .2), dz - .7)], y0, y1))
        s0, s1 = c['gate_stub_x_mm']
        pieces.append(box(min(sign * s0, sign * s1), max(sign * s0, sign * s1), y0, y1, lv['floor_top'] + .4, lv['roof_bottom'] + .2))
    bar_z0 = lv['roof_bottom'] - .4; bar_z1 = hi + .4
    pieces.append(prism_xz(base.rounded_rect_xz(-c['slot_x_centre_mm'] - .6, c['slot_x_centre_mm'] + .6, bar_z0, bar_z1, .6), y0, y1))
    return union(pieces)


# ---------------------------------------------------------------------------
# XIAO holder and removable over-top retainer
# ---------------------------------------------------------------------------
def board_y(v):
    """Assembly Y of a board-centred v coordinate."""
    return S['board_near_end_y_mm'] + S['board_outline_mm']['length'] / 2 + v


def board_outline(dx=0., dy=0., thickness=BT):
    return base.board_outline(dx, dy, thickness=thickness, z0=BZ)


def board_travel():
    bo = S['board_outline_mm']; r = bo['corner_radius']; cx = bo['width'] / 2 - r
    lateral = S['rail_x_mm'][0] - bo['width'] / 2
    near = S['stop_clearance_mm'] * math.sqrt(2)
    # Far faces meet the rounded corners; on centre the arc has receded at the block's inner edge.
    xl = max(0., S['cradle_inner_x_mm'] - cx)
    far = S['far_stop_y_mm'] - (S['board_near_end_y_mm'] + bo['length'] - r + math.sqrt(r * r - xl * xl))
    return {'rail_lateral': lateral, 'near': near, 'far': far}


def reachable_poses(n=5):
    """Board poses inside the V and far stops. Sideways play is set by how far the board has moved
    away from the V, so the poses follow that boundary rather than the wider rail gap."""
    t = board_travel(); poses = []
    for dy in np.linspace(-(t['near'] - .1), t['far'] - .1, n):
        room = max(0., (dy + t['near']) - .1)
        for dx in np.linspace(-room, room, 3) if room > 1e-6 else [0.]:
            poses.append((float(dx), float(dy)))
    return poses


def component_box(name, grow=0.):
    c = XO['components'][name]; lo = BOARD_TOP - c.get('below_top', 0.)
    return box(c['u'][0] - grow, c['u'][1] + grow, board_y(c['v'][0]) - grow, board_y(c['v'][1]) + grow, lo, BOARD_TOP + c['h'] + grow)


def pad_zones():
    """Plan rectangles beside each castellation where solder and wire fillets can stand."""
    bo = S['board_outline_mm']; half = bo['width'] / 2; hv = XO['pad_land_half_v']; zones = []
    for v in XO['castellation_v_centres']:
        for sign in (1, -1):
            a, b = sorted([sign * (half - 1.8), sign * (half + S['side_allowance_mm'] - .2)])
            zones.append((a, b, board_y(v - hv), board_y(v + hv)))
    return zones


@lru_cache(maxsize=1)
def sensor_holder():
    s = S; a = P['arrow_ring']; z = BZ; rx0, rx1 = s['rail_x_mm']; rz0, rz1 = s['rail_z_mm']; y0, y1 = s['y_mm']
    bo = s['board_outline_mm']; yn = s['board_near_end_y_mm']; yf = yn + bo['length']; inner = s['cradle_inner_x_mm']
    zl = z - s['ledge_thickness_mm']; zs = z + s['stop_height_mm']; under_far = s['ledge_under_board_mm'][1]; tab_y0 = s['near_tab_y0_mm']
    limit = s['near_contact_limit_y_mm']; drop = s['lead_top_drop_mm']; lead_t = s['lead_thickness_mm']; ramp = s['ramp_length_mm']
    pieces = []
    for sign in (1, -1):
        xr = lambda p, q: (min(sign * p, sign * q), max(sign * p, sign * q))
        pieces.append(box(*xr(rx0, rx1), y0, y1, rz0, rz1))
        # Near cradle. Full-height contact only ahead of the first pad; behind it the 45-degree
        # lead that grows the ledge from the rail stays 0.5 mm under the board plane, clear of solder.
        pieces.append(box(*xr(inner, rx0 + .1), tab_y0, limit, zl, z))
        pieces.append(mf.Manifold.batch_hull([box(*xr(inner, rx0 + .1), limit - .01, limit, zl, z),
                                              box(*xr(inner, rx0 + .1), limit + ramp, limit + ramp + .01, z - drop - lead_t, z - drop)]))
        reach = rx0 - inner
        lead_top = z - drop; lead_bottom = lead_top - lead_t
        pieces.append(mf.Manifold.batch_hull([box(*xr(inner, rx0 + .1), limit + ramp, limit + ramp + .01, lead_bottom, lead_top),
                                              box(*xr(rx0, rx0 + .1), limit + ramp + reach, limit + ramp + reach + .01, lead_bottom, lead_top)]))
        # Near V stop, clipped ahead of the first pad; it engages the corner arc at about Y 1.65.
        face = base.near_stop_face(); clip = s['near_stop_clip_y_mm']
        px = min(rx0 + .1, clip - face(0.) if face(rx0 + .1) > clip else rx0 + .1)
        outline = [(sign * (rx0 + .1), clip), (sign * (rx0 + .1), tab_y0), (sign * inner, tab_y0), (sign * inner, face(inner)), (sign * px, clip)]
        pieces.append(prism_xy(outline, z, zs))
        pieces.append(box(*xr(inner, rx0 + .1), yf - under_far, y1, zl, z))
        pieces.append(box(*xr(inner, rx0 + .1), s['far_stop_y_mm'], y1, z, zs))
        # End bars, as R16 with the rail moved outward.
        (cx, cz), (bx, bz) = s['bar_crown_mm'], s['bar_rail_mm']
        fy0, fy1 = s['far_band_y_mm']; ny0, ny1 = s['near_band_y_mm']
        pieces.append(bar_xz(fy0, fy1, (sign * cx, cz), (sign * bx, bz), s['bar_width_mm']))
        flat = bar_xz(ny0, ny1, (sign * cx, cz), (sign * bx, bz), s['bar_width_mm'])
        gusset = bx - cx; hw = s['bar_width_mm'] / 2
        root = box(min(sign * (rx0 + .05), sign * bx), max(sign * (rx0 + .05), sign * bx), ny0, ny1 + gusset, bz - hw, bz + hw)
        root_tip = box(min(sign * rx0, sign * (rx0 + .05)), max(sign * rx0, sign * (rx0 + .05)), ny0, ny1 + gusset + (bx - rx0), bz - hw, bz + hw)
        pieces.append(mf.Manifold.batch_hull([flat, root, root_tip]))
        (ax, ay, az), (kx_, ky, kz) = s['strut_rail_mm'], s['strut_keel_mm']; hw = s['strut_width_mm'] / 2
        pieces.append(mf.Manifold.batch_hull([box(sign * ax - hw, sign * ax + hw, ay - hw, ay + hw, az - hw, az + hw),
                                              box(sign * kx_ - hw, sign * kx_ + hw, ky - hw, ky + hw, kz - hw, kz + hw)]))
        # Near end: a short post carrying the plate's groove, grown from the rail at 45 degrees, all ahead of the first pad.
        r = RET; p = r['post']; fy0, fy1 = p['full_y_mm']; outer = p['outer_x_mm']; top = p['top_z_mm']; lead = p['lead_end_y_mm']
        pieces.append(box(*xr(rx0, outer), fy0, fy1, rz0, top))
        pieces.append(mf.Manifold.batch_hull([box(*xr(rx0, outer), fy1 - .01, fy1, rz0, top), box(*xr(rx0, rx1), lead, lead + .01, rz0, rz1)]))
        # Far end: fixed fingers over the bare board corners, standing on the far stop and tied into the rail.
        f = r['far_finger']; (fx0, fx1), (fy, fyr), (fz0, fz1), (ry0, ry1) = f['x_mm'], f['y_mm'], f['z_mm'], f['root_y_mm']
        pieces.append(box(*xr(fx0, fx1), fy, fyr, fz0, fz1))
        pieces.append(box(*xr(fx0, fx1), ry0, ry1, z, fz1))
        pieces.append(box(*xr(rx0, fx1), fy, fyr, rz1 - .05, fz0 + .05))
    kx = s['keel_x_mm']; kz0, kz1 = s['keel_z_mm']
    pieces.append(box(-kx, kx, y0, y1, kz0, kz1))
    near0, near1 = s['near_band_y_mm']; far0, far1 = s['far_band_y_mm']
    near, L, near_range = base.arrow_ring(near0, near1, +1, s['clip_width_mm'], P['rod']['sensor_clip_root_wall'])
    far = base.ring((far0 + far1) / 2, None, s['clip_width_mm'], P['rod']['sensor_clip_root_wall'])
    end = near_range[1] + .3; wide = a['saddle_max_half_width_mm']
    pieces.append(mf.Manifold.batch_hull([saddle_xz(kx, kz1, a['saddle_bottom_z_mm'], near0, end),
                                          saddle_xz(kx, kz1, a['saddle_bottom_z_mm'], near0, end + (wide - kx), max_half=kx + .01)]))
    shape = union(pieces) - base.corridor()
    shape = shape + near + far
    shape -= base.gap_cut(*near_range)
    shape -= base.gap_cut(far0, far1)
    r = RET; g = r['groove']; p = r['post']; spring = r['spring']; yb = spring['bump_y_mm']; depth = spring['notch_depth_mm']
    for sign in (1, -1):
        xr = lambda a, b: (min(sign * a, sign * b), max(sign * a, sign * b))
        # Groove, open toward the near end and closed at its board end; the lip is the only material above the plate.
        shape -= box(*xr(9.0, g['back_x_mm']), p['full_y_mm'][0] - 1., g['closed_end_y_mm'], g['floor_z_mm'], g['ceiling_z_mm'])
        shape -= box(*xr(9.0, g['lip_inner_x_mm']), p['full_y_mm'][0] - 1., p['lead_end_y_mm'] + 1., g['ceiling_z_mm'] - .01, p['top_z_mm'] + 1.)
        back = g['back_x_mm']
        notch = [(sign * (back - .05), yb - .95), (sign * back, yb - .9), (sign * (back + depth), yb - .4), (sign * (back + depth), yb + .4), (sign * back, yb + .9), (sign * (back - .05), yb + .95)]
        shape -= base.prism_xy(notch, g['floor_z_mm'], g['ceiling_z_mm'])
    return base.clean(shape, 'XIAO_Rod_Holder')


def retainer_outline(fitted=False):
    """Plan of the plate in assembly XY. `fitted` drops the detent bumps, as when flexed past the groove wall."""
    r = RET; (tx0, tx1), (ty0, ty1) = r['tab_x_mm'], r['tab_y_mm']; (fx0, fx1), tip, root = r['finger_x_mm'], r['finger_tip_y_mm'], r['finger_root_y_mm']; cb = r['crossbar']
    rect = lambda x0, x1, y0, y1: mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
    rx, re, fe, shift = cb['rear_x'], cb['rear_edge_y_mm'], cb['front_edge_y_mm'], cb['apex_shift_mm']
    chevron = mf.CrossSection([base.ccw([(-rx, re), (0, re + shift), (rx, re), (rx, fe), (0, fe + shift), (-rx, fe)])])
    pieces = [chevron]
    for sign in (1, -1):
        a, b = sorted([sign * tx0, sign * tx1]); pieces.append(rect(a, b, ty0, ty1))
        a, b = sorted([sign * fx0, sign * fx1]); pieces.append(rect(a, b, root, tip))
    plan = mf.CrossSection.batch_boolean(pieces, mf.OpType.Add).offset(.3, mf.JoinType.Round).offset(-.6, mf.JoinType.Round).offset(.3, mf.JoinType.Round)
    spring = r['spring']; (sx0, sx1), (sy0, sy1) = spring['slit_x_mm'], spring['slit_y_mm']
    for sign in (1, -1):
        a, b = sorted([sign * sx0, sign * sx1]); plan = plan - rect(a, b, sy0, sy1)
        if not fitted:
            yb = spring['bump_y_mm']; top = sign * (tx1 + spring['bump_height_mm'])
            bump = [(sign * (tx1 - .4), yb - .7), (sign * tx1, yb - .7), (top, yb - .15), (top, yb + .15), (sign * tx1, yb + .7), (sign * (tx1 - .4), yb + .7)]
            plan = plan + mf.CrossSection([base.ccw(bump)])
    return plan


def retainer(fitted=False):
    r = RET; z0, z1 = r['plate_z_mm']; relief = r['first_layer_relief_mm']; plan = retainer_outline(fitted)
    upper = mf.Manifold.extrude(plan, z1 - z0 - relief).translate((0, 0, z0))
    bed_side = mf.Manifold.extrude(plan.offset(-relief, mf.JoinType.Round), relief).translate((0, 0, z1 - relief))
    return base.clean(upper + bed_side, 'XIAO_Top_Retainer')


def part_shapes():
    return {'Battery_Holder': battery_module(), 'Battery_End_Gate': battery_gate(), 'XIAO_Rod_Holder': sensor_holder(), 'XIAO_Top_Retainer': retainer()}


# ---------------------------------------------------------------------------
# Working spaces: one definition for checks against the CAD and against actual beads
# ---------------------------------------------------------------------------
def pad_rows():
    """(pin side sign, castellation centre Y, Y half width) for every side pad; +X is the 5V/GND/3V3/D10-D7 column."""
    return [(sign, board_y(v), WIRE['corridor_width_mm'] / 2) for v in XO['castellation_v_centres'] for sign in (1, -1)]


def wired_board():
    """The board plus a rigid root of solder and wire on every pad: the part of a wire that cannot simply bend away."""
    half = XO['outline']['width'] / 2; h_ = WIRE['stub_height_mm']; pieces = [board_outline()]
    for sign, y, hw in pad_rows():
        a, b = sorted([sign * (half - .8), sign * (half + .85)]); pieces.append(box(a, b, y - hw, y + hw, BZ - .4, BOARD_TOP + h_))
    return union(pieces)


def insertion_poses():
    """Tilt the near end up, slide the USB end under the far fingers, then rotate the near end down."""
    I = INSERTION; yf = S['board_near_end_y_mm'] + S['board_outline_mm']['length']; pivot = np.array([0., yf, BZ]); angle = math.radians(I['tilt_degrees']); rows = []
    def pose(theta, shift_y):
        c_, s_ = math.cos(theta), math.sin(theta)
        R = np.array([[1, 0, 0], [0, c_, -s_], [0, s_, c_]]); t_ = pivot - R @ pivot + np.array([0., shift_y, 0.])
        return np.c_[R, t_]
    for f in np.linspace(1, 0, I['steps'] // 2):
        rows.append(pose(-angle, -I['slide_mm'] * f))
    for th in np.linspace(angle, 0, I['steps'] - I['steps'] // 2):
        rows.append(pose(-th, 0.))
    return rows


def regions(name):
    if name == 'Battery_Holder':
        result = spaces16.regions(name); c = CAGE; G = GATE; sx = c['slot_x_centre_mm']; wall = sx + c['slot_width_mm'] / 2; sy0, sy1 = c['gate_slot_y_mm']; dz = G['detent_z_mm']; d = G['notch_depth_mm']
        result['gate_removal_route'] = spaces16.Swept(battery_gate(True), [(0, 0, float(v)) for v in np.linspace(0, 15, 61)])
        for sign in (1, -1):
            a, b = sorted([sign * wall, sign * (wall + d - .05)]); result[f'gate_detent_notch_{sign:+d}'] = box(a, b, sy0 + .05, sy1 - .05, dz - .3, dz + .3)
        return result
    if name == 'Key_Carrier':
        return spaces16.regions(name)
    rod = P['rod']; result = {'unloaded_clip_bore': cyl(rod['clip_diameter'] / 2, -40, 100).rotate((-90, 0, 0))}
    if name == 'XIAO_Rod_Holder':
        s = S; bo = s['board_outline_mm']; yn = s['board_near_end_y_mm']
        result['clip_gap_near'] = base.gap_cut(*s['near_band_y_mm']); result['clip_gap_far'] = base.gap_cut(*s['far_band_y_mm'])
        result['board'] = board_outline()
        result['board_travel'] = union([board_outline(dx, dy) for dx, dy in reachable_poses()])
        result['usb_connector'] = component_box('usb_c')
        result['usb_plug_body'] = box(-6.3, 6.3, s['y_mm'][1] + .15, 45, BZ - .7, BZ + 6.0)
        result['board_underside_centre'] = box(-4.0, 4.0, 3.5, 20.0, BZ - s['board_underside_clear_mm'], BZ)
        result['wire_route'] = base.external_wire_route()
        for name_ in XO['components']:
            result['component_' + name_] = component_box(name_, .05)
        # Solder fillets on every castellation: board edge to just inside the rail, 0.45 mm under and 2.4 mm over the board.
        result['castellation_solder'] = union([box(a, b, c, d, BZ - .45, BOARD_TOP + 2.4) for a, b, c, d in pad_zones()])
        # Complete wire exit for every castellation: straight up and outward past the rail, down the outside to
        # rod-bus height, and along the outside clear of the near post. Independent of solder height.
        w = WIRE; half = bo['width'] / 2; hw = w['corridor_width_mm'] / 2; top = BOARD_TOP + w['exit_height_above_board_mm']; (ox0, ox1), (rx0, rx1), (ry0, ry1) = w['outboard_x_mm'], w['run_x_mm'], w['run_y_mm']
        for index, (sign, y, _) in enumerate(pad_rows()):
            a, b = sorted([sign * (half - 1.8), sign * ox1]); result[f'wire_exit_up_out_{index:02d}'] = box(a, b, y - hw, y + hw, BOARD_TOP, top)
        for sign in (1, -1):
            a, b = sorted([sign * ox0, sign * ox1]); result[f'wire_exit_down_outboard_{sign:+d}'] = box(a, b, ry0 + 12.28, ry1, -6., BOARD_TOP + .05)
            a, b = sorted([sign * rx0, sign * rx1]); result[f'wire_run_past_near_post_{sign:+d}'] = box(a, b, ry0, ry1, -6., top)
        result['board_insertion'] = PoseSweep(wired_board(), insertion_poses())
        r = RET; g = r['groove']; plate0, plate1 = r['plate_z_mm']; spring = r['spring']; yb = spring['bump_y_mm']; depth = spring['notch_depth_mm']
        for sign in (1, -1):
            a, b = sorted([sign * g['lip_inner_x_mm'], sign * g['back_x_mm']]); result[f'retainer_groove_{sign:+d}'] = box(a, b, r['post']['full_y_mm'][0], g['closed_end_y_mm'], g['floor_z_mm'] + .03, g['ceiling_z_mm'] - .03)
            a, b = sorted([sign * g['back_x_mm'], sign * (g['back_x_mm'] + depth - .05)]); result[f'retainer_detent_notch_{sign:+d}'] = box(a, b, yb - .3, yb + .3, g['floor_z_mm'] + .03, g['ceiling_z_mm'] - .03)
        result['retainer_route'] = spaces16.Swept(retainer(True), [(0, -float(d), 0) for d in np.linspace(0, r['route_travel_mm'], 33)])
    if name == 'XIAO_Top_Retainer':
        spring = RET['spring']; (sx0, sx1), (sy0, sy1) = spring['slit_x_mm'], spring['slit_y_mm']; z0, z1 = RET['plate_z_mm']
        for sign in (1, -1):
            a, b = sorted([sign * (sx0 + .05), sign * (sx1 - .05)]); result[f'retainer_spring_slit_{sign:+d}'] = box(a, b, sy0 + .1, sy1 - .15, z0 - 1, z1 + 1)
    return result


def battery_position(extra=0.):
    keys = base.carrier().bounding_box()
    battery = battery_module().rotate((0, 0, 180)).bounding_box()
    return keys[4] + P['assembly']['battery_end_clearance'] + extra - battery[1]


def xiao_position(extra=0.):
    battery = battery_module().rotate((0, 0, 180)).bounding_box()
    holder = sensor_holder().bounding_box()
    return battery_position() + battery[4] + P['assembly']['battery_end_clearance'] + extra - holder[1]


def to_print(shape, name=None):
    """Print pose: assembly +Y face on the bed, Y as the layer axis, except the flat top plate, which lies on its broad top face."""
    m = mesh(shape)
    rotation = trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]) if name == 'XIAO_Top_Retainer' else trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    oriented = m.copy(); oriented.apply_transform(rotation)
    shift = trimesh.transformations.translation_matrix(-oriented.bounds[0]); oriented.apply_transform(shift)
    return m, oriented, shift @ rotation


def export():
    out = HERE / 'exports'; out.mkdir(exist_ok=True); records = {}; shapes = part_shapes()
    for name in NEW_PARTS:
        shape = shapes[name].simplify(.0001); assert shape.status() == mf.Error.NoError, name
        m, oriented, tf = to_print(shape, name); assert m.is_watertight and len(shape.decompose()) == 1, (name, len(shape.decompose()))
        m.export(out / (name + '-assembly.stl'))
        normal = mf.Manifold(mf.Mesh(np.asarray(np.round(oriented.vertices, 6), np.float32), np.asarray(oriented.faces, np.uint32))).simplify(.000001)
        change = abs(normal.volume() - oriented.volume); assert normal.status() == mf.Error.NoError and change < .01, (name, change)
        mesh(normal).export(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        final = trimesh.load_mesh(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); assert final.is_watertight and len(normal.decompose()) == 1, name
        records[name] = {'bounds_mm': m.bounds.tolist(), 'volume_mm3': m.volume, 'solid_PETG_g': m.volume / 1000 * base.r15.P['print']['density_g_cm3'],
                         'print_height_mm': float(final.bounds[1][2]), 'stl_float32_volume_change_mm3': change, 'body_count': 1, 'watertight': True,
                         'stl_sha256': sha(out / (name + '-SOURCE-REQUIRES-PREPARATION.stl')), 'print_to_assembly': np.linalg.inv(tf).tolist()}
    r16_manifest = json.loads((R16 / 'exports/manifest.json').read_text())
    manifest = {'revision': LOCAL['revision'], 'source_sha256': {os.path.relpath(p, HERE): sha(p) for p in [HERE / 'holder17.py', HERE / 'parameters.json', R16 / 'holder16.py', R16 / 'spaces16.py', R16 / 'parameters.json']},
                'parts': records, 'unchanged_from_r16': {'Key_Carrier': r16_manifest['parts']['Key_Carrier']['stl_sha256']}, 'plate_parts': PLATE, 'physical_fit_verified': False, 'physical_strength_verified': False, 'physical_comfort_verified': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print({n: (round(v['solid_PETG_g'], 2), round(v['print_height_mm'], 1)) for n, v in records.items()}, flush=True)


if __name__ == '__main__':
    export()
