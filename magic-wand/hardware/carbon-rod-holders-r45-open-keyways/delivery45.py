"""Verify the selected native archive's machine recipe, deposition and identity."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import numpy as np
from holder45 import inherited
from plate45 import digest
import plate38


def inspect(archive):
    checker = inherited.common.load_checker().audit
    data, features, stats, config, offset, objects, _, _ = checker.read_project(archive)
    labels = np.asarray(features)[data[:, 5].astype(int)]
    assert not any(str(label).startswith('Support') for label in labels), 'Unexpected automatic support'
    with ZipFile(archive) as source:
        model = ET.fromstring(source.read('Metadata/model_settings.config'))
        gcode = source.read('Metadata/plate_1.gcode')
        slice_info = ET.fromstring(source.read('Metadata/slice_info.config'))
        archive_warnings = [
            {'tag': element.tag,
             'fields': {key: value for key, value in element.attrib.items()
                        if key in ('message', 'msg', 'code', 'level', 'key', 'value')},
             'text': (element.text or '').strip()}
            for element in slice_info.iter()
            if 'warn' in element.tag.lower()
            or 'warn' in element.get('key', '').lower()
        ]
        if 'Metadata/plate_1.gcode.md5' in source.namelist():
            expected = source.read('Metadata/plate_1.gcode.md5').decode().strip().split()[0]
            assert expected.lower() == hashlib.md5(gcode).hexdigest()
    recipes = {}
    for obj in model.findall('object'):
        fields = {m.get('key'): m.get('value') for m in obj.findall('metadata')}
        name = fields['name']
        assert fields.get('enable_support', config.get('enable_support')) == '0', name
        recipes[name] = {
            'settings': fields,
            # Native UUIDs identify Studio instances, not effective recipes.
            # Preserve ownership/type and every setting without publishing
            # opaque per-instance attributes in the public audit report.
            'parts': [{**{key: p.get(key) for key in ('id', 'subtype') if p.get(key) is not None},
                       'metadata': {m.get('key'): m.get('value') for m in p.findall('metadata')}}
                      for p in obj.findall('part')],
        }
    from owner45 import layout_owners
    assert set(objects) == layout_owners(archive.parent)
    assert config['timelapse_type'] == '1' and config['enable_prime_tower'] == '1'
    tower = labels == 'Prime tower'
    assert tower.sum() > 500
    positions = data[:, :3] + offset

    def bounds(mask):
        half = data[mask, 3, None] / 2
        return (positions[mask, :2] - half).min(0), (positions[mask, :2] + half).max(0)

    low, high = bounds(~tower)
    tl, th = bounds(tower)
    assert (np.minimum(low, tl) >= 0).all() and (np.maximum(high, th) <= 180).all()
    gap = float(np.linalg.norm(np.maximum(np.maximum(low-th, tl-high), 0.)))
    assert gap > .2
    startup = plate38.command_audit(archive, config)
    native_receipt = archive.with_suffix('.native.json')
    native_warnings = None
    if native_receipt.is_file():
        native = json.loads(native_receipt.read_text())
        assert native['archive_sha256'] == digest(archive), 'Native warning receipt belongs to a different archive'
        native_warnings = [plate.get('warning_message') for plate in native['plates']
                           if plate.get('warning_message')]
    report = {
        'archive_sha256': digest(archive), 'checker_sha256': digest(Path(__file__)),
        'gcode_sha256': hashlib.sha256(gcode).hexdigest(),
        'functional_parts': ['Key_Carrier'], 'disposable_parts': [n for n in ('External_cradle','Front_pull_shelf','Rear_pull_shelf','Release_tabs') if n in objects],
        'effective_object_recipes': recipes, 'startup': startup,
        'nozzle_diameter_mm': config.get('nozzle_diameter'),
        'layer_height_mm': config.get('layer_height'),
        'first_layer_height_mm': config.get('initial_layer_print_height'),
        'plate_type': config.get('curr_bed_type'),
        'actual_deposition_inside_180mm_bed': True,
        'actual_part_and_helper_bounds_mm': [low.tolist(), high.tolist()],
        'actual_tower_bounds_mm': [tl.tolist(), th.tolist()], 'tower_gap_mm': gap,
        'smooth_timelapse_selected': True, 'statistics': stats,
        'archive_slice_warnings': archive_warnings,
        'native_slice_warning_messages': native_warnings,
        'native_slice_receipt_sha256': digest(native_receipt) if native_receipt.is_file() else None,
        'gui_warning_inspection_verified': False,
        'physical_fit_strength_and_cleanup_verified': False,
    }
    target = archive.parent / 'delivery-checks.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print('Machine and delivery checks passed', digest(archive), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    inspect(parser.parse_args().archive)
