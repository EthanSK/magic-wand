"""Build the viewer from the same seated key positions and wire geometry as the fit checks."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

import design77 as d
import guide76


def update_keys(module):
    for step in module['steps']:
        for sample in step['samples']:
            for actor in ('socket_0', 'switch_0'):
                matrix = sample.get(actor)
                if matrix is not None:
                    # Undo the previous quarter turn, looking at the underside.
                    for i in (0, 4, 8):
                        matrix[i], matrix[i + 1] = -matrix[i + 1], matrix[i]
            for actor in ('socket_3', 'switch_3'):
                if sample.get(actor) is not None:
                    sample[actor][7] += d.UPPER_MOVE
    slide = next(
        (s for s in module['steps'] if s['title'] == 'Slide In the Lower-Left Socket'), None
    )
    if slide is None:
        return
    slide['caption'] = (
        'Slide the wired socket in from the outside edge, slightly towards the hinge. '
        'Centre it below the two contacts, then lift it onto them.'
    )
    seated = slide['samples'][-1]['socket_0'].copy()
    for sample, offset in zip(slide['samples'], d.lower_slide(), strict=True):
        for index, delta in zip((3, 7, 11), offset):
            sample['socket_0'][index] = seated[index] + delta
    for sample in module['steps'][0]['samples']:
        sample['socket_0'] = slide['samples'][0]['socket_0'].copy()
    module['note'] = (
        'Both pairs of keys are spaced equally. Fit each black socket before pressing the switch in '
        'from above. Fit the battery last, with the soldered wires flat against the backplate.'
    )


def write(current=False):
    prior = d.old.OUT
    source = prior / 'assembly-guide.json'
    guide = json.loads(source.read_text())
    hashes = {}
    for name, module in guide['modules'].items():
        if 'status' in module:
            module['status'] = 'R77 · Physical fit untested'
        for actor in module['actors'].values():
            for key in ('file', 'morphFile'):
                if key not in actor:
                    continue
                target = (prior / actor[key]).resolve(strict=True)
                if target.name in (d.HOLDER, d.PADDLE, d.WIRES):
                    target = d.OUT / target.name
                actor[key] = relative = relpath(target, d.OUT)
                if relative not in hashes:
                    hashes[relative] = sha256(target.read_bytes()).hexdigest()
        if 'socket_0' in module['actors']:
            update_keys(module)
        if 'sensor_lead' in module['actors']:
            module['note'] = (
                'Fit the OP1 board, switch and paddle in order. Run the three touchpad wires '
                'straight towards the top of the keypad, between the matching hinge arms and over the pin clip.'
            )
            for step in module['steps']:
                if step['title'] == 'Seat the touch board':
                    step['caption'] = (
                        'With the flat gold face up and the white connector underneath, lower the board '
                        'over both posts. Guide the wires straight out between the hinge arms.'
                    )
                if step['title'] == 'Lift the touch board':
                    step[
                        'caption'
                    ] = 'Lift the board off both posts, guiding the wires up between the hinge arms.'
    rest = guide['modules']['finger_rest']
    rest['steps'][0]['caption'] = (
        'The two long branches on each side follow the same rounded curves. '
        'Beside the battery, the guard is open at the outside edge so the black socket can slide in.'
    )
    guide['revision'] = 'R77'
    guide['physical_fit_verified'] = False
    guide['sources'] = dict(
        generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        upstream_guide_sha256=sha256(source.read_bytes()).hexdigest(),
        meshes_sha256=hashes,
    )
    path = d.OUT / 'assembly-guide.json'
    path.write_text(json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n')
    guide76.register_assembly(
        path, 'r77', 'R77 · Even keys and straight wire exit', group_keys=True, make_current=current
    )
    return path


if __name__ == '__main__':
    print(write('--current' in sys.argv))
