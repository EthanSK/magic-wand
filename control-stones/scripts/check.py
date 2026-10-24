"""Check source syntax and the hardware profile without contacting a device."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for source in ROOT.rglob("*.py"):
    ast.parse(source.read_text(), filename=str(source.relative_to(ROOT)))
profile = json.loads((ROOT / "profile.json").read_text())
assert profile["id"] == "control-stones", "Unexpected hardware profile"
assert (ROOT / "firmware/imu_debug/imu_debug.ino").is_file()
assert (ROOT / "docs/wiring.html").is_file()
print("Control Stones source syntax and profile passed; no hardware was contacted")
