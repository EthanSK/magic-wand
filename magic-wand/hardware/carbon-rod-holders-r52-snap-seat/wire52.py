"""Distinguish the OP1 through-slot in the carrier wall from its open assembly approach."""
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

from arm_fixture52 import carrier_fixture
from build52 import union
from clearance51 import distance, patches
from orient51 import digest, load_solid
from printed_props51 import native_mask
from removal51 import unpack
from sockets52 import paths


def capsule_column(a, b, radius):
    return mf.Manifold.batch_hull([
        mf.Manifold.cylinder(60, radius, radius, 96).translate((*point, -20)) for point in (a, b)
    ])


def check(out):
    archive = out / 'Mechanisms.gcode.3mf'
    frame_path = out / 'layout.frame.json'
    carrier_path = out.parent / 'Key_Carrier-assembly.stl'
    frame = np.array(json.loads(frame_path.read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    inverse = np.linalg.inv(frame)
    a, b = patches()['wire']
    carrier = load_solid(carrier_path)
    # Include 2 mm of material around the whole 4.16 mm CAD outlet, then use
    # the *entire* carrier thickness there to conservatively bound the passage.
    collar = carrier ^ capsule_column(a, b, 4.08)
    lower, upper = np.array(collar.bounding_box())[[2, 5]]
    data, labels, owners, normal = unpack(archive)
    prop, _ = native_mask(archive, paths, data, owners['Key_Carrier'], normal)
    xyz = data[:, :3].copy()
    xyz[:, 2] = data[:, 7] - data[:, 4] / 2
    local = xyz @ inverse[:3, :3].T + inverse[:3, 3]
    radial = distance(local[:, :2], a, b)
    r = data[:, 3] / 2
    support = np.char.startswith(labels[data[:, 5].astype(int)], 'Support') | prop
    raw = support & (radial <= 1.616 + r) & (local[:, 2] > -6-r) & (local[:, 2] < 22+r)
    # Bound each full deposited segment between 0.12 mm samples with its
    # circumradius, including half-height, half-width and full sample pitch.
    reach = np.hypot(r, data[:, 4]/2) + .12
    finite = (radial <= 1.616 + reach) & (local[:, 2]+reach >= lower) & (local[:, 2]-reach <= upper)
    fixture, _ = carrier_fixture(frame)
    within = np.zeros(len(data), bool)
    for z in np.unique(data[raw,7]):
        idx = np.flatnonzero(raw & (data[:,7] == z))
        within[idx] = paths._inside(fixture.slice(float(z)-.101).offset(.25), data[idx,:2])
    categories = {}
    for i in np.unique(data[raw,5]).astype(int):
        mask = raw & (data[:,5]==i)
        categories[str(labels[i])] = int(mask.sum())
    result = dict(archive_sha256=digest(archive),frame_sha256=digest(frame_path),carrier_sha256=digest(carrier_path),
        centreline_xy_mm=[a,b],bundle_radius_mm=1.616,collar_outer_radius_mm=4.08,
        carrier_collar_z_mm=[lower,upper],projected_support_samples=int(raw.sum()),
        samples_on_removable_fixture=int((raw & within & prop).sum()),projected_features=categories,
        projected_assembly_min_xyz_mm=local[raw].min(0).tolist(),projected_assembly_max_xyz_mm=local[raw].max(0).tolist(),
        minimum_fixture_surface_z_mm=float(np.min(local[raw,2]-reach[raw])),
        finite_passage_support_samples=int((finite & support).sum()),
        finite_passage_permanent_samples=int((finite & ~support).sum()))
    print(result,flush=True)
    (out/'op1-wire-passage.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    check(Path(sys.argv[1]))
