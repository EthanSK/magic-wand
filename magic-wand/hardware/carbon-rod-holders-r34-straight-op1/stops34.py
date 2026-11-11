"""Check that the sliced travel stops remain attached to the carrier."""

import numpy as np
import trimesh

import holder34 as h
from audit_plate32 import SOURCE_SUFFIX, digest, load_checker, read_json


def verify_stops(archive, source):
    audit = load_checker().audit
    q, starts = audit.q, audit.start_audit
    data, features, _, _, offset, objects, _, _ = audit.read_project(archive)
    name = 'Key_Carrier'
    mesh = trimesh.load_mesh(source / f'{name}{SOURCE_SUFFIX}')
    vertices = objects[name]['vertices']
    shift = (vertices.max(0) + vertices.min(0) - mesh.bounds.sum(0)) / 2
    frame = np.asarray(read_json(source / 'manifest.json')['parts'][name]['print_to_assembly'])
    to_print = np.linalg.inv(frame)[:3, :]
    carrier = q.solid(mesh.vertices, mesh.faces)
    xyz = data[:, :3] + offset - shift
    model = np.asarray([not feature.startswith(('Prime tower', 'Brim', 'Skirt', 'Support'))
                        for feature in features])[data[:, 5].astype(int)]
    reports = {}
    for stop in h.stop_posts().decompose():
        side = 'left' if stop.bounding_box()[0] < 0 else 'right'
        target = stop.transform(to_print) ^ carrier
        body = carrier - target
        low, high = np.asarray(target.bounding_box()).reshape(2, 3)
        near = model & (xyz[:, :2] >= low[:2] - 2.).all(1) & (xyz[:, :2] <= high[:2] + 2.).all(1)
        tops = data[:, 7]
        layers = []
        previous_material = None
        for top in np.unique(tops[(tops >= low[2] - .3) & (tops <= high[2] + .3)]):
            on_layer = np.abs(tops - top) < .001
            z = float(top) - float(data[on_layer, 4][0]) / 2
            section = target.slice(z)
            material = starts.bead_footprints(q, xyz[near & on_layer, :2], data[near & on_layer, 3])
            if section.area() >= .1:
                root = body.slice(z)
                stop_area = max(((component ^ section).area() for component in material.decompose()
                                 if (component ^ root).area() >= 1.), default=0.)
                backed = (section ^ material ^ previous_material).area() if previous_material is not None else 0.
                layers.append({'top_mm': round(float(top), 3), 'nominal_mm2': round(section.area(), 4),
                               'body_connected_mm2': round(stop_area, 4), 'prior_overlap_mm2': round(backed, 4),
                               'passed': stop_area >= .70 * section.area() and backed >= min(.4, .5 * stop_area)})
            previous_material = material
        reports[side] = {'layers': layers, 'passed': bool(layers) and all(row['passed'] for row in layers)}
    return {'archive_sha256': digest(archive), 'stops': reports,
            'passed': set(reports) == {'left', 'right'} and all(row['passed'] for row in reports.values())}
