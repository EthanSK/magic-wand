"""R78 key holder: the battery sits 2 mm further back and 0.8 mm nearer the keypad, in a
rebuilt, plain pair of rails. Run this file to export the carrier and print its fit numbers.

Built from the exported R77 carrier. Guard, key seats, hinge, rod grip and shell are R77's.
Only the battery rails under the left bank change.

Ethan chose the placement that was tested on R77: the installed Micron pouch moves +2.00 mm
in Y (toward the service end) and +0.80 mm in Z (toward the keypad deck). PACK_OFFSET is
that move and nothing else repeats it. The rails stay rooted in the body and still end on
the old print-bed plane, Y 36.45; only the pouch stands 2 mm further out.

The rail ends should feel smooth, with no extra ledges catching the hand or pack.
The old rails had collected a raised cap under the outer lip's end, a leftover round stub beside
the inner wall, a paper-thin flange and a tab over the outer wall, a front strip of a
different height and two short upper lips. They are replaced by two channels of one
section each, the same from front to back, every edge rounded, both cut flush on the rear
plane:

* outer channel: wall, lip under the pouch and a roof over it that reaches under the
  solid shoulder, so the wall no longer hangs from a flange at the rear;
* inner channel: wall with the same spring tongue and shoe, lip under the pouch and a
  guide over it up to the deck.

The lips are 1.6 mm thick instead of 0.8. Raised 0.8 mm with the pouch, their underside is
where R77's was, so nothing reaches lower, and the two breakaway fins under the rails
stand on 1.6 mm of lip without the cap that used to be added for one of them.

Nothing stops the pouch from the front or the rear: it is held where it is pushed to by
the spring shoe, as since R74. No stop is added in the insertion path.

Dimensions are mm in the assembly frame: rod along Y, +Z toward the keypad, rear at +Y.
 — Claude Fable 5.2"""
from hashlib import sha256
from pathlib import Path
import json
import sys

import manifold3d as mf

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r77-even-keys'))
import design77 as old  # noqa: E402
import checks71  # noqa: E402

b = old.b
r74 = old.old.prior                                        # design74: the R72 place of the pouch and its spring shoe
r71, r72 = r74.r71, r74.r72
soft = r71.r61.soft                                        # box with every edge rounded
HOLDER = old.HOLDER
SOURCE_SHA = sha256((old.OUT / HOLDER).read_bytes()).hexdigest()
DECK, BED = old.DECK, r71.BED                              # 7.27 underside of the key plate; 36.45 rear plane, the print bed

# Ethan's chosen placement, relative to the R77 pouch. Defined once.
PACK_OFFSET = (0.0, 2.0, 0.8)
RISE = PACK_OFFSET[2]

# ------------------------------------------------------------------ rails (R71's section, moved 8 mm inboard by R72)
FROM_Y = r71.RAIL_FROM_Y                                   # 20.40: both channels begin here
EDGE = 0.30                                                # radius on every edge
OUTER_X = tuple(v + r72.INBOARD for v in r71.outer_wall_x())      # -20.35 to -19.52: outer wall
INNER_X = tuple(v + r72.INBOARD for v in r71.INNER_X)             # -7.18 to -6.14: inner wall with the tongue
LIP_W = r71.LIP_W                                          # 2.4 under each edge of the pouch
LIP_T = 2 * r71.LIP_T                                      # 1.6 (R77: 0.8, plus a cap at one end)
UNDER, OVER = 0.15, 0.05                                   # room under and over the pouch, as R71
ROOF_TO_X = -14.40                                         # outer roof: 5 mm over the pouch, under solid deck even at the rear
GUIDE_W = 1.15                                             # inner guide over the pouch, as R75's upper lip


def pack():
    """The installed pouch at Ethan's chosen place."""
    return old.old.pack().translate(PACK_OFFSET)


def service_lane():
    """The pouch's section from its seat out through the rear, for the insertion audit."""
    x, y, z, xx, yy, zz = pack().bounding_box()
    return b.box(x, xx, y, yy + 30, z, zz)


def shoe():
    """The spring's shoe: the only part meant to stand in the nominal pouch (0.21 mm)."""
    return r74.shoe().translate((0, 0, RISE))


def levels():
    _, _, z0, _, _, z1 = pack().bounding_box()
    lip_top = z0 - UNDER
    return dict(pack=(z0, z1), lip=(lip_top - LIP_T, lip_top), over=z1 + OVER)


def old_rails(body, original):
    """Everything R77 has under the deck in the rails' lane, with the flange and tab beside
    the outer wall, and the round stub R72 left beside the inner wall. The rod sleeve keeps
    its R71 surface. — Claude Fable 5.2"""
    lane = b.box(OUTER_X[0] - 1.50, INNER_X[1] + .06, FROM_Y - .07, BED + .1, -3., DECK - .001)
    stub = b.box(INNER_X[1] + .06, -4.0, FROM_Y - .07, 23.0, -3., DECK - .001)
    flange = b.box(OUTER_X[0] - 1.50, OUTER_X[0], 33.0, BED + .1, DECK - .002, DECK + .002)      # the last hairline of that flange, on the deck plane
    return body - lane - flange - (stub - original)


def tongue_window():
    """R71's slot round the spring tongue, at the pouch's new height and R72's place."""
    return r71.tongue_window().translate((r72.INBOARD, 0, RISE))


def rails():
    """Two channels, each one section from FROM_Y to the rear plane. Built past the plane and
    cut on it, so every member ends flush and stands on its whole section when printed.
     — Claude Fable 5.2"""
    x0, _, _, x1, _, _ = pack().bounding_box()
    z = levels()
    low, lip, over = z['lip'][0], z['lip'][1], z['over']
    past, top = BED + .5, DECK + .02
    outer = [
        soft(OUTER_X[0], OUTER_X[1], FROM_Y, past, low, top, EDGE),                 # wall
        soft(OUTER_X[0], x0 + LIP_W, FROM_Y, past, low, lip, EDGE),                 # lip the pouch rests on
        soft(OUTER_X[0], ROOF_TO_X, FROM_Y, past, over, top + EDGE, EDGE),          # roof, joined to the deck and the shoulder
    ]
    inner = [
        soft(INNER_X[0], INNER_X[1], FROM_Y, past, low, top + EDGE, EDGE),          # wall, with the tongue cut free below
        soft(x1 - LIP_W, INNER_X[1], FROM_Y, past, low, lip, EDGE),                 # lip
        soft(x1 - GUIDE_W, INNER_X[1], FROM_Y, past, over, top + EDGE, EDGE),       # guide over the pouch
    ]
    made = (b.union(outer + inner) - tongue_window()) + shoe()
    return made ^ b.box(-80., 80., -80., BED, -80., 80.)


def carrier():
    path = old.OUT / HOLDER
    before = b.load(path)
    original = b.load(r71.OUT / HOLDER)
    new = rails()
    # R77 keeps every fitting pose of the two left keys free of printed plastic. The new
    # rails are held to the same rule.
    keys = old.spaces()
    clearance = b.union([b.union(poses) for name, poses in keys.items() if name.startswith(('key_0', 'key_3'))])
    return before, new, old_rails(before, original) + (new - clearance), clearance


def build():
    OUT.mkdir(exist_ok=True)
    before, new, body, clearance = carrier()
    pieces = sorted(body.decompose(), key=lambda part: -part.volume())
    loose = [(round(part.volume(), 4), [round(v, 2) for v in part.bounding_box()]) for part in pieces[1:] if abs(part.volume()) > .0001]
    print('components', loose, flush=True)
    if sum(abs(part.volume()) for part in pieces[1:]) > .025:
        raise ValueError('Detached carrier detail')
    shape = old.old.old.clean_export(OUT / HOLDER, pieces[0])
    report = numbers(before, new, shape, clearance)
    print(json.dumps(report, indent=1), flush=True)
    assert report['solids'] == 1 and report['key_poses'] == [336, 0]
    assert report['pouch']['rigid_carrier_in_the_seated_pouch_mm3'] < .001 and report['pouch']['rigid_carrier_in_the_rear_entry_mm3'] < .001
    assert abs(report['spring']['shoe_in_the_pouch_mm3']['r78'] - report['spring']['shoe_in_the_pouch_mm3']['r77']) < .01
    assert report['rails']['cut_away_by_key_poses_mm3'] < .001 and report['rails']['lowest_z_mm']['r78'] >= report['rails']['lowest_z_mm']['r77_lips'] - .001
    return shape


def numbers(before, new, shape, clearance):
    """Fit numbers from the exported mesh, R77 beside R78. CAD only. — Claude Fable 5.2"""
    mm3 = lambda one, two: round(float((one ^ two).volume()), 4)
    gap = lambda one, two, reach=6.: round(float(one.min_gap(two, reach)), 3)
    seat, was = pack(), old.old.pack()
    lane = service_lane()
    spring, old_spring = shoe(), r74.shoe()
    rigid = shape - spring
    x0, y0, z0, x1, y1, z1 = seat.bounding_box()
    z = levels()
    keys = old.spaces()
    fixed = {name: poses[-1] for name, poses in keys.items() if name.startswith(('key_0', 'key_3')) and ('soldered_socket' in name or 'tape_zone' in name or 'maximum_socket' in name)}
    front = shape ^ b.box(-40, 40, -50, FROM_Y - .01, -10, 30)
    held = b.box(-40, 40, FROM_Y, BED, -10, 30)
    under = (rigid ^ held ^ b.box(x0, x1, -80, 80, z0 - UNDER - .05, z0 - UNDER + .0)).project()
    over = (rigid ^ held ^ b.box(x0, x1, -80, 80, z1 + OVER, z1 + OVER + .05)).project()
    nose = rigid ^ b.box(x0 - 1., x1 + 1., -30., y0 + .01, z0 - 1., z1 + 1.)                      # what lies ahead of the seated pouch
    ahead = next((round(t, 1) for t in [v * .1 for v in range(0, 420)] if mm3(nose, seat.translate((0, -t, 0))) > .001), None)
    checked, hits = checks71.c70.routes(shape, keys)
    zone = b.box(OUTER_X[0] - 1.5, -4.0, FROM_Y - .07, BED + .1, -3., DECK - .001)
    outside = b.box(-80, 80, -80, 80, -80, 80) - zone - b.box(OUTER_X[0] - 1.5, -4.0, FROM_Y - .07, BED + .1, DECK - .001, DECK + .35)
    solid = lambda part: round(sum(float(p.volume()) for p in part.decompose() if p.volume() > 0), 3)
    return dict(
        revision='R78', physical_fit_verified=False, source_carrier_sha256=SOURCE_SHA, carrier_sha256=sha256((OUT / HOLDER).read_bytes()).hexdigest(),
        solids=len(shape.decompose()), pack_offset_mm=list(PACK_OFFSET),
        pouch=dict(box_mm=[round(v, 2) for v in seat.bounding_box()], deck_gap_mm=dict(r77=round(DECK - was.bounding_box()[5], 2), r78=round(DECK - z1, 2)),
                   behind_the_rear_plane_mm=dict(r77=round(was.bounding_box()[4] - BED, 2), r78=round(y1 - BED, 2)), inside_the_rails_mm=round(BED - FROM_Y, 2),
                   rigid_carrier_in_the_seated_pouch_mm3=mm3(rigid, seat), rigid_carrier_in_the_rear_entry_mm3=mm3(rigid, lane),
                   rear_entry_to_the_carrier_in_front_of_the_rails_mm=gap(front, lane, 2.),
                   rear_entry_to_fitted_socket_solder_and_tape_mm={name: gap(part, lane) for name, part in fixed.items()},
                   room_mm=dict(under=round(z0 - z['lip'][1], 2), over=round(z['over'] - z1, 2), outer_side=round(x0 - OUTER_X[1], 2), inner_side_behind_the_shoe=round(INNER_X[0] - x1, 2)),
                   bearing_mm2=dict(lips_under=round(under.area(), 1), roof_and_guide_over=round(over.area(), 1)),
                   located_by='the spring shoe only; nothing stops it from the front or the rear',
                   pushed_forward_it_first_meets_the_carrier_after_mm=ahead),
        spring=dict(shoe_in_the_pouch_mm3=dict(r77=mm3(before ^ old_spring, was), r78=mm3(shape ^ spring, seat)), shoe_box_mm=[round(v, 2) for v in spring.bounding_box()],
                    tongue_z_mm=[round(v + RISE, 2) for v in r71.TONGUE_Z], wall_left_under_and_over_the_slot_mm=[round(r71.TONGUE_Z[0] + RISE - r71.SLOT - z['lip'][0], 2), round(DECK - (r71.TONGUE_Z[1] + RISE + r71.SLOT), 2)]),
        rails=dict(from_y_mm=FROM_Y, end_on_the_rear_plane_y_mm=round(float(new.bounding_box()[4]), 2), lip_mm=dict(width_under_the_pouch=LIP_W, thick=LIP_T),
                   lowest_z_mm=dict(r77_lips=round(r71.LOW, 2), r77_cap=round(r71.LOW - r71.HEEL[1], 2), r78=round(float(new.bounding_box()[2]), 2)),
                   cut_away_by_key_poses_mm3=mm3(new, clearance), volume_mm3=dict(r77=solid(before ^ zone), r78=solid(shape ^ zone)),
                   changed_outside_the_rail_zone_mm3=dict(removed=solid((before - shape) ^ outside), added=solid((shape - before) ^ outside)),
                   plastic_over_the_fins_at_x_mm={str(x): round(float((shape ^ b.box(x - .85, x + .85, BED - 1.8, BED, -3., z['lip'][1] + .01)).bounding_box()[5] - (shape ^ b.box(x - .85, x + .85, BED - 1.8, BED, -3., z['lip'][1] + .01)).bounding_box()[2]), 2) for x in (-19.0, -8.0)}),
        key_poses=[checked, len(hits)])


if __name__ == '__main__':
    build()
