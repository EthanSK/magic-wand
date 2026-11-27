"""Place the same pouch at its lower rail height throughout every R78 assembly view."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

import design78 as design
import guide77


def write(current=False):
    old_exports = guide77.d.OUT
    source = old_exports / 'assembly-guide.json'
    guide = json.loads(source.read_text())
    hashes = {}
    dx, dy, dz = design.PACK_OFFSET
    for module in guide['modules'].values():
        if 'status' in module:
            module['status'] = 'R78 · Physical fit untested'
        for actor in module['actors'].values():
            for field in ('file', 'morphFile'):
                if field not in actor:
                    continue
                target = (old_exports / actor[field]).resolve()
                if target == old_exports / design.HOLDER:
                    target = design.OUT / design.HOLDER
                actor[field] = path = relpath(target, design.OUT)
                if path not in hashes:
                    hashes[path] = sha256(target.read_bytes()).hexdigest()
        if 'battery' not in module['actors']:
            continue
        for step in module['steps']:
            for sample in step['samples']:
                if (pose := sample.get('battery')) is not None:
                    # Move the loading line as well as its seated endpoint.
                    pose[3] += dx
                    pose[7] += dy
                    pose[11] += dz
            if step['title'] == 'Slide in the battery':
                step['caption'] = ('Slide the disconnected pack in from the battery end. '
                                   'Leave about 4.5 mm beyond the back of the key holder. Keep the leads free.')
    guide['revision'] = 'R78'
    guide['physical_fit_verified'] = False
    guide['sources'] = dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                            upstream_guide_sha256=sha256(source.read_bytes()).hexdigest(),
                            meshes_sha256=hashes)
    path = design.OUT / 'assembly-guide.json'
    path.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    guide77.guide76.register_assembly(path, 'r78', 'R78 · Lower battery and smooth rails',
                                     group_keys=True, make_current=current)
    return path


if __name__ == '__main__':
    print(write('--current' in sys.argv))
