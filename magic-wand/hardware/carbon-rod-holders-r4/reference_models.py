#!/usr/bin/env python3
"""Derive collision/preview meshes from the pinned KiSwitch STEP models.

These are community CAD checked against Kailh drawings, not manufacturer-
certified STEP or a scan of the purchased batch. Original units are mm;
OpenCASCADE's glTF export uses metres, so the explicit scale is 1000.
"""
from pathlib import Path
import hashlib
import json
import tempfile
import numpy as np
import trimesh
import manifold3d as mf
import cascadio

HERE = Path(__file__).resolve().parent
NAMES = {'switch': 'SW_Kailh_Choc_V1', 'socket': 'SW_Hotswap_Kailh_Choc_V1'}
UPSTREAM_REVISION = 'aefcf65038d48d2666ff14530d482be3c350fa6e'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    folder = HERE / 'references'
    report = {'source': 'https://github.com/kiswitch/kiswitch', 'revision': UPSTREAM_REVISION,
              'cad_authority': 'Community STEP; source drawings govern fit; purchased revision unverified',
              'generator_sha256': sha(Path(__file__)), 'parts': {}}
    for name, stem in NAMES.items():
        source = folder / (stem + '.stp')
        target = folder / (name + '.glb')
        cascadio.step_to_glb(str(source), str(target), tol_linear=.01, tol_angular=.15, merge_primitives=True, use_parallel=False)
        scene = trimesh.load(target, force='scene')
        m = scene.to_mesh(); m.apply_scale(1000)
        m.merge_vertices(digits_vertex=4)
        m.update_faces(m.unique_faces())
        m.update_faces(m.nondegenerate_faces())
        m.remove_unreferenced_vertices()
        # Match the float32 interchange used by the exported reference STL.
        m = trimesh.load_mesh(trimesh.util.wrap_as_stream(m.export(file_type='stl')), file_type='stl')
        m.merge_vertices(digits_vertex=3)
        # OpenCASCADE's tessellated seams are welded at 0.001 mm, far below
        # the manufacturer/FDM allowances. Manifold normalises their topology.
        solid = mf.Manifold(mf.Mesh(np.array(m.vertices, dtype=np.float32), np.array(m.faces, dtype=np.uint32)))
        assert solid.status() == mf.Error.NoError, (name, solid.status())
        result = solid.to_mesh()
        data = {'source_sha256': sha(source), 'generator_sha256': sha(Path(__file__)),
                'vertices': np.asarray(result.vert_properties)[:, :3].round(6).tolist(),
                'faces': np.asarray(result.tri_verts).tolist()}
        (folder / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')))
        bounds = m.bounds.tolist()
        report['parts'][name] = {'source_file': source.name, 'source_sha256': sha(source), 'mesh_sha256': sha(folder / (name + '.json')), 'bounds_mm': bounds, 'reference_volume_mm3': solid.volume()}
        expected = [15, 15, 10.9972] if name == 'switch' else [13.15, 6.85, 3.05]
        assert np.max(np.abs(m.extents - expected)) < .02, (name, m.extents)
    (folder / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    build()
