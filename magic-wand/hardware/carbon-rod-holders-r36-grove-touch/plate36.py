"""Build the eight-part Grove revision using the checked R35 A1 mini recipe.

Run assembly36.py first, then pass an empty output directory to this script.
"""

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np

import holder36 as design
import plate35 as old

plate = old.plate
BASE_STAGE = plate.stage_parts
BASE_CONFIGURE = plate.configure_layout
ORIGINAL_BRACKET = plate.BRACKET
NAMES = {ORIGINAL_BRACKET: design.BRACKET}


def stage_parts(selected, exports, holder, anchors20, manifold):
    manifest, anchors = BASE_STAGE(selected, exports, holder, anchors20, manifold)
    from slice19 import anchor_in_project

    with ZipFile(old.PREVIOUS_PLATE) as archive:
        model = ET.fromstring(archive.read(old.MODEL))
        names = old.object_names(ET.fromstring(archive.read(plate.MODEL_SETTINGS)))
    origins = {names[item.get("objectid")]: np.asarray(item.get("transform").split()[-3:], dtype=float)
               for item in model.findall("./{*}build/{*}item")}
    prior_parts = plate.read_json(design.R35 / "exports" / "manifest.json")["parts"]
    for original, geometry in plate.read_json(old.PAD_TEST / "pad-geometry.json").items():
        name = NAMES.get(original, original)
        origin = origins[original]
        pad, _ = anchor_in_project(old.PREVIOUS_PLATE, original, origin)
        old_frame = np.asarray(prior_parts[original]["print_to_assembly"])
        new_frame = np.asarray(manifest["parts"][name]["print_to_assembly"])
        rebase = np.linalg.solve(new_frame, old_frame)
        if name == design.BRACKET:
            # Centre the narrow ties on the remaining 1.0 mm front web.
            rebase[1, 3] += .45
        pad = pad.transform(rebase[:3, :])
        model = holder.read(exports / f"{name}{plate.SOURCE_SUFFIX}")
        overlap = [(part ^ model).volume() for part in pad.decompose()]
        # Each perforated pad still has to reach its original tear-off tie.
        # The bracket's board seat moved, so verify the tie on the new mesh.
        assert min(overlap) > .035, (name, overlap)
        holes = np.asarray(geometry["plate_hole_centres_mm"]) - origin[:2] + rebase[:2, 3]
        anchors[name] = plate.write_pads(exports, name, pad, holder, {
            "tie_overlap_mm3": round(sum(overlap), 5),
            "tie_overlaps_mm3": overlap,
            "hole_centres_print_xy_mm": holes.tolist(),
            "hole_diameter_mm": geometry["hole_diameter_mm"],
            "pad_thickness_mm": geometry["pad_thickness_mm"],
        })
    (exports / "anchors.json").write_text(json.dumps({"parts": anchors}, indent=2) + "\n")
    return manifest, anchors


def configure_layout(path, plate_name):
    import project22

    BASE_CONFIGURE(path, plate_name)
    with ZipFile(old.PREVIOUS_PLATE) as archive:
        old_names = old.object_names(ET.fromstring(archive.read(plate.MODEL_SETTINGS)))
        old_model = ET.fromstring(archive.read(old.MODEL))
        ranges = ET.fromstring(archive.read(old.LAYER_RANGES))
    with ZipFile(path) as archive:
        entries = {item.filename: archive.read(item) for item in archive.infolist()}
    settings = ET.fromstring(entries[plate.MODEL_SETTINGS])
    names = old.object_names(settings)
    model = ET.fromstring(entries[old.MODEL])
    old_order = [old_names[item.get("objectid")] for item in old_model.findall("./{*}build/{*}item")]
    order = [names[item.get("objectid")] for item in model.findall("./{*}build/{*}item")]
    for part in ranges.findall("object"):
        original = old_order[int(part.get("id")) - 1]
        part.set("id", str(order.index(NAMES.get(original, original)) + 1))
    entries[old.LAYER_RANGES] = ET.tostring(ranges, encoding="utf-8", xml_declaration=True)
    old.add_connector_support(model, settings, project22.studio.p19)
    entries[old.MODEL] = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    entries[plate.MODEL_SETTINGS] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for filename, content in entries.items():
            archive.writestr(filename, content)


def build(output):
    here = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=True)
    plate.BRACKET = design.BRACKET
    plate.LOCAL_PADS = (plate.KEY, plate.BRACKET)
    plate.ORIGINS = {NAMES.get(name, name): origin for name, origin in plate.ORIGINS.items()
                     if name not in plate.CLIPS}
    # The rebased ties sit further towards the keeper in print Y.
    x, y = plate.ORIGINS[design.BRACKET]
    plate.ORIGINS[design.BRACKET] = (x, y + 4)
    plate.CLIPS = ()
    plate.stage_parts = stage_parts
    plate.configure_layout = configure_layout
    plate.build(here, output.resolve(), plate.FLASHFORGE_PROFILE, True, True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
