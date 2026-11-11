#!/usr/bin/env python3
"""Compose the current assembly BOM as one isolated A1 mini plate."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BOM = "complete-assembly.json"
DEFAULT_PROFILE = "Generic PETG @BBL A1M"
FLASHFORGE_PROFILE = "Flashforge HS PETG Metallic"
FLASHFORGE_GUIDE = "https://uk.flashforge.com/products/hs-petg-metallic"
FLASHFORGE_SETTINGS = {
    "nozzle_temperature": ["250"],
    "nozzle_temperature_initial_layer": ["250"],
    "textured_plate_temp": ["60"],
    "textured_plate_temp_initial_layer": ["60"],
}
MODEL_SETTINGS = "Metadata/model_settings.config"
SOURCE_SUFFIX = "-SOURCE-REQUIRES-PREPARATION.stl"
PAD_SUFFIX = "-ANCHOR-REMOVE-AFTER-PRINT.stl"
KEY = "Key_Carrier"
BRACKET = "DFRobot_Hole_Bracket"
CLIPS = ("DFR0030_Post_Clip", "DFR0030_Post_Clip_2")
LOCAL_PADS = (KEY, BRACKET, *CLIPS)
INHERITED_PADS = ("Battery_Holder", "XIAO_Rod_Holder", "Cable_Clip_12_Wire")
OUTER_BRIM = ("Battery_End_Door", "XIAO_Near_Keeper", "Battery_Spacer_0p4mm_Patterned")
BRIM_WIDTH = 3
BRIM_GAP = .15
ORIGINS = {
    KEY: (24, 112),
    BRACKET: (98, 102),
    CLIPS[0]: (107, 67),
    CLIPS[1]: (138, 67),
    "XIAO_Rod_Holder": (125, 129),
    "XIAO_Near_Keeper": (70, 83),
    "Battery_Holder": (25, 66),
    "Battery_End_Door": (53, 24),
    "Battery_Spacer_0p4mm_Patterned": (18, 24),
    "Cable_Clip_12_Wire": (73, 56),
}


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def sources(source):
    """Resolve the exact mesh and recipe provenance without loading a CAD runtime."""
    bom = read_json(source / BOM)
    selected = {}
    manifests = {}
    for group, spec in bom["groups"].items():
        directory = (source / spec["directory"]).resolve()
        exports = directory / spec.get("exports", "exports")
        manifest = exports / "manifest.json"
        if manifest not in manifests:
            manifests[manifest] = read_json(manifest) if manifest.is_file() else None
        data = manifests[manifest]
        for name in spec["parts"]:
            if name in selected:
                raise ValueError(f"Duplicate plate part {name}")
            selected[name] = {
                "group": group,
                "directory": spec["directory"],
                "exports": spec.get("exports", "exports"),
                "path": exports / f"{name}{SOURCE_SUFFIX}",
                "record": data["parts"][name] if data else None,
            }
    if set(selected) != set(ORIGINS):
        raise ValueError(f"Plate placements and BOM differ: {set(selected) ^ set(ORIGINS)}")
    return selected


def describe(selected):
    provenance = {}
    for name, item in selected.items():
        record, path = item["record"], item["path"]
        actual = digest(path) if path.is_file() else None
        expected = record["stl_sha256"] if record else None
        if actual is not None and actual != expected:
            raise ValueError(f"Source mesh differs from manifest for {name}")
        provenance[name] = {
            **{key: item[key] for key in ("group", "directory", "exports")},
            "source_filename": path.name,
            "source_sha256": actual,
            "status": "verified" if actual else "pending CAD export",
            "volume_mm3": record.get("volume_mm3", record.get("geometry_checks", {}).get("patterned_volume_mm3")) if record else None,
            "print_to_assembly": record.get("print_to_assembly") if record else None,
            "adhesion": "tear-off pad" if name in (*LOCAL_PADS, *INHERITED_PADS) else "outer brim",
        }
    return provenance


def stage_parts(selected, exports, old, anchors20, mf):
    """Keep the previous revisions immutable and generate ties for new meshes."""
    exports.mkdir(parents=True)
    records = {}
    anchors = {}
    for name, item in selected.items():
        path = item["path"]
        if not path.is_file() or not item["record"]:
            raise ValueError(f"Export {name} before preparing the full plate")
        staged = exports / path.name
        shutil.copyfile(path, staged)
        if digest(staged) != item["record"]["stl_sha256"]:
            raise ValueError(f"Source mesh changed while staging {name}")
        record = dict(item["record"])
        if "assembly_bounds_mm" in record:
            record["bounds_mm"] = record["assembly_bounds_mm"]
        records[name] = record
        if name in INHERITED_PADS:
            anchor = path.with_name(f"{name}{PAD_SUFFIX}")
            receipt = read_json(path.parent / "anchors.json")["parts"][name]
            staged = exports / anchor.name
            shutil.copyfile(anchor, staged)
            if digest(staged) != receipt["stl_sha256"]:
                raise ValueError(f"Retained pads differ from checked source for {name}")
            anchors[name] = receipt

    manifest = {"parts": records, "plate_parts": list(records)}
    (exports / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    anchors20.OUT = exports
    solid, _, _, _, key_receipt = anchors20.anchor(KEY)
    key_body = old.read(exports / f"{KEY}{SOURCE_SUFFIX}")
    assert len(solid.decompose()) == 4
    assert all((piece ^ key_body).volume() > .04 for piece in solid.decompose())
    for tie in key_receipt["tie_sites"]:
        x, y = tie["site_print_xy"]
        nx, ny = tie["outward"]
        assert nx == 0 and abs(ny) == 1
        y0, y1 = sorted((y + ny * .45, y + ny * .95))
        assert (key_body ^ old.box(x - 1.5, x + 1.5, y0, y1, .45, 6.)).volume() < .01
    anchors[KEY] = write_pads(exports, KEY, solid, old, key_receipt)

    # Keep tear-off ties outside the bracket's board seat and the post clip jaws.
    bracket = old.read(exports / f"{BRACKET}{SOURCE_SUFFIX}")
    first = bracket.slice(.1)
    left_tip = first ^ mf.CrossSection.square((3., 50.)).translate((0., -10.))
    assert not left_tip.is_empty(), "Bracket print orientation no longer exposes its front rail"
    bounds = left_tip.bounds()
    y = (bounds[1] + bounds[3]) / 2
    left = mf.CrossSection.circle(2.4, 48).translate((-3.4, y))
    left += mf.CrossSection.square((1.36, 1.)).translate((-1.22, y - .5))
    right = left.mirror((1., 0.)).translate((bracket.bounding_box()[3], 0.))
    overlaps = [(side ^ first).area() for side in (left, right)]
    assert min(overlaps) > .03, overlaps
    anchors[BRACKET] = write_pads(exports, BRACKET, mf.Manifold.extrude(left + right, .4), old,
                                  {"tie_overlap_at_first_layer_mm2": overlaps})
    for name in CLIPS:
        clip = old.read(exports / f"{name}{SOURCE_SUFFIX}")
        x0, y0, _, x1, _, _ = clip.bounding_box()
        x = (x0 + x1) / 2
        pad = mf.CrossSection.circle(2.4, 48).translate((x, y0 - 3.4))
        pad += mf.CrossSection.square((1., 1.32)).translate((x - .5, y0 - 1.2))
        overlap = (pad ^ clip.slice(.1)).area()
        assert overlap > .03, (name, overlap)
        anchors[name] = write_pads(exports, name, mf.Manifold.extrude(pad, .4), old,
                                   {"tie_overlap_at_first_layer_mm2": [overlap]})
    (exports / "anchors.json").write_text(json.dumps({"parts": anchors}, indent=2) + "\n")
    return manifest, anchors


def write_pads(exports, name, solid, old, receipt):
    path = exports / f"{name}{PAD_SUFFIX}"
    old.mesh(solid).export(path)
    return {**receipt, "stl_sha256": digest(path)}


def configure_layout(path, plate_name):
    with ZipFile(path) as archive:
        files = {item.filename: (item, archive.read(item)) for item in archive.infolist()}
    model = ET.fromstring(files[MODEL_SETTINGS][1])
    model.find("plate/metadata[@key='plater_name']").set("value", plate_name)
    for obj in model.findall("object"):
        fields = {entry.get("key"): entry for entry in obj.findall("metadata")}
        name = fields["name"].get("value")
        overrides = {"wall_generator": "arachne"} if name in LOCAL_PADS else {}
        if name in OUTER_BRIM:
            overrides.update(brim_type="outer_only", brim_width=str(BRIM_WIDTH), brim_object_gap=str(BRIM_GAP))
        for key, value in overrides.items():
            item = fields.get(key)
            if item is None:
                item = ET.SubElement(obj, "metadata", key=key)
            item.set("value", value)
    files[MODEL_SETTINGS] = (files[MODEL_SETTINGS][0], ET.tostring(model, encoding="utf-8", xml_declaration=True))
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for item, content in files.values():
            archive.writestr(item, content)


def reserve_clearances(extents):
    """Check material envelopes, including the specified brims, before slicing."""
    material = {}
    for name, (lo, hi) in extents.items():
        border = BRIM_WIDTH + BRIM_GAP if name in OUTER_BRIM else 0.
        xy = [[lo[0] - border, lo[1] - border], [hi[0] + border, hi[1] + border]]
        assert min(xy[0]) >= 5 and max(xy[1]) <= 175, (name, xy)
        for other, (a, b) in material.items():
            assert any(b[k] + 3 <= xy[0][k] or xy[1][k] + 3 <= a[k] for k in range(2)), (name, other)
        material[name] = xy
    return material


def build(source, scratch, profile, do_slice, profile_selected=False):
    import manifold3d as mf

    sys.path.insert(0, str(source.parent / "carbon-rod-holders-r28-dfrobot-touch"))
    import holder28  # sets up the established per-revision imports
    import anchors20
    import project22

    selected = sources(source)
    provenance = describe(selected)
    old, studio = project22.holder, project22.studio.p19
    model, anchors = stage_parts(selected, scratch / "build-source" / "exports", old, anchors20, mf)
    base_profile = DEFAULT_PROFILE if profile == FLASHFORGE_PROFILE else profile
    print_settings = {
        **old.P["print"], "filament": base_profile,
        "local_recipe": {
            **old.P["print"]["local_recipe"],
            "Key_Carrier_bands_mm": old.key_carrier_bands(),
            "Battery_Holder_bands_mm": old.LOCAL["print"]["local_recipe"]["Battery_Holder_bands_mm"],
        },
    }
    studio.h = SimpleNamespace(
        PLATE=tuple(selected), ANCHORED=tuple(anchors), HERE=scratch / "build-source",
        P={"print": print_settings}, LOCAL=old.LOCAL, base=old.base, sha=old.sha,
    )
    studio.ORIGINS = ORIGINS
    filament = studio.resolve("filament", base_profile)
    if print_settings["printer"] not in filament.get("compatible_printers", []):
        raise ValueError(f"{profile} is not registered for {print_settings['printer']}")
    config = studio.settings()
    config["filament_ids"] = [filament["filament_id"]]
    if profile == FLASHFORGE_PROFILE:
        # Register the four changes in the existing filament slot so that reopening
        # the project retains these temperatures rather than inheriting 255/70.
        config.update(FLASHFORGE_SETTINGS)
        diff = config["different_settings_to_system"]
        diff[1] = ";".join(sorted(set(filter(None, diff[1].split(";"))) | set(FLASHFORGE_SETTINGS)))
    revision = read_json(source / BOM)["revision"].upper()
    label = f"{revision}-Complete-A1-mini-{filament['filament_type'][0]}"
    layout = scratch / f"{label}-layout.3mf"
    extents, bands = studio.layout(layout, model, config)
    configure_layout(layout, f"Magic Wand {revision} complete assembly · A1 mini {filament['filament_type'][0]}")
    report = {
        "build_list": list(selected), "source_parts": provenance, "bom_sha256": digest(source / BOM),
        "generator_sha256": digest(Path(__file__)),
        "layout_sha256": digest(layout), "anchors": anchors,
        "plate_extents_mm": extents, "material_bounds_xy_mm": reserve_clearances(extents),
        "slow_bands_mm": bands, "filament_profile": profile,
        "profile_explicitly_selected": profile_selected,
        "profile_base": base_profile,
        "filament_reference": FLASHFORGE_GUIDE if profile == FLASHFORGE_PROFILE else None,
        "effective_filament_settings": {key: config.get(key) for key in
            (*FLASHFORGE_SETTINGS, "filament_max_volumetric_speed")},
        "physical_fit_verified": False,
    }
    if do_slice:
        for folder in ("tmp", "data", "profile-home/Library/Preferences"):
            (scratch / folder).mkdir(parents=True, exist_ok=True)
        target = scratch / f"{label}.gcode.3mf"
        home = scratch / "profile-home"
        env = {**os.environ, "TMPDIR": str(scratch / "tmp"), "CFFIXED_USER_HOME": str(home)}
        args = [str(studio.BAMBU), "--datadir", str(scratch / "data"), "--debug", "2",
                "--orient", "0", "--arrange", "0", "--slice", "0", "--export-3mf", target.name,
                "--outputdir", str(scratch), str(layout)]
        with (scratch / "slice.log").open("w") as log:
            subprocess.run(args, cwd=scratch, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180, check=True)
        result = read_json(scratch / "result.json")
        assert result["return_code"] == 0
        plate, = result["sliced_plates"]
        assert {item["name"] for item in plate["objects"]} == set(selected)
        studio.restore_registration(target, config)
        report.update(archive_sha256=digest(target), commands=studio.command_audit(target, config),
                      estimate_seconds=round(plate["total_predication"]),
                      filament_g=round(sum(item["total_used_g"] for item in plate["filaments"]), 2),
                      warnings=[plate["warning_message"]] if plate.get("warning_message") else [],
                      archive_warnings=studio.slice_info_warnings(target))
    (scratch / "print-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("build_list", "filament_profile", "layout_sha256")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=HERE)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--provenance", action="store_true")
    parser.add_argument("--filament-profile")
    parser.add_argument("--slice", action="store_true")
    args = parser.parse_args()
    if args.provenance:
        print(json.dumps(describe(sources(args.source.resolve())), indent=2))
    else:
        if args.scratch is None:
            parser.error("--scratch is required to build a project")
        if args.slice and not args.filament_profile:
            parser.error("--slice requires the selected --filament-profile")
        args.scratch.mkdir(parents=True, exist_ok=True)
        build(args.source.resolve(), args.scratch.resolve(), args.filament_profile or DEFAULT_PROFILE, args.slice, bool(args.filament_profile))
