"""Audit R33 assembly clearances and material on the deposited Bambu paths."""

import argparse
import json
from pathlib import Path

import holder33 as h
from audit_plate32 import inspect, read_json
from bonds33 import verify_bonds
from windows33 import verify_windows


def print_routes():
    routes, material = h.previous.print_routes()
    _, fixed, ribs, _ = h.rib_candidates()
    carrier = material['Key_Carrier']
    for name, rib in ribs.items():
        sign = 1 if name.startswith('R') else -1
        row = h.RIB_ROWS[int(name[1:]) - 1]
        centre = h.box(*sorted((13.8 * sign, 17.5 * sign)), row - .38, row + .38, .92, 1.58)
        rail_x = 22.3 if sign > 0 else 28.3
        edge = h.box(*sorted(((rail_x - .55) * sign, (rail_x + .4) * sign)), 11.5, 16.4, 4.5, 9.5)
        carrier[f'{name} rounded finger-contact core'] = centre ^ rib
        carrier[f'{name} edge-rail joint'] = edge ^ fixed ^ rib

    # Sample the open centre of each new bracket window throughout its print.
    window = h.box(4.4, 5.7, -1.9, .5, 18.52, 19.12) ^ (h.r31.cap() - h.bracket())
    routes['DFRobot_Hole_Bracket']['Right crossbar window'] = window
    routes['DFRobot_Hole_Bracket']['Left crossbar window'] = window.mirror((1., 0., 0.))
    return routes, material


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    exports = args.scratch / 'build-source' / 'exports'
    report = inspect(args.archive, exports, print_routes,
                     read_json(args.scratch / 'print-checks.json'))
    report['rod_mount_bonds'] = verify_bonds(args.archive, exports)
    if not report['rod_mount_bonds']['passed']:
        report['failures'].append(['Key_Carrier', 'Insufficient deposited width across a rod-mount joint'])
    report['crossbar_windows'] = verify_windows(args.archive, exports)
    if not report['crossbar_windows']['passed']:
        report['failures'].append(['DFRobot_Hole_Bracket', 'Blocked crossbar window or missing rim'])
    report['passed'] = not report['failures']
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    if not report['passed']:
        raise SystemExit('See the R33 plate audit for the remaining issues.')


if __name__ == '__main__':
    main()
