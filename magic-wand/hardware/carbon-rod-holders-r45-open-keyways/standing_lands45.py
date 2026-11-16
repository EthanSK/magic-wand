"""Small rooted standing underlays beside the rod notch and OP1 shoulders."""
import manifold3d as mf
import numpy as np
from shelf45 import box,band
from standing45 import overlap

def make(body,frame,routes):
    # Each target identifies an actual free return in the Z14.2/17.6/34.0
    # slice. Build from existing carrier material every layer. Do not step
    # through a future board, rod or plug pose to reach the target.
    sites=[('rod_notch',14.2,33.15,5.21,1.8,1.95),('op1_inner',17.6,35.93,11.85,1.25,2.30),
           ('op1_shoulder',34.,27.58,10.26,1.15,2.)]
    members={};inverse=np.linalg.inv(frame)[:3]
    for name,z,x,y,w,h in sites:
        domain=box(x,y,w,h);bottom=z-2.8;top=z+.2
        slab=domain.extrude(top-bottom).translate((0,0,bottom))
        space=slab.transform(frame[:3]);bb=space.bounding_box();hits=[]
        for region in routes.values():
            for pose in region.poses() if hasattr(region,'poses') else [region]:
                if overlap(bb,pose.bounding_box()):
                    cut=space^pose
                    if not cut.is_empty():hits.append(cut)
        void=mf.Manifold.batch_boolean(hits,mf.OpType.Add).transform(inverse) if hits else mf.Manifold()
        target=(body.slice(z-.1)^domain).offset(.35)^domain
        previous=body.slice(bottom-.1);layers=[]
        for k in range(round(bottom/.2)+1,round(top/.2)+1):
            high=k*.2;low=high-.2
            legal=target-band(void,low-.00001,high+.00001).offset(.015)
            allowed=previous.offset(.14)^legal
            if not allowed.is_empty():layers.append(allowed.extrude(.200002).translate((0,0,low-.000001)))
            previous=body.slice(high-.1)+allowed
        if layers:
            member=mf.Manifold.batch_boolean(layers,mf.OpType.Add)
            if (member-body).volume()>.025:members[name]=(member,z)
    return members
