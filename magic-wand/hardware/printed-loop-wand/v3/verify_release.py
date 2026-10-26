#!/usr/bin/env python3
"""Verify the Print V3 candidate source, meshes, mechanism checks and prepared projects."""
import argparse,hashlib,importlib.util,json,re,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
RECORD=ROOT/'magic-wand-3d-models/Print-3-lightweight-410mm.json'
PROJECTS={
 'Print-3-upper-only-410mm.3mf':['Lower_Shaft_Existing_Handle','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover'],
 'Print-3-full-left-raised-buttons-410mm.3mf':['Handle_Left','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Socket_Carrier']*3+['Choc_Socket_Keeper']*3,
 'Print-3-compact-button-fit-test.3mf':['Choc_Socket_Carrier','Choc_Socket_Keeper'],
 'Print-3-slim-bayonet-fit-test.3mf':['Fit_Test_Male','Fit_Test_Female']}
sp=importlib.util.spec_from_file_location('privacy',ROOT/'shared/checks/privacy.py');privacy=importlib.util.module_from_spec(sp);sp.loader.exec_module(privacy)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inspect(p,expected):
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  for name in z.namelist():
   if name.endswith(('.model','.config','.json','.xml','.gcode','.rels')):
    t=z.read(name).decode()
    for label,pattern in privacy.PATTERNS.items():assert not pattern.search(t),(p.name,name,label)
    assert not re.search(r'/Volumes/|[A-Za-z]:\\Users\\',t)
  cfg=json.loads(z.read('Metadata/project_settings.config'))
  for k,v in {'printer_model':'Bambu Lab P1S','filament_type':['PETG'],'layer_height':'0.2','wall_loops':'3','sparse_infill_density':'20%'}.items():assert cfg[k]==v,(p.name,k)
  assert {'layer_height','wall_loops','sparse_infill_density'}<=set(cfg['different_settings_to_system'][0].split(';'))
  settings=E.fromstring(z.read('Metadata/model_settings.config'))
  for obj in settings.findall('object'):
   meta={m.attrib.get('key'):m.attrib.get('value') for m in obj.findall('metadata')}
   if meta.get('name','').startswith('Handle_'):assert meta.get('support_type')=='normal(auto)'
  names={o.attrib['id']:next(m.attrib['value'] for m in o.findall('metadata') if m.attrib.get('key')=='name') for o in settings.findall('object')}
  ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
  items=E.fromstring(z.read('3D/3dmodel.model')).findall('m:build/m:item',ns)
  actual=sorted(names[i.attrib['objectid']] for i in items)
  assert actual==sorted(expected),(p.name,actual)
  assert all(i.attrib.get('printable','1')=='1' for i in items)
  assert any(n.endswith('.gcode') for n in z.namelist())
  return {'sha256':sha(p),'parts':len(actual),'part_names':actual,'contains_gcode':True}
def record(dest):
 files=sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.log'])
 files += [ROOT/'magic-wand-3d-models'/n for n in PROJECTS]
 files += [ROOT/'magic-wand-3d-models/Print-3-README.md',ROOT/'magic-wand/tests/printed-wand-v3.test.mjs']
 report={'version':'Print V3 candidate','design_revision':'L410-R6','physical_fit_verified':False,'files':{p.relative_to(ROOT).as_posix():sha(p) for p in files},'projects':{n:inspect(ROOT/'magic-wand-3d-models'/n,names) for n,names in PROJECTS.items()}}
 with dest.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print('Recorded Print V3 candidate')
def check():
 r=json.loads(RECORD.read_text());assert r['design_revision']=='L410-R6' and not r['physical_fit_verified']
 for name,h in r['files'].items():assert sha(ROOT/name)==h,'Stale Print V3 file: '+name
 m=json.loads((HERE/'exports/manifest.json').read_text());assert m['length_mm']==410 and m['wire_bore_mm']==10.4 and m['handle_length_mm']==160
 assert m['design_revision']=='L410-R6' and m['button_insert_size_mm']==[16.4,16.4,6.6]
 for name,h in m['source'].items():assert sha(HERE/name)==h,'CAD dependency changed: '+name
 for part in m['parts']:
  assert sha(HERE/'exports'/part['file'])==part['sha256'];a=part['checks'];assert a['watertight'] and a['winding_consistent'] and a['every_edge_shared_twice'] and a['bodies']==1
 f=json.loads((HERE/'exports/fit-checks.json').read_text())
 assert not f['physical_fit_verified'] and abs(f['resting_board_overlap_mm3'])<.001 and abs(f['body_cover_overlap_mm3'])<.001
 assert all(abs(v)<.001 for v in f['cover_released_slide_overlap_mm3'].values())
 assert f['cover_side_pull_blocked_mm3']['0.5']>1.
 for a in f['slim_joint'].values():assert max(a['entry_insertion_mm3'].values())<.001 and a['locked_pull_overlap_mm3']>1.
 for a in f['compact_button_insert'].values():assert abs(a['rest_overlap_mm3'])<.01 and a['rear_stop_overlap_mm3']>1 and a['front_lip_overlap_mm3']>.1
 g=json.loads((HERE/'exports/sliced-clearance-check.json').read_text());assert g['project_sha256']==sha(ROOT/'magic-wand-3d-models/Print-3-full-left-raised-buttons-410mm.3mf');assert all(not features for a in g['clearance_extrusion_samples'].values() for features in a.values())
 for n,names in PROJECTS.items():assert r['projects'][n]==inspect(ROOT/'magic-wand-3d-models'/n,names)
 assert (HERE/'preview/../../../../../docs/lib/three-0.185.1/three.module.min.js').resolve().is_file()
 print('Print V3 source, 15 meshes, captured lid, bayonets, compact button seats and four Bambu projects match')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--record-new',type=Path);p.add_argument('--check',action='store_true');a=p.parse_args();record(a.record_new) if a.record_new else check()
