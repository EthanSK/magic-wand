#!/usr/bin/env python3
"""Check delivered meshes, board release and actual extrusion clearances."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,zipfile,xml.etree.ElementTree as ET
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent

def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m

def verify(exports,archive,out):
 c=load('long_rod_checks',HERE/'wand_cad.py');paths=load('long_rod_paths',HERE.parent/'continuous-two-wide-v19/inspect_sliced_paths.py')
 m=json.loads((exports/'manifest.json').read_text());parts={}
 assert hashlib.sha256((HERE/'wand_cad.py').read_bytes()).hexdigest()==m['source_sha256']
 for name,digest in m['dependency_sha256'].items():assert hashlib.sha256((HERE.parent/name).read_bytes()).hexdigest()==digest
 for p in m['parts']:
  f=exports/p['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==p['sha256']
  mesh=trimesh.load_mesh(f,process=True);assert mesh.is_watertight and mesh.is_winding_consistent
  mesh.apply_transform(p['print_to_assembly']);parts[p['name']]=c.v.b.closed_mesh(mesh.vertices,mesh.faces,p['name'])
 # STL float32 coordinates near 500 mm round by about 0.00003 mm.
 # A 0.001 mm seated-clip subtraction margin removes that Boolean boundary
 # film; the designed release clearance remains 0.06 mm in the CAD source.
 geometry=c.check(parts);upper=parts['Upper_Rod_Integral_Gyro_Mount'];clip=c.v.board_release_clip();raw=clip.refine_to_length(.7).to_mesh();rigid=upper-clip.minkowski_sum(c.mf.Manifold.sphere(.001,8)).translate((0,0,c.HEAD_SHIFT));hits=[]
 for depth in np.linspace(0,1.3,8):
  vv=np.array(raw.vert_properties[:,:3],dtype=np.float32);vv[:,2]-=depth*np.maximum(0,1-(vv[:,0]/10.)**2)**2;vv[:,2]+=c.HEAD_SHIFT
  moved=c.mf.Manifold(c.mf.Mesh(vv,np.asarray(raw.tri_verts,dtype=np.uint32)));hits.append(abs((rigid^moved).volume()))
 assert max(hits)<.004,('release clip interference',hits)
 islands=[]
 for z in np.arange(445.2,500.,.2):
  prior=upper.slice(float(z-.2)).offset(.25)
  for section in upper.slice(float(z)).decompose():
   if section.area()>.015 and (section^prior).area()<.002:islands.append(round(float(z),3))
 assert not islands,('unsupported sensor starts',islands)
 points,features=paths.samples(archive);p=next(p for p in m['parts']if p['name']=='Upper_Rod_Integral_Gyro_Mount');t=np.asarray(p['print_to_assembly'])
 xyz=(points+[0.,2.,0.]-[185.,110.,0.])@t[:3,:3].T+t[:3,3];x,y,z=xyz.T;z=z-c.HEAD_SHIFT
 masks={'board':(abs(x)<8.6)&(y>-5.2)&(y<-4.2)&(z>376.3)&(z<396.7),
 'solder':(abs(x)<5.1)&(y>-11.)&(y<-5.9)&(z>379.5)&(z<393.5),
 'usb':(abs(x)<5.4)&(y>-6.)&(y<-1.)&(z>397.6)&(z<410.7),
 'wire_exit':(x*x+(y-2.)**2<2.4**2)&(z>375.3)&(z<387.2)}
 counts={n:int(v.sum())for n,v in masks.items()};assert not any(counts.values()),counts
 nearby=int(((abs(abs(x)-10.5)<2.)&(y>-9.)&(y<-5.)&(z>381.)&(z<393.)).sum());assert nearby>100,('no nearby material tested',nearby)
 with zipfile.ZipFile(archive)as f:
  assert f.testzip()is None
  objects=ET.fromstring(f.read('Metadata/model_settings.config')).findall('object')
  assert len(objects)==3
  for obj in objects:
   settings={e.get('key'):e.get('value')for e in obj.findall('metadata')}
   assert settings['sparse_infill_density']=='100%'and settings['wall_loops']=='4',settings
  for name in f.namelist():
   if name.endswith(('.json','.config','.model','.gcode')):
    data=f.read(name);assert b'/Users/'not in data and b'/Volumes/'not in data,('private path',name)
 report={'geometry':geometry,'clip_release_overlap_mm3':max(hits),'seated_clip_numerical_margin_mm':.001,'unsupported_sensor_starts':islands,'sliced_clearance_samples':counts,'nearby_material_samples':nearby,'gcode_sampling_mm':.5,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'physical_strength_verified':False,'physical_fit_verified':False}
 out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();verify(a.exports,a.archive,a.out)
