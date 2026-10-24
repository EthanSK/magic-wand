#!/usr/bin/env python3
"""Render the Magic Wand how-to videos from tutorials/tutorials.json.

    python3 tutorials/render/render.py [tutorial-id ...] [--scratch DIR] [--workers 2]
    python3 tutorials/render/render.py --frames DIR [tutorial-id ...]   # still frames for review

Narration must exist first (tutorials/narrate.py). Timing comes from the measured length of
each narration beat. Frames are drawn with Pillow and streamed straight into ffmpeg (H.264 and
AAC in MP4, yuv420p, faststart), so no frame files are written. Outputs go to docs/how-to/videos/
and docs/how-to/transcripts/, and each tutorial's render block in the manifest records the asset
paths, hashes, duration and the wand.json revision it describes.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT, REPOSITORY, TRANSCRIPTS, VIDEOS, WAND, control_fingerprint, storyboard_fingerprint, load_manifest, save_manifest, sha256_file, transcript,
)
from scene import H, W, Painter, Timeline  # noqa: E402

RATE = 44100


def decode(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def narration_track(timeline: Timeline, destination: Path) -> None:
    samples = np.zeros(int(round(timeline.duration * RATE)) + RATE // 10, dtype=np.float32)
    for beat in timeline.beats:
        clip = decode(ROOT / beat["record"]["file"])
        start = int(round(beat["start"] * RATE))
        end = min(len(samples), start + len(clip))
        samples[start:end] += clip[: end - start]
    samples = samples[: int(round(timeline.duration * RATE))]
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(destination), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(pcm.tobytes())


def timestamp(seconds: float) -> str:
    minutes, rest = divmod(max(0.0, seconds), 60)
    return f"{int(minutes):02d}:{rest:06.3f}"


def captions(timeline: Timeline) -> str:
    cues = ["WEBVTT", ""]
    for index, beat in enumerate(timeline.beats):
        following = timeline.beats[index + 1]["start"] if index + 1 < len(timeline.beats) else timeline.duration
        end = min(following - 0.05, beat["speechEnd"] + 0.3)
        cues += [str(index + 1), f"{timestamp(beat['start'])} --> {timestamp(end)}", beat["beat"]["text"], ""]
    return "\n".join(cues)


def poster_time(timeline: Timeline) -> float:
    beat = timeline.beats[min(1, len(timeline.beats) - 1)]
    return beat["start"] + (beat["end"] - beat["start"]) * 0.6


def render_one(tutorial_id: str, scratch: str) -> dict:
    manifest = load_manifest()
    wand = json.loads(WAND.read_text())
    tutorial = next(t for t in manifest["tutorials"] if t["id"] == tutorial_id)
    timeline = Timeline(tutorial, manifest, wand)
    painter = Painter(timeline, manifest, wand)
    work = Path(tempfile.mkdtemp(prefix=f"{tutorial_id}-", dir=scratch))
    audio, video = work / "narration.wav", work / f"{tutorial_id}.mp4"
    narration_track(timeline, audio)
    fps = manifest["video"]["fps"]
    encoder = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-threads", "2",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "medium", "-tune", "animation", "-crf", "21", "-pix_fmt", "yuv420p",
        "-x264-params", "threads=2", "-c:a", "aac", "-b:a", "128k", "-ar", str(RATE),
        "-movflags", "+faststart", "-shortest", str(video),
    ], stdin=subprocess.PIPE)
    try:
        for index in range(timeline.frames):
            encoder.stdin.write(painter.frame(index / fps).tobytes())
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError(f"ffmpeg failed for {tutorial_id}")
    except BaseException:
        encoder.kill()
        raise
    VIDEOS.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    targets = {
        "video": VIDEOS / f"{tutorial_id}.mp4",
        "poster": VIDEOS / f"{tutorial_id}.jpg",
        "captions": VIDEOS / f"{tutorial_id}.vtt",
        "transcript": TRANSCRIPTS / f"{tutorial_id}.txt",
    }
    shutil.move(str(video), targets["video"])
    painter.frame(poster_time(timeline)).save(targets["poster"], quality=84, optimize=True, progressive=True)
    targets["captions"].write_text(captions(timeline))
    targets["transcript"].write_text(transcript(tutorial))
    shutil.rmtree(work, ignore_errors=True)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height",
                                       "-of", "json", str(targets["video"])], capture_output=True, text=True, check=True).stdout)
    return {
        "id": tutorial_id,
        "render": {
            **{key: path.relative_to(REPOSITORY).as_posix() for key, path in targets.items()},
            "duration": round(float(probe["format"]["duration"]), 2),
            "codecs": sorted({stream["codec_name"] for stream in probe["streams"]}),
            "size": [W, H],
            "beats": [{"start": round(b["start"], 3), "end": round(b["speechEnd"], 3)} for b in timeline.beats],
            "sha256": {key: sha256_file(path) for key, path in targets.items()},
            "controlFingerprint": control_fingerprint(tutorial, wand),
            "storyboardFingerprint": storyboard_fingerprint(tutorial, manifest),
            "wand": {
                "updated": wand["updated"],
                "receiver": f"{wand['versions']['receiver']} ({wand['versions']['receiverBuild']})",
                "controlVersion": wand["controlVersions"]["active"],
            },
            "renderer": "tutorials/render/render.py",
            "rendered": datetime.date.today().isoformat(),
        },
    }


def still_frames(ids: list[str], folder: Path) -> None:
    """Save frames at each beat's middle and a contact sheet per tutorial, for visual review."""
    from PIL import Image

    manifest = load_manifest()
    wand = json.loads(WAND.read_text())
    folder.mkdir(parents=True, exist_ok=True)
    for tutorial in manifest["tutorials"]:
        if ids and tutorial["id"] not in ids:
            continue
        timeline = Timeline(tutorial, manifest, wand)
        painter = Painter(timeline, manifest, wand)
        times = [0.3] + [b["start"] + (b["end"] - b["start"]) * f for b in timeline.beats for f in (0.35, 0.8)]
        frames = [painter.frame(t) for t in times]
        sheet = Image.new("RGB", (640 * 3, 360 * ((len(frames) + 2) // 3)), (0, 0, 0))
        for i, (t, frame) in enumerate(zip(times, frames)):
            sheet.paste(frame.resize((640, 360)), ((i % 3) * 640, (i // 3) * 360))
        sheet.save(folder / f"{tutorial['id']}-sheet.jpg", quality=82)
        frames[min(3, len(frames) - 1)].save(folder / f"{tutorial['id']}-frame.png")
        print(folder / f"{tutorial['id']}-sheet.jpg")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--scratch", type=Path, default=ROOT / "build" / "tutorial-render.noindex")
    parser.add_argument("--workers", type=int, default=1, choices=[1, 2])
    parser.add_argument("--frames", type=Path, help="Write review frames and contact sheets here instead of rendering")
    args = parser.parse_args()
    if args.frames:
        still_frames(args.ids, args.frames)
        return 0
    manifest = load_manifest()
    ids = args.ids or [t["id"] for t in manifest["tutorials"]]
    unknown = set(ids) - {t["id"] for t in manifest["tutorials"]}
    if unknown:
        raise SystemExit(f"Unknown tutorial: {', '.join(sorted(unknown))}")
    args.scratch.mkdir(parents=True, exist_ok=True)
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(render_one, ids, [str(args.scratch)] * len(ids)):
            results.append(result)
            print(f"{result['id']}: {result['render']['duration']:.2f} s -> {result['render']['video']}")
    manifest = load_manifest()  # Narration may have been updated meanwhile; merge only render blocks.
    for result in results:
        tutorial = next(t for t in manifest["tutorials"] if t["id"] == result["id"])
        tutorial["render"] = result["render"]
    save_manifest(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
