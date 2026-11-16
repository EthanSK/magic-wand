"""Footprint context for the short no-anchor native strokes in the selected archive."""
from pathlib import Path
import json,sys
import numpy as np
from holder46 import inherited
from native_order45 import map_moves
from plate45 import digest
import single44
def inspect(a):
    p=a.parent;c=inherited.common.load_checker().audit;q=c.q
    d,f,_,_,off,_,gcode,_=c.read_project(a);lines,seq,feed,fan=map_moves(q,gcode,len(d))
    xy=d[:,:2]+off[:2]-np.array(json.load(open(p/'frame.json'))['bed_translation'][:2])
    o=single44.previous.owners(a);normal=inherited.common.model_mask(np.array(f)[d[:,5].astype(int)])
    carrier=normal&(d[:,6]==o['Key_Carrier']);helper=normal&np.isin(d[:,6],[v for n,v in o.items() if n not in ('Key_Carrier','Release_tabs')])
    roof=json.load(open(p/'roof-strokes.json'));assert roof['archive_sha256']==digest(a)
    rows=[]
    for r in roof['sequence_gaps']:
     if r['classification']=='short straight two-ended bridge' or r['classification']=='beyond screened anchored span':continue
     if r['mm']<1. and (r['before'] or r['after']):continue
     z=r['z'];lo=r['first_gcode_line'];hi=r['last_gcode_line'];pts=np.array(r['sampled_path_xy'])
     inside=np.all((xy>=pts.min(0)-.9)&(xy<=pts.max(0)+.9),axis=1)
     idx=np.flatnonzero(carrier&inside&(lines>=lo)&(lines<=hi))
     start=np.argmin(np.linalg.norm(xy[idx]-pts[0],axis=1));end=np.argmin(np.linalg.norm(xy[idx]-pts[-1],axis=1))
     if start>=end:continue
     idx=idx[start:end+1];length=r['mm'];shape=c.start_audit.bead_footprints(q,xy[idx],d[idx,3])
     masks={'immediately_previous_carrier':carrier&(abs(d[:,7]-(z-.2))<.001),
           'earlier_helper_across_gap':helper&(abs(d[:,7]-(z-.4))<.001),
           'earlier_same_layer_carrier':carrier&(abs(d[:,7]-z)<.001)&(lines<lo),
           'later_same_layer_carrier':carrier&(abs(d[:,7]-z)<.001)&(lines>hi),
           'following_layer_carrier':carrier&(abs(d[:,7]-(z+.2))<.001)}
     areas={}
     for name,take in masks.items():
      take=take&inside
      prev=c.start_audit.bead_footprints(q,xy[take],d[take,3]) if take.any() else q.CrossSection()
      areas[name]=(prev^shape).area()
     rows.append(dict(layer=z,gcode_lines=[lo,hi],path_mm=length,anchored_before=r['before'],anchored_after=r['after'],
         width_range_mm=[float(d[idx,3].min()),float(d[idx,3].max())],footprint_mm2=shape.area(),overlap_mm2=areas))
     print(z,lo,length,areas,flush=True)
    (p/'roof-residual-context.json').write_text(json.dumps(dict(archive_sha256=digest(a),rows=rows,
        note='Overlap is measured against inscribed actual native bead footprints. Later material can capture a short stroke but does not back it when printed. Earlier same-layer contact area does not establish ancestry.'),indent=2))

if __name__=='__main__':
    inspect(Path(sys.argv[1]).resolve())
