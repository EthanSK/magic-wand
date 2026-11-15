"""Retain a checked R42 trial and compose its hash-bound review record.

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
                note = ('Short leading end of a load-bearing root rib or root fan, farthest from its loaded root. '
                        'The same overhang row is present in R41; physical underside quality and root strength remain unverified.')
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
    archive = reopened/'R42-Complete-A1-mini-PETG-reopened.gcode.3mf'
    package = reopened/'R42-DFRobot-Diagonal-print-only.3mf'
    layout = initial/'R42-Complete-A1-mini-PETG-layout.3mf'
    assert a['passed'] and not a['failures'] and roundtrip['passed']
    assert digest(archive)==a['archive_sha256']==check['archive_sha256']==roundtrip['reslice_sha256']==measured['archive_sha256']
    assert digest(layout)==check['layout_sha256']==roundtrip['retained_layout_sha256']
    assert digest(reopened/'print-manifest.json')==a['manifest_sha256']
    assert digest(HERE/'audit42.py')==a['checker_sha256']
    assert digest(HERE/'holder42.py')==a['geometry_source_sha256']
    assert digest(HERE/'plate42.py')==check['driver_sha256']
    assert digest(HERE/'complete-assembly.json')==a['bom_sha256']
    source_manifest=read(HERE/'exports/manifest.json')
    assert digest(HERE.parent/'carbon-rod-holders-r41-dfrobot-diagonal/holder41.py')==source_manifest['upstream_sha256']['holder41.py']
    assert all(digest(HERE/name)==value for name,value in source_manifest['source_sha256'].items())
    assert set(read(reopened/'print-manifest.json')['parts'])==set(a['parts'])==set(check['build_list']) and len(a['parts'])==9
    assert not check['warnings'] and not check['archive_warnings']
    assert read(reopened/'print-only.json')['sha256']==digest(package)
    with ZipFile(archive) as source, ZipFile(package) as target:
        paths=[n for n in source.namelist() if n.endswith('.gcode')]
        assert paths and all(source.read(n)==target.read(n) for n in paths)
    selected = [archive,package,layout,*[reopened/name for name in (
        'reopened-audit.json','reopened-print-checks.json','reopen-checks.json','print-only.json',
        'print-manifest.json','print-anchors.json','overhang-measurements.json',
        'audit38-support-projection.png','audit42-Key_Carrier-overhangs.png',
        'audit42-DFRobot_Hole_Bracket-overhangs.png')],initial/'quick-critical.json']
    out=HERE/'exports/print-trial'
    out.mkdir(exist_ok=True)
    for path in selected:
        shutil.copy2(path,out/path.name)
    report={'revision':'R42','generated_by':'trial42.py','generator_sha256':digest(Path(__file__)),
            'status':'Historical combined-plate digital checks pass; physical retry is on hold after R41 toppling',
            'physical_ready_for_send':False,
            'physical_hold_reason':'R41 appears to have toppled its battery holder. Prepare separate keys, battery and XIAO jobs; do not resend this combined archive unchanged.',
            'physical_print_started_at_generation':False,'parts':check['build_list'],
            'artifact_sha256':{path.name:digest(path) for path in selected},
            'source_sha256':{p.name:digest(p) for p in (HERE/'holder42.py',HERE/'assembly42.py',HERE/'plate42.py',HERE/'audit42.py',HERE/'test_audit42.py',HERE/'complete-assembly.json')},
            'composite_manifest':'print-manifest.json','composite_manifest_sha256':a['manifest_sha256'],
            'estimate_seconds':check['estimate_seconds'],'filament_g':check['filament_g'],
            'support_free_rod_grip':a['r42_deposition_checks']['Key_Carrier']['support_free_rod_grip'],
            'support_free_hinge':a['r42_deposition_checks']['Key_Carrier']['support_free_hinge'],
            'support_cleanup_required':{part:{name:row for name,row in check['temporary_support_in_working_spaces'].items()
                if row['must_remove_before_assembly']} for part,check in a['r42_deposition_checks'].items()},
            'bracket_feet':a['removable_support']['bracket_feet'],
            'all_layer_pusher_connectivity':a['r42_deposition_checks']['DFRobot_Hole_Bracket']['pusher_load_path']['all_layer_connectivity'],
            'partial_overhang_decisions':decisions(a,measured),
            'small_features_below_overhang_reporting_filter':{
                'reporting_area_mm2':2.,
                'features':['Shortened board-hole pad fronts (R41 print Z21.8 rows)',
                            'Local pin-pocket ends and moved pinch-pad fronts'],
                'decision':'Source-reviewed short starts, about 1.2 mm or less. Below the reporting filter does not establish actual backing; inspect their undersides in the physical trial.',
                'actual_support_backing_measured':False},
            'bracket_tie_nominal_contact':{
                'r42_mm2_per_side':.102,'r41_mm2_per_side':.14,
                'physical_adhesion_or_joint_strength_verified':False},
            'physical_trial_checks':['Remove all support from the listed working spaces before fitting electronics.',
              'Confirm bought DFR0030 hole/pin placement and solder allowance against the printed bracket.',
              'Confirm Gravity pin tails are 2.0 mm or less below the PCB before clicking; longer tails are outside the checked envelope.',
              'Push the DFRobot board forward on its posts and confirm it rests on its rails, not the raised rear pinch pads. Do not force a board that will not seat.',
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
