#!/usr/bin/env python3
"""Reopen the selected R31 Bambu project in isolation and compare its toolpaths."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
from zipfile import ZipFile

STUDIO = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
SETTINGS = "Metadata/project_settings.config"
COMMAND_KEYS = (
    "printer_settings_id", "print_settings_id", "filament_settings_id", "curr_bed_type",
    "nozzle_temperature_initial_layer", "textured_plate_temp_initial_layer", "machine_start_gcode",
    "machine_end_gcode", "layer_change_gcode", "time_lapse_gcode", "timelapse_type",
)

def archive_state(file):
    with ZipFile(file) as archive:
        assert archive.testzip() is None
        settings = json.loads(archive.read(SETTINGS))
        gcode = archive.read("Metadata/plate_1.gcode").decode()
    commands = gcode.split("; EXECUTABLE_BLOCK_START", 1)[1]
    commands = [re.sub(r"\s+", " ", line.split(";", 1)[0].strip()) for line in commands.splitlines()]
    return {key: settings.get(key) for key in COMMAND_KEYS}, [line for line in commands if line]

def reopen(source, scratch):
    for folder in ("tmp", "data", "profile-home/Library/Preferences"):
        (scratch / folder).mkdir(parents=True, exist_ok=True)
    reopened = scratch / "reopened.gcode.3mf"
    env = {**os.environ, "TMPDIR": str(scratch / "tmp"), "CFFIXED_USER_HOME": str(scratch / "profile-home")}
    args = [str(STUDIO), "--datadir", str(scratch / "data"), "--debug", "2", "--orient", "0",
            "--arrange", "0", "--slice", "0", "--export-3mf", reopened.name,
            "--outputdir", str(scratch), str(source)]
    with (scratch / "slice.log").open("w") as log:
        subprocess.run(args, cwd=scratch, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=150, check=True)
    result = json.loads((scratch / "result.json").read_text())
    assert result["return_code"] == 0
    first, original = archive_state(source)
    second, reopened_gcode = archive_state(reopened)
    assert first == second
    check = {
        "settings_match": True,
        "executable_gcode_matches": original == reopened_gcode,
        "warnings": [plate["warning_message"] for plate in result["sliced_plates"] if plate.get("warning_message")],
        "objects": [obj["name"] for plate in result["sliced_plates"] for obj in plate["objects"]],
    }
    (scratch / "roundtrip.json").write_text(json.dumps(check, indent=2) + "\n")
    print(check, flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("scratch", type=Path)
    args = parser.parse_args()
    reopen(args.source.resolve(), args.scratch.resolve())
