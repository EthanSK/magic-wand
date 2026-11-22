"""R58 click parts. Millimetres, R53 assembly frame.

The R57 pin hinge is kept: same cheeks, same 3.0 mm pin, same clip. These bodies change:

Touch_Paddle    R57 paddle with
                  - one convex contact bar in place of the two round crowns,
                  - the barrel bore narrowed fore and aft only (3.4 mm slot, was a 3.6 mm round hole),
                  - beside the two tower stations, a thinner sleeve wall with a wider 45 degree
                    flange for the optional lift stop.
OP1_Lid_Plain   The R53 board retainer with its two towers removed. It cannot reach the paddle.
OP1_Lid_Stop    Optional. The same retainer with two set-back towers that only limit paddle lift.
Hinge_Pin_Snug  Optional 3.2 mm pin for the same holes and the same clip.

The key holder is built by carrier58.py. Nothing here is a claim of physical fit.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import manifold3d as mf

HERE = Path(__file__).resolve().parent
R57 = HERE.parent / "carbon-rod-holders-r57-pin-hinge"
sys.path.insert(0, str(R57))
import build57 as m  # noqa: E402

b = m.b
EXPORT = Path(os.environ.get("WAND_CAD_EXPORT_DIR", HERE / "exports"))

# ---- contact bar
STATIONS = (0.0, b.MIRROR_STATION)       # plunger station for a switch plugged in either way round
PLUNGER = (1.45, 0.6)                    # half size of the plunger top across and along the board

# ---- hinge: only the fore-aft width of the paddle bore changes
SLOT_HALF = m.PIN_R + 0.20               # the R57 round bore left 0.30 mm
SNUG_PIN_R = 1.60                        # optional pin; the standard pin stays 1.50

# ---- optional lift stop. R53 left 0.30 mm beside the sleeve and 0.50 mm of lift.
WALL = b.BODY_X + b.SLEEVE_GAP + b.SLEEVE_WALL   # outer face of the R57 sleeve wall, board frame
WALL_TRIM = 0.50                         # the sleeve wall is 0.7 mm thick beside the towers (elsewhere 1.2)
FLANGE = 1.40                            # stop flange width and height there (R53/R57: 0.80)
FLANGE_Y = (b.TOWER_Y[0] - 1.0, b.TOWER_Y[1] + 0.6)
SIDE_CLEAR = 0.90                        # tower lip to sleeve wall
STEM_CLEAR = 1.00                        # tower stem to flange tip
LIFT_GAP = 1.00
STOP_TOP = 16.50                         # R53 towers: 16.40; the holder channel is open to 16.60
TOWER_BASE_TOP = 13.40                   # full-width tower foot, below the flange at full press
TOWER_CUT = 0.6


def _bar(lift):
    # Both ends stop inside the solid plate, 0.2 mm under the board seat.
    inside = b.box(-10, 10, -10, 10, 0, b.SEAT_Z - 0.2)
    return mf.Manifold.batch_hull([b.crown(STATIONS[0]).translate((0, 0, lift)) ^ inside, b.crown(STATIONS[1]) ^ inside])


def contact_bar():
    """One convex bar through both plunger stations (board frame).

    A straight bar between two contact heights would sit a few hundredths lower over the rear
    edge of the standard plunger than the R57 crown did. The standard end is raised by that
    amount, so the bar meets a free plunger at the same paddle angle as R57.
    """
    x, y = PLUNGER
    footprint = b.box(-x, x, -y, y, b.BODY_TOP, b.SEAT_Z - 0.05)
    low, high = 0.0, 0.2
    for _ in range(30):
        lift = (low + high) / 2
        if float((_bar(lift) ^ footprint).bounding_box()[2]) < b.FREE_TOP:
            low = lift
        else:
            high = lift
    return _bar(high)


def reslot(body):
    """Refill the straight part of the round paddle bore and cut it again as a slot.

    The slot keeps the R57 height, pointed roof and tapered entries. Only its fore-aft width shrinks.
    """
    z = m.BARREL_HOLE_Z
    half, front, rear = m.WELL
    inner, outer = half + 0.6, m.BARREL_X - 0.7          # between the tapered entries
    plug = b.mirrored(m.along_x(m.hole_section(m.AXIS_Y, z, m.BARREL_HOLE_R + 0.05, (0, -1)), inner, outer))
    band = mf.CrossSection.square((2 * SLOT_HALF, 8.0)).translate((m.AXIS_Y - SLOT_HALF, z - 4.0))
    section = m.hole_section(m.AXIS_Y, z, m.BARREL_HOLE_R, (0, -1)) ^ band
    return body + plug - m.along_x(section, -m.BARREL_X - 0.02, m.BARREL_X + 0.02)


def stop_flange(body):
    """Beside the two tower stations: a thinner sleeve wall carrying a wider 45 degree flange."""
    y0, y1 = FLANGE_Y
    inner = WALL - WALL_TRIM
    old = b.mirrored(b.box(inner, WALL + b.FLANGE + 0.05, y0, y1 + 0.01, b.SLEEVE_RIM - 0.01, b.PLATE_Z - 0.3))
    flare = b.prism_xz([(inner - 0.01, b.SLEEVE_RIM), (inner + FLANGE, b.SLEEVE_RIM), (inner - 0.01, b.SLEEVE_RIM + FLANGE + 0.01)], y0, y1)
    # As in R57, nothing under the paddle passes its plan outline.
    x, r, front = b.PLATE_X, 1.5, b.PLATE_FRONT
    footprint = b.prism_xy([(-x + r, front), (x - r, front), (x, front + r), (x, m.FRONT_END), (-x, m.FRONT_END), (-x, front + r)], 0, 40)
    return (body - b.to_world(old)) + (b.to_world(b.mirrored(flare)) ^ footprint)


def paddle():
    return reslot(stop_flange(m.paddle()) + b.to_world(contact_bar()))


def lid_plain():
    lid = b.load(m.R53 / "exports/OP1_Lid-assembly.stl")
    towers = b.ubox(-10, 10, b.TOWER_Y[0] - TOWER_CUT, b.TOWER_Y[1] + TOWER_CUT, b.LID_Z[1], 30)
    return lid - towers


def stop_tower():
    """Right-hand tower in the board frame. Its 45 degree lip hangs over the sleeve flange."""
    inner = WALL - WALL_TRIM
    tip, flange_tip = inner + SIDE_CLEAR, inner + FLANGE
    stem = flange_tip + STEM_CLEAR
    face = lambda x: b.SLEEVE_RIM + (flange_tip - x) + LIFT_GAP
    z1, top = b.LID_Z[1], STOP_TOP
    outline = [(b.TOWER_X[0], z1 - 0.01), (b.LID_HALF, z1 - 0.01), (b.LID_HALF, top), (tip, top), (tip, face(tip)),
               (stem, face(stem)), (stem, TOWER_BASE_TOP), (b.TOWER_X[0], TOWER_BASE_TOP)]
    tower = b.prism_xz(outline, *b.TOWER_Y)
    # Lead-in on the edge that passes the flange first.
    tower -= b.prism_xy([(tip - 0.01, b.TOWER_Y[1] - 0.8), (tip - 0.01, b.TOWER_Y[1] + 0.01), (tip + 0.8, b.TOWER_Y[1] + 0.01)], 0, 40)
    return tower


def lid_stop():
    return lid_plain() + b.to_world(b.mirrored(stop_tower()))


def snug_pin():
    """The R57 pin at 3.2 mm, resting on the bottom of the same cheek holes."""
    before = m.PIN_R
    m.PIN_R = SNUG_PIN_R
    try:
        pin = m.hinge_pin()
    finally:
        m.PIN_R = before
    return pin.translate((0, 0, SNUG_PIN_R - before))


def parts():
    return {"Touch_Paddle": paddle(), "OP1_Lid_Plain": lid_plain(), "OP1_Lid_Stop": lid_stop(), "Hinge_Pin_Snug": snug_pin()}


def main(output=None):
    output = Path(output) if output else EXPORT
    output.mkdir(parents=True, exist_ok=True)
    records = {}
    for name, shape in parts().items():
        pieces = sorted(shape.decompose(), key=lambda s: -s.volume())
        loose = [round(p.volume(), 5) for p in pieces[1:]]
        print(name, [round(float(v), 3) for v in shape.bounding_box()], "pieces", len(pieces), loose[:6], flush=True)
        if any(v > 0.001 for v in loose):
            raise ValueError(f"{name} has detached material: {loose[:8]}")
        path = output / f"{name}-assembly.stl"
        mesh = b.save_closed(path, pieces[0])
        records[name] = dict(sha256=sha256(path.read_bytes()).hexdigest(), volume_mm3=round(float(mesh.volume), 3),
                             bounds_mm=[round(float(v), 3) for v in pieces[0].bounding_box()])
    digest = lambda path: sha256(path.read_bytes()).hexdigest()
    inner = WALL - WALL_TRIM
    (output / "dimensions.json").write_text(json.dumps(dict(
        meshes=records, contact_bar_stations_along_board_mm=list(STATIONS),
        hinge=dict(pin_diameter_mm=2 * m.PIN_R, optional_snug_pin_diameter_mm=2 * SNUG_PIN_R,
                   cheek_hole_diameter_mm=2 * m.CHEEK_HOLE_R, paddle_bore_fore_aft_mm=2 * SLOT_HALF,
                   paddle_bore_up_down_mm=2 * m.BARREL_HOLE_R, r57_paddle_bore_mm=2 * m.BARREL_HOLE_R),
        lift_stop=dict(sleeve_wall_beside_towers_mm=b.SLEEVE_WALL - WALL_TRIM, sleeve_flange_mm=FLANGE,
                       tower_to_sleeve_wall_mm=SIDE_CLEAR, tower_to_flange_tip_mm=STEM_CLEAR,
                       lip_over_flange_mm=round(FLANGE - SIDE_CLEAR, 3), lift_gap_mm=LIFT_GAP, tower_top_mm=STOP_TOP,
                       tower_stem_board_x_mm=[round(inner + FLANGE + STEM_CLEAR, 3), b.LID_HALF]),
        reused_from_r57={name: digest(R57 / f"exports/{name}-assembly.stl")
                         for name in ("Hinge_Pin", "Pin_Clip", "DFR_Post_Bar")},
        baseline_retainer_sha256=digest(m.R53 / "exports/OP1_Lid-assembly.stl")), indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
