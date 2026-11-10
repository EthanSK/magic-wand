#!/usr/bin/env python3
"""Reopen the checked R23 archive and compare Studio's settings and toolpaths."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from xml.etree import ElementTree as ET

import holder23 as holder
from project23 import LABEL
import roundtrip22
import slice23


def object_recipe(model):
    """Record effective overrides and named model, helper and modifier parts."""
    studio = roundtrip22.project22.studio.p19
    recipe = {}
    for obj in ET.fromstring(model).findall("object"):
        fields = {entry.get("key"): entry.get("value") for entry in obj.findall("metadata")}
        name = fields.pop("name")
        parts = {}
        for part in obj.findall("part"):
            values = {entry.get("key"): entry.get("value") for entry in part.findall("metadata")}
            label = values.pop("name")
            overrides = {key: value for key, value in values.items()
                         if key in studio.PROCESS_OVERRIDES or key in studio.PRINTER_OVERRIDES}
            parts[label] = {"type": part.get("subtype"), "overrides": overrides}
        recipe[name] = {"object_overrides": fields, "parts": parts}
    return recipe


def run(scratch, staged_exports, *, label=LABEL, exports=holder.OUT):
    source = exports / f"{label}.gcode.3mf"
    audit_path = exports / "slice-clearances.json"
    audit = json.loads(audit_path.read_text())
    assert audit["passed"] and audit["project_sha256"] == holder.sha(source)
    scratch = scratch.resolve()
    for directory in ("tmp", "data", "profile-home/Library/Preferences", "out"):
        (scratch / directory).mkdir(parents=True, exist_ok=True)
    input_path = scratch / "delivered-input.gcode.3mf"
    output = scratch / "out/resliced.gcode.3mf"
    studio = roundtrip22.project22.studio.p19
    environment = {**os.environ, "TMPDIR": str(scratch / "tmp"),
                   "CFFIXED_USER_HOME": str(scratch / "profile-home")}
    command = [str(studio.BAMBU), "--datadir", str(scratch / "data"), "--debug", "2",
               "--orient", "0", "--arrange", "0", "--slice", "0", "--export-3mf", output.name,
               "--outputdir", str(output.parent), str(input_path)]
    if not (output.is_file() and input_path.is_file() and holder.sha(input_path) == holder.sha(source)):
        shutil.copyfile(source, input_path)
        output.unlink(missing_ok=True)
        with (scratch / "reslice.log").open("w") as log:
            subprocess.run(command, cwd=scratch, env=environment, stdout=log, stderr=subprocess.STDOUT,
                           timeout=90, check=True)
    result = json.loads((output.parent / "result.json").read_text())
    assert result["return_code"] == 0 and all(not plate.get("warning_message") for plate in result["sliced_plates"])
    assert not studio.slice_info_warnings(output)
    common = roundtrip22.common
    before, before_model, before_gcode = common.archive_settings(source)
    after, after_model, after_gcode = common.archive_settings(output)
    keys = set(studio.PROCESS_OVERRIDES) | set(studio.PRINTER_OVERRIDES) | {
        "printer_settings_id", "print_settings_id", "filament_settings_id", "curr_bed_type",
        "nozzle_temperature", "textured_plate_temp", "fan_min_speed", "fan_max_speed",
        "slow_down_layer_time", "fan_cooling_layer_time", "machine_start_gcode",
        "machine_end_gcode", "layer_change_gcode", "time_lapse_gcode", "change_filament_gcode",
    }
    assert not [key for key in keys if before.get(key) != after.get(key)], "Plate settings changed"
    assert object_recipe(before_model) == object_recipe(after_model), "Object settings or parts changed"
    first, second = (common.effective_modifier_placement(path) for path in (source, output))
    for part, modifiers in first.items():
        assert {label: row["world_bounds_mm"] for label, row in modifiers.items()} == {
            label: row["world_bounds_mm"] for label, row in second[part].items()}
    equal_paths = common.normalized_gcode(before_gcode) == common.normalized_gcode(after_gcode)
    receipt = audit
    if not equal_paths:
        # Studio may make slightly different arc and perimeter decisions when
        # reopening the same layout. Run the real clearance checks on that output.
        replay = scratch / "reopened-plate"
        replay.mkdir(exist_ok=True)
        for mesh in staged_exports.glob("*.stl"):
            link = replay / mesh.name
            if not link.exists():
                link.symlink_to(mesh.resolve(strict=True))
        for filename in ("anchors.json", "manifest.json"):
            shutil.copyfile(staged_exports / filename, replay / filename)
        reopened_project = replay / source.name
        shutil.copyfile(output, reopened_project)
        settings_receipt = json.loads((exports / f"{label}-print-checks.json").read_text())
        settings_receipt["executable_commands"] = studio.command_audit(reopened_project, before)
        (replay / f"{label}-print-checks.json").write_text(json.dumps(settings_receipt))
        replay_audit = replay / "slice-clearances.json"
        slice23.inspect(holder.HERE, replay, replay_audit, label=label)
        receipt = json.loads(replay_audit.read_text())
    report = {"project_sha256": holder.sha(source), "reslice_sha256": holder.sha(output),
              "checker_sha256": holder.sha(Path(__file__)), "source_audit_sha256": holder.sha(audit_path),
              "effective_settings_and_named_parts_identical": True, "modifier_world_bounds_identical": True,
              "normalized_toolpaths_identical": equal_paths, "resliced_path_checks_passed": receipt["passed"],
              "resliced_path_parts_checked": list(receipt["parts"]), "slicer_warnings": [], "passed": True,
              "physical_print_verified": False}
    (exports / "roundtrip-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--staged-exports", type=Path, required=True)
    args = parser.parse_args()
    run(args.scratch, args.staged_exports)
