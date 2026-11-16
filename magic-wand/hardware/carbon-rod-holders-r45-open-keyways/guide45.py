"""Compose the current assembly and cleanup animation from canonical parts.

Ethan's 'assembly thing' uses the same carrier exported for the selected slice.
Other components keep their existing sources; this is not another editable CAD.
"""
import argparse
import hashlib
import json
import os
import math
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE.parent / 'carbon-rod-holders-r44-middle-finger-rest/exports/assembly-guide.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pose(z=0, y=0, x=0):
    return [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z]


def highest_z(path):
    """Read every vertex of our binary STL without another geometry runtime."""
    raw = path.read_bytes()
    count, = struct.unpack_from('<I', raw, 80)
    if len(raw) != 84 + 50 * count or not count:
        raise ValueError('Expected a nonempty generated binary STL')
    return max(max(row[5], row[8], row[11])
               for row in struct.iter_unpack('<12fH', raw[84:]))


def build(parts):
    exports = HERE / 'exports'
    guide = json.loads(UPSTREAM.read_text())
    assets = {}

    def reference(source):
        source = source.resolve()
        relative = Path(os.path.relpath(source, exports)).as_posix()
        assets[relative] = sha(source)
        return relative

    for module in guide['modules'].values():
        for actor in module['actors'].values():
            for key in ('file', 'morphFile'):
                if key not in actor:
                    continue
                source = UPSTREAM.parent / actor[key]
                if key == 'file' and source.name == 'Key_Carrier-assembly.stl':
                    source = parts / 'R45-Key-Carrier-assembly.stl'
                actor[key] = reference(source)

    guide['revision'] = HERE.name
    guide['physical_fit_verified'] = False
    guide['modules']['key']['label'] = 'Fit the Choc switches'
    guide['modules']['xiao']['label'] = 'XIAO holder and keeper'
    guide['modules']['xiao_latch']['label'] = 'XIAO keeper detail'
    guide['modules']['finger_rest']['note'] = (
        'The joined, rounded finger rests retain their R44 positions. '
        'Comfort and strength need a physical trial.')
    key_note = (
        'R45 retains the R44 key, OP1, touch board and rod positions. '
        'The raised switch seats retain their positions. '
        'Remove every print helper shown in the cleanup animation before assembly. '
        'Bought board and connector dimensions include estimates; physical fit is unverified.')
    guide['modules']['key']['note'] = key_note
    guide['modules']['dfr']['note'] = key_note
    guide['modules']['whole']['note'] = (
        'R45 key holder with the matching existing DFRobot bracket, XIAO, battery and cable parts. '
        'Only the key holder and its disposable print helpers are on this trial plate. '
        'External wiring lengths are illustrative.')
    for module_name in ('key', 'dfr'):
        step = guide['modules'][module_name]['steps'][0]
        step['title'] = 'Remove the print cradle first'
        step['caption'] = (
            'Open Remove print support for the cleanup animation. Work on the cool part. '
            'Remove the orange cradle first, green front shelf next, then thin yellow bed tabs '
            'before fitting any hardware. '
            'Do not pull on the finger rests or force support through a key opening.')

    # The delivered audit owns the removal order and the side-helper direction.
    # Generate the animation from those receipts, rather than keeping another
    # independently maintained order or leaving the old 32-mm travel constant.
    audit_path = parts / 'candidate-audit.json'
    audit = json.loads(audit_path.read_text())
    order = [item.split(':', 1)[0].strip() for item in audit['removal_order']]
    supported = {'External_cradle', 'Front_pull_shelf', 'Rear_pull_shelf', 'Release_tabs'}
    if set(order) != set(audit['owners']) - {'Key_Carrier'} or not set(order) <= supported:
        raise ValueError('Cleanup inventory does not match the audited native owners')
    shelf_receipts = {}
    for owner, name in (('Front_pull_shelf', 'shelf-cad.json'),
                        ('Rear_pull_shelf', 'rear-shelf-cad.json')):
        if owner in order:
            receipt = json.loads((parts / name).read_text())
            if receipt['owner'] != owner:
                raise ValueError('Side-helper receipt names a different owner')
            shelf_receipts[owner] = receipt
    finger_comb = shelf_receipts.get('Front_pull_shelf', {}).get('generator_file') == 'standing_comb45.py'
    definition = {
        'External_cradle': ('cradle', 'Disposable external cradle pieces',
                            'R45-external-cradle.stl', '#e19753', 'orange cradle pieces'),
        'Front_pull_shelf': ('shelf', 'Disposable finger-side comb' if finger_comb else 'Disposable front-pull shelf',
                             'R45-front-pull-shelf.stl', '#a3c8a4', 'green finger-side comb' if finger_comb else 'green front shelf'),
        'Rear_pull_shelf': ('rear_shelf', 'Disposable rear support',
                            'R45-rear-pull-shelf.stl', '#b59ada', 'purple rear support'),
        'Release_tabs': ('tabs', 'Disposable thin bed tabs',
                         'R45-release-tabs.stl', '#ffdd68', 'yellow bed tabs'),
    }
    # A native owner can contain more than one real, disconnected helper.
    # Animate the exported pieces in their checked physical removal order,
    # rather than making several supports appear to be one pull-out part.
    cleanup = []
    for owner in order:
        actor, label, filename, color, description = definition[owner]
        pieces = shelf_receipts.get(owner, {}).get('removable_pieces')
        if pieces:
            if (owner != 'Front_pull_shelf' or not audit['individual_front_piece_release']['clear']
                    or audit['individual_front_piece_release']['unassigned_or_ambiguous_samples']):
                raise ValueError('Missing individual native support-removal checks')
            indices = [piece['removal_order'] for piece in pieces]
            if indices != sorted(set(indices)):
                raise ValueError('Ambiguous physical support-removal order')
            names = {
                'R45-finger-side-comb.stl': ('Disposable finger-side comb', 'green comb'),
                'R45-left-guard-web-prop.stl': ('Disposable web prop', 'green web prop'),
            }
            for index, piece in enumerate(pieces):
                filename = piece['file']
                if sha(parts / filename) != piece['sha256']:
                    raise ValueError('Physical support mesh changed after its check')
                label, description = names[filename]
                cleanup.append(dict(owner=owner, actor=f'{actor}_{index}', label=label,
                                    filename=filename, color=color, description=description,
                                    motion=piece, web_prop=filename == 'R45-left-guard-web-prop.stl'))
        else:
            cleanup.append(dict(owner=owner, actor=actor, label=label, filename=filename,
                                color=color, description=description,
                                motion=shelf_receipts.get(owner), web_prop=False))
    actors = {'carrier': {'label': 'Permanent key holder',
                          'file': reference(parts / 'R45-Key-Carrier.stl'), 'color': '#29a5b7'}}
    for piece in cleanup:
        actors[piece['actor']] = {'label': piece['label'],
                                  'file': reference(parts / piece['filename']), 'color': piece['color']}
    state = {actor: pose() for actor in actors}
    disposable_names = [piece['description'] for piece in cleanup]
    description = ', '.join(disposable_names[:-1]) + ' and ' + disposable_names[-1]
    steps = [{'title': 'Identify the disposable pieces', 'duration': 3,
              'caption': 'Blue stays. Remove the ' + description + ' after cooling. '
                         'Some assembly paths remain blocked until cleanup.',
              'samples': [{key: value[:] for key, value in state.items()}]}]
    for piece in cleanup:
        owner, actor, filename = piece['owner'], piece['actor'], piece['filename']
        vector = [0., 0., 0.]
        if owner == 'External_cradle':
            vector[2] = -math.ceil(highest_z(parts / filename) + 4.)
            title = 'Release the external cradle'
            caption = ('Hold the blue holder at its solid frame. Release the orange pieces '
                       'from their accessible feet, following the motion shown. Work one piece '
                       'at a time; never lever against the finger rests. Stop if the holder bends.')
        elif owner == 'Release_tabs':
            vector[2] = -18.
            title = 'Remove the thin bed tabs'
            caption = ('Peel or carefully trim the yellow tabs at their plate-facing contacts. '
                       'Check the key openings, rod clips, hinge holes and wire paths before assembly.')
        else:
            receipt = piece['motion']
            vector = [float(v) * float(receipt['translation_mm']) for v in receipt['direction_print']]
            if piece['web_prop']:
                title = 'Slide out the web prop'
                caption = ('Grip the small green prop at its wide foot and slide it straight '
                           'out, following the motion shown. Hold the solid blue frame and '
                           'keep pressure off the finger rests. Stop if the holder bends.')
            elif owner == 'Front_pull_shelf' and finger_comb:
                title = 'Slide out the finger-side comb'
                caption = ('Grip the green bar and slide the comb straight out from under '
                           'the finger rests, following the motion shown. Keep hold of the solid '
                           'blue frame. Do not push the comb down onto the rests or pry against them.')
            else:
                title = 'Pull the front shelf forward' if owner == 'Front_pull_shelf' else 'Pull out the rear support'
                caption = ('Grip the exposed bar and pull the shelf straight out, following '
                           'the motion shown. Keep pressure off the thin finger rests.')
        samples = []
        for index in range(25):
            sample = {key: value[:] for key, value in state.items()}
            sample[actor] = pose(x=vector[0] * index / 24,
                                 y=vector[1] * index / 24,
                                 z=vector[2] * index / 24)
            samples.append(sample)
        state[actor] = samples[-1][actor][:]
        steps.append({'title': title, 'duration': 4, 'caption': caption, 'samples': samples})
    guide['modules']['print_cleanup'] = {
        'label': 'Remove print support', 'rotation': [.85, 0, .35],
        'note': ('Actual exported print meshes, shown without the bed. Blue is the permanent '
                 'holder; the other coloured pieces are disposable. The animation follows '
                 'the audited removal order and directions. It does not establish release '
                 'force. Physical support removal remains untested.'),
        'actors': actors, 'steps': steps, 'native_removal_sequence': order,
        'physical_piece_removal_sequence': [
            {key: piece[key] for key in ('owner', 'actor', 'filename')} for piece in cleanup],
    }
    for module_name in ('key', 'dfr'):
        guide['modules'][module_name]['steps'][0]['caption'] = (
            'Open Remove print support and follow its cleanup order on the cool part before '
            'fitting hardware. Keep pressure off the finger rests and do not force support '
            'through a key opening.')
    guide['sources'] = {
        'upstream_guide_sha256': sha(UPSTREAM), 'generator_sha256': sha(Path(__file__)),
        'print_frame_sha256': sha(parts / 'frame.json'), 'meshes_sha256': assets,
        'native_audit_sha256': sha(audit_path),
        'selected_native_archive_sha256': audit['archive_sha256'],
        'side_helper_receipts_sha256': {owner: sha(parts / ('shelf-cad.json' if owner == 'Front_pull_shelf' else 'rear-shelf-cad.json')) for owner in shelf_receipts},
    }
    target = exports / 'assembly-guide.json'
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(guide, indent=2) + '\n')
    temporary.replace(target)
    print(target.name, sha(target))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('parts', type=Path)
    build(parser.parse_args().parts.resolve())
