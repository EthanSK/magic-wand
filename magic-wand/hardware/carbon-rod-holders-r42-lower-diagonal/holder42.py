"""R42: R41 with the DFRobot touch board seated 0.95 mm lower.

The carrier, the diagonal OP1 board, its harness, the hinge, the pusher and
its root, and both stops are R41's unchanged. Only the DFR0030 seat drops
inside the same bracket. Run assembly42.py through geometry_budget.py to check
and export; this module writes nothing.

Why the touch board, not the OP1 stack, moves (CAD-measured in R41):

- The R41 harness plug sits beside the round rod with 0.31 mm clearance.
  Lowering the whole OP1 board closes that gap by about 0.75 mm per mm. At
  -0.3 mm the gap is 0.09 mm, under R41's 0.2 mm gate. The plug cannot move
  sideways either. At 21-32 degree yaws, keeping the 0.73 mm wall at the
  upper-right Choc bay puts the plug 0.30-0.35 mm from the rod. The three
  socket barrels over the rod crown have 0.9 mm; they are not the limit.
- The switch fixes the bracket floor: free plunger 18.15, 0.35 mm gap, then a
  0.7 mm floor whose top is at 19.2. R41 left a 1.05 mm gap between that floor
  and the board underside (20.25). R42 closes it to 0.1 mm. The board now
  rests on its side rails, its hole pads and the front touch web, at 19.3.
  The hinge-arm tops stay 0.3 mm below the board.

The DFRobot Gravity pin tails (1.5-2.0 mm) now pass through R41's pin pocket
in the inner tips of the root fans. The arms, their roots and the bridge are
unchanged. The Gravity lead follows the lower connector.

Frame: X across the keys, +Y towards the two-key row, +Z up from the rod centre.
"""
from functools import lru_cache
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R41 = HERE.parent / 'carbon-rod-holders-r41-dfrobot-diagonal'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R41))
import holder41 as prev  # noqa: E402  (installs R41 into the shared R38/R39 functions; builds nothing)

r, base, old, h32, h28, r39 = prev.r, prev.base, prev.old, prev.h32, prev.h28, prev.r39
H, box, union = prev.H, prev.box, prev.union
CARRIER, BRACKET, CLIP = prev.CARRIER, prev.BRACKET, prev.CLIP
BATTERY, DOOR, battery_door, door_displacement = prev.BATTERY, prev.DOOR, prev.battery_door, prev.door_displacement

R41_BOARD_Z = tuple(r.BOARD_Z)            # (20.25, 21.85) in the bracket frame
SEAT_DROP = .95
BOARD_Z = (R41_BOARD_Z[0] - SEAT_DROP, R41_BOARD_Z[1] - SEAT_DROP)
FLOOR_TOP = 19.2                          # R31 floor, R26 paddle cut and pusher root
ARM_TOP = r39.ARM_Z[1]                    # 19.0
BOARD_TO_ARMS = .3
BOARD_TO_FLOOR = .1
BOARD_REAR_TO_PADS = .3
OP1_DROP_PROBES = (0., -.15, -.3)         # reported OP1 lowering limit, not applied
_bracket_r41 = prev.bracket_before_pin_relief


def gravity_lead():
    """R31's slack lead, its connector end lowered with the board.

    The lead is a flexible envelope. The last two points, behind the hinge,
    stay on R41's path.
    """
    f = r.board_front_y() + r.BOARD_LENGTH - 30.
    drop = SEAT_DROP
    points = [(0., f + 26., 24.3 - drop), (0., f + 33.5, 24.3 - drop), (2.5, f + 36.5, 23. - drop / 2),
              (6.5, f + 38.5, 19.5), (9., f + 40., 16.)]
    balls = [mf.Manifold.sphere(1.25, 20).translate(p) for p in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))


def board_space():
    """Everything above the new seat inside the board outline (plus 0.3 mm)."""
    front = r.board_front_y()
    return box(-r.BOARD_HALF - .3, r.BOARD_HALF + .3, front - .3, front + r.BOARD_LENGTH + .3,
               BOARD_Z[0], 40.)


def posts():
    return union(r.post().translate((s * r.POST_X, r.hole_y(), 0.)) for s in (-1, 1))


@lru_cache(maxsize=1)
def bracket_before_pin_relief():
    """R41's bracket built with R31's seat rails, pads and posts at the lower
    seat. The 0.15 mm of R35's touch web above the seat is trimmed off, so the
    web becomes a seat under the gold pad. The posts are kept."""
    return (_bracket_r41() - board_space() - pinch_pad_trim()) + posts()


PIN_CUT_BOTTOM = 16.9                     # below the 17.0 fan and root-rib undersides
PIN_CHAMFER_FOOT = 18.45                  # fan inner face (X 3.05) starts its 45 degree chamfer here
PIN_RAMP_FOOT = 18.4                      # far end of the pocket starts its 45 degree ramp here


def _xz_prism(points, y0, y1):
    """An X-Z polygon extruded along Y from y0 to y1."""
    section = mf.CrossSection([points])
    return mf.Manifold.extrude(section, y1 - y0).rotate((90., 0., 0.)).translate((0., y1, 0.))


def pin_relief():
    """R41's pin pocket, cut through the inner tips of the root fans.

    The 2.0 mm tails now reach Z 17.3, so R41's pocket floor would leave a
    0.05 mm skin over the 17.0 fan underside. The pocket goes through instead.
    Its width stays inside the arms' outer faces (X +/-3.05). Lower down, its
    length is R41's position band with a 0.25 mm margin.

    The solder fillets (0.75 mm radius at the board) now come below the
    19.0 fan tops. A 45 degree chamfer on each fan's inner top edge and a 45
    degree ramp at the far end clear them. The chamfer is vertical in the
    front-down print; the ramp is a 45 degree roof. The pocket stays more
    than 0.7 mm ahead of the arm roots and the bridge.
    """
    rear = r.board_front_y() + r.BOARD_LENGTH
    y = rear - prev.PIN_FROM_END
    band = prev.PIN_Y_TOLERANCE + .32 + prev.PIN_MARGIN
    y0, y1 = y - band, y + band
    x, top = r.h29.ARM_X[1], BOARD_Z[0] + .01
    flare = x + top - PIN_CHAMFER_FOOT
    across = _xz_prism([(-x, PIN_CUT_BOTTOM), (x, PIN_CUT_BOTTOM), (x, PIN_CHAMFER_FOOT), (flare, top),
                        (-flare, top), (-x, PIN_CHAMFER_FOOT)], y0 - 1., y1 + 3.)
    along = r.d.wedge(-flare - .1, flare + .1, [(y0, PIN_CUT_BOTTOM), (y1, PIN_CUT_BOTTOM), (y1, PIN_RAMP_FOOT),
                                                (y1 + top - PIN_RAMP_FOOT, top), (y0, top)])
    return across ^ along


def pinch_pad_trim():
    """Start the raised pinch pads 0.3 mm behind the lower board's rear edge.

    R41's board passed 0.25 mm above the 20.0 pad tops. R42's board is level
    with the pads, so their front 0.33 mm is cut down to the arm tops. The
    pads keep their height, width and rear end.
    """
    rear = r.board_front_y() + r.BOARD_LENGTH
    x0, x1 = r.h29.ARM_X
    return r.mirrored(box(x0 - .05, x1 + .05, rear - .5, rear + BOARD_REAR_TO_PADS, ARM_TOP, r.h29.PINCH[2] + .1))


@lru_cache(maxsize=1)
def bracket():
    return H.base.clean(bracket_before_pin_relief() - pin_relief(), BRACKET)


def configure():
    """Set the lower seat before any board, post, clip or bracket is built."""
    for fn in (r.cap, r.board_front_y, base.geometry, base.hardware, prev.bracket, _bracket_r41,
               prev.switch_relief, prev.pusher):
        assert fn.cache_info().currsize == 0, fn
    r.BOARD_Z = BOARD_Z
    r.SEAT_TOP = BOARD_Z[0]
    r.RAIL_Z = (r.RAIL_Z[0], r.SEAT_TOP)
    r.NECK = (BOARD_Z[1], BOARD_Z[1] + 1.)
    r.HEAD_TOP = r.NECK[1] + .8
    r.gravity_lead = gravity_lead
    prev.bracket_before_pin_relief = bracket_before_pin_relief
    prev.pin_relief = pin_relief
    prev.bracket = bracket
    base.bracket = bracket


configure()
# R41's helpers under their R42 names (assembly41's guide builder uses these).
geometry, carrier, hardware = prev.geometry, prev.carrier, prev.hardware
clip_part, gravity_pins, board_point = prev.clip_part, prev.gravity_pins, prev.board_point
REST, PITCH, PLUNGER_XY, PUSH_Y, PCB_TOP = prev.REST, prev.PITCH, prev.PLUNGER_XY, prev.PUSH_Y, prev.PCB_TOP


def op1_lowering_limit():
    """R41's OP1 underside against the rod if the whole OP1 group were lowered."""
    bar = base.rod()
    parts = hardware()
    rows = []
    for dz in OP1_DROP_PROBES:
        moved = {n: parts[n].translate((0., 0., dz)) for n in ('plug', 'sockets', 'housing', 'op1_wire')}
        rows.append({'op1_drop_mm': dz, **{f'{n}_to_rod_mm': round(float(s.min_gap(bar, 4.)), 3)
                                          for n, s in moved.items()}})
    return rows


def seat_metrics(paddle):
    """Board underside to every bracket surface below it, by feature."""
    front = r.board_front_y()
    under = box(-r.BOARD_HALF, r.BOARD_HALF, front, front + r.BOARD_LENGTH, 0., BOARD_Z[0] - .005)
    below = paddle ^ under
    seats = paddle ^ box(-r.BOARD_HALF, r.BOARD_HALF, front, front + r.BOARD_LENGTH, BOARD_Z[0] - .02, BOARD_Z[0])
    # Measure the loaded roots/fans, not the rear pinch pads or deliberate
    # board seats. Those are different features with different clearances.
    arms = paddle ^ box(-r.h29.ARM_X[1], r.h29.ARM_X[1],
                        r.ARM_ROOT_Y - 3.1, r.ARM_ROOT_Y + 1.2, 0., BOARD_Z[0])
    # Keep the probe above the expected floor, so an unwanted raised face
    # survives measurement and can fail the existing height gate.
    floor = paddle ^ box(-8.5, 8.5, -3.7, 4.72, 18.5, 40.)
    return {
        'seat_plane_area_mm2': round(float(seats.volume()) / .02, 2),
        'board_underside_to_arm_root_and_fan_tops_mm': round(BOARD_Z[0] - arms.bounding_box()[5], 4),
        'board_underside_to_floor_top_mm': round(BOARD_Z[0] - FLOOR_TOP, 4),
        'highest_fixed_floor_or_root_surface_mm': round(max(
            float(floor.bounding_box()[5]), float(arms.bounding_box()[5])), 4),
    }


@lru_cache(maxsize=1)
def checks():
    report = deepcopy_json(prev.checks())
    paddle = bracket()
    r41_checks = json.loads((R41 / 'exports' / 'geometry-checks.json').read_text())['checks']['layout']
    top = report['layout']['dfr_touch_face_top_released_mm']
    electrode = r.world(r.electrode(), 0.).bounding_box()[5]
    seat = seat_metrics(paddle)
    limit = op1_lowering_limit()
    lowering = {
        'seat_drop_in_bracket_mm': SEAT_DROP,
        'board_z_bracket_frame_mm': list(BOARD_Z), 'r41_board_z_bracket_frame_mm': list(R41_BOARD_Z),
        'touch_top_released_mm': top, 'r41_touch_top_released_mm': r41_checks['dfr_touch_face_top_released_mm'],
        'touch_top_lowering_mm': round(r41_checks['dfr_touch_face_top_released_mm'] - top, 4),
        'electrode_top_at_click_angle_0_mm': round(float(electrode), 4),
        'touch_top_above_choc_cap_top_released_mm': round(top - h28.CHOC_TOP, 4),
        'op1_shift_mm': [0., 0., 0.], 'carrier_changed_from_r41': False,
        'op1_lowering_limit': limit,
        'limiting_geometry': (
            'Touch board: the bracket floor top (19.2), set by the fixed switch plunger. '
            'OP1 stack: the harness plug beside the rod (0.31 mm, closing about 0.75 mm per mm).'),
        **seat,
    }
    report['lowering'] = lowering
    passed = bool(
        report['passed']
        and seat['board_underside_to_arm_root_and_fan_tops_mm'] >= BOARD_TO_ARMS - 1e-6
        and seat['highest_fixed_floor_or_root_surface_mm'] <= FLOOR_TOP + 1e-6
        and lowering['touch_top_lowering_mm'] >= SEAT_DROP - .05
        and report['layout']['op1_plug_to_rod_mm'] >= r41_checks['op1_plug_to_rod_mm'] - 1e-4
        and report['layout']['op1_sockets_to_rod_mm'] >= r41_checks['op1_sockets_to_rod_mm'] - 1e-4
    )
    report['r41_gates_passed'] = report['passed']
    report['cad_checks_passed'] = report['passed'] = passed
    report['basis'] += (' R42 lowers only the DFR0030 seat within the same bracket; '
                        'the OP1 envelopes, plug clearance and switch heights are R41\'s.')
    return report


def deepcopy_json(value):
    return json.loads(json.dumps(value, default=float))


def __getattr__(name):
    """Compose R41's unchanged interfaces for the plate and audit adapters."""
    return getattr(prev, name)
