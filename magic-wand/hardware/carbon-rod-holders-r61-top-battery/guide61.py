"""Use the checked R61 solids and connector-down seating path in each assembly view."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from design61 import FLIP, HERE, OUT, REAR, b, k, m, prior

SOURCE = prior.OUT / 'assembly-guide.json'
MESHES = dict(carrier='Key_Carrier', cap='Touch_Paddle', battery='Battery_Pack',
              hinge_pin='Hinge_Pin', pin_clip='Pin_Clip')
BOARD_IDS = ('sensor','electrode','connector','sensor_lead','gravity_plug','flat_electrode')
RIDERS = (*BOARD_IDS,'cap','post_bar','clip_left','clip_right','pin_clip')

def matrix(pose):
    return np.vstack([np.asarray(pose).reshape(3,4),[0,0,0,1]])

def pack(transform):
    return transform[:3,:].ravel().tolist()

def board_assets(module):
    shift=(0,-k.r.CLICK_SHIFT,0)
    originals={n:b.load(prior.OUT/module['actors'][n]['file']) for n in ('sensor','electrode','connector')}
    for name,solid in originals.items():
        b.save_closed(OUT/f'{name}-down.stl',solid.transform(FLIP))
    b.save_closed(OUT/'flat_electrode.stl',originals['electrode'])
    for name,mesh in [('gravity_plug','Gravity_Plug'),('sensor_lead','Gravity_Wires')]:
        b.save_closed(OUT/f'{name}-down.stl', b.load(OUT/f'{mesh}-assembly.stl').translate(shift))

def connector_down(module, stop):
    actors=module['actors']
    del actors['gravity_pins']
    actors['flat_electrode']=dict(actors['electrode'],label='Flat gold finger pad',file='flat_electrode.stl')
    actors['gravity_plug']=dict(actors['connector'],label='Three-pin Gravity lead plug',file='gravity_plug-down.stl')
    for name,label in [('sensor','DFR0030 touch board, flat face up'),('electrode','Component-side electrode'),
                       ('connector','White Gravity socket under the board'),('sensor_lead','Three wires exiting beside the hinge')]:
        actors[name].update(file=f'{name}-down.stl',label=label)
    pressing=next(s for s in module['steps'] if s['title'].startswith('Press the lower'))
    old_max=max(math.atan2(f['cap'][9],f['cap'][5]) for f in pressing['samples'])
    for step in module['steps']:
        for frame in step['samples']:
            frame.pop('gravity_pins',None)
            for name in BOARD_IDS[1:]:
                frame[name]=list(frame['sensor'])
            angle=math.atan2(frame['cap'][9],frame['cap'][5])
            if abs(angle)>1e-9:
                new=matrix(m.hinge_matrix(stop*.97*angle/old_max))
                new[:3,3]+=np.array([0,REAR,0])-new[:3,:3]@np.array([0,REAR,0])
                delta=new @ np.linalg.inv(matrix(frame['cap']))
                for name in RIDERS:
                    if name!='pin_clip' or abs(frame[name][9])>1e-9:
                        frame[name]=pack(delta @ matrix(frame[name]))
        if step['title']=='Seat the touch board':
            step['caption']='With the flat gold face up, lower the plugged-in board over both posts. The white socket faces down and the three wires turn out through the open right edge before the hinge.'
        if step['title']=='Lift the touch board':
            step['caption']='Lift the wired board straight off both posts. The lead lifts out through the open side with the board.'
    # Show the connector mating while the board is still in free space.
    i=next(i for i,s in enumerate(module['steps']) if s['title']=='Seat the touch board')
    for step in module['steps'][:i]:
        for frame in step['samples']:
            for name in ('gravity_plug','sensor_lead'):
                frame[name][7]+=9
    start=module['steps'][i]['samples'][0]
    samples=[]
    for t in np.linspace(0,1,25):
        frame=deepcopy(start)
        for name in ('gravity_plug','sensor_lead'):
            frame[name][7]+=9*(1-t)
        samples.append(frame)
    module['steps'].insert(i,dict(title='Connect the Gravity lead',caption='Plug the three-wire lead into the white socket on the underside while the touch board is still loose.',duration=2,samples=samples))
    module['note']='The flat gold face sits uppermost. The white socket and plug sit under the board. Leave the three wires free to bend beside the hinge.'
    for note in module.get('annotations',[]):
        if note.get('actor')=='pin_clip':
            note['point'][1]+=REAR
            note['title']='Press this clip over the groove in the hinge pin. The three wires leave through the open side in front of the hinge.'

def build():
    g=json.loads(SOURCE.read_text())
    board_assets(g['modules']['dfr'])
    refs={}
    stop=json.loads((OUT/'click-fit.json').read_text())['case_stop_deg']
    for mod in g['modules'].values():
        for name,actor in mod['actors'].items():
            for f in ('file','morphFile'):
                if f in actor:
                    actor[f]=(MESHES[name]+'-assembly.stl' if f=='file' and name in MESHES
                              else os.path.relpath((prior.OUT/actor[f]).resolve(),OUT))
        if 'sensor' in mod['actors']:
            connector_down(mod,stop)
        for actor in mod['actors'].values():
            for f in ('file','morphFile'):
                if f in actor and actor[f] not in refs:
                    refs[actor[f]]=sha256((OUT/actor[f]).read_bytes()).hexdigest()
    for n in ('battery','key'):
        step=next(s for s in g['modules'][n]['steps'] if s['title']=='Slide in the battery')
        step['caption']='At the narrow top extension, slide the wrapped cell along the rod into the rounded rails. Leave the lead and plug outside. Stop if the cell binds.'
    g['modules']['finger_rest']['note']='The integral rounded beams slope gradually from both ends and leave the sockets accessible from the side.'
    g.update(revision='R61',sources=dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
             upstream_guide_sha256=sha256(SOURCE.read_bytes()).hexdigest(),meshes_sha256=refs))
    return g

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--register',action='store_true')
    args=parser.parse_args()
    dst=OUT/'assembly-guide.json'
    dst.write_text(json.dumps(build(),separators=(',',':'),allow_nan=False)+'\n')
    if args.register:
        sys.path.insert(0,str(HERE.parent/'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(dst,'r61','R61 trial · Upper battery cradle and connector-down touch board',group_keys=True)
