#!/usr/bin/env python3
"""Compare exactly one complete wand per archive using sliced filament extrusion.
The caller supplies single-wand projects. No physical weight measurement is implied.
"""
from pathlib import Path
import argparse,hashlib,json,math,re,zipfile,collections,xml.etree.ElementTree as E

def inspect(path):
 with zipfile.ZipFile(path) as z:
  cfg=json.loads(z.read('Metadata/project_settings.config')) if 'Metadata/project_settings.config' in z.namelist() else {}
  code=z.read('Metadata/plate_1.gcode').decode()
  model=E.fromstring(z.read('3D/3dmodel.model'));ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
  count=len(model.findall('m:build/m:item',ns))
 density=float(re.search(r'; filament_density: ([0-9.]+)',code)[1]);diam=float(re.search(r'; filament_diameter: ([0-9.]+)',code)[1]);factor=math.pi*(diam/2)**2*density/1000
 total=float(re.search(r'; total filament weight \[g\] : ([0-9.]+)',code)[1]);features=collections.Counter();feat='';relative=True;prev_e=0.;xyz=[0.,0.,0.]
 for line in code.splitlines():
  if line.startswith('; FEATURE:'):feat=line[11:].strip();continue
  t=line.split(';')[0].split()
  if not t:continue
  if t[0]=='M83':relative=True
  if t[0]=='M82':relative=False
  if t[0]=='G92':
   for v in t[1:]:
    if v.startswith('E'):prev_e=float(v[1:])
   continue
  if t[0] not in ('G0','G1','G2','G3'):continue
  v={x[0]:float(x[1:]) for x in t[1:] if len(x)>1 and x[0] in 'XYZEIJ'}
  nxt=[v.get(k,xyz[i]) for i,k in enumerate('XYZ')];de=v.get('E',0.) if relative else v.get('E',prev_e)-prev_e
  if not relative:prev_e=v.get('E',prev_e)
  moving=any(abs(a-b)>.0001 for a,b in zip(nxt,xyz)) or (t[0] in ('G2','G3') and ('I' in v or 'J' in v))
  if moving and de>0 and feat and feat!='Custom':features[feat]+=de*factor
  xyz=nxt
 excluded=lambda f:f.startswith('Support') or f in ('Brim','Skirt','Flush','Wipe tower','Prime tower')
 model_g=sum(g for f,g in features.items() if not excluded(f));removable_g=sum(g for f,g in features.items() if excluded(f));summed=model_g+removable_g
 assert abs(summed-total)<max(.1,total*.01),(path.name,'extrusion accounting differs',summed,total)
 return {'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'build_instances':count,'printed_parts_g':round(model_g,3),'supports_and_brim_g':round(removable_g,3),'total_slicer_g':total,'accounted_g':round(summed,3),'startup_and_rounding_g':round(total-summed,3),'features_g':dict(features),'settings':{k:cfg.get(k) for k in ('printer_model','filament_type','layer_height','wall_loops','sparse_infill_density','support_type')}}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--v1',type=Path,required=True);ap.add_argument('--v2',type=Path,required=True);ap.add_argument('--current',type=Path,required=True);ap.add_argument('--v1-original',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 report={'scope':'Exactly one complete wand per row, excluding electronics, battery, bought switches, sockets and caps. PETG model mass derived from positive extruding moves, excluding support/brim and start/end custom code. Slicer estimates; no weighed print.','matched_settings':'P1S 0.4 mm PETG, 0.2 mm layers, 3 walls, 20% infill; normal supports on grips; other parts retain their geometry-specific support strategy.','versions':{'V1_mug_90_72_helix':inspect(a.v1),'V2_left_diamond':inspect(a.v2),'V6_left_raised_side_buttons':inspect(a.current)},'physical_mass_measured':False}
 assert [report['versions'][k]['build_instances'] for k in report['versions']]==[4,13,10], 'Expected one complete wand in every row'
 if a.v1_original:report['original_V1_project_settings']=inspect(a.v1_original)
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:{q:v[q] for q in ('printed_parts_g','supports_and_brim_g','total_slicer_g','build_instances')} for k,v in report['versions'].items()},indent=2))
