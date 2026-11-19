"""Measure the tower's connected bed footprint and its joint to the next layer."""
from pathlib import Path
import json
import re
import sys
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw
from parts52 import digest
from support51 import footprint, lost_islands, q, GRID


def root_joints(text, offset, origin, connected):
    """Measure all fourteen interfaces through the bottom 3 mm from the native beads."""
    bottom = '; CHANGE_LAYER'.join(text.split('; CHANGE_LAYER', 16)[:16])
    tower_only = re.sub(r'^; FEATURE: (?!Prime tower$).*$', '; FEATURE: Custom',
                        bottom, flags=re.MULTILINE)
    beads, names, _ = q.extrusion_points(tower_only, GRID)
    assert names == ['Prime tower'], names
    beads[:, :2] += offset
    previous = connected
    straight_to_bed = connected.copy()
    joints = []
    for index in range(2, 16):
        top = index / 5
        current = footprint(beads[np.isclose(beads[:, 7], top)], origin, connected.shape)
        contact = current & previous
        straight_to_bed &= current
        joints.append(dict(upper_layer_top_mm=top, contact_mm2=round(contact.sum()*GRID**2, 2),
                           continuous_to_bed_mm2=round(straight_to_bed.sum()*GRID**2, 2),
                           unbacked_islands=lost_islands(current, previous, origin)))
        previous = current
    return joints


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
    joints = root_joints(text, np.fromstring(config['extruder_offset'][0], sep='x'), origin, connected)
    return dict(root_joints=joints, archive_sha256=digest(archive), width_setting_mm=float(config['prime_tower_brim_width']),
                tower_and_brim_bounds_mm=tower_box.tolist(), connected_bed_area_mm2=area(connected),
                total_deposited_bed_area_mm2=area(first), second_layer_area_mm2=area(second),
                second_layer_overlap_with_connected_base_mm2=area(connected & second),
                minimum_bed_edge_mm=round(float(min(lo.min(),(180-hi).min())),2),
                minimum_other_part_gap_first_two_layers_mm=round(float(clearance.min()),2))


def check(directory, original):
    native = next(directory.glob('*.gcode.3mf'))
    selected, earlier = measure(native), measure(original)
    log = (directory / 'native/slice.log').read_text()
    warning_lines = [line.split('got warnings:', 1)[1].strip()
                     for line in log.splitlines() if 'got warnings:' in line]
    assert not warning_lines, warning_lines
    validate(selected, earlier)
    report = dict(previous_wide_tower=earlier, selected=selected, grid_mm=GRID,
                  slicer_placement_warnings=warning_lines)
    (directory/'tower-base.json').write_text(json.dumps(report, indent=2)+'\n')
    print(native.name, selected['connected_bed_area_mm2'], flush=True)
    return report


def validate(selected, earlier):
    assert selected['connected_bed_area_mm2'] >= max(2849, earlier['connected_bed_area_mm2']), selected
    assert selected['minimum_bed_edge_mm'] >= 3
    assert selected['minimum_other_part_gap_first_two_layers_mm'] >= 3
    root = 'second_layer_overlap_with_connected_base_mm2'
    assert selected[root] >= .95 * selected['second_layer_area_mm2']
    assert selected[root] >= 2 * earlier[root]
    for new, old in zip(selected['root_joints'], earlier['root_joints'], strict=True):
        assert new['upper_layer_top_mm'] == old['upper_layer_top_mm']
        assert new['contact_mm2'] > old['contact_mm2'], (new, old)
        assert new['continuous_to_bed_mm2'] > 0 and not new['unbacked_islands'], new


def verify_report(report, native_hash):
    selected = report['selected']
    assert selected['archive_sha256'] == native_hash
    assert report['slicer_placement_warnings'] == []
    assert len(selected['root_joints']) == 14
    validate(selected, report['previous_wide_tower'])


if __name__ == '__main__':
    check(*map(Path,sys.argv[1:3]))
