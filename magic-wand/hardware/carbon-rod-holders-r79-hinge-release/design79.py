"""R79 key holder: the two fixed hinge bearings are backed where they stand on the print bed,
grip the bed a little less, and the two fins beside them break away more easily.
Run this file to export the carrier and write its local measurements (exports/hinge79.json).

Built from the exported R78 carrier. Nothing else changes: pin bore, open journal sockets,
barrel bay, click, board and wire paths, pin trough, keys, guard and battery rails are R78's.

What happened. On the printed R78 the fixed right bearing, the block the hinge pin threads
through, split in half while the sacrificial base was being removed. There is no fracture
photo and no proof of poor bonding. What the files show:

* each bearing block stands on the bed on its whole rear face, 4.24 x 7.30 mm;
* 4.15 mm above the bed, at the pin line, the same block is necked by the pin bore and the
  open journal socket. That neck lies along one print layer;
* the block is free on its outboard side above the key plate, so whatever pulls on its
  foot has to pass through that neck;
* the fin on the shoulder 4.65 mm from the right block was 4.8 mm high with a 0.84 mm neck
  (4.03 mm2 to break). The matching left fin was 1.8 mm high (2.27 mm2).

What changes, the same on both sides:

1. Backing. A sloped web joins each block's rear 1.4 mm, the part behind the pin trough,
   to the key plate beside it. The foot's pull then goes sideways into the plate inside
   the first seven layers instead of up through the neck. The web stands on the bed and
   against the block. The plate's rear rim is rounded, so the web's foot does not stop at
   the plate's surface: it runs 0.9 mm down into the plate, where the plate is solid, and
   that is where its root is measured. What shows above the plate is the same slope.
2. Less bed grip. The upper rear edge of each block is chamfered 1.0 mm. Its foot loses
   4.24 mm2. The chamfer ends exactly at the top of the journal socket's rear wall, so
   no bearing surface is touched.
3. Easier break at the hinge end. carrier_panel() makes both shoulder fins 1.8 mm high
   with a 0.84 mm neck: 1.51 mm2 each to break.

Those two small fins alone left the holder held by too little (the first R79 plate
measured 15.7 mm2 of attachment where R78, which held, had 20.4). So carrier_panel() also
adds one fin: under the right key bank's rear rim, on the 3.85 mm plate, 4.7 mm outboard
of the bearing and on the other face of the plate from it, open to cutters from below.
The battery rails, the rod ring, the wire window and the hinge bay get nothing new.

The old flat DFRobot post clips (R59's, as printed through R70) are named by flat_clips().
This file does not copy or change them.

Dimensions are mm in the assembly frame: rod along Y, +Z toward the keypad, print bed at
Y 36.45 (hinge70.BED), printing toward -Y.
 — Claude Fable 5.2"""
from hashlib import sha256
from pathlib import Path
import json
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r78-low-battery'))
import design78 as old  # noqa: E402
import hinge70 as hinge  # noqa: E402

b = old.b
r77, r71 = old.old, old.r71
HOLDER = old.HOLDER
SOURCE_SHA = 'ecfa078e9f72dfce91d61e590d7e71076e429351896de1b54420170e2933957d'      # the exact R78 carrier
AXIS, KEEPER_Z, BED = hinge.AXIS, hinge.KEEPER_Z, hinge.BED       # 32.3, 12.7, 36.45
INNER, OUTER, TOP = hinge.INNER, hinge.OUTER, hinge.TOP           # block: X 7.26 to 11.5, top at Z 15.95
PLATE_TOP = r71.PLATE_TOP                                         # 11.12: top of the key plate beside each block
TROUGH_R = 2.38                                                   # hinge70.approach(): the pin's open trough outboard of each block

# ------------------------------------------------------------------ 1. backing web (written for the right block, then mirrored)
WEB_CLEAR = 0.35                                                  # the web stays this far behind the pin trough
WEB_FROM_Y = AXIS + TROUGH_R + WEB_CLEAR                          # 35.03: so it is 1.42 mm thick, from here to the bed
WEB_REACH = 2.20                                                  # along the key plate from the block's outer face: to X 13.70
WEB_EMBED = 0.30                                                  # how far it runs into the block; and where its slope ends, below the plate's nominal top
FOOT_DEPTH = 0.90                                                 # the foot runs this far below the plate's nominal top: to Z 10.22
ROOT_BELOW_Z = 10.55                                              # the plate is solid under the web from here down (R78 measured: 99.5 %); the root is judged there
# ------------------------------------------------------------------ 2. bed relief
CHAMFER = 1.00                                                    # upper rear edge of each block; ends at the socket's rear wall top
WEB_TOP = TOP - CHAMFER                                           # 14.95: the web meets the block at the chamfer's bed edge
# ------------------------------------------------------------------ 3. fins (print frame: '+y' is the keypad face, '-y' the underside)
SHOULDER_TIE_HEIGHT = 1.80                                        # the two beside the bearings. R78: 1.8 left, 4.8 right
SHOULDER_TIE_NECK = 0.84                                          # two 0.42 mm lines; R78: 1.26 left, 0.84 right
RIM_TIE = dict(face='-y', at=16.30, height=4.80, neck=1.26)       # the added fin: under the right bank's rear rim, like its neighbour at X 13


def _wedge(points_xz, y0, y1):
    """Convex prism: an (X, Z) outline carried from y0 to y1."""
    return mf.Manifold.hull_points(np.array([(x, y, z) for y in (y0, y1) for x, z in points_xz], float))


def web():
    """The right block's backing. Ethan's bearing split while the base came off; this ties
    the part of the block that stands on the bed to the plate beside it. Its slope ends
    0.3 mm under the plate's nominal top, as first drawn; below that a plain foot goes on
    down into solid plate, past the rounded rim. — Claude Fable 5.2"""
    foot, slope_end = PLATE_TOP - FOOT_DEPTH, PLATE_TOP - WEB_EMBED
    outline = [(OUTER - WEB_EMBED, foot), (OUTER + WEB_REACH, foot), (OUTER + WEB_REACH, slope_end), (OUTER - WEB_EMBED, WEB_TOP)]
    return _wedge(outline, WEB_FROM_Y, BED)


def relief():
    """What the chamfer takes from the right block's upper rear edge: less of the bearing on
    the bed, and an edge for the peel to start at. — Claude Fable 5.2"""
    outline_yz = [(BED - CHAMFER - .05, TOP + .05), (BED + .05, TOP + .05), (BED + .05, TOP - CHAMFER - .05)]
    return mf.Manifold.hull_points(np.array([(x, y, z) for x in (INNER - .05, OUTER) for y, z in outline_yz], float))


def carrier():
    path = old.OUT / HOLDER
    if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('R78 carrier differs from the checked export')
    before = b.load(path)
    added, cut = b.mirrored(web()), b.mirrored(relief())
    return before, added, cut, (before + added) - cut


def carrier_panel(options):
    """Ethan asked for an easier break at the hinge end. The two fins on the shoulders,
    beside the bearings, are lowered and necked. One fin is added under the right bank's
    rear rim so the holder is still held through the print. Every other fin, the sheet and
    the keep-clear boxes pass through as they are. Same option keys as before.
     — Claude Fable 5.2"""
    ties = [dict(tie) for tie in options['ties']]
    for tie in ties:
        if tie.get('face') == '+y':
            tie.update(height=SHOULDER_TIE_HEIGHT, neck=SHOULDER_TIE_NECK)
    if not any(tie.get('face') == RIM_TIE['face'] and abs(tie['at'] - RIM_TIE['at']) < .01 for tie in ties):
        ties.append(dict(RIM_TIE))
    return dict(options, ties=ties)


def break_sections(options):
    """Neck width times fin height for each fin, mm2, in the order of the options."""
    fin = options.get('fin_thickness', 1.7)
    return [dict(face=tie['face'], at=tie['at'], mm2=round(tie.get('neck', fin) * tie['height'], 2)) for tie in options['ties']]


def flat_clips():
    """The flat touch-board clips Ethan wants back: R59's own files, the ones kit70 printed."""
    import hinge71
    return {'DFR_Clip_' + side: path for side, path in hinge71.R59_CLIPS.items()}


# ------------------------------------------------------------------ export and local measurements
def _print_frame(shape):
    """Assembly to print: X stays, print Y is assembly Z, print Z is height above the bed."""
    return shape.transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, BED]])


def _ear(sign, more=.1):
    """Box round one bearing block and its web, down into the plate."""
    return b.box(*sorted((sign * (INNER - more), sign * (OUTER + WEB_REACH + more))), AXIS - 4.6, BED + .1, PLATE_TOP - FOOT_DEPTH - .4, TOP + .2)


def _starts(local, layer=.2):
    """Islands of a local piece that begin on nothing, cutting the print in layers."""
    local = _print_frame(local)
    below, found = None, []
    for k in range(int(round(float(local.bounding_box()[5]) / layer))):
        section = local.slice(layer * (k + .5))
        if below is not None:
            found += [round(layer * k, 1) for piece in section.decompose() if piece.area() > .02 and (piece ^ below.offset(layer + .01, mf.JoinType.Round)).area() < 1e-4]
        below = section
    return found


def numbers(before, added, cut, shape):
    """R78 beside R79, around the two bearings only. Every comparison is made inside the two
    small boxes round the bearings; the rest of the carrier is checked by its volume alone.
    CAD, not a slice. — Claude Fable 5.2"""
    mm3 = lambda one, two: round(float((one ^ two).volume()), 4)
    solid = lambda part: round(sum(float(p.volume()) for p in part.decompose() if p.volume() > 0), 4)     # the inherited mesh has inverted hairlines
    gap = lambda one, two, reach=6.: round(float(one.min_gap(two, reach)), 3)
    fraction = lambda part, body: round(mm3(part, body) / float(part.volume()), 4)
    foot_z = PLATE_TOP - FOOT_DEPTH
    values = json.loads((r71.OUT / 'carrier.json').read_text())['hinge']['click_values']['r71']
    near = b.box(-16., 16., AXIS - 9., BED + 1., 6., 24.)
    moving = (b.load(r77.OUT / r77.PADDLE) + r77.straight_wires()) ^ b.box(-16., 16., AXIS - 9., 60., 0., 40.)
    poses = [hinge.rotate(moving, float(a)) for a in np.linspace(-values['lift_stop_deg'], values['case_stop_deg'], 13)]
    box = added.bounding_box()
    reaches = lambda pose: all(pose.bounding_box()[i] <= box[i + 3] and pose.bounding_box()[i + 3] >= box[i] for i in range(3))
    key_hits = [mm3(added, pose) for group in r77.spaces().values() for pose in group if reaches(pose)]
    trough, pin = hinge.approach(), hinge.pin()
    sides, removed, grown = {}, 0., 0.
    for name, sign in (('left', -1), ('right', 1)):
        zone = _ear(sign)
        was, now = before ^ zone, shape ^ zone
        one = web() if sign > 0 else web().mirror((1, 0, 0))
        outboard = b.box(*sorted((sign * OUTER, sign * (OUTER + WEB_REACH))), 0, 60, 0, 60)
        in_block = one ^ b.box(*sorted((sign * (OUTER - WEB_EMBED), sign * OUTER)), 0, 60, 0, 60)
        foot = one ^ outboard ^ b.box(-60, 60, 0, 60, foot_z, ROOT_BELOW_Z)                 # the part of the foot that is meant to be buried
        rim = one ^ outboard ^ b.box(-60, 60, 0, 60, ROOT_BELOW_Z, PLATE_TOP)               # the part that passes the plate's rounded rim
        landing = lambda body: round(float((body ^ one ^ outboard).slice(ROOT_BELOW_Z - .005).area()), 3)
        block = b.box(*sorted((sign * (INNER - .05), sign * OUTER)), AXIS - 4.6, BED + .1, 8.6, TOP + .2)
        above_plate = mf.CrossSection.square((40., 40.)).translate((-20., PLATE_TOP + .02))
        bearing_zone = b.box(*sorted((sign * (INNER - .5), sign * (OUTER - .005))), AXIS - 4.6, BED - CHAMFER - .01, 8.6, TOP + .3)
        gone, came = solid(was - now), solid(now - was)
        removed, grown = removed + gone, grown + came
        sides[name] = dict(
            web_mm3=round(float(one.volume()), 3),
            root_in_the_block=fraction(in_block, before),
            root_in_the_plate=dict(buried_foot_z_mm=[round(foot_z, 2), ROOT_BELOW_Z], buried_foot_inside_solid_r78_plate=fraction(foot, before),
                                   landing_at_its_top_mm2=dict(web=round(float((one ^ outboard).slice(ROOT_BELOW_Z - .005).area()), 3), on_r78_plate=landing(before)),
                                   depth_below_that_level_mm=round(ROOT_BELOW_Z - foot_z, 2),
                                   rounded_rim_band_already_plate=fraction(rim, before), rim_band_z_mm=[ROOT_BELOW_Z, PLATE_TOP]),
            bed_contact_of_the_block_mm2=dict(r78=round(float(_print_frame(was ^ block).slice(.1).area()), 2), r79=round(float(_print_frame(now ^ block).slice(.1).area()), 2)),
            bed_contact_above_the_plate_block_and_web_mm2=dict(r78=round(float((_print_frame(was).slice(.1) ^ above_plate).area()), 2), r79=round(float((_print_frame(now).slice(.1) ^ above_plate).area()), 2)),
            islands_starting_on_nothing=dict(r78=_starts(was), r79=_starts(now)),
            bore_and_socket_unchanged_mm3=dict(removed=solid((was - now) ^ bearing_zone), added=solid((now - was) ^ bearing_zone)),
            changed_here_mm3=dict(removed=gone, added=came))
    return dict(
        revision='R79', physical_fit_verified=False, sliced=False, source_carrier_sha256=SOURCE_SHA, carrier_sha256=sha256((OUT / HOLDER).read_bytes()).hexdigest(),
        solids=len(shape.decompose()), sides=sides,
        web=dict(from_y_mm=round(WEB_FROM_Y, 2), thick_mm=round(BED - WEB_FROM_Y, 2), reach_from_the_block_mm=WEB_REACH, top_z_mm=WEB_TOP,
                 slope_from_to_xz_mm=[[OUTER, round(WEB_TOP - (WEB_TOP - PLATE_TOP + WEB_EMBED) * WEB_EMBED / (WEB_REACH + WEB_EMBED), 2)], [OUTER + WEB_REACH, round(PLATE_TOP - WEB_EMBED, 2)]],
                 foot_bottom_z_mm=round(foot_z, 2),
                 in_the_pin_trough_mm3=mm3(added, trough), to_the_pin_trough_mm=gap(added, trough ^ near),
                 in_the_seated_pin_mm3=mm3(added, pin), to_the_pin_mm=gap(added, pin),
                 to_paddle_and_wires_through_lift_and_click_mm=round(min(float(added.min_gap(pose, 8.)) for pose in poses), 3),
                 key_poses_reaching_the_webs=len(key_hits), in_any_key_pose_mm3=max(key_hits, default=0.)),
        relief=dict(chamfer_mm=CHAMFER, removed_mm3=round(removed, 4), socket_rear_wall_untouched_below_z_mm=round(TOP - CHAMFER + hinge.SOCKET_REAR_WALL, 2)),
        whole_carrier=dict(volume_mm3=dict(r78=round(float(before.volume()), 3), r79=round(float(shape.volume()), 3)),
                           volume_change_not_explained_by_the_two_bearing_boxes_mm3=round(float(shape.volume()) - float(before.volume()) - (grown - removed), 4)),
        fins=dict(shoulder=dict(height_mm=SHOULDER_TIE_HEIGHT, neck_mm=SHOULDER_TIE_NECK, break_mm2=round(SHOULDER_TIE_HEIGHT * SHOULDER_TIE_NECK, 2), r78_break_mm2=dict(left=2.27, right=4.03)),
                  added=dict(RIM_TIE, break_mm2=round(RIM_TIE['height'] * RIM_TIE['neck'], 2), outboard_of_the_bearing_mm=round(RIM_TIE['at'] - .85 - OUTER, 2)),
                  note='nominal neck sections; the plate audit measures the deposited seam'))


def build():
    OUT.mkdir(exist_ok=True)
    before, added, cut, body = carrier()
    pieces = sorted(body.decompose(), key=lambda part: -part.volume())
    if sum(abs(part.volume()) for part in pieces[1:]) > .025:
        raise ValueError('Detached carrier detail')
    shape = r77.old.old.clean_export(OUT / HOLDER, pieces[0])
    report = numbers(before, added, cut, shape)
    print(json.dumps(report, indent=1), flush=True)
    web_, sides = report['web'], report['sides']
    assert report['solids'] == 1
    assert web_['in_the_pin_trough_mm3'] == 0 and web_['in_the_seated_pin_mm3'] == 0 and web_['in_any_key_pose_mm3'] == 0
    assert web_['to_the_pin_trough_mm'] >= WEB_CLEAR - .02 and web_['to_paddle_and_wires_through_lift_and_click_mm'] >= .5
    assert abs(report['whole_carrier']['volume_change_not_explained_by_the_two_bearing_boxes_mm3']) < .02
    for side in sides.values():
        root = side['root_in_the_plate']
        assert side['root_in_the_block'] > .99, 'the web is not rooted in the block'
        # The root is judged where the plate is solid, not at its rounded rim: the buried foot and its landing.
        assert root['buried_foot_inside_solid_r78_plate'] > .99 and root['landing_at_its_top_mm2']['on_r78_plate'] > .99 * root['landing_at_its_top_mm2']['web'], 'the web foot is not in solid plate'
        assert root['depth_below_that_level_mm'] >= .30
        assert max(side['bore_and_socket_unchanged_mm3'].values()) < .001
        assert side['bed_contact_of_the_block_mm2']['r79'] < side['bed_contact_of_the_block_mm2']['r78'] - 3.5
        assert len(side['islands_starting_on_nothing']['r79']) <= len(side['islands_starting_on_nothing']['r78'])
    report['passes'] = True
    (OUT / 'hinge79.json').write_text(json.dumps(report, indent=2) + '\n')
    return shape


if __name__ == '__main__':
    build()
