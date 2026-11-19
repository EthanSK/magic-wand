"""Measure the tower's connected bed footprint and its joint to the next layer."""
from pathlib import Path
import json
import sys
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw
from parts52 import digest
from support51 import footprint, q, GRID


def measure(archive):
    with ZipFile(archive) as source:
        text = source.read('Metadata/plate_1.gcode').decode()
        boxes = json.loads(source.read('Metadata/plate_1.json'))['bbox_objects']
        config = json.loads(source.read('Metadata/project_settings.config'))
    tower_box = np.array(next(row['bbox'] for row in boxes if row['name'] == 'wipe_tower')).reshape((2, 2))
    first_layers = text.split('; CHANGE_LAYER', 3)
    points, names, _ = q.extrusion_points('; CHANGE_LAYER'.join(first_layers[:3]), .10)
    points[:, :2] += np.fromstring(config['extruder_offset'][0], sep='x')
    is_tower = points[:, 5] == names.index('Prime tower')
    tower = points[is_tower]
    origin = np.floor(tower[:, :2].min(0)) - 1
    shape = tuple((np.ceil((tower[:, :2].max(0) - origin + 1) / GRID)).astype(int)[::-1])
    layers = [footprint(tower[np.isclose(tower[:, 7], z)], origin, shape) for z in (.2, .4)]
    first, second = layers
    overlap = first & second
    if not overlap.any():
        raise ValueError('Tower trunk and bed layer do not overlap')
    supported_yx = np.argwhere(overlap)
    raster = Image.fromarray(first.astype(np.uint8)).copy()
    ImageDraw.floodfill(raster, tuple(map(int, supported_yx[len(supported_yx)//2][::-1])), 2)
    connected = np.asarray(raster) == 2
    # A conservative rectangular exclusion contains the complete native tower/brim,
    # including the gaps between adjacent lines and any rounded corners.
    # Single-object Bambu jobs can omit object labels entirely.
    functional_features = [i for i, name in enumerate(names) if name not in ('Prime tower', 'Skirt', 'Brim')]
    occupied = points[np.isin(points[:, 5], functional_features) & np.isin(np.rint(points[:, 7] * 5), [1, 2])]
    distances = np.maximum(0, np.maximum(tower_box[0] - occupied[:, :2], occupied[:, :2] - tower_box[1]))
    clearance = np.linalg.norm(distances, axis=1) - occupied[:, 3] / 2 - .05
    hi = tower[:, :2] + tower[:, 3:4] / 2
    lo = tower[:, :2] - tower[:, 3:4] / 2
    area = lambda mask: round(float(mask.sum()) * GRID**2, 2)
    return dict(archive_sha256=digest(archive), width_setting_mm=float(config['prime_tower_brim_width']),
                tower_and_brim_bounds_mm=tower_box.tolist(), connected_bed_area_mm2=area(connected),
                total_deposited_bed_area_mm2=area(first), second_layer_area_mm2=area(second),
                second_layer_overlap_with_connected_base_mm2=area(connected & second),
                minimum_bed_edge_mm=round(float(min(lo.min(),(180-hi).min())),2),
                minimum_other_part_gap_first_two_layers_mm=round(float(clearance.min()),2))


def check(directory, original):
    native = next(directory.glob('*.gcode.3mf'))
    selected, earlier = measure(native), measure(original)
    assert earlier['width_setting_mm'] == 3 and earlier['connected_bed_area_mm2'] < 600
    assert selected['width_setting_mm'] > earlier['width_setting_mm']
    assert selected['connected_bed_area_mm2'] >= 2849, selected
    assert selected['minimum_bed_edge_mm'] >= 3 and selected['minimum_other_part_gap_first_two_layers_mm'] >= 3, selected
    assert selected['second_layer_overlap_with_connected_base_mm2'] >= .85 * selected['second_layer_area_mm2'], selected
    report = dict(original=earlier, selected=selected, grid_mm=GRID)
    (directory/'tower-base.json').write_text(json.dumps(report, indent=2)+'\n')
    print(native.name, selected, flush=True)
    return report


if __name__ == '__main__':
    check(*map(Path,sys.argv[1:3]))
