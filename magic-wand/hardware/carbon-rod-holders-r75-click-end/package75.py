"""Retain the native plate and its matching independent re-slice and fit reports."""
import json
from pathlib import Path
from shutil import copyfile
import sys
from zipfile import ZipFile

import plate75
import guard_layers74
import release61

OUT = plate75.OUT
PREVIOUS = plate75.design.prior.OUT / 'print-mechanisms'


def compare_layers(folder):
    layers = release61.read(folder / 'layers.json')
    previous = release61.read(PREVIOUS / 'layers.json')
    new_spans = []
    for name, part in layers['parts'].items():
        if part['completely_unsupported_starts']:
            raise ValueError(f'A toolpath in {name} starts in midair')
        baseline = previous['parts'][name]['runs_requiring_review']
        for span in part['runs_requiring_review']:
            if any(guard_layers74.nearby(span, old) for old in baseline):
                continue
            # The local changes bridge very short turns. Both ends must have
            # printed plastic and the same carrier already has an equal or
            # longer anchored turn with at least as much sideways curvature.
            reference = next((old for old in baseline if old['two_anchors']
                              and old['mm'] >= span['mm']
                              and old['bend_mm'] >= span['bend_mm']), None)
            if name != 'Key_Carrier' or not span['two_anchors'] or span['mm'] > 1.55 or not reference:
                raise ValueError(f'Unsupported extrusion requires review: {name} {span}')
            new_spans.append(dict(part=name, span=span, reference=reference))
    if layers['native_support_moves']:
        raise ValueError('Unexpected generated supports in this plate')
    return new_spans


def package(primary, reopened):
    source = OUT / plate75.design.HOLDER
    checks = release61.read(OUT / 'fit75.json')
    assert checks['passes'] and checks['carrier_sha256'] == release61.digest(source)
    output = OUT / 'print-mechanisms'
    output.mkdir(exist_ok=True)
    inventory = {part['name'] for part in plate75.parts()}
    layout_hash = release61.digest(primary / 'layout.3mf')
    reports = []
    studies = {}
    for label, folder in [('primary', primary), ('reopened', reopened)]:
        checksum, warning = release61.checked(folder, layout_hash, plate75.parts)
        if warning:
            raise ValueError(warning)
        fit = release61.read(folder / 'fit.json')['parts']
        assert not fit['Key_Carrier']['battery_end_to_end']['obstructed_poses']
        studies[label] = dict(archive_sha256=checksum, route_groups=sum(map(len, fit.values())),
                              part_count=len(inventory), new_anchored_spans=compare_layers(folder))
        for name in release61.REPORTS:
            destination = output / (name if label == 'primary' else 'reopened-' + name)
            copyfile(folder / name, destination)
            reports.append(destination)
    native = release61.read(reopened / 'OP1-hinge.gcode.native.json')
    assert native['reopened_sliced_archive'] and native['slice_input_sha256'] == studies['primary']['archive_sha256']
    report = output / 'review.json'
    report.write_text(json.dumps(dict(revision='R75', physical_fit_verified=False,
                                      layout_sha256=layout_hash, carrier_sha256=checks['carrier_sha256'],
                                      slices=studies), indent=2) + '\n')
    for name in (release61.ARCHIVE, 'layout.3mf', 'layout.frame.json'):
        copyfile(primary / name, output / name)
    with ZipFile(primary / release61.ARCHIVE) as archive:
        (output / 'tray.png').write_bytes(archive.read('Metadata/top_1.png'))
    release61.package(primary / release61.ARCHIVE, output / 'R75-Complete-Key-Holder-A1-mini-PETG-print-only.3mf',
                      inventory, [*reports, report])


if __name__ == '__main__':
    package(Path(sys.argv[1]), Path(sys.argv[2]))
