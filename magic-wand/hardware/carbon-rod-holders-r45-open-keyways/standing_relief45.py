"""Bevel free socket-lip material where the actual hardware prevents adding below it."""
import manifold3d as mf
import numpy as np
from shelf45 import box,union
from standing45 import overlap

def make(body,with_aprons,sites,frame,routes,original_witnesses):
    # Keep resolving the same lower-deck overhang as the socket opening
    # progresses along the build axis. The preceding narrow X/Z windows
    # ended at an abrupt ledge, reinstating the unsupported lip one layer
    # beyond the mask. Restrict the relief to the four original low pads.
    windows=[(box(x,11.78,width,1.82),lo,hi)
             for x,width,lo,hi in ((-.3,20.1,14.8,23.4),(-.3,20.1,26.8,35.5),
                                   (46.,14.4,5.8,13.8),(46.,14.4,27.0,35.5))]
    allowed=mf.Manifold.batch_boolean([p.extrude(hi-lo).translate((0,0,lo)) for p,lo,hi in windows],mf.OpType.Add)
    assembly_bounds=allowed.transform(frame[:3]).bounding_box()
    inverse=np.linalg.inv(frame)[:3]
    protected=[]
    for target in original_witnesses.values():
        if overlap(assembly_bounds,target.bounding_box()):
            protected.append(target.transform(inverse)^allowed)
    # The outer keys sit on R44's raised backplates. Preserve the complete
    # original raised platforms (board face, locating hole walls and tape
    # lands), not a fictitious bearing surface around an oversized swept
    # solder-clearance envelope in the obsolete lower floor.
    from holder45 import inherited
    platforms=inherited.d.seat_platforms().transform(inverse)
    protected.append(platforms^allowed)
    # Keep material immediately bordering the real purchased solid and
    # operating mounting hole; maximum-socket and loading envelopes are
    # clearance volumes. Removing material only opens those air spaces.
    for name,target in routes.items():
        if not name.endswith(('_switch','_socket','_mount_opening','_socket_tape_zone')) or name.endswith('_maximum_socket'):continue
        if hasattr(target,'poses'):continue
        near=allowed.bounding_box();b=target.transform(inverse).bounding_box()
        if any(near[i]>=b[i+3]+.3 or b[i]>=near[i+3]+.3 for i in range(3)):continue
        local=target.transform(inverse)^mf.Manifold.cube(tuple(near[i+3]-near[i]+2 for i in range(3))).translate(tuple(near[i]-1 for i in range(3)))
        if local.is_empty():continue
        protected.append(local.minkowski_sum(mf.Manifold.sphere(.04,8))^allowed)
    keep=mf.Manifold.batch_boolean(protected,mf.OpType.Add)
    old=None;cuts=[]
    for k in range(1,round(with_aprons.bounding_box()[5]/.2)+1):
        z=k*.2;mid=z-.1;now=with_aprons.slice(mid)
        mask=union([section for section,lo,hi in windows if lo<mid<hi])
        if old is not None and not mask.is_empty():
            # Locally constrain growth of the remaining underside to 0.10
            # mm per 0.20-mm layer. Only unnecessary material outside the
            # structural/mating keep-outs can be removed.
            native_root=old.offset(-.22).offset(.22) if 7.8<z<11.0 else old
            unsupported=((now^mask)-native_root.offset(.10))-keep.slice(mid).offset(.05)
            if not unsupported.is_empty():
                cuts.append(unsupported.extrude(.20002).translate((0,0,z-.20001)))
                now-=unsupported
        old=now
    cut=(mf.Manifold.batch_boolean(cuts,mf.OpType.Add)^allowed)-keep if cuts else mf.Manifold()
    removed=body^cut
    hits={name:max(0.,(target^removed.transform(frame[:3])).volume()) for name,target in original_witnesses.items() if overlap(assembly_bounds,target.bounding_box())}
    assert max(hits.values(),default=0.)<1.e-5
    assert (removed^keep).volume()<1.e-5
    return cut,dict(original_removed_mm3=removed.volume(),protected_intersections_mm3=hits,
        maximum_mating_or_witness_intrusion_mm3=max(0.,(removed^keep).volume()),
        preserved_raised_platform_intersection_mm3=max(0.,(removed^platforms).volume()),purchased_solid_neighbourhood_mm=.04,
        lower_floor_only_assembly_z_bounds=[11.78+frame[2,3],13.60+frame[2,3]])
