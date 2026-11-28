"""R80: thicker touch-board posts that take up the hole's real size, and more room under
the paddle's two hook feet. Run this file to export both parts and write posts80.json.

Two printed parts change. The paddle (R77's file, the one already printed), the R79 key
holder, the two flat R59 clips, the hinge pin and its clip are used as they are.

1. DFR_Post_Bar. Ethan: the touch board still wobbles; "make the pole thicker and make it
   just go thinner at the top where the clips should go on."

   What limits a thicker pole. The posts are pushed up through the paddle from below, and
   the paddle's two holes are 2.66 mm along the bar by 2.94 mm across it. A round 3.0 mm
   pole cannot pass, but the four diagonal parts of a 3.0 mm circle can: the corners of
   that hole are 1.98 mm from its centre. The other limit is that nobody has measured the
   board's holes or their spacing. A rigid pole made for 3.00 mm is loose in a 3.15 mm
   hole and does not go into a 2.95 mm one, and the two poles are 15.5 mm apart on a
   printed bar while the holes are wherever the board maker drilled them.

   So each post has a thick rigid body and one sprung finger:
   * the body is 2.54 mm wide and, with the finger, 3.0 mm deep through the board (R57 to
     R79: a 2.25 x 2.52 mm teardrop that touched the hole with thin rib crests). On its
     rear side it carries two lands, each a 0.45 mm wide piece of a 3.0 mm circle,
     straight for 1.35 of the board's 1.6 mm. Outside the lands the body stands 0.1 mm
     back, so holes that are not exactly 15.5 mm apart do not wedge on it;
   * a finger 2.2 mm wide stands in front of the body on the end of a 6.75 mm arm cut out
     of the bar itself. The arm bends in the plane it is printed in. Above the paddle the
     finger has a round head that, free, stands 0.25 mm further out than a 3.0 mm hole.
     The board pushes it in as it goes on, and the finger pushes the board back against
     the two lands. Hole a little large, hole a little small, spacing a little off: the
     finger takes it up, within its 0.52 mm of travel (see posts80.json for the range);
   * the heads are wider than the paddle's holes, so the bar clicks up into the paddle
     (each finger gives 0.28 mm) and then stays there on its own while the board goes on;
   * above the board the post is the R71 neck and head, untouched, so the flat clips slide
     on exactly as before and the board can still lift 0.8 mm under them. Through that
     lift the board stays on the lands; the finger's full face reaches 1.0 mm up the board.

   Bar height, post height, the 15.5 mm spacing and the bar's fit in the paddle are kept.

2. OP1_Lid_Stop (the retainer). Ethan suspects the part that hangs under the paddle sits
   too close to the bottom. Under the paddle are two hook legs; each has a foot that dips
   into a pocket in the retainer when the paddle is pressed, and a lip above it that stops
   the paddle lifting off. Measured on the R79 parts, a foot has 0.82 mm above it at rest
   and, at full click, 0.56 to 0.62 mm below it to the pocket's 0.28 mm floor and 0.45 mm to
   the pocket's end wall. Nothing touches in the model, but the pocket is blind (it can
   hold print fluff) and tight lengthwise for a part that is slid into place.
   R80 opens the floor under each foot, so the next thing below is the OP1 board, and
   makes each pocket 0.6 mm longer in front and 0.2 mm longer behind, where the holder's
   rails begin. The lips, the posts that carry them, the paddle and the click are
   untouched over the foot, so the paddle is held exactly as before. The open floor had
   left each tine only 3.51 mm2 beside the ends of the foot, under the 4.10 mm2 the R69
   keeper check asks for. The lip's section now runs on past both ends of the foot,
   above it, and the thinnest station is back to 4.27 mm2.

Not known, and not claimed: the real hole size and spacing, the printed size of the lands
and finger, how the arm creeps, and which surface Ethan's paddle actually touched.
Dimensions are mm in the assembly frame (rod along Y, +Z toward the keypad); post
sections are given about the post's own axis, +Y toward the hinge.
 — Claude Fable 5.2"""
from hashlib import sha256
from pathlib import Path
import json
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r79-hinge-release'))
import design79 as r79  # noqa: E402
import hinge71 as h  # noqa: E402

b, m, h70, h69, r61 = h.b, h.m, h.h70, h.h69, h.r61
r77 = r79.r77
POST_BAR, LID = h.POST_BAR, h.LID                      # 'DFR_Post_Bar-assembly.stl', 'OP1_Lid_Stop-assembly.stl': the names every plate since R70 uses
REUSED = dict(Touch_Paddle=r77.OUT / r77.PADDLE, Key_Carrier=r79.OUT / r79.HOLDER, DFR_Clip_Left=h.R59_CLIPS['Left'], DFR_Clip_Right=h.R59_CLIPS['Right'])
HOLE_X, HOLE_Y = b.HOLE_X, b.HOLE_Y                    # 7.75, 15.33: the posts, 15.5 apart
BASE0, BASE1 = b.PLATE_Z - 1.8, b.PLATE_Z              # 15.9 to 17.7: the bar under the paddle, as R57
SEAT, TOP = b.SEAT_Z, b.BOARD_TOP                      # 19.3 to 20.9: the touch board
PASSAGE = (1.33, 1.47)                                 # half sizes of the printed paddle's post hole, measured on the R77 file

# ------------------------------------------------------------------ 1a. the thick body (about the post axis)
LAND_R = 1.50                    # the two rear lands lie on a 3.0 mm circle about the post axis
LAND_TO_DEG = 50.0               # each land ends this far round from the rear; beyond it the body stands LAND_RELIEF inside the circle,
LAND_RELIEF = 0.10               # so holes that are not exactly 15.5 mm apart do not wedge on the body's outer edges
LAND_HALF = 1.27                 # body half width through the board (R57: 1.125). R71's rib crests were this wide and went through the paddle
SHAFT_HALF = 1.20                # a little narrower inside the paddle, where nothing bears: 0.13 mm a side to its hole
CORE_N = 1.26                    # rear face, as the R57 post
LEAD = 0.25                      # chamfer round the body's top, so the board finds it
# ------------------------------------------------------------------ 1b. the sprung finger and its arm
SLOT = 0.52                      # open space between the finger or arm and the rigid bar: the finger's whole travel
FINGER_OUT = -1.38               # front face of the finger's stem, inside the paddle. The paddle hole's wall is at -1.47
FINGER_T = 0.55                  # stem thickness, across the direction it bends
FINGER_IN = FINGER_OUT + FINGER_T
CORE_S = FINGER_IN + SLOT        # -0.31: front face of the rigid body
FINGER_HALF = 1.10               # the finger is 2.2 mm wide
FINGER_CORNER = 0.30             # its two front corners are cut back this much
HEAD_OUT = -1.75                 # free front face of the finger's head, above the paddle: 0.25 mm further out than a 3.0 mm hole's wall
HEAD_R = 1.40                    # the head's face is rounder than any hole it will meet (2.8 mm circle), so it bears at its middle, not at two corners
HEAD_FROM = SEAT + 0.02          # the head starts just above the paddle's seat and grows out at 45 degrees
FINGER_TOP = TOP - 0.20          # 20.7: under the neck's round side with room to move
FINGER_LEAD = 0.40               # roof on the head: the board (from above) and the paddle hole (from below) both ride up it
FINGER_BACK = 0.36               # chamfer on the head's inner top edge: clear of the corbel under the neck when pushed right in
ARM_OUT, ARM_T = -1.26, 1.00     # the arm's front edge is the old bar's front edge; 1.0 mm across the direction it bends
ARM_IN = ARM_OUT + ARM_T
ARM_TOP = BASE1 - 0.20           # the arm stays 0.2 mm under the paddle so it never rubs it
ANCHOR_HALF = 1.00               # both arms leave a solid block at the middle of the bar
ARM_NECK = (1.60, 1.10)          # the arm narrows to the finger's thickness between these distances inboard of the post axis
SPINE_ADD = 0.50                 # the rigid bar is this much wider at the back between the paddle's skirts, for what the slots took
PETG_E = 2000.                   # MPa, a round figure for the force estimates only
# ------------------------------------------------------------------ 2. retainer pockets (board frame, as hinge69)
POCKET_END = (h69.NOTCH_V_CLEAR[0] + 0.60, b.RAIL_START - .05 - h69.LEG_V[1])   # 1.15 in front of the leg, 0.65 behind it (R69: 0.55, 0.45). The holder's rails start 0.7 behind the leg
WINDOW_END = 0.50                # the floor is open this far beyond each end of the leg
LIP_FRONT = 0.70                 # the lip's section runs on this far in front of the leg, over the open floor and 0.2 mm past it
LIP_LEAD = 0.50                  # lead-in on the lip's rear end, the end that passes the foot first as the retainer slides in (R69: 0.8, at the leg's end)
TINE_R59 = 4.32                  # mm2: the R59 retainer's tine section; checks69.keeper asks for 95 % of it at every station
TINE_MIN = 4.20                  # solid CAD section target above 4.104; sections80 checks the deposited beads against R79


def _rect(x0, x1, y0, y1):
    return mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def _slab(section, z0, z1):
    return mf.Manifold.extrude(section, z1 - z0).translate((0, 0, z0))


def core_section(half):
    """The rigid body in plan: a 3.0 mm circle cut to what goes through the paddle hole, with
    its front third left out for the finger. The two rear corners that remain are the lands."""
    reach = LAND_R * float(np.sin(np.radians(LAND_TO_DEG)))
    plan = (mf.CrossSection.circle(LAND_R, 240) ^ _rect(-reach, reach, -3., 3.)) + mf.CrossSection.circle(LAND_R - LAND_RELIEF, 240)
    return plan ^ _rect(-half, half, CORE_S, CORE_N)


def finger_section(head=False):
    """The finger in plan: a flat stem inside the paddle, and above the paddle a head whose face
    is round like the hole it presses on."""
    stem = _rect(-FINGER_HALF, FINGER_HALF, FINGER_OUT, FINGER_IN)
    if head:
        stem += mf.CrossSection.circle(HEAD_R, 240).translate((0., HEAD_OUT + HEAD_R)) ^ _rect(-FINGER_HALF, FINGER_HALF, HEAD_OUT - .1, FINGER_IN)
    # Both front corners are cut back at 45 degrees: in a round hole the middle of the finger must bear first, not its corners.
    w, c = FINGER_HALF, FINGER_CORNER
    ring = [(-w, FINGER_IN), (-w, FINGER_OUT + c), (-w + c, FINGER_OUT), (-w + c, HEAD_OUT - .2), (w - c, HEAD_OUT - .2), (w - c, FINGER_OUT), (w, FINGER_OUT + c), (w, FINGER_IN)]
    stem = stem ^ mf.CrossSection([np.array(ring)])
    return stem.offset(-.10, mf.JoinType.Round).offset(.10, mf.JoinType.Round, 2., 32)


def core():
    """Ethan asked for a thicker pole that goes thin only where the clips go on. This is the
    thick part, from the bar to the top of the board; the R71 neck and head stand on it."""
    lands = core_section(LAND_HALF)
    body = _slab(core_section(SHAFT_HALF), BASE1 - .01, SEAT) + _slab(lands, SEAT - .01, TOP - LEAD)
    body += mf.Manifold.batch_hull([_slab(lands, TOP - LEAD - .01, TOP - LEAD), _slab(lands.offset(-LEAD, mf.JoinType.Round), TOP - .01, TOP)])
    # The neck is round toward the finger and wider there than the body. A 45 degree corbel carries it, above the finger's roof.
    r = m.chain().NECK_R
    over = mf.CrossSection.circle(r, 96) ^ _rect(-2., 2., -2., CORE_S + .02)
    chord = float(over.bounds()[2])
    body += mf.Manifold.batch_hull([_slab(over, TOP - .02, TOP), _slab(_rect(-chord, chord, CORE_S, CORE_S + .02), TOP - (r + CORE_S) - .04, TOP - (r + CORE_S) - .02)])
    upper = h.post() ^ b.box(-3., 3., -3., 3., TOP - .01, TOP + 6.)             # R71's neck, head, side wings and ledge, as they are
    return body + upper


def finger():
    """The sprung contact. It has to stand out past a 3.0 mm hole when free, go through the
    paddle hole without being squeezed, and give when the board comes down on it."""
    plan, head = finger_section(), finger_section(head=True)
    foot = plan ^ _rect(-2., 2., ARM_OUT, 2.)                                    # below the paddle it keeps the old bar's front edge
    roof = head ^ _rect(-2., 2., HEAD_OUT + FINGER_LEAD, FINGER_IN - FINGER_BACK)
    step = FINGER_OUT - HEAD_OUT                                                 # the head stands this far out past the stem, on a 45 degree underside
    hull = mf.Manifold.batch_hull
    return (_slab(foot, BASE0, BASE1 - .12) + hull([_slab(foot, BASE1 - .13, BASE1 - .12), _slab(plan, BASE1 - .01, BASE1)])
            + _slab(plan, BASE1 - .01, HEAD_FROM + .01)
            + hull([_slab(plan, HEAD_FROM, HEAD_FROM + .01), _slab(head, HEAD_FROM + step, HEAD_FROM + step + .01)])
            + _slab(head, HEAD_FROM + step, FINGER_TOP - FINGER_LEAD)
            + hull([_slab(head, FINGER_TOP - FINGER_LEAD - .01, FINGER_TOP - FINGER_LEAD), _slab(roof, FINGER_TOP - .01, FINGER_TOP)]))


def arm_plan():
    """The right-hand arm in plan, in bar coordinates (post axis at HOLE_X, 0): from the middle
    block out to the finger. It is cut from the bar, so the bar looks the same from below."""
    x0, x1 = ANCHOR_HALF - .30, HOLE_X + FINGER_HALF
    ring = [(x0, ARM_OUT), (x1, ARM_OUT), (x1, FINGER_IN), (HOLE_X - ARM_NECK[1], FINGER_IN), (HOLE_X - ARM_NECK[0], ARM_IN), (x0, ARM_IN)]
    return mf.CrossSection([np.array(ring)])


def post_bar():
    both = lambda shape: shape + shape.mirror((1, 0, 0))
    arm = arm_plan()
    clear = arm.offset(SLOT, mf.JoinType.Miter, 4.) ^ _rect(ANCHOR_HALF, 20., -5., 5.)
    clear = clear.offset(-.18, mf.JoinType.Round).offset(.18, mf.JoinType.Round, 2., 32)        # round slot ends: no sharp corner at the arm's root
    north = float(h.post_bar().bounding_box()[4]) - HOLE_Y                                       # the R71 bar's rear edge
    spine = _rect(-HOLE_X - 1.3, HOLE_X + 1.3, ARM_OUT, north) + _rect(-HOLE_X + .15, HOLE_X - .15, north - .01, north + SPINE_ADD)
    base = _slab(spine, BASE0, BASE1) - both(_slab(clear, BASE0 - .1, BASE1 + .1)) + both(_slab(arm, BASE0, ARM_TOP))
    posts = both((core() + finger()).translate((HOLE_X, 0, 0)))
    return (base + posts).translate((0, HOLE_Y, 0))


# ------------------------------------------------------------------ retainer
def lid_notch():
    """Room for each foot. Ethan's worry is the part under the paddle sitting too close to the
    bottom: the floor under the foot is opened, and the pocket made longer, because the
    retainer is slid into place and nothing sets its position to a tenth."""
    u0, u1 = b.LID_SLOT - .01, h69.FOOT_TIP_U + h69.NOTCH_CLEAR
    v = h69.LEG_V
    pocket = b.box(u0, u1, v[0] - POCKET_END[0], v[1] + POCKET_END[1], b.LID_Z[0] + h69.NOTCH_FLOOR, b.LID_Z[1] + 1)
    window = b.box(u0, u1, v[0] - WINDOW_END, v[1] + WINDOW_END, b.LID_Z[0] - .1, b.LID_Z[1] + 1)
    return h69._mirror_u(pocket + window)


def lid_post():
    """R69's post and lip, the same section and height over the foot. With the floor open, the
    tine beside each end of the foot was only the 0.9 mm stem (3.51 mm2). The lip's section
    now carries on past both ends of the foot, above where the foot can go and no nearer
    to it than the lip itself, so the open floor and the room at the foot's ends stay.
    The stem runs the whole longer pocket. — Claude Fable 5.2"""
    v, stem, z1 = h69.LEG_V, h69.POST_U[0], b.LID_Z[1]
    face = lambda u: h69.LEG_BOTTOM_Z + h69.FOOT_EDGE + (h69.FOOT_TIP_U - u) + h69.LIFT_GAP      # the lip's underside, LIFT_GAP above the foot, as hinge69.lid_post
    outline = [(stem, z1 - .01), (h69.POST_U[1], z1 - .01), (h69.POST_U[1], h69.POST_TOP_Z), (h69.LIP_TIP_U, h69.POST_TOP_Z), (h69.LIP_TIP_U, face(h69.LIP_TIP_U)), (stem, face(stem))]
    rear = v[1] + POCKET_END[1]
    tower = b.prism_xz(outline, v[0] - LIP_FRONT, rear)
    tower -= b.prism_xy([(h69.LIP_TIP_U - .01, rear - LIP_LEAD), (h69.LIP_TIP_U - .01, rear + .01), (h69.LIP_TIP_U + LIP_LEAD, rear + .01)], 0, 40)
    return tower + b.box(stem, h69.POST_U[1], v[0] - POCKET_END[0] - .01, rear + .01, z1 - .01, h69.POST_TOP_Z)


def lid():
    plain = r61.prior.old.n.lid_plain()
    return (plain - b.to_world(lid_notch())) + b.to_world(h69._mirror_u(lid_post()))


def parts():
    one = h70.previous.one_piece
    return {POST_BAR: one(post_bar(), 'R80 post bar', limit=.001), LID: one(lid(), 'R80 retainer', limit=.001)}


# ------------------------------------------------------------------ measurements
def _rings(section):
    return np.vstack([np.asarray(ring) for ring in section.to_polygons()])


def _post_plan(bar, z, sign=1):
    """Rigid body and finger of one post at a height, as points about the post axis."""
    cell = bar.slice(float(z)) ^ _rect(sign * HOLE_X - 2.2, sign * HOLE_X + 2.2, HOLE_Y - 2.2, HOLE_Y + 2.2)
    pieces = [_rings(piece) - (sign * HOLE_X, HOLE_Y) for piece in cell.decompose() if piece.area() > .02]
    rigid = [p for p in pieces if p[:, 1].max() > 0]
    sprung = [p for p in pieces if p[:, 1].max() <= 0]
    return (np.vstack(rigid) if rigid else None), (np.vstack(sprung) if sprung else None)


def _seat(points, radius, dx):
    """The finger pushes the board forward until the hole's rear wall is on the body. Returns how
    far in front of the post axis the hole's centre then is (None: the body does not go in)."""
    inside = lambda cy: float(np.max(np.hypot(points[:, 0] - dx, points[:, 1] - cy))) <= radius + 1e-9
    grid = np.arange(-1.2, 1.2001, .002)
    ok = [cy for cy in grid if inside(cy)]
    return None if not ok else float(min(ok))


def _push(points, radius, centre):
    """How far the finger must move toward the body to stand inside the hole. Negative: it is
    short of the hole wall by that much, which is then the board's play."""
    reach = lambda d: float(np.max(np.hypot(points[:, 0] - centre[0], points[:, 1] + d - centre[1])))
    lo, hi = -1.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if reach(mid) > radius else (lo, mid)
    return hi


def spring():
    """Beam estimate of one arm and finger: the arm bends sideways and twists, the finger bends a
    little. Stations along the arm use the plan that is exported. Round-figure modulus. — Claude Fable 5.2"""
    plan = arm_plan()
    edges = np.linspace(HOLE_X, ANCHOR_HALF, 401)
    step = float(edges[0] - edges[1])
    xs = (edges[:-1] + edges[1:]) / 2
    thick = np.array([float((plan ^ _rect(float(x) - step / 2, float(x) + step / 2, -5., 5.)).area()) / step for x in xs])
    high = np.full(len(xs), ARM_TOP - BASE0)
    at_load, strain, _, _ = h.cantilever(xs, high, thick, step)                 # bending in the printed plane
    lever = (SEAT + TOP) / 2 - (BASE0 + ARM_TOP) / 2                             # the hole pushes the finger this far above the arm
    beta = 1 / 3 - .21 * (thick / high) * (1 - thick ** 4 / (12 * high ** 4))
    twist = float(np.sum(step / (PETG_E / 2.7 * beta * high * thick ** 3)))      # radians per N mm
    up = (SEAT + TOP) / 2 - BASE1
    width = 2 * FINGER_HALF
    stand = up ** 3 / (3 * PETG_E * width * FINGER_T ** 3 / 12)
    give = at_load / PETG_E + twist * lever ** 2 + stand                         # mm per N at the middle of the board
    share = at_load / PETG_E / give
    return dict(mm_per_n=round(give, 3), n_per_mm=round(1 / give, 3), share=dict(arm_bending=round(share, 2), arm_twist=round(twist * lever ** 2 / give, 2), finger_bending=round(stand / give, 2)),
                arm_bending_strain_per_mm_of_finger_travel=round(float(strain.max()) * share, 4),
                finger_root_stress_mpa_per_n=round(up / (width * FINGER_T ** 2 / 6), 1),
                arm=dict(length_mm=round(HOLE_X - ANCHOR_HALF, 2), across_mm=ARM_T, tall_mm=round(ARM_TOP - BASE0, 2), bends='in the printed plane, along continuous lines'),
                modulus_assumed_mpa=PETG_E, method='Euler beam and thin-bar torsion; an estimate, not a measured force')


def post_numbers(bar, old_bar, paddle):
    rigid, sprung = _post_plan(bar, SEAT + .5)
    old_rigid, _ = _post_plan(old_bar, SEAT + .1)
    old_top, _ = _post_plan(old_bar, TOP - .1)
    angle = lambda p: np.degrees(np.arctan2(np.abs(p[:, 0]), p[:, 1]))
    on = rigid[np.abs(np.hypot(rigid[:, 0], rigid[:, 1]) - LAND_R) < .003]
    lands = dict(on_a_circle_of_mm=2 * LAND_R, from_the_rear_deg=[round(float(angle(on).min()), 1), round(float(angle(on).max()), 1)],
                 each_land_width_mm=round(float(np.radians(angle(on).max() - angle(on).min()) * LAND_R), 2), lands_per_post=2,
                 full_section_height_mm=round(TOP - LEAD - SEAT, 2), board_thickness_mm=round(TOP - SEAT, 2))
    k = spring()
    box = lambda p: [round(float(v), 3) for v in (p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max())]
    holes = []
    for d in (2.90, 2.95, 3.00, 3.05, 3.10, 3.15, 3.20, 3.25, 3.30):
        e = _seat(rigid, d / 2, 0.)
        row = dict(hole_mm=d, body_goes_in=e is not None)
        if e is not None:
            push = _push(sprung, d / 2, (0., e))
            row.update(hole_centre_in_front_of_the_post_axis_mm=round(-e, 3), finger_pushed_in_mm=round(max(push, 0.), 3), board_play_fore_and_aft_mm=round(max(-push, 0.), 3),
                       finger_force_n=round(max(push, 0.) * k['n_per_mm'], 2), within_the_finger_travel=bool(push < SLOT - .04))
        holes.append(row)
    spacing = []
    for d in (3.00, 3.10, 3.20):
        for off in (.1, .2, .3):
            e = _seat(rigid, d / 2, off / 2)                                      # the mismatch is shared by the two posts
            row = dict(hole_mm=d, hole_spacing_off_by_mm=off, goes_on=e is not None)
            if e is not None:
                push = _push(sprung, d / 2, (off / 2, e))
                row.update(board_shifts_toward_the_hinge_mm=round(e - (_seat(rigid, d / 2, 0.) or 0.), 3), finger_pushed_in_mm=round(max(push, 0.), 3),
                           goes_on=bool(push < SLOT - .02))
            spacing.append(row)
    up = bar ^ b.box(-20, 20, 0, 40, BASE1 + .05, SEAT - .01)
    fingers = b.mirrored(b.box(HOLE_X - FINGER_HALF - .2, HOLE_X + FINGER_HALF + .2, HOLE_Y - 3., HOLE_Y + FINGER_IN + .02, BASE1 - .15, 40))
    rigid_bar = bar - fingers
    wall = -PASSAGE[1]
    lift = np.arange(0, 9.01, .25)
    clip_rows = {}
    for side, path in h.R59_CLIPS.items():
        clip = b.load(path)
        sweep = lambda stock: np.array([float((stock ^ clip.translate((0, -float(t), 0))).volume()) for t in np.linspace(0, 8, 81)])
        now, was = sweep(bar), sweep(old_bar)
        room = h.NECK - float(clip.bounding_box()[5] - clip.bounding_box()[2])
        clip_rows[side] = dict(slide_poses=len(now), most_extra_overlap_against_r71_mm3=round(float((now - was).max()), 5), seated_overlap_mm3=round(float(now[0]), 5),
                               peak_snap_overlap_mm3=dict(r71=round(float(was.max()), 4), r80=round(float(now.max()), 4)),
                               board_lift_under_the_clip_mm=round(room, 2), head_holds_a_lifted_clip_mm3=round(float((bar ^ clip.translate((0, 0, room + .15))).volume()), 4))
    above = lambda stock: stock ^ b.box(-20, 20, 0, 40, TOP + .005, 40)
    return dict(
        paddle_hole_half_sizes_mm=list(PASSAGE), paddle_hole_corner_from_its_centre_mm=round(float(np.hypot(*PASSAGE)), 2),
        section_in_the_board=dict(r71_at_the_seat_box_mm=box(old_rigid), r71_at_the_board_top_box_mm=box(old_top), r80_rigid_body_box_mm=box(rigid), r80_finger_box_mm=box(sprung),
                                  r80_body_and_finger_across_mm=[round(float(rigid[:, 0].max() - rigid[:, 0].min()), 2), round(float(rigid[:, 1].max() - sprung[:, 1].min()), 2)],
                                  r71_across_mm=[m.chain().POST_W, m.chain().POST_L], r71_rib_crest_width_mm=h70.RIB_LAND_WIDTH, r71_full_rib_height_mm=h.RIB_FULL),
        lands=lands,
        finger=dict(wide_mm=2 * FINGER_HALF, stem_thick_mm=FINGER_T, stem_front_face_mm=FINGER_OUT, head_free_front_face_mm=HEAD_OUT, head_face_on_a_circle_of_mm=2 * HEAD_R,
                    head_beyond_a_3_0_hole_wall_mm=round(-LAND_R - HEAD_OUT, 2), travel_before_it_meets_the_body_mm=SLOT,
                    full_face_in_the_board_z_mm=[round(HEAD_FROM + FINGER_OUT - HEAD_OUT, 2), round(FINGER_TOP - FINGER_LEAD, 2)],
                    full_face_left_in_a_board_lifted_0_8_mm=round(FINGER_TOP - FINGER_LEAD - (SEAT + .8), 2), top_z_mm=FINGER_TOP, spring=k),
        holes=holes, hole_spacing=spacing,
        through_the_paddle=dict(everything_but_the_fingers_pushed_up_from_9_mm_below_mm3=max(round(float((rigid_bar.translate((0, 0, -float(t))) ^ paddle).volume()), 5) for t in lift),
                                finger_heads_stand_past_the_paddle_hole_wall_mm=round(wall - HEAD_OUT, 2), each_finger_gives_while_the_bar_goes_in_mm=round(wall - HEAD_OUT, 2),
                                finger_travel_mm=SLOT, free_bar_pushed_up_meets_the_paddle_mm3=max(round(float((bar.translate((0, 0, -float(t))) ^ paddle).volume()), 4) for t in lift),
                                heads_hold_the_bar_up_in_the_paddle=bool(wall - HEAD_OUT > .1),
                                seated_mm3=round(float((bar ^ paddle).volume()), 5), post_and_finger_to_the_paddle_hole_mm=round(float(up.min_gap(paddle, 2.)), 3),
                                r71_post_to_the_paddle_hole_mm=round(float((old_bar ^ b.box(-20, 20, 0, 40, BASE1 + .05, 40)).min_gap(paddle, 2.)), 3),
                                bar_below_the_paddle_to_it_mm3=round(float(((bar ^ b.box(-20, 20, 0, 40, 0, BASE1 - .02)) ^ paddle).volume()), 5)),
        flat_clips=clip_rows,
        above_the_board=dict(differs_from_r71_mm3=round(float((above(bar) - above(old_bar)).volume() + (above(old_bar) - above(bar)).volume()), 5),
                             post_top_z_mm=round(float(bar.bounding_box()[5]), 2), r71_post_top_z_mm=round(float(old_bar.bounding_box()[5]), 2)),
        bar=dict(z_mm=[BASE0, BASE1], box_mm=[round(float(v), 2) for v in bar.bounding_box()], r71_box_mm=[round(float(v), 2) for v in old_bar.bounding_box()],
                 solids=len(bar.decompose()), slot_mm=SLOT, post_spacing_mm=2 * HOLE_X))


def click_numbers(bar, old_bar, new_lid, old_lid, paddle, carrier):
    """The moving paddle with its bar and clips against everything fixed, R79 beside R80. — Claude Fable 5.2"""
    import hinge_fit64 as fit
    k, vol = fit.k, fit.vol
    k.old.configure_new_op1()
    hw = k.q.hardware()
    rot = h.rotate
    stop = k.onset(lambda a: vol(rot(paddle, a), hw['switch']) > .001, 0, 4, 24)
    start = k.onset(lambda a: vol(rot(paddle, a), hw['plunger']) > .001, 0, stop, 24)
    zone = lambda u0, u1: b.to_world(b.box(u0, u1, -3.6, 1.2, 12.0, 15.36))
    legs = dict(left=paddle ^ zone(-6.2, -3.5), right=paddle ^ zone(3.5, 6.2))
    station = np.array([0., b.STATION[1], b.FREE_TOP - .8])
    rear = lambda t: b.to_world(b.box(-9, 9, float(t), 20, 0, 40))
    clips = b.union([b.load(path) for path in h.R59_CLIPS.values()])
    under = hw['board'] + b.union(hw[n] for n in ('sockets', 'housing', 'plug', 'terminals', 'fasteners'))

    def lean(shape, roll, shift, heel):
        tilt = np.degrees(heel / (h.AXIS - station[1]))
        return shape.translate(-station).rotate((tilt, roll, 0)).translate(station + np.array([shift, 0, 0]))

    def one(lid_, bar_):
        lift = k.first_true(lambda a: vol(rot(paddle, -a), lid_) > .00001, list(np.linspace(0, 6, 241)))
        fixed = carrier + lid_ + under
        rows = {}
        for label, a in (('rest', 0.), ('full_click', stop), ('quarter_degree_past_full_click', stop + .25)):
            row = {}
            for side, leg in legs.items():
                q = rot(leg, a)
                down = next((round(float(t), 2) for t in np.arange(0, 3.01, .02) if vol(q.translate((0, 0, -float(t))), fixed) > .0005), 3.0)
                up = next((round(float(t), 2) for t in np.arange(0, 3.01, .02) if vol(q.translate((0, 0, float(t))), lid_) > .0005), 3.0)
                along = [next((round(float(t), 2) for t in np.arange(0, 2.01, .02) if vol(q.translate(tuple(np.asarray(b.board_matrix())[:, 1] * s * float(t))), lid_) > .0005), 2.0) for s in (-1, 1)]
                row[side] = dict(straight_down_mm=down, straight_up_to_the_lip_mm=up, along_the_pocket_mm=dict(toward_the_front=along[0], toward_the_hinge=along[1]), nearest_retainer_mm=round(float(q.min_gap(lid_, 3.)), 3))
            rows[label] = row
        front = paddle ^ b.box(-40, 40, -40, 26., -20, 40)
        worst = []
        for roll, shift in ((0., 0.), (.45, .1), (-.45, -.1), (.8, .2), (-.8, -.2)):
            heel = .35 if abs(roll) > .5 else 0.
            q = lean(rot(front + bar_, stop + .25), roll, shift, heel)
            worst.append(dict(roll_deg=roll, shift_mm=shift, hinge_end_lifted_mm=heel, to_the_retainer_mm=round(float(q.min_gap(lid_, 3.)), 3), into_the_retainer_mm3=round(vol(q, lid_), 5),
                              to_the_holder_mm=round(float(q.min_gap(carrier ^ b.box(-40, 40, -40, 26., -20, 40), 3.)), 3), to_the_op1_board_and_its_parts_mm=round(float(q.min_gap(under, 3.)), 3)))
        riding = bar_ + clips
        poses = np.linspace(-lift + .025, stop - .035, 19)
        rigid = carrier + lid_ + h.pin() + b.union(hw[n] for n in ('board', 'plug', 'sockets', 'op1_wire', 'housing', 'terminals', 'switch'))
        return dict(paddle_lifts_before_the_lips_stop_it_deg=round(float(lift), 3), feet=rows, pressed_a_quarter_degree_too_far_and_leaning=worst,
                    least_gap_past_full_click_mm=min(min(r['to_the_retainer_mm'], r['to_the_holder_mm'], r['to_the_op1_board_and_its_parts_mm']) for r in worst),
                    bar_and_clips_through_lift_and_click=dict(poses=len(poses), into_fixed_parts_mm3=max(round(vol(rot(riding, a), rigid), 5) for a in poses),
                                                              least_gap_mm=round(min(float(rot(riding, a).min_gap(rigid, 5.)) for a in poses), 3)))

    frame = lambda s: s.transform(np.linalg.inv(np.vstack([np.asarray(b.board_matrix()), [0, 0, 0, 1]]))[:3].tolist()).rotate((90, 0, 0))

    def tine(lid_):
        body = frame(lid_)
        # checks69.retainer_sections: every station from -4.5 to 2.0, each tine's whole section
        out = {}
        for side, u0 in (('left', -7.21), ('right', 3.59)):
            rows = [(float((body.slice(float(v)) ^ _rect(u0, u0 + 3.62, -17., -10.8)).area()), round(float(v), 2)) for v in np.arange(-4.5, 2.001, .05)]
            out[side] = dict(least_mm2=round(min(rows)[0], 3), at_station_mm=min(rows)[1],
                             beside_the_foot_ends_mm2=[round(a, 3) for a, v in rows if v in (-3.75, -3.5, 1.0, 1.25)])
        return out

    cover = lambda lid_: round(float((lid_ ^ b.to_world(b.box(-9, 9, b.RAIL_START, 20, b.LID_Z[0], b.LID_Z[1]))).volume()), 3)
    return dict(button_contact_deg=round(float(start), 4), full_click_deg=round(float(stop), 4), r79=one(old_lid, old_bar), r80=one(new_lid, bar),
                retainer=dict(tine_section=dict(r79=tine(old_lid), r80=tine(new_lid), r59_mm2=TINE_R59, checks69_asks_mm2=round(.95 * TINE_R59, 3), this_source_keeps_mm2=TINE_MIN),
                              lip_runs_past_the_leg_mm=dict(front=LIP_FRONT, rear=POCKET_END[1]), lip_lead_in_mm=LIP_LEAD,
                              old_lip_and_post_lost_mm3=round(float(((old_lid - new_lid) ^ b.to_world(b.box(-9, 9, -9, 9, b.LID_Z[1] + .02, 40))).volume()), 5),
                              plate_under_the_holder_rails_mm3=dict(r79=cover(old_lid), r80=cover(new_lid)),
                              removed_mm3=round(float((old_lid - new_lid).volume()), 3), added_mm3=round(float((new_lid - old_lid).volume()), 3),
                              solids=len(new_lid.decompose()), pocket_beyond_the_leg_mm=dict(r79=list(h69.NOTCH_V_CLEAR), r80=list(POCKET_END)), floor_open_beyond_the_leg_mm=WINDOW_END))


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    made = parts()
    for name, shape in made.items():
        b.save_closed(OUT / name, shape)
    digest = lambda path: sha256(Path(path).read_bytes()).hexdigest()
    bar, new_lid = b.load(OUT / POST_BAR), b.load(OUT / LID)
    old_bar, old_lid = b.load(h.OUT / POST_BAR), b.load(h.OUT / LID)
    paddle, carrier = b.load(REUSED['Touch_Paddle']), b.load(REUSED['Key_Carrier'])
    posts = post_numbers(bar, old_bar, paddle)
    click = click_numbers(bar, old_bar, new_lid, old_lid, paddle, carrier)
    report = dict(revision='R80', physical_fit_verified=False, sliced=False,
                  written={name: digest(OUT / name) for name in made},
                  reused={name: dict(file=str(Path(path).relative_to(HERE.parent)), sha256=digest(path)) for name, path in REUSED.items()},
                  compared_with=dict(post_bar=digest(h.OUT / POST_BAR), retainer=digest(h.OUT / LID)), posts=posts, click=click,
                  not_known=['the real diameter and spacing of the board holes', 'the printed size of the lands and finger', 'creep of the arm under a small hole',
                             'which surface the paddle touched on the printed R79'])
    print(json.dumps(report, indent=1), flush=True)
    p, c = posts, click
    assert p['bar']['solids'] == 1 and c['retainer']['solids'] == 1
    through = p['through_the_paddle']
    assert through['everything_but_the_fingers_pushed_up_from_9_mm_below_mm3'] == 0 and through['seated_mm3'] == 0 and through['post_and_finger_to_the_paddle_hole_mm'] >= .05
    assert through['each_finger_gives_while_the_bar_goes_in_mm'] < SLOT - .1
    assert all(row['most_extra_overlap_against_r71_mm3'] < .002 and row['seated_overlap_mm3'] < .001 and row['head_holds_a_lifted_clip_mm3'] > .1 for row in p['flat_clips'].values())
    assert p['above_the_board']['differs_from_r71_mm3'] < .001 and p['above_the_board']['post_top_z_mm'] == p['above_the_board']['r71_post_top_z_mm']
    fit = {row['hole_mm']: row for row in p['holes']}
    assert all(fit[d]['body_goes_in'] and fit[d]['within_the_finger_travel'] for d in (2.95, 3.0, 3.1, 3.2)) and fit[3.0]['finger_pushed_in_mm'] > .15 and fit[3.2]['board_play_fore_and_aft_mm'] == 0
    assert all(row['goes_on'] for row in p['hole_spacing'] if row['hole_spacing_off_by_mm'] <= .2)
    assert p['finger']['spring']['arm_bending_strain_per_mm_of_finger_travel'] * SLOT < .02
    now, was = c['r80'], c['r79']
    assert now['paddle_lifts_before_the_lips_stop_it_deg'] == was['paddle_lifts_before_the_lips_stop_it_deg'], 'the upper catch moved'
    keeper = c['retainer']
    assert keeper['old_lip_and_post_lost_mm3'] < .001, 'the upper catch lost material'
    # The R69 keeper rule: no station of either tine below 95 % of R59's section. This source keeps more, for the slice.
    assert all(side['least_mm2'] >= TINE_MIN > .95 * TINE_R59 for side in keeper['tine_section']['r80'].values()), keeper['tine_section']['r80']
    for side in ('left', 'right'):
        f, g = now['feet']['full_click'][side], was['feet']['full_click'][side]
        assert f['straight_down_mm'] >= g['straight_down_mm'] + .3 and min(f['along_the_pocket_mm'].values()) >= min(g['along_the_pocket_mm'].values()) + .15
        assert now['feet']['rest'][side]['straight_up_to_the_lip_mm'] == was['feet']['rest'][side]['straight_up_to_the_lip_mm']
    assert abs(c['retainer']['plate_under_the_holder_rails_mm3']['r80'] - c['retainer']['plate_under_the_holder_rails_mm3']['r79']) < .01, 'the pocket reached under the rails'
    assert now['least_gap_past_full_click_mm'] >= was['least_gap_past_full_click_mm'] and now['bar_and_clips_through_lift_and_click']['into_fixed_parts_mm3'] == 0
    assert max(r['into_the_retainer_mm3'] for r in now['pressed_a_quarter_degree_too_far_and_leaning']) == 0
    report['passes'] = True
    (OUT / 'posts80.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    build()
