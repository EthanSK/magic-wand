#!/usr/bin/env python3
"""Check actual guard beads through the assembled slide-on route.

CAD clearance and a guard's own bores do not establish clearance to the wired
key holder. Include the R16/R20 holders, bought parts and stated wire/solder
allowances at every 0.25 mm pose. Pads are removed before assembly. This checks
the delivered and roundtrip slices separately; physical fit remains unverified.
Run through geometry_budget.py, one job at a time.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
from pathlib import Path
import numpy as np
import holder20 as h
import slice20 as s

OUT = h.HERE / 'exports'


def inspect(project, destination):
    manifest = json.loads((OUT / 'manifest.json').read_text())
    data, features, _, _, offset, parts, _, _ = s.s16.read_project(project)
    name = 'Finger_Guard'
    mesh = s.trimesh.load_mesh(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
    pad = s.trimesh.load_mesh(OUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl'))
    place = (parts[name]['vertices'].min(0) + parts[name]['vertices'].max(0) - mesh.bounds.sum(0)) / 2
    local = data[:, :3] + offset - place
    lo = np.minimum(mesh.bounds[0], pad.bounds[0]); hi = np.maximum(mesh.bounds[1], pad.bounds[1])
    mask = np.all(local >= lo - .4, 1) & np.all(local <= hi + .4, 1)
    points, widths, heights = local[mask], data[mask, 3], data[mask, 4]
    types = data[mask, 5].astype(int); tops = data[mask, 7]
    _, flange, plan, _, record = s.anchors20.anchor(name)
    pad_plan = flange + s.mf.CrossSection.batch_boolean(plan['necks'], s.mf.OpType.Add)
    keep = ~((tops <= record['thickness_mm'] + 1e-3) & s.q._inside(pad_plan.offset(.3, s.q.JoinType.Round), points[:, :2]))
    points, widths, heights, types = points[keep], widths[keep], heights[keep], types[keep]
    assert len(points) > 500, 'Empty or misplaced guard scan'
    pa = np.array(manifest['parts'][name]['print_to_assembly'])
    # Exact mesh identity is already checked by slice20; also verify this input
    # is bound to a completed slice audit rather than accepting an arbitrary file.
    registered = json.loads((OUT / 'slice-clearances.json').read_text())
    roundtrip = json.loads((OUT / 'roundtrip-checks.json').read_text())
    assert registered['passed'] and roundtrip['passed']
    assert registered['manifest_sha256'] == h.sha(OUT / 'manifest.json')
    assert roundtrip['input_project_sha256'] == registered['project_sha256']
    assert h.sha(project) in (registered['project_sha256'], roundtrip['resliced_project_sha256'])
    references = {'R20_key_holder': h.read(OUT / 'Key_Carrier-assembly.stl'),
                  'R16_key_holder': h.carrier_r16(), **h.bought_parts(), **h.contact_envelopes()}
    # Deliberately push the carrier 1 mm into the guard: the same transform and
    # bead test must detect this known interference instead of an empty scan.
    control = s.q.inspect_region(references['R20_key_holder'].translate((0, 0, -1.)).transform(np.linalg.inv(pa)[:3]),
                                 points, widths, heights, types, features, pa, limit=1)
    assert sum(control['violations'].values()) > 0, 'Positive interference control missed'
    rows = {}; bad = {}; candidate_count = 0
    for distance in np.arange(0, 19.01, .25):
        pose = pa.copy(); pose[1, 3] -= distance
        inverse = np.linalg.inv(pose); checks = {}
        for label, region in references.items():
            result = s.q.inspect_region(region.transform(inverse[:3]), points, widths, heights, types, features, pose, limit=3)
            checks[label] = {k: result[k] for k in ('checked_samples', 'violations', 'examples')}
            candidate_count += result['checked_samples']
            if result['violations']: bad[f'{distance:g}:{label}'] = checks[label]
        rows[f'{distance:g}'] = checks
        if int(distance * 4) % 16 == 0: print('Guard distance', distance, 'violations', len(bad), flush=True)
    assert candidate_count > 1000, 'No neighbouring reference material examined'
    result = {'project_sha256': h.sha(project), 'checker_sha256': h.sha(Path(__file__)),
              'manifest_sha256': h.sha(OUT / 'manifest.json'), 'parser_sha256': h.sha(Path(s.q.__file__)),
              'slice_audit_sha256': h.sha(OUT / 'slice-clearances.json'),
              'roundtrip_audit_sha256': h.sha(OUT / 'roundtrip-checks.json'),
              'sample_count': len(points), 'candidate_samples': candidate_count,
              'positive_control_intrusion_samples': sum(control['violations'].values()),
              'positions': len(rows), 'step_mm': .25, 'travel_mm': 19.,
              'references_per_position': len(references), 'violations': bad,
              'checks': rows, 'passed': not bad, 'physical_fit_verified': False,
              'method': 'All guard bead types after pad removal, full bead discs with inherited numerical boundary guards, against exact assembled reference meshes and stated unmeasured wiring allowances. Both seated pose and full slide-on route; no physical tolerance guarantee.'}
    destination.write_text(json.dumps(result, indent=2) + '\n')
    print('Guard actual beads', len(points), 'positions', len(rows), 'violations', bad, flush=True)
    assert not bad


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, default=OUT / 'R20-A1-mini-PETG.gcode.3mf')
    parser.add_argument('--report', type=Path, default=OUT / 'guard-path-checks.json')
    args = parser.parse_args(); inspect(args.project, args.report)
