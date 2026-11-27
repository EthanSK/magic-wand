"""R71 CAD checks. Each report puts the printed R70 beside R71 and is bound to the R71 mesh
hashes. Nothing here is a slice, a print or a fit in the hand.

    carrier.json   what did not change (sections against R70), the re-routed left guard, the
                   mirrored rear outline, the click with the eased hinge, the post ribs against R70's
                   native slice, the spring clips, the round edges
    battery.json   where the pouch sits, what limits it, every loading route, the spring, removal
    base.json      nine pieces; each base fin's one neck beside the holder and its sections

The limits in battery.json are read from the fitted switch and socket models, not from
the constants in design71: the check fails if the two disagree.
 — Claude Fable 5.2"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import design71 as d
import hinge71
import kit71
import checks70 as c70

r70, old, b, r66, r61, hinge70 = d.r70, d.old, d.b, d.r66, d.r61, hinge71.h70
fit, c66, c67, kit70 = c70.fit, c70.c66, c70.c67, kit71.kit70
OUT = d.OUT
mm3, rnd, digest, PETG = c70.mm3, c70.rnd, c70.digest, c70.PETG
SAME = (hinge71.WIRES, hinge71.LID)                         # R70's files, byte for byte
MESHES = (d.HOLDER, hinge71.PADDLE, hinge71.POST_BAR, *hinge71.CLIPS.values(), *SAME)
R71_PARTS = {name: OUT / name for name in MESHES}
R70_PARTS = {name: r70.OUT / name for name in MESHES}
R70_PARTS.update({hinge71.CLIPS[side]: path for side, path in hinge71.R59_CLIPS.items()})     # R70 printed the R59 clips
REPORTS = ('carrier.json', 'battery.json', 'base.json')
BOARD_G = 5.0               # assumed mass the two clips hold down: the touch board (about 2.2 g of laminate by its modelled volume), its connector, the plug and the wire it carries. Not weighed.


def main(only=None):
    new = {n: b.load(p) for n, p in R71_PARTS.items()}
    prev = {n: b.load(p) for n, p in R70_PARTS.items()}
    hashes = {n: digest(p) for n, p in R71_PARTS.items()}
    makers = {'carrier.json': lambda: carrier(new, prev), 'battery.json': lambda: battery(new, prev), 'base.json': base}
    results = {}
    if only and 'carrier.json' not in only:
        old.k.old.configure_new_op1()                      # otherwise hinge_fit64.run does it, exactly once
    for name in REPORTS:
        if only and name not in only:
            continue
        results[name] = makers[name]()
        write(name, results[name], hashes)
    if only:
        return
    summary = dict(revision='R71', physical_fit_verified=False, sliced=False, meshes_sha256=hashes, checks_sha256=digest(__file__),
                   **{n.replace('.json', '') + '_passes': v['passes'] for n, v in results.items()})
    summary['passes'] = bool(all(v['passes'] for v in results.values()) and len(results) == len(REPORTS))
    (OUT / 'checks.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=1), flush=True)
    if not summary['passes']:
        sys.exit('R71 checks failed')


def write(name, report, hashes):
    report['meshes_sha256'] = hashes
    report['carrier_sha256'] = hashes[d.HOLDER]
    report['generator_sha256'] = {Path(m.__file__).name: digest(m.__file__) for m in (d, hinge71, r70, hinge70, kit71)}
    (OUT / name).write_text(json.dumps(report, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else float(o) if isinstance(o, np.floating) else str(o)) + '\n')
    print(name, 'passes', report['passes'], report.get('gates'), flush=True)


def box_of(shape, n=2):
    return [rnd(v, n) for v in shape.bounding_box()]


# ----------------------------------------------------------------------- carrier
def bank_outlines(body, z0, z1):
    """Filled outer outlines of the two key banks' plates in one height band: left, and right mirrored."""
    plan = (body ^ b.box(-80, 80, -80, 80, z0, z1)).project()
    filled = mf.CrossSection([ring for ring in plan.to_polygons() if r70._area(ring) > 0])
    left = filled ^ mf.CrossSection.square((60., 200.)).translate((-60. - d.BANK_FROM, -100.))
    right = filled ^ mf.CrossSection.square((60., 200.)).translate((d.BANK_FROM, -100.))
    return left, right.mirror((1., 0.))


def rear_outline(body):
    """Left against mirrored right, behind the taper line: the plate's outline, and the deck level with the rail's roof strip."""
    behind = mf.CrossSection.square((200., d.BED - .05 - d.TAPER_FROM_Y)).translate((-100., d.TAPER_FROM_Y))
    rows = {}
    for name, z0, z1 in (('plate_above_the_deck_edge_round', d.DECK + r70.EDGE_R + .15, d.PLATE_TOP - r70.TOP_R - .15), ('deck_level', d.DECK + .1, d.DECK + 1.0)):
        left, mirrored = (outline ^ behind for outline in bank_outlines(body, z0, z1))
        rows[name] = dict(left_only_mm2=rnd((left - mirrored).area(), 2), right_only_mm2=rnd((mirrored - left).area(), 2))
    return rows


def enclosing_diameter(bar, sign, z):
    """Smallest circle round one post's CAD section at a height. The section is symmetric about
    the post's fore-aft line, so the circle's centre lies on it. — Claude Fable 5.2"""
    px, py = sign * hinge70.b.HOLE_X, hinge70.b.HOLE_Y
    section = bar.slice(float(z)) ^ mf.CrossSection.square((8., 8.)).translate((px - 4., py - 4.))
    points = np.vstack([np.asarray(ring) for ring in section.to_polygons()]) - (px, py)
    return rnd(2 * min(float(np.max(np.hypot(points[:, 0], points[:, 1] - cy))) for cy in np.arange(-.6, .8, .002)), 3)


def post_fit(bar, old_bar, paddle):
    """The post in the board's thickness, layer by layer. CAD sections of R70 and R71, beside what
    R70's own native slice measured. R71's first three layers have the section R70's first layer
    had, which that slice printed 3.049 mm across. Above them the printed size is predicted from
    the CAD size less the difference measured on R70. — Claude Fable 5.2"""
    bb, layer = hinge70.b, hinge71.LAYER
    native = json.loads((r70.OUT / 'print-mechanisms/mechanical-sections.json').read_text())
    measured = {row['board_plane_z_mm']: row['smallest_enclosing_diameter_mm'] for row in native['post_fit']['r70']['left']}
    planes = [rnd(bb.SEAT_Z + layer * (k + .5), 2) for k in range(round((bb.BOARD_TOP - bb.SEAT_Z) / layer))]
    cad = {rev: [enclosing_diameter(shape, -1, z) for z in planes] for rev, shape in (('r70', old_bar), ('r71', bar))}
    offsets = [rnd(cad['r70'][planes.index(z)] - measured[z], 3) for z in (planes[0], planes[-1])]      # the two planes R70's report shares with a layer middle
    rows = []
    for k, z in enumerate(planes):
        same = abs(cad['r71'][k] - cad['r70'][0]) < .002
        rows.append(dict(layer=k + 1, plane_z_mm=z, above_the_seat_mm=[rnd(k * layer, 1), rnd((k + 1) * layer, 1)], cad_mm=dict(r70=cad['r70'][k], r71=cad['r71'][k]),
                         r70_native_mm=measured.get(z), r71_expected_native_mm=[measured[planes[0]]] * 2 if same else [rnd(cad['r71'][k] - max(offsets), 3), rnd(cad['r71'][k] - min(offsets), 3)],
                         r71_same_section_as_r70_first_layer=bool(same)))
    stop = hinge71.LIFT
    at = lambda lift: rows[min(int((lift + 1e-9) / layer), len(rows) - 1)]
    head = (bar ^ b.box(-hinge70.b.HOLE_X - 3, -hinge70.b.HOLE_X + 3, hinge70.b.HOLE_Y - 3, hinge70.b.HOLE_Y + 3, bb.BOARD_TOP + .01, 60))
    plan = head.project()
    points = np.vstack([np.asarray(ring) for ring in plan.to_polygons()]) - (-hinge70.b.HOLE_X, hinge70.b.HOLE_Y)
    over = rnd(2 * min(float(np.max(np.hypot(points[:, 0], points[:, 1] - cy))) for cy in np.arange(-.6, .8, .002)), 3)
    holes = []
    for hole in (3.0, 3.1, 3.2):
        seated, lifted = at(0.)['r71_expected_native_mm'], at(stop)['r71_expected_native_mm']
        holes.append(dict(hole_mm=hole, seated_squeeze_on_diameter_mm=rnd(seated[0] - hole, 3), at_the_wing_stop_squeeze_on_diameter_mm=rnd(lifted[0] - hole, 3),
                          r70_at_the_same_lift_expected_mm=[rnd(cad['r70'][1] - max(offsets) - hole, 3), rnd(cad['r70'][1] - min(offsets) - hole, 3)]))
    return dict(
        source=('R70 native slice %s: its post rows at the first and last layer middles. Positive squeeze: the ribs must give by that much. '
                'Negative: clear. R71 has not been sliced; its rows are expectations, not measurements.' % native['archive_sha256'][:12]),
        cad_minus_native_on_r70_mm=offsets, full_section_layers=sum(row['r71_same_section_as_r70_first_layer'] for row in rows), full_section_height_mm=hinge71.RIB_FULL,
        layers=rows, holes=holes, largest_lift_under_the_clip_mm=rnd(stop, 2),
        left_post_box_in_the_board_mm=dict(r70=box_of(old_bar ^ b.box(-12, 0, 10, 20, bb.SEAT_Z + .01, bb.BOARD_TOP - .01), 3), r71=box_of(bar ^ b.box(-12, 0, 10, 20, bb.SEAT_Z + .01, bb.BOARD_TOP - .01), 3)),
        pushed_up_through_the_paddle_mm3=max(mm3(bar.translate((0, 0, -float(t))), paddle) for t in np.arange(0, 9.01, .25)),
        seated_in_the_paddle_mm3=mm3(bar, paddle),
        post_above_the_board_fits_a_circle_of_mm=over, added_mm3=rnd((bar - old_bar).volume(), 3), removed_mm3=rnd((old_bar - bar).volume(), 3),
        unchanged_outside_ribs_and_nose_mm3=rnd(c67_volume_outside(bar, old_bar), 4),
        reading=('The board can rise %.2f mm before the clip\'s frame stops it, and only by bending the clip\'s arms. Through that whole travel the hole\'s lower edge stays on layers with the '
                 'full rib section. Real hole size and pitch are not measured: a hole above %.2f mm is clear of the ribs at every height.' % (stop, measured[planes[0]])))


def c67_volume_outside(bar, old_bar):
    """What differs between the two bars away from the ribs and the nose: nothing should."""
    bb = hinge70.b
    zones = b.mirrored(b.box(bb.HOLE_X - 2., bb.HOLE_X + 2., bb.HOLE_Y - 2., bb.HOLE_Y + 2., bb.SEAT_Z - .01, bb.BOARD_TOP + .01)
                       + b.box(bb.HOLE_X - 1., bb.HOLE_X + 1., bb.HOLE_Y - 1.5, bb.HOLE_Y, bb.BOARD_TOP + hinge71.NECK - .01, bb.BOARD_TOP + hinge71.NOSE_TOP + .01))
    return float(((bar - old_bar) - zones).volume() + ((old_bar - bar) - zones).volume())


def touch_board():
    """The nominal DFR0030 board at its seat, as the inherited click check places it."""
    return fit.k.r.sensor().translate((0, fit.k.r.CLICK_SHIFT, 0)).transform(fit.r61.FLIP)


def clip_print_layers(side):
    """The exported clip in its print pose (top face down), cut at the middle of each 0.2 mm
    layer: every island has to stand on the layer below, and nothing may overhang it by more
    than 0.3 mm. CAD sections, not a slice. — Claude Fable 5.2"""
    source = OUT / hinge71.CLIPS[side]
    shape = kit71.printer.load_solid(source).transform(kit71.printer.pose_for(source, *kit71.CLIP_PRINT)[:3])
    low, high = float(shape.bounding_box()[2]), float(shape.bounding_box()[5])
    below, counts, starts, over = None, [], [], 0.
    for k in range(round((high - low) / hinge71.LAYER)):
        section = shape.slice(low + hinge71.LAYER * (k + .5))
        pieces = [piece for piece in section.decompose() if piece.area() > .005]
        counts.append(len(pieces))
        if below is not None:
            starts += [dict(layer=k + 1, area_mm2=rnd(piece.area(), 3)) for piece in pieces if (piece ^ below).area() < 1e-4]
            over = max(over, float((section - below.offset(.30, mf.JoinType.Round)).area()))
        below = section
    return dict(layers=len(counts), islands_per_layer=counts, islands_starting_on_nothing=starts, largest_overhang_beyond_0_3_mm_mm2=rnd(over, 4),
                first_layer_mm2=rnd(shape.slice(low + hinge71.LAYER / 2).area(), 2))


def clip_fit(side, clip, flat, bar, old_bar, board, paddle):
    """The spring clip on its post in three poses: as exported (frame up against the head's
    ledges, arms unbent, so the feet stand in the board model), fitted (arms bent, heels on the
    board) and pressed flat for sliding on. `flat` is the R59 clip, which must still fit. — Claude Fable 5.2"""
    _, box, post, axis = hinge71.clip_frame(side)
    z0 = float(box[0, 2])
    numbers = hinge71.clip_numbers(side)
    fitted, pressed = hinge71.spring_clip(side, hinge71.LIFT, hinge71.PRESS), hinge71.spring_clip(side, 0., hinge71.FOOT)
    near = mf.CrossSection.square((6., 6.)).translate((float(post[0]) - 3., float(post[1]) - 3.))
    cell = b.box(float(post[0]) - 3., float(post[0]) + 3., float(post[1]) - 3., float(post[1]) + 3., z0 + hinge71.NECK - .01, 80)

    def ledges(shape):
        """Head wings and nose only: what overhangs the neck from the head's underside up."""
        return (shape ^ cell) - mf.Manifold.extrude(shape.slice(z0 + 1.0) ^ near, 6.).translate((0, 0, z0))

    def bearing(shape):
        under = (ledges(shape) ^ b.box(-80, 80, -80, 80, z0 + hinge71.NECK - .02, z0 + hinge71.NECK + .05)).project()
        top = (fitted ^ b.box(-80, 80, -80, 80, z0 + hinge71.NECK - .05, z0 + hinge71.NECK + .01) ^ b.box(float(post[0]) - hinge71.FRAME_HALF - .01, float(post[0]) + hinge71.FRAME_HALF + .01, -80, 80, -80, 80)).project()
        return rnd((under ^ top).area(), 3)

    back = lambda shape, short=0., up=0.: shape.translate((float(axis[0]) * short, float(axis[1]) * short, up))
    rise = next((rnd(v, 2) for v in np.arange(0, .41, .01) if mm3(hinge71.spring_clip(side, float(v), hinge71.FOOT - float(v)), bar) > 1e-5), None)
    lift = lambda shape: next((rnd(v, 2) for v in np.arange(0, 1.21, .01) if mm3(back(shape, 0., float(v)), bar) > 1e-5), None)
    steps = np.arange(0, 8.01, .1)
    throat = lambda shape: max(mm3(back(shape, float(u)), bar) for u in steps)
    feet = (fitted ^ b.box(-80, 80, -80, 80, z0 - .01, z0 + .15)).project()                        # under the lifted frame: the two feet only
    seat = (paddle ^ b.box(-80, 80, -80, 80, hinge70.b.SEAT_Z - .05, hinge70.b.SEAT_Z + .02)).project()
    size = np.reshape(clip.bounding_box(), (2, 3))
    frame, arms, _ = hinge71.clip_plans(side)
    slab = lambda plan: mf.Manifold.extrude(plan, 1.)
    in_front = mf.CrossSection.square((20., 20.)).translate((-10., -hinge71.ARM_ROOT + .25))          # in front of the half-round slot ends on the rear bar
    voids = hinge71.clip_voids(side)
    weight = BOARD_G * 9.81e-3
    return dict(numbers, size_mm=[rnd(v, 2) for v in size[1] - size[0]], volume_mm3=dict(r59=rnd(flat.volume(), 2), r71=rnd(clip.volume(), 2)),
                exported_pose=dict(what='frame against the head\'s ledges, arms unbent', into_the_post_mm3=mm3(clip, bar), feet_into_the_board_model_mm3=mm3(clip, board)),
                fitted_pose=dict(what='arms bent %.1f mm, the heels of the feet on the board' % hinge71.PRESS, into_the_post_mm3=mm3(fitted, bar), into_the_board_mm3=mm3(fitted, board),
                                 frame_above_the_board_mm=rnd(hinge71.LIFT, 2), feet_plan_mm2=rnd(feet.area(), 2), feet_over_the_paddle_seat_mm2=rnd((feet ^ seat).area(), 2)),
                frame_rise_to_the_ledges_mm=rise, bearing_under_the_ledges_mm2=dict(with_the_r70_head=bearing(old_bar), r71=bearing(bar)),
                pressed_flat=dict(what='frame on the board, arms bent %.1f mm' % hinge71.FOOT, into_the_board_mm3=mm3(pressed, board), into_the_post_at_home_mm3=mm3(pressed, bar),
                                  into_the_ledges_while_sliding_on_mm3=max(mm3(back(pressed, float(u)), ledges(bar)) for u in steps),
                                  room_under_the_ledges_mm=lift(hinge71.spring_clip(side, 0., 0.) ^ b.box(float(post[0]) - hinge71.FRAME_HALF - .01, float(post[0]) + hinge71.FRAME_HALF + .01, -80, 80, -80, 80))),
                snap_throat_overlap_per_mm_of_thickness_mm3=dict(r59=rnd(throat(flat) / numbers['frame_mm']['r59'], 4), r71=rnd(throat(pressed) / hinge71.CLIP_T, 4)),
                r59_clip_on_this_post=dict(into_the_post_at_home_mm3=mm3(flat, bar), lift_before_the_ledges_mm=lift(flat)),
                slots=dict(least_gap_between_arm_and_frame_mm=rnd(slab(arms ^ in_front).min_gap(slab(frame ^ in_front), 1.)),
                           open_spaces_checked={name: len(group) for name, group in voids.items()},
                           clip_inside_those_spaces_mm3=max(mm3(space, clip) for group in voids.values() for space in group)),
                print_layers=clip_print_layers(side),
                hold_down=dict(assumed_mass_g=BOARD_G, its_weight_n=rnd(weight, 3), one_clip_over_that_weight=rnd(numbers['hold_down_per_clip_n'] / weight, 1),
                               reading='the mass is an assumption, not a weighing; the frame stops a lift at %.1f mm whatever the spring does' % hinge71.LIFT),
                reading=('Pressed down on its front half, between its two feet, the clip slides on like the R59 clip, %.1f mm under the head. Let go and the two arms lift the frame against '
                         'the head\'s three ledges while the heels of their feet press the board down. Strains are bending estimates for the stated deflection and forces use a '
                         'round-figure modulus: neither is a measurement, and PETG held bent relaxes with time. A board that lifts must bend the arms further; after %.1f mm '
                         'the frame itself is in the way.' % (hinge71.LIFT, hinge71.LIFT)))


def spring_arm_gate(c):
    """The arm against the first spring clip's own figures (4.4 % pressed flat, 2.2 % seated, as
    that clip was reported): at most half of each, by the stricter estimate that loads the
    heel. The largest strain has to lie in the plain strip, with less at every root step and
    under half of it at the rear bar. Hold-down: each clip alone at least ten times the
    assumed weight, and less than the first clip asked of the board. No elastic limit is
    assumed anywhere. — Claude Fable 5.2"""
    arm, was = c['arm'], c['arm']['first_spring_clip']
    said = was['loaded_at_the_middle_of_the_foot_as_first_reported']
    return bool(arm['bending_strain_while_pressed_flat'] <= .5 * said['bending_strain_while_pressed_flat']
                and arm['bending_strain_when_seated'] <= .5 * said['bending_strain_when_seated']
                and arm['pressed_flat_strain_over_the_first_spring_clip'] <= .40 and arm['largest_strain_in_the_plain_arm']
                and all(step['strain_in_front_while_pressed_flat'] < arm['bending_strain_while_pressed_flat'] for step in arm['root_steps'])
                and arm['strain_at_the_rear_bar_while_pressed_flat'] <= .5 * arm['bending_strain_while_pressed_flat']
                and c['hold_down']['one_clip_over_that_weight'] >= 10. and c['hold_down_per_clip_n'] < c['first_spring_clip']['hold_down_per_clip_n']
                and c['press_to_fit_per_clip_n'] <= 5.
                and c['rear_bar']['arm_root_moment_while_pressed_flat_n_mm']['r71'] <= .5 * c['rear_bar']['arm_root_moment_while_pressed_flat_n_mm']['first_spring_clip'])


def fastener_sweep(new, click, board):
    """Both clips (fitted pose) and the post bar ride on the paddle through the lift and click
    poses, against everything fixed. The inherited click check uses the R57 bar and R59 clips. — Claude Fable 5.2"""
    purchased = fit.k.q.hardware()
    fixed = new[d.HOLDER] + new[hinge71.LID] + hinge70.pin() + b.union(purchased[n] for n in ('board', 'plug', 'sockets', 'op1_wire', 'housing', 'terminals', 'switch'))
    clips = b.union([hinge71.spring_clip(side, hinge71.LIFT, hinge71.PRESS) for side in hinge71.CLIPS])
    riding = new[hinge71.POST_BAR] + clips
    old = b.union([b.load(R70_PARTS[hinge71.POST_BAR]), *(b.load(path) for path in hinge71.R59_CLIPS.values())])
    poses = np.linspace(-click['lift_stop_deg'] + .025, click['case_stop_deg'] - .035, 19)
    plug = fit.r61.housing() + fit.r61.plug() + new[hinge71.WIRES]
    slide = [hinge71.spring_clip('Left', 0., hinge71.FOOT).translate((0, -float(u), 0)) for u in np.arange(0, 8.01, .5)]
    outside = clips.project() - board.project().hull()
    return dict(poses=len(poses), into_holder_retainer_pin_and_op1_mm3=max(mm3(hinge70.rotate(riding, a), fixed) for a in poses),
                least_gap_mm=dict(r70=rnd(min(hinge70.rotate(old, a).min_gap(fixed, 5.) for a in poses)), r71=rnd(min(hinge70.rotate(riding, a).min_gap(fixed, 5.) for a in poses))),
                clips_to_plug_housing_and_wires_mm=rnd(clips.min_gap(plug, 6.)), clips_to_paddle_mm3=mm3(clips, new[hinge71.PADDLE]),
                clip_plan_beyond_the_board_edge_mm2=rnd(outside.area(), 3), clip_to_the_board_edge_mm=rnd(float(board.bounding_box()[3]) - float(clips.bounding_box()[3]), 2),
                clip_sliding_on_over_board_and_paddle_mm3=max(mm3(pose, board + new[hinge71.PADDLE]) for pose in slide),
                paddle_with_fasteners_lowered_into_the_holder_mm3=max(mm3(riding.translate((0, 0, float(z))), new[d.HOLDER] + new[hinge71.LID]) for z in np.arange(0, 19.1, .4)))


def inside_the_taper(body, deck):
    """The left bank from the deck up, behind the taper line, well inside the mirrored outline:
    the taper cut may only take the shoulder outside it, never an opening. — Claude Fable 5.2"""
    keep = d.mirrored_right_plan(body).offset(-(r70.EDGE_R + .40), mf.JoinType.Round)
    return keep.extrude(60.).translate((0, 0, deck + .03)) ^ b.box(-80, -d.BANK_FROM - .30, d.TAPER_FROM_Y - 1.20, d.BED - 1.0, deck + .03, 80)


def carrier(new, prev):
    body, before = new[d.HOLDER], prev[d.HOLDER]
    paddle, old_paddle = new[hinge71.PADDLE], prev[hinge71.PADDLE]
    then = json.loads((r70.OUT / 'hinge.json').read_text())
    assert then['meshes_sha256'][d.HOLDER] == digest(R70_PARTS[d.HOLDER]), 'the R70 hinge report is not bound to the R70 carrier'
    fit.h = hinge70
    click = fit.run(*(R71_PARTS[n] for n in (d.HOLDER, hinge71.PADDLE, hinge71.WIRES, hinge71.LID)))
    same = ('button_contact_deg', 'case_stop_deg', 'lift_stop_deg', 'plunger_travel_at_case_mm', 'reversed_plunger_travel_mm')
    built = dict(d.steps())
    deck, edge = d.DECK, r70.EDGE_R
    front = d.r62.CROWN_END[1] - d.BAR_R - d.OLD_SKIN - .10          # the guard is R70's in front of this
    zones = dict(
        right_of_the_old_rail=b.box(-8.20, 80, -80, 80, -80, 80),
        left_in_front_of_the_guard_crown=b.box(-80, -8.20, -80, front, -80, 80),
        left_deck_in_front_of_the_rail=b.box(-80, -8.20, front, d.RAIL_FROM_Y - .30, deck + .03, deck + edge + .15),
        left_bank_above_its_rounded_edge=b.box(-80, -8.20, front, d.TAPER_FROM_Y - 1.20, deck + edge + .15, 80))
    inside = inside_the_taper(built['short_holder'], deck)
    sections = {name: c67.section_difference(before ^ zone, body ^ zone) for name, zone in zones.items()}
    rails = r70.guard_rails().project().offset(.5, mf.JoinType.Round)
    keep = {'guard rail enters the deck here': rails, 'battery rail hangs from the deck here': r70.hanging_keep(built['battery']).project()}
    lower = c70.edge_profile(body, r70.bank_outline(r70.plate_plan(built['battery'])), deck, 1, edge, keep)
    lower.pop('samples', None)
    lower['r70_round_share'] = json.loads((r70.OUT / 'edges.json').read_text())['lower_edge']['r70']['round_share']
    bar, board = new[hinge71.POST_BAR], touch_board()
    guard = guard_change(body, before)
    report = dict(
        revision='R71', physical_fit_verified=False, r70_carrier_sha256=digest(R70_PARTS[d.HOLDER]),
        unchanged_parts={n: digest(R71_PARTS[n]) == digest(R70_PARTS[n]) for n in SAME},
        unchanged_zones_sections_against_r70=sections,
        left_bank_inside_the_mirrored_outline=dict(removed_mm3=rnd(mm3(before ^ inside, before ^ inside) - mm3(before ^ inside, body), 3),
                                                   added_mm3=rnd(mm3(body ^ inside, body ^ inside) - mm3(body ^ inside, before), 3),
                                                   reading='from the deck up, behind the taper line: nothing is taken; the tops of the rail walls and pad ribs show in the lightening windows'),
        rear_outline_left_against_mirrored_right=dict(r70=rear_outline(before), r71=rear_outline(body), roof_strip_mm=[rnd(d.outer_wall_x()[0], 2), d.STRIP_X1],
                                                      removed_for_the_taper_mm3=rnd(mm3(built['short_holder'] - d.old_rail(), d.taper_cutter(d.mirrored_right_plan(built['short_holder']))), 1)),
        hinge=dict(report='the printed R70 hinge clicked but felt slightly stiff; the rubbing place was not identified',
                   click_values=dict(r70={n: then['click'][n] for n in same}, r71={n: click[n] for n in same}),
                   click_overlaps_mm3={n: v for n, v in click['overlap_mm3'].items() if v},
                   journal_flat_mm=hinge71.JOURNAL_FLAT, journal_radius_mm=hinge70.JOURNAL_R,
                   journal_room_above_and_below_mm=dict(r70=.035, r71=rnd(.035 + hinge71.JOURNAL_FLAT, 3)), journal_room_fore_and_aft_mm=hinge70.RADIAL_GAP,
                   journal_travel_each_way_mm=click['journal_travel_each_direction_mm']['z_0.00'],
                   paddle_to_holder_at_rest_mm=dict(r70=rnd(old_paddle.min_gap(before, 2.)), r71=rnd(paddle.min_gap(body, 2.))),
                   paddle_volume_mm3=dict(r70=rnd(old_paddle.volume(), 2), r71=rnd(paddle.volume(), 2)),
                   joint_throat_mm2=dict(r70=hinge70.joint_throat(old_paddle), r71=hinge70.joint_throat(paddle))),
        left_guard=guard,
        print_layers=dict(r70=layer_survey(before), r71=layer_survey(body),
                          reading=('R71\'s largest overhang is the wall closing over the free end of the spring tongue, which bridges 3.8 mm between two strips of the same wall. '
                                   'The re-routed guard arm and the crown bars overhang about as much per layer as R70\'s did. A native slice still has to confirm this.')),
        clips={side: clip_fit(side, new[hinge71.CLIPS[side]], prev[hinge71.CLIPS[side]], bar, prev[hinge71.POST_BAR], board, paddle) for side in hinge71.CLIPS},
        posts=post_fit(bar, prev[hinge71.POST_BAR], paddle), fasteners_through_the_click=fastener_sweep(new, click, board),
        lower_edge=lower, components=len(body.decompose()),
        source_reproduction=dict(built_mm3=rnd(built['edges'].volume(), 3), exported_mm3=rnd(body.volume(), 3)),
        build_steps_mm3={name: rnd(shape.volume(), 2) for name, shape in built.items()},
        holder_mass=dict(r70_g=rnd(before.volume() * PETG), r71_g=rnd(body.volume() * PETG)),
        kept_from_r70="rear face, hinge line, bearing blocks, rod bore, right key, OP1 seat, right guard, the left guard's lower rails and root, the posts' shaft, neck, head and height, and the retainer")
    r = report
    outline, h, clips, posts, sweep = r['rear_outline_left_against_mirrored_right'], r['hinge'], r['clips'], r['posts'], r['fasteners_through_the_click']
    throat = h['joint_throat_mm2']
    r['gates'] = [all(r['unchanged_parts'].values()), max(v['max_area_mm2'] for v in sections.values()) < .05 and r['left_bank_inside_the_mirrored_outline']['removed_mm3'] < .05,
                  max(outline['r71']['plate_above_the_deck_edge_round'].values()) < 1.0 < max(outline['r70']['plate_above_the_deck_edge_round'].values())
                  and outline['r71']['deck_level']['right_only_mm2'] < 1.0 and outline['r71']['deck_level']['left_only_mm2'] < 22.,
                  all(abs(click[n] - then['click'][n]) < .02 for n in same) and max(click['overlap_mm3'].values()) < .012,
                  h['paddle_to_holder_at_rest_mm']['r71'] >= h['paddle_to_holder_at_rest_mm']['r70'] + .03
                  and max(h['journal_travel_each_way_mm'].values()) < .19,
                  all(throat['r71'][side] >= .9 * throat['r70'][side] for side in ('left', 'right')),
                  all(c['exported_pose']['into_the_post_mm3'] == 0 and .15 <= c['exported_pose']['feet_into_the_board_model_mm3'] <= .40
                      and c['fitted_pose']['into_the_post_mm3'] == 0 and c['fitted_pose']['into_the_board_mm3'] < .02 and .19 <= c['frame_rise_to_the_ledges_mm'] <= .22
                      and c['bearing_under_the_ledges_mm2']['r71'] >= .5 and c['bearing_under_the_ledges_mm2']['r71'] > c['bearing_under_the_ledges_mm2']['with_the_r70_head']
                      and c['pressed_flat']['into_the_post_at_home_mm3'] == 0 and c['pressed_flat']['into_the_ledges_while_sliding_on_mm3'] == 0
                      and c['pressed_flat']['room_under_the_ledges_mm'] >= .18 and c['pressed_flat']['into_the_board_mm3'] < .03
                      and abs(c['snap_throat_overlap_per_mm_of_thickness_mm3']['r71'] - c['snap_throat_overlap_per_mm_of_thickness_mm3']['r59']) < .005
                      and c['layers']['r71'] == 10 and c['print_height_layers'] == 12 and spring_arm_gate(c)
                      and c['slots']['least_gap_between_arm_and_frame_mm'] >= .34 and c['slots']['clip_inside_those_spaces_mm3'] == 0
                      and c['slots']['open_spaces_checked'] == dict(spring_arm_side_slots=2, space_below_the_spring_arms=2)
                      and c['print_layers']['layers'] == 12 and not c['print_layers']['islands_starting_on_nothing'] and c['print_layers']['largest_overhang_beyond_0_3_mm_mm2'] == 0
                      and c['print_layers']['islands_per_layer'][0] == 1
                      and c['r59_clip_on_this_post']['into_the_post_at_home_mm3'] == 0 and c['r59_clip_on_this_post']['lift_before_the_ledges_mm'] >= .75 for c in clips.values())
                  and posts['full_section_layers'] == 3 and posts['largest_lift_under_the_clip_mm'] + .15 <= posts['full_section_height_mm']
                  and posts['pushed_up_through_the_paddle_mm3'] == 0 and posts['seated_in_the_paddle_mm3'] == 0 and posts['post_above_the_board_fits_a_circle_of_mm'] <= 2.75
                  and posts['unchanged_outside_ribs_and_nose_mm3'] < .002 and posts['layers'][-1]['cad_mm']['r71'] <= posts['layers'][-1]['cad_mm']['r70'] + .02
                  and posts['holes'][0]['seated_squeeze_on_diameter_mm'] == posts['holes'][0]['at_the_wing_stop_squeeze_on_diameter_mm'] > 0
                  and sweep['into_holder_retainer_pin_and_op1_mm3'] == 0 and sweep['least_gap_mm']['r71'] >= 1.0 and sweep['clips_to_paddle_mm3'] == 0
                  and sweep['clip_plan_beyond_the_board_edge_mm2'] == 0 and sweep['clip_sliding_on_over_board_and_paddle_mm3'] < .03
                  and sweep['paddle_with_fasteners_lowered_into_the_holder_mm3'] == 0,
                  lower['round_share'] >= .75 and not lower['square'],
                  r['components'] == 1 and abs(r['source_reproduction']['built_mm3'] - r['source_reproduction']['exported_mm3']) < 2.0,
                  guard['new_members_core_missing_mm3'] < .02 and guard['old_arm_and_bars_left_mm3'] < .02 and guard['lowest_z_mm']['r71'] >= guard['lowest_z_mm']['r70'] - .01
                  and guard['arm_root_section_changed_mm2'] < .05 and guard['slot_between_the_crown_and_the_pouch_nose_mm'] < 1.0
                  and guard['steepest_descent_from_the_print_axis_deg']['r71'] <= guard['steepest_descent_from_the_print_axis_deg']['r70'] + 1.,
                  not r['print_layers']['r71']['islands_starting_on_nothing']]
    r['passes'] = all(r['gates'])
    return report


def guard_change(body, before):
    """The left guard, R70 against R71: what is kept, what moved, how low it reaches and what
    it covers. — Claude Fable 5.2"""
    deck = d.DECK
    keep_y = float(d.arm_split()[0][1])
    below = b.box(-80, 80, -80, 80, -20, deck - .02)
    zone = b.box(-31., -8.5, -12., d.RAIL_FROM_Y - .50, -20., deck - .50)
    core = d.new_guard(.25) ^ below
    gone = ((d.old_top_arm() ^ b.box(-80, 80, -80, keep_y - .30, -20, deck - .05)) + d.old_crown_bars()) - d.new_guard(-.02) - d.kept_guard()
    low = b.box(-31., -8.5, -12., d.RAIL_FROM_Y - .50, -20., 3.2)
    plan = lambda shape: (shape ^ low).project()
    lost = plan(before) - plan(body)
    pouch = mf.CrossSection.square((d.PACK[0], d.PACK[1])).translate((d.PACK_X[0], d.PACK_Y0))
    path = d.arm_path()
    old_path = d._bezier(d.r62.TOP_PATH, np.linspace(0, 1, 60))
    steps = np.diff(path, axis=0)
    def steepest(pts, to_y):
        """Largest angle between the arm and the print axis (-Y) on its way down, before it turns sideways."""
        steps = np.diff(pts[pts[:, 1] >= to_y], axis=0)
        return rnd(float(np.degrees(np.max(np.arctan2(np.hypot(steps[:, 0], steps[:, 2]), -steps[:, 1])))), 1)
    root = dict(under_the_deck=b.box(-14.5, -9.5, keep_y + .30, d.OLD_ZONE[2] - .05, -20, 20), in_the_deck=b.box(-14.5, -9.5, d.OLD_ZONE[2] - .05, 22.5, deck + .03, 20))
    gained = plan(body) - plan(before)
    return dict(
        kept='root and first %.1f mm of the top arm (to Y %.2f), both lower rails, the closed outer tip, every height and both sections' % (float(np.linalg.norm(d.arm_split()[0] - np.asarray(d.r62.TOP_PATH[0]))), keep_y),
        moved=dict(hub_mm=dict(r70=list(d.r62.CROWN_START), r71=list(d.HUB)), hub_moved_toward_the_lower_row_mm=rnd(d.r62.CROWN_START[1] - d.HUB[1], 2),
                   arm_centre_beside_the_pouch_x_mm=rnd(d.PACK_X[1] + d.ARM_R + d.ARM_SIDE_GAP, 2), arm_length_mm=dict(r70=rnd(float(np.linalg.norm(np.diff(old_path, axis=0), axis=1).sum()), 1),
                   r71=rnd(float(np.linalg.norm(steps, axis=1).sum() + np.linalg.norm(d.arm_split()[0] - np.asarray(d.r62.TOP_PATH[0]))), 1))),
        new_members_core_missing_mm3=rnd(core.volume() - mm3(core, body), 4), old_arm_and_bars_left_mm3=mm3(gone, body),
        arm_root_section_changed_mm2=max(c67.section_difference(before ^ zone_, body ^ zone_)['max_area_mm2'] for zone_ in root.values()),
        lowest_z_mm=dict(r70=rnd((before ^ zone).bounding_box()[2], 2), r71=rnd((body ^ zone).bounding_box()[2], 2)),
        crown_rear_edge_y_mm=dict(r70=rnd((before ^ low ^ b.box(-31, -15.7, 2, 14, -20, 3.2)).bounding_box()[4], 2), r71=rnd((body ^ low ^ b.box(-31, -15.7, 2, 14, -20, 3.2)).bounding_box()[4], 2)),
        plan_under_z_3_2_mm2=dict(r70=rnd(plan(before).area(), 1), r71=rnd(plan(body).area(), 1)),
        plan_no_longer_covered_mm2=rnd(lost.area(), 1), of_that_under_the_pouch_mm2=rnd((lost ^ pouch).area(), 1), plan_newly_covered_mm2=rnd(gained.area(), 1),
        slot_between_the_crown_and_the_pouch_nose_mm=rnd(d.PACK_Y0 - d.HUB[1] - d.BAR_R, 2),
        steepest_descent_from_the_print_axis_deg=dict(r70=steepest(old_path, 12.0), r71=steepest(np.vstack([old_path[old_path[:, 1] > keep_y], path]), d.ARM_TURN_Y)),
        sideways_run_to_the_hub=dict(r70=dict(length_mm=8.7, rise_deg=rnd(float(np.degrees(np.arctan2(1.1, 8.7))), 1)),
                                     r71=dict(length_mm=rnd(d.HUB[0] + d.PACK_X[1], 2), rise_deg=rnd(float(np.degrees(np.arctan2(d.PACK_Y0 - d.ARM_R - d.ARM_STOP_GAP - d.HUB[1], d.HUB[0] + d.PACK_X[1]))), 1))),
        reading=('The crown ends %.1f mm nearer the lower row. The strip it used to cover lies under the pouch. Without a pouch that strip is open, '
                 'as the space under the upper-left socket always was.' % (d.r62.CROWN_START[1] - d.HUB[1])))


def layer_survey(body, layer=.2):
    """The holder cut into print layers, rear face down: islands that start on nothing, and
    plastic that overhangs the layer below by more than 0.5 mm in the left bank under the deck.
    CAD sections, not a slice: it only shows that R71 asks nothing new of the printer. — Claude Fable 5.2"""
    turned = body.transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]])
    lo, hi = float(body.bounding_box()[1]), float(body.bounding_box()[4])
    window = mf.CrossSection.square((23., 14.)).translate((-31., -6.5))
    starts, rows, below = [], [], None
    for k in range(int((hi - lo) / layer)):
        y = hi - layer / 2 - k * layer
        section = turned.slice(y)
        if below is not None:
            grown = below.offset(layer + .01, mf.JoinType.Round)
            starts += [dict(y_mm=rnd(y, 2), area_mm2=rnd(piece.area(), 3)) for piece in section.decompose() if piece.area() > .02 and (piece ^ grown).area() < 1e-4]
            beyond = (section - below.offset(.50, mf.JoinType.Round)) ^ window
            if beyond.area() > .01:
                x0, z0, x1, z1 = beyond.bounds()
                rows.append(dict(y_mm=rnd(y, 2), area_mm2=rnd(beyond.area(), 2), x_mm=[rnd(x0, 1), rnd(x1, 1)], z_mm=[rnd(z0, 1), rnd(z1, 1)]))
        below = section
    return dict(islands_starting_on_nothing=starts, layers_overhanging_more_than_0_5_mm=len(rows), overhang_total_mm2=rnd(sum(r['area_mm2'] for r in rows), 2),
                largest=sorted(rows, key=lambda r: -r['area_mm2'])[:5])


# ----------------------------------------------------------------------- battery
def fitted_limits():
    """The two left keys as fitted: sockets, posts, tape margins and the stated solder-and-wire
    allowance on the socket terminals, each at its seat. — Claude Fable 5.2"""
    hw = r66.r64.fitted_key_hardware()
    switch, socket = hw['switch_3'], hw['socket_3']
    under = switch ^ b.box(-40, 40, -40, 60, -10, d.DECK - .02)
    posts = sorted((p for p in under.decompose() if p.volume() > .5), key=lambda p: p.bounding_box()[0])
    working = old.k.h.d.geometry()[1]
    at = lambda name: old.placed(working[name], name)
    largest = b.union([at('key_3_maximum_socket'), at('key_0_maximum_socket')])
    tape = b.union([at('key_3_socket_tape_zone'), at('key_0_socket_tape_zone')])
    seated = {name: list(old.c.poses(at(name)))[-1] for name in ('key_3_soldered_socket_dogleg', 'key_0_soldered_socket_slide')}
    solder = {name: b.union([p for p in (shape ^ b.box(-80, 80, -80, 80, -20, d.SOCKET_Z - .01)).decompose() if p.volume() > .01]) for name, shape in seated.items()}
    return dict(hw=hw, switch=switch, socket=socket, posts=posts, largest=largest, tape=tape, solder=solder,
                left=b.union([hw[n] for n in ('switch_3', 'socket_3', 'switch_0', 'socket_0')]))


def battery(new, prev):
    body, before = new[d.HOLDER], prev[d.HOLDER]
    lim = fitted_limits()
    hw, posts, solder = lim['hw'], lim['posts'], lim['solder']
    joints = b.union(list(solder.values()))
    pack, old_pack = d.pack(), old.pack()
    guard = d.new_guard()
    tongue_zone = b.box(d.INNER_X[0] - .8, d.INNER_X[1] + .4, d.TONGUE_Y[0] - d.SLOT, d.TONGUE_Y[1], d.TONGUE_Z[0] - d.SLOT, d.TONGUE_Z[1] + d.SLOT)
    rigid = body - tongue_zone
    rail = body ^ b.box(d.outer_wall_x()[0] - .1, d.INNER_X[1] + .1, d.RAIL_FROM_Y - .1, d.BED, d.LOW - 1., d.DECK - .02)
    spaces = c70.placed_spaces()
    checked, hits = c70.routes(body, spaces)
    crossing = lambda shape: {n: v for n, v in ((n, max(mm3(shape, p) for p in poses)) for n, poses in spaces.items()) if v > .01}
    upper_left = b.union([p for n in ('key_3_socket_loading', 'key_3_maximum_socket_loading', 'key_3_soldered_socket_dogleg') for p in spaces[n]])
    lower_left = b.union(list(spaces['key_0_soldered_socket_slide']))
    wide = b.box(d.PACK_X[0], d.PACK_X[1] + d.ALLOWANCE - .02, d.PACK_Y0, d.PACK_Y0 + d.PACK[1], *d.PACK_Z)
    plan = b.box(d.PACK_X[0], d.PACK_X[1], d.PACK_Y0, d.BED, -20, 40)
    area = lambda shape, z0, z1: rnd((shape ^ plan ^ b.box(-80, 80, -80, 80, z0, z1)).project().area(), 1)
    old_plan = b.box(old.PACK_X[0], old.PACK_X[1], old.PACK_Y0, d.BED, -20, 40)
    old_area = lambda z0, z1: rnd((before ^ old_plan ^ b.box(-80, 80, -80, 80, z0, z1)).project().area(), 1)
    sweep = placement_sweep(lim, before)
    slide = [pack.translate((0, float(t), 0)) for t in np.arange(0., 30.01, .5)]
    everything = lim['left'] + lim['largest'] + lim['tape'] + joints
    face = d.PACK[0] * d.PACK[1]
    under = (body ^ plan ^ b.box(-80, 80, -80, 80, -20, d.PACK_Z[0])).project()
    over = (body ^ plan ^ b.box(-80, 80, -80, 80, d.PACK_Z[1], 40)).project()
    window = mf.CrossSection.square((d.PACK[0], d.RAIL_FROM_Y - d.PACK_Y0 - 1.0)).translate((d.PACK_X[0], d.PACK_Y0 + .5))
    left_zone = b.box(-31., -8.5, -12., d.RAIL_FROM_Y - .50, -20., d.DECK - .50)
    measured = dict(socket_underside_z_mm=rnd(lim['socket'].bounding_box()[2], 2), tape_underside_z_mm=rnd(lim['tape'].bounding_box()[2], 2),
                    solder_allowance_underside_z_mm=rnd(joints.bounding_box()[2], 2), post_tip_z_mm=min(rnd(p.bounding_box()[2], 2) for p in posts))
    report = dict(
        revision='R71', physical_fit_verified=False,
        pouch=('Micron 72217 protected 3.7 V 100 mAh, nominal 27 x 11.8 x 3.9 mm, 35 mm leads, Molex 2 mm 2-pin. The cell was not measured; '
               'the lead exit end and slack are unknown and the connector is not modelled.'),
        placement=d.numbers(), other_places_tried=sweep,
        limits=dict(
            measured_on_the_fitted_models=measured,
            above=dict(what='the stated solder-and-wire allowance on the terminals of both left sockets, at their seats',
                       allowance_blocks={n: box_of(s) for n, s in solder.items()}, pad_underside_z_mm=d.PAD_Z, pouch_top_z_mm=rnd(d.PACK_Z[1], 2),
                       pads_to_the_allowance_mm=rnd(measured['solder_allowance_underside_z_mm'] - d.PAD_Z, 2),
                       pouch_to_the_allowance_mm=rnd(pack.min_gap(joints, 5.)), pouch_to_the_tape_margin_mm=rnd(pack.min_gap(lim['tape'], 5.)),
                       pouch_to_the_fitted_switches_and_sockets_mm=rnd(pack.min_gap(lim['left'], 5.)), pouch_to_the_largest_sockets_mm=rnd(pack.min_gap(lim['largest'], 5.)),
                       under_the_deck_mm=rnd(d.DECK - d.PACK_Z[1], 2),
                       at_the_tape_margin_instead=dict(pouch_top_z_mm=rnd(d.TAPE_Z - .10, 2), into_the_solder_allowance_mm3=sweep['fully_inside_at_the_tape_margin_into_the_solder_allowance_mm3'],
                                                       reading='0.93 mm less under the deck, but the pouch would lie in the space kept for two solder joints and their wires')),
            forward=dict(what='the rear face: a 27 mm pouch that ends there starts at Y %.2f' % d.PACK_Y0, pouch_front_y_mm=rnd(d.PACK_Y0, 2), rear_face_y_mm=d.BED,
                         behind_the_rear_face_mm=rnd(d.PACK_Y0 + d.PACK[1] - d.BED, 2), front_stop="the left guard's top arm, across the nose at the pouch's mid height",
                         nose_to_the_arm_mm=rnd(pack.min_gap(guard, 5.)), nose_to_the_lower_left_socket_mm=rnd(pack.min_gap(hw['socket_0'], 5.))),
            inboard=dict(what="the left guard's top arm, re-routed beside the pouch", arm_to_the_pouch_side_mm=d.ARM_SIDE_GAP, rail_to_the_guard_mm=rnd(rail.min_gap(guard, 6.)),
                         guard_to_the_fitted_switches_and_sockets_mm=rnd(guard.min_gap(lim['left'], 6.)), guard_to_the_solder_allowance_mm=rnd(guard.min_gap(joints, 6.)),
                         guard_to_the_tape_margin_mm=rnd(guard.min_gap(lim['tape'], 6.))),
            outward=dict(what='the side of the left key bank', bank_side_x_mm=d.BANK_SIDE_X, outer_wall_x_mm=[rnd(v, 2) for v in d.outer_wall_x()],
                         inset_mm=d.EDGE_INSET, edge_round_mm=r70.EDGE_R),
            below=dict(rail_lowest_z_mm=dict(r70=rnd(old.LOW, 2), r71=rnd(d.LOW, 2)), heel_under_the_outer_lip_z_mm=rnd(d.LOW - d.HEEL[1], 2),
                       pouch_underside_z_mm=dict(r70=rnd(old.PACK_Z[0], 2), r71=rnd(d.PACK_Z[0], 2)),
                       left_guard_lowest_z_mm=dict(r70=rnd((before ^ left_zone).bounding_box()[2], 2), r71=rnd((body ^ left_zone).bounding_box()[2], 2)))),
        fitted_parts=dict(pouch_to_switches_and_sockets_mm3={n: mm3(pack, s) for n, s in hw.items() if n != 'rod'},
                          pouch_to_tape_and_solder_allowance_mm3=mm3(pack, lim['tape'] + joints + lim['largest']),
                          rail_to_left_switches_and_sockets_mm3={n: mm3(rail, hw[n]) for n in ('switch_0', 'socket_0', 'switch_3', 'socket_3')},
                          rail_and_guard_to_tape_and_solder_allowance_mm3=mm3(rail + guard, lim['tape'] + joints + lim['largest'])),
        loading=dict(key_poses_checked=checked, key_obstructions=hits,
                     upper_left_socket_routes_to_the_rail_gap_mm=rnd(rail.min_gap(upper_left, 4.)), upper_left_socket_routes_to_the_guard_gap_mm=rnd(guard.min_gap(upper_left, 4.)),
                     lower_left_socket_route_to_the_guard_gap_mm=rnd(guard.min_gap(lower_left, 4.)),
                     routes_crossing_the_seated_pouch_mm3=dict(r70=crossing(old_pack), r71=crossing(pack)),
                     order=('Sockets first, taped, then the switches, then the pouch. The upper-left socket comes up through the place the pouch then takes, '
                            'and the lower-left socket slides past its nose: take the pouch out before changing either. With the pouch out every key route is open.')),
        seat=dict(seated_overlap_with_the_spring_mm3=mm3(body, pack), seated_overlap_without_the_spring_mm3=mm3(rigid, pack),
                  slide_in_from_the_rear_without_the_spring_mm3=max(mm3(rigid, pose) for pose in slide), slide_in_poses=len(slide),
                  slide_in_against_switches_sockets_tape_and_solder_mm3=max(mm3(everything, pose) for pose in slide),
                  widest_pouch_seated_mm3=mm3(rigid, wide), widest_pouch_mm=rnd(d.PACK[0] + d.ALLOWANCE - .02, 2),
                  pushed_0_2mm_past_the_stop_mm3=mm3(rigid, pack.translate((0, -.2, 0))),
                  lips_under_the_pouch_mm2=dict(r70=old_area(old.LIP_TOP - .3, old.LIP_TOP - .05), r71=area(body, d.LIP_TOP - .3, d.LIP_TOP - .05)),
                  bearing_over_the_pouch_mm2=dict(r70=old_area(old.PACK_Z[1] + .06, old.PACK_Z[1] + .12), r71=area(body, d.PACK_Z[1] + .06, d.PACK_Z[1] + .12)),
                  vertical_play_mm=rnd((d.PAD_Z - d.PACK_Z[1]) + (d.PACK_Z[0] - d.LIP_TOP), 2)),
        removal=dict(how=('Press a fingertip on the pouch\'s open underside, between the rail and the guard, and slide it back until its end can be held. '
                          'Nothing has to be pulled by the leads.'),
                     underside_open_mm2=rnd(face - under.area(), 1), underside_share_open=rnd(1 - under.area() / face, 2),
                     open_window_in_front_of_the_rail_mm=[d.PACK[0], rnd(d.RAIL_FROM_Y - d.PACK_Y0 - 1.0, 2)], covered_inside_that_window_mm2=rnd((under ^ window).area(), 2),
                     top_open_from_above_mm2=rnd(face - (over + ((lim['left'] + lim['tape']) ^ plan).project()).area(), 1),
                     nothing_behind_the_pouch_end_mm3=mm3(body, b.box(d.PACK_X[0], d.PACK_X[1], d.BED - .01, d.BED + 30., *d.PACK_Z))),
        spring=dict(tongue_to_frame_gap_mm=d.SLOT, room_behind_the_tongue_to_the_guard_mm=rnd((body ^ tongue_zone).min_gap(guard, 8.))),
        wires=('Assumed, not measured: the wires of both left sockets are taped to the deck, as the guide asks, inside the stated allowance. '
               'Over the pouch\'s nose there is %.1f mm between pouch and deck for them; the strip of deck behind the upper-left socket is free to Y %.2f, as in R70. '
               'The battery leads leave from the rear end as before.' % (d.DECK - d.PACK_Z[1], d.RAIL_FROM_Y)),
        not_measured='pouch size, lead exit, real solder joints and wire runs, spring force, how firmly 16 mm of rail holds in use, and the feel of a rail 3 mm lower')
    r = report
    place, lim_, seat = r['placement'], r['limits'], r['seat']
    expected = {'key_3_socket_loading', 'key_3_maximum_socket_loading', 'key_3_soldered_socket_dogleg', 'key_0_soldered_socket_slide'}
    r['gates'] = [max(r['fitted_parts']['pouch_to_switches_and_sockets_mm3'].values()) < .001 and max(r['fitted_parts']['rail_to_left_switches_and_sockets_mm3'].values()) < .001
                  and r['fitted_parts']['pouch_to_tape_and_solder_allowance_mm3'] < .001 and r['fitted_parts']['rail_and_guard_to_tape_and_solder_allowance_mm3'] < .001,
                  abs(measured['solder_allowance_underside_z_mm'] - d.SOLDER_Z) < .011 and abs(measured['tape_underside_z_mm'] - d.TAPE_Z) < .011
                  and abs(measured['socket_underside_z_mm'] - d.SOCKET_Z) < .011 and abs(measured['post_tip_z_mm'] - d.POST_TIP_Z) < .011,
                  lim_['above']['pads_to_the_allowance_mm'] >= .14 and lim_['above']['pouch_to_the_allowance_mm'] >= .19 and lim_['above']['pouch_to_the_fitted_switches_and_sockets_mm'] >= 1.0,
                  abs(place['behind_the_rear_face_mm']['r71']) < .01 and place['behind_the_rear_face_mm']['r70'] > 12. and r['removal']['nothing_behind_the_pouch_end_mm3'] == 0,
                  .03 <= lim_['forward']['nose_to_the_arm_mm'] <= .08 and lim_['inboard']['arm_to_the_pouch_side_mm'] >= d.ALLOWANCE and lim_['inboard']['rail_to_the_guard_mm'] >= .5
                  and lim_['inboard']['guard_to_the_tape_margin_mm'] >= .5 and lim_['below']['left_guard_lowest_z_mm']['r71'] >= lim_['below']['left_guard_lowest_z_mm']['r70'] - .01,
                  not hits and checked == 336 and set(r['loading']['routes_crossing_the_seated_pouch_mm3']['r71']) <= expected and not r['loading']['routes_crossing_the_seated_pouch_mm3']['r70']
                  and min(r['loading'][k] for k in ('upper_left_socket_routes_to_the_rail_gap_mm', 'upper_left_socket_routes_to_the_guard_gap_mm', 'lower_left_socket_route_to_the_guard_gap_mm')) > .1,
                  0 < seat['seated_overlap_with_the_spring_mm3'] < 4. and seat['seated_overlap_without_the_spring_mm3'] < .01
                  and seat['slide_in_from_the_rear_without_the_spring_mm3'] < .01 and seat['widest_pouch_seated_mm3'] < .01 and seat['slide_in_against_switches_sockets_tape_and_solder_mm3'] < .001,
                  seat['pushed_0_2mm_past_the_stop_mm3'] > .02 and sweep['fully_inside_at_the_tape_margin_into_the_solder_allowance_mm3'] > 1.,
                  place['outer_rail_mm']['r71'] < 1.0 and place['held_by_the_rail_mm']['r71'] >= place['held_by_the_rail_mm']['r70'],
                  place['spring']['thickness_mm'] == place['spring']['r70']['thickness_mm'] and abs(place['spring']['lever_mm'] - place['spring']['r70']['lever_mm']) < .05
                  and place['spring']['height_mm'] == place['spring']['r70']['height_mm'] and r['spring']['room_behind_the_tongue_to_the_guard_mm'] > .5,
                  seat['lips_under_the_pouch_mm2']['r71'] >= seat['lips_under_the_pouch_mm2']['r70'] and seat['bearing_over_the_pouch_mm2']['r71'] > 30.,
                  r['removal']['underside_share_open'] >= .5 and r['removal']['covered_inside_that_window_mm2'] < .01]
    r['passes'] = all(r['gates'])
    return report


def placement_sweep(lim, before):
    """How far forward a pouch can go at four heights and four sideways positions. It is slid
    forward in 0.1 mm steps until it meets the fitted switches and sockets of the left bank,
    their tape margins or the solder allowance; and again with R70's own holder (guard and
    all) in the way as well. — Claude Fable 5.2"""
    joints = b.union(list(lim['solder'].values()))
    hardware = lim['left'] + lim['largest'] + lim['tape'] + joints
    carrier = before ^ b.box(-31.5, -8.5, -12., d.RAIL_FROM_Y - .02, -20., d.DECK - .02)       # R70 under the deck in front of its rail: the guard
    heights = {'against the deck (R70)': old.PACK_Z[1], 'under the switch posts': rnd(d.POST_TIP_Z - .15, 2), 'under the tape margin': rnd(d.TAPE_Z - .10, 2),
               'under the solder allowance (R71)': rnd(d.PACK_Z[1], 2)}
    rows, best = [], {}
    for label, top in heights.items():
        for x0 in (-29.05, d.PACK_X[0], -24.5, old.PACK_X[0]):
            pouch = lambda y: b.box(x0, x0 + d.PACK[0], y, y + d.PACK[1], top - d.PACK[2], top)
            row = dict(height=label, pouch_top_z_mm=rnd(top, 2), under_the_deck_mm=rnd(d.DECK - top, 2), pouch_x0_mm=x0)
            for name, fixed in (('hardware_only', hardware), ('hardware_and_the_r70_guard', hardware + carrier)):
                front = 24.0
                if mm3(fixed, pouch(front)) > 1e-4:
                    row[name] = 'blocked behind the keys'
                    continue
                while front > d.PACK_Y0 and mm3(fixed, pouch(round(front - .1, 2))) <= 1e-4:
                    front = round(front - .1, 2)
                front = max(front, rnd(d.PACK_Y0, 2))
                row[name] = dict(front_y_mm=front, behind_the_rear_face_mm=rnd(front + d.PACK[1] - d.BED, 2))
                best.setdefault(label, {})[name] = min(best.get(label, {}).get(name, 99.), row[name]['behind_the_rear_face_mm'])
            rows.append(row)
    tape_pose = b.box(d.PACK_X[0], d.PACK_X[1], d.PACK_Y0, d.BED, d.TAPE_Z - .10 - d.PACK[2], d.TAPE_Z - .10)
    return dict(rows=rows, least_behind_the_rear_face_mm=best,
                fully_inside_at_the_tape_margin_into_the_solder_allowance_mm3=mm3(tape_pose, joints),
                fully_inside_at_the_tape_margin_into_the_r70_guard_mm3=mm3(tape_pose, carrier),
                reading=('Sideways position does not help: both sockets span the bank. Height decides. Against the deck or under the switch posts the pouch stops '
                         'behind the upper-left socket. Under the socket it can end at the rear face, if it also clears the solder allowance on the terminals '
                         'and if the guard\'s top arm and the crown\'s rear bar leave its nose free. R71 does both.'))


# ----------------------------------------------------------------------- base
def base():
    rows = {r['name']: r for r in kit71.parts()}
    before = {r['name']: r for r in kit70.parts()}
    now = kit71.base_report(rows['Key_Carrier']['source'], rows['Key_Carrier']['panel'])
    then = kit71.base_report(before['Key_Carrier']['source'], before['Key_Carrier']['panel'])
    depth = dict(r70=c70.root_depth(before['Key_Carrier']['source'], before['Key_Carrier']['panel']),
                 r71=c70.root_depth(rows['Key_Carrier']['source'], rows['Key_Carrier']['panel']))
    body = kit71.bed_body(rows['Key_Carrier']['source'])
    lay = kit71.p54.layout54(body, kit71.panel55.settings(rows['Key_Carrier']['panel']))
    necks = [dict(face=root['tie']['face'], at_x_mm=root['tie']['at'], moat_mm=rnd(root['start'] - root['outer'], 2),
                  necks=[dict(end=end, from_holder_face_mm=[rnd(a0 - root['outer'], 2), rnd(a1 - root['outer'], 2)], width_mm=width)
                         for a0, a1, width, end in kit71.neck_spans(root)]) for root in lay['roots']]
    ratio = sorted(f['at_the_plate_mm2'] / f['at_the_holder_mm2'] for f in now['fins'])
    ratio = (ratio[0], ratio[-1])
    report = dict(
        revision='R71', physical_fit_verified=False, sliced=False,
        fault=('R70: the fins were hard to pull from the plate and left stubs. Each was a full 1.7 mm strip where it met its post on the plate, '
               'and three of the five were full width at the holder as well. Which fins and how long the stubs were was not measured.'),
        pieces=dict(r70=sorted(before), r71=sorted(rows)),
        holder_base=dict(r70=then, r71=now), plastic_behind_each_fin=depth, fin_width_mm=kit71.FIN, necks=necks,
        section_r71_over_r70=dict(at_the_plate=rnd(now['total_at_the_plate_mm2'] / then['total_at_the_plate_mm2'], 2),
                                  at_the_holder=rnd(now['total_at_the_holder_mm2'] / then['total_at_the_holder_mm2'], 2),
                                  weakest_path=rnd(now['weakest_path_mm2'] / then['weakest_path_mm2'], 2)),
        load_path=('Each fin carries load from the holder through one neck beside the holder\'s face into a full-width fin, a 1.2 mm post, a buttress and a '
                   '9 x 11 mm foot on the 0.4 mm panel. That neck is the smallest section on the path. The panel, feet, buttresses and fin heights are R70\'s.'),
        break_order=['First and only intended break: the neck beside the holder, 0.02 to 0.47 mm from its face. The fin stays on the plate.',
                     'The fin at the plate is full width, %.2f to %.2f times the neck\'s section, so it should not break there first.' % (ratio[0], ratio[1]),
                     'An earlier R71 draft also necked the plate end to the same width; a fin breaking there would have left 1.5 mm on the holder.'],
        release=['Fold a wing of the panel away from the holder: each fin breaks at its neck beside the holder.',
                 'What can stay on the holder is at most 0.47 mm long: nip or scrape it flush.',
                 'Nothing is attached at the hinge, over the open pouch lane or on a lip.'],
        assumptions=('PETG breaks at the smallest section when bent. The force to break a neck was not measured. With slightly less section at the holder than R70 '
                     '(numbers above), holding through the print is an assumption until the plate is sliced, its deposited beads are measured and it is printed.'),
        first_layer_note='holder first layer %.1f mm2 (R70 %.1f): the mirrored left shoulder takes some away and the deeper rail gives some back; the fins\' smallest sections add up to %.0f%% of R70\'s'
                         % (now['holder_first_layer_mm2'], then['holder_first_layer_mm2'], 100 * now['weakest_path_mm2'] / then['weakest_path_mm2']))
    r = report
    least = lambda rev: min(row['least_plastic_behind_the_fin_mm'] for row in depth[rev])
    r['gates'] = [len(rows) == 9 and sorted(rows) == sorted(before), least('r71') >= 1.6,
                  all(len(row['necks']) == 1 and row['necks'][0]['end'] == 'holder' and row['necks'][0]['from_holder_face_mm'][0] <= .05 and row['necks'][0]['from_holder_face_mm'][1] <= .50 for row in necks),
                  all(f['at_the_holder_mm2'] <= .75 * f['at_the_plate_mm2'] and f['at_the_plate_mm2'] == f['full_section_mm2'] for f in now['fins'])
                  and sum(f['at_the_holder_mm2'] == f['full_section_mm2'] for f in then['fins']) == 3,
                  now['weakest_path_mm2'] >= 15. and now['first_layer_pieces'] == 1 and now['panel_pieces'] == 1 and now['base_volume_in_hinge_bay_mm3'] == 0,
                  now['holder_first_layer_mm2'] >= .9 * then['holder_first_layer_mm2'] and now['print_height_mm'] == then['print_height_mm']
                  and now['weakest_path_mm2'] >= .9 * then['weakest_path_mm2']]
    r['passes'] = all(r['gates'])
    return report


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
