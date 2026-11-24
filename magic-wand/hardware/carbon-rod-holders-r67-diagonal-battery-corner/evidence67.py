"""Resolve the final review's empty-air scan and inspect the lower socket bores.

The turn above the holder has no bead centres in its one-millimetre search box.
Measure a conservative separation from *all* deposited samples instead, and put
the same plug deliberately into the nearby deck as a positive control.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile

import numpy as np
from shapely.geometry import Point

import audit67 as audit
import design67 as d


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def source():
    with tempfile.TemporaryDirectory() as scratch:
        regenerated = Path(scratch) / d.HOLDER
        d.b.save_closed(regenerated, d.carrier())
        report = dict(generator_sha256=digest(d.__file__),
                      carrier_sha256=digest(d.OUT / d.HOLDER),
                      reproduced_sha256=digest(regenerated))
    report['passes'] = report['carrier_sha256'] == report['reproduced_sha256']
    assert report['passes'], report
    return report


def slice_evidence(folder):
    archive = folder / audit.v.ARCHIVE
    points, labels = audit.v.read_native(archive)
    frame = np.asarray(audit.v.read(folder / 'layout.frame.json')['parts']['Key_Carrier']['assembly_to_machine'])
    poses = audit.prior.op1_routes()['op1_plug_turns_above_holder']
    bounds = np.asarray([shape.transform(frame[:3]).bounding_box() for shape in poses])
    low, high = bounds[:, :3].min(axis=0) - .05, bounds[:, 3:].max(axis=0) + .05
    delta = np.maximum(np.maximum(low - points[:, :3], points[:, :3] - high), 0)
    # The reader samples every .12 mm. Inflating by half that spacing plus the
    # half-width/half-height diagonal conservatively encloses the deposited bead.
    radius = np.hypot(points[:, 3], points[:, 4]) / 2 + .06
    separation = float((np.linalg.norm(delta, axis=1) - radius).min())
    assert separation > 0, separation
    local = points[:, :3] @ np.linalg.inv(frame)[:3, :3].T + np.linalg.inv(frame)[:3, 3]
    target = np.asarray((5., 1., 8.6))
    point = local[np.linalg.norm(local - target, axis=1).argmin()]
    assert np.linalg.norm(point - target) < 2, point
    first = poses[0]
    box = np.asarray(first.bounding_box()).reshape(2, 3)
    control = first.translate(point - box.mean(axis=0))
    witness = audit.v.check_routes({'plug_in_printed_deck': [control]}, frame, points, labels)['plug_in_printed_deck']
    assert witness['nearby_samples'] > 25 and witness['obstructed_poses'], witness
    native = (points, labels)
    bores = []
    for z in (7.3, 7.6, 7.95):
        section = audit.printed_seat.printed_contact(folder, archive, native, z)
        assert section.area > 30, (z, section.area)
        clear = [float(Point(0, y).distance(section)) for y in d.b.SOCKET_Y]
        assert min(clear) > d.b.SOCKET_R, (z, clear)
        bores.append(dict(z_mm=z, deposited_section_area_mm2=round(section.area, 3),
                          bore_clear_radii_mm=[round(r, 4) for r in clear]))
    report = dict(archive_sha256=digest(archive), checker_sha256=digest(__file__),
                  carrier_sha256=digest(d.OUT / d.HOLDER), passes=True,
                  turn_poses=len(poses), all_deposited_samples=len(points),
                  turn_aabb_clearance_lower_bound_mm=round(separation, 4),
                  positive_control=witness, lower_socket_sections=bores)
    (folder / 'supplemental-evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders', type=Path, nargs='*')
    args = parser.parse_args()
    report = source()
    (d.OUT / 'source-reproduction.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    for folder in args.folders:
        print(json.dumps(slice_evidence(folder)), flush=True)
