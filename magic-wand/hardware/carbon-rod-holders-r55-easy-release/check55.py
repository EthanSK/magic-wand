"""Audit the exact seven-piece native slice, especially the removable holder panel."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
import numpy as np

from plate55 import HERE, LABELS, MODEL, R53, R54
from adhesion53 import bases, verify
from bridge53 import compare
from contacts53 import measure as switch_contacts
from joint54 import measure as seam
from layers53 import inspect
from mating53 import check as mating
from native_layout53 import load_solid, mesh_path
from openings53 import keys, read_native
from panel55 import BAY, report55
from part_map53 import font, generate
from parts52 import audit
from release53 import check_paths, digest, read


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def check_rod(archive, frame, baseline, previous_frame):
    def contacts(path, position):
        points, labels = read_native(path)
        local = points[:, :3] - position[:3, 3]
        nearby = np.linalg.norm(local[:, :2], axis=1) - points[:, 3] / 2 - .06 < 4
        temporary = np.array([label.startswith(('Support', 'Prime tower', 'Brim', 'Skirt')) for label in labels])
        assert not (nearby & temporary[points[:, 5].astype(int)]).any()
        return local[nearby & (points[:, 7] <= 2.401)]

    before = contacts(baseline, previous_frame)
    current = contacts(archive, frame)
    assert len(before) > 50 and len(current) > 50
    # The unchanged rod clip intentionally intersects the fitting envelope.
    nearest = np.concatenate([np.square(batch[:, None, :] - before).sum(axis=2).min(axis=1)
                              for batch in np.array_split(current, 1 + len(current) // 128)])
    unexpected = int((nearest > .29**2).sum())
    assert not unexpected, unexpected
    return dict(archive_sha256=digest(archive), radius_mm=4, earlier_snap_land_samples=len(before),
                current_snap_land_samples=len(current), contacts_outside_existing_path_region=unexpected)


def draw_map(archive, frame_file, design, position, out):
    generate(archive, frame_file, MODEL, LABELS, out)
    image = Image.open(out).convert('RGB')
    draw = ImageDraw.Draw(image)
    color = '#247851'
    for fin in design['fins']:
        x, y = np.asarray(fin['cut_at_xy']) + position[:2, 3]
        cx, cy = 32 + x * 4, 805 - y * 4
        draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=color, outline='white', width=2)
    draw.ellipse((789, 651, 801, 663), fill=color)
    draw.text((827, 642), 'Cut the six green tabs on the holder', fill='#15272d', font=font(19))
    draw.text((827, 668), 'Fold the base away from the hinge', fill='#15272d', font=font(19))
    image.save(out)


def check(plate, *, compact_pads=None):
    compact_pads = compact_pads or {}
    archive = plate / 'OP1-hinge.gcode.3mf'
    layout = plate / 'layout.3mf'
    frame_file = plate / 'layout.frame.json'
    frame = read(frame_file)
    sha = digest(archive)
    native = read(archive.with_suffix('.native.json'))
    assert native['archive_sha256'] == sha and native['return_code'] == 0
    assert len(native['plates']) == 1 and not native['plates'][0]['warning_message']
    assert 'got warnings:' not in (plate / 'native/slice.log').read_text()
    assert frame['layout_sha256'] == digest(layout)
    prior = R53 / 'exports/print-mechanisms'
    old_frames = read(prior / frame_file.name)['parts']
    assert set(frame['parts']) == set(old_frames) == set(LABELS)
    for part, entry in frame['parts'].items():
        assert digest(mesh_path(entry['source'], MODEL)) == entry['source_sha256']
        previous_entry = old_frames[part]
        assert entry['source_sha256'] == previous_entry['source_sha256']
        assert entry['assembly_to_machine'] == previous_entry['assembly_to_machine']
        if part != 'Key_Carrier':
            expected_panel = previous_entry['adhesion_panel'].copy()
            if part in compact_pads:
                size, _ = compact_pads[part]
                expected_panel['size'] = list(size)
            assert entry['adhesion_panel'] == expected_panel

    audit(archive, layout, plate / 'separation-and-machine.json', set(LABELS))
    adhesion = bases(archive)
    minimum = {part: area for part, (_, area) in compact_pads.items()}
    verify(adhesion, minimum_base_mm2=minimum)
    if compact_pads:
        baseline = read(HERE / 'exports/wide-bases.json')
        for name, row in adhesion['parts'].items():
            previous_area = baseline['parts'][name]['connected_base_mm2']
            if name in compact_pads:
                assert row['connected_base_mm2'] <= .45 * previous_area, (name, row, previous_area)
            else:
                assert abs(row['connected_base_mm2'] - previous_area) <= 10, (name, row, previous_area)
    write(plate / 'wide-bases.json', adhesion)
    for label, run in [('keys', lambda path: keys(archive, frame_file, ['Key_Carrier'], path)),
                       ('fit', lambda path: mating(archive, frame_file, path))]:
        path = plate / (label + '.json')
        run(path)
        for part, routes in read(prior / path.name)['parts'].items():
            current = read(path)['parts'][part]
            assert current.keys() == routes.keys()
            assert all(current[key]['nearby_samples'] > 25 for key, row in routes.items()
                       if row['nearby_samples'] > 25), label
    write(plate / 'contacts.json', switch_contacts(archive, frame_file))
    layers = plate / 'layers.json'
    write(layers, inspect(archive))
    check_paths(plate, sha)
    compare(layers, frame_file, plate / 'spans.json')

    carrier = frame['parts']['Key_Carrier']
    position = np.asarray(carrier['assembly_to_machine'])
    assert np.allclose(abs(position[:3, 1]), [0, 0, 1])
    old_pose = np.asarray(old_frames['Key_Carrier']['assembly_to_machine'])
    write(plate / 'rod.json', check_rod(archive, position, prior / archive.name, old_pose))
    body = load_solid(mesh_path(carrier['source'], MODEL))
    previous = R54 / 'exports'
    zones = {'hinge_bay': BAY}
    before = seam(previous / 'Key-holder.gcode.3mf', read(previous / frame_file.name), body, regions=zones)
    current = seam(archive, frame, body, regions=zones)
    write(plate / 'joint.json', dict(previous=before, current=current))
    assert current['vertical_joint_area_mm2'] >= .9 * before['vertical_joint_area_mm2'], (before, current)
    assert len(current['layers']) >= len(before['layers'])
    assert before['regional_joint_area_mm2']['hinge_bay'] > 2
    assert current['regional_joint_area_mm2']['hinge_bay'] < .25, current
    oriented = position[:3].copy()
    oriented[:2, 3] = 0
    design = report55(body.transform(oriented), carrier['adhesion_panel'])
    assert design['hinge_bay_open_to_panel_edge'] and design['nearest_base_to_hinge_mm'] >= 3
    assert design['base_volume_in_hinge_bay_mm3'] == 0 and design['fins_on_hinge'] == 0
    assert len(design['fins']) == 6 and design['panel_pieces'] == 1
    write(plate / 'fin-design.json', dict(archive_sha256=sha, **design))
    draw_map(archive, frame_file, design, position, plate / 'tray.png')
    print(f'Passed seven-piece native checks, holder seam {current["vertical_joint_area_mm2"]} mm², archive {sha}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plate', type=Path)
    check(parser.parse_args().plate)
