"""Measure continuous deposited material from the rod saddle into each rib."""

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

import holder33 as h
from audit_plate32 import SOURCE_SUFFIX, digest, load_checker, read_json


def verify_bonds(archive, source):
    audit = load_checker().audit
    q, starts = audit.q, audit.start_audit
    data, features, _, _, offset, objects, _, _ = audit.read_project(archive)
    name = 'Key_Carrier'
    source_mesh = trimesh.load_mesh(source / f'{name}{SOURCE_SUFFIX}')
    saved = objects[name]
    shift = (saved['vertices'].max(0) + saved['vertices'].min(0) - source_mesh.bounds.sum(0)) / 2
    frame = np.asarray(read_json(source / 'manifest.json')['parts'][name]['print_to_assembly'])
    to_print = np.linalg.inv(frame)[:3, :]
    xyz = data[:, :3] + offset - shift
    features = np.asarray(features)[data[:, 5].astype(int)]
    model = (features != 'Prime tower') & ~np.char.startswith(features, 'Support')
    _, fixed, ribs, _ = h.rib_candidates()
    result = {}
    for rib_name, rib in ribs.items():
        sign = 1 if rib_name.startswith('R') else -1
        bond = fixed ^ rib
        window = h.box(*sorted((2.65 * sign, 4.75 * sign)), 12.5, 18.6, 4.4, 6.85)
        # All the bands from the saddle into the rib must be covered by one
        # footprint. Measuring across the seam catches a thin middle neck.
        bands = [h.box(*sorted((x * sign, (x + .2) * sign)), 12.5, 18.6, 4.4, 6.85).transform(to_print)
                 for x in np.linspace(2.75, 4.55, 10)]
        window, bond = window.transform(to_print), bond.transform(to_print)
        low, high = np.asarray(window.bounding_box()).reshape(2, 3)
        near = model & (xyz[:, :2] >= low[:2] - .65).all(1) & (xyz[:, :2] <= high[:2] + .65).all(1)
        near &= (data[:, 7] > low[2]) & (data[:, 7] < high[2] + .2)
        widths_by_layer = []
        run, longest = 0, 0
        previous_layer, previous_piece = None, None
        for layer in np.unique(data[near, 7]):
            same_layer = near & (abs(data[:, 7] - layer) < .001)
            z = layer - data[same_layer, 4][0] / 2
            anchor = bond.slice(z)
            if anchor.area() < .1:
                continue
            material = starts.bead_footprints(q, xyz[same_layer, :2], data[same_layer, 3])
            connected = (material ^ window.slice(z)).decompose()
            band_sections = [band.slice(z) for band in bands]
            width, piece = max(((min((piece ^ band).area() for band in band_sections) / .20, piece)
                                for piece in connected if (piece ^ anchor).area() > .1),
                               key=lambda measurement: measurement[0], default=(0., None))
            consecutive = previous_layer is not None and abs(layer - previous_layer - .2) < .002
            overlap = (piece ^ previous_piece).area() if consecutive and piece is not None and previous_piece is not None else 0.
            walls = same_layer & np.isin(features, ['Outer wall', 'Inner wall'])
            wall_area = (starts.bead_footprints(q, xyz[walls, :2], data[walls, 3]) ^ piece).area() if piece is not None else 0.
            qualifies = width >= .8 and wall_area >= .15
            if qualifies:
                run = run + 1 if consecutive and overlap >= .3 else 1
            else:
                run = 0
            longest = max(longest, run)
            previous_layer, previous_piece = layer, piece if qualifies else None
            widths_by_layer.append({'layer_top_mm': round(float(layer), 3), 'connected_width_mm': round(float(width), 4),
                                    'prior_overlap_mm2': round(float(overlap), 4), 'wall_area_mm2': round(float(wall_area), 4)})
        result[rib_name] = {'minimum_width_target_mm': .8, 'minimum_prior_overlap_mm2': .3,
                            'minimum_wall_area_mm2': .15, 'consecutive_layers_at_target': longest,
                            'layers': widths_by_layer, 'passed': longest >= 3}
    return {'archive_sha256': digest(archive), 'bonds': result, 'passed': all(row['passed'] for row in result.values())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('staged_exports', type=Path)
    args = parser.parse_args()
    result = verify_bonds(args.archive, args.staged_exports)
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit('Insufficient measured deposition at a rib root.')
