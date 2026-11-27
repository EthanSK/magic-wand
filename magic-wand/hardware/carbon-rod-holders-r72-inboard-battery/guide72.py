"""Generate the R72 viewer from R71's sampled assembly motions and shared parts."""
from hashlib import sha256
import json
from os.path import relpath
import sys
from pathlib import Path

import design72 as model


def write(register=False):
    source = model.prev.OUT / 'assembly-guide.json'
    guide = json.loads(source.read_text())
    original = model.prev.OUT / model.HOLDER
    hashes = {}
    moved = 0
    for module in guide['modules'].values():
        if 'status' in module:
            module['status'] = 'R72 design · physical fit untested'
        for actor in module['actors'].values():
            for field in ('file', 'morphFile'):
                if field not in actor:
                    continue
                path = (source.parent / actor[field]).resolve(strict=True)
                if path == original:
                    path = model.OUT / model.HOLDER
                actor[field] = relpath(path, model.OUT)
                if actor[field] not in hashes:
                    hashes[actor[field]] = sha256(path.read_bytes()).hexdigest()
        for step in module['steps']:
            for pose in step['samples']:
                if 'battery' in pose:
                    pose['battery'][3] += model.INBOARD
                    moved += 1
    if not moved or model.HOLDER not in hashes:
        raise ValueError('No assembled battery or carrier found in base guide')
    guide['revision'] = 'R72'
    guide['optional_components']['note'] = guide['optional_components']['note'].replace('R71 plate', 'R72 plate')
    guide['r72_changes'] = dict(battery_inboard_mm=model.INBOARD, moved_battery_poses=moved,
                                lower_guard='Two rounded branches on the battery side')
    guide['sources'] = dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                            upstream_guide_sha256=sha256(source.read_bytes()).hexdigest(), meshes_sha256=hashes)
    out = model.OUT / 'assembly-guide.json'
    out.write_text(json.dumps(guide,separators=(',', ':'),allow_nan=False) + '\n')
    if register:
        sys.path.insert(0, str(model.HERE.parent / 'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(out, 'r72','R72 · Inboard battery and forked finger guard', group_keys=True, make_current=True)
    return out


if __name__ == '__main__':
    print(write('--current' in sys.argv))
