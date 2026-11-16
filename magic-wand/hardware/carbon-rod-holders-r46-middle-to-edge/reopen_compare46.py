"""Complete the reopen comparison using authoritative 3MF component placement."""
import copy
import json
import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import numpy as np

from holder46 import inherited
from plate45 import digest

def process_only(recipes):
    result=copy.deepcopy(recipes)
    for object in result.values():
        for part in object['parts']:
            part['metadata'].pop('matrix',None)
    return result

def transform(text):
    result=np.eye(4)
    if text:
        values=np.fromstring(text,sep=' ').reshape(4,3)
        result[:3,:3]=values[:3].T
        result[:3,3]=values[3]
    return result

def modifier_geometry(archive):
    result={}
    with ZipFile(archive) as z:
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        resources={o.get('id'):o for o in model.findall('./{*}resources/{*}object')}
        config=ET.fromstring(z.read('Metadata/model_settings.config'))
        by_id={o.get('id'):o for o in config.findall('object')}
        documents={}
        for item in model.findall('./{*}build/{*}item'):
            settings=by_id[item.get('objectid')]
            owner=settings.find("metadata[@key='name']").get('value')
            base=transform(item.get('transform'))
            parts={p.get('id'):p for p in settings.findall('part')}
            for component in resources[item.get('objectid')].findall('./{*}components/{*}component'):
                id=component.get('objectid')
                if id not in parts:continue
                part=parts[id]
                if part.get('subtype')=='normal_part':continue
                assert 'modifier' in part.get('subtype','').lower(),part.attrib
                file=next(v for k,v in component.attrib.items() if k.endswith('}path')).lstrip('/')
                if file not in documents:documents[file]=ET.fromstring(z.read(file))
                obj=documents[file].find(f"./{{*}}resources/{{*}}object[@id='{id}']")
                assert obj is not None
                vertices=np.array([[float(v.get(k)) for k in ('x','y','z')] for v in obj.findall('./{*}mesh/{*}vertices/{*}vertex')])
                faces=np.array([[int(t.get(k)) for k in ('v1','v2','v3')] for t in obj.findall('./{*}mesh/{*}triangles/{*}triangle')])
                world=base@transform(component.get('transform'))
                vertices=vertices@world[:3,:3].T+world[:3,3]
                result[(owner,id)]=(vertices,faces)
    return result

def check(out):
    first=out/'R46-first-slice.gcode.3mf'
    final=out/'R46-Key-Carrier.gcode.3mf'
    initial=json.loads((out/'initial-delivery-checks.json').read_text())
    after=json.loads((out/'delivery-checks.json').read_text())
    assert initial['archive_sha256']==digest(first) and after['archive_sha256']==digest(final)
    recipes_before=initial['effective_object_recipes']
    recipes_after=after['effective_object_recipes']

    assert process_only(recipes_before)==process_only(recipes_after),'Actual object process settings changed'
    matrix_changes=[]
    for owner,record in recipes_before.items():
        for a,b in zip(record['parts'],recipes_after[owner]['parts']):
            if a['metadata'].get('matrix')!=b['metadata'].get('matrix'):
                matrix_changes.append({'owner':owner,'part_id':a['id'],'part_name':a['metadata'].get('name')})

    old=modifier_geometry(first)
    new=modifier_geometry(final)
    assert old.keys()==new.keys() and old
    comparisons=[]
    for key,(a,af) in old.items():
        b,bf=new[key]
        assert a.shape==b.shape and len(af)==len(bf),key
        assert len(a)<1000,'Unexpected complex modifier; inspect before pairwise comparison'
        distances=np.linalg.norm(b[:,None,:]-a[None,:,:],axis=2)
        nearest=distances.argmin(axis=1)
        error=float(distances[np.arange(len(b)),nearest].max())
        assert len(set(nearest))==len(a) and error<=.00001,(key,error)
        assert {tuple(sorted(face)) for face in af}=={tuple(sorted(nearest[face])) for face in bf},key
        comparisons.append({'owner':key[0],'part_id':key[1],'vertices':len(a),'maximum_world_vertex_delta_mm':error,'topology_identical':True})

    with ZipFile(first) as a,ZipFile(final) as b:
        assert json.loads(a.read('Metadata/project_settings.config'))==json.loads(b.read('Metadata/project_settings.config'))
        ag=a.read('Metadata/plate_1.gcode');bg=b.read('Metadata/plate_1.gcode')
        identical=ag==bg
    checker=inherited.common.load_checker().audit
    deposition_identical=True
    if not identical:
        a=checker.read_project(first);b=checker.read_project(final)
        deposition_identical=bool(np.array_equal(a[0],b[0]) and np.array_equal(a[1],b[1]) and np.array_equal(a[4],b[4]))

    record=json.loads((out/'candidate-audit.json').read_text())
    assert record['archive_sha256']==digest(final) and record['screen_passed']
    assert record['shared_left_guard_buttress']['qualified']
    for name in ('helper-starts.json','roof-strokes.json','roof-residual-context.json','contact-areas.json','shelf-contact-areas.json','rear-shelf-contact-areas.json'):
        assert json.loads((out/name).read_text())['archive_sha256']==digest(final),name
    helpers=json.loads((out/'helper-starts.json').read_text())
    assert all(not row['unrooted_actual_components'] for row in helpers['owners'].values())
    report={'initial_archive_sha256':digest(first),'selected_archive_sha256':digest(final),
        'global_settings_identical':True,'object_process_settings_identical':True,
        'part_matrix_metadata_changes':matrix_changes,'actual_modifier_geometry_comparisons':comparisons,
        'actual_modifier_placements_equivalent':True,'modifier_vertex_tolerance_mm':.00001,
        'normal_mesh_placements':'Both actual native files independently checked against the same exported normal meshes by audit45.',
        'gcode_bytes_identical':identical,'actual_deposition_identical':deposition_identical,
        'own_final_deposition_audited':True,'physical_trial_verified':False,
        'assessment':'Studio rewrote part matrix metadata. Actual build/component transforms and modifier mesh vertices retain placement; process settings are unchanged. The newly emitted toolpaths have their own complete audit.'}
    (out/'reopen-checks.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=="__main__":check(Path(sys.argv[1]).resolve())
