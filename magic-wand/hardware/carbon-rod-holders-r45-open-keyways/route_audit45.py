"""Check every complete pose once; retain per-pose, per-owner hits before cleanup."""
import numpy as np
from regions45 import external_air,fixed_endpoints

def inspect(checker,region,name,frame,xyz,data,kinds,features,keep,helpers,tabs,can_remove):
    q=checker.q; to_print=np.linalg.inv(frame)[:3]
    poses=list(region.poses()) if hasattr(region,'poses') else [region]
    endpoints=set(fixed_endpoints(name,list(range(len(poses)))))
    print_poses=[p.transform(to_print) for p in poses]
    bb=np.array([p.bounding_box() for p in print_poses]);lo=bb[:,:3].min(0);hi=bb[:,3:].max(0)
    half=data[:,3,None]/2
    near=((xyz[:,:2]>=lo[:2]-half)&(xyz[:,:2]<=hi[:2]+half)).all(axis=1)
    mid=xyz[:,2]-data[:,4]/2
    select=keep & near & (mid>lo[2]+q.Z_GUARD)&(mid<hi[2]-q.Z_GUARD)
    owners=['carrier or brim',*['removable helper '+name for name in helpers],'release tabs']
    ids=kinds.copy()
    for index,mask in enumerate(helpers.values(),1):ids[mask]+=len(features)*index
    ids[tabs]+=len(features)*(len(owners)-1)
    labels=[owner+' / '+feature for owner in owners for feature in features]
    samples=xyz[select],data[select,3],data[select,4],ids[select]
    conflicts=[];max_checked=0
    for i,p in enumerate(print_poses):
        result=q.inspect_region(p,*samples,labels,frame,limit=2)
        max_checked=max(max_checked,result['checked_samples'])
        if result['violations']:conflicts.append({'pose_index':i,'hits_by_owner_and_feature':result['violations'],
            'examples':result['examples'],'seated_or_hard_endpoint':i in endpoints})
    permanent=any(not label.startswith('removable helper ') for row in conflicts for label in row['hits_by_owner_and_feature'])
    hard=bool(conflicts and (not external_air(name) or any(row['seated_or_hard_endpoint'] for row in conflicts)))
    worst=max(conflicts,key=lambda row:sum(row['hits_by_owner_and_feature'].values())) if conflicts else None
    return {'poses_checked':len(poses),'maximum_checked_samples_per_pose':max_checked,
        'violations':worst['hits_by_owner_and_feature'] if worst else {},'worst_pose_index':worst['pose_index'] if worst else None,
        'pose_obstructions':conflicts,'pose_counting':'Counts are per pose; a bead can appear in multiple poses. No summed physical-volume estimate.',
        'clear_before_cleanup':not conflicts,'clear_after_whole_cradle_removal':not permanent,
        'requires_print_helper_removal':bool(conflicts and not permanent and can_remove),
        'temporary_hard_space_obstruction':bool(hard and not permanent),
        'unacceptable_obstruction':bool(permanent or (conflicts and not can_remove)),
        'acceptance_basis':'Temporary named-helper occupancy is cleanup-dependent, including hard holes. Accept only complete CAD and actual-bead withdrawal in the recorded removal order, accessible grip and measured release gaps. No fragment-removal exemption.',
        'external_assembly_air':external_air(name),'seated_or_hard_pose_indices':sorted(endpoints),
        'physical_cleanup_verified':False}
