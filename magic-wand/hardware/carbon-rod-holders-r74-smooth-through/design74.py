"""R74 key holder: the battery slides straight through, and the battery-side finger guard is
rebuilt from whole round rods. Run this file to export the carrier and its design numbers.

Built from the checked R73 carrier. Only the left (battery-side) bank changes below its
deck, plus four unused openings in the key plate.

Battery. Ethan: "It should be flat so I can push the battery all the way through." The
pouch keeps its R72 place, rails, lips and spring. Everything printed that stood in its
section in front of the rails is gone: the arm that stopped its nose, the strut beside it,
the inner guard leg, the crown bars and the stub of an older arm above it. The path is
open from behind the holder to in front of it.

Guard. Ethan: "We can't have any sticky-outy things... It should be exactly the same as
the other one." Two bought-part facts decide what "the same" can be on this bank:

* the lower-left hot-swap socket faces outward and is fitted, prewired, by sliding it in
  from the side, 1.8 mm low, along its whole length (Y -4.67 to 9.68, Z 2.57 to 8.85).
  A leg that comes down gently from the front rim, as the other three do, would stand in
  that slot wherever it is put outboard of X -22.35;
* inboard of X -19.45 the battery now passes.

So no rod may slope down from the front rim anywhere on this bank. What is built instead:

* the outer leg has the right bank's outer leg mirrored in plan and in section (1.35 mm
  radius, same root place on the rim), but it comes straight down behind the rim first
  and turns under the socket's slot, then runs back at the guard's usual depth;
* a second, inner branch runs forward beside the battery path and ends in a slim post up
  to the deck between the switch's centre post and its front peg;
* both meet a rear leg that climbs to the solid deck between the two keys.

Every member is one smooth rod that ends inside the deck: no free end, nothing clipped by
a clearance mask, nothing in the battery path or in a socket's way.

Plate openings. Ethan: "you can remove the holes from the bottom because the metal thing
only has to poke through these in the middle." Each opening in the lower plate was tested
against the fitted switch and socket models and all 336 fitting poses. Four contain
nothing and are closed. Every opening that holds a centre post, a peg, a socket boss or a
contact stays as it is, and so does any opening a fitted part merely touches.

Dimensions are mm in the assembly frame: rod along Y, +Z up, rear face at Y 36.45.
 — Claude Fable 5.2"""
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r73-inset-guard'))
import design73 as r73  # noqa: E402

r72, r71, b, fit = r73.prior, r73.design, r73.b, r73.fit
OUT = HERE / 'exports'
HOLDER = r73.HOLDER
SOURCE_SHA = 'a9b1257475f234c7b0e2f5b4bd41be601e43fd17591202cd12545b3922ff3b7f'
DECK = r71.DECK                                            # 7.27: underside of the key plate
CLIP_FLOOR = 8.87                                          # top of the lower plate: the switch clips' relief starts here

# ------------------------------------------------------------------ battery path
PACK_X = tuple(v + r72.INBOARD for v in r71.PACK_X)        # -19.45 to -7.65: the R72 place
PACK_Z = r71.PACK_Z                                        # 0.27 to 4.17
RAIL_FROM_Y = r71.RAIL_FROM_Y                              # 20.40: the rails begin here
PATH_SIDE, PATH_UNDER, PATH_OVER = 0.40, 0.30, 0.10        # room kept round the pouch's section in front of the rails

# ------------------------------------------------------------------ guard
RADIUS = 1.35                                              # the other three legs
CROWN_Z = 0.88                                             # the guard's usual depth
MARGIN = r73.SOCKET_MARGIN                                 # 0.18: kept to every left key space
RIGHT_LEG = fit.smooth_return(28.3)                        # the shape reference: the right bank's outer leg
BEND = 2.00                                                # the outer leg's turn under the socket slot, centre line
COLLAR = (1.35, 0.90)                                      # radius where the outer leg enters the deck, and the height over which it gets there (no swelling)
TOP_IN = 0.05                                              # the outer leg's centre line ends this far inside the plate, its round end 0.2 mm under the clip relief
SPINE_X = -21.25                                           # inner branch and rear leg at the guard's depth: 0.45 mm from the battery path
WINDOW_X = -20.80                                          # and where they rise: between the socket's tape (X -21.90) and the path (X -19.45)
SLIM = 0.90                                                # half width there
RISE = (1.00, 2.60)                                        # Z over which they narrow and move to the window
REAR_ROOT = (9.60, 51.0)                                   # rear leg: Y where its centre line meets the deck, and its angle from the print axis
REAR_LAND_Y = 3.50                                         # it is level from here forward
INNER_POST_Y = -3.10                                       # inner post: between the centre post (to Y -1.7) and the front peg (from Y -4.55)
INNER_BEND = 1.80
INNER_R = 0.90                                             # radius of the inner post above the rise
APEX = (-21.30, 4.00)                                      # where the outer leg joins: 1.4 mm from the mirrored joint (-22.1, 5.2)
JOIN_FROM = 0.75                                           # the outer leg is the exact mirror up to this point of the reference curve

# ------------------------------------------------------------------ plate openings
KEYS = {'key_0': (-21.0, 0.0), 'key_3': (-21.0, 19.95), 'key_2': (21.0, 0.0), 'key_4': (21.0, 17.95)}
CELL = 16.6
PLAN_Z = 8.55                                              # inside the lower plate
SLIVER = 0.15                                              # mm3: less than this of a fitted part or pose inside an opening is a touch, not a use
GROUND = (-28.2, -14.2, -7.2, 11.0)                        # lower-left seat, inside its rounded edge: shallow unused pockets are filled flat


def _step(v):
    v = np.clip(v, 0., 1.)
    return v * v * (3. - 2. * v)


def _bezier(points, t):
    a, c1, c2, d = (np.asarray(p, float) for p in points)
    t = np.asarray(t, float)[..., None]
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * d


def rod(points, radii):
    """One smooth rod through the points: spheres joined pair by pair. — Claude Fable 5.2"""
    radii = np.broadcast_to(np.asarray(radii, float), (len(points),))
    balls = [mf.Manifold.sphere(float(r), 36).translate(tuple(float(v) for v in p)) for p, r in zip(points, radii)]
    return b.union([mf.Manifold.batch_hull([one, two]) for one, two in zip(balls[:-1], balls[1:])])


def mirrored_leg(t):
    """The right bank's outer leg, mirrored to the left bank."""
    return _bezier(RIGHT_LEG, t) * np.array([-1., 1., 1.])


def window_x(z):
    """Centre line X of the inner branch and the rear leg at a height."""
    return SPINE_X + (WINDOW_X - SPINE_X) * _step((np.asarray(z, float) - RISE[0]) / (RISE[1] - RISE[0]))


def outer_leg():
    """Ethan wants this leg exactly like the one on the other bank. It is: same place on the
    rim, same section, same curve seen from below as far as the joint. It cannot also slope
    like it, because the prewired socket slides in sideways behind it, so it comes straight
    down behind the rim and turns under that slot. — Claude Fable 5.2"""
    table = np.linspace(0., 1., 2001)
    curve = mirrored_leg(table)
    x_at = lambda y: np.interp(y, curve[:, 1], curve[:, 0])
    t_at = lambda y: float(np.interp(y, curve[:, 1], table))
    root_y = float(curve[0, 1])
    top = DECK + float(TOP_IN)                                           # the rod ends inside the plate
    post = [(float(x_at(root_y)), root_y, float(z)) for z in np.arange(top, CROWN_Z + BEND, -.25)]
    radii = [RADIUS + (COLLAR[0] - RADIUS) * float(_step((z - (DECK - COLLAR[1])) / COLLAR[1])) for _, _, z in post]
    angles = np.linspace(0., np.pi / 2, 17)
    turn = [(float(x_at(root_y + BEND * (1 - np.cos(a)))), root_y + BEND * (1 - np.cos(a)), CROWN_Z + BEND * (1 - np.sin(a))) for a in angles]
    level = [tuple(float(v) for v in (p[0], p[1], CROWN_Z)) for p in mirrored_leg(np.linspace(t_at(root_y + BEND), JOIN_FROM, 40))[1:]]
    here, ahead = mirrored_leg(JOIN_FROM), mirrored_leg(JOIN_FROM + .001)
    heading = (ahead - here)[:2] / np.linalg.norm((ahead - here)[:2])
    into = np.array([.15, .99]) / np.linalg.norm([.15, .99])            # it runs into the spine almost along it
    join = _bezier([(here[0], here[1]), tuple(here[:2] + 2.0 * heading), tuple(np.array(APEX) - 1.8 * into), APEX], np.linspace(0., 1., 24))[1:]
    points = post + turn + level + [(float(x), float(y), CROWN_Z) for x, y in join]
    return rod(points, radii + [RADIUS] * (len(points) - len(radii)))


def rear_leg():
    """What carries the fork while it prints and ties it to the solid deck between the two
    keys. It replaces the flat web Ethan saw sticking out under the battery holder: a round
    leg at the angle of the other guard arms, narrowed sideways where it passes between the
    socket's tape and the battery path. — Claude Fable 5.2"""
    slope = np.radians(REAR_ROOT[1])
    down = np.array([-np.cos(slope), -np.sin(slope)])                    # (dY, dZ) along the leg
    deck = np.array([REAR_ROOT[0], DECK])
    start, low = deck - .8 * down, deck + (DECK - 3.0) / np.sin(slope) * down
    straight = [start + (low - start) * f for f in np.linspace(0., 1., 28)]
    land = np.array([REAR_LAND_Y, CROWN_Z])
    bend = _bezier([low, low + 1.5 * down, land + np.array([1.3, 0.]), land], np.linspace(0., 1., 22))[1:]
    yz = np.vstack([straight, bend])
    leg = rod([(WINDOW_X, float(y), float(z)) for y, z in yz], RADIUS)
    return leg.translate((-WINDOW_X, 0, 0)).scale((SLIM / RADIUS, 1., 1.)).translate((WINDOW_X, 0, 0))      # 1.8 mm wide, 2.7 mm deep


def inner_branch():
    """The second branch of the fork. The battery passes where the other bank's inner leg
    would be, so this one runs beside the path and stands on a slim post under the key
    instead of on the rim. — Claude Fable 5.2"""
    level = [(SPINE_X, float(y), CROWN_Z) for y in np.arange(REAR_LAND_Y, INNER_POST_Y + INNER_BEND + .01, -.3)]
    angles = np.linspace(0., np.pi / 2, 15)[1:]
    turn = [(INNER_POST_Y + INNER_BEND * (1 - np.sin(a)), CROWN_Z + INNER_BEND * (1 - np.cos(a))) for a in angles]
    post = [(INNER_POST_Y, float(z)) for z in np.arange(CROWN_Z + INNER_BEND + .25, DECK + .65, .25)]
    up = [(float(window_x(z)), float(y), float(z)) for y, z in turn + post]
    radii = [RADIUS] * len(level) + [RADIUS + (INNER_R - RADIUS) * float(_step((z - RISE[0]) / (RISE[1] - RISE[0]))) for _, _, z in up]
    return rod(level + up, radii)


def guard():
    return outer_leg() + rear_leg() + inner_branch()


# ------------------------------------------------------------------ bought parts and fitting poses
@lru_cache(maxsize=1)
def key_models():
    """Fitted switches and sockets, and every inherited key space at each of its poses."""
    r71.old.k.old.configure_new_op1()
    import checks71
    return r72.r64.fitted_key_hardware(), checks71.c70.placed_spaces()


def left_spaces(margin=0.):
    """Everything the two left keys and their sockets occupy on the way in and when seated."""
    _, spaces = key_models()
    solid = b.union([pose for name, poses in spaces.items() if name.startswith(('key_0', 'key_3')) for pose in poses])
    solid ^= b.box(-60., -5., -20., 30., -10., 20.)
    if not margin:
        return solid
    return b.union([solid.translate(v) for v in ((0, 0, 0), (margin, 0, 0), (-margin, 0, 0), (0, margin, 0), (0, -margin, 0), (0, 0, margin), (0, 0, -margin))])


def battery_path(body):
    """The pouch's section pushed from behind the holder to in front of it: nominal between the
    rails, with room round it in front of them. Returns the two gauges. — Claude Fable 5.2"""
    front = float((body ^ b.box(-31., -5., -40., 0., -5., 12.)).bounding_box()[1])
    rails = b.box(PACK_X[0], PACK_X[1], RAIL_FROM_Y - .10, r71.BED + 8., PACK_Z[0], PACK_Z[1])
    ahead = b.box(PACK_X[0] - PATH_SIDE, PACK_X[1] + PATH_SIDE, front - 8., RAIL_FROM_Y - .10, PACK_Z[0] - PATH_UNDER, PACK_Z[1] + PATH_OVER)
    return rails, ahead


def shoe():
    return r71.shoe().translate((r72.INBOARD, 0, 0))


# ------------------------------------------------------------------ carrier
def clear_left_underside(body, original):
    """Take away everything printed under the left bank's deck in front of the rails: the old
    guard, the arm across the pouch's nose with its strut, and the stub of an older arm above
    the path. Beside the rod sleeve only what R72 added is removed, so the sleeve keeps its
    R71 surface. — Claude Fable 5.2"""
    under = b.box(-31.5, -9.05, -9.30, RAIL_FROM_Y - .07, -6., DECK - .001)
    beside = b.box(-9.05, -4.00, 2.00, RAIL_FROM_Y - .07, -6., DECK - .001)
    return body - under - (beside - original)


def plate_openings(body):
    """Every opening in the lower plate under the four keys, with what is in it: fitted switch
    or socket, and the largest volume any fitting pose puts there. — Claude Fable 5.2"""
    hardware, spaces = key_models()
    plan = body.slice(PLAN_Z)
    rows = []
    for key, (cx, cy) in KEYS.items():
        cell = mf.CrossSection.square((CELL, CELL)).translate((cx - CELL / 2, cy - CELL / 2))
        fitted = b.union([hardware[n] for n in hardware if n.endswith(key[-1]) and n != 'rod'])
        poses = [pose for name, group in spaces.items() if name.startswith(key) for pose in group]
        for hole in (cell - plan).decompose():
            if hole.area() < .30:
                continue
            x0, y0, x1, y1 = hole.bounds()
            at_edge = min(x0 - (cx - CELL / 2), cx + CELL / 2 - x1, y0 - (cy - CELL / 2), cy + CELL / 2 - y1) < .02
            column = mf.Manifold.extrude(hole.offset(.05, mf.JoinType.Round), CLIP_FLOOR - .01 - DECK - .02).translate((0, 0, DECK + .02))
            part = 0. if key == 'key_4' else float((column ^ fitted).volume())       # key_4's fitted model is not at its R70 place; its poses are
            pose = max(float((column ^ shape).volume()) for shape in poses)
            use = 'holds a fitted part' if max(part, pose) >= SLIVER else 'touched only' if max(part, pose) > .002 else 'empty'
            rows.append(dict(key=key, centre_mm=[round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2)], size_mm=[round(x1 - x0, 2), round(y1 - y0, 2)], area_mm2=round(hole.area(), 2),
                             on_the_seat_edge=bool(at_edge), fitted_part_mm3=round(part, 3), largest_pose_mm3=round(pose, 3), use=use,
                             closed=bool(use == 'empty' and not at_edge), plan=hole))
    return rows


def closed_openings(body):
    """Ethan: the metal only has to poke through the middle holes, so the others can go. Only
    openings that hold nothing at all are closed, from the deck's underside to the floor of
    the clip relief. An opening a part merely touches, or one on the seat's edge, stays.
     — Claude Fable 5.2"""
    rows = plate_openings(body)
    plugs = [mf.Manifold.extrude(row['plan'].offset(.03, mf.JoinType.Round), CLIP_FLOOR - DECK).translate((0, 0, DECK)) for row in rows if row['closed']]
    return (b.union(plugs) if plugs else mf.Manifold()), [{k: v for k, v in row.items() if k != 'plan'} for row in rows]


def flat_ground(body):
    """Shallow pockets in the underside of the lower-left seat that no fitted part and no
    fitting pose uses, filled level with the deck: the old guard roots stood in some of them
    and would be left as lumps. Through openings are not touched here. — Claude Fable 5.2"""
    hardware, _ = key_models()
    x0, x1, y0, y1 = GROUND
    plan = body.slice(PLAN_Z) ^ mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
    fill = mf.Manifold.extrude(plan, PLAN_Z - DECK).translate((0, 0, DECK)) - body - left_spaces() - hardware['switch_0'] - hardware['socket_0']
    pieces = [piece for piece in fill.decompose() if piece.volume() > .02]
    return (b.union(pieces) if pieces else mf.Manifold()), [dict(mm3=round(float(p.volume()), 3), box_mm=[round(float(v), 2) for v in p.bounding_box()]) for p in pieces]


@lru_cache(maxsize=1)
def build():
    path = r73.OUT / HOLDER
    if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('R73 carrier differs from the checked export')
    before = b.load(path)
    original = b.load(r71.OUT / HOLDER)
    body = clear_left_underside(before, original)
    body = max(body.decompose(), key=lambda part: part.volume())
    ground, pockets = flat_ground(body)
    plugs, openings = closed_openings(body)
    new = guard()
    parts = (body + ground + plugs + new).decompose()
    whole = max(parts, key=lambda part: part.volume())
    # Filling a pocket can shut an old hairline slit inside the plate. Such a closed slit is
    # dropped, which leaves solid plate there; anything else loose is an error.
    slits = [part for part in parts if part.volume() < -1e-4]
    for part in slits:
        box = part.bounding_box()
        if abs(part.volume()) > 1.5 or box[2] < DECK - .01 or box[5] > CLIP_FLOOR + .01:
            raise ValueError(('unexpected closed space', part.volume(), box))
    if sum(part.volume() for part in parts if part.volume() > 1e-4) - whole.volume() > .05:
        raise ValueError('detached material in the R74 carrier')
    sealed = [dict(mm3=round(abs(float(part.volume())), 3), box_mm=[round(float(v), 2) for v in part.bounding_box()]) for part in slits]
    return dict(before=before, cleared=body, guard=new, carrier=whole, pockets=pockets, openings=openings, sealed=sealed)


def carrier():
    return build()['carrier']


def export():
    OUT.mkdir(exist_ok=True)
    path = OUT / HOLDER
    shape = carrier()
    for _ in range(3):
        b.save_closed(path, shape)
        mesh = b.load(path)
        if mesh.status() == mf.Error.NoError and len(mesh.decompose()) == 1:
            return path
        shape = r71.old.one_piece(mesh, 'float32 seam', limit=.00001)
    raise ValueError('R74 must export as one watertight solid')


# ------------------------------------------------------------------ design numbers
def numbers():
    """What the exported mesh measures: the battery path, the guard against the left keys and
    against the other bank's leg, all 336 fitting poses, and what was removed or closed.
    CAD only: nothing here is a slice, a print or a fit in the hand. — Claude Fable 5.2"""
    import checks71
    made = build()
    body = b.load(OUT / HOLDER)
    before, new = made['before'], made['guard']
    hardware, spaces = key_models()
    mm3 = lambda one, two: round(float((one ^ two).volume()), 4)
    gap = lambda one, two, reach=4.: round(float(one.min_gap(two, reach)), 3)
    solid_mm3 = lambda shape: round(sum(float(part.volume()) for part in shape.decompose() if part.volume() > 0), 4)     # the inherited mesh has inverted hairlines beside X -12.7
    rails, ahead = battery_path(body)
    spring = shoe()
    bought = b.union([shape for name, shape in hardware.items() if name != 'rod'])
    checked, hits = checks71.c70.routes(body, spaces)
    left = left_spaces()
    pouch = b.box(PACK_X[0], PACK_X[1], -40., 60., *PACK_Z)
    table = np.linspace(0., JOIN_FROM, 400)
    mirror = rod([tuple(p) for p in mirrored_leg(np.linspace(0., 1., 80))], RADIUS)
    level = rod([(float(p[0]), float(p[1]), CROWN_Z) for p in mirrored_leg(table)], RADIUS + .02)
    low = new ^ b.box(-31., -24.2, float(mirrored_leg(0.)[1]) + BEND + .2, .6, -2., CROWN_Z + RADIUS + .05)       # the level run, clear of the turn and the joint
    survey = checks71.layer_survey(body)
    was = checks71.layer_survey(before)
    report = dict(
        revision='R74', physical_fit_verified=False, sliced=False, source_carrier_sha256=SOURCE_SHA, carrier_sha256=sha256((OUT / HOLDER).read_bytes()).hexdigest(),
        battery_path=dict(
            pouch_section_mm=dict(x=[round(v, 2) for v in PACK_X], z=[round(v, 2) for v in PACK_Z]),
            from_behind_the_holder_to_in_front_of_it_y_mm=[round(float(rails.bounding_box()[4]), 2), round(float(ahead.bounding_box()[1]), 2)],
            room_kept_in_front_of_the_rails_mm=dict(each_side=PATH_SIDE, under=PATH_UNDER, over=PATH_OVER),
            carrier_in_the_nominal_section_between_the_rails_mm3=dict(r73=mm3(before - spring, rails), r74=mm3(body - spring, rails)),
            carrier_in_the_section_with_room_in_front_of_the_rails_mm3=dict(r73=mm3(before, ahead), r74=mm3(body, ahead)),
            spring_shoe_in_the_pouch_mm3=dict(r73=mm3(before ^ spring, rails), r74=mm3(body ^ spring, rails)),
            fitted_switches_and_sockets_in_the_whole_path_mm3=mm3(bought, rails + ahead),
            guard_to_the_pouch_side_mm=gap(new ^ b.box(-40., 0., -40., 60., PACK_Z[0] - PATH_UNDER, PACK_Z[1] + PATH_OVER), pouch),
            rails_unchanged_mm3=dict(removed=solid_mm3((before - body) ^ b.box(-40., 0., RAIL_FROM_Y - .05, 60., -10., 20.)),
                                     added_below_the_deck=solid_mm3((body - before) ^ b.box(-40., 0., RAIL_FROM_Y - .05, 60., -10., DECK - .01))),
            not_modelled='the pouch wrap, its leads and connector; how the pouch behaves once its nose is past the rails'),
        guard=dict(
            members=['outer leg: rim root, straight down, turn, then the other bank\'s curve at the usual depth',
                     'inner branch beside the battery path, on a slim post under the key', 'rear leg to the deck between the two keys'],
            radius_mm=RADIUS, lowest_z_mm=dict(r73=round(float((before ^ b.box(-31., -9., -9.3, 20., -6., DECK)).bounding_box()[2]), 2), r74=round(float(new.bounding_box()[2]), 2)),
            volume_mm3=dict(left_guard_r73=round(float((before - made['cleared']).volume()), 1), left_guard_r74=round(float(new.volume()), 1)),
            in_the_left_key_spaces_mm3=mm3(new, left), in_those_spaces_grown_by_the_margin_mm3=mm3(new, left_spaces(MARGIN)), margin_mm=MARGIN,
            least_gap_to_the_left_key_spaces_mm=gap(new, left), in_the_fitted_switches_and_sockets_mm3=mm3(new, bought),
            outer_leg_against_the_other_bank=dict(
                root_on_the_rim_mm=dict(r74=[round(float(v), 2) for v in mirrored_leg(0.)[:2]], right_bank_mirrored=[round(float(v), 2) for v in mirrored_leg(0.)[:2]]),
                same_curve_seen_from_below_to_mm_from_the_joint=round(float(np.linalg.norm(mirrored_leg(1.)[:2] - mirrored_leg(JOIN_FROM)[:2])), 2),
                low_run_outside_the_mirrored_plan_mm3=round(float((low - level).volume()), 4),
                joint_mm=dict(r74=list(APEX), right_bank_mirrored=[round(float(v), 2) for v in mirrored_leg(1.)[:2]]),
                differs='in side view: it comes straight down behind the rim, then turns; the other three slope',
                why='the mirrored leg itself would stand %.2f mm3 in the lower-left socket\'s fitting poses' % mm3(mirror, left)),
            free_ends=0),
        key_fitting=dict(poses_checked=checked, obstructions=hits),
        plate=dict(openings=made['openings'], closed=sum(row['closed'] for row in made['openings']), pockets_filled_flat_in_the_lower_left_seat=made['pockets'], hairline_slits_closed_inside_the_plate=made['sealed'],
                   rule='closed only if no fitted switch or socket and no fitting pose puts anything in the opening; openings on a seat edge are left'),
        removed_from_r73=dict(under_the_left_deck_mm3=round(float((before - made['cleared']).volume()), 1), carrier_volume_mm3=dict(r73=round(float(before.volume()), 1), r74=round(float(body.volume()), 1))),
        print_layers=dict(r73=dict(islands_starting_on_nothing=was['islands_starting_on_nothing'], overhang_total_mm2=was['overhang_total_mm2'], largest=was['largest']),
                          r74=dict(islands_starting_on_nothing=survey['islands_starting_on_nothing'], overhang_total_mm2=survey['overhang_total_mm2'], largest=survey['largest']),
                          note='CAD sections with the rear face down, not a slice'),
        generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    report['passes'] = bool(
        report['battery_path']['carrier_in_the_nominal_section_between_the_rails_mm3']['r74'] == 0 and report['battery_path']['carrier_in_the_section_with_room_in_front_of_the_rails_mm3']['r74'] == 0
        and report['battery_path']['spring_shoe_in_the_pouch_mm3']['r74'] == report['battery_path']['spring_shoe_in_the_pouch_mm3']['r73'] > 0
        and report['battery_path']['fitted_switches_and_sockets_in_the_whole_path_mm3'] == 0 and max(report['battery_path']['rails_unchanged_mm3'].values()) < .001
        and report['guard']['in_those_spaces_grown_by_the_margin_mm3'] == 0 and report['guard']['in_the_fitted_switches_and_sockets_mm3'] == 0
        and report['guard']['outer_leg_against_the_other_bank']['low_run_outside_the_mirrored_plan_mm3'] < .01
        and checked == 336 and not hits and len(survey['islands_starting_on_nothing']) <= len(was['islands_starting_on_nothing']))
    return report


def write_numbers():
    report = numbers()
    (OUT / 'design74.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(export())
    result = write_numbers()
    print(json.dumps({key: result[key] for key in ('battery_path', 'key_fitting', 'passes')}, indent=1))
    print(json.dumps(result['guard'], indent=1))
    if not result['passes']:
        sys.exit('R74 design numbers failed')
