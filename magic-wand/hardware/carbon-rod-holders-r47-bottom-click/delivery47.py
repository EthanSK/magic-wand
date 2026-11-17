"""Bind the complete native plate to its machine recipe and completed audits."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
import holder47 as h
import audit42
from compose47 import FUNCTIONAL
from material47 import HELPERS
from plate45 import digest


def inspect(archive):
    directory = archive.parent
    sha = digest(archive)
    reports = {name: json.loads((directory / name).read_text()) for name in
               ('candidate-audit.json', 'helper-starts.json', 'roof-strokes.json',
                'other-audit/other-parts-audit.json', 'reopen-checks.json')}
    core = reports['candidate-audit.json']
    other = reports['other-audit/other-parts-audit.json']
    reopen = reports['reopen-checks.json']
    assert core['screen_passed'] and other['passed']
    for name, row in reports.items():
        assert row['selected_archive_sha256' if name == 'reopen-checks.json' else 'archive_sha256'] == sha
    assert all(not r['unrooted_actual_components'] for r in reports['helper-starts.json']['owners'].values())
    assert reopen['actual_modifier_placements_equivalent'] and reopen['object_process_settings_identical']
    engine = audit42.common.load_checker()
    data, features, statistics, config, offset, objects, _, _ = engine.audit.read_project(archive)
    assert set(objects) == FUNCTIONAL | HELPERS
    assert config['filament_type'] == ['PETG']
    assert config['nozzle_diameter'] == ['0.4']
    assert config['timelapse_type'] == '1' and config['enable_prime_tower'] == '1'
    labels = np.asarray(features)[data[:, 5].astype(int)]
    owners = audit42.native_support_owners(archive)
    support = np.char.startswith(labels, 'Support')
    assert support.any() and not (support & (data[:, 6] != owners[h.BRACKET])).any()
    assert (labels == 'Prime tower').sum() > 500
    startup = audit42.plate42.command_audit(archive, config)
    assert startup['passed'] and startup['project_sha256'] == sha
    assert other['complete_plate_layout']['passed']
    with ZipFile(archive) as z:
        gcode = z.read('Metadata/plate_1.gcode')
        expected = z.read('Metadata/plate_1.gcode.md5').decode().strip().split()[0]
        assert expected.lower() == hashlib.md5(gcode).hexdigest()
        settings = ET.fromstring(z.read('Metadata/model_settings.config'))
        info = ET.fromstring(z.read('Metadata/slice_info.config'))
    recipes = {}
    for obj in settings.findall('object'):
        values = {m.get('key'): m.get('value') for m in obj.findall('metadata')}
        recipes[values['name']] = {
            'settings': values,
            'parts': [{'id': p.get('id'), 'subtype': p.get('subtype'),
                       'metadata': {m.get('key'): m.get('value') for m in p.findall('metadata')}}
                      for p in obj.findall('part')]}
    warnings = [{'tag': e.tag, 'text': (e.text or '').strip(), 'attributes': dict(e.attrib)}
                for e in info.iter() if 'warn' in e.tag.lower() or 'warn' in e.get('key', '').lower()]
    native_path = archive.with_suffix('.native.json')
    native = json.loads(native_path.read_text())
    assert native['archive_sha256'] == sha
    result = {
        'archive_sha256': sha, 'gcode_sha256': hashlib.sha256(gcode).hexdigest(),
        'checker_sha256': digest(Path(__file__)), 'functional_parts': sorted(FUNCTIONAL),
        'disposable_parts': sorted(HELPERS), 'effective_object_recipes': recipes,
        'startup': startup, 'statistics': statistics,
        'actual_deposition_inside_180mm_bed': True,
        'complete_plate_layout': other['complete_plate_layout'],
        'smooth_timelapse_selected': True, 'actual_tower_present': True,
        'automatic_support_owners': [h.BRACKET],
        'archive_slice_warnings': warnings,
        'native_slice_warning_messages': [p['warning_message'] for p in native['plates'] if p.get('warning_message')],
        'native_slice_receipt_sha256': digest(native_path),
        'report_sha256': {name: digest(directory / name) for name in reports if name != 'reopen-checks.json'},
        'native_reopen': {name: reopen[name] for name in (
            'initial_archive_sha256', 'selected_archive_sha256', 'global_settings_identical',
            'object_process_settings_identical', 'actual_modifier_placements_equivalent')},
        'gui_warning_inspection_verified': False,
        'physical_fit_strength_and_cleanup_verified': False,
    }
    (directory / 'delivery-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Complete native machine and delivery checks passed', sha, flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('archive', type=Path)
    inspect(p.parse_args().archive.resolve())
