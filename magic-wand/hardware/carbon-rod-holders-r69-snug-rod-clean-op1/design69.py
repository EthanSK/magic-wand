"""R69 key carrier: the R68 carrier with six local changes from the first fitted R68 print.

Assembly frame as in R53-R68: the rod runs along Y through X = Z = 0, +Z is up,
+Y is the top (two-key) end and the rear face Y = BED lies on the print bed.

1. Hinge seat (hinge69.carrier). The bearing cheeks move 1.3 mm toward the touch board
   with the paddle's shorter hinge. Their long ramps become 45 degree buttresses that
   land on the existing rear plateau; the bed face is unchanged.

2. OP1 plug entry. R62's right finger guard ran its top arm from the deck beside the
   OP1 pocket in toward the rod (X 11.7 at Y 11.3) and only then out to the crown. That
   inward bow stood beside the opening the white plug must pass. The arm now leaves its
   root downward and runs straight out to the crown start, bowed away from the rod.
   On the rod side of the same path a 33 mm3 rib root hung from the right face of the
   front saddle, touching nothing else: the twin of the left stubs R67 removed. It is
   removed too.

3. OP1 seat. R53 put two sprung locator leaves with noses for the board's eyelets in
   the deck, each in its own horseshoe pocket. R66 cut the rear one through with the
   plug route, and R67 chamfered that route. All of that is removed: R66's window box is
   replaced by the same box of the R63 export, the board floor is filled as one flat
   slab and both noses and the rear leaf's print backing rib are removed. What remains is the flat seat, the three socket holes and
   one rounded connector window with a centred lead notch and an underside lead-in.

4. Rod grip. R63 bored the whole sleeve to 8.55 mm and added a loose wedge collet. The
   bore from the front face to Y 32.7 is put back to R62's: the 7.8 mm split ring at
   Y 9.25-19.75, the saddle and the 8.0 mm ring at Y 29.25-32.65, identical in R58, R60,
   R61 and R62. Behind Y 32.7 the R63 bore and its rear funnel stay, so nothing at the
   bed face can pinch the rod. A short lead-in is added on the rear ring.

5. Key deck. R58 moved the upper keys 1.4 mm toward the lower row and left a small
   through-window in the strip between the rows on each side. No switch, socket, clip
   or loading path uses it. Both are filled.

6. Retainer rail: unchanged. The carrier keeps R53's two rails and left latch notch.

Build: load the R68 export (SHA-256 checked) and apply the changes. Nothing here is a
claim of physical fit.
 — Claude Fable 5.2"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
for folder in ('carbon-rod-holders-r68-pre-taper-battery-rail', 'carbon-rod-holders-r67-diagonal-battery-corner',
               'carbon-rod-holders-r66-three-hole-op1', 'carbon-rod-holders-r64-under-entry',
               'carbon-rod-holders-r63-open-hinge', 'carbon-rod-holders-r62-compact-guard',
               'carbon-rod-holders-r53-guided-op1'):
    if str(HARDWARE / folder) not in sys.path:
        sys.path.insert(0, str(HARDWARE / folder))

import design68 as r68  # noqa: E402
import hinge69 as hinge  # noqa: E402
import carrier53  # noqa: E402

r67, r66, old, b = r68.r67, r68.r66, r68.old, r68.b       # old is design63, b is build53
r62, r61 = old.r62, old.r61
base = old.k.h.d.r22.base                                 # R16 key-bay helpers
OUT = HERE / 'exports'
HOLDER = r68.HOLDER
R68_CARRIER, R63_CARRIER, R62_CARRIER = r68.OUT / HOLDER, old.OUT / HOLDER, r62.OUT / HOLDER
R68_SHA256 = '4e914a59acfc5f32038d4ee3d21b8b2231f9ba9498f49ffd9f6449d64c31771f'
R63_SHA256 = 'f88e95360c0c4a25082e5369e46e960dd84cff735221da8b89c8d152233d4652'
R62_SHA256 = 'd43e06c3ab89078ae2f908575bfdbee2a05e20fda80b530a7fb61b9b851f8f29'
DECK, SEAT = old.DECK, b.PCB_Z                            # 7.27 deck underside, 9.4 board seat

# ------------------------------------------------------------------ 2. guard top arm
OLD_TOP_PATH = r62.TOP_PATH                               # root (11.25, 21.0, 8.7), in to X 11.7 at Y 11.3
NEW_TOP_PATH = [(12.10, 21.0, 8.7), (12.20, 19.4, 4.2), (17.4, 13.4, .9), r62.CROWN_START]
TOP_R = 1.32
ROOT_EMBED_TOP = 8.30                                     # the new root is added up to here, below the latch pass
OLD_ARM_SKIN = 0.15                                       # the old arm is cut this much oversize, so no skin of it stays

# ------------------------------------------------------------------ 2b. right saddle stub
# The mirror of R67's left search box, reaching lower: the right stub hangs down to Z 1.65.
RIGHT_STUB_ZONE = (3.85, 11.5, 2.5, 17.5, 1.0, 6.5)

# ------------------------------------------------------------------ 3. OP1 seat (board frame)
EYELETS = ((-6.25, -1), (11.65, 1))                       # R53 locator stations and sides
# Remove the narrow corner whose first deposited bead floated beside the window.
# Found and fixed by GPT-6.1 Sol.
WINDOW_U = (-4.45, 5.85)                                  # clear the entire thin pocket-wall corner, not just its nominal face
WINDOW_V = (13.20, 23.00)                                 # R53: 14.39 to 21.71
WINDOW_R = 1.0
WINDOW_Z = (6.31, SEAT + .05)                             # R53 depth, through the seat
NOTCH_U, NOTCH_END_V = 3.50, 25.30                        # remove the old pocket/wire-mouth corner; retain the outer board stops
NOTCH_TOP = 12.65                                         # the notch also passes the board's end stop, as in R66
LEAD_IN = 0.70                                            # 45 degree lead-in under the deck edge
POCKET_BOTTOM, POCKET_CLOSE = 6.88, 2.1                   # R53 locator pocket floor; closing radius over its 4 mm width
SEAT_SLAB = (-5.20, 4.90, -8.50, 21.30)                   # board floor filled flat: u0, u1, v0, v1 (the pocket is 5.45 each side)

# ------------------------------------------------------------------ 4. rod grip
GRIP_END_Y = 32.70                                        # R58-R62 carrier rear; the R62 bore is restored up to here
REAR_RING_LEAD = (32.15, 4.00, 4.28)                      # lead-in on the restored rear ring: from Y, radius to radius
GRIP_OVERLAP = 0.02                                       # the restored piece reaches this far into the sleeve wall

# ------------------------------------------------------------------ 5. key deck
STRIP_WINDOW = (19.3, 22.8, 8.6, 10.9)                    # |X| span and Y span of the window between the rows


def carrier():
    body = None
    for _, body in steps():
        pass
    return old.one_piece(body, 'R69 carrier', limit=.05)


def export(path):
    r66.exported(carrier(), path)
    assert len(b.load(path).decompose()) == 1


# ================================================================ carrier
def steps():
    """The carrier after each change, in build order. — Claude Fable 5.2"""
    body = r68_carrier()
    yield 'r68', body
    zone = route_zone()
    body = (body - zone) + (r63_carrier() ^ zone)
    body = (body + seat_fill()) - locator_noses() - backing_rib()
    body += pocket_floor_fill(body)
    body -= connector_window()
    body -= window_lead_in(body)
    yield 'op1_seat', body
    body = (body - old_top_arm()) + new_top_arm()
    yield 'guard_arm', body
    body -= right_stub_cutter(body)
    yield 'right_stub', body
    body += strip_fill()
    yield 'key_deck', body
    body += grip_restore()
    yield 'rod_grip', body
    body = hinge.carrier(body)
    yield 'hinge', body


def main():
    OUT.mkdir(exist_ok=True)
    export(OUT / HOLDER)
    hinge.save_parts()
    for name in (HOLDER, hinge.PADDLE, hinge.LID, hinge.WIRES):
        print('saved', name, _sha(OUT / name), flush=True)


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _checked(path, expected):
    assert _sha(path) == expected, f'{path.parent.parent.name} carrier changed'
    return b.load(path)


@lru_cache(maxsize=1)
def r68_carrier():
    return _checked(R68_CARRIER, R68_SHA256)


@lru_cache(maxsize=1)
def r63_carrier():
    return _checked(R63_CARRIER, R63_SHA256)


@lru_cache(maxsize=1)
def r62_carrier():
    return _checked(R62_CARRIER, R62_SHA256)


# ------------------------------------------------------------------ 2. guard
def crown_bars():
    return b.union([r61.curve([r62.CROWN_START, (x, 9.5, .88), (x, 6.6, .88), r62.CROWN_END], 1.26) for x in (15.1, 22.1, 28.1)])


def old_top_arm():
    """The R62 top arm below the deck, less the crown bars it meets. — Claude Fable 5.2"""
    arm = r61.curve(OLD_TOP_PATH, TOP_R + OLD_ARM_SKIN) ^ b.box(-40, 40, -40, 40, -10, DECK)
    return arm - crown_bars()


def new_top_arm():
    return r61.curve(NEW_TOP_PATH, TOP_R) ^ b.box(-40, 40, -40, 40, -10, ROOT_EMBED_TOP)


def right_stub_cutter(body):
    """Every piece that hangs from the right side face of the front saddle and touches
    nothing else: the right-hand twin of the rib roots R67 removed on the left. It stood
    beside the rod exactly where the white plug comes up. — Claude Fable 5.2"""
    x0, x1, y0, y1, z0, z1 = RIGHT_STUB_ZONE
    zone = b.box(*RIGHT_STUB_ZONE) - r67.ring_keep()
    free = []
    for piece in (body ^ zone).decompose():
        lo, hi = np.reshape(piece.bounding_box(), (2, 3))
        on_saddle = lo[0] < x0 + .01
        elsewhere = hi[0] > x1 - .01 or lo[1] < y0 + .01 or hi[1] > y1 - .01 or lo[2] < z0 + .01 or hi[2] > z1 - .01
        if on_saddle and not elsewhere and piece.volume() > 1e-3:
            free.append(piece)
    assert free and max(p.volume() for p in free) > 20., [round(p.volume(), 2) for p in free]
    plan = b.union(free).project().offset(.3, mf.JoinType.Round)
    return (plan.extrude(z1 - z0).translate((0, 0, z0)) ^ b.box(*RIGHT_STUB_ZONE)) - r67.ring_keep()


# ------------------------------------------------------------------ 3. OP1 seat
def _rounded(u0, u1, v0, v1, r):
    core = mf.CrossSection.square((u1 - u0 - 2 * r, v1 - v0 - 2 * r)).translate((u0 + r, v0 + r))
    return core.offset(r, mf.JoinType.Round, 2.0, 48)


def window_sections():
    """(main window, lead notch) in the board frame. Each is convex. — Claude Fable 5.2"""
    main = _rounded(*WINDOW_U, *WINDOW_V, WINDOW_R)
    # A wide rounded mouth removes the old intersecting-cut horns outside the PCB.
    # The outer end stops and both retainer rails remain. — GPT-6.1 Sol
    notch = _rounded(-NOTCH_U, NOTCH_U, WINDOW_V[1] - 2.0, NOTCH_END_V, 1.0)
    return main, notch


def _prism(section, z0, z1):
    return mf.Manifold.extrude(section, z1 - z0).translate((0, 0, z0))


def connector_window():
    main, notch = window_sections()
    return b.to_world(_prism(main, *WINDOW_Z) + _prism(notch, WINDOW_Z[0], NOTCH_TOP))


def window_lead_in(body):
    """45 degree lead-in round the underside of the window, on free deck edges only. — Claude Fable 5.2"""
    parts = []
    for section in window_sections():
        top = _prism(section, DECK + LEAD_IN - .01, DECK + LEAD_IN)
        wide = _prism(section.offset(LEAD_IN, mf.JoinType.Round, 2.0, 48), DECK - .03, DECK - .02)
        parts.append(mf.Manifold.batch_hull([top, wide]))
    funnel = b.to_world(b.union(parts))
    lo, hi = np.reshape(funnel.bounding_box(), (2, 3))
    below = body ^ b.box(lo[0] - 1, hi[0] + 1, lo[1] - 1, hi[1] + 1, DECK - 1.5, DECK - .05)
    if below.is_empty():
        return funnel
    keep = below.project().offset(.3, mf.JoinType.Round).extrude(2.0).translate((0, 0, DECK - .5))
    return funnel - keep


def socket_holes():
    """The three socket holes with their float and print peaks, as cutters for new material. — Claude Fable 5.2"""
    holes = []
    for v in b.SOCKET_Y:
        x, y = b.board_point(0, v)
        holes.append(base.teardrop(float(x), float(y), b.SOCKET_R + b.FLOAT + .01, 4.0, SEAT + .1))
    return b.union(holes)


def route_zone():
    """R66's window box. It holds everything R66's plug route and R67's lead-in removed;
    outside those cuts R63 and R68 are the same plastic inside it. — Claude Fable 5.2"""
    return b.box(*r66.WINDOW)


def seat_fill():
    """The board floor as one flat slab from the deck underside to the seat. It closes both
    R53 locator pockets; only the socket holes stay open (the window is cut afterwards). — Claude Fable 5.2"""
    u0, u1, v0, v1 = SEAT_SLAB
    # 0.01 mm inside the deck faces, so the slab never lies face on face with them.
    return b.to_world(b.box(u0, u1, v0, v1, DECK + .01, SEAT - .01)) - socket_holes()


def pocket_floor_fill(body):
    """The locator pockets were cut 0.39 mm below the deck underside. Where that left a
    shallow recess in plastic that hangs under the deck, level it; in free air add nothing. — Claude Fable 5.2"""
    low = (POCKET_BOTTOM - .03, DECK + .02)
    gaps = b.union([carrier53.locator(y, side)[0] for y, side in EYELETS])
    plan = gaps.project()
    lo, hi = np.reshape(gaps.bounding_box(), (2, 3))
    around = (body ^ b.box(lo[0] - 3, hi[0] + 3, lo[1] - 3, hi[1] + 3, *low)).project()
    closed = around.offset(POCKET_CLOSE, mf.JoinType.Round, 2.0, 32).offset(-POCKET_CLOSE, mf.JoinType.Round, 2.0, 32)
    return _prism(closed ^ plan.offset(.05, mf.JoinType.Round, 2.0, 16), *low) - socket_holes()


def backing_rib():
    """R53's slanted print backing under the rear locator, hanging below the deck beside the window. — Claude Fable 5.2"""
    a, z = carrier53_rib()
    stick = mf.Manifold.batch_hull([carrier53.puck(a, .48 + .12, .53 + .12, .58 + .2), carrier53.puck(z, .61 + .12, .53 + .12, .65 + .2)])
    return stick ^ b.box(-40, 40, -40, 40, -10, DECK)


def carrier53_rib():
    return (10.43, 10.75, 7.42), (9.02, 6.75, 5.15)       # third entry of carrier53.add_backing


def locator_noses():
    """The two noses stood in the board's eyelets above the seat. — Claude Fable 5.2"""
    return b.union([b.to_world(mf.Manifold.cylinder(2.6, 2.5, 2.5, 64).translate((0, y, SEAT))) for y, _ in EYELETS])


# ------------------------------------------------------------------ 4. rod grip
def grip_restore():
    """R62 material inside the R63 bore, from the front face to GRIP_END_Y.

    The piece reaches GRIP_OVERLAP into the sleeve wall, where R62 and R68 are the same
    plastic, so it fuses instead of meeting the bore face edge to edge.
     — Claude Fable 5.2"""
    radius = old.ROD_R + GRIP_OVERLAP
    bore = old.lay(mf.Manifold.cylinder(GRIP_END_Y + 20., radius, radius, 144), -20.)
    start, r0, r1 = REAR_RING_LEAD
    lead = old.lay(mf.Manifold.cylinder(GRIP_END_Y - start + .01, r0, r1, 144), start)
    return ((r62_carrier() ^ bore) - lead).simplify(.002)


# ------------------------------------------------------------------ 5. key deck
def strip_fill():
    x0, x1, y0, y1 = STRIP_WINDOW
    return b.mirrored(b.box(x0, x1, y0, y1, DECK, float(base.plate_top())))

if __name__ == '__main__':
    main()
