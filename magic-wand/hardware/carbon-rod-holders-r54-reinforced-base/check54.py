"""Check the holder-only native slice and bind its measurements to that archive."""
import argparse
import json
from pathlib import Path

from plate54 import CARRIER, LABELS, R53, load_solid
from adhesion53 import bases, verify
from bridge53 import compare
from joint54 import measure
from layers53 import inspect
from mating53 import gauges
from openings53 import check_routes, digest, read_native
from part_map53 import font, generate
from panel54 import report54
from PIL import Image, ImageDraw
from parts52 import audit
from sockets52 import key_spaces
import numpy as np


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def check(plate, frame_file):
    archive = plate / 'Key-holder.gcode.3mf'
    layout = plate / 'layout.3mf'
    sha = digest(archive)
    native = json.loads(archive.with_suffix('.native.json').read_text())
    assert native['archive_sha256'] == sha
    assert native['return_code'] == 0 and not native['plates'][0]['warning_message'], native
    log = (plate / 'native/slice.log').read_text()
    assert 'got warnings:' not in log, log[-900:]
    frame = json.loads(frame_file.read_text())
    assert frame['layout_sha256'] == digest(layout)
    carrier = frame['parts']['Key_Carrier']
    assert carrier['source_sha256'] == digest(CARRIER)
    transform = np.array(carrier['assembly_to_machine'])
    assert np.allclose(abs(transform[:3, 1]), [0, 0, 1])
    data, types = read_native(archive)
    prior = R53 / 'exports/print-mechanisms'
    prior_frame = json.loads((prior / 'layout.frame.json').read_text())
    groups = [('keys', key_spaces()), ('fit', gauges()['Key_Carrier'])]
    for name, regions in groups:
        result = check_routes(regions, transform, data, types)
        write(plate / (name + '.json'), dict(archive_sha256=sha, frame_sha256=digest(frame_file), parts={'Key_Carrier': result}))
        earlier = json.loads((prior / (name + '.json')).read_text())['parts']['Key_Carrier']
        assert all(row['nearby_samples'] > 25 for key, row in result.items()
                   if earlier[key]['nearby_samples'] > 25), name
        assert not [key for key, row in result.items() if row['obstructed_poses']], result

    def rod_samples(points, labels, direction):
        radius = np.linalg.norm(points[:, :2] - direction[:2, 3], axis=1)
        intersects = radius - points[:, 3] / 2 - .06 < 4
        features = np.array([label.startswith(('Support', 'Prime tower', 'Skirt')) for label in labels])
        assert not (intersects & features[points[:, 5].astype(int)]).any()
        selected = points[intersects & (points[:, 7] <= 2.401)]
        return selected[:, :3] - direction[:3, 3]

    old_points, old_types = read_native(prior / 'OP1-hinge.gcode.3mf')
    old_transform = np.asarray(prior_frame['parts']['Key_Carrier']['assembly_to_machine'])
    previous_rod_contacts = rod_samples(old_points, old_types, old_transform)
    current_rod_contacts = rod_samples(data, types, transform)
    assert len(previous_rod_contacts) > 50 and len(current_rod_contacts) > 50
    def nearest_squared(points):
        deltas = points[:, None, :] - previous_rod_contacts[None, :, :]
        return np.square(deltas).sum(axis=2).min(axis=1)
    nearest = np.concatenate([nearest_squared(current_rod_contacts[i:i+128])
                              for i in range(0, len(current_rod_contacts), 128)])
    # These layers include an intentional R53 rod clip. Check location against
    # its earlier paths so any added plastic in the rod opening is rejected.
    new_contacts = int((nearest > .29**2).sum())
    write(plate / 'rod.json', dict(archive_sha256=sha, radius_mm=4,
                                   earlier_snap_land_samples=len(previous_rod_contacts),
                                   retry_snap_land_samples=len(current_rod_contacts),
                                   contacts_outside_existing_path_region=new_contacts))
    assert not new_contacts

    adhesion = bases(archive)
    verify(adhesion)
    write(plate / 'wide-base.json', adhesion)
    audit(archive, layout, plate / 'machine.json', set(LABELS))
    shape = load_solid(CARRIER)
    previous = measure(prior / 'OP1-hinge.gcode.3mf', prior_frame, shape)
    current = measure(archive, frame, shape)
    ratio = current['vertical_joint_area_mm2'] / previous['vertical_joint_area_mm2']
    write(plate / 'joint.json', dict(new=current, previous=previous, contact_ratio=round(ratio, 2)))
    assert ratio >= 4 and len(current['layers']) >= 4, (current, previous)
    assert any(row['left_mm'] for row in current['layers']) and any(row['right_mm'] for row in current['layers'])

    layers = inspect(archive)
    layer_report = plate / 'layers.json'
    write(layer_report, layers)
    assert not layers['native_support_moves']
    assert not layers['parts']['Key_Carrier']['completely_unsupported_starts'], layers['parts']['Key_Carrier']['completely_unsupported_starts']
    compare(layer_report, frame_file, plate / 'spans.json')
    draw_map(plate, frame_file, shape)
    print('Native openings, joint, base, tower and machine checks passed. Joint area ratio', round(ratio, 2), flush=True)


def draw_map(plate, frame_file, shape):
    archive = plate / 'Key-holder.gcode.3mf'
    sha = digest(archive)
    carrier = json.loads(frame_file.read_text())['parts']['Key_Carrier']
    transform = np.array(carrier['assembly_to_machine'])
    map_file = plate / 'tray.png'
    generate(archive, frame_file, CARRIER.parent, LABELS, map_file)
    bed_pose = transform[:3].copy()
    bed_pose[:2, 3] = 0
    oriented = shape.transform(bed_pose)
    design = report54(oriented, carrier['adhesion_panel'])
    write(plate / 'fin-design.json', dict(archive_sha256=sha, **design))
    image = Image.open(map_file).convert('RGB')
    draw = ImageDraw.Draw(image)
    color = '#247851'
    for fin in design['fins']:
        x, y = np.asarray(fin['cut_at_xy']) + transform[:2, 3]
        cx, cy = 32 + x * 4, 805 - y * 4
        draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=color, outline='white', width=2)
    draw.ellipse((789, 322, 801, 334), fill=color)
    draw.text((827, 315), 'Snip all six fins at the green marks', fill='#15272d', font=font(20))
    draw.rectangle((823, 768, 1216, 811), fill='#faf8f4')
    draw.text((827, 777), 'Discard base after clipping', fill='#15272d', font=font(19))
    image.save(map_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    parser.add_argument('--frame', type=Path)
    parser.add_argument('--map-only', action='store_true')
    args = parser.parse_args()
    frame = args.frame or args.plate / 'layout.frame.json'
    if args.map_only:
        draw_map(args.plate, frame, load_solid(CARRIER))
    else:
        check(args.plate, frame)
