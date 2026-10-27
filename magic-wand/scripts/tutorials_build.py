#!/usr/bin/env python3
"""The How To gallery: its generated parts, and the checks that keep its videos honest.

    python3 scripts/build.py             # writes the gallery with every other generated file
    python3 scripts/tutorials_build.py   # checks videos, captions, narration and control references

tutorials/tutorials.json is the one list of guides. scripts/build.py calls artifacts() to fill the
marked sections of docs/how-to/index.html, write docs/how-to/tutorials.json for agents, list the
guides on the home page and refresh the gallery's ?v= cache keys.

The check fails when a video, poster, caption file or transcript is missing or differs from its
render record, when narration no longer matches its text, or when wand.json has changed a control
a video describes since it was rendered. Re-render that guide (tutorials/README.md).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, REPOSITORY, DOCS
HOWTO = DOCS / "how-to"
PAGE = HOWTO / "index.html"
sys.path.insert(0, str(ROOT / "tutorials" / "render"))

import common  # noqa: E402

GUIDE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Element IDs the gallery page already uses; a guide ID must not collide with one.
PAGE_IDS = {"guides", "player", "player-title", "player-video", "howto-q", "howto-count", "howto-empty", "howto-clear", "top"}
STAMP = re.compile(
    r"(?<=[\"'(])(?P<prefix>https://ethansk\.github\.io/magic-wand/)?"
    r"(?P<path>(?:\.\./|\./)?[A-Za-z0-9_\-][A-Za-z0-9_\-./]*\.(?:css|mjs|js|json|svg|png|jpg|webp|woff2|mp4|vtt|txt))\?v=[0-9a-f]*"
)
CUE_TIME = re.compile(r"^(\d+):(\d\d)\.(\d{3})$")


def load() -> tuple[dict, dict]:
    manifest=common.load_manifest()
    wand=json.loads(common.WAND.read_text())
    if manifest["controlVersion"] != wand["controlVersions"]["active"]:
        entry=next(item for item in wand["controlVersions"]["available"] if item["id"]==manifest["controlVersion"])
        wand=json.loads((ROOT / entry["snapshotManifest"]).read_text())
    return manifest,wand


def duration(seconds: float) -> str:
    whole = round(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


def rendered(manifest: dict) -> list[dict]:
    return [tutorial for tutorial in manifest["tutorials"] if tutorial.get("render")]


def control_texts(tutorial: dict, wand: dict) -> list[dict]:
    """The wand.json wording for each control a guide shows, for agents answering questions."""
    buttons = {button["id"]: button for button in wand["buttons"]}
    out = []
    for ref in tutorial["controls"]:
        button = buttons[ref["button"]]
        if "gesture" in ref:
            result = next(result for label, result in button["gestures"] if label == ref["gesture"])
            out.append({"button": button["name"], "gesture": ref["gesture"], "result": result})
        else:
            out.append({"button": button["name"], "note": next(note for note in button.get("notes", []) if ref["note"] in note)})
    return out


def guide(tutorial: dict, wand: dict, base: str) -> dict:
    """One guide's public record. base is "" for page-relative URLs, or the site URL for agents."""
    names = {button["id"]: button["name"] for button in wand["buttons"]}
    files = {key: tutorial["render"][key].removeprefix("docs/how-to/") for key in ("video", "poster", "captions", "transcript")}
    record = {
        "id": tutorial["id"],
        "question": tutorial["question"],
        "questions": tutorial["questions"],
        "keywords": tutorial["keywords"],
        "summary": tutorial["summary"],
        "buttons": tutorial["buttons"],
        "buttonNames": [names[item] for item in tutorial["buttons"]],
        "steps": tutorial["steps"],
        "seconds": tutorial["render"]["duration"],
        "optionNote": ("This video shows the default review gestures. With Review with nods and shakes on, use up/down for next and side-to-side for previous instead. Each clear direction change makes one step." if tutorial["id"] in {"review-changes", "stage-files"} else ""),
        **{key: f"{base}{path}?v={tutorial['render']['sha256'][key][:10]}" for key, path in files.items()},
    }
    if base:
        record = {
            "id": record["id"],
            "url": f"{base}#{tutorial['id']}",
            **{key: value for key, value in record.items() if key != "id"},
            "narration": [beat["text"] for beat in tutorial["beats"]],
            "controls": control_texts(tutorial, wand),
            "describes": tutorial["render"]["wand"],
        }
    return record


# ---------------------------------------------------------------- page fragments

def html_cards(manifest: dict, wand: dict) -> str:
    lights = {button["id"]: button["light"] for button in wand["buttons"]}
    names = {button["id"]: button["name"] for button in wand["buttons"]}
    cards = []
    for order, tutorial in enumerate(rendered(manifest)):
        item = guide(tutorial, wand, "")
        seconds = round(item["seconds"])
        chips = "".join(
            f'<span data-light="{lights[button]}"><span class="swatch" aria-hidden="true"></span>{escape(names[button])}</span>'
            for button in item["buttons"]
        )
        loading = "eager" if order < 3 else "lazy"
        cards.append("\n".join([
            f'<li class="howto-card" id="{item["id"]}" data-id="{item["id"]}" data-buttons="{" ".join(item["buttons"])}">',
            f'  <div class="howto-thumb"><img src="{item["poster"]}" width="1280" height="720" loading="{loading}" decoding="async" alt="">'
            f'<time class="howto-time" datetime="PT{seconds}S">{duration(item["seconds"])}</time></div>',
            '  <div class="howto-body">',
            f'    <h2><a href="{item["video"]}" data-guide="{item["id"]}">{escape(item["question"])}</a></h2>',
            f'    <p class="howto-summary">{escape(item["summary"])}</p>',
            f'    <p class="howto-buttons">{chips}</p>',
            "  </div>",
            "</li>",
        ]))
    return "\n".join(cards)


def html_data(manifest: dict, wand: dict) -> str:
    data = json.dumps([guide(tutorial, wand, "") for tutorial in rendered(manifest)], ensure_ascii=False, indent=1)
    data = data.replace("</", "<\\/")  # Keep the JSON from closing its script element.
    return f'<script type="application/json" id="guide-data">\n{data}\n</script>'


def html_home_list(manifest: dict, wand: dict) -> str:
    """The home page's question list. Each link carries the light colour of the button it uses."""
    lights = {button["id"]: button["light"] for button in wand["buttons"]}
    items = [
        f'<li data-light="{lights[tutorial["buttons"][0]]}"><a href="./how-to/#{tutorial["id"]}">'
        f'<span class="swatch" aria-hidden="true"></span><span class="howto-q">{escape(tutorial["question"])}</span>'
        f'<span class="howto-len">{duration(tutorial["render"]["duration"])}</span></a></li>'
        for tutorial in rendered(manifest)
    ]
    scope = f'<p class="fine">Illustrated with Control V{manifest["controlVersion"]}.</p>'
    return '<ul class="howto-links">\n' + "\n".join(items) + "\n</ul>\n" + scope


def agent_index(manifest: dict, wand: dict) -> str:
    site = manifest["site"]
    data = {
        "$comment": "Generated by scripts/build.py from tutorials/tutorials.json. Each guide answers one question with a short narrated video; link people to its url.",
        "title": "Magic Wand How To",
        "page": site,
        "search": f"{site}?q={{question}}",
        "scope": manifest["scope"],
        "controlVersion": manifest["controlVersion"],
        "illustrated": "Each video is an illustrated guide drawn from wand.json, not a recording of the real wand.",
        "guides": [guide(tutorial, wand, site) for tutorial in rendered(manifest)],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def stamp(text: str, contents: dict[Path, str]) -> str:
    """Refresh ?v= keys on the gallery's own, site-relative and absolute asset URLs."""
    def version(match: re.Match) -> str:
        base = DOCS if match.group("prefix") else HOWTO
        path = Path(os.path.normpath(base / match.group("path")))
        if path in contents:
            data = contents[path].encode()
        elif path.is_file():
            data = path.read_bytes()
        else:
            raise SystemExit(f"docs/how-to/index.html points at a missing file: {match.group('path')}")
        return f"{match.group('prefix') or ''}{match.group('path')}?v={hashlib.sha256(data).hexdigest()[:10]}"
    return STAMP.sub(version, text)


def artifacts(contents: dict[Path, str]) -> dict[Path, str]:
    """Generated gallery files, given the other generated files (the home page and styles.css)."""
    from site_build import replace_markers  # noqa: PLC0415 - same marker format as the home page

    manifest, wand = load()
    out: dict[Path, str] = {HOWTO / "tutorials.json": agent_index(manifest, wand)}
    if PAGE.exists():
        page = replace_markers(PAGE.read_text(), {"howto-cards": html_cards(manifest, wand), "howto-data": html_data(manifest, wand)})
        out[PAGE] = stamp(page, {**contents, **out})
    home = DOCS / "index.html"
    if home in contents:
        out[home] = replace_markers(contents[home], {"howto": html_home_list(manifest, wand)})
    return out


# ---------------------------------------------------------------- checks

def cue_seconds(value: str) -> float:
    match = CUE_TIME.match(value)
    if not match:
        raise ValueError(value)
    minutes, seconds, millis = (int(part) for part in match.groups())
    return minutes * 60 + seconds + millis / 1000


def caption_problems(text: str, tutorial: dict) -> list[str]:
    if not text.startswith("WEBVTT\n"):
        return ["captions must start with WEBVTT"]
    cues = []
    for block in text.strip().split("\n\n")[1:]:
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            return [f"caption block without timing: {lines[:1]}"]
        start, end = (part.strip().split(" ")[0] for part in lines[timing].split("-->"))
        try:
            cues.append((cue_seconds(start), cue_seconds(end), "\n".join(lines[timing + 1:])))
        except ValueError as error:
            return [f"caption timestamp {error} isn't mm:ss.mmm"]
    problems = []
    texts = [beat["text"].strip() for beat in tutorial["beats"]]
    if [cue[2].strip() for cue in cues] != texts:
        problems.append("caption text differs from the narration beats")
    previous = 0.0
    for start, end, _ in cues:
        if not previous <= start < end <= tutorial["render"]["duration"] + 0.05:
            problems.append(f"caption timing out of order or past the end at {start:.3f}")
            break
        previous = end
    return problems


def problems(manifest: dict | None = None, wand: dict | None = None) -> list[str]:
    """Every reason the published guides don't match the manifest, the narration or wand.json."""
    if manifest is None or wand is None:
        loaded = load()
        manifest, wand = manifest or loaded[0], wand or loaded[1]
    found: list[str] = []
    limit = manifest["narration"]["maxBeatCharacters"]
    if manifest["controlVersion"] != wand["controlVersions"]["active"]:
        found.append(f"tutorials target Control V{manifest['controlVersion']}, but wand.json's active control version is {wand['controlVersions']['active']}")
    buttons = {button["id"] for button in wand["buttons"]}
    seen: set[str] = set()
    for tutorial in manifest["tutorials"]:
        name = tutorial.get("id", "?")
        say = lambda message: found.append(f"{name}: {message}")  # noqa: E731
        if not GUIDE_ID.match(name) or name in PAGE_IDS or name in seen:
            say("IDs must be unique lowercase words joined by hyphens, distinct from the page's own element IDs")
        seen.add(name)
        for field in ("question", "summary"):
            if not tutorial.get(field, "").strip():
                say(f"missing {field}")
        if not all(text.endswith("?") for text in [tutorial.get("question", ""), *tutorial.get("questions", [])]):
            say("questions must end with a question mark")
        if not tutorial.get("keywords") or not tutorial.get("steps") or not tutorial.get("beats"):
            say("needs keywords, steps and beats")
        if not set(tutorial.get("buttons", [])) <= buttons or not tutorial.get("buttons"):
            say("buttons must name wand.json buttons")
        for index, beat in enumerate(tutorial.get("beats", [])):
            if not 1 <= len(beat["text"].strip()) <= limit:
                say(f"beat {index + 1} must have 1 to {limit} characters")
            if not 0 <= beat.get("step", 0) < len(tutorial.get("steps", [])):
                say(f"beat {index + 1} points at a missing step")
        try:
            fingerprint = common.control_fingerprint(tutorial, wand)
        except KeyError as error:
            say(f"describes a control wand.json no longer has ({error.args[0].split(': ', 1)[-1]})")
            fingerprint = None

        narration = tutorial.get("narration", {}).get("beats", [])
        if len(narration) != len(tutorial.get("beats", [])):
            say("narration is missing beats; run tutorials/narrate.py")
        else:
            for index, (beat, record) in enumerate(zip(tutorial["beats"], narration)):
                text = beat["text"].strip()
                expected = f"tutorials/narration/{name}/{common.beat_audio_name(index, text)}"
                if record.get("textSha256") != common.sha256_text(text) or record.get("file") != expected:
                    say(f"beat {index + 1} narration was made for different text; run tutorials/narrate.py")
                elif not (ROOT / expected).is_file():
                    say(f"beat {index + 1} narration file is missing")

        render = tutorial.get("render")
        if not render:
            say("not rendered; run tutorials/render/render.py")
            continue
        for key in ("video", "poster", "captions", "transcript"):
            path = common.resolve_artifact(render[key])
            if not path.is_file():
                say(f"{key} is missing: {render[key]}")
            elif common.sha256_file(path) != render["sha256"][key]:
                say(f"{key} differs from its render record; re-render it")
        if render.get("codecs") != ["aac", "h264"] or render.get("size") != [manifest["video"]["width"], manifest["video"]["height"]]:
            say("video must be H.264 and AAC at the manifest's size")
        if len(render.get("beats", [])) != len(tutorial.get("beats", [])):
            say("rendered with a different number of beats; re-render it")
        if fingerprint and render.get("controlFingerprint") != fingerprint:
            say("wand.json changed a control this video shows; check the beats and re-render it")
        if render.get("storyboardFingerprint") != common.storyboard_fingerprint(tutorial, manifest):
            say("the storyboard changed; re-render this guide")
        captions = common.resolve_artifact(render["captions"])
        if captions.is_file():
            found += [f"{name}: {message}" for message in caption_problems(captions.read_text(), tutorial)]
        transcript = common.resolve_artifact(render["transcript"])
        if transcript.is_file() and transcript.read_text() != common.transcript(tutorial):
            say("transcript differs from the question, beats and steps; re-render it")
    return found


def main() -> int:
    found = problems()
    if found:
        print("How To checks failed (suggested tutorial commands run from magic-wand/):\n  " + "\n  ".join(found), file=sys.stderr)
        return 1
    count = len(common.load_manifest()["tutorials"])
    print(f"How To checks passed: {count} videos, captions, transcripts, narration and control references are current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
