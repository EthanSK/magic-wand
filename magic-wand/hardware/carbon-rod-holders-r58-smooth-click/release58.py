"""Package the checked R58 fit-trial files without changing the native G-code."""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile

from verify58 import ARCHIVE, LABELS, MODEL, read
from release_accessories52 import package
from parts52 import digest

REPORTS = (
    'OP1-hinge.gcode.native.json', 'fit.json', 'layers.json', 'wide-bases.json',
    'rod.json', 'separation-and-machine.json', 'joint.json', 'fin-design.json',
)
PRINT_NAME = 'R58-Smooth-Click-A1-mini-PETG-print-only.3mf'


def check_receipts(plate, layout_hash):
    archive_hash = digest(plate / ARCHIVE)
    assert digest(plate / 'layout.3mf') == layout_hash
    frame = read(plate / 'layout.frame.json')
    assert frame['layout_sha256'] == layout_hash and set(frame['parts']) == set(LABELS)
    for part, source in frame['parts'].items():
        assert digest(MODEL / source['source']) == source['source_sha256'], part
    native = read(plate / 'OP1-hinge.gcode.native.json')
    assert native['archive_sha256'] == archive_hash and native['return_code'] == 0
    assert len(native['plates']) == 1
    for report in ('layers', 'fit', 'rod', 'wide-bases', 'fin-design', 'separation-and-machine'):
        assert read(plate / f'{report}.json')['archive_sha256'] == archive_hash, report
    assert read(plate / 'joint.json')['current']['archive_sha256'] == archive_hash
    layers = read(plate / 'layers.json')
    assert layers['native_support_moves'] == 0 and set(layers['parts']) == set(LABELS)
    assert all(not piece['completely_unsupported_starts'] for piece in layers['parts'].values())
    fit = read(plate / 'fit.json')
    assert fit['frame_sha256'] == digest(plate / 'layout.frame.json')
    assert all(not route['obstructed_poses'] for piece in fit['parts'].values() for route in piece.values())
    return archive_hash, native['plates'][0]['warning_message']


def release(plate, reopened, output):
    archive = plate / ARCHIVE
    layout_hash = digest(plate / 'layout.3mf')
    archive_hash, warning = check_receipts(plate, layout_hash)
    reopened_hash, reopened_warning = check_receipts(reopened, layout_hash)
    mechanics = read(MODEL / 'mechanical-fit.json')
    assert mechanics['passes']
    for name, sha in mechanics['checked_mesh_sha256'].items():
        assert digest(MODEL / f'{name}-assembly.stl') == sha, name
    carrier = read(MODEL / 'carrier.json')
    assert carrier['passes'] and digest(MODEL / 'Key_Carrier-assembly.stl') == carrier['sha256']
    review = read(plate / 'review.json')
    assert review['archive_sha256'] == archive_hash and review['trial_approved']
    assert review['reopened_sha256'] == reopened_hash
    warnings = {sha: message for sha, message in
                ((archive_hash, warning), (reopened_hash, reopened_warning)) if message}
    if warnings:
        disposition = review['native_warning']
        assert disposition['reviewed_archive_warnings'] == warnings
        assert disposition['evidence'].strip()

    output.mkdir(exist_ok=True, parents=True)
    for name in ('layout.3mf', 'layout.frame.json', ARCHIVE, 'review.json', *REPORTS):
        copyfile(plate / name, output / name)
    for name in REPORTS:
        copyfile(reopened / name, output / f'reopened-{name}')
    (output / 'reopened.json').write_text(json.dumps(dict(
        layout_sha256=layout_hash, checked_archive=archive_hash, reopened_archive=reopened_hash
    ), indent=2) + '\n')
    with ZipFile(archive) as native:
        (output / 'tray.png').write_bytes(native.read('Metadata/top_1.png'))
    return package(archive, output / PRINT_NAME, set(LABELS),
                   [output / name for name in (*REPORTS, 'reopened.json', 'review.json')])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('reopened', type=Path)
    parser.add_argument('--output', type=Path, default=MODEL / 'print-mechanisms')
    args = parser.parse_args()
    release(args.plate, args.reopened, args.output)
