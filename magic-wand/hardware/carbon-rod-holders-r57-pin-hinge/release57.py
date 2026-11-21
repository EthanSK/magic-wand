"""Package the checked R57 native archive without changing the machine instructions."""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile

from verify57 import ARCHIVE, LABELS, MODEL, read
from release_accessories52 import package
from parts52 import digest

REPORTS = (
    'OP1-hinge.gcode.native.json', 'fit.json', 'keys.json', 'layers.json', 'wide-bases.json',
    'rod.json', 'separation-and-machine.json', 'joint.json', 'fin-design.json',
)
PRINT_NAME = 'R57-Pin-Hinge-A1-mini-PETG-print-only.3mf'


def release(plate, output):
    """Bind both native audits and the independent review to the editable and printer files. — GPT-6.2 Sol"""
    archive = plate / ARCHIVE
    reopened = plate / 'reopened'
    archive_hash, reopened_hash = digest(archive), digest(reopened / ARCHIVE)
    layout_hash = digest(plate / 'layout.3mf')
    for folder, native_hash in ((plate, archive_hash), (reopened, reopened_hash)):
        assert digest(folder / 'layout.3mf') == layout_hash
        assert read(folder / 'layout.frame.json')['layout_sha256'] == layout_hash
        assert read(folder / 'OP1-hinge.gcode.native.json')['archive_sha256'] == native_hash
        assert read(folder / 'joint.json')['current']['archive_sha256'] == native_hash
        layers = read(folder / 'layers.json')
        assert layers['archive_sha256'] == native_hash and layers['native_support_moves'] == 0
        assert set(layers['parts']) == set(LABELS)
        assert all(not part['completely_unsupported_starts'] for part in layers['parts'].values())
        for name in ('fit', 'keys'):
            report = read(folder / f'{name}.json')
            assert report['archive_sha256'] == native_hash
            assert all(not route['obstructed_poses'] for part in report['parts'].values() for route in part.values())

    mechanical = read(MODEL / 'mechanical-fit.json')
    assert mechanical['passes']
    for name, sha in mechanical['checked_mesh_sha256'].items():
        assert digest(MODEL / f'{name}-assembly.stl') == sha, name
    review = read(plate / 'review.json')
    assert review['archive_sha256'] == archive_hash and review['trial_approved']

    output.mkdir(exist_ok=True, parents=True)
    for name in ('layout.3mf', 'layout.frame.json', ARCHIVE, 'review.json', *REPORTS):
        copyfile(plate / name, output / name)
    for name in REPORTS:
        copyfile(reopened / name, output / f'reopened-{name}')
    reopened_receipt = output / 'reopened.json'
    reopened_receipt.write_text(json.dumps(dict(layout_sha256=layout_hash, checked_archive=archive_hash,
                                               reopened_archive=reopened_hash), indent=2) + '\n')
    with ZipFile(archive) as native:
        (output / 'tray.png').write_bytes(native.read('Metadata/top_1.png'))
    return package(archive, output / PRINT_NAME, set(LABELS),
                   [output / name for name in (*REPORTS, 'reopened.json', 'review.json')])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('--output', type=Path, default=MODEL / 'print-mechanisms')
    args = parser.parse_args()
    release(args.plate, args.output)
