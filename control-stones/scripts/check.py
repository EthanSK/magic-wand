"""Check source syntax and the hardware profile without contacting a device."""
import ast
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main(root=ROOT):
    for folder in ("debug", "scripts"):
        for directory, folders, files in os.walk(root / folder):
            folders[:] = [name for name in folders if name not in {".venv", "venv", "__pycache__"} and not name.endswith(".noindex")]
            for name in files:
                source = Path(directory) / name
                if source.suffix == ".py":
                    ast.parse(source.read_text(), filename=str(source.relative_to(root)))
    profile = json.loads((root / "profile.json").read_text())
    assert profile["id"] == "control-stones", "Unexpected hardware profile"
    assert (root / "firmware/imu_debug/imu_debug.ino").is_file()
    assert (root / "docs/wiring.html").is_file()
    print("Control Stones source syntax and profile passed; no hardware was contacted")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
