"""Show the current carrier and the complete forward battery removal path."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

import kit74

INSERT = ('Fit the battery last. Guide the battery between the rails from the rear until its end '
          'is level with the back of the holder. Keep the connector outside and leave slack in the leads.')
REMOVE = ('With the battery disconnected, push on the wrapped end and slide the pack out through '
          'the front. Support it as it leaves the rails. You can also slide it back out the way it went in.')


def write(register=False):
    old = kit74.kit73.model
    previous = old.OUT / 'assembly-guide.json'
    guide = json.loads(previous.read_text())
    guide['revision'] = 'R74'
    hashes = {}
    for module in guide['modules'].values():
        if 'status' in module:
            module['status'] = 'R74 design · physical fit untested'
        for actor in module['actors'].values():
            for field in ('file', 'morphFile'):
                if field not in actor:
                    continue
                path = (old.OUT / actor[field]).resolve(strict=True)
                if path == old.OUT / kit74.HOLDER:
                    path = kit74.OUT / kit74.HOLDER
                name = relpath(path, kit74.OUT)
                actor[field] = name
                if name not in hashes:
                    hashes[name] = sha256(path.read_bytes()).hexdigest()
    battery = guide['modules']['battery']
    install, remove = battery['steps']
    install['caption'] = INSERT
    remove['caption'] = REMOVE
    # Keep the installed position used by the complete assembly. Continue the
    # pack forward until its trailing end visibly clears the front of the body.
    poses = [sample['battery'] for sample in remove['samples']]
    start, end = poses[0][7], poses[-1][7]
    carrier = old.b.load(kit74.OUT / kit74.HOLDER)
    pack = old.design.pack().translate((old.prior.INBOARD, 0, 0))
    travel = carrier.bounding_box()[1] - pack.bounding_box()[4] - 2.
    for pose in poses:
        fraction = (pose[7] - start) / (end - start)
        pose[7] = start + fraction * travel
    for step in guide['modules']['key']['steps']:
        if step['title'] == install['title']:
            step['caption'] = INSERT
    battery['note'] = ('The side spring grips the pack between two open-ended rails. '
                       'Take the battery out before changing either left socket.')
    guide['optional_components']['note'] = guide['optional_components']['note'].replace('R73 plate', 'R74 plate')
    guide['sources'] = dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                            upstream_guide_sha256=sha256(previous.read_bytes()).hexdigest(), meshes_sha256=hashes)
    assert kit74.HOLDER in hashes
    out = kit74.OUT / 'assembly-guide.json'
    out.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    if register:
        sys.path.insert(0, str(kit74.HERE.parent / 'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(out, 'r74', 'R74 · Smooth guard and open battery slot', group_keys=True, make_current=True)
    return out


if __name__ == '__main__':
    print(write('--current' in sys.argv))
