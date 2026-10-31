#!/usr/bin/env python3
"""Copy the wand's canonical sources from a private working directory into this repository.

The device code and bridge are copied byte for byte. The receiver's entry point is copied with
one documented change: the installed build pins one Puck's CoreBluetooth identifier and advertised
name, so the public copy reads them from device.json instead. Run with the directory that holds the
private originals (it is never recorded):

    python3 scripts/import_private.py --from /path/to/private/outputs

The script refuses to write if a sanitising anchor is missing or a private value would survive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, REPOSITORY, DOCS
LOCK = ROOT / "data" / "import.lock.json"

# private name -> public path, transform name
FILES = {
    "wand-mouse-prototype.js": ("device/wand-mouse-prototype.js", "verbatim"),
    "wand-mode-bridge.js": ("device/wand-mode-bridge.js", "verbatim"),
    "wand-power-policy.js": ("device/wand-power-policy.js", "verbatim"),
    "wand-startup.js": ("device/wand-startup.js", "verbatim"),
    "ble_hid_mouse.js": ("device/modules/ble_hid_mouse.js", "verbatim"),
    "wand-mac-receiver.swift": ("receiver/Sources/main.swift", "receiver"),
    "wand-control-transport.swift": ("receiver/Sources/WandControlTransport.swift", "verbatim"),
    "wand-context-listener.swift": ("receiver/Sources/WandContextListener.swift", "verbatim"),
    "wand-recording-state.swift": ("receiver/Sources/WandRecordingState.swift", "verbatim"),
    "wand-review-trace.swift": ("receiver/Sources/WandReviewTrace.swift", "verbatim"),
    "wand-pointer-control.swift": ("receiver/Sources/WandPointerControl.swift", "verbatim"),
    "wand-calibration.swift": ("receiver/Sources/WandCalibration.swift", "verbatim"),
    "wand-uart.swift": ("receiver/Sources/WandUART.swift", "verbatim"),
    "wand-sense-update.swift": ("receiver/Sources/WandSenseUpdate.swift", "verbatim"),
    "wand-receiver-sense-update.swift": ("receiver/Sources/WandReceiverSenseUpdate.swift", "verbatim"),
    "wand-sense-link.swift": ("receiver/Sources/WandSenseLink.swift", "verbatim"),
    "wand-sense-protocol.swift": ("receiver/Sources/WandSenseProtocol.swift", "verbatim"),
    "wand-receiver-sense.swift": ("receiver/Sources/WandReceiverSense.swift", "verbatim"),
    "wand-receiver-actions.swift": ("receiver/Sources/WandReceiverActions.swift", "verbatim"),
    # Publish the complete compiled Sense program from the same checked snapshot.
    "sense/wand_sense.ino": ("device/sense/wand_sense/wand_sense.ino", "verbatim"),
    "sense/wand_time.h": ("device/sense/wand_sense/wand_time.h", "verbatim"),
    "sense/wand_merge.h": ("device/sense/wand_sense/wand_merge.h", "verbatim"),
    "sense/wand_light.h": ("device/sense/wand_sense/wand_light.h", "verbatim"),
    "sense/wand_update.h": ("device/sense/wand_sense/wand_update.h", "verbatim"),
    "sense/wand_usb_output.h": ("device/sense/wand_sense/wand_usb_output.h", "verbatim"),
    "sense/wand_ble_output.h": ("device/sense/wand_sense/wand_ble_output.h", "verbatim"),
    "Wand Receiver.app/Contents/Info.plist": ("receiver/Info.plist", "verbatim"),
}

# The Nordic UART and legacy DFU service/characteristic UUIDs are public protocols, not device identity.
PUBLIC_UUIDS = {
    "6E400001-B5A3-F393-E0A9-E50E24DCCA9E",
    "6E400002-B5A3-F393-E0A9-E50E24DCCA9E",
    "6E400003-B5A3-F393-E0A9-E50E24DCCA9E",
    "00001530-1212-EFDE-1523-785FEABCD123",
    "00001531-1212-EFDE-1523-785FEABCD123",
    "00001532-1212-EFDE-1523-785FEABCD123",
}
UUID_PATTERN = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}")
PRIVATE_PATTERNS = [
    re.compile(r"/Users/[^/\s\"']+"),
    re.compile(r"/private/(?:tmp|var)/"),
    re.compile(r"puck\.js [0-9a-f]{4}\b", re.IGNORECASE),
    re.compile(r"\b(?:gh[pousr]_|sk-)[A-Za-z0-9_-]{16,}"),
]


def sanitize_receiver(text: str) -> str:
    # A previously imported entry point can be the canonical source for a
    # receiver-only update. Accept the complete public configuration block;
    # incomplete migrations still hit the strict one-match guards below.
    public_anchors = (
        '    let deviceSettings = WandDeviceConfiguration.load(from: support.appendingPathComponent("device.json"))',
        "    var target: UUID? { deviceSettings.identifier }",
        "if let target, let p = manager.retrievePeripherals(withIdentifiers: [target]).first { begin(p) }",
        "guard p.identifier == target || deviceSettings.matches(name: name) else { return }",
        'guard !CommandLine.arguments.contains("--permissions-only"), deviceSettings.isConfigured, AXIsProcessTrusted(),',
    )
    if all(text.count(anchor) == 1 for anchor in public_anchors):
        return text
    replacements = [
        (
            re.compile(r'    let target = UUID\(uuidString: "[0-9A-Fa-f-]{36}"\)!\n'),
            "    // Public source: the installed build pinned one Puck here. Set yours in device.json\n"
            "    // (see BUILDING.md); the identifier is optional and only skips scanning.\n"
            '    let deviceSettings = WandDeviceConfiguration.load(from: support.appendingPathComponent("device.json"))\n'
            "    var target: UUID? { deviceSettings.identifier }\n",
        ),
        (
            re.compile(r"if let p = manager\.retrievePeripherals\(withIdentifiers: \[target\]\)\.first \{ begin\(p\) \}"),
            "if let target, let p = manager.retrievePeripherals(withIdentifiers: [target]).first { begin(p) }",
        ),
        (
            re.compile(r'guard p\.identifier == target \|\| name\.lowercased\(\) == "[^"]+" else \{ return \}'),
            "guard p.identifier == target || deviceSettings.matches(name: name) else { return }",
        ),
        (
            re.compile(r'guard !CommandLine\.arguments\.contains\("--permissions-only"\), AXIsProcessTrusted\(\),'),
            'guard !CommandLine.arguments.contains("--permissions-only"), deviceSettings.isConfigured, AXIsProcessTrusted(),',
        ),
    ]
    for pattern, replacement in replacements:
        text, count = pattern.subn(lambda _match: replacement, text)
        if count != 1:
            raise SystemExit(f"Receiver anchor changed; update the sanitiser: {pattern.pattern}")
    return text


def leaks(text: str) -> list[str]:
    found = [f"UUID {value}" for value in UUID_PATTERN.findall(text) if value.upper() not in PUBLIC_UUIDS]
    found += [f"pattern {pattern.pattern}" for pattern in PRIVATE_PATTERNS if pattern.search(text)]
    return found


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", required=True, type=Path, help="Private directory holding the originals")
    parser.add_argument("--check", action="store_true", help="Report differences without writing")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    lock: dict[str, dict[str, str]] = {}
    changed: list[str] = []
    for private_name, (public_name, transform) in FILES.items():
        original = (source / private_name).read_bytes()
        text = original.decode("utf-8")
        public_text = sanitize_receiver(text) if transform == "receiver" else text
        problems = leaks(public_text)
        if problems:
            raise SystemExit(f"{private_name} still contains private values: {', '.join(problems)}")
        public_bytes = public_text.encode("utf-8")
        target = ROOT / public_name
        if not target.exists() or target.read_bytes() != public_bytes:
            changed.append(public_name)
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(public_bytes)
        lock[public_name] = {
            "importedFrom": private_name,
            "transform": transform,
            "originalSha256": sha256(original),
            "publicSha256": sha256(public_bytes),
        }
    payload = json.dumps({"schemaVersion": 1, "files": lock}, indent=2) + "\n"
    if not LOCK.exists() or LOCK.read_text() != payload:
        changed.append(str(LOCK.relative_to(ROOT)))
        if not args.check:
            LOCK.write_text(payload)
    if args.check:
        print("Up to date" if not changed else "Would change: " + ", ".join(changed))
        return 1 if changed else 0
    print("Imported" if changed else "Already current", *(f"\n  {name}" for name in changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
