"""Audit one native R59 slice folder from its deposited toolpaths.

Expects layout.3mf, layout.frame.json, OP1-hinge.gcode.3mf, OP1-hinge.gcode.native.json and
native/slice.log, as written by plate59.py and the saved headless slicer script.

Same shared checks as R58: separation, pad areas, deposited-path gauges, unsupported starts, rod
bore, holder base seam and fins. R59 gauges added to the holder: every key and socket route at its
fitted position, each finger guard sliding onto its rails, and the battery sliding in from the rear.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from manifold3d import Manifold

from build59 import CLIP_T
from plate59 import LABELS, MINIMUM_BASE_MM2, MODEL, placement_parts59
import carrier59 as f
import fit57
from adhesion53 import bases, verify
from layers53 import inspect
from openings53 import check_routes, key_spaces, read_native
from panel54 import base54
from panel55 import settings
from parts52 import audit, digest
from verify57 import BAY, load_solid, report55, rod_bore, seam

ARCHIVE = 'OP1-hinge.gcode.3mf'
R57_LAYOUT = f.n.R57 / 'exports/print-mechanisms'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def gauges(carrier):
    geometry = fit57.gauges()
    holder = geometry['Key_Carrier']
    hinge = fit57.m
    inner, outer = hinge.CHEEK_X
    for side, (low, high) in {'left': (-outer - .6, -inner), 'right': (inner, outer + .6)}.items():
        holder[f'pin_go_gauge_through_{side}_cheek'] = [
            fit57.rod(hinge.AXIS_Y, hinge.CHEEK_HOLE_Z, fit57.GO, low, high)
        ]
    board_frame = hinge.b
    clip_profile = hinge.chain()
    mouth_half = clip_profile.CLIP_SLOT / 2 - .10
    for side, x in {'Left': -board_frame.HOLE_X, 'Right': board_frame.HOLE_X}.items():
        y, bottom = board_frame.HOLE_Y, board_frame.BOARD_TOP
        bore = Manifold.cylinder(CLIP_T + .1, clip_profile.NECK_R - .10, circular_segments=48)
        mouth = board_frame.box(x - mouth_half, x + mouth_half, y + .2, y + clip_profile.CLIP_TIP + .15,
                                bottom - .05, bottom + CLIP_T + .05)
        geometry[f'DFR_Clip_{side}'] = {'post_clip_bore_and_mouth': [bore.translate((x, y, bottom - .05)) + mouth]}
    layout = carrier['key_layout']
    drop = carrier['change']['moved_down_mm']
    bottom_y, top_y = layout['row_centres_y_mm']
    left_x, right_x = layout['column_centres_x_mm']
    turn = layout['socket_turn_deg']
    seats = {0: (-21, 0, left_x, bottom_y, turn['bottom_left']), 2: (21, 0, right_x, bottom_y, turn['bottom_right']),
             3: (-21, 21.35, left_x, top_y, turn['top_left'] - 180), 4: (21, 21.35, right_x, top_y, turn['top_right'])}
    for name, route in key_spaces().items():
        old_x, old_y, x, y, angle = seats[int(name.split('_')[1])]
        holder[name] = [shape.translate((-old_x, -old_y, 0)).rotate((0, 0, angle)).translate((x, y, -drop)) for shape in route]
    for side, sign in (('right', 1.0), ('left', -1.0)):
        guard = f.guard(sign)
        holder[f'{side}_guard_slides_onto_its_rails'] = [guard.translate((0, -float(dy), 0)) for dy in np.arange(1.0, 14.1, 1.0)]
    pouch = f.pack()
    holder['battery_seated'] = [pouch]
    holder['battery_slides_in_from_the_rear'] = [pouch.translate((0, float(dy), 0)) for dy in np.linspace(0.0, 29.0, 30)]
    return geometry


def check(plate, meshes=MODEL):
    archive, layout, frame_file = plate / ARCHIVE, plate / 'layout.3mf', plate / 'layout.frame.json'
    frame = read(frame_file)
    sha = digest(archive)
    native = read(archive.with_suffix('.native.json'))
    assert native['archive_sha256'] == sha and native['return_code'] == 0
    assert len(native['plates']) == 1
    # As in the R58 verifier: the slicer's floating-region estimate is recorded for review, and the
    # deposited paths below decide whether anything really starts unsupported.
    warning = native['plates'][0]['warning_message']
    if warning:
        print(f'Native slicer warning for review: {warning}')
    write(plate / 'slicer-warning.json', dict(archive_sha256=sha, warning=warning))
    assert 'got warnings:' not in (plate / 'native/slice.log').read_text()
    assert frame['layout_sha256'] == digest(layout)
    assert set(frame['parts']) == set(LABELS)
    for part in placement_parts59(meshes):
        assert digest(part['source']) == frame['parts'][part['name']]['source_sha256'], part['name']

    audit(archive, layout, plate / 'separation-and-machine.json', set(LABELS))
    adhesion = bases(archive)
    verify(adhesion, minimum_base_mm2=MINIMUM_BASE_MM2)
    write(plate / 'wide-bases.json', adhesion)

    points, labels = read_native(archive)
    records = {part: check_routes(routes, np.array(frame['parts'][part]['assembly_to_machine']), points, labels)
               for part, routes in gauges(read(Path(meshes) / 'carrier.json')).items()}
    write(plate / 'fit.json', dict(archive_sha256=sha, frame_sha256=digest(frame_file), pin_go_gauge_mm=2 * fit57.GO, parts=records))
    blocked = [(part, name) for part, rows in records.items() for name, row in rows.items() if row['obstructed_poses']]
    assert not blocked, blocked
    for part, names in {'Key_Carrier': ['pin_go_gauge_through_left_cheek', 'pin_go_gauge_through_right_cheek'],
                        'Touch_Paddle': ['pin_go_gauge_through_barrel', 'post_-1', 'post_1']}.items():
        for name in names:
            assert records[part][name]['nearby_samples'] >= 25, (part, name)
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
    panel = carrier['adhesion_panel']
    on_bed = body.transform(oriented)
    base, _, _ = base54(on_bed, settings(panel))
    base_in_machine = base.translate((float(position[0, 3]), float(position[1, 3]), 0))
    joint = seam(archive, frame, body, regions={'hinge_bay': BAY}, regional_base=base_in_machine)
    baseline = read(R57_LAYOUT / 'joint.json')['current']
    write(plate / 'joint.json', dict(r57=baseline, current=joint))
    prior_area = baseline['vertical_joint_area_mm2']
    assert .80 * prior_area <= joint['vertical_joint_area_mm2'] <= prior_area, (baseline, joint)
    assert joint['regional_joint_area_mm2']['hinge_bay'] < .25, joint
    base = report55(on_bed, panel)
    write(plate / 'fin-design.json', dict(archive_sha256=sha, **base))
    assert base['hinge_bay_open_to_panel_edge'] and base['nearest_base_to_hinge_mm'] >= 3
    assert base['base_volume_in_hinge_bay_mm3'] == 0 and base['fins_on_hinge'] == 0
    assert len(base['fins']) == 6 and base['panel_pieces'] == 1
    print(f'Passed R59 native checks, holder seam {joint["vertical_joint_area_mm2"]} mm2, archive {sha}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('--meshes', type=Path, default=MODEL)
    args = parser.parse_args()
    check(args.plate, args.meshes)
