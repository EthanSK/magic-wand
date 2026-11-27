"""Save the two checked R73 slice reports and the exact machine instructions they cover."""
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile
import json
import sys

import numpy as np

import kit73
import release61
from design73 import HOLDER, OUT, RADIUS, centres


def guard_layer_check(folder):
    frame = release61.read(folder / 'layout.frame.json')['parts']['Key_Carrier']
    to_machine = np.asarray(frame['assembly_to_machine'])
    path = np.asarray(centres()) @ to_machine[:3, :3].T + to_machine[:3, 3]
    # Include the entire rounded fork and a bead on either side. Check both
    # the end that meets the deck and the moving bend clear of the wired key.
    margin = RADIUS + 0.5
    x0, y0, z0 = path.min(axis=0) - margin
    x1, y1, z1 = path.max(axis=0) + margin
    layers = release61.read(folder / 'layers.json')
    carrier = layers['parts']['Key_Carrier']
    assert 0 < z0 < z1 <= carrier['layers'] * layers['layer_mm']
    flagged = []
    for run in carrier['runs_requiring_review']:
        height = run['layer'] * layers['layer_mm']
        left, bottom, right, top = run['extent_machine_xy']
        if z0 <= height <= z1 and left <= x1 and right >= x0 and bottom <= y1 and top >= y0:
            flagged.append(run)
    if flagged:
        raise ValueError(('Inspect the unbacked extrusion at the changed guard', flagged))
    return dict(machine_bounds_mm=[x0, y0, z0, x1, y1, z1], unbacked_runs_requiring_review=flagged)


def release(primary, reopened):
    layout = release61.digest(primary / 'layout.3mf')
    fit = release61.read(OUT / 'fit73.json')
    assert fit['passes'] and fit['carrier_sha256'] == release61.digest(OUT / HOLDER)
    dest = OUT / 'print-mechanisms'
    dest.mkdir(exist_ok=True)
    copies = []
    reviews = {}
    for label, folder in [('primary', primary), ('reopened', reopened)]:
        sha, warnings = release61.checked(folder, layout, kit73.parts)
        assert not warnings
        layers = release61.read(folder / 'layers.json')
        assert layers['native_support_moves'] == 0
        assert all(not part['completely_unsupported_starts'] for part in layers['parts'].values())
        fit_routes = release61.read(folder / 'fit.json')['parts']
        reviews[label] = dict(archive_sha256=sha, route_groups=sum(map(len, fit_routes.values())),
                              part_count=len(layers['parts']), guard=guard_layer_check(folder))
        for name in release61.REPORTS:
            target = dest / (name if label == 'primary' else 'reopened-' + name)
            copyfile(folder / name, target)
            copies.append(target)
    native = release61.read(reopened / 'OP1-hinge.gcode.native.json')
    assert native['reopened_sliced_archive'] and native['slice_input_sha256'] == reviews['primary']['archive_sha256']
    review = dest / 'review.json'
    review.write_text(json.dumps(dict(revision='R73', physical_fit_verified=False,
                                      layout_sha256=layout, carrier_sha256=fit['carrier_sha256'],
                                      slices=reviews), indent=2) + '\n')
    for name in (release61.ARCHIVE, 'layout.3mf', 'layout.frame.json'):
        copyfile(primary / name, dest / name)
    with ZipFile(primary / release61.ARCHIVE) as archive:
        (dest / 'tray.png').write_bytes(archive.read('Metadata/top_1.png'))
    release61.package(primary / release61.ARCHIVE, dest / 'R73-Complete-Key-Holder-A1-mini-PETG-print-only.3mf',
                      {row['name'] for row in kit73.parts()}, [*copies, review])


if __name__ == '__main__':
    release(Path(sys.argv[1]), Path(sys.argv[2]))
