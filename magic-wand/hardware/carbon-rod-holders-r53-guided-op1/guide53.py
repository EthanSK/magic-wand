"""Animate the actual loose R53 parts and retain the complete 500 mm rod assembly."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import build53 as b

HERE = Path(__file__).resolve().parent
OUT = HERE/'exports'
OLD = b.R52/'exports'
sys.path.insert(0,str(HERE.parent/'carbon-rod-holders/assembly'))
from register_assembly import full_length_rods, register_assembly
from hashlib import sha256

BOARD = ('board','sockets','housing','plug','op1_wire')
SWITCH = ('switch','terminals','plunger')
SENSOR = ('sensor','electrode','connector','gravity_pins','sensor_lead')
CLIPS = ('clip_left','clip_right')
TOUCH = ('cap','post_bar',*SENSOR,*CLIPS)
NAMES = dict(carrier=('Key_Carrier','Key holder with open hinge seats','#9d4139'),
             cap=('Touch_Paddle','Paddle with switch guide and pivot','#d78845'),
             post_bar=('DFR_Post_Bar','Two-post touch-board bar','#ba75ae'),
             hinge_cap=('Hinge_Cap','Sliding hinge cap','#f1c35d'),
             lid=('OP1_Lid','OP1 board retainer','#47b3aa'))
I = np.eye(4)


def translation(v):
    m=I.copy()
    m[:3,3]=v
    return m


def pack(m):
    return np.asarray(m)[:3].reshape(-1).tolist()


def unpack(m):
    return np.vstack([np.asarray(m).reshape(3,4),[0,0,0,1]])


def add(steps,title,caption,state,group,delta):
    start=deepcopy(state)
    delta=np.array(delta)
    samples=[]
    for t in np.linspace(0,1,25):
        pose=deepcopy(start)
        for actor in group:
            pose[actor]=pack(translation(t*delta) @ unpack(start[actor]))
        samples.append(pose)
    steps.append(dict(title=title,caption=caption,duration=2.3,samples=samples))
    state.update(samples[-1])


def subset(module,names,steps,label,note):
    actors={k:v for k,v in module['actors'].items() if k in names}
    result=dict(label=label,note=note,rotation=module['rotation'],actors=actors,steps=[])
    for step in steps:
        record={k:deepcopy(v) for k,v in step.items() if k!='samples'}
        record['samples']=[{k:v for k,v in sample.items() if k in actors} for sample in step['samples']]
        result['steps'].append(record)
    return result


def reverse(step,title,caption):
    return dict(title=title,caption=caption,samples=list(reversed(step['samples'])),duration=step['duration'])


def build(fit):
    guide=json.loads((OLD/'assembly-guide.json').read_text())
    modules=guide['modules']
    for module in modules.values():
        for actor in module['actors'].values():
            for key in ('file','morphFile'):
                if key in actor:actor[key]=os.path.relpath((OLD/actor[key]).resolve(),OUT)
    old=modules['dfr']
    references=json.loads((OUT/'assembly-transforms.json').read_text())['actors']
    actors={k:deepcopy(old['actors'][k]) for k in ('rod',*BOARD,*SWITCH,*SENSOR,*CLIPS)}
    for actor,(name,label,color) in NAMES.items():
        actors[actor]=dict(file=name+'-assembly.stl',label=label,color=color)
    seated=old['steps'][-1]['samples'][-1]
    state={k:pack(I) for k in actors}
    state['rod']=seated['rod']
    for actor in (*BOARD,*SWITCH,*SENSOR,*CLIPS):
        source=references[actor]
        state[actor]=source['base']
        actors[actor]['file']=source['file']
        if 'morphFile' in source:
            actors[actor]['morphFile']=source['morphFile']
    axis=b.board_axis()
    def shift(group,delta):
        for actor in group:state[actor]=pack(translation(delta)@unpack(state[actor]))
    shift(BOARD,[0,0,15]);shift(SWITCH,[0,0,29])
    shift(TOUCH,[52,0,19])
    shift(('post_bar',),[0,0,-9]);shift(SENSOR,[0,0,11]);shift(CLIPS,[0,-8,11])
    shift(('hinge_cap',),[0,10,0]);shift(('lid',),-axis*34)
    steps=[]
    add(steps,'Seat the OP1 board','Feed the plugged-in lead through its outlet, then lower the board straight into the angled pocket until both eyelets settle over the tapered fingers.',state,BOARD,[0,0,-15])
    add(steps,'Fit the mouse switch','Line the three switch pins up with the OP1 sockets and seat the case squarely.',state,SWITCH,[0,0,-29])
    add(steps,'Insert the two-post bar','With the paddle off the holder, insert both posts through its mounting holes from underneath.',state,('post_bar',),[0,0,9])
    add(steps,'Seat the touch board','Lower the DFRobot board onto its two posts.',state,(*SENSOR,*CLIPS),[0,0,-11])
    add(steps,'Slide on the two small clips','Slide the open ends around the post necks above the touch board.',state,CLIPS,[0,8,0])
    add(steps,'Move the paddle over the holder','Align its pivot with the two open hinge seats. The sleeve faces the mouse switch.',state,TOUCH,[-52,0,0])
    add(steps,'Lower the pivot into its seats','Lower the paddle so its sleeve surrounds the switch and both axle ends sit in the open hinge.',state,TOUCH,[0,0,-19])
    add(steps,'Slide on the hinge cap','Slide the separate cap in from the rear until it holds both ends of the pivot.',state,('hinge_cap',),[0,-10,0])
    add(steps,'Fit the OP1 retainer','Slide the retainer into the two rails above the board and seat the latch.',state,('lid',),axis*34)
    click=fit['click']
    tested_stop=click['paddle_meets_switch_case_deg']
    angle=.90*tested_stop
    pressed=[]
    for t in np.linspace(0,1,41):
        a=angle*math.sin(math.pi*t)**2
        tf=unpack(b.hinge_matrix(a))
        sample=deepcopy(state)
        for actor in TOUCH:sample[actor]=pack(tf @ unpack(state[actor]))
        travel=max(0.,b.FREE_TOP-(tf @ [*b.STATION,b.FREE_TOP,1])[2])
        sample['plunger']=pack(translation([0,0,-travel]) @ unpack(state['plunger']))
        pressed.append(sample)
    steps.append(dict(title='Press the lower half of the pad',caption='Press and release the centre and either lower corner. The switch should click and return freely.',duration=2,samples=pressed))
    mod=dict(label='OP1 and DFRobot paddle',rotation=old['rotation'],actors=actors,steps=steps,annotations=[],
             keysLabel='Key assembly',fitOuterKeysSeparately=True,note='The switch body locates the sleeve. The OP1 board outline and the touch-board hole positions use photo estimates.')
    modules['dfr']=mod
    modules['key']['actors']['carrier']=actors['carrier']
    modules['finger_rest']['actors']['carrier']=actors['carrier']
    rem=[reverse(steps[8],'Remove the OP1 retainer','Release its latch and slide the retainer out towards the front.'),
         reverse(steps[7],'Withdraw the hinge cap','Pull the cap straight back.'),
         reverse(steps[6],'Lift out the paddle','Lift both journals out of the open seats and clear the sleeve from the switch.')]
    remove_keys=[reverse(steps[1],'Lift out the mouse switch','Lift the switch straight up from its three sockets.'),
                 reverse(steps[0],'Lift the OP1 board','Lift the board straight up and guide the lead out of the open channel.')]
    remove_touch=[reverse(steps[5],'Move the paddle clear','Move the lifted paddle clear of the holder.'),
                  reverse(steps[4],'Remove the two clips','Slide both clips away from the post necks. Keep both clips.'),
                  reverse(steps[3],'Lift the touch board','Lift the board clear of the two posts.'),
                  reverse(steps[2],'Withdraw the post bar','Pull the loose two-post bar out from the underside of the paddle.')]
    modules['pin_hinge']=subset(mod,('carrier','cap','hinge_cap','lid','post_bar','switch','plunger',*SENSOR,*CLIPS),steps[2:]+rem+remove_touch,
                                'Open hinge and guide','The cap holds both built-in pivot ends in the open seats.')
    modules['op1_clips']=subset(mod,('carrier','lid',*BOARD,*SWITCH),steps[:2]+[steps[8],rem[0]]+remove_keys,
                                'OP1 board retainer','Install the touch paddle before sliding its retainer into place.')
    guide.update(revision='R53',physical_fit_verified=False)
    guide['print_components']['keys']=[v[0] for v in NAMES.values()]+['DFR_Clip_Left','DFR_Clip_Right']
    guide=full_length_rods(guide,OUT)
    files={a[k] for m in modules.values() for a in m['actors'].values() for k in ('file','morphFile') if k in a}
    digest=lambda p:sha256(p.read_bytes()).hexdigest()
    guide['sources']=dict(upstream_guide_sha256=digest(OLD/'assembly-guide.json'),generator_sha256=digest(Path(__file__)),
                          meshes_sha256={f:digest(OUT/f) for f in sorted(files)})
    return guide


if __name__=='__main__':
    fit=json.loads((OUT/'mechanical-fit.json').read_text())
    guide=build(fit)
    path=OUT/'assembly-guide.json'
    path.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    if '--register' in sys.argv:register_assembly(path,'r53','R53 · Open hinge and guided OP1 paddle',make_current=True,group_keys=True)
