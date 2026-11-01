#!/usr/bin/env python3
"""Derive viewer meshes from the final STLs and canonical CAD references."""
import json
import trimesh
import cad

def record(name: str, shape, part: str, reference: bool) -> dict:
    mesh = shape if isinstance(shape, trimesh.Trimesh) else cad.mesh(shape)
    return {'name': name, 'part': part, 'reference': reference,
            'vertices': mesh.vertices.round(6).tolist(), 'faces': mesh.faces.tolist()}

if __name__ == '__main__':
    revisions = {}
    refs = cad.references()
    for revision, folder in [('r2', cad.R2), ('r3', cad.HERE)]:
        items = [record(name, trimesh.load_mesh(folder / 'exports' / (name + '-assembly.stl')), part, False)
                 for name, part in [('Key_Battery_Carrier', 'carrier'), ('XIAO_Rod_Holder', 'sensor')]]
        for name, shape in refs.items():
            if name == 'rod':
                continue
            if revision == 'r2' and name.startswith(('key_3_', 'key_4_')):
                continue
            items.append(record(name, shape, 'sensor' if name in ['pcb', 'usb'] else 'carrier', True))
        items.append(record('rod', cad.tube_y(3.5, 4, -20, 65), 'carrier', True))
        items.append(record('rod', cad.tube_y(3.5, 4, -9, 23.4), 'sensor', True))
        items.append(record('wire', cad.wire_route(), 'sensor', True))
        manifest = json.loads((folder / 'exports/manifest.json').read_text())
        mass_file = folder / 'exports/mass.json'
        revisions[revision] = {'items': items, 'manifest': manifest,
            'mass': json.loads(mass_file.read_text()) if mass_file.exists() else None}
    (cad.HERE / 'exports/review-scene.json').write_text(json.dumps(revisions, separators=(',', ':')))
