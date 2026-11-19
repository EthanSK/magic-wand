"""External triangulated fork with snippable contacts for the two OP1 leaves."""
import numpy as np
import manifold3d as mf
from build52 import arm_features, q, h, union, box


def node(x,y,z,sx,sy,sz):
    return box(x-sx/2,x+sx/2,y-sy/2,y+sy/2,z-sz/2,z+sz/2)


def carrier_fixture(frame, with_sweep=False):
    # The tool stands outboard in +machine Y, above the OP1 when assembled.
    stanchions=[]
    ribs=[]
    contacts=[]
    clipped_tips=[]
    loose_pieces=[]
    for y,side,post_x in zip(h.h32.EYELETS,(1,-1),(53.,65.)):
        root,spine,nose=arm_features(y,side)
        stem=q.board_frame(spine).transform(frame[:3])
        end=q.board_frame(nose).transform(frame[:3])
        a=np.array(end.bounding_box())
        bottom=a[2]
        # Begin the peg on a positive solid foot, then support its crossbar and
        # tether the length of the slender bending beam in four-millimetre steps.
        profiles=[(end,bottom+.30),(end,bottom+1.7)]
        b=stem.bounding_box()
        profiles.extend((stem,z) for z in np.arange(b[2]+2.8,b[5]-1.2,4.0))
        post_y=104.5
        high=0
        for leaf,z in profiles:
            sec=leaf.slice(float(z)); loops=sec.to_polygons()
            if not len(loops): continue
            pts=np.concatenate(loops)
            xmin,ymin=pts.min(0); xmax,ymax=pts.max(0)
            x=(xmin+xmax)/2
            face=ymax
            if leaf is end and z==profiles[0][1]:
                # Positive nose starter from directly below, with a stem
                # tapering at 45 degrees from the external frame.
                top=node(x,(ymin+ymax)/2,bottom+.03,.70,.60,.22)
                neck=node(x,(ymin+ymax)/2,bottom-.42,.75,.66,.56)
                end_node=neck
            else:
                top=node(x,face-.03,z,.58,.20,.40)
                neck=node(x,face+.42,z-.12,.67,.75,.50)
                end_node=neck
            contacts.append(top)
            ribs.append(mf.Manifold.batch_hull([top,neck]))
            dx=post_x-x;dy=post_y-face
            dz=np.hypot(dx,dy)+1.0
            seat=node(post_x,post_y,z-dz,3.8,4.2,1.8)
            shoulder=node(x,face+1.18,z-.8,1.45,1.35,1.1)
            strut=mf.Manifold.batch_hull([seat,shoulder])
            end_strut=mf.Manifold.batch_hull([shoulder,end_node])
            ribs.extend([strut,end_strut])
            # Flush cutters sever the narrow end before the frame is pulled.
            # Keep the outboard side of the actual cut plane in the removal proof.
            keeper=(box(-20,160,20,150,-1,bottom-.34)
                    if leaf is end and z==profiles[0][1] else box(-20,160,face+.55,150,-1,60))
            clipped_tips.append(end_strut^keeper)
            loose_pieces.extend([strut])
            high=max(high,z-dz+1.)
        stanchions.append(node(post_x,post_y,high/2,4.4,5.0,high))
        stanchions.append(mf.Manifold.cylinder(.4,4.7,4.7,40).translate((post_x,post_y,0)))
    # Each diagonal stiffens both tall posts without a horizontal roof.
    for z in (1,10,19):
        ribs.append(mf.Manifold.batch_hull([node(53,104.5,z,2.5,2.6,1.5),node(65,104.5,z+11,2.5,2.6,1.5)]))
    pieces=stanchions+ribs
    if with_sweep:
        # All ribs are convex hulls and both round feet are convex.
        sweep=union(mf.Manifold.batch_hull([s,s.translate((0,60,0))]) for s in stanchions+loose_pieces+clipped_tips+ribs[-3:])
        return union(pieces),union(contacts),sweep
    return union(pieces),union(contacts)


def inspect(carrier_path,frame):
    from orient51 import load_solid
    fixed=load_solid(carrier_path).transform(frame[:3])
    prop,contacts=carrier_fixture(frame)
    leaves=union(q.board_frame(union(arm_features(y,s)[1:])).transform(frame[:3])
                 for y,s in zip(h.h32.EYELETS,(1,-1)))
    stationary=fixed-leaves
    for name,item in [('arms',leaves),('fixed',stationary)]:
        hit=prop^item
        chunks=[(round(s.volume(),4),[round(v,2) for v in s.bounding_box()]) for s in hit.decompose() if s.volume()>.0001]
        print(name,'contacts',chunks,flush=True)
    print('fixture components',[(round(p.volume(),3),p.bounding_box()) for p in prop.decompose()],flush=True)
    return prop


if __name__=='__main__':
    import sys,json
    from pathlib import Path
    from build52 import HERE, old
    old.configure_new_op1()
    frame=np.array(json.loads((HERE/'exports/print-mechanisms/layout.frame.json').read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    inspect(Path(sys.argv[1]),frame)
