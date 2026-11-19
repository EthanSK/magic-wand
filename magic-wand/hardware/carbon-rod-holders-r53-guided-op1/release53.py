"""Release the reviewed native printer instructions, CAD and reports together."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from plate53 import LABELS
from native_layout53 import mesh_path
from release_accessories52 import package

REPORTS = ('OP1-hinge.gcode.native.json', 'keys.json', 'fit.json', 'contacts.json',
           'layers.json', 'spans.json', 'wide-bases.json', 'rod.json',
           'separation-and-machine.json', 'reopened.json', 'fit-trial-review.json')


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_paths(folder, archive_hash):
    for name in ('keys', 'fit'):
        report = read(folder / (name + '.json'))
        assert report['archive_sha256'] == archive_hash
        for gauges in report['parts'].values():
            assert all(not gauge['obstructed_poses'] for gauge in gauges.values()), name
    layers = read(folder / 'layers.json')
    assert layers['archive_sha256'] == archive_hash and layers['native_support_moves'] == 0
    assert set(layers['parts']) == set(LABELS)
    assert all(not row['completely_unsupported_starts'] for row in layers['parts'].values())
    assert read(folder / 'wide-bases.json')['archive_sha256'] == archive_hash


def release(model, plate, exports):
    archive = plate / 'OP1-hinge.gcode.3mf'
    source_hash = digest(archive)
    layout = read(plate / 'layout.frame.json')
    assert layout['layout_sha256'] == digest(plate / 'layout.3mf')
    assert all((plate / f).is_file() for f in REPORTS)
    for info in layout['parts'].values():
        source = mesh_path(info['source'],model)
        assert digest(source) == info['source_sha256'], source.name
    mechanical = read(model / 'mechanical-fit.json')
    assert mechanical['passes']
    for name, sha in mechanical['checked_mesh_sha256'].items():
        assert sha == digest(model / (name + '-assembly.stl'))
    check_paths(plate, source_hash)
    reopened = read(plate / 'reopened.json')
    assert reopened['checked_archive'] == source_hash and not reopened['warning']
    check_paths(plate / 'reopened', reopened['reopened_archive'])
    review = read(plate / 'fit-trial-review.json')
    assert review['archive_sha256'] == source_hash and review['decision'] == 'pass for monitored fit trial'
    destination = exports / 'print-mechanisms'
    destination.mkdir(exist_ok=True, parents=True)
    for f in [*model.glob('*-assembly.stl'), *(model / n for n in ('dimensions.json', 'mechanical-fit.json', 'key-bearing.json', 'locator-fit.json'))]:
        if f.resolve() != (exports / f.name).resolve():
            shutil.copyfile(f, exports / f.name)
    for name in (*REPORTS, archive.name, 'layout.3mf', 'layout.frame.json', 'tray.png'):
        if (plate / name).resolve() != (destination / name).resolve():
            shutil.copyfile(plate / name, destination / name)
    for name in ('keys', 'fit', 'layers', 'wide-bases'):
        shutil.copyfile(plate / 'reopened' / (name + '.json'), destination / ('reopened-' + name + '.json'))
    return package(destination / archive.name, destination / 'R53-Guided-OP1-and-Hinge-print-only.3mf',
                   set(LABELS), [destination / name for name in REPORTS])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('model', type=Path)
    parser.add_argument('plate', type=Path)
    parser.add_argument('--exports', type=Path, default=Path(__file__).resolve().parent / 'exports')
    args = parser.parse_args()
    release(args.model, args.plate, args.exports)
