"""R63 key holder and paddle: saddle hinge, open rod bore, battery against the deck, lower-left key turned.

The holder is generated with the R60 to R62 functions (R60 deck, R61 tail, R62 compact tongue and
right-hand guard, R62 upper-right latch pass). Four local changes are made on the way.

1. Hinge. The R57 arrangement closes on the pin by design: the pin lies on the cheek floors and the
   paddle hangs on the pin, so the opening both parts share at rest is the pin diameter. R63 carries
   the paddle on a V saddle under its barrel instead. The paddle pose is unchanged. Both bores are
   then opened round one common line, so the pin is a keeper with air all round in the resting pose.
   The barrel keeps short fore-aft lands at its two ends. Same 3.0 and 3.2 pins and the same clip.
2. Rod. One straight bore, wider than the rod over the whole length, with a funnel at each end.
   The two grip rings no longer squeeze the rod.
3. Battery. The pouch lies with its broad face 0.05 mm under the keypad deck. The old lower cradle
   is not built. Two lips, an inboard wall and an outboard spring leaf hold it.
4. Lower-left key (key_0). Its mount is turned +90 degrees about its own centre. The socket still
   slides in from the outer edge in world coordinates. The left guard's outer bottom rail crossed
   that path at socket height, so on the left it moves inboard and a low arm covers the outer front.

Nothing here is a claim of physical fit. The parent runs the native slice and the bead checks.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r62-compact-guard'))
import design62 as r62  # noqa: E402

r61 = r62.r61
prior = r61.prior                 # design60
c, k, b, m = prior.c, prior.k, r61.b, r61.m
OUT = HERE / 'exports'
HOLDER, PADDLE, PACK_FILE, BACKER = ('Key_Carrier-assembly.stl', 'Touch_Paddle-assembly.stl',
                                     'Battery_Pack-assembly.stl', 'Socket_Backer_Left-assembly.stl')
REAR, BED, AXIS = r61.REAR, r61.BED, r61.AXIS
DECK = 7.27                       # underside of the keypad backplate; checked against the R16 parameters

# ---- 4. lower-left key
KEY0 = (-21.0, 0.0)
TURN_DEG = 90.0
LEFT_RAIL_X = 19.0                # left guard, second bottom rail (R62: 28.3); written for the right, then mirrored
LEFT_ARM = [(27.3, 0.0, 0.62), (27.3, -5.2, 0.62)]   # low arm from the crown end, under the socket path

# ---- 3. battery (Micron 72217)
PACK = (11.8, 27.0, 3.9)          # across, along the rod, thick
PACK_X = (-21.25, -9.45)          # the wire lane starts at X -8.5
PACK_Y0 = 21.9                    # behind the upper-left switch posts and the left guard's top root
PACK_Z = (DECK - 0.05 - PACK[2], DECK - 0.05)
OLD_PACK_MIN = (-17.75, 20.6, -4.60)                  # R61/R62 pouch, lowest corner
PACK_MOVE = tuple(round(new - old, 3) for new, old in zip((PACK_X[0], PACK_Y0, PACK_Z[0]), OLD_PACK_MIN))
OLD_GAP_TO_DECK = 7.97            # parent's ray cast on the R62 deck
WALL, CLEAR, LIP_T, LIP_W = 0.83, 0.07, 0.80, 2.4
LIP_TOP = PACK_Z[0] - 0.15
LOW = LIP_TOP - LIP_T             # lowest point of the new seat
SHOE = 0.21                       # the leaf's shoe stands this far into the nominal pouch
LEAF_X = (PACK_X[0] - 0.75 - 1.04, PACK_X[0] - 0.75)
LEAF_GAP = 0.68
WALL_FACE = LEAF_X[0] - LEAF_GAP  # inner face of the outboard wall
LAND = (33.0, -11.9, 1.2)         # roof land beside the tongue: start Y, inboard X, thickness

# ---- 2. rod
ROD_R = 4.275                     # 8.55 mm bore for the 8.0 mm rod
FUNNEL = (0.5, 1.0)               # front mouth: wider by, over this length
# Rear mouth: a tapered socket at the bed face. With nothing in it, it is the rear funnel. A separate
# open wedge ring (Rod_Collet) snaps onto the rod behind the holder and is pushed into it to hold the rod.
SOCKET = (5.0, 6.0)               # radius at the bed face, depth back to the bore
COLLET_FILE = 'Rod_Collet-assembly.stl'
COLLET_BORE_R = 4.03              # on the 8.0 mm rod
COLLET_WEDGE = 3.6                # wedge length inside the socket when its flange stands COLLET_GAP proud
COLLET_GAP = 1.5                  # push-in travel left for print error and wear
COLLET_FLANGE = (5.9, 1.4)        # radius, thickness: the grip for pushing in and pulling out
COLLET_OPEN_DEG = 55.0            # half angle of the opening, toward -X, the wire lane side
# Roofs of the two turned switch-tab notches in the plate, from the native slice: X spans and the layer they start in.
NOTCH_ROOFS = ((-22.185, -19.785), (-17.585, -16.185))    # kept as the record of the native finding
# Middle of the front switch rim: X span, where the cut opens (before the first island), where the rim
# starts to grow back (after the clip relief ends at Y -7.80), and the backed level it grows from.
FRONT_RIM = ((-25.4, -15.05), -6.7, -7.86, 8.72)
ROOT_GUSSET = ((-20.5, -17.5), (-6.7, -9.3), 1.6)     # under the front strip at the second left rail: X, Y run, depth at the front

# ---- 1. hinge
KEEPER_Z = m.BARREL_HOLE_Z        # common pin line: the barrel bore centre, with the paddle at rest
BORE_Z = 1.90                     # cheek void half height
BORE_FLOOR = 1.87                 # rear floor from the axis; flat, so the layer under it is whole
BORE_SHOULDER = 0.80              # where the 45 degree roof starts, toward the print top
FLAT_HALF = 0.425
RELIEF = 0.6
BORE_ROOF = BORE_SHOULDER + BORE_Z - FLAT_HALF
SADDLE_X = (3.4, 7.3)
SADDLE_DEG = 30.0
SADDLE_GAP = 0.03
SADDLE_BASE = 10.9
LAND_HALF = m.PIN_R + 0.28        # barrel end lands; R58 slot 0.20
LAND_X = (5.2, 6.4)
RELIEF_X = (1.55, LAND_X[0])
CLIP_CLEARANCE = (12.3, 15.2, 22, 25.15, 8.35, 13.2)   # R62 upper-right latch pass
TO_YZ = [[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]]


def vol(a, other):
    return float((a ^ other).volume())


def one_piece(body, name, limit=0.05):
    pieces = sorted(body.decompose(), key=lambda s: -s.volume())
    loose = sum(abs(p.volume()) for p in pieces[1:])
    assert loose < limit, (name, 'detached material', round(loose, 4))
    return pieces[0]


# ----------------------------------------------------------------- 4. key_0
def turn(solid):
    """+90 degrees about the lower-left key centre. The same transform the audit uses."""
    return solid.translate((-KEY0[0], -KEY0[1], 0)).rotate((0, 0, TURN_DEG)).translate((KEY0[0], KEY0[1], 0))


def placed(space, name):
    """One inherited key space at its R63 position. Only key_0 spaces turn."""
    here = c.placed(space, name, k.h.d.KEY_RAISE_MM, prior.old.NEARER)
    if not name.startswith('key_0_'):
        return here
    if not hasattr(here, 'offsets'):
        return turn(here)
    seat = np.asarray(here.offsets[-1], float)
    solid = turn(here.solid.translate(tuple(float(v) for v in seat)))
    moves = here.offsets - seat
    if not name.endswith('_soldered_socket_slide'):
        # Every other route turns with the key. The slide keeps its world direction from the outer edge.
        moves = np.column_stack([-moves[:, 1], moves[:, 0], moves[:, 2]])
    return type(here)(solid, moves)


def turned_seat(deck, base):
    """Refill the old lower-left pin, post and window holes and cut the turned set. Heights are the R16 ones."""
    bay, z0, bottom = base.P['bay'], base.PCB_Z, base.slab_bottom()
    here = lambda s: s.translate((KEY0[0], KEY0[1], 0))
    holes = base.backplate_hole_centres(0)
    fill = [base.teardrop(x, y, r + 0.3, bottom + (0.0 if y > 0.4 else 0.4), z0) for x, y, r in holes if (x, y) != (0.0, 0.0)]
    window = np.asarray(base.window_outline(0), float)
    middle = window.mean(axis=0)
    fill.append(base.prism_xy([tuple(middle + 1.08 * (p - middle)) for p in window], bottom, z0))
    # Full backplate thickness under the turned socket, as under every other socket.
    pad = turn(here(base.box(-4.8, 9.9, 0.4, 9.2, bottom, bottom + 0.42)))
    relief = base.rr(2 * bay['clip_relief_half_x_mm'], 2 * bay['clip_relief_half_y_mm'], 0.5, z0, z0 + bay['plate_bottom_mm'] + 0.01)
    # The old relief was wider across X. Rebuild the plate support there; the turned relief is wider along Y instead.
    half_x, half_y = bay['clip_relief_half_x_mm'], bay['clip_relief_half_y_mm']
    fill += [base.box(*sorted((s * (half_y - 0.05), s * (half_x + 0.05))), -half_y - 0.05, half_y + 0.05, z0, z0 + bay['plate_bottom_mm'] + 0.01)
             for s in (1, -1)]
    cuts = [relief.rotate((0, 0, TURN_DEG))]
    # Hole centres turn with the key; every teardrop peak still points to -Y, the print top.
    cuts += [base.teardrop(-y, x, r, bottom - 1, z0 + 1) for x, y, r in holes]
    out = deck + here(base.union(fill)) + pad - here(base.union(cuts))
    # Print layers grow toward -Y. Between the turned switch tabs the front plate used to start as loose
    # islands (Y -7.1 on) over the open clip relief. Across the middle of the front rim everything above
    # the backplate is removed from before the first island, and the rim then grows back off the backed
    # backplate at 45 degrees once the relief has ended. The plate shoulders at both X sides stay.
    (rx0, rx1), y_open, y_grow, floor = FRONT_RIM
    out -= b.prism_yz([(y_open, floor), (y_grow, floor), (y_grow - 3.0, floor + 3.0), (y_grow - 3.0, floor + 6.0), (y_open, floor + 6.0)], rx0, rx1)
    # A gusset under the front strip carries the relocated left rail root. It thickens at 32 degrees as the print rises.
    (gx0, gx1), (gy0, gy1), depth = ROOT_GUSSET
    return out + b.prism_yz([(gy0, bottom + 0.03), (gy1, bottom + 0.03), (gy1, bottom - depth)], gx0, gx1)


def left_guard():
    g = r62
    shapes = [r61.curve(g.TOP_PATH, 1.32)]
    shapes += [r61.curve([g.CROWN_START, (x, 9.5, .88), (x, 6.6, .88), g.CROWN_END], 1.26) for x in (15.1, 22.1, 28.1)]
    shapes += [r61.curve(g.bottom_path(x), 1.35) for x in (14.2, LEFT_RAIL_X)]
    shapes.append(r61.run([g.CROWN_END, *LEFT_ARM], 1.26))
    return b.union(shapes).mirror((1, 0, 0))


def left_guard_cores():
    g = r62
    paths = {'top': r61.curve(g.TOP_PATH, 1.05), 'inner_bottom': r61.curve(g.bottom_path(14.2), 1.05),
             'second_bottom': r61.curve(g.bottom_path(LEFT_RAIL_X), 1.05), 'outer_arm': r61.run([g.CROWN_END, *LEFT_ARM], 0.95)}
    return {name: core.mirror((1, 0, 0)) for name, core in paths.items()}


def left_backer(socket):
    """The R58 tongue recipe on the turned socket: slides in from the left, under the seated socket."""
    x0, y0, z0, x1, y1, _ = (float(v) for v in socket.bounding_box())
    return b.box(x0 - 12.0, x1 - 0.5, y0 + 0.35, y1 - 0.35, z0 - 1.7, z0 - 0.1)


# --------------------------------------------------------------- 3. battery
def pack():
    return b.box(PACK_X[0], PACK_X[1], PACK_Y0, PACK_Y0 + PACK[1], PACK_Z[0], PACK_Z[1])


def spring():
    """Free-ended side leaf, rooted at the print bed. Only its rounded shoe touches the pouch edge."""
    zb = PACK_Z[0]
    leaf = r61.soft(LEAF_X[0], LEAF_X[1], PACK_Y0 + 2.0, BED, zb + 0.42, zb + PACK[2] - 0.45, 0.35)
    shoe = r61.soft(LEAF_X[1] - 0.2, PACK_X[0] + SHOE, PACK_Y0 + 4.7, PACK_Y0 + 10.2, zb + 0.45, zb + PACK[2] - 0.65, 0.46)
    return leaf + shoe


def cradle():
    """Every member runs fore-aft from the bed, so each prints as a wall. Nothing roofs the pouch space."""
    xo, xi = PACK_X
    zb, zt = PACK_Z
    wall_x = xi + CLEAR
    front_in, front_out = PACK_Y0 - 1.45, PACK_Y0 - 0.85      # each stop wedge meets its pouch corner just past PACK_Y0
    start, inboard, thick = LAND
    parts = [
        b.box(wall_x, wall_x + WALL, front_in, BED, LOW, DECK + 0.3),                        # rigid inboard wall
        b.box(xi - LIP_W, wall_x + WALL, front_in, BED, LOW, LIP_TOP),                        # inboard lip
        r61.soft(WALL_FACE - WALL, WALL_FACE, front_out, BED, LOW, DECK + 0.3, 0.3),          # outboard wall
        b.box(WALL_FACE - 0.01, xo + LIP_W, front_out, BED, LOW, LIP_TOP),                    # outboard lip, under the leaf
        b.box(WALL_FACE - 0.01, xo - 0.38, BED - 5.5, BED, LIP_TOP - 0.01, DECK + 0.3),       # leaf root
        r61.soft(WALL_FACE - WALL, inboard, start, BED, DECK, DECK + thick, 0.4),             # roof land beside the tongue
        # Front stops grow sideways at 45 degrees as the print rises.
        b.prism_xy([(wall_x + 0.01, front_in), (wall_x - 1.5, front_in), (wall_x + 0.01, front_in + 1.51)], LIP_TOP - 0.01, zt),
        b.prism_xy([(WALL_FACE - 0.01, front_out), (WALL_FACE + 3.3, front_out), (WALL_FACE - 0.01, front_out + 3.31)], LIP_TOP - 0.01, 5.8),
    ]
    return b.union(parts) + spring()


def pack_bay():
    """Anything hanging under the deck inside the pouch and leaf space. The deck itself is not cut."""
    return b.box(WALL_FACE, PACK_X[1] + CLEAR, PACK_Y0 - 0.05, BED + 1.0, LIP_TOP, DECK)


# ------------------------------------------------------------------- 2. rod
def rod_cutter(body):
    near = body ^ b.box(-5.6, 5.6, -80, 80, -5.6, 5.6)
    front = float(near.bounding_box()[1])
    wider, length = FUNNEL
    bore = lay(mf.Manifold.cylinder(BED - front + 4.0, ROD_R, ROD_R, 144), front - 2.0)
    mouth_front = lay(mf.Manifold.cylinder(length + 0.1, ROD_R + wider * (length + 0.1) / length, ROD_R, 144), front - 0.1)
    mouth_rear = lay(mf.Manifold.cylinder(SOCKET[1] + 0.1, ROD_R, socket_radius(-0.1), 144), BED - SOCKET[1])
    return bore + mouth_front + mouth_rear, front


def lay(shape, y):
    """A solid built along +Z, laid along +Y from station y."""
    return shape.rotate((-90, 0, 0)).translate((0, y, 0))


def socket_radius(depth):
    """Radius of the rear socket this far in from the bed face."""
    return SOCKET[0] - (SOCKET[0] - ROD_R) * depth / SOCKET[1]


def collet(pushed=0.0):
    """Open wedge ring at its installed place: flange COLLET_GAP proud of the bed face, less `pushed`.

    At pushed = 0 its cone lies on the socket cone. Pushing it in closes it on the rod; pulling the
    flange releases it. It snaps on sideways over the rod, so nothing has to be threaded from a rod end.
    """
    radius, thick = COLLET_FLANGE
    face = BED + COLLET_GAP
    wedge = lay(mf.Manifold.cylinder(COLLET_WEDGE + COLLET_GAP, socket_radius(COLLET_WEDGE) - 0.02, socket_radius(-COLLET_GAP) - 0.02, 144), BED - COLLET_WEDGE)
    ring = wedge + lay(mf.Manifold.cylinder(thick, radius, radius, 144), face)
    ring -= lay(mf.Manifold.cylinder(COLLET_WEDGE + COLLET_GAP + thick + 2.0, COLLET_BORE_R, COLLET_BORE_R, 144), BED - COLLET_WEDGE - 1.0)
    reach = 9.0 * math.tan(math.radians(COLLET_OPEN_DEG))
    ring -= b.prism_xz([(0.0, 0.0), (-9.0, reach), (-9.0, -reach)], BED - COLLET_WEDGE - 1.0, face + thick + 1.0)
    return ring.translate((0, -float(pushed), 0))


# ----------------------------------------------------------------- 1. hinge
def bore_section():
    """Cheek void in (Y, Z) about the common line. The print top is -Y."""
    at = lambda v, u: (AXIS - u, KEEPER_Z + v)
    drop = BORE_FLOOR - 0.9
    return b._section([at(-1.0, -BORE_FLOOR), at(1.0, -BORE_FLOOR), at(BORE_Z, -drop), at(BORE_Z, BORE_SHOULDER),
                       at(FLAT_HALF, BORE_ROOF), at(-FLAT_HALF, BORE_ROOF), at(-BORE_Z, BORE_SHOULDER), at(-BORE_Z, -drop)])


def lead_in(section, face, inward):
    wide = m.along_x(section.offset(RELIEF, mf.JoinType.Round, 2.0, 48), *sorted((face - 0.02 * inward, face + 0.01 * inward)))
    deep = m.along_x(section, *sorted((face + RELIEF * inward, face + (RELIEF + 0.01) * inward)))
    return mf.Manifold.batch_hull([wide, deep])


def cheek_cutter():
    section = bore_section()
    inner, outer = m.CHEEK_X
    cut = m.along_x(section, inner - 0.02, outer + 0.02) + lead_in(section, inner, 1) + lead_in(section, outer, -1)
    return b.mirrored(cut)


def saddle_height(y):
    reach = m.BARREL_R + SADDLE_GAP
    angle = math.radians(SADDLE_DEG)
    return KEEPER_Z - (reach - math.sin(angle) * abs(y - AXIS)) / math.cos(angle)


def saddle():
    """Two V pads under the barrel ends. The barrel's own cylinder turns in them."""
    front = AXIS - m.BARREL_R * math.sin(math.radians(36.0))
    outline = [(front, SADDLE_BASE), (front, saddle_height(front)), (AXIS, saddle_height(AXIS)), (BED, saddle_height(BED)), (BED, SADDLE_BASE)]
    return b.mirrored(b.prism_yz(outline, *SADDLE_X))


def hinge(body):
    inner, outer = m.CHEEK_X
    # Refill the R57 cheek holes and their funnels inside each cheek, then cut the new bore.
    plug = b.mirrored(b.box(inner + 0.01, outer - 0.01, AXIS - 2.75, AXIS + 2.45, 14.05, 18.88))
    return body + plug + saddle() - cheek_cutter()


def barrel_cutter():
    """Only the two side walls of the R58 slot are cut. The top of the bore and its roof are not touched."""
    z = m.BARREL_HOLE_Z
    bore = m.hole_section(AXIS, z, m.BARREL_HOLE_R, (0, -1))
    start = m.PIN_R + 0.19                    # 0.01 mm inside the R58 slot wall, in air

    def strip(sign, reach):
        y0, y1 = sorted((AXIS + sign * start, AXIS + sign * reach))
        return bore ^ mf.CrossSection.square((y1 - y0, 8.0)).translate((y0, z - 4.0))

    cuts = []
    for sign in (1.0, -1.0):
        cuts.append(m.along_x(strip(sign, 3.0), *RELIEF_X))                                  # back to the round bore
        cuts.append(m.along_x(strip(sign, LAND_HALF), LAND_X[0] - 0.05, LAND_X[1] + 0.05))   # wider short lands
    return b.mirrored(b.union(cuts))


def hinge_gauges():
    """Replacements for the three inherited cheek gauges and the barrel-lowering box, on the R63 line."""
    inner, outer = m.CHEEK_X
    radius = m.PIN_R + 0.10
    rod = lambda x0, x1: mf.Manifold.cylinder(x1 - x0, radius, radius, 48).rotate((0, 90, 0)).translate((x0, AXIS, KEEPER_Z))
    barrel = m.barrel().translate((0, REAR, 0.15))
    return {'pin_go_gauge_through_both_cheeks': [rod(-outer - 0.6, outer + 0.6)],
            'pin_go_gauge_through_left_cheek': [rod(-outer - 0.6, -inner)],
            'pin_go_gauge_through_right_cheek': [rod(inner, outer + 0.6)],
            'barrel_between_cheeks_from_above': [barrel.translate((0, 0, float(z))) for z in np.arange(0, 10.1, 1.0)]}


def posed(shape, degrees):
    """Paddle pose about the R63 hinge line, the barrel axis in its saddle. Positive lowers the front edge."""
    a = math.radians(degrees)
    cs, sn = math.cos(a), math.sin(a)
    basis = np.array([[1, 0, 0], [0, cs, -sn], [0, sn, cs]])
    pivot = np.array([0, AXIS, KEEPER_Z])
    return shape.transform(np.column_stack([basis, pivot - basis @ pivot]).tolist())


def clip_recess():
    """Room in the paddle top behind the clip well for the clip's grip, which now sits lower with the pin."""
    drop = m.PIN_Z - KEEPER_Z
    # 0.55 mm beside the grip and 0.42 mm under it, for a real 0.5 mm bead; open through the barrel's rear face.
    return b.box(-m.CLIP_T / 2 - 0.55, m.CLIP_T / 2 + 0.55, AXIS + m.WELL[2] - m.AXIS_Y - 0.1, AXIS + 4.0, b.SEAT_Z - drop - 0.42, b.SEAT_Z + 1.0)


# ------------------------------------------------------- common pin opening
def segments(section):
    rings = [np.asarray(ring, float) for ring in section.to_polygons() if len(ring) >= 3]
    if not rings:
        return np.zeros((0, 2)), np.zeros((0, 2))
    return np.vstack(rings), np.vstack([np.roll(ring, -1, axis=0) for ring in rings])


def distance(points, section):
    start, end = segments(section)
    points = np.atleast_2d(np.asarray(points, float))
    if not len(start):
        return np.full(len(points), np.inf)
    span = end - start
    length = np.maximum((span * span).sum(axis=1), 1e-18)
    rel = points[:, None, :] - start[None]
    t = np.clip((rel * span[None]).sum(axis=2) / length[None], 0.0, 1.0)
    gap = rel - t[..., None] * span[None]
    return np.sqrt((gap * gap).sum(axis=2)).min(axis=1)


def inside(points, section):
    start, end = segments(section)
    points = np.atleast_2d(np.asarray(points, float))
    if not len(start):
        return np.zeros(len(points), bool)
    rise = end[:, 1] - start[:, 1]
    rise = np.where(rise == 0, 1e-18, rise)
    y, z = points[:, 0][:, None], points[:, 1][:, None]
    spans = (start[None, :, 1] > z) != (end[None, :, 1] > z)
    cross = start[None, :, 0] + (z - start[None, :, 1]) * (end[None, :, 0] - start[None, :, 0]) / rise[None]
    return (np.sum(spans & (y < cross), axis=1) % 2) == 1


def shadow(body, x0, x1, centre, reach=3.0):
    """All material between two X stations, seen along the pin, as a section in (Y, Z)."""
    y, z = centre
    return (body ^ b.box(x0, x1, y - reach, y + reach, z - reach, z + reach)).transform(TO_YZ).project()


def go(shades, centre):
    """Largest straight round pin through every listed section: radius and centre."""
    free = mf.CrossSection.circle(2.6, 144).translate((float(centre[0]), float(centre[1])))
    for shade in shades:
        free = free - shade
    best, room = np.asarray(centre, float), 0.0
    half, step = 0.60, 0.03
    for _ in range(3):
        axis = np.arange(-half, half + step / 2, step)
        grid = best + np.array([(y, z) for y in axis for z in axis])
        space = np.where(inside(grid, free), distance(grid, free), 0.0)
        i = int(space.argmax())
        if space[i] > room:
            best, room = grid[i], float(space[i])
        half, step = 1.5 * step, step / 8
    return round(room, 3), [round(float(v), 3) for v in best]


# -------------------------------------------------------------------- build
def paddle():
    source = b.load(r61.OUT / PADDLE)
    cutter = barrel_cutter() + clip_recess()
    cut = one_piece(source - cutter, 'paddle')
    # Locality: the cutter's own intersection, the barrel zone and everything outside it, never a whole-body difference.
    zone = b.box(-6.6, 6.6, AXIS - 2.0, AXIS + 3.7, KEEPER_Z - 2.3, b.SEAT_Z + 0.1)
    removed = vol(source, cutter)
    inside_change = vol(source, zone) - vol(cut, zone)
    outside_change = float((source - zone).volume() - (cut - zone).volume())
    before, after = source.transform(TO_YZ), cut.transform(TO_YZ)
    sections = {f'x_{x:g}': round(float(before.slice(x).area() - after.slice(x).area()), 4) for x in (-9.5, -8.0, 8.0, 9.5)}
    report = dict(cut_from_the_slot_walls_mm3=round(removed, 3), change_inside_the_barrel_zone_mm3=round(inside_change, 3),
                  change_outside_the_barrel_zone_mm3=round(outside_change, 4), section_area_change_away_from_the_cut_mm2=sections,
                  barrel_land_half_width_mm=LAND_HALF, lands_x_mm=list(LAND_X))
    assert 0.3 < removed < 5.0 and abs(inside_change - removed) < 0.02 and abs(outside_change) < 0.02, report
    assert max(abs(v) for v in sections.values()) < 0.005, report
    return cut, report


def holder():
    _, bare, _, working, _ = prior.geometry()
    d44 = k.h.d
    base = d44.r22.base
    assert abs(base.slab_bottom() - DECK) < 0.01, base.slab_bottom()
    assert np.allclose(base.key_positions()[0], KEY0) and base.key_rotations()[0] == 0
    spaces = {n: placed(v, n) for n, v in working.items() if n.startswith('key_')}
    cutters = {n: placed(v, n) for n, v in d44.socket_print_cutters(working).items() if n.startswith('key_')}
    tail = r62.compact_tail(turned_seat(bare, base))
    bay = pack_bay()
    stage = (tail - bay) + r62.finger_guard() + left_guard() + cradle()
    joined = d44.r22.spaces16.carve(stage, cutters, 'R63 key spaces')
    joined, _ = c.blend_seam(joined, d44.OUTER_BANK_START, float(base.plate_top()))
    joined, _ = c.ease_socket_end(joined, spaces['key_3_maximum_socket'])
    for name, route in spaces.items():
        if name.endswith('_mount_opening'):
            centre = np.asarray(route.bounding_box()).reshape(2, 3).mean(axis=0)
            joined -= route.translate(tuple(-centre)).scale((1.001, 1.001, 1)).translate(tuple(centre))
    # Keep the outer lip clear of the turned switch clip after STL simplification.
    clip_space = spaces['key_0_clip_relief']
    centre = np.asarray(clip_space.bounding_box()).reshape(2, 3).mean(axis=0)
    joined -= clip_space.translate(tuple(-centre)).scale((1.008, 1.004, 1.025)).translate(tuple(centre))
    joined -= b.box(-14.8, -12.35, 19.15, 23.15, 8.45, 10.4)       # R61: upper-left inboard latch
    joined -= b.box(*CLIP_CLEARANCE)                               # R62: upper-right latch, open through the top
    joined = hinge(joined)
    bore, front = rod_cutter(joined)
    joined -= bore
    facts = dict(bay_cut_under_the_deck_mm3=round(vol(tail, bay), 3), rod_front_face_y_mm=round(front, 3),
                 turned_socket=spaces['key_0_maximum_socket'], working=working, spaces=spaces)
    return joined, facts


def main():
    OUT.mkdir(exist_ok=True)
    body, facts = holder()
    mesh = OUT / HOLDER
    b.save_closed(mesh, one_piece(body, 'holder').simplify(0.001))
    C = b.load(mesh)
    fold = b.box(12.4, 15.1, 22.1, 25.05, 8.45, 10.5)
    if not (C ^ fold).is_empty():
        b.save_closed(mesh, C - b.box(*CLIP_CLEARANCE))            # R62: a folded socket wall can remain in the STL
        C = b.load(mesh)
    assert (C ^ fold).is_empty(), 'A folded mesh remains inside the switch clip relief'
    # The turned inboard corner can fold across its own opening during mesh
    # simplification. Trim the exported solid with the actual mating contours.
    corner = b.box(-14.9, -13.25, -8.05, -2.9, 9.20, 13.2)
    for name in ('key_0_switch', 'key_0_clip_relief', 'key_0_mount_opening'):
        seat = facts['spaces'][name]
        xyz = np.asarray(seat.bounding_box()).reshape(2, 3).mean(axis=0)
        relief = seat.translate(tuple(-xyz)).scale((1.008, 1.008, 1.025)).translate(tuple(xyz))
        C -= relief ^ corner
    b.save_closed(mesh, C)
    C = b.load(mesh)
    P, paddle_report = paddle()
    b.save_closed(OUT / PADDLE, P)
    P = b.load(OUT / PADDLE)
    pouch, leaf = pack(), spring()
    b.save_closed(OUT / PACK_FILE, pouch)
    spaces, working = facts['spaces'], facts['working']
    tool = left_backer(facts['turned_socket'])
    b.save_closed(OUT / BACKER, tool)

    # ---- keys: every inherited space, key_0 turned, against the saved holder
    entered, checked = [], 0
    for name, space in spaces.items():
        for i, pose in enumerate(c.poses(space)):
            checked += 1
            amount = vol(C, pose)
            if amount > 0.01:
                entered.append([name, i, round(amount, 4)])
    fitted = b.union([spaces[f'key_{i}_{item}'] for i in (0, 2, 3, 4) for item in ('switch', 'maximum_socket')])
    neighbour = b.union([spaces[f'key_3_{item}'] for item in ('switch', 'maximum_socket', 'socket_tape_zone')])
    key0 = dict(centre_xy_mm=list(KEY0), turned_deg=TURN_DEG,
                socket_bounds_mm=[round(float(v), 2) for v in facts['turned_socket'].bounding_box()],
                slide_poses=len(spaces['key_0_soldered_socket_slide']),
                soldered_socket_to_upper_left_key_parts_mm3=round(max(vol(pose, neighbour) for pose in c.poses(spaces['key_0_soldered_socket_slide'])), 4),
                left_guard_core_missing_mm3={name: round(float((core - C).volume()), 4) for name, core in left_guard_cores().items()},
                new_left_backer_sweep_mm3=round(max(vol(C, tool.translate((-float(dx), 0, 0))) for dx in range(27)), 4),
                new_left_backer_under_socket_mm2=round(vol(tool.translate((0, 0, 0.3)), facts['turned_socket']) / 0.2, 1),
                r58_backers_sweep_mm3={side: round(max(vol(C, b.load(prior.old.R58 / 'exports' / f'Socket_Backer_{side}-assembly.stl')
                                                           .translate((sign * float(dx), 0, 0))) for dx in range(27)), 4)
                                       for side, sign in (('Left', -1), ('Right', 1))})

    # ---- battery
    rod, lane = k.h.base.rod(), working['external_wire_bus']
    cross = lane.rotate((-90, 0, 0)).slice(-prior.BED + 0.55)
    tail_lane = cross.extrude(REAR + 0.12).rotate((90, 0, 0)).translate((0, BED + 0.05, 0))     # as fit61
    keep_out = rod + lane + tail_lane
    rigid = C - leaf
    face = b.box(PACK_X[0], PACK_X[1], PACK_Y0, PACK_Y0 + PACK[1], PACK_Z[1], PACK_Z[1] + 0.12)
    loading = {}
    for name, space in spaces.items():
        amount = max(vol(pouch, pose) for pose in c.poses(space))
        if amount > 0.01:
            loading[name] = round(amount, 3)
    battery = dict(
        pack_bounds_mm=[round(float(v), 3) for v in pouch.bounding_box()], moved_from_r62_mm=list(PACK_MOVE),
        gap_pack_face_to_deck_mm=dict(r62=OLD_GAP_TO_DECK, r63=round(DECK - PACK_Z[1], 3)),
        lowest_seat_material_below_the_deck_mm=dict(r62=round(DECK - (OLD_PACK_MIN[2] - 1.1), 2), r63=round(DECK - LOW, 2)),
        deck_or_land_directly_over_the_pack_face_mm2=round(float((C ^ face).project().area()), 1), pack_face_mm2=round(PACK[0] * PACK[1], 1),
        seated_to_holder_with_the_leaf_mm3=round(vol(C, pouch), 4), seated_to_holder_without_the_leaf_mm3=round(vol(rigid, pouch), 4),
        slide_in_from_the_free_end_without_the_leaf_mm3=round(max(vol(rigid, pouch.translate((0, float(t), 0))) for t in range(31)), 4),
        pack_and_seat_in_rod_or_wire_lane_mm3=round(vol(pouch + cradle(), keep_out), 4),
        pack_to_fitted_switches_and_sockets_mm3=round(vol(pouch, fitted), 4), key_routes_that_cross_the_seated_pack_mm3=loading,
        pack_to_both_guards_mm3=round(vol(pouch, r62.finger_guard() + left_guard()), 4),
        end_past_the_bed_face_mm=round(PACK_Y0 + PACK[1] - BED, 2), leaf_shoe_into_nominal_pack_mm=SHOE, rigid_side_clearance_mm=CLEAR)

    # ---- rod and hinge
    probe = mf.Manifold.cylinder(BED + 40.0, ROD_R - 0.01, ROD_R - 0.01, 96).rotate((-90, 0, 0)).translate((0, -30.0, 0))
    reach = m.CHEEK_X[1] + 0.2
    line = (AXIS, KEEPER_Z)
    cheeks, barrel = shadow(C, -36.0, 36.0, line), shadow(P, -reach, reach, line)
    bay_zone = C ^ b.box(-12, 12, AXIS - 6.0, BED + 0.1, 10, 22)
    hinge_report = dict(
        common_line_yz_mm=[AXIS, KEEPER_Z], cheeks_alone=go([cheeks], line), barrel_alone=go([barrel], line),
        both_at_rest=go([cheeks, barrel], line), paddle_to_holder_at_rest_mm3=round(vol(P, C), 4),
        paddle_swing_to_hinge_end_of_holder_mm3=round(max(vol(posed(P, float(a)), bay_zone) for a in np.linspace(-6.0, 1.5, 16)), 4),
        saddle_gap_mm=SADDLE_GAP, cheek_void_z_mm=[round(KEEPER_Z - BORE_Z, 2), round(KEEPER_Z + BORE_Z, 2)],
        wall_in_front_of_the_roof_mm=round(AXIS - m.CHEEK_FRONT - REAR - BORE_ROOF, 3), wall_under_the_floor_to_the_bed_mm=round(BED - AXIS - BORE_FLOOR, 3))
    # ---- pin and clip on the new line, and the rod keeper
    down = (0, 0, KEEPER_Z - m.PIN_Z)
    clip = b.load(r61.OUT / 'Pin_Clip-assembly.stl').translate(down)
    pin = b.load(r61.OUT / 'Hinge_Pin-assembly.stl').translate(down)
    hinge_report.update(
        clip_to_paddle_seated_mm3=round(vol(clip, P), 4), pin_to_paddle_and_holder_mm3=round(vol(pin, P) + vol(pin, C), 4),
        clip_lowers_into_the_well_mm3=round(max(vol(clip.translate((0, 0, float(z))), P) for z in np.linspace(0.0, 8.0, 17)), 4),
        clip_grip_on_the_pin_waist_mm3=round(vol(clip, pin), 4), clip_recess_cut_mm=[round(float(v), 2) for v in clip_recess().bounding_box()])
    ring = collet()
    b.save_closed(OUT / COLLET_FILE, ring)
    slope = (SOCKET[0] - ROD_R) / SOCKET[1]
    rod_only = mf.Manifold.cylinder(60.0, 4.0, 4.0, 96).rotate((-90, 0, 0)).translate((0, BED - 20.0, 0))
    mouth_ring = lay(mf.Manifold.cylinder(1.0, 6.0, 6.0, 96), BED - 1.0)       # holder material here is the socket wall
    keeper = dict(
        part='Rod_Collet', file=COLLET_FILE, installed_flange_face_y_mm=round(BED + COLLET_GAP, 2), push_in_travel_mm=COLLET_GAP,
        path='snap sideways onto the rod behind the holder with the opening toward the wire lane, then push along -Y into the rear socket; pull the flange to release',
        socket_radius_at_bed_face_mm=SOCKET[0], socket_depth_mm=SOCKET[1], taper_half_angle_deg=round(math.degrees(math.atan(slope)), 2),
        radial_squeeze_available_mm=round(COLLET_GAP * slope, 3), collet_bore_on_8mm_rod_radial_gap_mm=round(COLLET_BORE_R - 4.0, 3),
        wall_at_tip_mm=round(socket_radius(COLLET_WEDGE) - COLLET_BORE_R, 3), wrap_deg=round(360 - 2 * COLLET_OPEN_DEG, 1),
        snap_on_spread_mm=round(8.0 - 2 * COLLET_BORE_R * math.sin(math.radians(COLLET_OPEN_DEG)), 2),
        installed_to_holder_mm3=round(vol(ring, C), 4), pushed_home_overlap_with_holder_mm3=round(vol(collet(COLLET_GAP), C), 3),
        installed_to_rod_mm3=round(vol(ring, rod_only), 4), installed_to_pack_and_wire_lane_mm3=round(vol(ring, pouch + keep_out - rod), 4),
        holder_wall_within_6mm_of_the_axis_at_the_mouth_mm3=round(vol(C, mouth_ring), 2), a_full_1mm_wall_ring_there_would_be_mm3=round(math.pi * (36.0 - SOCKET[0] ** 2), 1),
        socket_opens_into_the_wire_lane_mm3=round(vol(lay(mf.Manifold.cylinder(SOCKET[1], ROD_R, SOCKET[0], 96), BED - SOCKET[1]), lane + tail_lane), 3),
        holding_torque_and_slide_force='not measured; friction of a printed wedge on carbon needs the physical test')
    report = dict(revision='R63', physical_fit_verified=False, rod_keeper=keeper, carrier_sha256=sha256(mesh.read_bytes()).hexdigest(),
                  paddle_sha256=sha256((OUT / PADDLE).read_bytes()).hexdigest(), carrier_volume_mm3=round(float(C.volume()), 1),
                  key_poses_checked=checked, key_obstructions=entered, key_0=key0, battery=battery,
                  rod=dict(bore_diameter_mm=2 * ROD_R, material_inside_the_bore_mm3=round(vol(C, probe), 4), funnel_mm=list(FUNNEL),
                           front_face_y_mm=facts['rod_front_face_y_mm'], grip='Rod_Collet wedged into the rear socket; nothing fixed stands in the bore'),
                  hinge=hinge_report, paddle=paddle_report, bay_cut_under_the_deck_mm3=facts['bay_cut_under_the_deck_mm3'])
    gates = {
        'every key, socket and loading space is clear of the holder': not entered,
        'the left guard members keep their cores': max(key0['left_guard_core_missing_mm3'].values()) < 0.05,
        'the new left backing strip slides in': key0['new_left_backer_sweep_mm3'] < 0.01,
        'the pack seats and slides in against the rigid seat': max(battery['seated_to_holder_without_the_leaf_mm3'],
                                                                   battery['slide_in_from_the_free_end_without_the_leaf_mm3']) < 0.01,
        'only the leaf shoe touches the seated pack': 0 < battery['seated_to_holder_with_the_leaf_mm3'] < 4.0,
        'pack and seat stay out of the rod and wire lane': battery['pack_and_seat_in_rod_or_wire_lane_mm3'] < 0.01,
        'pack clears fitted keys and both guards': max(battery['pack_to_fitted_switches_and_sockets_mm3'], battery['pack_to_both_guards_mm3']) < 0.01,
        'deck or land lies over the pack face': battery['deck_or_land_directly_over_the_pack_face_mm2'] > 60,
        'the rod bore is empty': report['rod']['material_inside_the_bore_mm3'] < 0.01,
        'the moved clip and pin clear the paddle and holder': max(hinge_report['clip_to_paddle_seated_mm3'], hinge_report['pin_to_paddle_and_holder_mm3'],
                                                                  hinge_report['clip_lowers_into_the_well_mm3']) < 0.005,
        'the rod keeper sits clear until pushed, then bears on the socket': keeper['installed_to_holder_mm3'] < 0.01 < keeper['pushed_home_overlap_with_holder_mm3']
        and keeper['installed_to_rod_mm3'] < 0.01 and keeper['installed_to_pack_and_wire_lane_mm3'] < 0.01,
        'one straight pin line through both parts at rest': hinge_report['both_at_rest'][0] >= 1.74,
        'the paddle rests and swings clear of the saddle and cheeks': max(hinge_report['paddle_to_holder_at_rest_mm3'],
                                                                         hinge_report['paddle_swing_to_hinge_end_of_holder_mm3']) < 0.01,
    }
    report['failed'] = [name for name, passed in gates.items() if not passed]
    report['passes'] = not report['failed']
    (OUT / 'carrier.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=1), flush=True)
    if report['failed']:
        raise SystemExit('R63 checks need attention: ' + '; '.join(report['failed']))


if __name__ == '__main__':
    main()
