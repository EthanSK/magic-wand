"""Gauge the deposited toolpaths of an R57 slice: pin holes, clip well, sleeve, posts and holder routes.

Every gauge is a solid in assembly coordinates. A gauge passes when no printed bead, of any
owner or feature type, enters it. The pin gauges are 3.2 mm, 0.2 mm larger than the pin.
"""
import argparse
import json
from pathlib import Path

import manifold3d as mf
import numpy as np

import build57 as m

b = m.b
import mating53  # noqa: E402
from openings53 import check_routes, digest, read_native  # noqa: E402

GO = m.PIN_R + 0.10


def rod(y, z, radius, x0, x1):
    return mf.Manifold.cylinder(x1 - x0, radius, radius, 48).rotate((0, 90, 0)).translate((x0, y, z))


def gauges():
    old = mating53.gauges()            # board, switch, lead and lid routes; sleeve and post gauges
    carrier = {name: poses for name, poses in old['Key_Carrier'].items()
               if name not in ('journals_from_above', 'hinge_cap_from_rear')}
    reach = m.CHEEK_X[1] + 0.6
    # A 3.2 mm rod on the centre of both cheek holes, from outside one cheek to outside the other.
    carrier['pin_go_gauge_through_both_cheeks'] = [rod(m.AXIS_Y, m.CHEEK_HOLE_Z, GO, -reach, reach)]
    # The paddle barrel lowers between the two cheeks.
    barrel = b.box(-m.BARREL_X - 0.1, m.BARREL_X + 0.1, m.BARREL_Y[0] - 0.1, m.BARREL_Y[1] - 0.2, 12.4, 19.3)
    carrier['barrel_between_cheeks_from_above'] = [barrel.translate((0, 0, float(z))) for z in np.arange(0, 10.1, 1.0)]
    paddle = dict(old['Touch_Paddle'])
    paddle['pin_go_gauge_through_barrel'] = [rod(m.AXIS_Y, m.BARREL_HOLE_Z, GO, -m.BARREL_X - 0.5, m.BARREL_X + 0.5)]
    half, front, rear = m.WELL
    paddle['pin_clip_well'] = [b.box(-m.CLIP_T / 2 - 0.15, m.CLIP_T / 2 + 0.15, front + 0.35, rear - 0.35, 12.3, 19.6)]
    return {'Key_Carrier': carrier, 'Touch_Paddle': paddle}


def check(archive, framefile, output):
    frame = json.loads(framefile.read_text())['parts']
    points, labels = read_native(archive)
    records = {}
    for part, routes in gauges().items():
        records[part] = check_routes(routes, np.array(frame[part]['assembly_to_machine']), points, labels)
    data = dict(archive_sha256=digest(archive), frame_sha256=digest(framefile), pin_go_gauge_mm=2 * GO, parts=records)
    output.write_text(json.dumps(data, indent=2) + '\n')
    bad = [(part, name) for part, rows in records.items() for name, row in rows.items() if row['obstructed_poses']]
    empty = [(part, name) for part, rows in records.items() for name, row in rows.items()
             if name.startswith('pin_') and row['nearby_samples'] < 25]
    if bad or empty:
        raise ValueError(dict(obstructed=bad, no_nearby_paths=empty))


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    for name in ('archive', 'frame', 'output'):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    check(args.archive, args.frame, args.output)
