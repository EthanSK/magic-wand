"""Register an exported revision in the shared assembly viewer."""

import json
from pathlib import Path
import os
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


def register_assembly(guide: Path, revision: str, label: str, *,
                      make_current: bool = False, helper: Path | None = None,
                      group_keys: bool = False) -> None:
    directory = Path(__file__).resolve().parent
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
