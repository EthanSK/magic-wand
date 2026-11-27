"""Publish the photographed click-end view alongside the full assembly."""
from hashlib import sha256
import json
from math import pi
from os.path import relpath
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
PRIOR = HERE.parent / 'carbon-rod-holders-r74-smooth-through' / 'exports'
VIEWER = HERE.parent / 'carbon-rod-holders' / 'assembly'
HOLDER = 'Key_Carrier-assembly.stl'


def write():
    source = PRIOR / 'assembly-guide.json'
    guide = json.loads(source.read_text())
    hashes = {}
    for module in guide['modules'].values():
        if 'status' in module:
            module['status'] = 'R75 shape preview'
        for actor in module['actors'].values():
            for field in ('file', 'morphFile'):
                if field not in actor:
                    continue
                target = (PRIOR / actor[field]).resolve(strict=True)
                if target == PRIOR / HOLDER:
                    target = (OUT / HOLDER).resolve(strict=True)
                actor[field] = name = relpath(target, OUT)
                if name not in hashes:
                    hashes[name] = sha256(target.read_bytes()).hexdigest()
    ident = [1,0,0,0,0,1,0,0,0,0,1,0]
    guide['modules']['finger_rest'] = dict(
        label='Click-end finger rest', status='R75 shape preview',
        note='The battery slot is at the far end. Rotate the model to see where each rounded arm meets the click end.',
        actors={'carrier':guide['modules']['key']['actors']['carrier']},
        rotation=[-.24,pi,0], steps=[dict(title='Index finger at the click end',
        caption='The two forks run into the near edge, where your index finger rests. The battery slot is at the opposite end.',
        duration=2, samples=[{'carrier':ident},{'carrier':ident}])])
    guide['revision']='R75'
    guide['physical_fit_verified']=False
    guide['sources']=dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                          upstream_guide_sha256=sha256(source.read_bytes()).hexdigest(),meshes_sha256=hashes)
    path=OUT/'assembly-guide.json'
    path.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    sys.path.insert(0,str(VIEWER))
    from register_assembly import register_assembly
    register_assembly(path,'r75','R75 · Click-end finger rest preview',group_keys=True,make_current=True)
    return path


if __name__=='__main__':
    print(write())
