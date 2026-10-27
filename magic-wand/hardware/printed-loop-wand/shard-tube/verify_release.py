#!/usr/bin/env python3
"""Portable source, mesh, layout, slice and privacy verification."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,importlib.util,json,zipfile,xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];RECEIPT=HERE/'exports/release.json';NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files():return sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=RECEIPT)+sorted((ROOT/'magic-wand-3d-models').glob('Print-Shard-Tube-*.3mf'))
def snapshot(p):p.write_text(json.dumps({'files':{str(q.relative_to(ROOT)):sha(q) for q in files()}},indent=2)+'\n')
def check():
    receipt=json.loads(RECEIPT.read_text());assert receipt['files']=={str(p.relative_to(ROOT)):sha(p) for p in files()},'Continuous design files changed without rebuilding'
    m=json.loads((HERE/'exports/manifest.json').read_text())
    for source,digest in m['source'].items():assert sha(HERE/source)==digest,source
    for p in m['parts']+m['shared_parts']:assert sha(HERE/'exports'/p['file'])==p['sha256'],p['name']
    c=m['checks'];assert c['radius_monotonic'] and c['tip_radius_mm']<c['base_radius_mm'] and c['shaft_length_mm']<250 and c['old_seam_open_samples']>0
    assert not c['physical_fit_verified'] and not c['physical_strength_verified']
    shaft=next(p for p in m['parts'] if p['name']=='Continuous_Shaft');assert shaft['checks']['bodies']==1 and shaft['checks']['watertight'] and shaft['checks']['print_size_mm'][2]<250
    geometry=json.loads((HERE/'exports/exported-model-checks.json').read_text());assert not geometry['floating_layer_starts'] and geometry['grip_joint_difference_mm3']<.75
    assert max(geometry['holder_insert_mm3'].values())<.1 and max(v for t,v in geometry['holder_turn_mm3'].items() if float(t)<=0)<.1 and geometry['holder_turn_mm3']['5.0']>1 and geometry['holder_pull_stop_mm3']>1
    slices=json.loads((HERE/'exports/sliced-clearances.json').read_text());grip=json.loads((HERE/'exports/v20-grip-clearances.json').read_text());assert all(not hit for part in slices['clearance_extrusion_samples'].values() for hit in part.values());assert all(not hit for part in grip['clearance_extrusion_samples'].values() for hit in part.values());assert grip['project_sha256']==slices['project_sha256']
    assert set(slices['clearance_extrusion_samples'])=={'Handle_Left','Handle_Right','Continuous_Shaft','Sense_Open_Cradle','Removable_Finger_Loop'}
    projects=json.loads((HERE/'exports/projects.json').read_text())['continuous'];mass=json.loads((HERE/'exports/mass.json').read_text())
    privacy_spec=importlib.util.spec_from_file_location('privacy',ROOT/'shared/checks/privacy.py');privacy=importlib.util.module_from_spec(privacy_spec);privacy_spec.loader.exec_module(privacy)
    for label,entry in projects.items():
        archive=ROOT/'magic-wand-3d-models'/entry['file'];assert sha(archive)==entry['sha256'] and not entry['slice']['warning_message']
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            model=E.fromstring(z.read('3D/3dmodel.model'));build=model.findall('m:build/m:item',NS);assert len(build)==(10 if label=='complete' else 9)
            cfg=E.fromstring(z.read('Metadata/model_settings.config'));objects=cfg.findall('object');names={o.get('id'):next(v.get('value') for v in o.findall('metadata') if v.get('key')=='name') for o in objects}
            expected=Counter(x['name'] for x in m['parts']+m['shared_parts']);expected['Choc_Recessed_Plate']=3
            if label=='one-left':del expected['Handle_Right']
            assert Counter(names[i.get('objectid')] for i in build)==expected==Counter(entry['part_names'])
            loop=next(o for o in objects if names[o.get('id')]=='Removable_Finger_Loop');loop_settings={v.get('key'):v.get('value') for v in loop.findall('metadata')};assert loop_settings['sparse_infill_density']=='100%'
            for name,mode in [('Continuous_Shaft','normal(auto)'),('Sense_Open_Cradle','normal(manual)')]:
                obj=next(o for o in objects if names[o.get('id')]==name);settings={v.get('key'):v.get('value') for v in obj.findall('metadata')};assert settings['enable_support']=='1' and settings['support_type']==mode
                if name=='Sense_Open_Cradle':assert settings['bridge_no_support']=='1' and any(q.get('subtype')=='support_enforcer' for q in obj.findall('part'))
            for name in z.namelist():
                if name.endswith(('.model','.config','.xml','.rels','.gcode','.json')):
                    text=z.read(name).decode()
                    for reason,pattern in privacy.PATTERNS.items():assert not pattern.search(text),(entry['file'],reason)
        if label=='complete':assert slices['project_sha256']==entry['sha256']
        else:assert mass['continuous']['archive_sha256']==entry['sha256'] and mass['continuous']['build_instances']==9
    print('Sharper tube: source, retained loop, meshes and both checked print projects match')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record-new',type=Path);a=p.parse_args();snapshot(a.record_new) if a.record_new else check()
