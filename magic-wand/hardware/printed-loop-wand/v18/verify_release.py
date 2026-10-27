#!/usr/bin/env python3
"""Verify the Print V18 candidate source, meshes, mechanism checks and prepared projects."""
import argparse,hashlib,importlib.util,json,re,zipfile,struct,math
from pathlib import Path
import xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
RECORD=ROOT/'magic-wand-3d-models/Print-18-seated-handle-slim-grip-410mm.json'
PROJECTS={
 'Print-18-replacement-loop-only.3mf':['Removable_Finger_Loop'],
 'Print-18-upper-only-helix-410mm.3mf':['Lower_Shaft_Existing_Handle','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover'],
 'Print-18-complete-left-right-seated-handle-slim-grip-410mm.3mf':['Handle_Left','Handle_Right','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Recessed_Plate']*3+['Removable_Finger_Loop'],
 'Print-18-one-left-wand-410mm.3mf':['Handle_Left','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Recessed_Plate']*3+['Removable_Finger_Loop'],
 'Print-18-recessed-switch-button-fit-test.3mf':['Choc_Recessed_Plate','Button_Mount_Coupon'],
 'Print-18-detachable-loop-fit-test.3mf':['Loop_Socket_Coupon','Loop_Foot_Coupon'],
 'Print-18-slim-bayonet-fit-test.3mf':['Fit_Test_Male','Fit_Test_Female']}
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
 files += [ROOT/'magic-wand-3d-models/Print-18-README.md',ROOT/'magic-wand/tests/printed-wand-v18.test.mjs']
 report={'version':'Print V18 candidate','design_revision':'S410-R14','physical_fit_verified':False,'files':{p.relative_to(ROOT).as_posix():sha(p) for p in files},'projects':{n:inspect(ROOT/'magic-wand-3d-models'/n,names) for n,names in PROJECTS.items()}}
 with dest.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print('Recorded Print V18 candidate')
def check():
 r=json.loads(RECORD.read_text());assert r['design_revision']=='S410-R14' and not r['physical_fit_verified']
 for name,h in r['files'].items():assert sha(ROOT/name)==h,'Stale Print V18 file: '+name
 m=json.loads((HERE/'exports/manifest.json').read_text());assert m['length_mm']==410 and m['wire_bore_mm']==10.4 and m['handle_length_mm']==160
 assert m['design_revision']=='S410-R14' and m['button_insert_size_mm']==[16.4,17.2,2.5] and m['button_plate_face_mm']==1.3
 assert m['hand_buttons']==[['thumb',90.,139.],['index',-35.,135.],['middle',-35.,109.]]
 assert m['helix']=={'directions':[1,-1],'pitch_mm':[90.,72.],'height_mm':1.2}
 assert m['shaft_core_monotonic'] and m['shaft_wall_mm']==1.0 and m['grip_wall_mm']==1.0 and m['loop_wall_mm']==1.45 and m['loop_section_mm']==[18.,12.]
 for name,h in m['source'].items():assert sha(HERE/name)==h,'CAD dependency changed: '+name
 for part in m['parts']:
  assert sha(HERE/'exports'/part['file'])==part['sha256'];a=part['checks'];assert a['watertight'] and a['winding_consistent'] and a['every_edge_shared_twice'] and a['bodies']==1
 f=json.loads((HERE/'exports/fit-checks.json').read_text())
 assert f['direct_handle_joins']['matching_seat_difference_mm3']<.001
 assert m['grip_diameter_reduction_mm']==3.2 and m['loop_neck_diameter_mm']==4.2 and m['loop_seat_mm']==[14.4,9.6,1.2]
 assert f['direct_handle_joins']['old_toe_material_mm3']<.001 and f['direct_handle_joins']['neck_diameter_mm']==4.2
 assert len(f['seated_shoulders'])==2 and all(p['inserted_shoulder_material_mm3']>25. and p['locked_stem_overlap_mm3']<.001 for p in f['seated_shoulders'].values())
 assert all(abs(p['reduction_mm']-1.6)<.001 for p in f['slimmer_grip'].values())
 assert not f['physical_fit_verified'] and abs(f['resting_board_overlap_mm3'])<.001 and abs(f['body_cover_overlap_mm3'])<.001
 assert all(abs(v)<.001 for v in f['cover_released_slide_overlap_mm3'].values())
 assert f['cover_side_pull_blocked_mm3']['0.5']>1.
 for a in f['slim_joint'].values():assert max(a['entry_insertion_mm3'].values())<.001 and a['locked_pull_overlap_mm3']>1.
 for a in f['button_claw_mount'].values():assert a['rest_mm3']<.01 and max(abs(v)for v in a['released_radial_route_mm3'].values())<.01 and min(a['radial_pull_blocked_mm3'],a['downward_stop_mm3'],a['upward_stop_mm3'])>.05
 assert len(f['socket_and_switch'])==6 and all(a['socket_rest_mm3']<.01 and a['switch_housing_rest_mm3']<.01 for a in f['socket_and_switch'].values())
 assert len(f['button_claw_mount'])==6 and all(max(a.values())<.01 for a in f['button_neighbour_clearance'].values())
 assert not f['thin_plate']['separate_keeper']
 assert len(f['borderless_switches'])==6 and all(a['external_material_outside_small_tabs_mm3']<.001 and a['full_3mm_keycap_stroke_overlap_mm3']<.001 for a in f['borderless_switches'].values())
 plate=next(p for p in m['parts']if p['name']=='Choc_Recessed_Plate')
 assert plate['checks']['print_size_mm']==[16.4,17.2,2.5]
 blob=(HERE/'exports'/plate['file']).read_bytes();bed_area=0.
 for k in range(struct.unpack_from('<I',blob,80)[0]):
  row=struct.unpack_from('<12f',blob,84+50*k);a,b,c=[row[j:j+3]for j in (3,6,9)]
  if max(abs(p[2])for p in (a,b,c))<.0002:
   u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)];cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];bed_area+=math.sqrt(sum(x*x for x in cross))/2
 assert bed_area>80.,('Plate is not on its broad face',bed_area)
 assert not m['external_square_surround'] and m['button_surround_mm']==[0.,0.] and m['button_recess_increase_mm']==3.4
 assert all('Keeper' not in p['name'] for p in m['parts'])
 assert all(a['maximum_outward_step_mm']<=0 for a in f['shaft_taper'].values())
 assert all(v>.002 for v in f['helix_material_probe_mm3'].values())
 assert all(v<.001 for v in f['thin_hollow_shaft_overlap_mm3'].values())
 g=json.loads((HERE/'exports/sliced-clearance-check.json').read_text());assert g['project_sha256']==sha(ROOT/'magic-wand-3d-models/Print-18-complete-left-right-seated-handle-slim-grip-410mm.3mf');assert all(not features for a in g['clearance_extrusion_samples'].values() for features in a.values())
 assert {'Handle_Left','Handle_Right','Removable_Finger_Loop'}<=set(g['clearance_extrusion_samples'])
 for hand in ['Handle_Left','Handle_Right']:
  assert all('loop_mount_'+str(k)+'_broad_shoulder_'+str(angle) in g['clearance_extrusion_samples'][hand] for k in [0,1] for angle in [0.,3.,6.,9.,12.])
  assert {'loop_mount_0_cam_0.0','loop_mount_1_cam_0.0','loop_mount_0_cam_12.0','loop_mount_1_cam_12.0'}<=set(g['clearance_extrusion_samples'][hand])
 solo=json.loads((HERE/'exports/replacement-loop-sliced-clearance-check.json').read_text());assert solo['project_sha256']==sha(ROOT/'magic-wand-3d-models/Print-18-replacement-loop-only.3mf') and set(solo['clearance_extrusion_samples'])=={'Removable_Finger_Loop'}
 assert all(not feature for values in solo['clearance_extrusion_samples'].values()for feature in values.values())
 mass=json.loads((HERE/'exports/one-wand-mass-comparison.json').read_text())
 assert not mass['physical_mass_measured'] and [a['build_instances'] for a in mass['versions'].values()]==[11,11]
 assert mass['versions']['V18_left_art_nouveau']['archive_sha256']==sha(ROOT/'magic-wand-3d-models/Print-18-one-left-wand-410mm.3mf')
 assert mass['versions']['V18_left_art_nouveau']['printed_parts_g']<80.
 assert m['loop_shift_mm']==0. and len(m['loop_air_ports'])==3
 assert len(f['loop_contact_airflow'])==3 and max(f['loop_contact_airflow'].values())<.001
 assert f['head_layer_islands']==[]
 assert max(f['slot_open_probes'].values())<.001
 assert all(v>=f['previous_spiral_reference_probes'][k]-.00015 for k,v in f['solid_helix_probes'].items())
 assert all(v>500 for v in f['window_area_mm2'].values())
 assert .7<f['window_area_ratio']['grip']<.95
 assert all(p['new_mm3']>.0015 and p['previous_mm3']<.0001 for p in f['rail_reinforcement_probes'].values())
 assert m['solid_spine_width_mm']==3.6 and m['grip_rail_depth_mm']==1.6 and m['solid_spine_depth_mm']==1.8
 assert all(not v for v in f['shaft_window_layer_islands'].values())
 assert min(f['axial_land_probes'].values())>.002 and len(f['slot_open_probes'])>=15
 assert f['loop_projection']['upper_thumb_centerline_reach_mm']-f['loop_projection']['lower_centerline_reach_mm']>8.
 for fit in f['detachable_loop'].values():
  assert fit['rest_overlap_mm3']<.001 and fit['rigid_rest_overlap_mm3']<.001
  assert .001<fit['nominal_spring_preload_overlap_mm3']<1.
  assert fit['radial_preload_float_proof']['0.5']['rigid_overlap_mm3']>1.
  assert all(p['nominal_spring_overlap_mm3']>.005 for p in fit['radial_preload_float_proof'].values() if p['rigid_overlap_mm3']<.001)
  assert max(fit['released_slide_mm3'].values())<.001 and max(fit['released_turn_mm3'].values())<.001
  assert min(fit['radial_capture_mm3'],fit['upward_hard_stop_mm3'],fit['locked_downward_capture_without_latch_mm3'],fit['left_turn_end_stop_mm3'])>1.
  assert fit['reverse_catch_mm3']['2.0']>.1 and fit['left_locking_turn_deg']==12. and fit['cam_draw_mm']==.6
  assert max(fit['keycap_and_battery_turn_path_mm3'].values())<.001 and max(fit['keycap_and_battery_slide_path_mm3'].values())<.001
  assert max(fit['outward_removal_after_downward_slide_mm3'].values())<.001
 q=f['loop_mount_coupon'];assert q['rest_overlap_mm3']<.001 and max(q['released_turn_mm3'].values())<.001 and max(q['released_slide_mm3'].values())<.001 and q['upward_hard_stop_mm3']>1. and q['locked_downward_capture_without_latch_mm3']>.5
 assert set(f['bare_wand'])=={'left','right'}
 assert all(p['mount_material_outside_original_surface_mm3']<.001 and p['lost_original_raised_helix_mm3']<.01 and p['rear_mount_band_outside_0_01mm_surface_tolerance_mm3']<.001 and not p['protruding_stem_mounts'] for p in f['bare_wand'].values())
 assert len(f['recessed_pocket_floor_material_mm3'])==2 and min(f['recessed_pocket_floor_material_mm3'].values())>.09
 assert m['removable_loop']['stem_mount_type'].startswith('recessed keyhole')
 assert len(m['parts'])==18 and m['removable_loop']['release_slide_mm']==4.
 assert m['removable_loop']['attach_vector']==[0,0,1] and m['removable_loop']['release_vector']==[0,0,-1]
 assert m['removable_loop']['twist_deg']==12. and m['removable_loop']['cam_rise_mm']==.6 and m['removable_loop']['unlock_before_lowering']
 slice_results=json.loads((HERE/'exports/slice-results.json').read_text())
 assert set(slice_results)==set(PROJECTS) and all(v['return_code']==0 and v['warnings']==[] for v in slice_results.values())
 for n,names in PROJECTS.items():assert r['projects'][n]==inspect(ROOT/'magic-wand-3d-models'/n,names)
 assert (HERE/'preview/../../../../../docs/lib/three-0.185.1/three.module.min.js').resolve().is_file()
 print('Print V18 matching direct seated handles, slimmer grip, preserved helix, both hands, 18 meshes and seven Bambu projects match')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--record-new',type=Path);p.add_argument('--check',action='store_true');a=p.parse_args();record(a.record_new) if a.record_new else check()
