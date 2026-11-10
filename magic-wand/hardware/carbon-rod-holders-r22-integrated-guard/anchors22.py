#!/usr/bin/env python3
"""Build R22's tear-off pads against the final print-oriented meshes."""
import json
from pathlib import Path

import manifold3d as mf
import trimesh

import holder22 as holder
import anchors20 as previous


OUTPUT = holder.HERE / 'exports'


def build():
    previous.OUT = OUTPUT
    assert holder.LOCAL['anchors']['key_carrier_sites'] == previous.A['sites_assembly_x_print_y_outward']['Key_Carrier']
    records = {}
    for name in ('Key_Carrier', 'Battery_Holder'):
        solid, _, _, _, record = previous.anchor(name)
        main = holder.read(OUTPUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
        for tie in record['tie_sites']:
            if name == 'Key_Carrier':
                # The rounded rear edge can reach the start of the tie above the bed.
                # Snip across the exposed centre of the 1 mm gap instead.
                x, y = tie['site_print_xy']
                nx, ny = tie['outward']
                assert nx == 0 and abs(ny) == 1
                y0, y1 = sorted((y + ny * .45, y + ny * .95))
                cutter = holder.box(x - 1.5, x + 1.5, y0, y1, .45, 6.)
                volume = (main ^ cutter).volume()
                assert volume < .01, (name, 'blocked cut midway through the tie', tie, volume)
                tie['mid_gap_cutter_intrusion_mm3'] = round(volume, 5)
            else:
                assert tie['part_volume_in_cutter_corridor_mm3'] < .25, (name, 'blocked cutter access', tie)
        path = OUTPUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl')
        holder.mesh(solid).export(path)
        assert trimesh.load_mesh(path).is_watertight, name
        records[name] = {**record, 'stl_sha256': holder.sha(path)}

    name = 'XIAO_Rod_Holder'
    path = OUTPUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl')
    original = json.loads((holder.R20 / 'exports/anchors.json').read_text())['parts'][name]
    assert holder.sha(path) == original['stl_sha256']
    records[name] = original

    name = holder.C['name']
    pad_path = OUTPUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl')
    part_path = OUTPUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')
    pads = holder.read(pad_path)
    clip = holder.read(part_path)
    pieces = pads.decompose()
    assert len(pieces) == 2 and pads.status() == mf.Error.NoError
    overlap = [(piece ^ clip).volume() for piece in pieces]
    assert min(overlap) > .05, ('cable clip pad did not join the root', overlap)
    records[name] = {
        'stl_sha256': holder.sha(pad_path),
        'thickness_mm': holder.C['pad_thickness_mm'],
        'tie_section_each_mm2': holder.C['tie_width_mm'] * holder.C['pad_thickness_mm'],
        'tie_count': len(pieces),
        'overlap_at_root_mm3': [round(volume, 3) for volume in overlap],
    }
    report = {
        'generator_sha256': holder.sha(Path(__file__)),
        'previous_anchor_generator_sha256': holder.sha(holder.R20 / 'anchors20.py'),
        'parts': records,
        'physical_adhesion_or_release_verified': False,
    }
    (OUTPUT / 'anchors.json').write_text(json.dumps(report, indent=2) + '\n')
    print({name: record['tie_count'] for name, record in records.items()}, flush=True)


if __name__ == '__main__':
    build()
