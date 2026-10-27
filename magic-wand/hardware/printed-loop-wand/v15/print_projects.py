"""Portable Print V15 candidate project recipe. Output directories must be new."""
from pathlib import Path
import importlib.util,json,zipfile,xml.etree.ElementTree as ET,struct,uuid,sys,numpy as np,argparse,shutil,subprocess
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('print_v15_cad',HERE/'wand_cad.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
m=json.loads((HERE/'exports/manifest.json').read_text());parts={p['name']:p for p in m['parts']}
config=json.loads((HERE/'print-settings/project.json').read_text())
changed={k:config[k] for k in ['layer_height','wall_loops','sparse_infill_density','support_threshold_angle','support_on_build_plate_only','brim_type','brim_width','brim_object_gap','enable_support','support_type']}
diffs=config.get('different_settings_to_system',['','','']);diffs[0]=';'.join(sorted(set(filter(None,diffs[0].split(';')))|set(changed)));config['different_settings_to_system']=diffs
ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',ns);tag=lambda n:'{'+ns+'}'+n

def cam_blocker(z):
 r=c.loop_mount_radius(z)
 return c.loop_motion_void(z,.35)+c.box(-10.,10.,-r+1.9,-r+6.2,z-8.,z+8.)+c.loop_slide_clearance(z)

def blocker(name):
 if name=='Button_Mount_Coupon':return c.cyl(3.4,-8.,3.)
 if name in ['Removable_Finger_Loop','Loop_Foot_Coupon']:
  shadows=[]
  for a in c.loop_air_ports():
   center=np.array(a['center']);u=np.array(a['tangent']);v=np.array(a['inward']);normal=np.array([1.,0.,0.])
   profile=c.CrossSection([[(-9.5,0),(-6.5,-2.8),(6.5,-2.8),(9.5,0),(6.5,2.8),(-6.5,2.8)]]).offset(2.,c.mf.JoinType.Round)
   shadows.append(c.Manifold.extrude(profile,32.).transform(np.column_stack([u,v,normal,center-16*normal])))
  return c.union([c.hollow_loop()[1],c.loop_vents(),c.loop_side_windows()]+shadows)
 if name=='Loop_Socket_Coupon':
  z=c.LOOP_MOUNTS[1]
  return cam_blocker(z)
 if name.startswith('Handle_'):
  right=name.endswith('Right')
  # Exclude support landing sources above the slots, not only their mouths.
  shadows=[c.cyl(max(3.,p['width_mm']/2),p['z']-p['height_mm']/2,c.HANDLE_END+2.).translate((p['outer_radius']*np.sin(np.radians(p['angle'])),p['outer_radius']*np.cos(np.radians(p['angle'])),0)) for p in c.slot_locations('grip')]
  tracks=[cam_blocker(z) for z in c.LOOP_MOUNTS]
  return c.union(shadows+tracks+[c.body_slots('grip'),c.cyl(13.,11.8,140.),c.cyl(5.45,3.,177.),c.bottom_socket()]+[c.branch(-a if right else a,z,4.3) for _,a,z in c.HAND_BUTTONS])
 if name.startswith('Lower_Shaft'):return c.union([c.female_at(140. if name.endswith('Existing_Handle') else c.HANDLE_END),c.cyl(5.45,139.,c.MID+15.)])
 if name=='Upper_Shaft':return c.union([c.slim_female_at(c.MID),c.cyl(5.45,c.MID-1,c.TOP+15.)])
 if name=='Sense_Head_Base':return c.union([c.slim_female_at(c.TOP),c.head_cavity(),c.cyl(5.45,c.TOP-1,c.BOARD0+14.)])
 return None

def make(names,centers,dest):
 model=ET.Element(tag('model'),unit='millimeter',attrib={'xml:lang':'en-US'})
 ET.SubElement(model,tag('metadata'),name='Application').text='BambuStudio-02.08.04.57'
 resources=ET.SubElement(model,tag('resources'));build=ET.SubElement(model,tag('build'));cfg=ET.Element('config');ident=0;rootids=[]
 def mesh_object(verts,faces,name):
  nonlocal ident
  ident+=1;objid=ident;o=ET.SubElement(resources,tag('object'),id=str(objid),type='model',name=name);mesh=ET.SubElement(o,tag('mesh'));vs=ET.SubElement(mesh,tag('vertices'));ts=ET.SubElement(mesh,tag('triangles'))
  for v in verts:ET.SubElement(vs,tag('vertex'),**{a:format(float(x),'.7g') for a,x in zip('xyz',v)})
  for f in faces:ET.SubElement(ts,tag('triangle'),v1=str(int(f[0])),v2=str(int(f[1])),v3=str(int(f[2])))
  return objid
 for k,(name,center) in enumerate(zip(names,centers)):
  p=parts[name];ta=np.asarray(p['print_to_assembly']);it=np.linalg.inv(ta)
  def print_points(v):
   v=np.asarray(v);return v@it[:3,:3].T+it[:3,3]
  child=mesh_object(print_points(p['assembly_vertices']),p['assembly_faces'],name)
  children=[(child,'normal_part',name)]
  if name=='Removable_Finger_Loop':
   # Flat loop faces sit directly on the bed. Support only its two mounting
   # roots, keeping automatic support/brim out of the broad-face apertures.
   enforce=c.union([c.box(-10.,11.,-24.,-6.,29.,49.),c.box(-10.,11.,-38.,-22.,23.,30.),c.box(-10.,11.,-32.,-6.,114.,138.)]);ee=enforce.to_mesh()
   eid=mesh_object(print_points(np.asarray(ee.vert_properties)[:,:3]),np.asarray(ee.tri_verts),'Support mounting roots only');children.append((eid,'support_enforcer','Support mounting roots only'))
  block=blocker(name)
  if block is not None:
   mm=block.to_mesh();bid=mesh_object(print_points(np.asarray(mm.vert_properties)[:,:3]),np.asarray(mm.tri_verts),'NO SUPPORT inside wire passages');children.append((bid,'support_blocker','NO SUPPORT inside wire passages'))
  ident+=1;rootid=ident;rootids.append(rootid);parent=ET.SubElement(resources,tag('object'),id=str(rootid),type='model',name=name);comps=ET.SubElement(parent,tag('components'))
  settings=ET.SubElement(cfg,'object',id=str(rootid));ET.SubElement(settings,'metadata',key='name',value=name);ET.SubElement(settings,'metadata',key='extruder',value='1')
  if name.startswith('Handle_') or name in ['Button_Mount_Coupon','Loop_Foot_Coupon','Loop_Socket_Coupon']:ET.SubElement(settings,'metadata',key='support_type',value='normal(auto)')
  if name=='Removable_Finger_Loop':
   ET.SubElement(settings,'metadata',key='support_type',value='normal(manual)')
   ET.SubElement(settings,'metadata',key='brim_type',value='no_brim')
  if not name.startswith('Handle_') and name not in ['Sense_Sliding_Cover','Button_Mount_Coupon','Removable_Finger_Loop','Loop_Foot_Coupon','Loop_Socket_Coupon']:ET.SubElement(settings,'metadata',key='enable_support',value='0')
  for cid,sub,n in children:
   ET.SubElement(comps,tag('component'),objectid=str(cid));part=ET.SubElement(settings,'part',id=str(cid),subtype=sub,uuid=str(uuid.uuid4()));ET.SubElement(part,'metadata',key='name',value=n);ET.SubElement(part,'metadata',key='matrix',value='1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')
  ET.SubElement(build,tag('item'),objectid=str(rootid),transform=f'1 0 0 0 1 0 0 0 1 {center[0]} {center[1]} 0',printable='1')
 plate=ET.SubElement(cfg,'plate');ET.SubElement(plate,'metadata',key='plater_id',value='1');ET.SubElement(plate,'metadata',key='plater_name',value='Print V15 candidate - 410 mm helix wand - BOTH handed handles')
 for rootid in rootids:
  ins=ET.SubElement(plate,'model_instance');ET.SubElement(ins,'metadata',key='object_id',value=str(rootid));ET.SubElement(ins,'metadata',key='instance_id',value='0');ET.SubElement(ins,'metadata',key='identify_id',value=str(rootid))
 ET.SubElement(cfg,'assemble')
 types='''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>'''
 rels='''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
 with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',rels);z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True));z.writestr('Metadata/model_settings.config',ET.tostring(cfg,encoding='utf-8',xml_declaration=True));z.writestr('Metadata/project_settings.config',json.dumps(config,indent=2))
 print(dest)
 return dict(zip([f'{i}:{n}' for i,n in enumerate(names)],centers))

def build(out, slice_projects=False, bambu=None, only_project=None):
 out.mkdir(parents=True,exist_ok=False)
 upper=['Lower_Shaft_Existing_Handle','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover']
 full=['Handle_Left','Handle_Right','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Top_Slide_Plate']*3+['Removable_Finger_Loop']
 left=['Handle_Left','Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Top_Slide_Plate']*3+['Removable_Finger_Loop']
 inputs=[('complete-layout.3mf','Print-15-complete-left-right-top-slide-410mm.3mf',full,[(35,55),(80,55),(125,55),(160,55),(215,55),(207,100),(156,100),(231,160),(25,100),(55,100),(85,100),(75,190)]),
         ('one-left-layout.3mf','Print-15-one-left-wand-410mm.3mf',left,[(35,55),(125,55),(160,55),(215,55),(207,100),(156,100),(231,160),(25,100),(55,100),(85,100),(75,190)]),
         ('upper-layout.3mf','Print-15-upper-only-helix-410mm.3mf',upper,[(55,65),(95,65),(140,65),(190,65)]),
         ('button-layout.3mf','Print-15-top-slide-button-fit-test.3mf',['Choc_Top_Slide_Plate','Button_Mount_Coupon'],[(100,110),(145,110)]),
         ('loop-layout.3mf','Print-15-detachable-loop-fit-test.3mf',['Loop_Socket_Coupon','Loop_Foot_Coupon'],[(100,110),(145,110)]),
         ('joint-layout.3mf','Print-15-slim-bayonet-fit-test.3mf',['Fit_Test_Male','Fit_Test_Female'],[(100,110),(145,110)])]
 layout={}
 for source,final,part_names,positions in inputs:
  if only_project and final!=only_project:continue
  layout[final]=make(part_names,positions,out/(source if slice_projects else final))
  if slice_projects:
   slice_dir=out/(Path(final).stem+'-slice');slice_dir.mkdir()
   exe=bambu or shutil.which('BambuStudio') or '/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
   command=[exe,'--datadir',str(slice_dir/'bambu-data'),'--debug','2','--load-settings',str(HERE/'print-settings/machine.json')+';'+str(HERE/'print-settings/process.json'),'--load-filaments',str(HERE/'print-settings/filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf',final,'--outputdir',str(slice_dir),str(out/source)]
   with (out/(final+'.slice.log')).open('x') as log:subprocess.run(command,cwd=slice_dir,stdout=log,stderr=subprocess.STDOUT,check=True)
   result=json.loads((slice_dir/'result.json').read_text())
   assert result['return_code']==0 and all(not p.get('warning_message','') for p in result['sliced_plates']),result
   # Persist prepared process overrides when the CLI resolves a named base preset.
   sliced=slice_dir/final
   with zipfile.ZipFile(sliced) as z:
    entries={i.filename:z.read(i.filename) for i in z.infolist()};settings=json.loads(entries['Metadata/project_settings.config'])
   diff=settings.get('different_settings_to_system',['','','']);diff[0]=';'.join(sorted(set(filter(None,diff[0].split(';')))|set(changed)));settings['different_settings_to_system']=diff
   entries['Metadata/project_settings.config']=json.dumps(settings,indent=2).encode()
   # Keep the raw CLI artifact and create a complete new copy with registered settings.
   clean=out/(Path(final).stem+'-prepared.3mf')
   with zipfile.ZipFile(clean,'x',zipfile.ZIP_DEFLATED) as z:
    for name,data in entries.items():z.writestr(name,data)
   with zipfile.ZipFile(clean) as z:assert z.testzip() is None
 with (out/'layout.json').open('x') as f:json.dump(layout,f,indent=2)

if __name__=='__main__':
 ap=argparse.ArgumentParser(description='Generate Print V15 candidate layouts in a new directory; optionally slice with Bambu Studio.')
 ap.add_argument('--only-project',help='Generate one named project instead of all six');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--slice',action='store_true');ap.add_argument('--bambu');args=ap.parse_args();build(args.out.resolve(),args.slice,args.bambu,args.only_project)
