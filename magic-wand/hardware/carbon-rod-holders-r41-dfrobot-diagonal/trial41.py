"""Retain a checked R41 trial and compose its hash-bound review record.

Inputs are the initial and reopened evidence directories from the finite
Studio run. This does not slice, alter a toolpath or contact a printer.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def decisions(audit, measured):
    result = {}
    for part, rows in measured['parts'].items():
        assert len(rows) == len(audit['parts'][part]['partial_overhangs'])
        result[part] = []
        for row in rows:
            top = row['layer_top_mm']
            reach = row['maximum_distance_to_actual_lower_model_or_support_mm']
            if part == 'Key_Carrier':
                assert reach <= 1., (part, top, reach, 'Needs a new overhang decision')
                note = 'Small remaining reach from actual prior plastic or native support; broad Choc lips retain support.'
            elif abs(top-.6)<.001:
                assert audit['removable_support']['bracket_feet']['passed'] and row['support_samples']>0 and reach<=.35
                note = 'Early backup foot has actual interface at a 0.2 mm gap; separate coverage, removal and spacing checks pass.'
            elif any(abs(top-z)<.001 for z in (19.8,21.8,25.8)):
                assert reach<=1.65
                note = 'Short nonfunctional down-facing ledge; retained from the independent review, with physical underside quality unverified.'
            else:
                assert abs(top-28.2)<.001 and reach<=2.1, (part,top,reach)
                note = 'Existing 3.4 mm bridge anchored at both ends; physical sag remains a trial check.'
            result[part].append({**row,'decision_required':False,'accepted_for_trial':True,'decision':note})
    assert all(not row['partial_overhangs'] for part,row in audit['parts'].items() if part not in result)
    return result


def retain(initial, reopened):
    a = read(reopened/'reopened-audit.json')
    check = read(reopened/'reopened-print-checks.json')
    roundtrip = read(reopened/'reopen-checks.json')
    measured = read(reopened/'overhang-measurements.json')
    archive = reopened/'R41-Complete-A1-mini-PETG-reopened.gcode.3mf'
    package = reopened/'R41-DFRobot-Diagonal-print-only.3mf'
    layout = initial/'R41-Complete-A1-mini-PETG-layout.3mf'
    assert a['passed'] and not a['failures'] and roundtrip['passed']
    assert digest(archive)==a['archive_sha256']==check['archive_sha256']==roundtrip['reslice_sha256']==measured['archive_sha256']
    assert digest(layout)==check['layout_sha256']==roundtrip['retained_layout_sha256']
    assert digest(reopened/'print-manifest.json')==a['manifest_sha256']
    assert digest(HERE/'audit41.py')==a['checker_sha256']
    assert digest(HERE/'holder41.py')==a['geometry_source_sha256']
    assert digest(HERE/'plate41.py')==check['driver_sha256']
    assert digest(HERE/'complete-assembly.json')==a['bom_sha256']
    assert set(read(reopened/'print-manifest.json')['parts'])==set(a['parts'])==set(check['build_list']) and len(a['parts'])==9
    assert not check['warnings'] and not check['archive_warnings']
    assert read(reopened/'print-only.json')['sha256']==digest(package)
    with ZipFile(archive) as source, ZipFile(package) as target:
        paths=[n for n in source.namelist() if n.endswith('.gcode')]
        assert paths and all(source.read(n)==target.read(n) for n in paths)
    selected = [archive,package,layout,*[reopened/name for name in (
        'reopened-audit.json','reopened-print-checks.json','reopen-checks.json','print-only.json',
        'print-manifest.json','print-anchors.json','overhang-measurements.json',
        'audit38-support-projection.png','audit41-Key_Carrier-overhangs.png',
        'audit41-DFRobot_Hole_Bracket-overhangs.png')],initial/'quick-critical.json']
    out=HERE/'exports/print-trial'
    out.mkdir(exist_ok=True)
    for path in selected:
        shutil.copy2(path,out/path.name)
    report={'revision':'R41','generated_by':'trial41.py','generator_sha256':digest(Path(__file__)),
            'status':'Digital checks pass; physical fit, cleanup and strength remain unverified',
            'physical_print_started_at_generation':False,'parts':check['build_list'],
            'artifact_sha256':{path.name:digest(path) for path in selected},
            'source_sha256':{p.name:digest(p) for p in (HERE/'holder41.py',HERE/'assembly41.py',HERE/'plate41.py',HERE/'audit41.py',HERE/'test_audit41.py',HERE/'complete-assembly.json')},
            'composite_manifest':'print-manifest.json','composite_manifest_sha256':a['manifest_sha256'],
            'estimate_seconds':check['estimate_seconds'],'filament_g':check['filament_g'],
            'support_free_rod_grip':a['r41_deposition_checks']['Key_Carrier']['support_free_rod_grip'],
            'support_free_hinge':a['r41_deposition_checks']['Key_Carrier']['support_free_hinge'],
            'support_cleanup_required':{part:{name:row for name,row in check['temporary_support_in_working_spaces'].items()
                if row['must_remove_before_assembly']} for part,check in a['r41_deposition_checks'].items()},
            'bracket_feet':a['removable_support']['bracket_feet'],
            'all_layer_pusher_connectivity':a['r41_deposition_checks']['DFRobot_Hole_Bracket']['pusher_load_path']['all_layer_connectivity'],
            'partial_overhang_decisions':decisions(a,measured),
            'physical_trial_checks':['Remove all support from the listed working spaces before fitting electronics.',
              'Confirm bought DFR0030 hole/pin placement and solder allowance against the printed bracket.',
              'Set the stop screw so the real switch clicks before either stop; never force the plunger.',
              'Check flex-arm roots, post clips, rod grip and finger comfort by hand.'],
            'physical_success_guaranteed':False}
    (out/'trial-review.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('initial',type=Path)
    parser.add_argument('reopened',type=Path)
    args=parser.parse_args()
    report=retain(args.initial.resolve(),args.reopened.resolve())
    print(json.dumps({k:report[k] for k in ('revision','status','parts','estimate_seconds','filament_g')}))
