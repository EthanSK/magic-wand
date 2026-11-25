"""Rebuild every R69 mesh from source and compare it with the export, byte for byte. — Claude Fable 5.2"""
from hashlib import sha256
import argparse
import json
from pathlib import Path
import tempfile

import numpy as np
from shapely.geometry import Point

import design69 as d
import hinge69
import audit69 as audit


def source():
    rows = {}
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        d.export(scratch / d.HOLDER)
        for name, shape in hinge69.parts().items():
            d.b.save_closed(scratch / name, shape)
        for name in (d.HOLDER, hinge69.PADDLE, hinge69.LID, hinge69.WIRES):
            rows[name] = dict(export_sha256=digest(d.OUT / name), reproduced_sha256=digest(scratch / name))
    report = dict(revision='R69', generator_sha256={Path(m.__file__).name: digest(m.__file__) for m in (d, hinge69)}, meshes=rows,
                  carrier_sha256=rows[d.HOLDER]['export_sha256'], reproduced_sha256=rows[d.HOLDER]['reproduced_sha256'])
    report['passes'] = all(r['export_sha256'] == r['reproduced_sha256'] for r in rows.values())
    assert report['passes'], report
    return report


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def slice_evidence(folder: Path) -> dict:
    """Check the published plug motion and lower bores against every deposited bead type.

    Reuses the established R68 empty-air witness with R69's actual guide poses.
    — GPT-6.1 Sol
    """
    archive = folder / audit.v.ARCHIVE
    points, labels = audit.v.read_native(archive)
    frame = np.asarray(audit.v.read(folder / 'layout.frame.json')['parts']['Key_Carrier']['assembly_to_machine'])
    guide = json.loads((d.OUT / 'assembly-guide.json').read_text())
    module = guide['modules']['op1_clips']
    plug = d.b.load((d.OUT / module['actors']['plug']['file']).resolve(strict=True))
    poses, turn = [], []
    for step in module['steps']:
        for sample in step['samples']:
            if 'plug' in sample:
                shape = plug.transform(np.asarray(sample['plug']).reshape(3, 4))
                poses.append(shape)
                if step['title'] == 'Turn the plug upright above the holder':
                    turn.append(shape)
    assert len(poses) > 50 and len(turn) > 10
    route = audit.v.check_routes({'published_plug_motion': poses}, frame, points, labels)['published_plug_motion']
    assert not route['obstructed_poses'], route
    bounds = np.asarray([shape.transform(frame[:3]).bounding_box() for shape in turn])
    low, high = bounds[:, :3].min(axis=0) - .05, bounds[:, 3:].max(axis=0) + .05
    delta = np.maximum(np.maximum(low - points[:, :3], points[:, :3] - high), 0)
    radius = np.hypot(points[:, 3], points[:, 4]) / 2 + .06
    separation = float((np.linalg.norm(delta, axis=1) - radius).min())
    assert separation > 0, separation
    inverse = np.linalg.inv(frame)
    local = points[:, :3] @ inverse[:3, :3].T + inverse[:3, 3]
    target = np.asarray((5., 1., 8.6))
    point = local[np.linalg.norm(local - target, axis=1).argmin()]
    assert np.linalg.norm(point - target) < 2
    box = np.asarray(poses[0].bounding_box()).reshape(2, 3)
    witness = audit.v.check_routes({'plug_in_printed_deck': [poses[0].translate(point - box.mean(axis=0))]}, frame, points, labels)['plug_in_printed_deck']
    assert witness['nearby_samples'] > 25 and witness['obstructed_poses']
    bores = []
    for z in (7.3, 7.6, 7.95):
        section = audit.audit68.printed_seat.printed_contact(folder, archive, (points, labels), z)
        assert section.area > 30
        clear = [float(Point(0, y).distance(section)) for y in d.b.SOCKET_Y]
        assert min(clear) > d.b.SOCKET_R, (z, clear)
        bores.append(dict(z_mm=z, deposited_section_area_mm2=round(section.area, 3), bore_clear_radii_mm=[round(r, 4) for r in clear]))
    report = dict(archive_sha256=digest(archive), checker_sha256=digest(__file__), carrier_sha256=digest(d.OUT / d.HOLDER),
                  guide_sha256=digest(d.OUT / 'assembly-guide.json'), passes=True, published_plug_route=route,
                  turn_poses=len(turn), all_deposited_samples=len(points), turn_aabb_clearance_lower_bound_mm=round(separation, 4),
                  positive_control=witness, lower_socket_sections=bores)
    (folder / 'supplemental-evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders', type=Path, nargs='*')
    parser.add_argument('--slice-only', action='store_true')
    args = parser.parse_args()
    if not args.slice_only:
        result = source()
        (d.OUT / 'source-reproduction.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=1), flush=True)
    for folder in args.folders:
        print(json.dumps(slice_evidence(folder)), flush=True)
