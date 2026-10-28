#!/usr/bin/env python3
"""Slim, open loop studies using the unmodified Shard R2 attachment.

Ethan's 'outer rim' is the removable finger-loop band, not the shaft.
The older solid R2 loop remains the baseline; these are unprinted studies.
"""
import argparse, importlib.util, json, math, sys
from pathlib import Path
import numpy as np
from manifold3d import Manifold
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'shard-tube-r2'
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
r=module('slim_loop_r2',BASE/'wand_cad.py')
c=r.c
SPECS={'slim':{'width':7.6,'height':3.4,'slot_count':0},'petal':{'width':7.6,'height':3.4,'slot_count':3},'leaf':{'width':8.0,'height':3.6,'slot_count':4}}
def sweep(width,height):
 points=[list(p) for p in c.LOOP_POINTS]
 for i,z in [(0,14.),(-1,104.)]:points[i]=[z,-c.radius(z)-2.3]
 path=np.asarray(c.b.catmull_rom(points,spacing=.6),float)
 tangent=np.gradient(path,axis=0);tangent/=np.linalg.norm(tangent,axis=1,keepdims=True);tangent[0]=[0.,-1.];tangent[-1]=[0.,1.]
 normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)
 distance=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
 vertices=[]
 for point,n,d in zip(path,normal,distance):
  edge=min(d,distance[-1]-d);u=float(np.clip(edge/23.,0.,1.));fade=1.-(6*u**5-15*u**4+10*u**3)
  w=width+(9.-width)*fade;h=height+(8.-height)*fade
  vertices.extend((x-(9.-w)/2.,point[1]+s*n[1],point[0]+s*n[0]) for s,x in c.rounded_band_section(w,h,1.2))
 k=len(c.rounded_band_section(width,height,1.2));tri=[]
 for i in range(len(path)-1):
  a=i*k;b=(i+1)*k
  for j in range(k):
   j1=(j+1)%k;tri.extend([(a+j,a+j1,b+j1),(a+j,b+j1,b+j)])
 last=k*(len(path)-1);tri += [(0,j+1,j)for j in range(1,k-1)]+[(last,last+j,last+j+1)for j in range(1,k-1)]
 return c.b.closed_mesh(vertices,tri,'slim swept finger-loop band'),path,distance

def slot_shapes(path,dist,count,radius=1.,extent=5.):
 holes=[]
 if count:
  # Rounded slots pass through the skin-facing side, on the straight outer
  # portion, well clear of the hooks and key. Preserve solid material above
  # and below every opening; geometry is not a strength guarantee.
  for d in np.linspace(48.,dist[-1]-48.,count):
   a=np.array([np.interp(d-3.,dist,path[:,0]),np.interp(d-3.,dist,path[:,1])]);b=np.array([np.interp(d+3.,dist,path[:,0]),np.interp(d+3.,dist,path[:,1])])
   tangent=(b-a)/np.linalg.norm(b-a);normal=np.array([-tangent[1],tangent[0]])
   def sphere(p,offset):return Manifold.sphere(radius,24).translate((-.5,float(p[1]+normal[1]*offset),float(p[0]+normal[0]*offset)))
   # Through the contact surface, preserving side rails across the 7.6 mm width.
   hole=Manifold.batch_hull([sphere(p,offset) for p in (a,b) for offset in (-extent,extent)]);holes.append(hole)
 return holes

def make(key):
 spec=SPECS[key];hd=r.handle_module().HandleDesign(c);band,path,dist=sweep(spec['width'],spec['height'])
 holes=slot_shapes(path,dist,spec['slot_count'])
 if holes:
  band-=c.union(holes)
 roots=[hd.shoulder(z)+hd.neck(z)+hd.wings(z) for z in (14.,104.)]
 loop=(c.union([band,hd.upper_key_ear()]+roots)-hd.key_entry_hole()).as_original().simplify(.001)
 assert len(loop.decompose())==1 and loop.status().name=='NoError',(key,loop.status(),len(loop.decompose()))
 # Use the same validated interface geometry and check the full path.
 hd.loop=lambda:loop
 result={hand:hd.check(r.grip(hand=='Right'),cap=r.cp.light_cap(c)) for hand in ('Left','Right')}
 return loop,{'width_mm':spec['width'],'thickness_mm':spec['height'],'openings':spec['slot_count'],'solid_baseline_width_mm':9.,'solid_baseline_thickness_mm':4.,'opening_probe_clear_mm3':[abs((loop^h).volume()) for h in holes],'loop_volume_mm3':loop.volume(),'baseline_volume_mm3':r.handle_module().loop(c).volume(),'physical_fit_verified':False,'physical_strength_verified':False,'interfaces':result}

def main(out):
 out.mkdir(parents=True,exist_ok=False);results={}
 for name in SPECS:
  solid,checks=make(name)
  folder=out/name;folder.mkdir();record=r.export_part('Removable_Finger_Loop',solid,folder)
  results[name]={'checks':checks,'part':record}
  print(name,checks['loop_volume_mm3'],checks['baseline_volume_mm3'],flush=True)
 (out/'manifest.json').write_text(json.dumps({'base_commit':'c945772','variants':results},separators=(',',':'))+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.out)
