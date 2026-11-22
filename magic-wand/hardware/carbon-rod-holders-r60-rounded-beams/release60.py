"""Package the checked R60 standalone key-holder files without changing the native G-code."""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile

from plate60 import LABELS, parts
from design60 import OUT as MODEL, PREVIOUS
from verify59 import ARCHIVE, read
from release_accessories52 import package
from parts52 import digest

REPORTS = (
    'OP1-hinge.gcode.native.json', 'fit.json', 'layers.json', 'wide-bases.json',
    'rod.json', 'separation-and-machine.json', 'joint.json', 'fin-design.json',
)
PRINT_NAME = 'R60-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'


def check_receipts(plate, layout_hash):
    archive_hash = digest(plate / ARCHIVE)
    assert digest(plate / 'layout.3mf') == layout_hash
    frame = read(plate / 'layout.frame.json')
    assert frame['layout_sha256'] == layout_hash and set(frame['parts']) == set(LABELS)
    for part in parts():
        assert digest(part['source']) == frame['parts'][part['name']]['source_sha256'], part['name']
    assert read(plate / 'audit-receipt.json')['exit_code'] == 0
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
    assert set(fit['lowered_backer_positive_controls']) == {'Left', 'Right'}
    assert all(r['obstructed_poses'] for r in fit['lowered_backer_positive_controls'].values())
    samples = fit['side_spring_midheight']
    assert len(samples) == 3 and all(0 < r['nominal_pack_interference_mm'] < .35 for r in samples)
    return archive_hash, native['plates'][0]['warning_message']


def release(plate, reopened, output):
    archive = plate / ARCHIVE
    layout_hash = digest(plate / 'layout.3mf')
    archive_hash, warning = check_receipts(plate, layout_hash)
    reopened_hash, reopened_warning = check_receipts(reopened, layout_hash)
    click = read(PREVIOUS / 'exports/click-fit.json')
    assert click['passes'] and click['stop_retainer']['hinge_play_study']['poses_touching_the_retainer'] == 0
    carrier = read(MODEL / 'carrier.json')
    assert digest(MODEL / 'Key_Carrier-assembly.stl') == carrier['source_sha256']
    assert not carrier['obstructed_key_poses'] and max(carrier['backer_route_overlap_mm3'].values()) < .01
    assert carrier['battery_rigid_sweep_mm3'] < .01 and carrier['new_material_inside_rod_or_wire_route_mm3'] < .01
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
