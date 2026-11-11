"""Confirm that both new crossbar windows have printed walls and open centres."""

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

import holder33 as h
from audit_plate32 import SOURCE_SUFFIX, digest, load_checker, read_json


def verify_windows(archive, source):
    audit = load_checker().audit
    q, starts = audit.q, audit.start_audit
    data, features, _, _, offset, objects, _, _ = audit.read_project(archive)
    name = 'DFRobot_Hole_Bracket'
    mesh = trimesh.load_mesh(source / f'{name}{SOURCE_SUFFIX}')
    saved = objects[name]['vertices']
    shift = (saved.max(0) + saved.min(0) - mesh.bounds.sum(0)) / 2
    frame = np.asarray(read_json(source / 'manifest.json')['parts'][name]['print_to_assembly'])
    to_print = np.linalg.inv(frame)[:3, :]
    wall = h.bracket().transform(to_print)
    cut = h.r31.cap() - h.bracket()
    xy = data[:, :2] + offset[:2] - shift[:2]
    model = np.asarray(features)[data[:, 5].astype(int)] != 'Prime tower'
    result = {}
    for side, sign in [('right', 1), ('left', -1)]:
        region = cut ^ h.box(*sorted((2.7 * sign, 7.5 * sign)), -3., 3., 18.45, 19.25)
        region = region.transform(to_print)
        low, high = np.asarray(region.bounding_box()).reshape(2, 3)
        near = model & (xy >= low[:2] - 1.).all(1) & (xy <= high[:2] + 1.).all(1)
        near &= (data[:, 7] > low[2]) & (data[:, 7] < high[2] + .2)
        layers = []
        for layer in np.unique(data[near, 7]):
            same_layer = near & (abs(data[:, 7] - layer) < .001)
            z = layer - data[same_layer, 4][0] / 2
            cut_section = region.slice(z)
            opening = cut_section.offset(-.18)
            if opening.area() < .1:
                continue
            rim = (cut_section.offset(.65) - cut_section) ^ wall.slice(z)
            material = starts.bead_footprints(q, xy[same_layer], data[same_layer, 3])
            layers.append({'layer_top_mm': round(float(layer), 3), 'open_core_mm2': round(opening.area(), 4),
                           'intrusion_mm2': round((opening ^ material).area(), 4),
                           'printed_rim_mm2': round((rim ^ material).area(), 4)})
        passed = len(layers) >= 8 and all(row['intrusion_mm2'] < .015 and row['printed_rim_mm2'] > .1 for row in layers)
        result[side] = {'layers': layers, 'passed': passed}
    return {'archive_sha256': digest(archive), 'windows': result, 'passed': all(row['passed'] for row in result.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('staged_exports', type=Path)
    args = parser.parse_args()
    result = verify_windows(args.archive, args.staged_exports)
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit('A crossbar window is obstructed or lacks printed rim material.')
