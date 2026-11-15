"""Prepare the main key holder alone, retaining required helpers and timelapse.

Ethan's one-component test removes the touch bracket and both post clips too.
The complete assembly/BOM and previously checked group jobs remain intact.
Verify the exact mesh, transform and settings against the group project,
then check this single job's own deposited paths with carrier_checks42.
Run through geometry_budget.py in disposable scratch. This never sends a job.
"""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np

import split42 as split
import roundtrip23 as rt
import carrier_checks42

HERE=Path(__file__).resolve().parent
KEY='Key_Carrier'
REFERENCE=HERE/'exports/print-jobs/keys'


def single_marker_text(text: str, identifier: int) -> str:
    """Adapt Studio's single-object comments for the existing strict readers.

    Studio omits its multi-object start/stop comments for one built object.
    OBJECT_ID is still emitted. Translate that comment in memory only and
    reset ownership before each wipe tower. Never change a printer command
    or the selected archive; all physical checks still use its exact paths.
    """
    assert '; start printing object,' not in text
    rows=[]; seen=0
    for line in text.splitlines():
        if line.startswith('; OBJECT_ID:'):
            assert int(line.split(':',1)[1])==identifier
            rows.append(f'; start printing object, unique label id: {identifier}')
            seen+=1
        elif line.startswith('; FEATURE: Prime tower') or line.startswith('; layer num/'):
            rows.append(f'; stop printing object, unique label id: {identifier}')
        rows.append(line)
    assert seen>0
    result='\n'.join(rows)+'\n'
    executable=lambda t:[line.split(';',1)[0].strip() for line in t.splitlines() if line.split(';',1)[0].strip()]
    assert executable(result)==executable(text),'An audit comment adapter changed a command'
    return result


@contextmanager
def single_marker_reader(archive: Path):
    ownership=owners(archive)
    assert set(ownership)=={KEY}
    read=ZipFile.read
    def adapted(source,name,*args,**kwargs):
        data=read(source,name,*args,**kwargs)
        if Path(source.filename).resolve()==archive.resolve() and name=='Metadata/plate_1.gcode':
            return single_marker_text(data.decode(),ownership[KEY]).encode()
        return data
    with patch.object(ZipFile,'read',adapted):
        yield


def commands(archive: Path, config: dict) -> dict:
    with single_marker_reader(archive):
        result=split.p.command_audit(archive,config)
    result['single_object_comment_adapter_only']=True
    return result


def owners(archive: Path) -> dict[str,int]:
    with ZipFile(archive) as source:
        root=ET.fromstring(source.read('Metadata/slice_info.config'))
    result={obj.get('name'):int(obj.get('identify_id')) for obj in root.findall('./plate/object')}
    assert len(result)==len(set(result.values())), 'Duplicate actual support/object owner'
    return result


def footprints(data: np.ndarray, labels: np.ndarray, owner: int) -> dict[str,np.ndarray]:
    """Exact footprint membership, independent of path order/repeated endpoints.

    These are the same float32 XYZ, width, height and layer-top samples used
    by the established opening, material, prior-layer and removal checkers.
    No rounding, inset, tolerance relaxation or nearest-point substitution.
    """
    selected=data[:,6]==owner
    assert selected.any()
    result={}
    for label in sorted(set(labels[selected])):
        keep=selected & (labels==label)
        rows=data[keep][:,[0,1,2,3,4,7]]
        assert np.isfinite(rows).all()
        result[label]=np.unique(rows,axis=0)
    return result


def audit(archive: Path, output: Path) -> dict:
    baseline=REFERENCE/'R42-keys-reopened.gcode.3mf'
    prior=split.p.plate.read_json(REFERENCE/'slice-audit.json')
    assert prior['passed'] and not prior['failures']
    assert prior['archive_sha256']==split.p.plate.digest(baseline)
    assert prior['checker_sha256']==split.p.plate.digest(HERE/'audit42.py')
    assert prior['geometry_source_sha256']==split.p.plate.digest(HERE/'holder42.py')
    checker=split.audit.common.load_checker().audit
    before=checker.read_project(baseline)
    with single_marker_reader(archive):
        after=checker.read_project(archive)
    bd,bf,_,bc,bo,bobjects,_,bm=before
    data,features,stats,config,offset,objects,_,model=after
    assert set(objects)=={KEY}, 'The diagnostic must contain one functional component'
    assert config==bc, 'Effective global settings differ from the audited carrier reference'
    assert np.array_equal(offset,bo)
    assert rt.object_recipe(model)[KEY]==rt.object_recipe(bm)[KEY]
    assert np.array_equal(objects[KEY]['faces'],bobjects[KEY]['faces'])
    assert np.array_equal(objects[KEY]['vertices'],bobjects[KEY]['vertices'])
    old_owners,new_owners=owners(baseline),owners(archive)
    assert set(new_owners)=={KEY}
    labels=np.asarray(features)[data[:,5].astype(int)]
    before_labels=np.asarray(bf)[bd[:,5].astype(int)]
    selected=data[:,6]==new_owners[KEY]
    tower=labels=='Prime tower'
    assert tower.sum()>500 and config['timelapse_type']=='1' and config['enable_prime_tower']=='1'
    assert not (~tower & ~selected).any(), 'Unaudited extrusion outside the sole part or wipe tower'
    old=footprints(bd,before_labels,old_owners[KEY])
    current=footprints(data,labels,new_owners[KEY])
    differences={}
    for name in sorted(set(old)|set(current)):
        a,b=old.get(name),current.get(name)
        equal=a is not None and b is not None and np.array_equal(a,b)
        differences[name]={'reference_unique_samples':0 if a is None else len(a),
                           'current_unique_samples':0 if b is None else len(b),
                           'exactly_equal':equal}
    positions=data[:,:3]+offset
    def bounds(keep):
        radius=data[keep,3,None]/2
        return (positions[keep,:2]-radius).min(0),(positions[keep,:2]+radius).max(0)
    part_low,part_high=bounds(selected)
    tower_low,tower_high=bounds(tower)
    on_bed=bool((np.minimum(part_low,tower_low)>=0).all() and (np.maximum(part_high,tower_high)<=180).all())
    gap=float(np.linalg.norm(np.maximum(np.maximum(part_low-tower_high,tower_low-part_high),0.)))
    assert on_bed and gap>.2, 'Actual model/support/tower deposition leaves the bed or meets its neighbour'
    with single_marker_reader(archive):
        result=carrier_checks42.audit(archive,output,new_owners[KEY])
    result.update({'archive_sha256':split.p.plate.digest(archive),
        'reference_archive_sha256':prior['archive_sha256'],
        'reference_audit_sha256':split.p.plate.digest(REFERENCE/'slice-audit.json'),
        'driver_sha256':split.p.plate.digest(Path(__file__)),
        'comparison_basis':'Exact unique XYZ, width, height and layer-top footprint samples per actual extrusion feature, including all native support and CAD helpers; no rounding or relaxed thresholds.',
        'feature_equivalence':differences,'mesh_and_placement_identical':True,
        'effective_global_and_object_settings_identical':True,
        'part_and_support_bounds_mm':[part_low.tolist(),part_high.tolist()],
        'wipe_tower_bounds_mm':[tower_low.tolist(),tower_high.tolist()],
        'tower_clearance_mm':gap,'actual_deposition_inside_bed':on_bed,
        'startup':commands(archive,config),
        'physical_success_verified':False,'statistics':stats,
        'path_comparison_scope':'Diagnostic only. Changed samples require the fresh carrier_checks42 audit above; the prior report is not reused as a one-part path pass.'})
    return result


def run(output: Path, retained: Path) -> None:
    layout=split.make('keys',output,only=(KEY,))
    first=split.slice_archive('keys',layout,output,command_checker=commands)
    initial=audit(first,output)
    split.save(output/'initial-audit.json',initial)
    if not initial['passed']:
        raise RuntimeError(initial['failures'])
    reopened=split.slice_archive('keys',first,output,'-reopened',command_checker=commands)
    checked=audit(reopened,output)
    split.save(output/'slice-audit.json',checked)
    assert checked['passed'],checked['failures']
    first_settings,first_model,_=rt.roundtrip22.common.archive_settings(first)
    settings,model,_=rt.roundtrip22.common.archive_settings(reopened)
    assert first_settings==settings and rt.object_recipe(first_model)==rt.object_recipe(model)
    split.save(output/'reopen-checks.json',{'passed':True,'input_sha256':split.p.plate.digest(first),
        'selected_archive_sha256':split.p.plate.digest(reopened),'settings_and_object_recipe_identical':True,
        'selected_archive_own_deposition_verified':True,'parts':[KEY]})
    package=split.p.previous.recipe.make_print_only(reopened,output)
    final=output/'R42-Key-Holder-Only-print-only.3mf'
    package.rename(final)
    receipt=split.p.plate.read_json(output/'print-only.json')
    receipt.update(file=final.name,sha256=split.p.plate.digest(final));split.save(output/'print-only.json',receipt)
    retained.mkdir(parents=True,exist_ok=False)
    selected=[layout,first,reopened,final,*[output/name for name in ('job.json','initial-audit.json',
        'slice-audit.json','print-checks.json','reopen-checks.json','print-only.json')]]
    for path in selected:shutil.copy2(path,retained/path.name)
    for name in ('manifest.json','anchors.json'):
        shutil.copy2(output/'build-source/exports'/name,retained/('print-'+name))
    checks=split.p.plate.read_json(output/'print-checks.json')
    split.save(retained/'trial-review.json',{'passed':True,'parts':[KEY],
        'source_sha256':{name:split.p.plate.digest(HERE/name) for name in ('single42.py','carrier_checks42.py','split42.py','plate42.py','holder42.py','audit42.py')},
        'artifact_sha256':{path.name:split.p.plate.digest(retained/path.name) for path in selected},
        'reference_audit_sha256':checked['reference_audit_sha256'],
        'selected_file':final.name,'selected_sha256':split.p.plate.digest(final),
        'estimate_seconds':checks['estimate_seconds'],'filament_g':checks['filament_g'],
        'support_and_adhesion_helpers_included':True,'smooth_timelapse_wipe_tower_included':True,
        'physical_ready_for_send':False,'physical_hold_reason':'Ethan will confirm he is home and has cleared/reseated the plate and nozzle. Do not start before that confirmation.',
        'physical_success_verified':False})
    print(json.dumps({'passed':True,'parts':[KEY],'seconds':checks['estimate_seconds'],
                      'grams':checks['filament_g']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('retained',type=Path)
    args=parser.parse_args()
    run(args.output.resolve(),args.retained.resolve())
