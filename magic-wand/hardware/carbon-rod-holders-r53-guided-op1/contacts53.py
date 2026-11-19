"""Measure where the paddle crowns and journal retainer end in the actual deposited layers."""
import argparse
import json
from pathlib import Path

import numpy as np
import build53 as cad
from openings53 import digest, read_native


def measure(archive, frames_path):
    frames = json.loads(frames_path.read_text())['parts']
    data, names = read_native(archive)
    model = np.array([not name.startswith(('Prime tower','Support','Skirt','Brim')) for name in names])
    beads = data[model[data[:, 5].astype(int)]]
    def column(part, xy, radius):
        frame = np.asarray(frames[part]['assembly_to_machine'])
        assert np.isclose(frame[2, 2], -1.0)
        centre = (frame @ [*xy, cad.SEAT_Z, 1])[:2]
        near = beads[np.all(np.abs(beads[:, :2] - centre) < radius + 1, axis=1)]
        region = near[np.linalg.norm(near[:, :2] - centre, axis=1) < radius]
        assert len(region) > 20, (part, xy, len(region))
        deposited = frame[2, 3] - region[:, 7]
        layer = region[np.isclose(deposited, deposited.min(), atol=.005)]
        return float(deposited.min()), np.ptp(layer[:, :2], axis=0).tolist(), len(layer)
    crowns = []
    for station in (0, cad.MIRROR_STATION):
        point = cad.board_point(0, station)
        apex, extent, samples = column('Touch_Paddle', point, 1.7)
        crowns.append(dict(station_xy_mm=list(point), sliced_apex_assembly_z_mm=apex,
                           deepest_layer_span_mm=extent, deepest_layer_samples=samples,
                           modeled_apex_assembly_z_mm=cad.crown_apex(station)))
        assert min(extent) >= 2.4 and abs(apex - cad.crown_apex(station)) <= .13
    clearances = []
    for x in (-8.5, 8.5):
        xy = (x, cad.AXIS_Y)
        cap_z = column('Hinge_Cap', xy, .45)[0]
        frame = np.asarray(frames['Touch_Paddle']['assembly_to_machine'])
        axis_xy = (frame @ [*xy, cad.SEAT_Z, 1])[:2]
        near = beads[np.linalg.norm(beads[:, :2] - axis_xy, axis=1) < .45]
        journal_top = float(frame[2, 3] - np.min(near[:, 7] - near[:, 4]))
        gap = cap_z - journal_top
        clearances.append(dict(journal_x_mm=x, cap_z_mm=cap_z, journal_flat_z_mm=journal_top, gap_mm=gap))
        assert .16 <= gap <= .25, (xy, gap)
    return dict(archive_sha256=digest(archive), crowns=crowns, journal_cap=clearances)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for key in ('archive','frames','report'):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    args.report.write_text(json.dumps(measure(args.archive, args.frames),indent=2)+'\n')
