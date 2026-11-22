"""Compose the integral guard and cap-free battery into the existing full-rod assembly."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from design60 import OUT, PREVIOUS, HERE
from plate60 import LABELS

SOURCE = PREVIOUS / 'exports/assembly-guide.json'
OBSOLETE = {'guard_left','guard_right','battery_cap'}
DROP_STEPS = {'Slide on the left guard','Slide on the right guard','Push on the cap','Pull off the cap'}
INSERT = ('Slide the wrapped battery lengthwise into the open rails, with its wire and plug outside. '
          'The rounded side leaf flexes against the long edge. Stop if the cell binds.')


def build():
    guide=json.loads(SOURCE.read_text())
    modules=guide['modules']
    del modules['finger_guards']
    rest=modules['finger_rest']
    rest['rotation']=[-.34,3.03,.08]
    rest['note']='Both rounded finger guards are printed into the key holder.'
    rest['steps'][0]['caption']='Rest a fingertip across the round beams under each lower socket. Slide the socket and its backing strip in from the open side.'
    rest['annotations']=[]
    battery=modules['battery']
    battery['rotation']=[-.52,2.90,.15]
    battery['note']='The battery slides beside the rod. The integral side spring provides friction along its wrapped edge.'
    battery['annotations']=[]
    refs={}
    for module in modules.values():
        module['steps']=[s for s in module['steps'] if s['title'] not in DROP_STEPS]
        for actor in OBSOLETE:
            module['actors'].pop(actor,None)
        for name,actor in module['actors'].items():
            if name=='carrier':
                actor['label']='Key holder with rounded finger beams and integral battery spring'
            for field in ('file','morphFile'):
                if field not in actor:
                    continue
                path=actor[field]
                if path not in ('Key_Carrier-assembly.stl','Battery_Pack-assembly.stl'):
                    path=os.path.relpath((SOURCE.parent/path).resolve(), OUT)
                    actor[field]=path
                refs[path]=sha256((OUT/path).read_bytes()).hexdigest()
        for step in module['steps']:
            if step['title']=='Slide in the battery':
                step['caption']=INSERT
            elif step['title']=='Remove the battery':
                step['caption']='Hold the exposed end of the wrapped cell and slide it straight back along the rod.'
            for sample in step['samples']:
                for name in OBSOLETE:
                    sample.pop(name,None)
    whole=modules['whole']
    whole['note']='The battery and both finger guards are carried by the keys on the 500 mm rod.'
    whole['finalCaption']='Check the battery holds in the rails, the pad clicks freely, and all wires clear the controls.'
    guide.update(revision='R60',sources=dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                 upstream_guide_sha256=sha256(SOURCE.read_bytes()).hexdigest(),meshes_sha256=refs))
    del guide['r59_changes']
    guide['print_components']['keys']=list(LABELS)
    guide['reuse_components']['note']='The standalone kit includes every printed key-holder part and a spare centre clip.'
    guide['optional_components']['note']='The two flat strips support the sockets while pressing the lower switches in. The extra hinge pin gives a second fit.'
    return guide


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--register',action='store_true')
    args=parser.parse_args()
    path=OUT/'assembly-guide.json'
    path.write_text(json.dumps(build(),separators=(',',':'),allow_nan=False)+'\n')
    if args.register:
        sys.path.insert(0,str(HERE.parent/'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(path,'r60','R60 trial · Integral rounded guards and friction-fit battery',group_keys=True)
