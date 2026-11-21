"""Audit one native R57 slice folder from its deposited toolpaths.

Expects layout.3mf, layout.frame.json, OP1-hinge.gcode.3mf, OP1-hinge.gcode.native.json and
native/slice.log, as written by plate57.py and the saved headless slicer script.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from plate57 import HARDWARE, LABELS, MINIMUM_BASE_MM2, MODEL
import fit57
from adhesion53 import bases, verify
from joint54 import measure as seam
from layers53 import inspect
from native_layout53 import load_solid
from openings53 import keys, read_native
from panel55 import BAY, report55
from parts52 import audit, digest

R55 = HARDWARE / 'carbon-rod-holders-r55-easy-release/exports'
ARCHIVE = 'OP1-hinge.gcode.3mf'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def rod_bore(archive, position):
    """No temporary plastic inside the 8 mm rod bore, which stands vertically in this print."""
    points, labels = read_native(archive)
    near = points[np.linalg.norm(points[:, :2] - position[:2, 3], axis=1) < 8]
    radius = np.linalg.norm(near[:, :2] - position[:2, 3], axis=1) - near[:, 3] / 2 - .06
    temporary = np.array([n.startswith(('Support', 'Brim', 'Skirt', 'Prime tower')) for n in labels])[near[:, 5].astype(int)]
    record = dict(archive_sha256=digest(archive), checked_samples=len(radius), min_radius_mm=float(radius.min()),
                  working_rod_mm=8.0, temporary_plastic_in_rod=int((temporary & (radius < 4.)).sum()))
    assert len(radius) > 1000 and not record['temporary_plastic_in_rod'], record
    return record


def check(plate):
    archive, layout, frame_file = plate / ARCHIVE, plate / 'layout.3mf', plate / 'layout.frame.json'
    frame = read(frame_file)
    sha = digest(archive)
    native = read(archive.with_suffix('.native.json'))
    assert native['archive_sha256'] == sha and native['return_code'] == 0
    assert len(native['plates']) == 1 and not native['plates'][0]['warning_message']
    assert 'got warnings:' not in (plate / 'native/slice.log').read_text()
    assert frame['layout_sha256'] == digest(layout)
    assert set(frame['parts']) == set(LABELS)
    for part, entry in frame['parts'].items():
        assert digest(MODEL / entry['source']) == entry['source_sha256'], part

    audit(archive, layout, plate / 'separation-and-machine.json', set(LABELS))
    adhesion = bases(archive)
    verify(adhesion, minimum_base_mm2=MINIMUM_BASE_MM2)
    write(plate / 'wide-bases.json', adhesion)
    keys(archive, frame_file, ['Key_Carrier'], plate / 'keys.json')
    fit57.check(archive, frame_file, plate / 'fit.json')
    write(plate / 'layers.json', inspect(archive))

    carrier = frame['parts']['Key_Carrier']
    position = np.asarray(carrier['assembly_to_machine'])
    assert np.allclose(abs(position[:3, 1]), [0, 0, 1])
    write(plate / 'rod.json', rod_bore(archive, position))

    # The holder keeps the R55 open-bay base: six rim tabs, nothing on or round the hinge.
    body = load_solid(MODEL / carrier['source'])
    current = seam(archive, frame, body, regions={'hinge_bay': BAY})
    proven = read(R55 / 'joint.json')['current']
    write(plate / 'joint.json', dict(r55=proven, current=current))
    assert current['vertical_joint_area_mm2'] >= .9 * proven['vertical_joint_area_mm2'], (proven, current)
    assert len(current['layers']) >= len(proven['layers'])
    assert current['regional_joint_area_mm2']['hinge_bay'] < .25, current
    oriented = position[:3].copy()
    oriented[:2, 3] = 0
    design = report55(body.transform(oriented), carrier['adhesion_panel'])
    assert design['hinge_bay_open_to_panel_edge'] and design['nearest_base_to_hinge_mm'] >= 3
    assert design['base_volume_in_hinge_bay_mm3'] == 0 and design['fins_on_hinge'] == 0
    assert len(design['fins']) == 6 and design['panel_pieces'] == 1
    write(plate / 'fin-design.json', dict(archive_sha256=sha, **design))
    print(f'Passed R57 native checks, holder seam {current["vertical_joint_area_mm2"]} mm2, archive {sha}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    check(parser.parse_args().plate)
