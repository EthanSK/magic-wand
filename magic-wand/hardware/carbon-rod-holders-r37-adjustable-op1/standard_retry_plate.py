"""Prepare R37 with Standard motion and a lower-ooze PETG trial.

Run this with a fresh output directory, then slice and run audit37.py.
The finished holder geometry, breakaway pads and local OP1 support come
from solid_pad_plate.py. This is a printing recipe revision.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import solid_pad_plate as solid
import project22


TITLE = "Magic Wand R37 Standard PETG retry"
SPACER = "Battery_Spacer_0p4mm_Patterned"
MOTION_KEYS = (
    "outer_wall_speed", "inner_wall_speed", "internal_solid_infill_speed",
    "sparse_infill_speed", "gap_infill_speed", "top_surface_speed",
    "support_speed", "support_interface_speed", "bridge_speed", "travel_speed",
    "default_acceleration", "outer_wall_acceleration", "inner_wall_acceleration",
    "top_surface_acceleration", "travel_acceleration", "sparse_infill_acceleration",
    "prime_tower_max_speed",
)
EARLY_LAYERS = {
    "layer_height": "0.2",
    "outer_wall_speed": "40", "inner_wall_speed": "50",
    "internal_solid_infill_speed": "50", "sparse_infill_speed": "60",
    "gap_infill_speed": "40", "top_surface_speed": "40",
    "default_acceleration": "1000", "outer_wall_acceleration": "1000",
    "inner_wall_acceleration": "1000", "top_surface_acceleration": "1000",
    "sparse_infill_acceleration": "1000", "travel_acceleration": "1000",
}


def make(output: Path) -> Path:
    layout = solid.make(output)
    with ZipFile(layout) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    config = json.loads(files[solid.PROJECT])
    studio = project22.studio.p19
    standard = studio.resolve("process", "0.20mm Standard @BBL A1M")
    machine = studio.resolve("machine", config["printer_settings_id"])
    process = {key: standard[key] for key in MOTION_KEYS if key in standard}
    # Keep the first three layers gentle while the flat pads form.
    # Ethan requested normal motion afterwards, including taller travels.
    process.update(initial_layer_speed=["20"], initial_layer_infill_speed=["30"],
                   initial_layer_acceleration=["500"], enable_height_slowdown=["0"],
                   initial_layer_travel_acceleration=["1000"],
                   support_speed=["40"], support_interface_speed=["35"],
                   prime_tower_max_speed="60", wipe_tower_x=["120"], wipe_tower_y=["20"])
    filament = {
        # Matching targets keep the official A1 mini's unconditional
        # nozzle wait valid for the first deposited line as well.
        "nozzle_temperature_initial_layer": ["245"],
        "nozzle_temperature": ["245"],
        "textured_plate_temp_initial_layer": ["60"],
        "textured_plate_temp": ["60"],
        "filament_retraction_length": ["1.2"],
        "filament_retraction_speed": ["35"],
        "filament_deretraction_speed": ["35"],
        "close_fan_the_first_x_layers": ["3"],
        "fan_min_speed": ["50"], "fan_max_speed": ["90"],
        "overhang_fan_speed": ["100"],
        "filament_max_volumetric_speed": ["8"],
    }
    config.update(process)
    config.update(filament)
    # Remove the interrupted trial's Y-axis and height-based overrides.
    # Studio emits M201/M203 from the machine limits before its startup
    # template. Verify those executable commands in the finished slice.
    for key in ("layer_change_gcode", "machine_end_gcode"):
        config[key] = machine[key]
    for key, value in machine.items():
        if key.startswith("machine_max_"):
            config[key] = value
    # Support travel ignores object-height acceleration overrides. Keep
    # both moving axes gentle for the three base layers, then restore
    # the actual machine profile before normal layer-four motion.
    config["layer_change_gcode"] += early_acceleration_commands(machine)
    for index, additions in ((0, process), (1, filament), (2, ("layer_change_gcode",))):
        current = set(filter(None, config["different_settings_to_system"][index].split(";")))
        if index == 2:
            current -= {"layer_change_gcode", "machine_end_gcode"}
        config["different_settings_to_system"][index] = ";".join(sorted(current | set(additions)))

    model = ET.fromstring(files[solid.MODEL])
    settings = ET.fromstring(files[solid.SETTINGS])
    objects = {obj.get("id"): obj for obj in settings.findall("object")}
    build = model.find("{*}build")
    resources = model.find("{*}resources")
    original_order = list(build)
    kept_indices = []
    for index, item in enumerate(original_order, 1):
        obj = objects[item.get("objectid")]
        name = obj.find("metadata[@key='name']").get("value")
        if name == SPACER:
            # Ethan excluded routine loose spacers, while keeping doors
            # and retainers in every holder batch.
            build.remove(item)
            settings.remove(obj)
            parent = resources.find(f"{{*}}object[@id='{item.get('objectid')}']")
            removed_ids = {parent.get("id")} | {
                child.get("objectid") for child in parent.findall("{*}components/{*}component")
            }
            for resource in list(resources):
                if resource.get("id") in removed_ids:
                    resources.remove(resource)
            for instance in settings.findall("plate/model_instance"):
                identity = instance.find("metadata[@key='object_id']")
                if identity.get("value") == item.get("objectid"):
                    settings.find("plate").remove(instance)
        else:
            kept_indices.append(index)
    resource_ids = {resource.get("id") for resource in resources}
    assert all(child.get("objectid") in resource_ids
               for child in resources.findall("{*}object/{*}components/{*}component"))
    assert {instance.find("metadata[@key='object_id']").get("value")
            for instance in settings.findall("plate/model_instance")} == {
                item.get("objectid") for item in build}
    ranges_path = "Metadata/layer_config_ranges.xml"
    if ranges_path in files:
        ranges = ET.fromstring(files[ranges_path])
        for entry in list(ranges):
            old_index = int(entry.get("id"))
            if old_index in kept_indices:
                entry.set("id", str(kept_indices.index(old_index) + 1))
            else:
                ranges.remove(entry)
        for index in range(1, len(kept_indices) + 1):
            obj = ranges.find(f"object[@id='{index}']")
            if obj is None:
                obj = ET.SubElement(ranges, "object", id=str(index))
            early = ET.Element("range", min_z="0", max_z="0.6")
            obj.insert(0, early)
            for key, value in EARLY_LAYERS.items():
                ET.SubElement(early, "option", opt_key=key).text = value
        files[ranges_path] = ET.tostring(ranges, encoding="utf-8", xml_declaration=True)
    settings.find("plate/metadata[@key='plater_name']").set("value", TITLE)
    files[solid.MODEL] = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    files[solid.SETTINGS] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    files[solid.PROJECT] = json.dumps(config).encode()
    final = output / "R37-Standard-PETG-retry-layout.3mf"
    with ZipFile(final, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    layout.unlink()
    report_path = output / "print-checks.json"
    report = solid.plate.read_json(report_path)
    report["build_list"].remove(SPACER)
    for field in ("source_parts", "flat_brim_width_mm", "material_bounds_xy_mm"):
        report[field].pop(SPACER, None)
    manifest_path = output / "build-source/exports/manifest.json"
    manifest = solid.plate.read_json(manifest_path)
    manifest["parts"].pop(SPACER)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    report["effective_filament_settings"].update(filament)
    report.update(layout_sha256=solid.plate.digest(final), process_overrides=process,
                  first_three_layer_overrides=EARLY_LAYERS,
                  unchanged_holder_geometry=True, physical_success_verified=False,
                  omitted_routine_spacer=SPACER)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return final


def early_acceleration_commands(machine: dict) -> str:
    return (
        "\n{if layer_num == 0}\nM400\nM201 X1000 Y1000 ; Three gentle base layers\n{endif}"
        "\n{if layer_num == 3}\nM400"
        f"\nM201 X{machine['machine_max_acceleration_x'][0]}"
        f" Y{machine['machine_max_acceleration_y'][0]} ; Restore Standard motion\n{{endif}}"
    )


def make_print_only(archive: Path, output: Path) -> Path:
    """Keep audited G-code immutable when Studio opens the print file."""
    source_hash = solid.plate.digest(archive)
    with ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist()
                 if not name.startswith("3D/") or name == solid.MODEL}
    gcode_name = "Metadata/plate_1.gcode"
    gcode_hash = sha256(files[gcode_name]).hexdigest()
    model = ET.fromstring(files[solid.MODEL])
    model.find("{*}resources").clear()
    model.find("{*}build").clear()
    for metadata in model.findall("{*}metadata"):
        if metadata.get("name") == "DesignerUserId":
            model.remove(metadata)
    files[solid.MODEL] = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    settings = ET.fromstring(files[solid.SETTINGS])
    for obj in settings.findall("object"):
        settings.remove(obj)
    for plate in settings.findall("plate"):
        for instance in plate.findall("model_instance"):
            plate.remove(instance)
    files[solid.SETTINGS] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    output.mkdir(parents=True, exist_ok=True)
    target = output / "R37-Standard-PETG-retry-print-only.3mf"
    with ZipFile(target, "w", ZIP_DEFLATED) as destination:
        for name, data in files.items():
            destination.writestr(name, data)
    with ZipFile(target) as reopened:
        assert sha256(reopened.read(gcode_name)).hexdigest() == gcode_hash
    receipt = {"source": archive.name, "source_sha256": source_hash,
               "file": target.name, "sha256": solid.plate.digest(target),
               "gcode_sha256": gcode_hash, "gcode_bytes_unchanged": True}
    (output / "print-only.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--package", type=Path, help="Package an audited sliced archive for printing")
    arguments = parser.parse_args()
    if arguments.package:
        print(make_print_only(arguments.package.resolve(), arguments.output.resolve()))
    else:
        print(make(arguments.output.resolve()))
