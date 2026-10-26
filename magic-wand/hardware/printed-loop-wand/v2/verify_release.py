#!/usr/bin/env python3
"""Verify Print V2 source/export freshness and inspect both public Bambu archives.
Only the standard library is needed. --record-new writes an unused release record.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
RECORD=ROOT/'magic-wand-3d-models/Print-2-diamond-mug-wand.json'
PROJECTS={'wand':'Print-2-diamond-mug-wand.3mf','head_fit_test':'Print-2-diamond-head-fit-test.3mf'}
FULL_NAMES=['Handle_Left','Handle_Right','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Socket_Carrier']*3+['Choc_Socket_Keeper']*3
sp=importlib.util.spec_from_file_location('repository_privacy',ROOT/'shared/checks/privacy.py');privacy=importlib.util.module_from_spec(sp);sp.loader.exec_module(privacy)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inspect_project(path,kind):
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None,path.name
  for name in z.namelist():
   if name.endswith(('.model','.config','.json','.xml','.gcode','.rels')):
    text=z.read(name).decode('utf8')
    for label,pattern in privacy.PATTERNS.items():assert not pattern.search(text),f'{path.name}: {label} in {name}'
    assert not re.search(r'(?:/Volumes/|[A-Za-z]:\\Users\\)',text),f'{path.name}: local path'
  config=json.loads(z.read('Metadata/project_settings.config'))
  expected={'printer_model':'Bambu Lab P1S','filament_type':['PETG'],'layer_height':'0.2','wall_loops':'3','sparse_infill_density':'20%'}
  for key,value in expected.items():assert config[key]==value,f'{path.name}: {key}'
  registered=set(config['different_settings_to_system'][0].split(';'))
  assert {'layer_height','wall_loops','sparse_infill_density'}<=registered
  settings=ET.fromstring(z.read('Metadata/model_settings.config'))
  names={o.attrib['id']:next(m.attrib['value'] for m in o.findall('metadata') if m.attrib.get('key')=='name') for o in settings.findall('object')}
  ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
  items=ET.fromstring(z.read('3D/3dmodel.model')).findall('m:build/m:item',ns)
  assert items and all(i.attrib.get('printable','1')=='1' for i in items)
  actual=sorted(names[i.attrib['objectid']] for i in items)
  expected_names=FULL_NAMES if kind=='wand' else ['Sense_Head_Base','Sense_Sliding_Cover']
  assert actual==sorted(expected_names),f'{path.name}: unexpected build instances'
  return {'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'parts':len(actual),'part_names':actual,'contains_gcode':any(n.endswith('.gcode') for n in z.namelist())}
def record_new(dest):
 files=sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.log'])
 files += [ROOT/'magic-wand-3d-models'/n for n in PROJECTS.values()]
 files += [ROOT/'magic-wand-3d-models/Print-2-README.md',ROOT/'magic-wand/tests/printed-wand-v2.test.mjs']
 report={'schema':1,'print_version':2,'design_revision':'V17','status':'print prototype','physical_fit_verified':False,
  'inputs':{p.relative_to(ROOT).as_posix():sha(p) for p in files},
  'projects':{kind:inspect_project(ROOT/'magic-wand-3d-models'/name,kind) for kind,name in PROJECTS.items()}}
 with dest.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print('Recorded Print V2 source and export hashes')
def check():
 report=json.loads(RECORD.read_text());assert report['print_version']==2 and report['design_revision']=='V17'
 assert report['physical_fit_verified'] is False
 for name,digest in report['inputs'].items():assert sha(ROOT/name)==digest,f'Stale Print V2 release: {name}'
 geometry=json.loads((HERE/'exports/manifest.json').read_text())
 assert geometry['version']=='Print V2' and geometry['design_revision']=='V17'
 assert geometry['length_mm']==340 and geometry['head_size_mm']==[40,37,58]
 assert geometry['physical_fit_verified'] is False
 for name,digest in geometry['source'].items():assert sha(HERE/name)==digest,f'Stale CAD: {name}'
 for part in geometry['parts']:
  assert sha(HERE/'exports'/part['file'])==part['sha256'],part['name']
  mesh=part['checks'];assert mesh['watertight'] and mesh['winding_consistent'] and mesh['every_edge_shared_twice'] and mesh['bodies']==1
 fit=json.loads((HERE/'exports/fit-checks.json').read_text())
 assert abs(fit['resting_board_overlap_mm3'])<.001 and abs(fit['body_cover_overlap_mm3'])<.001
 assert all(p['minimum_loop_gap_mm']>=4.9 and abs(p['loop_overlap_mm3'])<.001 for p in fit['thumb_mount'].values())
 for kind,name in PROJECTS.items():assert report['projects'][kind]==inspect_project(ROOT/'magic-wand-3d-models'/name,kind)
 script=(HERE/'preview/preview.mjs').read_text();module=re.search(r"import \* as THREE from '([^']+)'",script).group(1)
 assert (HERE/'preview'/module).resolve().is_file()
 print('Print V2 source, twelve meshes, board/cover checks, 5 mm thumb clearance and both Bambu projects match')
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);group=ap.add_mutually_exclusive_group();group.add_argument('--record-new',type=Path);group.add_argument('--check',action='store_true');args=ap.parse_args()
 record_new(args.record_new) if args.record_new else check()
