#!/usr/bin/env python3
"""Check battery loading and screw caps using the FINAL exported STL meshes.

The manifest supplies hashes and print-to-assembly transforms only. Geometry
comes from the STL bytes, never cached assembly vertices or fresh CAD solids.
No slicer simulation or physical strength/fit acceptance is implied.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(exports):
    # Helpers are used for primitive probes and reconstruction, not regenerated
    # model geometry. This distinguishes actual export tests from CAD tests.
    c = load_module('battery_check_v20_library', HERE.parent / 'v20/wand_cad.py')
    cp = load_module('battery_check_cap_parameters', HERE / 'cap_design.py')
    manifest_path = exports / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    records = {record['name']: record for record in manifest['parts']}
    loaded, hashes = {}, {}

    def model(name):
        if name not in loaded:
            record = records[name]
            path = exports / record['file']
            actual = digest(path)
            assert actual == record['sha256'], ('stale mesh hash', name)
            mesh = trimesh.load_mesh(path, process=True)
            assert mesh.is_watertight and mesh.is_winding_consistent, name
            matrix = np.asarray(record['print_to_assembly'], dtype=float)
            assert matrix.shape == (4, 4), name
            assert abs(np.linalg.det(matrix[:3, :3]) - 1.) < .0001, name
            mesh.apply_transform(matrix)
            loaded[name] = c.b.closed_mesh(mesh.vertices.tolist(),
                                           mesh.faces.tolist(), name + ' final STL')
            assert len(loaded[name].decompose()) == 1, ('multiple exported solids', name)
            hashes[name] = actual
        return loaded[name]

    hands = {hand: model('Grip_' + hand.title()) for hand in ('left', 'right')}
    loop, keeper = model('Removable_Finger_Loop'), model('Loop_Keeper_Key')
    sled = model('Battery_Sled')
    caps = {'light': model('Battery_Screw_Cap_Light'),
            'weighted': model('Battery_Screw_Cap_Weighted')}
    # Conservative rectangular nominal cell: do not assume rounded corners to
    # make an incompatible rail appear clear. The floor ends Z14.2; a Z14.5
    # cell position reserves 0.3 mm for a removable soft pad, not compression.
    cell = c.box(-10., 10., -3., 3., 14.5, 54.5)
    cell_clearance = c.box(-10.2, 10.2, -3.2, 3.2, 14.5, 54.5)
    cell_sled_overlap = abs((cell ^ sled).volume())
    cell_margin_sled_overlap = abs((cell_clearance ^ sled).volume())
    report = {
        'verification': 'final exported STL + verified print-to-assembly transforms',
        'manifest_sha256': digest(manifest_path),
        'physical_fit_verified': False,
        'cell': {'nominal_mm': [20., 6., 40.], 'provisional_product': True,
                 'conservative_rectangular_shape': True,
                 'seated_z_mm': [14.5, 54.5],
                 'target_side_clearance_mm': .2,
                 'cell_sled_overlap_mm3': round(cell_sled_overlap, 8),
                 'cell_0_2mm_side_clearance_sled_overlap_mm3':
                     round(cell_margin_sled_overlap, 8)},
        'bottom_loading': {}, 'cap_screw_motion': {},
    }
    # A convex hull of both sled poses is a conservative CONTINUOUS envelope
    # of every translated final-STL point. It fills some ladder gaps but never
    # misses an intermediate obstacle. Discrete real-STL poses are reported as
    # a second, independent check and can locate any blocked diaphragm.
    descent = 80.
    sled_sweep = c.Manifold.batch_hull([sled, sled.translate((0., 0., -descent))])
    cell_sweep = c.Manifold.batch_hull([cell, cell.translate((0., 0., -descent))])
    for hand, grip in hands.items():
        obstacles = grip + loop + keeper
        samples = []
        for down in np.linspace(0., descent, 161):
            pose = (0., 0., -float(down))
            samples.append({'down_mm': round(float(down), 6),
                            'sled_overlap_mm3': round(abs((sled.translate(pose) ^ obstacles).volume()), 8),
                            'cell_overlap_mm3': round(abs((cell.translate(pose) ^ obstacles).volume()), 8)})
        report['bottom_loading'][hand] = {
            'cap_removed': True, 'travel_mm': descent,
            'pose_count': len(samples), 'pose_step_mm': .5,
            'sled_continuous_conservative_sweep_overlap_mm3': round(abs((sled_sweep ^ obstacles).volume()), 8),
            'cell_continuous_sweep_overlap_mm3': round(abs((cell_sweep ^ obstacles).volume()), 8),
            'maximum_sled_pose_overlap_mm3': max(s['sled_overlap_mm3'] for s in samples),
            'maximum_cell_pose_overlap_mm3': max(s['cell_overlap_mm3'] for s in samples),
            'seated_cell_overlap_mm3': round(abs((cell ^ grip).volume()), 8),
            'seated_cell_0_2mm_side_clearance_probe_overlap_mm3': round(abs((cell_clearance ^ grip).volume()), 8),
            'samples': samples,
        }
    # The upper grip is irrelevant to downward unscrewing; crop the actual
    # final grip mesh below Z12 to keep hundreds of Boolean checks economical.
    lower_region = c.box(-30., 30., -30., 30., -25., 12.)
    lower_hands = {hand: grip ^ lower_region for hand, grip in hands.items()}
    obstacles = {'loop': loop, 'keeper': keeper, 'sled': sled, 'cell': cell}
    turns = np.linspace(0., 2.8, 337)
    for name, cap in caps.items():
        result = {'bounds_mm': list(cap.bounding_box()),
                  'cad_solid_volume_mm3': round(cap.volume(), 6),
                  'turn_samples': len(turns), 'turn_step_deg': 3.,
                  'travel_mm': round(2.8 * cp.PITCH, 6), 'against': {}}
        for obstacle_name, obstacle in {**lower_hands, **obstacles}.items():
            values = [abs((cp.screw_pose(cap, float(turn)) ^ obstacle).volume())
                      for turn in turns]
            largest = max(values)
            worst = int(np.argmax(values))
            result['against'][obstacle_name] = {
                'maximum_overlap_mm3': round(largest, 8),
                'worst_turns_out': round(float(turns[worst]), 6),
                'locked_overlap_mm3': round(values[0], 8),
            }
        result['locked_straight_withdrawal_capture_mm3'] = {
            hand: round(abs((cap.translate((0., 0., -.9)) ^ grip).volume()), 6)
            for hand, grip in lower_hands.items()
        }
        result['locked_sled_gap_mm'] = round(cap.min_gap(sled, 2.), 6)
        report['cap_screw_motion'][name] = result
    # Direct mouth section of the actual mesh. Corners of the sled's maximum
    # conservative section require only Ø22.172 mm, versus Ø24.4 mm core.
    mouth = c.box(-30., 30., -30., 30., 3.2, 11.4)
    mouth_sled_probe = c.box(-10.3, 10.3, -4.1, 4.1, 3.1, 11.5)
    report['mouth'] = {
        'nominal_clear_diameter_mm': 2. * cp.CORE_RADIUS,
        'conservative_sled_section_mm': [20.6, 8.2],
        'required_circle_diameter_mm': round(float(np.hypot(20.6, 8.2)), 6),
        'actual_grip_section_overlap_mm3': {
            hand: round(abs((grip ^ mouth ^ mouth_sled_probe).volume()), 8)
            for hand, grip in hands.items()
        },
    }
    report['mesh_sha256'] = hashes
    failures = []
    if cell_sled_overlap > .01:
        failures.append('rectangular nominal battery intersects the final sled')
    if cell_margin_sled_overlap > .01:
        failures.append('rectangular battery lacks 0.2 mm side clearance to final sled')
    for hand, values in report['bottom_loading'].items():
        for key in ['sled_continuous_conservative_sweep_overlap_mm3',
                    'cell_continuous_sweep_overlap_mm3',
                    'maximum_sled_pose_overlap_mm3', 'maximum_cell_pose_overlap_mm3',
                    'seated_cell_overlap_mm3',
                    'seated_cell_0_2mm_side_clearance_probe_overlap_mm3']:
            if values[key] > .01:
                failures.append(hand + ': ' + key)
    for name, values in report['cap_screw_motion'].items():
        for obstacle_name, collision in values['against'].items():
            if collision['maximum_overlap_mm3'] > .01:
                failures.append(name + ' cap screw path against ' + obstacle_name)
        for hand, capture in values['locked_straight_withdrawal_capture_mm3'].items():
            if capture < 1.:
                failures.append(name + ' cap lacks threaded capture on ' + hand)
        if values['locked_sled_gap_mm'] < .30:
            failures.append(name + ' cap insufficient sled-floor clearance')
    for hand, value in report['mouth']['actual_grip_section_overlap_mm3'].items():
        if value > .01:
            failures.append(hand + ' mouth blocks sled section')
    report['failures'] = failures
    report['passed'] = not failures
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports', type=Path, default=HERE / 'exports')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = check(args.exports.resolve())
    # Never replace an earlier check receipt, including failed receipts.
    with args.out.open('x') as target:
        json.dump(report, target, indent=2)
        target.write('\n')
    print(json.dumps({'passed': report['passed'], 'failures': report['failures'],
                      'mesh_count': len(report['mesh_sha256'])}, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
