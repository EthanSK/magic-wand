"""Resolve zero-sample route rows with complete native bead-slab intersections."""
import json
from pathlib import Path
import sys
import numpy as np
import holder47 as h
import build47 as b
import plate47
from scope47 import key_group
from plate45 import digest


def deposited_overlap(checker, target, xyz, data):
    low, high = np.asarray(target.bounding_box()).reshape(2, 3)
    radius = data[:, 3, None] / 2
    near = ((xyz[:, :2] >= low[:2] - radius) & (xyz[:, :2] <= high[:2] + radius)).all(1)
    near &= (data[:, 7] > low[2]) & (data[:, 7] - data[:, 4] < high[2])
    contacts, overlap = [], 0.
    for top in np.unique(data[near, 7]):
        selected = near & (abs(data[:, 7] - top) < .001)
        height = round(float(data[selected, 4][0]), 3)
        top = round(float(top), 3)
        film = checker.start_audit.bead_footprints(checker.q, xyz[selected, :2], data[selected, 3])
        contact = target ^ film.extrude(height).translate((0, 0, top - height))
        overlap += contact.volume()
        if contact.volume() > 1e-7:
            contacts.append({'top_mm': top, 'height_mm': height, 'volume_mm3': contact.volume(),
                             'bounds_mm': contact.bounding_box()})
    return max(0., overlap), int(near.sum()), contacts


def inspect(archive, scratch):
    directory = archive.parent
    result = json.loads((directory / 'candidate-audit.json').read_text())
    assert result['archive_sha256'] == digest(archive)
    receipt = json.loads((scratch / 'stage/r47-checks.json').read_text())
    routes = plate47.routes_for(receipt['backup_angle_deg'])()[0][h.CARRIER]
    frame = json.loads((directory / 'frame.json').read_text())
    inverse = np.linalg.inv(np.asarray(frame['print_to_assembly']))[:3]
    rows = {}
    with key_group(archive) as engine:
        checker = engine.audit
        data, features, _, _, offset, objects, *_ = checker.read_project(archive)
        xyz = data[:, :3] + offset - frame['bed_translation']
        assert len(data) > 100000 and 'Key_Carrier' in objects
        reference_path = h.R46 / 'exports/key-holder-only/R46-Key-Carrier.gcode.3mf'
        reference_frame = json.loads((reference_path.parent / 'frame.json').read_text())
        assert np.allclose(frame['print_to_assembly'], reference_frame['print_to_assembly'])
        reference_data, _, _, _, reference_offset, *_ = checker.read_project(reference_path)
        reference_xyz = reference_data[:, :3] + reference_offset - reference_frame['bed_translation']
        for name, old in result['working_spaces'].items():
            if old['maximum_checked_samples_per_pose']:
                continue
            region = routes[old['inherited_source_region']]
            poses = list(region.poses()) if hasattr(region, 'poses') else [region]
            record = []
            for pose in poses:
                target = pose.transform(inverse)
                assert target.volume() > .0001, (name, 'empty route')
                low, high = np.asarray(target.bounding_box()).reshape(2, 3)
                # Resolve the original scanner's centre-plane guard into a
                # whole-slab guard. Keep raw end contacts and require no
                # increase over the physically fitted R46 mounting openings.
                vertex_bound = result['native_vertex_bound_mm']
                assert 0. < vertex_bound < .001
                guard = checker.q.Z_GUARD
                assert 0. <= guard <= .1
                boundary = guard + .1 + vertex_bound if old['inherited_source_region'].endswith('_mount_opening') else 0.
                interior = (target.trim_by_plane((0, 0, 1), low[2] + boundary)
                            .trim_by_plane((0, 0, -1), -high[2] + boundary))
                assert interior.volume() > .0001
                overlap, samples, contacts = deposited_overlap(checker, target, xyz, data)
                interior_overlap, _, _ = deposited_overlap(checker, interior, xyz, data)
                reference_overlap = None
                if boundary:
                    for contact in contacts:
                        bounds = contact['bounds_mm']
                        assert contact['height_mm'] == .2 and (bounds[5] <= low[2] + boundary
                                                              or bounds[2] >= high[2] - boundary)
                    reference_overlap, _, _ = deposited_overlap(checker, target, reference_xyz, reference_data)
                    assert overlap <= reference_overlap + .0001, (name, overlap, reference_overlap)
                record.append({'target_volume_mm3': target.volume(),
                               'candidate_samples': samples,
                               'contacts': contacts,
                               'nominal_end_boundary_mm': boundary,
                               'r46_nominal_overlap_mm3': reference_overlap,
                               'interior_bead_overlap_mm3': max(0., interior_overlap),
                               'whole_native_bead_overlap_mm3': max(0., overlap)})
            rows[name] = record
    report = {'archive_sha256': digest(archive), 'checker_sha256': digest(Path(__file__)),
              'r46_reference_archive_sha256': digest(reference_path),
              'nonempty_routes': rows,
              'maximum_overlap_mm3': max(r['whole_native_bead_overlap_mm3'] for v in rows.values() for r in v),
              'maximum_interior_overlap_mm3': max(r['interior_bead_overlap_mm3'] for v in rows.values() for r in v),
              'scope': 'Every zero-sample route from the point scanner, in the verified carrier frame; complete deposited slabs, including disposable helpers and boundary heights.'}
    (directory / 'empty-space-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Zero-sample spaces, maximum whole-bead intersection:', report['maximum_overlap_mm3'], flush=True)
    assert report['maximum_interior_overlap_mm3'] < .0001, report
    return report


if __name__ == '__main__':
    inspect(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
