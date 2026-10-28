#!/usr/bin/env python3
"""Reload the actual exported STLs before checking functional geometry."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('r2_cad_verification',HERE/'wand_cad.py');w=importlib.util.module_from_spec(sp);sys.modules[sp.name]=w;sp.loader.exec_module(w)

def verify(exports):
 m=json.loads((exports/'manifest.json').read_text());parts={};beds={};meshchecks={}
 for p in m['parts']:
  path=exports/p['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256'],p['name']
  mesh=trimesh.load_mesh(path,process=True);loaded=w.c.b.closed_mesh(mesh.vertices.tolist(),mesh.faces.tolist(),p['name']+' print STL');bodies=len(loaded.decompose());assert mesh.is_watertight and mesh.is_winding_consistent and bodies==1,p['name']
  t=mesh.triangles;bed=np.max(np.abs(t[:,:,2]),axis=1)<.00003;area=float(mesh.area_faces[bed].sum());beds[p['name']]=area
  first_layer_area=float(loaded.slice(.1).area())
  assert (area>.5 or(p['name']=='Sense_Open_Cradle'and first_layer_area>1.)),(p['name'],'inadequate bed start',area,first_layer_area)
  meshchecks[p['name']]={'bodies':bodies,'watertight':True,'bed_contact_mm2':area,'print_height_mm':float(mesh.extents[2]),'first_layer_section_mm2':first_layer_area,'manual_low_back_support':p['name']=='Sense_Open_Cradle'}
  mesh.apply_transform(np.asarray(p['print_to_assembly']));parts[p['name']]=w.c.b.closed_mesh(mesh.vertices.tolist(),mesh.faces.tolist(),p['name']+' exported STL')
 assert beds['Removable_Finger_Loop']>100 and beds['Switch_Fit_Test']>25 and beds['Loop_Keeper_Key']>2,beds
 hd=w.handle_module().build(w.c);controls={};handle={}
 # Override the moving handle/key with the actual reloaded exported meshes.
 hd.loop=lambda:parts['Removable_Finger_Loop']
 key_z=w.handle_module().KEY_Z
 entry_key=parts['Loop_Keeper_Key'].translate((0.,-hd.key_y+w.handle_module().KEY_SEAT_OUT,-key_z)).rotate((0.,-90.,0.)).translate((0.,hd.key_y,key_z))
 hd.key=lambda:entry_key
 for right in [False,True]:
  hand='Right'if right else'Left';stem=parts['Grip_'+hand]
  controls[hand]=w.ds.assembled_checks(w.c,stem,right)
  obstacles=[]
  for _,a,z in w.hand_buttons(right):obstacles+=list(w.ds.hardware(w.c,a,z).values())
  handle[hand]=hd.check(stem,w.c.union(obstacles),parts['Battery_Screw_Cap_Light'])
  assert handle[hand]['remove_cap_to_attach'],'Instructions and receiver/cap interference assumption changed; re-review assembly order'
  # All rails and mounts sit in the old stem envelope apart from the compact
  # approved switch seats. No permanent external mount remains on the rear.
  receiver=w.handle_module().receiver_material(w.c)
  shell_envelope=w.c.body(3.2,w.c.HANDLE_END-.2)+w.c.male_at(w.c.HANDLE_END)
  assert abs((receiver-shell_envelope).volume())<.001
  bore=(stem^w.c.cyl(5.1,61.,177.)).volume();assert abs(bore)<.001
  meshchecks['Grip_'+hand]['wire_bore_probe_mm3']=abs(bore)
 # Compare exported upper assembly with unchanged main STLs in assembly space.
 upper={}
 for name in ['Continuous_Shaft','Sense_Open_Cradle']:
  a=parts[name];b=w.reused_upper(name);difference=abs((a-b).volume())+abs((b-a).volume());assert difference<.1,(name,difference)
  upper[name]={'symmetric_geometry_difference_mm3':difference}
 # Keycap full nominal stroke against BOTH final stems and neighbours.
 capchecks={}
 for right in [False,True]:
  hand='Right'if right else'Left';stem=parts['Grip_'+hand];samples={}
  for name,a,z in w.hand_buttons(right):
   keycap=w.c.mount_local(w.c.rr(16.6,17.5,.5,4.6,9.8),a,z)
   axis=(np.sin(np.radians(a)),np.cos(np.radians(a)),0.)
   other=w.c.union([w.c.mount_local(w.c.rr(16.6,17.5,.5,4.6,9.8),aa,zz)for nn,aa,zz in w.hand_buttons(right)if nn!=name])
   overlaps=[abs(((stem+other)^keycap.translate(tuple(-d*v for v in axis))).volume())for d in np.linspace(0.,3.,13)]
   assert max(overlaps)<.001,(hand,name,max(overlaps));samples[name]=max(overlaps)
  capchecks[hand]=samples
 return {'actual_exported_stls_checked':True,'mesh_checks':meshchecks,'switches':controls,'handle':handle,'nominal_keycap_3mm_stroke_collision_mm3':capchecks,'unchanged_main_upper':upper,'physical_fit_verified':False,'strength_verified':False,'battery_product_dimensions_verified':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,default=HERE/'exports');p.add_argument('--out',type=Path,required=True);a=p.parse_args();report=verify(a.exports)
 with a.out.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print('Exported meshes, both hands, controls, full handle route, keycap stroke and unchanged upper assembly checked')
