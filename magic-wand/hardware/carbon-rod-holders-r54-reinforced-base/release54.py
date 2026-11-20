"""Package the reviewed printer instructions without altering their G-code."""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile

from plate54 import HERE, LABELS
from openings53 import digest
from release_accessories52 import package

REPORTS = ('Key-holder.gcode.native.json', 'machine.json', 'keys.json', 'fit.json',
           'rod.json', 'wide-base.json', 'joint.json', 'layers.json', 'spans.json',
           'fin-design.json', 'review.json')


def release(plate, output):
    archive = plate / 'Key-holder.gcode.3mf'
    sha = digest(archive)
    review = json.loads((plate / 'review.json').read_text())
    assert review['archive_sha256'] == sha and review['trial_approved']
    reopened = plate / 'reopened'
    output.mkdir(exist_ok=True, parents=True)
    for name in (*REPORTS, 'layout.3mf', 'layout.frame.json', 'tray.png', archive.name):
        copyfile(plate / name, output / name)
    for name in ('Key-holder.gcode.native.json', 'wide-base.json', 'joint.json', 'layers.json', 'keys.json', 'fit.json', 'rod.json'):
        copyfile(reopened / name, output / ('reopened-' + name))
    print_file = output / 'R54-Reinforced-Key-Holder-print-only.3mf'
    receipt = output / 'print-only.json'
    if not print_file.exists():
        return package(output / archive.name, print_file, set(LABELS), [output / name for name in REPORTS])
    # Keep the bytes already opened for Studio's release preflight.
    with ZipFile(print_file) as staged, ZipFile(archive) as source:
        assert staged.testzip() is None
        assert staged.read('Metadata/plate_1.gcode') == source.read('Metadata/plate_1.gcode')
    details = json.loads(receipt.read_text())
    assert details['sha256'] == digest(print_file) and details['source_sha256'] == sha
    details['reviewed_reports_sha256'] = {name: digest(output / name) for name in REPORTS}
    receipt.write_text(json.dumps(details, indent=2) + '\n')
    return print_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('--output', type=Path, default=HERE / 'exports')
    args = parser.parse_args()
    release(args.plate, args.output)
