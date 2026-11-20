"""Measure deposited material crossing the carrier-to-base seam at each layer."""
import json
from zipfile import ZipFile

import numpy as np

from openings53 import digest
from support51 import footprint, q


GRID = .10
HEIGHT = .20


def seam_samples(section):
    points, normals, weights = [], [], []
    for loop in section.to_polygons():
        following = np.roll(loop, -1, axis=0)
        twice_area = np.sum(loop[:, 0] * following[:, 1] - loop[:, 1] * following[:, 0])
        if twice_area <= 0:
            continue
        for start, end in zip(loop, following):
            delta = end - start
            span = np.linalg.norm(delta)
            if span < .001:
                continue
            count = int(np.ceil(span / .08))
            points.extend(start + delta * ((np.arange(count) + .5) / count)[:, None])
            normals.extend([np.array((delta[1], -delta[0])) / span] * count)
            weights.extend([span / count] * count)
    return np.asarray(points), np.asarray(normals), np.asarray(weights)


def measure(archive, frame, body):
    with ZipFile(archive) as src:
        text = src.read('Metadata/plate_1.gcode').decode()
        settings = json.loads(src.read('Metadata/project_settings.config'))
    short = '; CHANGE_LAYER'.join(text.split('; CHANGE_LAYER')[:14])
    data, labels, _ = q.extrusion_points(short, .06)
    data = data[~np.isin(data[:, 5], [i for i, label in enumerate(labels)
                                     if label in ('Prime tower', 'Skirt')])]
    data[:, :2] += np.fromstring(settings['extruder_offset'][0], sep='x')
    position = np.asarray(frame['parts']['Key_Carrier']['assembly_to_machine'])
    solid = body.transform(position[:3])
    origin = np.floor(data[:, :2].min(axis=0)) - 1
    size = tuple(np.ceil((data[:, :2].max(axis=0) - origin + 1) / GRID).astype(int)[::-1])

    rows = []
    for layer in range(1, 13):
        z = layer * HEIGHT
        deposited = data[np.isclose(data[:, 7], z)]
        if not len(deposited):
            continue
        occupied = footprint(deposited, origin, size)
        samples, normals, weights = seam_samples(solid.slice(z - HEIGHT / 2))
        # Follow each normal across the original part boundary. Requiring
        # occupied pixels half a millimetre outside it rejects the stock wall.
        joined = np.ones(len(samples), dtype=bool)
        for offset in (-.25, -.10, .05, .20, .35, .52):
            ij = np.rint((samples + normals * offset - origin) / GRID).astype(int)
            joined &= occupied[ij[:, 1], ij[:, 0]]
        if joined.any():
            x = samples[:, 0] - position[0, 3]
            rows.append(dict(layer=layer, fused_length_mm=round(weights[joined].sum(), 2),
                             left_mm=round(weights[joined & (x < -4)].sum(), 2),
                             right_mm=round(weights[joined & (x > 4)].sum(), 2)))
    return dict(archive_sha256=digest(archive), layers=rows,
                vertical_joint_area_mm2=round(sum(row['fused_length_mm'] for row in rows) * HEIGHT, 2))
