"""Check the eight non-carrier pieces in the actual complete R47 toolpaths.

The established all-part checker is reused with a scoped object view. All
deposition, including neighbouring pieces and the tower, remains unchanged.
Only triangle index order is normalised, after coordinate identity is proved.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
import trimesh
from itertools import product
import holder47 as h
import audit42 as full
import audit_plate32 as common
import slice22


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(saved, mesh, shift):
    """Bound every vertex displacement and retain every triangle multiplicity."""
    # Match all vertices using exact neighbour cells, without an extra SciPy dependency.
    pitch = .0002
    buckets = {}
    for index, point in enumerate(mesh.vertices):
        buckets.setdefault(tuple(np.floor(point / pitch).astype(int)), []).append(index)
    indices, distance = [], []
    neighbours = list(product((-1, 0, 1), repeat=3))
    for point in saved['vertices'] - shift:
        cell = np.floor(point / pitch).astype(int)
        candidates = [i for delta in neighbours
                      for i in buckets.get(tuple(cell + delta), ())]
        assert candidates, 'Native vertex has no matching reference cell'
        lengths = np.linalg.norm(mesh.vertices[candidates] - point, axis=1)
        nearest = int(np.argmin(lengths))
        indices.append(candidates[nearest]); distance.append(lengths[nearest])
    indices, distance = np.asarray(indices), np.asarray(distance)
    assert float(distance.max()) < .0002, 'Native vertex drift'
    mapped = np.sort(indices[saved['faces']], axis=1)
    expected = np.sort(mesh.faces, axis=1)
    a = mapped[np.lexsort(mapped.T[::-1])]
    b = expected[np.lexsort(expected.T[::-1])]
    assert np.array_equal(a, b), 'Native triangle topology drift'
    return float(distance.max())


def check(archive, scratch, output):
    hardware = h.HERE.parent
    r42 = hardware / 'carbon-rod-holders-r42-lower-diagonal/exports'
    base = r42 / 'print-trial/R42-Complete-A1-mini-PETG-layout.3mf'
    battery = r42 / 'print-jobs/battery/R42-battery-A1-mini-PETG-layout.3mf'
    records = json.loads((r42 / 'print-trial/print-manifest.json').read_text())['parts']
    records.pop(h.CARRIER)
    exports = output / 'build-source/exports'
    exports.mkdir(parents=True, exist_ok=True)
    references = {}
    for name, record in records.items():
        target = exports / (name + common.SOURCE_SUFFIX)
        if name == h.BRACKET:
            cap = scratch / 'stage/R47-DFRobot_Hole_Bracket-cap.stl'
            raw = trimesh.load_mesh(cap)
            record['assembly_stl_sha256'] = digest(cap)
            record['assembly_bounds_mm'] = raw.bounds.tolist()
            record['bounds_mm'] = raw.bounds.tolist()
            record['volume_mm3'] = float(raw.volume)
            raw.apply_transform(np.linalg.inv(np.asarray(record['print_to_assembly'])))
            record['print_height_mm'] = float(raw.bounds[1, 2] - raw.bounds[0, 2])
            raw.export(target)
            record['stl_sha256'] = digest(target)
        else:
            candidates = [p for p in hardware.glob('*/exports/' + name + common.SOURCE_SUFFIX)
                          if digest(p) == record['stl_sha256']]
            assert candidates, (name, 'Missing exact inherited print mesh')
            shutil.copyfile(candidates[0], target)
        references[name] = {'print_mesh_sha256': digest(target)}
    engine = common.load_checker()
    actual = list(engine.audit.read_project(archive))
    data, features, stats, settings, offset, objects = actual[:6]
    native = deepcopy(objects)
    for name, record in records.items():
        mesh = trimesh.load_mesh(exports / (name + common.SOURCE_SUFFIX))
        saved = native[name]
        shift = (saved['vertices'].max(0) + saved['vertices'].min(0) - mesh.bounds.sum(0)) / 2
        vertex_error = identity(saved, mesh, shift)
        # The existing checker compares arrays by index. Equivalent triangle
        # reordering is safe only after the full coordinate proof above.
        saved['vertices'], saved['faces'] = mesh.vertices + shift, mesh.faces.copy()
        references[name]['native_shift_mm'] = shift.tolist()
        references[name]['maximum_native_vertex_drift_mm'] = vertex_error
    actual[5] = {name: native[name] for name in records}
    owners = full.native_support_owners(archive)
    labels = np.asarray(features)[data[:, 5].astype(int)]
    positions = data[:, :3] + offset
    bounds = {}
    for name, owner in owners.items():
        selected = data[:, 6] == owner
        if not selected.any():
            continue
        radius = data[selected, 3, None] / 2
        bounds[name] = [(positions[selected, :2] - radius).min(0).tolist(),
                        (positions[selected, :2] + radius).max(0).tolist()]
    helper_names = {'Key_Carrier', 'External_cradle', 'Release_tabs', 'Front_pull_shelf', 'Rear_pull_shelf'}
    assert set(owners) == helper_names | set(records), 'Complete build list changed'
    groups = {name: [name] for name in records}
    groups['Key carrier and temporary helpers'] = sorted(helper_names)
    group_bounds = {}
    for name, members in groups.items():
        selected = np.isin(data[:, 6], [owners[member] for member in members])
        assert selected.any(), (name, 'No deposited group')
        radius = data[selected, 3, None] / 2
        group_bounds[name] = [(positions[selected, :2] - radius).min(0),
                              (positions[selected, :2] + radius).max(0)]
    tower = labels == 'Prime tower'
    assert tower.any()
    radius = data[tower, 3, None] / 2
    group_bounds['Smooth timelapse tower'] = [(positions[tower, :2] - radius).min(0),
                                            (positions[tower, :2] + radius).max(0)]
    unassigned = ~tower & ~np.isin(data[:, 6], list(owners.values()))
    unassigned_features = {name: int((unassigned & (labels == name)).sum())
                           for name in np.unique(labels[unassigned])}
    separations = []
    ordered = sorted(group_bounds)
    for i, name in enumerate(ordered):
        low, high = group_bounds[name]
        assert (low >= 0).all() and (high <= 180).all(), (name, 'Beads outside the A1 mini bed')
        for other in ordered[i + 1:]:
            a, b = group_bounds[other]
            gap = float(np.linalg.norm(np.maximum(np.maximum(low - b, a - high), 0)))
            separations.append({'groups': [name, other], 'conservative_xy_gap_mm': gap})
    plate_layout = {'bounds_xy_mm': {name: [a.tolist(), b.tolist()] for name, (a, b) in group_bounds.items()},
                    'group_gaps': separations, 'inside_bed': True,
                    'unassigned_bead_features': unassigned_features,
                    'passed': not unassigned_features and all(row['conservative_xy_gap_mm'] > .55 for row in separations),
                    'scope': 'All deposited part, support, adhesion and tower bead widths; intentional key/helper group checked separately'}
    anchors = json.loads((r42 / 'print-trial/print-anchors.json').read_text())['parts']
    anchors.pop(h.CARRIER, None)
    later = json.loads((r42 / 'print-jobs/battery/print-anchors.json').read_text())['parts']
    anchors['Battery_Holder'] = later['Battery_Holder']
    for name, record in anchors.items():
        source = battery if name == 'Battery_Holder' else base
        with ZipFile(source) as z:
            config = ET.fromstring(z.read('Metadata/model_settings.config'))
            model = ET.fromstring(z.read('3D/3dmodel.model'))
        names = {o.get('id'): next(m.get('value') for m in o.findall('metadata') if m.get('key') == 'name')
                 for o in config.findall('object')}
        item = next(i for i in model.findall('./{*}build/{*}item') if names[i.get('objectid')] == name)
        transform = list(map(float, item.get('transform').split()))
        shape, label = slice22.previous.slice19.anchor_in_project(source, name, np.asarray(transform[9:12]))
        assert 'REMOVE AFTER PRINT' in label
        mesh = shape.to_mesh()
        path = exports / (name + common.PAD_SUFFIX)
        trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False).export(path)
        record['stl_sha256'] = digest(path)
        references[name]['anchor_reference_project_sha256'] = digest(source)
    (exports / 'manifest.json').write_text(json.dumps({'parts': records}, indent=2))
    (exports / 'anchors.json').write_text(json.dumps({'parts': anchors}, indent=2))
    layout = {'build_list': list(records), 'effective_filament_settings': {},
              'material_bounds_xy_mm': bounds, 'bom_sha256': digest(h.HERE / 'holder47.py')}
    gaps, material = full.routes()
    gaps[h.BRACKET]['arm flex gaps'] = h.r.mirrored(h.box(.72, 1.77,
        h.r.ARM_ROOT_Y + 1.7, 27.2 - h.HINGE_PULL, 17.07, 18.24))
    gaps = {name: row for name, row in gaps.items() if name in records}
    material = {name: row for name, row in material.items() if name in records}
    prior_regions = h.p.BATTERY.h18.regions
    def regions(name):
        if name != 'Battery_End_Door': return prior_regions(name)
        door = h.p.DOOR
        return {'tongue_slit': h.box(door['tongue_root_x_mm'] + .05, door['window_x_mm'][0] - .05,
            door['y_mm'][0] - 1., door['y_mm'][1] + 1., door['tongue_z_mm'][1] + .05,
            door['tongue_z_mm'][1] + door['slit_mm'] - .05)}
    support_evidence = {}
    def supports(raw, places, kinds, selected_objects, q, starts):
        support = np.char.startswith(kinds, 'Support')
        assert not (support & (raw[:, 6] != owners[h.BRACKET])).any(), 'Unexpected support owner'
        with patch.object(full.d, 'HERE', output / 'build-source'):
            feet = full.bracket_support_check(engine.audit, raw, places, kinds, selected_objects, layout, owners)
        mesh = trimesh.load_mesh(exports / (h.BRACKET + common.SOURCE_SUFFIX))
        solid = q.solid(mesh.vertices, mesh.faces)
        local = full.common.local_points(raw, offset, selected_objects[h.BRACKET], mesh)
        normal = full.common.model_mask(kinds) & (raw[:, 6] == owners[h.BRACKET])
        removal = full.support_removal_grid(solid, engine.audit, raw, local, normal, support, records[h.BRACKET])
        support_evidence.update(feet=feet, removal=removal)
        return {'passed': feet['passed'] and removal['passed'], 'part': h.BRACKET, 'top_gap_mm': .2,
                'feet': feet, 'removal': removal}
    with patch.object(common, 'load_checker', return_value=engine), \
         patch.object(engine.audit, 'read_project', return_value=tuple(actual)), \
         patch.object(engine.project22.studio.p19, 'command_audit', full.plate42.command_audit), \
         patch.object(h.p.BATTERY.h18, 'regions', side_effect=regions):
        result = common.inspect(archive, exports, lambda: (gaps, material), layout, supports)
    result['scope'] = 'Eight non-carrier functional pieces; all actual complete-plate beads retained'
    result['complete_plate_layout'] = plate_layout
    result['passed'] = bool(result['passed'] and plate_layout['passed'])
    result['coordinate_identity'] = references
    result['complete_archive_sha256'] = digest(archive)
    result['adapter_sha256'] = digest(Path(__file__))
    (output / 'other-parts-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'failures': result['failures']}, indent=2))
    assert result['passed']


if __name__ == '__main__':
    check(*map(lambda p: Path(p).resolve(), sys.argv[1:]))
