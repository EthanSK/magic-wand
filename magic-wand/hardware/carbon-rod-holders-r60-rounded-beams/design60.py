"""A single-piece key holder with round finger beams and an open, lengthwise battery cradle.

Assembly frame: +Y is toward the upper key row and the print bed. X=0 is the rod.
The removable OP1/DFRobot hardware and the key/socket frames come from R59.
"""
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'carbon-rod-holders-r59-flipped-guard'
sys.path.insert(0, str(PREVIOUS))
import carrier59 as old

b, c, k = old.b, old.c, old.k
OUT = HERE / 'exports'
BED = old.BED_Y
# The three-wire lane runs above the inboard edge. Lowering the pouch lets it
# tuck under that lane without moving the wires or increasing the bank width.
INNER, WIDTH, BOTTOM, THICK = -5.95, 11.8, -4.60, 3.9
OUTER = INNER - WIDTH
START, LENGTH = 9.6, 27.0
FLOOR = BOTTOM - 1.1
SHOE_PROJECTION, OPPOSITE_CLEARANCE = .21, .07
LEAF_GAP = .68


def soft_box(x0, x1, y0, y1, z0, z1, radius=.45):
    radius = min(radius, (x1-x0)*.48, (y1-y0)*.48, (z1-z0)*.48)
    ball = mf.Manifold.sphere(radius, 16)
    return mf.Manifold.batch_hull([ball.translate((x,y,z))
        for x in (x0+radius,x1-radius) for y in (y0+radius,y1-radius)
        for z in (z0+radius,z1-radius)])


def run(nodes, radius=1.26):
    ball = mf.Manifold.sphere(radius, 24)
    joints = [ball.translate(p) for p in nodes]
    return b.union(mf.Manifold.batch_hull([a,z]) for a,z in zip(joints,joints[1:]))


def finger_guard():
    # Two front/bottom roots and a short rear printing return. The three round
    # branches sit between the fingertip and the contacts. The socket backer
    # passes ABOVE them from the outside; there is no removable rest or shelf.
    root = (12.2, 21.0, 8.7)
    fork = (20.4, 6.65, .88)
    tip = (22.1,-4,.9)
    frame = [run([root, (13.6,16.0,4.4), (14.4,12.0,2.1), fork], 1.32)]
    for x in (15.1,22.1,28.1):
        frame.append(run([fork, (x,3.9,.88), (x,-1.0,.88), tip]))
    for x in (14.2,28.3):
        frame.append(run([tip,(x,-5,.9),(x,-7.7,4.8),(x,-8.1,7.9)],1.35))
    return b.union(frame)


def pouch():
    return b.box(OUTER,INNER,START,START+LENGTH,BOTTOM,BOTTOM+THICK)


def spring():
    # A long, free-ended PETG side leaf. Only its broad rounded shoe touches
    # the wrapped long edge. Its back is open to flex away from the cell.
    x=OUTER-.75
    leaf = soft_box(x-1.04,x,START+2,BED,BOTTOM+.42,BOTTOM+THICK-.45,.35)
    # Anchor the rear end so the leaf grows from the print bed. The nose
    # first slopes outwards, then bears 0.21 mm into the nominal side envelope.
    shoe = soft_box(x-.2,OUTER+SHOE_PROJECTION,START+4.7,START+10.2,BOTTOM+.45,BOTTOM+THICK-.65,.46)
    return leaf + shoe


def cradle():
    lo, hi = START-1.35, BED
    # The edges that overhang the key underside and touch the hand are radiused.
    # Keep the rear footprint at the established print-bed plane.
    pieces = [
        soft_box(OUTER-1.1, INNER+.85,lo,hi,FLOOR,BOTTOM,.49),
        soft_box(INNER+OPPOSITE_CLEARANCE,INNER+1.65,lo,hi,BOTTOM-.65,BOTTOM+THICK+.88),
        soft_box(INNER-1.35,INNER+1.65,lo,hi,BOTTOM+THICK+.24,BOTTOM+THICK+.90,.31),
        soft_box(OUTER-1.75,OUTER-.38,BED-5.5,BED,BOTTOM-.65,BOTTOM+THICK+1.15),
        # Close the deep end with a full-width rounded ramp. It grows from
        # the floor on successive print layers, entirely beyond the seated
        # pouch. An upright end wall here would roof over the whole pocket.
        mf.Manifold.batch_hull([
            soft_box(OUTER-.75,INNER+.8,lo-2.1,START-.05,FLOOR+.12,BOTTOM+.02,.30),
            soft_box(OUTER-.75,INNER+.8,lo-2.1,lo-1.75,BOTTOM+.30,BOTTOM+2.45,.16),
        ]),
        soft_box(OUTER-3.4,-8.85,BED-2.4,BED,4.0,7.9,.72),
        spring(),
    ]
    # Left-hand roof and attachment above the outer edge. Leave the upper-left
    # socket's path and the spring's deflection space open at the mouth.
    pieces.extend([
        soft_box(OUTER-3.4,OUTER-.75-1.04-LEAF_GAP,20.9,hi,BOTTOM-.65,7.75),
        soft_box(OUTER-3.4,OUTER+1.1,20.9,hi,BOTTOM+THICK+.32,BOTTOM+THICK+1.16),
        soft_box(OUTER-3.4,OUTER-.1,20.9,hi,FLOOR,BOTTOM-.12),
    ])
    assembled=b.union(pieces)
    # Open windows in the floor retain two skids and transverse load paths.
    window=soft_box(OUTER+2.2,INNER-2.1,START+3.7,BED-3.6,FLOOR-1,BOTTOM+1,1)
    return assembled-window


@lru_cache(maxsize=1)
def geometry():
    k.old.configure_new_op1()
    d=k.h.d
    working=d.geometry()[1]
    drop,bank=d.KEY_RAISE_MM,d.OUTER_BANK_START
    layer=(float(d.r22.base.slab_bottom())-drop,float(d.r22.base.slab_bottom()))
    # Reuse R59's unguarded deck by reconstructing its R58 seat and web recipe.
    upstream=b.load(old.n.R57/'exports/Key_Carrier-assembly.stl')
    _,moved=c.drop_seats(upstream,drop,bank)
    relieved,_,footprint=c.relieve(moved,bank,layer)
    slab=relieved ^ c.banks(bank,layer[1],60)
    plan={side:c.web_plan(slab,sign,old.NEARER) for side,sign in [('right',1),('left',-1)]}
    deck=c.move_upper_row(relieved,bank,layer[1],old.NEARER,plan,footprint)
    ribs=b.union(list(d.geometry()[3].values()))
    bare=deck-c.banks(bank,-10,layer[1]-.02)-b.mirrored(b.box(9.3,bank,-3,10,-8,3.4))
    bare-=b.mirrored(b.box(9.3,bank,-3,14.5,-8,3.4)) ^ ribs
    routes={n:c.placed(v,n,drop,old.NEARER) for n,v in working.items() if n.startswith('key_')}
    cutters={n:c.placed(v,n,drop,old.NEARER) for n,v in d.socket_print_cutters(working).items() if n.startswith('key_')}
    guards=b.mirrored(finger_guard())
    stage=d.r22.spaces16.carve(bare+guards+cradle(),cutters,'R60 socket openings')
    stage,_=c.blend_seam(stage,bank,float(d.r22.base.plate_top()))
    stage,_=c.ease_socket_end(stage,routes['key_3_maximum_socket'])
    return stage, bare, guards, working, routes


def main():
    body, bare, guards, working, routes=geometry()
    pieces=sorted(body.decompose(),key=lambda s:-s.volume())
    print('fragments', [round(s.volume(),3) for s in pieces[1:10]],flush=True)
    assert sum(abs(s.volume()) for s in pieces[1:])<.6
    C=pieces[0]
    OUT.mkdir(exist_ok=True)
    b.save_closed(OUT/'Key_Carrier-assembly.stl',C)
    b.save_closed(OUT/'Battery_Pack-assembly.stl',pouch())
    vol=k.vol
    loaded=[(name,i,vol(C,p)) for name,v in routes.items() for i,p in enumerate(c.poses(v))]
    blocked=[row for row in loaded if row[2]>.01]
    pack=pouch()
    # Test the rigid opening independently of the intended flexible shoe.
    rigid=C-spring()
    sweep=max(vol(rigid,pack.translate((0,float(t),0))) for t in np.linspace(0,30,31))
    rod=k.h.base.rod(); lane=working['external_wire_bus']
    keepout=rod+lane
    shoulders=[round(vol(bare,x),3) for x in (finger_guard(),cradle())]
    backers={}
    for side,sign in [('Left',-1),('Right',1)]:
        part=b.load(old.R58/'exports'/f'Socket_Backer_{side}-assembly.stl')
        backers[side]=max(vol(C,part.translate((sign*float(dx),0,0))) for dx in np.linspace(0,26,27))
    keys=json.loads((PREVIOUS/'exports/carrier.json').read_text())
    report=dict(revision='R60', key_layout=keys['key_layout'], change=keys['change'],
      source_sha256=sha256((OUT/'Key_Carrier-assembly.stl').read_bytes()).hexdigest(),
      physical_fit_verified=False, key_poses_checked=len(loaded), obstructed_key_poses=blocked,
      battery_rigid_sweep_mm3=sweep,spring_contact_volume_mm3=vol(C,pack), nominal_side_leaf_deflection_mm=round(SHOE_PROJECTION-OPPOSITE_CLEARANCE,3),
      shoe_projection_mm=SHOE_PROJECTION, rigid_opposite_clearance_mm=OPPOSITE_CLEARANCE, leaf_back_gap_mm=LEAF_GAP,
      new_material_inside_rod_or_wire_route_mm3=vol((C-bare)+pack,keepout),
      direct_root_overlap_mm3=shoulders, backer_route_overlap_mm3=backers,
      exposed_battery_end_mm=round(START+LENGTH-BED,2),old_to_new_inboard_pouch_edge_mm=[old.pack().bounding_box()[3],INNER],
      finger_beam_diameter_mm=2.52, holder_bounds_mm=C.bounding_box(),holder_solid_petg_g=round(C.volume()*.00127,2))
    print(json.dumps(report,indent=1),flush=True)
    (OUT/'carrier.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not blocked and sweep<.01 and report['new_material_inside_rod_or_wire_route_mm3']<.01
    assert min(shoulders)>2 and max(backers.values())<.01


if __name__=='__main__':
    main()
