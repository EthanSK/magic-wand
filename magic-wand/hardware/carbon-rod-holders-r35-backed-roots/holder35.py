"""Back the separately printed R34 rod clip and touch-bracket feet.

Run assembly35.py to export these solids and verify the retained mechanisms.
"""

from functools import lru_cache
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
R34 = HERE.parent / 'carbon-rod-holders-r34-straight-op1'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R34))
import holder34 as prior
from audit34 import print_routes

KEY_BRACE_WIDTH = 1.56
KEY_BRACE_CENTER = 2.8
KEY_BRACE_BACK = 32.65
KEY_BRACE_FRONT = 24.0
KEY_BRACE_TAPER_END = 22.2
KEY_BRACE_BOTTOM, KEY_BRACE_TOP = 3.85, 8.72
CENTRE_BRACE_FRONT = 15.4
CENTRE_BRACE_TAPER_END = 13.8
TOUCH_WEB_FRONT = -11.835
TOUCH_WEB_BACK = -3.735
TOUCH_WEB_HALF_WIDTH = 9.7
TOUCH_WEB_BOTTOM, TOUCH_WEB_TOP = 18.35, 19.45


def key_braces():
    """Join the solid crown of the C-clip to the key deck from layer one."""
    # The narrow free ends of the clip still flex to admit the rod.
    # Join at its crown, where the bore and wire path have clearance.
    half = KEY_BRACE_WIDTH / 2
    brace = prior.r.d.wedge(KEY_BRACE_CENTER - half, KEY_BRACE_CENTER + half, [
        (KEY_BRACE_BACK, KEY_BRACE_BOTTOM),
        (KEY_BRACE_TAPER_END, KEY_BRACE_BOTTOM),
        (KEY_BRACE_TAPER_END, KEY_BRACE_TOP - (KEY_BRACE_FRONT - KEY_BRACE_TAPER_END)),
        (KEY_BRACE_FRONT, KEY_BRACE_TOP),
        (KEY_BRACE_BACK, KEY_BRACE_TOP),
    ])
    # The narrow centre of the original clip remains a separate single
    # wall above the low crown. Back that wall until the main body reaches it.
    centre = prior.r.d.wedge(-.65, .65, [
        (KEY_BRACE_BACK, 4.04),
        (CENTRE_BRACE_TAPER_END, 4.04),
        (CENTRE_BRACE_TAPER_END, KEY_BRACE_TOP - (CENTRE_BRACE_FRONT - CENTRE_BRACE_TAPER_END)),
        (CENTRE_BRACE_FRONT, KEY_BRACE_TOP),
        (KEY_BRACE_BACK, KEY_BRACE_TOP),
    ])
    return {'left clip brace': (brace.mirror((1., 0., 0.)), KEY_BRACE_BACK - KEY_BRACE_FRONT),
            'centre clip brace': (centre, KEY_BRACE_BACK - CENTRE_BRACE_FRONT),
            'right clip brace': (brace, KEY_BRACE_BACK - KEY_BRACE_FRONT)}


def touch_web():
    """Join the front feet on the bed side without closing the snap arms."""
    return prior.box(-TOUCH_WEB_HALF_WIDTH, TOUCH_WEB_HALF_WIDTH, TOUCH_WEB_FRONT, TOUCH_WEB_BACK,
                     TOUCH_WEB_BOTTOM, TOUCH_WEB_TOP)


@lru_cache(maxsize=1)
def geometry():
    carrier, working, fixed, guards = prior.geometry()
    braces = prior.union(brace for brace, _ in key_braces().values())
    return prior.H.base.clean(carrier + braces, 'Key_Carrier'), working, fixed + braces, guards


@lru_cache(maxsize=1)
def bracket():
    return prior.H.base.clean(prior.bracket() + touch_web(), 'DFRobot_Hole_Bracket')


def checks():
    checks = prior.checks(geometry, bracket)
    old_carrier, working, _, _ = prior.geometry()
    routes, _ = print_routes()
    added = geometry()[0] - old_carrier
    added_bracket = bracket() - prior.bracket()
    openings = prior.previous.route_overlaps(added, {**working, **routes['Key_Carrier']})
    moving_clearance = {
        'touch_board': (added_bracket ^ prior.r.sensor()).volume(),
        'touch_connector': (added_bracket ^ prior.r.connector()).volume(),
        'touch_wire': (added_bracket ^ prior.r.gravity_lead()).volume(),
        'post_clips': (added_bracket ^ prior.r.clips()).volume(),
    }
    brace_bonds = [(brace ^ old_carrier).volume() for brace, _ in key_braces().values()]
    checks.update(
        carrier_added_mm3=round(added.volume(), 4),
        bracket_added_mm3=round(added_bracket.volume(), 4),
        brace_bonds_mm3=brace_bonds,
        brace_opening_overlaps_mm3=openings,
        added_bracket_clearance_mm3=moving_clearance,
    )
    checks['passed'] = (
        checks['passed'] and max(openings.values()) < .005
        and max(moving_clearance.values()) < .005 and min(brace_bonds) > 1.
    )
    return checks
