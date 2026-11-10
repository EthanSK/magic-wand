#!/usr/bin/env python3
"""Slice only the R21 cable clip, using the checked R19 A1 mini template resolver.

This offline CLI build uses isolated data/preferences and never sends a printer
job. Keep the active R20 Studio session and all earlier model files unchanged.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
import clip21 as h

sys.dont_write_bytecode = True
sys.path.insert(0, str(h.R19))
import project19 as p19  # noqa: E402

LABEL = 'R21-A1-mini-PETG'
TITLE = 'Magic Wand R21 split cable clip - A1 mini PETG'
p19.h = SimpleNamespace(PLATE=[h.NAME], ANCHORED=[h.NAME], HERE=h.HERE,
                        P={'print': {**h.h19.P['print'], 'local_recipe': {}}},
                        LOCAL={'print': {'z_hop_mm': .6}}, base=h.h19.base, sha=h.sha)
p19.ORIGINS = {h.NAME: (70, 90)}
p19.PROCESS_OVERRIDES = {**p19.PROCESS_OVERRIDES, 'timelapse_type': '1',
                         'enable_prime_tower': '1', 'wipe_tower_x': ['120'], 'wipe_tower_y': ['20']}


def check_commands(config: dict, text: str, expected: dict) -> dict:
    """R19's command contract at the first extrusion feature, for one object.

    Studio omits cancellation/object-label comments for a single object. Use
    the earlier first non-custom feature (the tower) as the temperature gate,
    rather than adding an unwanted second part or changing the delivered code.
    Official command templates still come from the existing profile resolver.
    """
    machine = p19.resolve('machine', expected['printer_settings_id'])
    keys = ('machine_start_gcode', 'machine_end_gcode', 'layer_change_gcode', 'time_lapse_gcode', 'change_filament_gcode')
    assert all(config.get(key) == machine[key] for key in keys)
    executable = text.split('; EXECUTABLE_BLOCK_START', 1)[1]
    match = re.search(r'^; FEATURE: (?!Custom\b)\S', executable, re.M)
    assert match is not None
    before, body = executable[:match.start()], executable[match.start():]
    assert 'machine: A1 mini' in before
    assert not re.search(r'[{}\[\]]', '\n'.join(line.split(';', 1)[0] for line in executable.splitlines()))
    def targets(lines: str, codes: str) -> list[float]:
        return [float(m.group(1)) for line in lines.splitlines()
                if (m := re.match(r'^(?:' + codes + r')\s+[^;]*?\bS(-?\d+(?:\.\d+)?)\b', line.strip()))]
    rows = []
    flags = ams = 0
    for raw in before.splitlines():
        line = raw.split(';', 1)[0].strip()
        if re.match(r'^M622\s', line): flags += 1
        elif re.match(r'^M623\b', line): flags -= 1
        elif re.match(r'^M620\s+S', line): ams += 1
        elif re.match(r'^M621\s+S', line): ams -= 1
        elif not flags and not ams: rows.append(line)
        assert flags >= 0 and ams >= 0
    assert flags == ams == 0
    ungated = '\n'.join(rows)
    nozzle = float(expected['nozzle_temperature_initial_layer'][0])
    bed = float(expected['textured_plate_temp_initial_layer'][0])
    assert targets(before, 'M104|M109')[-1:] == [nozzle]
    assert targets(ungated, 'M109')[-1:] == [nozzle]
    after_wait = re.split(r'^M109\s', ungated, flags=re.M)[-1].split('\n', 1)[-1]
    assert all(v == nozzle for v in targets(after_wait, 'M104|M109'))
    assert targets(before, 'M140|M190')[-1:] == [bed]
    assert targets(ungated, 'M190')[-1:] == [bed]
    printing, ending = body.rsplit('; filament end gcode', 1)
    assert all(v == nozzle for v in targets(printing, 'M104|M109'))
    assert all(v == bed for v in targets(printing, 'M140|M190'))
    assert re.findall(r'^M8[23]\b', before, re.M)[-1:] == ['M83']
    assert not re.search(r'^M82\b', printing, re.M)
    assert targets(ending, 'M104|M109')[-1:] == [0]
    assert targets(ending, 'M140|M190')[-1:] == [0]
    return {'passed': True, 'first_extrusion_nozzle_c': nozzle, 'first_extrusion_bed_c': bed,
            'official_machine_templates_match': list(keys), 'boundary': 'first non-custom extrusion feature',
            'unconditional_temperature_waits': True, 'ending_heater_targets_c': [0, 0]}


def command_audit(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as z:
        config = json.loads(z.read('Metadata/project_settings.config'))
        text = z.read('Metadata/plate_1.gcode').decode()
    return {**check_commands(config, text, p19.settings()), 'project_sha256': h.sha(archive)}


def build(scratch: Path) -> None:
    out = h.HERE / 'exports'
    manifest = json.loads((out / 'manifest.json').read_text())
    cfg = p19.settings()
    layout = out / (LABEL + '-layout.3mf')
    extents, bands = p19.layout(layout, manifest, cfg)
    with zipfile.ZipFile(layout) as z:
        files = {i.filename: (i, z.read(i)) for i in z.infolist()}
    key = 'Metadata/model_settings.config'
    files[key] = (files[key][0], files[key][1].replace(b'Magic Wand R19 lightweight - A1 mini PETG', TITLE.encode()))
    with zipfile.ZipFile(layout, 'w', zipfile.ZIP_DEFLATED) as z:
        for info, data in files.values():
            z.writestr(info, data)
    scratch = scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / 'tmp').mkdir(exist_ok=True)
    home = scratch / 'profile-home'
    (home / 'Library/Preferences').mkdir(parents=True, exist_ok=True)
    target = LABEL + '.gcode.3mf'
    command = [str(p19.BAMBU), '--datadir', str(scratch / 'bambu-data'), '--debug', '2',
               '--orient', '0', '--arrange', '0', '--slice', '0', '--export-3mf', target,
               '--outputdir', str(scratch), str(layout)]
    # Avoid a second GUI instance: this is an isolated, finite CLI process.
    env = {**os.environ, 'TMPDIR': str(scratch / 'tmp'), 'CFFIXED_USER_HOME': str(home)}
    with (scratch / 'slice.log').open('w') as log:
        subprocess.run(command, cwd=scratch, stdout=log, stderr=subprocess.STDOUT,
                       env=env, timeout=240, check=True)
    result = json.loads((scratch / 'result.json').read_text())
    assert result['return_code'] == 0
    delivery = out / target
    delivery.write_bytes((scratch / target).read_bytes())
    registration = p19.restore_registration(delivery, cfg)
    warnings = [row['warning_message'] for row in result['sliced_plates'] if row.get('warning_message')]
    warnings += p19.slice_info_warnings(delivery)
    assert not warnings, warnings
    report = {'project_sha256': h.sha(delivery), 'layout_sha256': h.sha(layout),
              'manifest_sha256': h.sha(out / 'manifest.json'), 'generator_sha256': h.sha(Path(__file__)),
              'profile_resolver_sha256': h.sha(h.R19 / 'project19.py'),
              'parts': [h.NAME], 'plate_extents_mm': extents, 'slow_bands_mm': bands,
              'registration': registration, 'warnings': warnings,
              'actual_commands': command_audit(delivery),
              'physical_print_verified': False}
    (out / 'print-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', type=Path, required=True)
    build(parser.parse_args().scratch)
