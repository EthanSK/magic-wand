"""R71 click-side parts: R70's paddle with a little more room at the hinge, a post bar whose
ribs keep their full size for three layers, and two spring clips that press the touch
board down on the paddle.

Hinge. The printed R70 hinge clicked but felt slightly stiff. The tightest place in the
CAD is the pair of journals: each has 0.15 mm fore and aft in its open bearing but only
0.035 mm above and below. R71 makes each journal 0.07 mm lower top and bottom (a slight
oval, like its bearing), so that becomes 0.105 mm. Fore-aft and sideways play, which keep
the paddle snug, are unchanged, and so are the pin line, the barrel, the gussets, the stop
legs and the click geometry. The arm gussets were checked and are 1.5 mm clear of the
holder; they stay. Which surface rubbed in the hand is not known.

What the native R70 slice showed. The posts print upright in 0.2 mm layers. R70's ribs
taper from the paddle seat up, so only the first layer (to 0.2 mm above the seat) prints
3.049 mm across; the next prints 2.995 mm. A 3.0 mm hole is therefore gripped by 0.05 mm
in that first layer only. Any clip that lets the board rise 0.2 mm lets the hole leave it.
The CAD rib tips are about 0.18 mm further out than the printed beads, so CAD squeeze
figures are not the printed fit.

Posts. Shaft, neck, head, side wings and height are R70's. Two things change:
* each rib keeps the section of R70's first printed layer for 0.6 mm (three layers) before
  it tapers, so the fit at the seat is also the fit with the board 0.2 or 0.4 mm up;
* the head gets a third ledge, on the round side of the neck, level with its two side
  wings. R57 had cut the head back there for a print orientation R70 no longer uses.

Clips. The frame is the whole R59 clip, 2.0 mm thick, with a narrow spine and a rear bar
behind it. Lying on the board it passes 0.2 mm under the head. Two arms run forward from
the rear bar at the clip's top face, and each ends beside the post in a foot that stands
0.4 mm below the frame. Pressed down over its feet the clip slides on; let go, and the arms
lift the frame 0.2 mm against the head's three ledges while the two feet press the board
down on the paddle. A board that lifts has to bend the arms further, and after 0.2 mm the
frame itself is in the way. A board that sits high leaves the arms more bent rather than
jamming the clip, until it is 0.2 mm high. The clip prints top face down: frame and arms
on the bed, then the root steps, the feet last, no bridge.

Arms. The first spring clip had straight arms, 0.8 x 1.0 mm, on a 3.3 mm lever from the
rear bar to the heel of the foot, with a square corner under the root. Pressing it flat
bends each arm 0.4 mm: by a beam estimate 5.5 % surface strain at that corner. This arm is
a leaf: 0.6 mm thick (three layers), 0.8 mm wide beside the frame and widening inward
behind the R59 clip to 1.8 mm at its root, on a 4.6 mm lever. Under the root it thickens a
layer at a time (0.8, 1.0, 1.2 mm) instead of meeting a wall. The same estimate gives 2.0 %
pressed flat and 1.0 % seated, largest in the plain strip and a little less at every step.
Hold-down falls from about 4.5 N to about 1.3 N a clip (round-figure modulus); one clip
alone is still about 27 times the weight of the 5 g assumed for the board, its plug and
wire. The rear bar is 1.0 mm deep instead of 0.7 and carries less than half the root
moment. These are estimates of strain for a given bend, not strengths: PETG's elastic
limit, its creep and the printed arm are not measured here.

Two things were tried and dropped. A sloped clip top prints as 0.2 mm steps. A spring
tongue under a lower ledge has to climb one whole layer step as it slides in, and two
printed steps meet head-on; a spring that is pressed flat by the finger avoids that.

Not known: the real hole size and pitch. A hole larger than 3.05 mm is clear of the ribs
at every height; the board is then located sideways by the clips' pressure only. The R59
clip still fits the new posts.
 — Claude Fable 5.2"""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from shutil import copyfile
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE.parent / 'carbon-rod-holders-r70-short-holder') not in sys.path:
    sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r70-short-holder'))
import hinge70 as h70  # noqa: E402

b, m, r61, h69 = h70.b, h70.m, h70.r61, h70.h69
OUT = HERE / 'exports'
PADDLE, LID, WIRES, POST_BAR = h70.PADDLE, h70.LID, h70.WIRES, h70.POST_BAR
CLIPS = {side: f'DFR_Clip_{side}-assembly.stl' for side in ('Left', 'Right')}
R59_CLIPS = {side: r61.prior.PREVIOUS / 'exports' / name for side, name in CLIPS.items()}
AXIS, KEEPER_Z, PIVOT = h70.AXIS, h70.KEEPER_Z, h70.PIVOT
rotate, pin, clip, wired_lead = h70.rotate, h70.pin, h70.clip, h70.wired_lead

# ------------------------------------------------------------------ hinge relief
JOURNAL_FLAT = 0.07              # off the journal's height, top and bottom (R70: 0.035 mm above and below in the bearing)

# ------------------------------------------------------------------ touch-board posts
RIB_SLICE = 0.10                 # the slicer reads a 0.2 mm layer at its middle: R70's first layer saw its rib 0.1 mm above the seat
RIB_FULL = 0.60                  # the ribs keep that section this far above the paddle seat: three layers (R70: one)
NECK = m.NECK                    # 2.2: post neck above the board
NOSE_HALF = 0.65                 # half width of the head's new ledge: it passes the clip's 1.5 mm throat
NOSE_Y = (-1.24, -0.40)          # from beyond the neck's round side (-0.85) into the neck, where it is rooted
NOSE_TOP = 2.90                  # above the board; its underside is at NECK, level with the side wings; the head's top stays at 3.0

# ------------------------------------------------------------------ spring clips
LAYER = 0.20                     # print layer height of the kit plate
CLIP_T = 10 * LAYER              # 2.0: the frame (R59: 1.4), 0.2 mm under the head's ledges when it lies on the board
LIFT = NECK - CLIP_T             # 0.2: the frame rises this far to the ledges
LEAD = 0.40                      # chamfer on the top edge of the prong tips
FRAME_HALF = 1.80                # R59's half width
SPINE_HALF = 0.80                # the spine behind the R59 clip (first spring clip: 1.80); the arms' roots take the width beside it
SPINE_FILLET = 0.30              # round web where the spine meets the R59 clip
ARM_X = (2.15, 2.95)             # each spring arm beside the frame, from the post axis: 0.35 mm outside it
ARM_T = 3 * LAYER                # 0.6 thick, at the clip's top face (first spring clip: 1.0)
ARM_ROOT = 5.00                  # the arms leave the rear bar here, behind the post axis (first spring clip: 4.00)
ARM_FLARE = 1.95                 # behind this the arm widens inward at 45 degrees, clear of the R59 clip's rear corner
ROOT_X = SPINE_HALF + ARM_X[0] - FRAME_HALF      # 1.15: inner edge of the arm at its root, the same 0.35 mm from the spine
STEP_RUNS = (1.50, 0.60, 0.30)   # under its root the arm is one layer thicker from each of these distances in front of the rear bar: 0.8, 1.0, 1.2 mm
REAR_BAR = 1.00                  # first spring clip: 0.70
FOOT_Y = (-0.40, 0.60)           # each foot, along the clip: beside the post, under the head's ledges
HEEL_STEP = 0.30                 # behind each foot the arm is one layer thicker this far: no square corner where the foot hangs
FOOT = 2 * LAYER                 # 0.4: how far a free foot stands below the frame
PRESS = FOOT - LIFT              # 0.2: how far each arm stays bent when the board is seated
PETG_E = 2000.                   # MPa, a round figure for the force estimates; the strain estimates do not depend on it
SLIDE_MU = 0.30                  # assumed friction of a foot on the board, for the sliding estimate only
FIRST_SPRING = dict(width=0.80, thickness=1.00, root=4.00, foot_y=(-0.70, 0.10))       # the arm of the first spring clip, for comparison


def paddle():
    """R70's paddle with both journals lowered top and bottom: round fore and aft as before,
    JOURNAL_FLAT less in height, like the bearing they turn in. — Claude Fable 5.2"""
    x0, x1 = m.BARREL_X + .02, h70.JOURNAL_OUT + .1
    radius = h70.JOURNAL_R
    unit = h70.disc(1., x0 - .1, x1 + .1).translate((0, -AXIS, -KEEPER_Z))
    oval = unit.scale((1, radius + .01, radius - JOURNAL_FLAT)).translate((0, AXIS, KEEPER_Z))
    return h70.paddle() - b.mirrored(h70.disc(radius + .4, x0, x1) - oval)


def clip_frame(side):
    """The R59 clip at its fitted place, its post axis and the unit vector toward its closed end:
    the side of the neck where the clip has plastic on the post's centre line. — Claude Fable 5.2"""
    flat = b.load(R59_CLIPS[side])
    box = np.reshape(flat.bounding_box(), (2, 3))
    post = np.array([(-1 if side == 'Left' else 1) * b.HOLE_X, b.HOLE_Y])
    mid = float(box[:, 2].mean())
    def filled(axis):
        x, y = post + np.array(axis) * (m.chain().NECK_R + .35)
        return float((flat ^ b.box(x - .1, x + .1, y - .1, y + .1, mid - .1, mid + .1)).volume()) > 1e-4

    # The prongs pass both sides of the neck; only the closed end has plastic on one side and none opposite.
    closed = [np.array(axis) for axis in ((1., 0.), (-1., 0.), (0., 1.), (0., -1.)) if filled(axis) and not filled((-axis[0], -axis[1]))]
    assert len(closed) == 1, closed
    return flat, box, post, closed[0]


def rib_land(height):
    """Outer corner (x, y) of R70's rib crest at a height above the paddle seat. R70 built each rib
    as the hull of a 0.02 mm slab at the seat and one at the board top. — Claude Fable 5.2"""
    board = b.BOARD_TOP - b.SEAT_Z
    f = min(max((height - .02) / (board - .04), 0.), 1.)
    return tuple(lo + (hi - lo) * f for lo, hi in (h70.RIB_LAND_X, h70.RIB_LAND_Y))


def rib_section(sign, land):
    a = np.radians(sign * h70.RIB_DEG)
    out, across = np.array([np.sin(a), np.cos(a)]), np.array([np.cos(a), -np.sin(a)])
    ring = [out * h70.RIB_ROOT_RADIUS - across * h70.RIB_BASE / 2, out * h70.RIB_ROOT_RADIUS + across * h70.RIB_BASE / 2,
            np.array([sign * land[0], land[1]]), np.array([sign * (land[0] - h70.RIB_LAND_WIDTH), land[1]])]
    return mf.CrossSection.hull_points(np.asarray(ring))


def rib(sign):
    """R70's rib with its first printed section held for RIB_FULL, then tapering to R70's
    section at the board top. In the native R70 slice only the first 0.2 mm layer reached
    3.05 mm across; a board lifted 0.2 mm was already on the next, smaller layer. — Claude Fable 5.2"""
    seat, top = b.SEAT_Z, b.BOARD_TOP
    full, last = rib_section(sign, rib_land(RIB_SLICE)), rib_section(sign, rib_land(top - seat))
    slab = lambda section, z: mf.Manifold.extrude(section, .02).translate((0, 0, z))
    return mf.Manifold.extrude(full, RIB_FULL).translate((0, 0, seat)) + mf.Manifold.batch_hull([slab(full, seat + RIB_FULL - .02), slab(last, top - .02)])


def nose():
    """A ledge on the round side of the neck, level with the head's two side wings. R57 cut the
    head back on that side for a print orientation R70 no longer uses. The clip's closed end
    now has a third place to bear. — Claude Fable 5.2"""
    return b.box(-NOSE_HALF, NOSE_HALF, NOSE_Y[0], NOSE_Y[1], b.BOARD_TOP + NECK, b.BOARD_TOP + NOSE_TOP)


def post():
    """R57's post with R71's ribs in the board's thickness and the ledge under the head. Shaft,
    neck, head, side wings and height are unchanged. — Claude Fable 5.2"""
    return m.post(m.chain()) + rib(-1) + rib(1) + nose()


def post_bar():
    plain = m.post(m.chain())
    posts = b.union(post().translate((s * b.HOLE_X, b.HOLE_Y, 0)) for s in (-1, 1))
    bounds = plain.bounding_box()
    base = b.box(-b.HOLE_X - 1.3, b.HOLE_X + 1.3, b.HOLE_Y + bounds[1], b.HOLE_Y + bounds[4], b.PLATE_Z - 1.8, b.PLATE_Z)
    return posts + base


def clip_plans(side):
    """Frame, arms and feet in plan about the post axis, -Y toward the closed end as fitted.
    The frame is the whole R59 clip with a spine behind it and a rear bar. Each arm is a strip
    beside the frame that widens inward behind the R59 clip to a root 1.8 mm wide. — Claude Fable 5.2"""
    flat, box, post_xy, axis = clip_frame(side)
    assert tuple(int(v) for v in axis) == (0, -1), 'the clip is expected to close toward -Y'
    r59 = flat.project().translate((-float(post_xy[0]), -float(post_xy[1])))
    back = -(ARM_ROOT + REAR_BAR)
    square = lambda x0, x1, y0, y1: mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
    rounded = lambda section, r=.35: section.offset(-r, mf.JoinType.Round).offset(r, mf.JoinType.Round, 2., 48)
    eased = lambda section, r: rounded(section.offset(r, mf.JoinType.Round, 2., 48).offset(-r, mf.JoinType.Round), r)      # re-entrant corners too
    spine = square(-SPINE_HALF, SPINE_HALF, back, -1.0)
    bar = rounded(square(-ARM_X[1], ARM_X[1], back, -ARM_ROOT), .25)
    # The slot between spine and arm root ends in a half round on the rear bar: one quarter belongs to the frame, one to the arm.
    radius, centre = (ROOT_X - SPINE_HALF) / 2, (ROOT_X + SPINE_HALF) / 2
    quarter = lambda x0, x1: square(x0, x1, -ARM_ROOT - .05, -ARM_ROOT + radius) - mf.CrossSection.circle(radius, 48).translate((centre, -ARM_ROOT + radius))
    both = lambda section: section + section.mirror((1., 0.))
    rear = float(box[0, 1] - post_xy[1])                                 # the R59 clip's closed end
    web = square(SPINE_HALF - .05, SPINE_HALF + SPINE_FILLET, rear - SPINE_FILLET, rear + .05) \
        - mf.CrossSection.circle(SPINE_FILLET, 48).translate((SPINE_HALF + SPINE_FILLET, rear - SPINE_FILLET))
    frame = r59 + spine + bar + both(quarter(SPINE_HALF - .05, centre)) + both(web)
    flare_end = ARM_FLARE + ARM_X[0] - ROOT_X
    outline = [(ROOT_X, -ARM_ROOT - 1.5), (ARM_X[1], -ARM_ROOT - 1.5), (ARM_X[1], FOOT_Y[1]), (ARM_X[0], FOOT_Y[1]), (ARM_X[0], -ARM_FLARE), (ROOT_X, -flare_end)]
    inside = square(0., ARM_X[1] + 1., -ARM_ROOT - .40, FOOT_Y[1] + 1.)                              # the arms run 0.4 mm into the rear bar
    arm = (eased(mf.CrossSection([np.array(outline)]), .2) ^ inside) + quarter(centre, ROOT_X + .05)
    feet = both(rounded(square(ARM_X[0], ARM_X[1], FOOT_Y[0], FOOT_Y[1]), .2))
    return frame, both(arm), feet


def step_runs():
    """(how far in front of the rear bar, how far below the arm) for each root step, longest first."""
    return [(run, LAYER * (k + 1)) for k, run in enumerate(STEP_RUNS)]


def arm_thickness(y):
    """Arm thickness at a station along the clip (post axis at 0, the rear bar behind -ARM_ROOT)."""
    heel = LAYER if y >= FOOT_Y[0] - HEEL_STEP else 0.
    return ARM_T + max([depth for run, depth in step_runs() if y <= -ARM_ROOT + run] + [heel])


@lru_cache(maxsize=None)
def arm_profile(count=460):
    """One arm cut into stations from the heel of its foot back to the rear bar: station, width
    measured on the plan that is exported, and thickness. — Claude Fable 5.2"""
    arms = clip_plans('Left')[1] ^ mf.CrossSection.square((10., 20.)).translate((0., -15.))
    edges = np.linspace(FOOT_Y[0], -ARM_ROOT, count + 1)
    step = float(edges[0] - edges[1])
    stations = (edges[:-1] + edges[1:]) / 2
    widths = [float((arms ^ mf.CrossSection.square((10., step)).translate((0., float(y) - step / 2))).area()) / step for y in stations]
    return stations, np.array(widths), np.array([arm_thickness(float(y)) for y in stations]), step


def cantilever(stations, widths, thick, step):
    """Euler beam along one arm: clamped behind its last station, loaded upward at the leading
    edge of its first. Returns the deflection at the load per newton times the modulus, the
    surface strain at every station per unit of that deflection, the deflected shape at each
    station's leading edge (1 at the load) and the slope at the load. Strain per deflection is
    geometry only; no material figure enters it. — Claude Fable 5.2"""
    lever = stations[0] + step / 2 - stations
    inertia = widths * thick ** 3 / 12
    curvature = lever / inertia                                          # per newton, times the modulus
    slope = np.cumsum(curvature[::-1])[::-1] * step                      # integrated from the clamp forward
    height = np.cumsum((slope - curvature * step / 2)[::-1])[::-1] * step
    at_load = float(height[0])
    return at_load, curvature * thick / 2 / at_load, height / at_load, float(slope[0] / at_load)


def arm_shape():
    """Deflected shape of an arm for the posed models: station, rise (1 at the heel), slope at the heel."""
    stations, widths, thick, step = arm_profile()
    _, _, shape, slope = cantilever(stations, widths, thick, step)
    return stations + step / 2, shape, slope


def spring_clip(side, lift=LIFT, bent=0.):
    """The R71 clip. A 2.0 mm frame (R59's clip with a spine and a rear bar) and two arms at its
    top face, each ending in a foot that stands FOOT below the frame when free.

    `lift` puts the frame that far above the board; the exported pose has it against the
    head's ledges. `bent` raises the heel of each foot relative to the frame by that much:
    PRESS is the fitted pose (heels on the board), FOOT the pose while it is pressed flat and
    slid on. A bent arm tilts its foot, so the heel is what bears.
     — Claude Fable 5.2"""
    flat, box, post_xy, axis = clip_frame(side)
    z0 = float(box[0, 2])
    frame, arms, feet = clip_plans(side)
    put = lambda section, low, high: mf.Manifold.extrude(section, high - low).translate((float(post_xy[0]), float(post_xy[1]), z0 + low))
    body = put(frame, 0., CLIP_T)
    tips = float(min((box[:, :2] - post_xy) @ axis))
    across, top = np.array([-axis[1], axis[0]]), z0 + CLIP_T
    corners = [(tips - .5, top - LEAD - .5), (tips + LEAD + .5, top + .5), (tips - .5, top + .5)]
    body -= mf.Manifold.hull_points([(*(post_xy + axis * station + across * side_), height) for station, height in corners for side_ in (-4., 4.)])
    under = CLIP_T - ARM_T
    behind = lambda y: mf.CrossSection.square((20., 10.)).translate((-10., y - 10.))
    spring = put(arms, under, CLIP_T) + put(feet, -FOOT, under + .01)
    for run, depth in step_runs():
        spring += put(arms ^ behind(-ARM_ROOT + run), under - depth, under + .01)
    spring += put(arms - behind(FOOT_Y[0] - HEEL_STEP), under - LAYER, under + .01)
    spring = spring.refine_to_length(.25)
    if bent:
        stations, shape, slope = arm_shape()
        heel, y0 = float(stations[0]), float(post_xy[1])

        def bend(points):
            points = np.array(points, float)
            y = points[:, 1] - y0
            rise = np.where(y > heel, 1. + slope * (y - heel), np.interp(y, stations[::-1], shape[::-1], left=0.))
            points[:, 2] += bent * rise
            return points
        spring = spring.warp_batch(bend)
    return (body + spring).translate((0, 0, lift))


def clip_voids(side, lift=LIFT):
    """Spaces that must stay open for the spring to work, in the exported pose, each drawn
    0.07 mm inside its walls: the slot between each arm and the frame (with the window behind
    the R59 clip) through the whole frame height, and the space under each arm in front of
    its root steps. For a deposited-path audit. — Claude Fable 5.2"""
    flat, box, post_xy, axis = clip_frame(side)
    z0 = float(box[0, 2]) + lift
    frame, arms, feet = clip_plans(side)
    put = lambda section, low, high: mf.Manifold.extrude(section, high - low).translate((float(post_xy[0]), float(post_xy[1]), z0 + low))
    square = lambda x0, x1, y0, y1: mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
    field = square(SPINE_HALF, ARM_X[1], -ARM_ROOT + .10, FOOT_Y[0] - .20)
    field += field.mirror((1., 0.))
    open_plan = field - (frame + arms).offset(.07, mf.JoinType.Round, 2., 24)
    longest = max(run for run, _ in step_runs())
    under = (arms ^ square(-ARM_X[1], ARM_X[1], -ARM_ROOT + longest + .15, FOOT_Y[0] - .20)).offset(-.15, mf.JoinType.Round)
    return dict(spring_arm_side_slots=[put(piece, .15, CLIP_T - .05) for piece in open_plan.decompose() if piece.area() > .02],
                space_below_the_spring_arms=[put(piece, .15, CLIP_T - ARM_T - .20) for piece in under.decompose() if piece.area() > .02])


def arm_numbers():
    """Beam estimate for one arm: a cantilever clamped at the rear bar and loaded at the heel of
    its foot, cut into stations with the width and thickness of the exported plan. The same
    method on the first spring clip's arm is given beside it. Strain is surface strain from
    bending only, for the stated deflection: geometry, no material figure. Forces use a
    round-figure modulus. Nothing here is a measured force or a strength. — Claude Fable 5.2"""
    stations, widths, thick, step = arm_profile()
    at_load, strain, _, _ = cantilever(stations, widths, thick, step)
    stiffness = PETG_E / at_load
    worst = int(np.argmax(strain))
    width = ARM_X[1] - ARM_X[0]
    steps = [dict(in_front_of_the_rear_bar_mm=round(run, 2), thickness_mm=dict(in_front=round(ARM_T + depth - LAYER, 2), behind=round(ARM_T + depth, 2)),
                  strain_in_front_while_pressed_flat=round(float(strain[np.argmin(np.abs(stations - (-ARM_ROOT + run + step / 2)))]) * FOOT, 4)) for run, depth in step_runs()]
    slide = lambda give, wide, deep: 6 * SLIDE_MU * FOOT / give * (FOOT + CLIP_T - deep / 2) / (wide * deep ** 2)       # friction on the foot bends the strip; the modulus cancels

    def first(load):
        """The first spring clip's straight arm by the same integration, loaded at its heel or at its foot's middle."""
        edges = np.linspace(load, -FIRST_SPRING['root'], 401)
        gap = float(edges[0] - edges[1])
        give, bending, _, _ = cantilever((edges[:-1] + edges[1:]) / 2, np.full(400, FIRST_SPRING['width']), np.full(400, FIRST_SPRING['thickness']), gap)
        return dict(lever_mm=round(load + FIRST_SPRING['root'], 2), stiffness_n_per_mm=round(PETG_E / give, 2), force_when_seated_n=round(PETG_E / give * PRESS, 2),
                    force_while_pressed_flat_n=round(PETG_E / give * FOOT, 2),
                    bending_strain_when_seated=round(float(bending.max()) * PRESS, 4), bending_strain_while_pressed_flat=round(float(bending.max()) * FOOT, 4),
                    sliding_friction_adds_while_pressed_flat=round(slide(give, FIRST_SPRING['width'], FIRST_SPRING['thickness']), 4))
    old = dict(arm='0.8 mm wide, 1.0 mm thick, straight, from a rear bar 4.0 mm behind the post axis; a square corner under its root',
               loaded_at_the_heel=first(FIRST_SPRING['foot_y'][0]), loaded_at_the_middle_of_the_foot_as_first_reported=first(sum(FIRST_SPRING['foot_y']) / 2))
    flat = float(strain.max()) * FOOT
    return dict(width_mm=round(width, 2), root_width_mm=round(ARM_X[1] - ROOT_X, 2), thickness_mm=round(ARM_T, 2), layers=round(ARM_T / LAYER), root_steps=steps,
                lever_mm=round(ARM_ROOT + FOOT_Y[0], 2), foot_below_the_frame_when_free_mm=FOOT,
                bent_when_seated_mm=round(PRESS, 2), bent_while_pressed_flat_mm=FOOT, stiffness_n_per_mm=round(stiffness, 2),
                force_when_seated_n=round(stiffness * PRESS, 2), force_while_pressed_flat_n=round(stiffness * FOOT, 2),
                bending_strain_when_seated=round(float(strain.max()) * PRESS, 4), bending_strain_while_pressed_flat=round(flat, 4),
                largest_strain_is_mm_behind_the_post_axis=round(-float(stations[worst]), 2), largest_strain_in_the_plain_arm=bool(thick[worst] < ARM_T + 1e-9),
                strain_at_the_rear_bar_while_pressed_flat=round(float(strain[-1]) * FOOT, 4),
                sliding_friction=dict(assumed_coefficient=SLIDE_MU, adds_while_pressed_flat=round(slide(at_load, width, ARM_T), 4),
                                      adds_under_the_spring_alone=round(slide(at_load, width, ARM_T) * PRESS / FOOT, 4),
                                      reading='slid back off, friction on the feet adds this to the strain in the plain strip; slid on, it takes it away'),
                foot_tilt_when_seated_mm_per_mm=round(arm_shape()[2] * PRESS, 3),
                first_spring_clip=old, pressed_flat_strain_over_the_first_spring_clip=round(flat / old['loaded_at_the_heel']['bending_strain_while_pressed_flat'], 2),
                modulus_assumed_mpa=PETG_E,
                method='Euler beam, %d stations from the exported plan, clamped at the rear bar, loaded at the heel of the foot; surface strain from bending only' % len(stations))


def clip_numbers(side='Left'):
    flat, box, post, axis = clip_frame(side)
    flat_thickness = float(box[1, 2] - box[0, 2])
    arm = arm_numbers()
    was = arm['first_spring_clip']['loaded_at_the_heel']
    return dict(neck_mm=NECK, layer_mm=LAYER, frame_mm=dict(r59=round(flat_thickness, 2), r71=CLIP_T), layers=dict(r59=round(flat_thickness / LAYER), r71=round(CLIP_T / LAYER)),
                print_height_layers=round((CLIP_T + FOOT) / LAYER), free_lift_under_the_clip_mm=dict(r59=round(NECK - flat_thickness, 2), r71=0.),
                board_lift_before_the_frame_stops_it_mm=round(LIFT, 2), arms=2, arm=arm, hold_down_per_clip_n=round(2 * arm['force_when_seated_n'], 2),
                press_to_fit_per_clip_n=round(2 * arm['force_while_pressed_flat_n'], 2),
                first_spring_clip=dict(hold_down_per_clip_n=round(2 * was['force_when_seated_n'], 2), press_to_fit_per_clip_n=round(2 * was['force_while_pressed_flat_n'], 2)),
                rear_bar=dict(depth_mm=dict(first_spring_clip=0.70, r71=REAR_BAR),
                              arm_root_moment_while_pressed_flat_n_mm=dict(first_spring_clip=round(was['force_while_pressed_flat_n'] * was['lever_mm'], 1),
                                                                           r71=round(arm['force_while_pressed_flat_n'] * arm['lever_mm'], 1))),
                press_where='on the front half of the clip, between its two feet; pressing the rear bar does not lower the prongs',
                free_on_the_board=dict(rests_on='its two feet and the lower edge of its rear bar',
                                       prong_tips_above_the_board_mm=round(FOOT * (float(box[1, 1] - post[1]) + ARM_ROOT + REAR_BAR) / (FOOT_Y[0] + ARM_ROOT + REAR_BAR), 2),
                                       room_under_the_head_for_them_mm=round(NECK - CLIP_T, 2)),
                tip_chamfer_mm=LEAD, slide_axis=[int(v) for v in axis],
                printed='top face down: frame and arms on the bed, then the root steps, the two feet last')


def parts():
    made = h70.parts()
    out = {PADDLE: h70.previous.one_piece(paddle(), 'R71 paddle'), POST_BAR: h70.previous.one_piece(post_bar(), 'R71 post bar', limit=.001), WIRES: made[WIRES]}
    out.update({CLIPS[side]: h70.previous.one_piece(spring_clip(side), 'R71 clip', limit=.001) for side in CLIPS})
    return out


def save_parts(folder=None):
    folder = Path(folder or OUT)
    folder.mkdir(exist_ok=True)
    for name, shape in parts().items():
        b.save_closed(folder / name, shape)
    assert sha256(h70.R69_LID.read_bytes()).hexdigest() == h70.R69_LID_SHA256, 'the R69 retainer changed'
    copyfile(h70.R69_LID, folder / LID)


if __name__ == '__main__':
    save_parts()
