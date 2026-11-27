"""Package the reviewed R71 native pair without changing its machine instructions.

This keeps release61.checked/package as the established archive machinery. R71's
changed report contracts, source reproduction and selected layer views are checked
here, rather than passed through release61's archived battery assumptions.
— GPT-6.1 Sol
"""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile

import audit71
import arms71
import checks71
import design71 as d
import evidence71
import hinge71 as h
import kit71 as k
import release61
import retention71
import sections71

ARCHIVE = release61.ARCHIVE
PRINT_NAME = 'R71-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'
REPORTS = (
    'OP1-hinge.gcode.native.json', 'fit.json', 'layers.json', 'wide-bases.json',
    'rod.json', 'separation-and-machine.json', 'joint.json', 'fin-design.json',
    'battery-base.json', 'passages.json', 'pin-fit.json', 'printed-seat.json',
    'r70-base-reference.json', 'mechanical-sections.json', 'supplemental-evidence.json',
    'native-retention.json', 'native-spring-arms.json',
)
IMAGES = ('r71-critical-native-layers.png', 'op1-seat-comparison.png')
digest, read = release61.digest, release61.read


def checked(folder, layout):
    # The historical reference deliberately identifies R70's archive, not R71's.
    current_reports = tuple(name for name in REPORTS if name != 'r70-base-reference.json')
    archive, warning = release61.checked(folder, layout, k.parts, reports=current_reports)
    frame = read(folder / 'layout.frame.json')
    native = read(folder / 'OP1-hinge.gcode.native.json')
    assert native['archive_sha256'] == archive
    layers = read(folder / 'layers.json')
    assert layers['native_support_moves'] == 0
    assert set(layers['parts']) == set(frame['parts'])
    assert all(not p['completely_unsupported_starts'] for p in layers['parts'].values())
    fit = read(folder / 'fit.json')
    assert fit['guide_sha256'] == digest(d.OUT / 'assembly-guide.json')
    assert fit['adapter_sha256'] == digest(audit71.__file__)
    reference = read(folder / 'r70-base-reference.json')
    old = d.r70.OUT / 'print-mechanisms'
    assert reference['archive_sha256'] == digest(old / ARCHIVE)
    assert reference['report_sha256'] == digest(old / 'joint.json')
    for name in ('battery-base.json', 'pin-fit.json', 'printed-seat.json',
                 'mechanical-sections.json', 'supplemental-evidence.json', 'native-retention.json'):
        assert read(folder / name)['passes'], name
    sections = read(folder / 'mechanical-sections.json')
    assert sections['checker_sha256'] == digest(sections71.__file__)
    assert sections['frame_sha256'] == digest(folder / 'layout.frame.json')
    extra = read(folder / 'supplemental-evidence.json')
    assert extra['carrier_sha256'] == digest(d.OUT / d.HOLDER)
    assert extra['guide_sha256'] == digest(d.OUT / 'assembly-guide.json')
    assert extra['adapter_sha256'] == digest(evidence71.__file__)
    retention = read(folder / 'native-retention.json')
    assert retention['checker_sha256'] == digest(retention71.__file__)
    assert retention['frame_sha256'] == digest(folder / 'layout.frame.json')
    arms = read(folder / 'native-spring-arms.json')
    assert arms['passes'] and arms['archive_sha256'] == archive
    assert arms['frame_sha256'] == digest(folder / 'layout.frame.json')
    assert arms['checker_sha256'] == digest(arms71.__file__)
    assert arms['dependencies_sha256'] == arms71.dependencies()
    assert all((folder / name).is_file() for name in IMAGES)
    return archive, warning


def source_checked():
    source = read(d.OUT / 'source-reproduction.json')
    checks = read(d.OUT / 'checks.json')
    assert source['passes'] and checks['passes']
    assert checks['checks_sha256'] == digest(checks71.__file__)
    modules = (d, h, d.r70, h.h70)
    assert source['generator_sha256'] == {Path(m.__file__).name: digest(m.__file__) for m in modules}
    for name, row in source['meshes'].items():
        assert row['export_sha256'] == row['reproduced_sha256'] == digest(d.OUT / name)
        assert checks['meshes_sha256'][name] == row['export_sha256']
    for name in checks71.REPORTS:
        assert read(d.OUT / name)['passes'], name


def release(primary, reopened, output=None):
    source_checked()
    layout = digest(primary / 'layout.3mf')
    first, warning = checked(primary, layout)
    second, other_warning = checked(reopened, layout)
    native = read(reopened / 'OP1-hinge.gcode.native.json')
    assert native['reopened_sliced_archive'] is True
    assert native['slice_input_sha256'] == first
    review = read(primary / 'review.json')
    assert review['revision'] == 'R71' and review['trial_approved'] is True
    assert review['archive_sha256'] == first and review['reopened_sha256'] == second
    assert review['layout_sha256'] == layout
    assert review['native_warning']['reviewed_archive_warnings'] == {
        sha: message for sha, message in ((first, warning), (second, other_warning)) if message}
    assert review['native_warning']['evidence'].strip()
    rows = k.parts()
    assert set(review['per_part']) == {p['name'] for p in rows}
    for part in rows:
        assert review['per_part'][part['name']]['source_sha256'] == digest(part['source'])
    for prefix, folder in (('', primary), ('reopened-', reopened)):
        expected = {name: digest(folder / name) for name in (*REPORTS, *IMAGES)}
        assert review['evidence_sha256'][prefix or 'primary'] == expected
    output = Path(output or d.OUT / 'print-mechanisms')
    output.mkdir(parents=True, exist_ok=True)
    for name in ('layout.3mf', 'layout.frame.json', ARCHIVE, 'review.json', *REPORTS, *IMAGES):
        copyfile(primary / name, output / name)
    for name in (*REPORTS, *IMAGES):
        copyfile(reopened / name, output / ('reopened-' + name))
    (output / 'reopened.json').write_text(json.dumps(dict(
        layout_sha256=layout, checked_archive=first, reopened_archive=second,
        audit_adapter_sha256=digest(audit71.__file__)), indent=2) + '\n')
    with ZipFile(primary / ARCHIVE) as archive:
        (output / 'tray.png').write_bytes(archive.read('Metadata/top_1.png'))
    retained = (*REPORTS, *IMAGES, 'review.json', 'reopened.json')
    return release61.package(primary / ARCHIVE, output / PRINT_NAME,
                             {p['name'] for p in rows}, [output / n for n in retained])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('primary', type=Path)
    parser.add_argument('reopened', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    release(args.primary, args.reopened, args.output)
