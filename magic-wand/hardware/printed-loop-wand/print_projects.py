#!/usr/bin/env python3
"""Build the shared Bambu projects from canonical STLs, or verify their freshness."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "magic-wand-3d-models"
SETTINGS = HERE / "print-settings"
EXPORTS = HERE / "exports"
RECEIPT = OUT / "manifest.json"
FILES = {"spiral": "tapered-double-helix.3mf", "mug": "tapered-mug-double-helix.3mf",
         "smooth": "tapered-smooth.3mf", "pair": "two-spiral-wands.3mf"}
# Explicitly retain the prepared values when Studio resolves the named base preset.
# Otherwise its default 15% infill can replace our 20% when opening a valid CLI slice.
PERSISTED_PROCESS_KEYS = {
    "layer_height", "wall_loops", "sparse_infill_density", "sparse_infill_pattern",
    "enable_support", "support_type", "support_style", "support_threshold_angle",
    "support_on_build_plate_only", "brim_type", "brim_width", "brim_object_gap",
}


def arrange_parts(names: list[str], path: Path) -> None:
    """Arrange complete wands, including duplicate shafts, with room for supports."""
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    ET.register_namespace("", ns)
    tag = lambda name: f"{{{ns}}}{name}"
    model = ET.Element(tag("model"), unit="millimeter")
    resources, build = ET.SubElement(model, tag("resources")), ET.SubElement(model, tag("build"))
    layouts = {4: [(60, 70), (150, 70), (60, 170), (150, 170)],
               8: [(45, 50), (105, 50), (165, 50), (218, 50),
                   (45, 168), (105, 168), (165, 168), (218, 168)]}
    assert len(names) in layouts
    footprints = []
    for ident, (name, centre) in enumerate(zip(names, layouts[len(names)]), 1):
        data = (EXPORTS / f"{name}.stl").read_bytes()
        count = struct.unpack_from("<I", data, 80)[0]
        vertices, faces, ids = [], [], {}
        for t in range(count):
            points = struct.unpack_from("<9f", data, 84 + 50 * t + 12)
            face = []
            for j in range(0, 9, 3):
                point = points[j:j + 3]
                if point not in ids:
                    ids[point] = len(vertices)
                    vertices.append(point)
                face.append(ids[point])
            faces.append(face)
        obj = ET.SubElement(resources, tag("object"), id=str(ident), type="model", name=name)
        mesh = ET.SubElement(obj, tag("mesh"))
        vs, ts = ET.SubElement(mesh, tag("vertices")), ET.SubElement(mesh, tag("triangles"))
        for x, y, z in vertices:
            ET.SubElement(vs, tag("vertex"), x=str(x), y=str(y), z=str(z))
        for a, b, c in faces:
            ET.SubElement(ts, tag("triangle"), v1=str(a), v2=str(b), v3=str(c))
        lo = [min(v[k] for v in vertices) for k in range(3)]
        hi = [max(v[k] for v in vertices) for k in range(3)]
        tx, ty = [centre[k] - (lo[k] + hi[k]) / 2 for k in range(2)]
        footprint = (lo[0] + tx - 9, lo[1] + ty - 9, hi[0] + tx + 9, hi[1] + ty + 9)
        assert all(4 <= edge <= 252 for edge in footprint), f"Insufficient bed margin: {name}"
        for old in footprints:
            assert (footprint[2] <= old[0] or old[2] <= footprint[0] or
                    footprint[3] <= old[1] or old[3] <= footprint[1]), "Support clearance overlaps"
        footprints.append(footprint)
        ET.SubElement(build, tag("item"), objectid=str(ident), transform=f"1 0 0 0 1 0 0 0 1 {tx} {ty} {-lo[2]}")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        archive.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs() -> dict[str, str]:
    cad = json.loads((EXPORTS / "manifest.json").read_text())
    for name, key in (("dimensions.json", "dimensions_sha256"), ("wand_cad.py", "script_sha256")):
        if sha(HERE / name) != cad["source"][key]:
            raise ValueError("CAD exports are stale; run wand_cad.py first")
    paths = [Path(__file__), HERE / "dimensions.json", HERE / "wand_cad.py", EXPORTS / "manifest.json"]
    paths += sorted(SETTINGS.glob("*.json"))
    names = {p for aid in cad["profiles"]["tapered-xiao"]["assemblies"] for p in cad["assemblies"][aid]["parts"]}
    paths += [EXPORTS / f"{name}.stl" for name in sorted(names)]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def project_part_names(cad: dict, style: str) -> list[str]:
    # Ethan wants two whole wands, not just a second handle: duplicate both shaft
    # sections and the XIAO holder while composing from the same canonical parts.
    styles = cad["profiles"]["tapered-xiao"]["overview"] if style == "pair" else [style]
    return [part for key in styles for part in cad["assemblies"][f"tapered-xiao-{key}"]["parts"]]


def inspect_project(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        # Exported archives must not leak machine-local paths or account credentials.
        for name in archive.namelist():
            if name.endswith((".model", ".config", ".json", ".xml", ".gcode", ".rels")):
                text = archive.read(name).decode("utf8")
                if re.search(r"(?:/Users/|/Volumes/|/private/|[A-Za-z]:\\\\Users\\\\)", text):
                    raise ValueError(f"Private path in {path.name}: {name}")
                if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|BEGIN .*PRIVATE KEY)", text):
                    raise ValueError(f"Credential-like data in {path.name}: {name}")
        config = json.loads(archive.read("Metadata/project_settings.config"))
        assert config["printer_model"] == "Bambu Lab P1S"
        assert config["filament_type"] == ["PETG"]
        assert config["enable_support"] == "1"
        process = json.loads((SETTINGS / "process.json").read_text())
        registered = set(config["different_settings_to_system"][0].split(";"))
        assert PERSISTED_PROCESS_KEYS <= registered, "Prepared process overrides are missing"
        for key in PERSISTED_PROCESS_KEYS:
            assert config[key] == process[key], f"Prepared process value changed: {key}"
        plate_nodes = ET.fromstring(archive.read("Metadata/slice_info.config")).findall("plate")
        plates = [{m.attrib["key"]: m.attrib["value"] for m in p.findall("metadata")} for p in plate_nodes]
        assert len(plates) == 1 and plates[0]["outside"] == "false"
        # CLI slices omit the GUI's optional per-object slice metadata. Count the
        # actual printable build instances and resolve their names from settings.
        settings = ET.fromstring(archive.read("Metadata/model_settings.config"))
        by_id = {o.attrib["id"]: {m.attrib["key"]: m.attrib["value"]
                 for m in o.findall("metadata") if "key" in m.attrib}["name"]
                 for o in settings.findall("object")}
        ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
        items = ET.fromstring(archive.read("3D/3dmodel.model")).findall("m:build/m:item", ns)
        assert items and all(i.attrib.get("printable", "1") == "1" for i in items)
        names = sorted(by_id[i.attrib["objectid"]] for i in items)
        return {"sha256": sha(path), "seconds": int(plates[0]["prediction"]),
                "grams": float(plates[0]["weight"]), "parts": len(names), "part_names": names}


def check() -> None:
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["inputs"] == inputs(), "Print projects are stale; run print_projects.py"
    cad = json.loads((EXPORTS / "manifest.json").read_text())
    for style, filename in FILES.items():
        assert receipt["projects"][style] == inspect_project(OUT / filename), filename
        assert receipt["projects"][style]["part_names"] == sorted(project_part_names(cad, style))
    frozen = OUT / "Print-1-crossed-110mm.json"
    if frozen.exists():
        record = json.loads(frozen.read_text())
        assert sha(OUT / record["file"]) == record["sha256"], "The frozen first print changed"
    print("Shared Bambu projects match the current CAD and print settings")


def build(args) -> None:
    source = inputs()
    executable = args.bambu or shutil.which("BambuStudio") or "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
    if not Path(executable).is_file():
        raise ValueError("Bambu Studio is required; pass its executable with --bambu")
    cad = json.loads((EXPORTS / "manifest.json").read_text())
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wand-print-", suffix=".noindex", dir=args.scratch) as temp:
        temp = Path(temp)
        projects = {}
        for style, filename in FILES.items():
            part_names = project_part_names(cad, style)
            target = temp / filename
            arranged = temp / f"{style}-layout.3mf"
            arrange_parts(part_names, arranged)
            command = [executable, "--datadir", str(temp / "bambu"), "--debug", "2", "--load-settings",
                       str(SETTINGS / "machine.json") + ";" + str(SETTINGS / "process.json"),
                       "--load-filaments", str(SETTINGS / "filament.json"), "--orient", "0", "--arrange", "0",
                       "--slice", "0", "--export-3mf", str(target)]
            command += [str(arranged)]
            result = subprocess.run(command, cwd=temp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout[-5000:])
            with zipfile.ZipFile(target) as archive:
                entries = [(i, archive.read(i)) for i in archive.infolist()]
                config = json.loads(archive.read("Metadata/project_settings.config"))
            # Bambu otherwise discards CLI overrides when the project opens.
            changed = config.get("different_settings_to_system", ["", "", ""])
            changed += [""] * max(0, 3 - len(changed))
            changed[0] = ";".join(sorted(PERSISTED_PROCESS_KEYS | set(filter(None, changed[0].split(";")))))
            config["different_settings_to_system"] = changed
            clean = temp / (filename + ".clean")
            with zipfile.ZipFile(clean, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for info, blob in entries:
                    if info.filename == "Metadata/project_settings.config":
                        blob = (json.dumps(config, indent=2) + "\n").encode()
                    archive.writestr(info, blob)
            projects[style] = inspect_project(clean)
            shutil.copyfile(clean, OUT / filename)
        RECEIPT.write_text(json.dumps({"schema": 1, "inputs": source, "projects": projects}, indent=2) + "\n")
    check()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bambu", help="Bambu Studio executable")
    parser.add_argument("--scratch", type=Path, help="Parent folder for temporary slicing files")
    args = parser.parse_args()
    check() if args.check else build(args)
