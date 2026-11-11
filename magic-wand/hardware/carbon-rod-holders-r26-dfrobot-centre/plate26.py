#!/usr/bin/env python3
"""Slice the matched DFR0030 parts with the A1 mini textured-plate PETG recipe."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import trimesh

import holder26 as d
import project22
import project23

LABEL = "R26-DFRobot-A1-mini-PETG"


def carrier_pads():
    """Re-use the verified narrow ties on the identical rear contact face."""
    source = d.h.R22 / "exports"
    manifest = json.loads((d.OUT / "manifest.json").read_text())
    before = json.loads((source / "manifest.json").read_text())["parts"][d.CARRIER]
    transform = np.linalg.inv(manifest["parts"][d.CARRIER]["print_to_assembly"]) @ before["print_to_assembly"]
    normal = f"{d.CARRIER}-SOURCE-REQUIRES-PREPARATION.stl"
    file = f"{d.CARRIER}-ANCHOR-REMOVE-AFTER-PRINT.stl"
    pads_at_contact = d.h.h22.read(source / file).transform(transform[:3, :])
    earlier = d.h.h22.read(source / normal).transform(transform[:3, :]) ^ pads_at_contact
    current = d.h.h22.read(d.OUT / normal) ^ pads_at_contact
    difference = (earlier - current).volume() + (current - earlier).volume()
    assert difference < .02 and all((tie ^ current).volume() > .04 for tie in pads_at_contact.decompose()), difference
    pads = trimesh.load_mesh(source / file)
    pads.apply_transform(transform)
    pads.export(d.OUT / file)
    d.save_json("anchors.json", {"parts": {d.CARRIER: {
        "stl_sha256": d.h.sha(d.OUT / file), "source_sha256": d.h.sha(source / file),
        "pad_transform": transform.tolist(), "contact_drift_mm3": round(difference, 6),
    }}})
    return manifest, transform


def build(scratch):
    manifest, pad_transform = carrier_pads()
    old = project22.holder
    project22.holder = SimpleNamespace(
        PLATE=d.PARTS, ANCHORED=(d.CARRIER,), HERE=d.HERE,
        R19=old.R19, R20=old.R20, P=old.P, LOCAL=old.LOCAL,
        base=old.base, sha=old.sha, key_carrier_bands=old.key_carrier_bands,
    )
    project22.LABEL = LABEL
    project22.PLATE_NAME = "Magic Wand R26 DFRobot centre click · first fit"
    project22.ORIGINS = {d.CARRIER: (24, 112), d.PADDLE: (98, 102), d.KEEPER: (101, 57)}
    project22.OBJECT_WALL_GENERATORS = {d.CARRIER: "arachne", d.PADDLE: "arachne"}
    project22.FILL_BOUNDS = [tuple(map(tuple, np.asarray(bounds) + pad_transform[:3, 3]))
                             for bounds in project22.FILL_BOUNDS]
    previous_configure = project22.configure_layout

    def configure(path):
        previous_configure(path)
        name = project22.MODEL_SETTINGS
        with ZipFile(path) as archive:
            members = {item.filename: (item, archive.read(item)) for item in archive.infolist()}
        tree = ET.fromstring(members[name][1])
        for obj in tree.findall("object"):
            fields = {entry.get("key"): entry for entry in obj.findall("metadata")}
            if fields["name"].get("value") == d.CARRIER:
                continue
            options = {**project23.FLAT_BRIM, "brim_width": "4"}
            if fields["name"].get("value") == d.PADDLE:
                options.update(project23.KEY_SUPPORT)
                add_paddle_blockers(members, obj, manifest)
            for key, value in options.items():
                field = fields.get(key)
                if field is None:
                    field = ET.SubElement(obj, "metadata", key=key)
                field.set("value", value)
        members[name] = (members[name][0], ET.tostring(tree, encoding="utf-8", xml_declaration=True))
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            for item, data in members.values():
                archive.writestr(item, data)

    project22.configure_layout = configure
    project22.build(scratch, True)
    receipt = d.OUT / f"{LABEL}-print-checks.json"
    report = json.loads(receipt.read_text())
    report["trial_generator_sha256"] = d.h.sha(__file__)
    report["adhesion_policy"] = ("The key carrier uses the verified rear pads and narrow ties. "
                                 "The paddle and keeper use 4 mm outer-only brims. "
                                 "The paddle allows build-plate-only tree support outside its openings.")
    receipt.write_text(json.dumps(report, indent=2) + "\n")


def add_paddle_blockers(members, obj, manifest):
    studio = project22.studio.p19
    filename = "3D/3dmodel.model"
    model = ET.fromstring(members[filename][1])
    resources = model.find(studio.tag("resources"))
    first = 1 + max(int(item.get("id")) for item in resources.findall(studio.tag("object")))
    to_print = np.linalg.inv(manifest["parts"][d.PADDLE]["print_to_assembly"])
    y, z = d.KEEPER_PIN
    volumes = {
        "Keeper entrance": [[-5.14, -35.8, 16.92], [5.14, -24.62, 21.52]],
        "Keeper pin path": [[-8.4, y - 1.6, z - 1.35], [8.4, y + 1.24, z + 1.35]],
        "Snap hinge bores": [[-4.5, 4.8, 17.32], [4.5, 8.4, 19.75]],
    }
    for index, (title, bounds) in enumerate(volumes.items()):
        volume = trimesh.creation.box(bounds=bounds)
        volume.apply_transform(to_print)
        studio.add_mesh_part(model, obj, volume, first + index, "support_blocker", title)
    members[filename] = (members[filename][0], ET.tostring(model, encoding="utf-8", xml_declaration=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    build(parser.parse_args().scratch)
