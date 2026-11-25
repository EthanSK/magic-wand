"""R69 click-side parts: a shorter hinge without the rear web, and a low OP1 retainer.

Assembly frame as in R53-R68: the rod runs along Y through X = Z = 0, +Z is up, the
rear face Y = BED lies on the print bed. The touch board keeps its R63 pose: its top
(hinge-side) edge is at Y 26.23 and the white connector faces down.

Hinge. R64 lowered the pin under the three leads so they leave the plug straight over
the barrel. That stays, because any barrel at board height needs a gap in front of it
for the leads to turn in, which pushes the hinge further back. Two things change:

* The axis moves from Y 33.6 to 32.3, as far forward as the mated plug allows.
* The R64 rear web is removed. It was a print backing: the paddle prints upside down
  with its board seat on the bed, and the lowered barrel starts 3.3 mm above the bed.
  The web carried the first barrel layers down to the bed behind the leads. Now both
  side beams run at full height into a post on the barrel, and the barrel top between
  the posts is flat, so those layers bridge 7.65 mm between the two posts instead.
  The right beam was a low strip (so the leads could cross it); it is now the mirror
  of the left one, which also stiffens that side of the paddle.

The leads rise over the barrel between the posts and turn right behind the right post.

Retainer. The R59 retainer's two towers stood 16.5 mm high, 1.2 mm under the paddle
plate; a full press at the far end leaves 0.3 mm there. The hook that limits paddle
lift moves down: the paddle gets two legs with a foot at Z 12.9-14.35 and the retainer
two posts 15.05 mm high whose lips sit over the feet. The retainer plate is notched
under the legs. Nothing here is a claim of physical fit.
 — Claude Fable 5.2"""
from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
for folder in ('carbon-rod-holders-r64-under-entry', 'carbon-rod-holders-r63-open-hinge'):
    if str(HARDWARE / folder) not in sys.path:
        sys.path.insert(0, str(HARDWARE / folder))
import hinge64 as h64  # noqa: E402

previous = h64.previous            # design63
b, m, r61 = previous.b, previous.m, previous.r61
OUT = HERE / 'exports'
PADDLE, LID, WIRES = 'Touch_Paddle-assembly.stl', 'OP1_Lid_Stop-assembly.stl', 'Gravity_Wires-assembly.stl'
R59_LID = r61.prior.PREVIOUS / 'exports' / LID

# ------------------------------------------------------------------ hinge
BOARD_TOP_EDGE_Y = 26.23051      # hinge-side edge of the seated touch board
PLUG_REAR_Y, PLUG_BOTTOM_Z = r61.SOCKET_FACE + 3.6, b.SEAT_Z - 5.1     # 28.83, 14.2 (nominal Gravity plug)
AXIS = 32.3                      # R64: 33.6
KEEPER_Z = h64.KEEPER_Z          # 12.7, the lowered pin line
PIVOT = np.array([0., AXIS, KEEPER_Z])
MOVE = (0., AXIS - previous.AXIS, KEEPER_Z - previous.KEEPER_Z)     # from the R63 pin line, as hinge64.MOVE
BARREL_R, JOURNAL_R, JOURNAL_OUT = h64.BARREL_R, h64.JOURNAL_R, h64.JOURNAL_OUT
RADIAL_GAP, AXIAL_GAP = h64.RADIAL_GAP, h64.AXIAL_GAP
INNER, OUTER = h64.INNER, h64.OUTER
TOP = KEEPER_Z + 3.25
REAR = AXIS + 3.50
BARREL_FLAT = 0.25               # the barrel top between the posts is lowered this much
POST_X = (4.65, 6.80)            # right post; the plug is 4.0 wide each side of the centre
LEFT_POST_X = (-6.80, -3.00)     # left post, widened toward the centre; the leads start at X -2.65
POST_Y = (-0.80, 0.70)           # post fore-aft from the axis, as the R64 left post
FLARE_STOP = 0.55                # the post flare stays this far behind the plug's rear face
CHEEK_CLEAR_Z = TOP + 0.30       # beams keep their full width above the cheeks
BUTTRESS_END_Z = 10.95           # the cheek buttress lands on the existing rear plateau

# ------------------------------------------------------------------ retainer hook (board frame)
LEG_V = (-3.30, 0.90)            # stations along the OP1 board (R59 towers: -5.1 to 0.9); the rails start at 1.6
LEG_U = (3.60, 4.55)             # leg, across the board; the switch body is 2.9 each side
FOOT_TIP_U = 5.75
LEG_BOTTOM_Z = 12.90             # R58 flange: 14.6
FOOT_EDGE = 0.25
LIFT_GAP = 0.80                  # paddle lift before the foot meets the lip
LIP_TIP_U = 5.25                 # 0.5 mm over the foot, 0.7 mm off the leg face
LIP_THICK = 0.60
POST_U = (6.30, b.LID_HALF)      # retainer post stem
NOTCH_CLEAR = 0.55               # retainer plate cut back round the leg and foot
NOTCH_V_CLEAR = (0.55, 0.45)
NOTCH_FLOOR = 0.28
POST_TOP_Z = LEG_BOTTOM_Z + FOOT_EDGE + (FOOT_TIP_U - LIP_TIP_U) + LIFT_GAP + LIP_THICK   # 15.05


def parts():
    return {PADDLE: previous.one_piece(paddle(), 'R69 paddle'), LID: previous.one_piece(lid(), 'R69 retainer', limit=.001),
            WIRES: wired_lead()}


def save_parts():
    OUT.mkdir(exist_ok=True)
    for name, shape in parts().items():
        b.save_closed(OUT / name, shape)


def carrier(body):
    """Move the R64 hinge seat on a carrier that already has it, to the R69 axis. — Claude Fable 5.2"""
    body -= old_cheek_zone()
    body -= b.box(-INNER, INNER, AXIS - 4.65, AXIS + 4.20, KEEPER_Z - BARREL_R - .45, 32.)
    body -= b.box(-.96, .96, AXIS + 2., previous.BED + .1, KEEPER_Z - 3.62, 20.)
    approach = disc(2.38, OUTER - .01, 35.) + b.box(OUTER - .01, 35., AXIS - 2.38, AXIS + 2.38, KEEPER_Z, 24.)
    return (body - b.mirrored(approach)) + cheeks()


def paddle():
    old = b.load(previous.OUT / previous.PADDLE)
    front = old ^ b.box(-15, 15, -30, 20.05, 0, 40)
    # As in R57 and R58, nothing under the paddle passes its plan outline.
    x, r, edge = b.PLATE_X, 1.5, b.PLATE_FRONT
    outline = b.prism_xy([(-x + r, edge), (x - r, edge), (x, edge + r), (x, 20.), (-x, 20.), (-x, edge + r)], 0, 40)
    front = (front - b.to_world(old_flanges())) + (b.to_world(hook_legs()) ^ outline)
    body = front + beams() + barrel()
    bore = m.hole(AXIS, KEEPER_Z, m.BARREL_HOLE_R, (0, -1), -JOURNAL_OUT, JOURNAL_OUT)
    return body - bore - rear_clip_slot()


def lid():
    """The R58 plain retainer (R53 plate, rails, left spring latch) with the low hook posts. — Claude Fable 5.2"""
    plain = r61.prior.old.n.lid_plain()                   # build58
    return (plain - b.to_world(lid_notch())) + b.to_world(_mirror_u(lid_post()))


@lru_cache(maxsize=1)
def wired_lead():
    return b.union(r61.run(nodes, r61.LEAD_R) for nodes in wire_paths())


def rotate(shape, degrees):
    return shape.translate(-PIVOT).rotate((float(degrees), 0, 0)).translate(PIVOT)


def pin(name='Hinge_Pin'):
    body = b.load(r61.OUT / (name + '-assembly.stl'))
    snug_lift = .1 if name == 'Hinge_Pin_Snug' else 0.
    return body.translate((0, AXIS - r61.AXIS, KEEPER_Z - m.PIN_Z - snug_lift))


def clip():
    return rotate(pin('Pin_Clip'), h64.CLIP_ANGLE)


def disc(radius, x0, x1):
    return mf.Manifold.cylinder(x1 - x0, radius, radius, 96).rotate((0, 90, 0)).translate((x0, AXIS, KEEPER_Z))


def wire_paths():
    """Nominal route of the three 1.3 mm leads: out of the plug, over the barrel between the
    posts, then right behind the right post. Two lie side by side and the third on top. — Claude Fable 5.2"""
    start_y, start_z = r61.SOCKET_FACE + 3.25, b.SEAT_Z - 2.85
    behind = AXIS + POST_Y[1] + .45 + r61.LEAD_R          # first lane behind the right post
    lanes = {2.: (behind, 16.90), 0.: (behind, 18.30), -2.: (behind + 1.40, 17.60)}
    strands = []
    for start_x, (lane_y, lane_z) in lanes.items():
        turn = 30.5                                        # the bend starts here, clear of the plug
        radius = lane_y - turn
        plan = [(start_x, start_y), (start_x, PLUG_REAR_Y)]
        plan += [(start_x + radius * (1 - math.cos(a)), turn + radius * math.sin(a)) for a in np.linspace(0., np.pi / 2, 19)]
        plan.append((15.2, lane_y))
        # Each lead climbs to its lane over the first 5 mm behind the plug.
        nodes, run = [], 0.
        for i, (x, y) in enumerate(plan):
            if i > 1:
                run += math.hypot(x - plan[i - 1][0], y - plan[i - 1][1])
            t = min(1., run / 5.)
            nodes.append((x, y, start_z + (lane_z - start_z) * t * t * (3 - 2 * t)))
        strands.append(nodes)
    return strands


def rear_clip_slot():
    return b.box(-1.00, 1.00, AXIS - 3.75, AXIS + 8., KEEPER_Z - 2.57, KEEPER_Z + 2.57)


def post(x0, x1):
    """A beam end standing on the barrel up to the board seat (the bed, in the upside-down
    print). Its front face flares down to the barrel so the first barrel layers start on it. — Claude Fable 5.2"""
    y0, y1 = AXIS + POST_Y[0], AXIS + POST_Y[1]
    column = b.box(x0, x1, y0, y1, KEEPER_Z + .4, b.SEAT_Z)
    strip = b.box(x0, x1, y0, y1, b.SEAT_Z - .02, b.SEAT_Z)
    barrel = mf.Manifold.cylinder(x1 - x0, BARREL_R, BARREL_R, 96).rotate((0, 90, 0)).translate((x0, AXIS, KEEPER_Z))
    flare = mf.Manifold.batch_hull([strip, barrel]) ^ b.box(x0, x1, PLUG_REAR_Y + FLARE_STOP, y1, KEEPER_Z, b.SEAT_Z)
    return column + flare


def beams():
    left = mf.Manifold.batch_hull([b.box(-10.6, -8.6, 19.65, 20.05, 15.35, b.SEAT_Z),
                                   b.box(-6.80, -4.65, AXIS + POST_Y[0], AXIS + POST_Y[1], KEEPER_Z + .4, b.SEAT_Z)])
    both = left + left.mirror((1, 0, 0)) + post(*LEFT_POST_X) + post(*POST_X)
    # Inside the cheek zone the beams are cut back only below the cheek tops.
    relief = b.mirrored(b.box(m.BARREL_X - .08, 12., AXIS - 4.65, REAR + .1, 8., CHEEK_CLEAR_Z))
    return both - relief


def barrel():
    length = m.BARREL_X
    body = disc(BARREL_R, -length, length) + b.mirrored(disc(JOURNAL_R, length - .22, JOURNAL_OUT))
    flat = b.box(LEFT_POST_X[1] - .01, POST_X[0] + .01, AXIS - BARREL_R, AXIS + BARREL_R,
                 KEEPER_Z + BARREL_R - BARREL_FLAT, KEEPER_Z + BARREL_R + 1.)
    return body - flat


# ------------------------------------------------------------------ retainer hook
def _mirror_u(shape):
    return shape + shape.mirror((1, 0, 0))


def hook_legs():
    """Two legs under the sleeve wall, each with an outward foot (board frame). — Claude Fable 5.2"""
    u0, u1 = LEG_U
    z0 = LEG_BOTTOM_Z
    rise = FOOT_TIP_U - u1
    outline = [(u0, z0 + .40), (u0 + .40, z0), (FOOT_TIP_U, z0), (FOOT_TIP_U, z0 + FOOT_EDGE), (u1, z0 + FOOT_EDGE + rise),
               (u1, 14.90), (4.10, 15.35), (u0, 15.35)]
    return _mirror_u(b.prism_xz(outline, *LEG_V))


def old_flanges():
    """Every R53/R58 lift-stop flange outside the sleeve wall (board frame). — Claude Fable 5.2"""
    wall = b.BODY_X + b.SLEEVE_GAP + b.SLEEVE_WALL                 # 4.6
    trimmed = wall - .50                                           # R58 thinned the wall beside the towers
    cut = b.box(wall + .001, wall + 1.6, -9., 1.75, 14.4, 16.3)
    cut += b.box(trimmed + .001, wall + 1.6, -3.25, 1.55, 14.4, 16.3)
    return _mirror_u(cut)


def lid_notch():
    reach = FOOT_TIP_U + NOTCH_CLEAR
    return _mirror_u(b.box(b.LID_SLOT - .01, reach, LEG_V[0] - NOTCH_V_CLEAR[0], LEG_V[1] + NOTCH_V_CLEAR[1],
                          b.LID_Z[0] + NOTCH_FLOOR, b.LID_Z[1] + 1))


def lid_post():
    """Right-hand post in the board frame. Its 45 degree lip sits LIFT_GAP above the foot. — Claude Fable 5.2"""
    z1 = b.LID_Z[1]
    face = lambda u: LEG_BOTTOM_Z + FOOT_EDGE + (FOOT_TIP_U - u) + LIFT_GAP
    stem = POST_U[0]
    outline = [(stem, z1 - .01), (POST_U[1], z1 - .01), (POST_U[1], POST_TOP_Z), (LIP_TIP_U, POST_TOP_Z),
               (LIP_TIP_U, face(LIP_TIP_U)), (stem, face(stem))]
    tower = b.prism_xz(outline, *LEG_V)
    # Carry the posts across the full notch, and keep a shallow floor under the feet.
    # This removes the two 0.9 x 1.2 mm necks on each tine without raising the lips.
    # Found by Claude Opus 5.5. Fixed by GPT-6.1 Sol.
    tower += b.box(stem, POST_U[1], LEG_V[0] - NOTCH_V_CLEAR[0] - .01,
                   LEG_V[1] + NOTCH_V_CLEAR[1] + .01, z1 - .01, POST_TOP_Z)
    # Lead-in on the lip edge that passes the foot first as the retainer slides in.
    tower -= b.prism_xy([(LIP_TIP_U - .01, LEG_V[1] - .8), (LIP_TIP_U - .01, LEG_V[1] + .01), (LIP_TIP_U + .8, LEG_V[1] + .01)], 0, 40)
    return tower


# ------------------------------------------------------------------ carrier side of the hinge
def cheek_profile():
    """(Y, Z) outline of one cheek: the R64 bearing block, then a 45 degree buttress
    down to the rear plateau. Printed rear-down, the buttress is what the block grows from. — Claude Fable 5.2"""
    bottom = 8.65
    slope_start = (REAR + .05, TOP - .50)
    slope_end = slope_start[0] + (slope_start[1] - BUTTRESS_END_Z)
    return [(AXIS - 4.40, bottom), (AXIS - 4.40, TOP - .85), (AXIS - 3.55, TOP), (REAR - .45, TOP), slope_start,
            (slope_end, BUTTRESS_END_Z), (slope_end, bottom)]


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


def old_cheek_zone():
    """Both R64 cheeks, their ramps above the rear plateau, and the bands they stood in. — Claude Fable 5.2"""
    end = cheek_profile()[-1][0]
    # Leave a positive fused rear overlap instead of a slot across one slicing plane.
    # Found by Claude Opus 5.5. Fixed by GPT-6.1 Sol.
    # A shared boundary removes the old upper ramp while preserving the fused floor.
    # Found by Claude Opus 5.5. Fixed by GPT-6.1 Sol.
    boundary = end - .30
    band = b.box(INNER - .01, OUTER + .01, AXIS - 4.5, boundary, 8.80, 32.)
    ramp = b.box(INNER - .01, OUTER + .01, boundary, previous.BED + .1, BUTTRESS_END_Z + .001, 32.)
    return b.mirrored(band + ramp)

if __name__ == '__main__':
    save_parts()
