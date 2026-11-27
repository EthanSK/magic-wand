"""Publish the checked finger-rest shape and the actual rear battery service motion."""
from copy import deepcopy
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys
import design76 as model

OUT = model.OUT
VIEWER = model.HERE.parent / 'carbon-rod-holders/assembly'
sys.path.insert(0, str(VIEWER))
from register_assembly import register_assembly


def write(current=False):
    prior = model.old.OUT
    source = prior / 'assembly-guide.json'
    guide = json.loads(source.read_text())
    hashes = {}
    for module in guide['modules'].values():
        if 'status' in module:
            module['status'] = 'R76 · Physical fit untested'
        for actor in module['actors'].values():
            for key in ('file','morphFile'):
                if key not in actor:
                    continue
                target = (prior/actor[key]).resolve(strict=True)
                if target == prior / model.HOLDER:
                    target = OUT / model.HOLDER
                actor[key] = relative = relpath(target,OUT)
                if relative not in hashes:
                    hashes[relative] = sha256(target.read_bytes()).hexdigest()
        if 'battery' in module['actors']:
            for step in module['steps']:
                for sample in step['samples']:
                    if sample.get('battery') is not None:
                        sample['battery'][7] += model.PACK_PROJECTION
    battery = guide['modules']['battery']
    install, remove = battery['steps']
    install['caption'] = (f'Slide the disconnected pack in from the battery end. Leave about {model.PACK_PROJECTION:g} mm '
                          'showing past the ends of the rails and keep the leads free.')
    remove['caption'] = 'Disconnect the pack. Push on its wrapped end and slide it back out through the same opening.'
    # Use the same sampled path in reverse. This also keeps the neighbouring
    # step endpoints identical when the user scrubs the animation backwards.
    remove['samples'] = deepcopy(install['samples'][::-1])
    battery['note'] = 'Fit and remove the pack at the battery end. The rounded guard sits at the click end.'
    key = guide['modules']['key']
    next(s for s in key['steps'] if s['title']==install['title'])['caption'] = install['caption']
    rest = guide['modules']['finger_rest']
    # Show the purchased parts in their installed positions in the same view as
    # the guard. A bare-carrier view hid precisely which side the socket loads on.
    seated = key['steps'][-1]['samples'][-1]
    rest_step = rest['steps'][0]
    for name in ('battery', 'socket_0', 'socket_2', 'socket_3', 'socket_4'):
        rest['actors'][name] = deepcopy(key['actors'][name])
        for sample in rest_step['samples']:
            sample[name] = list(seated[name])
    rest['note'] = 'The click is at the bottom. The guard on the right sits beside the battery.'
    rest['steps'][0]['caption'] = 'Both rod-side curves and the open loops follow the same shape. The outside branch bends locally around the sideways-loading key socket.'
    guide['revision'] = 'R76'
    guide['physical_fit_verified'] = False
    guide['sources'] = dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                            upstream_guide_sha256=sha256(source.read_bytes()).hexdigest(),meshes_sha256=hashes)
    path = OUT / 'assembly-guide.json'
    path.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    register_assembly(path,'r76','R76 · Matching click-end finger rests',group_keys=True,make_current=current)
    return path


if __name__=='__main__':
    print(write('--current' in sys.argv))
