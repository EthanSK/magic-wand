"""Package the qualified R72 plate, retaining the exact reviewed machine instructions."""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile

import audit72
import release61
from kit72 import parts

m = audit72.m
ARCHIVE = release61.ARCHIVE
PRINT = 'R72-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'
REPORTS = ('OP1-hinge.gcode.native.json', 'fit.json', 'layers.json', 'wide-bases.json',
           'rod.json', 'separation-and-machine.json', 'joint.json', 'fin-design.json',
           'printed-seat.json', 'release-fins-and-reused-parts.json')
read, digest = release61.read, release61.digest


def release(primary, reopened):
    fit = read(m.OUT/'fit72.json')
    assert fit['passes'] and fit['carrier_sha256'] == digest(m.OUT/m.HOLDER)
    rows = parts()
    names = {row['name'] for row in rows}
    layout = digest(primary/'layout.3mf')
    review = read(primary/'review.json')
    assert review['revision'] == 'R72' and review['trial_approved'] is True
    for folder, key in ((primary,'archive_sha256'), (reopened,'reopened_sha256')):
        checksum, warning = release61.checked(folder, layout, parts, reports=REPORTS)
        assert review[key] == checksum
        assert read(folder/'OP1-hinge.gcode.native.json')['archive_sha256'] == checksum
        assert warning == review['warnings'][key]
        assert set(read(folder/'layers.json')['parts']) == names
        assert read(folder/'printed-seat.json')['passes']
        assert read(folder/'release-fins-and-reused-parts.json')['passes']
        assert all(not row['completely_unsupported_starts'] for row in read(folder/'layers.json')['parts'].values())
    native = read(reopened/'OP1-hinge.gcode.native.json')
    assert native['reopened_sliced_archive'] and native['slice_input_sha256'] == review['archive_sha256']
    for path, sha in review['source_files_sha256'].items():
        assert digest(Path(path)) == sha, path
    dest = m.OUT/'print-mechanisms'
    dest.mkdir(exist_ok=True)
    reports = []
    for prefix, folder in (('',primary), ('reopened-',reopened)):
        extra = [name for name in ('native-retention.json','native-spring-arms.json','front-print-layers.svg','front-print-layers.log') if (folder/name).exists()]
        for name in (*REPORTS,*extra):
            path = dest/(prefix+name)
            copyfile(folder/name,path)
            reports.append(path)
    for name in (ARCHIVE,'layout.3mf','layout.frame.json','review.json'):
        copyfile(primary/name,dest/name)
    with ZipFile(primary/ARCHIVE) as z:
        (dest/'tray.png').write_bytes(z.read('Metadata/top_1.png'))
    return release61.package(primary/ARCHIVE, dest/PRINT, names, [*reports,dest/'review.json'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('primary',type=Path)
    parser.add_argument('reopened',type=Path)
    args = parser.parse_args()
    print(release(args.primary,args.reopened))
