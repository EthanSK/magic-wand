"""R70 key carrier: the fitted R69 carrier, shorter, with the right upper key nearer the
lower row and the lower edge of both key banks rounded.

Assembly frame as in R53-R69: the rod runs along Y through X = Z = 0, +Z is up,
+Y is the top (two-key) end and the rear face Y = BED lies on the print bed.

1. Right upper key. The whole right bank above the deck, from the strip between the two
   rows to the rear, moves KEY_SHIFT toward the lower row: key seat, socket floor, latch
   pass and rear shoulder together, so every inherited key space moves with it. The
   left upper key does not move: its prewired socket slides in under the deck past the
   left guard, and that path meets the guard after 0.2 mm (checks70 measures it).

2. Short holder. R69 ended 11.35 mm behind the pin line. R70 ends BED - AXIS = 4.15 mm
   behind it. Each bearing block is a plain prism standing on the new rear face, the old
   buttresses, rear plateau and tapered rear socket are gone, and the bore gets a short
   mouth at the new face. The two rod rings in front of it are R69's, untouched.

3. Battery. The pouch keeps its place against the deck; 12.45 mm of it now stands behind
   the holder instead of 5.25. The side spring is rebuilt on the new rear face: shorter
   lever, lower leaf of about the same stiffness, same preload, shoe moved forward so it
   still bears near the middle of the held length.

4. Round edges. The lower edge of both key banks was a square arris with a small foot.
   It is now a quarter round of EDGE_R all the way along the front, the outer corners,
   both outer sides and the rear shoulders. The upper edge gets a smaller round. The
   guard rails keep their full tubes where they enter the deck. The centre, between the
   banks, already had its round. The rounds run along the edges into the rear face; the rim of
   the rear print-face rim uses a smaller round to retain a broad first layer.

Build: load the printed R69 export (SHA-256 checked) and apply the changes. Nothing here
is a claim of physical fit.
 — Claude Fable 5.2"""
from functools import lru_cache
from hashlib import sha256
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
for folder in ('carbon-rod-holders-r69-snug-rod-clean-op1', 'carbon-rod-holders-r68-pre-taper-battery-rail',
               'carbon-rod-holders-r67-diagonal-battery-corner', 'carbon-rod-holders-r66-three-hole-op1',
               'carbon-rod-holders-r64-under-entry', 'carbon-rod-holders-r63-open-hinge',
               'carbon-rod-holders-r62-compact-guard', 'carbon-rod-holders-r53-guided-op1'):
    if str(HARDWARE / folder) not in sys.path:
        sys.path.insert(0, str(HARDWARE / folder))

import design69 as r69  # noqa: E402
import hinge70 as hinge  # noqa: E402
import design64 as r64  # noqa: E402

r66, old, b = r69.r66, r69.old, r69.b                     # old is design63, b is build53
r62, r61, base = r69.r62, r69.r61, r69.base
OUT = HERE / 'exports'
HOLDER = r69.HOLDER
R69_CARRIER = r69.OUT / HOLDER
R69_SHA256 = '1363f07f6ea16b3bcf4b362e98b150e2af38128fc1312846442d57c3df3b2ee7'   # the printed, fitted R69 carrier
DECK, SEAT = old.DECK, b.PCB_Z                            # 7.27 deck underside, 9.4 board seat
PLATE_TOP = float(base.plate_top())                       # 11.12, top of the key plate (R16)
BED, R69_BED = hinge.BED, old.BED                         # 36.45 and 43.65
AXIS, KEEPER_Z = hinge.AXIS, hinge.KEEPER_Z

# ------------------------------------------------------------------ 1. right upper key
KEY_SHIFT = 2.00                                          # toward the lower row
BANK_X = 12.70                                            # the right key bank starts here (R16 seam); the centre does not move
BLOCK_FROM_Y = 12.20                                      # R69 station where the moved block starts, in the plain strip between the rows
SEAM = 0.20                                               # the moved block reaches this far into the strip that stays
TIE_KEEP = (13.60, 10.30, 12.60, PLATE_TOP - .05, 12.20)  # R53's small rib to the retainer rail backing stays: X to, Y span, Z span
WINDOW_ZONE = (14.45, 17.20, 9.47)                        # the fixed OP1 connector window reaches into the bank: X to, Y to, Z to
ROOT_ZONE = (13.75, 19.15, 22.45, 8.32)                   # the right guard's top arm is rooted in the bank's underside: X to, Y span, Z to
TROUGH = (11.52, 27.90, 35.70, 10.25)                     # pin approach troughs refilled before the new one is cut: |X| from, Y span, floor

# ------------------------------------------------------------------ 2. short holder
MOUTH = (0.90, 0.33)                                      # rear bore mouth: length, extra radius at the bed face

# ------------------------------------------------------------------ 3. battery
ROOT_LENGTH = 2.00                                        # leaf root on the new rear face (R63: 5.5)
LEAF_Z = (4.07, 6.43)                                     # R63: 3.74 to 6.77
SHOE_Y = (24.40, 28.00)                                   # R63: 26.6 to 32.1
SHOE_Z = (4.10, 6.40)
LEAF_T = old.LEAF_X[1] - old.LEAF_X[0]                    # 1.04

# ------------------------------------------------------------------ 4. round edges
EDGE_R = 1.50                                             # lower edge of the key banks
TOP_R = 0.90                                              # upper edge of the key banks
REAR_R = 0.60                                             # small rear round: first-layer contact remains, 0.2 mm layer steps stay printable
BANK_FROM = 12.72                                         # |X| where the key banks start
OPEN_R = 1.00                                             # outline features narrower than twice this are not followed
RAIL_SKIN = 0.03                                          # the guard rails are kept this much oversize
WALL_SKIN = 0.30                                          # anything else that hangs under the deck edge is kept with this margin
HANGING_MIN = 2.0                                         # mm3 in the 0.8 mm under the deck; smaller scraps are not kept
SCRAP_DEPTH = 2.0                                         # scraps hanging this far under the rounded edge go with it
OUTSIDE = 0.30                                            # anything this far beyond the outline goes too
CREST = ((-25.40, -15.05), 0.40)                          # R63's sloped front rim before the turned key: X span, crest radius
ARC = 64                                                  # facets round a full circle


def carrier():
    body = None
    for _, body in steps():
        pass
    return old.one_piece(body, 'R70 carrier', limit=.05)


def export(path):
    """Save, reload and keep the one solid until the file reloads as exactly that solid.
    Rounding to the STL's 32-bit coordinates can pinch off zero-volume flakes; each pass
    drops them (under 0.001 mm3 in all) and the second or third pass is stable. — Claude Fable 5.2"""
    b.save_closed(path, carrier())
    for _ in range(6):
        back = b.load(path)
        if len(back.decompose()) == 1:
            return back
        b.save_closed(path, old.one_piece(back, 'exported R70 carrier', limit=.001))
    raise ValueError('the R70 carrier does not reload as one solid')


def steps():
    """The carrier after each change, in build order. — Claude Fable 5.2"""
    body = r69_carrier()
    yield 'r69', body
    body = move_right_key(body)
    yield 'right_key', body
    body = shorten(body)
    yield 'short_holder', body
    body = _tidy((body - old_spring()) + spring())
    yield 'battery', body
    body = _tidy(body - edge_cutter(body) - crest_cutter(body), limit=.01)
    yield 'bank_edges', body
    body = _tidy(body - rear_edge_cutter(body), limit=.01)
    yield 'edges', body


def main():
    OUT.mkdir(exist_ok=True)
    export(OUT / HOLDER)
    hinge.save_parts()
    for name in (HOLDER, hinge.PADDLE, hinge.POST_BAR, hinge.WIRES, hinge.LID):
        print('saved', name, _sha(OUT / name), flush=True)


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def r69_carrier():
    assert _sha(R69_CARRIER) == R69_SHA256, 'the R69 carrier changed'
    return b.load(R69_CARRIER)


def _snap(value):
    """The value as the STL stores it, so a cut plane lies exactly on an existing face."""
    return float(np.float32(value))


# ------------------------------------------------------------------ 1. right upper key
def bank_zone(from_y):
    return b.box(_snap(BANK_X), 60., from_y, 80., _snap(DECK), 60.)


def window_zone(shift=0.):
    """Where the fixed OP1 connector window and its lead-in enter the right bank under the key plate."""
    x1, y1, z1 = WINDOW_ZONE
    y0 = BLOCK_FROM_Y - KEY_SHIFT + SEAM
    return b.box(_snap(BANK_X), x1, y0 + shift, y1 + shift, _snap(DECK), z1)


def root_zone():
    x1, y0, y1, z1 = ROOT_ZONE
    return b.box(_snap(BANK_X), x1, y0, y1, _snap(DECK), z1)


def root_stub():
    """R69's guard top arm, a little oversize, where it stands in the deck."""
    return r61.curve(r69.NEW_TOP_PATH, r69.TOP_R + .02) ^ b.box(-40., 40., -40., 40., DECK - .5, r69.ROOT_EMBED_TOP + .02)


def window_reach():
    """R69's connector window with the reach of its under-deck lead-in: air that belongs to the
    OP1 board and so does not move with the key. — Claude Fable 5.2"""
    plan = r69.connector_window().project()
    main = plan.offset(.02, mf.JoinType.Round).extrude(4.).translate((0, 0, 6.))
    lead = plan.offset(r69.LEAD_IN + .05, mf.JoinType.Round).extrude(r69.LEAD_IN + .10).translate((0, 0, DECK - .05))
    return main + lead


@lru_cache(maxsize=1)
def key4_cutters():
    """Every upper-right key cutter of the R63 build (switch, socket, clip relief, loading
    routes), at the R70 place. — Claude Fable 5.2"""
    d44 = old.k.h.d
    working = d44.geometry()[1]
    shapes = []
    for name, value in d44.socket_print_cutters(working).items():
        if name.startswith('key_4_'):
            here = old.placed(value, name)
            shapes += list(old.c.poses(here)) if hasattr(here, 'offsets') else [here]
    return b.union(shapes).translate((0, -KEY_SHIFT, 0))


def trough_fill(body):
    """Plate put back in the old pin approach troughs (R64's, R69's and, on the right, both
    again 2 mm forward). The outline is the body's own, 0.07 mm under the trough floors. — Claude Fable 5.2"""
    x0, y0, y1, floor = TROUGH
    zone = b.mirrored(b.box(x0, 60., y0, y1, floor - .05, floor + .01))
    plan = (body ^ zone).project().offset(-.01, mf.JoinType.Round)
    return plan.extrude(PLATE_TOP - .01 - floor).translate((0, 0, floor))


def move_right_key(body):
    """The bank above the deck moves as one block. Every cut plane is shared by the piece
    that stays and the piece that moves, so they meet face on face exactly or overlap by SEAM.

    Three things inside the bank do not belong to the key and stay where they are: the end
    of R53's small rib on the plate, the corner of the OP1 connector window and the root of
    the right guard's top arm. In the window's and the root's zones the R69 plastic is kept
    and only the key's own air is moved into it.
     — Claude Fable 5.2"""
    tx, ty0, ty1, tz0, tz1 = TIE_KEEP
    keep = b.box(_snap(BANK_X), tx, ty0, ty1, tz0, tz1)
    zone, root = window_zone(), root_zone()
    block = (body ^ bank_zone(BLOCK_FROM_Y)).translate((0, -KEY_SHIFT, 0)) - keep - zone - root
    block -= (root_stub() ^ root).translate((0, -KEY_SHIFT, 0)) ^ key4_cutters()      # the root's copy that rode forward into key air
    key_air = ((window_zone(KEY_SHIFT) - body) - window_reach()).translate((0, -KEY_SHIFT, 0))
    fixed = (((body ^ zone) - key_air) + (body ^ root)) - key4_cutters()
    out = (body - (bank_zone(BLOCK_FROM_Y - KEY_SHIFT + SEAM) - keep)) + block + fixed
    # R62's latch pass crossed the seam: its part in the centre is filled and cut again 2 mm forward.
    x0, x1, y0, y1, z0, z1 = old.CLIP_CLEARANCE
    out += b.box(x0 - .02, BANK_X + .02, y1 - KEY_SHIFT, y1 + .02, z0 - .02, PLATE_TOP - .01)
    return _tidy(out - b.box(x0, x1, y0 - KEY_SHIFT, y1 - KEY_SHIFT, z0, z1))


def _tidy(body, limit=1e-3):
    """Drop the flakes exact face-on-face cuts can leave: together under `limit` mm3."""
    pieces = body.decompose()
    loose = [p for p in pieces if abs(p.volume()) < limit]
    assert sum(abs(p.volume()) for p in loose) < limit, [p.volume() for p in loose]
    kept = [p for p in pieces if abs(p.volume()) >= limit]
    return kept[0] if len(kept) == 1 else mf.Manifold.compose(kept)


# ------------------------------------------------------------------ 2. short holder
def rear_mouth():
    length, wider = MOUTH
    return old.lay(mf.Manifold.cylinder(length + .1, old.ROD_R, old.ROD_R + wider * (length + .1) / length, 144), BED - length)


def shorten(body):
    body = body ^ b.box(-80., 80., -80., BED, -80., 80.)
    body = (body + trough_fill(body)) - hinge.cheek_bands()
    body -= b.box(-hinge.INNER, hinge.INNER, AXIS - 4.65, BED + 1., KEEPER_Z - hinge.BARREL_R - .45, 32.)
    return ((body - hinge.approach()) + hinge.cheeks()) - rear_mouth()


# ------------------------------------------------------------------ 3. battery
def old_spring():
    """R63's leaf and shoe, slightly oversize. Their root was behind the new rear face. — Claude Fable 5.2"""
    zb, skin = old.PACK_Z[0], .04
    leaf = b.box(old.LEAF_X[0] - skin, old.LEAF_X[1] + skin, old.PACK_Y0 + 2.0 - skin, R69_BED + 1., zb + .42 - skin, zb + old.PACK[2] - .45 + skin)
    shoe = b.box(old.LEAF_X[1] - .2, old.PACK_X[0] + old.SHOE + skin, old.PACK_Y0 + 4.7 - skin, old.PACK_Y0 + 10.2 + skin,
                 zb + .45 - skin, zb + old.PACK[2] - .65 + skin)
    return leaf + shoe


def spring():
    """Free-ended side leaf rooted on the new rear face. Only its rounded shoe touches the pouch. — Claude Fable 5.2"""
    x0, x1 = old.LEAF_X
    root = b.box(old.WALL_FACE - .01, old.PACK_X[0] - .38, BED - ROOT_LENGTH, BED, old.LIP_TOP - .01, DECK + .3)
    leaf = r61.soft(x0, x1, old.PACK_Y0 + 2.0, BED - .01, LEAF_Z[0], LEAF_Z[1], .35)
    shoe = r61.soft(x1 - .2, old.PACK_X[0] + old.SHOE, SHOE_Y[0], SHOE_Y[1], SHOE_Z[0], SHOE_Z[1], .46)
    return root + leaf + shoe


def spring_numbers():
    """Lever, section and relative stiffness of the leaf, R63/R69 beside R70 (same thickness). — Claude Fable 5.2"""
    zb = old.PACK_Z[0]
    before = dict(lever_mm=round((R69_BED - 5.5) - (old.PACK_Y0 + 7.45), 2), leaf_height_mm=round(old.PACK[2] - .87, 2))
    after = dict(lever_mm=round((BED - ROOT_LENGTH) - sum(SHOE_Y) / 2, 2), leaf_height_mm=round(LEAF_Z[1] - LEAF_Z[0], 2))
    stiff = lambda row: row['leaf_height_mm'] / row['lever_mm'] ** 3
    return dict(r69=before, r70=after, leaf_thickness_mm=round(LEAF_T, 2), preload_mm=old.SHOE,
                stiffness_r70_over_r69=round(stiff(after) / stiff(before), 3),
                pouch_behind_the_rear_face_mm=dict(r69=round(old.PACK_Y0 + old.PACK[1] - R69_BED, 2), r70=round(old.PACK_Y0 + old.PACK[1] - BED, 2)),
                pouch_inside_the_rails_mm=dict(r69=round(R69_BED - old.PACK_Y0, 2), r70=round(BED - old.PACK_Y0, 2)))


# ------------------------------------------------------------------ 4. round edges
def plate_plan(body):
    """Plan outline of the key plate without holes, carried straight on past the rear face
    so that face itself is never rounded. — Claude Fable 5.2"""
    slab = body ^ b.box(-80., 80., -80., 80., DECK + .05, PLATE_TOP - .05)
    filled = mf.CrossSection([ring for ring in slab.project().to_polygons() if _area(ring) > 0])
    band = filled ^ mf.CrossSection.square((200., .2)).translate((-100., BED - .25))
    pieces = [mf.CrossSection.batch_hull([piece, piece.translate((0., 6.))]) for piece in band.decompose()]
    return filled + mf.CrossSection.batch_boolean(pieces, mf.OpType.Add)


def bank_outline(plan):
    """The outline the rounds follow: the plan with every convex corner sharper than OPEN_R
    rounded to OPEN_R, which also drops features narrower than twice that. — Claude Fable 5.2"""
    return plan.offset(-OPEN_R, mf.JoinType.Round, 2.0, ARC).offset(OPEN_R, mf.JoinType.Round, 2.0, ARC)


def _area(ring):
    ring = np.asarray(ring, float)
    x, y = ring[:, 0], ring[:, 1]
    return .5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _rounded_core(outline, radius, level, direction, beyond=.1):
    """Everything within `radius` of the outline inset by `radius`, at one height: the plate
    with a full quarter round along its edge. direction +1 rounds a lower edge. — Claude Fable 5.2"""
    inset = outline.offset(-radius, mf.JoinType.Round, 2.0, ARC)
    centre = level + direction * radius
    ball = mf.Manifold.sphere(radius, ARC)
    low, high = (level - beyond, centre + .1) if direction > 0 else (centre - .1, level + beyond)
    pieces = [inset.extrude(high - low).translate((0, 0, low))]
    for ring in inset.to_polygons():
        ring = np.asarray(ring, float)
        for a, c in zip(ring, np.roll(ring, -1, axis=0)):
            if np.hypot(*(c - a)) < 1e-6:
                continue
            pieces.append(mf.Manifold.batch_hull([ball.translate((float(a[0]), float(a[1]), centre)),
                                                  ball.translate((float(c[0]), float(c[1]), centre))]))
    return mf.Manifold.batch_boolean(pieces, mf.OpType.Add)


def guard_rails():
    """The four lower guard rails where they enter the deck, as R64 built them. — Claude Fable 5.2"""
    right = [r61.curve(r64.smooth_return(x), 1.35 + RAIL_SKIN) for x in (14.2, 28.3)]
    left = [r61.curve(r64.smooth_return(x), 1.35 + RAIL_SKIN).mirror((1, 0, 0)) for x in (14.2, old.LEFT_RAIL_X)]
    return b.union(right + left)


def hanging_keep(body):
    """Walls and blocks that hang from the deck right at its edge (the battery rail): the
    deck above them is left square, so the round never undercuts their joint. — Claude Fable 5.2"""
    below = (body ^ b.box(-80., 80., -80., 80., DECK - .9, DECK - .08)) - guard_rails()
    walls = [piece for piece in below.decompose() if piece.volume() > HANGING_MIN]
    plan = b.union(walls).project().offset(WALL_SKIN, mf.JoinType.Round, 2.0, 32)
    return plan.extrude(PLATE_TOP - DECK + SCRAP_DEPTH + 2.).translate((0, 0, DECK - SCRAP_DEPTH - 1.))


def standing_keep(body):
    """Ribs that stand on the key plate at its edge (the retainer rail backings beside the
    centre): the plate edge under them is left as it was. — Claude Fable 5.2"""
    above = body ^ b.box(-80., 80., -80., 80., PLATE_TOP + .03, PLATE_TOP + .60)
    plan = above.project().offset(WALL_SKIN, mf.JoinType.Round, 2.0, 32)
    return plan.extrude(PLATE_TOP - DECK + SCRAP_DEPTH + 2.).translate((0, 0, DECK - SCRAP_DEPTH - 1.))


def bank_zones():
    return b.mirrored(b.box(BANK_FROM, 80., -80., BED + 10., -20., 40.))


def edge_cutter(body):
    """What the rounds remove from the two key banks.

    lower: outside a quarter round of EDGE_R on the deck's lower edge, and any scrap that
           hangs within SCRAP_DEPTH under that edge (remains of R63's root gusset);
    upper: outside a quarter round of TOP_R on the plate's upper edge;
    tips:  everything up to OUTSIDE beyond the outline, over the whole plate height: the
           corner tips OPEN_R rounds off in plan (the ends of the left socket lip), the two
           ends of R63's socket pad that stood 0.2 mm proud of the left side, and the
           hair-thin skins a polygon outline leaves along the true corner arcs.
    Guard rails, hanging walls and standing ribs are not cut. — Claude Fable 5.2"""
    outline = bank_outline(plate_plan(body))
    outer = outline.offset(OUTSIDE, mf.JoinType.Round, 2.0, ARC)
    floor = DECK - SCRAP_DEPTH
    lower = outer.extrude(EDGE_R + SCRAP_DEPTH).translate((0, 0, floor)) - _rounded_core(outline, EDGE_R, DECK, 1, SCRAP_DEPTH + .1)
    upper = outer.extrude(TOP_R + .3).translate((0, 0, PLATE_TOP - TOP_R)) - _rounded_core(outline, TOP_R, PLATE_TOP, -1, .4)
    tips = (outer - outline).extrude(PLATE_TOP + .3 - floor).translate((0, 0, floor))
    rear = b.box(-80., 80., -80., BED, -80., 80.)
    cut = (((lower + tips) - hanging_keep(body)) + ((upper + tips) - standing_keep(body))) ^ bank_zones() ^ rear
    return cut - guard_rails()


def crest_cutter(body):
    """R63 left the front rim before the turned key as a 45 degree wedge with a knife crest.
    The crest gets a small round. The front face is read from the body. — Claude Fable 5.2"""
    (x0, x1), radius = CREST
    (_, _), _, y_grow, floor = old.FRONT_RIM
    front = float((body ^ b.box(x0, x1, -12., -8., floor + .2, PLATE_TOP)).bounding_box()[1])
    crest = floor + (y_grow - front)                      # the slope meets the front face here
    reach = radius / math.tan(math.radians(22.5))
    slope = reach * math.sin(math.radians(45))
    tip = b.prism_yz([(front - .05, crest + .05), (front - .05, crest - reach), (front + slope, crest - slope)], x0 + .01, x1 - .01)
    rod = mf.Manifold.cylinder(x1 - x0 + .2, radius, radius, ARC).rotate((0, 90, 0)).translate((x0 - .1, front + radius, crest - reach))
    return tip - rod


def rear_edge_cutter(body):
    """Round the exposed bank rims on the rear print face, without cutting loaded roots.

    A 0.6 mm radius gives a broad first-layer section 0.1 mm into the face and
    a smaller second-layer step than the 0.42 mm bead width. The native slice
    still has to demonstrate attachment and anchored starts. Guard, battery-wall
    and standing-rib roots retain their complete sections.
    Found by Codex and Claude Opus 5.5. Fixed by GPT-6.1 Sol.
    """
    r = REAR_R
    lower = b.box(-80., 80., BED-r, BED+.05, DECK-.05, DECK+r)
    upper = b.box(-80., 80., BED-r, BED+.05, PLATE_TOP-r, PLATE_TOP+.05)
    cylinder = lambda z: mf.Manifold.cylinder(160., r, r, ARC).rotate((0,90,0)).translate((-80., BED-r, z))
    cut = ((lower-cylinder(DECK+r))-hanging_keep(body)) + ((upper-cylinder(PLATE_TOP-r))-standing_keep(body))
    return (cut ^ bank_zones()) - guard_rails()


if __name__ == '__main__':
    main()
