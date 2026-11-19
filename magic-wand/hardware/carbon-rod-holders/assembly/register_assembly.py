"""Register an exported revision in the shared assembly viewer."""

import json
from pathlib import Path
import os
import hashlib
import subprocess
from tempfile import NamedTemporaryFile


def write_json(path: Path, data: dict) -> None:
    """A viewer fetching during regeneration sees a complete recipe."""
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(json.dumps(data, indent=2) + "\n")
            stream.close()
            temporary.chmod(0o644)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def full_length_rods(guide: dict, directory: Path) -> dict:
    """Keep the complete purchased tube in new offline guides and registered revisions."""
    shared = Path(__file__).resolve().parent
    stock = shared.parent / "exports/carbon-stock-tube.stl"
    relative = os.path.relpath(stock, directory)
    rods = [module["actors"]["rod"] for module in guide["modules"].values() if "rod" in module["actors"]]
    if all(record.get("file") == relative for record in rods):
        return guide
    old_files = {record["file"] for record in rods if "file" in record}
    converted = subprocess.run(["node", str(shared / "export-stock-guide.mjs"), relative],
                               input=json.dumps(guide), capture_output=True, text=True, check=True)
    result = json.loads(converted.stdout)
    hashes = result.get("sources", {}).get("meshes_sha256")
    if hashes is not None:
        retained = {actor.get("file") for module in result["modules"].values() for actor in module["actors"].values()}
        for name in old_files - retained:
            hashes.pop(name, None)
        hashes[relative] = hashlib.sha256(stock.read_bytes()).hexdigest()
    return result


def register_assembly(guide: Path, revision: str, label: str, *,
                      make_current: bool = False, helper: Path | None = None,
                      group_keys: bool = False) -> None:
    directory = Path(__file__).resolve().parent
    if make_current:
        source = json.loads(guide.read_text())
        converted = full_length_rods(source, guide.parent.resolve())
        if converted is not source:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=guide.parent, delete=False) as stream:
                json.dump(converted, stream, separators=(",", ":"), allow_nan=False)
                stream.write("\n")
                staged = Path(stream.name)
            staged.chmod(0o644)
            staged.replace(guide)
    catalog_file = directory / "catalog.json"
    before = catalog_file.read_text()
    catalog = json.loads(before)
    version = next((item for item in catalog["versions"] if item["id"] == revision), None)
    if version is None:
        version = {"id": revision}
        catalog["versions"].insert(0, version)
    version.update(label=label, guide=os.path.relpath(guide.resolve(strict=True), directory))
    if group_keys:
        version["groupKeys"] = True
    if helper is not None:
        version["helper"] = os.path.relpath(helper.resolve(strict=True), directory)
    if make_current:
        catalog["current"] = revision
    if json.loads(before) != catalog:
        write_json(catalog_file, catalog)
