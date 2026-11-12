"""Check the R35 slice, including the new first-layer load paths.

Run audit35.py with the sliced archive, plate35.py output directory and report path.
"""

import argparse
import json
from math import floor
from pathlib import Path

import manifold3d as mf
import numpy as np

import holder35 as design
from audit34 import print_routes, verify_bonds, verify_stops, verify_windows
from audit_plate32 import inspect, load_checker
from plate35 import plate

ROOF_LAYER = 15.8
SUPPORT_LAYER = 15.4


def rectangle(low_x, low_y, high_x, high_y):
    return mf.CrossSection.square((high_x - low_x, high_y - low_y)).translate((low_x, low_y))


def early_connections(data, samples, regions, footprints, q):
    """Each path crosses its full reinforcement and sits on earlier plastic."""
    widths, tops = data[:, 3], data[:, 7]
    rows = []
    expected = 0
    for name, (region, entry, exit, height) in regions.items():
        expected += floor((height + .001) / .2)
        x0, y0, x1, y1 = region.bounds()
        near = ((samples[:, :2] >= [x0 - .6, y0 - .6])
                & (samples[:, :2] <= [x1 + .6, y1 + .6])).all(1)
        previous = None
        for top in np.unique(tops[near & (tops > 0.) & (tops <= height + .001)]):
            layer = near & (abs(tops - top) < .001)
            deposited = footprints(q, samples[layer, :2], widths[layer]) ^ region
            crossing = [part for part in deposited.decompose()
                        if (part ^ entry).area() > .08 and (part ^ exit).area() > .08]
            backed = 1. if previous is None else (deposited ^ previous).area() / max(deposited.area(), 1e-8)
            rows.append({'connection': name, 'top_mm': round(float(top), 3),
                         'continuous': bool(crossing), 'prior_overlap_fraction': round(backed, 4)})
            previous = deposited
    return {'layers': rows, 'passed': len(rows) == expected and
            all(row['continuous'] and row['prior_overlap_fraction'] >= .75 for row in rows)}


def audit_roots(archive, exports):
    checker = load_checker().audit
    data, features, _, _, offset, objects, *_ = checker.read_project(archive)
    names = np.asarray(features)[data[:, 5].astype(int)]
    model_only = (names != 'Prime tower') & ~np.char.startswith(names, 'Skirt') & ~np.char.startswith(names, 'Support')
    data = data[model_only]
    xyz = data[:, :3] + offset
    q, footprints = checker.q, checker.start_audit.bead_footprints
    manifest = plate.read_json(exports / 'manifest.json')['parts']
    anchors = plate.read_json(exports / 'anchors.json')['parts']
    result = {}
    for name in (plate.KEY, plate.BRACKET):
        samples = xyz - objects[name]['vertices'].min(0)
        to_print = np.linalg.inv(np.asarray(manifest[name]['print_to_assembly']))[:3, :]
        if name == plate.KEY:
            regions = {}
            for label, (brace, height) in design.key_braces().items():
                x0, low_y, x1, high_y = brace.transform(to_print).slice(.1).bounds()
                regions[label] = (
                    rectangle(x0, low_y, x1, high_y),
                    rectangle(x0, low_y, x1, low_y + .65),
                    rectangle(x0, high_y - .65, x1, high_y),
                    height,
                )
        else:
            x0, y0, x1, y1 = design.touch_web().transform(to_print).slice(.1).bounds()
            regions = {'front crossbar': (rectangle(x0, y0, x1, y1),
                                          rectangle(x0, y0, x0 + 1.2, y1),
                                          rectangle(x1 - 1.2, y0, x1, y1),
                                          design.TOUCH_WEB_BACK - design.TOUCH_WEB_FRONT)}
        connections = early_connections(data, samples, regions, footprints, q)
        holes = pad_holes(data, samples, anchors[name], footprints, q)
        result[name] = {'early_connections': connections, 'pad_holes': holes,
                        'passed': connections['passed'] and holes['passed']}
    return result


def pad_holes(data, samples, anchor, footprints, q):
    rows = []
    for top in (.2, .4):
        for index, (x, y) in enumerate(anchor['hole_centres_print_xy_mm'], 1):
            near = ((abs(samples[:, 0] - x) < 1.6) & (abs(samples[:, 1] - y) < 1.6)
                    & (abs(data[:, 7] - top) < .001))
            deposited = footprints(q, samples[near, :2], data[near, 3])
            core = mf.CrossSection.circle(1., 48).translate((x, y))
            rows.append({'hole': index, 'top_mm': top, 'blocked_core_mm2': round((core ^ deposited).area(), 5)})
    return {'holes': rows, 'passed': all(row['blocked_core_mm2'] < .01 for row in rows)}


def connector_support(data, positions, names, objects, q, starts):
    """Find removable support immediately below the formerly loose OP1 loop."""
    local = positions - objects[plate.KEY]['vertices'].min(0)
    support = np.char.startswith(names, 'Support')
    assert support.any(), 'The OP1 ledge has no printed support.'
    radius = data[support, 3] / 2
    support_min = (local[support, :2] - radius[:, None]).min(0)
    support_max = (local[support, :2] + radius[:, None]).max(0)
    maximum_top = float(data[support, 7].max())
    # This is the footprint of the normal-support stack, including its
    # wider base. The other parts and the rod clip are outside this box.
    contained = (support_min >= [30.4, 5.6]).all() and (support_max <= [47., 19.2]).all() and maximum_top <= 15.601
    interface = support & (abs(data[:, 7] - SUPPORT_LAYER) < .001)
    plastic = starts.bead_footprints(q, local[interface, :2], data[interface, 3])
    # The existing connector cut ends below the first loop of the rear
    # OP1 mounting seat. The perimeter was unbacked along its entire run.
    loop = rectangle(34.4, 11.6, 40.6, 13.1)
    first_roof = ((abs(data[:, 7] - ROOF_LAYER) < .001) & (names == 'Overhang wall')
                  & q._inside(loop, local[:, :2]))
    centres = local[first_roof, :2]
    direct = int(q._inside(plastic, centres).sum())
    near = int(q._inside(plastic.offset(.25, q.JoinType.Round), centres).sum())
    return {
        'part': plate.KEY, 'top_gap_mm': .2, 'support_samples': int(support.sum()),
        'bounds_print_xy_mm': [support_min.round(4).tolist(), support_max.round(4).tolist()],
        'highest_support_layer_mm': round(maximum_top, 3),
        'supported_loop_mm': ROOF_LAYER, 'support_below_loop_mm': SUPPORT_LAYER,
        'loop_samples': len(centres), 'directly_above_support': direct, 'within_quarter_mm': near,
        'removal_required': ('Break up and peel the support through the outboard OP1 connector opening, '
                             'then clear the remaining interface before fitting the PCB.'),
        'passed': bool(contained and len(centres) > 100 and near == len(centres)),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    exports = args.scratch / 'build-source' / 'exports'
    result = inspect(args.archive, exports, print_routes, plate.read_json(args.scratch / 'print-checks.json'),
                     removable_support=connector_support)
    for name, verify in (('travel_stop_bonds', verify_stops), ('rod_mount_bonds', verify_bonds),
                         ('crossbar_windows', verify_windows)):
        result[name] = verify(args.archive, exports)
        if not result[name]['passed']:
            result['failures'].append([name, 'Deposited connection or opening check failed'])
    result['early_roots'] = audit_roots(args.archive, exports)
    for name, root in result['early_roots'].items():
        if not root['passed']:
            result['failures'].append([name, 'Early reinforcement or perforated pad check failed'])
    result['passed'] = not result['failures']
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise SystemExit('See the R35 audit for remaining printability issues.')
