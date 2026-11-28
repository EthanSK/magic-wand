"""Use the same fitted assembly and animation, binding the repair parts to their new meshes."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

from plate80 import OUT, parts, previous
from guide76 import register_assembly


def write(current=False):
    baseline = previous.OUT / 'assembly-guide.json'
    guide = json.loads(baseline.read_text())
    repair = {row['source'].name: row['source'] for row in parts()}
    hits, hashes = set(), {}
    for module in guide['modules'].values():
        if 'status' in module:
            module['status'] = 'R80 · Physical fit untested'
        if 'post_bar' in module['actors']:
            module['actors']['post_bar']['label'] = 'Two-post bar with wider board seats and narrow clip necks'
        for actor in module['actors'].values():
            for field in ('file', 'morphFile'):
                if field not in actor:
                    continue
                original = (baseline.parent / actor[field]).resolve()
                target = repair.get(original.name, original)
                if original.name in repair:
                    hits.add(original.name)
                actor[field] = name = relpath(target, OUT)
                if name not in hashes:
                    hashes[name] = sha256(target.read_bytes()).hexdigest()
        for step in module['steps']:
            if step['title'] == 'Insert the two-post bar':
                step['caption'] = ('With the paddle off the holder, line up both posts underneath it. '
                                   'Push the bar up squarely until the spring tips pass through and the bar seats.')
    assert hits == set(repair), (hits, repair.keys())
    guide['revision'] = 'R80'
    guide['physical_fit_verified'] = False
    guide['print_components']['keys'] = sorted(row['name'] for row in parts())
    guide['optional_components']['note'] = ('The plate contains the touchpad repair parts and both flat board clips. '
        'Reuse the fixed key holder and its hinge pin and retaining clip.')
    guide['sources'] = dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                            upstream_guide_sha256=sha256(baseline.read_bytes()).hexdigest(), meshes_sha256=hashes)
    path = OUT / 'assembly-guide.json'
    path.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    register_assembly(path, 'r80', 'R80 · Touchpad board posts and paddle clearance', group_keys=True, make_current=current)


if __name__ == '__main__':
    write('--current' in sys.argv)
