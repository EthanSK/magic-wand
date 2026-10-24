"""Shared helpers for the how-to video pipeline: the manifest, control fingerprints and audio timing."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from paths import ROOT, REPOSITORY, DOCS, resolve_artifact
MANIFEST = ROOT / "tutorials" / "tutorials.json"
WAND = ROOT / "wand.json"
NARRATION = ROOT / "tutorials" / "narration"
VIDEOS = DOCS / "how-to" / "videos"
TRANSCRIPTS = DOCS / "how-to" / "transcripts"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def _compact(value, indent: int = 0) -> str:
    """JSON with short arrays and objects kept on one line, so the authored file stays readable."""
    inline = json.dumps(value, ensure_ascii=False)
    if not isinstance(value, (dict, list)) or (len(inline) + indent <= 110 and "\n" not in inline):
        return inline
    pad, inner = " " * indent, " " * (indent + 2)
    if isinstance(value, list):
        return "[\n" + ",\n".join(inner + _compact(item, indent + 2) for item in value) + "\n" + pad + "]"
    items = [inner + json.dumps(key, ensure_ascii=False) + ": " + _compact(item, indent + 2) for key, item in value.items()]
    return "{\n" + ",\n".join(items) + "\n" + pad + "}"


def save_manifest(manifest: dict) -> None:
    MANIFEST.write_text(_compact(manifest) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audio_seconds(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(result.stdout.strip()), 3)


def resolve_controls(tutorial: dict, wand: dict) -> list[str]:
    """Return the current wand.json text for each control a tutorial depends on.

    Gestures match their exact label; notes match a distinctive substring. A missing reference
    raises, because the tutorial now describes a control that no longer exists.
    """
    buttons = {button["id"]: button for button in wand["buttons"]}
    lines = [f"controlVersion={wand['controlVersions']['active']}"]
    for ref in tutorial["controls"]:
        button = buttons[ref["button"]]
        if "gesture" in ref:
            matches = [result for label, result in button["gestures"] if label == ref["gesture"]]
            kind, needle = "gesture", ref["gesture"]
            text = matches[0] if matches else None
            if text is not None:
                text = f"{needle} => {text}"
        else:
            matches = [note for note in button.get("notes", []) if ref["note"] in note]
            kind, needle = "note", ref["note"]
            text = matches[0] if matches else None
        if text is None:
            raise KeyError(f"{tutorial['id']}: {ref['button']} {kind} not found in wand.json: {needle}")
        lines.append(f"{ref['button']}|{kind}|{text}")
    return lines


def control_fingerprint(tutorial: dict, wand: dict) -> str:
    return sha256_text("\n".join(resolve_controls(tutorial, wand)))


def storyboard_fingerprint(tutorial: dict, manifest: dict) -> str:
    recipe = {key: tutorial.get(key) for key in ("question", "base", "initial", "steps", "beats")}
    recipe["video"] = manifest["video"]
    return sha256_text(json.dumps(recipe, ensure_ascii=False, sort_keys=True))


def transcript(tutorial: dict) -> str:
    """The plain-text transcript published beside each video: question, narration, then steps."""
    lines = [tutorial["question"], "", *[beat["text"] for beat in tutorial["beats"]], "", "Steps:"]
    lines += [f"{i + 1}. {step}" for i, step in enumerate(tutorial["steps"])]
    return "\n".join(lines) + "\n"


def beat_audio_name(index: int, text: str) -> str:
    return f"{index + 1:02d}-{sha256_text(text)[:10]}.mp3"
