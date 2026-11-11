"""Check the exact R34 assembly plate and the straight OP1's working spaces."""

import argparse
import json
from pathlib import Path

import holder34 as h
from audit_plate32 import inspect, read_json
from bonds33 import verify_bonds
from stops34 import verify_stops
from windows33 import verify_windows


def print_routes():
    routes, material = h.h32.print_routes()
    carrier, _, fixed, ribs = h.geometry()
    keys = routes['Key_Carrier']
    for name, region in keys.items():
        if name.startswith('OP1 '):
            keys[name] = h.straighten(region)
    critical = material['Key_Carrier']
    critical['OP1 mounting shoulders'] = h.straighten(h.h32.mount_saddles()) ^ carrier
    # Measure each load-bearing core independently. The tapered lead-in
    # is checked separately for layer overlap and attachment to the body.
    for sign, name in ((-1, 'Left'), (1, 'Right')):
        core = h.box(*sorted((8.28 * sign, 10.52 * sign)), -8.4, -7.2, 8.65, h.STOP_Z - .23)
        critical[f'{name} travel stop core'] = h.stop_posts() ^ carrier ^ core
    for name, rib in ribs.items():
        sign = 1 if name.startswith('R') else -1
        row = h.previous.RIB_ROWS[int(name[1:]) - 1]
        core = h.box(*sorted((13.8 * sign, 17.5 * sign)), row - .38, row + .38, .92, 1.58)
        rail = 22.3 if sign > 0 else 28.3
        edge = h.box(*sorted(((rail - .55) * sign, (rail + .4) * sign)), 11.5, 16.4, 4.5, 9.5)
        critical[f'{name} rounded finger-contact core'] = core ^ rib
        critical[f'{name} edge-rail joint'] = edge ^ fixed ^ rib
    bracket = material['DFRobot_Hole_Bracket']
    bracket['Moved switch pusher'] = h.bracket() ^ h.box(h.PCB_X - .53, h.PCB_X + .62, -1.85, .2, 18.05, 19.05)
    for sign, name in ((1, 'Right'), (-1, 'Left')):
        foot = h.box(*sorted(((h.STOP_X - .5) * sign, (h.STOP_X + .5) * sign)), -11.25, -10.45, 13.35, 18.8)
        bracket[f'{name} front stop'] = h.bracket() ^ foot
    return routes, material


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    exports = args.scratch / 'build-source' / 'exports'
    result = inspect(args.archive, exports, print_routes, read_json(args.scratch / 'print-checks.json'))
    for name, verify in (('travel_stop_bonds', verify_stops), ('rod_mount_bonds', verify_bonds),
                         ('crossbar_windows', verify_windows)):
        result[name] = verify(args.archive, exports)
        if not result[name]['passed']:
            result['failures'].append([name, 'Deposited connection or opening check failed'])
    result['passed'] = not result['failures']
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise SystemExit('See the R34 audit for remaining printability issues.')
