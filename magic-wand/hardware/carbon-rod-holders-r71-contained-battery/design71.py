"""R71 key carrier: R70 with the battery inside the holder's outline.

Assembly frame as in R53-R70: the rod runs along Y through X = Z = 0, +Z is up,
+Y is the top (two-key) end and the rear face Y = BED lies on the print bed.

Where the pouch sits. It is 27 mm long and the holder ends at BED, so a pouch that does
not stand behind the holder starts at Y BED - 27 = 9.45: it lies under the upper-left
key's hot-swap socket and ends between the two left sockets. What it must pass (all read
from the fitted switch and socket models, checks71):

* The socket body hangs under the deck to Z 5.60 and its tape margin to 5.20.
* The stated solder-and-wire allowance on each socket terminal (R20) reaches Z 4.37. The
  inboard terminal of the upper-left socket and the rear terminal of the lower-left
  socket lie over the pouch. The pad ribs keep the pouch 0.15 mm under that allowance:
  top face Z 4.17, 3.10 mm under the deck (R70: against the deck).
* Outward, the side of the key bank: the outer rail is one 0.83 mm wall, 1.6 mm inside
  the bank's side so the rounded lower edge of the bank runs past it untouched.

The rail. R63-R70 had a rigid inboard wall and, outboard, a leaf spring behind its own
wall: 3.3 mm of rail outside the pouch. R71 has a rigid outer wall and one inboard wall
with the spring cut into it as a tongue (same section, lever and preload as R70's leaf).
Both walls and both lips start at Y 20.40, where R70's rail started, and three pad ribs
at Y 21.80: the upper-left socket still comes up from below in front of them, and the
strip of deck behind that socket stays free for its tape and wires. The rail holds the
rear 16.05 mm of the pouch; its nose runs 10.95 mm forward under the socket.

The guard. R70's left top arm crossed under the pouch's nose and the crown's rear bar lay
under it. The arm keeps its root and its first 3.9 mm. From there it runs down beside the
pouch's inboard face, turns round the nose and reaches the crown from the front. Where it
passes in front of the nose, at the pouch's mid height, it is the pouch's front stop. The
crown's hub moves 2.7 mm toward the lower row and its three bars keep their far end, their
height and their section. No guard member is lower than before.

Rear outline. Seen from above, R70's two rear shoulders differed: the right bank had moved
2 mm forward with its key, and the left carried R63's square roof over the battery. In R71
the left bank's plate behind Y 24 is cut to the mirror image of the right bank's outer
outline, which only removes plastic. The battery rail keeps a 2.95 mm roof strip over its outer wall.

Build: R70's own steps up to the shortened holder, then this battery step, then R70's
edge rounds. Nothing here is a claim of physical fit.
 — Claude Fable 5.2"""
from hashlib import sha256
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
if str(HARDWARE / 'carbon-rod-holders-r70-short-holder') not in sys.path:
    sys.path.insert(0, str(HARDWARE / 'carbon-rod-holders-r70-short-holder'))

import design70 as r70  # noqa: E402
import hinge71 as hinge  # noqa: E402

r69, r66, old, b, r61 = r70.r69, r70.r66, r70.old, r70.b, r70.r61    # old is design63, b is build53
r62 = old.r62
OUT = HERE / 'exports'
HOLDER = r70.HOLDER
BED, DECK, PLATE_TOP = r70.BED, r70.DECK, r70.PLATE_TOP
PACK = old.PACK                                           # 11.8 x 27.0 x 3.9, Micron 72217 nominal

# ------------------------------------------------------------------ what the fitted keys allow
SOCKET_Z = 5.60                                           # underside of both left hot-swap socket bodies
TAPE_Z = 5.20                                             # underside of their tape margin
SOLDER_Z = 4.37                                           # underside of the stated solder-and-wire allowance on their terminals (R20)
POST_TIP_Z = 6.27                                         # the three switch posts, 1.00 mm under the deck

# ------------------------------------------------------------------ the pouch
PACK_Y0 = BED - PACK[1]                                   # 9.45: the pouch ends at the rear face (R63-R70: 21.9)
PAD_Z = SOLDER_Z - 0.15                                   # 4.22: underside of the pad ribs
PACK_Z = (PAD_Z - 0.05 - PACK[2], PAD_Z - 0.05)           # 0.27 to 4.17 (R63-R70: 3.32 to 7.22)
PACK_MID = sum(PACK_Z) / 2
WALL, CLEAR, LIP_T, LIP_W = old.WALL, old.CLEAR, old.LIP_T, old.LIP_W    # 0.83, 0.07, 0.80, 2.4
EDGE_INSET = 1.60                                         # outer wall face inside the bank's side (the edge round is 1.5)
BANK_SIDE_X = -29.95
PACK_X = (BANK_SIDE_X + EDGE_INSET + WALL + CLEAR, BANK_SIDE_X + EDGE_INSET + WALL + CLEAR + PACK[0])   # -27.45 to -15.65
LIP_TOP = PACK_Z[0] - 0.15
LOW = LIP_TOP - LIP_T                                     # -0.68: lowest point of the rail (R70: 2.37)

# ------------------------------------------------------------------ the rail
RAIL_FROM_Y = 20.40                                       # as R70's rail: behind the upper-left socket, its loading space and its tape
LEAF_T = r70.LEAF_T                                       # 1.04
ALLOWANCE = old.LEAF_GAP - old.SHOE                       # 0.47: pouch width allowance behind the shoe, as R63
INNER_X = (PACK_X[1] + ALLOWANCE, PACK_X[1] + ALLOWANCE + LEAF_T)    # -15.18 to -14.14
FULL_FROM_Y = 20.95                                       # full-height inboard wall from here; in front it stays under the inner switch post
LOW_TOP_Z = 5.00                                          # top of that short front strip
ROOT_LENGTH = 2.15                                        # solid wall between the tongue and the rear face
TONGUE_Y = (23.40, BED - ROOT_LENGTH)                     # free end to root
TONGUE_Z = (PACK_MID - 1.18, PACK_MID + 1.18)             # 2.36 high about the pouch's mid height, as R70's leaf
SLOT = 0.70                                               # gap round the tongue (the strip below it stays 1.0 mm)
LEVER = 8.25                                              # root to shoe centre, as R70
SHOE_LENGTH, SHOE_Z = 3.60, (PACK_MID - 1.15, PACK_MID + 1.15)
SHOE = old.SHOE                                           # 0.21 into the nominal pouch
PAD_FROM_Y = 21.80                                        # behind the centre post (to Y 21.55), where R70's pouch began
PAD_X = ((PACK_X[0] - CLEAR - .01, -25.40), (-22.40, -20.60), (-17.90, -16.10))   # the outer rib is one piece with the outer wall
ROOF = (28.00, 1.20)                                      # roof strip over the outer wall and its pad rib: from Y, thickness
STRIP_X1 = -25.40                                         # inboard edge of that strip (the outer pad rib's edge)
TAPER_FROM_Y = 24.00                                      # behind this the left bank's plate is cut to the mirror image of the right bank's
BANK_FROM = 11.52                                         # outer face of the bearing blocks: the banks' rear plates start here
HEEL = (2.20, 0.80)                                       # under the outer lip at the rear face, for the base fin: length, depth

# ------------------------------------------------------------------ the left guard (written for the right, then mirrored, as R62)
ARM_R, BAR_R = 1.32, 1.26                                 # R62's sections
ARM_KEEP_T = 0.25                                         # R62's top arm stays from its root to this point of its curve
ARM_SIDE_GAP = ALLOWANCE + 0.08                           # 0.55: arm to the pouch's inboard face, past the rail's own width allowance
ARM_STOP_GAP = 0.05                                       # arm to the pouch's front face: the arm is the front stop
ARM_STOP_SPAN = 0.65                                      # the arm stays at that distance from the pouch's corner to here and on
ARM_HANDLE = 3.30                                         # how far the new arm keeps the old arm's direction where it leaves it
ARM_TURN_Y = 10.90                                        # the arm has come down to the pouch's mid height here
HUB = (20.40, 7.50, 0.88)                                 # where arm and crown bars meet (R62: 20.4, 10.2, 0.88)
BAR_CONTROL_Y = (HUB[1] - 0.70, 6.10)                     # the bars' two control stations (R62: 9.5 and 6.6, from a hub at 10.2)
OLD_SKIN = 0.15                                           # the old arm and bars are cut this much oversize

# ------------------------------------------------------------------ R63 rail that goes
OLD_ZONE = (-24.60, -8.50, 20.40)                         # X span and front of the R63 cradle under the deck


def carrier():
    body = None
    for _, body in steps():
        pass
    return old.one_piece(body, 'R71 carrier', limit=.05)


def export(path):
    """As design70.export: save and reload until the file reloads as one solid. — Claude Fable 5.2"""
    b.save_closed(path, carrier())
    for _ in range(6):
        back = b.load(path)
        if len(back.decompose()) == 1:
            return back
        b.save_closed(path, old.one_piece(back, 'exported R71 carrier', limit=.001))
    raise ValueError('the R71 carrier does not reload as one solid')


def steps():
    """R70's build to the shortened holder, the R71 battery rail, then R70's edge rounds. — Claude Fable 5.2"""
    for name, body in r70.steps():
        yield name, body
        if name == 'short_holder':
            break
    body = r70._tidy(battery(body), limit=.01)
    yield 'battery', body
    body = r70._tidy(body - r70.edge_cutter(body) - r70.crest_cutter(body), limit=.01)
    yield 'bank_edges', body
    body = r70._tidy(body - r70.rear_edge_cutter(body), limit=.01)
    yield 'edges', body


def main():
    OUT.mkdir(exist_ok=True)
    export(OUT / HOLDER)
    hinge.save_parts(OUT)                                 # R71 paddle and clips; post bar, leads and retainer are R70's, byte for byte
    for name in (HOLDER, hinge.PADDLE, *hinge.CLIPS.values(), hinge.POST_BAR, hinge.WIRES, hinge.LID):
        print('saved', name, sha256((OUT / name).read_bytes()).hexdigest(), flush=True)


# ------------------------------------------------------------------ pouch and rail
def pack():
    return b.box(PACK_X[0], PACK_X[1], PACK_Y0, PACK_Y0 + PACK[1], PACK_Z[0], PACK_Z[1])


def outer_wall_x():
    return PACK_X[0] - CLEAR - WALL, PACK_X[0] - CLEAR


def old_rail():
    """Everything of R63's cradle that hangs under the deck, and anything else in the new
    rail's lane. The roof land above the deck plane stays, and so does the guard arm's
    root. — Claude Fable 5.2"""
    x0, x1, y0 = OLD_ZONE
    deck = r70._snap(DECK)
    zone = b.box(x0, x1, y0, BED + 1., old.LOW - .1, deck)
    lane = b.box(outer_wall_x()[0] - .02, INNER_X[1] + .02, RAIL_FROM_Y - .02, BED + 1., LOW - .02, deck)
    return (zone + lane) - old_top_arm(.02)


def tongue_window():
    """The slot round the tongue: open above, below and at its free end. — Claude Fable 5.2"""
    y0, y1 = TONGUE_Y
    window = b.box(INNER_X[0] - .5, INNER_X[1] + .5, y0 - SLOT, y1, TONGUE_Z[0] - SLOT, TONGUE_Z[1] + SLOT)
    return window - b.box(INNER_X[0] - .6, INNER_X[1] + .6, y0, y1 + .1, TONGUE_Z[0], TONGUE_Z[1])


def shoe():
    centre = TONGUE_Y[1] - LEVER
    return r61.soft(PACK_X[1] - SHOE, INNER_X[0] + .2, centre - SHOE_LENGTH / 2, centre + SHOE_LENGTH / 2, SHOE_Z[0], SHOE_Z[1], .30)


# ------------------------------------------------------------------ guard
def _bezier(points, t):
    a, b1, c, e = (np.asarray(p, float) for p in points)
    t = np.asarray(t, float)[:, None]
    return (1 - t) ** 3 * a + 3 * t * (1 - t) ** 2 * b1 + 3 * t * t * (1 - t) * c + t ** 3 * e


def _mirror(shape):
    return shape.mirror((1, 0, 0))


def arm_split():
    """Where R62's top arm is left: the point of its curve at ARM_KEEP_T and its direction there."""
    p = [np.asarray(v, float) for v in r62.TOP_PATH]
    t = ARM_KEEP_T
    slope = (1 - t) ** 2 * (p[1] - p[0]) + 2 * t * (1 - t) * (p[2] - p[1]) + t * t * (p[3] - p[2])
    return _bezier(p, [t])[0], slope / np.linalg.norm(slope)


def arm_path():
    """Centre line of the new part of the top arm, right-hand side: from the kept root part
    down beside the pouch's inboard face, round its front corner at the pouch's mid height,
    across the front of its nose and on to the crown's hub. — Claude Fable 5.2"""
    start, heading = arm_split()
    corner = np.array((-PACK_X[1], PACK_Y0))                   # the pouch's inboard front corner
    beside, ahead = ARM_R + ARM_SIDE_GAP, ARM_R + ARM_STOP_GAP
    side = corner[0] - beside                                  # 13.78
    hub = np.asarray(HUB, float)
    t = np.linspace(0., 1., 16)
    down = _bezier([start, start + ARM_HANDLE * heading, (side, 13.60, PACK_MID + .38), (side, ARM_TURN_Y, PACK_MID + .30)], t)
    angle, reach = np.radians(np.linspace(180., 270., 13)), np.linspace(beside, ahead, 13)
    turn = np.column_stack([corner[0] + reach * np.cos(angle), corner[1] + reach * np.sin(angle), np.linspace(PACK_MID + .12, PACK_MID, 13)])
    front = np.array((corner[0] + ARM_STOP_SPAN, corner[1] - ahead, PACK_MID))
    out = _bezier([front, front + (1.50, 0., -.03), hub + (-1.40, .25, .07), hub], t)
    return np.vstack([down, turn, out])


def bar_paths():
    """The crown's three bars from the new hub. Their outer stations (X 15.1, 22.1, 28.1), their
    height and their far end are R62's. — Claude Fable 5.2"""
    return [[HUB, (x, BAR_CONTROL_Y[0], HUB[2]), (x, BAR_CONTROL_Y[1], HUB[2]), r62.CROWN_END] for x in (15.1, 22.1, 28.1)]


def new_guard(shrink=0.):
    """The re-routed arm and the three bars, left side. `shrink` gives their cores. — Claude Fable 5.2"""
    arm = r61.run([tuple(float(v) for v in p) for p in arm_path()], ARM_R - shrink)
    bars = [r61.curve(path, BAR_R - shrink) for path in bar_paths()]
    return _mirror(b.union([arm] + bars))


def old_top_arm(skin=0.):
    return _mirror(r61.curve(r62.TOP_PATH, ARM_R + skin))


def old_crown_bars(skin=0.):
    return _mirror(b.union([r61.curve([r62.CROWN_START, (x, 9.5, .88), (x, 6.6, .88), r62.CROWN_END], BAR_R + skin) for x in (15.1, 22.1, 28.1)]))


def kept_guard():
    """The left guard's lower rails and the closed outer tip, as R64 built them: never cut."""
    return r70.r64.guard_returns(True)


def old_guard_cutter():
    """R62's top arm below the deck from where the new arm leaves it, and the crown's three
    bars, both a little oversize; less the lower rails they meet. — Claude Fable 5.2"""
    keep_y = float(arm_split()[0][1])
    arm = old_top_arm(OLD_SKIN) ^ b.box(-80., 80., -80., keep_y, -80., r70._snap(DECK))
    return (arm + old_crown_bars(OLD_SKIN)) - kept_guard()


def guard(body):
    return (body - old_guard_cutter()) + new_guard()


def mirrored_right_plan(body):
    """Outer outline of the right key bank's plate behind TAPER_FROM_Y, mirrored onto the left.
    R70 moved the right bank 2 mm toward the lower row with its key; the left kept R62's rear
    shoulder and R63's roof over the battery, so from above the two sides differed. The whole
    right bank is projected, so its key opening and lightening windows are closed rings and
    drop out: only the outline is mirrored, never an opening. — Claude Fable 5.2"""
    zone = b.box(BANK_FROM, 80., -80., BED + 1., DECK + .05, PLATE_TOP - .05)
    outline = mf.CrossSection([ring for ring in (body ^ zone).project().to_polygons() if r70._area(ring) > 0])
    behind = mf.CrossSection.square((80., BED + 1. - TAPER_FROM_Y)).translate((-80., TAPER_FROM_Y))
    return outline.mirror((1., 0.)) ^ behind


def strip_box(z0, z1, past=.5):
    return b.box(outer_wall_x()[0], STRIP_X1, ROOF[0], BED + past, z0, z1)


def taper_cutter(plan):
    """Left bank plate and roof behind TAPER_FROM_Y that lie outside the mirrored right plan.
    The narrow roof strip over the outer rail stays. — Claude Fable 5.2"""
    deck = r70._snap(DECK)
    zone = b.box(-80., -BANK_FROM, TAPER_FROM_Y, BED + 1., deck, 60.)
    keep = plan.extrude(70.).translate((0, 0, deck - 5.))
    return zone - keep - strip_box(deck - 1., deck + ROOF[1])


def rail(plan):
    """Every member runs fore-aft from the bed, so each prints as a wall. The rounded members
    are built past the rear face and cut on it, so each stands on its full section. The pad
    ribs end where the deck above them ends. — Claude Fable 5.2"""
    ox0, ox1 = outer_wall_x()
    ix0, ix1 = INNER_X
    front, past = RAIL_FROM_Y, BED + .5
    parts = [
        r61.soft(ox0, ox1, front, past, LOW, DECK + .3, .30),                             # rigid outer wall
        r61.soft(ox0, PACK_X[0] + LIP_W, front, past, LOW, LIP_TOP, .30),                 # outer lip
        r61.soft(ix0, ix1, FULL_FROM_Y, past, LOW, DECK + .3, .30),                       # inboard wall, full height
        r61.soft(ix0, ix1, front, FULL_FROM_Y + .5, LOW, LOW_TOP_Z, .30),                 # its front strip, under the inner post
        r61.soft(PACK_X[1] - LIP_W, ix1, front, past, LOW, LIP_TOP, .30),                 # inboard lip
        strip_box(DECK, DECK + ROOF[1]),                                                  # roof strip over the outer wall
    ]
    x0, _, x1, _ = plan.bounds()
    ahead = mf.CrossSection.square((x1 - x0, 8.)).translate((x0, TAPER_FROM_Y - 7.99))    # in front of the taper line the deck is R70's, full width
    inside = (plan + ahead).offset(-(r70.EDGE_R + .40), mf.JoinType.Round)                # clear of the deck's edge round
    covered = inside.extrude(PAD_Z + 6.).translate((0, 0, PAD_Z - 1.)) + strip_box(PAD_Z - 1., DECK + 1.)
    pads = b.union([r61.soft(x0, x1, PAD_FROM_Y, past, PAD_Z, DECK + .3, .30) for x0, x1 in PAD_X])
    parts.append(pads ^ covered)                                                          # pad ribs under the deck
    length, depth = HEEL
    parts.append(r61.soft(ox0, PACK_X[0] + LIP_W, BED - length, past, LOW - depth, LOW + .3, .30))   # heel the left base fin stands on
    made = (b.union(parts) - tongue_window()) + shoe()
    return made ^ b.box(-80., 80., -80., BED, -80., 80.)


def battery(body):
    plan = mirrored_right_plan(body)
    return guard((body - old_rail()) - taper_cutter(plan)) + rail(plan)


def numbers():
    """The placement in one place, R70 beside R71. — Claude Fable 5.2"""
    ox0, ox1 = outer_wall_x()
    path = arm_path()
    return dict(
        pouch_mm=list(PACK),
        pouch_x_mm=dict(r70=list(old.PACK_X), r71=[round(v, 2) for v in PACK_X]), pouch_front_y_mm=dict(r70=old.PACK_Y0, r71=round(PACK_Y0, 2)),
        pouch_top_z_mm=dict(r70=round(old.PACK_Z[1], 2), r71=round(PACK_Z[1], 2)), pouch_underside_z_mm=dict(r70=round(old.PACK_Z[0], 2), r71=round(PACK_Z[0], 2)),
        rail_lowest_z_mm=dict(r70=round(old.LOW, 2), r71=round(LOW, 2)),
        moved_outward_mm=round(old.PACK_X[0] - PACK_X[0], 2), moved_down_the_holder_mm=round(old.PACK_Y0 - PACK_Y0, 2),
        lower_than_r70_mm=round(old.PACK_Z[1] - PACK_Z[1], 2), under_the_deck_mm=dict(r70=round(DECK - old.PACK_Z[1], 2), r71=round(DECK - PACK_Z[1], 2)),
        behind_the_rear_face_mm=dict(r70=round(old.PACK_Y0 + PACK[1] - BED, 2), r71=round(PACK_Y0 + PACK[1] - BED, 2)),
        held_by_the_rail_mm=dict(r70=round(BED - old.PACK_Y0, 2), r71=round(BED - RAIL_FROM_Y, 2)), nose_in_front_of_the_rail_mm=round(RAIL_FROM_Y - PACK_Y0, 2),
        outer_rail_mm=dict(r70=round(old.PACK_X[0] - (old.WALL_FACE - old.WALL), 2), r71=round(PACK_X[0] - ox0, 2)),
        inboard_rail_mm=dict(r70=round(old.CLEAR + old.WALL, 2), r71=round(INNER_X[1] - PACK_X[1], 2)),
        rail_width_overall_mm=dict(r70=round(old.PACK_X[1] + old.CLEAR + old.WALL - (old.WALL_FACE - old.WALL), 2), r71=round(INNER_X[1] - ox0, 2)),
        spring=dict(kind='tongue cut into the inboard wall', thickness_mm=round(LEAF_T, 2), height_mm=round(TONGUE_Z[1] - TONGUE_Z[0], 2),
                    lever_mm=LEVER, preload_mm=SHOE, width_allowance_mm=round(ALLOWANCE, 2),
                    r70=dict(thickness_mm=round(r70.LEAF_T, 2), height_mm=round(r70.LEAF_Z[1] - r70.LEAF_Z[0], 2),
                             lever_mm=round((BED - r70.ROOT_LENGTH) - sum(r70.SHOE_Y) / 2, 2), preload_mm=old.SHOE)),
        guard=dict(arm_radius_mm=ARM_R, bar_radius_mm=BAR_R, old_arm_kept_to_y_mm=round(float(arm_split()[0][1]), 2),
                   hub_mm=dict(r70=list(r62.CROWN_START), r71=list(HUB)), arm_centre_beside_the_pouch_x_mm=round(PACK_X[1] + ARM_R + ARM_SIDE_GAP, 2), arm_centre_in_front_of_the_nose_y_mm=round(PACK_Y0 - ARM_R - ARM_STOP_GAP, 2),
                   arm_to_the_pouch_side_mm=ARM_SIDE_GAP, arm_to_the_pouch_front_mm=ARM_STOP_GAP,
                   arm_lowest_centre_z_mm=dict(r70=round(float(_bezier(r62.TOP_PATH, np.linspace(0, 1, 200))[:, 2].min()), 2), r71=round(float(path[:, 2].min()), 2)),
                   bars_centre_z_mm=dict(r70=r62.CROWN_START[2], r71=HUB[2])))


if __name__ == '__main__':
    main()
