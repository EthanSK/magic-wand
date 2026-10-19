#!/usr/bin/env python3
"""Synthesize missing how-to narration beats with the configured ElevenLabs voice.

    python3 tutorials/narrate.py --session-id CURRENT_TASK_ID [tutorial-id ...]

Each beat (at most 240 characters) is synthesized once into tutorials/narration/<id>/, named by its
text hash, and reused until the text changes. The helper reads its own private credential source;
this script never reads or stores credentials, and the session ID is not recorded. On a failure it
saves the beats already made, prints the provider's error and stops. It never plays audio.
"""
from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "render"))
from common import NARRATION, audio_seconds, beat_audio_name, load_manifest, save_manifest, sha256_text  # noqa: E402

HELPER = Path.home() / ".codex" / "skills" / "speak-action-reminder" / "scripts" / "elevenlabs-audio.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*", help="Tutorial IDs (default: all)")
    parser.add_argument("--session-id", required=True, help="Current task ID, which keeps one narrator voice")
    parser.add_argument("--dry-run", action="store_true", help="List missing beats without synthesizing")
    args = parser.parse_args()
    manifest = load_manifest()
    limit = manifest["narration"]["maxBeatCharacters"]
    selected = [t for t in manifest["tutorials"] if not args.ids or t["id"] in args.ids]
    if args.ids and len(selected) != len(args.ids):
        raise SystemExit("Unknown tutorial ID")
    made = 0
    for tutorial in selected:
        folder = NARRATION / tutorial["id"]
        folder.mkdir(parents=True, exist_ok=True)
        previous = {beat["textSha256"]: beat for beat in tutorial.get("narration", {}).get("beats", [])}
        beats = []
        for index, beat in enumerate(tutorial["beats"]):
            text = beat["text"].strip()
            if not 1 <= len(text) <= limit:
                raise SystemExit(f"{tutorial['id']} beat {index + 1} has {len(text)} characters; the limit is {limit}")
            name = beat_audio_name(index, text)
            audio = folder / name
            source = folder / name.replace(".mp3", ".txt")
            record = previous.get(sha256_text(text))
            if audio.exists() and record and record.get("file") == f"tutorials/narration/{tutorial['id']}/{name}":
                beats.append(record)
                continue
            if args.dry_run:
                print("missing", tutorial["id"], index + 1, text)
                continue
            source.write_text(text + "\n")
            pending = folder / (name + ".partial.mp3")
            pending.unlink(missing_ok=True)
            result = subprocess.run(
                [sys.executable, str(HELPER), str(source), str(pending), "--session-id", args.session_id, "--delivery", manifest["narration"]["delivery"]],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0 or not pending.exists():
                tutorial["narration"] = {**tutorial.get("narration", {}), "beats": beats}
                save_manifest(manifest)
                print(f"Synthesis failed for {tutorial['id']} beat {index + 1} (exit {result.returncode}).", file=sys.stderr)
                print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
                return 1
            pending.rename(audio)
            seconds = audio_seconds(audio)
            words = len(text.split())
            model = result.stdout.strip().split(" audio generated")[0] or "unknown"
            beats.append({
                "file": f"tutorials/narration/{tutorial['id']}/{name}",
                "textSha256": sha256_text(text),
                "seconds": seconds,
                "wordsPerMinute": round(words / seconds * 60) if seconds else None,
                "model": model,
                "generated": datetime.date.today().isoformat(),
            })
            made += 1
            print(f"{tutorial['id']} beat {index + 1}: {seconds:.2f} s ({model})")
        if not args.dry_run:
            tutorial["narration"] = {
                "provider": manifest["narration"]["provider"],
                "delivery": manifest["narration"]["delivery"],
                "voice": "The voice the helper assigns to the production session",
                "beats": beats,
            }
            save_manifest(manifest)
    print(f"Synthesized {made} new beat(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
