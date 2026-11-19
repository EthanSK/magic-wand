"""Reusable placement data for the R53 viewer and plate: actors, hinge poses and fitting order.

Matrices are 3 x 4, row-major, the same layout as the samples in earlier assembly guides.
Run after build53.py, checks53.py and print53.py.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np

import build53 as b

GUIDE48 = "../../carbon-rod-holders-r48-edge-click/exports/guide/"
R51 = "../../carbon-rod-holders-r51-guided-hinge/exports/"
OP1_SHIFT = (0.0, 3.3, 0.2)      # R48 guide meshes to the R51-R53 switch position
TOUCH_SHIFT = (0.0, 3.55, 0.0)   # touch-board meshes are stored in the old bracket frame


def flat(matrix):
    return [round(float(v), 9) for v in np.asarray(matrix, dtype=float)[:3].ravel()]


def shift(offset):
    m = np.eye(4)
    m[:3, 3] = offset
    return m


def hinge(angle):
    return np.vstack([np.asarray(b.hinge_matrix(angle)), [0, 0, 0, 1]])


def main(source=None):
    source = Path(source) if source else b.EXPORT
    fit = json.loads((source / "mechanical-fit.json").read_text())
    click, lift = fit["click"], fit["lift"]
    per_degree = click["travel_mm_per_degree"]
    typical = (b.FREE_TOP - (b.PCB_TOP + 6.9)) / per_degree
    angles = dict(rest=0.0, typical_operating_point=round(typical, 4), switch_case_stop=round(click["paddle_meets_switch_case_deg"], 4),
                  lid_lift_stop=round(-lift["lid_stops_paddle_deg"], 4))
    axis = b.board_axis()
    actors = {
        # printed in this revision
        "carrier": dict(file="Key_Carrier-assembly.stl", label="Key holder with open hinge yoke and lid rails", printed=True, base=flat(np.eye(4))),
        "paddle": dict(file="Touch_Paddle-assembly.stl", label="Touch paddle with switch sleeve and axle bar", printed=True, base=flat(np.eye(4)), rides="paddle"),
        "post_bar": dict(file="DFR_Post_Bar-assembly.stl", label="Post bar fitted from below", printed=True, base=flat(np.eye(4)), rides="paddle"),
        "hinge_cap": dict(file="Hinge_Cap-assembly.stl", label="Hinge cap pushed in from the rear", printed=True, base=flat(np.eye(4))),
        "lid": dict(file="OP1_Lid-assembly.stl", label="OP1 lid pushed in from the front", printed=True, base=flat(np.eye(4))),
        "lid_close": dict(file="OP1_Lid_Close-assembly.stl", label="Optional closer lid (two ribs)", printed=True, optional=True,
                          replaces="lid", base=flat(np.eye(4))),
        # printed earlier and reused
        "clip_left": dict(file=GUIDE48 + "dfr-clip-left.stl", label="Left post clip (existing print)", reused=True, base=flat(shift(TOUCH_SHIFT)), rides="paddle"),
        "clip_right": dict(file=GUIDE48 + "dfr-clip-right.stl", label="Right post clip (existing print)", reused=True, base=flat(shift(TOUCH_SHIFT)), rides="paddle"),
        # bought parts, reference shapes
        "rod": dict(file="../../carbon-rod-holders/exports/carbon-stock-tube.stl", label="Carbon tube, 500 mm", bought=True, base=flat(shift((0, -30, 0)))),
        "board": dict(file=GUIDE48 + "op1-board.stl", label="OP1 board at 20.5 degrees", bought=True, base=flat(shift(OP1_SHIFT)), group="op1_board"),
        "sockets": dict(file=GUIDE48 + "op1-sockets.stl", label="Three socket barrels", bought=True, base=flat(shift(OP1_SHIFT)), group="op1_board"),
        "housing": dict(file=GUIDE48 + "op1-housing.stl", label="Connector under the board", bought=True, base=flat(shift(OP1_SHIFT)), group="op1_board"),
        "plug": dict(file=GUIDE48 + "op1-plug.stl", label="Lead plug, fitted first", bought=True, base=flat(shift(OP1_SHIFT)), group="op1_board"),
        "op1_wire": dict(file=R51 + "op1_wire.stl", morphFile=R51 + "op1-wire-hanging.stl", label="OP1 lead", bought=True,
                         base=flat(np.eye(4)), group="op1_board"),
        "switch": dict(file=GUIDE48 + "op1-switch.stl", label="Switch body reference", bought=True, base=flat(shift(OP1_SHIFT)), group="switch"),
        "terminals": dict(file=GUIDE48 + "op1-terminals.stl", label="Switch terminals", bought=True, base=flat(shift(OP1_SHIFT)), group="switch"),
        "plunger": dict(file=R51 + "op1-button-reference.stl", label="Click button reference", bought=True, base=flat(shift(OP1_SHIFT)), group="switch"),
        "sensor": dict(file=GUIDE48 + "dfr-sensor.stl", label="DFRobot DFR0030 V2 board", bought=True, base=flat(shift(TOUCH_SHIFT)), rides="paddle"),
        "electrode": dict(file=GUIDE48 + "dfr-electrode.stl", label="Gold touch pad", bought=True, base=flat(shift(TOUCH_SHIFT)), rides="paddle"),
        "connector": dict(file=GUIDE48 + "dfr-connector.stl", label="Gravity socket and plug (estimate)", bought=True, base=flat(shift(TOUCH_SHIFT)), rides="paddle"),
        "gravity_pins": dict(file=GUIDE48 + "dfr-gravity-pins.stl", label="Gravity pin tails", bought=True, base=flat(shift(TOUCH_SHIFT)), rides="paddle"),
        "sensor_lead": dict(file=GUIDE48 + "dfr-sensor-lead.stl", label="Gravity lead slack", bought=True, base=flat(shift(TOUCH_SHIFT)), rides="paddle", frame=False),
    }
    missing = [a["file"] for a in actors.values() if not (source / a["file"]).resolve().exists()]
    if missing:
        raise FileNotFoundError(missing)
    along = [round(float(v), 9) for v in -axis]
    steps = [
        dict(id="board", title="Lower the OP1 board", caption="Plug the lead into the board, feed the lead through the holder and lower the board straight into its pocket.",
             moves=[dict(group="op1_board", start_offset=[0, 0, 16], path="straight")]),
        dict(id="switch", title="Plug in the switch", caption="Push the switch straight down into the three sockets. Either way round fits.",
             moves=[dict(group="switch", start_offset=[0, 0, 10], path="straight")]),
        dict(id="posts", title="Fit the post bar", caption="Away from the holder, push the post bar up through the two holes in the paddle.",
             moves=[dict(actor="post_bar", start_offset=[0, 0, -8], path="straight", relative_to="paddle")]),
        dict(id="touch", title="Fit the touch board", caption="Lower the touch board over the two posts and slide a clip onto each post neck.",
             moves=[dict(actors=["sensor", "electrode", "connector", "gravity_pins"], start_offset=[0, 0, 12], path="straight", relative_to="paddle"),
                    dict(actors=["clip_left", "clip_right"], start_offset=[0, -5, 0], path="straight", relative_to="paddle", after_previous=True)]),
        dict(id="paddle", title="Lower the paddle", caption="Lower the paddle straight down. Its sleeve goes over the switch and the axle bar drops into the two V seats.",
             moves=[dict(rides="paddle", start_offset=[0, 0, 14], path="straight")]),
        dict(id="cap", title="Push in the hinge cap", caption="Push the cap forward along the top of the yoke until it clicks over the ridge and sits flush with the rear face.",
             moves=[dict(actor="hinge_cap", start_offset=[0, 9, 0], path="straight")]),
        dict(id="lid", title="Slide in the lid", caption="With the paddle resting on the switch, slide the lid in from the front along the board until its latch clicks.",
             moves=[dict(actor="lid", start_offset=[round(v * 34, 6) for v in along], path="straight")]),
        dict(id="press", title="Press the pad", caption="Press the centre and both lower corners. Each press should click once and spring back.",
             moves=[dict(rides="paddle", hinge_angles_deg=[0.0, angles["switch_case_stop"], 0.0])]),
    ]
    data = dict(
        schema="r53-assembly-transforms/1", units="mm", revision="R53", physical_fit_verified=False,
        frame="Assembly frame of R48 to R52: rod along Y through X = Z = 0, +Y toward the two-key row, +Z up.",
        matrix_format="3 x 4 row-major. World pose of an actor = pose matrix x base matrix.",
        hinge=dict(axis_point=[0.0, b.AXIS_Y, b.AXIS_Z], axis_direction=[1.0, 0.0, 0.0],
                   positive_angle="front edge down", angles_deg=angles,
                   pose_matrices={k: flat(hinge(v)) for k, v in angles.items()},
                   rule="Actors with rides = paddle use hinge(angle) x base. All other actors stay on their base matrix."),
        lid_slide_direction_into_place=[round(float(v), 9) for v in axis],
        actors=actors, steps=steps, removal="Reverse order: lid, cap, paddle, switch, board.",
        print_set=dict(new=["Key_Carrier", "Touch_Paddle", "Hinge_Cap", "OP1_Lid", "DFR_Post_Bar"], optional=["OP1_Lid_Close"],
                       unchanged_clip_designs_included_on_plate=["DFR0030_Post_Clip", "DFR0030_Post_Clip_2"],
                       no_longer_used=["M2 x 20 screw", "M2 locknut", "3 mm metal sleeve", "two M1.6 kit screws"],
                       print_poses="print-spec.json"),
        checked_mesh_sha256=fit["checked_mesh_sha256"])
    (source / "assembly-transforms.json").write_text(json.dumps(data, indent=2) + "\n")
    print("actors", len(actors), "steps", len(steps), angles)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
