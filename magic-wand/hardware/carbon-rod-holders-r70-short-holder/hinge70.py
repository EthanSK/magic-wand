"""R70 click-side parts: the fitted R69 hinge with stronger arm-to-barrel joints, the
bearing blocks that stand on the new rear face, and a touch-board post bar that grips.

Assembly frame as in R53-R69: the rod runs along Y through X = Z = 0, +Z is up. The R69
pin line, barrel, journals, hook legs, retainer and lead route are unchanged.

Paddle. Each side beam met the barrel through a post 1.5 mm long. A gusset now fills the
corner between each beam's underside and the front of the barrel, over the beam's width,
and the left post flares to the barrel behind as well as in front. The right post keeps
its plain rear face, where the three leads turn. Nothing is added inside the bearing
blocks, under the plug or in the lead lane.

Bearing blocks. R69's blocks grew from 45 degree buttresses because the rear face was
7 mm behind them. R70 ends the holder 4.15 mm behind the pin line, so each block is a plain
prism standing on the bed and the buttresses are gone.

Post bar. The two posts were 2.25 x 2.52 mm in 3 mm nominal board holes, so the touch
board could shift up to 0.75 mm. Each post now carries two slim crush ribs on its upper
flanks, inside the board thickness only. With the post's own lower edge they make three
contacts. Nozzle-width flat crests taper toward the board-entry end: a 3.0 mm nominal
hole is the snug-fit target; printed ribs are smaller than the CAD tips. They pass the paddle's existing
post holes, and the neck, head and bar are R57's, so the existing clips fit. The hole
size is the maker's nominal figure, not a measurement. — Claude Fable 5.2; GPT-6.1 Sol
"""
from functools import lru_cache
from hashlib import sha256
import math
from shutil import copyfile
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
for folder in ('carbon-rod-holders-r69-snug-rod-clean-op1', 'carbon-rod-holders-r64-under-entry', 'carbon-rod-holders-r63-open-hinge'):
    if str(HARDWARE / folder) not in sys.path:
        sys.path.insert(0, str(HARDWARE / folder))
import hinge69 as h69  # noqa: E402

previous, b, m, r61, h64 = h69.previous, h69.b, h69.m, h69.r61, h69.h64
OUT = HERE / 'exports'
PADDLE, LID, WIRES, POST_BAR = h69.PADDLE, h69.LID, h69.WIRES, 'DFR_Post_Bar-assembly.stl'
R69_LID = h69.OUT / LID                                   # the fitted retainer: R70 carries the same file, byte for byte
R69_LID_SHA256 = 'e3a4a954badc22404c600566af25ed2fe986c4a15b99349bdabc408858194422'
R57_POST_BAR = r61.prior.old.n.R57 / 'exports' / POST_BAR

# ------------------------------------------------------------------ hinge (R69 values)
AXIS, KEEPER_Z, PIVOT, MOVE = h69.AXIS, h69.KEEPER_Z, h69.PIVOT, h69.MOVE
BARREL_R, JOURNAL_R, JOURNAL_OUT = h69.BARREL_R, h69.JOURNAL_R, h69.JOURNAL_OUT
RADIAL_GAP, AXIAL_GAP, INNER, OUTER, TOP, REAR = h69.RADIAL_GAP, h69.AXIAL_GAP, h69.INNER, h69.OUTER, h69.TOP, h69.REAR
BED = AXIS + 4.15                # 36.45: R69's 0.2 mm layer phase, with 1.0 mm behind the open bearings.
SOCKET_REAR_WALL = BED - (AXIS + JOURNAL_R + RADIAL_GAP)   # 1.0 mm behind each open bearing

# ------------------------------------------------------------------ arm-to-barrel joints
GUSSET_X = (4.65, 6.80)          # the beams' width at the barrel
GUSSET_FROM_Y = 27.90            # 0.25 mm behind the front wall of the barrel nest

# ------------------------------------------------------------------ touch-board posts
BOARD_HOLE_NOMINAL = 3.0         # DFR0030: "3 mm" mounting holes, no tolerance published
RIB_DEG = 40.0                   # each rib's angle from the post's upper edge
RIB_LAND_X = (1.27, 1.08)        # outer corner at the seat and board top, inside the existing paddle passage
RIB_LAND_Y = (1.38, 1.12)
RIB_LAND_WIDTH = .42             # a real printable crest, rather than a vanishing triangle tip
RIB_BASE = 0.90                  # rib root buried in the unchanged post
RIB_ROOT_RADIUS = 0.95           # inside the post, so the rib is fused to it
POST_EDGE_Y = -1.26              # the post's lower edge (assembly datum; R70 prints the bar upright)


rotate, pin, clip, disc = h69.rotate, h69.pin, h69.clip, h69.disc
wire_paths, wired_lead, rear_clip_slot = h69.wire_paths, h69.wired_lead, h69.rear_clip_slot


def _beam(sign):
    left = mf.Manifold.batch_hull([b.box(-10.6, -8.6, 19.65, 20.05, 15.35, b.SEAT_Z),
                                   b.box(-6.80, -4.65, AXIS + h69.POST_Y[0], AXIS + h69.POST_Y[1], KEEPER_Z + .4, b.SEAT_Z)])
    return left if sign < 0 else left.mirror((1, 0, 0))


def gusset(sign):
    """Fills the corner between one beam's underside and the front of the barrel."""
    x0, x1 = sorted((sign * GUSSET_X[0], sign * GUSSET_X[1]))
    start = _beam(sign) ^ b.box(-12, 12, GUSSET_FROM_Y, GUSSET_FROM_Y + .30, 0, 40)
    drum = mf.Manifold.cylinder(x1 - x0, BARREL_R, BARREL_R, 96).rotate((0, 90, 0)).translate((x0, AXIS, KEEPER_Z))
    return mf.Manifold.batch_hull([start, drum]) ^ b.box(-12, 12, GUSSET_FROM_Y, AXIS + BARREL_R, 0, b.SEAT_Z)


def left_rear_flare():
    """The left post's flare to the barrel, behind the post. No lead passes there."""
    x0, x1 = h69.LEFT_POST_X
    y0, y1 = AXIS + h69.POST_Y[0], AXIS + h69.POST_Y[1]
    strip = b.box(x0, x1, y0, y1, b.SEAT_Z - .02, b.SEAT_Z)
    drum = mf.Manifold.cylinder(x1 - x0, BARREL_R, BARREL_R, 96).rotate((0, 90, 0)).translate((x0, AXIS, KEEPER_Z))
    return mf.Manifold.batch_hull([strip, drum]) ^ b.box(x0, x1, y1 - .01, AXIS + BARREL_R, KEEPER_Z, b.SEAT_Z)


def joints():
    added = gusset(-1) + gusset(1) + left_rear_flare()
    relief = b.mirrored(b.box(m.BARREL_X - .08, 12., AXIS - 4.65, REAR + .1, 8., h69.CHEEK_CLEAR_Z))
    return added - relief


def paddle():
    body = h69.paddle() + joints()
    bore = m.hole(AXIS, KEEPER_Z, m.BARREL_HOLE_R, (0, -1), -JOURNAL_OUT, JOURNAL_OUT)
    return body - bore - rear_clip_slot()


def joint_throat(shape):
    """Plastic joining the beams to the barrel: the section 0.15 mm outside the barrel
    radius, in front of and above the pin line, within each beam's reach (mm2 per side)."""
    shell = (disc(BARREL_R + .25, -7., 7.) - disc(BARREL_R + .05, -7.1, 7.1)) ^ b.box(-7, 7, AXIS - 4, AXIS + 4, KEEPER_Z - .5, 30)
    out = {}
    for side, sign in (('left', -1), ('right', 1)):
        x0, x1 = sorted((sign * 2.9, sign * 7.0))
        out[side] = round(float(((shape ^ shell) ^ b.box(x0, x1, 0, 60, 0, 40)).volume()) / .20, 2)
    return out


# ------------------------------------------------------------------ touch-board post bar
def _rib(sign, z0, z1):
    """One crush rib with a nozzle-width land tapering into the board-entry end.

    A triangular apex disappeared in the native slice. The short flat crest
    retains a printable contour inside the fitted paddle slot. Print upright.
    Found by Claude Opus 5.5. Fixed by GPT-6.1 Sol.
    — Claude Fable 5.2; GPT-6.1 Sol
    """
    a = math.radians(sign * RIB_DEG)
    out, across = np.array([math.sin(a), math.cos(a)]), np.array([math.cos(a), -math.sin(a)])
    ends = []
    for z, x, y in ((z0, RIB_LAND_X[0], RIB_LAND_Y[0]), (z1-.02, RIB_LAND_X[1], RIB_LAND_Y[1])):
        ring = [out * RIB_ROOT_RADIUS - across * RIB_BASE / 2,
                out * RIB_ROOT_RADIUS + across * RIB_BASE / 2,
                np.array([sign*x,y]), np.array([sign*(x-RIB_LAND_WIDTH),y])]
        # Convex hull gives the same outline on either mirrored flank.
        section=mf.CrossSection.hull_points(np.asarray(ring))
        ends.append(mf.Manifold.extrude(section, .02).translate((0, 0, z)))
    return mf.Manifold.batch_hull(ends)


def post():
    """The R57 post with two crush ribs inside the board thickness."""
    r = m.chain()
    seat, top = b.SEAT_Z, b.BOARD_TOP
    return m.post(r) + _rib(-1, seat, top) + _rib(1, seat, top)


def post_bar():
    r = m.chain()
    plain = m.post(r)
    posts = b.union(post().translate((s * b.HOLE_X, b.HOLE_Y, 0)) for s in (-1, 1))
    bounds = plain.bounding_box()
    base = b.box(-b.HOLE_X - 1.3, b.HOLE_X + 1.3, b.HOLE_Y + bounds[1], b.HOLE_Y + bounds[4], b.PLATE_Z - 1.8, b.PLATE_Z)
    return posts + base


def post_fit(hole_d):
    """Where a board hole of this diameter sits on one post and how hard the ribs are pressed.

    The hole rests on the post's lower edge. At each height in the board the rib tips are
    compared with the hole there; positive means the rib must give by that much.
    """
    r = hole_d / 2
    centre_y = POST_EDGE_Y + r                            # the hole sits down on the lower edge
    rows = []
    for z_fraction in (0.0, .5, 1.0):
        x=RIB_LAND_X[0]+(RIB_LAND_X[1]-RIB_LAND_X[0])*z_fraction
        y=RIB_LAND_Y[0]+(RIB_LAND_Y[1]-RIB_LAND_Y[0])*z_fraction
        reach = math.hypot(x, y - centre_y)
        rows.append(round(reach - r, 3))
    side = math.sqrt(max(r * r - centre_y ** 2, 0)) - m.chain().POST_W / 2
    return dict(hole_mm=hole_d, rib_interference_at_seat_mid_top_mm=rows, r57_play_across_mm=round(hole_d - m.chain().POST_W, 3),
                r57_play_along_mm=round(hole_d - m.chain().POST_L, 3), plain_post_side_gap_mm=round(side, 3))


# ------------------------------------------------------------------ carrier side of the hinge
def cheek_profile():
    """(Y, Z) outline of one bearing block: it stands on the rear face, which is the print bed."""
    bottom = 8.65
    return [(AXIS - 4.40, bottom), (AXIS - 4.40, TOP - .85), (AXIS - 3.55, TOP), (BED, TOP), (BED, bottom)]


def cheeks():
    cheek = b.prism_yz(cheek_profile(), INNER, OUTER)
    section = previous.bore_section().translate((AXIS - previous.AXIS, KEEPER_Z - previous.KEEPER_Z))
    cut = m.along_x(section, INNER - .3, OUTER + .1)
    cut += previous.lead_in(section, OUTER, -1)
    cut += previous.lead_in(section, JOURNAL_OUT + AXIAL_GAP, 1)
    socket_r = JOURNAL_R + RADIAL_GAP
    end = JOURNAL_OUT + AXIAL_GAP
    socket = disc(socket_r, INNER - .02, end).translate((0, 0, -KEEPER_Z)).scale(
        (1, 1, (JOURNAL_R + .035) / socket_r)).translate((0, 0, KEEPER_Z))
    socket += b.box(INNER - .02, end, AXIS - socket_r, AXIS + socket_r, KEEPER_Z, TOP + .1)
    return b.mirrored(cheek - cut - socket)


def cheek_bands():
    """Everything above the block floor in the two bands the R69 blocks and buttresses stood in."""
    return b.mirrored(b.box(INNER - .01, OUTER + .01, AXIS - 4.5, BED + 1., 8.80, 32.))


def approach():
    """Open trough for the pin's leading end outboard of each block, as R64 and R69."""
    one = disc(2.38, OUTER - .01, 35.) + b.box(OUTER - .01, 35., AXIS - 2.38, AXIS + 2.38, KEEPER_Z, 24.)
    return b.mirrored(one)


def parts():
    return {PADDLE: previous.one_piece(paddle(), 'R70 paddle'), POST_BAR: previous.one_piece(post_bar(), 'R70 post bar', limit=.001),
            WIRES: wired_lead()}


def save_parts(folder=None):
    folder = Path(folder or OUT)
    folder.mkdir(exist_ok=True)
    for name, shape in parts().items():
        b.save_closed(folder / name, shape)
    assert sha256(R69_LID.read_bytes()).hexdigest() == R69_LID_SHA256, 'the R69 retainer changed'
    copyfile(R69_LID, folder / LID)


if __name__ == '__main__':
    save_parts()
