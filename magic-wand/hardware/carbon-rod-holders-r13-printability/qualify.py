#!/usr/bin/env python3
"""Fail closed on stale or unreviewed overhangs; never assert physical readiness."""
import argparse,hashlib,json,zipfile,xml.etree.ElementTree as E
import deliverables
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE/'exports'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def row_id(name,scope,row):
    value=json.dumps([name,scope,row],sort_keys=True,separators=(',',':'))
    return hashlib.sha256(value.encode()).hexdigest()[:20]

def cases(report):
    result={}
    for name,part in report['parts'].items():
        for scope in ['layer_starts','whole_print_layer_starts']:
            for row in part[scope]['partial_overhangs']:
                result[row_id(name,scope,row)]={'part':name,'scope':scope,**row}
    return result

def qualify(exports=OUT):
    source=exports/'slice-clearances.json';report=json.loads(source.read_text());found=cases(report)
    project=exports/deliverables.project_name(exports);manifest=json.loads((exports/'manifest.json').read_text())
    assert report['project_sha256']==sha(project) and report['manifest_sha256']==sha(exports/'manifest.json')
    for key,file in [('checker_sha256','verify_slice.py'),('start_auditor_sha256','start_audit.py'),
                     ('side_gap_checker_sha256','side_gap.py'),('working_spaces_sha256','working_spaces.py')]:
        assert report[key]==sha(HERE/file),('Stale checker',file)
    for file,digest in manifest.get('source_sha256',{}).items():assert sha(HERE/file)==digest,('Stale model source',file)
    if exports!=OUT:assert manifest['source_manifest_sha256']==sha(OUT/'manifest.json')
    for name,part in manifest['parts'].items():assert part['stl_sha256']==sha(exports/deliverables.normal_name(name)),name
    printed=json.loads((exports/'print-checks.json').read_text())
    assert printed['generator_sha256']==sha(HERE/'print_project.py') and printed['sliced_project_sha256']==sha(project)
    for file,digest in printed['helper_sha256'].items():assert sha(exports/file)==digest,file
    strength=json.loads((exports/'strength-checks.json').read_text())
    assert strength['passed']and strength['project_sha256']==sha(project)and strength['checker_sha256']==sha(HERE/'strength_audit.py')
    assert strength['manifest_sha256']==sha(exports/'manifest.json')
    with zipfile.ZipFile(project)as z:
        config=json.loads(z.read('Metadata/project_settings.config'))
        objects=E.fromstring(z.read('Metadata/model_settings.config'))
    required={'enable_support':'0','brim_type':'no_brim','layer_height':'0.2','wall_loops':'3','sparse_infill_density':'20%'}
    registered=set(config.get('different_settings_to_system',[''])[0].split(';'))
    assert set(required)|{'bridge_no_support','max_bridge_length'}<=registered,'Delivered override registration missing'
    assert printed['delivered_settings_registration']['values_unchanged']
    for key,value in required.items():assert str(config.get(key))==value,('Global delivered value',key)
    for obj in objects.findall('object'):
        values={m.get('key'):m.get('value')for m in obj.findall('metadata')}
        for key,value in required.items():assert str(values.get(key,config.get(key)))==value,(key,values.get('name'))
    decisions=json.loads((HERE/'overhang-decisions.json').read_text())
    chosen=decisions['projects'].get(exports.relative_to(HERE).as_posix(),{})
    unknown=sorted(set(found)-set(chosen));obsolete=sorted(set(chosen)-set(found))
    for key,row in chosen.items():
        assert row['decision']=='bounded-physical-trial' and row['reason'] and row['required_test'],key
    warnings=printed.get('warnings',[])
    reopen=exports/'reopen-checks.json'
    if reopen.exists():
        reopened=json.loads(reopen.read_text())
        assert reopened['input_project_sha256']==sha(project),'Stale reopened project'
        warnings=list(dict.fromkeys(warnings+reopened.get('warnings',[])))
    warning_decisions=decisions['slicer_warnings']
    pending_warnings=[w for w in warnings if w not in warning_decisions]
    result={'slice_sha256':sha(source),'decisions_sha256':sha(HERE/'overhang-decisions.json'),
            'qualifier_sha256':sha(Path(__file__)),'project_sha256':report['project_sha256'],
            'partial_overhang_threshold_mm2':2.,'cases':{k:{**v,**chosen.get(k,{})}for k,v in found.items()},
            'unreviewed_cases':unknown,'obsolete_decisions':obsolete,'unreviewed_warnings':pending_warnings,
            'warning_decisions':{w:warning_decisions[w]for w in warnings if w in warning_decisions},
            'test_recipe_audited':bool(report['passed']and not unknown and not obsolete and not pending_warnings),
            'full_set_ready':False,'physical_print_verified':False,
            'qualification':'Bounded experiment only. Stop if helpers fuse, a bridge droops into a fit, a guide binds or any part cracks/whitens. Full-set readiness requires successful physical trials.'}
    (exports/'overhang-review.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['test_recipe_audited'],('Unqualified trial',unknown,obsolete,pending_warnings,report['passed'])
    print('All broad overhangs and slicer warnings have explicit bounded-trial decisions; physical readiness remains false.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,default=OUT);a=p.parse_args();qualify(a.exports.resolve())
