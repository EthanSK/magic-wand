#!/usr/bin/env python3
"""Reopen the delivered Studio archive and re-audit it if paths change."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from audit26 import inspect
import holder26 as d
from plate26 import LABEL
from project22 import studio
from roundtrip23 import object_recipe, roundtrip22


def run(scratch):
    source = d.OUT / f"{LABEL}.gcode.3mf"
    before = json.loads((d.OUT / "slice-clearances.json").read_text())
    assert before["passed"] and before["project_sha256"] == d.h.sha(source)
    for directory in ("tmp", "data", "profile-home/Library/Preferences", "out"):
        (scratch / directory).mkdir(parents=True, exist_ok=True)
    output = scratch / "out/resliced.gcode.3mf"
    env = {**os.environ, "TMPDIR": str(scratch / "tmp"),
           "CFFIXED_USER_HOME": str(scratch / "profile-home")}
    command = [str(studio.p19.BAMBU), "--datadir", str(scratch / "data"), "--debug", "2",
               "--orient", "0", "--arrange", "0", "--slice", "0", "--export-3mf", output.name,
               "--outputdir", str(output.parent), str(source)]
    with (scratch / "reslice.log").open("w") as log:
        subprocess.run(command, cwd=scratch, env=env, stdout=log, stderr=subprocess.STDOUT,
                       timeout=120, check=True)
    result = json.loads((output.parent / "result.json").read_text())
    assert result["return_code"] == 0 and all(not p.get("warning_message") for p in result["sliced_plates"])
    common = roundtrip22.common
    initial_settings, initial_objects, initial_gcode = common.archive_settings(source)
    new_settings, new_objects, new_gcode = common.archive_settings(output)
    settings = set(studio.p19.PROCESS_OVERRIDES) | set(studio.p19.PRINTER_OVERRIDES) | {
        "printer_settings_id", "print_settings_id", "filament_settings_id", "curr_bed_type",
        "nozzle_temperature", "textured_plate_temp", "machine_start_gcode", "machine_end_gcode",
        "time_lapse_gcode", "layer_change_gcode", "timelapse_type",
    }
    assert all(initial_settings.get(k) == new_settings.get(k) for k in settings)
    assert object_recipe(initial_objects) == object_recipe(new_objects)
    assert not studio.p19.slice_info_warnings(output)
    equal = common.normalized_gcode(initial_gcode) == common.normalized_gcode(new_gcode)
    if not equal:
        d.set_lower_seats()
        assert inspect(output, scratch / "slice-clearances.json")
    d.save_json("roundtrip-checks.json", {"passed": True, "project_sha256": d.h.sha(source),
                                         "reslice_sha256": d.h.sha(output),
                                         "same_normalized_paths": equal, "settings_checked": sorted(settings),
                                         "physical_print_verified": False})
    print(f"Reopen and slice passed. Normalized paths identical: {equal}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    run(parser.parse_args().scratch.resolve())
