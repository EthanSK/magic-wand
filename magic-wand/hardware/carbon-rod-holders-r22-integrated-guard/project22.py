#!/usr/bin/env python3
"""Build the R22 one-plate PETG project with the checked R20 slicing workflow."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import trimesh

import holder22 as holder
import project20 as studio


LABEL = 'R22-A1-mini-PETG'
PLATE_NAME = 'Magic Wand R22 holders and keepers - A1 mini PETG'
MODEL_SETTINGS = 'Metadata/model_settings.config'
OBJECT_WALL_GENERATORS = {'Key_Carrier': 'arachne'}
FILL_BOUNDS = [((24.5, 8.75, .4), (30.9, 13.95, 1.8)),
               ((24.5, 8.75, 16.2), (30.9, 13.95, 17.6))]
ORIGINS = {
    'Key_Carrier': (22, 136),
    'XIAO_Rod_Holder': (105, 128),
    'Battery_Holder': (25, 86),
    'Battery_End_Door': (75, 85),
    'Battery_End_Door_Easy_Trial': (120, 85),
    'XIAO_Near_Keeper': (85, 50),
    'Cable_Clip_12_Wire': (32, 48),
    'Battery_Spacer_0p4mm': (15, 12),
    'Battery_Spacer_0p6mm': (48, 12),
    'Battery_Spacer_0p8mm': (81, 12),
}


def object_wall_generators(model_settings):
    result = {}
    for obj in ET.fromstring(model_settings).findall('object'):
        options = {row.get('key'): row.get('value') for row in obj.findall('metadata')}
        if 'wall_generator' in options:
            result[options['name']] = options['wall_generator']
    return result


def configure_layout(path):
    with ZipFile(path) as archive:
        members = {item.filename: (item, archive.read(item)) for item in archive.infolist()}
    model_name = '3D/3dmodel.model'
    model = ET.fromstring(members[model_name][1])
    config = ET.fromstring(members[MODEL_SETTINGS][1])
    config.find("plate/metadata[@key='plater_name']").set('value', PLATE_NAME)
    objects = {obj.find("metadata[@key='name']").get('value'): obj for obj in config.findall('object')}
    for name, generator in OBJECT_WALL_GENERATORS.items():
        obj = objects[name]
        assert obj.find("metadata[@key='wall_generator']") is None
        # Variable-width beads fill the six narrow guard cores without thickening them.
        ET.SubElement(obj, 'metadata', key='wall_generator', value=generator)

    p19 = studio.p19
    resources = model.find(p19.tag('resources'))
    next_id = max(int(obj.get('id')) for obj in resources.findall(p19.tag('object'))) + 1
    for number, bounds in enumerate(FILL_BOUNDS):
        # Back two small internal shells over the rod rings. The modifier changes
        # infill only where it overlaps the part, so neither bore gets material added.
        box = trimesh.creation.box(bounds=bounds)
        p19.add_mesh_part(model, objects['Key_Carrier'], box, next_id + number, 'modifier_part',
                          f'SOLID BACKING {number + 1} - modifier, not printed',
                          [('sparse_infill_density', '100%')])

    for filename, tree in ((model_name, model), (MODEL_SETTINGS, config)):
        members[filename] = (members[filename][0], ET.tostring(tree, encoding='utf-8', xml_declaration=True))
    with ZipFile(path, 'w', ZIP_DEFLATED) as archive:
        for item, data in members.values():
            archive.writestr(item, data)


def build(scratch, do_slice):
    assert set(ORIGINS) == set(holder.PLATE), 'Every plate part needs an explicit position'
    recipe = {
        **holder.P['print']['local_recipe'],
        'Key_Carrier_bands_mm': holder.key_carrier_bands(),
        'Battery_Holder_bands_mm': holder.LOCAL['print']['local_recipe']['Battery_Holder_bands_mm'],
    }
    print_settings = {**holder.P['print'], 'local_recipe': recipe}
    profile = {'print': {**holder.LOCAL['print'], 'z_hop_mm': holder.LOCAL['print']['z_hop_mm']}}
    # Use the exact multi-object layout, official startup templates, and isolated CLI
    # slicing used for R20. Only this module's build changes the adapter settings.
    adapter = SimpleNamespace(
        PARTS=holder.PLATE, PLATE=holder.PLATE, ANCHORED=holder.ANCHORED,
        HERE=holder.HERE, R19=holder.R19, P={**holder.P, 'print': print_settings},
        LOCAL=profile, base=holder.base, sha=holder.sha,
    )
    studio.h = studio.p19.h = adapter
    studio.ORIGINS = studio.p19.ORIGINS = ORIGINS
    studio.PRINT = print_settings
    studio.LABEL = LABEL
    studio.rename_plate = configure_layout
    studio.build(scratch, do_slice)
    report_path = holder.HERE / 'exports' / (LABEL + '-print-checks.json')
    report = json.loads(report_path.read_text())
    report['project20_sha256'] = holder.sha(holder.R20 / 'project20.py')
    report['generator_sha256'] = holder.sha(Path(__file__))
    report['object_wall_generators'] = OBJECT_WALL_GENERATORS
    report['key_carrier_solid_fill_bounds_mm'] = FILL_BOUNDS
    report['adhesion_policy'] = (
        'The key, battery and XIAO holders and the cable clip have labelled tear-off pads. '
        'The flat doors, keeper and spacers print directly on the plate. No slicer brim or automatic support.'
    )
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    if do_slice:
        assert not report['warnings'] and not report['slice_info_warnings'], 'Inspect the slicer warnings'
        with ZipFile(holder.HERE / 'exports' / report['sliced_project_filename']) as archive:
            assert object_wall_generators(archive.read(MODEL_SETTINGS)) == OBJECT_WALL_GENERATORS


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--slice', action='store_true')
    args = parser.parse_args()
    build(args.scratch, args.slice)
