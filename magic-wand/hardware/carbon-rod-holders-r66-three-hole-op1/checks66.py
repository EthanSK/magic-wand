"""CAD checks for the R66 carrier: the threaded OP1 plug route, the restored three-hole seat,
the existing top retainer, every key socket route, the tapered outboard battery rail and the
exterior backing on the rear rod socket.

Writes exports/op1-route.json, exports/battery.json, exports/socket-backing.json and
exports/carrier.json and exits
non-zero when a gate fails. Slice-based checks of the same routes live in audit66.py.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import design66 as d

b, old, r64 = d.b, d.old, d.r64
OUT = d.OUT


def mm3(a, c):
    return round(max(0.0, float((a ^ c).volume())), 5)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def full_rod():
    return old.lay(mf.Manifold.cylinder(500, 4, 4, 144), -250)


def board_zones():
    """Plan regions in the board's own frame, matching the slice comparison of R63-R65."""
    def zone(x0, x1, y0, y1):
        return b.ubox(x0, x1, y0, y1, 0, 1).slice(.5)
    return dict(whole=d.hardware()['board'].project(), left=zone(-5, 0, -10, 22), right=zone(0, 5, -10, 22),
                switch_left=zone(-b.BODY_X, 0, *b.BODY_Y), switch_right=zone(0, b.BODY_X, *b.BODY_Y),
                plunger=zone(-1.45, 1.45, -.6, .6))


def seat_support(body, z):
    section = body.slice(z)
    return {k: round((section ^ v).area(), 2) for k, v in board_zones().items()}


def socket_holes(body):
    """Clear radius and surrounding bearing of each of the three integral socket holes."""
    rows = []
    for y in b.SOCKET_Y:
        cx, cy = b.board_point(0, y)
        row = dict(board_y=y, world_xy=[round(cx, 3), round(cy, 3)], hardware_radius=b.SOCKET_R)
        for z in (9.05, 8.3, 7.6):
            section = body.slice(z)
            centre = mf.CrossSection.circle(.01, 8).translate((cx, cy))
            # Largest empty circle about the socket axis, and how much of a 1 mm ring outside it is plastic.
            lo, hi = 0.0, 4.0
            for _ in range(30):
                mid = (lo + hi) / 2
                if (section ^ mf.CrossSection.circle(mid, 96).translate((cx, cy))).area() > 1e-5:
                    hi = mid
                else:
                    lo = mid
            ring = mf.CrossSection.circle(lo + 1.0, 96).translate((cx, cy)) - mf.CrossSection.circle(lo + .01, 96).translate((cx, cy))
            row[f'z{z}'] = dict(clear_radius=round(lo, 3), plastic_in_1mm_ring_fraction=round((section ^ ring).area() / ring.area(), 3))
            del centre
        rows.append(row)
    return rows


def closed_opening(body):
    """The new opening is a hole in the deck, not a slot open to an edge, at every deck height."""
    cx, cy = d.THREAD_XY
    probe = mf.CrossSection.circle(.2, 16).translate((cx, cy))
    result = {}
    for z in np.arange(7.4, 9.31, .3):
        lo = body.bounding_box()
        frame = mf.CrossSection.square((lo[3] - lo[0] + 20, lo[4] - lo[1] + 20)).translate((lo[0] - 10, lo[1] - 10))
        empty = frame - body.slice(float(z))
        region = next((p for p in empty.decompose() if (p ^ probe).area() > 1e-6), None)
        outer = frame - frame.offset(-1.0)
        result[round(float(z), 2)] = dict(open_to_outside=bool(region is not None and (region ^ outer).area() > 1e-6),
                                          area_mm2=round(region.area(), 2) if region is not None else 0.0)
    return result


def stepped(matrices, solid):
    return [d.pose(solid, m) for m in matrices]


def interpolate_pose(a, z, t):
    """Rotation by slerp-equivalent axis-angle blending and linear translation."""
    ra, rz = a[:3, :3], z[:3, :3]
    rel = rz @ ra.T
    angle = math.acos(max(-1.0, min(1.0, (np.trace(rel) - 1) / 2)))
    if angle < 1e-9:
        r = ra
    else:
        axis = np.array([rel[2, 1] - rel[1, 2], rel[0, 2] - rel[2, 0], rel[1, 0] - rel[0, 1]]) / (2 * math.sin(angle))
        k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
        step = np.eye(3) + math.sin(angle * t) * k + (1 - math.cos(angle * t)) * k @ k
        r = step @ ra
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = (1 - t) * a[:3, 3] + t * z[:3, 3]
    return m


def turn_poses(count=13):
    """Plug held above the deck: tipped (lead down) to upright under the waiting housing."""
    start, end = d.tip_pose(d.THREAD_Z[1]), d.mate_pose(d.LIFT)
    e = d.exit_world()
    first, last = [m[:3, :3] @ e + m[:3, 3] for m in (start, end)]
    poses = []
    for t in np.linspace(0, 1, count):
        m = interpolate_pose(start, end, t)
        # Rotate the plug around the lead exit so the drawn lead remains attached.
        m[:3, 3] = (1 - t) * first + t * last - m[:3, :3] @ e
        poses.append(m)
    return poses


def op1_route(body, r63):
    hw = d.hardware()
    rod = full_rod()
    keys = r64.fitted_key_hardware()
    keys.pop('rod')
    window = d.window()
    thread = d.thread_route()
    thread_gap = d.plug_clearance()
    below = body - window
    x0, x1, y0, y1, z0, z1 = d.WINDOW
    deck_level = body ^ b.box(x0, x1, y0, y1, z0, d.DECK_TOP)
    above_deck = body ^ b.box(x0, x1, y0, y1, d.DECK_TOP, z1)
    plug = hw['plug']
    turn = turn_poses(51)
    turning = stepped(turn, plug)
    first, faces = d.preview_lead_vertices('thread')
    last, _ = d.preview_lead_vertices('turn_end')
    turning_wire = [mf.Manifold(mf.Mesh(((1-t)*first + t*last).astype(np.float32), faces.astype(np.uint32)))
                    for t in np.linspace(0, 1, len(turn))]
    drop = {n: d.drop_route(n, bearing_skin=.2 if n == 'board' else 0.0) for n in ('board', 'sockets', 'housing', 'plug', 'lead')}
    route = d.lead_solid('route')
    report = dict(
        revision='R66', physical_fit_verified=False,
        sequence=['Unplug the white plug from the bare board (switch and retainer off).',
                  'Tip the plug so its lead hangs down and raise it beside the rod, inside the right finger guard, '
                  'up through the deck opening.',
                  'Above the holder, turn the plug upright and push the board housing onto it.',
                  'Lower the board straight down: three sockets into the three holes, housing and plug into the opening.',
                  'Press the lead up into the open channel under the deck.'],
        thread=dict(path_xy=list(d.THREAD_XY), yaw_deg=d.THREAD_YAW, exit_height_mm=list(d.THREAD_Z),
                    tipped_section_mm=[3.1, 6.2], deck_clearance_mm=d.PLUG_GAP, above_deck_clearance_mm=d.ABOVE_GAP,
                    to_carrier_mm3=mm3(thread, body), with_clearance_in_deck_to_carrier_mm3=mm3(thread_gap ^ window, body),
                    through_deck_min_gap_mm=round(thread.min_gap(deck_level, 8), 3),
                    past_end_stop_min_gap_mm=round(thread.min_gap(above_deck, 8), 3),
                    below_and_above_deck_min_gap_mm=round(thread.min_gap(below, 8), 3),
                    full_rod_min_gap_mm=round(thread.min_gap(rod, 8), 3),
                    to_fitted_keys_mm3={k: mm3(thread, v) for k, v in keys.items()},
                    r63_deck_min_gap_mm=round(thread.min_gap(r63, 8), 3)),
        turn_above_holder=dict(poses=len(turning), plug_to_carrier_mm3=max(mm3(p, body) for p in turning),
                               plug_to_keys_mm3=max(mm3(p, v) for p in turning for v in keys.values())),
        drop=dict(lift_mm=d.LIFT, lead_bend_radius_mm=d.BEND_R,
                  to_carrier_mm3={n: mm3(s, body) for n, s in drop.items()},
                  to_full_rod_mm3={n: mm3(s, rod) for n, s in drop.items()},
                  to_fitted_keys_mm3=max(mm3(s, v) for s in drop.values() for v in keys.values()),
                  housing_and_plug_with_0_2_gap_to_carrier_mm3=mm3(d.drop_route('housing', .2) + d.drop_route('plug', .2), body),
                  board_bearing_skin_mm=.2),
        seated=dict(route_lead_to_carrier_mm3=mm3(route, body), route_lead_to_rod_mm3=mm3(route, rod),
                    r51_lead_to_carrier_mm3=mm3(hw['op1_wire'], body),
                    hardware_to_carrier_mm3={n: mm3(hw[n], body) for n in ('board', 'sockets', 'housing', 'plug')}),
        deck_opening_is_closed_hole=closed_opening(body),
    )
    # The two other sequences, measured rather than assumed.
    upright_from_below = mf.Manifold.batch_hull([plug.translate((0, 0, -24)), plug])
    report['not_feasible'] = dict(
        plug_pushed_up_into_seated_housing=dict(
            note='The mated plug is 6.2 mm across beside the rod; pushing it straight up into the seated housing '
                 'overlaps the rod and leaves no finger access.',
            straight_up_overlap_with_full_rod_mm3=mm3(upright_from_below, rod),
            straight_up_overlap_with_carrier_mm3=mm3(upright_from_below, body)),
        mated_board_from_above=dict(
            note='With the plug already mated, the attached harness would have to thread through the closed deck opening.',
            closed_ring_heights_mm=[z for z, v in report['deck_opening_is_closed_hole'].items() if not v['open_to_outside']]))
    # Three holes and deck support: compare with R63 itself.
    report['three_holes'] = dict(r63=socket_holes(r63), r66=socket_holes(body))
    report['seat_support_mm2'] = {f'z{z}': dict(r63=seat_support(r63, z), r66=seat_support(body, z)) for z in (9.3, 9.05, 8.8)}
    # The OP1 seat itself: the board footprint grown 2 mm plus the plug window, inboard of the
    # right guard rail (R64 reworked the guards; that change is checked separately).
    seat = d.hardware()['board'].hull().project().offset(2.0).extrude(9).translate((0, 0, 5))
    zone = (seat + d.window()) ^ b.box(-12, 12.5, -20, 26, 5, 14)
    report['deck_change_from_r63_in_op1_zone_mm3'] = dict(removed=mm3(r63 - body, zone), added=mm3(body - r63, zone),
                                                          plug_passage_volume_in_r63_mm3=mm3(r63, d.plug_passage()))
    report['lid'] = r64.seating_measurements(body, r63)
    report['lid_r63_baseline'] = r64.seating_measurements(r63, r63)
    g = report
    shift = g['lid']['board_shift_1mm_into_stops_at_0_2mm_lift_mm3']
    base = g['lid_r63_baseline']['board_shift_1mm_into_stops_at_0_2mm_lift_mm3']
    report['back_stop_kept_fraction_of_r63'] = round(shift['back'] / base['back'], 3) if base['back'] else None
    checks = [
        g['thread']['to_carrier_mm3'] < .001, g['thread']['with_clearance_in_deck_to_carrier_mm3'] < .001,
        g['thread']['below_and_above_deck_min_gap_mm'] >= .5, g['thread']['full_rod_min_gap_mm'] >= 1.0,
        max(g['thread']['to_fitted_keys_mm3'].values()) < .001,
        g['turn_above_holder']['plug_to_carrier_mm3'] < .001, g['turn_above_holder']['plug_to_keys_mm3'] < .001,
        max(g['drop']['to_carrier_mm3'].values()) < .002, max(g['drop']['to_full_rod_mm3'].values()) < .001,
        g['drop']['to_fitted_keys_mm3'] < .001, g['drop']['housing_and_plug_with_0_2_gap_to_carrier_mm3'] < .002,
        g['seated']['route_lead_to_carrier_mm3'] < .002, g['seated']['route_lead_to_rod_mm3'] < .002,
        max(g['seated']['hardware_to_carrier_mm3'].values()) < .002,
        g['not_feasible']['mated_board_from_above']['closed_ring_heights_mm'] != [],
        all(abs(n['z8.3']['clear_radius'] - o['z8.3']['clear_radius']) < .01 for n, o in zip(g['three_holes']['r66'], g['three_holes']['r63'])),
        all(v['r66']['left'] >= v['r63']['left'] - 1.0 and v['r66']['right'] >= v['r63']['right'] - 1.0
            and v['r66']['plunger'] >= v['r63']['plunger'] - .01 for v in g['seat_support_mm2'].values()),
        g['deck_change_from_r63_in_op1_zone_mm3']['added'] < .01, g['deck_change_from_r63_in_op1_zone_mm3']['removed'] < 8,
        g['thread']['through_deck_min_gap_mm'] >= d.PLUG_GAP - .05, g['thread']['past_end_stop_min_gap_mm'] >= d.ABOVE_GAP - .05,
        # The board stops: left, right and front exactly as R63. The plug rises past the back
        # (end) stop, so that one may lose at most 10 % of its R63 engagement.
        all(abs(shift[k] - base[k]) < .01 for k in ('left', 'right', 'front'))
        and shift['back'] >= .9 * base['back'],
        g['lid']['board_lifted_0_35mm_into_lid_mm3'] > .2, g['lid']['additional_lid_interference_per_pose_mm3'] < .001,
    ]
    # Test the flexible lead throughout the actual world-space morph as well as its end poses.
    obstacles = {'carrier': body, 'rod': rod, 'keys': b.union(list(keys.values()))}
    wire_overlap = {k: max(mm3(wire, obstacle) for wire in turning_wire) for k, obstacle in obstacles.items()}
    report['turn_above_holder']['wire_max_overlap_mm3'] = wire_overlap
    report['turn_above_holder']['wire_samples'] = len(turn)
    checks.append(max(wire_overlap.values()) < .002)
    report['gates'] = checks
    report['passes'] = all(checks)
    return report


# ----------------------------------------------------------------------------- battery
def lowest(body, x0, x1, y, z_top=old.DECK - .01):
    s = body ^ b.box(x0, x1, y - .05, y + .05, -6, z_top)
    return None if s.is_empty() else round(float(s.bounding_box()[2]), 3)


def rail_profile(body):
    rows = []
    for y in np.arange(20.5, old.BED, .5):
        rows.append(dict(y=round(float(y), 2),
                         inboard_rail_bottom=lowest(body, old.PACK_X[1] + old.CLEAR, old.PACK_X[1] + old.CLEAR + old.WALL, y),
                         inboard_lip_bottom=lowest(body, old.PACK_X[1] - old.LIP_W + .05, old.PACK_X[1] - .05, y),
                         outboard_wall_bottom=lowest(body, old.WALL_FACE - old.WALL, old.WALL_FACE - .05, y),
                         outboard_lip_bottom=lowest(body, old.PACK_X[0] + .05, old.PACK_X[0] + old.LIP_W - .05, y)))
    return rows


def extent(rows, key, limit):
    ys = [r['y'] for r in rows if r[key] is not None and r[key] <= limit]
    return [min(ys), max(ys)] if ys else None


def battery(body, r64_body):
    pack = old.pack()
    leaf_zone = b.box(old.LEAF_X[0] - .01, old.PACK_X[0] + .3, old.PACK_Y0, old.BED - 5.5, old.PACK_Z[0], old.DECK)
    rows = rail_profile(body)
    reference = rail_profile(r64_body)
    lip = old.LIP_TOP + .01
    slide = [pack.translate((0, dy, 0)) for dy in np.arange(0, 30.1, .5)]
    drop = pack.translate((0, 0, -.30))     # pouch pushed away from the deck
    inboard = b.box(old.PACK_X[1] - old.LIP_W, old.PACK_X[1] + 1, 15, 50, -1, old.PACK_Z[0])
    outboard = b.box(old.WALL_FACE - 1, old.PACK_X[0] + old.LIP_W, 15, 50, -1, old.PACK_Z[0])
    root_zone = b.box(old.WALL_FACE - .02, old.PACK_X[0] - .37, old.BED - 5.5, old.BED, old.LIP_TOP - .02, old.DECK + .01)
    root_now, root_then = body ^ root_zone, r64_body ^ root_zone
    report = dict(
        revision='R66', physical_fit_verified=False, taper_y_mm=list(d.TAPER), edge_radius_mm=d.WALL_EDGE_R,
        inboard_full_depth_y_mm=extent(rows, 'inboard_rail_bottom', old.LOW + .05),
        inboard_lip_y_mm=extent(rows, 'inboard_lip_bottom', lip),
        outboard_full_depth_y_mm=extent(rows, 'outboard_wall_bottom', old.LOW + .05),
        outboard_lip_under_pack_y_mm=extent(rows, 'outboard_lip_bottom', lip),
        outboard_wall_any_y_mm=extent(rows, 'outboard_wall_bottom', old.DECK - .05),
        r64=dict(outboard_full_depth_y_mm=extent(reference, 'outboard_wall_bottom', old.LOW + .05),
                 outboard_lip_under_pack_y_mm=extent(reference, 'outboard_lip_bottom', lip)),
        # The leaf shoe deliberately stands 0.21 mm into the nominal pouch: that is the spring preload.
        shoe_preload_overlap_mm3=dict(r64=mm3(pack, r64_body ^ leaf_zone), r66=mm3(pack, body ^ leaf_zone)),
        pack_seated_to_carrier_outside_spring_mm3=mm3(pack, body - leaf_zone),
        pack_slide_from_rear_to_carrier_outside_spring_mm3=max(mm3(p, body - leaf_zone) for p in slide),
        pack_to_deck_gap_mm=round(old.DECK - old.PACK_Z[1], 3),
        retention_pack_dropped_0_3mm_mm3=dict(inboard=mm3(drop, body ^ inboard), outboard=mm3(drop, body ^ outboard)),
        spring_leaf_and_shoe_unchanged_xor_mm3=round(float(((body ^ leaf_zone) - (r64_body ^ leaf_zone)).volume()
                                                     + ((r64_body ^ leaf_zone) - (body ^ leaf_zone)).volume()), 5),
        shoe_into_nominal_pack_mm=old.SHOE,
        spring_root=dict(y_mm=[old.BED - 5.5, old.BED], bottom_z_mm=old.LIP_TOP - .01,
                         volume_r64_mm3=round(root_then.volume(), 3), volume_r66_mm3=round(root_now.volume(), 3),
                         joined_to_deck_mm2=round((root_now.slice(old.DECK - .02)).area(), 3)),
        profile_every_0_5mm=rows,
    )
    r = report
    checks = [r['pack_seated_to_carrier_outside_spring_mm3'] < .001, r['pack_slide_from_rear_to_carrier_outside_spring_mm3'] < .001,
              abs(r['shoe_preload_overlap_mm3']['r66'] - r['shoe_preload_overlap_mm3']['r64']) < .001,
              r['inboard_full_depth_y_mm'][1] >= old.BED - .6,
              r['outboard_full_depth_y_mm'][1] < r['inboard_full_depth_y_mm'][1] - 5,
              r['outboard_lip_under_pack_y_mm'][1] >= old.PACK_Y0 + 10,
              min(r['retention_pack_dropped_0_3mm_mm3'].values()) > 1.0,
              r['spring_leaf_and_shoe_unchanged_xor_mm3'] < .01,
              r['spring_root']['volume_r66_mm3'] > .85 * r['spring_root']['volume_r64_mm3'],
              r['spring_root']['joined_to_deck_mm2'] > 8]
    report['gates'] = checks
    report['passes'] = all(checks)
    return report


# ----------------------------------------------------------------------------- keys
def key_routes(body):
    working = old.k.h.d.geometry()[1]
    checked, obstructions = 0, []
    for name, space in working.items():
        if not name.startswith('key_'):
            continue
        for idx, posed in enumerate(old.c.poses(old.placed(space, name))):
            checked += 1
            overlap = mm3(body, posed)
            if overlap > .01:
                obstructions.append(dict(route=name, pose_index=idx, overlap_mm3=overlap))
    strips = [b.load(old.OUT / old.BACKER), b.load(old.prior.old.R58 / 'exports/Socket_Backer_Right-assembly.stl')]
    sweeps = {side: mm3(body, mf.Manifold.batch_hull([s, s.translate((26 * sign, 0, 0))]))
              for s, side, sign in zip(strips, ['left', 'right'], [-1, 1])}
    return checked, obstructions, sweeps


def unchanged_elsewhere(body, r64_body):
    """Net volume against R64 outside the OP1 seat, battery and socket backing zones.

    Boolean differences between two meshes with coincident faces are not reliable here,
    so each carrier is only cut by the region and the volumes are compared. R66 keeps
    R63's deck underside and rod-side skin where R64 cut its under-entry lead lane.
    """
    op1 = b.box(-12, 16, -70, 24, -1, 16)                     # R64's under-entry lane and seat
    battery = b.box(*d.OUTBOARD_ZONE).minkowski_sum(b.box(-.2, .2, -.2, .2, -.2, 1.3))
    outside = b.box(-60, 60, -80, 80, -30, 40) - op1 - battery - d.socket_backing_box(.5)
    return dict(r66_minus_r64_net_mm3=round(float((body ^ outside).volume() - (r64_body ^ outside).volume()), 4),
                note='R63 material that R64 cut for its under-entry lead lane: under the deck at X 7.1-12, '
                     'Y 24-42.6 and a 0.2 mm skin beside the rod at X 4.86-5.06, Y 29-43.65.')


def triangles(path):
    """Triangles of an exported STL, each rotated to start at its smallest vertex (winding kept)."""
    import trimesh
    tris = np.asarray(trimesh.load_mesh(path, process=False).triangles, np.float64)
    first =np.array([min(range(3), key=lambda i: tuple(t[i])) for t in tris])
    return np.stack([np.roll(t, -k, axis=0) for t, k in zip(tris, first)])


def _rows(tris):
    flat = np.ascontiguousarray(np.asarray(tris, np.float32).reshape(len(tris), 9))
    return flat.view(np.dtype((np.void, 36))).ravel()


def triangle_digest(tris):
    """Order-independent digest of a triangle set: equal only for identical geometry and triangulation."""
    return sha256(np.sort(_rows(tris)).tobytes()).hexdigest()


def _closest_distance(points, tris):
    """Distance from each point to the nearest of `tris` (Ericson's closest point on a triangle)."""
    a, b_, c = (tris[None, :, i] for i in range(3))
    p = points[:, None, :]
    ab, ac, ap = b_ - a, c - a, p - a
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    bp = p - b_
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    cp = p - c
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide='ignore', invalid='ignore'):
        on_ab = a + (d1 / (d1 - d3))[..., None] * ab
        on_ac = a + (d2 / (d2 - d6))[..., None] * ac
        on_bc = b_ + ((d4 - d3) / ((d4 - d3) + (d5 - d6)))[..., None] * (c - b_)
        denom = 1 / (va + vb + vc)
        inside = a + (vb * denom)[..., None] * ab + (vc * denom)[..., None] * ac
    conditions = [(d1 <= 0) & (d2 <= 0), (d3 >= 0) & (d4 <= d3), (vc <= 0) & (d1 >= 0) & (d3 <= 0),
                  (d6 >= 0) & (d5 <= d6), (vb <= 0) & (d2 >= 0) & (d6 <= 0), (va <= 0) & (d4 >= d3) & (d5 >= d6)]
    choices = [np.broadcast_to(a, inside.shape), np.broadcast_to(b_, inside.shape), on_ab,
               np.broadcast_to(c, inside.shape), on_ac, on_bc]
    nearest = inside.copy()
    for cond, choice in reversed(list(zip(conditions, choices))):
        nearest = np.where(cond[..., None], choice, nearest)
    return np.nan_to_num(np.linalg.norm(p - nearest, axis=-1), nan=np.inf).min(axis=1)


def surface_distance_mm(changed, other):
    """Largest distance from sample points on the `changed` triangles to the `other` surface.

    Manifold re-triangulates some flat faces anywhere in a mesh after a union; zero
    distance both ways separates such re-triangulation from any real change of shape.
    """
    area = .5 * np.linalg.norm(np.cross(changed[:, 1] - changed[:, 0], changed[:, 2] - changed[:, 0]), axis=1)
    changed = changed[area > 1e-9]
    if not len(changed):
        return 0.0
    weights = np.array([[1 / 3, 1 / 3, 1 / 3], [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])
    points = np.einsum('kj,ijl->ikl', weights, changed).reshape(-1, 3)
    points = points[np.lexsort(points.T[::-1])]
    tmin, tmax = other.min(axis=1), other.max(axis=1)
    worst = 0.0
    for chunk in np.array_split(points, max(1, len(points) // 48)):
        lo, hi = chunk.min(axis=0) - .05, chunk.max(axis=0) + .05
        near = other[np.all((tmax >= lo) & (tmin <= hi), axis=1)]
        worst = max(worst, float(_closest_distance(chunk, near).max()) if len(near) else np.inf)
    return round(worst, 6)


def outside_sections(old, new):
    """Compare occupied material at each half-layer outside the reinforcement. Internal overlapping
    faces can disappear in an STL union even where the manufactured outline is unchanged.
    """
    # Rotate the assembly's Y axis onto the printer's Z axis.
    before, after = [solid.rotate((90, 0, 0)) for solid in (old, new)]
    lo, hi = np.reshape(d.socket_backing_box(.5).bounding_box(), (2, 3))
    patch = mf.CrossSection.square([hi[0] - lo[0], hi[2] - lo[2]]).translate([lo[0], -hi[2]])
    bounds = before.bounding_box()
    bottom, top = bounds[2], bounds[5]
    spacing = .1
    boundary_samples = [lo[1] - .001, lo[1] + .001, hi[1] - .001, bottom + .001, top - .001]
    heights = np.unique(np.r_[np.arange(bottom + .025, top, spacing), boundary_samples])

    areas = []
    for height in heights:
        original = before.slice(float(height))
        reinforced = after.slice(float(height))
        if lo[1] <= height <= hi[1]:
            original = original - patch
            reinforced = reinforced - patch
        areas.append((original - reinforced).area() + (reinforced - original).area())
    worst = int(np.argmax(areas))
    return dict(sections=len(heights), spacing_mm=spacing, max_area_mm2=round(areas[worst], 7),
                worst_y_mm=round(float(heights[worst]), 5), sum_area_times_step_mm3=round(sum(areas) * spacing, 7))


def collet_poses():
    """The kit's split collet slid along the rod from clear of the bed face to fully pushed home."""
    collet = b.load(d.collet_file())
    return [(round(float(dy), 2), collet.translate((0, float(dy), 0)))
            for dy in np.arange(14.0, -old.COLLET_GAP - .01, -.25)]


def pre_backing():
    """Rebuild the pre-backing export. Run first in a fresh process: manifold's triangle
    order, and so the file bytes, depend on what geometry the process created before."""
    import tempfile
    with tempfile.TemporaryDirectory(dir=OUT) as scratch:
        path = Path(scratch) / d.HOLDER
        solid = d.exported(d.carrier(), path)
        return solid, digest(path), triangles(path)


def socket_backing(body, before, pre_sha, pre):
    """The authorised exterior backing on the rear rod socket, and nothing else, changed."""
    post = triangles(OUT / d.HOLDER)
    box = d.socket_backing_box(.5)
    lo, hi = np.reshape(box.bounding_box(), (2, 3))

    def outside(tris):
        return tris[np.any((tris.max(axis=1) < lo) | (tris.min(axis=1) > hi), axis=1)]

    def on_seat(tris):
        # Faces of the collet seat taper itself: every vertex on the socket cone.
        radius = np.hypot(tris[..., 0], tris[..., 2])
        depth = old.BED - tris[..., 1]
        cone = np.vectorize(old.socket_radius)(depth)
        keep = np.all((abs(radius - cone) < .02) & (depth >= -.01) & (depth <= old.SOCKET[1] + .01), axis=1)
        return tris[keep]

    backing = d.rod_socket_backing()
    seat = d.socket_seat_void(0.0)
    rod = full_rod()
    split = b.box(-.45, .45, old.BED - 8, old.BED + .1, -6, -3.6)
    collet_rows = []
    for dy, collet in collet_poses():
        collet_rows.append(dict(dy=dy, to_backing_mm3=mm3(collet, backing),
                                carrier_overlap_before_mm3=mm3(collet, before), carrier_overlap_after_mm3=mm3(collet, body)))
    inserting = [r for r in collet_rows if r['dy'] >= 0]
    pushing = [r for r in collet_rows if r['dy'] < 0]
    seated = next(r for r in collet_rows if r['dy'] == 0.0)
    out_before, out_after = outside(pre), outside(post)
    unmatched_before = out_before[~np.isin(_rows(out_before), _rows(out_after))]
    unmatched_after = out_after[~np.isin(_rows(out_after), _rows(out_before))]
    full_push = pushing[-1]
    report = dict(
        revision='R66', physical_fit_verified=False,
        pre_backing_sha256=pre_sha, pre_backing_is_proven_export=pre_sha == d.PRE_BACKING_SHA256,
        export_triangle_digest=triangle_digest(post),
        export_is_natively_proven_solid=triangle_digest(post) == d.BACKED_TRIANGLES_SHA256,
        box_mm=[lo.round(3).tolist(), hi.round(3).tolist()],
        added_volume_mm3=round(body.volume() - before.volume(), 5),
        added_volume_inside_box_mm3=round((body ^ box).volume() - (before ^ box).volume(), 5),
        outside_box=dict(triangles_before=len(out_before), triangles_after=len(out_after),
                         sections=outside_sections(before, body),
                         retriangulated_before=len(unmatched_before), retriangulated_after=len(unmatched_after),
                         before_to_after_surface_max_mm=surface_distance_mm(unmatched_before, post),
                         after_to_before_surface_max_mm=surface_distance_mm(unmatched_after, pre)),
        seat_taper_faces=dict(before=len(on_seat(pre)), after=len(on_seat(post)),
                              identical=triangle_digest(on_seat(pre)) == triangle_digest(on_seat(post))),
        backing_to_seat_taper_min_gap_mm=round(backing.min_gap(seat, 1.0), 4),
        backing_beyond_bed_face_mm=round(float(backing.bounding_box()[4] - old.BED), 4),
        bed_face_y_mm=dict(before=round(float(before.bounding_box()[4]), 4), after=round(float(body.bounding_box()[4]), 4)),
        backing_min_x_mm=round(float(backing.bounding_box()[0]), 3),
        split_probe_to_carrier_mm3=dict(before=mm3(split, before), after=mm3(split, body)),
        backing_to_split_min_gap_mm=round(backing.min_gap(split, 5.0), 3),
        backing_to_full_rod_min_gap_mm=round(backing.min_gap(rod, 3.0), 3),
        collet_insertion=dict(poses=len(inserting), dy_mm=[inserting[0]['dy'], inserting[-1]['dy']],
                              to_backing_max_mm3=max(r['to_backing_mm3'] for r in inserting),
                              seated_overlap_before_after_mm3=[seated['carrier_overlap_before_mm3'], seated['carrier_overlap_after_mm3']]),
        # The last 1.5 mm is the designed push-in stroke: the split wedge is meant to bear on the
        # original taper. The exterior backing clears the grip throughout that extra travel.
        collet_push_in_stroke=dict(poses=len(pushing), dy_mm=[pushing[0]['dy'], full_push['dy']],
                                   first_contact_with_backing_dy_mm=next((r['dy'] for r in pushing if r['to_backing_mm3'] > 0), None),
                                   full_push_overlap_before_after_mm3=[full_push['carrier_overlap_before_mm3'], full_push['carrier_overlap_after_mm3']],
                                   added_by_backing_max_mm3=round(max(r['carrier_overlap_after_mm3'] - r['carrier_overlap_before_mm3'] for r in pushing), 5)),
        collet_rows=collet_rows,
        components=len(body.decompose()),
    )
    r = report
    stroke = r['collet_push_in_stroke']
    r['gates'] = [r['pre_backing_is_proven_export'], r['export_is_natively_proven_solid'],
                  abs(r['added_volume_mm3'] - 21.8397) < .01, abs(r['added_volume_inside_box_mm3'] - r['added_volume_mm3']) < .01,
                  r['outside_box']['sections']['sections'] >= 600,
                  r['outside_box']['sections']['max_area_mm2'] < .0025,  # 0.05 mm square on any one section
                  r['outside_box']['sections']['sum_area_times_step_mm3'] < .001,
                  r['seat_taper_faces']['identical'] and r['seat_taper_faces']['before'] > 100,
                  r['backing_to_seat_taper_min_gap_mm'] >= .18, r['backing_beyond_bed_face_mm'] <= 1e-4,
                  r['bed_face_y_mm']['before'] == r['bed_face_y_mm']['after'],
                  r['split_probe_to_carrier_mm3']['after'] == r['split_probe_to_carrier_mm3']['before'] == 0,
                  r['backing_to_split_min_gap_mm'] >= 1.5, r['backing_to_full_rod_min_gap_mm'] >= .04,
                  r['collet_insertion']['to_backing_max_mm3'] == 0,
                  r['collet_insertion']['seated_overlap_before_after_mm3'][0] == r['collet_insertion']['seated_overlap_before_after_mm3'][1],
                  all(row['to_backing_mm3'] == 0 for row in collet_rows),
                  stroke['added_by_backing_max_mm3'] <= 1e-4,
                  r['components'] == 1]
    r['passes'] = all(r['gates'])
    return report


def main():
    before, pre_sha, pre = pre_backing()        # first: see pre_backing()
    body = b.load(OUT / d.HOLDER)
    r63 = b.load(d.R63_CARRIER)
    r64_body = b.load(d.R64_OUT / d.HOLDER)
    route = op1_route(body, r63)
    route['carrier_sha256'] = digest(OUT / d.HOLDER)
    route['generator_sha256'] = digest(d.__file__)
    (OUT / 'op1-route.json').write_text(json.dumps(route, indent=2) + '\n')
    print('op1 route passes', route['passes'], route['gates'], flush=True)
    cell = battery(body, r64_body)
    cell['carrier_sha256'] = route['carrier_sha256']
    (OUT / 'battery.json').write_text(json.dumps(cell, indent=2) + '\n')
    print('battery passes', cell['passes'], cell['gates'], flush=True)
    backing = socket_backing(body, before, pre_sha, pre)
    backing['carrier_sha256'] = route['carrier_sha256']
    (OUT / 'socket-backing.json').write_text(json.dumps(backing, indent=2) + '\n')
    print('outside-patch occupied sections', backing['outside_box']['sections'], flush=True)
    print('socket backing passes', backing['passes'], backing['gates'], flush=True)
    checked, obstructions, sweeps = key_routes(body)
    same = unchanged_elsewhere(body, r64_body)
    parts = body.decompose()
    summary = dict(revision='R66', physical_fit_verified=False, carrier_sha256=route['carrier_sha256'],
                   generator_sha256=route['generator_sha256'], checks_sha256=digest(__file__),
                   carrier_components=len(parts), key_poses_checked=checked, key_obstructions=obstructions,
                   socket_backer_sweeps_mm3=sweeps, outside_op1_battery_and_backing_vs_r64=same,
                   op1_route_passes=route['passes'], battery_passes=cell['passes'],
                   socket_backing_passes=backing['passes'],
                   socket_backing_added_mm3=backing['added_volume_mm3'],
                   socket_backing_outside_box_surface_max_mm=max(backing['outside_box']['before_to_after_surface_max_mm'],
                                                                 backing['outside_box']['after_to_before_surface_max_mm']),
                   socket_backing_export_is_natively_proven_solid=backing['export_is_natively_proven_solid'])
    summary['passes'] = bool(route['passes'] and cell['passes'] and backing['passes'] and not obstructions
                             and checked == 336 and max(sweeps.values()) < .01 and len(parts) == 1)
    (OUT / 'carrier.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items()}, indent=1), flush=True)
    if not summary['passes']:
        sys.exit('R66 carrier checks failed')


if __name__ == '__main__':
    main()
