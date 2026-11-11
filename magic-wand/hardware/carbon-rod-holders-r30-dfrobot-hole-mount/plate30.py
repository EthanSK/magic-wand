#!/usr/bin/env python3
"""Slice the R30 DFRobot assembly with the existing A1 mini PETG recipe."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import manifold3d as mf
import numpy as np
import trimesh

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LABEL = "R30-DFRobot-Hinge-A1-mini-PETG"
KEY = "Key_Carrier"
BRACKET = "DFRobot_Hole_Bracket"

def slice_plate(source, scratch, support_boxes=(), hardware=None):
    scratch.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str((hardware or source.parent) / "carbon-rod-holders-r28-dfrobot-touch"))
    import holder28
    import anchors20
    import project22

    studio = project22.studio.p19
    old = project22.holder
    exports = source / "exports"
    manifest = json.loads((exports / "manifest.json").read_text())
    parts = tuple(manifest["parts"])
    keepers = tuple(name for name in parts if name != KEY and "keeper" in name.lower())
    changed = tuple(name for name in parts if name not in (KEY, *keepers))
    assert KEY in parts and len(changed) <= 3 and len(keepers) <= 2, parts
    layout = scratch / f"{LABEL}-layout.3mf"
    pads = exports / f"{KEY}-ANCHOR-REMOVE-AFTER-PRINT.stl"
    anchor_input = scratch / "anchor-source"
    anchor_input.mkdir(exist_ok=True)
    key_source = exports / f"{KEY}-SOURCE-REQUIRES-PREPARATION.stl"
    key_record = manifest["parts"][KEY]
    (anchor_input / "manifest.json").write_text(json.dumps({"parts": {KEY: {
        **key_record, "bounds_mm": key_record["assembly_bounds_mm"],
    }}}))
    anchor_source = anchor_input / key_source.name
    if not anchor_source.exists():
        anchor_source.symlink_to(key_source)
    anchors20.OUT = anchor_input
    anchor, _, _, _, anchor_report = anchors20.anchor(KEY)
    key_body = old.read(key_source)
    assert len(anchor.decompose()) == 4
    assert all((piece ^ key_body).volume() > .04 for piece in anchor.decompose())
    for tie in anchor_report["tie_sites"]:
        x, y = tie["site_print_xy"]
        nx, ny = tie["outward"]
        assert nx == 0 and abs(ny) == 1
        y0, y1 = sorted((y + ny * .45, y + ny * .95))
        assert (key_body ^ old.box(x - 1.5, x + 1.5, y0, y1, .45, 6.)).volume() < .01
    old.mesh(anchor).export(pads)
    anchor_report["stl_sha256"] = old.sha(pads)
    # The bracket's brim reached into the PCB seat. Two thin outside pads
    # tie into the rigid rear crossbar below the PCB surface instead.
    bracket_body = old.read(exports / f"{BRACKET}-SOURCE-REQUIRES-PREPARATION.stl")
    max_x = bracket_body.bounding_box()[3]
    first = bracket_body.slice(.1)
    print_to_assembly = np.asarray(manifest["parts"][BRACKET]["print_to_assembly"])
    y = 18.4 - print_to_assembly[2, 3]
    base_pad = mf.CrossSection.circle(2.4, 48).translate((-3.4, y))
    tie = mf.CrossSection.square((1.28, 1.)).translate((-1.22, y - .5))
    left = base_pad + tie
    right = left.mirror((1., 0.)).translate((max_x, 0.))
    bracket_pads = mf.Manifold.extrude(left + right, .4)
    assert (left ^ first).area() > .03 and (right ^ first).area() > .03
    bracket_pad_path = exports / f"{BRACKET}-ANCHOR-REMOVE-AFTER-PRINT.stl"
    old.mesh(bracket_pads).export(bracket_pad_path)
    anchor_report["bracket_pads_sha256"] = old.sha(bracket_pad_path)
    recipe = {**old.P["print"], "local_recipe": {**old.P["print"]["local_recipe"],
                                                "Key_Carrier_bands_mm": old.key_carrier_bands()}}
    studio.h = SimpleNamespace(PLATE=parts, ANCHORED=(KEY, BRACKET), HERE=source, P={"print": recipe},
                               LOCAL=old.LOCAL, base=old.base, sha=old.sha)
    studio.ORIGINS = {
        KEY: (24, 112),
        **dict(zip(keepers, ((35, 63), (55, 63)))),
        **dict(zip(changed, ((98, 102), (105, 60), (137, 60)))),
    }
    config = studio.settings()
    extents, _ = studio.layout(layout, manifest, config)
    model_name = "3D/3dmodel.model"
    settings_name = "Metadata/model_settings.config"
    with ZipFile(layout) as archive:
        members = {row.filename: (row, archive.read(row)) for row in archive.infolist()}
    model = ET.fromstring(members[model_name][1])
    settings = ET.fromstring(members[settings_name][1])
    objects = {obj.find("metadata[@key='name']").get("value"): obj for obj in settings.findall("object")}
    resources = model.find(studio.tag("resources"))
    ident = 1 + max(int(row.get("id")) for row in resources.findall(studio.tag("object")))

    def set_value(obj, name, value):
        item = obj.find(f"metadata[@key='{name}']")
        if item is None:
            item = ET.SubElement(obj, "metadata", key=name)
        item.set("value", value)

    for part, obj in objects.items():
        if part not in keepers:
            set_value(obj, "wall_generator", "arachne")
    for part, role, label, low, high in support_boxes:
        if role == "support_enforcer":
            for key, value in {"enable_support": "1", "support_type": "normal(manual)",
                               "support_top_z_distance": "0.24", "support_on_build_plate_only": "0",
                               "support_object_xy_distance": "0.55"}.items():
                set_value(objects[part], key, value)
        box = trimesh.creation.box(bounds=[low, high])
        frame = np.asarray(manifest["parts"][part]["print_to_assembly"])
        box.apply_transform(np.linalg.inv(frame))
        studio.add_mesh_part(model, objects[part], box, ident, role, label)
        ident += 1
    settings.find("plate/metadata[@key='plater_name']").set("value", "R30 DFRobot hinge fit · A1 mini PETG")
    members[settings_name] = (members[settings_name][0], ET.tostring(settings, encoding="utf-8", xml_declaration=True))
    members[model_name] = (members[model_name][0], ET.tostring(model, encoding="utf-8", xml_declaration=True))
    with ZipFile(layout, "w", ZIP_DEFLATED) as archive:
        for info, content in members.values():
            archive.writestr(info, content)

    for folder in ("tmp", "data", "profile-home/Library/Preferences"):
        (scratch / folder).mkdir(parents=True, exist_ok=True)
    target = scratch / f"{LABEL}.gcode.3mf"
    env = {**os.environ, "TMPDIR": str(scratch / "tmp"), "CFFIXED_USER_HOME": str(scratch / "profile-home")}
    cmd = [str(studio.BAMBU), "--datadir", str(scratch / "data"), "--debug", "2",
           "--orient", "0", "--arrange", "0", "--slice", "0", "--export-3mf", target.name,
           "--outputdir", str(scratch), str(layout)]
    with (scratch / "slice.log").open("w") as log:
        subprocess.run(cmd, cwd=scratch, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=150, check=True)
    result = json.loads((scratch / "result.json").read_text())
    assert result["return_code"] == 0
    studio.restore_registration(target, config)
    report = {
        "commands": studio.command_audit(target, config),
        "warnings": [plate["warning_message"] for plate in result["sliced_plates"] if plate.get("warning_message")],
        "archive_warnings": studio.slice_info_warnings(target),
        "build_list": parts, "plate_extents_mm": extents, "anchors": anchor_report,
        "supports": support_boxes, "physical_fit_verified": False,
        "layout_sha256": old.sha(layout), "archive_sha256": old.sha(target),
    }
    (scratch / "print-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Slice warnings", report["warnings"], report["archive_warnings"], flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=HERE)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--support-boxes", type=Path)
    parser.add_argument("--hardware", type=Path)
    args = parser.parse_args()
    slice_plate(args.source.resolve(), args.scratch.resolve(),
                json.loads(args.support_boxes.read_text()) if args.support_boxes else (), args.hardware)
