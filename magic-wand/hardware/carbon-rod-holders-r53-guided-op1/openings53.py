"""Check complete mating routes using deposited bead widths, including the outer brims."""
import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import numpy as np
import manifold3d as mf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'carbon-rod-holders-r52-snap-seat'))
from sockets52 import KEYS, key_spaces, paths
from orient51 import digest


def read_native(archive):
    with ZipFile(archive) as z:
        text = z.read('Metadata/plate_1.gcode').decode()
        settings = json.loads(z.read('Metadata/project_settings.config'))
    points, names, _ = paths.extrusion_points(text, .12)
    points[:, :2] += np.fromstring(settings['extruder_offset'][0], sep='x')
    return points, names


def check_routes(space, frame, points, names):
    # Keep all nearby owners and features. A brim or another owner may enter an
    # opening even though the design files keep the parts separate.
    results = {}
    to_local = np.linalg.inv(frame)
    for name, shapes in space.items():
        tested = [pose.transform(frame[:3]) for pose in shapes]
        bounds = np.array([shape.bounding_box() for shape in tested])
        lo, hi = bounds[:,:3].min(axis=0)-1, bounds[:,3:].max(axis=0)+1
        local = points[np.all((points[:,:3] >= lo) & (points[:,:3] <= hi),axis=1)]
        conflicts = []
        max_checked = 0
        def inspect(shape):
            return paths.inspect_region(shape,local[:,:3],local[:,3],local[:,4],
                                        local[:,5].astype(int),names,to_local,limit=1)

        # A clear union proves every pose inside it is clear. If the union
        # touches plastic, locate the exact failing poses individually.
        union = mf.Manifold.batch_boolean(tested,mf.OpType.Add) if len(tested)>1 else tested[0]
        swept = inspect(union)
        max_checked = swept['checked_samples']
        if swept['violations']:
            for i,shape in enumerate(tested):
                r=inspect(shape) if len(tested)>1 else swept
                if r['violations']:
                    conflicts.append(dict(pose=i, bead_counts=r['violations'],examples=r['examples']))
        results[name] = dict(poses=len(tested), nearby_samples=len(local),
                             checked_in_combined_route=max_checked, obstructed_poses=conflicts)
    return results


def keys(archive, frames, names, output):
    records = json.loads(frames.read_text())['parts']
    data, labels = read_native(archive)
    routes = key_spaces()
    report = dict(archive_sha256=digest(archive), frame_sha256=digest(frames), parts={})
    for name in names:
        frame = np.array(records[name]['assembly_to_machine'])
        result = check_routes(routes,frame,data,labels)
        # When a split carrier is placed on the bed, hardware outside that piece
        # can project into another piece's brim. Whole-part checks have no such
        # ambiguity; for split pieces the admissible route window must be explicit.
        report['parts'][name] = result
    output.write_text(json.dumps(report,indent=2)+'\n')
    for key in KEYS:
        row = f'key_{key}_mount_opening'
        assert any(result[row]['nearby_samples']>25 for result in report['parts'].values()), row
    conflicts = [(part, route) for part, rows in report['parts'].items()
                 for route, row in rows.items() if row['obstructed_poses']]
    assert not conflicts, conflicts


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive',type=Path)
    parser.add_argument('frames',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('carrier',nargs='+')
    args = parser.parse_args()
    keys(args.archive,args.frames,args.carrier,args.output)
