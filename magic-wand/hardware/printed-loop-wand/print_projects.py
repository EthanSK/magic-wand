#!/usr/bin/env python3
"""Build the shared Bambu projects from canonical STLs, or verify their freshness."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
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
FILES = {"spiral": "tapered-double-helix.3mf", "smooth": "tapered-smooth.3mf"}


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
        plates = [{m.attrib["key"]: m.attrib["value"] for m in p.findall("metadata")}
                  for p in ET.fromstring(archive.read("Metadata/slice_info.config")).findall("plate")]
        assert len(plates) == 1 and plates[0]["outside"] == "false"
        return {"sha256": sha(path), "seconds": int(plates[0]["prediction"]),
                "grams": float(plates[0]["weight"]), "parts": 4}


def check() -> None:
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["inputs"] == inputs(), "Print projects are stale; run print_projects.py"
    for style, filename in FILES.items():
        assert receipt["projects"][style] == inspect_project(OUT / filename), filename
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
            part_names = cad["assemblies"][f"tapered-xiao-{style}"]["parts"]
            target = temp / filename
            command = [executable, "--datadir", str(temp / "bambu"), "--debug", "2", "--load-settings",
                       str(SETTINGS / "machine.json") + ";" + str(SETTINGS / "process.json"),
                       "--load-filaments", str(SETTINGS / "filament.json"), "--orient", "0", "--arrange", "1",
                       "--slice", "0", "--export-3mf", str(target)]
            command += [str(EXPORTS / f"{part}.stl") for part in part_names]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout[-5000:])
            with zipfile.ZipFile(target) as archive:
                entries = [(i, archive.read(i)) for i in archive.infolist()]
                config = json.loads(archive.read("Metadata/project_settings.config"))
            # Bambu otherwise discards CLI support/brim overrides when the project opens.
            keys = {"enable_support", "support_type", "support_style", "support_threshold_angle",
                    "support_on_build_plate_only", "brim_type", "brim_width", "brim_object_gap"}
            changed = config.get("different_settings_to_system", ["", "", ""])
            changed += [""] * max(0, 3 - len(changed))
            changed[0] = ";".join(sorted(keys | set(filter(None, changed[0].split(";")))))
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
