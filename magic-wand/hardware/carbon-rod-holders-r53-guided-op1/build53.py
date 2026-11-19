"""R53 guided OP1 click. Millimetres, assembly frame: +Y toward the two-key row, +Z up.

Five printed bodies, none trapped inside another:

Key_Carrier   R52 key zones unchanged. The centre returns to R51's fitted OP1 pocket.
              New: an open hinge yoke at the rear, two short lid rails beside the pocket.
Touch_Paddle  Flat top. A D-section axle bar, a three-sided sleeve round the switch body
              and one rounded crown at each of the two possible plunger stations.
Hinge_Cap     Dovetail bar pushed in from the rear over the axle journals.
OP1_Lid       Flat fork pushed in from the front. It holds the board down and its two
              towers stop the paddle lifting.
DFR_Post_Bar  Two R48 posts on a bar, fitted from below so the paddle top can print flat.

The switch body is the datum for the click. The board floats in its pocket and the
sleeve brings the switch under the crowns. Nothing here is a claim of physical fit.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
R52 = HERE.parent / "carbon-rod-holders-r52-snap-seat"
R51 = HERE.parent / "carbon-rod-holders-r51-guided-hinge"
EXPORT = HERE / "exports"

# ---- bought-part reference (R32 model, Omron D2FC drawing, kit photos) ----
YAW = -20.5                      # OP1 board yaw in plan, degrees
STATION = (0.4, -3.81949)        # modelled plunger station, world XY
PCB_Z, PCB_TOP = 9.4, 11.0       # 1.6 mm board thickness is assumed
BODY_X = 2.9                     # switch body half width (5.8 +/- 0.15)
BODY_Y = (-4.45, 8.35)           # body ends from the plunger station (12.8 +/- 0.15)
BODY_TOP = PCB_TOP + 6.5
FREE_TOP = PCB_TOP + 7.35        # free position is a maximum in the drawing
OPERATE = (PCB_TOP + 6.7, PCB_TOP + 7.1)
MIRROR_STATION = BODY_Y[0] + BODY_Y[1]   # plunger station if the switch is plugged in reversed
PCB_HALF, PCB_Y = 5.0, (-9.05, 20.95)    # photo estimate
POCKET_HALF = 5.45                       # R51 pocket half width at board level
SOCKET_Y, SOCKET_R, SOCKET_DEPTH = (-3.13, 1.95, 7.03), 1.3, 4.3   # photo estimate
HOUSING = (-3.6, 3.6, 14.95, 21.15, 6.6)   # connector body under the board: x0, x1, y0, y1, bottom
PLUG = (-3.1, 3.1, 17.0, 20.65, 3.5)       # fitted plug below it
FLOAT = 0.45                             # room for the board to follow the switch
SEAT_Z = 19.3                    # underside of the DFRobot board, flat paddle top
BOARD_TOP = 20.9
BOARD_FRONT, BOARD_REAR = -8.76949, 26.23051
HOLE_Y, HOLE_X = BOARD_FRONT + 24.1, 7.75

# ---- hinge ----
AXIS_Y, AXIS_Z = 29.3, 18.3
JOURNAL_R = 2.0
JOURNAL_X = (7.4, 9.6)           # each journal runs between these |X| stations
THRUST_X = 7.28                  # keel end faces; the yoke cheeks start at 7.40
FRONT_FLANK, REAR_FLANK = 40.0, 50.0
REAR_WALL_Y = AXIS_Y + JOURNAL_R + 0.12
CARRIER_REAR = 32.65
CHEEK_FRONT_TOP = 17.5
WALL_X = (10.45, 11.5)
CAP_Z = (19.5, 20.9)
DOVETAIL = (19.45, 20.15, 9.75)  # 45 degree lip: starts, ends, tip |X|
CAP_Y = (27.25, CARRIER_REAR)
CAP_GAP = 0.10
WALL_TOP = 19.47                 # rear wall under the cap
JOURNAL_TOP_GAP = CAP_Z[0] - SEAT_Z  # 0.20 mm above the flat at rest
RIDGE = (32.03, 0.40, 3.0)       # detent ridge centre Y, height, half length

# ---- paddle ----
PLATE_Z = 17.7
PLATE_X = 10.6
PLATE_FRONT = -8.65
SLEEVE_GAP, GUIDE_GAP, SLEEVE_WALL = 0.50, 0.35, 1.2
SLEEVE_RIM = 14.6
FLANGE = 0.8
CEILING = 18.5
MOAT = 18.9
CROWN_R = 2.4
RIB_X = (9.2, 10.4)
RIB_Z = 15.9
KEEL = (28.1, 30.5, 14.3)

# ---- OP1 lid ----
LID_Z = (11.15, 12.35)
LID_HALF = 7.2
LID_SLOT = 3.6
LID_FRONT = -9.0
LID_BAR = -5.3
TINE_END = (17.3, 8.6)           # left, right
RAIL_START = 1.6
RAIL_WALL = (7.35, 8.55)
RAIL_LIP = (5.6, 12.47, 13.25)
TOWER_Y = (-2.2, 0.9)
TOWER_X = (5.7, 7.2)
TOWER_TOP = 16.4
LIFT_GAP = 0.5                   # modelled lift before the towers stop the paddle
CLOSE_GAP = 0.2                  # optional second lid for a switch that rests low
DETENT = (11.2, 0.50)            # lid latch station along the board, bump height


def box(x0, x1, y0, y1, z0, z1):
    return mf.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def union(shapes):
    shapes = [s for s in shapes if not s.is_empty()]
    return mf.Manifold.batch_boolean(shapes, mf.OpType.Add) if shapes else mf.Manifold()


def mirrored(shape):
    return shape + shape.mirror((1.0, 0.0, 0.0))


def _section(points):
    section = mf.CrossSection([[tuple(map(float, p)) for p in points]])
    if section.area() <= 0:
        section = mf.CrossSection([[tuple(map(float, p)) for p in reversed(points)]])
    return section


def prism_xy(points, z0, z1):
    return mf.Manifold.extrude(_section(points), z1 - z0).translate((0, 0, z0))


def prism_yz(points, x0, x1):
    """Polygon in (Y, Z), extruded along X."""
    solid = mf.Manifold.extrude(_section(points), x1 - x0)
    return solid.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])


def prism_xz(points, y0, y1):
    """Polygon in (X, Z), extruded along Y."""
    solid = mf.Manifold.extrude(_section(points), y1 - y0)
    return solid.transform([[1, 0, 0, 0], [0, 0, -1, y1], [0, 1, 0, 0]])


def board_matrix():
    a = math.radians(YAW)
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0, STATION[0]], [s, c, 0, STATION[1]], [0, 0, 1, 0]]


def to_world(shape):
    """Board frame (origin at the plunger station, +y along the board) to assembly frame."""
    return shape.transform(board_matrix())


def board_point(x, y):
    m = np.asarray(board_matrix())
    return tuple(float(v) for v in m[:2, :2] @ (x, y) + m[:2, 3])


def board_axis():
    m = np.asarray(board_matrix())
    return np.array([m[0, 1], m[1, 1], 0.0])


def ubox(x0, x1, y0, y1, z0, z1):
    return to_world(box(x0, x1, y0, y1, z0, z1))


def uprism(points, z0, z1):
    return to_world(prism_xy(points, z0, z1))


def load(path):
    mesh = trimesh.load_mesh(path, process=False)
    raw = mf.Mesh(np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces, np.uint32))
    raw.merge()
    solid = mf.Manifold(raw)
    if solid.is_empty() or solid.status() != mf.Error.NoError:
        raise ValueError(f"Invalid body: {path}")
    return solid


def hinge_matrix(angle):
    """Paddle pose. Positive angle lowers the front edge."""
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    basis = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    pivot = np.array([0, AXIS_Y, AXIS_Z])
    return np.column_stack([basis, pivot - basis @ pivot]).tolist()


def posed(shape, angle):
    return shape.transform(hinge_matrix(angle))


# ------------------------------------------------------------------ carrier
ZONE = (-11.55, 14.55)


def carrier_base():
    """R52 everywhere near the four keys. R51's unrelieved pocket in the centre."""
    c52 = load(R52 / "exports/Key_Carrier-assembly.stl")
    c51 = load(R51 / "exports/Key_Carrier-assembly.stl")
    zone = box(ZONE[0], ZONE[1], -25, 34, -10, 30)
    base = (c52 - zone) + (c51 ^ zone)
    # Flat board floor: R52 already filled the screw pilots and removed the eyelet locators.
    for y in (-6.25, 11.65):
        plug = mf.Manifold.cylinder(PCB_Z - 7.31, 0.80, 0.80, 48).translate((0, y, 7.31))
        clear = mf.Manifold.cylinder(2.6, 2.5, 2.5, 64).translate((0, y, PCB_Z))
        offset = -0.85 if y < 0 else 0.0
        base = (base + to_world(plug.translate((0, offset, 0)))) - to_world(clear)
    base -= float_relief()
    # Old hinge cheeks, front stop pads and anything else standing on the deck.
    base -= mirrored(box(5.9, 8.6, 25.3, 33.0, 11.35, 30)) ^ box(-7.1, 7.1, 0, 40, 0, 40)
    base -= mirrored(box(7.1, 8.6, 25.3, 33.0, 11.12, 30))
    base -= mirrored(box(8.2, 10.9, -8.9, -6.9, 11.12, 30))
    return base


def float_relief():
    """Let the parts under the board move as far as the board slot already allows."""
    under = union(mf.Manifold.cylinder(SOCKET_DEPTH + 0.02, SOCKET_R, SOCKET_R, 48).translate((0, y, PCB_Z - SOCKET_DEPTH))
                  for y in SOCKET_Y)
    under += box(*HOUSING[:4], HOUSING[4], PCB_Z + 0.02) + box(*PLUG[:4], PLUG[4], HOUSING[4] + 0.02)
    steps = [(FLOAT * math.cos(a), FLOAT * math.sin(a), 0) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
    return to_world(union(under.translate(t) for t in steps))


def seat_profile():
    """(Y, Z) outline of one cheek: open top, sloped front lump, V seat, rear wall."""
    f, r = math.radians(FRONT_FLANK), math.radians(REAR_FLANK)
    tf = (AXIS_Y - JOURNAL_R * math.sin(f), AXIS_Z - JOURNAL_R * math.cos(f))
    tr = (AXIS_Y + JOURNAL_R * math.sin(r), AXIS_Z - JOURNAL_R * math.cos(r))
    front = lambda z: tf[0] - (z - tf[1]) / math.tan(f)
    rear = lambda z: tr[0] + (z - tr[1]) / math.tan(r)
    flat = AXIS_Z - JOURNAL_R - 0.4
    cheek_top = SEAT_Z - 0.02   # the cap lands pass over this on their way in
    return [(CARRIER_REAR, 10.6), (front(CHEEK_FRONT_TOP), 10.6), (front(CHEEK_FRONT_TOP), CHEEK_FRONT_TOP),
            (front(flat), flat), (rear(flat), flat), (REAR_WALL_Y, tr[1] + (REAR_WALL_Y - tr[0]) * math.tan(r)),
            (REAR_WALL_Y, cheek_top), (CARRIER_REAR, cheek_top)]


def yoke():
    profile = seat_profile()
    front = profile[1][0]
    cheek = prism_yz(profile, JOURNAL_X[0], WALL_X[0] + 0.01)
    lip0, lip1, tip = DOVETAIL
    wall = prism_xz([(WALL_X[0], 10.6), (WALL_X[1], 10.6), (WALL_X[1], CAP_Z[1]), (tip, CAP_Z[1]),
                     (tip, lip1), (WALL_X[0], lip0)], front, CARRIER_REAR)
    # Round the outer top edge and blunt the front top corner next to the touch board.
    wall -= prism_xz([(WALL_X[1] + 0.01, CAP_Z[1] - 0.6), (WALL_X[1] + 0.01, CAP_Z[1] + 0.01),
                      (WALL_X[1] - 0.6, CAP_Z[1] + 0.01)], front - 1, CARRIER_REAR + 1)
    wall -= prism_yz([(front - 0.01, CAP_Z[1] - 1.1), (front - 0.01, CAP_Z[1] + 0.01),
                      (front + 1.1, CAP_Z[1] + 0.01)], WALL_X[0] - 1.2, WALL_X[1] + 0.1)
    back = box(-JOURNAL_X[0] - 0.01, JOURNAL_X[0] + 0.01, REAR_WALL_Y, CARRIER_REAR, 11.0, WALL_TOP)
    # Pointed lightening arch. It lies on the bed in the rear-down print.
    back -= prism_xz([(-5.2, 12.6), (5.2, 12.6), (5.2, 15.4), (0, 17.9), (-5.2, 15.4)], REAR_WALL_Y - 1, CARRIER_REAR + 1)
    y, height, half = RIDGE
    ridge = prism_yz([(y - height, WALL_TOP - 0.01), (y + height, WALL_TOP - 0.01),
                      (y, WALL_TOP + height)], -half, half)
    # Two fingernail reliefs under the rear edge of the cap.
    top = WALL_TOP
    nail = mirrored(prism_yz([(CARRIER_REAR + 0.01, top - 0.9), (CARRIER_REAR + 0.01, top + 0.01), (CARRIER_REAR - 0.75, top + 0.01)],
                             half + 0.8, half + 3.8))
    return mirrored(cheek + wall) + (back - nail) + ridge


def lid_cut():
    """Space swept by the lid on its way in from the front, with running clearance."""
    plate = ubox(-RAIL_WALL[0], RAIL_WALL[0], -45, TINE_END[0] + 0.12, LID_Z[0], RAIL_LIP[1])
    towers = [ubox(s * (TOWER_X[0] - 1.0) if s > 0 else -RAIL_WALL[0],
                   RAIL_WALL[0] if s > 0 else -(TOWER_X[0] - 1.0), -45, TOWER_Y[1] + 0.3,
                   LID_Z[0], TOWER_TOP + 0.2) for s in (-1, 1)]
    return plate + union(towers)


def rails():
    """Two fixed guides. Their lips stay outside the board's drop-in opening."""
    lip_x, lip_z0, lip_z1 = RAIL_LIP
    parts = []
    for sign, end in zip((-1, 1), TINE_END):
        stop = end + 0.12
        outline = [(RAIL_WALL[0], 10.6), (RAIL_WALL[1], 10.6), (RAIL_WALL[1], lip_z1 - 0.5),
                   (RAIL_WALL[1] - 0.5, lip_z1), (lip_x, lip_z1), (lip_x, lip_z0), (RAIL_WALL[0], lip_z0)]
        if sign < 0:
            outline = [(-x, z) for x, z in outline]
        rail = to_world(prism_xz(outline, RAIL_START, stop + 1.2))
        end_stop = ubox(*sorted((sign * lip_x, sign * RAIL_WALL[1])), stop, stop + 1.2, 10.6, lip_z1)
        # In the rear-down print each rail starts on a 45 degree ramp from the deck.
        rise = lip_z1 - 11.0
        ramp = to_world(prism_yz([(stop + 1.19, 11.0), (stop + 1.21 + rise, 11.0), (stop + 1.19, lip_z1)],
                                 *sorted((sign * lip_x, sign * RAIL_WALL[1]))))
        lead = to_world(prism_xy([(sign * (RAIL_WALL[0] - 0.01), RAIL_START - 0.01), (sign * (RAIL_WALL[0] + 0.7), RAIL_START - 0.01),
                                  (sign * (RAIL_WALL[0] - 0.01), RAIL_START + 0.7)], LID_Z[0], lip_z0))
        parts.append((rail - lead) + end_stop + ramp)
    return union(parts)


def detent_notch():
    y, height = DETENT
    x = RAIL_WALL[0]
    return to_world(prism_xy([(-x + 0.01, y - height - 0.2), (-x - height - 0.1, y),
                              (-x + 0.01, y + height + 0.2)], LID_Z[0], RAIL_LIP[1]))


def carrier():
    body = carrier_base() + yoke()
    body = (body - lid_cut()) + rails()
    return body - detent_notch()


# ------------------------------------------------------------------- paddle
def crown_apex(station):
    """Both crowns reach the case top at the same paddle angle, so a reversed switch gets the same travel."""
    lever = AXIS_Y - STATION[1]
    full = math.asin((FREE_TOP - BODY_TOP) / lever)
    here = AXIS_Y - board_point(0, station)[1]
    return BODY_TOP + here * math.sin(full)


def crown(station):
    """Rounded 4.8 mm contact. Its lowest point rests on the free plunger."""
    apex = crown_apex(station)
    contact = 1.50
    # A shallow 3 mm crown keeps a full contact face on the final toolpath.
    # Its skirt turns smoothly back to the 4.8 mm shoulder.
    drop = 0.025
    profile = [(0.0, apex)]
    for angle in np.linspace(0, math.pi / 2, 21)[1:]:
        profile.append((contact * math.sin(angle), apex + drop * (1.0 - math.cos(angle))))
    for angle in np.linspace(0, math.pi / 2, 33)[1:]:
        profile.append((contact + (CROWN_R - contact) * math.sin(angle),
                        apex + drop + (MOAT - apex - drop) * (1.0 - math.cos(angle))))
    profile.extend([(CROWN_R, SEAT_Z), (0.0, SEAT_Z)])
    return mf.CrossSection([profile]).revolve(96).translate((0, station, 0))


def sleeve_parts():
    """Board-frame sleeve solid and the cavity cut out of the plate."""
    inner = BODY_X + SLEEVE_GAP
    outer = inner + SLEEVE_WALL
    rear_in = BODY_Y[1] + SLEEVE_GAP
    rear_out = rear_in + SLEEVE_WALL
    front = BODY_Y[0] - 6.0
    ring = box(-outer, outer, front, rear_out, SLEEVE_RIM, PLATE_Z + 0.01)
    # Outward 45 degree flange on the two long walls. The lid towers stop it.
    flare = prism_xz([(outer - 0.01, SLEEVE_RIM), (outer + FLANGE, SLEEVE_RIM), (outer - 0.01, SLEEVE_RIM + FLANGE + 0.01)],
                     front, TOWER_Y[1] + 0.6)
    ring += mirrored(flare)
    cavity = box(-inner, inner, front - 1, rear_in, SLEEVE_RIM - 1, CEILING)
    # Entry bevel at the rim.
    bevel = prism_xz([(inner - 0.01, SLEEVE_RIM - 0.01), (inner + 0.55, SLEEVE_RIM - 0.01), (inner - 0.01, SLEEVE_RIM + 0.55)],
                     front - 1, rear_in)
    cavity += mirrored(bevel)
    cavity += prism_yz([(rear_in - 0.01, SLEEVE_RIM - 0.01), (rear_in + 0.55, SLEEVE_RIM - 0.01),
                        (rear_in - 0.01, SLEEVE_RIM + 0.55)], -inner, inner)
    moat = union(mf.Manifold.cylinder(MOAT - CEILING + 0.3, CROWN_R + 0.9, CROWN_R + 0.9, 72)
                 .translate((0, s, CEILING - 0.3)) for s in (0.0, MIRROR_STATION))
    cavity += moat ^ box(-inner, inner, front, rear_in, 0, MOAT)
    # Rounded guide lands leave 0.35 mm to the nominal body. They fade out above the rim bevel.
    reach = SLEEVE_GAP - GUIDE_GAP
    start, full = SLEEVE_RIM + 0.7, SLEEVE_RIM + 1.7
    rod = (mf.Manifold.cylinder(full - start, 0.05, 0.9, 48).translate((0, 0, start))
           + mf.Manifold.cylinder(CEILING - full + 0.01, 0.9, 0.9, 48).translate((0, 0, full - 0.01)))
    lands = []
    for y in (BODY_Y[0] + 2.0, BODY_Y[1] - 2.0):
        for sign in (-1, 1):
            lands.append(rod.scale((reach / 0.9, 1, 1)).translate((sign * inner, y, 0)) ^ box(-inner, inner, -50, 50, 0, 50))
    lands.append(rod.scale((1, reach / 0.9, 1)).translate((0, rear_in, 0)) ^ box(-inner, inner, -50, rear_in, 0, 50))
    return ring, cavity, union(lands)


def plate_outline():
    """Plan outline: full width under the board, narrowed where it passes between the yoke walls."""
    x, n, r = PLATE_X, JOURNAL_X[1], 1.5
    step = AXIS_Y - JOURNAL_R - 0.4
    pts = [(-x + r, PLATE_FRONT), (x - r, PLATE_FRONT), (x, PLATE_FRONT + r), (x, step - 0.6), (n, step),
           (n, AXIS_Y), (-n, AXIS_Y), (-n, step), (-x, step - 0.6), (-x, PLATE_FRONT + r)]
    return pts


def axle():
    """D-section bar. The flat is the bed face; the round runs in the yoke."""
    n = JOURNAL_X[1]
    round_bar = mf.Manifold.cylinder(2 * n, JOURNAL_R, JOURNAL_R, 96).rotate((0, 90, 0)).translate((-n, AXIS_Y, AXIS_Z))
    bar = round_bar ^ box(-n, n, AXIS_Y - 3, AXIS_Y + 3, 0, SEAT_Z)
    y0, y1, z = KEEL
    keel = prism_yz([(y0, AXIS_Z), (y1, AXIS_Z), (y1 - 0.5, z), (y0 + 0.5, z)], -THRUST_X, THRUST_X)
    return bar + keel


def paddle():
    plate = prism_xy(plate_outline(), PLATE_Z, SEAT_Z)
    footprint = prism_xy(plate_outline(), 0, 40)
    ring, cavity, lands = sleeve_parts()
    ring, cavity, lands = to_world(ring), to_world(cavity), to_world(lands)
    ribs = mirrored(box(RIB_X[0], RIB_X[1], PLATE_FRONT + 3.0, AXIS_Y - JOURNAL_R - 1.2, RIB_Z, PLATE_Z + 0.01))
    ribs -= mirrored(prism_yz([(PLATE_FRONT + 2.9, RIB_Z - 0.01), (PLATE_FRONT + 2.9, PLATE_Z), (PLATE_FRONT + 4.7, RIB_Z - 0.01)],
                              RIB_X[0] - 0.1, RIB_X[1] + 0.1))
    body = plate + axle() + ((ring + ribs) ^ footprint)
    body -= cavity
    body += lands ^ footprint
    body += to_world(union(crown(s) for s in (0.0, MIRROR_STATION)))
    # Board post holes, Gravity pin tails and a plain lightening window.
    holes = mirrored(box(HOLE_X - 1.33, HOLE_X + 1.33, HOLE_Y - 1.47, HOLE_Y + 1.47, 0, 40))
    window = prism_xy(rounded(-5.6, 5.6, 12.0, 24.4, 1.6), 0, 40)
    body -= holes + window
    return body


def rounded(x0, x1, y0, y1, r, n=10):
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for a in np.linspace(a0, a0 + 90, n):
            pts.append((cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))))
    return pts


# ---------------------------------------------------------------- hinge cap
def hinge_cap():
    lip0, lip1, tip = DOVETAIL
    slope = (WALL_X[0] - tip) / (lip1 - lip0)
    half = lambda z: WALL_X[0] - slope * (min(z, lip1) - lip0) - CAP_GAP
    # The acute lower corners are cut back to a 0.25 mm flat so they do not chip.
    edge = CAP_Z[0] + 0.25
    outline = [(-half(edge), CAP_Z[0]), (half(edge), CAP_Z[0]), (half(edge), edge), (half(lip1), lip1), (half(lip1), CAP_Z[1]),
               (-half(lip1), CAP_Z[1]), (-half(lip1), lip1), (-half(edge), edge)]
    bar = prism_xz(outline, *CAP_Y)
    # Lead-in under the front edge so it rides over the detent ridge.
    bar -= prism_yz([(CAP_Y[0] - 0.01, CAP_Z[0] - 0.01), (CAP_Y[0] + 0.9, CAP_Z[0] - 0.01), (CAP_Y[0] - 0.01, CAP_Z[0] + 0.45)], -12, 12)
    y, height, length = RIDGE
    peak = WALL_TOP + height
    groove = prism_yz([(y - height - 0.15, CAP_Z[0] - 0.01), (y + height + 0.15, CAP_Z[0] - 0.01),
                       (y, peak + 0.12)], -length - 0.5, length + 0.5)
    # The flat underside captures both journals with one print layer of running clearance.
    return bar - groove


# ------------------------------------------------------------------ OP1 lid
def op1_lid(lift_gap=LIFT_GAP, grips=1):
    z0, z1 = LID_Z
    h, s_, f, bar, c = LID_HALF, LID_SLOT, LID_FRONT, LID_BAR, 0.9
    left, right = TINE_END
    plate = prism_xy([(-h + 1.4, f), (h - 1.4, f), (h, f + 1.4), (h, right - c), (h - c, right), (s_ + c, right),
                      (s_, right - c), (s_, bar), (-s_, bar), (-s_, left - c), (-s_ - c, left), (-h + c, left),
                      (-h, left - c), (-h, f + 1.4)], z0, z1)
    # Spring strip with the latch bump, along the left edge inside its rail.
    y, height = DETENT
    slit = box(-LID_HALF + 0.95, -LID_HALF + 1.55, y - 7.2, y + 1.4, z0 - 1, z1 + 1)
    relief = box(-LID_HALF - 1, -LID_HALF + 0.95, y + 0.9, y + 1.4, z0 - 1, z1 + 1)
    # Lead-in under both tine tips so they ride over a board that sits slightly proud.
    for end, side in zip(TINE_END, ((-LID_HALF - 1, 0), (0, LID_HALF + 1))):
        plate -= prism_yz([(end - 0.42, z0 - 0.01), (end + 0.01, z0 - 0.01), (end + 0.01, z0 + 0.42)], *side)
    plate -= slit + relief
    bump = prism_xy([(-LID_HALF + 0.01, y - height - 0.2), (-LID_HALF - height, y), (-LID_HALF + 0.01, y + height + 0.2)], z0, z1)
    # Two towers. Their 45 degree lips sit LIFT_GAP above the sleeve flange.
    outer = BODY_X + SLEEVE_GAP + SLEEVE_WALL
    face = lambda x: SLEEVE_RIM + FLANGE - (x - outer) + lift_gap
    lip_tip = outer + 0.3
    tower = prism_xz([(TOWER_X[0], z1 - 0.01), (TOWER_X[1], z1 - 0.01), (TOWER_X[1], TOWER_TOP), (lip_tip, TOWER_TOP),
                      (lip_tip, face(lip_tip)), (TOWER_X[0], face(TOWER_X[0]))], *TOWER_Y)
    # Lead-in on the edge that meets the flange first.
    tower -= prism_xy([(lip_tip - 0.01, TOWER_Y[1] - 0.8), (lip_tip - 0.01, TOWER_Y[1] + 0.01), (lip_tip + 0.8, TOWER_Y[1] + 0.01)], 0, 40)
    # One raised rib marks the standard lid. The optional closer lid has two.
    grip = union(box(-LID_HALF + 1.6, LID_HALF - 1.6, LID_FRONT + 0.5 + 1.5 * i, LID_FRONT + 1.3 + 1.5 * i, z1 - 0.01, z1 + 0.6)
                 for i in range(grips))
    return to_world(plate + bump + mirrored(tower) + grip)


# ------------------------------------------------------------- DFR post bar
def post_bar(post):
    """`post` is the R31 post solid at the origin (shaft from 19.25 to its head)."""
    lower = post ^ box(-5, 5, -5, 5, 0, SEAT_Z + 0.4)
    down = union(lower.translate((0, 0, -dz)) for dz in np.arange(0.0, SEAT_Z - PLATE_Z + 0.31, 0.3))
    one = post + down
    posts = union(one.translate((s * HOLE_X, HOLE_Y, 0)) for s in (-1, 1))
    bounds = one.bounding_box()
    base = box(-HOLE_X - 1.3, HOLE_X + 1.3, HOLE_Y + bounds[1], HOLE_Y + bounds[4], PLATE_Z - 1.8, PLATE_Z)
    return posts + base


def reference_post():
    """The R31/R48 post, loaded only when the inherited CAD chain is available."""
    sys.path.insert(0, str(R52))
    sys.path.insert(0, str(R51))
    import build52 as d
    return d.r.post()


def parts():
    return {"Key_Carrier": carrier(), "Touch_Paddle": paddle(), "Hinge_Cap": hinge_cap(),
            "OP1_Lid": op1_lid(), "OP1_Lid_Close": op1_lid(CLOSE_GAP, 2), "DFR_Post_Bar": post_bar(reference_post())}


def save(path, shape):
    mesh = shape.to_mesh()
    trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False).export(path)


def save_closed(path, final):
    save(path, final)
    mesh = trimesh.load_mesh(path)
    if not mesh.is_volume:
        indexed = final.to_mesh()
        vertices = np.array(indexed.vert_properties[:, :3], dtype=np.float64)
        _, groups, counts = np.unique(vertices, axis=0, return_inverse=True, return_counts=True)
        same = counts[groups] > 1
        vertices[same] += np.random.default_rng(53).uniform(-0.00018, 0.00018, (same.sum(), 3))
        trimesh.Trimesh(vertices, indexed.tri_verts, process=False).export(path)
        mesh = trimesh.load_mesh(path)
    if not mesh.is_volume:
        raise ValueError(f"{path.stem} did not export as a closed solid")
    return mesh


def main(output=None):
    output = Path(output) if output else EXPORT
    output.mkdir(parents=True, exist_ok=True)
    records = {}
    for name, shape in parts().items():
        pieces = sorted(shape.decompose(), key=lambda s: -s.volume())
        loose = [round(p.volume(), 5) for p in pieces[1:]]
        print(name, [round(float(v), 3) for v in shape.bounding_box()], "pieces", len(pieces), loose[:6], flush=True)
        # The inherited carrier meshes share a few zero-thickness skins. R52 dropped the same remnants.
        limit = (0.11, 0.6) if name == "Key_Carrier" else (0.001, 0.001)
        if any(v > limit[0] for v in loose) or sum(loose) > limit[1]:
            raise ValueError(f"{name} has detached material: {loose[:8]}")
        final = pieces[0]
        path = output / f"{name}-assembly.stl"
        mesh = save_closed(path,final)
        if name == "Key_Carrier":
            from carrier53 import brace_finger_rest, finish
            save_closed(path, finish(path))
            final = brace_finger_rest(load(path))
            mesh = save_closed(path, final)
        records[name] = dict(sha256=sha256(path.read_bytes()).hexdigest(), volume_mm3=round(float(mesh.volume), 3),
                             bounds_mm=[round(float(v), 3) for v in final.bounding_box()],
                             discarded_skin_mm3=round(sum(loose), 6))
    (output / "dimensions.json").write_text(json.dumps(dict(
        meshes=records, hinge_axis_world_yz_mm=[AXIS_Y, AXIS_Z], journal_diameter_mm=2 * JOURNAL_R,
        journal_span_mm=[-JOURNAL_X[1], JOURNAL_X[1]], op1_yaw_deg=YAW, plunger_station_world_xy_mm=list(STATION),
        mirrored_station_world_xy_mm=list(board_point(0, MIRROR_STATION)), crown_diameter_mm=2 * CROWN_R,
        sleeve_side_gap_mm=GUIDE_GAP, lid_lift_gap_mm=LIFT_GAP, optional_close_lid_lift_gap_mm=CLOSE_GAP, switch_reference=dict(
            body_mm=[12.8, 5.8, 6.5], free_position_max_mm=7.35, operating_position_mm=[6.7, 7.1],
            plunger_from_body_end_mm=4.45)), indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
