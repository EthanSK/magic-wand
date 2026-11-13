"""Prepare the checked solid-pad R37 geometry with gentler early motion."""

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import solid_pad_plate as solid


TITLE = "Magic Wand R37 gentle start"


def make(output):
    layout = solid.make(output)
    with ZipFile(layout) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    config = json.loads(files[solid.PROJECT])
    process = {
        "initial_layer_speed": ["20"], "initial_layer_infill_speed": ["30"],
        "initial_layer_acceleration": ["500"], "initial_layer_travel_acceleration": ["1000"],
        "outer_wall_speed": ["40"], "inner_wall_speed": ["50"],
        "internal_solid_infill_speed": ["50"], "sparse_infill_speed": ["60"],
        "gap_infill_speed": ["40"], "top_surface_speed": ["40"],
        "support_speed": ["40"], "support_interface_speed": ["35"],
        "bridge_speed": ["25"], "travel_speed": ["120"],
        "default_acceleration": ["1000"], "outer_wall_acceleration": ["1000"],
        "inner_wall_acceleration": ["1000"], "top_surface_acceleration": ["1000"],
        "travel_acceleration": ["1000"], "sparse_infill_acceleration": ["1000"],
        "prime_tower_max_speed": "40",
    }
    config.update(process)
    # The battery door bridges on layer five. Give it moderate cooling while
    # avoiding the old rapid changes between 40% and 90% overhang cooling.
    filament = {
        "close_fan_the_first_x_layers": ["3"], "fan_min_speed": ["50"],
        "fan_max_speed": ["60"], "overhang_fan_speed": ["60"],
        "filament_retraction_length": ["1"],
    }
    config.update(filament)
    # Bound the moving bed during all deposited layers, including tower and
    # camera travel. Keep the stock startup and ending routines intact.
    old_transition = (
        f"\n{{if layer_num == {solid.SLOW_LAYER-1}}}\nM400\nM201 Y{solid.Y_ACCEL}"
        f" ; Bed acceleration limit\nM203 Y{solid.Y_SPEED} ; Bed speed limit\n{{endif}}")
    assert config["layer_change_gcode"].endswith(old_transition)
    config["layer_change_gcode"] = config["layer_change_gcode"][:-len(old_transition)] + (
        "\n{if layer_num == 0}\nM400\nM201 Y1000 ; Bed acceleration limit"
        "\nM203 Y120 ; Bed speed limit\n{endif}")
    config["different_settings_to_system"][0] = ";".join(sorted(
        set(filter(None, config["different_settings_to_system"][0].split(";"))) | set(process)))
    config["different_settings_to_system"][1] = ";".join(sorted(
        set(filter(None, config["different_settings_to_system"][1].split(";"))) | set(filament)))
    settings = ET.fromstring(files[solid.SETTINGS])
    settings.find("plate/metadata[@key='plater_name']").set("value", TITLE)
    files[solid.SETTINGS] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    files[solid.PROJECT] = json.dumps(config).encode()
    final = output / "R37-Gentle-Start-A1-mini-PETG-layout.3mf"
    with ZipFile(final, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    layout.unlink()
    report_path = output / "print-checks.json"
    report = solid.plate.read_json(report_path)
    report["effective_filament_settings"].update(filament)
    report.update(layout_sha256=solid.plate.digest(final),
                  pad_geometry_matches_solid_retry=True,
                  motion_from_layer=1, process_overrides=process,
                  physical_adhesion_verified=False)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(make(parser.parse_args().output.resolve()))
