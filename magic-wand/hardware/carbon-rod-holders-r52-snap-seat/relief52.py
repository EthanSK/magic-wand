"""Bevel only disconnected underside starts at the lower socket floors."""
import manifold3d as mf
import numpy as np
from sockets52 import key_spaces
from clearance51 import blockers
from build52 import union,box

def relieve(carrier,frame,evidence):
    """Work in the selected print pose. Preserve the actual socket seating lands."""
    import holder44
    windows=[]
    for w in evidence['parts']['Key_Carrier']['completely_unrooted_model_islands']:
        x,y,xx,yy=w['machine_xy_bounds']; z=w['z_mm']
        if y>90:continue  # The removable upper OP1 springs have separate support.
        windows.append(box(x-2.2,xx+2.2,y-.65,yy+.65,z-.65,z+5.5))
    region=union(windows)
    machine=carrier.transform(frame[:3])
    fit=key_spaces()
    # The existing print repair protects the raised platforms and the real
    # switch, socket, locating opening and tape lands. A maximum cable/solder
    # sweep is extra clearance, so removing a non-mating fringe opens it.
    from unittest.mock import patch
    # key_spaces has already set the inherited XY layout in this process.
    with patch.object(holder44.previous,'geometry',return_value=None):
        ws=[holder44.seat_platforms().transform(frame[:3])^region]
    for name,poses in fit.items():
        if len(poses)!=1 or name.endswith('_maximum_socket'):continue
        if name.endswith(('_switch','_socket','_mount_opening','_socket_tape_zone')):
            stock=poses[0].transform(frame[:3])^region
            if not stock.is_empty():ws.append(stock.minkowski_sum(mf.Manifold.sphere(.045,12)))
    # All praised finger surfaces stay exact.
    for n,s in blockers('Key_Carrier').items():
        if n.startswith('finger'):ws.append(s.transform(frame[:3])^region)
    fixed=union(ws)
    prev=mf.CrossSection();cuts=[]
    for k in range(1,1+int(np.ceil(machine.bounding_box()[5]/.2))):
        top=k*.2; mid=top-.1
        current=machine.slice(mid).simplify(.008)
        mask=region.slice(mid)
        if not mask.is_empty():
            # A sub-bead sliver cannot carry a fresh standing lip. Limit the
            # growth of the lower floor to 0.12 mm at each 0.20-mm layer.
            previous=prev.simplify(.008).offset(-.12,circular_segments=12).offset(.12,circular_segments=12)
            loose=(((current^mask)-previous.offset(.12,circular_segments=12))-fixed.slice(mid).offset(.065,circular_segments=12)).simplify(.006)
            if not loose.is_empty():
                cuts.append(loose.extrude(.20002).translate((0,0,top-.20001)))
                current-=loose
        prev=current.simplify(.008)
    cut=union(cuts)-fixed
    # Two sub-nozzle whiskers remain along corresponding lower Choc floors
    # even after a progressive bevel. Their source sits beyond the bought
    # switch and socket lands. Relieve the whole free fringe to its root.
    for cx,cy in [(-16.65,.25),(25.0,.05)]:
        notch=box(cx-1.0,cx+1.0,cy-3.15,cy+1.35,7.20,8.04).transform(frame[:3])
        cut+=notch-fixed
    inv=np.linalg.inv(frame)
    removed=(machine^cut).transform(inv[:3])
    return carrier-removed,dict(removed_mm3=round(removed.volume(),6),protected_overlap_mm3=max(0.,(cut^fixed).volume()))


def key_entry_bevel(shape,frame):
    """Break up transverse roof spans while retaining the original key seats."""
    body=shape.transform(frame[:3])
    cut=[]
    spaces=key_spaces()
    for key in (0,2,3,4):
        bb=spaces[f'key_{key}_mount_opening'][0].transform(frame[:3]).bounding_box()
        cx=(bb[0]+bb[3])*.5
        z=18.38 if key in (3,4) else 39.56
        # The skin at the top remains the existing mount datum. Place a lead-in
        # on the concealed front edge, retain ends and every seating flange.
        def slab(x0,x1,y0,y1,h):
            return box(x0,x1,y0,y1,z-.22,z+h)
        wedge=mf.Manifold.batch_hull([slab(cx-6.15,cx+6.15,91.23,91.28,.03),
                                      slab(cx-5.8,cx+5.8,93.26,93.30,.66)])
        # Keep the original central clip datum as well as both ends and the
        # top flange. The shallow pockets lie between the three original lands.
        centre=union(box(cx+dx-half,cx+dx+half,90.6,94.0,z-.4,z+1.1) for dx,half in ((-4.1,.80),(0,1.25),(4.1,.80)))
        cut.append(wedge-centre)
    cut=union(cut)
    real=union([r[0] for n,r in spaces.items() if len(r)==1 and n.endswith(('_switch','_socket','_socket_tape_zone')) and not n.endswith('_maximum_socket')]).transform(frame[:3])
    free=body^cut
    return shape-free.transform(np.linalg.inv(frame)[:3]),{'removed_mm3':free.volume(),'real_hardware_overlap_mm3':(free^real).volume(),'complete_top_flange_and_three_clip_lands_preserved':True}


def back_fixed_starts(shape, frame):
    """Back fixed rim, hinge base, rod shoulder and spring anchor at their first native beads."""
    def slab(x,y,z,w,d):
        return box(x-w/2,x+w/2,y-d/2,y+d/2,z-.10,z+.10)
    def ramp(bottom,top):
        return mf.Manifold.batch_hull([slab(*bottom),slab(*top)])
    shoulder=ramp((53.82,85.27,14.0,.42,.44),(54.35,85.15,15.32,.54,.48))
    shoulder-=mf.Manifold.cylinder(50,4.13,4.13,96).translate((frame[0,3],frame[1,3],0))
    hinge=ramp((44.9,90.18,41.25,.72,.63),(44.85,91.06,43.3,.69,.66))
    root=ramp((63.25,92.50,27.0,.75,1.85),(62.57,92.49,29.0,.75,2.34))
    from build52 import arm_features, h, q, RELEASE, board_entry_relief
    arms=union(q.board_frame(union(arm_features(y,sign,travel)[1:])) for y,sign in zip(h.h32.EYELETS,(1,-1))
               for travel in (0,RELEASE/2,RELEASE))
    local=root.transform(np.linalg.inv(frame)[:3])
    local-=arms.minkowski_sum(mf.Manifold.sphere(.67,16))
    extra=union([shoulder,hinge]).transform(np.linalg.inv(frame)[:3])+local
    extra-=board_entry_relief()
    return shape+extra,float((extra-shape).volume())


def trim_fixed_fringes(shape,frame):
    """Give the spring pockets three sloping open ends on fixed non-mating rims."""
    from build52 import arm_features,h,q
    def run(x0,x1,y0,y1,z0,z1,z2):
        # The top of the open pocket slopes from the fixed back wall out to
        # its lip. Successive 0.2 mm layers gain at most 0.12 mm overhang.
        low=box(x0,x1,y0,y1,z0,z1)
        ramp=mf.Manifold.batch_hull([box(x0,x1,y0,y1,z1-.02,z1),
                                     box(x0,x1,y1-.02,y1,z2-.02,z2)])
        return low+ramp
    cutoff=union([run(65.5,67.85,90.50,94.3,27.15,31.00,37.4),
                  run(61.95,64.95,90.65,94.1,26.15,28.85,34.7),
                  run(43.75,46.2,90.10,92.18,41.0,43.8,47.3)])
    leaves=union(q.board_frame(union(arm_features(y,side))) for y,side in zip(h.h32.EYELETS,(1,-1)))
    return shape-(cutoff.transform(np.linalg.inv(frame)[:3])-leaves)
