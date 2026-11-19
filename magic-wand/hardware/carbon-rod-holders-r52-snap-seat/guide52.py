"""Compose the R52 mechanism and lifting sequence into the complete rod assembly."""
import copy
import json
import os
from pathlib import Path
import sys

import numpy as np
import trimesh
import build52 as d
from orient51 import digest,load_solid

HERE=Path(__file__).resolve().parent
OUT=HERE/'exports'
OLD=d.PREV/'exports'
sys.path.insert(0,str(HERE.parent/'carbon-rod-holders/assembly'))
from register_assembly import full_length_rods, register_assembly

ATTACHED=('board','sockets','housing','plug','op1_wire')
ARM_IDS=('front_op1_arm','rear_op1_arm')
I=np.eye(4)


def as4(a):
    return np.vstack([np.asarray(a).reshape(3,4),[0,0,0,1]])


def make_step(title,caption,samples):
    return dict(title=title,caption=caption,samples=samples,duration=2.5)


def support_actors(module,arms):
    module['actors'].pop('fasteners',None)
    for step in module['steps']:
        for s in step['samples']:
            s.pop('fasteners',None)
    module['actors']['carrier']['file']='carrier-without-moving-leaves.stl'
    for name in arms:
        module['actors'][name]=dict(file=name+'.stl',morphFile=name+'-lifted.stl',
                                    label='Liftable OP1 retaining arm',color='#29a5b7')
    for step in module['steps']:
        for s in step['samples']:
            if 'carrier' in s:
                for arm in arms:s[arm]=s['carrier'].copy()


def generate(register):
    d.old.configure_new_op1()
    guide=json.loads((OLD/'assembly-guide.json').read_text())
    modules=guide['modules']
    for module in modules.values():
        for actor in module['actors'].values():
            for key in ('file','morphFile'):
                old=actor.get(key)
                if not old or old in ('Key_Carrier-assembly.stl','DFRobot_Hole_Bracket-assembly.stl'):continue
                actor[key]=os.path.relpath((OLD/old).resolve(),OUT)
    base=load_solid(OUT/'Key_Carrier-assembly.stl')
    lift=d.RELEASE
    for name,y,side in zip(ARM_IDS,d.h.h32.EYELETS,(1,-1)):
        _,spring,peg=d.arm_features(y,side)
        arm=d.q.board_frame(spring+peg)
        base-=arm
        raw=arm.to_mesh()
        verts=np.asarray(raw.vert_properties[:,:3])
        tris=raw.tri_verts
        trimesh.Trimesh(verts,tris,process=False).export(OUT/(name+'.stl'))
        lifted=d.lifted_vertices(verts,y,side,lift)
        trimesh.Trimesh(lifted,tris,process=False).export(OUT/(name+'-lifted.stl'))
    d.old.baseline.b.save(OUT/'carrier-without-moving-leaves.stl',base)
    mod=modules['dfr']
    support_actors(mod,ARM_IDS)
    src=mod['steps']
    seat=copy.deepcopy(src[1]['samples'][-1])
    def pose(t=0.,raised=0.,above=0.):
        s=copy.deepcopy(seat)
        # Keep the seated pose exactly equal to the next established assembly step.
        move=as4(d.entry_transform(float(t))) if t else I.copy()
        move[2,3]+=above
        for actor in ATTACHED:
            s[actor]=(move@as4(seat[actor]))[:3].ravel().tolist()
        for arm in ARM_IDS:s.setdefault('morphs',{})[arm]=float(raised)
        return s
    ts=np.linspace(0,1,33)
    approach=[pose(1.,0.,16.+(1-t)*20) for t in ts]
    lifting=[pose(1.,t,16.) for t in ts]
    lowering=[pose(1.,1.,(1-t)*16.) for t in ts]
    insertion=[pose(1-t,1.) for t in ts]
    engage=[pose(0,1-t) for t in ts]
    sequence=[
        make_step('Feed the OP1 lead','Plug the lead into the board and feed its free end through the holder.',approach),
        make_step('Lift the two retaining arms','Lift both rounded ends just enough for the downward pegs to clear the PCB.',lifting),
        make_step('Offer the board at an angle','Bring the plugged board down to the open side of the recess.',lowering),
        make_step('Slide the board under the pegs','Slide the edge into the recess and tilt the board flat onto its seats.',insertion),
        make_step('Seat both pegs','Lower the arms until their tapered pegs sit in the two board holes.',engage)]
    mod['steps']=sequence+src[3:]
    for name in ('dfr','pin_hinge'):
        for st in modules[name]['steps']:
            if 'Press the lower' in st['title']:
                st['caption']='Press the centre and both lower corners. The rounded dome should press the OP1 button and the paddle should return when released.'
    # Removal has its own view so whole-rod assembly does not dismantle the board.
    small=('carrier',*ARM_IDS,*ATTACHED)
    detail=copy.deepcopy(mod)
    detail['label']='OP1 board clips'
    detail['note']='Fit the OP1 before the paddle and the four outer keys.'
    detail['actors']={k:v for k,v in detail['actors'].items() if k in small}
    # The touch board and its retaining posts are absent in this close-up.
    detail['annotations']=[
        dict(actor=arm, side=side, point=[*d.q.board_point(0, y), 12.82],
             step='Lift the two retaining arms', title=label)
        for arm, y, side, label in zip(ARM_IDS, d.h.h32.EYELETS,
            ('left', 'right'), ('Front lifting tab', 'Rear lifting tab'))
    ]
    reverse=[make_step(label,text,list(reversed(copy.deepcopy(st['samples'])))) for st,label,text in [
        (sequence[4],'Release both pegs','Lift both ends until the pegs leave the board holes.'),
        (sequence[3],'Tilt the board out','Tilt and slide the board towards the open side.'),
        (sequence[2],'Lift out the board','Raise the board while guiding its lead out of the holder.')]]
    detail['steps']=copy.deepcopy(sequence)+reverse
    for st in detail['steps']:
        for s in st['samples']:
            for k in list(s):
                if k not in (*small,'morphs'):s.pop(k)
    modules['op1_clips']=detail
    guide.update(revision='R52',physical_fit_verified=False,
                 print_components=dict(keys=['Key_Carrier','DFRobot_Hole_Bracket','DFR0030_Post_Clip','DFR0030_Post_Clip_2'],
                                       battery=['Battery_Holder','Battery_End_Door'],xiao=['XIAO_Rod_Holder','XIAO_Near_Keeper'],cable=['Cable_Clip_12_Wire']))
    guide=full_length_rods(guide,OUT)
    modules=guide['modules']
    names={a[k] for mod in modules.values() for a in mod['actors'].values() for k in ('file','morphFile') if k in a}
    guide['sources']=dict(upstream_guide_sha256=digest(OLD/'assembly-guide.json'),generator_sha256=digest(Path(__file__)),
                          meshes_sha256={n:digest(OUT/n) for n in sorted(names)})
    path=OUT/'assembly-guide.json'
    path.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    if register:register_assembly(path,'r52','R52 · Lift-in OP1 board and rounded click dome',make_current=True,group_keys=True)


if __name__=='__main__':
    generate('--register' in sys.argv)
