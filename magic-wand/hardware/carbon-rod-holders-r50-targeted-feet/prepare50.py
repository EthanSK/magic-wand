"""Compose the nine-part plate from the checked R48 and R49 editable layouts."""
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

HARDWARE = Path(__file__).resolve().parent.parent
BASE = HARDWARE / "carbon-rod-holders-r48-edge-click/exports/wide-pad-retry/R48-Wide-Pads-layout.3mf"
WIDE = HARDWARE / "carbon-rod-holders-r49-wide-feet/exports/R49-Wide-Feet-layout.3mf"
MODEL = "3D/3dmodel.model"
SETTINGS = "Metadata/model_settings.config"
HELPERS = {"Release_tabs", "External_cradle", "Front_pull_shelf", "Rear_pull_shelf"}


def compose(output, standard_carrier_walls=True):
    with ZipFile(BASE) as small, ZipFile(WIDE) as large:
        files = {name: small.read(name) for name in small.namelist()}
        base_model = ET.fromstring(files[MODEL])
        wide_model = ET.fromstring(large.read(MODEL))
        settings = ET.fromstring(files[SETTINGS])
        wide_settings = ET.fromstring(large.read(SETTINGS))
        assert files["Metadata/project_settings.config"] == large.read("Metadata/project_settings.config")
        assert files["Metadata/layer_config_ranges.xml"] == large.read("Metadata/layer_config_ranges.xml")
    ET.register_namespace("", base_model.tag[1:].split("}")[0])
    base_resources = base_model.find("{*}resources")
    wide_resources = wide_model.find("{*}resources")
    assert ET.tostring(base_model.find("{*}build")) == ET.tostring(wide_model.find("{*}build"))
    replaced = set()
    for obj in settings.findall("object"):
        name = obj.find("metadata[@key='name']").get("value")
        if name in HELPERS:
            source = wide_settings.find(f"object[@id='{obj.get('id')}']")
            assert ET.tostring(obj) == ET.tostring(source)
            (part,) = obj.findall("part[@subtype='normal_part']")
            path = "{*}object[@id='%s']" % part.get("id")
            base_resources.remove(base_resources.find(path))
            base_resources.append(wide_resources.find(path))
            replaced.add(name)
        if name == "Key_Carrier" and standard_carrier_walls:
            # Local modifiers keep the controlled speeds at the thin joints.
            # Retain the carrier acceleration and surface finish settings.
            for speed in ("inner_wall_speed", "outer_wall_speed"):
                obj.remove(obj.find(f"metadata[@key='{speed}']"))
    assert replaced == HELPERS
    settings.find("plate/metadata[@key='plater_name']").set("value", "Magic Wand R50 targeted feet - A1 mini PETG")
    for key, tree in ((MODEL, base_model), (SETTINGS, settings)):
        files[key] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for key, data in files.items():
            archive.writestr(key, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--control", action="store_true", help="Retain the slower R48 carrier walls for a timing comparison.")
    args = parser.parse_args()
    compose(args.output, standard_carrier_walls=not args.control)
