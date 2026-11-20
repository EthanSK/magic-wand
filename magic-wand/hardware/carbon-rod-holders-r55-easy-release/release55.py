"""Package the reviewed native printer instructions without altering their G-code."""
import argparse
import json
from pathlib import Path
from shutil import copyfile

from plate55 import HERE, LABELS
from release53 import check_paths, digest, read
from release_accessories52 import package

ARCHIVE = 'OP1-hinge.gcode.3mf'
PRINT_NAME = 'R55-Easy-Release-Complete-Hinge-print-only.3mf'
REPORTS = ('OP1-hinge.gcode.native.json', 'keys.json', 'fit.json', 'contacts.json',
           'layers.json', 'spans.json', 'wide-bases.json', 'rod.json',
           'separation-and-machine.json', 'joint.json', 'fin-design.json')


def release(plate, out, *, print_name=PRINT_NAME):
    reopened = plate / 'reopened'
    sha = digest(plate / ARCHIVE)
    reopened_sha = digest(reopened / ARCHIVE)
    for folder, archive_hash in ((plate, sha), (reopened, reopened_sha)):
        assert read(folder / 'layout.frame.json')['layout_sha256'] == digest(plate / 'layout.3mf')
        assert read(folder / 'OP1-hinge.gcode.native.json')['archive_sha256'] == archive_hash
        assert read(folder / 'joint.json')['current']['archive_sha256'] == archive_hash
        check_paths(folder, archive_hash)
    assert read(plate / 'joint.json')['current']['vertical_joint_area_mm2'] == read(reopened / 'joint.json')['current']['vertical_joint_area_mm2']
    review = read(plate / 'review.json')
    assert review['archive_sha256'] == sha and review['trial_approved']

    out.mkdir(exist_ok=True, parents=True)
    for name in (*REPORTS, 'review.json', 'layout.3mf', 'layout.frame.json', 'tray.png', ARCHIVE):
        copyfile(plate / name, out / name)
    for name in REPORTS:
        copyfile(reopened / name, out / ('reopened-' + name))
    round_trip = out / 'reopened.json'
    round_trip.write_text(json.dumps(dict(checked_archive=sha, reopened_archive=reopened_sha,
                                          layout_sha256=digest(plate / 'layout.3mf')), indent=2) + '\n')
    return package(out / ARCHIVE, out / print_name,
                   set(LABELS), [out / name for name in (*REPORTS, 'review.json', 'reopened.json')])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('--output', type=Path, default=HERE / 'exports')
    args = parser.parse_args()
    release(args.plate, args.output)
