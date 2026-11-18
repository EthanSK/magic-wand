"""Package the exact slice after all hardware and print checks pass."""
import hashlib
from pathlib import Path
import re
import shutil
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from audit49 import FUNCTIONAL, R48
from native48 import digest, read, write
from plate38 import recipe

source = Path(sys.argv[1])
target = Path(sys.argv[2])
archive = source / "R49-Wide-Feet.gcode.3mf"
layout = source / "R49-Wide-Feet-layout.3mf"
sha = digest(archive)
gcode_path = "Metadata/plate_1.gcode"
gates = {
    "machine-check.json": ("project_sha256", "passed"),
    "plate-clearance.json": ("archive_sha256", "passed"),
    "helper-starts.json": ("archive_sha256", None),
    "key-tab-feet.json": ("archive_sha256", "carrier_grounded"),
    "roof-comparison.json": ("archive_sha256", "within_previous_trial_envelope"),
    "key-release.json": ("archive_sha256", "passed"),
    "key-working-spaces.json": ("archive_sha256", "passed"),
    "swing-tab-removal.json": ("archive_sha256", "passed"),
    "hardware-audit/other-parts-audit.json": ("complete_archive_sha256", "passed"),
    "hardware-audit/edge-click-load-path.json": ("archive_sha256", "passed"),
    "reopen-checks.json": ("selected_archive_sha256", "actual_modifier_placements_equivalent"),
    "R49-Wide-Feet.gcode.native.json": ("archive_sha256", None),
}
if (source / "lead-tab-removal.json").is_file():
    gates["lead-tab-removal.json"] = ("archive_sha256", "passed")
for name, (key, check) in gates.items():
    row = read(source / name)
    assert row[key] == sha, name
    assert check is None or row[check], name
starts = read(source / "helper-starts.json")
assert all(not row["unrooted_actual_components"] for row in starts["owners"].values())
assert starts["first_layer_body_and_tabs"]["actual_body_components"]
reopen = read(source / "reopen-checks.json")
assert reopen["global_settings_identical"] and reopen["object_process_settings_identical"]

with ZipFile(archive) as z:
    assert z.testzip() is None
    data = z.read(gcode_path)
    checksum = z.read(gcode_path + ".md5").decode().strip().lower()
    assert hashlib.md5(data).hexdigest() == checksum
    info = ET.fromstring(z.read("Metadata/slice_info.config"))
    owners = {node.get("name") for node in info.findall("plate/object")}
    assert owners == FUNCTIONAL | {"Release_tabs", "External_cradle", "Front_pull_shelf", "Rear_pull_shelf"}
    assert not any("warn" in n.tag.lower() or "warn" in n.get("key", "").lower() for n in info.iter())
    material = {n.get("key"): n.get("value") for n in info.findall("plate/metadata")}
    preview = z.read("Metadata/plate_1.png")

source_archives = [archive, layout]
for candidate in source_archives:
    with ZipFile(candidate) as z:
        assert z.testzip() is None
        for key in z.namelist():
            if key.endswith((".model", ".config", ".xml", ".json", ".gcode")):
                assert not re.search(rb"/Users/|/Volumes/|/private/(?:tmp|var)/", z.read(key)), key
        description = ET.fromstring(z.read("3D/3dmodel.model"))
        assert all(not n.text for n in description.findall("{*}metadata[@name='DesignerUserId']"))

target.mkdir(parents=True, exist_ok=True)
for file in source_archives:
    shutil.copyfile(file, target / file.name)
for key in [*gates, "roof-strokes.json", "pad-design.json"]:
    output = target / Path(key).name
    shutil.copyfile(source / key, output)
reopen["own_final_deposition_audited"] = True
reopen["scope"] = "Reopened in the native slicer, then audited the selected G-code."
write(target / "reopen-checks.json", reopen)
(target / "plate-preview.png").write_bytes(preview)
sealed = target / "Magic-Wand-R49-All-Components-Wide-Feet-print-only.3mf"
recipe.make_print_only(target / archive.name, target).replace(sealed)
readback = read(target / "print-only.json")
with ZipFile(sealed) as z:
    assert z.read(gcode_path) == data and z.testzip() is None
    assert readback["source_sha256"] == sha
    assert readback["gcode_sha256"] == hashlib.sha256(data).hexdigest()
readback.update(file=sealed.name, sha256=digest(sealed))
write(target / "print-only.json", readback)
write(target / "verification.json", {
    "selected_archive_sha256": sha,
    "editable_layout_sha256": digest(layout),
    "r48_source_layout_sha256": digest(R48 / "exports/wide-pad-retry/R48-Wide-Pads-layout.3mf"),
    "print_only_sha256": digest(sealed),
    "functional_parts": sorted(FUNCTIONAL),
    "estimated_seconds": int(material["prediction"]),
    "grams": float(material["weight"]),
    "smooth_timelapse": material["timelapse_type"] == "1",
    "nominal_foot_design": "Separate interleaved feet supporting the original functional components",
    "verified_digital_trial": True,
    "physical_acceptance_verified": False,
    "source_sha256": {f.name: digest(f) for f in sorted(Path(__file__).parent.glob("*.py"))},
    "file_sha256": {f.name: digest(f) for f in sorted(target.iterdir()) if f.name != "verification.json"},
})
print(sealed)
