"""Reuse the R64 hinge assembly and show the exact R65 OP1 insertion in both directions."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import kit65
import design65

OUT = kit65.OUT
PARENT_GUIDE = kit65.kit64.OUT / 'assembly-guide.json'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def install_sled(module, path, loading):
    if not any(s['title'] == 'Seat the OP1 board' for s in module['steps']):
        return
    module['actors'][design65.SLED] = dict(file=design65.SLED_FILE,
        label='Removable OP1 board seat', color='#c98140')
    sequence = []
    for step in module['steps']:
        title = step['title']
        if title in ('Seat the OP1 board', 'Lift the OP1 board'):
            inserting = title == 'Seat the OP1 board'
            fixed = {k:t for k,t in step['samples'][0].items() if k not in design65.ACTORS}
            step['samples'] = [dict(fixed, **pose) for pose in (path if inserting else reversed(path))]
            step['caption'] = design65.INSERT_CAPTION if inserting else design65.REMOVE_CAPTION
            stage = dict(step, duration=1.8,
                title='Place the board on its seat' if inserting else 'Lift the board off its seat',
                caption=('Outside the holder, lower the wired board onto the loose printed seat. '
                         'The three metal sockets pass through its holes.' if inserting else
                         'With the seat outside the holder, lift the board straight off.'))
            stage['samples'] = [dict(fixed, **pose) for pose in (loading if inserting else reversed(loading))]
            sequence.extend((stage, step) if inserting else (step, stage))
        else:
            for sample in step['samples']:
                if 'board' in sample:
                    sample[design65.SLED] = path[-1][design65.SLED]
            sequence.append(step)
    module['steps'] = sequence
    for label in module.get('annotations', []):
        if label.get('step') == 'Seat the OP1 board':
            if label['actor'] == 'carrier':
                label['title'] = 'Slide the loaded seat into the opening beside the rod.'
            elif label['actor'] == 'board':
                label.update(actor=design65.SLED, title='The seat lands on the two carrier ledges under the board.')
        elif label.get('step') == 'Fit the OP1 retainer' and label['actor'] == 'carrier':
            label['title'] = 'The upper rails guide the retainer over the board and hold the loaded seat down.'


def write(current=False):
    guide = json.loads(PARENT_GUIDE.read_text())
    hashes = {}
    positions = design65.entry_samples()
    loading = design65.seat_samples()
    for module in guide['modules'].values():
        for name, actor in module['actors'].items():
            for field in ('file', 'morphFile'):
                if field not in actor:
                    continue
                src = (PARENT_GUIDE.parent / actor[field]).resolve(strict=True)
                if name == 'carrier' and field == 'file' and src == kit65.kit64.OUT / 'Key_Carrier-assembly.stl':
                    src = OUT / src.name
                relative = os.path.relpath(src, OUT)
                actor[field] = relative
                if relative not in hashes:
                    hashes[relative] = digest(src)
        if 'status' in module:
            module['status'] = 'R65 design · physical fit untested'
        install_sled(module, positions, loading)
    hashes[design65.SLED_FILE] = digest(OUT/design65.SLED_FILE)
    guide['print_components']['keys'] = sorted(row['name'] for row in kit65.parts())
    guide['revision'] = 'R65'
    guide['sources'] = dict(generator_sha256=digest(Path(__file__)), upstream_guide_sha256=digest(PARENT_GUIDE),
                            meshes_sha256=hashes)
    dest = OUT / 'assembly-guide.json'
    dest.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    sys.path.insert(0, str(kit65.HERE.parent / 'carbon-rod-holders/assembly'))
    from register_assembly import register_assembly
    register_assembly(dest, 'r65', 'R65 · Restored OP1 board seat', group_keys=True, make_current=current)


if __name__ == '__main__':
    write('--current' in sys.argv)
