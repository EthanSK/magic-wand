"""R47 bottom click: the OP1 click moves to the DFRobot touch board's bottom edge.

Ethan, after the R46 key holder printed (17 Nov 2026): "the placement of where
the OP1 is, it's way too close to the hinge. So it's kind of hard to press
because it's so high up." ... "the mouse click itself should be touching the
DF Robot ... at essentially as close to the bottom as possible because of the
hinge mechanics." ... "It can stick out a bit more at the bottom to allow for
the board to be held." ... "Maybe shift the holes for the OP1 right by like
two millimeters, just because it's slightly left right now." ... "design it so
the gap between the hinge and the top of the DF Robot board is as small as it
can be while still allowing it to rotate that tiny bit on the hinge".

Frame: X across the keys (+X is right in Ethan's top view), +Y towards the
two-key row, +Z up from the rod centre. Bracket ("cap") frame Y is world Y
minus CLICK_SHIFT (3.55) at the modelled angle 0.

Changes from R46, each owned by a parameter below:

- OP1 group: +2.0 mm in X; its plunger moves from world Y 3.05 to 6.5 mm
  behind the touch board's front edge (world Y -2.27). The hinge-to-plunger
  lever grows from 28.10 to 33.02 mm, against 39.52 mm to the board's front
  edge. The bought board's own holes, plunger, pins, sockets and connector keep
  their positions on the PCB.
- Why 6.5 mm and not nearer the edge: the plug under the board's far end sits
  about 18 mm behind the plunger. Any plunger nearer the front puts the plug
  over the middle rod-clip ring (Y 9.0-12.6). At 2.5 mm (lever 37.0) the
  from-below plug tube removed 27 mm3 of that ring, splitting its right side
  over 4.6 mm, and split three right guard ribs. At 6.5 mm the ring is untouched.
- Plan yaw 25 -> 19 degrees. Larger yaws, or the 2 mm shift with 20 degrees,
  bring the board's far corner within 0.6 mm of the upper-right Choc clip
  relief; at 18 degrees or less the plug nears the rod.
- The harness plug is fitted to the OP1 board before the board goes in, and
  both drop in from above. Its pocket stops 0.15 mm under the plug instead of
  running down through the rod clip as R32-R46's from-below entry did. The
  lead still presses into its open underside groove.
- A rounded centre chin below the bottom keys carries the OP1 board's lower
  end. The board slot is open at that end: the fitted R46 board's body sat
  on the lower lip although its holes fitted, so its true length there is
  unknown. The floor runs 1.2 mm past the modelled board end.
- Stops: the longer lever moves more plunger per degree, so the backup feet,
  the adjustment-screw landing and the screw's start turns are re-set
  (HEEL_TOP, LANDING_RAISE, START_TURNS) and re-checked in build47.
- Guard legs: the plug pocket cuts the deck ends of the R2 and R3 right guard
  legs. A rounded bar (LANDING_RUN) ahead of the pocket ties them, through
  the R1 leg, into the centre deck again. Its bonds are measured separately.
- Hinge: arms, tabs, roots, squeeze stop and supports move 0.4 mm towards
  the board, so the board-to-support gap falls from 2.97 to 2.57 mm. The arm
  length is unchanged. R42's pocket for the Gravity pin tails must still end
  ahead of the arm-root bridge; a shorter arm would raise the root strain
  that failed in hand assembly before. The supports reach back to the rear
  (bed) face again.
- Unchanged: the touch board and its seat, posts and clips, the four Choc
  seats, the rod clips, the finger rests and R46 braces.

Bought-part sizes remain photo-derived (OP1: Endgame Gear EGG-SP-U1 renders;
DFR0030 V2: distributor sheet and photos). This module writes nothing and
claims no physical fit, click feel or strength.
"""
from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R46 = HERE.parent / 'carbon-rod-holders-r46-middle-to-edge'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R46))
import holder46 as h46  # noqa: E402  (imports the R45..R26 chain; builds nothing)

d = h46.d                 # holder44: raised keys and finger rests
p = d.previous            # holder42: lower touch seat, pin pocket
q = p.prev                # holder41: diagonal OP1, DFRobot bracket, checks
r = q.r                   # holder31: rear snap hinge
base = q.base             # holder38: stop screw, motion limits
h32, h29, h28, r39 = q.h32, r.h29, q.h28, q.r39
box, union = q.box, q.union
CARRIER, BRACKET, CLIP = q.CARRIER, q.BRACKET, q.CLIP
R46_ASSEMBLY = R46 / 'exports/key-holder-only/R46-Key-Carrier-assembly.stl'

# --- R46 reference values (read before configure) ----------------------------
R46_PLUNGER_XY = tuple(q.PLUNGER_XY)       # (-1.6, 3.05) world
R46_YAW = q.OP1_YAW                        # -25 degrees
R46_AXIS_Y = r.AXIS_Y                      # 27.6 bracket frame
R46_LEVER = q.LEVER                        # 28.1
R46_STOP_X = base.STOP_X                   # 8.3

# --- R47 parameters -----------------------------------------------------------
BOARD_FRONT = -12.31949       # R42-R46 touch-board pad edge, bracket frame (kept)
OP1_SHIFT_X = 2.0             # "shift the holes for the OP1 right by like two millimeters"
PUSH_FROM_FRONT = 6.5         # pusher centre behind the board front; the plug must clear the mid ring
OP1_YAW = -19.
HINGE_PULL = .4               # hinge towards the board; limited by the pin pocket
STOP_X = R46_STOP_X           # the right-hand landing stays clear of the moved slot
# The 33 mm lever moves the plunger 1.18x as far per degree as R46's 28.1 mm.
HEEL_TOP = 13.365             # R41-R46 13.42: backup feet meet 0.055 mm sooner
LANDING_RAISE = .20           # R41-R46 0.15: the screw, fully in, still lands first
START_TURNS = 1.7             # R41-R46 2.0: the softest setting stays below free height
# The plug pocket removes R46's spine landings of the R2 and R3 guard legs.
# One rounded bar ahead of the pocket ties the R3, R2 and R1 legs to the deck.
LANDING_RUN = ((9.4, 10.6, 4.35), (3.4, 10.6, 4.95))   # world centres
LANDING_RADIUS = .95
PLUG_POCKET_FLOOR = h32.PCB_Z - h32.PLUG_DEPTH - .15  # 0.15 mm under the pre-fitted plug
FRONT_FLOOR = False           # R35's touch web already carries the pusher root
FLOOR_FRONT = (BOARD_FRONT + .5, BOARD_FRONT + 4.1)   # starts with the seat rails
SLOT_OPEN_END = 8.0           # slot runs this far past the modelled PCB end
FLOOR_PAST_END = 1.2          # chin floor past the modelled PCB end
CHIN_WALL = 1.6               # beside the slot clearance
CHIN_ROOT_Y = -8.0            # world; buried 1.2 mm inside R46's bottom edge (-9.2)
CHIN_Z = (7.3, 11.35)         # R46 centre deck at its bottom edge
CHIN_ROUND = 1.2              # skin-contact edge radius


def configure():
    """Set every inherited module value before any solid is built."""
    for fn in (r.cap, r.board_front_y, base.geometry, base.hardware, q.hardware, q.op1_reliefs,
               q.lead_channel, q.carrier_parts, q.switch_relief, q.pusher, p.bracket_before_pin_relief,
               p.bracket):
        assert fn.cache_info().currsize == 0, fn
    g = HINGE_PULL
    r.AXIS_Y -= g
    r.ARM_ROOT_Y -= g
    r.HINGE_SHIFT -= g
    r.ARM_MIRROR_Y -= g
    r.ROOT = (r.ROOT[0] - g, r.ROOT[1] - g, r.ROOT[2], r.ROOT[3])
    r.ARM_OFFSET = r.ARM_OFFSET + np.array([0., -g, 0.])
    r.PINCH_Y = (r.PINCH_Y[0] - g, r.PINCH_Y[1] - g)
    r.board_front_y = board_front_y
    push_y = BOARD_FRONT + PUSH_FROM_FRONT
    plunger = (R46_PLUNGER_XY[0] + OP1_SHIFT_X, push_y + r.CLICK_SHIFT)
    q.PLUNGER_XY = p.PLUNGER_XY = plunger
    q.OP1_YAW = d.OP1_YAW = h32.PCB_YAW = OP1_YAW
    q.PUSH_Y = p.PUSH_Y = push_y
    q.LEVER = r.AXIS_Y - push_y
    q.REST = p.REST = r.REST = math.degrees(math.asin(q.DEPRESSION / q.LEVER))
    q.EARLY_ANGLE = base.EARLY_ANGLE = -(q.REST + math.degrees(.095 / q.LEVER))
    base.STOP_X = STOP_X
    q.HEEL_TOP, q.LANDING_RAISE = HEEL_TOP, LANDING_RAISE
    q.START_TURNS = START_TURNS
    q.SAMPLE_TURNS = tuple(np.linspace(0., START_TURNS, 10))
    q.hinge_repairs = hinge_repairs
    q.op1_reliefs = op1_reliefs
    r.supports = supports
    p.bracket_before_pin_relief = q.bracket_before_pin_relief = bracket_before_pin_relief


def board_front_y():
    return BOARD_FRONT


_r46_supports = r.supports
_r42_bracket_before_pin_relief = p.bracket_before_pin_relief


def supports():
    """R39 supports with caps, moved with the hinge and reaching the rear face again."""
    y = r.AXIS_Y + r.CLICK_SHIFT + h29.SUPPORT_HALF_Y
    x0, x1, z0, z1 = h29.SUPPORT_ROOT
    tail = box(*h29.SUPPORT_X, y - .01, h28.REAR, z0, r39.SUPPORT_TOP) + box(x0, x1, y - .01, h28.REAR, z0, z1)
    return _r46_supports() + r.mirrored(tail)


def hinge_repairs():
    """R41's arm extension, roots, squeeze stop, bridge and fillets, moved with the hinge."""
    arm_z, g = r39.ARM_Z, HINGE_PULL
    extension = r.mirrored(box(*h29.ARM_X, r.ARM_ROOT_Y - .6, 28.4 - g, *arm_z))
    roots = r.mirrored(mf.Manifold.batch_hull([
        box(1.85, 3.05, r.ARM_ROOT_Y - .6, r.ARM_ROOT_Y, *arm_z),
        box(3.05, 8.65, r.ARM_ROOT_Y - 3.0, r.ARM_ROOT_Y, 17.0, 19.0)]))
    stop = box(-.65, .65, r.ARM_ROOT_Y - .15, 27.6 - g, 17.0, 18.3)
    bridge = box(-2.5, 2.5, r.ARM_ROOT_Y - .6, r.ARM_ROOT_Y, 17.0, 18.3)
    radius, y = 1.5, r.ARM_ROOT_Y
    fillet = (box(3.05, 3.05 + radius, y, y + radius, *arm_z)
              - mf.Manifold.cylinder(2.1, radius, radius, 64).translate((3.05 + radius, y + radius, 16.95)))
    return extension + roots + stop + bridge + r.mirrored(fillet)


@lru_cache(maxsize=1)
def op1_reliefs():
    """R41's OP1 openings: the board slot runs open past the PCB's lower end and
    the plug pocket stops under the pre-fitted plug (no tube from below)."""
    c, side = q.SLOT_CLEARANCE, q.SLOT_SIDE_CLEARANCE
    slot = q.board_frame(box(-h32.PCB_HALF_X - c, h32.PCB_HALF_X + side, h32.PCB_Y[0] - SLOT_OPEN_END,
                             h32.PCB_Y[1] + c, h32.PCB_Z - .02, 16.5))
    barrels = q.diagonal(h32.board_frame(h32.socket_local(.35, sweep=True)))
    barrels = barrels + q._roofs(barrels)
    white = box(-h32.PLUG_HALF_X - .52, h32.PLUG_HALF_X + .52, h32.PLUG_Y[0] - .5, h32.PLUG_Y[1] + .55,
                h32.MATE_TOP - .35, 16.5)
    mate = box(-h32.MATE_HALF_X - .45, h32.MATE_HALF_X + .45, h32.MATE_Y[0] - .4, h32.MATE_Y[1] + .4,
               PLUG_POCKET_FLOOR, h32.MATE_TOP + .15)
    connector = q.board_frame(white + mate) + q.lead_channel()
    pilots = q.diagonal(h32.screw_pilots(h32.PCB_Z - 3.75))
    pilots = pilots + q._roofs(pilots)
    return slot, barrels, connector, pilots


def front_floor():
    """Crossbar between the seat rails under the touch board's front, carrying the pusher root."""
    raw = box(-r.RAIL_X[0] - .1, r.RAIL_X[0] + .1, *FLOOR_FRONT, 18.5, 19.2)
    return raw - q.switch_relief() - base.stop_pilot()


@lru_cache(maxsize=1)
def bracket_before_pin_relief():
    shape = _r42_bracket_before_pin_relief()
    return shape + front_floor() if FRONT_FLOOR else shape


@lru_cache(maxsize=1)
def rib_landing():
    """The right guard legs' new deck landing, cut like R44's members and by the OP1 reliefs."""
    working = d.geometry()[1]
    raw = d.h33.rounded_run(LANDING_RUN, radius=LANDING_RADIUS)
    cut = d.r22.spaces16.carve(raw - d.finger_rest_keepouts(), d.socket_print_cutters(working),
                               'R47 right guard leg landing') - d.socket_approach_relief()
    return cut - union(q.op1_reliefs())


def chin_outline():
    """World XY polygon of the chin: the OP1 lower end plus walls, back to the R46 deck."""
    c, side = q.SLOT_CLEARANCE, q.SLOT_SIDE_CLEARANCE
    xl, xr = -h32.PCB_HALF_X - c - CHIN_WALL, h32.PCB_HALF_X + side + CHIN_WALL
    y0 = h32.PCB_Y[0] - FLOOR_PAST_END
    a = math.radians(q.OP1_YAW)
    points = [q.board_point(xl, y0), q.board_point(xr, y0)]
    for x in (xl, xr):
        y = (CHIN_ROOT_Y - q.PLUNGER_XY[1] - x * math.sin(a)) / math.cos(a)
        points.append(q.board_point(x, y))
    return mf.CrossSection.batch_hull([mf.CrossSection.circle(.001, 4).translate(pt) for pt in points])


@lru_cache(maxsize=1)
def chin():
    """Convex chin with every exposed edge rounded (sphere-swept inner polygon)."""
    inner = chin_outline().offset(-CHIN_ROUND, mf.JoinType.Miter)
    corners = [tuple(v) for poly in inner.to_polygons() for v in poly]
    z0, z1 = CHIN_Z[0] + CHIN_ROUND, CHIN_Z[1] - CHIN_ROUND
    balls = [mf.Manifold.sphere(CHIN_ROUND, 32).translate((x, y, z)) for x, y in corners for z in (z0, z1)]
    return mf.Manifold.batch_hull(balls)


def summary():
    """Plain numbers for the report (call after configure)."""
    hw_axis = r.AXIS_Y + r.CLICK_SHIFT
    rear = BOARD_FRONT + r.BOARD_LENGTH
    support_front = r.AXIS_Y - h29.SUPPORT_HALF_Y - h29.SUPPORT_FRONT_EXTENSION
    return {
        'plunger_xy_world_mm': {'r46': list(R46_PLUNGER_XY), 'r47': [round(v, 4) for v in q.PLUNGER_XY]},
        'op1_yaw_deg': {'r46': R46_YAW, 'r47': q.OP1_YAW},
        'hinge_axis_world_y_mm': {'r46': round(R46_AXIS_Y + r.CLICK_SHIFT, 4), 'r47': round(hw_axis, 4)},
        'hinge_to_plunger_lever_mm': {'r46': round(R46_LEVER, 4), 'r47': round(q.LEVER, 4)},
        'hinge_to_board_front_edge_mm': {'r46': round(R46_AXIS_Y - BOARD_FRONT, 4), 'r47': round(r.AXIS_Y - BOARD_FRONT, 4)},
        'plunger_fraction_of_board_lever': {'r46': round(R46_LEVER / (R46_AXIS_Y - BOARD_FRONT), 4),
                                            'r47': round(q.LEVER / (r.AXIS_Y - BOARD_FRONT), 4)},
        'board_rear_edge_to_support_front_mm': {'r46': round(R46_AXIS_Y - h29.SUPPORT_HALF_Y - h29.SUPPORT_FRONT_EXTENSION - rear, 4),
                                                'r47': round(support_front - rear, 4)},
        'board_rear_edge_to_hinge_axis_mm': {'r46': round(R46_AXIS_Y - rear, 4), 'r47': round(r.AXIS_Y - rear, 4)},
        'rest_angle_deg': round(q.REST, 4),
        'stop_screw_xy_bracket_mm': {'r46': [R46_STOP_X, base.STOP_Y], 'r47': [base.STOP_X, base.STOP_Y]},
        'stop_screw_lever_mm': round(r.AXIS_Y - base.STOP_Y, 4),
    }


configure()
