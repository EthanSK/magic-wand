"""R66 key carrier: R63's one-piece OP1 deck with its three socket holes, opened only
where the white plug and its lead must pass, on the R64 guards, hinge and rod grip.

Assembly frame as in R53-R64: the rod runs along Y through X = Z = 0, +Z is up,
+Y is the top (two-key) end and the rear face Y = BED lies on the print bed.

OP1 route (the prewired harness stays attached to the wand):
1. Leave the black switch and the top retainer off. Unplug the white plug from the board.
2. Tip the plug so its lead hangs straight down. Raise it from below, beside the
   installed rod and inside the right finger guard, up through the deck opening.
3. Above the holder, turn the plug upright and push the board's fixed white housing onto it.
4. Lower the board straight down. Its three metal sockets enter the three integral holes,
   the housing and plug drop into the opening and the lead runs down through the outlet.
5. Press the lead up into the open channel under the deck, fit the switch, then the
   paddle and finally the existing top retainer.

Printability: an exterior backing on the right-hand rear rod socket wall (see
rod_socket_backing) removes a knife edge that sliced as an unsupported fragment.

What the prewired option does not allow: a board whose plug is already mated cannot be
lowered from above, because its lead would have to thread through the closed deck. The
plug also cannot be pushed into the housing from below once the board is seated: in its
mating orientation it is 6.2 mm across and must rise beside the rod into the 6-7 mm gap
inside the finger guard with no room for fingers. Both limits are reported by the checks.
"""
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
for folder in ('carbon-rod-holders-r64-under-entry', 'carbon-rod-holders-r63-open-hinge',
               'carbon-rod-holders-r62-compact-guard'):
    if str(HARDWARE / folder) not in sys.path:
        sys.path.insert(0, str(HARDWARE / folder))

import design64 as r64  # noqa: E402
import hinge64  # noqa: E402

old = r64.old          # design63
b = old.b              # build53 helpers and the measured OP1 constants
OUT = HERE / 'exports'
HOLDER = old.HOLDER
R63_CARRIER = old.OUT / HOLDER
R64_OUT = r64.OUT
GUIDE_DIR = OUT / 'guide'
LEAD_FILES = {'thread': 'op1_lead_thread.stl', 'turn_end': 'op1_lead_turned.stl', 'drop': 'op1_lead_drop.stl', 'route': 'op1_lead_route.stl'}

# ------------------------------------------------------------------ OP1 plug passage
LEAD_R = 1.30                 # R51 OP1 lead, measured from its mesh
EXIT = (0.0, 20.65, 5.05)     # board frame: where the lead leaves the plug's end face
PLUG_GAP = 0.75               # R63 cleared the tipped plug by only 0.026 mm; open the deck this much round it
ABOVE_GAP = 0.45              # above the deck the plug rises past the board's end stop: standard float only
DECK_TOP = b.PCB_Z            # the board rests here; below it the opening is a closed hole
LEAD_GAP = 0.45               # clearance of the lead in the outlet while the board drops
HOUSING_GAP = 0.45            # the R53/R63 float round the fixed housing and mated plug
THREAD_XY = (8.2, 14.6)       # world centre of the tipped plug's vertical path
THREAD_YAW = 10.0             # its long side runs nearly parallel to the rod
THREAD_Z = (-17.0, 15.0)      # lowest and highest height of the lead exit while threading
BEND_R = 2.0                  # lead centreline bend radius while the mated board drops
LIFT = 16.0                   # the mated board starts this far above its seat
WINDOW = (0.8, 13.5, 6.0, 26.0, 7.0, 12.6)   # only deck-level material in here may be opened
TURN_HEIGHT = 18.0            # exit height where the plug is turned upright above the holder

# --------------------------------------------------------- battery: outboard rail taper
# The rod-side (inboard) rail, the spring leaf and its bed-side root are unchanged.
# The outboard wall and lip keep full depth up to TAPER[0], then rise smoothly to the deck.
TAPER = (32.0, 41.0)
WALL_EDGE_R = 0.38            # bull-nose on the reduced outboard edge
ROOT_EDGE_R = 0.45            # rounded corners on the spring root post, now exposed


# ================================================================ bought hardware
def board_frame():
    m = np.eye(4)
    m[:3] = b.board_matrix()
    return m


@lru_cache(maxsize=1)
def hardware():
    """Seated bought parts in world coordinates (board, sockets, housing, plug, op1_wire)."""
    return r64.hardware()


def exit_world():
    return board_frame()[:3] @ np.array([*EXIT, 1.0])


def board_axes():
    m = board_frame()
    return m[:3, 0], m[:3, 1], m[:3, 2]


def rotation_about(axis, degrees, point):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    a = math.radians(degrees)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    r = np.eye(3) + math.sin(a) * k + (1 - math.cos(a)) * k @ k
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = point - r @ point
    return m


def translation(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def tip_pose(height, xy=THREAD_XY, yaw=THREAD_YAW):
    """World transform of the plug (and its lead) from the seated pose to the tipped pose.

    The end face with the lead turns down, the plug's long side turns to `yaw` from +Y,
    and the lead exit sits at (xy, height).
    """
    e = exit_world()
    bx, by, bz = board_axes()
    tip = rotation_about(bx, -90.0, e)                      # lead exit now points down
    long_axis = (tip[:3, :3] @ bx)                          # the 6.2 mm side, horizontal
    heading = math.degrees(math.atan2(long_axis[1], long_axis[0]))
    turn = rotation_about((0, 0, 1), (90.0 + yaw) - heading, e)
    return translation((xy[0] - e[0], xy[1] - e[1], height - e[2])) @ turn @ tip


def mate_pose(lift):
    return translation((0, 0, lift))


def tube(points, radius=LEAD_R, sides=20):
    """Closed tube along a polyline with a fixed vertex order, so lead shapes can morph."""
    pts = np.asarray(points, float)
    tangents = np.gradient(pts, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1)[:, None]
    ref = np.array([1.0, 0, 0]) if abs(tangents[0][0]) < .9 else np.array([0, 1.0, 0])
    normal = np.cross(tangents[0], ref)
    normal /= np.linalg.norm(normal)
    rings = []
    for p, t in zip(pts, tangents):
        normal = normal - t * (normal @ t)       # parallel transport keeps the seams aligned
        normal /= np.linalg.norm(normal)
        binormal = np.cross(t, normal)
        angles = np.linspace(0, 2 * math.pi, sides, endpoint=False)
        rings.append(p + radius * (np.cos(angles)[:, None] * normal + np.sin(angles)[:, None] * binormal))
    vertices = np.vstack(rings + [pts[:1], pts[-1:]])
    n, s = len(pts), sides
    faces = []
    for i in range(n - 1):
        for j in range(s):
            a, c = i * s + j, i * s + (j + 1) % s
            faces += [(a, c, a + s), (c, c + s, a + s)]
    first, last = n * s, n * s + 1
    for j in range(s):
        faces.append((first, (j + 1) % s, j))
        faces.append((last, (n - 1) * s + j, (n - 1) * s + (j + 1) % s))
    return vertices, np.asarray(faces)


SAMPLES = 90
LEAD_LENGTH = 34.0


def _resample(points, count=SAMPLES):
    pts = np.asarray(points, float)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    s = np.linspace(0, seg[-1], count)
    return np.column_stack([np.interp(s, seg, pts[:, k]) for k in range(3)])


def lead_path(shape):
    """Lead centreline in the seated world frame, equal arc length for every shape."""
    e = exit_world()
    _, by, _ = board_axes()
    if shape == 'thread':
        # Straight out of the end face. The tipped pose turns it straight down.
        return _resample([e, e + by * LEAD_LENGTH])
    if shape == 'drop':
        stub, arc = .4, BEND_R * math.pi / 2
        pts = [e, e + by * stub]
        centre = e + by * stub - np.array([0, 0, BEND_R])
        for a in np.linspace(0, math.pi / 2, 12)[1:]:
            pts.append(centre + by * BEND_R * math.sin(a) + np.array([0, 0, BEND_R * math.cos(a)]))
        tail = LEAD_LENGTH - stub - arc
        pts.append(pts[-1] - np.array([0, 0, tail]))
        return _resample(pts)
    if shape == 'route':
        # Follow the established R51 lead through the under-deck channel to the rear.
        wire = hardware()['op1_wire']
        centres = [e]
        for y in np.arange(16.0, 41.0, 1.0):
            cut = wire ^ b.box(-40, 40, y - .05, y + .05, -20, 20)
            if not cut.is_empty():
                lo, hi = np.reshape(cut.bounding_box(), (2, 3))
                centres.append((lo + hi) / 2)
        pts = _resample(centres, 400)
        length = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
        return _resample(pts[length <= LEAD_LENGTH])
    raise ValueError(shape)


def lead_solid(shape):
    v, f = tube(lead_path(shape))
    return mf.Manifold(mf.Mesh(v.astype(np.float32), f.astype(np.uint32)))


def preview_lead_vertices(shape):
    # The tail stays threaded through the fixed opening when the plug turns. Morph its
    # two end shapes in the carrier frame, instead of rotating the tail with the plug.
    if shape in ('thread', 'turn_end'):
        tipped = shape == 'thread'
        path = lead_path('thread' if tipped else 'drop')
        matrix = tip_pose(THREAD_Z[1]) if tipped else mate_pose(LIFT)
        return tube(path @ matrix[:3, :3].T + matrix[:3, 3])
    return tube(lead_path(shape))


def save_lead_meshes():
    GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    for shape, name in LEAD_FILES.items():
        v, f = preview_lead_vertices(shape)
        trimesh.Trimesh(v, f, process=False).export(GUIDE_DIR / name)


def plug_and_lead(shape):
    return hardware()['plug'] + lead_solid(shape)


# ================================================================ swept routes
def pose(solid, matrix):
    return solid.transform(np.asarray(matrix)[:3].tolist())


def thread_route(clearance=0.0):
    """Tipped plug and its hanging lead rising from below the rod to above the deck."""
    shape = plug_and_lead('thread')
    lo, hi = pose(shape, tip_pose(THREAD_Z[0])), pose(shape, tip_pose(THREAD_Z[1]))
    parts = [mf.Manifold.batch_hull([p, q]) for p, q in
             zip(_convex(lo), _convex(hi))]
    if clearance:
        grow = b.box(-clearance, clearance, -clearance, clearance, -clearance, clearance)
        parts = [p.minkowski_sum(grow) for p in parts]
    return b.union(parts)


def _convex(solid):
    """Convex pieces of a posed plug-and-lead: the plug box and short lead segments."""
    pieces = []
    for piece in solid.decompose():
        bb = np.reshape(piece.bounding_box(), (2, 3))
        if np.ptp(bb, axis=0).max() < 8.0:
            pieces.append(piece.hull())
            continue
        # A long lead: hull consecutive slabs along its own length.
        axis = int(np.argmax(np.ptp(bb, axis=0)))
        lo, hi = bb[0, axis], bb[1, axis]
        steps = np.linspace(lo, hi, int(math.ceil((hi - lo) / 2.0)) + 1)
        for a, z in zip(steps, steps[1:]):
            box = [-60, 60, -60, 80, -60, 60]
            box[2 * axis], box[2 * axis + 1] = a - .01, z + .01
            part = piece ^ b.box(*box)
            if not part.is_empty():
                pieces.append(part.hull())
    return pieces


def drop_group(with_board=True):
    """Mated board group as it is lowered: housing, plug and the lead bent down to the outlet."""
    hw = hardware()
    group = {'housing': hw['housing'], 'plug': hw['plug'], 'lead': lead_solid('drop')}
    if with_board:
        group.update(board=hw['board'], sockets=hw['sockets'])
    return group


def drop_route(name, clearance=0.0, lift=LIFT, bearing_skin=0.0):
    solid = drop_group()[name]
    pieces = _convex(solid) if name == 'lead' else (solid.decompose() if name == 'sockets' else [solid.hull()] if name != 'board' else [solid])
    swept = []
    for p in pieces:
        if name == 'board':
            # The board has eyelet holes; sweep its true outline straight down.
            swept.append(b.union([p.translate((0, 0, z)) for z in np.arange(0, lift + .01, .25)]))
            continue
        piece = mf.Manifold.batch_hull([p, p.translate((0, 0, lift))])
        if clearance:
            piece = piece.minkowski_sum(b.box(-clearance, clearance, -clearance, clearance, 0, clearance))
        swept.append(piece)
    out = b.union(swept)
    if bearing_skin:
        footprint = hardware()['board'].hull().project()
        out -= footprint.extrude(bearing_skin + .001).translate((0, 0, b.PCB_Z - .001))
    return out


def window():
    return b.box(*WINDOW)


@lru_cache(maxsize=1)
def plug_clearance():
    """Tipped plug path grown by PLUG_GAP through the closed deck hole and by ABOVE_GAP
    past the end stop above it, inside the window only."""
    x0, x1, y0, y1, z0, z1 = WINDOW
    return ((thread_route(PLUG_GAP) ^ b.box(x0, x1, y0, y1, z0, DECK_TOP + .05))
            + (thread_route(ABOVE_GAP) ^ b.box(x0, x1, y0, y1, DECK_TOP, z1)))


@lru_cache(maxsize=1)
def plug_passage():
    """The only new opening: the tipped plug path and the dropping lead, at deck level only."""
    # R63 already floats the fixed housing and mated plug by 0.45 mm in its pocket;
    # those faces are checked, not re-cut. The smaller float above the deck keeps most
    # of R63's board end stop (checked against R63 in checks66).
    return plug_clearance() + (drop_route('lead', LEAD_GAP) ^ window())


# ================================================================ battery rail
def taper_floor(y):
    """Underside of the outboard rail: full depth, then a smooth cosine rise to the deck."""
    lo, hi = old.LOW, old.DECK
    t = np.clip((np.asarray(y, float) - TAPER[0]) / (TAPER[1] - TAPER[0]), 0, 1)
    return lo + (hi - lo) * (1 - np.cos(np.pi * t)) / 2


def _hull_spheres(points, radius):
    ball = mf.Manifold.sphere(radius, 16)
    return mf.Manifold.batch_hull([ball.translate(p) for p in points])


def outboard_wall():
    x0, x1 = old.WALL_FACE - old.WALL, old.WALL_FACE
    # The slabs reach 1.1 mm up into the deck and roof land, so the rounded wall can
    # rise all the way into them and vanish without leaving a residual ridge.
    front, top, r = old.PACK_Y0 - .85, old.DECK + 1.1, WALL_EDGE_R
    flat = r64.old.r61.soft(x0, x1, front, TAPER[0] + .2, old.LOW, old.DECK + .3, .3)
    ys = np.r_[np.arange(TAPER[0], TAPER[1], .5), TAPER[1] - .05]
    slabs = []
    for y in ys:
        zb = float(taper_floor(y))
        zb = min(zb, top - 2 * r - .01)
        slabs.append([(x0 + r, y, zb + r), (x1 - r, y, zb + r), (x0 + r, y, top - r), (x1 - r, y, top - r)])
    ball = mf.Manifold.sphere(r, 16)
    pieces = [mf.Manifold.batch_hull([ball.translate(p) for p in s + t]) for s, t in zip(slabs, slabs[1:])]
    return flat + b.union(pieces)


def above_taper(x0, x1):
    ys = np.linspace(old.PACK_Y0 - 2, old.BED + 1, 200)
    profile = [(float(y), float(taper_floor(y))) for y in ys]
    profile += [(old.BED + 1, 12.0), (old.PACK_Y0 - 2, 12.0)]
    return b.prism_yz(profile, x0, x1)


def outboard_lip():
    xo = old.PACK_X[0]
    lip = b.box(old.WALL_FACE - .01, xo + old.LIP_W, old.PACK_Y0 - .85, old.BED, old.LOW, old.LIP_TOP)
    return lip ^ above_taper(old.WALL_FACE - 1, xo + old.LIP_W + 1)


def spring_root():
    """The R63 leaf root at the bed-side end, unchanged in size, with its exposed edges rounded."""
    x0, x1 = old.WALL_FACE - .01, old.PACK_X[0] - .38
    z0, z1 = old.LIP_TOP - .01, old.DECK + .3
    soft = r64.old.r61.soft(x0, x1, old.BED - 5.5, old.BED + 2.0, z0, z1, ROOT_EDGE_R)
    return soft ^ b.box(x0 - 1, x1 + 1, old.BED - 6, old.BED, z0 - 1, z1 + 1)


def front_stop():
    wf, front = old.WALL_FACE, old.PACK_Y0 - .85
    return b.prism_xy([(wf - .01, front), (wf + 3.3, front), (wf - .01, front + 3.31)], old.LIP_TOP - .01, 5.8)


OUTBOARD_ZONE = (-24.62, -18.80, old.PACK_Y0 - 1.0, old.BED + .01, old.LOW - .05, old.DECK)


def outboard_original():
    """R63's outboard members exactly as built, for the equivalence check."""
    xo = old.PACK_X[0]
    wf, front = old.WALL_FACE, old.PACK_Y0 - .85
    parts = [old.r61.soft(wf - old.WALL, wf, front, old.BED, old.LOW, old.DECK + .3, .3),
             b.box(wf - .01, xo + old.LIP_W, front, old.BED, old.LOW, old.LIP_TOP),
             b.box(wf - .01, xo - .38, old.BED - 5.5, old.BED, old.LIP_TOP - .01, old.DECK + .3),
             front_stop(), old.spring()]
    return b.union(parts) ^ b.box(*OUTBOARD_ZONE)


def outboard_new():
    parts = [outboard_wall(), outboard_lip(), spring_root(), front_stop(), old.spring()]
    return b.union(parts) ^ b.box(*OUTBOARD_ZONE)


def taper_battery(body):
    return (body - b.box(*OUTBOARD_ZONE)) + outboard_new()


# ================================================================ rear rod socket backing
# The R63 rear socket is a tapered collet seat inside a split clip. Near the bed face its
# right-hand wall tapers to a sub-bead knife edge, and the R66 native slice started a stray
# 0.15 mm2 outer-wall fragment there at layer 9 with nothing beneath it. This exterior
# backing thickens only the outside of that wall. The collet seat itself, the bed (thrust)
# face and the lengthwise split are untouched; checks66 proves all three.
SOCKET_BACKING_DEPTH = 5.8                   # from the bed face toward the keys
SOCKET_BACKING_R = (5.36, 5.72)              # outer radius at that depth and at the bed face
SOCKET_SEAT_CLEAR = .19                      # clears the split grip even at full tightening travel
SOCKET_BACKING_XZ = [(2.3, 1.5), (6.0, 1.5), (6.0, -2.8), (3.25, -4.7), (2.3, -4.7)]   # right wall only
# The backing was proven on the native slice of this exact exported carrier...
PRE_BACKING_SHA256 = '527c5ee710dbd830bcbc3b5844b4c2634aa8a48ac1ebc227993e4be2eb518de0'
# ...and the natively sliced backed solid has exactly this triangle set (order-independent
# digest, checks66.triangle_digest). Manifold may write the same triangles in another order.
BACKED_TRIANGLES_SHA256 = '26d50f9a82aed730a539bb2cd2c47651d6941e6aa5de699325827c3c26583333'


def socket_backing_box(margin=0.0):
    xs, zs = zip(*SOCKET_BACKING_XZ)
    return b.box(min(xs) - margin, max(xs) + margin, old.BED - SOCKET_BACKING_DEPTH - margin, old.BED + margin,
                 min(zs) - margin, max(zs) + margin)


def socket_seat_void(clear=SOCKET_SEAT_CLEAR):
    """The rear socket taper (the collet seat), grown by `clear` and run 0.1 mm past both ends."""
    depth = SOCKET_BACKING_DEPTH
    return old.lay(mf.Manifold.cylinder(depth + .2, old.socket_radius(depth + .1) + clear,
                                        old.socket_radius(-.1) + clear, 128), old.BED - depth - .1)


def rod_socket_backing():
    """Annular sector added to the outside of the right-hand rear socket wall."""
    depth = SOCKET_BACKING_DEPTH
    outer = old.lay(mf.Manifold.cylinder(depth, *SOCKET_BACKING_R, 128), old.BED - depth)
    sector = b.prism_xz(SOCKET_BACKING_XZ, old.BED - depth, old.BED)
    return (outer - socket_seat_void()) ^ sector


# ================================================================ carrier
def carrier():
    r63 = b.load(R63_CARRIER)
    core, guards = r64.revised_guards(r63)          # R64 rounded guard returns
    body = taper_battery(core + guards)
    body -= plug_passage()
    body = hinge64.carrier(body)                    # R64 compact hinge
    return old.one_piece(body, 'R66 carrier', limit=.02)


def collet_file():
    return R64_OUT / r64.COLLET_FILE


def exported(body, path):
    """Save as the release does and return the reloaded single closed solid."""
    b.save_closed(path, body)
    reloaded = b.load(path)
    if len(reloaded.decompose()) > 1:
        b.save_closed(path, old.one_piece(reloaded, 'exported R66 carrier', limit=.001))
        reloaded = b.load(path)
    return reloaded


def main():
    import tempfile
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUT) as scratch:
        # Export the pre-backing carrier first and add the backing to that exact mesh,
        # as on the native slice that proved it.
        before = Path(scratch) / HOLDER
        base = exported(carrier(), before)
        made = sha256(before.read_bytes()).hexdigest()
        assert made == PRE_BACKING_SHA256, ('pre-backing carrier changed; re-prove the socket backing', made)
    body = base + rod_socket_backing()
    assert len(body.decompose()) == 1, 'socket backing must fuse to the carrier'
    b.save_closed(OUT / HOLDER, body)
    assert len(b.load(OUT / HOLDER).decompose()) == 1
    save_lead_meshes()
    print('saved', OUT / HOLDER, sha256((OUT / HOLDER).read_bytes()).hexdigest(), flush=True)


if __name__ == '__main__':
    main()
