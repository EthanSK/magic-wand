"""R41: DFRobot DFR0030 touch board with the diagonal OP1 click under the bottom row.

Composes R39 (stronger hinge arms, hinge-support caps, rounded front deck
edge, lower battery-door catch) on R38's carrier rebuild. Run assembly41.py
through geometry_budget.py to check and export; this module writes nothing.

Frame: X across the keys, +Y towards the two-key row, +Z up from the rod centre.

Each change follows from Ethan's request for the DFRobot board, a diagonal
OP1 board and the click on the bottom row:

- The touch board is the DFRobot DFR0030 V2 on R35's two-post hinged bracket
  with its two printed post clips, not R36-R40's Grove board. R39's taller arms,
  root fillets, squeeze stop and R38's adjustable M2 stop are applied to it.
- The OP1 PCB uses R32's 25 degree plan yaw at R32's height (underside Z 9.2,
  no lift; the key carrier keeps R39's heights). Its plunger sits under the
  three-key row at PLUNGER_XY, 28.1 mm from the hinge axis; R40's was 16.2.
- With R32's plunger at X 0, the board's far corner reaches the upper-right
  Choc bay: its slot would merge with that key's clip relief. The whole OP1
  group therefore moves 1.6 mm left (and 0.5 mm towards the two-key row,
  which thickens the front wall at the board's near corner). The yaw keeps the
  under-board plug beside the rod; seated it clears the rod, but it cannot pass
  the rod vertically. The harness plug is therefore pushed in from below and
  its lead pressed into an open underside groove BEFORE the carrier goes on
  the rod. That is the existing order for wiring the Choc sockets.
- The bracket's pusher moves over the shifted plunger; its small contact face
  follows the carrier axes and stays inside the diagonal plunger.

OP1 PCB, connector and lead sizes remain photo-derived envelopes (Endgame Gear
EGG-SP-U1). DFR0030 length, hole pitch/position, thickness and its underside
connector pins are distributor-sheet, photo-derived or assumed (see R30).
"""
from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R39 = HERE.parent / 'carbon-rod-holders-r39-retention'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R39))
import holder39 as r39  # noqa: E402

base = r39.previous           # holder38: R22-based carrier rebuild, stop screw, checks helpers
old = base.old                # holder35: DFRobot bracket with touch web and backup stop feet
h, r, h32, h33, h28, r22 = base.h, base.r, base.h32, base.h33, base.h28, base.r22
H, box, union = base.H, base.box, base.union
CARRIER, BRACKET = 'Key_Carrier', 'DFRobot_Hole_Bracket'
CLIP = 'DFR0030_Post_Clip'
POST_CLIP_BORE_R = 1.0                    # clear printed neck bulge; 1.5 mm snap mouth stays
BATTERY, DOOR, battery_door = r39.BATTERY, r39.DOOR, r39.battery_door
door_displacement = r39.door_displacement

# --- OP1 layout -------------------------------------------------------------
OP1_YAW = h32.PCB_YAW                     # -25 degrees in plan; plug end towards +X/+Y
R32_ACTUATOR = (0., h32.ACTUATOR_Y)
PLUNGER_XY = (-1.6, 3.05)                 # world; R32 was (0, 2.55)
OP1_DZ = 0.                               # R32 height: PCB underside Z 9.2
PCB_Z = h32.PCB_Z + OP1_DZ
PCB_TOP = h32.PCB_TOP + OP1_DZ
SLOT_CLEARANCE = .65                      # R32/R38 board slot clearance
# The board's +X long side faces the upper-right Choc bay. A smaller side gap
# there keeps two printed lines between the slot and that key's clip relief.
SLOT_SIDE_CLEARANCE = .45

# --- click geometry ---------------------------------------------------------
PUSH_Y = PLUNGER_XY[1] - r.CLICK_SHIFT    # bracket frame
LEVER = r.AXIS_Y - PUSH_Y
FREE_TOP = PCB_TOP + h32.PLUNGER_H         # nominal free plunger top
DEPRESSION = .48                           # at the modelled angle 0, as R26-R35
PUSH_Z = FREE_TOP - DEPRESSION
REST = math.degrees(math.asin(DEPRESSION / LEVER))
EARLY_ANGLE = -(REST + math.degrees(.095 / LEVER))   # R37-R40 over-lift allowance
# R38's M2 stop screw, at a 34.75 mm lever against the 28.1 mm pusher lever. Its
# landing is 0.15 mm taller so that, fully screwed in, it still stops before
# the outer feet; the feet then stop before the plunger bottoms in its body.
LANDING_RAISE = .15
START_TURNS = 2.0                          # start position: turns out from fully in
PITCH = base.PITCH
SAMPLE_TURNS = tuple(np.linspace(0., START_TURNS, 10))
HEEL_TOP = 13.42                           # R37's 13.59 left the plunger to bottom first
SWITCH_CLEARANCE = .3                      # bracket to switch body through the press
PRESS_LIMIT = 1.0                          # degrees; beyond the backup stop contact
PAD_HALF = (.55, .3)                       # pusher face in carrier X/Y; fits the yawed plunger


def diagonal(shape):
    """R32 OP1 part (actuator at (0, 2.55), yaw -25) moved to this seat."""
    return shape.translate((PLUNGER_XY[0] - R32_ACTUATOR[0], PLUNGER_XY[1] - R32_ACTUATOR[1], OP1_DZ))


def board_point(x, y):
    """World XY of a point given in the OP1 PCB frame (actuator origin)."""
    a = math.radians(OP1_YAW)
    return (PLUNGER_XY[0] + x * math.cos(a) - y * math.sin(a),
            PLUNGER_XY[1] + x * math.sin(a) + y * math.cos(a))


def board_frame(shape):
    """PCB-frame solid (actuator origin) to world at this seat."""
    return diagonal(h32.board_frame(shape))


# --- bought OP1 parts -------------------------------------------------------
LEAD_Z = (h32.PCB_Z - h32.PLUG_DEPTH + h32.MATE_TOP) / 2 + OP1_DZ   # middle of the plug end face


def lead_points():
    """Plug end face, a short stub along the board, then an underside run to the rear."""
    s0 = board_point(0., h32.MATE_Y[1] - .2)
    s1 = board_point(0., h32.MATE_Y[1] + .9)
    z = LEAD_Z
    r0 = (s1[0] + .55, s1[1] + 1.2)
    xr = s1[0] + 1.05
    return [(*s0, z), (*s1, z), (*r0, z), (xr, s1[1] + 2.9, z), (xr, 30.5, z),
            (xr, 33.6, z - .6), (xr - .8, 37.0, z - 2.4), (xr - 2.2, 40.5, z - 4.4)]


def _tube(points, radius):
    balls = [mf.Manifold.sphere(radius, 24).translate(p) for p in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))


def op1_cable(radius=1.3):
    """Two-wire OP1 lead envelope from the plug's end face.

    It leaves the end face along the board, turns towards the two-key end and
    runs in an open underside groove beside the rod to the carrier's rear face.
    Diameter, stiffness and outlet height are not measured; fit-trial envelope.
    """
    return _tube(lead_points(), radius)


@lru_cache(maxsize=1)
def hardware():
    body, plunger = h32.switch()
    parts = {'board': h32.board(), 'sockets': h32.sockets(), 'housing': h32.white_housing(),
             'plug': h32.plug(), 'switch': body, 'terminals': h32.terminals(),
             'plunger': plunger, 'fasteners': h32.screws()}
    parts = {name: diagonal(shape) for name, shape in parts.items()}
    parts['op1_wire'] = op1_cable()
    return parts


def op1_board(pitch=17.9, hole_d=4.05):
    return diagonal(h32.board(pitch, hole_d))


def _teardrop(x, y, radius, z0, z1, direction):
    """Prism under a round hole/boss: 45-degree point along world Y (print axis)."""
    section = mf.CrossSection.batch_hull([
        mf.CrossSection.circle(radius, 48).translate((x, y)),
        mf.CrossSection.square((.02, .02)).translate((x - .01, y + direction * radius * math.sqrt(2) - .01))])
    return mf.Manifold.extrude(section, z1 - z0).translate((0., 0., z0))


def _roofs(holes, direction=-1.):
    """45-degree print roofs for vertical (world Z) round holes; rear-down print-up is -Y."""
    roofs = []
    for bore in holes.decompose():
        x0, y0, z0, x1, y1, z1 = bore.bounding_box()
        roofs.append(_teardrop((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, z0, z1, direction))
    return union(roofs)


def op1_seats():
    """R32 eyelet bosses and locating shoulders, each boss backed by a 45-degree
    rear-down print point (towards +Y) where it hangs below the slab."""
    saddles = diagonal(h32.mount_saddles())
    backs = []
    for y in h32.EYELETS:
        x, wy = board_point(0., y)
        stock = _teardrop(x, wy, 2.8, PCB_Z - 3.4, PCB_Z, 1.)
        # Square off only the print base's knife ends. Keep the original
        # locating shoulders above the PCB seat and the two eyelet centres.
        stock ^= box(x-3., x+3., wy-2.8+.2, wy+2.8*math.sqrt(2)-1., PCB_Z-3.4, PCB_Z)
        backs.append(stock)
    locators = saddles ^ box(-40., 40., -40., 40., PCB_Z-.03, PCB_Z+.6)
    return locators + union(backs)


@lru_cache(maxsize=1)
def lead_channel():
    """Lead groove, open below so the lead presses in; the stub joins the plug opening."""
    pts = lead_points()
    balls = [mf.Manifold.sphere(1.6, 24).translate(p) for p in pts]
    return union(mf.Manifold.batch_hull([a, b, a.translate((0., 0., -9.)), b.translate((0., 0., -9.))])
                 for a, b in zip(balls, balls[1:]))


@lru_cache(maxsize=1)
def op1_reliefs():
    """Board slot, socket barrels, white socket, plug entry from below, lead groove, pilots."""
    c, side = SLOT_CLEARANCE, SLOT_SIDE_CLEARANCE
    slot = board_frame(box(-h32.PCB_HALF_X - c, h32.PCB_HALF_X + side, h32.PCB_Y[0] - c, h32.PCB_Y[1] + c,
                           h32.PCB_Z - .02, 16.5))
    barrels = diagonal(h32.board_frame(h32.socket_local(.35, sweep=True)))
    barrels = barrels + _roofs(barrels)
    white = box(-h32.PLUG_HALF_X - .52, h32.PLUG_HALF_X + .52, h32.PLUG_Y[0] - .5, h32.PLUG_Y[1] + .55,
                h32.MATE_TOP - .35, 16.5)
    # Plug is pushed up from below with the carrier off the rod (R32 entry).
    mate = box(-h32.MATE_HALF_X - .45, h32.MATE_HALF_X + .45, h32.MATE_Y[0] - .4, h32.MATE_Y[1] + .4,
               -12., h32.MATE_TOP + .15)
    connector = board_frame(white + mate) + lead_channel()
    pilots = diagonal(h32.screw_pilots(h32.PCB_Z - 3.75))
    pilots = pilots + _roofs(pilots)
    return slot, barrels, connector, pilots


# --- carrier ------------------------------------------------------------------
def stop_landing():
    """R38's pad for the adjustment screw head, LANDING_RAISE taller."""
    y = base.STOP_Y + r.CLICK_SHIFT
    return box(base.STOP_X - 2.05, base.STOP_X + 2.05, y - 2.1, y + 2.1, 10.9, base.DECK_TOP + LANDING_RAISE)


def left_tail_web():
    """R40's short 45-degree web under the shared left guard tail."""
    # Carry the shared tail another millimetre into the frame: the narrower
    # R41 edge made the first slice leave an unfilled seam through this join.
    return r.d.wedge(-31., -26., [(13.4, 7.65), (15.5, 7.65), (15.5, 6.95), (13.55, 5.)])


@lru_cache(maxsize=1)
def carrier_parts():
    """R38's carrier composition with the diagonal OP1 mount and no Grove pocket."""
    base.set_key_layout()
    bottom, rear = h28.BOTTOM_EDGE, h28.REAR
    working = {name: shape for name, shape in r22.carrier_regions().items()
               if not name.startswith('key_1_')}
    body = r22.carrier_base()
    deck = box(-base.DECK_HALF, base.DECK_HALF, bottom, rear, r22.base.slab_bottom() - .01, base.DECK_TOP)
    bay_fill = box(-7.94, 7.94, -7.28, 7.28, 8.85, 10.02)
    slot, barrels, connector, pilots = op1_reliefs()
    socket_relief = box(-17.15 + base.KEY_SHIFT, -16.05 + base.KEY_SHIFT, 14.50, 16.35, 6.85, 7.82)
    fixed = union((body, deck, bay_fill, r.supports(), h.stop_posts(), stop_landing(),
                   op1_seats(), base.edge_rails()))
    fixed -= union((slot, barrels, connector, pilots, socket_relief, working['unloaded_clip_bore']))
    fixed ^= box(-40., 40., bottom, rear, -12., 30.)
    fixed = r22.spaces16.carve(fixed, working, 'r41 diagonal OP1')
    keepouts = union((r22.guard_keepout(), r22.slab_cutters(), barrels, connector,
                      working['key_3_socket_tape_zone']))
    ribs = {}
    for number, row in enumerate(h33.RIB_ROWS):
        for name, sign in (('R', 1), ('L', -1)):
            ribs[f'{name}{number + 1}'] = base.rib_at(row, number, sign) - keepouts
    saddle_tip = box(-5., 5., 16.80, 19., 3., 9.)
    ribs['R3'] -= saddle_tip
    ribs['L3'] -= saddle_tip
    for name, sign, y in (('L2', -1, 15.6), ('L3', -1, 16.4), ('R3', 1, 16.4)):
        web = h33.rounded_run([(sign * 2.75, y + 1.6, 4.45), (sign * 3.0, y + .55, 4.85),
                               (sign * 3.42, y - .6, 5.55)], radius=.67)
        ribs[name] += web - keepouts
    tip_relief = box(-29.5, -26.8, 12.6, 13.15, 4.4, 5.4)
    rod_relief = mf.Manifold.cylinder(.8, 4.1, 4.1, 96).rotate((-90., 0., 0.)).translate((0., 20.05, 0.))
    outside_rod = base.rod() - base.clip_bands()
    fixed -= tip_relief + rod_relief + outside_rod
    ribs = {name: rib - tip_relief - rod_relief - outside_rod for name, rib in ribs.items()}
    existing = fixed + union(ribs.values())
    # R40's web was sized for its wider upper row. Here it stops at the
    # existing left guard face instead of standing 1 mm proud of it.
    outer = (existing ^ box(-40., -25., 13.4, 15.5, 5., 7.65)).bounding_box()[0]
    web = r22.spaces16.carve(left_tail_web() ^ box(outer, 0., 0., 40., 0., 20.), working, 'R41 left guard web')
    web = union(piece for piece in web.decompose() if (piece ^ existing).volume() > .1)
    assert len(web.decompose()) == 1 and (web ^ fixed).volume() > 1.
    # Measure both real attachment interfaces before the web joins the carrier.
    joints = {'left guard web-to-frame bond': web ^ fixed,
              **{f'{name} guard-to-web bond': web ^ rib for name, rib in ribs.items() if name.startswith('L')}}
    fixed = fixed + web
    ribs = {name: rib + web if name.startswith('L') else rib for name, rib in ribs.items()}
    carrier = H.base.clean(fixed + union(ribs.values()), CARRIER)
    return carrier, working, fixed, ribs, web, joints


@lru_cache(maxsize=1)
def base_geometry():
    return carrier_parts()[:4]


def guard_web_interfaces():
    parts = carrier_parts()
    return {'left guard reinforcement web': parts[4], **parts[5]}


def lead_chamfer():
    """0.55 mm 45-degree chamfer on the right hinge cap's rear top edge.

    R39's caps are new against R35, and the DFRobot board's Gravity lead
    passes this edge as it bends down behind the carrier. The chamfer starts
    on the print bed (rear face down).
    """
    rear, top = h28.REAR, r39.SUPPORT_TOP
    return r.d.wedge(r.h29.SUPPORT_X[0] - .1, r.h29.SUPPORT_X[1] + .1,
                     [(rear - .55, top + .01), (rear + .01, top + .01), (rear + .01, top - .55)])


@lru_cache(maxsize=1)
def geometry():
    """R39 adds the hinge-support caps and the rounded front deck edge."""
    key, working, fixed, ribs = r39.geometry()
    return key - lead_chamfer(), working, fixed - lead_chamfer(), ribs


def carrier():
    return geometry()[0]


# --- bracket --------------------------------------------------------------------
def inverse_placement(angle):
    m = np.eye(4)
    m[:3] = r.placement(angle)
    return np.linalg.inv(m)[:3]


@lru_cache(maxsize=1)
def switch_relief():
    """Bracket-frame room swept by the turned switch body from early lift to beyond the backup stop."""
    c = SWITCH_CLEARANCE
    y = h32.ACTUATOR_TO_MIDDLE
    grown = board_frame(box(-2.9 - c, 2.9 + c, y - 6.4 - c, y + 6.4 + c, h32.PCB_TOP, h32.PCB_TOP + 6.5 + c))
    return mf.Manifold.batch_hull([grown.transform(inverse_placement(a).tolist())
                                   for a in np.linspace(EARLY_ANGLE, PRESS_LIMIT, 7)])


PUSHER_TOP = 19.15                    # 0.65 mm into the 18.5-19.2 bracket floor


@lru_cache(maxsize=1)
def pusher():
    """R40's printable wedge, over the same diagonal switch actuator.

    Its 1.1 x 0.6 mm face is aligned with the carrier, and fits inside the
    turned 2.9 x 1.2 mm plunger. The board stays diagonal. This avoids the
    underfilled triangular sections of a rotated, flared pusher.
    """
    rise = PUSHER_TOP - PUSH_Z
    run = PAD_HALF[1]+rise
    x0, x1 = PLUNGER_XY[0]-PAD_HALF[0], PLUNGER_XY[0]+PAD_HALF[0]
    shape = r.d.wedge(x0, x1, [(PUSH_Y-run, PUSHER_TOP), (PUSH_Y-PAD_HALF[1], PUSH_Z),
                                (PUSH_Y+PAD_HALF[1], PUSH_Z), (PUSH_Y+run, PUSHER_TOP)])
    # As in R40, the ends start with 0.7 mm stock rather than knife edges.
    return shape ^ box(x0, x1, PUSH_Y-run+.7, PUSH_Y+run-.7, PUSH_Z, PUSHER_TOP)


def pusher_root():
    """A small local floor thickening backs the pusher with continuous stock.

    Both ends begin inside the old floor and descend at 45 degrees, so this
    is permanent reinforcement rather than an unsupported hanging block.
    """
    x = PLUNGER_XY[0]
    shape = r.d.wedge(x-.9, x+.9, [(PUSH_Y-1.7, 19.2), (PUSH_Y-.5, 18.),
                                   (PUSH_Y+.5, 18.), (PUSH_Y+1.7, 19.2)])
    return shape ^ box(x-.9, x+.9, PUSH_Y-1., PUSH_Y+1., 18., 19.2)


def old_pusher_space():
    """R34's pusher below the floor, left in R35's bracket at X 0."""
    return box(-.8, .9, r.d.PUSH_Y - 1.85, r.d.PUSH_Y + 2.05, 16.9, 18.49)


def hinge_repairs():
    """R39's taller arms, root fan, 1.5 mm root fillets, squeeze stop and bridge."""
    arm_z = r39.ARM_Z
    extension = r.mirrored(box(*r.h29.ARM_X, r.ARM_ROOT_Y - .6, 28.4, *arm_z))
    roots = r.mirrored(mf.Manifold.batch_hull([
        box(1.85, 3.05, r.ARM_ROOT_Y - .6, r.ARM_ROOT_Y, *arm_z),
        box(3.05, 8.65, r.ARM_ROOT_Y - 3.0, r.ARM_ROOT_Y, 17.0, 19.0),
    ]))
    stop = box(-.65, .65, r.ARM_ROOT_Y - .15, 27.6, 17.0, 18.3)
    bridge = box(-2.5, 2.5, r.ARM_ROOT_Y - .6, r.ARM_ROOT_Y, 17.0, 18.3)
    radius = 1.5
    y = r.ARM_ROOT_Y
    fillet = (box(3.05, 3.05 + radius, y, y + radius, *arm_z)
              - mf.Manifold.cylinder(2.1, radius, radius, 64).translate((3.05 + radius, y + radius, 16.95)))
    return extension + roots + stop + bridge + r.mirrored(fillet)


def heel_relief():
    """R37: the outer feet stay as backup stops after the screw sets travel."""
    return r.mirrored(box(8.50, 10.30, -12., -9.85, 12.80, HEEL_TOP))


# --- DFR0030 Gravity socket pins ----------------------------------------------
# The maker's dimension photo shows a side-entry PH2.0 housing, laterally
# centred, 1 mm short of the board end. Its three pin stubs at 2 mm pitch sit
# behind the housing, about 9 mm from that end. Tail length below the board is
# not measured. An unclipped PH pin leaves about 1.8 mm below a 1.6 mm board,
# so 1.5 and 2.0 mm tails with solder fillets are checked at every
# position tolerance.
PIN_FROM_END = 9.0
PIN_Y_TOLERANCE, PIN_X_TOLERANCE = .6, .5
PIN_TAILS = (1.5, 2.0)
PIN_MARGIN = .25


def gravity_pins(tail=max(PIN_TAILS), dx=0., dy=0.):
    """Bracket-frame pin tails and solder fillets under the DFR0030 board."""
    rear = r.board_front_y() + r.BOARD_LENGTH
    z0, y = r.BOARD_Z[0], rear - PIN_FROM_END + dy
    return union(box(x + dx - .32, x + dx + .32, y - .32, y + .32, z0 - tail, z0 + .01)
                 + mf.Manifold.cylinder(.7, .32, .75, 32).translate((x + dx, y, z0 - .7))
                 for x in (-2., 0., 2.))


def pin_variants():
    return [(tail, dx, dy) for tail in PIN_TAILS for dx in (-PIN_X_TOLERANCE, 0., PIN_X_TOLERANCE)
            for dy in (-PIN_Y_TOLERANCE, 0., PIN_Y_TOLERANCE)]


def pin_relief():
    """Pocket over the inner tips of R39's root fans, under the whole pin band.

    It stays within the arms' outer faces (X +/-3.05) and ends before the arm
    roots and bridge. Its far end rises at 45 degrees for the front-down print.
    """
    rear = r.board_front_y() + r.BOARD_LENGTH
    band = PIN_Y_TOLERANCE + .32 + .2
    y0, y1 = rear - PIN_FROM_END - band, rear - PIN_FROM_END + band
    z, top = r.BOARD_Z[0] - max(PIN_TAILS) - PIN_MARGIN, r.BOARD_Z[0]
    x = r.h29.ARM_X[1]
    return r.d.wedge(-x, x, [(y0, z), (y1, z), (y1 + top - z, top), (y0, top)])


@lru_cache(maxsize=1)
def bracket_before_pin_relief():
    shape = old.bracket() - old_pusher_space()
    shape = shape + hinge_repairs() + base.stop_stock()
    shape = (shape - switch_relief()) + pusher_root() + pusher()
    return shape - base.stop_pilot() - heel_relief()


@lru_cache(maxsize=1)
def bracket():
    return H.base.clean(bracket_before_pin_relief() - pin_relief(), BRACKET)


def clip_part():
    """The R31 post clip, printed flat as modelled. Two are printed."""
    return r.clip_local()


def install():
    """Point R38/R39's shared functions at this revision before any solid is built."""
    r39.install_checks()                  # R39 arm height and bend
    r.CLIP_BORE_R = POST_CLIP_BORE_R
    r.REST = REST
    r39.BASE_GEOMETRY = base_geometry
    base.geometry = geometry
    base.bracket = bracket
    base.hardware = hardware
    base.EARLY_ANGLE = EARLY_ANGLE


assert base.geometry.cache_info().currsize == 0 and base.hardware.cache_info().currsize == 0
assert r.cap.cache_info().currsize == 0 and r.board_front_y.cache_info().currsize == 0
install()


# --- checks -------------------------------------------------------------------
def _max(pairs):
    return round(max(float((a ^ b).volume()) for a, b in pairs), 6)


def _vol(shape):
    return round(float(shape.volume()), 6)


def _gap(a, b, search=4.):
    return round(float(a.min_gap(b, search)), 4)


def dfr_group(pitch=r.HOLE_PITCH):
    """Bracket-frame DFRobot board, pad, top connector, 2 mm pin tails and both clips."""
    return r.sensor(pitch) + r.electrode() + r.connector() + gravity_pins() + r.clips()


def press_travel(angle_from, angle_to):
    x0, y0, _, x1, y1, z1 = r.electrode().bounding_box()
    point = np.array([(x0 + x1) / 2, (y0 + y1) / 2, z1, 1.])
    front = np.array([0., r.board_front_y(), r.BOARD_Z[1], 1.])
    out = {}
    for name, p in (('electrode_centre', point), ('board_front_edge', front)):
        out[name] = round(float((r.placement(angle_from) @ p)[2] - (r.placement(angle_to) @ p)[2]), 4)
    return out


def pusher_face_margin(angles):
    """Smallest XY margin of the complete contact face inside the bought plunger."""
    corners = np.asarray([(PLUNGER_XY[0]+x, PUSH_Y+y, PUSH_Z, 1.)
                          for x in (-PAD_HALF[0], PAD_HALF[0]) for y in (-PAD_HALF[1], PAD_HALF[1])])
    angle = math.radians(-OP1_YAW)
    inverse_yaw = np.asarray(((math.cos(angle), -math.sin(angle)),
                             (math.sin(angle), math.cos(angle))))
    margins = []
    for tilt in angles:
        world = corners @ r.placement(float(tilt)).T
        local = (world[:, :2]-np.asarray(PLUNGER_XY)) @ inverse_yaw.T
        margins.extend((np.asarray((1.45, .6))-abs(local)).ravel())
    return round(float(min(margins)), 4)


def r39_carrier():
    return BATTERY.read(R39 / 'exports' / f'{CARRIER}-assembly.stl')


def key_apertures(key):
    """Each Choc seat neighbourhood against R39's exported carrier (same key layout)."""
    old_key = r39_carrier()
    rows = {}
    for i, (x, y) in enumerate(r22.base.key_positions()):
        if i == 1:
            continue
        region = box(x - 7.7, x + 7.7, y - 7.7, y + 7.7, 7.7, 12.0)
        new, was = key ^ region, old_key ^ region
        rows[f'key_{i}'] = {'centre_mm': [round(x, 3), round(y, 3)],
                            'difference_mm3': round(float((new - was).volume() + (was - new).volume()), 4),
                            'seat_volume_mm3': round(float(new.volume()), 3)}
    return rows


def key4_walls(key):
    """Plastic between the OP1 slot and the upper-right Choc opening and clip relief.

    Measured on the final carrier at the plate and under-plate levels, within the
    Y span where the slot's far corner meets that bay.
    """
    slot = op1_reliefs()[0]
    out = {}
    x_key, y_key = r22.base.key_positions()[4]
    opening = r22.P['keys']['opening'] / 2
    relief = r22.P['bay']['clip_relief_half_x_mm']
    for name, z, edge in (('plate_ring_mm', 10.7, x_key - opening), ('under_plate_wall_mm', 9.45, x_key - relief)):
        sx = (slot ^ box(0., 40., y_key - 7.2, y_key + 7.2, z - .01, z + .01)).bounding_box()[3]
        out[name] = round(edge - sx, 3)
    return out


def front_wall(key):
    """Carrier material in front of the OP1 slot's near corner (towards Y -9.2)."""
    slot = op1_reliefs()[0]
    return round(slot.bounding_box()[1] - h28.BOTTOM_EDGE, 3)


@lru_cache(maxsize=1)
def checks():
    key, working, fixed, ribs = geometry()
    paddle = bracket()
    parts = hardware()
    bar = base.rod()
    switches = union(working[f'key_{i}_{p}'] for i in (0, 2, 3, 4) for p in ('switch', 'maximum_socket'))
    keys = switches + union(working[f'key_{i}_cap_travel'] for i in (0, 2, 3, 4))
    board_group = union(parts[n] for n in ('board', 'sockets', 'housing'))
    harness = parts['plug'] + parts['op1_wire']
    mouse = union(parts[n] for n in ('switch', 'terminals', 'plunger'))
    op1_fixed = union(parts[n] for n in ('board', 'sockets', 'housing', 'plug', 'op1_wire', 'switch', 'terminals', 'fasteners'))
    static = key + keys + op1_fixed
    installed = static + working['unloaded_clip_bore']
    touch = dfr_group()
    lead = r.gravity_lead()
    moving = paddle + touch
    rest_angles = np.linspace(-REST, 0., 25)
    hy = r.hole_y()
    necks = union(mf.Manifold.cylinder(r.NECK[1] - r.NECK[0] + .2, r.NECK_R + .02, r.NECK_R + .02, 48)
                  .translate((s * r.POST_X, hy, r.NECK[0] - .1)) for s in (-1, 1))
    clearance = {
        'choc_switches_and_sockets_to_carrier': _max([(switches, key)]),
        # OP1 is fitted with the carrier off the rod; the Choc keys may stay fitted.
        'op1_board_drop_with_keys_fitted': _max((board_group.translate((0., 0., z)), key + keys)
                                                for z in np.linspace(0., h32.BOARD_RISE, 57)),
        # Screw heads only: the shanks thread into the printed pilots by design.
        'op1_screw_heads_drop_with_keys_fitted': _max(((parts['fasteners'] ^ box(-40., 40., -20., 40., PCB_TOP + .01, 30.))
                                                       .translate((0., 0., z)), key + keys + board_group)
                                                      for z in np.linspace(0., h32.BOARD_RISE + 6., 45)),
        'op1_board_eyelet_pitch_range': _max([(op1_board(p, 3.6), key) for p in np.linspace(17.3, 18.5, 7)]),
        'op1_screw_shank_in_eyelets': _max([(op1_board(p, 3.6), parts['fasteners']) for p in np.linspace(17.3, 18.5, 7)]),
        'op1_plug_and_lead_from_below_off_rod': _max((harness.translate((0., 0., z)),
                                                      key + keys + board_group + parts['fasteners'])
                                                     for z in np.linspace(-9., 0., 37)),
        'op1_seated_lead': _max([(parts['op1_wire'], key + keys + bar)]),
        'op1_switch_install': _max((mouse.translate((0., 0., z)),
                                    key + keys + parts['board'] + parts['sockets'] + parts['fasteners'])
                                   for z in np.linspace(0., 8., 33)),
        'op1_pins_in_sockets': _max([(parts['terminals'], parts['sockets'])]),
        'op1_screw_heads_to_switch': _max([(parts['fasteners'], parts['switch'])]),
        # The carrier goes onto the rod after the OP1 harness is fitted.
        'rod_slide_past_fitted_op1': _max((bar.translate((0., y, 0.)), key - base.clip_bands() + op1_fixed)
                                          for y in np.linspace(-60., 0., 25)),
        'rod_snap_up_past_fitted_op1': _max((bar.translate((0., 0., z)), op1_fixed) for z in np.linspace(-6., 0., 25)),
        'hinge_stroke': _max((r.world(moving, a), installed) for a in rest_angles),
        'gravity_lead_stroke': _max((r.world(lead, a), installed + r.world(paddle, a)) for a in rest_angles),
        'gravity_lead_to_bracket_and_board': _max([(lead, paddle + r.sensor())]),
        'pinched_bracket_drop': _max((r.world(r.bent(paddle)).translate((0., 0., z)), installed)
                                     for z in np.linspace(0., 8., 21)),
        'bracket_arm_release': _max((r.world(r.bent(paddle, b)), installed) for b in np.linspace(0., 1., 13)),
        'dfr_board_and_pins_lift_off_posts': _max(((r.sensor() + gravity_pins(t, dx, dy)).translate((0., 0., z)), paddle)
                                                  for t, dx, dy in pin_variants() for z in np.linspace(0., 6., 25)),
        'dfr_pins_seated_all_positions_and_tails': _max((gravity_pins(t, dx, dy), paddle + r.clips())
                                                        for t, dx, dy in pin_variants()),
        'dfr_pins_click_stroke_all_positions': _max((r.world(gravity_pins(t, dx, dy), a), installed)
                                                    for t, dx, dy in pin_variants() for a in (-REST, 0., PRESS_LIMIT)),
        'dfr_board_on_posts_by_pitch': _max([(r.sensor(pitch=p), paddle) for p in np.linspace(*r.PITCH_RANGE, 5)]),
        'dfr_clip_seated': round(float((r.clips() ^ (paddle + r.sensor() + r.connector())).volume()), 6),
        'dfr_clip_slide_excluding_snap': _max((r.clips().translate((0., -y, 0.)), (paddle - necks) + r.sensor() + r.connector())
                                              for y in np.linspace(0., 5., 21)),
        'dfr_group_on_rod': _max((r.world(touch + lead, a), bar) for a in rest_angles),
        'rod_to_carrier_outside_clip_rings': _max([(bar, key - base.clip_bands())]),
        'rod_to_sockets_pins_housing_plug': _max([(bar, parts['sockets'] + parts['terminals'] + parts['housing'] + parts['plug'])]),
        'rod_to_op1_wire': _max([(bar, parts['op1_wire'])]),
    }
    limit_static = key + bar + keys + union(v for n, v in parts.items() if n != 'plunger')
    settings = []
    for turns in SAMPLE_TURNS:
        screw = base.stop_screw(turns)
        stop, contact = base.motion_limit(limit_static, screw)
        travel = base.actuator_travel(stop)
        settings.append({
            'turns_out': round(float(turns), 4), 'angle_deg': round(stop, 5),
            'nominal_plunger_travel_mm': round(travel, 4),
            'stop_height_above_switch_base_mm': round(base.SWITCH_FREE_REFERENCE - travel, 4),
            'screw_contacts_landing_mm3': (r.world(screw, contact) ^ key).volume(),
            'plastic_before_screw_contact_mm3': (r.world(paddle, contact) ^ limit_static).volume(),
        })
    steps = np.diff([row['nominal_plunger_travel_mm'] for row in reversed(settings)])
    backup, beyond = base.motion_limit(limit_static)
    backup_stops = [(r.world(paddle, beyond + .01) ^ post).volume() for post in h.stop_posts().decompose()]
    sweep = np.linspace(EARLY_ANGLE, backup, 29)
    full_stroke = {
        'dfr_board_clips_and_lead': _max((r.world(touch + lead, a), installed) for a in sweep),
        'bracket': _max((r.world(paddle, a), installed) for a in sweep),
        'bracket_to_switch_body': _max((r.world(paddle, a), parts['switch']) for a in sweep),
        'pinched_install_with_screw': _max(
            (r.world(r.bent(paddle) + base.stop_screw(turns)).translate((0., 0., z)), installed)
            for turns in (0., START_TURNS) for z in np.linspace(0., 8., 21)),
        'stop_screw_to_dfr_parts': max((base.stop_screw(t) ^ (touch + lead)).volume() for t in SAMPLE_TURNS),
    }
    pad_zone = box(PLUNGER_XY[0]-PAD_HALF[0]-1.2, PLUNGER_XY[0]+PAD_HALF[0]+1.2,
                   PUSH_Y-PAD_HALF[1]-1.2, PUSH_Y+PAD_HALF[1]+1.2, 0., PUSH_Z+.3)
    switch_gap_at_backup = _gap(r.world(paddle - pad_zone, backup), parts['switch'])
    pad_to_body_at_backup = _gap(r.world(pusher(), backup), parts['switch'])
    guard = h33.rib_metrics(fixed, ribs)
    fingertip = h33.fingertip_reaches(key)
    seats = []
    for eye in h32.EYELETS:
        x, y = board_point(0., eye)
        zone = box(x - 3.2, x + 3.2, y - 3.2, y + 3.2, PCB_Z - .25, PCB_Z + .1)
        seats.append(round(float((parts['board'].translate((0., 0., -.2)) ^ key ^ zone).volume()), 4))
    squeezed = r.bent(paddle)
    tab_box = box(2.4, r.h29.TAB_TIP + .5, r.AXIS_Y - .8, r.AXIS_Y + .8, r.h29.AXIS_Z - .8, r.h29.AXIS_Z + .8)
    arm = r.h29.arm_estimate()
    free_length = arm['root_to_tab_mm'] - 1.5
    arm['nominal_unfilleted_strain_percent_estimate'] = arm['root_strain_percent_estimate']
    arm['conservative_free_length_mm'] = round(free_length, 3)
    arm['root_strain_percent_estimate'] = round(arm['root_strain_percent_estimate'] * (arm['root_to_tab_mm'] / free_length) ** 2, 2)
    arm['physical_strength_verified'] = False
    lift = {f'{z:.2f}': _vol(r.world(paddle).translate((0., 0., z)) ^ key) for z in (.1, .3, .5)}
    hinge = {
        'released_tab_axial_engagement_mm': round((paddle ^ tab_box).bounding_box()[3] - r.h29.SUPPORT_X[0], 4),
        'squeezed_tab_clear_of_support_mm': round(r.h29.SUPPORT_X[0] - (squeezed ^ tab_box).bounding_box()[3], 4),
        'straight_lift_contact_by_height_mm3': lift,
        'straight_lift_retention_contact_mm3': lift['0.30'],
        'arm_bending_estimate': arm,
        'clip': r.clip_estimate(),
    }
    capture = {
        'board_seat_contact_mm3': _vol(paddle ^ r.sensor().translate((0., 0., -.1))),
        'board_lateral_capture_contact_mm3': _vol(paddle ^ r.sensor().translate((.55, 0., 0.))),
        'board_along_capture_contact_mm3': _vol(paddle ^ r.sensor().translate((0., .4, 0.))),
        'clip_head_capture_contact_mm3': _vol(r.clips().translate((0., 0., r.NECK[1] - r.NECK[0] - r.CLIP_T + .1)) ^ paddle),
        'board_to_clip_lift_contact_mm3': _vol(r.sensor().translate((0., 0., .1)) ^ r.clips()),
        'pusher_contact_at_angle_0_mm3': _vol(r.world(paddle, 0.) ^ parts['plunger']),
    }
    bonds = {
        'stop_boss_mm3': round(float((paddle ^ base.stop_stock()).volume()), 4),
        'pusher_to_floor_mm3': round(float((pusher() ^ (old.bracket() - old_pusher_space())).volume()), 4),
        'pusher_to_root_mm3': round(float((pusher() ^ pusher_root()).volume()), 4),
        'pusher_root_to_floor_mm3': round(float((pusher_root() ^ (old.bracket()-old_pusher_space()-switch_relief())).volume()), 4),
        'hinge_supports_mm3': round(float((key ^ r.supports()).volume()), 4),
        'edge_stops_mm3': [round(float((key ^ post).volume()), 4) for post in h.stop_posts().decompose()],
        'op1_seat_contacts_mm3': seats,
        'dfr_posts_mm3': [round(float((paddle ^ r.post().translate((s * r.POST_X, hy, 0.))).volume()), 4) for s in (-1, 1)],
    }
    web_interfaces = {name: round(float(shape.volume()), 4) for name, shape in guard_web_interfaces().items()}
    middle = settings[len(settings) // 2]
    caps = np.asarray([working[f'key_{i}_cap_travel'].bounding_box() for i in (0, 2, 3, 4)])
    seats_xy = [[round(float(v), 3) for v in q] for i, q in enumerate(r22.base.key_positions()) if i != 1]
    pin_gaps = {f'{t:.1f}': round(min(float(gravity_pins(t, dx, dy).min_gap(paddle, 3.))
                                       for _, dx, dy in pin_variants()), 4) for t in PIN_TAILS}
    relief_removed = bracket_before_pin_relief() - bracket()
    walls = key4_walls(key)
    electrode = r.electrode().bounding_box()
    layout = {
        'touch_board': 'DFRobot DFR0030 V2 on two posts with two printed clips',
        'op1_board_yaw_degrees': OP1_YAW, 'op1_plunger_xy_mm': list(PLUNGER_XY),
        'op1_plunger_xy_r32_mm': list(R32_ACTUATOR),
        'op1_board_bounds_mm': [round(v, 3) for v in parts['board'].bounding_box()],
        'op1_board_underside_z_mm': round(PCB_Z, 3),
        'choc_centres_mm': seats_xy, 'choc_seat_and_rod_clip_height_change_mm': 0.,
        'hinge_axis_world_y_mm': round(r.AXIS_Y + r.CLICK_SHIFT, 4),
        'switch_lever_arm_mm': round(LEVER, 4), 'switch_lever_arm_r40_mm': 16.15,
        'electrode_centre_lever_arm_mm': round(r.AXIS_Y - (electrode[1] + electrode[4]) / 2, 4),
        'electrode_world_y_span_released_mm': [round(v, 3) for v in r.world(r.electrode()).bounding_box()[1::3]],
        'rest_angle_deg': round(REST, 4), 'early_lift_angle_deg': round(EARLY_ANGLE, 4),
        'press_travel_rest_to_middle_stop_mm': press_travel(-REST, middle['angle_deg']),
        'press_travel_rest_to_backup_mm': press_travel(-REST, backup),
        'dfr_touch_face_top_released_mm': round(r.world(r.sensor() + r.electrode()).bounding_box()[5], 4),
        'dfr_released_front_y_mm': round(r.world(r.sensor()).bounding_box()[1], 4),
        'outer_cap_front_y_mm': h28.OUTER_CAP_BOTTOM,
        'choc_cap_top_mm': h28.CHOC_TOP,
        'slot_to_upper_right_choc_mm': walls,
        'slot_front_wall_mm': front_wall(key),
        'op1_sockets_to_rod_mm': round(parts['sockets'].bounding_box()[2] - base.ROD_R, 4),
        'op1_plug_to_rod_mm': _gap(parts['plug'], bar),
        'op1_housing_to_rod_mm': _gap(parts['housing'], bar),
        'op1_lead_to_rod_mm': _gap(parts['op1_wire'], bar),
        'op1_lead_to_carrier_mm': _gap(parts['op1_wire'], key),
        'op1_lead_to_upper_right_socket_mm': _gap(parts['op1_wire'], working['key_4_maximum_socket']),
        'op1_board_to_upper_right_choc_envelope_mm': _gap(parts['board'], union(working[f'key_4_{p}'] for p in ('switch', 'maximum_socket', 'cap_travel'))),
        'pusher_contact_xy_world_mm': list(PLUNGER_XY), 'pusher_bottom_z_mm': round(PUSH_Z, 4),
        'pusher_pad_mm': [2 * PAD_HALF[0], 2 * PAD_HALF[1]], 'pusher_pad_axes': 'Carrier X/Y',
        'pusher_face_inside_plunger_margin_mm': pusher_face_margin(sweep),
        'plunger_top_mm': [2.9, 1.2],
        'free_plunger_top_z_mm': round(FREE_TOP, 4), 'depression_at_modelled_angle_mm': DEPRESSION,
        'bracket_to_switch_body_at_backup_mm': switch_gap_at_backup,
        'pusher_pad_to_switch_body_at_backup_mm': pad_to_body_at_backup,
        'bracket_side_to_cap_travel_envelope_mm': round(float(caps[:, 0][caps[:, 0] > 0].min()) - paddle.bounding_box()[3], 4),
        'stop_screw_xy_bracket_mm': [base.STOP_X, base.STOP_Y],
        'stop_screw_to_electrode_vertical_mm': round(r.BOARD_Z[1] - (base.STOP_BOSS_BOTTOM + 4.), 3),
        'dfr_gravity_pins': {
            'from_board_end_mm': PIN_FROM_END, 'position_tolerance_xy_mm': [PIN_X_TOLERANCE, PIN_Y_TOLERANCE],
            'tails_checked_mm': list(PIN_TAILS), 'tail_length_measured': False,
            'min_gap_to_bracket_by_tail_mm': pin_gaps,
            'bracket_relief_removed_mm3': round(float(relief_removed.volume()), 4),
            'bracket_relief_bounds_mm': [round(v, 3) for v in relief_removed.bounding_box()],
            'arm_section_changed': False},
        'dfr_underside_to_arm_tops_mm': round(r.BOARD_Z[0] - r39.ARM_Z[1], 3),
        'carrier_bottom_plane_y_mm': round(key.bounding_box()[1], 4),
        'carrier_width_mm': round(key.bounding_box()[3] - key.bounding_box()[0], 4),
        'carrier_height_mm': round(key.bounding_box()[5] - key.bounding_box()[2], 4),
    }
    guard_report = base.reference_guard(key, parts)
    misplaced = base.reference_guard(key, parts, base.rod().translate((0., 140., 0.)))
    guard_report['misplaced_rod_is_rejected'] = not misplaced['passed']
    guard_report['passed'] = bool(guard_report['passed'] and not misplaced['passed'])
    apertures = key_apertures(key)
    cad = bool(
        max(clearance.values()) < .035 and max(full_stroke.values()) < .035
        and len(key.decompose()) == len(paddle.decompose()) == 1
        and bonds['stop_boss_mm3'] > 15. and bonds['pusher_to_floor_mm3'] > 1.
        and bonds['pusher_root_to_floor_mm3'] > 1.
        and bonds['pusher_to_root_mm3'] > 1.
        and min(bonds['edge_stops_mm3']) > 1. and min(seats) > .1 and min(bonds['dfr_posts_mm3']) > 5.
        and len(backup_stops) == 2 and min(backup_stops) > .0002
        and settings[0]['stop_height_above_switch_base_mm'] < 6.65
        and settings[-1]['stop_height_above_switch_base_mm'] > 7.15
        and min(steps) > 0. and max(steps) < .11
        and all(row['screw_contacts_landing_mm3'] > .00015
                and row['plastic_before_screw_contact_mm3'] < .00015 for row in settings)
        and hinge['released_tab_axial_engagement_mm'] >= .6
        and hinge['squeezed_tab_clear_of_support_mm'] > .2
        and hinge['straight_lift_retention_contact_mm3'] > .04 and lift['0.10'] < .035
        and min(capture.values()) > .04
        and not any(fingertip.values())
        and all(part['pieces'] == 1 and min(part['rod_mount_contact_mm3'], part['edge_contact_mm3']) > 1.
                for part in guard.values())
        and min(v for k, v in web_interfaces.items() if 'bond' in k) > 1.
        and min(walls.values()) >= .6
        and layout['slot_front_wall_mm'] >= 1.
        and layout['op1_sockets_to_rod_mm'] >= .45
        and layout['op1_plug_to_rod_mm'] >= .2
        and layout['bracket_to_switch_body_at_backup_mm'] > .2
        and layout['pusher_pad_to_switch_body_at_backup_mm'] > .08
        and layout['pusher_face_inside_plunger_margin_mm'] > .05
        and min(pin_gaps.values()) >= .2
        and relief_removed.bounding_box()[4] < r.ARM_ROOT_Y - .6
        and max(row['difference_mm3'] for row in apertures.values()) < .05
        and guard_report['passed']
        and abs(layout['carrier_bottom_plane_y_mm'] - h28.BOTTOM_EDGE) < .001
        and abs(layout['dfr_released_front_y_mm'] - h28.OUTER_CAP_BOTTOM) < .01
    )
    return {
        'layout': layout,
        'clearance_overlap_mm3': clearance,
        'full_stroke_overlap_mm3': full_stroke,
        'stop_settings': settings,
        'max_plunger_change_per_step_mm': round(float(max(steps)), 4),
        'screw_engagement_at_start_mm': round(4. - START_TURNS * PITCH, 3),
        'backup_angle_deg': round(backup, 5),
        'backup_nominal_plunger_travel_mm': round(base.actuator_travel(backup), 4),
        'backup_stop_contacts_mm3': backup_stops,
        'capture_contacts_mm3': capture,
        'bonds': bonds,
        'left_guard_web_interfaces_mm3': web_interfaces,
        'hinge': hinge,
        'ribs': guard,
        'key_apertures_vs_r39': apertures,
        'finger_contact_probes_reaching_terminals': fingertip,
        'rod_grip_interference_in_clip_rings_mm3': round(float((bar ^ key).volume()), 4),
        'reference_guard': guard_report,
        'basis': ('OP1 board, socket, plug and lead envelopes are photo-derived (Endgame Gear EGG-SP-U1); '
                  'the 7.35 mm free and 6.7-7.1 mm operating heights are the Omron reference switch. '
                  'DFR0030 length 35 mm (distributor sheet; maker says 30), hole pitch/position and '
                  '1.6 mm thickness are photo-derived or assumed. Its Gravity pin tails are checked at '
                  '1.5 and 2.0 mm, at +/-0.5 x +/-0.6 mm positions from the maker photo; tail length is '
                  'not measured. Stop and travel values are nominal CAD, not '
                  'measured force, feel or fatigue.'),
        'cad_checks_passed': cad,
        'passed': cad,
    }
