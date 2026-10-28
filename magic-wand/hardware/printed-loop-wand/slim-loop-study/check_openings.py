#!/usr/bin/env python3
"""Check that sliced bead paths leave the centres of the new slots open."""
import argparse, importlib.util, json, sys, zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
cad=load('slim_slot_geometry',HERE/'wand_cad.py')
check=load('slim_slot_path_checker',HERE.parent/'shard-tube-r2/check_sliced_paths.py')
def main(projects,manifests,out):
 results={}
 for name in ('petal','leaf'):
  mpath=manifests/(name+'-manifest.json');m=json.loads(mpath.read_text());project=projects/('Slim-Loop-'+name+'-one-left-light.3mf')
  with zipfile.ZipFile(project) as z:
   objects,offset,config=check.objects(z,m,mpath)
   data,features,_=check.extrusion_points(z.read('Metadata/plate_1.gcode').decode(),.5,float(config.get('line_width','.42')),float(config.get('layer_height','.2')))
  obj=next(o for o in objects if o['name']=='Removable_Finger_Loop');local=check.points(data[:,:3]+offset,np.linalg.inv(obj['build']))
  _,path,dist=cad.sweep(cad.SPECS[name]['width'],cad.SPECS[name]['height'])
  # Conservative slot cores: smaller than the CAD cut to leave room for
  # extrusion width and normal slicer boundary rounding.
  cores=cad.slot_shapes(path,dist,cad.SPECS[name]['slot_count'],radius=.25,extent=.8);transform=np.linalg.inv(obj['print_to_assembly'])
  checks=[]
  for core in cores:
   region=core.transform(transform[:3,:]);bounds=np.asarray(region.bounding_box());lo,hi=bounds[:3],bounds[3:]
   nearby=int(np.count_nonzero(np.all(local>=lo-3.,axis=1)&np.all(local<=hi+3.,axis=1)))
   assert nearby>10,(name,'no neighbouring extrusion around the slot',nearby)
   result=check.inspect_region(region,local,data[:,3],data[:,4],data[:,5].astype(np.int16),features,obj['print_to_assembly']);result['nearby_samples']=nearby;checks.append(result)
  assert all(not c['violations'] for c in checks),(name,checks)
  results[name]={'slot_core_checks':checks,'project_sha256':check.sha(project),'physical_fit_verified':False}
  print(name,'slot cores passed',flush=True)
 out.write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--projects',type=Path,required=True);p.add_argument('--manifests',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.projects,a.manifests,a.out)
