"""Add a standing-print chamfer beneath the inherited left key-floor lip."""
from pathlib import Path
import json
import manifold3d as mf
import numpy as np
import trimesh
from holder45 import inherited

def overlap(a,b):
    return all(a[i]<b[i+3] and b[i]<a[i+3] for i in range(3))

def prepare(body,frame,directory):
    # Work in the actual standing print frame. The narrow floor lip at
    # Z30.6 extends from the previous wall towards print -Y. Back it
    # progressively over 2.4 mm, including both corners of the native path.
    # The same recessed underside returns around the other socket lands.
    # Each local apron is restricted to the actual higher-layer carrier
    # face, and to its own measured short X interval. This keeps the original
    # outline; hardware/operating sweeps are subtracted from the addition.
    sites=[('left_lip',30.6,.01,11.43)]
    for z,x0,x1 in [(7.2,46.95,49.0),(8.,48.88,52.84),(9.6,58.23,60.04),
                       (16.8,.01,1.91),(17.6,1.64,6.43),(19.2,10.96,14.21),
                       (28.6,46.93,49.13),(29.4,49.,52.95),
                       (30.8,16.20,19.21),(30.8,58.25,60.04)]:
        sites.append((f'socket_{len(sites)}',z,x0,x1))
    # Only the left floor accepted a useful added wedge throughout its
    # approach. At the remaining sites the seated socket/solder routes
    # truncate added aprons; bevel the obsolete underside lip instead.
    label,z,x0,x1=sites[0]
    # The earlier continuous wedge left 0.03-mm and 0.10-mm partial
    # terminal slabs which the machine did not deposit. Draw full native
    # 0.20-mm layers and step the slope by 0.15 mm at each new layer.
    steps=[]
    for k in range(142,155):
        top=k*.2
        leading=13.82-(k-142)*.15
        section=mf.CrossSection.square((x1-x0,14.03-leading)).translate((x0,leading))
        low=top-.2
        steps.append(section.extrude(.200001).translate((0,0,low-.000001)))
    piece=mf.Manifold.batch_boolean(steps,mf.OpType.Add)
    members={label:(piece,z)}
    zones,structural=inherited.routes()
    routes={**zones[inherited.d.CARRIER],**inherited.full.precision_support_spaces()}
    raw=mf.Manifold.batch_boolean([v[0] for v in members.values()],mf.OpType.Add)
    candidate=raw.transform(frame[:3]);bb=candidate.bounding_box()
    cuts=[];stats={}
    for name,region in routes.items():
        poses=list(region.poses()) if hasattr(region,'poses') else [region]
        local=[(i,p) for i,p in enumerate(poses) if overlap(bb,p.bounding_box())]
        actual=[]
        for i,p in local:
            hit=candidate^p
            if hit.volume()>1.e-8:
                cuts.append(hit);actual.append(i)
        stats[name]=dict(total_poses=len(poses),overlapping_pose_indices=actual)
    safe=candidate-mf.Manifold.batch_boolean(cuts,mf.OpType.Add) if cuts else candidate
    inverse=np.linalg.inv(frame)[:3];bevel=safe.transform(inverse)
    from standing_relief45 import make as relieve
    cut,relief=relieve(body,body+bevel,sites,frame,routes,structural[inherited.d.CARRIER])
    bevel-=cut
    # A narrowing original wall reveals new-only wedge material late
    # inside this slab, above the native sampling plane. Remove that
    # upward-only fringe from the physical addition; retain all original
    # material, overlaps and the complete uncropped exported difference.
    band30=mf.Manifold.cube((13.,4.,.2)).translate((-.5,11.,30.2))
    slice_new=(bevel-body).slice(30.30)
    unavailable=((bevel-body)^band30)-slice_new.extrude(.20001).translate((0,0,30.199995))
    bevel-=unavailable
    new=bevel-body;joined=(body-cut)+bevel
    from plate45 import digest
    full_file=directory/'R45-complete-added-chamfer-witness.stl'
    mesh=new.to_mesh()
    trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False).export(full_file)
    remaining={}
    for name,region in routes.items():
        poses=region.poses() if hasattr(region,'poses') else [region]
        remaining[name]=max(((p^new.transform(frame[:3])).volume() for p in poses if overlap(bb,p.bounding_box())),default=0.)
    assert max(remaining.values())<1.e-5,remaining
    # Both witnesses are taken from the original body and the independently
    # clipped bevel BEFORE union. The lower bond and lap onto the existing
    # floor are disjoint height bands. Preserve their native material checks.
    bonds={}
    for label,(member,z) in members.items():
        before=member^bevel^body
        for role,lo,hi in [('root',z-2.5,z-.29),('floor_lap',z-.17,z+.23)]:
            name=f'{label}_{role}'
            witness=before.trim_by_plane((0,0,1),lo).trim_by_plane((0,0,-1),-hi)
            volume=witness.volume()
            if volume>.001:
                mesh=witness.to_mesh()
                filename=f'R45-chamfer-{name}-witness.stl'
                trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False).export(directory/filename)
                bonds[name]=dict(file=filename,sha256=digest(directory/filename),volume_mm3=volume)
    result=dict(added_mm3=new.volume(),removed_mm3=max(0.,(body-joined).volume()),
        new_only_unsampled_fringe_removed_mm3=max(0.,unavailable.volume()),lower_lip_relief=relief,feature='Standing key-floor underside chamfers',complete_route_checks=stats,complete_added_witness=dict(file=full_file.name,sha256=digest(full_file)),
        maximum_added_intersection_mm3_by_route=remaining,pre_union_bonds=bonds)
    (directory/'standing-repair.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Standing repair',new.volume(),bonds,'added route intrusions',max(remaining.values()),flush=True)
    return joined,result
