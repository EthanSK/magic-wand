"""Package one independently approved, twice-sliced R61 plate without reslicing G-code."""
from pathlib import Path
from shutil import copyfile
import argparse
import json
from zipfile import ZipFile
from design61 import OUT
from plate61 import LABELS, parts
from release60 import ARCHIVE, REPORTS, digest, package, read

PRINT_NAME='R61-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'

def checked(folder,layout,part_rows=parts):
    native=read(folder/'OP1-hinge.gcode.native.json')
    archive=digest(folder/ARCHIVE)
    frame=read(folder/'layout.frame.json')
    assert frame['layout_sha256']==digest(folder/'layout.3mf')==layout
    assert read(folder/'audit-receipt.json')['exit_code']==native['return_code']==0
    assert set(frame['parts'])==set(LABELS)
    assert all(digest(p['source'])==frame['parts'][p['name']]['source_sha256'] for p in part_rows())
    for name in REPORTS:
        report=read(folder/name)
        assert (report['current'] if name=='joint.json' else report)['archive_sha256']==archive
    fit=read(folder/'fit.json')
    assert fit['frame_sha256']==digest(folder/'layout.frame.json')
    assert all(not route['obstructed_poses'] for routes in fit['parts'].values() for route in routes.values())
    assert len(native['plates'])==1
    return archive,native['plates'][0]['warning_message']

def release(primary,reopened,export_dir=OUT,part_rows=parts,print_name=PRINT_NAME):
    layout=digest(primary/'layout.3mf')
    archive,warning=checked(primary,layout,part_rows)
    other,other_warning=checked(reopened,layout,part_rows)
    review=read(primary/'review.json')
    assert review['archive_sha256']==archive and review['reopened_sha256']==other and review['trial_approved']
    assert review['native_warning']['reviewed_archive_warnings']=={s:w for s,w in ((archive,warning),(other,other_warning)) if w}
    assert review['native_warning']['evidence']
    carrier=read(export_dir/'carrier.json')
    assert not carrier['key_obstructions'] and carrier['source_sha256']==digest(export_dir/'Key_Carrier-assembly.stl')
    fit=read(export_dir/'click-fit.json')
    assert max(fit['overlap_mm3'].values())<.013 and 0<fit['button_contact_deg']<fit['case_stop_deg']
    output=export_dir/'print-mechanisms'
    output.mkdir(parents=True,exist_ok=True)
    for name in ('layout.3mf','layout.frame.json',ARCHIVE,'review.json',*REPORTS):
        copyfile(primary/name,output/name)
    for name in REPORTS:
        copyfile(reopened/name,output/('reopened-'+name))
    (output/'reopened.json').write_text(json.dumps(dict(layout_sha256=layout,checked_archive=archive,reopened_archive=other),indent=2)+'\n')
    with ZipFile(primary/ARCHIVE) as z:
        (output/'tray.png').write_bytes(z.read('Metadata/top_1.png'))
    return package(primary/ARCHIVE,output/print_name,set(LABELS),[output/n for n in (*REPORTS,'review.json','reopened.json')])

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('primary',type=Path)
    parser.add_argument('reopened',type=Path)
    args=parser.parse_args()
    release(args.primary,args.reopened)
