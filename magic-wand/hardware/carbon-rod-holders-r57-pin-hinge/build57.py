"""R57 pin hinge and longer touch-board posts. Millimetres, R53 assembly frame.

Changed bodies
    Key_Carrier    R53 key holder with the open yoke replaced by two thick cheeks, each with one hole.
    Touch_Paddle   R53 sleeve and crowns unchanged. New barrel with one through hole and a clip well.
                   The top now touches the touch board only at its pad end, two edge rails and
                   round the two post holes, so parts or pin tails under the board hang free.
    Hinge_Pin      Plain 3 mm rod with one waist in the middle.
    Pin_Clip       Peg that drops into the well and snaps over the waist, so the rod cannot wander.
    DFR_Post_Bar   The R48 posts with a 2.2 mm clip neck in place of 1.0 mm.
    DFR_Tall_Clip  Optional 2.0 mm clip for a board that sits flat on the paddle.

Unchanged and reused: OP1_Lid, both 0.8 mm post clips, every bought part.
Nothing here is a claim of physical fit.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R53 = HERE.parent / "carbon-rod-holders-r53-guided-op1"
sys.path.insert(0, str(R53))
import build53 as b  # noqa: E402

EXPORT = HERE / "exports"

# ---- hinge: loose fits, sized for a 0.4 mm nozzle
AXIS_Y = b.AXIS_Y                 # 29.3, as R53, so the click lever is unchanged
PIN_R = 1.50
CHEEK_HOLE_R = 1.75               # 0.25 mm all round the pin
BARREL_HOLE_R = 1.80              # 0.30 mm all round the pin
CHEEK_HOLE_Z = 16.50
REST = 0.02                       # modelled contacts keep this much air so faceted circles do not overlap
PIN_Z = CHEEK_HOLE_Z - (CHEEK_HOLE_R - PIN_R) + REST      # the pin lies on the bottom of the cheek holes
BARREL_HOLE_Z = PIN_Z - (BARREL_HOLE_R - PIN_R) + REST    # the paddle hangs on top of the pin
ROOF = 0.30                       # the flat that closes each printed hole sits this far beyond its radius
CHEEK_X = (7.4, 11.5)
CHEEK_FRONT = 25.35
CHEEK_TOP = 20.5
BARREL_X = 7.1                    # 0.3 mm to each cheek
BARREL_R = 3.3
BARREL_Y = (25.75, 32.6)
WELL = (1.0, 26.8, 31.8)          # half width, front, rear of the clip well
PIN_HALF = 10.9
WAIST = (0.75, 0.95)              # half length and radius of the pin waist
CLIP_T = 1.2

# ---- paddle top
FRONT_END = 7.5                   # the solid pad-end zone stops here
RAIL = (8.6, b.PLATE_X, 20.5, 15.3)   # inner X, outer X, rear end, underside
PAD = (5.9, 12.6, 18.1)           # inner X, front, rear of the land round each post hole
STRUT_Z = (14.9, 17.3)            # 2 mm below the board

# ---- posts
NECK = 2.2                        # was 1.0
HEAD = 0.8
TALL_CLIP = 2.0


def hinge_matrix(angle):
    """Paddle pose about the resting pin. Positive angle lowers the front edge."""
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    basis = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    pivot = np.array([0, AXIS_Y, PIN_Z])
    return np.column_stack([basis, pivot - basis @ pivot]).tolist()


def posed(shape, angle):
    return shape.transform(hinge_matrix(angle))


def hole_section(y, z, radius, toward):
    """Round hole closed by two 45 degree faces and a short flat on the side that prints last."""
    d = np.array(toward, float)
    d /= np.linalg.norm(d)
    p = np.array([-d[1], d[0]])
    t = radius + ROOF
    half = radius * math.sqrt(2) - t
    circle = mf.CrossSection.circle(radius, 72)
    tips = b._section([tuple(d * t - p * half), tuple(d * t + p * half), tuple(d * (t - 0.05))])
    return mf.CrossSection.batch_hull([circle, tips]).translate((float(y), float(z)))


def along_x(section, x0, x1):
    return b.prism_yz(section.to_polygons()[0], x0, x1)


def taper(y, z, radius, toward, face, inward, relief):
    """Entry relief: the hole section opened by `relief` at the face, back to size `relief` deep."""
    wide = along_x(hole_section(y, z, radius + relief, toward), *sorted((face - 0.02 * inward, face + 0.01 * inward)))
    deep = along_x(hole_section(y, z, radius, toward), *sorted((face + relief * inward, face + (relief + 0.01) * inward)))
    return mf.Manifold.batch_hull([wide, deep])


def hole(y, z, radius, toward, x0, x1, relief=0.6):
    """Through hole along X with a tapered entry at both ends."""
    cut = along_x(hole_section(y, z, radius, toward), x0 - 0.02, x1 + 0.02)
    return cut + taper(y, z, radius, toward, x0, 1, relief) + taper(y, z, radius, toward, x1, -1, relief)


# ------------------------------------------------------------------ carrier
def cheeks():
    rear = b.CARRIER_REAR
    # The front 1.25 mm stays below a 35 mm touch board's rear corners; the full height starts behind it.
    profile = [(rear, 10.6), (CHEEK_FRONT, 10.6), (CHEEK_FRONT, 18.9), (CHEEK_FRONT + 1.25, 18.9),
               (CHEEK_FRONT + 2.25, CHEEK_TOP), (rear - 0.6, CHEEK_TOP), (rear, CHEEK_TOP - 0.6)]
    block = b.prism_yz(profile, *CHEEK_X)
    # Soften the outer top edge beside the upper keys.
    block -= b.prism_xz([(CHEEK_X[1] + 0.01, CHEEK_TOP - 0.6), (CHEEK_X[1] + 0.01, CHEEK_TOP + 0.01),
                         (CHEEK_X[1] - 0.6, CHEEK_TOP + 0.01)], CHEEK_FRONT - 1, rear + 1)
    # The rear face is on the bed, so each hole closes toward the front.
    block -= hole(AXIS_Y, CHEEK_HOLE_Z, CHEEK_HOLE_R, (-1, 0), *CHEEK_X)
    return b.mirrored(block)


def carrier():
    body = b.load(R53 / "exports/Key_Carrier-assembly.stl")
    # Remove the R53 open seats, dovetail walls and rear wall down to the deck.
    body -= b.box(-11.62, 11.62, 27.0, 33.0, 11.35, 30)
    body -= b.mirrored(b.box(7.1, 11.62, 27.0, 33.0, 11.12, 30))
    return body + cheeks()


# ------------------------------------------------------------------- paddle
def barrel():
    y0, y1 = BARREL_Y
    z = BARREL_HOLE_Z
    arc = [(AXIS_Y + BARREL_R * math.cos(a), z + BARREL_R * math.sin(a)) for a in np.linspace(0, -math.pi, 49)]
    profile = [(y0, b.SEAT_Z), (y1, b.SEAT_Z), *arc, (y0, z + 0.25)]
    solid = b.prism_yz(profile, -BARREL_X, BARREL_X)
    # The top is on the bed, so the hole closes toward the underside.
    solid -= hole(AXIS_Y, z, BARREL_HOLE_R, (0, -1), -BARREL_X, BARREL_X)
    half, front, rear = WELL
    well = b.box(-half, half, front, rear, 0, 40)
    well += taper(AXIS_Y, z, BARREL_HOLE_R, (0, -1), -half, -1, 0.5) + taper(AXIS_Y, z, BARREL_HOLE_R, (0, -1), half, 1, 0.5)
    return solid - well


def paddle():
    x, r, front = b.PLATE_X, 1.5, b.PLATE_FRONT
    outline = [(-x + r, front), (x - r, front), (x, front + r), (x, FRONT_END), (-x, FRONT_END), (-x, front + r)]
    plate = b.prism_xy(outline, b.PLATE_Z, b.SEAT_Z)
    footprint = b.prism_xy(outline, 0, 40)
    ring, cavity, lands = (b.to_world(s) for s in b.sleeve_parts())
    ribs = b.mirrored(b.box(b.RIB_X[0], b.RIB_X[1], front + 3.0, FRONT_END + 0.01, b.RIB_Z, b.PLATE_Z + 0.01))
    ribs -= b.mirrored(b.prism_yz([(front + 2.9, b.RIB_Z - 0.01), (front + 2.9, b.PLATE_Z), (front + 4.7, b.RIB_Z - 0.01)],
                                  b.RIB_X[0] - 0.1, b.RIB_X[1] + 0.1))
    body = plate + ((ring + ribs) ^ footprint)
    body -= cavity
    body += lands ^ footprint
    body += b.to_world(b.union(b.crown(s) for s in (0.0, b.MIRROR_STATION)))
    # Two edge rails and a land round each post hole carry the board behind the pad end.
    x0, x1, rail_end, rail_z = RAIL
    rails = b.mirrored(b.box(x0, x1, FRONT_END - 0.1, rail_end, rail_z, b.SEAT_Z))
    rails -= b.mirrored(b.prism_yz([(FRONT_END - 0.11, rail_z - 0.01), (FRONT_END - 0.11, b.RIB_Z),
                                    (FRONT_END + 0.6, rail_z - 0.01)], x0 - 0.1, x1 + 0.1))
    pad_x, pad_front, pad_rear = PAD
    pads = b.mirrored(b.box(pad_x, x0 + 0.01, pad_front, pad_rear, b.PLATE_Z, b.SEAT_Z))
    # Room for the post bar base under the lands.
    rails -= b.mirrored(b.box(x0 - 0.1, b.HOLE_X + 1.5, b.HOLE_Y - 1.65, b.HOLE_Y + 1.65, 0, b.PLATE_Z))
    # Two sunk struts run from the rails to the barrel and pass inside the holder cheeks.
    z0, z1 = STRUT_Z
    strut = mf.Manifold.batch_hull([b.box(x0 - 0.2, x1, rail_end - 0.9, rail_end, z0, z1),
                                    b.box(4.2, BARREL_X - 0.1, BARREL_Y[0] - 0.05, BARREL_Y[0] + 0.5, z0, z1)])
    strut -= b.box(BARREL_X + 0.05, 20, CHEEK_FRONT - 0.75, 40, 0, 40)
    body += rails + pads + b.mirrored(strut) + barrel()
    body -= b.mirrored(b.box(b.HOLE_X - 1.33, b.HOLE_X + 1.33, b.HOLE_Y - 1.47, b.HOLE_Y + 1.47, 0, 40))
    return body


# ------------------------------------------------------------ pin and clip
def hinge_pin():
    reach = PIN_HALF - 0.5

    def disc(x, radius):
        return mf.Manifold.cylinder(0.01, radius, radius, 64).rotate((0, 90, 0)).translate((x, 0, 0))

    rod = mf.Manifold.batch_hull([disc(-reach, PIN_R), disc(reach, PIN_R)])
    rod += mf.Manifold.batch_hull([disc(reach - 0.01, PIN_R), disc(PIN_HALF - 0.01, PIN_R - 0.5)])
    rod += mf.Manifold.batch_hull([disc(-reach, PIN_R), disc(-PIN_HALF, PIN_R - 0.5)])
    # One flat to lie on the bed.
    rod -= b.box(-20, 20, -5, 5, -5, -1.2)
    half, radius = WAIST
    rod -= b.box(-half, half, -5, 5, -5, 5)
    rod += mf.Manifold.batch_hull([disc(-half - 0.3, radius), disc(half + 0.3, radius)])
    return rod.translate((0, AXIS_Y, PIN_Z))


def pin_clip():
    """Peg profile in (Y, Z) about the pin axis, CLIP_T thick. Two legs spring over the waist.

    The wide grip stops on the paddle top behind the well and stays behind a 35 mm touch board.
    """
    leg, slot, mouth = 1.95, 0.975, 0.85
    seat = b.SEAT_Z - PIN_Z + 0.05
    top = b.BOARD_TOP - PIN_Z
    outer = [(-leg, -2.65), (-leg, seat), (-2.4, seat), (-2.4, top), (3.3, top), (3.3, seat), (leg, seat), (leg, -2.65)]
    inner = [(-1.05, -2.66), (-mouth, -1.95), (-mouth, -1.40), (-slot, -1.15), (-slot, 0.85), (-0.3, 1.25), (-0.3, 3.35),
             (0.3, 3.35), (0.3, 1.25), (slot, 0.85), (slot, -1.15), (mouth, -1.40), (mouth, -1.95), (1.05, -2.66)]
    shape = b.prism_yz(outer, -CLIP_T / 2, CLIP_T / 2) - b.prism_yz(inner, -1, 1)
    return shape.translate((0, AXIS_Y, PIN_Z))


# ----------------------------------------------------------------- post bar
def chain():
    sys.path.insert(0, str(b.R52))
    sys.path.insert(0, str(b.R51))
    import build52 as d
    return d.r


def post(r, neck=NECK, head=HEAD):
    """The R31 post with a longer clip neck. Same shaft, neck and head sections, so the old clips fit."""
    z0, z1 = b.BOARD_TOP, b.BOARD_TOP + neck
    top = z1 + head
    section = r._section(r.POST_W, r.POST_L)
    shaft = r._prism(section, b.PLATE_Z - 0.01, z0)
    waist = r._prism(mf.CrossSection.batch_hull([mf.CrossSection.circle(r.NECK_R, 48), r._point(r.POST_L / 2)]),
                     z0 - 0.01, z1 + 0.01)
    cap = mf.Manifold.batch_hull([r._prism(section, z1, top - 0.3),
                                  r._prism(r._section(r.POST_W - 0.6, r.POST_L - 0.6), top - 0.01, top)])
    # As R31: the head grows from the neck on a 45 degree ramp in the front-down print.
    under = r.d.wedge(-2.0, 2.0, [(-3.0, z1), (-r.NECK_R, z1), (-r.NECK_R + 1.8, z1 + 1.8), (-3.0, z1 + 1.8)])
    return b.union((shaft, waist, cap)) - under


def post_bar(r):
    one = post(r)
    posts = b.union(one.translate((s * b.HOLE_X, b.HOLE_Y, 0)) for s in (-1, 1))
    bounds = one.bounding_box()
    base = b.box(-b.HOLE_X - 1.3, b.HOLE_X + 1.3, b.HOLE_Y + bounds[1], b.HOLE_Y + bounds[4], b.PLATE_Z - 1.8, b.PLATE_Z)
    return posts + base


def tall_clip(r):
    """The R31 clip outline, 2.0 mm thick, for a board that sits flat. Modelled on the left post."""
    flat = r.clip_local().translate((0, 0, -r.NECK[0]))
    return flat.scale((1, 1, TALL_CLIP / r.CLIP_T)).translate((-b.HOLE_X, b.HOLE_Y, b.BOARD_TOP))


def parts():
    r = chain()
    return {"Key_Carrier": carrier(), "Touch_Paddle": paddle(), "Hinge_Pin": hinge_pin(), "Pin_Clip": pin_clip(),
            "DFR_Post_Bar": post_bar(r), "DFR_Tall_Clip": tall_clip(r)}


def main(output=None):
    output = Path(output) if output else EXPORT
    output.mkdir(parents=True, exist_ok=True)
    records = {}
    for name, shape in parts().items():
        pieces = sorted(shape.decompose(), key=lambda s: -s.volume())
        loose = [round(p.volume(), 5) for p in pieces[1:]]
        print(name, [round(float(v), 3) for v in shape.bounding_box()], "pieces", len(pieces), loose[:6], flush=True)
        limit = (0.11, 0.6) if name == "Key_Carrier" else (0.001, 0.001)
        if any(v > limit[0] for v in loose) or sum(loose) > limit[1]:
            raise ValueError(f"{name} has detached material: {loose[:8]}")
        path = output / f"{name}-assembly.stl"
        mesh = b.save_closed(path, pieces[0])
        records[name] = dict(sha256=sha256(path.read_bytes()).hexdigest(), volume_mm3=round(float(mesh.volume), 3),
                             bounds_mm=[round(float(v), 3) for v in pieces[0].bounding_box()])
    (output / "dimensions.json").write_text(json.dumps(dict(
        meshes=records, hinge_axis_world_yz_mm=[AXIS_Y, PIN_Z], pin_diameter_mm=2 * PIN_R, pin_length_mm=2 * PIN_HALF,
        cheek_hole_diameter_mm=2 * CHEEK_HOLE_R, barrel_hole_diameter_mm=2 * BARREL_HOLE_R,
        cheek_width_mm=CHEEK_X[1] - CHEEK_X[0], barrel_to_cheek_gap_mm=CHEEK_X[0] - BARREL_X,
        post_neck_mm=NECK, post_head_top_above_board_mm=NECK + HEAD, tall_clip_mm=TALL_CLIP,
        reused_from_r53=dict(OP1_Lid=sha256((R53 / "exports/OP1_Lid-assembly.stl").read_bytes()).hexdigest())), indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
