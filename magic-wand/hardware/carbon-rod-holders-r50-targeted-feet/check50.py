"""Verify the selected native slice and package its original printer instructions."""
import argparse
from hashlib import md5, sha256
import json
import re
from pathlib import Path
import shutil
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from prepare50 import BASE, HELPERS, WIDE

HERE = Path(__file__).resolve().parent
R49 = WIDE.parent.parent
sys.path.insert(0, str(R49))
import audit49
from native48 import digest, read, write
from plate38 import command_audit, recipe

SLICE = "R50.gcode.3mf"
LAYOUT = "R50-layout.3mf"
PRINT_ONLY = "Magic-Wand-R50-Targeted-Feet-print-only.3mf"
RETAINED_BRIMS = {"Battery_End_Door", "XIAO_Near_Keeper"}


def structure(folder, scratch):
    import guard_bond48
    import shoulder_paths48
    import strength48

    archive = folder / SLICE
    # The old joint checker uses its historical directory name for the
    # per-part report and the normalized meshes derived from the current slice.
    link = folder / "other-audit"
    link.symlink_to("hardware-audit", target_is_directory=True)
    try:
        strength48.check_native(archive, scratch)
    finally:
        link.unlink()
    shutil.copyfile(audit49.BASELINE / "R45-Key-Carrier.stl", folder / "R45-Key-Carrier.stl")
    assert guard_bond48.check_seams(archive)["passed"]
    shoulder_paths48.check(archive, scratch, cradle_release_report=folder / "key-release.json")


def estimate(path):
    with ZipFile(path) as z:
        info = ET.fromstring(z.read("Metadata/slice_info.config"))
    settings = {n.get("key"): n.get("value") for n in info.findall("plate/metadata")}
    return {"seconds": int(settings["prediction"]), "grams": float(settings["weight"])}


def package(folder, target):
    archive = folder / SLICE
    layout = folder / LAYOUT
    checksum = digest(archive)
    with ZipFile(archive) as z:
        assert z.testzip() is None
        cfg = json.loads(z.read("Metadata/project_settings.config"))
        code = z.read("Metadata/plate_1.gcode")
        assert z.read("Metadata/plate_1.gcode.md5").decode().strip().lower() == md5(code).hexdigest()
        preview = z.read("Metadata/plate_1.png")
        objects = ET.fromstring(z.read("Metadata/slice_info.config")).findall("plate/object")
        assert {o.get("name") for o in objects} == audit49.FUNCTIONAL | HELPERS
        assert cfg["timelapse_type"] == cfg["enable_prime_tower"] == "1"
        assert cfg["filament_max_volumetric_speed"] == ["8"] and cfg["filament_type"] == ["PETG"]
    with ZipFile(layout) as z:
        original_cfg = json.loads(z.read("Metadata/project_settings.config"))
    machine = command_audit(archive, original_cfg)
    assert machine["passed"] and machine["project_sha256"] == checksum
    assert machine["first_object_nozzle_target_c"] == 245 and machine["first_object_bed_target_c"] == 60
    write(folder / "machine-check.json", machine)
    gates = {
        "machine-check.json": ("project_sha256", "passed"),
        "plate-clearance.json": ("archive_sha256", "passed"),
        "helper-starts.json": ("archive_sha256", None),
        "key-tab-feet.json": ("archive_sha256", "carrier_grounded"),
        "roof-comparison.json": ("archive_sha256", "within_previous_trial_envelope"),
        "key-release.json": ("archive_sha256", "passed"),
        "key-working-spaces.json": ("archive_sha256", "passed"),
        "swing-tab-removal.json": ("archive_sha256", "passed"),
        "lead-tab-removal.json": ("archive_sha256", "passed"),
        "hardware-audit/other-parts-audit.json": ("complete_archive_sha256", "passed"),
        "hardware-audit/edge-click-load-path.json": ("archive_sha256", "passed"),
        "guard-seams.json": ("archive_sha256", "passed"),
        "strength-paths.json": ("archive_sha256", "passed"),
        "wire-feed-path.json": ("archive_sha256", "passed"),
        "rod-clip-shoulder.json": ("archive_sha256", "passed"),
        "reopen-checks.json": ("selected_archive_sha256", "actual_modifier_placements_equivalent"),
        "R50.gcode.native.json": ("archive_sha256", None),
    }
    receipts = {}
    for filename, (identity, gate) in gates.items():
        row = read(folder / filename)
        assert row[identity] == checksum and (gate is None or row[gate]), filename
        receipts[filename] = row
    assert all(not r["unrooted_actual_components"] for r in receipts["helper-starts.json"]["owners"].values())
    reopen = receipts["reopen-checks.json"]
    assert reopen["global_settings_identical"] and reopen["object_process_settings_identical"]
    prior_native = read(R49 / "exports/R49-Wide-Feet.gcode.native.json")
    assert [p["warning_message"] for p in receipts["R50.gcode.native.json"]["plates"]] == [p["warning_message"] for p in prior_native["plates"]]
    target.mkdir(parents=True, exist_ok=True)
    for file in (archive, layout):
        with ZipFile(file) as source:
            assert source.testzip() is None
            for name in source.namelist():
                if name.endswith((".model", ".config", ".xml", ".json", ".gcode")):
                    assert not re.search(rb"/Users/|/Volumes/|/private/(?:tmp|var)/", source.read(name)), name
            model = ET.fromstring(source.read("3D/3dmodel.model"))
            assert all(not n.text for n in model.findall("{*}metadata[@name='DesignerUserId']"))
        shutil.copyfile(file, target / file.name)
    for name, row in receipts.items():
        if name == "reopen-checks.json":
            row.update(own_final_deposition_audited=True, scope="Selected native slice reopened and checked.")
        write(target / Path(name).name, row)
    (target / "plate.png").write_bytes(preview)
    shipped = target / PRINT_ONLY
    recipe.make_print_only(archive, target).replace(shipped)
    with ZipFile(shipped) as z:
        assert z.testzip() is None and z.read("Metadata/plate_1.gcode") == code
    packing = read(target / "print-only.json")
    packing.update(file=PRINT_ONLY)
    assert packing["sha256"] == digest(shipped) and packing["gcode_sha256"] == sha256(code).hexdigest()
    write(target / "print-only.json", packing)
    report = {
        "editable_sha256": digest(layout),
        "selected_sha256": checksum,
        "print_only_sha256": digest(shipped),
        "functional_parts": sorted(audit49.FUNCTIONAL),
        "source_editable_sha256": {"R48": digest(BASE), "R49": digest(WIDE)},
        "estimates": {
            "R48_wide_bracket": estimate(BASE.parent / "R48-Wide-Pads.gcode.3mf"),
            "R49_all_wide": estimate(WIDE.parent / "R49-Wide-Feet.gcode.3mf"),
            "R50_targeted_slower_carrier": estimate(folder.parent / "control/initial.gcode.3mf"),
            "R50_targeted_standard_carrier_first_slice": estimate(folder / "initial.gcode.3mf"),
            "R50_targeted_standard_carrier": estimate(archive),
        },
        "key_supports_with_larger_feet": sorted(HELPERS),
        "native_warning": "Key_Carrier floating regions; explicit support, roof and removal checks recorded.",
        "physical_trial_verified": False,
        "verification_files": {Path(name).name: digest(target / Path(name).name) for name in receipts},
    }
    write(target / "verification.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("hardware", "key", "structure", "package"))
    parser.add_argument("folder", type=Path)
    parser.add_argument("r48_scratch", type=Path)
    args = parser.parse_args()
    if args.phase == "hardware":
        audit49.check_hardware(args.folder / SLICE, args.r48_scratch, args.folder / LAYOUT,
                               retained_outer_brims=RETAINED_BRIMS)
    elif args.phase == "key":
        audit49.check_key(args.folder / SLICE, args.r48_scratch)
    elif args.phase == "structure":
        structure(args.folder, args.r48_scratch)
    else:
        package(args.folder, HERE / "exports")
