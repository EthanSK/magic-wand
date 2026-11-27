"""Bind the complete carrier kit to both checked slices and the reviewed paths."""
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile
import json
import sys

import kit74
import release61


def release(primary, reopened):
    layout_hash = release61.digest(primary / 'layout.3mf')
    fit = release61.read(kit74.OUT / 'fit74.json')
    assert fit['passes'] and fit['carrier_sha256'] == release61.digest(kit74.OUT / kit74.HOLDER)
    parts = {row['name'] for row in kit74.parts()}
    output = kit74.OUT / 'print-mechanisms'
    output.mkdir(exist_ok=True)
    artifacts = []
    reviews = {}
    for label, folder in [('primary', primary), ('reopened', reopened)]:
        checksum, warnings = release61.checked(folder, layout_hash, kit74.parts)
        assert not warnings
        layers = release61.read(folder / 'layers.json')
        assert layers['native_support_moves'] == 0 and set(layers['parts']) == parts
        assert all(not piece['completely_unsupported_starts'] for piece in layers['parts'].values())
        routes = release61.read(folder / 'fit.json')['parts']
        assert not routes['Key_Carrier']['battery_end_to_end']['obstructed_poses']
        # Former guard and pouch supports carried load here. Keep the local
        # layer assessment tied to the exact archive that was inspected.
        local = release61.read(folder / 'guard-review.json')
        assert local['passes'] and local['archive_sha256'] == checksum
        reviews[label] = dict(archive_sha256=checksum, route_groups=sum(map(len, routes.values())),
                              part_count=len(parts), print_warnings=warnings)
        for name in (*release61.REPORTS, 'guard-review.json'):
            target = output / (name if label == 'primary' else 'reopened-' + name)
            copyfile(folder / name, target)
            artifacts.append(target)
    native = release61.read(reopened / 'OP1-hinge.gcode.native.json')
    assert native['reopened_sliced_archive'] and native['slice_input_sha256'] == reviews['primary']['archive_sha256']
    review = output / 'review.json'
    review.write_text(json.dumps(dict(revision='R74', physical_fit_verified=False,
                                      carrier_sha256=fit['carrier_sha256'], layout_sha256=layout_hash,
                                      slices=reviews), indent=2) + '\n')
    for name in (release61.ARCHIVE, 'layout.3mf', 'layout.frame.json'):
        copyfile(primary / name, output / name)
    with ZipFile(primary / release61.ARCHIVE) as archive:
        (output / 'tray.png').write_bytes(archive.read('Metadata/top_1.png'))
    release61.package(primary / release61.ARCHIVE, output / 'R74-Complete-Key-Holder-A1-mini-PETG-print-only.3mf',
                      parts, [*artifacts, review])


if __name__ == '__main__':
    release(Path(sys.argv[1]), Path(sys.argv[2]))
