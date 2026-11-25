"""CAD checks for R69. Every report is bound to the exported meshes it measured.

* hinge.json     board edge to hinge distances, R68 against R69; the inherited click, lift,
                 assembly and edge-press sweeps on the R69 parts; the barrel print bridge
* keeper.json    paddle to retainer through a far-end press with the hinge lifted, rolled
                 and shifted, R68 against R69 in the same poses
* op1.json       the flat seat: three holes, one window; the white plug rising beside the
                 rod, as the largest plug that passes and the room round it, R68 against R69
* rod.json       the bore along the holder against R62 (grip) and R63 (clear), ring by ring
* carrier.json   key deck windows, 336 key poses, both backer sweeps, the battery box and the
                 untouched remainder against R68, masses, and the summary

A gate that R68 also passes is not evidence for a fix, so each comparison names the R68
value beside the R69 one. Exits non-zero when a gate fails. Slice checks live in audit69.py.
 — Claude Fable 5.2"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import design69 as d
import hinge69
import hinge_fit64 as fit
import checks66 as c66
import checks67 as c67

b, old, r66, r68, h64 = d.b, d.old, d.r66, d.r68, hinge69.h64
k, r61 = old.k, old.r61
OUT = d.OUT
mm3 = c66.mm3
PETG = 1.27e-3                                            # g per mm3
R68_PARTS = dict(carrier=d.R68_CARRIER, paddle=h64.OUT / hinge69.PADDLE, lid=hinge69.R59_LID, wires=h64.OUT / hinge69.WIRES)
R69_PARTS = dict(carrier=OUT / d.HOLDER, paddle=OUT / hinge69.PADDLE, lid=OUT / hinge69.LID, wires=OUT / hinge69.WIRES)
PLUG_ESTIMATE = (3.1, 6.2, 3.65)                          # thick, wide, long: photo estimate, not a measurement


def main(only=None):
    # hinge_fit64.run configures the bought OP1 once; configuring twice moves its datum.
    parts69 = {n: b.load(p) for n, p in R69_PARTS.items()}
    parts68 = {n: b.load(p) for n, p in R68_PARTS.items()}
    hashes = {Path(p).name: digest(p) for p in R69_PARTS.values()}
    results = {}
    results['hinge.json'] = hinge(parts69, parts68)
    makers = (('keeper.json', lambda: keeper(parts69, parts68, results['hinge.json']['click'])), ('op1.json', lambda: op1(parts69, parts68)),
              ('rod.json', lambda: rod(parts69, parts68)), ('carrier.json', lambda: carrier(parts69, parts68)))
    write('hinge.json', results['hinge.json'], hashes)
    for name, make in makers:
        if only and name not in only:
            continue
        results[name] = make()
        write(name, results[name], hashes)
    summary = dict(revision='R69', physical_fit_verified=False, meshes_sha256=hashes, checks_sha256=digest(__file__),
                   **{n.replace('.json', '') + '_passes': v['passes'] for n, v in results.items()})
    summary['passes'] = bool(all(v['passes'] for v in results.values()) and len(results) == 5)
    (OUT / 'checks.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=1), flush=True)
    if not summary['passes']:
        sys.exit('R69 checks failed')


def hinge(parts69, parts68):
    fit.h = hinge69
    click = fit.run(R69_PARTS['carrier'], R69_PARTS['paddle'], R69_PARTS['wires'], R69_PARTS['lid'])
    now = hinge_distances(parts69['paddle'], parts69['wires'], hinge69)
    before = hinge_distances(parts68['paddle'], parts68['wires'], h64)
    bridge = barrel_bridge(parts69['paddle'])
    report = dict(revision='R69', physical_fit_verified=False, r68=before, r69=now, barrel_print_bridge=bridge, click=click,
                  removed='hinge64.paddle rear_web: a print backing for the lowered barrel, behind and above it up to the board seat',
                  holder_rear_face_y_mm=old.BED, holder_length_changed=False)
    report['gates'] = [now['edge_to_paddle_rear_end_mm'] < 10.0 < before['edge_to_paddle_rear_end_mm'],
                       now['edge_to_nominal_lead_rear_mm'] < 10.0, now['mated_plug_to_paddle_gap_mm'] > .35,
                       bridge['rear_web_volume_mm3'] == 0, bridge['span_mm'] <= 8.0 and bridge['posts_on_bed'] == 2,
                       click['lift_stop_deg'] < click['case_stop_deg'] + 1.0]
    report['passes'] = all(report['gates'])
    return report


def keeper(parts69, parts68, click69):
    hw = r66.hardware()
    front = b.box(-40, 40, -40, 22., -20, 40)             # the bearings themselves are checked by the click sweeps
    fixed69, fixed68 = (parts69['carrier'] + hw['board']) ^ front, (parts68['carrier'] + hw['board']) ^ front
    fit.h = h64
    stop68 = k.onset(lambda a: old.vol(h64.rotate(parts68['paddle'], a), k.q.hardware()['switch']) > .001, 0, 4, 24)
    now = end_press(parts69['paddle'], parts69['lid'], fixed69, hinge69, click69['case_stop_deg'])
    before = end_press(parts68['paddle'], parts68['lid'], fixed68, h64, stop68)
    travel_at_posts = math.radians(click69['case_stop_deg']) * (hinge69.AXIS - (b.STATION[1] - 5.0))
    lid_frame = board_frame(parts69['lid'])
    section_profiles = dict(r69=retainer_sections(parts69['lid']), r59=retainer_sections(parts68['lid']))
    floor_probe = b.LID_Z[0] + hinge69.NOTCH_FLOOR + .15
    report = dict(
        revision='R69', physical_fit_verified=False,
        cause=('The R59 towers stood to Z 16.5, 1.2 mm under the paddle plate. A full stroke takes about 0.9 mm of that at the '
               'towers; with the hinge end lifting in its open bearings and the paddle rolled or shifted, the plate reaches them.'),
        rest=dict(r68=rest_gaps(parts68['paddle'], parts68['lid']), r69=rest_gaps(parts69['paddle'], parts69['lid'])),
        travel_at_posts_full_stroke_mm=rnd(travel_at_posts),
        far_end_press=dict(r68=before, r69=now),
        hook=dict(leg_bottom_z_mm=hinge69.LEG_BOTTOM_Z, foot_tip_u_mm=hinge69.FOOT_TIP_U, lip_tip_u_mm=hinge69.LIP_TIP_U,
                  lip_over_foot_mm=rnd(hinge69.FOOT_TIP_U - hinge69.LIP_TIP_U), lip_to_leg_face_mm=rnd(hinge69.LIP_TIP_U - hinge69.LEG_U[1]),
                  lift_gap_mm=hinge69.LIFT_GAP, lift_stop_deg=click69['lift_stop_deg'], post_top_z_mm=hinge69.POST_TOP_Z,
                  r59_tower_top_z_mm=16.5, r59_lip_over_flange_mm=0.0),
        retention=dict(rail_cover_mm=dict(left=rnd(b.TINE_END[0] - b.RAIL_START), right=rnd(b.TINE_END[1] - b.RAIL_START)),
                       right_rail_limit='The right rail cannot run further back: past board station 9.8 its outer wall would stand in the upper-right keycap travel.',
                       latch='R53 spring latch on the left tine, unchanged', retainer_pieces=len(parts69['lid'].decompose()),
                       notch_floor_mm=hinge69.NOTCH_FLOOR, plate_probe_z_mm=floor_probe,
                       tine_sections=section_profiles,
                       plate_under_each_leg_mm2={s: rnd((lid_frame.slice(floor_probe) ^ mf.CrossSection.square((1.9, 4.0)).translate((x, -3.2))).area())
                                                 for s, x in (('left', -5.6), ('right', 3.7))}))
    r = report
    r['gates'] = [now['max_overlap_with_retainer_mm3'] == 0, now['max_overlap_with_carrier_and_board_mm3'] < .001,
                  now['least_gap_to_retainer_mm'] >= .15, before['max_overlap_with_retainer_mm3'] > 0,
                  min(v['room_mm'] for v in r['rest']['r69'].values()) >= 2.2,
                  max(r['retention']['plate_under_each_leg_mm2'].values()) == 0 and r['hook']['lip_to_leg_face_mm'] >= .6,
                  0 < click69['lift_stop_deg'] < 1.6 and r['hook']['lip_over_foot_mm'] >= .4,
                  all(section_profiles['r69'][side]['minimum_area_mm2'] >= .95 * section_profiles['r59'][side]['minimum_area_mm2']
                      for side in ('left', 'right'))]
    r['passes'] = all(r['gates'])
    return report


def retainer_sections(lid) -> dict:
    """Measure the complete notched load path, not only the material under each foot.

    Found by Claude Opus 5.5. Fixed by GPT-6.1 Sol. — GPT-6.1 Sol
    """
    body = board_frame(lid).rotate((90, 0, 0))
    rows = {'left': [], 'right': []}
    windows = {'left': (-7.21, -3.59), 'right': (3.59, 7.21)}
    for v in np.arange(-4.5, 2.001, .05):
        section = body.slice(float(v))
        for side, (u0, u1) in windows.items():
            window = mf.CrossSection.square((u1 - u0, 6.2)).translate((u0, -17.0))
            rows[side].append(dict(v_mm=rnd(v, 3), area_mm2=rnd((section ^ window).area(), 4)))
    return {side: dict(minimum_area_mm2=min(row['area_mm2'] for row in samples), samples=samples)
            for side, samples in rows.items()}


def op1(parts69, parts68):
    body, before = parts69['carrier'], parts68['carrier']
    openings = dict(r68=seat_openings(before), r69=seat_openings(body))
    plug = dict(r68=largest_plug(before), r69=largest_plug(body, hand_reference=before))
    path = plug['r69']['centre_world_xy_mm']
    room = dict(path_centre_xy_mm=path, r68=outboard_room(before, path), r69=outboard_room(body, path))
    main, notch = d.window_sections()
    report = dict(
        revision='R69', physical_fit_verified=False,
        plug_evidence=('Endgame Gear OP1 Universal Switch Set (EGG-SP-U1). No dimensioned drawing of the plug exists in the project; '
                       '3.1 x 6.2 x 3.65 mm is a photo estimate. The printed R68 passed it only with force.'),
        why_r68_checks_passed=('R66-R68 checked one fixed vertical line for the estimated plug with 0.75 mm round it, and a turn in free '
                               'air above the holder. Neither asked how much room a hand has below the deck, where the guard arm '
                               'stood 6.4 mm from the rod, nor how much larger than the estimate the real plug may be.'),
        seat_openings_inside_board_outline=openings,
        window=dict(u_mm=list(d.WINDOW_U), v_mm=list(d.WINDOW_V), corner_radius_mm=d.WINDOW_R, area_mm2=rnd(main.area(), 2),
                    r53_window_mm=[8.28, 7.32], lead_notch_half_width_mm=d.NOTCH_U, lead_notch_end_v_mm=d.NOTCH_END_V, underside_lead_in_mm=d.LEAD_IN),
        largest_plug_margin_per_side=plug, room_outboard_of_plug_path_mm=room,
        seat_support_mm2={f'z{z}': dict(r68=c66.seat_support(before, z), r69=c66.seat_support(body, z)) for z in (8.8, 9.05, 9.3)},
        three_holes=dict(r68=c66.socket_holes(before), r69=c66.socket_holes(body)),
        board_stops=dict(r68=r66.r64.seating_measurements(before, d.r63_carrier())['board_shift_1mm_into_stops_at_0_2mm_lift_mm3'],
                         r69=r66.r64.seating_measurements(body, d.r63_carrier())['board_shift_1mm_into_stops_at_0_2mm_lift_mm3']),
        seated_hardware_to_carrier_mm3={n: mm3(body, r66.hardware()[n]) for n in ('board', 'sockets', 'housing', 'plug', 'op1_wire')},
        guard_arm=dict(old_path=[list(map(float, p)) for p in d.OLD_TOP_PATH], new_path=[list(map(float, p)) for p in d.NEW_TOP_PATH],
                       old_arm_left_below_deck_mm3=mm3(body, d.r61.curve(d.OLD_TOP_PATH, d.TOP_R - .15) ^ b.box(9.5, 13.2, 10.5, 15.5, -5, d.DECK - .3)),
                       new_arm_core_missing_mm3=rnd((d.r61.curve(d.NEW_TOP_PATH, d.TOP_R - .25) ^ b.box(-40, 40, -40, 40, -10, d.DECK) ).volume()
                                                    - mm3(body, d.r61.curve(d.NEW_TOP_PATH, d.TOP_R - .25) ^ b.box(-40, 40, -40, 40, -10, d.DECK)), 4)))
    r = report
    below = [f'z{z:g}' for z in np.arange(-3.5, 3.51, 1.0)]     # under the bank walls that hang just below the deck
    widths69, widths68 = [room['r69'][z] for z in below], [room['r68'][z] for z in below]
    holes69 = r['seat_openings_inside_board_outline']['r69']
    simple = lambda rows: len(rows) == 4 and sum(row['area_mm2'] < 12.0 for row in rows) == 3
    same_holes = all(a[z]['clear_radius'] >= c[z]['clear_radius'] - .01 for a, c in zip(r['three_holes']['r69'], r['three_holes']['r68']) for z in ('z9.05', 'z8.3'))
    seat = r['seat_support_mm2']['z9.3']
    r['gates'] = [simple(holes69) and not simple(openings['r68']), same_holes,
                  plug['r69']['margin_mm'] >= .80 and plug['r69']['margin_mm'] >= plug['r68']['margin_mm'] + .5,
                  min(widths69) >= 6.5 and min(widths69) >= min(widths68) + 2.5,
                  all(seat['r69'][kk] >= seat['r68'][kk] - .5 for kk in seat['r69'] if kk.startswith('switch')),
                  max(r['seated_hardware_to_carrier_mm3'].values()) < .01,
                  r['guard_arm']['old_arm_left_below_deck_mm3'] < .01 and r['guard_arm']['new_arm_core_missing_mm3'] < .05]
    r['passes'] = all(r['gates'])
    return report


def rod(parts69, parts68):
    body = parts69['carrier']
    profiles = dict(r62=bore_profile(d.r62_carrier()), r68=bore_profile(parts68['carrier']), r69=bore_profile(body))
    r58 = bore_profile(b.load(d.HARDWARE / 'carbon-rod-holders-r58-smooth-click' / 'exports' / d.HOLDER), y1=32.6)
    zones = dict(front_ring=(9.25, 19.75), saddle=(20.25, 28.75), rear_ring=(29.25, 31.75), behind=(33.25, 37.25), rear_funnel=(37.75, 43.25))
    table = {name: {rev: zone(rows, *span) for rev, rows in profiles.items()} for name, span in zones.items()}
    same = lambda a, c, y1: max(abs(p[1] - q[1]) for p, q in zip(a, c) if p[0] <= y1)
    full = c66.full_rod()
    report = dict(
        revision='R69', physical_fit_verified=False,
        reference=('R58, R60, R61 and R62 share one bore from the front face to Y 32.65: a 7.8 mm split ring, a saddle and an 8.0 mm '
                   'ring. R58 is the fitted reference that gripped. R62 has the same nominal bore and did not pass the rod when printed; '
                   'its extra 11 mm tail at 8.36 mm ended on the bed face. R63 bored everything to 8.55 mm and added the collet.'),
        zones=table, r58_to_r62_radius_difference_mm=rnd(same(r58, profiles['r62'], 32.3)),
        r69_to_r62_radius_difference_to_y31_75_mm=rnd(same(profiles['r69'], profiles['r62'], 31.8)),
        rear_ring_lead_in=list(d.REAR_RING_LEAD), restored_mm3=rnd(d.grip_restore().volume(), 2),
        nominal_8mm_rod_overlap_mm3=dict(r62=mm3(d.r62_carrier(), full), r68=mm3(parts68['carrier'], full), r69=mm3(body, full)),
        smallest_bore_mm=rnd(2 * min(r[1] for r in profiles['r69'])), bed_face_bore_mm=rnd(2 * profiles['r69'][-1][1]),
        collet='Rod_Collet is no longer part of the kit. The rear socket it seated in is kept as the rear funnel.',
        not_measured='grip torque and slide force of the printed ring on the bought rod')
    r = report
    z = r['zones']
    r['gates'] = [r['r58_to_r62_radius_difference_mm'] < .02, r['r69_to_r62_radius_difference_to_y31_75_mm'] < .02,
                  abs(z['front_ring']['r69']['bore_diameter_mm'][0] - 7.8) < .01 and z['front_ring']['r68']['bore_diameter_mm'][0] > 8.5,
                  abs(z['rear_ring']['r69']['bore_diameter_mm'][0] - 8.0) < .01,
                  z['behind']['r69']['bore_diameter_mm'][0] >= 8.5 and z['rear_funnel']['r69']['bore_diameter_mm'][0] >= 8.55,
                  r['bed_face_bore_mm'] >= 9.0, r['smallest_bore_mm'] >= 7.79]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- carrier
CHANGED = dict(op1_seat=(-12., 14.5, -14., 27.5, 4.5, 12.7), guard_arm=(8.5, 23., 8.0, 23.0, -1.0, 8.4),
               strip_left=(-23., -19., 8.4, 11.1, 7.2, 11.2), strip_right=(19., 23., 8.4, 11.1, 7.2, 11.2),
               right_stub=(3.8, 11.6, 2.4, 17.6, .9, 6.6), rod_bore=(-4.4, 4.4, -20., 32.75, -4.4, 4.4), hinge=(-36., 36., 27.6, 43.66, 8.6, 33.))


def carrier(parts69, parts68):
    body, before = parts69['carrier'], parts68['carrier']
    zones = b.union([b.box(*v) for v in CHANGED.values()])
    outside = b.box(-200, 200, -200, 200, -200, 200) - zones
    battery = b.box(*r68.RESTORE_BOX)
    strips = {}
    for side, sign in (('left', -1), ('right', 1)):
        x0, x1, y0, y1 = d.STRIP_WINDOW
        probe = b.box(*sorted((sign * x0, sign * x1)), y0, y1, d.DECK + .05, float(d.base.plate_top()) - .05)
        strips[side] = dict(r68_open_mm3=rnd(probe.volume() - mm3(before, probe)), r69_open_mm3=rnd(probe.volume() - mm3(body, probe)))
    checked, obstructions, sweeps = c66.key_routes(body)
    mass = {name: dict(r68_g=rnd(parts68[name].volume() * PETG), r69_g=rnd(parts69[name].volume() * PETG)) for name in ('carrier', 'paddle', 'lid')}
    mass['rod_collet'] = dict(r68_g=rnd(b.load(r66.collet_file()).volume() * PETG), r69_g=0.0)
    report = dict(
        revision='R69', physical_fit_verified=False, r68_carrier_sha256=d.R68_SHA256,
        key_deck=dict(strips=strips, origin='carrier58.move_upper_row left a through-window in the strip between the rows on each side'),
        key_poses_checked=checked, key_obstructions=obstructions, socket_backer_sweeps_mm3=sweeps,
        battery_box_sections_against_r68=c67.section_difference(before ^ battery, body ^ battery),
        outside_changed_zones_sections_against_r68=c67.section_difference(before ^ outside, body ^ outside),
        changed_zones_mm={kk: list(v) for kk, v in CHANGED.items()}, components=len(body.decompose()), mass=mass,
        mass_total_g=dict(r68=rnd(sum(v['r68_g'] for v in mass.values())), r69=rnd(sum(v['r69_g'] for v in mass.values()))))
    r = report
    r['gates'] = [not obstructions and checked == 336, max(sweeps.values()) < .01,
                  all(v['r69_open_mm3'] < .01 < v['r68_open_mm3'] for v in strips.values()),
                  r['battery_box_sections_against_r68']['max_area_mm2'] < .0025,
                  r['outside_changed_zones_sections_against_r68']['max_area_mm2'] < .01, r['components'] == 1]
    r['passes'] = all(r['gates'])
    return report


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def rnd(v, n=3):
    return round(float(v), n)


def board_frame(shape):
    m = np.eye(4)
    m[:3] = np.asarray(b.board_matrix())
    return shape.transform(np.linalg.inv(m)[:3].tolist())


# ----------------------------------------------------------------------- hinge
def touch_board():
    return k.r.sensor().translate((0, k.r.CLICK_SHIFT, 0)).transform(r61.FLIP)


def hinge_distances(paddle, wires, module):
    edge = float(touch_board().bounding_box()[4])
    barrel = paddle ^ b.box(-7, 7, module.AXIS - 3.4, module.AXIS + 3.4, module.KEEPER_Z - 3.4, module.KEEPER_Z + 3.4)
    return dict(board_top_edge_y_mm=rnd(edge), axis_y_mm=module.AXIS,
                edge_to_barrel_front_mm=rnd(module.AXIS - module.BARREL_R - edge), edge_to_pin_axis_mm=rnd(module.AXIS - edge),
                edge_to_paddle_rear_end_mm=rnd(paddle.bounding_box()[4] - edge),
                edge_to_cheek_block_rear_mm=rnd(module.REAR - .45 - edge),
                edge_to_nominal_lead_rear_mm=rnd(wires.bounding_box()[4] - edge),
                mated_plug_to_paddle_gap_mm=rnd(r61.plug().min_gap(paddle, 4.0)))


def barrel_bridge(paddle):
    """The paddle prints seat-down. Between the two posts the flat barrel top is a bridge. — Claude Fable 5.2"""
    top = hinge69.KEEPER_Z + hinge69.BARREL_R - hinge69.BARREL_FLAT
    span = (hinge69.LEFT_POST_X[1], hinge69.POST_X[0])
    strip = paddle.slice(top - .05) ^ mf.CrossSection.square((span[1] - span[0], 8)).translate((span[0], hinge69.AXIS - 4))
    posts = paddle.slice(b.SEAT_Z - .1) ^ mf.CrossSection.square((16, 3)).translate((-8, hinge69.AXIS - 1.5))
    return dict(span_mm=rnd(span[1] - span[0]), first_layer_width_mm=rnd(strip.bounds()[3] - strip.bounds()[1]),
                height_above_bed_mm=rnd(b.SEAT_Z - top), posts_on_bed_mm2=rnd(posts.area()),
                posts_on_bed=len(posts.decompose()), rear_web_volume_mm3=rnd(mm3(paddle, b.box(-7, 7, hinge69.AXIS + 3.35, 60, 0, 30))))


# ----------------------------------------------------------------------- keeper
def end_press(paddle, lid, fixed, module, stop_deg):
    """A press at the far end: full stroke plus 0.25 degrees, the hinge end lifted in its open
    bearings, the paddle rolled 0.8 degrees and shifted 0.20 mm sideways (the journals allow 0.16).
    Returns the worst case against the retainer and against the holder in front of the hinge. — Claude Fable 5.2"""
    station = np.array([0., b.STATION[1], b.FREE_TOP - .8])
    rows = []
    for lift in (0., .35):
        for roll in (-.8, 0., .8):
            for shift in (-.20, 0., .20):
                pose = paddle.translate(-module.PIVOT).rotate((stop_deg + .25, 0, 0)).translate(module.PIVOT)
                heel = math.degrees(lift / (module.AXIS - station[1]))
                pose = pose.translate(-station).rotate((heel, roll, 0)).translate(station + np.array([shift, 0, 0]))
                rows.append(dict(lift=lift, roll=roll, shift=shift, to_retainer_mm3=mm3(pose, lid), to_fixed_mm3=mm3(pose, fixed),
                                 gap_to_retainer_mm=rnd(pose.min_gap(lid, 3.0))))
    worst = max(rows, key=lambda r: (r['to_retainer_mm3'], -r['gap_to_retainer_mm']))
    return dict(poses=len(rows), worst_pose=worst, max_overlap_with_retainer_mm3=max(r['to_retainer_mm3'] for r in rows),
                max_overlap_with_carrier_and_board_mm3=max(r['to_fixed_mm3'] for r in rows),
                least_gap_to_retainer_mm=min(r['gap_to_retainer_mm'] for r in rows))


def rest_gaps(paddle, lid):
    """Vertical room over each retainer post at rest (board frame). — Claude Fable 5.2"""
    p, l = board_frame(paddle), board_frame(lid)
    out = {}
    for side, sign in (('left', -1), ('right', 1)):
        zone = b.box(*sorted((sign * 5.0, sign * 7.3)), -5.2, 1.0, 12.4, 30)
        post = l ^ zone
        over = p ^ b.box(*sorted((sign * 5.0, sign * 7.3)), -5.2, 1.0, float(post.bounding_box()[5]), 30)
        out[side] = dict(post_top_z_mm=rnd(post.bounding_box()[5]), paddle_underside_over_post_z_mm=rnd(over.bounding_box()[2]),
                         room_mm=rnd(over.bounding_box()[2] - post.bounding_box()[5]))
    return out


# ----------------------------------------------------------------------- OP1 seat and plug entry
def seat_openings(body):
    """Openings through the board floor just under the seat, inside the board outline. — Claude Fable 5.2"""
    floor = board_frame(body).slice(d.SEAT - .15)
    outline = mf.CrossSection.square((9.6, 29.2)).translate((-4.8, -8.6))
    holes = sorted((outline - floor).decompose(), key=lambda s: s.bounds()[1])
    return [dict(area_mm2=rnd(h.area(), 2), u_mm=[rnd(h.bounds()[0], 2), rnd(h.bounds()[2], 2)], v_mm=[rnd(h.bounds()[1], 2), rnd(h.bounds()[3], 2)])
            for h in holes if h.area() > .05]


def plug_box(margin, yaw):
    """The tipped plug (lead straight down) grown by `margin` per side, centred on the origin,
    its wide side along the rod turned by `yaw` degrees. — Claude Fable 5.2"""
    thick, wide, long = (v + 2 * margin for v in PLUG_ESTIMATE)
    return b.box(-thick / 2, thick / 2, -wide / 2, wide / 2, -long / 2, long / 2).rotate((0, 0, float(yaw)))


def obstacles(body):
    keys = r66.r64.fitted_key_hardware()
    return b.union([body, *keys.values()])                 # the 500 mm rod is one of the fitted parts


def largest_plug(body, heights=np.arange(-14., 13.01, 1.0), *, hand_reference=None):
    """Largest uniform margin round the estimated plug that still rises from below the rod to
    above the seat on some vertical line, without touching the holder, the rod or a fitted key. — Claude Fable 5.2"""
    fixed = obstacles(body) ^ b.box(0., 16., 2., 24., heights[0] - 5., heights[-1] + 5.)
    candidates = [(float(x), float(y)) for x in np.arange(5.5, 10.01, .5) for y in np.arange(10.5, 16.01, .5)]
    if hand_reference is not None:
        # The widest plug route can be harder to reach. Preserve hand access before
        # optimizing its size; the exported guide uses this same selected route. — GPT-6.1 Sol
        accessible = []
        below = [f'z{z:g}' for z in np.arange(-3.5, 3.51, 1.0)]
        for x, y in candidates:
            room, prior = outboard_room(body, (x, y)), outboard_room(hand_reference, (x, y))
            if (min(room[z] for z in below) >= 6.5
                    and min(room[z] for z in below) >= min(prior[z] for z in below) + 2.5
                    and all(room[z] >= prior[z] + 2 for z in ('z0.5', 'z1.5', 'z2.5', 'z3.5'))):
                accessible.append((x, y))
        assert accessible, 'No plug route meets the existing hand-access requirements'
        candidates = accessible
    best = dict(margin_mm=-1.0)
    for yaw in (-20.5, -10., 0., 10.):                      # the board's angle, either side of R66's, along the rod
        for x, y in candidates:
            column = lambda m: b.union([plug_box(m, yaw).translate((float(x), float(y), float(z))) for z in heights])
            if mm3(fixed, column(0.0)) > 1e-4:
                continue
            lo, hi = 0.0, 2.5
            for _ in range(7):
                mid = (lo + hi) / 2
                if mm3(fixed, column(mid)) > 1e-4:
                    hi = mid
                else:
                    lo = mid
            if lo > best['margin_mm']:
                best = dict(margin_mm=rnd(lo), centre_world_xy_mm=[rnd(x, 2), rnd(y, 2)], wide_side_yaw_deg=yaw)
    return best


def outboard_room(body, centre):
    """Room on the guard side of the plug's path, by height below the deck: from the path
    centre outward (+X) to the first holder material, in a 5 mm band. This is where a
    fingertip or tweezers must reach; the rod is on the other side. — Claude Fable 5.2"""
    cx, cy = centre
    rows = {}
    for z in np.arange(-3.5, 6.51, 1.0):
        section = body.slice(float(z)) ^ mf.CrossSection.square((25., 5.0)).translate((cx, cy - 2.5))
        rows[f'z{z:g}'] = rnd((section.bounds()[0] if not section.is_empty() else cx + 25.) - cx, 2)
    return rows


# ----------------------------------------------------------------------- rod
def bore_profile(body, y0=5.75, y1=43.5, step=.5):
    turned = body.rotate((90, 0, 0))
    rows = []
    for y in np.arange(y0, y1, step):
        section = turned.slice(float(y)) ^ mf.CrossSection.circle(5.6, 96)
        radius, wrap = 9.0, 0
        pts = [np.asarray(p, float) for p in section.to_polygons() if len(p) >= 3]
        if pts:
            dense = np.vstack([(p[:, None, :] * (1 - t) + np.roll(p, -1, axis=0)[:, None, :] * t).reshape(-1, 2)
                               for p in pts for t in [np.linspace(0, 1, 9)[None, :, None]]])
            dist = np.hypot(dense[:, 0], dense[:, 1])
            radius = float(dist.min())
            near = dense[dist < radius + .12]
            wrap = len(set((np.degrees(np.arctan2(near[:, 1], near[:, 0])) % 360).astype(int)))
        rows.append((rnd(y, 2), rnd(radius), wrap))
    return rows


def zone(rows, y0, y1):
    part = [r for r in rows if y0 <= r[0] <= y1]
    return dict(y_mm=[y0, y1], bore_diameter_mm=[rnd(2 * min(r[1] for r in part)), rnd(2 * max(r[1] for r in part))],
                wrap_deg=[min(r[2] for r in part), max(r[2] for r in part)])


# ----------------------------------------------------------------------- main
def write(name, report, hashes):
    report['meshes_sha256'] = hashes
    report['carrier_sha256'] = hashes[d.HOLDER]
    report['generator_sha256'] = {Path(m.__file__).name: digest(m.__file__) for m in (d, hinge69)}
    (OUT / name).write_text(json.dumps(report, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)) + '\n')
    print(name, 'passes', report['passes'], report.get('gates'), flush=True)

if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
