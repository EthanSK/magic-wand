#!/usr/bin/env python3
"""Build and slice the R20 Bambu A1 mini / Generic PETG project from the exact exported STLs.

One plate: key holder, battery holder, XIAO holder and finger guard, each with its labelled tear-off pads.
Reuses project19's profile resolver (inherits and include templates), layout writer, registration restore and
executable-command audit unchanged; only the plate contents, origins and slow bands are R20's.
No automatic support and no slicer brim. CLI slicing uses explicit private scratch.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from types import SimpleNamespace
import argparse, json, os, re, subprocess, zipfile
import holder20 as h
sys.path.insert(0, str(h.R19))
import project19 as p19  # noqa: E402

LABEL = 'R20-A1-mini-PETG'; PLATE_NAME = 'Magic Wand R20 finger guard and holders - A1 mini PETG'
ORIGINS = {'Key_Carrier': (20, 125), 'Finger_Guard': (95, 130), 'Battery_Holder': (25, 75), 'XIAO_Rod_Holder': (100, 75)}
PRINT = {**h.P['print'], 'local_recipe': {**h.P['print']['local_recipe'], **{k: v for k, v in h.LOCAL['print']['local_recipe'].items() if k.endswith('_bands_mm')}}}
# project19 reads its parts and recipe through its module-level `h`; point that at the R20 plate.
p19.h = SimpleNamespace(PLATE=h.PARTS, ANCHORED=h.ANCHORED, HERE=h.HERE, P={**h.P, 'print': PRINT}, LOCAL=h.LOCAL, base=h.base, sha=h.sha)
p19.ORIGINS = ORIGINS
# The A1 mini flags traditional timelapse on these thin parts. Smooth mode
# needs a generated wipe tower; keep it in the otherwise empty front region.
p19.PROCESS_OVERRIDES = {**p19.PROCESS_OVERRIDES, 'timelapse_type': '1',
                         'enable_prime_tower': '1', 'wipe_tower_x': ['120'],
                         'wipe_tower_y': ['20']}


def rename_plate(path):
    with zipfile.ZipFile(path) as z: files = {i.filename: (i, z.read(i)) for i in z.infolist()}
    key = 'Metadata/model_settings.config'; text = files[key][1].decode(); assert 'Magic Wand R19 lightweight - A1 mini PETG' in text
    files[key] = (files[key][0], text.replace('Magic Wand R19 lightweight - A1 mini PETG', PLATE_NAME).encode())
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for info, data in files.values(): z.writestr(info, data)


def build(scratch, do_slice):
    out = h.HERE / 'exports'; manifest = json.loads((out / 'manifest.json').read_text()); cfg = p19.settings()
    assert cfg['brim_type'] == 'no_brim' and cfg['enable_support'] == '0'
    layout_path = out / (LABEL + '-layout.3mf'); extents, bands = p19.layout(layout_path, manifest, cfg); rename_plate(layout_path)
    report = {'layout_sha256': h.sha(layout_path), 'generator_sha256': h.sha(Path(__file__)), 'project19_sha256': h.sha(h.R19 / 'project19.py'), 'builder_sha256': h.sha(p19.BUILDER / 'print_projects.py'), 'manifest_sha256': h.sha(out / 'manifest.json'), 'anchors_sha256': h.sha(out / 'anchors.json'),
              'parts': h.PARTS, 'plate_origins_mm': ORIGINS, 'plate_extents_mm': extents, 'printer': cfg['printer_settings_id'], 'process': cfg['print_settings_id'], 'filament': cfg['filament_settings_id'], 'nozzle_c': cfg.get('nozzle_temperature'), 'bed_c': cfg.get('textured_plate_temp'),
              'process_overrides': p19.PROCESS_OVERRIDES, 'printer_overrides': p19.PRINTER_OVERRIDES, 'slow_bands_mm': bands, 'local_recipe': PRINT['local_recipe'],
              'adhesion_policy': 'No slicer brim: it would run into the open rod rings. Every object has labelled 0.4 mm tear-off pads on 1.0 x 0.4 mm ties instead. No automatic support.', 'physical_print_verified': False}
    if do_slice:
        scratch = scratch.resolve(); scratch.mkdir(parents=True, exist_ok=True); (scratch / 'tmp').mkdir(exist_ok=True); target = LABEL + '.gcode.3mf'
        cmd = [str(p19.BAMBU), '--datadir', str(scratch / 'bambu-data'), '--debug', '2', '--orient', '0', '--arrange', '0', '--slice', '0', '--export-3mf', target, '--outputdir', str(scratch), str(layout_path)]
        profile_home = scratch / 'profile-home'; (profile_home / 'Library' / 'Preferences').mkdir(parents=True, exist_ok=True)
        # Isolate native preferences and Studio data without replacing the process HOME.
        env = {**os.environ, 'TMPDIR': str(scratch / 'tmp'), 'CFFIXED_USER_HOME': str(profile_home)}
        with (scratch / 'slice.log').open('w') as log:
            subprocess.run(cmd, cwd=scratch, stdout=log, stderr=subprocess.STDOUT, check=True, env=env, timeout=400)
        result = json.loads((scratch / 'result.json').read_text()); assert result['return_code'] == 0, result
        report['slice'] = {k: v for k, v in result.items() if k in ('return_code', 'error_string', 'sliced_plates')}; report['warnings'] = [p['warning_message'] for p in result['sliced_plates'] if p.get('warning_message')]
        (out / target).write_bytes((scratch / target).read_bytes())
        report['delivered_settings_registration'] = p19.restore_registration(out / target, cfg); report['sliced_project_filename'] = target; report['sliced_project_sha256'] = h.sha(out / target)
        report['executable_commands'] = p19.command_audit(out / target, cfg)      # actual startup, printing and shutdown commands, not profile labels
        report['slice_info_warnings'] = p19.slice_info_warnings(out / target)
        match = re.search(r'BambuStudio Version (\S+)', (scratch / 'slice.log').read_text()); report['bambu_studio_version'] = match.group(1) if match else None
    (out / (LABEL + '-print-checks.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(report.get('warnings', []), report.get('sliced_project_filename'), report.get('executable_commands'), {k: [[round(v, 1) for v in row] for row in e] for k, e in extents.items()}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--scratch', type=Path, required=True); p.add_argument('--slice', action='store_true'); a = p.parse_args(); build(a.scratch, a.slice)
