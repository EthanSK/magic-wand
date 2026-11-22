"""R59 click-side parts. Millimetres, R53 assembly frame. The paddle, pins and post bar are unchanged.

Pin_Clip        The R57 pin clip with the front of its grip lowered 0.95 mm and the rest 0.5 mm. That part of the
                grip stood level with the top of the touch board, directly behind the board's
                side-entry Gravity socket, where the bought plug and its three wires leave.
DFR_Clip_Left / DFR_Clip_Right
                The R31 touch-board post clip at 1.4 mm thick instead of 0.8 mm. Same outline,
                bore and mouth, so the snap is unchanged. The R57 post neck is 2.2 mm long.
OP1_Lid_Stop    The R58 stop retainer with each tower stem carried 2.9 mm further forward and a
                small fillet at its root. The inner lip is shortened so the paddle clears in
                off-centre presses while the remaining sloped face limits upward lift.

Nothing here is a claim of physical fit or strength.
"""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "carbon-rod-holders-r58-smooth-click"))
import build58 as n  # noqa: E402

m, b = n.m, n.b
EXPORT = n.EXPORT if n.EXPORT != n.HERE / "exports" else HERE / "exports"

GRIP_LOW = 0.60                      # grip height left above the paddle top in front of the pin
GRIP_FRONT = (-2.5, -0.35)           # that part of the grip, fore and aft from the pin axis; it stops short of the centre slit
GRIP_REAR = 1.05                     # grip height left behind that, over the centre slit
CLIP_T = 1.4                         # post clip thickness (R31: 0.8)
STEM_FROM_Y = -5.1                   # tower stems start here along the board (R58: -2.2)
ROOT = 0.3                           # fillet at the stem root
TIP_RELIEF = 0.50                    # remove the top inside edge reached by an offset press


def pin_clip():
    seat = b.SEAT_Z + 0.05
    cut = b.box(-2, 2, m.AXIS_Y + GRIP_FRONT[0], m.AXIS_Y + GRIP_FRONT[1], seat + GRIP_LOW, 40)
    # The rest of the grip, which is the part you pinch, comes down 0.5 mm.
    cut += b.box(-2, 2, m.AXIS_Y + GRIP_FRONT[1] - 0.01, m.AXIS_Y + 4.0, seat + GRIP_REAR, 40)
    return m.pin_clip() - cut


def post_clips():
    r = m.chain()
    flat = r.clip_local().translate((0, 0, -r.NECK[0])).scale((1, 1, CLIP_T / r.CLIP_T))
    left = flat.translate((-b.HOLE_X, b.HOLE_Y, b.BOARD_TOP))
    return left, left.mirror((1.0, 0.0, 0.0)), r


def lid_stop():
    stem = (n.WALL - n.WALL_TRIM) + n.FLANGE + n.STEM_CLEAR
    z1, base = b.LID_Z[1], n.TOWER_BASE_TOP
    longer = b.box(stem, b.LID_HALF, STEM_FROM_Y, b.TOWER_Y[0] + 0.01, z1 - 0.01, n.STOP_TOP)
    longer += b.box(b.TOWER_X[0], b.LID_HALF, STEM_FROM_Y, b.TOWER_Y[0] + 0.01, z1 - 0.01, base)
    fillet = b.prism_xz([(stem - ROOT, base - 0.01), (stem + 0.01, base - 0.01), (stem + 0.01, base + ROOT)], STEM_FROM_Y, b.TOWER_Y[1])
    tip = n.WALL - n.WALL_TRIM + n.SIDE_CLEAR
    relief = b.box(tip - 0.1, tip + TIP_RELIEF, b.TOWER_Y[0] - 0.02,
                   b.TOWER_Y[1] + 0.02, n.TOWER_BASE_TOP, n.STOP_TOP + 0.1)
    tower = n.stop_tower() + longer + fillet - relief
    return n.lid_plain() + b.to_world(b.mirrored(tower))


def parts():
    left, right, _ = post_clips()
    return {"Pin_Clip": pin_clip(), "DFR_Clip_Left": left, "DFR_Clip_Right": right, "OP1_Lid_Stop": lid_stop()}


def main(output=None):
    output = Path(output) if output else EXPORT
    output.mkdir(parents=True, exist_ok=True)
    (HERE / "exports").mkdir(exist_ok=True)
    records = {}
    for name, shape in parts().items():
        pieces = sorted(shape.decompose(), key=lambda s: -s.volume())
        loose = [round(float(p.volume()), 5) for p in pieces[1:]]
        print(name, [round(float(v), 3) for v in shape.bounding_box()], "pieces", len(pieces), loose[:4], flush=True)
        if any(v > 0.001 for v in loose):
            raise ValueError(f"{name} has detached material: {loose[:6]}")
        path = output / f"{name}-assembly.stl"
        mesh = b.save_closed(path, pieces[0])
        records[name] = dict(sha256=sha256(path.read_bytes()).hexdigest(), volume_mm3=round(float(mesh.volume), 3))
        if output.resolve() != (HERE / "exports").resolve():
            shutil.copy2(path, HERE / "exports" / path.name)
    stem = (n.WALL - n.WALL_TRIM) + n.FLANGE + n.STEM_CLEAR
    text = json.dumps(dict(meshes=records, pin_clip=dict(grip_front_lowered_mm=round(b.BOARD_TOP - (b.SEAT_Z + 0.05 + GRIP_LOW), 2), over_y_mm=[m.AXIS_Y + GRIP_FRONT[0], m.AXIS_Y + GRIP_FRONT[1]]),
                           post_clip=dict(thickness_mm=CLIP_T, r31_thickness_mm=0.8, post_neck_mm=m.NECK),
                           stop_retainer=dict(stem_thickness_mm=round(b.LID_HALF - stem, 2), stem_length_mm=dict(r58=round(b.TOWER_Y[1] - b.TOWER_Y[0], 2), r59=round(b.TOWER_Y[1] - STEM_FROM_Y, 2)),
                                              root_fillet_mm=ROOT)), indent=2) + "\n"
    for folder in {output, HERE / "exports"}:
        (folder / "dimensions59.json").write_text(text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
