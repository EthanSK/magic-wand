"""Export R47's parts and its assembly guide from the composed carrier and the R47 hardware.

Usage (through geometry_budget.py): guide47.py SCRATCH [PARTS]
SCRATCH/stage holds build47's carrier and checks. PARTS, once it exists,
holds the key-holder plate files with R47's native helper audit
(candidate-audit.json); without it the guide omits the cleanup animation.

R42's guide writer (through R44's raised-key wrapper) builds every OP1, touch
board, bracket and click actor from the configured hardware, so at R47's
settings the meshes and motions follow the moved switch, the 19-degree board
and the pulled-in hinge. The carrier actor is the composed R47 carrier.
R45's cleanup module then animates the R47 helpers in their audited order.

R47 changes the harness steps. The plug goes onto the board first and drops
in with it; the lead's free end passes down through the opening beside the
rod channel, and the lead then presses up into the underside groove.
"""
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

import numpy as np

import holder47 as h
import build47 as b

R44 = h.HERE.parent / 'carbon-rod-holders-r44-middle-finger-rest'
R45 = h.HERE.parent / 'carbon-rod-holders-r45-open-keyways'
sys.path.insert(0, str(R44))
sys.path.insert(0, str(R45))
import assembly44  # noqa: E402
import guide45  # noqa: E402

d, q, r, base = h.d, h.q, h.r, h.base
up = assembly44.upstream            # assembly42
A, H = assembly44.A, assembly44.H
OUT = h.HERE / 'exports'
I = up.I
YAW = f'{abs(q.OP1_YAW):.0f}°'
WHERE = "6.5 mm in from the touch board's lower edge"


def export_parts(carrier, checks, layout):
    """R44's export() with the composed carrier and R47's own manifest."""
    (OUT / 'guide').mkdir(parents=True, exist_ok=True)
    A.OUT = H.OUT = OUT
    H.PRINT_ROT[d.BRACKET] = A.trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])
    H.PRINT_ROT['Battery_End_Door'] = H.PRINT_ROT[d.BRACKET]
    H.PRINT_ROT[d.CLIP] = H.PRINT_ROT[up.CLIP2] = np.eye(4)
    shapes = ((d.BRACKET, d.bracket()), (d.CLIP, d.clip_part()),
              (up.CLIP2, d.clip_part()), ('Battery_End_Door', d.battery_door()))
    parts = {n: H.export_part(n, s, n) for n, s in shapes}
    # Reuse the checked layout's exact carrier bytes. The older R23 writer
    # simplifies and rounds again, which changes this stepped underside.
    frame = json.loads((layout / 'frame.json').read_text())
    assembly = OUT / (d.CARRIER + '-assembly.stl')
    source = OUT / (d.CARRIER + '-SOURCE-REQUIRES-PREPARATION.stl')
    shutil.copyfile(layout / 'R45-Key-Carrier-assembly.stl', assembly)
    shutil.copyfile(layout / 'R45-Key-Carrier.stl', source)
    placed, printed = A.trimesh.load_mesh(assembly), A.trimesh.load_mesh(source)
    parts[d.CARRIER] = {
        'volume_mm3': round(float(placed.volume), 3),
        'solid_PETG_g': round(float(placed.volume) / 1000 * 1.27, 3),
        'assembly_bounds_mm': placed.bounds.round(3).tolist(),
        'print_height_mm': round(float(printed.bounds[1, 2]), 3),
        'stl_sha256': H.sha(source), 'assembly_stl_sha256': H.sha(assembly),
        'print_to_assembly': frame['print_to_assembly'],
        'source': 'Exact checked R47 key-layout mesh; no additional simplify or coordinate rounding.',
        'layout_body_vs_checked_carrier': frame['layout_body_vs_checked_carrier'],
    }
    parts['Battery_Holder'] = d.BATTERY.copy_part('Battery_Holder', d.BATTERY.HERE, OUT, anchored=True)
    A.write_json(OUT / 'anchors.json', {'parts': {'Battery_Holder': up.previous.old.read(
        d.BATTERY.HERE / 'exports/anchors.json')['parts']['Battery_Holder']}})
    battery = d.BATTERY.read(OUT / 'Battery_Holder-assembly.stl')
    door = d.BATTERY.read(OUT / 'Battery_End_Door-assembly.stl')
    checks['battery_door'] = up.previous.battery_checks(battery, door)
    A.write_json(OUT / 'geometry-checks.json', {'revision': h.HERE.name, 'physical_fit_verified': False,
                                                'sliced': False, 'checks': checks})
    A.write_json(OUT / 'manifest.json', {
        'revision': h.HERE.name, 'units': 'mm', 'parts': parts, 'physical_fit_verified': False, 'print_cleared': False,
        'source_sha256': {p.name: H.sha(p) for p in sorted(h.HERE.glob('*.py')) + [h.HERE / 'complete-assembly.json']},
        'upstream_sha256': {p.name: H.sha(p) for p in (R44 / 'holder44.py', R44 / 'assembly44.py',
                                                       Path(up.__file__), h.R46 / 'holder46.py')}})
    return battery, door


def base_guide(checks, battery, door):
    with patch.object(assembly44, 'HERE', h.HERE), patch.object(assembly44, 'OUT', OUT):
        return assembly44.write_guide(checks, battery, door)


def cleanup(parts):
    """R45's cleanup module from the R47 plate meshes (R47-* published as R45-* aliases)."""
    assets = OUT / 'print-supports'
    assets.mkdir(parents=True, exist_ok=True)
    for source in parts.iterdir():
        if source.suffix == '.stl' or source.name in (
                'candidate-audit.json', 'frame.json', 'shelf-cad.json', 'rear-shelf-cad.json'):
            shutil.copyfile(source, assets / source.name)
    with tempfile.TemporaryDirectory(dir=parts.parent) as tmp:
        view = Path(tmp)
        upstream = view / 'base-guide.json'
        shutil.copyfile(OUT / 'assembly-guide.json', upstream)
        with patch.object(guide45, 'HERE', h.HERE), patch.object(guide45, 'UPSTREAM', upstream):
            # Actor files in the base guide are relative to exports/.
            data = json.loads(upstream.read_text())
            for module in data['modules'].values():
                for actor in module['actors'].values():
                    for key in ('file', 'morphFile'):
                        if key in actor:
                            actor[key] = str((OUT / actor[key]).resolve())
            upstream.write_text(json.dumps(data))
            target = guide45.build(assets)
    return target


def follow(sample, actor, leader):
    sample[actor] = list(sample[leader])


def r47_harness(guide):
    """Pre-fitted plug: it rides with the board; the lead presses up from below."""
    dfr = guide['modules']['dfr']
    titles = [s['title'] for s in dfr['steps']]
    lower, connect = titles.index('Lower the OP1 Board'), titles.index('Connect the Harness Underneath')
    for step in dfr['steps'][:connect]:
        for sample in step['samples']:
            follow(sample, 'plug', 'board')
    for sample in dfr['steps'][connect]['samples']:
        sample['plug'] = list(I)
    dfr['steps'][lower]['caption'] = (
        'Push the harness plug onto the white socket under the board first. Pass the free end of its lead down '
        'through the opening beside the rod channel, under the plug pocket. With the holder off the rod, lower '
        f'the board and plug together onto the two seats at the board\'s {YAW} angle. Its switch sits {WHERE}; '
        'the keys can stay fitted.')
    dfr['steps'][connect]['title'] = 'Press the Lead into the Groove'
    dfr['steps'][connect]['caption'] = (
        'From below, press the lead up into the open groove beside the rod channel so it leaves at the two-key end. '
        'Do this before the holder goes on the rod.')
    for annotation in dfr.get('annotations', []):
        if annotation['title'].startswith('Plug enters from below'):
            annotation.update(title='Plug fitted to the board before it drops in', step='Lower the OP1 Board')
    return {'plug_rides_with_board_steps': connect, 'lead_press_step': connect}


def r47_text(guide):
    replacements = [
        ('OP1 PCB at 25°', f'OP1 PCB at {YAW}'),
        ('Harness plug, pushed in from below', 'Harness plug, fitted to the board first'),
        ('Switch plunger under the three-key row', "Switch plunger near the touch board's lower edge"),
        ('onto the OP1 switch under the three-key row', f'onto the OP1 switch {WHERE}'),
        ('The OP1 board is turned 25° so its switch sits under the three-key row.',
         f"The OP1 board is turned {YAW} so its switch sits {WHERE}, near the end the finger presses."),
    ]

    def walk(value):
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, str):
            for old, new in replacements:
                value = value.replace(old, new)
            return value.replace('R46', 'R47').replace('R45 ', 'R47 ')
        return value

    modules = walk(guide['modules'])
    note = (f'R47 moves the OP1 click to {WHERE} (lever 33.0 mm from the hinge, was 28.1), shifts the OP1 '
            f'2 mm right and turns it to {YAW}. A rounded chin below the bottom keys carries the board end. '
            'The harness plug is fitted to the board before it goes in. Hinge, keys, rod clips and finger rests '
            'keep R46\'s positions apart from the hinge, 0.4 mm closer to the board. Bought board and connector '
            'dimensions include estimates; physical fit, click feel and strength are unverified.')
    for key in ('key', 'dfr'):
        modules[key]['note'] = note
    modules['whole']['note'] = (
        'R47 keys, DFRobot touch bracket and diagonal OP1 board on the same rod as the XIAO holder, '
        'battery holder and cable clip. The OP1 click sits near the lower touch-board edge. '
        'Use the component views for the matching keepers, door and hinge clips. '
        'Wire lengths outside the holders are illustrative.')
    modules['finger_rest']['note'] = (
        'The cyan holder keeps R46\'s rounded braces from each finger rest to its outer edge and both deck '
        'returns. R47 adds one short rounded bar ahead of the OP1 plug pocket that ties the right guard legs '
        'to the deck.')
    guide['modules'] = modules
    guide['revision'] = h.HERE.name
    guide['physical_fit_verified'] = False


def build(scratch, parts):
    stage = scratch / 'stage'
    carrier = b.load(stage / 'R47-Key-Carrier-assembly.stl')
    full = json.loads((stage / 'r47-checks.json').read_text())
    assert full['r47']['passed'], 'build47 checks must pass'
    checks = dict(full, passed=True, inherited_r44_gates_passed=full['passed'])
    shutil.copyfile(R44 / 'complete-assembly.json', h.HERE / 'complete-assembly.json')
    with patch.object(d, 'carrier', lambda: carrier), patch.object(d, 'checks', lambda: checks):
        battery, door = export_parts(carrier, checks, parts or scratch / 'final-key-layout')
        report = base_guide(checks, battery, door)
    audit_path = parts / 'candidate-audit.json' if parts is not None else None
    audited = (audit_path is not None and audit_path.is_file()
               and json.loads(audit_path.read_text())['screen_passed'])
    if audited:
        guide = json.loads(cleanup(parts).read_text())
        for module_name in ('key', 'dfr'):
            step = guide['modules'][module_name]['steps'][0]
            step['title'] = 'Remove Print Supports'
            step['caption'] = (
                'Choose Remove print support in Assembly view and follow the shown order on the cool print. '
                'Remove every cradle, shelf piece and bed tab before fitting hardware. '
                'Do not pull on the finger rests or force a support through a key opening.')
    else:
        # The cleanup animation follows the native helper audit's removal
        # order. Until R47's own audit exists, the guide shows the assembly
        # only and says so; R46's order is not substituted.
        guide = json.loads((OUT / 'assembly-guide.json').read_text())
        for module_name in ('key', 'dfr'):
            step = guide['modules'][module_name]['steps'][0]
            step['caption'] = ('Remove every disposable print helper before fitting hardware. The R47 removal '
                               'animation is added after the native helper audit; until then follow the layout\'s '
                               'colours and do not pull on the finger rests.')
    r47_text(guide)
    harness = r47_harness(guide)
    for module in guide['modules'].values():
        for actor in module['actors'].values():
            for key in ('file', 'morphFile'):
                if key in actor:
                    path = Path(actor[key])
                    if path.is_absolute():
                        actor[key] = Path(os.path.relpath(path, OUT)).as_posix()
    guide.setdefault('sources', {}).update(generator_sha256=H.sha(Path(__file__)), r47_harness_steps=harness,
                                           r47_checks_sha256=H.sha(stage / 'r47-checks.json'),
                                           helper_cleanup_from_native_audit=audited)
    with patch.object(up, 'OUT', OUT):
        report = up.guide_checks(guide)
    A.write_json(OUT / 'assembly-guide.json', guide)
    print(json.dumps({'guide': report, 'harness': harness}, indent=1))
    return OUT / 'assembly-guide.json'


if __name__ == '__main__':
    build(Path(sys.argv[1]), Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None)
