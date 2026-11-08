# Audit the exact Studio export against reviewed R18 meshes and label-specific XY bounds.
import sys,json,zipfile,xml.etree.ElementTree as E,re,argparse,hashlib
from pathlib import Path
import numpy as np
part=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=part/'exports/R18-SENT-A1-mini-PETG.gcode.3mf');p.add_argument('--output',type=Path,required=True);args=p.parse_args()
sys.path.insert(0,str(part))
import slice18 as s
out=args.output;out.mkdir(parents=True,exist_ok=True)
gui=args.project
reviewed=s.OUT/'R18-A1-mini-PETG.gcode.3mf'
read=s.s16.read_project; reviewed_data=read(reviewed); orig_anchor=s.anchor_in_project
assert s.h.sha(reviewed)=='6e796431d061d52c2164ca99cf1ad007eab9a8cd6f654408325405938af5e4f3'
with zipfile.ZipFile(gui) as z:
 info=E.fromstring(z.read('Metadata/slice_info.config'));labels={o.get('identify_id'):o.get('name') for o in info.iter('object')};text=z.read('Metadata/plate_1.gcode').decode();cfg=json.loads(z.read('Metadata/project_settings.config'))
assert set(labels.values())==set(s.h.PLATE) and all(o.get('skipped')=='false' for o in info.iter('object'))
assert cfg['z_hop']==['0.6'] and cfg['z_hop_types']==['Normal Lift']
# Verify each GUI label occupies its reviewed part's real footprint, before mapping names.
bounds={n:[np.array([np.inf,np.inf]),np.array([-np.inf,-np.inf])] for n in s.h.PLATE};x=y=0.;label=None
word=re.compile(r'([XYE])(-?\d*\.?\d+)')
for line in text.splitlines():
 if line.startswith('; start printing object, unique label id:'):label=labels[line.rsplit(':',1)[1].strip()];continue
 if line.startswith('; stop printing object'):label=None;continue
 if line.startswith(('G0 ','G1 ','G2 ','G3 ')):
  w={a:float(b) for a,b in word.findall(line.split(';')[0])};nx,ny=w.get('X',x),w.get('Y',y)
  if label and w.get('E',0)>0 and ('X' in w or 'Y' in w):
   bounds[label][0]=np.minimum(bounds[label][0],np.minimum([x,y],[nx,ny]));bounds[label][1]=np.maximum(bounds[label][1],np.maximum([x,y],[nx,ny]))
  x,y=nx,ny
expected=json.loads((s.OUT/'R18-A1-mini-PETG-print-checks.json').read_text())['plate_extents_mm']
for n,(lo,hi) in bounds.items():
 e=np.array(expected[n]);assert np.all(lo>=e[0,:2]-.5) and np.all(hi<=e[1,:2]+.5),(n,lo,hi,e)
 assert np.all(abs(lo-e[0,:2])<1.) and np.all(abs(hi-e[1,:2])<1.),(n,lo,hi,e)
config=''.join('<object id="'+i+'"><metadata key="name" value="'+n+'"/></object><model_instance><metadata key="object_id" value="'+i+'"/><metadata key="identify_id" value="'+i+'"/></model_instance>' for i,n in labels.items())
def read_gui(p):
 row=list(read(p));row[5]=reviewed_data[5];row[7]=config;return tuple(row)
s.s16.read_project=read_gui;s.anchor_in_project=lambda p,n,place:orig_anchor(reviewed,n,place)
r=s.inspect(gui,out_dir=out,tag='-gui-final')
r['geometry_expectation_archive_sha256']=s.h.sha(reviewed);r['geometry_note']='Actual GUI G-code audited against reviewed meshes and placements. GUI sliced-only export contains no source meshes; label-specific extrusion XY bounds verified separately before mapping.'
r['gui_audit_adapter_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
r['gui_gcode_label_map']=labels;r['gui_label_xy_bounds_mm']={n:[a.tolist(),b.tolist()] for n,(a,b) in bounds.items()}
(out/'slice-clearances-gui-final.json').write_text(json.dumps(r,indent=2)+'\n')
print('GUI_FINAL_AUDIT_PASSED',flush=True)
