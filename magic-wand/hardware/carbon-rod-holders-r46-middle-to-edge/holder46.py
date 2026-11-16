"""R46 rounded middle-to-edge finger-rest braces, built on the frozen R45 carrier."""
import hashlib
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parent
R45=HERE.parent/'carbon-rod-holders-r45-open-keyways'
sys.path.insert(0,str(R45))
from holder45 import inherited
from standing45 import overlap

BASE=R45/'exports/key-holder-only'
d=inherited.d

def union(shapes):
    return mf.Manifold.batch_boolean(list(shapes),mf.OpType.Add)

def mesh(path):
    raw=trimesh.load_mesh(path)
    return mf.Manifold(mf.Mesh64(raw.vertices,np.asarray(raw.faces,np.uint64)))

def run(points,radii):
    ends=[mf.Manifold.sphere(r,24).translate(p) for p,r in zip(points,radii)]
    return union([mf.Manifold.batch_hull([a,b]) for a,b in zip(ends,ends[1:])])

def write_mesh(out,name,shape):
    f=out/(name+'.stl');m=shape.to_mesh()
    trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False).export(f)
    return {'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'volume_mm3':shape.volume()}

def design(out):
    out.mkdir(exist_ok=True,parents=True)
    body=mesh(BASE/'R45-Key-Carrier-assembly.stl')
    _,fixed,ribs=d._base_geometry();rests=d.finger_rests()
    routes={**inherited.routes()[0][d.CARRIER],**inherited.full.precision_support_spaces()}
    poses={name:list(item.poses()) if hasattr(item,'poses') else [item] for name,item in routes.items()}
    frame=np.array(json.loads((BASE/'frame.json').read_text())['print_to_assembly'])
    inv=np.linalg.inv(frame)[:3]
    additions=[];records={}
    for side,sign in [('L',-1),('R',1)]:
        spine=abs(d.finger_rest_paths()[side]['spine'][0][0])
        # Ethan asked for “more connections from the middle to the edge”.
        # The left deck return lands inward of the socket dogleg and window.
        # The right reuses its original deck landing. The right and
        # left existing edge rails differ in width around their sockets.
        outer=20.1 if side=='R' else 22.1
        for label,stations,radii,targets in [
            ('cross brace',[(spine,9.95,1.38),(spine+1.7,7.2,1.45),
                (outer-1.25,3.45,1.47),(outer,.8,1.51)], [1.08,1.13,1.13,1.2],
                {'middle':rests[side]['shape'],'edge':ribs[side+'1'],'middle row':ribs[side+'2']}),
            ('deck return',[(spine,9.95,1.40),(spine-1.3,12.1,2.85),(11.7,16.,5.62),
                (8.7,19.55,7.95),(8.3,20.6,8.52)], [1.10,1.20,1.25,1.38,1.45],
                {'middle':rests[side]['shape'],'base':fixed})]:
            if side=='R' and label=='deck return':
                # Broaden the existing right riser into its proven inner frame land.
                stations=[(spine,9.95,1.40),(14.9,11.75,3.05),(13.7,14.0,5.45),
                          (12.3,16.7,8.12),(12.05,17.25,8.65)]
            pts=[(sign*x,y,z) for x,y,z in stations];raw=run(pts,radii)
            cuts=[];bb=raw.bounding_box()
            for name,all_poses in poses.items():
                for pose in all_poses:
                    if overlap(bb,pose.bounding_box()):
                        hit=raw^pose
                        if hit.volume()>1e-8:cuts.append(hit)
            # Clip the added shape against the complete swept source
            # envelopes. Existing joints stay fixed.
            blocked=union(cuts) if cuts else mf.Manifold()
            pieces=[p for p in (raw-blocked).decompose() if p.volume()>1.e-6]
            joined=[p for p in pieces if all((p^ref^body).volume()>.1 for ref in targets.values())]
            assert len(joined)==1,(side,label,[(p.volume(),p.bounding_box()) for p in pieces])
            safe=joined[0]
            bonds={n:(safe ^ ref ^ body) for n,ref in targets.items()}
            key=side+' '+label
            records[key]={'stations':pts,'radii':radii,'raw_mm3':raw.volume(),
                'cut_mm3':raw.volume()-safe.volume(),'components':[(p.volume(),p.bounding_box()) for p in pieces],
                'bonds':{n:s.volume() for n,s in bonds.items()},'new_mm3':(safe-body).volume()}
            print(key,records[key],flush=True)
            additions.append(safe)
            records[key]['witness']=write_mesh(out,'R46-'+key.replace(' ','-'),safe.transform(inv))
            records[key]['joint_witnesses']={}
            for n,s in bonds.items():
                if s.volume()>.00001:records[key]['joint_witnesses'][n]=write_mesh(out,'R46-'+(key+'-'+n).replace(' ','-')+'-bond',s.transform(inv))
    members=union(additions);new=members-body
    hits={name:max([0.]+[(new^v).volume() for v in all_poses if overlap(new.bounding_box(),v.bounding_box())]) for name,all_poses in poses.items()}
    assert max(hits.values())<1.e-5,hits
    write_mesh(out,'R46-added-braces',new.transform(inv))
    full=(body+members).simplify(.000005)
    write_mesh(out,'R46-Key-Carrier-assembly',full)
    write_mesh(out,'R46-Key-Carrier',full.transform(inv))
    report={'records':records,'added_mm3':new.volume(),'route_max_added_intrusion_mm3':hits}
    (out/'r46-braces.json').write_text(json.dumps(report,indent=2))
    return full,report

if __name__=='__main__':design(Path(sys.argv[1]))
