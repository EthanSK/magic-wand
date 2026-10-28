#!/usr/bin/env python3
"""Portable release receipt and project-content checks; no CAD runtime required."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,importlib.util,json,zipfile,xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];RECEIPT=HERE/'exports/release.json';NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files():return sorted(p for p in HERE.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p!=RECEIPT)+sorted((ROOT/'magic-wand-3d-models').glob('Print-Shard-R2-*.3mf'))
def record(path):
 with path.open('x')as f:json.dump({'files':{str(p.relative_to(ROOT)):sha(p)for p in files()}},f,indent=2);f.write('\n')
def check():
 receipt=json.loads(RECEIPT.read_text());assert receipt['files']=={str(p.relative_to(ROOT)):sha(p)for p in files()},'R2 release files changed; regenerate and recheck receipts'
 m=json.loads((HERE/'exports/manifest.json').read_text());assert not m['functional_negative_modifiers']and set(m['support_helpers'])=={'Sense_Open_Cradle'}and m['separate_switch_plate_count']==0 and not m['physical_fit_verified']
 assert m['length_light_mm']==410 and m['handle']['mount_centres_z_mm']==[14.,104.]
 assert m['button_mounts']==[['thumb',90.,111.],['index',-35.,107.],['middle',-35.,81.]]
 for source,digest in m['source'].items():assert sha(HERE/source)==digest,source
 for p in m['parts']:
  assert sha(HERE/'exports'/p['file'])==p['sha256']and all(p['checks'][k]for k in ['watertight','winding_consistent','every_edge_shared_twice']),p['name']
  assert p['checks']['bodies']==1
 geometry=json.loads((HERE/'exports/model-checks.json').read_text());assert geometry['actual_exported_stls_checked']and not geometry['physical_fit_verified']
 battery=json.loads((HERE/'exports/battery-cap-checks.json').read_text());assert battery['passed']and not battery['failures']and battery['manifest_sha256']==sha(HERE/'exports/manifest.json')
 assert all(battery['mesh_sha256'][name]==next(p['sha256']for p in m['parts']if p['name']==name)for name in battery['mesh_sha256'])
 projects=json.loads((HERE/'exports/projects.json').read_text());mass=json.loads((HERE/'exports/mass.json').read_text())
 privacy_spec=importlib.util.spec_from_file_location('r2_privacy',ROOT/'shared/checks/privacy.py');privacy=importlib.util.module_from_spec(privacy_spec);privacy_spec.loader.exec_module(privacy)
 slice_receipts=json.loads((HERE/'exports/sliced-clearances.json').read_text())
 for key,label in [('complete','complete-both-hands'),('fit_tests','fit-tests')]:
  receipt=slice_receipts[key];assert receipt['passed']and len(receipt['projects'])==1
  scan=receipt['projects'][0];assert scan['passed']and scan['sha256']==projects[label]['sha256']and scan['manifest_sha256']==sha(HERE/'exports/manifest.json')and scan['checker_sha256']==sha(HERE/'check_sliced_paths.py')
  assert all(sha(HERE/name)==digest for name,digest in scan['region_source_hashes'].items())
  assert scan['used_part_stl_sha256']=={p['name']:p['sha256']for p in m['parts']if p['name']in projects[label]['parts']}
  assert all(not p['layer_start_audit']['floating_components']for p in scan['parts'].values())
  assert all(not result['violations']for p in scan['parts'].values()for result in p['checks'].values())
 # Independent sliced checker asserts functional clearances before producing
 # its receipt; the complete receipt is hash-bound with all release files.
 for label,entry in projects.items():
  path=ROOT/'magic-wand-3d-models'/entry['file'];assert sha(path)==entry['sha256']and entry['return_code']==0 and not entry['warnings']
  with zipfile.ZipFile(path)as z:
   assert z.testzip()is None
   model=E.fromstring(z.read('3D/3dmodel.model'));build=model.findall('m:build/m:item',NS);cfg=E.fromstring(z.read('Metadata/model_settings.config'));objects=cfg.findall('object');names={o.get('id'):next(t.get('value')for t in o.findall('metadata')if t.get('key')=='name')for o in objects}
   assert Counter(names[i.get('objectid')]for i in build)==Counter(entry['parts'])

   for o in objects:
    roles=Counter(p.get('subtype')for p in o.findall('part'))
    assert roles==(Counter(normal_part=1,support_blocker=1,support_enforcer=1)if names[o.get('id')]=='Sense_Open_Cradle'else Counter(normal_part=1))
   settings=json.loads(z.read('Metadata/project_settings.config'));assert str(settings['enable_support'])=='0'
   assert all(t.get('value')==('1'if names[o.get('id')]=='Sense_Open_Cradle'else'0')for o in objects for t in o.findall('metadata')if t.get('key')=='enable_support')
   if label=='fit-tests':
    for name in ['Switch_Fit_Test','Loop_Upper_Socket_Test']:
     obj=next(o for o in objects if names[o.get('id')]==name);s={t.get('key'):t.get('value')for t in obj.findall('metadata')};assert s['brim_type']=='no_brim'
   if 'Battery_Screw_Cap_Weighted'in entry['parts']:
    obj=next(o for o in objects if names[o.get('id')]=='Battery_Screw_Cap_Weighted');s={t.get('key'):t.get('value')for t in obj.findall('metadata')};assert s['sparse_infill_density']=='45%'and s['sparse_infill_pattern']=='gyroid'and s['wall_loops']=='3'and s['top_shell_layers']=='5'and s['bottom_shell_layers']=='5'
   for filename in z.namelist():
    if filename.endswith(('.model','.config','.xml','.rels','.gcode','.json')):
     text=z.read(filename).decode()
     for reason,pattern in privacy.PATTERNS.items():assert not pattern.search(text),(entry['file'],reason)
  if label=='complete-both-hands':assert {'Grip_Left','Grip_Right'}<=set(entry['parts'])and len(build)==9
  if label.startswith('one-left-'):assert len(build)==7
 for label,version in [('one-left-light','R2_left_light'),('one-left-weighted','R2_left_weighted')]:assert mass['versions'][version]['archive_sha256']==projects[label]['sha256']and mass['versions'][version]['build_instances']==7
 assert mass['weighted_cap_extra_printed_g']>0
 print('Shard R2 source, final meshes, both-handed normal-mesh projects, weighted infill and checked receipts match')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--record-new',type=Path);a=p.parse_args();record(a.record_new)if a.record_new else check()
