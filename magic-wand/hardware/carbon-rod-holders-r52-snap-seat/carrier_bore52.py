"""Sweep the actual 8 mm rod through every deposited layer of the upright carrier."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import numpy as np

from sockets52 import paths
from orient51 import digest


def measure(archive, frame_file):
    frame = json.loads(frame_file.read_text())['parts']['Key_Carrier']
    matrix = np.array(frame['assembly_to_machine'])
    # The source rod runs along assembly Y through X=Z=0. Here it is bed-normal.
    assert np.allclose(np.abs(matrix[:3, 1]), [0, 0, 1])
    axis = matrix[:2, 3]
    with ZipFile(archive) as src:
        code = src.read('Metadata/plate_1.gcode').decode()
    spacing = .10
    samples, labels, _ = paths.extrusion_points(code, spacing)
    near = samples[np.max(np.abs(samples[:, :2] - axis), axis=1) < 9]
    assert len(near) > 1000
    # Subtract half the maximum distance between samples as a conservative
    # bound on the closest point between samples, in addition to bead radius.
    radii = np.linalg.norm(near[:, :2] - axis, axis=1) - near[:, 3] / 2 - spacing / 2
    by_type = {name: round(float(radii[near[:, 5] == i].min()), 4)
               for i, name in enumerate(labels) if np.any(near[:, 5] == i)}
    result = dict(archive_sha256=digest(archive), frame_sha256=digest(frame_file),
                  axis_on_bed_mm=axis.tolist(), rod_radius_mm=4,
                  nearby_samples=len(near), sampled_layer_count=len(np.unique(near[:, 7])),
                  min_radius_to_plastic_mm=by_type,
                  rigid_8_mm_cylinder_passes_unflexed=bool(np.min(radii) >= 4.),
                  machine_z_from_assembly_y=matrix[2, :].tolist())
    model = near[:, 6] == frame['owner']
    plastic = model & (radii < 4) & np.array([not labels[int(i)].startswith(('Support', 'Brim', 'Skirt')) for i in near[:,5]])
    touched = np.unique(np.round(near[plastic,7], 3))
    result['model_contact_layers_mm'] = touched.tolist()
    result['model_contact_min_radius_mm'] = round(float(radii[plastic].min()), 4) if plastic.any() else None
    result['support_or_brim_in_passage'] = {key: value for key,value in by_type.items()
                                          if key.startswith(('Support', 'Brim', 'Skirt')) and value < 4}
    return result


def inspect(directory):
    reference = Path(__file__).resolve().parent.parent / 'carbon-rod-holders-r51-guided-hinge/exports/print'
    prior = measure(reference / 'paths.gcode.3mf', reference / 'trial.frame.json')
    final = measure(directory / 'Mechanisms.gcode.3mf', directory / 'layout.frame.json')
    # The two spring rings grip an 8 mm rod. The R20 CAD specifies 7.8 mm at rest.
    final['reference'] = prior
    final['nominal_relaxed_grip_diameter_mm'] = 7.8
    assert np.allclose(prior['machine_z_from_assembly_y'], final['machine_z_from_assembly_y'])
    common = set(prior['model_contact_layers_mm'])
    final['new_model_contact_layers_mm'] = [v for v in final['model_contact_layers_mm'] if v not in common]
    final['relative_to_reference_min_radius_mm'] = round(final['model_contact_min_radius_mm'] - prior['model_contact_min_radius_mm'],4)
    (directory / 'rod-passage.json').write_text(json.dumps(final, indent=2) + '\n')
    print('Entry', final['support_or_brim_in_passage'], 'smallest radius change',
          final['relative_to_reference_min_radius_mm'], 'new contact layers', final['new_model_contact_layers_mm'])


if __name__ == '__main__':
    inspect(Path(sys.argv[1]))
