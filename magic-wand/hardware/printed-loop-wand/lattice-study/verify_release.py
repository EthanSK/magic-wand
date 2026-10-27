#!/usr/bin/env python3
"""Portable freshness, packaging and privacy checks for the lattice study."""
from pathlib import Path
import argparse, hashlib, json, zipfile, xml.etree.ElementTree as E, importlib.util
from collections import Counter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];RECEIPT=HERE/'exports/release.json'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files():
    return sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=RECEIPT)+sorted((ROOT/'magic-wand-3d-models').glob('Print-Lattice-*.3mf'))
def snapshot(out):
    out.write_text(json.dumps({'baseline_commit':'e53e8de','files':{str(p.relative_to(ROOT)):sha(p) for p in files()}},indent=2)+'\n')
def check():
    record=json.loads(RECEIPT.read_text())
    assert record['files']=={str(p.relative_to(ROOT)):sha(p) for p in files()},'Source/export/project snapshot is stale'
    m=json.loads((HERE/'exports/manifest.json').read_text())
    for name,h in m['source'].items():assert sha(HERE/name)==h,('Stale CAD export',name)
    for name,h in m['baseline_source'].items():assert sha(HERE/name)==h,('Changed baseline',name)
    assert not m['physical_fit_verified'] and not m['physical_strength_verified']
    geometry=json.loads((HERE/'exports/exported-model-checks.json').read_text())
    sliced=json.loads((HERE/'exports/sliced-clearances.json').read_text())
    projects=json.loads((HERE/'exports/projects.json').read_text())
    mass=json.loads((HERE/'exports/mass-comparison.json').read_text())
    sp=importlib.util.spec_from_file_location('privacy',ROOT/'shared/checks/privacy.py');privacy=importlib.util.module_from_spec(sp);sp.loader.exec_module(privacy)
    assert set(m['variants'])==set(geometry['variants'])==set(projects)==set(mass['variants'])==set(sliced) and mass['baseline']['build_instances']==11
    for key,v in m['variants'].items():
        assert len(v['parts'])==(6 if v.get('open_head') else 5) and all(p['checks']['bodies']==1 and p['checks']['watertight'] for p in v['parts'])
        for p in v['parts']:assert sha(HERE/'exports'/key/p['file'])==p['sha256']
        assert geometry['variants'][key]['minimum_members']
        if v.get('open_head'):
            h=geometry['variants'][key]['open_head']
            assert max(h['clearances_mm3'].values())<.75
            assert h['neck_difference_mm3']<.75 and h['clip_material_lost_mm3']<.75 and h['corner_pocket_material_lost_mm3']<.75
            assert 'Sense_Open_Cradle' in sliced[key]['clearance_extrusion_samples']
        assert all(not hit for part in sliced[key]['clearance_extrusion_samples'].values() for hit in part.values())
        for label,p in projects[key].items():
            archive=ROOT/'magic-wand-3d-models'/p['file'];assert sha(archive)==p['sha256']
            assert not p['slice']['warning_message']
            with zipfile.ZipFile(archive) as z:
                assert z.testzip() is None
                model=E.fromstring(z.read('3D/3dmodel.model'));build=model.findall('m:build/m:item',NS)
                assert len(build)==len(p['part_names'])==(12 if label=='complete' else 11)-int(v.get('open_head',False))
                cfg=E.fromstring(z.read('Metadata/model_settings.config'))
                names={o.get('id'):next(m.get('value') for m in o.findall('metadata') if m.get('key')=='name') for o in cfg.findall('object')}
                # Bambu reorders metadata objects. Check the actual build items,
                # including multiplicity, so an unprinted right stem cannot pass.
                actual=Counter(names[item.get('objectid')] for item in build)
                expected=Counter(q['name'] for q in v['parts']+[q for q in m['shared_parts'] if q['name'] not in v.get('omit_shared_parts',[])])
                expected['Choc_Recessed_Plate']=3
                if label=='one-left':del expected['Handle_Right']
                assert actual==expected==Counter(p['part_names'])
                if v.get('open_head'):
                    obj=next(o for o in cfg.findall('object') if names[o.get('id')]=='Sense_Open_Cradle')
                    settings={q.get('key'):q.get('value') for q in obj.findall('metadata')}
                    assert settings['enable_support']=='1' and settings['support_type']=='normal(manual)' and settings['bridge_no_support']=='1'
                    assert any(q.get('subtype')=='support_enforcer' for q in obj.findall('part'))
                for name in z.namelist():
                    if name.endswith(('.model','.config','.xml','.rels','.gcode','.json')):
                        text=z.read(name).decode()
                        for reason,pattern in privacy.PATTERNS.items():assert not pattern.search(text),(p['file'],reason)
            if label=='complete':assert sliced[key]['project_sha256']==p['sha256']
            else:assert mass['variants'][key]['archive_sha256']==p['sha256'] and mass['variants'][key]['build_instances']==11-int(v.get('open_head',False))
    for p in m['shared_parts']:assert sha(HERE/'exports'/p['file'])==p['sha256']
    print(f"{len(m['variants'])} lattice candidates: source/export freshness, connected meshes, sliced projects and functional clearance receipts match")
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record-new',type=Path);a=p.parse_args();snapshot(a.record_new) if a.record_new else check()
