"""Compose the verified, retained R22 plate sources into the next plate staging directory.

The R23 builder uses the returned manifest and anchor records with the new centre
assembly. Staged links keep the R22 geometry in its original, checked location.
"""

from hashlib import sha256
from pathlib import Path
import json


RETAINED_PARTS = (
    "Battery_Holder",
    "Battery_End_Door",
    "Battery_End_Door_Easy_Trial",
    "XIAO_Rod_Holder",
    "XIAO_Near_Keeper",
    "Cable_Clip_12_Wire",
)


def retained_plate_sources(source_exports: Path, staged_exports: Path) -> tuple[dict, dict]:
    """Check and stage the six carried-forward models and their print helpers."""
    source_exports = source_exports.resolve(strict=True)
    source_manifest = source_exports / "manifest.json"
    manifest = json.loads(source_manifest.read_text())
    anchors = json.loads((source_exports / "anchors.json").read_text())
    guide = json.loads((source_exports / "assembly-guide.json").read_text())

    def digest(path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    if guide["sources"]["manifest_sha256"] != digest(source_manifest):
        raise ValueError("R22 assembly and plate manifests differ")

    parts, pads, inputs = {}, {}, []
    for name in RETAINED_PARTS:
        record = manifest["parts"][name]
        if name not in manifest["plate_parts"] or not record["watertight"] or record["body_count"] != 1:
            raise ValueError(f"Unverified R22 plate source for {name}")
        parts[name] = record
        inputs.extend((
            (source_exports / f"{name}-SOURCE-REQUIRES-PREPARATION.stl", record["stl_sha256"]),
            (source_exports / f"{name}-assembly.stl", guide["sources"]["assembly_mesh_sha256"][name]),
        ))
        if name in anchors["parts"]:
            pads[name] = anchors["parts"][name]
            inputs.append((source_exports / f"{name}-ANCHOR-REMOVE-AFTER-PRINT.stl", pads[name]["stl_sha256"]))

    # Verify the full input set before writing any links so a wrong revision cannot
    # leave a mixture of old and new parts in the plate builder's staging directory.
    for source, expected_sha in inputs:
        if digest(source) != expected_sha:
            raise ValueError(f"R22 mesh differs from its checked export: {source.name}")
    staged_exports.mkdir(parents=True, exist_ok=True)
    for source, _ in inputs:
        (staged_exports / source.name).symlink_to(source)
    return parts, pads
