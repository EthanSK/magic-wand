#!/usr/bin/env python3
"""Reload the exact R21 archive once, comparing its recipe and all new beads.

Use explicit SD scratch. The sent R20 job, source R21 archive and Studio GUI are
never changed. This checks CLI reload/re-slice, not a new physical print.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import subprocess
import clip21 as h
import project21 as project
import check21

OUT = h.HERE / 'exports'
spec = importlib.util.spec_from_file_location('r21_archive_comparisons', h.h19.R16 / 'roundtrip16.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def run(scratch: Path) -> None:
    source = OUT / 'R21-A1-mini-PETG.gcode.3mf'
    source_hash = h.sha(source)
    audit = json.loads((OUT / 'slice-checks.json').read_text())
    assert audit['project_sha256'] == source_hash and audit['passed']
    work = scratch.resolve() / 'roundtrip'
    for directory in ('tmp', 'data', 'profile-home/Library/Preferences', 'out'):
        (work / directory).mkdir(parents=True, exist_ok=True)
    copied = work / 'input.gcode.3mf'
    copied.write_bytes(source.read_bytes())
    result_path = work / 'out/resliced.gcode.3mf'
    env = {**os.environ, 'TMPDIR': str(work / 'tmp'), 'CFFIXED_USER_HOME': str(work / 'profile-home')}
    command = [str(project.p19.BAMBU), '--datadir', str(work / 'data'), '--debug', '2', '--orient', '0',
               '--arrange', '0', '--slice', '0', '--export-3mf', result_path.name,
               '--outputdir', str(work / 'out'), str(copied)]
    with (work / 'reslice.log').open('w') as log:
        subprocess.run(command, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240, check=True)
    result = json.loads((work / 'out/result.json').read_text())
    assert result['return_code'] == 0 and not any(p.get('warning_message') for p in result['sliced_plates'])
    before, _, gcode_before = common.archive_settings(source)
    after, _, gcode_after = common.archive_settings(result_path)
    keys = set(project.p19.PROCESS_OVERRIDES) | set(project.p19.PRINTER_OVERRIDES) | {
        'printer_settings_id', 'print_settings_id', 'filament_settings_id', 'curr_bed_type',
        'nozzle_temperature', 'textured_plate_temp', 'machine_start_gcode', 'machine_end_gcode',
        'layer_change_gcode', 'time_lapse_gcode', 'change_filament_gcode', 'elefant_foot_compensation'}
    equal = {key: before.get(key) == after.get(key) for key in sorted(keys)}
    assert all(equal.values())
    check21.check(result_path, 'roundtrip-slice-checks.json')
    resliced = json.loads((OUT / 'roundtrip-slice-checks.json').read_text())
    assert h.sha(source) == source_hash
    report = {'generator_sha256': h.sha(Path(__file__)), 'input_project_sha256': source_hash,
              'resliced_project_sha256': h.sha(result_path), 'input_audit_sha256': h.sha(OUT / 'slice-checks.json'),
              'resliced_audit_sha256': h.sha(OUT / 'roundtrip-slice-checks.json'),
              'settings_identical': equal, 'actual_bead_audit_passed': resliced['passed'],
              'normalized_gcode_identical': common.normalized_gcode(gcode_before) == common.normalized_gcode(gcode_after),
              'gui_reopen_verified': False, 'physical_print_verified': False, 'passed': True}
    (OUT / 'roundtrip-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'settings_identical': all(equal.values())}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--scratch', required=True, type=Path)
    run(p.parse_args().scratch)
