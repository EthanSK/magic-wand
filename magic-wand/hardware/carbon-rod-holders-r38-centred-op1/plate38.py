"""Prepare R38 from its current meshes and the checked R37 PETG recipe.

Run assembly38.py first. This only prepares an editable plate; slice it and
audit the deposited paths before packaging a print-only archive.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import trimesh

import holder38 as design
import plate32 as plate
import solid_pad_plate as pads
import standard_retry_plate as recipe

HERE = Path(__file__).resolve().parent
BASE = design.R37 / "exports/standard-retry/R37-Standard-PETG-retry-layout.3mf"
MODEL = "3D/3dmodel.model"
PROJECT = "Metadata/project_settings.config"
RANGES = "Metadata/layer_config_ranges.xml"
BASE_STAGE = plate.stage_parts
BASE_CONFIGURE = plate.configure_layout
BASE_COMMAND_AUDIT = recipe.project22.studio.p19.command_audit

# R38's exported downward faces give these X/Z assembly coordinates, with
# print height measured from the rear face. Include the saddle's adjacent
# 13.4 mm strip as well as its 13.5 mm face in the same support selection.
# The actual support, its removal route and nearby holes still need a slice audit.
LEDGES = (
    ("rod holder side", (4.12, 7.26, 8.03, 11.35), 9.5),
    ("rod holder ledge", (-3.55, .74548, 4.85842, 6.95), 13.4),
    ("connector opening", (-4.12, 6.95, 4.12, 10.08), 15.65),
    ("outer finger guard", (-30.1, 4.3, -26.3, 5.8), 19.7),
)


def command_audit(path, expected):
    """Keep the A1 mini guard, allowing only R37's exact base-layer extension.

    The generic R19 guard intentionally accepts only stock machine commands.
    Validate the sole approved extension before reusing all of that guard's
    temperature, extrusion-mode and shutdown checks. Never treat an arbitrary
    command block from the supplied archive as a trusted machine template.
    """
    import project22

    studio = project22.studio.p19
    resolve = studio.resolve
    printer = expected["printer_settings_id"]
    machine = resolve("machine", printer)
    extended = {**machine, "layer_change_gcode": machine["layer_change_gcode"]
                + recipe.early_acceleration_commands(machine)}
    with ZipFile(path) as archive:
        config = json.loads(archive.read(PROJECT))
        gcode = archive.read("Metadata/plate_1.gcode").decode()
    templates = ("machine_start_gcode", "machine_end_gcode", "layer_change_gcode",
                 "time_lapse_gcode", "change_filament_gcode")
    assert all(config.get(key) == extended[key] for key in templates), "Unapproved machine commands"
    limits = {key: value for key, value in machine.items() if key.startswith("machine_max_")}
    assert all(config.get(key) == value for key, value in limits.items()), "Machine limits changed"
    assert config["nozzle_temperature"] == config["nozzle_temperature_initial_layer"] == ["245"]
    assert config["textured_plate_temp"] == config["textured_plate_temp_initial_layer"] == ["60"]

    def trusted(kind, name):
        return extended if (kind, name) == ("machine", printer) else resolve(kind, name)

    with patch.object(studio, "resolve", side_effect=trusted):
        result = BASE_COMMAND_AUDIT(path, expected)
    # The slicer emits machine limits once, the gentle cap at layer one, and
    # the stock limit restoration at layer four. Reject extra motion edits.
    layer, events = 0, []
    for raw in gcode.split("; EXECUTABLE_BLOCK_START", 1)[1].splitlines():
        line = raw.split(";", 1)[0].strip()
        if match := re.fullmatch(r"M73 L(\d+)", line):
            layer = int(match[1])
        if re.match(r"^M201\s", line):
            axes = {axis: float(value) for axis, value in re.findall(r"\b([XYZE])(-?\d+(?:\.\d+)?)", line)}
            events.append((layer, axes))
    initial = {axis: float(machine[f"machine_max_acceleration_{axis.lower()}"][0]) for axis in "XYZE"}
    restored = {axis: initial[axis] for axis in "XY"}
    assert events == [(0, initial), (1, {"X": 1000., "Y": 1000.}), (4, restored)], events
    result["official_machine_templates_match"] = [key for key in templates if key != "layer_change_gcode"]
    result.update(approved_layer_change_extension="R37 early_acceleration_commands", machine_limits_unchanged=True,
                  early_acceleration_events=[{"layer": number, "axes": axes} for number, axes in events])
    return result


def names(settings):
    return {obj.get("id"): obj.find("metadata[@key='name']").get("value")
            for obj in settings.findall("object")}


def stage_parts(selected, exports, holder, anchors20, manifold):
    """Use the established R32 ties, then R37's solid-pad enlargement."""
    manifest, anchors = BASE_STAGE(selected, exports, holder, anchors20, manifold)
    for name, distance in pads.PAD_EXTENSION.items():
        if name not in selected:
            continue
        previous = holder.read(exports / f"{name}{plate.PAD_SUFFIX}")
        body = holder.read(exports / f"{name}{plate.SOURCE_SUFFIX}")
        enlarged = pads.solid_pads(previous, body, distance, name)
        receipt = {
            **anchors[name],
            "hole_centres_print_xy_mm": [],
            "old_area_mm2": round(previous.slice(.1).area(), 3),
            "solid_area_mm2": round(enlarged.slice(.1).area(), 3),
            "pad_thickness_mm": pads.PAD_HEIGHT,
            "ties_unchanged": True,
        }
        anchors[name] = plate.write_pads(exports, name, enlarged, holder, receipt)
    (exports / "anchors.json").write_text(json.dumps({"parts": anchors}, indent=2) + "\n")
    return manifest, anchors


def support_boxes(record):
    frame = np.asarray(record["print_to_assembly"])
    expected = np.asarray(((1., 0., 0.), (0., 0., -1.), (0., 1., 0.)))
    assert np.allclose(frame[:3, :3], expected), "Re-screen ledges after changing print orientation"
    x_shift, y_shift = -frame[0, 3], -frame[2, 3]
    return [(label, ((x0 + x_shift - .15, y0 + y_shift - .15,
                      height - (.8 if label == "outer finger guard" else .05)),
                     (x1 + x_shift + .15, y1 + y_shift + .15,
                      height + (1.1 if label == "outer finger guard" else .35))))
            for label, (x0, y0, x1, y1), height in LEDGES]


def configure_layout(path, title):
    import project22

    BASE_CONFIGURE(path, title)
    with ZipFile(path) as source:
        files = {name: source.read(name) for name in source.namelist()}
    with ZipFile(BASE) as source:
        baseline = {name: source.read(name) for name in (PROJECT, RANGES, MODEL, plate.MODEL_SETTINGS)}
    config = json.loads(baseline[PROJECT])
    settings = ET.fromstring(files[plate.MODEL_SETTINGS])
    model = ET.fromstring(files[MODEL])
    current_names = names(settings)
    current_order = [current_names[item.get("objectid")] for item in model.findall("./{*}build/{*}item")]
    old_names = names(ET.fromstring(baseline[plate.MODEL_SETTINGS]))
    old_order = [old_names[item.get("objectid")] for item in ET.fromstring(baseline[MODEL]).findall("./{*}build/{*}item")]
    assert set(old_order) == set(current_order), "R38 must keep the complete seven-part assembly"
    ranges = ET.fromstring(baseline[RANGES])
    for entry in ranges.findall("object"):
        entry.set("id", str(current_order.index(old_order[int(entry.get("id")) - 1]) + 1))

    carrier = next(obj for obj in settings.findall("object") if current_names[obj.get("id")] == plate.KEY)
    overrides = {
        "enable_support": "1", "support_type": "normal(manual)",
        "support_on_build_plate_only": "0", "support_top_z_distance": "0.2",
        "support_bottom_z_distance": "0.2", "support_object_xy_distance": "0.35",
        "support_interface_top_layers": "2", "support_interface_spacing": "0.20",
        "bridge_no_support": "0",
    }
    for key, value in overrides.items():
        entry = carrier.find(f"metadata[@key='{key}']")
        if entry is None:
            entry = ET.SubElement(carrier, "metadata", key=key)
        entry.set("value", value)
    manifest = plate.read_json(path.parent / "build-source/exports/manifest.json")
    boxes = support_boxes(manifest["parts"][plate.KEY])
    identifier = max(int(obj.get("id")) for obj in model.findall("./{*}resources/{*}object")) + 1
    for label, bounds in boxes:
        project22.studio.p19.add_mesh_part(model, carrier, trimesh.creation.box(bounds=bounds),
                                          identifier, "support_enforcer",
                                          f"REMOVE AFTER PRINT - {label} support")
        identifier += 1
    # Keep the board-screw seats solid without filling the rest of the light
    # carrier. Modifier meshes set local infill; they add no external plastic.
    inverse = np.linalg.inv(np.asarray(manifest["parts"][plate.KEY]["print_to_assembly"]))[:3, :]
    for number, seat in enumerate(design.op1_seats().decompose(), 1):
        bounds = np.asarray(seat.transform(inverse).bounding_box()).reshape(2, 3)
        bounds[0] -= .15
        bounds[1] += .15
        project22.studio.p19.add_mesh_part(
            model, carrier, trimesh.creation.box(bounds=bounds), identifier,
            "modifier_part", f"OP1 mounting seat {number} solid infill",
            (("sparse_infill_density", "100%"),))
        identifier += 1
    files.update({
        PROJECT: json.dumps(config).encode(),
        RANGES: ET.tostring(ranges, encoding="utf-8", xml_declaration=True),
        MODEL: ET.tostring(model, encoding="utf-8", xml_declaration=True),
        plate.MODEL_SETTINGS: ET.tostring(settings, encoding="utf-8", xml_declaration=True),
    })
    with ZipFile(path, "w", ZIP_DEFLATED) as target:
        for name, content in files.items():
            target.writestr(name, content)


def make(output):
    output.mkdir(parents=True, exist_ok=True)
    assert not any(output.iterdir()), "Use a fresh preparation directory"
    selected = {name for group in plate.read_json(HERE / plate.BOM)["groups"].values()
                for name in group["parts"]}
    plate.BRACKET = design.BRACKET
    plate.CLIPS = ()
    plate.LOCAL_PADS = (plate.KEY, plate.BRACKET)
    plate.ORIGINS = {name: origin for name, origin in pads.ORIGINS.items() if name in selected}
    plate.BRIM_WIDTH = 6
    plate.stage_parts = stage_parts
    plate.configure_layout = configure_layout
    plate.build(HERE, output, plate.FLASHFORGE_PROFILE, False, True)
    target = output / "R38-Complete-A1-mini-PETG-layout.3mf"
    with ZipFile(target) as archive:
        config = json.loads(archive.read(PROJECT))
    report_path = output / "print-checks.json"
    report = plate.read_json(report_path)
    baseline_report = plate.read_json(BASE.parent / "print-checks.json")
    report.update(
        layout_sha256=plate.digest(target), driver_sha256=plate.digest(Path(__file__)),
        recipe_source_sha256=plate.digest(BASE),
        effective_filament_settings={key: config[key] for key in baseline_report["effective_filament_settings"]},
        process_overrides=baseline_report["process_overrides"],
        support_enforcers=support_boxes(plate.read_json(output / "build-source/exports/manifest.json")["parts"][plate.KEY]),
        physical_success_verified=False,
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return target


def package(archive, output):
    target = recipe.make_print_only(archive, output)
    renamed = output / "R38-Centred-OP1-print-only.3mf"
    target.rename(renamed)
    receipt_path = output / "print-only.json"
    receipt = plate.read_json(receipt_path)
    receipt.update(file=renamed.name, sha256=sha256(renamed.read_bytes()).hexdigest())
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return renamed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    print(package(args.package.resolve(), args.output.resolve()) if args.package
          else make(args.output.resolve()))
