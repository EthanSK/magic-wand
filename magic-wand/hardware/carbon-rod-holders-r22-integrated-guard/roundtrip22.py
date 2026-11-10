#!/usr/bin/env python3
"""Open and re-slice the checked archive with isolated Bambu Studio preferences."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import holder22 as holder
import project22
import slice22


SPEC = importlib.util.spec_from_file_location('roundtrip_comparisons', holder.R16 / 'roundtrip16.py')
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
OUT = holder.HERE / 'exports'


def run(scratch):
    source = slice22.PROJECT
    audit_path = OUT / 'slice-clearances.json'
    audit = json.loads(audit_path.read_text())
    assert audit['passed'] and holder.sha(source) == audit['project_sha256'], 'The delivered slice audit is stale'
    scratch = scratch.resolve()
    for directory in ('tmp', 'data', 'profile-home/Library/Preferences', 'out'):
        (scratch / directory).mkdir(parents=True, exist_ok=True)
    copied = scratch / 'delivered-input.gcode.3mf'
    shutil.copyfile(source, copied)
    output = scratch / 'out/resliced.gcode.3mf'
    output.unlink(missing_ok=True)
    studio = project22.studio.p19
    environment = {**os.environ, 'TMPDIR': str(scratch / 'tmp'),
                   'CFFIXED_USER_HOME': str(scratch / 'profile-home')}
    command = [str(studio.BAMBU), '--datadir', str(scratch / 'data'), '--debug', '2',
               '--orient', '0', '--arrange', '0', '--slice', '0', '--export-3mf', output.name,
               '--outputdir', str(output.parent), str(copied)]
    with (scratch / 'reslice.log').open('w') as log:
        subprocess.run(command, cwd=scratch, env=environment, stdout=log, stderr=subprocess.STDOUT,
                       timeout=90, check=True)
    result = json.loads((output.parent / 'result.json').read_text())
    assert result['return_code'] == 0 and all(not row.get('warning_message') for row in result['sliced_plates'])
    assert not studio.slice_info_warnings(output)
    before, before_model, before_gcode = common.archive_settings(source)
    after, after_model, after_gcode = common.archive_settings(output)
    keys = set(studio.PROCESS_OVERRIDES) | set(studio.PRINTER_OVERRIDES) | {
        'printer_settings_id', 'print_settings_id', 'filament_settings_id', 'curr_bed_type',
        'nozzle_temperature', 'textured_plate_temp', 'elefant_foot_compensation',
        'fan_min_speed', 'fan_max_speed', 'slow_down_layer_time', 'fan_cooling_layer_time',
        'machine_start_gcode', 'machine_end_gcode', 'layer_change_gcode',
        'time_lapse_gcode', 'change_filament_gcode',
    }
    changed_settings = sorted(key for key in keys if before.get(key) != after.get(key))
    assert not changed_settings, changed_settings
    assert (project22.object_wall_generators(before_model) == project22.OBJECT_WALL_GENERATORS
            == project22.object_wall_generators(after_model)), 'Object wall generators changed'
    before_modifiers = common.modifier_settings(before_model)
    after_modifiers = common.modifier_settings(after_model)
    for group in (before_modifiers, after_modifiers):
        for objects in group.values():
            for values in objects.values():
                values.pop('matrix', None)
    assert before_modifiers == after_modifiers
    def world_bounds(archive):
        placement = common.effective_modifier_placement(archive)
        # Studio can rewrite internal component matrices while preserving the
        # modifier's effective geometry and position on the plate.
        return {(part, label): row['world_bounds_mm'] for part, modifiers in placement.items()
                for label, row in modifiers.items()}

    before_placement = world_bounds(source)
    after_placement = world_bounds(output)
    assert before_placement and before_placement == after_placement, 'Slow zones moved'
    equal_paths = common.normalized_gcode(before_gcode) == common.normalized_gcode(after_gcode)
    if not equal_paths:
        audit_path = output.parent / 'resliced-clearances.json'
        slice22.inspect(output, audit_path)
    report = {
        'generator_sha256': holder.sha(Path(__file__)),
        'input_project_sha256': holder.sha(source), 'resliced_project_sha256': holder.sha(output),
        'path_audit_sha256': holder.sha(audit_path), 'effective_settings_identical': True,
        'object_wall_generators': project22.OBJECT_WALL_GENERATORS,
        'modifier_settings_and_positions_identical': True, 'normalized_toolpaths_identical': equal_paths,
        'slicer_warnings': [], 'passed': True, 'gui_reopen_verified': False,
        'physical_print_verified': False,
    }
    (OUT / 'roundtrip-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    run(parser.parse_args().scratch)
