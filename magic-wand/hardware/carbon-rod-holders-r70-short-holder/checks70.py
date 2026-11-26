"""R70 CAD checks. Every report puts the printed, fitted R69 beside R70 and is bound to the
R70 mesh hashes. Nothing here is a slice, a print or a fit in the hand.

    hinge.json     the fitted click, unchanged, with the stronger arm-to-barrel joints
    short.json     the shorter holder: rear face, bearing blocks, pin line, rod bore
    battery.json   the pouch in the shorter rail and the rebuilt side spring
    keys.json      the right upper key 2 mm nearer, every key route, and why the left stays
    posts.json     the touch-board posts with crush ribs
    edges.json     the lower and upper edge of both key banks, station by station
    base.json      the sacrificial base: nine pieces, where each fin is rooted
    carrier.json   what did not change, source reproduction, plastic used

A gate that describes a fault R69 had in the hand (a fin rooted in the battery roof, a
square lower edge) is evaluated on R69 too and must fail there.
 — Claude Fable 5.2"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import design70 as d
import hinge70
import kit70
import checks69 as c69

fit, c66, c67 = c69.fit, c69.c66, c69.c67
b, old, r66, r69 = d.b, d.old, d.r66, d.r69
k, r61, h69 = old.k, old.r61, hinge70.h69
OUT = d.OUT
mm3, rnd, digest = c66.mm3, c69.rnd, c69.digest
PETG = c69.PETG
R69_PARTS = dict(carrier=d.R69_CARRIER, paddle=h69.OUT / hinge70.PADDLE, lid=hinge70.R69_LID, wires=h69.OUT / hinge70.WIRES,
                 post_bar=hinge70.R57_POST_BAR)
R70_PARTS = dict(carrier=OUT / d.HOLDER, paddle=OUT / hinge70.PADDLE, lid=OUT / hinge70.LID, wires=OUT / hinge70.WIRES,
                 post_bar=OUT / hinge70.POST_BAR)
SHIFT = (0., -d.KEY_SHIFT, 0.)
REPORTS = ('hinge.json', 'short.json', 'battery.json', 'keys.json', 'posts.json', 'edges.json', 'base.json', 'carrier.json')


def main(only=None):
    new = {n: b.load(p) for n, p in R70_PARTS.items()}
    prev = {n: b.load(p) for n, p in R69_PARTS.items()}
    hashes = {Path(p).name: digest(p) for p in R70_PARTS.values()}
    built = {}
    makers = dict([('hinge.json', lambda: hinge(new, prev)), ('short.json', lambda: short(new, prev)),
                   ('battery.json', lambda: battery(new, prev)), ('keys.json', lambda: keys(new, prev)),
                   ('posts.json', lambda: posts(new, prev)), ('edges.json', lambda: edges(new, prev, steps(built))),
                   ('base.json', base), ('carrier.json', lambda: carrier(new, prev, steps(built)))])
    results = {}
    if only and 'hinge.json' not in only:
        k.old.configure_new_op1()                          # otherwise hinge_fit64.run does it, exactly once
    for name in REPORTS:
        if only and name not in only:
            continue
        results[name] = makers[name]()
        write(name, results[name], hashes)
    if only:
        return
    summary = dict(revision='R70', physical_fit_verified=False, sliced=False, meshes_sha256=hashes, checks_sha256=digest(__file__),
                   **{n.replace('.json', '') + '_passes': v['passes'] for n, v in results.items()})
    summary['passes'] = bool(all(v['passes'] for v in results.values()) and len(results) == len(REPORTS))
    (OUT / 'checks.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=1), flush=True)
    if not summary['passes']:
        sys.exit('R70 checks failed')


def steps(built):
    """Every build step, made once (about two minutes)."""
    if not built:
        built.update(dict(d.steps()))
    return built


def write(name, report, hashes):
    report['meshes_sha256'] = hashes
    report['carrier_sha256'] = hashes[d.HOLDER]
    report['generator_sha256'] = {Path(m.__file__).name: digest(m.__file__) for m in (d, hinge70, kit70)}
    (OUT / name).write_text(json.dumps(report, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)) + '\n')
    print(name, 'passes', report['passes'], report.get('gates'), flush=True)


# ----------------------------------------------------------------------- hinge
def hinge(new, prev):
    # hinge_fit64.run configures the bought OP1 once; configuring twice moves its datum, so
    # R69's sweep is read from its own report, which is bound to the printed R69 meshes.
    before = json.loads((h69.OUT / 'hinge.json').read_text())
    assert before['meshes_sha256'][d.HOLDER] == d.R69_SHA256 and before['meshes_sha256'][hinge70.PADDLE] == digest(R69_PARTS['paddle'])
    fit.h = hinge70
    click = fit.run(R70_PARTS['carrier'], R70_PARTS['paddle'], R70_PARTS['wires'], R70_PARTS['lid'])
    then = before['click']
    hw = r66.hardware()
    front = b.box(-40, 40, -40, 22., -20, 40)
    press = c69.end_press(new['paddle'], new['lid'], (new['carrier'] + hw['board']) ^ front, hinge70, click['case_stop_deg'])
    # The gussets start on the beams, which are still 8.3 mm out where the gussets start, above the bearing blocks.
    zone = b.box(-8.6, 8.6, hinge70.GUSSET_FROM_Y - .1, hinge70.AXIS + 3.4, hinge70.KEEPER_Z - hinge70.BARREL_R - .1, b.SEAT_Z + .1)
    gaps = lambda paddle: {n: rnd(s.min_gap(paddle, 4.)) for n, s in (('plug', r61.plug()), ('housing', r61.housing()), ('leads', new['wires']))}
    joints = dict(
        throat_mm2=dict(r69=hinge70.joint_throat(prev['paddle']), r70=hinge70.joint_throat(new['paddle'])),
        paddle_volume_mm3=dict(r69=rnd(prev['paddle'].volume(), 2), r70=rnd(new['paddle'].volume(), 2)),
        added_in_the_joint_zone_mm3=rnd((new['paddle'] ^ zone).volume() - (prev['paddle'] ^ zone).volume(), 2),
        change_outside_the_joint_zone_mm3=rnd((new['paddle'] - zone).volume() - (prev['paddle'] - zone).volume(), 3),
        gusset_width_mm=list(hinge70.GUSSET_X), left_post_width_mm=list(h69.LEFT_POST_X),
        gaps_to_fitted_parts_mm=dict(r69=gaps(prev['paddle']), r70=gaps(new['paddle'])),
        paddle_to_carrier_at_rest_gap_mm=dict(r69=rnd(prev['paddle'].min_gap(prev['carrier'], 2.)), r70=rnd(new['paddle'].min_gap(new['carrier'], 2.))),
        barrel_print_bridge=c69.barrel_bridge(new['paddle']))
    same = ('button_contact_deg', 'case_stop_deg', 'lift_stop_deg', 'plunger_travel_at_case_mm', 'reversed_plunger_travel_mm')
    report = dict(revision='R70', physical_fit_verified=False, pin_line_yz_mm=[hinge70.AXIS, hinge70.KEEPER_Z],
                  click_values=dict(r69={n: then[n] for n in same}, r70={n: click[n] for n in same}),
                  common_straight_pin_diameter_mm=dict(r69=then['common_round_straight_line_diameter_mm'], r70=click['common_round_straight_line_diameter_mm']),
                  joints=joints, far_end_press=press, click=click,
                  post_bar_in_the_sweep='hinge_fit64 moves the plain R57 post bar with the paddle; the ribbed bar differs only inside the board holes (posts.json)',
                  key_places_in_the_sweep='hinge_fit64 uses the R69 key places; the right key moved 2 mm away from the hinge (keys.json checks it at its R70 place)')
    t = joints['throat_mm2']
    report['gates'] = [all(abs(click[n] - then[n]) < .02 for n in same),
                       max(click['overlap_mm3'].values()) <= max(max(then['overlap_mm3'].values()), .001),
                       all(t['r70'][s] >= 1.3 * t['r69'][s] for s in ('left', 'right')), abs(joints['change_outside_the_joint_zone_mm3']) < .02,
                       all(joints['gaps_to_fitted_parts_mm']['r70'][n] >= joints['gaps_to_fitted_parts_mm']['r69'][n] - .005 for n in ('plug', 'housing', 'leads')),
                       press['max_overlap_with_retainer_mm3'] == 0 and press['max_overlap_with_carrier_and_board_mm3'] < .001 and press['least_gap_to_retainer_mm'] >= .15,
                       click['common_round_straight_line_diameter_mm'] >= then['common_round_straight_line_diameter_mm'] - .01,
                       not click['paddle_layer_backing']['unsupported_new_sections']]
    report['passes'] = all(report['gates'])
    return report


# ----------------------------------------------------------------------- short holder
def block_numbers(body, bed):
    rows = {}
    for side, sign in (('left', -1), ('right', 1)):
        x0, x1 = sorted((sign * (hinge70.INNER - .01), sign * (hinge70.OUTER + .01)))
        block = body ^ b.box(x0, x1, hinge70.AXIS - 4.5, bed, 8.8, 20.)
        foot = block.rotate((90, 0, 0)).slice(bed - .1)
        rows[side] = dict(volume_mm3=rnd(block.volume(), 1), on_the_rear_face_mm2=rnd(foot.area(), 1), top_z_mm=rnd(block.bounding_box()[5], 2))
    return rows


def short(new, prev):
    body, before = new['carrier'], prev['carrier']
    profiles = dict(r69=c69.bore_profile(before), r70=c69.bore_profile(body, y1=d.BED - .04))
    # The regular half-mm stations do not always reach a changed rear face.
    # Measure the mouth there explicitly; do not call the last grid point its face.
    # Found and fixed by GPT-6.1 Sol.
    mouth_profile=c69.bore_profile(body, y0=d.BED-.04, y1=d.BED-.03, step=.005)
    zones = dict(front_ring=(9.25, 19.75), saddle=(20.25, 28.75), rear_ring=(29.25, 31.75), behind=(33.25, 35.25))
    table = {name: {rev: c69.zone(rows, *span) for rev, rows in profiles.items()} for name, span in zones.items()}
    kept = max(abs(p[1] - q[1]) for p, q in zip(profiles['r70'], profiles['r69']) if p[0] <= d.BED - d.MOUTH[0] - .3)
    full = c66.full_rod()
    length = lambda s: rnd(s.bounding_box()[4] - s.bounding_box()[1], 2)
    report = dict(
        revision='R70', physical_fit_verified=False,
        rear_face_y_mm=dict(r69=rnd(before.bounding_box()[4], 2), r70=rnd(body.bounding_box()[4], 2)),
        behind_the_pin_line_mm=dict(r69=rnd(before.bounding_box()[4] - hinge70.AXIS, 2), r70=rnd(body.bounding_box()[4] - hinge70.AXIS, 2)),
        holder_length_and_print_height_mm=dict(r69=length(before), r70=length(body)),
        behind_the_touch_board_edge_mm=dict(r69=rnd(before.bounding_box()[4] - h69.BOARD_TOP_EDGE_Y, 2), r70=rnd(body.bounding_box()[4] - h69.BOARD_TOP_EDGE_Y, 2)),
        bearing_blocks=dict(r69=block_numbers(before, d.R69_BED), r70=block_numbers(body, d.BED),
                            wall_behind_each_open_bearing_mm=rnd(hinge70.SOCKET_REAR_WALL), wall_behind_the_pin_bore_mm=rnd(d.BED - hinge70.AXIS - old.BORE_FLOOR),
                            shape='plain prism on the rear face; R69 grew each block from a 45 degree buttress'),
        rod=dict(zones=table, largest_radius_change_in_front_of_the_mouth_mm=rnd(kept), mouth_mm=list(d.MOUTH),
                 rear_face_bore_mm=dict(r69=rnd(2 * profiles['r69'][-1][1]), r70=rnd(2 * mouth_profile[0][1])),
                 wall_round_the_mouth_at_the_rear_face_mm=rnd(5.2 - old.ROD_R - d.MOUTH[1], 2),
                 nominal_8mm_rod_overlap_mm3=dict(r69=mm3(before, full), r70=mm3(body, full)),
                 removed='R63 tapered rear socket and 7.35 mm of plain 8.55 mm bore; neither gripped the rod'),
        not_measured='grip of the printed rings on the bought rod; R69 printed and held with the same two rings')
    r = report
    blocks = r['bearing_blocks']['r70']
    r['gates'] = [abs(r['rear_face_y_mm']['r70'] - d.BED) < .01 and r['behind_the_pin_line_mm']['r70'] <= 4.2 < r['behind_the_pin_line_mm']['r69'],
                  r['behind_the_touch_board_edge_mm']['r70'] < 10.3,
                  all(v['on_the_rear_face_mm2'] > 25. and abs(v['top_z_mm'] - hinge70.TOP) < .02 for v in blocks.values()),
                  r['rod']['largest_radius_change_in_front_of_the_mouth_mm'] < .02,
                  abs(table['front_ring']['r70']['bore_diameter_mm'][0] - 7.8) < .01 and abs(table['rear_ring']['r70']['bore_diameter_mm'][0] - 8.0) < .01,
                  r['rod']['rear_face_bore_mm']['r70'] >= 9.0 and abs(r['rod']['nominal_8mm_rod_overlap_mm3']['r70'] - r['rod']['nominal_8mm_rod_overlap_mm3']['r69']) < .02]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- battery
def battery(new, prev):
    body, before = new['carrier'], prev['carrier']
    pouch = old.pack()
    rows = {}
    for rev, shape, leaf, bed in (('r69', before, old.spring(), d.R69_BED), ('r70', body, d.spring(), d.BED)):
        rigid = shape - leaf
        face = b.box(old.PACK_X[0], old.PACK_X[1], old.PACK_Y0, bed, old.PACK_Z[1], old.PACK_Z[1] + .12)
        under = b.box(old.PACK_X[0], old.PACK_X[1], old.PACK_Y0, bed, old.LIP_TOP - .3, old.LIP_TOP - .05)
        rows[rev] = dict(
            seated_overlap_with_the_spring_mm3=mm3(shape, pouch), seated_overlap_without_the_spring_mm3=mm3(rigid, pouch),
            slide_in_from_the_rear_without_the_spring_mm3=max(mm3(rigid, pouch.translate((0, float(t), 0))) for t in range(31)),
            deck_or_roof_over_the_pouch_mm2=rnd((shape ^ face).project().area(), 1), lips_under_the_pouch_mm2=rnd((shape ^ under).project().area(), 1),
            pouch_inside_the_rails_mm=rnd(bed - old.PACK_Y0, 2), pouch_behind_the_rear_face_mm=rnd(old.PACK_Y0 + old.PACK[1] - bed, 2))
    fitted = r66.r64.fitted_key_hardware()
    near = b.union([fitted[n] for n in ('switch_3', 'socket_3', 'switch_0', 'socket_0')])
    spring_zone = b.box(old.WALL_FACE - .02, old.PACK_X[0] + old.SHOE + .06, old.PACK_Y0 + 1.9, d.R69_BED + 1., old.LIP_TOP - .02, d.DECK + .31)
    rail = b.box(old.WALL_FACE - old.WALL - .1, old.PACK_X[1] + old.CLEAR + old.WALL + .1, old.PACK_Y0 - 1.6, d.BED - .05, old.LOW - .1, d.DECK - .02) - spring_zone
    def free_gap(shape, leaf, root_from, bed):
        """Least gap from the free leaf and shoe to anything but their own root."""
        free = leaf ^ b.box(-40, 0, 0, root_from - .05, 0, 20)
        rest = shape - b.box(old.LEAF_X[0] - .05, old.PACK_X[0] + old.SHOE + .05, old.PACK_Y0 + 1.9, bed, old.PACK_Z[0] + .3, old.PACK_Z[1] - .3)
        rest -= b.box(old.WALL_FACE - .02, old.PACK_X[0], root_from - .06, bed, old.LIP_TOP - .02, d.DECK + .31)
        return rnd(free.min_gap(rest, 2.))
    free = dict(r69=free_gap(before, old.spring(), d.R69_BED - 5.5, d.R69_BED), r70=free_gap(body, d.spring(), d.BED - d.ROOT_LENGTH, d.BED))
    report = dict(
        revision='R70', physical_fit_verified=False, pouch_mm=list(old.PACK), pouch_place='unchanged: broad face 0.05 mm under the deck, front at Y 21.9',
        why_the_pouch_does_not_move_forward='the left guard top arm is rooted in the deck at Y 21, directly in front of it',
        seat=rows, spring=d.spring_numbers(), spring_free_gap_to_everything_else_mm=free,
        nearest_to_the_free_spring='the outboard front stop beside the leaf tip, as in R69',
        rail_sections_in_front_of_the_new_rear_face_against_r69=c67.section_difference(before ^ rail, body ^ rail),
        pouch_to_left_keys_mm3=mm3(pouch, near), cover='none: the pouch is held by two lips, the deck, two walls and the side spring, as in R69',
        not_measured='spring force on the real pouch, and how firmly 14.4 mm of rail holds a 27 mm pouch in use')
    r, now, then = report, rows['r70'], rows['r69']
    r['gates'] = [0 < now['seated_overlap_with_the_spring_mm3'] < 4.0 and now['seated_overlap_without_the_spring_mm3'] < .01,
                  now['slide_in_from_the_rear_without_the_spring_mm3'] < .01,
                  12. <= now['pouch_behind_the_rear_face_mm'] <= 13. and then['pouch_inside_the_rails_mm'] - now['pouch_inside_the_rails_mm'] > 7.,
                  .9 <= r['spring']['stiffness_r70_over_r69'] <= 1.1 and free['r70'] >= free['r69'] - .01 and free['r70'] >= .25,
                  r['rail_sections_in_front_of_the_new_rear_face_against_r69']['max_area_mm2'] < .01, r['pouch_to_left_keys_mm3'] < .01,
                  now['lips_under_the_pouch_mm2'] > 40.]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- keys
def placed_spaces():
    """Every inherited key space at its R70 place: key_4 moved, the rest as R63 to R69."""
    working = old.k.h.d.geometry()[1]
    out = {}
    for name, space in working.items():
        if name.startswith('key_'):
            here = old.placed(space, name)
            out[name] = [p.translate(SHIFT) if name.startswith('key_4_') else p for p in old.c.poses(here)]
    return out


def routes(body, spaces):
    checked, hits = 0, []
    for name, poses in spaces.items():
        for idx, pose in enumerate(poses):
            checked += 1
            overlap = mm3(body, pose)
            if overlap > .01:
                hits.append(dict(route=name, pose_index=idx, overlap_mm3=overlap))
    return checked, hits


def left_key_limit(body, spaces):
    """How far the left upper key could follow if its bank moved with it, and what stops it:
    the plastic that would not move (everything under the deck and the centre) and the
    spaces of the lower-left key. — Claude Fable 5.2"""
    mine = {n: p for n, p in spaces.items() if n.startswith('key_3_')}
    lower = b.union([p for n, ps in spaces.items() if n.startswith('key_0_') for p in ps])
    stays = (body ^ b.box(-80, 80, -80, 80, -40, d.DECK - .02)) + (body ^ b.box(-d.BANK_FROM + .02, d.BANK_FROM - .02, -80, 80, -40, 60))
    rows = []
    for delta in (.1, .2, .3, .5, 1.0, 1.5, 2.0):
        worst = dict(shift_mm=delta, into_fixed_plastic_mm3=0., into_lower_key_spaces_mm3=0.)
        for name, poses in mine.items():
            for pose in poses:
                moved = pose.translate((0, -delta, 0))
                hit, pair = mm3(stays, moved), mm3(lower, moved)
                if hit > worst['into_fixed_plastic_mm3']:
                    worst.update(into_fixed_plastic_mm3=hit, route=name, where_mm=[rnd(v, 2) for v in (stays ^ moved).bounding_box()])
                if pair > worst['into_lower_key_spaces_mm3']:
                    worst.update(into_lower_key_spaces_mm3=pair, pair_route=name)
        rows.append(worst)
    free = [row['shift_mm'] for row in rows if row['into_fixed_plastic_mm3'] <= .01 and row['into_lower_key_spaces_mm3'] <= .01]
    return dict(rows=rows, largest_free_shift_tested_mm=max(free) if free else 0.0)


def plug_margin(body, centre, yaw, heights=np.arange(-14., 13.01, 1.0)):
    """c69.largest_plug on one fixed line: the route R69 selected."""
    fixed = c69.obstacles(body) ^ b.box(0., 16., 2., 24., heights[0] - 5., heights[-1] + 5.)
    column = lambda m: b.union([c69.plug_box(m, yaw).translate((float(centre[0]), float(centre[1]), float(z))) for z in heights])
    if mm3(fixed, column(0.0)) > 1e-4:
        return -1.0
    lo, hi = 0.0, 2.5
    for _ in range(7):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if mm3(fixed, column(mid)) > 1e-4 else (mid, hi)
    return rnd(lo)


def keys(new, prev):
    body, before = new['carrier'], prev['carrier']
    spaces = placed_spaces()
    checked, hits = routes(body, spaces)
    fitted = r66.r64.fitted_key_hardware()
    hardware = {n: mm3(body, s.translate(SHIFT) if n.endswith('_4') else s) for n, s in fitted.items() if n != 'rod'}
    span = lambda name: b.union(spaces[name]).bounding_box()
    cap = {n: span(f'key_{n}_cap_travel') for n in (0, 2, 3, 4)}
    gap = dict(right=dict(r69=rnd(cap[4][1] + d.KEY_SHIFT - cap[2][4], 2), r70=rnd(cap[4][1] - cap[2][4], 2)),
               left=dict(r69=rnd(cap[3][1] - cap[0][4], 2), r70=rnd(cap[3][1] - cap[0][4], 2)))
    middle = lambda n: (span(f'key_{n}_switch')[1] + span(f'key_{n}_switch')[4]) / 2
    strips = dict(left=b.load(old.OUT / old.BACKER), right=b.load(old.prior.old.R58 / 'exports/Socket_Backer_Right-assembly.stl'))   # both serve the lower row
    sweeps = {side: mm3(body, mf.Manifold.batch_hull([s, s.translate((26 * sign, 0, 0))])) for (side, s), sign in zip(strips.items(), (-1, 1))}
    arm = r69.new_top_arm() ^ b.box(-40, 40, -40, 40, d.DECK - .07, d.DECK - .01)
    root = lambda shape: rnd((arm.project() ^ (shape ^ b.box(9, 16, 16, 26, d.DECK + .01, d.DECK + .07)).project()).area(), 2)
    window = r69.connector_window()
    then = json.loads((h69.OUT / 'op1.json').read_text())
    route = then['largest_plug_margin_per_side']['r69']
    path = route['centre_world_xy_mm']
    seat = {f'z{z}': dict(r69=c66.seat_support(before, z), r70=c66.seat_support(body, z)) for z in (8.8, 9.05, 9.3)}
    x0, x1, y0, y1, z0, z1 = old.CLIP_CLEARANCE
    report = dict(
        revision='R70', physical_fit_verified=False, right_key_shift_mm=d.KEY_SHIFT,
        row_distance_centre_to_centre_mm=dict(right=dict(r69=rnd(middle(4) + d.KEY_SHIFT - middle(2), 2), r70=rnd(middle(4) - middle(2), 2)),
                                              left=dict(r69=rnd(middle(3) - middle(0), 2), r70=rnd(middle(3) - middle(0), 2))),
        gap_between_cap_travel_envelopes_mm=gap, key_poses_checked=checked, key_obstructions=hits, fitted_switches_and_sockets_to_holder_mm3=hardware,
        socket_backer_sweeps_mm3=sweeps, left_key=left_key_limit(body, spaces),
        left_key_reading=('The left upper socket is loaded prewired from the outer edge, under the deck. Moved toward the lower row, that path '
                          'enters the left guard, which is rooted there. Following the right key would need the left guard reshaped.'),
        kept_in_place=dict(
            right_guard_arm_root_on_the_deck_mm2=dict(r69=root(before), r70=root(body), arm_section_mm2=rnd(arm.project().area(), 2)),
            deck_floor_under_the_moved_latch_pass_mm=rnd(z0 - d.DECK, 2), latch_pass_y_mm=dict(r69=[y0, y1], r70=[y0 - d.KEY_SHIFT, y1 - d.KEY_SHIFT]),
            plastic_inside_the_op1_connector_window_mm3=dict(r69=mm3(before, window), r70=mm3(body, window)),
            plug_margin_on_the_r69_route_mm=dict(route=route, r69=plug_margin(before, path, route['wide_side_yaw_deg']), r70=plug_margin(body, path, route['wide_side_yaw_deg'])),
            room_outboard_of_the_plug_path_mm=dict(r69=c69.outboard_room(before, path), r70=c69.outboard_room(body, path)),
            op1_seat_support_mm2=seat, three_socket_holes=dict(r69=c66.socket_holes(before), r70=c66.socket_holes(body)),
            seated_op1_hardware_to_holder_mm3={n: mm3(body, r66.hardware()[n]) for n in ('board', 'sockets', 'housing', 'plug', 'op1_wire')}))
    r, keep = report, report['kept_in_place']
    room = keep['room_outboard_of_the_plug_path_mm']
    r['gates'] = [not hits and checked == 336, max(hardware.values()) < .01, max(sweeps.values()) < .01,
                  abs(gap['right']['r69'] - gap['right']['r70'] - d.KEY_SHIFT) < .01 and gap['right']['r70'] >= .5,
                  r['left_key']['largest_free_shift_tested_mm'] < .5 and r['left_key']['rows'][-1]['into_fixed_plastic_mm3'] > .5,
                  keep['right_guard_arm_root_on_the_deck_mm2']['r70'] >= keep['right_guard_arm_root_on_the_deck_mm2']['r69'] - .05,
                  abs(keep['plastic_inside_the_op1_connector_window_mm3']['r70'] - keep['plastic_inside_the_op1_connector_window_mm3']['r69']) < .01,
                  keep['plug_margin_on_the_r69_route_mm']['r70'] >= keep['plug_margin_on_the_r69_route_mm']['r69'] - .02,
                  all(room['r70'][z] >= room['r69'][z] - .05 for z in room['r69']),
                  all(abs(seat[z]['r70'][kk] - seat[z]['r69'][kk]) < .05 for z in seat for kk in seat[z]['r69']),
                  max(keep['seated_op1_hardware_to_holder_mm3'].values()) < .01]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- touch-board posts
def rib_fit(hole_d, pitch):
    """Rib interference at the seat for one hole diameter and hole pitch. The posts are
    15.5 mm apart, so each hole sits (pitch - 15.5) / 2 off its post, resting on the post's
    lower edge. Positive: the rib has to give by that much. — Claude Fable 5.2"""
    r,x,y = hole_d / 2,hinge70.RIB_LAND_X[0],hinge70.RIB_LAND_Y[0]
    off = (pitch - 2 * b.HOLE_X) / 2
    centre = (off, hinge70.POST_EDGE_Y + math.sqrt(max(r * r - off * off, 0.)))
    reach = lambda sign: math.hypot(sign*x-centre[0],y-centre[1])-r
    return dict(hole_mm=hole_d, pitch_mm=pitch, outer_rib_mm=rnd(reach(1)), inner_rib_mm=rnd(reach(-1)))


def posts(new, prev):
    bar, plain, paddle = new['post_bar'], prev['post_bar'], new['paddle']
    board = c69.touch_board()
    ribs = hinge70._rib(1, b.SEAT_Z, b.BOARD_TOP)         # the generator's own rib; the meshes are compared by volume below
    clips = {side: b.load(r61.prior.PREVIOUS / 'exports' / f'DFR_Clip_{side}-assembly.stl') for side in ('Left', 'Right')}
    outside = b.box(-40, 40, -40, 40, -40, b.SEAT_Z - .02) + b.box(-40, 40, -40, 40, b.BOARD_TOP + .02, 60)
    report = dict(
        revision='R70', physical_fit_verified=False,
        source=('DFRobot DFR0030 capacitive touch sensor: two mounting holes of 3 mm nominal, no tolerance published. '
                'The hole pitch on the bought board was read from photographs as 15 to 16 mm; the posts are 15.5 mm apart.'),
        r57_post_mm=dict(across=old.m.chain().POST_W, along=old.m.chain().POST_L, play_in_a_3mm_hole=[rnd(3. - old.m.chain().POST_W), rnd(3. - old.m.chain().POST_L)]),
        ribs=dict(per_post=2, root_angle_from_the_upper_edge_deg=hinge70.RIB_DEG,
                  land_outer_x_at_seat_and_board_top_mm=list(hinge70.RIB_LAND_X),land_y_at_seat_and_board_top_mm=list(hinge70.RIB_LAND_Y),
                  crest_width_mm=hinge70.RIB_LAND_WIDTH,
                  width_at_the_post_mm=hinge70.RIB_BASE, added_mm3=rnd(bar.volume() - plain.volume(), 3),
                  built_z_span_mm=[rnd(ribs.bounding_box()[2], 2), rnd(ribs.bounding_box()[5], 2)], board_z_mm=[b.SEAT_Z, b.BOARD_TOP]),
        fit_by_hole_diameter=[hinge70.post_fit(v) for v in (3.0, 3.1, 3.2, 3.3)],
        fit_by_hole_pitch_at_the_seat=[rib_fit(v, p) for v in (3.0, 3.2) for p in (15.0, 15.5, 16.0)],
        bar_outside_the_board_thickness_against_r57_mm3=rnd(abs((bar ^ outside).volume() - (plain ^ outside).volume()), 4),
        through_the_paddle_holes_mm3=max(mm3(bar.translate((0, 0, -float(z))), paddle) for z in np.arange(0, 6.01, .25)),
        seated_in_the_paddle_mm3=mm3(bar, paddle),
        into_a_nominal_3mm_board_mm3=dict(r57=mm3(plain, board), r70=mm3(bar, board)),
        clips_on_the_posts_mm3={side: dict(r57=mm3(clip, plain), r70=mm3(clip, bar)) for side, clip in clips.items()},
        assembly_lower_y_mm=dict(r57=rnd(plain.bounding_box()[1]), r70=rnd(bar.bounding_box()[1])),
        print_pose='Upright on the broad bar foot; actual printed dimensions are in mechanical-sections.json, not these CAD tip values.',
        fit_measurement='CAD crest-to-circle radial overlap, not measured printed squeeze or insertion force.',
        reading=('Two rigid 3 mm pins would force the board whenever its pitch is not exactly the posts\'. The posts stay 2.25 mm; '
                 'only the slim ribs touch the hole, and they crush or shave to the hole they meet.'),
        not_measured='the real hole diameter and pitch, the printed rib width, and the force to seat the board')
    r = report
    three, wide = r['fit_by_hole_diameter'][0]['rib_interference_at_seat_mid_top_mm'], r['fit_by_hole_diameter'][2]['rib_interference_at_seat_mid_top_mm']
    r['gates'] = [.05 <= three[0] <= .30 and three[2] < 0, abs(wide[0]) <= .05,
                  r['through_the_paddle_holes_mm3'] < .001 and r['seated_in_the_paddle_mm3'] < .001,
                  r['bar_outside_the_board_thickness_against_r57_mm3'] < .002,
                  all(abs(v['r70'] - v['r57']) < .001 for v in r['clips_on_the_posts_mm3'].values()),
                  r['ribs']['built_z_span_mm'][0] >= b.SEAT_Z - .01 and r['ribs']['built_z_span_mm'][1] <= b.BOARD_TOP + .01 and .3 < r['ribs']['added_mm3'] < 2.0,
                  abs(r['assembly_lower_y_mm']['r70'] - r['assembly_lower_y_mm']['r57']) < .01]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- round edges
EDGE_HEIGHTS = (.05, .30, .75)                            # above the deck underside, or below the plate top


def quarter_inset(radius, h):
    return radius - math.sqrt(max(2 * radius * h - h * h, 0.))


def stations(outline, spacing=1.5):
    """Points every `spacing` along the outline of both key banks with their inward normals,
    clear of the rear face."""
    rows = []
    for ring in outline.to_polygons():
        ring = np.asarray(ring, float)
        if d._area(ring) <= 0:
            continue
        due = spacing / 2
        for a, c in zip(ring, np.roll(ring, -1, axis=0)):
            step = c - a
            length = float(np.hypot(*step))
            if length < 1e-9:
                continue
            tangent = step / length
            while due <= length:
                point = a + tangent * due
                due += spacing
                if abs(point[0]) >= d.BANK_FROM + .2 and point[1] <= d.BED - .6:
                    rows.append((point, np.array([-tangent[1], tangent[0]])))     # counter-clockwise ring: inward is to the left
            due -= length
    return rows


def inset_at(section, point, inward, reach=3.0):
    """Distance from the outline point inward to the first material of this section."""
    across = np.array([-inward[1], inward[0]]) * .12
    ring = [point - across - inward * .2, point + across - inward * .2, point + across + inward * reach, point - across + inward * reach]
    if d._area(ring) < 0:
        ring = ring[::-1]
    hit = section ^ mf.CrossSection([[tuple(map(float, p)) for p in ring]])
    if hit.is_empty():
        return reach
    pts = np.vstack([np.asarray(p, float) for p in hit.to_polygons()])
    return float(((pts - point) @ inward).min())


def edge_profile(body, outline, level, direction, radius, keep):
    """Station by station: is the edge at least a quarter round of 80% of `radius`?"""
    sections = {h: body.slice(level + direction * h) for h in EDGE_HEIGHTS}
    deep = body.slice(level + direction * 1.9)
    rows, kinds = [], {}
    for point, inward in stations(outline):
        insets = [inset_at(sections[h], point, inward) for h in EDGE_HEIGHTS]
        want = [quarter_inset(.8 * radius, h) for h in EDGE_HEIGHTS]
        present = inset_at(deep, point, inward) < 1.0
        if insets[0] >= 2.5 or not present:
            kind = 'the face is not at this level here'    # the socket entrance, the sloped front rim, the battery roof, a trough
        elif all(i >= w - .03 for i, w in zip(insets, want)):
            kind = 'round'
        else:
            probe = mf.CrossSection.circle(.25, 12).translate((float(point[0] + inward[0] * .6), float(point[1] + inward[1] * .6)))
            kind = next((name for name, plan in keep.items() if not (plan ^ probe).is_empty()), 'square')
        kinds[kind] = kinds.get(kind, 0) + 1
        rows.append(dict(xy_mm=[rnd(point[0], 2), rnd(point[1], 2)], inset_mm=[rnd(i, 2) for i in insets], kind=kind))
    return dict(stations=len(rows), kinds=kinds, round_share=rnd(kinds.get('round', 0) / max(len(rows), 1), 3),
                square=[row for row in rows if row['kind'] == 'square'], samples=rows[::6])


def edges(new, prev, built):
    body, before, raw = new['carrier'], prev['carrier'], built['battery']
    plan = d.plate_plan(raw)
    outline = d.bank_outline(plan)
    rails = d.guard_rails().project().offset(.5, mf.JoinType.Round)
    below = {'guard rail enters the deck here': rails, 'battery rail hangs from the deck here': d.hanging_keep(raw).project()}
    above = {'rib stands on the plate here': d.standing_keep(raw).project()}
    old_outline = d.bank_outline(d.plate_plan(before))
    core = outline.offset(-(d.EDGE_R + .03), mf.JoinType.Round).extrude(8.).translate((0, 0, d.DECK - 2.5))
    # Rear-round material is intentionally removed within its own radius too.
    core ^= b.box(-80.,80.,-80.,d.BED-d.REAR_R-.03,-80.,80.)
    lower = dict(r69=edge_profile(before, old_outline, d.DECK, 1, d.EDGE_R, below), r70=edge_profile(body, outline, d.DECK, 1, d.EDGE_R, below))
    upper = dict(r69=edge_profile(before, old_outline, d.PLATE_TOP, -1, d.TOP_R, above), r70=edge_profile(body, outline, d.PLATE_TOP, -1, d.TOP_R, above))
    (x0, x1), crest_r = d.CREST
    window = mf.CrossSection.square((1.2, 4.)).translate((-9.5, 8.9))        # the crest of the sloped rim, in (Y, Z)
    top = lambda shape: rnd(max(np.asarray(p)[:, 1].max() for p in (shape.transform(old.TO_YZ).slice((x0 + x1) / 2) ^ window).to_polygons()), 3)
    rear = lambda shape, y: rnd(shape.rotate((90, 0, 0)).slice(y).area(), 2)
    report = dict(
        revision='R70', physical_fit_verified=False,
        meaning=('"Bottom edge" is read both ways and both are rounded: the underside rim of the two key banks all the way round '
                 '(front, outer corners, outer sides, rear shoulders), and the lower-key end as a whole (lower and upper edge of its rim).'),
        radius_mm=dict(lower_edge=d.EDGE_R, upper_edge=d.TOP_R, sloped_front_rim_crest=crest_r, plan_corners=d.OPEN_R),
        measure=('at each station the distance from the outline inward to the first plastic, 0.05, 0.30 and 0.75 mm from the face; '
                 'round means at least the quarter round of 80% of the radius at all three'),
        lower_edge=lower, upper_edge=upper,
        centre_between_the_banks='not changed: R62 already rounded its front edge to about 1.8 mm and the OP1 tongue to about 1 mm',
        rear_face='Exposed rear bank rims use a 0.6 mm round; guard, battery-wall and standing-rib roots retain their complete sections.',
        rear_round=dict(radius_mm=d.REAR_R,removed_mm3=rnd(built['bank_edges'].volume()-built['edges'].volume(),4),
                        remaining_cutter_overlap_mm3=rnd(mm3(body,d.rear_edge_cutter(built['bank_edges'])),4)),
        removed_mm3=rnd(raw.volume() - built['edges'].volume(), 2),
        removed_further_than_the_radius_from_the_outline_mm3=rnd((raw ^ core).volume() - (built['edges'] ^ core).volume(), 4),
        crest_highest_z_mm=dict(r69=top(before), r70=top(body)),
        rear_face_section_mm2=dict(before_the_rounds=rear(raw, d.BED - .1), r70=rear(body, d.BED - .1)),
        not_measured='how the round feels on the fingers; the print turns the 1.5 mm round into 0.2 mm steps on the front rim')
    r = report
    r['gates'] = [lower['r70']['round_share'] >= .80 and not lower['r70']['square'], lower['r69']['round_share'] < .10,
                  upper['r70']['round_share'] >= .60 and not upper['r70']['square'],
                  abs(r['removed_further_than_the_radius_from_the_outline_mm3']) < .02, 20. < r['removed_mm3'] < 90.,
                  r['crest_highest_z_mm']['r70'] < r['crest_highest_z_mm']['r69'] - .3,
                  .1 < r['rear_round']['removed_mm3'] < 10. and r['rear_round']['remaining_cutter_overlap_mm3'] < .01]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- base
def root_depth(source, panel):
    """Holder plastic straight behind each fin, at every layer the fin reaches: the least
    depth from the holder's face inward before air. A fin on a 1.2 mm roof reads 1.2. — Claude Fable 5.2"""
    printer, p54 = kit70.printer, kit70.p54
    pose = printer.pose_for(source, *kit70.kit64.PRINT_POSES['Key_Carrier'])
    body = sorted(printer.load_solid(source).transform(pose[:3]).decompose(), key=lambda s: -abs(s.volume()))[0]
    rows = []
    for tie in panel['ties']:
        sign = 1. if tie['face'] == '+y' else -1.
        depths = []
        for z in np.arange(.1, tie['height'], .2):
            strip = body.slice(float(z)) ^ p54._box(tie['at'] - .1, -500, tie['at'] + .1, 500)
            pieces = [np.asarray(p, float)[:, 1] for p in strip.to_polygons()]
            if not pieces:
                continue
            outer = max(pieces, key=lambda ys: (sign * ys).max())             # the piece the fin meets
            depths.append(float(outer.max() - outer.min()))
        rows.append(dict(face=tie['face'], at_x_mm=tie['at'], least_plastic_behind_the_fin_mm=rnd(min(depths), 2)))
    return rows


def base():
    rows = {r['name']: r for r in kit70.parts()}
    before = {r['name']: r for r in kit70.kit69.parts()}
    now = kit70.base_report(rows['Key_Carrier']['source'], rows['Key_Carrier']['panel'])
    then = kit70.base_report(before['Key_Carrier']['source'], before['Key_Carrier']['panel'])
    depth = dict(r69=root_depth(before['Key_Carrier']['source'], before['Key_Carrier']['panel']),
                 r70=root_depth(rows['Key_Carrier']['source'], rows['Key_Carrier']['panel']))
    report = dict(
        revision='R70', physical_fit_verified=False, sliced=False,
        fault='R69: three fins were rooted in the 1.2 mm roof over the battery, two of them over the open pouch space; pulling one out left a hole',
        pieces=dict(r69=sorted(before), r70=sorted(rows), no_longer_printed=sorted(set(before) - set(rows))),
        holder_base=dict(r69=then, r70=now), plastic_behind_each_fin=depth,
        neck=dict(width_mm=kit70.NECK, length_mm=kit70.NECK_LENGTH, starts_beyond_the_holder_face_mm=kit70.NECK_FROM, full_fin_mm=1.7,
                  on='the two fins of the battery corner block'),
        assumptions=('A fin breaks at its smallest section. With the neck beside the holder and 2.9 mm of solid block behind it, the break '
                     'should stay in the fin. Holding through the print rests on a larger first layer than R69 and a print 7.35 mm '
                     'lower, with less fin section (numbers above). Neither is proven until the plate is sliced, printed and released.'),
        fin_section_r70_over_r69=dict(full=rnd(now['total_full_section_mm2'] / then['total_full_section_mm2'], 2),
                                      weakest=rnd(now['total_weakest_section_mm2'] / then['total_weakest_section_mm2'], 2)),
        left_bank_fin='stops 2.0 mm up, below the open pin approach trough, so no stub is left in the trough',
        release=['Nip or snap the two necked fins at the battery corner first: they are the weakest.',
                 'Nip the fin on top of the left key bank and the two under the deck (X -7.4 and X 13.0) with flush cutters.',
                 'Fold the two wings of the panel away. Nothing is attached at the hinge, the roof over the pouch, a wall or a lip.'])
    r = report
    least = lambda rev: min(row['least_plastic_behind_the_fin_mm'] for row in depth[rev])
    r['gates'] = [len(rows) == 9 and r['pieces']['no_longer_printed'] == ['Hinge_Pin_Snug', 'Socket_Backer_Left', 'Socket_Backer_Right'],
                  least('r70') >= 1.6, least('r69') < 1.3,
                  now['holder_first_layer_mm2'] >= then['holder_first_layer_mm2'] and now['print_height_mm'] < then['print_height_mm'],
                  now['total_weakest_section_mm2'] >= 15. and now['first_layer_pieces'] == 1 and now['panel_pieces'] == 1,
                  now['base_volume_in_hinge_bay_mm3'] == 0,
                  all(f['height_mm'] <= d.ROOT_LENGTH - .15 for f in now['fins'] if f['necked']) and sum(f['necked'] for f in now['fins']) == 2]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- carrier
def carrier(new, prev, built):
    body, before = new['carrier'], prev['carrier']
    outline = d.bank_outline(d.plate_plan(built['battery']))
    inner = outline.offset(-(d.EDGE_R + .1), mf.JoinType.Round)
    front = b.box(-80, 80, -80, hinge70.AXIS - 4.6, -80, 80)
    zones = dict(
        centre_in_front_of_the_hinge=b.box(-d.BANK_FROM + .03, old.CLIP_CLEARANCE[0] - .05, -80, hinge70.AXIS - 4.7, -80, 80),
        left_bank_inside_its_rounded_rim=(inner.extrude(d.PLATE_TOP - d.DECK + 1.).translate((0, 0, d.DECK)) ^ b.box(-80, -d.BANK_FROM, -80, 80, 0, 40)) ^ front,
        both_guards_under_the_deck=b.mirrored(b.box(d.BANK_FROM, 80, -80, 21.0, -20, d.DECK - d.SCRAP_DEPTH - .1))
    )
    same = {name: c67.section_difference(before ^ zone, body ^ zone) for name, zone in zones.items()}
    dropped = dict(Hinge_Pin_Snug=r61.OUT / 'Hinge_Pin_Snug-assembly.stl', Socket_Backer_Left=old.OUT / old.BACKER,
                   Socket_Backer_Right=old.prior.old.R58 / 'exports/Socket_Backer_Right-assembly.stl')
    mass = {name: dict(r69_g=rnd(prev[name].volume() * PETG), r70_g=rnd(new[name].volume() * PETG)) for name in ('carrier', 'paddle', 'lid', 'post_bar')}
    mass.update({name: dict(r69_g=rnd(b.load(path).volume() * PETG), r70_g=0.0) for name, path in dropped.items()})
    report = dict(
        revision='R70', physical_fit_verified=False, r69_carrier_sha256=d.R69_SHA256,
        unchanged_zones_sections_against_r69=same, components=len(body.decompose()),
        source_reproduction=dict(built_mm3=rnd(built['edges'].volume(), 3), exported_mm3=rnd(body.volume(), 3)),
        build_steps_mm3={name: rnd(shape.volume(), 2) for name, shape in built.items()},
        mass=mass, mass_total_g=dict(r69=rnd(sum(v['r69_g'] for v in mass.values())), r70=rnd(sum(v['r70_g'] for v in mass.values()))),
        guard='unchanged: no guard beam moved; the candidate of more room between guard and base was not taken up')
    r = report
    r['gates'] = [max(v['max_area_mm2'] for v in same.values()) < .01, r['components'] == 1,
                  abs(r['source_reproduction']['built_mm3'] - r['source_reproduction']['exported_mm3']) < 2.0,
                  r['mass_total_g']['r70'] < r['mass_total_g']['r69']]
    r['passes'] = all(r['gates'])
    return report


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
