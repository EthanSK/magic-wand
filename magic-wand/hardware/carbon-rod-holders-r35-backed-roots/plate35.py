"""Slice the R35 assembly with the established A1 mini PETG profile.

Run plate35.py with an output directory after running assembly35.py.
"""

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import trimesh

import holder35 as design
import plate32 as plate

HERE = Path(__file__).resolve().parent
PAD_TEST = design.R34 / 'exports' / 'perforated-pad-test'
PREVIOUS_PLATE = PAD_TEST / 'R34-Perforated-Pad-Test-editable.3mf'
BASE_STAGE = plate.stage_parts
BASE_CONFIGURE = plate.configure_layout
LAYER_RANGES = 'Metadata/layer_config_ranges.xml'
MODEL = '3D/3dmodel.model'
# The rear edge of the OP1 connector cut ends abruptly at print Z 15.65.
# Keep support local to this ledge so the bought plug can keep its full opening.
SUPPORT_ENFORCER_BOUNDS = ((33.2, 10.3, 15.45), (42.0, 14.3, 15.93))


def object_names(settings):
    return {element.get('id'): element.find("metadata[@key='name']").get('value')
            for element in settings.findall('object')}


def original_pad_origins():
    with ZipFile(PREVIOUS_PLATE) as archive:
        model = ElementTree.fromstring(archive.read('3D/3dmodel.model'))
        settings = ElementTree.fromstring(archive.read(plate.MODEL_SETTINGS))
    names = object_names(settings)
    origins = {}
    for item in model.findall('./{*}build/{*}item'):
        name = names[item.get('objectid')]
        if name in (plate.KEY, plate.BRACKET):
            transform = item.get('transform').split()
            origins[name] = np.asarray(transform[-3:], dtype=float)
    return origins


def stage_parts(selected, exports, old, anchors20, mf):
    manifest, anchors = BASE_STAGE(selected, exports, old, anchors20, mf)
    # Reuse the perforated pads already checked on the prior slice. The
    # reinforcements are between these pads, away from the tear-off ties.
    from slice19 import anchor_in_project

    origins = original_pad_origins()
    for name, geometry in plate.read_json(PAD_TEST / 'pad-geometry.json').items():
        origin = origins[name]
        pad, _ = anchor_in_project(PREVIOUS_PLATE, name, origin)
        model = old.read(exports / f'{name}{plate.SOURCE_SUFFIX}')
        tie_overlap = (pad ^ model).volume()
        assert abs(tie_overlap - geometry['tie_overlap_mm3']) < .01, name
        hole_centres = np.asarray(geometry['plate_hole_centres_mm']) - origin[:2]
        anchors[name] = plate.write_pads(exports, name, pad, old, {
            'tie_overlap_mm3': round(tie_overlap, 5),
            'hole_centres_print_xy_mm': hole_centres.tolist(),
            'hole_diameter_mm': geometry['hole_diameter_mm'],
            'pad_thickness_mm': geometry['pad_thickness_mm'],
        })
    (exports / 'anchors.json').write_text(json.dumps({'parts': anchors}, indent=2) + '\n')
    return manifest, anchors


def configure_layout(path, plate_name):
    import project22

    BASE_CONFIGURE(path, plate_name)
    with ZipFile(PREVIOUS_PLATE) as archive:
        old_names = object_names(ElementTree.fromstring(archive.read(plate.MODEL_SETTINGS)))
        old_model = ElementTree.fromstring(archive.read(MODEL))
        ranges = ElementTree.fromstring(archive.read(LAYER_RANGES))
    with ZipFile(path) as archive:
        entries = {item.filename: archive.read(item) for item in archive.infolist()}
    settings = ElementTree.fromstring(entries[plate.MODEL_SETTINGS])
    new_names = object_names(settings)
    new_model = ElementTree.fromstring(entries[MODEL])
    old_order = [old_names[item.get('objectid')] for item in old_model.findall('./{*}build/{*}item')]
    new_order = [new_names[item.get('objectid')] for item in new_model.findall('./{*}build/{*}item')]
    # Both tops retain their original geometry. Keep the validated wall
    # count and wall width at those heights. Bambu's range XML uses the
    # one-based model order, unlike the object IDs in model_settings.
    for part in ranges.findall('object'):
        name = old_order[int(part.get('id')) - 1]
        part.set('id', str(new_order.index(name) + 1))
    entries[LAYER_RANGES] = ElementTree.tostring(ranges, encoding='utf-8', xml_declaration=True)
    add_connector_support(new_model, settings, project22.studio.p19)
    entries[MODEL] = ElementTree.tostring(new_model, encoding='utf-8', xml_declaration=True)
    entries[plate.MODEL_SETTINGS] = ElementTree.tostring(settings, encoding='utf-8', xml_declaration=True)
    with ZipFile(path, 'w', ZIP_DEFLATED) as archive:
        for filename, content in entries.items():
            archive.writestr(filename, content)


def add_connector_support(model, settings, studio):
    carrier = next(part for part in settings.findall('object')
                   if part.find("metadata[@key='name']").get('value') == plate.KEY)
    overrides = {
        'enable_support': '1',
        'support_type': 'normal(manual)',
        'support_on_build_plate_only': '0',
        'support_top_z_distance': '0.2',
        'support_bottom_z_distance': '0.2',
        'support_object_xy_distance': '0.35',
        'support_interface_top_layers': '2',
        'support_interface_spacing': '0.20',
    }
    for key, value in overrides.items():
        field = carrier.find(f"metadata[@key='{key}']")
        if field is None:
            field = ElementTree.SubElement(carrier, 'metadata', key=key)
        field.set('value', value)
    resources = model.find(studio.tag('resources'))
    identifier = max(int(part.get('id')) for part in resources.findall(studio.tag('object'))) + 1
    helper = trimesh.creation.box(bounds=SUPPORT_ENFORCER_BOUNDS)
    studio.add_mesh_part(model, carrier, helper, identifier, 'support_enforcer',
                         'REMOVE AFTER PRINT - OP1 connector ledge support')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plate.stage_parts = stage_parts
    plate.configure_layout = configure_layout
    plate.build(HERE, args.output.resolve(), plate.FLASHFORGE_PROFILE, True, True)
