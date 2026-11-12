"""Prepare unchanged R34 parts with slightly larger removable bracket pads."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r32-complete-assembly'))
import plate32 as plate

BASE_STAGE = plate.stage_parts
BASE_CONFIGURE = plate.configure_layout
PAD_RADIUS = 2.9
PAD_CENTRE_OFFSET = 3.9


def stage(selected, exports, old, anchors20, mf):
    manifest, anchors = BASE_STAGE(selected, exports, old, anchors20, mf)
    name = plate.BRACKET
    original_mesh = old.read(exports / f'{name}{plate.SOURCE_SUFFIX}')
    original_pads = old.read(exports / f'{name}{plate.PAD_SUFFIX}')
    first_layer = original_mesh.slice(.1)
    contact = first_layer ^ mf.CrossSection.square((3., 50.)).translate((0., -10.))
    bounds = contact.bounds()
    y = (bounds[1] + bounds[3]) / 2

    # Keep the original small ear and thin tie intact. The added hull grows only
    # away from the body, so all removal force still passes through that same tie.
    original_ear = mf.CrossSection.circle(2.4, 48).translate((-3.4, y))
    outer_ear = mf.CrossSection.circle(PAD_RADIUS, 64).translate((-PAD_CENTRE_OFFSET, y))
    extended_left = (original_ear + outer_ear).hull()
    extended_right = extended_left.mirror((1., 0.)).translate((original_mesh.bounding_box()[3], 0.))
    added_pads = mf.Manifold.extrude(extended_left + extended_right, .4)
    larger_pads = original_pads + added_pads
    assert (added_pads ^ original_mesh).volume() < .0001
    assert abs((larger_pads ^ original_mesh).volume() - (original_pads ^ original_mesh).volume()) < .0001

    pad_file = exports / f'{name}{plate.PAD_SUFFIX}'
    old.mesh(larger_pads).export(pad_file)
    anchors[name] = {
        **anchors[name], 'stl_sha256': plate.digest(pad_file),
        'original_tie_overlap_mm3': (original_pads ^ original_mesh).volume(),
        'new_tie_overlap_mm3': (larger_pads ^ original_mesh).volume(),
        'original_pad_area_mm2': original_pads.slice(.1).area(),
        'new_pad_area_mm2': larger_pads.slice(.1).area(),
        'tie_geometry_unchanged': True,
    }
    (exports / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (exports / 'anchors.json').write_text(json.dumps({'parts': anchors}, indent=2) + '\n')
    return manifest, anchors


def configure(path, name):
    BASE_CONFIGURE(path, 'Magic Wand R34 pad-area retry')


def write_print_only(archive, target):
    """Keep checked G-code while removing editable-model references for Studio."""
    with ZipFile(archive) as source:
        gcode = source.read('Metadata/plate_1.gcode')
        model = source.read('3D/3dmodel.model').decode()
        # Preserve the model root's original namespaces and Bambu metadata.
        for tag in ('resources', 'build'):
            model = re.sub(fr'<{tag}\b[^>]*>.*?</{tag}>', f'<{tag}/>', model, flags=re.S)
        settings = ET.fromstring(source.read('Metadata/model_settings.config'))
        for child in list(settings):
            if child.tag in ('object', 'assemble'):
                settings.remove(child)
        for instance in settings.findall('plate/model_instance'):
            settings.find('plate').remove(instance)
        with ZipFile(target, 'w', ZIP_DEFLATED) as output:
            for entry in source.infolist():
                if entry.filename.startswith(('3D/Objects/', '3D/_rels/')):
                    continue
                content = source.read(entry.filename)
                if entry.filename == '3D/3dmodel.model':
                    content = model.encode()
                elif entry.filename == 'Metadata/model_settings.config':
                    content = ET.tostring(settings, encoding='utf-8', xml_declaration=True)
                output.writestr(entry, content)
    with ZipFile(target) as output:
        assert output.testzip() is None
        assert output.read('Metadata/plate_1.gcode') == gcode
    return {'file': target.name, 'sha256': plate.digest(target),
            'gcode_sha256': sha256(gcode).hexdigest(), 'gcode_identical_to_source_archive': True,
            'empty_mesh_resources_and_build': True, 'dangling_model_references_removed': True}


def build(scratch):
    plate.stage_parts = stage
    plate.configure_layout = configure
    scratch.mkdir(parents=True, exist_ok=True)
    plate.build(HERE, scratch, 'Flashforge HS PETG Metallic', True, True)
    report_file = scratch / 'print-checks.json'
    report = plate.read_json(report_file)
    print_only = write_print_only(scratch / 'R34-Complete-A1-mini-PETG.gcode.3mf',
                                 scratch / 'R34-Pad-Retry-print-only.3mf')
    report.update(
        retry_generator_sha256=plate.digest(Path(__file__)),
        print_only=print_only,
        change='Same assembly geometry, orientation, layout and thin pad ties. Bracket pad radius increased from 2.4 to 2.9 mm, keeping its inner edge fixed.',
    )
    report_file.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scratch', type=Path)
    args = parser.parse_args()
    build(args.scratch.resolve())
