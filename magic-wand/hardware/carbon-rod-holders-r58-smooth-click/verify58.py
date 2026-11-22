"""Audit one native R58 slice folder from its deposited toolpaths.

Expects layout.3mf, layout.frame.json, OP1-hinge.gcode.3mf, OP1-hinge.gcode.native.json and
native/slice.log, as written by plate58.py and the saved headless slicer script.

The lowered key and socket routes use the fitted positions recorded by the carrier build.
The pack gauge includes the removable spring hook's intended flex space only during loading.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from plate58 import LABELS, MINIMUM_BASE_MM2, MODEL
import carrier58 as c
import fit57
from adhesion53 import bases, verify
from layers53 import inspect
from openings53 import check_routes, key_spaces, read_native
from panel54 import base54
from panel55 import settings
from parts52 import audit, digest
from verify57 import BAY, load_solid, report55, rod_bore, seam

ARCHIVE = 'OP1-hinge.gcode.3mf'
m, b = fit57.m, fit57.b
R57_LAYOUT = c.n.R57 / 'exports/print-mechanisms'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def gauges(carrier):
    geometry = fit57.gauges()
    holder = geometry['Key_Carrier']
    layout = carrier['key_layout']
    drop = carrier['change']['moved_down_mm']
    bottom_y, top_y = layout['row_centres_y_mm']
    left_x, right_x = layout['column_centres_x_mm']
    # The bought-component route files are in the R57 key-bank frame.
    seat_poses = {
        0: (-21, 0, left_x, bottom_y, layout['socket_turn_deg']['bottom_left']),
        2: (21, 0, right_x, bottom_y, layout['socket_turn_deg']['bottom_right']),
        3: (-21, 21.35, left_x, top_y, layout['socket_turn_deg']['top_left'] - 180),
        4: (21, 21.35, right_x, top_y, layout['socket_turn_deg']['top_right']),
    }
    for name, route in key_spaces().items():
        old_x, old_y, x, y, turn = seat_poses[int(name.split('_')[1])]
        holder[name] = [shape.translate((-old_x, -old_y, 0)).rotate((0, 0, turn))
                        .translate((x, y, -drop)) for shape in route]

    pouch = c.pack().translate((0, 0, .10))
    hook = b.box(c.MOUTH_X - .1, c.ROOM_X[0] + .01, c.REAR_Y - c.HOOK - .1,
                 c.REAR_Y + .3, c.LEAF[1] - .05, c.LEAF[2] + .05)
    holder['battery_seated'] = [pouch]
    holder['battery_slides_in_from_the_left'] = [pouch.translate((-dx, 0, 0)) - hook
                                                for dx in np.linspace(0., 33., 34)]
    return geometry


def check(plate, meshes=MODEL):
    archive, layout, frame_file = plate / ARCHIVE, plate / 'layout.3mf', plate / 'layout.frame.json'
    frame = read(frame_file)
    sha = digest(archive)
    native = read(archive.with_suffix('.native.json'))
    assert native['archive_sha256'] == sha and native['return_code'] == 0
    assert len(native['plates']) == 1
    assert frame['layout_sha256'] == digest(layout)
    assert set(frame['parts']) == set(LABELS)
    for part, entry in frame['parts'].items():
        assert digest(Path(meshes) / entry['source']) == entry['source_sha256'], part

    audit(archive, layout, plate / 'separation-and-machine.json', set(LABELS))
    adhesion = bases(archive)
    verify(adhesion, minimum_base_mm2=MINIMUM_BASE_MM2)
    write(plate / 'wide-bases.json', adhesion)

    points, labels = read_native(archive)
    records = {part: check_routes(routes, np.array(frame['parts'][part]['assembly_to_machine']), points, labels)
               for part, routes in gauges(read(Path(meshes) / 'carrier.json')).items()}
    write(plate / 'fit.json', dict(archive_sha256=sha, frame_sha256=digest(frame_file),
                                   pin_go_gauge_mm=2 * fit57.GO, parts=records))
    blocked = [(part, name) for part, rows in records.items() for name, row in rows.items() if row['obstructed_poses']]
    assert not blocked, blocked
    assert records['Touch_Paddle']['pin_go_gauge_through_barrel']['nearby_samples'] >= 25
    layers = inspect(archive)
    write(plate / 'layers.json', layers)
    assert layers['native_support_moves'] == 0
    assert all(not part['completely_unsupported_starts'] for part in layers['parts'].values())

    carrier = frame['parts']['Key_Carrier']
    position = np.asarray(carrier['assembly_to_machine'])
    write(plate / 'rod.json', rod_bore(archive, position))
    body = load_solid(Path(meshes) / carrier['source'])
    oriented = position[:3].copy()
    oriented[:2, 3] = 0
    on_bed = body.transform(oriented)
    panel = carrier['adhesion_panel']
    base, _, _ = base54(on_bed, settings(panel))
    base_in_machine = base.translate((float(position[0, 3]), float(position[1, 3]), 0))
    joint = seam(archive, frame, body, regions={'hinge_bay': BAY}, regional_base=base_in_machine)
    baseline = read(R57_LAYOUT / 'joint.json')['current']
    write(plate / 'joint.json', dict(r57=baseline, current=joint))
    prior_area = baseline['vertical_joint_area_mm2']
    assert .80 * prior_area <= joint['vertical_joint_area_mm2'] <= prior_area, (baseline, joint)
    assert len(joint['layers']) >= len(baseline['layers'])
    assert joint['regional_joint_area_mm2']['hinge_bay'] < .25, joint
    fin_design = report55(on_bed, panel)
    write(plate / 'fin-design.json', dict(archive_sha256=sha, **fin_design))
    assert fin_design['hinge_bay_open_to_panel_edge'] and fin_design['nearest_base_to_hinge_mm'] >= 3
    assert fin_design['base_volume_in_hinge_bay_mm3'] == 0 and fin_design['fins_on_hinge'] == 0
    assert len(fin_design['fins']) == 6 and fin_design['panel_pieces'] == 1
    assert 'got warnings:' not in (plate / 'native/slice.log').read_text()
    # The release check requires an independent disposition for any native support
    # warning. Collect the real deposition measurements before that decision.
    warning = native['plates'][0]['warning_message']
    if warning:
        print(f'Native slicer warning for review: {warning}')
    print(f'Passed R58 deposited-path and base checks, joint {joint["vertical_joint_area_mm2"]} mm², archive {sha}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('--meshes', type=Path, default=MODEL)
    args = parser.parse_args()
    check(args.plate, args.meshes)
