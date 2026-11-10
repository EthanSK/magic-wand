#!/usr/bin/env python3
"""Reload the delivered R20 archive and audit its new offline slice.

The delivered input is read only. The re-sliced archive and images stay in
explicit scratch; only its hash-bound comparison receipt is retained here.
This is a CLI round trip, not a Studio GUI or physical-print check.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import holder20 as h
import project20
import slice20

spec = importlib.util.spec_from_file_location('r20_archive_comparisons', h.R16 / 'roundtrip16.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
OUT = h.HERE / 'exports'
p19 = project20.p19


def run(scratch: Path) -> None:
    source = OUT / (project20.LABEL + '.gcode.3mf')
    registered = json.loads((OUT / 'slice-clearances.json').read_text())
    assert h.sha(source) == registered['project_sha256'], 'Stale registered slice'
    work = scratch.resolve() / 'roundtrip'
    for directory in ('tmp', 'data', 'profile-home/Library/Preferences', 'out'):
        (work / directory).mkdir(parents=True, exist_ok=True)
    copied = work / 'delivered-input.gcode.3mf'
    copied.write_bytes(source.read_bytes())
    result_path = work / 'out/resliced.gcode.3mf'
    result_path.unlink(missing_ok=True)
    env = {**os.environ, 'TMPDIR': str(work / 'tmp'),
           'CFFIXED_USER_HOME': str(work / 'profile-home')}
    command = [str(p19.BAMBU), '--datadir', str(work / 'data'), '--debug', '2',
               '--orient', '0', '--arrange', '0', '--slice', '0', '--export-3mf',
               result_path.name, '--outputdir', str(work / 'out'), str(copied)]
    with (work / 'reslice.log').open('w') as log:
        subprocess.run(command, cwd=work, env=env, stdout=log,
                       stderr=subprocess.STDOUT, timeout=300, check=True)
    result = json.loads((work / 'out/result.json').read_text())
    assert result['return_code'] == 0, result.get('error_string')
    warnings = [p['warning_message'] for p in result.get('sliced_plates', [])
                if p.get('warning_message')]
    before, before_model, before_gcode = common.archive_settings(source)
    after, after_model, after_gcode = common.archive_settings(result_path)
    keys = set(p19.PROCESS_OVERRIDES) | set(p19.PRINTER_OVERRIDES) | {
        'printer_settings_id', 'print_settings_id', 'filament_settings_id',
        'curr_bed_type', 'nozzle_temperature', 'textured_plate_temp',
        'elefant_foot_compensation', 'fan_min_speed', 'fan_max_speed',
        'slow_down_layer_time', 'fan_cooling_layer_time', 'machine_start_gcode',
        'machine_end_gcode', 'layer_change_gcode', 'time_lapse_gcode',
        'change_filament_gcode'}
    settings_equal = {key: before.get(key) == after.get(key) for key in sorted(keys)}
    modifiers_before = common.modifier_settings(before_model)
    modifiers_after = common.modifier_settings(after_model)
    for objects in (modifiers_before, modifiers_after):
        for parts in objects.values():
            for values in parts.values():
                values.pop('matrix', None)  # Compare effective bounds below.
    placement_before = common.effective_modifier_placement(source)
    placement_after = common.effective_modifier_placement(result_path)
    placement_equal = {
        f'{name}: {part}': values['world_bounds_mm'] ==
        placement_after.get(name, {}).get(part, {}).get('world_bounds_mm')
        for name, parts in placement_before.items() for part, values in parts.items()}
    assert placement_equal, 'No slow modifiers found'
    # Reuse the actual-bead checker, including normal meshes, pad meshes, every
    # working route and tie, instead of trusting settings or matching previews.
    audit = slice20.inspect(result_path, out_dir=work / 'out', tag='-roundtrip')
    notes_before = p19.slice_info_warnings(source)
    notes_after = p19.slice_info_warnings(result_path)
    report = {
        'generator_sha256': h.sha(Path(__file__)),
        'input_project_sha256': h.sha(source),
        'registered_audit_sha256': h.sha(OUT / 'slice-clearances.json'),
        'resliced_project_sha256': h.sha(result_path),
        'resliced_audit_sha256': h.sha(work / 'out/slice-clearances-roundtrip.json'),
        'effective_settings_identical': settings_equal,
        'modifier_settings_identical': modifiers_before == modifiers_after,
        'modifier_effective_bounds_identical': placement_equal,
        'normalized_gcode_identical': common.normalized_gcode(before_gcode) == common.normalized_gcode(after_gcode),
        'resliced_actual_bead_audit_passed': audit['passed'],
        'slicer_warnings': warnings,
        'slice_info_warnings_delivered': notes_before,
        'slice_info_warnings_resliced': notes_after,
        'slice_info_warnings_unchanged': notes_before == notes_after,
        'gui_reopen_verified': False, 'physical_print_verified': False,
        'resliced_artifacts_in_private_scratch_only': True,
        'executable_commands': p19.command_audit(result_path, p19.settings()),
    }
    report['passed'] = bool(all(settings_equal.values()) and
                            report['modifier_settings_identical'] and
                            all(placement_equal.values()) and audit['passed'] and
                            not warnings and notes_before == notes_after)
    (OUT / 'roundtrip-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in
                      ('passed', 'normalized_gcode_identical', 'modifier_settings_identical')}), flush=True)
    assert report['passed'], 'See roundtrip-checks.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', required=True, type=Path)
    run(parser.parse_args().scratch)
