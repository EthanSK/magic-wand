"""R61 key holder, raised battery cradle, gradual finger rests and connector-down paddle."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import json
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
R60 = HERE.parent / 'carbon-rod-holders-r60-rounded-beams'
sys.path.insert(0, str(R60))
import design60 as prior
import build59

b, k, m = prior.b, prior.k, prior.old.m
REAR = 11.0
Y_SHIFT = (0, REAR, 0)
BED = prior.BED + REAR
SEAT = b.SEAT_Z
AXIS = m.AXIS_Y + REAR
FLIP = [[-1,0,0,0], [0,1,0,0], [0,0,-1,SEAT+b.BOARD_TOP]]
SOCKET_FACE = b.BOARD_REAR-1
LEAD_R = .65
run, soft = prior.run, prior.soft_box


def curve(points, r):
    a,bp,c,d = np.asarray(points)
    t = np.linspace(0,1,12)[:,None]
    return run((1-t)**3*a + 3*t*(1-t)**2*bp + 3*t*t*(1-t)*c + t**3*d,r)


def finger_guard():
    tip=(22.1,-2.2,.88)
    fork=(20.4,6.65,.88)
    shapes=[curve([(12.2,21,8.7),(13.4,14.7,2.25),(14.0,10.7,.88),fork],1.32)]
    for x in (15.1,22.1,28.1):
        shapes.append(run([fork,(x,3.9,.88),(x,-.3,.88),tip]))
    for x in (14.2,28.3):
        shapes.append(curve([tip,((x+22.1)/2,-4.4,.9),(x,-7.3,5.85),(x,-9.3,8.3)],1.35))
    return b.union(shapes)


def pouch():
    return prior.pouch().translate(Y_SHIFT)


def tail(deck):
    # Retain the original rim's rod and wiring openings in a tapered extension.
    # Both hinge cheeks ride on this extension. The broad banks end at the
    # old rear edge. The narrower tongue and battery cradle extend beyond them.
    stripped = deck - b.box(-11.63,11.63,m.CHEEK_FRONT-.05,prior.BED+.1,11.125,32)
    xz = stripped.rotate((-90,0,0)).slice(-prior.BED+.48)
    extrusion = xz.extrude(REAR+.7).rotate((90,0,0)).translate((0,BED,0))
    # The extruded section runs towards -Y from the bed.
    plan = b.prism_xy([(-28.4,prior.BED-.70),(28.4,prior.BED-.70),
                       (22.,BED),(-24.9,BED)],-9,23)
    # Relieve the added length of the guide tube slightly so the rod
    # bears on the original seats. Avoid coincident cylindrical skins.
    bore=mf.Manifold.cylinder(REAR+2,4.18,4.18,circular_segments=128).rotate((-90,0,0)).translate((0,prior.BED-1,0))
    return stripped + ((extrusion ^ plan)-bore) + m.cheeks().translate(Y_SHIFT)


def paddle():
    original=b.load(prior.PREVIOUS/'exports/Touch_Paddle-assembly.stl')
    # Keep the pressed end, board lands, and the refitted R58 barrel unchanged.
    front=original ^ b.box(-15,15,-20,20.1,0,40)
    barrel=original ^ b.box(-15,15,25.75,40,0,40)
    # The side rails leave an open-bottom, open-sided exit under the PCB.
    # The right bridge sits below the cable and ends at the barrel.
    rail=mf.Manifold.batch_hull([b.box(8.6,10.6,19.75,20.1,15.3,19.3),
                                 b.box(6.0,8.55,24.6,25.4,17.7,19.3)])
    rail+=mf.Manifold.batch_hull([b.box(6,8.55,24.6,25.4,17.7,19.3),
                                  b.box(4.35,7.05,m.BARREL_Y[0]+REAR,m.BARREL_Y[0]+REAR+.9,15.5,19.1)])
    # Drop the right bridge under the wires so the wired board can lift vertically.
    right=mf.Manifold.batch_hull([b.box(8.6,10.6,19.75,20.1,15.3,19.3),
                                  b.box(6.15,8.65,28.4,28.9,12.65,14.86)])
    right+=mf.Manifold.batch_hull([b.box(6.15,8.65,28.4,28.9,12.65,14.86),
                                   b.box(4.35,7.02,36.9,37.95,12.9,14.9)])
    plate=front+rail.mirror((1,0,0))+right+barrel.translate(Y_SHIFT)
    # Shallow relief under the component-side copper. The board still seats
    # along its structural edges, at its original height and hole positions.
    return plate-b.box(-9.86,9.86,b.BOARD_FRONT+.4,b.BOARD_FRONT+13.85,SEAT-.085,SEAT+.05)


def housing():
    return b.box(-4.6,4.6,SOCKET_FACE-7.65,SOCKET_FACE,SEAT-6.15,SEAT)


def plug():
    return soft(-4.0,4.,SOCKET_FACE-1,SOCKET_FACE+3.6,SEAT-5.1,SEAT-.3,.32)


def lead():
    # Start in the crimp end of the 3-way plug. Form a gentle right turn
    # over the lowered outboard rail, then exit into open air beside the hinge.
    strands=[]
    for x in (-2.,0.,2.):
        y=SOCKET_FACE+3.25
        r=4.65-x
        nodes=[(x,y,SEAT-2.85),(x,y+.5,SEAT-2.85)]
        for t in np.linspace(0,np.pi/2,16)[1:]:
            nodes.append((4.65-r*np.cos(t),y+.5+r*np.sin(t),SEAT-2.85))
        nodes.append((14.3,nodes[-1][1],SEAT-2.85))
        strands.append(run(nodes,LEAD_R))
    return b.union(strands)


def posed(s, degrees):
    return m.posed(s.translate((0,-REAR,0)), degrees).translate(Y_SHIFT)


@lru_cache(maxsize=1)
def holder():
    _, bare, _, working, routes=prior.geometry()
    base=tail(bare)
    guards=b.mirrored(finger_guard())
    cradle=prior.cradle().translate(Y_SHIFT)
    # The inboard shoulder of the outboard rail is carried directly by the
    # tapered rear rim. Carve the bought key routes after joining everything.
    drop=k.h.d.KEY_RAISE_MM
    cutters={n:prior.c.placed(v,n,drop,prior.old.NEARER) for n,v in k.h.d.socket_print_cutters(working).items() if n.startswith('key_')}
    joined=k.h.d.r22.spaces16.carve(base+guards+cradle,cutters,'R61 socket insertion')
    joined,_=prior.c.blend_seam(joined,k.h.d.OUTER_BANK_START,float(k.h.d.r22.base.plate_top()))
    joined,_=prior.c.ease_socket_end(joined,routes['key_3_maximum_socket'])
    for name,route in routes.items():
        if name.endswith('_mount_opening'):
            center=np.asarray(route.bounding_box()).reshape(2,3).mean(axis=0)
            join_clearance=route.translate(-center).scale((1.001,1.001,1)).translate(center)
            joined-=join_clearance
    # Keep the upper socket's inboard latch clear of slicer wall rounding.
    joined-=b.box(-14.8,-12.35,19.15,23.15,8.45,10.4)
    return joined,base,guards,cradle,working,routes


def main():
    OUT.mkdir(exist_ok=True)
    body,base,guards,cradle,working,routes=holder()
    parts={'Key_Carrier':body,'Touch_Paddle':paddle(),'Battery_Pack':pouch(),'Gravity_Plug':plug(),'Gravity_Wires':lead(),
           'Hinge_Pin':b.load(prior.old.n.R57/'exports/Hinge_Pin-assembly.stl').translate(Y_SHIFT),
           'Hinge_Pin_Snug':b.load(prior.old.R58/'exports/Hinge_Pin_Snug-assembly.stl').translate(Y_SHIFT),
           'Pin_Clip':build59.pin_clip().translate(Y_SHIFT)}
    for name,s in parts.items():
        pieces=sorted(s.decompose(),key=lambda part:-part.volume())
        if name!='Gravity_Wires':
            debris=sum(abs(p.volume()) for p in pieces[1:])
            assert debris<.05,(name,debris)
            s=pieces[0].simplify(.001)
        b.save_closed(OUT/(name+'-assembly.stl'),s)
    C=b.load(OUT/'Key_Carrier-assembly.stl')
    pack=pouch()
    rigid=C-prior.spring().translate(Y_SHIFT)
    report=dict(revision='R61',physical_fit_verified=False,
                rear_extension_mm=REAR,pouch_end_beyond_original_rim_mm=prior.START+prior.LENGTH+REAR-prior.BED,
                guard_to_original_deck_mm3=k.vol(base,guards),cradle_to_rear_rim_mm3=k.vol(base,cradle),
                key_poses_checked=0,key_obstructions=[],backer_sweep_mm3={})
    for name,g in routes.items():
        for i,s in enumerate(prior.c.poses(g)):
            report['key_poses_checked']+=1
            v=k.vol(C,s)
            if v>.01: report['key_obstructions'].append([name,i,v])
    for side,sign in [('Left',-1),('Right',1)]:
        p=b.load(prior.old.R58/'exports'/f'Socket_Backer_{side}-assembly.stl')
        report['backer_sweep_mm3'][side]=max(k.vol(C,p.translate((sign*float(t),0,0))) for t in range(27))
    report['battery_slide_mm3']=max(k.vol(rigid,pack.translate((0,float(t),0))) for t in range(31))
    report['wire_rod_obstruction_mm3']=k.vol((C-base)+pack,k.h.base.rod()+working['external_wire_bus'])
    report['source_sha256']=sha256((OUT/'Key_Carrier-assembly.stl').read_bytes()).hexdigest()
    report.update({key:json.loads((prior.OUT/'carrier.json').read_text())[key] for key in ['key_layout','change']})
    (OUT/'carrier.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('change','key_layout')},flush=True)
    assert not report['key_obstructions'] and max(report['backer_sweep_mm3'].values())<.01
    assert max(report['battery_slide_mm3'],report['wire_rod_obstruction_mm3'])<.01
    assert min(report['guard_to_original_deck_mm3'],report['cradle_to_rear_rim_mm3'])>15

if __name__=='__main__':
    main()
