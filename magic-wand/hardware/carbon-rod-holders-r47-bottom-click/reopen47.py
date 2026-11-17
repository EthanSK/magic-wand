"""Reopen once in Studio's native slicer; compare effective recipes and modifiers."""
import argparse
from pathlib import Path
import json
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import numpy as np
import holder47
import slice45
from plate45 import digest
from reopen_compare46 import process_only, transform


def recipes(path):
    with ZipFile(path) as z:
        model=ET.fromstring(z.read('Metadata/model_settings.config'))
    result={}
    for obj in model.findall('object'):
        fields={m.get('key'):m.get('value') for m in obj.findall('metadata')}
        result[fields['name']]={'settings':fields,'parts':[
            {**{k:p.get(k) for k in ('id','subtype') if p.get(k) is not None},
             'metadata':{m.get('key'):m.get('value') for m in p.findall('metadata')}}
            for p in obj.findall('part')]}
    return result


def modifier_geometry(archive):
    result={}
    with ZipFile(archive) as z:
        model=ET.fromstring(z.read('3D/3dmodel.model'))
        resources={o.get('id'):o for o in model.findall('./{*}resources/{*}object')}
        config=ET.fromstring(z.read('Metadata/model_settings.config'))
        settings={o.get('id'):o for o in config.findall('object')};documents={}
        for item in model.findall('./{*}build/{*}item'):
            obj=settings[item.get('objectid')]
            owner=obj.find("metadata[@key='name']").get('value')
            base=transform(item.get('transform'));parts={p.get('id'):p for p in obj.findall('part')}
            for component in resources[item.get('objectid')].findall('./{*}components/{*}component'):
                identifier=component.get('objectid')
                if identifier not in parts:continue
                part=parts[identifier];kind=part.get('subtype','')
                if kind=='normal_part':continue
                assert 'modifier' in kind or kind=='support_enforcer',(owner,kind)
                file=next(v for k,v in component.attrib.items() if k.endswith('}path')).lstrip('/')
                if file not in documents:documents[file]=ET.fromstring(z.read(file))
                resource=documents[file].find('./{*}resources/{*}object[@id="'+identifier+'"]')
                vertices=np.asarray([[float(v.get(k)) for k in 'xyz'] for v in resource.findall('./{*}mesh/{*}vertices/{*}vertex')])
                faces=np.asarray([[int(t.get(k)) for k in ('v1','v2','v3')] for t in resource.findall('./{*}mesh/{*}triangles/{*}triangle')])
                world=base@transform(component.get('transform'))
                result[(owner,identifier)]=(vertices@world[:3,:3].T+world[:3,3],faces)
    return result


def run(initial,final):
    slice45.run(initial,final)
    return compare(initial,final)


def compare(initial,final):
    assert process_only(recipes(initial))==process_only(recipes(final)), 'Object process recipe changed on reopening'
    first,second=modifier_geometry(initial),modifier_geometry(final)
    assert first.keys()==second.keys() and first
    rows=[]
    for key,(a,af) in first.items():
        b,bf=second[key]
        assert a.shape==b.shape and len(af)==len(bf) and len(a)<1000,key
        distances=np.linalg.norm(b[:,None,:]-a[None,:,:],axis=2)
        nearest=distances.argmin(axis=1)
        error=float(distances[np.arange(len(b)),nearest].max())
        assert len(set(nearest))==len(a) and error<=.00001,(key,error)
        assert {tuple(sorted(f)) for f in af}=={tuple(sorted(nearest[f])) for f in bf},key
        rows.append({'owner':key[0],'part_id':key[1],'maximum_world_vertex_delta_mm':error,'topology_identical':True})
    with ZipFile(initial) as a,ZipFile(final) as b:
        assert json.loads(a.read('Metadata/project_settings.config'))==json.loads(b.read('Metadata/project_settings.config'))
        identical=a.read('Metadata/plate_1.gcode')==b.read('Metadata/plate_1.gcode')
    report={'initial_archive_sha256':digest(initial),'selected_archive_sha256':digest(final),
            'global_settings_identical':True,'object_process_settings_identical':True,
            'actual_modifier_placements_equivalent':True,'modifier_comparisons':rows,
            'gcode_bytes_identical':identical,'own_final_deposition_audited':False,
            'scope':'Native reopen and recipe/transform comparison. The selected complete plate still needs its own actual-path audits.'}
    (final.parent/'reopen-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('initial',type=Path);p.add_argument('final',type=Path);p.add_argument('--compare-only',action='store_true')
    a=p.parse_args();(compare if a.compare_only else run)(a.initial,a.final)
