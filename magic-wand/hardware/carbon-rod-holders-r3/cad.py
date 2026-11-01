#!/usr/bin/env python3
"""Generate the five-key carbon-tube accessories with `python cad.py`.

Ethan's five keys are three below, two above, with the upper middle left
for the battery. Compose the preserved Choc seats and R2 XIAO holder.
Python remains appropriate because the existing CAD uses manifold3d.
"""
from pathlib import Path
import importlib.util
import json
import sys
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
R2 = HERE.parent / 'carbon-rod-holders-r2'

def load_previous(name: str, folder: Path = R2):
    spec = importlib.util.spec_from_file_location('five_key_' + name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

previous = load_previous('cad')
base = previous.base
P = json.loads((R2 / 'parameters.json').read_text())
overrides = json.loads((HERE / 'parameters.json').read_text())
for section, values in overrides.items():
    if isinstance(values, dict):
        P[section].update(values)
    else:
        P[section] = values
previous.P = P
base.P = P
base.HERE = HERE
original_carrier = base.carrier
for name in ['box', 'cyl', 'rr', 'rib', 'union', 'tube_y', 'mesh', 'sha', 'ds', 'C']:
    globals()[name] = getattr(base, name)
sensor_holder = previous.sensor_holder
wire_route = previous.wire_route

def key_positions() -> list[tuple[float, float]]:
    k = P['keys']
    return [(-k['pitch'], 0), (0, 0), (k['pitch'], 0),
            (-k['upper_half_spacing'], k['row_spacing']),
            (k['upper_half_spacing'], k['row_spacing'])]

def carrier():
    k, b = P['keys'], P['battery']
    z, row, upper = k['plate_z'], k['row_spacing'], k['upper_half_spacing']
    # Preserve the three bottom seats. Trim projecting tape ears where the
    # upper switches now sit; one relocated tape loop per side stays clear.
    w = b['width'] + 2 * b['clearance_per_side']
    outer = w / 2 + 1.3
    body = original_carrier() - union([
        box(outer, 45, 19, 43, 9, 16),
        box(-45, -outer, 19, 43, 9, 16)])
    parts = [body]
    for sign in [-1, 1]:
        x = sign * upper
        parts.append(base.key_seat().translate((x, row, z)))
        # Two edge rails join each top seat to its bottom neighbour and to
        # the battery ladder. Factory switch clips remain the only clips.
        for y in [row - 10.5, row + 10.5]:
            parts.append(rib((x - 8.4, y, z - .45), (x + 8.4, y, z - .45), 1.0))
            for side in [-1, 1]:
                parts.append(rib((x + side * 7.7, y, z - .45),
                                 (x + side * 7.7, row + (8.1 if y > row else -8.1), z - .45), 1.2))
        parts.append(rib((sign * (k['pitch'] + 7.7), 8.1, z - .45),
                         (sign * (upper + 7.7), row + 8.1, z - .45), 1.0))
        parts.append(rib((sign * (upper - 8.4), row + 10.5, z - .45),
                         (sign * (w / 2 + .65), row + 10.5, b['floor_z']), .9))
        ear = rr(5.4, 8, 1.2, b['floor_z'] - 1.2, b['floor_z'] + .2)
        ear -= rr(2.6, 4.8, .7, b['floor_z'] - 1.4, b['floor_z'] + .4)
        parts.append(ear.translate((sign * (w / 2 + 2.95), b['tape_loop_y'], 0)))
    # Clear all five real hardware interfaces only after every new rail.
    result = union(parts) - union([ds.local_void(C).translate((x, y, z)) for x, y in key_positions()])
    return result

def references():
    refs = previous.references()
    z = P['keys']['plate_z']
    for i, (x, y) in enumerate(key_positions()[3:], 3):
        for name, shape in ds.local_hardware(C).items():
            if name in ['switch', 'socket']:
                refs[f'key_{i}_{name}'] = shape.translate((x, y, z))
        refs[f'key_{i}_cap'] = rr(16.6, 17.5, 1.4, z + 3.6, z + 6.6).translate((x, y, 0))
    return refs

def export() -> None:
    out = HERE / 'exports'
    base.carrier = carrier
    base.sensor_holder = sensor_holder
    base.references = references
    base.export(out)
    scene = trimesh.load(out / 'Assembly-reference.glb', force='scene')
    wire = mesh(wire_route())
    wire.apply_translation((0, 451.6, 0))
    wire.visual.vertex_colors = [175, 74, 60, 255]
    scene.add_geometry(wire, node_name='REFERENCE_provisional_wire_route')
    scene.export(out / 'Assembly-reference.glb')
    manifest = json.loads((out / 'manifest.json').read_text())
    for folder in [R2, HERE.parent / 'carbon-rod-holders']:
        for name in ['cad.py', 'parameters.json']:
            manifest['source_sha256'][str((folder / name).relative_to(HERE.parent).as_posix())] = sha(folder / name)
    # Source keys are relative to this revision, also in portable packages.
    manifest['source_sha256'] = {('../' + n if n.startswith('carbon-rod-holders') else n): d
                                 for n, d in manifest['source_sha256'].items()}
    manifest['key_positions_mm'] = key_positions()
    manifest['revision'] = P['revision']
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    export()
