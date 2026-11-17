"""Compose and check the R47 carrier and bracket in one process.

Usage (through geometry_budget.py): build47.py SCRATCH
Writes the carrier, bracket cap and checks into SCRATCH/stage, with R45's
standing-repair receipts in SCRATCH/stage/r45-standing.

The R47 carrier is built procedurally, in R45/R46's own order:
1. R44's procedural carrier at the R47 parameters (moved OP1 seats and
   openings, pulled-in hinge);
2. R45's standing repairs, run by R45's own generators on that body in the
   standing print frame: the left key-floor chamfer and the four lower-floor
   lip reliefs (standing45, standing_relief45), then the left guard-web
   buttress (standing_web45). R45's relief of the old OP1 ledge
   (standing_board45) belonged to the old opening and is not applied;
3. R46's four rounded braces at R46's stations (holder46), clipped by the
   R47 routes;
4. the R47 chin and right guard-leg landing;
then the moved OP1 openings and every R47 hardware route are cut from the
additions. Routes are R47's (carrier_gaps), never R42's stored ones.

The earlier route subtracted R46's frozen mesh from R44 and re-applied the
difference. Float rounding left slivers in the relief windows and along the
brace roots that an STL export merged differently (up to 1 mm2 in one print
layer), so it was replaced by this procedural build.
"""
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

import manifold3d as mf
import numpy as np
import trimesh

import holder47 as h
import layers47
from layers47 import R45_LIP_WINDOWS, layer_differences, print_frame
import holder45 as h45        # R45 is on the path through holder46
import standing45  # noqa: E402
import standing_web45  # noqa: E402

d, p, q, r, base, h32, h29 = h.d, h.p, h.q, h.r, h.base, h.h32, h.h29
box, union = h.box, h.union
R46_EXPORTS = h.R46 / 'exports/key-holder-only'
R45_EXPORTS = h.HERE.parent / 'carbon-rod-holders-r45-open-keyways/exports/key-holder-only'
# R42's route names, so R45's generators and classifiers treat R47's routes alike.
LEGACY = {'OP1 board insertion': 'centred OP1 and complete prewired insertion',
          'DFRobot board through stroke': 'shifted Grove plug operating stroke',
          'DFRobot lead through stroke': 'shifted Grove lead operating stroke'}
SLIVER = .005
START = time.monotonic()


def load(path):
    t = trimesh.load_mesh(path)
    return mf.Manifold(mf.Mesh64(t.vertices, np.asarray(t.faces, np.uint64)))


def save(path, shape):
    m = shape.to_mesh()
    trimesh.Trimesh(m.vert_properties[:, :3], m.tri_verts, process=False).export(path)


def mark(name):
    print(f'[{time.monotonic() - START:7.1f} s] {name}', file=sys.stderr, flush=True)


def keep(shape, minimum=SLIVER):
    pieces = [s for s in shape.decompose() if s.volume() > minimum]
    return union(pieces) if pieces else mf.Manifold()


# R45's stepped left-lip chamfer (its published witness bounds, print frame).
R45_CHAMFER_PRINT = (.01, 11.43, 12.02, 14.03, 28.2, 30.8)


def r45_step_boxes():
    """R45's lip-relief windows and stepped chamfer, grown 0.3 mm, as assembly bounds."""
    m, frame = .3, print_frame()[:3].tolist()
    x0, x1, y0, y1, z0, z1 = R45_CHAMFER_PRINT
    boxes = [box(x - m, x + w + m, 11.78 - m, 13.60 + m, lo - m, hi + m) for x, w, lo, hi in R45_LIP_WINDOWS]
    boxes.append(box(x0 - m, x1 + m, y0 - m, y1 + m, z0 - m, z1 + m))
    return [b.transform(frame).bounding_box() for b in boxes]


def inside_r45_steps(shape):
    """Zero-volume shells (|V| < 1e-5 mm3) carry no material and pass."""
    if abs(shape.volume()) < 1e-5:
        return True
    x0, y0, z0, x1, y1, z1 = shape.bounding_box()
    return any(w[0] <= x0 and w[1] <= y0 and w[2] <= z0 and x1 <= w[3] and y1 <= w[4] and z1 <= w[5]
               for w in r45_step_boxes())


def flat(value):
    return list(value.poses()) if hasattr(value, 'poses') else [value]


def bb(shape):
    return [round(float(v), 3) for v in shape.bounding_box()]


def carrier_gaps(working, angles):
    """R42's carrier routes (audit42.routes) at R47 positions, as lists of poses."""
    parts = q.hardware()
    hinge = r.mirrored(r.d.axis_oval(r.AXIS_Y + r.CLICK_SHIFT, r.AXIS_Z, h29.TAB_R + .03, *h29.SUPPORT_X))
    board = union(parts[n] for n in ('board', 'sockets', 'housing'))
    mouse = union(parts[n] for n in ('switch', 'terminals', 'plunger'))
    pins = union(q.gravity_pins(max(q.PIN_TAILS), dx, dy)
                 for dx in (-q.PIN_X_TOLERANCE, 0., q.PIN_X_TOLERANCE)
                 for dy in (-q.PIN_Y_TOLERANCE, 0., q.PIN_Y_TOLERANCE))
    sensor = r.sensor() + r.connector() + r.electrode() + pins
    gaps = {name: flat(shape) for name, shape in working.items()}
    gaps['external_wire_bus'] = gaps.get('external_wire_bus', []) + [
        parts['op1_wire'].translate((0., 0., z)) for z in np.linspace(-9., 0., 37)]
    gaps.update({
        'snap hinge bores': [hinge],
        'OP1 mounting screw pilots': [q.diagonal(h32.screw_pilots(parts['fasteners'].bounding_box()[2] - .15))],
        'OP1 board insertion': [board.translate((0., 0., z)) for z in np.linspace(0., h32.BOARD_RISE, 33)],
        'OP1 pre-fitted board and plug drop': [(board + parts['plug']).translate((0., 0., z))
                                               for z in np.linspace(0., h32.BOARD_RISE, 33)],
        'OP1 switch insertion': [mouse.translate((0., 0., z)) for z in np.linspace(0., 8., 17)],
        'DFRobot board through stroke': [r.world(sensor, a) for a in angles],
        'DFRobot lead through stroke': [r.world(r.gravity_lead(), a) for a in angles],
        # Cutting only: R46's braces never met the swing past the backup feet.
        'bracket swing to the press limit': [r.world(p.bracket(), a) for a in angles],
    })
    return gaps


def intrusions(solid, gaps):
    out = {}
    box_ = solid.bounding_box()
    for name, poses in gaps.items():
        worst = 0.
        for pose in poses:
            b = pose.bounding_box()
            if b[0] > box_[3] or b[3] < box_[0] or b[1] > box_[4] or b[4] < box_[1] or b[2] > box_[5] or b[5] < box_[2]:
                continue
            worst = max(worst, float((solid ^ pose).volume()))
        out[name] = round(worst, 6)
    return out


class Poses:
    """R42's route form: a region swept through several poses."""
    def __init__(self, items):
        self.items = tuple(items)

    def poses(self):
        return self.items


def r45_zones(gaps):
    return {LEGACY.get(n, n): (v[0] if len(v) == 1 else Poses(v)) for n, v in gaps.items()}


def r45_standing(body, gaps, receipts):
    """R45's standing repairs on the R47 body, by R45's own generators.

    standing45 and standing_web45 read inherited.routes(); here it returns
    the R47 routes and R44's structural witnesses at the R47 parameters
    (the joints the lip relief must never cut).
    """
    structural = h45.inherited.routes()[1]
    frame = print_frame()
    zones = r45_zones(gaps)
    receipts.mkdir(parents=True, exist_ok=True)
    original_web_export = standing_web45.export
    def web_export(shape, directory, name):
        record = original_web_export(shape, directory, name)
        path = directory / ('R47-web-' + name + '-source64.npz')
        mesh = shape.to_mesh64()
        np.savez(path, vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))
        from plate45 import digest
        record['source_mesh64'] = {'file': path.name, 'sha256': digest(path)}
        return record
    with tempfile.TemporaryDirectory(dir=receipts.parent) as tmp, \
            patch.object(h45.inherited, 'routes', lambda: ({d.CARRIER: zones}, structural)), \
            patch.object(standing_web45, 'export', web_export):
        # The float64 body is given as is. Rounding it to float32 first, as
        # plate45's layout input was, makes standing_web45 detach part of its
        # member on the R47 body (its own assertion fails).
        solid = body.transform(np.linalg.inv(frame)[:3])
        joined, chamfer = standing45.prepare(solid, frame, Path(tmp))
        joined, web = standing_web45.prepare(joined, frame, Path(tmp))
        for path in Path(tmp).iterdir():
            if path.suffix in ('.json', '.stl', '.npz'):
                shutil.copyfile(path, receipts / path.name)
    # R45's plate45 simplified the repaired body by 1e-5 mm before laying it out.
    joined = joined.simplify(.00001)
    return joined.transform(frame[:3]), {
        'chamfer_added_mm3': round(chamfer['added_mm3'], 4),
        'lip_relief_removed_mm3': round(chamfer['lower_lip_relief']['original_removed_mm3'], 4),
        'lip_relief_protected_intrusion_mm3': chamfer['lower_lip_relief']['maximum_mating_or_witness_intrusion_mm3'],
        'chamfer_max_route_intrusion_mm3': max(chamfer['maximum_added_intersection_mm3_by_route'].values()),
        'web_added_mm3': round(web['added_mm3'], 4), 'web_removed_mm3': round(web['removed_mm3'], 4),
        'web_max_route_intrusion_mm3': max(web['actual_added_intersections_by_route'].values()),
        'web_attachments_mm3': {n: round(v['new_volume_mm3'], 4) for n, v in web['attachments'].items()},
        'web_original_witness_losses_mm3': {n: v for n, v in web['original_witness_losses_mm3'].items() if v > 1e-6},
        'receipts': ['r45-standing/standing-repair.json', 'r45-standing/standing-web.json'],
    }


def r46_brace_specs():
    """Compose the frozen R46 member recipe with current named bond targets."""
    _, fixed, ribs = d._base_geometry()
    rests = d.finger_rests()
    recipe = json.loads((R46_EXPORTS / 'r46-braces.json').read_text())['records']
    for name, record in recipe.items():
        side = name[0]
        targets = {'middle': rests[side]['shape'], 'base': fixed,
                   'edge': ribs[side + '1'], 'middle row': ribs[side + '2']}
        yield name, record['stations'], record['radii'], {key: targets[key] for key in record['bonds']}


def r46_braces(body, gaps):
    """R46's rounded braces, clipped by every R47 route pose as holder46 clipped them by R46's."""
    precision = h45.inherited.full.precision_support_spaces()
    poses = {**gaps, **{n: flat(v) for n, v in precision.items()}}
    members, records = [], {}
    for key, pts, radii, targets in r46_brace_specs():
        raw = h.h46.run(pts, radii)
        bounds = raw.bounding_box()
        cuts = [raw ^ pose for items in poses.values() for pose in items
                if standing45.overlap(bounds, pose.bounding_box()) and (raw ^ pose).volume() > 1e-8]
        pieces = [s for s in (raw - union(cuts)).decompose() if s.volume() > 1e-6] if cuts else [raw]
        joined = [s for s in pieces if all((s ^ ref ^ body).volume() > .1 for ref in targets.values())]
        assert len(joined) == 1, (key, [(s.volume(), s.bounding_box()) for s in pieces])
        member = joined[0]
        records[key] = {'raw_mm3': round(raw.volume(), 4), 'route_cut_mm3': round(raw.volume() - member.volume(), 4),
                        'new_mm3': round((member - body).volume(), 4),
                        'bonds_mm3': {n: round((member ^ ref ^ body).volume(), 4) for n, ref in targets.items()}}
        members.append(member)
    return union(members), records


def compose(stage):
    key44, working, fixed, ribs = d.geometry()
    slot, barrels, connector, pilots = q.op1_reliefs()
    reliefs = slot + barrels + connector + pilots
    angles = np.linspace(q.EARLY_ANGLE, q.PRESS_LIMIT, 29)
    gaps = carrier_gaps(working, angles)
    body, r45 = r45_standing(key44, gaps, stage / 'r45-standing')
    mark('R45 standing repairs')
    members, braces = r46_braces(body, gaps)
    mark('R46 braces')
    chin_raw = h.chin()
    landing_raw = h.rib_landing()
    raw = members + chin_raw + landing_raw
    blocked = union(pose for poses in gaps.values() for pose in poses if not (pose ^ raw.hull()).is_empty())
    additions = raw - reliefs - blocked
    landing = landing_raw - reliefs - blocked
    # R46 simplified its carrier with braces by 5e-6 mm (holder46.design).
    carrier = (body + additions).simplify(.000005)
    mark('composed')
    # The landing joins the R2 and R3 guards; their old deck ends left inside
    # the deck by the plug pocket add no material and are dropped from the guards.
    inside = box(0., 9., -12., 35., 0., 13.)
    mains = {n: max(ribs[n].decompose(), key=lambda s: s.volume()) for n in ('R1', 'R2', 'R3')}
    ribs = dict(ribs)
    buried = {}
    for name in ('R2', 'R3'):
        pieces = (ribs[name] + landing).decompose()
        buried[name] = [round(s.volume(), 4) for s in pieces if (s - fixed).volume() <= SLIVER]
        ribs[name] = union(s for s in pieces if (s - fixed).volume() > SLIVER)
    # Only the carrier body is kept; any loose piece is reported and gated.
    pieces = sorted(carrier.decompose(), key=lambda s: -s.volume())
    carrier = pieces[0]
    mark('decomposed')
    from relief47 import prepare as local_relief
    structural = h45.inherited.routes()[1][d.CARRIER]
    routes = {**r45_zones(gaps), **h45.inherited.full.precision_support_spaces()}
    carrier, local_repairs = local_relief(carrier, print_frame(), routes, structural,
        d.seat_platforms(), stage, load, save, inside_r45_steps)
    mark('local underside relief')
    r46 = json.loads((R46_EXPORTS / 'r46-braces.json').read_text())
    record = {
        'construction': 'procedural: R44 at R47 + R45 standing45/standing_web45 + R46 brace stations + R47 chin/landing',
        'r44_procedural_mm3': round(key44.volume(), 4),
        'r45_standing_repairs': r45,
        'r47_local_print_repairs': local_repairs,
        'r45_published_mm3': {'chamfer_added': 6.19, 'lip_relief_removed': 75.39, 'web_added': 12.22,
                              'old_op1_ledge_relief_not_applied': 4.91},
        'r46_braces': {k: dict(v, r46_new_mm3=round(r46['records'][k]['new_mm3'], 4),
                               r46_bonds_mm3={n: round(x, 4) for n, x in r46['records'][k]['bonds'].items()})
                       for k, v in braces.items()},
        'r46_braces_new_mm3': {'r47': round((members - body).volume(), 4), 'r46': round(r46['added_mm3'], 4)},
        'additions_cut_by_reliefs_and_routes_mm3': round(raw.volume() - additions.volume(), 4),
        'braces_cut_by_op1_reliefs_mm3': round((members ^ reliefs).volume(), 4),
        'chin_raw_mm3': round(chin_raw.volume(), 4),
        'chin_new_material_mm3': round((chin_raw - key44 - reliefs).volume(), 4),
        'chin_bounds_mm': bb(chin_raw),
        'right_leg_landing': {
            'run_world_mm': [list(pt) for pt in h.LANDING_RUN], 'radius_mm': h.LANDING_RADIUS,
            'kept_mm3': round(landing.volume(), 4), 'pieces': len(landing.decompose()),
            'new_material_mm3': round((landing - key44).volume(), 4),
            'bond_to_centre_deck_mm3': round((landing ^ fixed ^ inside).volume(), 4),
            'bond_to_leg_mm3': {n: round((landing ^ m).volume(), 4) for n, m in mains.items()},
            'gap_to_op1_reliefs_mm': round(float(landing.min_gap(reliefs, 2.)), 4),
            'cut_by_routes_mm3': round((landing_raw - landing).volume(), 4),
            'old_deck_ends_inside_deck_dropped_mm3': buried,
            'bounds_mm': bb(landing),
        },
        # Beside the carrier body, decompose() returns R45's floating relief
        # specks (positive) and tiny internal void shells (negative volume).
        # Keeping only the body drops the specks and fills the voids.
        'loose_specks_dropped': [(round(x.volume(), 5), bb(x)) for x in pieces[1:] if x.volume() > 0],
        'loose_specks_total_mm3': round(sum(x.volume() for x in pieces[1:] if x.volume() > 0), 5),
        'internal_voids_filled': [(round(x.volume(), 5), bb(x)) for x in pieces[1:] if x.volume() < 0],
        'internal_voids_total_mm3': round(-sum(x.volume() for x in pieces[1:] if x.volume() < 0), 5),
        'all_dropped_or_filled_inside_r45_stepped_regions': all(inside_r45_steps(x) for x in pieces[1:]),
        'carrier_mm3': round(carrier.volume(), 4),
        'carrier_bounds_mm': bb(carrier),
    }
    mark('recorded')
    return carrier, working, fixed, ribs, gaps, record


def long_board_drop(key, keys, extra):
    """The bought OP1 board lengthened at its lower end, dropped into the open slot."""
    ext = box(-h32.PCB_HALF_X, h32.PCB_HALF_X, h32.PCB_Y[0] - extra, h32.PCB_Y[0] + .01, h32.PCB_Z, h32.PCB_TOP)
    parts = q.hardware()
    board = union(parts[n] for n in ('board', 'sockets', 'housing')) + q.board_frame(ext)
    return max(float((board.translate((0., 0., z)) ^ (key + keys)).volume())
               for z in np.linspace(0., h32.BOARD_RISE, 33))


def r47_checks(carrier, working, fixed, ribs, gaps, record):
    """R44's complete inherited checks on the R47 carrier, then R47's own."""
    d.checks.cache_clear()
    with patch.object(d, 'geometry', return_value=(carrier, working, fixed, ribs)):
        result = json.loads(json.dumps(d.checks(), default=float))
    d.checks.cache_clear()
    lay, bonds = result['layout'], result['bonds']
    hinge, settings = result['hinge'], result['stop_settings']
    paddle = p.bracket()
    steps = np.diff([row['nominal_plunger_travel_mm'] for row in reversed(settings)])
    clearance = dict(result['clearance_overlap_mm3'])
    from_below = clearance.pop('op1_plug_and_lead_from_below_off_rod')
    gates = {
        'clearances_below_0.035': max(clearance.values()) < .035,
        'op1_plug_from_below_route (R32-R46 entry, replaced by pre-fitting)': from_below < .035,
        'full_stroke_below_0.035': max(result['full_stroke_overlap_mm3'].values()) < .035,
        'carrier_one_piece': len(carrier.decompose()) == 1,
        'bracket_one_piece': len(paddle.decompose()) == 1,
        'stop_boss': bonds['stop_boss_mm3'] > 15.,
        'pusher_to_floor': bonds['pusher_to_floor_mm3'] > 1.,
        'pusher_root_to_floor': bonds['pusher_root_to_floor_mm3'] > 1.,
        'pusher_to_root': bonds['pusher_to_root_mm3'] > 1.,
        'edge_stops': min(bonds['edge_stops_mm3']) > 1.,
        'op1_seat_contacts': min(bonds['op1_seat_contacts_mm3']) > .1,
        'dfr_posts': min(bonds['dfr_posts_mm3']) > 5.,
        'backup_stops_both_sides': len(result['backup_stop_contacts_mm3']) == 2 and min(result['backup_stop_contacts_mm3']) > .0002,
        'stop_range_low_below_6.65': settings[0]['stop_height_above_switch_base_mm'] < 6.65,
        'stop_range_high_above_7.15': settings[-1]['stop_height_above_switch_base_mm'] > 7.15,
        'stop_steps_0_to_0.11': min(steps) > 0. and max(steps) < .11,
        'screw_lands_before_plastic': all(row['screw_contacts_landing_mm3'] > .00015 and row['plastic_before_screw_contact_mm3'] < .00015 for row in settings),
        'tab_engagement_0.6': hinge['released_tab_axial_engagement_mm'] >= .6,
        'squeezed_tab_clear_0.2': hinge['squeezed_tab_clear_of_support_mm'] > .2,
        'straight_lift_retention': hinge['straight_lift_retention_contact_mm3'] > .04 and hinge['straight_lift_contact_by_height_mm3']['0.10'] < .035,
        'capture_contacts': min(result['capture_contacts_mm3'].values()) > .04,
        'fingertip_terminals': not any(result['finger_contact_probes_reaching_terminals'].values()),
        'guard_ribs_one_piece': all(part['pieces'] == 1 and min(part['rod_mount_contact_mm3'], part['edge_contact_mm3']) > 1. for part in result['ribs'].values()),
        'guard_web_bonds': min(v for k, v in result['left_guard_web_interfaces_mm3'].items() if 'bond' in k) > 1.,
        'slot_to_upper_right_choc_0.6': min(lay['slot_to_upper_right_choc_mm'].values()) >= .6,
        'slot_front_wall_1.0 (R41-R46 closed slot)': lay['slot_front_wall_mm'] >= 1.,
        'sockets_to_rod_0.45': lay['op1_sockets_to_rod_mm'] >= .45,
        'plug_to_rod_0.3135 (R42: not below R41)': lay['op1_plug_to_rod_mm'] >= .3134,
        'bracket_to_switch_body_at_backup_0.2': lay['bracket_to_switch_body_at_backup_mm'] > .2,
        'pusher_pad_to_switch_body_at_backup_0.08': lay['pusher_pad_to_switch_body_at_backup_mm'] > .08,
        'pusher_face_inside_plunger_0.05': lay['pusher_face_inside_plunger_margin_mm'] > .05,
        'pin_gaps_0.2': min(lay['dfr_gravity_pins']['min_gap_to_bracket_by_tail_mm'].values()) >= .2,
        'pin_relief_ahead_of_arm_root': lay['dfr_gravity_pins']['bracket_relief_bounds_mm'][4] < r.ARM_ROOT_Y - .6,
        'reference_guard': result['reference_guard']['passed'],
        'carrier_bottom_plane_at_r46_edge (superseded by the chin)': abs(lay['carrier_bottom_plane_y_mm'] - h.h28.BOTTOM_EDGE) < .001,
        'dfr_front_on_cap_fronts': abs(lay['dfr_released_front_y_mm'] - h.h28.OUTER_CAP_BOTTOM) < .01,
        'r44_finger_rests': result['finger_rest']['passed'],
    }
    # The open slot, the chin and the pre-fitted plug replace these R41-R46
    # features on purpose; R47 gates below check what they protected.
    intended = {'slot_front_wall_1.0 (R41-R46 closed slot)', 'carrier_bottom_plane_at_r46_edge (superseded by the chin)',
                'op1_plug_from_below_route (R32-R46 entry, replaced by pre-fitting)'}
    parts = q.hardware()
    keys = union(working[f'key_{i}_{n}'] for i in (0, 2, 3, 4) for n in ('switch', 'maximum_socket', 'cap_travel'))
    backup = result['backup_angle_deg']
    sweep = np.linspace(q.EARLY_ANGLE, backup, 29)
    backup_height = base.SWITCH_FREE_REFERENCE - result['backup_nominal_plunger_travel_mm']
    route_hits = intrusions(carrier, {**{k: v for k, v in gaps.items() if k != 'bracket swing to the press limit'},
                                      'bracket through stroke to backup': [r.world(paddle, a) for a in sweep]})
    # The worst bracket-to-carrier contact on the way to backup, and where.
    worst = max(((float((r.world(paddle, a) ^ carrier).volume()), a) for a in sweep), key=lambda t: t[0])
    touch = r.world(paddle, worst[1]) ^ carrier
    bracket_touch = {'mm3': round(worst[0], 6), 'angle_deg': round(float(worst[1]), 4),
                     'is_backup_angle': bool(abs(worst[1] - backup) < 1e-9),
                     'bounds_mm': bb(touch) if not touch.is_empty() else None}
    others = union(v for n, v in parts.items() if n not in ('op1_wire', 'plunger'))
    contact_rows = []
    for a in sweep:
        travel = base.actuator_travel(a)
        moving = r.world(paddle, a)
        contact_rows.append({'angle_deg': round(float(a), 4), 'plunger_travel_mm': round(travel, 4),
                             'bracket_to_depressed_plunger_mm3': round(float((moving ^ parts['plunger'].translate((0., 0., -travel))).volume()), 6),
                             'bracket_to_other_op1_parts_mm3': round(float((moving ^ others).volume()), 6)})
    board_plug = union(parts[n] for n in ('board', 'sockets', 'housing', 'plug'))
    band = base.clip_bands()
    zones = {'mid_band': box(-8, 8, 9.0, 12.6, -8, 4.4), 'skirt': box(-8, 8, 12.6, 20.9, -8, 4.4),
             'rear_band': box(-8, 8, 23.3, 26.9, -8, 4.4)}
    rod = base.rod()
    r46 = load(h.R46_ASSEMBLY)
    clip = {name: {k: {'material_mm3': round(float((c ^ band ^ zone).volume()), 3),
                       'rod_grip_interference_mm3': round(float((c ^ band ^ zone ^ rod).volume()), 4)}
                   for k, c in (('r46', r46), ('r47', carrier))} for name, zone in zones.items()}
    rib_rows = {}
    for name, rib in ribs.items():
        sign = 1 if name.startswith('R') else -1
        inside = box(*sorted((0., sign * 9.)), -12., 35., 0., 13.)
        outside = box(*sorted((sign * 20., sign * 34.)), -12., 35., 0., 13.)
        rib_rows[name] = [{'volume_mm3': round(float(s.volume()), 3),
                           'rod_mount_contact_mm3': round(float((s ^ fixed ^ inside).volume()), 3),
                           'edge_contact_mm3': round(float((s ^ fixed ^ outside).volume()), 3),
                           'bounds': bb(s)} for s in sorted(rib.decompose(), key=lambda s: -s.volume())]
    # R46's middle-to-edge braces and their joint witnesses must survive whole.
    frame = print_frame()[:3].tolist()
    parts_ = q.hardware()
    op1_open = union(q.op1_reliefs()) + union(
        (union(parts_[n] for n in ('board', 'sockets', 'housing', 'plug'))).translate((0., 0., z))
        for z in np.linspace(0., h32.BOARD_RISE, 33))
    braces = {}
    for side in ('L', 'R'):
        for member in ('cross-brace', 'deck-return'):
            for suffix in ('', '-edge-bond', '-middle-row-bond', '-middle-bond', '-base-bond'):
                path = R46_EXPORTS / f'R46-{side}-{member}{suffix}.stl'
                if path.exists():
                    w = load(path).transform(frame)
                    lost = w - carrier
                    braces[path.stem] = {'fraction_kept': round(float((w ^ carrier).volume() / w.volume()), 5),
                                         'kept_mm3': round(float((w ^ carrier).volume()), 4),
                                         'lost_outside_op1_openings_mm3': round(float((lost - op1_open).volume()), 5)}
    y_stop = base.STOP_Y + r.CLICK_SHIFT
    landing_top = base.DECK_TOP + q.LANDING_RAISE
    head = mf.Manifold.cylinder(landing_top - 10.9, 2.05, 2.05, 64).translate((base.STOP_X, y_stop, 10.9))
    op1_cut = union(q.op1_reliefs())
    trimmed = q.stop_landing() ^ op1_cut
    leg = record['right_leg_landing']
    r45 = record['r45_standing_repairs']
    # The harness free end passes down through the carrier beside the rod
    # channel before the pre-fitted board drops in; its lead then presses
    # up into the open underside groove (the wire-bus route above).
    start = q.lead_points()[0][:2]
    window = mf.CrossSection.square((30., 30.)).translate((start[0] - 15., start[1] - 15.))
    openings = [c for c in (window - carrier.project()).decompose()
                if not (c ^ mf.CrossSection.circle(.05, 12).translate(start)).is_empty()]
    radius = 0.
    for t in np.arange(.05, 6., .05):
        if not openings or openings[0].offset(-t, mf.JoinType.Round).is_empty():
            break
        radius = round(float(t), 2)
    harness = {'through_opening_area_mm2': round(openings[0].area(), 3) if openings else 0.,
               'through_opening_bounds_mm': [round(float(v), 3) for v in openings[0].bounds()] if openings else None,
               'largest_round_free_end_mm': round(2 * radius, 2),
               'three_1.5mm_wire_bundle_mm': round(1.5 * (1 + 2 / math.sqrt(3)), 3)}
    extra = {
        'op1_prefitted_board_and_plug_drop_mm3': round(max(float((board_plug.translate((0., 0., z)) ^ (carrier + keys)).volume())
                                                            for z in np.linspace(0., h32.BOARD_RISE, 57)), 6),
        'long_board_drop_overlap_mm3': {f'{e:.1f}': round(long_board_drop(carrier, keys, e), 6) for e in (1., 2., 4.)},
        'switch_height_above_base_at_backup_mm': round(backup_height, 4),
        'omron_operating_height_mm': [6.7, 7.1],
        'clicks_before_backup_feet': backup_height < 6.7,
        'press_contacts_through_stroke': contact_rows,
        'stop_landing_trimmed_by_op1_reliefs': {'mm3': round(float(trimmed.volume()), 4),
                                               'bounds_mm': bb(trimmed) if not trimmed.is_empty() else None},
        'stop_screw_head_footprint_r2.05_cut_by_op1_reliefs_mm3': round(float((head ^ op1_cut).volume()), 6),
        'r46_brace_and_joint_witness_fraction_kept': braces,
        'harness_free_end_through_opening': harness,
        'largest_bracket_to_carrier_contact_to_backup': bracket_touch,
        'clip_rings_vs_r46': clip,
        'guard_rib_pieces': rib_rows,
        'route_intrusion_mm3': route_hits,
        'summary': h.summary(),
        'stop_parameters': {'HEEL_TOP': q.HEEL_TOP, 'LANDING_RAISE': q.LANDING_RAISE, 'START_TURNS': q.START_TURNS,
                            'screw_engagement_at_start_mm': round(4. - q.START_TURNS * base.PITCH, 3)},
    }
    grip = {k: sum(z[k]['rod_grip_interference_mm3'] for z in clip.values()) for k in ('r46', 'r47')}
    extra['gates'] = {
        'prefitted_drop': extra['op1_prefitted_board_and_plug_drop_mm3'] < .035,
        'long_board_drop': max(extra['long_board_drop_overlap_mm3'].values()) < .035,
        'clicks_before_backup_feet': extra['clicks_before_backup_feet'],
        'only_pusher_meets_plunger': all(row['bracket_to_other_op1_parts_mm3'] < .0002 for row in contact_rows),
        'stop_screw_head_footprint_whole': extra['stop_screw_head_footprint_r2.05_cut_by_op1_reliefs_mm3'] < .0001,
        # The moved OP1 openings may trim a brace end; nothing else may, and
        # every R46 joint keeps at least 90 % of its volume.
        'r46_braces_and_joints_kept': (len(braces) >= 10 and all(v['lost_outside_op1_openings_mm3'] < .002 for v in braces.values())
                                       and all(v['fraction_kept'] > .9 for k, v in braces.items() if k.endswith('-bond'))),
        # The exported float32 STL, closed as the slicer closes each layer,
        # must print as the checked solid: in no layer may any change be wider
        # than 0.2 mm (half a bead) or lie outside R45's relief floor band.
        'stl_export_prints_as_checked_solid': (layers47.prints_alike(record['stl_round_trip'])
                                               and record['stl_round_trip']['pieces_over_0.001mm3'] == 1),
        # R45's stepped lip relief and chamfer leave 0.0016 mm3 specks and
        # tiny voids; only those, inside those regions, may be dropped or filled.
        'only_r45_relief_specks_and_voids': (record['loose_specks_total_mm3'] < .05
                                             and record['internal_voids_total_mm3'] < .05
                                             and record['all_dropped_or_filled_inside_r45_stepped_regions']),
        # R45's generators, run on the R47 body, reproduce R45's published
        # chamfer, lip relief and web (those regions did not move).
        'r45_standing_repairs_reproduced': (abs(r45['chamfer_added_mm3'] - 6.19) < .3
                                            and abs(r45['lip_relief_removed_mm3'] - 75.39) < 2.
                                            and abs(r45['web_added_mm3'] - 12.22) < .5
                                            and r45['chamfer_max_route_intrusion_mm3'] < 1e-5
                                            and r45['web_max_route_intrusion_mm3'] < 1e-5),
        'harness_free_end_passes_beside_rod': harness['largest_round_free_end_mm'] >= harness['three_1.5mm_wire_bundle_mm'],
        'right_leg_landing_bonds': (leg['pieces'] == 1 and leg['bond_to_centre_deck_mm3'] > 1.
                                    and min(leg['bond_to_leg_mm3'][n] for n in ('R2', 'R3')) > 1.),
        'clip_material_not_below_r46': all(clip[z]['r47']['material_mm3'] >= clip[z]['r46']['material_mm3'] - .05 for z in zones),
        'rod_grip_not_below_r46': grip['r47'] >= grip['r46'] - .005,
        'main_rib_pieces_keep_both_contacts': all(rows[0]['rod_mount_contact_mm3'] > 1. and rows[0]['edge_contact_mm3'] > 1.
                                                  for rows in rib_rows.values()),
        'no_route_intrusion': max(route_hits.values()) < .0002,
    }
    extra['passed'] = all(extra['gates'].values())
    failed = sorted(k for k, v in gates.items() if not v)
    result['r47'] = {
        'inherited_gates': gates,
        'inherited_failures': failed,
        'intended_inherited_exceptions': sorted(intended),
        'unexpected_inherited_failures': sorted(set(failed) - intended),
        'checks': extra,
        'passed': bool(not (set(failed) - intended) and extra['passed']),
        'physical_fit_click_strength_and_print_verified': False,
    }
    return result


def main(scratch):
    stage = scratch / 'stage'
    stage.mkdir(parents=True, exist_ok=True)
    carrier, working, fixed, ribs, gaps, record = compose(stage)
    print(json.dumps(record, indent=1), flush=True)
    save(stage / 'R47-Key-Carrier-assembly.stl', carrier)
    save(stage / 'R47-DFRobot_Hole_Bracket-cap.stl', p.bracket())
    reloaded = load(stage / 'R47-Key-Carrier-assembly.stl')
    mark('saved')
    record['stl_round_trip'] = {'volume_change_mm3': round(reloaded.volume() - carrier.volume(), 5),
                                'pieces': len(reloaded.decompose()),
                                'pieces_over_0.001mm3': sum(s.volume() > .001 for s in reloaded.decompose()),
                                **layer_differences(carrier, reloaded)}
    mark('export compared')
    result = r47_checks(carrier, working, fixed, ribs, gaps, record)
    result['r47']['composition'] = record
    (stage / 'r47-checks.json').write_text(json.dumps(result, indent=1, default=float))
    ch = result['r47']['checks']
    print(json.dumps({k: result['r47'][k] for k in ('inherited_failures', 'unexpected_inherited_failures', 'passed')}, indent=1))
    print(json.dumps({k: v for k, v in ch.items() if k not in ('press_contacts_through_stroke', 'route_intrusion_mm3', 'guard_rib_pieces')},
                     indent=1, default=float))
    print('rib pieces:', {n: [(row['volume_mm3'], row['rod_mount_contact_mm3'], row['edge_contact_mm3']) for row in rows]
                          for n, rows in ch['guard_rib_pieces'].items()})
    print('route intrusions > 0:', {k: v for k, v in ch['route_intrusion_mm3'].items() if v > 0})
    print('press contacts:', [(row['angle_deg'], row['plunger_travel_mm'], row['bracket_to_other_op1_parts_mm3'])
                              for row in ch['press_contacts_through_stroke'][::7]])
    for key in ('backup_angle_deg', 'backup_nominal_plunger_travel_mm', 'max_plunger_change_per_step_mm'):
        print(key, result[key])
    print('stop heights:', [row['stop_height_above_switch_base_mm'] for row in result['stop_settings']])
    print('layout:', {k: result['layout'][k] for k in ('pusher_pad_to_switch_body_at_backup_mm', 'bracket_to_switch_body_at_backup_mm',
                                                         'slot_to_upper_right_choc_mm', 'op1_plug_to_rod_mm', 'op1_sockets_to_rod_mm',
                                                         'op1_lead_to_carrier_mm', 'press_travel_rest_to_backup_mm')})
    print('full stroke:', result['full_stroke_overlap_mm3'])
    print('clearance > 0:', {k: v for k, v in result['clearance_overlap_mm3'].items() if v > 0})
    print('bonds:', result['bonds'])


if __name__ == '__main__':
    main(Path(sys.argv[1]))
