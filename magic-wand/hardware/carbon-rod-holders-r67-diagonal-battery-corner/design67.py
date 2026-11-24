"""R67 key carrier: the exact R66 export with three local subtractions and nothing added.

Assembly frame as in R53-R66: the rod runs along Y through X = Z = 0, +Z is up,
+Y is the top (two-key) end and the rear face Y = BED lies on the print bed.

1. Battery corner. Seen from below, the battery side of the carrier ended in a square
   outboard corner at the bed face: the 1.2 mm roof plate, the end of the outboard wall
   and the spring-root post. A vertical diagonal cut replaces that corner. It runs from
   the outer edge at Y 40.0, where the R66 wall has finished rising into the deck, to
   X -22.6 at the bed face. The spring leaf's free length, its root post ahead of Y 40,
   the pouch-side face of the post and both lips are untouched. The cut's top and
   bottom edges are rounded like the R66 post.

2. Left saddle stubs. R33's crosswise finger guards had three rounded ribs on each side,
   running from the outer rails to the front rod saddle. R60 replaced those guards with
   its rounded beams but removed the old ribs only outboard of |X| 9.3
   (design60.py: `bare -= mirrored(box(9.3, bank, ...)) ^ ribs`). On the left, the rib
   roots were left behind as three diagonal strips hanging from the saddle's side wall,
   ending in air at X -10.8. They carry nothing and every revision since has copied them.
   R67 removes them as far as the saddle face (X -3.85) and the rod ring (radius 5.2).
   The ring, its stem and the current guard are unchanged. On the right, the same station
   holds deck-connected material that shares only 4.8 mm3 with the mirrored stubs; it is
   left alone.

3. OP1 plug entrance. The R66 deck opening is kept, so the three socket holes, the board
   bearing and the end stop are R66's. Its underside edge gets a 45 degree lead-in, so
   the plug, pushed up blind from below, is guided into the hole instead of catching on
   a square edge. The lead-in stops 1.43 mm below the board seat.

Build: load the R66 export (its SHA-256 is checked), subtract the three regions, keep the
single solid and save it. design66 supplies every route, pose and hardware model.
"""
from functools import lru_cache
from hashlib import sha256
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
for folder in ('carbon-rod-holders-r66-three-hole-op1', 'carbon-rod-holders-r64-under-entry',
               'carbon-rod-holders-r63-open-hinge', 'carbon-rod-holders-r62-compact-guard'):
    if str(HARDWARE / folder) not in sys.path:
        sys.path.insert(0, str(HARDWARE / folder))

import design66 as r66  # noqa: E402

old, b = r66.old, r66.b
OUT = HERE / 'exports'
HOLDER = r66.HOLDER
R66_CARRIER = r66.OUT / HOLDER
R66_SHA256 = '0112b7da1e8704eb93e148d889c8f362ae3892bdccc9a2f58bd798de825e8542'

# ------------------------------------------------------------------ 1. battery corner
OUTER_X = old.WALL_FACE - old.WALL          # -24.55, outer face of the battery side
CORNER_START_Y = 40.0                       # on the outer edge; the R66 wall has risen into the deck here
CORNER_BED_X = -22.6                        # where the diagonal meets the bed face
CORNER_EDGE_R = .40                         # rounds the cut's top and bottom edges (R66 post: 0.45)
ROOF_TOP = old.DECK + old.LAND[2]           # 8.47, top of the battery roof plate
POST_BOTTOM = old.LIP_TOP - .01             # 3.16, underside of the spring-root post

# ------------------------------------------------------------------ 2. saddle stubs
# Search box beside the front saddle. Its inner face stops just outside the saddle's
# side face (X -3.80), and the ring keep-out leaves the rod ring itself alone.
STUB_ZONE = (-11.5, -3.85, 2.5, 17.5, 2.0, 6.5)
RING_KEEP_R = 5.2
STUB_PLAN_MARGIN = .30                      # plan margin round the stubs, clear of other members

# ------------------------------------------------------------------ 3. plug lead-in
LEAD_IN = .70                               # extra opening at the deck underside, 45 degrees
LEAD_IN_TOP = old.DECK + LEAD_IN            # 7.97; the opening above is exactly R66's
LEAD_IN_FLOOR = old.DECK - .02              # deck material only


def corner_line():
    p1 = np.array([OUTER_X, CORNER_START_Y])
    p2 = np.array([CORNER_BED_X, old.BED])
    u = (p2 - p1) / np.linalg.norm(p2 - p1)
    n = np.array([-u[1], u[0]])                         # outward: toward -X and the bed face
    return p1, p2, u, n


def _along_line(section, a0, a1):
    """Extrude a (normal offset, Z) section along the corner line from a0 to a1."""
    p1, _, u, n = corner_line()
    solid = mf.Manifold.extrude(section, a1 - a0).translate((0, 0, a0))
    # (a, z, c) -> world: a along the outward normal, z up, c along the line.
    return solid.transform([[n[0], 0, u[0], p1[0]], [n[1], 0, u[1], p1[1]], [0, 1, 0, 0]])


def battery_corner_cutter():
    """Everything outboard of the diagonal, plus rounding strips on its top and bottom edges."""
    p1, p2, u, n = corner_line()
    length = float(np.linalg.norm(p2 - p1))
    a, c = (-.3, length + 2.0)
    region = [p1 + u * a, p1 + u * c, p1 + u * c + n * 6.0, p1 + u * a + n * 6.0]
    z0, z1 = old.LOW - 1.0, ROOF_TOP + 1.0
    cut = b.prism_xy([tuple(map(float, q)) for q in region], z0, z1)
    r = CORNER_EDGE_R
    square = lambda a0, a1, b0, b1: mf.CrossSection.square((a1 - a0, b1 - b0)).translate((a0, b0))
    disk = lambda a, z: mf.CrossSection.circle(r, 48).translate((a, z))
    top = square(-r, .5, ROOF_TOP - r, ROOF_TOP + .5) - disk(-r, ROOF_TOP - r)
    bottom = square(-r, .5, POST_BOTTOM - .5, POST_BOTTOM + r) - disk(-r, POST_BOTTOM + r)
    return b.union([cut, _along_line(top, a, c), _along_line(bottom, a, c)])


# ------------------------------------------------------------------ 2. saddle stubs
def ring_keep():
    return old.lay(mf.Manifold.cylinder(40.0, RING_KEEP_R, RING_KEEP_R, 128), -10.0)


def stub_zone():
    return b.box(*STUB_ZONE) - ring_keep()


def zone_pieces(body):
    """Material in the search box, split into pieces; the stubs are the one free-ended piece."""
    x0, x1, y0, y1, z0, z1 = STUB_ZONE
    rows = []
    for piece in (body ^ stub_zone()).decompose():
        lo, hi = np.reshape(piece.bounding_box(), (2, 3))
        touches = dict(x0=lo[0] < x0 + .01, y0=lo[1] < y0 + .01, y1=hi[1] > y1 - .01, z0=lo[2] < z0 + .01, z1=hi[2] > z1 - .01)
        rows.append(dict(solid=piece, volume=float(piece.volume()), lo=lo, hi=hi, touches=touches,
                         free=not any(touches.values()) and hi[0] > x1 - .01))
    return sorted(rows, key=lambda r: -r['volume'])


@lru_cache(maxsize=1)
def saddle_stub_cutter():
    """Plan outline of the free stubs (grown by STUB_PLAN_MARGIN, never into another member),
    extruded through the search box, minus the rod ring."""
    body = b.load(R66_CARRIER)
    rows = zone_pieces(body)
    stubs = [r for r in rows if r['free'] and r['volume'] > 1.0]
    assert len(stubs) == 1, [(round(r['volume'], 2), r['touches']) for r in rows]
    stub = stubs[0]['solid']
    m = STUB_PLAN_MARGIN
    # Every other member in the box keeps its own bounding box grown by the margin.
    others = [b.box(r['lo'][0] - m, r['hi'][0] + m, r['lo'][1] - m, r['hi'][1] + m, r['lo'][2] - m, r['hi'][2] + m)
              for r in rows if r['solid'] is not stub and r['volume'] > 1e-3]
    plan = stub.project().offset(m, mf.JoinType.Round)
    x0, x1, y0, y1, z0, z1 = STUB_ZONE
    cutter = (plan.extrude(z1 - z0).translate((0, 0, z0)) ^ b.box(*STUB_ZONE)) - ring_keep()
    return cutter - b.union(others) if others else cutter


# ------------------------------------------------------------------ 3. plug lead-in
@lru_cache(maxsize=1)
def plug_lead_in():
    """45 degree chamfer round the underside of the R66 deck opening.

    The R66 opening is the tipped plug's vertical sweep grown by PLUG_GAP, built from
    convex pieces. Each piece, cut to the underside slab, is summed with a cone whose apex
    is up, so at height z the opening grows by min(LEAD_IN, LEAD_IN_TOP - z).
    """
    x0, x1, y0, y1, _, _ = r66.WINDOW
    slab = b.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, old.DECK - .3, LEAD_IN_TOP)
    shape = r66.plug_and_lead('thread')
    lo, hi = r66.pose(shape, r66.tip_pose(r66.THREAD_Z[0])), r66.pose(shape, r66.tip_pose(r66.THREAD_Z[1]))
    g = r66.PLUG_GAP
    grow = b.box(-g, g, -g, g, -g, g)
    ring = [(LEAD_IN * math.cos(t), LEAD_IN * math.sin(t), -LEAD_IN) for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    parts = []
    for p, q in zip(r66._convex(lo), r66._convex(hi)):
        piece = mf.Manifold.batch_hull([p, q]).minkowski_sum(grow) ^ slab
        if piece.is_empty():
            continue
        parts.append(mf.Manifold.batch_hull([piece] + [piece.translate(v) for v in ring]))
    funnel = b.union(parts) ^ b.box(x0, x1, y0, y1, LEAD_IN_FLOOR, LEAD_IN_TOP)
    # Only the deck's own underside edge is chamfered. Members that hang below the deck
    # here (the right finger-guard roots) keep their full joint with it.
    below = r66_carrier() ^ b.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, old.DECK - 1.5, old.DECK - .05)
    if below.is_empty():
        return funnel
    keep = below.project().offset(.3, mf.JoinType.Round).extrude(LEAD_IN_TOP - LEAD_IN_FLOOR + 1).translate((0, 0, LEAD_IN_FLOOR - .5))
    return funnel - keep


# ================================================================ carrier
@lru_cache(maxsize=1)
def _r66_checked():
    data = R66_CARRIER.read_bytes()
    assert sha256(data).hexdigest() == R66_SHA256, 'R66 carrier changed'
    return True


def r66_carrier():
    _r66_checked()
    return b.load(R66_CARRIER)



def carrier():
    body = r66_carrier()
    body -= battery_corner_cutter()
    body -= saddle_stub_cutter()
    body -= plug_lead_in()
    return old.one_piece(body, 'R67 carrier', limit=.02)


def main():
    OUT.mkdir(exist_ok=True)
    body = carrier()
    b.save_closed(OUT / HOLDER, body)
    assert len(b.load(OUT / HOLDER).decompose()) == 1
    print('saved', OUT / HOLDER, sha256((OUT / HOLDER).read_bytes()).hexdigest(), flush=True)


if __name__ == '__main__':
    main()
