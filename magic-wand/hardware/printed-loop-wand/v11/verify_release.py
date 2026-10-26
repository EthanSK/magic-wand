#!/usr/bin/env python3
"""Verify the Print V11 candidate source, meshes, mechanism checks and prepared projects."""
import argparse,hashlib,importlib.util,json,re,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
RECORD=ROOT/'magic-wand-3d-models/Print-11-top-slide-410mm.json'
PROJECTS={
 'Print-11-upper-only-helix-410mm.3mf':['Lower_Shaft_Existing_Handle','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover'],
 'Print-11-complete-left-right-top-slide-410mm.3mf':['Handle_Left','Handle_Right','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Top_Slide_Plate']*3+['Removable_Finger_Loop'],
 'Print-11-one-left-wand-410mm.3mf':['Handle_Left','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Top_Slide_Plate']*3+['Removable_Finger_Loop'],
 'Print-11-top-slide-button-fit-test.3mf':['Choc_Top_Slide_Plate','Button_Mount_Coupon'],
 'Print-11-detachable-loop-fit-test.3mf':['Loop_Socket_Coupon','Loop_Foot_Coupon'],
 'Print-11-slim-bayonet-fit-test.3mf':['Fit_Test_Male','Fit_Test_Female']}
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
   if meta.get('name')=='Removable_Finger_Loop':
    assert meta.get('support_type')=='normal(manual)' and meta.get('brim_type')=='no_brim'
    assert any(part.attrib.get('subtype')=='support_enforcer' for part in obj.findall('part'))
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
 files += [ROOT/'magic-wand-3d-models/Print-11-README.md',ROOT/'magic-wand/tests/printed-wand-v11.test.mjs']
 report={'version':'Print V11 candidate','design_revision':'S410-R7','physical_fit_verified':False,'files':{p.relative_to(ROOT).as_posix():sha(p) for p in files},'projects':{n:inspect(ROOT/'magic-wand-3d-models'/n,names) for n,names in PROJECTS.items()}}
 with dest.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print('Recorded Print V11 candidate')
def check():
 r=json.loads(RECORD.read_text());assert r['design_revision']=='S410-R7' and not r['physical_fit_verified']
 for name,h in r['files'].items():assert sha(ROOT/name)==h,'Stale Print V11 file: '+name
 m=json.loads((HERE/'exports/manifest.json').read_text());assert m['length_mm']==410 and m['wire_bore_mm']==10.4 and m['handle_length_mm']==160
 assert m['design_revision']=='S410-R7' and m['button_insert_size_mm']==[16.4,17.2,2.5] and m['button_plate_face_mm']==1.3
 assert m['hand_buttons']==[['thumb',90.,139.],['index',-35.,135.],['middle',-35.,109.]]
 assert m['helix']=={'directions':[1,-1],'pitch_mm':[90.,72.],'height_mm':1.2}
 assert m['shaft_core_monotonic'] and m['shaft_wall_mm']==1.0 and m['grip_wall_mm']==1.0 and m['loop_wall_mm']==1.2 and m['loop_section_mm']==[18.,12.]
 for name,h in m['source'].items():assert sha(HERE/name)==h,'CAD dependency changed: '+name
 for part in m['parts']:
  assert sha(HERE/'exports'/part['file'])==part['sha256'];a=part['checks'];assert a['watertight'] and a['winding_consistent'] and a['every_edge_shared_twice'] and a['bodies']==1
 f=json.loads((HERE/'exports/fit-checks.json').read_text())
 assert not f['physical_fit_verified'] and abs(f['resting_board_overlap_mm3'])<.001 and abs(f['body_cover_overlap_mm3'])<.001
 assert all(abs(v)<.001 for v in f['cover_released_slide_overlap_mm3'].values())
 assert f['cover_side_pull_blocked_mm3']['0.5']>1.
 for a in f['slim_joint'].values():assert max(a['entry_insertion_mm3'].values())<.001 and a['locked_pull_overlap_mm3']>1.
 for a in f['top_slide_button'].values():assert max(abs(v) for v in a['upward_release_path_mm3'].values())<.01 and a['radial_pull_blocked_mm3']>.05 and a['downward_stop_mm3']>.05
 assert len(f['top_slide_button'])==6 and all(max(a.values())<.01 for a in f['button_neighbour_clearance'].values())
 assert not f['thin_plate']['separate_keeper']
 assert all('Keeper' not in p['name'] for p in m['parts'])
 assert all(a['maximum_outward_step_mm']<=0 for a in f['shaft_taper'].values())
 assert all(v>.002 for v in f['helix_material_probe_mm3'].values())
 assert all(v<.001 for v in f['thin_hollow_shaft_overlap_mm3'].values())
 g=json.loads((HERE/'exports/sliced-clearance-check.json').read_text());assert g['project_sha256']==sha(ROOT/'magic-wand-3d-models/Print-11-complete-left-right-top-slide-410mm.3mf');assert all(not features for a in g['clearance_extrusion_samples'].values() for features in a.values())
 assert {'Handle_Left','Handle_Right','Removable_Finger_Loop'}<=set(g['clearance_extrusion_samples'])
 for hand in ['Handle_Left','Handle_Right']:assert {'loop_mount_slide_0','loop_mount_slide_1'}<=set(g['clearance_extrusion_samples'][hand])
 mass=json.loads((HERE/'exports/one-wand-mass-comparison.json').read_text())
 assert not mass['physical_mass_measured'] and [a['build_instances'] for a in mass['versions'].values()]==[11,11]
 assert mass['versions']['V11_left_ribbed_windows']['archive_sha256']==sha(ROOT/'magic-wand-3d-models/Print-11-one-left-wand-410mm.3mf')
 assert mass['versions']['V11_left_ribbed_windows']['printed_parts_g']<80.
 assert mass['versions']['V11_left_ribbed_windows']['object_printed_parts_g']['Handle_Left']<mass['versions']['V10_left_slotted_helix']['object_printed_parts_g']['Handle_Left']*1.05
 assert m['loop_shift_mm']==0. and len(m['loop_air_ports'])==3
 assert len(f['loop_contact_airflow'])==3 and max(f['loop_contact_airflow'].values())<.001
 assert f['head_layer_islands']==[]
 assert max(f['slot_open_probes'].values())<.001
 assert all(v>=f['previous_spiral_reference_probes'][k]-.00015 for k,v in f['solid_helix_probes'].items())
 assert all(v>1000 for v in f['window_area_mm2'].values())
 assert all(not v for v in f['shaft_window_layer_islands'].values())
 assert min(f['axial_land_probes'].values())>.002 and len(f['slot_open_probes'])>=15
 assert f['loop_projection']['upper_thumb_centerline_reach_mm']-f['loop_projection']['lower_centerline_reach_mm']>8.
 for fit in f['detachable_loop'].values():
  assert fit['rest_overlap_mm3']<.001 and max(fit['released_slide_mm3'].values())<.001
  assert fit['radial_capture_mm3']>1. and fit['unreleased_upward_capture_mm3']>.1
 assert len(m['parts'])==18 and m['removable_loop']['release_slide_mm']==22.
 slice_results=json.loads((HERE/'exports/slice-results.json').read_text())
 assert set(slice_results)==set(PROJECTS) and all(v['return_code']==0 and v['warnings']==[] for v in slice_results.values())
 for n,names in PROJECTS.items():assert r['projects'][n]==inspect(ROOT/'magic-wand-3d-models'/n,names)
 assert (HERE/'preview/../../../../../docs/lib/three-0.185.1/three.module.min.js').resolve().is_file()
 print('Print V11 source, restored helix, continuous taper, both grips, raised side buttons, top-slide plates, 18 meshes and six Bambu projects match')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--record-new',type=Path);p.add_argument('--check',action='store_true');a=p.parse_args();record(a.record_new) if a.record_new else check()
