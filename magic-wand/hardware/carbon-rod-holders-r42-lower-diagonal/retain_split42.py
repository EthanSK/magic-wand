"""Retain the three passed R42 jobs and bind their reports to exact artifacts."""
import argparse
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

from trial42 import digest, read

HERE=Path(__file__).resolve().parent
EXPECTED={
    'keys':{'Key_Carrier','DFRobot_Hole_Bracket','DFR0030_Post_Clip','DFR0030_Post_Clip_2'},
    'battery':{'Battery_Holder','Battery_End_Door'},
    'xiao':{'XIAO_Rod_Holder','XIAO_Near_Keeper','Cable_Clip_12_Wire'},
}


def retain(source):
    destination=HERE/'exports/print-jobs'
    current_driver=digest(HERE/'split42.py')
    bom=read(HERE/'complete-assembly.json')
    complete={part for group in bom['groups'].values() for part in group['parts']}
    assert set().union(*EXPECTED.values())==complete
    assert sum(map(len,EXPECTED.values()))==len(complete)==9
    jobs={}
    for job,expected in EXPECTED.items():
        folder=source/job
        review=read(folder/'job-review.json')
        checks=read(folder/'print-checks.json')
        audit=read(folder/'slice-audit.json')
        reopened=read(folder/'reopen-checks.json')
        assert review['digital_checks_passed'] and audit['passed'] and not audit['failures'] and reopened['passed']
        assert set(review['parts'])==set(checks['build_list'])==set(audit['parts'])==expected
        assert checks['complete_bom_sha256']==digest(HERE/'complete-assembly.json')
        archive=folder/f'R42-{job}-reopened.gcode.3mf'
        package=folder/f'R42-{job}-print-only.3mf'
        assert digest(archive)==audit['archive_sha256']==checks['archive_sha256']==reopened['selected_archive_sha256']
        assert digest(folder/'print-manifest.json')==audit['manifest_sha256']
        assert read(folder/'print-only.json')['sha256']==digest(package)
        assert all(digest(folder/name)==value for name,value in review['artifact_sha256'].items())
        if review['driver_sha256']!=current_driver:
            validation=read(folder/'source-revalidation.json')
            assert validation['passed'] and validation['current_driver_sha256']==current_driver
            assert validation['selected_archive_sha256']==digest(archive)
        for part,record in checks['source_parts'].items():
            mesh=HERE/record['directory']/record['exports']/record['source_filename']
            assert digest(mesh)==record['source_sha256'],part
        with ZipFile(archive) as editable,ZipFile(package) as printable:
            paths=[name for name in editable.namelist() if name.endswith('.gcode')]
            assert paths and all(editable.read(name)==printable.read(name) for name in paths)
        out=destination/job
        out.mkdir(parents=True,exist_ok=True)
        artifacts=[*folder.glob('*.3mf'),*folder.glob('*.json'),*folder.glob('audit*.png')]
        for artifact in artifacts: shutil.copy2(artifact,out/artifact.name)
        jobs[job]={'parts':checks['build_list'],'estimate_seconds':checks['estimate_seconds'],
            'filament_g':checks['filament_g'],'selected_file':f'{job}/{package.name}',
            'selected_sha256':digest(package),'archive_sha256':digest(archive),
            'artifact_sha256':{artifact.name:digest(artifact) for artifact in artifacts},
            'physical_ready_for_send':False,
            'physical_hold_reason':'Inspect and clear the failed R41 plate, reseat it and confirm nozzle/motion clearance before a new start.'}
    battery=read(source/'battery/print-anchors.json')['parts']['Battery_Holder']
    result={'revision':'R42','generator_sha256':digest(Path(__file__)),
        'source_sha256':{name:digest(HERE/name) for name in ('holder42.py','assembly42.py','plate42.py','split42.py','audit42.py','complete-assembly.json')},
        'selection_complete_and_disjoint':True,'all_nine_retention_and_main_parts_included':True,
        'digital_checks_passed':True,'independent_review':'See REVIEW.md for the checked review disposition.',
        'combined_print_on_hold':True,'jobs':jobs,
        'battery_changes':{'model_geometry_changed':False,'native_holder_brim':False,
            'reason_native_brim_rejected':'Actual 8 mm outer-brim paths entered the open rod bore and clip mouth.',
            'pad_extension_mm':battery['outward_extension_mm'],'previous_pad_extension_mm':6.,
            'tie_count':battery['tie_count'],'tie_width_mm':battery['tie_width_mm'],
            'previous_tie_width_mm':1.,'tie_thickness_mm':battery['pad_thickness_mm'],
            'tie_contact_mm2':battery['tie_contact_mm2'],'previous_tie_contact_mm2':battery['previous_tie_contact_mm2'],
            'r41_first_layer_contact_mm2':1017.289,
            'retry_first_layer_contact_mm2':read(source/'battery/slice-audit.json')['parts']['Battery_Holder']['first_layer_mm2']},
        'physical_fit_cleanup_strength_and_success_verified':False,
        'failure_cause':'Image/layout comparison suggests Battery_Holder toppled in R41. Peeling, tie fracture and collision remain unconfirmed; no causal link to diagonal OP1 yaw established.'}
    destination.mkdir(exist_ok=True)
    (destination/'jobs-review.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    args=parser.parse_args()
    result=retain(args.source.resolve())
    print(json.dumps({'passed':result['digital_checks_passed'],'jobs':{name:{key:job[key] for key in ('parts','estimate_seconds','filament_g')} for name,job in result['jobs'].items()}}))
