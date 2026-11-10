#!/usr/bin/env python3
"""Build the R23 fit-trial plate from the new exports and the checked R22 parts.

Use the same R22/R20 Studio pipeline, including the PETG startup commands,
slow regions and separate Smooth timelapse tower. Run with --scratch and --slice.
"""

import argparse
import json
from pathlib import Path
from shutil import copyfile
import sys
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import trimesh

from r23_retained_plate import RETAINED_PARTS, retained_plate_sources


LABEL = "R23-A1-mini-PETG"
NEW_ORIGINS = {
    "Centre_Paddle": (15, 12),
    "Centre_Paddle_Shallow_Trial": (48, 12),
    "Centre_Paddle_Deep_Trial": (81, 12),
}
FLAT_BRIM = {"brim_type": "outer_only", "brim_width": "3", "brim_object_gap": "0.15"}
KEY_SUPPORT = {"enable_support": "1", "support_type": "tree(auto)",
               "support_on_build_plate_only": "1", "support_top_z_distance": "0.24",
               "support_critical_regions_only": "1", "support_object_xy_distance": "0.65"}


def configure_fit_trial(path: Path, configure_previous, support: bool, holder, studio, carrier_frame) -> None:
    configure_previous(path)
    with ZipFile(path) as archive:
        members = {item.filename: (item, archive.read(item)) for item in archive.infolist()}
    name = "Metadata/model_settings.config"
    model = ET.fromstring(members[name][1])
    carrier = None
    for obj in model.findall("object"):
        fields = {entry.get("key"): entry for entry in obj.findall("metadata")}
        part = fields["name"].get("value")
        if part == "Key_Carrier" and support:
            overrides = KEY_SUPPORT
            carrier = obj
        elif part in (*NEW_ORIGINS, "Battery_End_Door", "Battery_End_Door_Easy_Trial", "XIAO_Near_Keeper"):
            overrides = FLAT_BRIM
        else:
            continue
        for key, value in overrides.items():
            field = fields.get(key)
            if field is None:
                field = ET.SubElement(obj, "metadata", key=key)
            field.set("value", value)
    if carrier is not None:
        model_name = "3D/3dmodel.model"
        geometry = ET.fromstring(members[model_name][1])
        resources = geometry.find(studio.tag("resources"))
        identifier = 1 + max(int(obj.get("id")) for obj in resources.findall(studio.tag("object")))
        # Keep the paths used during assembly out of the support generator.
        # The four Choc cap volumes already printed without support on R22.
        old_spaces = holder.h22.spaces16.regions("Key_Carrier")
        blockers = {}
        for index in (0, 2, 3, 4):
            bounds = np.asarray(old_spaces[f"key_{index}_cap_travel"].bounding_box()).reshape(2, 3)
            blockers[f"Choc {index + 1} cap clearance"] = bounds + [[-.6, -.6, 0.], [.6, .6, .6]]
        hinge_y, hinge_z = holder.HG["axis_y_mm"], holder.HG["axis_z_mm"]
        blockers["Hinge pin clearance"] = [[-12.2, hinge_y - 1.6, hinge_z - 1.6],
                                            [12.2, hinge_y + 1.6, hinge_z + 1.6]]
        blockers["OP1 board and switch clearance"] = [[-6.1, holder.BOARD_FRONT - 2., holder.ZB - 4.6],
                                                        [6.1, holder.BOARD_REAR + .5, holder.PLUNGER_FREE + .7]]
        for index, (label, bounds) in enumerate(blockers.items()):
            box = trimesh.creation.box(bounds=bounds)
            box.apply_transform(np.linalg.inv(carrier_frame))
            studio.add_mesh_part(geometry, carrier, box, identifier + index, "support_blocker", label)
        members[model_name] = (members[model_name][0], ET.tostring(geometry, encoding="utf-8", xml_declaration=True))
    members[name] = (members[name][0], ET.tostring(model, encoding="utf-8", xml_declaration=True))
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for item, data in members.values():
            archive.writestr(item, data)


def stage_changed_part(name: str, record: dict, source_exports: Path, staged_exports: Path, holder) -> dict:
    """Check both exports and reconstruct the exact print-to-assembly transform."""
    assembly = source_exports / f"{name}-assembly.stl"
    normal = source_exports / f"{name}-SOURCE-REQUIRES-PREPARATION.stl"
    if holder.sha(assembly) != record["assembly_stl_sha256"] or holder.sha(normal) != record["stl_sha256"]:
        raise ValueError(f"R23 mesh differs from its manifest: {name}")

    assembly_mesh = trimesh.load_mesh(assembly)
    rotation = holder.PRINT_ROT["Key_Carrier" if name == "Key_Carrier" else "Centre_Paddle"]
    oriented = assembly_mesh.copy()
    oriented.apply_transform(rotation)
    to_print = trimesh.transformations.translation_matrix(-oriented.bounds[0]) @ rotation
    oriented.apply_translation(-oriented.bounds[0])
    written = trimesh.load_mesh(normal)
    if not assembly_mesh.is_watertight or not written.is_watertight:
        raise ValueError(f"Open R23 mesh: {name}")
    if not np.allclose(written.bounds, oriented.bounds, atol=.0002, rtol=0):
        raise ValueError(f"R23 print orientation differs from its source: {name}")
    for source in (assembly, normal):
        (staged_exports / source.name).symlink_to(source)
    return {**record, "bounds_mm": assembly_mesh.bounds.tolist(),
            "print_to_assembly": np.linalg.inv(to_print).tolist()}


def build(revision: Path, scratch: Path, do_slice: bool, support: bool) -> None:
    revision = revision.resolve(strict=True)
    sys.path.insert(0, str(revision))
    import holder23 as holder
    import project22 as previous

    scratch = scratch.resolve()
    staged_exports = scratch / "build-source" / "exports"
    staged_exports.mkdir(parents=True)
    old_exports = holder.R22 / "exports"
    new_exports = revision / "exports"
    old_manifest = json.loads((old_exports / "manifest.json").read_text())
    new_manifest = json.loads((new_exports / "manifest.json").read_text())
    old_anchors = json.loads((old_exports / "anchors.json").read_text())
    parts, anchors = retained_plate_sources(old_exports, staged_exports)
    new_parts = new_manifest["parts"]
    expected = {"Key_Carrier", *NEW_ORIGINS}
    if set(new_parts) != expected:
        raise ValueError(f"Unexpected R23 export names: {sorted(set(new_parts) ^ expected)}")
    for name, record in new_parts.items():
        parts[name] = stage_changed_part(name, record, new_exports, staged_exports, holder)

    # The new work is at the front of the carrier. Its rear face remains on the
    # bed. Check the original pad plane and print frame before reusing its pads,
    # two solid backing boxes and slow bands at the original coordinates.
    carrier = "Key_Carrier"
    if not np.allclose(parts[carrier]["print_to_assembly"],
                       old_manifest["parts"][carrier]["print_to_assembly"], atol=.0002, rtol=0):
        raise ValueError("R23 carrier changed the print frame of the R22 pads or modifiers")
    normal_file = f"{carrier}-SOURCE-REQUIRES-PREPARATION.stl"
    old_body = holder.h22.read(old_exports / normal_file)
    new_body = holder.h22.read(new_exports / normal_file)
    pad_layers = holder.box(-1, 60, -2, 30, -.1, .401)
    old_contact, new_contact = old_body ^ pad_layers, new_body ^ pad_layers
    contact_change = holder.vol(old_contact - new_contact) + holder.vol(new_contact - old_contact)
    if contact_change > .02:
        raise ValueError(f"R23 changed the pad layers by {contact_change:.4f} mm³")
    pad_file = f"{carrier}-ANCHOR-REMOVE-AFTER-PRINT.stl"
    anchors[carrier] = old_anchors["parts"][carrier]
    if holder.sha(old_exports / pad_file) != anchors[carrier]["stl_sha256"]:
        raise ValueError("R22 key carrier pad differs from its checked source")
    (staged_exports / pad_file).symlink_to(old_exports / pad_file)

    order = (carrier, *RETAINED_PARTS, *NEW_ORIGINS)
    (staged_exports / "manifest.json").write_text(json.dumps({
        **new_manifest, "parts": parts, "plate_parts": order,
        "anchored_parts": list(anchors), "retained_r22_manifest_sha256": holder.sha(old_exports / "manifest.json"),
    }, indent=2) + "\n")
    (staged_exports / "anchors.json").write_text(json.dumps({
        "parts": anchors, "source_r22_sha256": holder.sha(old_exports / "anchors.json"),
        "carrier_pad_layer_change_mm3": round(contact_change, 6),
        "physical_adhesion_or_release_verified": False,
    }, indent=2) + "\n")
    old_holder = previous.holder
    previous.holder = SimpleNamespace(
        PLATE=order, ANCHORED=tuple(anchors), HERE=staged_exports.parent,
        R19=old_holder.R19, R20=old_holder.R20, P=old_holder.P, LOCAL=old_holder.LOCAL,
        base=old_holder.base, sha=old_holder.sha, key_carrier_bands=old_holder.key_carrier_bands,
    )
    previous.ORIGINS = {**{name: previous.ORIGINS[name] for name in order if name not in NEW_ORIGINS},
                        **NEW_ORIGINS}
    previous.LABEL = LABEL
    previous.PLATE_NAME = "Magic Wand R23 centre click and keepers - A1 mini PETG"
    configure_previous = previous.configure_layout
    previous.configure_layout = lambda path: configure_fit_trial(
        path, configure_previous, support, holder, previous.studio.p19,
        np.asarray(parts[carrier]["print_to_assembly"]))
    previous.build(scratch / "studio", do_slice)

    report_file = f"{LABEL}-print-checks.json"
    report = json.loads((staged_exports / report_file).read_text())
    report["r23_generator_sha256"] = holder.sha(Path(__file__))
    report["adhesion_policy"] = (
        "The carrier, battery and XIAO holders and the cable clip have checked removable pads. "
        "The flat doors, keeper and paddles use separate 3 mm removable outer brims."
    )
    report["flat_part_brim"] = FLAT_BRIM
    report["key_carrier_support"] = KEY_SUPPORT if support else {}
    (staged_exports / report_file).write_text(json.dumps(report, indent=2) + "\n")
    deliverables = [f"{LABEL}-layout.3mf", report_file]
    if do_slice:
        deliverables.append(f"{LABEL}.gcode.3mf")
    for name in deliverables:
        copyfile(staged_exports / name, new_exports / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--slice", action="store_true")
    parser.add_argument("--support", action="store_true")
    args = parser.parse_args()
    build(args.revision, args.scratch, args.slice, args.support)
