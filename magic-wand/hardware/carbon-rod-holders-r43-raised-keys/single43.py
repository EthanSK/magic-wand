"""Slice and audit R43's main carrier alone, twice; never send or start.

The complete nine-part assembly remains intact. Native supports, removable
pads and the Smooth timelapse tower are retained in the one-part trial.
"""
import argparse
import json
from pathlib import Path
import shutil
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile,ZIP_DEFLATED
import numpy as np
import holder43 as d
import plate43 as p
import split42 as split
import single42 as previous
import carrier_checks43
import roundtrip23 as rt

HERE=d.HERE
KEY=d.CARRIER
save=split.save


def layout(output):
    source=split.make('keys',output,only=(KEY,))
    with ZipFile(source) as archive:files={n:archive.read(n) for n in archive.namelist()}
    settings=ET.fromstring(files[p.plate.MODEL_SETTINGS])
    p.set_fields(settings.find('plate'),{'plater_name':'Magic Wand R43 key holder alone · A1 mini PETG'})
    files[p.plate.MODEL_SETTINGS]=ET.tostring(settings,encoding='utf-8',xml_declaration=True)
    target=output/'R43-Key-Holder-Only-layout.3mf'
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for n,data in files.items():archive.writestr(n,data)
    source.unlink()
    checks=p.plate.read_json(output/'print-checks.json')
    checks.update(layout_sha256=p.plate.digest(target),driver_sha256=p.plate.digest(Path(__file__)))
    save(output/'print-checks.json',checks)
    job=p.plate.read_json(output/'job.json')
    job.update(revision='r43',model_geometry_changed=True,raised_outer_keys_mm=d.KEY_RAISE_MM)
    save(output/'job.json',job)
    return target


def sliced(source,output,suffix=''):
    archive=split.slice_archive('keys',source,output,suffix,command_checker=previous.commands)
    target=output/f'R43-Key-Holder-Only{suffix}.gcode.3mf'
    archive.rename(target)
    return target


def audit(archive,output):
    checker=carrier_checks43.common.load_checker().audit
    owners=previous.owners(archive)
    assert set(owners)=={KEY}
    with previous.single_marker_reader(archive):
        data,features,stats,config,offset,objects,_,model=checker.read_project(archive)
        assert set(objects)=={KEY}
        result=carrier_checks43.audit(archive,output,owners[KEY])
    labels=np.asarray(features)[data[:,5].astype(int)]
    tower=labels=='Prime tower';selected=data[:,6]==owners[KEY]
    assert tower.sum()>500 and config['timelapse_type']=='1' and config['enable_prime_tower']=='1'
    assert not (~tower & ~selected).any()
    positions=data[:,:3]+offset
    def bounds(mask):
        r=data[mask,3,None]/2
        return (positions[mask,:2]-r).min(0),(positions[mask,:2]+r).max(0)
    low,high=bounds(selected);tl,th=bounds(tower)
    gap=float(np.linalg.norm(np.maximum(np.maximum(low-th,tl-high),0.)))
    assert (np.minimum(low,tl)>=0).all() and (np.maximum(high,th)<=180).all() and gap>.2
    result.update(archive_sha256=p.plate.digest(archive),driver_sha256=p.plate.digest(Path(__file__)),
        part_and_support_bounds_mm=[low.tolist(),high.tolist()],wipe_tower_bounds_mm=[tl.tolist(),th.tolist()],
        tower_clearance_mm=gap,actual_deposition_inside_bed=True,statistics=stats,
        startup=previous.commands(archive,config),physical_success_verified=False)
    return result


def preflight(archive,output):
    """Fail early on the last slice's specific defects; full audit still follows."""
    c=carrier_checks43.common
    exports=output/'build-source/exports'
    with previous.single_marker_reader(archive):
        checker,data,labels,_,offset,objects,records=c.object_data(archive,exports)
        features=checker.read_project(archive)[1]
    mesh=c.trimesh.load_mesh(exports/f'{KEY}{c.SOURCE_SUFFIX}')
    solid=checker.q.solid(mesh.vertices,mesh.faces)
    xyz=c.local_points(data,offset,objects[KEY],mesh)
    frame=np.asarray(records[KEY]['print_to_assembly']);owner=previous.owners(archive)[KEY]
    keep=c.model_mask(labels)&(data[:,6]==owner)
    gaps,material=carrier_checks43.routes()
    probes=tuple(n for n in gaps[KEY] if n.startswith('key_'))
    routes={n:c.route_hits(checker.q,gaps[KEY][n],xyz,data[:,3],data[:,4],data[:,5].astype(int),features,frame,keep) for n in probes}
    measure=c.load_checker().material_coverage
    joins={n:measure(checker.q,checker.start_audit,s.transform(np.linalg.inv(frame)[:3])^solid,
        xyz[keep],data[keep,3],data[keep,4],data[keep,7]) for n,s in material[KEY].items() if 'web' in n}
    result={'passed':not any(v['violations'] for v in routes.values()) and
        all(v['minimum_layer_fraction']>=.9 for v in joins.values()),
        'routes':routes,'joins':joins,'scope':'Early diagnostic only; does not replace the complete actual-path audit.'}
    save(output/'preflight.json',result)
    print(json.dumps({'preflight':result}),flush=True)
    assert result['passed'],'R43 targeted preflight failed'


def run(output,retained):
    with patch.object(split,'p',p),patch.object(split,'HERE',HERE),patch.object(split,'BASE_STAGE',p.stage_parts):
        source=layout(output)
        first=sliced(source,output)
        preflight(first,output)
        initial=audit(first,output);save(output/'initial-audit.json',initial)
        assert initial['passed'],initial['failures']
        second=sliced(first,output,'-reopened')
        final_audit=audit(second,output);save(output/'slice-audit.json',final_audit)
        assert final_audit['passed'],final_audit['failures']
        before,bm,_=rt.roundtrip22.common.archive_settings(first)
        after,am,_=rt.roundtrip22.common.archive_settings(second)
        assert before==after and rt.object_recipe(bm)==rt.object_recipe(am)
        save(output/'reopen-checks.json',{'passed':True,'input_sha256':p.plate.digest(first),
            'selected_archive_sha256':p.plate.digest(second),'settings_and_object_recipe_identical':True,
            'selected_archive_own_deposition_verified':True,'parts':[KEY]})
        package=p.previous.recipe.make_print_only(second,output)
        final=output/'R43-Key-Holder-Only-print-only.3mf';package.rename(final)
        receipt=p.plate.read_json(output/'print-only.json')
        receipt.update(file=final.name,sha256=p.plate.digest(final));save(output/'print-only.json',receipt)
        retained.mkdir(parents=True,exist_ok=False)
        selected=[source,first,second,final,*[output/n for n in ('job.json','initial-audit.json',
            'slice-audit.json','print-checks.json','reopen-checks.json','print-only.json','preflight.json')]]
        for path in selected:shutil.copy2(path,retained/path.name)
        for name in ('manifest.json','anchors.json'):
            shutil.copy2(output/'build-source/exports'/name,retained/('print-'+name))
        checks=p.plate.read_json(output/'print-checks.json')
        save(retained/'trial-review.json',{'passed':True,'parts':[KEY],
            'source_sha256':{n:p.plate.digest(HERE/n) for n in ('single43.py','carrier_checks43.py','plate43.py','holder43.py','assembly43.py')},
            'upstream_sha256':{n:p.plate.digest(d.R42/n) for n in ('single42.py','carrier_checks42.py','split42.py','plate42.py','audit42.py')},
            'artifact_sha256':{path.name:p.plate.digest(retained/path.name) for path in selected},
            'selected_file':final.name,'selected_sha256':p.plate.digest(final),
            'estimate_seconds':checks['estimate_seconds'],'filament_g':checks['filament_g'],
            'support_and_adhesion_helpers_included':True,'smooth_timelapse_wipe_tower_included':True,
            'physical_ready_for_send':False,
            'physical_hold_reason':'Ethan will confirm he is home and the failed plate and nozzle are clear and reseated. Do not start before that confirmation.',
            'physical_success_verified':False})
        print(json.dumps({'passed':True,'parts':[KEY],'seconds':checks['estimate_seconds'],'grams':checks['filament_g']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path);parser.add_argument('retained',type=Path)
    args=parser.parse_args()
    run(args.output.resolve(),args.retained.resolve())
