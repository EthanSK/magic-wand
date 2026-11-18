"""Generate straight-pull PETG props from measured rear-edge slice roof positions."""
from pathlib import Path
import json
import math
import sys

import manifold3d as mf
import numpy as np

from clearance51 import blockers
from orient51 import digest

# Coordinates on plate used by plate51, with native path witnesses in the
# 'clear' comparison. These five roof groups are outside the screw journal.
TARGETS = [
    (110, 29.5,82.2), (110,32.2,82.0), (110,35.6,82.8),
    (110,40.7,82.2), (110,42.6,83.25), (110,64.0,83.6),
    (110,65.7,82.5), (110,71.6,82.1), (199,62.6,92.75),
    (156,39.9,88.59), (101,58.8,83.3),
]


def box(x,y,z,w,d,h):
    return mf.Manifold.cube((w,d,h)).translate((x-w/2,y-d/2,z))


def route_parts(foot, top, rise, radius=.62):
    ztop=top[2]
    start=max(.60,ztop-rise)
    def disk(pos,z,r):return mf.Manifold.cylinder(.4,r,r,24).translate((*pos,z))
    root=disk(foot,0,1.65);middle=disk(foot,start-.4,1.00)
    neck=2.5
    frac=neck/max(rise,neck)
    before=top[:2]*(1-frac)+foot*frac
    upper=disk(before,ztop-neck-.4,.86);tip=disk(top[:2],ztop-.4,radius)
    return [mf.Manifold.batch_hull([root,middle]),mf.Manifold.batch_hull([middle,upper]),mf.Manifold.batch_hull([upper,tip]),
            mf.Manifold.cylinder(.4,2.6,2.6,36).translate((*foot,0))]


def route(foot,top,rise):
    from functools import reduce
    from operator import add
    return reduce(add,route_parts(foot,top,rise))


def project_sections(s,heights):
    return {round(z,3):s.slice(float(z)).offset(.74) for z in heights}


def search(body, frame, offset):
    from support51 import q
    # Account for the whole stroke; the final exact solids and extraction
    # sweeps independently verify this raster shortlist.
    no_go=mf.Manifold.batch_boolean([body]+[v.transform(frame[:3]) for v in blockers('Key_Carrier',contact_only=True).values()],mf.OpType.Add)
    hz=np.arange(.1,40.1,.4)
    slices=project_sections(no_go,hz)
    lo=np.array(body.bounding_box()[:2]);hi=np.array(body.bounding_box()[3:5])
    made=[]; rows=[]; feet_used=[]
    for layer,mx,my in TARGETS:
        ztop=round(layer*.2-.6,2)
        target=np.array([mx-offset[0],my-offset[1],ztop])
        directions=[np.array([math.cos(a),math.sin(a)]) for a in np.linspace(0,2*np.pi,32,endpoint=False)]
        candidates=[]
        for direction in directions:
            for length in (5.,7.,9.,11.,13.,16.,20.,24.,28.):
                foot=target[:2]+direction*length
                outdist=np.linalg.norm(np.maximum(0.,np.maximum(lo-foot,foot-hi)))
                if outdist<1.7:continue
                for slope in (.54,.76,.94):
                    rise=length/slope
                    if rise>ztop-.5:continue
                    candidates.append((foot,direction,rise,outdist,length))
        if not candidates:
            rows.append(dict(layer=layer,xy=[mx,my],found=False));continue
        feet=np.asarray([row[0] for row in candidates]);rises=np.asarray([row[2] for row in candidates])
        valid=np.ones(len(candidates),bool)
        for z in hz[hz<ztop]:
            ids=np.flatnonzero(valid)
            if not len(ids):break
            fraction=np.clip((z-(ztop-rises[ids]))/rises[ids],0,1)
            xy=feet[ids]*(1-fraction[:,None])+target[:2]*fraction[:,None]
            valid[ids]&=~q._inside(slices[round(z,3)],xy)
        chosen=None
        for idx in sorted(np.flatnonzero(valid),key=lambda i: candidates[i][4]):
            foot,dir,rise,_,_=candidates[idx]
            if any(np.linalg.norm(foot-used)<5.6 for used in feet_used):continue
            prop=route(foot,target,rise)
            if any((prop^previous).volume()>.0001 for previous in made):continue
            if (prop^no_go).volume()>.0001:continue
            # Sweep each convex segment individually. A hull of the whole L
            # would include empty space inside the elbow.
            # Exact 0.5-mm withdrawal stepping resolves posts and walls >1mm.
            if any((prop.translate((*list(dir*dx),0))^body).volume()>.0001
                   for dx in np.arange(.3,31,.6)):continue
            chosen=(prop,foot,dir);break
        found=chosen is not None
        row=dict(layer=layer,xy=[mx,my],found=found)
        if found:
            prop,foot,dir=chosen;made.append(prop);feet_used.append(foot)
            row.update(foot_xy=(foot+offset).tolist(),pull_xy=dir.tolist(),rise_mm=float(rise),volume_mm3=round(prop.volume(),3))
        rows.append(row)
    print('External rootable tips',sum(r['found'] for r in rows),'/',len(rows),flush=True)
    return made,rows


def generate(two_sources,report):
    import json
    from orient51 import load_solid,oriented
    frame_json=json.loads(Path(two_sources).read_text())['parts']['Key_Carrier']
    src=Path(__file__).parent/'exports/Key_Carrier-assembly.stl'
    assert frame_json['source_sha256']==digest(src) and frame_json['orientation']=='rear_down'
    body,frame=oriented(load_solid(src),'rear_down')
    off=np.asarray(frame_json['assembly_to_machine'])[:2,3]-frame[:2,3]
    found,rows=search(body,frame,off)
    from orient51 import trimesh
    for old in report.parent.glob('prop-*.stl'):old.unlink()
    for i,obj in enumerate(found):
        m=obj.to_mesh();trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False).export(report.parent/f'prop-{i}.stl')
    report.write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    generate(sys.argv[1],Path(sys.argv[2]))
