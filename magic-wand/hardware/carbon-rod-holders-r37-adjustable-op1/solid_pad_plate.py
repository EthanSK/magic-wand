"""Prepare an R37 A1 mini plate with solid breakaway pads from the checked layout."""

import argparse
import json
import math
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import manifold3d as mf
import numpy as np
import trimesh

import holder37 as design
from plate36 import plate
import project22
from slice19 import anchor_in_project

OUT = design.HERE / "exports"
BASE = OUT / "R37-Complete-A1-mini-PETG-layout.3mf"
TITLE = "Magic Wand R37 solid pads"
MODEL = "3D/3dmodel.model"
SETTINGS = plate.MODEL_SETTINGS
PROJECT = "Metadata/project_settings.config"
PAD_HEIGHT = .4
SLOW_LAYER = 105
SLOW_HEIGHT = 21.0
Y_SPEED = 120
Y_ACCEL = 1000
# Give the tall, heavy carrier the most contact area and front-back leverage.
PAD_EXTENSION = {
    "Key_Carrier": 9., "Grove_Touch_Bracket": 7., "XIAO_Rod_Holder": 5.,
    "Battery_Holder": 6., "Cable_Clip_12_Wire": 3.,
}
# The flat pieces use a wider continuous outer brim. The patterned spacer
# retains every through-opening and its full 0.4 mm finished thickness.
FLAT_BRIMS = {"XIAO_Near_Keeper": 6, "Battery_End_Door": 6,
              "Battery_Spacer_0p4mm_Patterned": 5}
# Shelf placement leaves the Smooth Timelapse tower in its verified front
# position. Actual envelopes are checked before slicing.
ORIGINS = {
    "Key_Carrier": (18., 113.), "Grove_Touch_Bracket": (109., 120.),
    "XIAO_Rod_Holder": (113., 75.), "XIAO_Near_Keeper": (119., 51.),
    "Battery_Holder": (24., 63.), "Battery_End_Door": (58., 28.),
    "Battery_Spacer_0p4mm_Patterned": (18., 18.), "Cable_Clip_12_Wire": (73., 56.),
}


def solid_pads(previous, body, distance, name):
    # Keep the original narrow ties and their release direction. Grow away
    # from each tie, and fill old perforations without entering the part.
    keepout = body.project().offset(.42)
    sections = []
    for pad in previous.decompose():
        section = pad.slice(.1)
        outer = mf.CrossSection([max(section.to_polygons(), key=len)])
        tie = (pad ^ body).bounding_box()
        assert not (pad ^ body).is_empty(), name
        bounds = section.bounds()
        vx = (bounds[0] + bounds[2] - tie[0] - tie[3]) / 2
        vy = (bounds[1] + bounds[3] - tie[1] - tie[4]) / 2
        norm = math.hypot(vx, vy)
        delta = (distance * vx / norm, distance * vy / norm)
        shifted = outer.translate(delta).offset(distance * .18)
        if name == "Cable_Clip_12_Wire":
            # Short, square-ended pads avoid a thin point beside the wire slit.
            end = bounds[1] if vy < 0 else bounds[3]
            lower = end - distance if vy < 0 else end - 1.
            enlarged = mf.CrossSection.square((7., distance + 1.)).translate((6., lower))
        else:
            enlarged = (outer + shifted).hull()
        enlarged -= keepout
        connected = [piece for piece in enlarged.decompose() if (piece ^ section).area() > 1.]
        assert connected, name
        sections.append(section + mf.CrossSection.compose(connected))
    result = mf.Manifold.extrude(mf.CrossSection.batch_boolean(sections, mf.OpType.Add), PAD_HEIGHT)
    assert len(result.decompose()) == len(previous.decompose()), name
    assert abs((result ^ body).volume() - (previous ^ body).volume()) < .001, name
    assert result.slice(.1).area() > previous.slice(.1).area() * 1.3, name
    return result


def make(output):
    output.mkdir(parents=True, exist_ok=True)
    staged = output / "build-source" / "exports"
    staged.mkdir(parents=True, exist_ok=True)
    with ZipFile(BASE) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    model = ET.fromstring(files[MODEL])
    settings = ET.fromstring(files[SETTINGS])
    config = json.loads(files[PROJECT])
    ET.register_namespace("", model.tag.split("}")[0][1:])
    baseline = plate.read_json(OUT / "print-checks.json")
    records = {}
    anchors = {}
    extents = {}
    for item in model.findall("./{*}build/{*}item"):
        ident = item.get("objectid")
        obj = settings.find(f"object[@id='{ident}']")
        name = obj.find("metadata[@key='name']").get("value")
        source = baseline["source_parts"][name]
        folder = design.HERE / source["directory"] / source["exports"]
        source_mesh = folder / source["source_filename"]
        record = plate.read_json(folder / "manifest.json")["parts"][name]
        assert plate.digest(source_mesh) == record["stl_sha256"]
        shutil.copyfile(source_mesh, staged / source_mesh.name)
        records[name] = record
        body = project22.holder.read(source_mesh)
        transform = item.get("transform").split()
        original = np.asarray(transform[-3:], dtype=float)
        placement = ORIGINS[name]
        item.set("transform", " ".join((*transform[:9], *map(str, placement), transform[-1])))
        if name in PAD_EXTENSION:
            prior, title = anchor_in_project(BASE, name, original)
            pads = solid_pads(prior, body, PAD_EXTENSION[name], name)
            old_pad = next(p for p in obj.findall("part") if p.find("metadata[@key='name']").get("value") == title)
            child_id = old_pad.get("id")
            parent = model.find(f"./{{*}}resources/{{*}}object[@id='{ident}']")
            parent.find("{*}components").remove(parent.find(f"./{{*}}components/{{*}}component[@objectid='{child_id}']"))
            resources = model.find("{*}resources")
            resources.remove(resources.find(f"{{*}}object[@id='{child_id}']"))
            obj.remove(old_pad)
            receipt = {
                "hole_centres_print_xy_mm": [],
                "old_area_mm2": round(prior.slice(.1).area(), 2),
                "solid_area_mm2": round(pads.slice(.1).area(), 2),
                "pad_thickness_mm": PAD_HEIGHT,
                "bounds_local_mm": list(pads.bounding_box()),
                "ties_unchanged": True,
            }
            anchors[name] = plate.write_pads(staged, name, pads, project22.holder, receipt)
            mesh = trimesh.load_mesh(staged / f"{name}{plate.PAD_SUFFIX}")
            project22.studio.p19.add_mesh_part(model, obj, mesh, child_id, "normal_part",
                                              f"REMOVE AFTER PRINT - {name} solid tear-off pads")
            extent = (pads + body).bounding_box()
            extents[name] = [extent[0]+placement[0], extent[1]+placement[1],
                             extent[3]+placement[0], extent[4]+placement[1]]
        else:
            width = FLAT_BRIMS[name]
            obj.find("metadata[@key='brim_width']").set("value", str(width))
            extent = body.bounding_box()
            gap = width + .15
            extents[name] = [extent[0]+placement[0]-gap, extent[1]+placement[1]-gap,
                             extent[3]+placement[0]+gap, extent[4]+placement[1]+gap]
    used = {"Smooth Timelapse tower": [113., 13., 140., 41.]}
    for name, (x0, y0, x1, y1) in extents.items():
        assert min(x0, y0) >= 5 and max(x1, y1) <= 175, (name, extents[name])
        for other, (a0, b0, a1, b1) in used.items():
            assert x1 + 3 <= a0 or a1 + 3 <= x0 or y1 + 3 <= b0 or b1 + 3 <= y0, (
                name, extents[name], other, used[other])
        used[name] = extents[name]
    settings.find("plate/metadata[@key='plater_name']").set("value", TITLE)
    height_recipe = {
        "enable_height_slowdown": ["1"], "slowdown_start_height": [f"{SLOW_HEIGHT:g}"],
        "slowdown_end_height": [str(SLOW_HEIGHT + .2)], "slowdown_start_speed": ["45"],
        "slowdown_end_speed": ["45"], "slowdown_start_acc": [str(Y_ACCEL)],
        "slowdown_end_acc": [str(Y_ACCEL)],
    }
    config.update(height_recipe)
    config["layer_change_gcode"] += (
        f"\n{{if layer_num == {SLOW_LAYER-1}}}\nM400\nM201 Y{Y_ACCEL}"
        f" ; Bed acceleration limit\nM203 Y{Y_SPEED} ; Bed speed limit\n{{endif}}")
    config["machine_end_gcode"] += (
        f"\nM400\nM201 Y{config['machine_max_acceleration_y'][0]} ; Restore bed acceleration"
        f"\nM203 Y{config['machine_max_speed_y'][0]} ; Restore bed speed\n")
    registrations = config["different_settings_to_system"]
    for index, additions in ((0, height_recipe), (2, ("layer_change_gcode", "machine_end_gcode"))):
        registrations[index] = ";".join(sorted(set(filter(None, registrations[index].split(";"))) | set(additions)))
    files.update({MODEL: ET.tostring(model, encoding="utf-8", xml_declaration=True),
                  SETTINGS: ET.tostring(settings, encoding="utf-8", xml_declaration=True),
                  PROJECT: json.dumps(config).encode()})
    layout = output / "R37-Solid-Pads-A1-mini-PETG-layout.3mf"
    with ZipFile(layout, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    for file, contents in (
        (staged / "manifest.json", {"parts": records}),
        (staged / "anchors.json", {"parts": anchors}),
        (output / "print-checks.json", {
            "build_list": baseline["build_list"], "source_parts": baseline["source_parts"],
            "effective_filament_settings": baseline["effective_filament_settings"],
            "bom_sha256": baseline["bom_sha256"], "baseline_layout_sha256": plate.digest(BASE),
            "layout_sha256": plate.digest(layout), "anchors": anchors,
            "flat_brim_width_mm": FLAT_BRIMS, "material_bounds_xy_mm": extents,
        }),
    ):
        file.write_text(json.dumps(contents, indent=2) + "\n")
    return layout


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(make(parser.parse_args().output.resolve()))
