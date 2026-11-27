"""Show the repaired fixed bearing and the original flat slide-on board clips."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

import plate79 as plate
from guide76 import register_assembly

CAPTIONS = {
    'Slide on the two small clips': 'Seat the touch board on the paddle. Lay each flat clip on the board and slide its open end around the narrow part of the post, under the head.',
    'Remove the two clips': 'Support the two-post bar and slide each flat clip straight back off its post.',
}


def write(current=False):
    upstream = plate.old.OUT / 'assembly-guide.json'
    guide = json.loads(upstream.read_text())
    replacements = {plate.old.OUT / plate.design.HOLDER: plate.OUT / plate.design.HOLDER}
    for side, filename in plate.posts.CLIPS.items():
        replacements[plate.posts.OUT / filename] = plate.posts.R59_CLIPS[side]
    hashes = {}
    for module in guide['modules'].values():
        if 'status' in module:
            module['status'] = 'R79 · Physical fit untested'
        for key, actor in module['actors'].items():
            for field in ('file','morphFile'):
                if field not in actor:
                    continue
                src = (upstream.parent / actor[field]).resolve()
                target = replacements.get(src,src)
                actor[field] = name = relpath(target,plate.OUT)
                if name not in hashes:
                    hashes[name] = sha256(target.read_bytes()).hexdigest()
            if key in ('clip_left','clip_right'):
                actor['label'] = 'Flat touch-board clip, ' + key.split('_')[1]
        for step in module['steps']:
            if step['title'] in CAPTIONS:
                step['caption'] = CAPTIONS[step['title']]
    guide['revision'] = 'R79'
    guide['physical_fit_verified'] = False
    guide['print_components']['keys'] = sorted(plate.LABELS)
    guide['optional_components']['note'] = ('Reuse the moving touch paddle from R78. The replacement plate includes the carrier, '
        'the two flat board clips, post bar, hinge pin, pin clip and spare, and the OP1 retainer.')
    guide['sources'] = dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                            upstream_guide_sha256=sha256(upstream.read_bytes()).hexdigest(), meshes_sha256=hashes)
    path = plate.OUT / 'assembly-guide.json'
    path.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    register_assembly(path,'r79','R79 · Easier hinge release and flat board clips',group_keys=True,make_current=current)


if __name__ == '__main__':
    write('--current' in sys.argv)
