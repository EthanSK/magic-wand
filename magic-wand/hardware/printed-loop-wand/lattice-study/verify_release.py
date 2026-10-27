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
    assert len(m['variants'])==4 and mass['baseline']['build_instances']==11
    for key,v in m['variants'].items():
        assert len(v['parts'])==5 and all(p['checks']['bodies']==1 and p['checks']['watertight'] for p in v['parts'])
        for p in v['parts']:assert sha(HERE/'exports'/key/p['file'])==p['sha256']
        assert geometry['variants'][key]['minimum_members']
        assert all(not hit for part in sliced[key]['clearance_extrusion_samples'].values() for hit in part.values())
        for label,p in projects[key].items():
            archive=ROOT/'magic-wand-3d-models'/p['file'];assert sha(archive)==p['sha256']
            assert not p['slice']['warning_message']
            with zipfile.ZipFile(archive) as z:
                assert z.testzip() is None
                model=E.fromstring(z.read('3D/3dmodel.model'));build=model.findall('m:build/m:item',NS)
                assert len(build)==(12 if label=='complete' else 11)
                cfg=E.fromstring(z.read('Metadata/model_settings.config'))
                names={o.get('id'):next(m.get('value') for m in o.findall('metadata') if m.get('key')=='name') for o in cfg.findall('object')}
                # Bambu reorders metadata objects. Check the actual build items,
                # including multiplicity, so an unprinted right stem cannot pass.
                assert Counter(names[item.get('objectid')] for item in build)==Counter(p['part_names'])
                for name in z.namelist():
                    if name.endswith(('.model','.config','.xml','.rels','.gcode','.json')):
                        text=z.read(name).decode()
                        for reason,pattern in privacy.PATTERNS.items():assert not pattern.search(text),(p['file'],reason)
            if label=='complete':assert sliced[key]['project_sha256']==p['sha256']
            else:assert mass['variants'][key]['archive_sha256']==p['sha256'] and mass['variants'][key]['build_instances']==11
    for p in m['shared_parts']:assert sha(HERE/'exports'/p['file'])==p['sha256']
    print('Four lattice candidates: source/export freshness, 20 connected meshes, 8 sliced projects and functional clearance receipts match')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record-new',type=Path);a=p.parse_args();snapshot(a.record_new) if a.record_new else check()
