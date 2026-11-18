"""Check for narrow connections anywhere in the working parts retained from R48."""
import hashlib
import json
from pathlib import Path

import build48
import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'carbon-rod-holders-r48-edge-click/exports'
NAMES = {'XIAO_Rod_Holder': ('xiao','holder'), 'XIAO_Near_Keeper': ('xiao','keeper'),
         'Cable_Clip_12_Wire': ('cable','clip'), 'Battery_Holder': ('battery','holder'),
         'DFR0030_Post_Clip': ('dfr','clip_left'), 'DFR0030_Post_Clip_2': ('dfr','clip_right')}


def section_check(body, radius=.28, pitch=.2):
    # Remove material at both faces and all edges, then follow every component
    # across successive planes. This catches a substantial lobe held by a very
    # thin neck anywhere, independently of the preselected joint measurements.
    parents, volumes = [], []
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    previous = []
    low, high = body.bounding_box()[2::3]
    for z in np.arange(low+radius+.0001, high-radius, pitch):
        slab = body.slice(z).offset(-radius)
        for dz in [-radius, radius]:
            slab = slab ^ body.slice(z+dz).offset(-radius)
        current = []
        for section in slab.decompose():
            idx = len(parents)
            parents.append(idx)
            volumes.append(section.area()*pitch)
            for other, ref in previous:
                if (section ^ other).area() > .0001:
                    parents[root(ref)] = root(idx)
            current.append((section,idx))
        previous = current
    groups = {}
    for i,vol in enumerate(volumes):
        groups[root(i)] = groups.get(root(i),0.) + vol
    return sorted((round(v,3) for v in groups.values() if v >= .01),reverse=True)


def main():
    read = lambda p: json.loads(p.read_text())
    mods = read(OLD/'assembly-guide.json')['modules']
    paths = read(OLD/'complete-plate/strength-paths.json')
    slices = read(OLD/'complete-plate/other-audit/other-parts-audit.json')
    retry = read(OLD/'wide-pad-retry/verification.json')
    results = {}
    for name,(module,actor) in NAMES.items():
        file = OLD/mods[module]['actors'][actor]['file']
        mesh = trimesh.load_mesh(file)
        solid = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
        assert solid.status() == mf.Error.NoError and len(solid.decompose())==1
        results[name] = {
            'assembly_mesh_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
            'raw_mesh_watertight':bool(mesh.is_watertight),
            'raw_zero_area_faces':int((~mesh.nondegenerate_faces()).sum()),
            'resolved_solid_count':len(solid.decompose()),
            'eroded_connected_volumes_mm3':section_check(solid),
            'printed_joint_checks':{k:all(q['passed'] for q in v['layers']) for k,v in paths['parts'][name].items()},
            'working_spaces_checked':len(slices['parts'][name]['working_spaces']),
            'floating_components':slices['parts'][name]['floating_components'],
            'checked_layers':slices['parts'][name]['checked_layers'],
            'retry_move_comparison':retry['non_brim_deposition_comparison'].get(name),
        }
        if name == 'Cable_Clip_12_Wire' and not mesh.is_watertight:
            # R22 carried zero-area facets at coincident edges. Dropping just
            # these fixes mesh readers while preserving every real triangle.
            before = float(mesh.volume)
            keep = mesh.area_faces > 0
            if not np.array_equal(keep,mesh.nondegenerate_faces()):
                raise ValueError('Cable clip contains thin nonzero faces; inspect before cleaning')
            mesh.update_faces(keep)
            mesh.remove_unreferenced_vertices()
            assert mesh.is_watertight and mesh.is_winding_consistent and abs(mesh.volume-before)<1e-7
            clean = HERE/'exports/Cable_Clip_12_Wire-reference.stl'
            mesh.export(clean)
            results[name]['clean_reference_sha256'] = hashlib.sha256(clean.read_bytes()).hexdigest()
            results[name]['volume_change_mm3'] = float(mesh.volume-before)
        print(name,results[name]['eroded_connected_volumes_mm3'],flush=True)
    report = dict(eroded_edge_mm=.28,slice_spacing_mm=.20,
                  method='Whole reference mesh erosion screen, R48 native slice at named joints, and comparison against wide-pad retry movements. Separate islands below 0.01 cubic mm are omitted. Physical fatigue life is unmeasured.',
                  source_slice_sha256=paths['archive_sha256'],retry_sha256=retry['retry_archive_sha256'],parts=results)
    (HERE/'exports/reused-parts.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
