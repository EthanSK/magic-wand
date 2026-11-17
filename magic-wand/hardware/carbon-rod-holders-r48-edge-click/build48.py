"""R48 moves the OP1 switch under the free edge of the DFRobot touch board.

Assembly axes are the R47 axes: +Y is towards the top pair of Choc keys.
Import this module before using the inherited CAD, plate or audit generators.
"""
from functools import lru_cache, partial
import hashlib
import json
import math
from pathlib import Path
from unittest.mock import patch
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'carbon-rod-holders-r47-bottom-click'
sys.path.insert(0, str(PREVIOUS))
import build47 as b

h = b.h
q, r, p = h.q, h.r, h.p
EDGE_INSET = 1.65
BOARD_YAW = -20.5



def configure():
    if any(fn.cache_info().currsize for fn in (h.d.geometry, q.hardware, p.bracket, q.op1_reliefs)):
        raise RuntimeError('Configure R48 in a fresh process before constructing geometry')
    h.PUSH_FROM_FRONT = EDGE_INSET
    h.OP1_YAW = q.OP1_YAW = h.d.OP1_YAW = h.h32.PCB_YAW = BOARD_YAW
    q.PUSH_Y = p.PUSH_Y = h.BOARD_FRONT + EDGE_INSET
    q.PLUNGER_XY = p.PLUNGER_XY = (q.PLUNGER_XY[0], q.PUSH_Y + r.CLICK_SHIFT)
    q.LEVER = r.AXIS_Y - q.PUSH_Y
    q.REST = p.REST = r.REST = math.degrees(math.asin(q.DEPRESSION / q.LEVER))
    q.EARLY_ANGLE = h.base.EARLY_ANGLE = -(q.REST + math.degrees(.095 / q.LEVER))
    h.HEEL_TOP = q.HEEL_TOP = 13.33
    h.LANDING_RAISE = q.LANDING_RAISE = .23
    h.START_TURNS = q.START_TURNS = 1.5
    q.SAMPLE_TURNS = b.np.linspace(0.0, q.START_TURNS, 10)
    h.STOP_X = h.base.STOP_X = -8.3
    h.FRONT_FLOOR = True
    # Follow the three outer guard legs inward and rise into the underside of
    # the centre deck ahead of the connector. The finger rests stay rounded.
    h.LANDING_RUN = ((10.15, 8.1, 2.15), (9.35, 7.05, 3.25),
                     (8.15, 6.45, 4.45), (3.9, 7.7, 4.9),
                     (3.5, 11.1, 4.7), (3.5, 15.8, 4.95))
    h.LANDING_RADIUS = 1.05


configure()

from shoulder48 import connector_buttress, shoulder

import cable48
import hinge48
from strength48 import chin_runners, triangle_rails, check_cad

stock_bracket = p.bracket_before_pin_relief


@lru_cache(maxsize=1)
def reinforced_bracket():
    return stock_bracket() + triangle_rails(h)


p.bracket_before_pin_relief = q.bracket_before_pin_relief = reinforced_bracket
hinge48.install(h)
WIRE_FEED_XY = cable48.centres(h)[0]
WIRE_FEED_RADIUS = 2.08
reliefs_previous = q.op1_reliefs


@lru_cache(maxsize=1)
def op1_reliefs():
    slot, barrels, connector, pilots = reliefs_previous()
    return slot, barrels, connector + cable48.outlet(h), pilots


q.op1_reliefs = op1_reliefs

geometry_previous = h.d.geometry


@lru_cache(maxsize=1)
def carrier_geometry():
    carrier, working, fixed, ribs = geometry_previous()
    added = shoulder(h) + connector_buttress(h) + chin_runners(h)
    # The guard and clip still expose their working gaps. In particular an
    # added shoulder must never form an accidental third grip on the rod.
    added = h.d.r22.spaces16.carve(added, working, 'R48 forward clip shoulder')
    return carrier + added, working, fixed + added, ribs


h.d.geometry = carrier_geometry
compose_previous = b.compose


def compose(stage):
    import relief47
    # The native layer after R47's fixed pocket bevel began two unsupported
    # loops at the new switch position. Only this R48 build continues the cut.
    with patch.object(relief47, 'prepare', partial(relief47.prepare, finish_pocket=True)):
        carrier, working, fixed, ribs, gaps, record = compose_previous(stage)
    # R47 combined its two split right guards with the replacement landing.
    # The forward switch also divides R1; credit only the joined guard body
    # after checking that every other fragment is buried inside the frame.
    pieces = (ribs['R1'] + h.rib_landing()).decompose()
    exposed = [piece for piece in pieces if (piece - fixed).volume() > b.SLIVER]
    if len(exposed) != 1:
        raise ValueError(f'Disconnected R1 guard after adding the landing: {[s.volume() for s in exposed]}')
    ribs = {**ribs, 'R1': exposed[0]}
    return carrier, working, fixed, ribs, gaps, record


b.compose = compose


def finish(scratch):
    """Bind the inherited checks to the exact revised solids and mechanism."""
    from mechanics48 import check
    stage = scratch / 'stage'
    path = stage / 'r47-checks.json'
    result = json.loads(path.read_text())
    cap_file = stage / 'R47-DFRobot_Hole_Bracket-cap.stl'
    seated_path = stage / 'R48-DFRobot_Hole_Bracket-seated.stl'
    b.save(seated_path, p.bracket())
    cap = b.load(seated_path)
    b.save(cap_file, hinge48.free_bracket(h))
    carrier = b.load(stage / 'R47-Key-Carrier-assembly.stl')
    mechanism = check(h, cap, result, b.load(stage / 'R47-Key-Carrier-assembly.stl'), b.load(h.R46_ASSEMBLY))
    wire = cable48.check(h, carrier)
    mechanism['harness_outlet'] = wire
    mechanism['gates']['harness_outlet_faces_fitted_plug'] = wire['passes']
    hinge = hinge48.check_hinge(h, cap, b.load(cap_file), carrier)
    mechanism['hinge_fit'] = hinge
    mechanism['gates']['spring_arms_fit_from_either_side'] = all(hinge['gates'].values())
    structure = check_cad(h, cap, carrier)
    mechanism['structural_sections'] = structure
    mechanism['gates']['triangle_and_chin_reinforced'] = structure['passed']
    mechanism['passed'] = result['r47']['passed'] and all(mechanism['gates'].values())
    inputs = [HERE / name for name in ('build48.py', 'mechanics48.py', 'shoulder48.py', 'strength48.py', 'hinge48.py', 'cable48.py')]
    inputs += [stage / name for name in ('R47-DFRobot_Hole_Bracket-cap.stl', 'R48-DFRobot_Hole_Bracket-seated.stl', 'R47-Key-Carrier-assembly.stl')]
    mechanism['source_sha256'] = {src.name: hashlib.sha256(src.read_bytes()).hexdigest() for src in inputs}
    inherited_relief = Path('..') / PREVIOUS.name / 'relief47.py'
    mechanism['source_sha256'][str(inherited_relief)] = hashlib.sha256((HERE / inherited_relief).read_bytes()).hexdigest()
    result['revision'] = 'r48'
    result['r48'] = mechanism
    path.write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(mechanism, indent=1))
    if not mechanism['passed']:
        raise SystemExit('R48 geometry check failed')


def main(scratch):
    b.main(scratch)
    finish(scratch)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
