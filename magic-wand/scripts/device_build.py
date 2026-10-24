"""Generate the wand's upload artifacts from the readable device sources.

These functions reproduce the installed build byte for byte; the runtime version and bridge
revision they compute are the identifiers the receiver and Puck report. Keep the algorithms
unchanged unless the receiver changes too: both hashes are compared on every reconnect.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, REPOSITORY, DOCS
DEVICE = ROOT / "device"
GENERATED = DEVICE / "generated"
BODY_ANCHOR = "// Adjust only"

# Stops the previous program, then makes mouse reports travel over the Bluetooth UART link.
RUNTIME_PREFIX = (
    "delete global.WAND_RUNTIME_VERSION;global.WAND_UPDATING=true;LED1.set();LED2.reset();LED3.reset(); "
    "if(global.wandPinProbe){global.wandPinProbe.forEach(function(id){clearWatch(id);});delete global.wandPinProbe;} "
    "Puck.removeListener('accel',onMotion); NRF.removeListener('connect',onConnect); NRF.removeListener('disconnect',onDisconnect); "
    "watches.forEach(function(id){clearWatch(id);}); if(sendTimer!==undefined)clearInterval(sendTimer); "
    "if(typeof hudTimer!=='undefined')clearInterval(hudTimer); if(typeof holdClickTimer!=='undefined')clearTimeout(holdClickTimer); "
    "if(typeof pointerTrackTimer!=='undefined')clearInterval(pointerTrackTimer); if(typeof tapTimer!=='undefined')clearTimeout(tapTimer); "
    "if(typeof scrollTimer!=='undefined')clearInterval(scrollTimer); if(typeof hudDelayTimer!=='undefined')clearTimeout(hudDelayTimer); "
    "if(!global.wandBridgeOriginalSend)global.wandBridgeOriginalSend=mouse.send; "
    "mouse.send=function(x,y,b,cb){Bluetooth.println('@WAND '+x+','+y+','+b);if(cb)cb();}; Bluetooth.println('@WAND 0,0,0');"
)


def runtime_version(source: str) -> str:
    body = source[source.index(BODY_ANCHOR):]
    return "wand-" + hashlib.sha256(body.encode()).hexdigest()[:12]


def split_statements(compact: str) -> list[str]:
    statements: list[str] = []
    start = depth = 0
    quote: str | None = None
    escape = False
    for index, char in enumerate(compact):
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            continue
        if char in "{([":
            depth += 1
        elif char in "})]":
            depth -= 1
        if depth == 0 and (char == ";" or (char == "}" and compact[start:index + 1].lstrip().startswith("function "))):
            statements.append(compact[start:index + 1].strip())
            start = index + 1
    if compact[start:].strip():
        statements.append(compact[start:].strip())
    return statements


def compact_bridge(source: str) -> str:
    """Strip authoring comments and split into complete statements, one per line.

    The receiver sends each line as its own REPL command; a single large command ran the Puck
    out of memory. An `if` keeps its `else` on the same line.
    """
    text = " ".join(line.strip() for line in source.splitlines() if line.strip() and not line.lstrip().startswith("//"))
    parts: list[str] = []
    start = depth = 0
    quote: str | None = None
    escape = False
    for index, char in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            continue
        if char in "({[":
            depth += 1
        elif char in ")}]":
            depth -= 1
        if char == ";" and depth == 0 and not text[index + 1:].lstrip().startswith("else"):
            parts.append(text[start:index + 1].strip())
            start = index + 1
    if text[start:].strip():
        parts.append(text[start:].strip())
    if quote or depth:
        raise ValueError("Bridge source has an unbalanced quote or bracket")
    return "\n".join(parts) + "\n"


def bridge_revision(compacted: str) -> str:
    return hashlib.sha256(compacted.encode()).hexdigest()


def artifacts() -> dict[Path, str]:
    """Return every generated device file and its exact content."""
    source = (DEVICE / "wand-mouse-prototype.js").read_text()
    body = source[source.index(BODY_ANCHOR):]
    version = runtime_version(source)
    compact = " ".join(re.sub(r"//[^\n]*", "", body).split())  # The source has no // inside strings.
    statements = split_statements(compact)
    ready = (
        "onConnect();global.WAND_UPDATING=false;updateLights();global.WAND_RUNTIME_VERSION='" + version + "';"
        "print('WAND_BRIDGE_READY BOTTOM=D1 TAP=0.22 HZ=104 POWER=IDLE_SLEEP');"
    )
    commands = [RUNTIME_PREFIX] + statements + [ready]
    if commands[-2] != "onInit();":
        raise ValueError("Device source must end by calling onInit();")
    bridge = compact_bridge((DEVICE / "wand-mode-bridge.js").read_text())
    out = {
        GENERATED / "wand-runtime-version.txt": version,
        GENERATED / "wand-commands.json": json.dumps(commands, indent=2) + "\n",
        GENERATED / "wand-runtime.js": RUNTIME_PREFIX + "eval(" + json.dumps(body) + ");" + ready + "\n",
        # Saved to Puck storage and evaluated by a short .bootcde shim, so function bodies stay in flash.
        GENERATED / "wand-boot.js": "\n".join(commands[:-2]) + "\n",
        GENERATED / "wand-mode-bridge.compact.js": bridge,
        GENERATED / "wand-power-policy.compact.js": compact_bridge((DEVICE / "wand-power-policy.js").read_text()),
    }
    manifest = json.loads((ROOT / "wand.json").read_text())
    module = (DEVICE / "modules" / "ble_hid_mouse.js").read_text()
    startup = (DEVICE / "wand-startup.js").read_text().replace(
        'require("ble_hid_mouse")', '(function(){var exports={};\n' + module + '\nreturn exports;})()', 1
    ).replace("__WAND_RUNTIME__", version).replace("__WAND_BRIDGE__", bridge_revision(bridge)).replace(
        "__WAND_PERSISTENT__", manifest["versions"]["persistentImage"]
    )
    def minify(text: str) -> str:
        return subprocess.run(["node", str(ROOT / "scripts" / "minify_device.mjs")],
                              input=text, capture_output=True, text=True, check=True).stdout
    payloads = {
        "base.js": ("wand.boot.v4", out[GENERATED / "wand-boot.js"]),
        "bridge.js": ("wand.bridge.p1", minify((DEVICE / "wand-mode-bridge.js").read_text())),
        "power.js": ("wand.power.p1", minify((DEVICE / "wand-power-policy.js").read_text())),
        "startup.js": (".bootcde", minify(startup)),
    }
    records = []
    for filename, (storage_name, text) in payloads.items():
        if not text.isascii():
            raise ValueError("Flash artifacts must be ASCII for byte-accurate writes")
        checksum = 0
        for char in text:
            checksum = (checksum * 31 + ord(char)) & 0xffffffff
        out[GENERATED / "persistent" / filename] = text
        records.append({"file": filename, "storageName": storage_name, "bytes": len(text),
                        "checksum31": checksum, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    out[GENERATED / "persistent" / "manifest.json"] = json.dumps({
        "schemaVersion": 1, "image": manifest["versions"]["persistentImage"], "files": records,
        "calibrationStorageName": "wand.zero", "totalCodeBytes": sum(item["bytes"] for item in records)
    }, indent=2) + "\n"
    return out


def identifiers() -> dict[str, str]:
    files = artifacts()
    return {
        "deviceRuntime": files[GENERATED / "wand-runtime-version.txt"],
        "bridgeRevision": bridge_revision(files[GENERATED / "wand-mode-bridge.compact.js"]),
    }
