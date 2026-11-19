"""Check seven separate native objects and archive their exact machine instructions."""
import json
from pathlib import Path
import sys
from zipfile import ZipFile
from parts52 import audit
from plate52 import EXTRAS
from orient51 import digest
from plate38 import recipe
from check_lid51 import check as check_lid


def release(out):
    archive=out/'Clips-and-holders.gcode.3mf'
    editable=out/'Clips-and-holders.3mf'
    assert not json.loads(archive.with_suffix('.native.json').read_text())['plates'][0]['warning_message']
    audit(archive,editable,out/'separation-and-machine.json',{'Battery_End_Door',*EXTRAS})
    check_lid(archive,out/'lid-openings.json')
    return package(archive, out/'Magic-Wand-R52-Clips-and-Holders-print-only.3mf',
                   {'Battery_End_Door', *EXTRAS})


def package(archive, saved, parts, reports=()):
    """Keep the exact native G-code and bind the reviews to the printer file."""
    out=saved.parent
    recipe.make_print_only(archive,out).replace(saved)
    with ZipFile(saved) as dst, ZipFile(archive) as src:
        assert dst.testzip() is None and dst.read('Metadata/plate_1.gcode')==src.read('Metadata/plate_1.gcode')
    receipt=out/'print-only.json'
    data=json.loads(receipt.read_text())
    assert data['sha256']==digest(saved)
    data.update(file=saved.name,parts=sorted(parts))
    if reports:
        data['reviewed_reports_sha256']={path.name:digest(path) for path in reports}
    receipt.write_text(json.dumps(data,indent=2)+'\n')
    print(saved,flush=True)
    return saved


if __name__=='__main__':
    release(Path(sys.argv[1]))
