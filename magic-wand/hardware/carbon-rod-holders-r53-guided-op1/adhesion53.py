"""Measure each part's external peel-away brim on its actual two bottom layers."""
import argparse
import itertools
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import MultiPoint

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r52-snap-seat'))
from tower_check52 import GRID, footprint, measure, q
from parts52 import digest


def outer_envelope(mask, origin):
    # Only left/right occupied pixels in each row can be convex hull vertices.
    rows = np.flatnonzero(mask.any(axis=1))
    used = mask[rows]
    left = used.argmax(axis=1)
    right = used.shape[1] - 1 - used[:, ::-1].argmax(axis=1)
    xy = np.vstack([np.column_stack((x, rows)) for x in (left, right)])
    return MultiPoint(xy * GRID + origin).convex_hull.buffer(GRID / 2**.5)


def bases(archive):
    with ZipFile(archive) as source:
        settings = json.loads(source.read('Metadata/project_settings.config'))
        meta = ET.fromstring(source.read('Metadata/slice_info.config')).find('plate')
        owners = {o.get('name'): int(o.get('identify_id')) for o in meta.findall('object')}
        text = source.read('Metadata/plate_1.gcode').decode()
    assert not any(line.startswith('; FEATURE: Support') for line in text.splitlines())
    pts, names, _ = q.extrusion_points('; CHANGE_LAYER'.join(text.split('; CHANGE_LAYER', 3)[:3]), GRID)
    pts[:, :2] += np.fromstring(settings['extruder_offset'][0], sep='x')
    report = {}
    envelopes = {}
    for name, owner in {**owners, 'wipe_tower': None}.items():
        if owner is None:
            which = pts[:, 5] == names.index('Prime tower')
        else:
            functional = ~np.isin(pts[:, 5], [i for i, n in enumerate(names) if n in ('Prime tower', 'Skirt')])
            which = functional if len(owners) == 1 else functional & (pts[:, 6] == owner)
        own = pts[which]
        origin = np.floor(own[:, :2].min(axis=0)) - 1
        shape = tuple(np.ceil((own[:, :2].max(axis=0) - origin + 1) / GRID).astype(int)[::-1])
        def raster(subset):
            return footprint(subset, origin, shape)
        first = own[np.isclose(own[:, 7], .2)]
        base = raster(first)
        upper = raster(own[np.isclose(own[:, 7], .4)])
        touching = np.argwhere(base & upper)
        assert touching.size, f'{name} has no physical join to the second layer'
        # Start on the body so a large but detached skirt cannot pass.
        connected = Image.fromarray(base.astype(np.uint8)).copy()
        ImageDraw.floodfill(connected, tuple(int(i) for i in touching[len(touching) // 2][::-1]), 2)
        anchored = np.asarray(connected) == 2
        mm2 = lambda mask: round(float(mask.sum()) * GRID**2, 2)
        envelopes[name] = outer_envelope(base | upper, origin)
        minx, miny, maxx, maxy = envelopes[name].bounds
        row = dict(connected_base_mm2=mm2(anchored), first_layer_total_mm2=mm2(base),
                   second_layer_on_connected_base_mm2=mm2(upper & anchored),
                   second_layer_total_mm2=mm2(upper),
                   bed_edge_mm=round(min(minx, miny, 180-maxx, 180-maxy), 2))
        if owner is not None and 'Brim' in names:
            row['outer_brim_mm2'] = mm2(raster(first[first[:, 5] == names.index('Brim')]))
        report[name] = row
    gaps = {f'{a} / {b}': round(envelopes[a].distance(envelopes[b]), 2)
            for a, b in itertools.combinations(envelopes, 2)}
    tower = measure(archive)
    return dict(archive_sha256=digest(archive), grid_mm=GRID, parts=report,
                minimum_base_gap_mm=min(gaps.values()), convex_hull_gap_lower_bounds_mm=gaps, tower=tower)


def verify(data):
    for name, row in data['parts'].items():
        assert row['connected_base_mm2'] >= 2849, (name, row)
        assert row['bed_edge_mm'] >= 2, (name, row)
        assert row['second_layer_on_connected_base_mm2'] >= .90 * row['second_layer_total_mm2'], (name, row)
    assert data['minimum_base_gap_mm'] >= 3, data['convex_hull_gap_lower_bounds_mm']
    tower = data['tower']
    assert tower['second_layer_overlap_with_connected_base_mm2'] >= .95 * tower['second_layer_area_mm2']
    assert tower['second_layer_overlap_with_connected_base_mm2'] >= 300
    assert all(j['continuous_to_bed_mm2'] > 0 and not j['unbacked_islands'] for j in tower['root_joints'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = bases(args.archive)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(result['parts'], result['minimum_base_gap_mm'])
    verify(result)
