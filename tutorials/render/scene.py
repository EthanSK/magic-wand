"""Timeline and drawing for one Magic Wand how-to video.

The manifest gives each narration beat a list of actions placed at fractions of that beat's
measured window (spoken seconds plus its pause). Timeline turns them into tracks: button presses,
the light, the wand's aim, the on-screen pointer, discrete scene values, animated numbers and
one-off pulses. Painter draws a 1280 x 720 frame from those tracks at time t.

Everything is drawn at twice the size and reduced, which antialiases the vector shapes.
Colours, fonts, pins and the button order come from the website and wand.json.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common import ROOT

S = 2
W, H = 1280, 720

NIGHT = (31, 23, 61)
DEEP = (19, 14, 41)
WELL = (12, 9, 25)
RAISED = (42, 33, 82)
RULE = (59, 49, 112)
CHALK = (242, 239, 249)
HAZE = (174, 167, 207)
CARBON = (44, 42, 52)
GRIP = (23, 20, 31)

SCREEN = (44, 104, 764, 554)
BAND = (44, 574, 764, 690)
INSET = (800, 488, 1240, 690)
GRIP_END = (1192, 452)
TIP_REST = (932, 216)
PX_PER_DEGREE = 7.0
AIM_FROM_POINTER = (30.0, 22.0)  # Degrees of wand travel across the whole simulated screen.
TRAIL_SECONDS = 0.8
ROLL_SECONDS = 3.0

FONT_DIR = ROOT / "docs" / "fonts"
SYMBOL_FONTS = [Path("/System/Library/Fonts/Apple Symbols.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")]


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, f):
    return tuple(round(a[i] + (b[i] - a[i]) * f) for i in range(3))


def ease(kind: str, u: float) -> float:
    u = min(1.0, max(0.0, u))
    if kind == "linear":
        return u
    if kind == "out":
        return 1 - (1 - u) ** 3
    if kind == "steps":
        return u
    return u * u * (3 - 2 * u)


# --------------------------------------------------------------------------- fonts and text

@lru_cache(maxsize=None)
def font(name: str, size: float, weight: int) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(str(FONT_DIR / f"{name}.woff2"), round(size * S))
    try:
        face.set_variation_by_axes([weight])
    except OSError:
        pass
    return face


@lru_cache(maxsize=None)
def symbol_font(size: float) -> ImageFont.FreeTypeFont | None:
    for path in SYMBOL_FONTS:
        if path.exists():
            return ImageFont.truetype(str(path), round(size * 1.2 * S))
    return None


@lru_cache(maxsize=4096)
def has_glyph(name: str, size: float, weight: int, char: str) -> bool:
    face = font(name, size, weight)
    return face.getmask(char).getbbox() != face.getmask("￿").getbbox()


def text_runs(name: str, size: float, weight: int, text: str):
    """Split text into (font, string) runs, using a system symbol font for missing glyphs."""
    runs, current, fallback = [], "", None
    for char in text:
        missing = char.strip() and not has_glyph(name, size, weight, char)
        use = symbol_font(size) if missing else None
        if missing and use is None:
            char, use = {"⌘": "Cmd ", "↩": "Return", "→": "->"}.get(char, "?"), None
        if current and use is not fallback:
            runs.append((fallback or font(name, size, weight), current))
            current = ""
        fallback = use
        current += char
    if current:
        runs.append((fallback or font(name, size, weight), current))
    return runs


def text_width(name: str, size: float, weight: int, text: str) -> float:
    return sum(face.getlength(part) for face, part in text_runs(name, size, weight, text)) / S


class Pen:
    """Drawing in 1x coordinates on a 2x image."""

    def __init__(self, image: Image.Image):
        self.image = image
        self.draw = ImageDraw.Draw(image, "RGBA")

    @staticmethod
    def s(value):
        return round(value * S)

    def rect(self, box, fill=None, outline=None, width=1.0, radius=0.0):
        x0, y0, x1, y1 = (self.s(v) for v in box)
        if x1 <= x0 or y1 <= y0:
            return
        self.draw.rounded_rectangle((x0, y0, x1, y1), radius=self.s(radius), fill=fill, outline=outline,
                                    width=max(1, self.s(width)) if outline else 0)

    def circle(self, cx, cy, r, fill=None, outline=None, width=1.0):
        self.draw.ellipse((self.s(cx - r), self.s(cy - r), self.s(cx + r), self.s(cy + r)), fill=fill, outline=outline,
                          width=max(1, self.s(width)) if outline else 0)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=1.0):
        self.draw.ellipse((self.s(cx - rx), self.s(cy - ry), self.s(cx + rx), self.s(cy + ry)), fill=fill, outline=outline,
                          width=max(1, self.s(width)) if outline else 0)

    def line(self, points, fill, width=1.0):
        self.draw.line([(self.s(x), self.s(y)) for x, y in points], fill=fill, width=max(1, self.s(width)), joint="curve")

    def poly(self, points, fill):
        self.draw.polygon([(self.s(x), self.s(y)) for x, y in points], fill=fill)

    def text(self, x, y, value, name="atkinson-hyperlegible-next", size=18, weight=500, fill=CHALK, anchor="la"):
        width = text_width(name, size, weight, value)
        if anchor[0] == "m":
            x -= width / 2
        elif anchor[0] == "r":
            x -= width
        cursor = self.s(x)
        base = font(name, size, weight)
        vertical = anchor[1] if len(anchor) > 1 else "a"
        # Fallback symbols share the main font's baseline.
        baseline = self.s(y) + base.getbbox("H", anchor="l" + vertical)[1] - base.getbbox("H", anchor="ls")[1]
        for face, part in text_runs(name, size, weight, value):
            if face is base:
                self.draw.text((cursor, self.s(y)), part, font=face, fill=fill, anchor="l" + vertical)
            else:
                self.draw.text((cursor, baseline), part, font=face, fill=fill, anchor="ls")
            cursor += face.getlength(part)
        return width

    def dashed_rect(self, box, fill, width=2.0, dash=8.0, gap=6.0):
        x0, y0, x1, y1 = box
        for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            length = math.hypot(bx - ax, by - ay)
            position = 0.0
            while position < length:
                end = min(length, position + dash)
                f0, f1 = position / length, end / length
                self.line([(ax + (bx - ax) * f0, ay + (by - ay) * f0), (ax + (bx - ax) * f1, ay + (by - ay) * f1)], fill, width)
                position += dash + gap


@lru_cache(maxsize=64)
def glow_sprite(rgb: tuple[int, int, int], radius: int, strength: float) -> Image.Image:
    size = radius * 2 * S
    sprite = Image.new("RGBA", (size, size), (*rgb, 0))
    axis = (np.arange(size) + 0.5 - size / 2) / (size / 2)
    distance = np.sqrt(axis[None, :] ** 2 + axis[:, None] ** 2)
    alpha = (np.clip(1 - distance, 0, 1) ** 2.2 * 255 * strength).astype(np.uint8)  # Exactly zero at the radius.
    sprite.putalpha(Image.fromarray(alpha, "L"))
    return sprite


def paste_glow(image: Image.Image, cx, cy, rgb, radius, strength=0.55):
    sprite = glow_sprite(tuple(rgb), int(radius), strength)
    image.alpha_composite(sprite, (round((cx - radius) * S), round((cy - radius) * S))) if image.mode == "RGBA" else \
        image.paste(sprite, (round((cx - radius) * S), round((cy - radius) * S)), sprite)


# --------------------------------------------------------------------------- timeline

class Timeline:
    def __init__(self, tutorial: dict, manifest: dict, wand: dict):
        video = manifest["video"]
        self.tutorial = tutorial
        self.fps = video["fps"]
        records = tutorial["narration"]["beats"]
        if len(records) != len(tutorial["beats"]):
            raise ValueError(f"{tutorial['id']}: narrate before rendering")
        self.beats = []
        t = video["introSeconds"]
        for beat, record in zip(tutorial["beats"], records):
            seconds = record["seconds"]
            window = seconds + beat.get("pause", video["gapSeconds"])
            self.beats.append({"start": t, "speechEnd": t + seconds, "end": t + window, "beat": beat, "record": record})
            t += window
        self.duration = round(max(self.beats[-1]["end"], self.beats[-1]["speechEnd"] + video["tailSeconds"]), 3)
        self.frames = math.ceil(self.duration * self.fps)
        initial = tutorial.get("initial", {})
        self.presses: dict[str, list[list[float]]] = {"top": [], "middle": [], "bottom": []}
        self.lights: list[tuple[float, str]] = [(0.0, initial.get("light", "idle"))]
        self.steps: list[tuple[float, int]] = [(0.0, 0)]
        self.values: dict[str, list[tuple[float, object]]] = {}
        self.numbers: dict[str, list[tuple[float, float, float, float, str]]] = {}
        self.aim_segments: list[tuple[float, float, object]] = []
        self.pointer_segments: list[tuple[float, float, object]] = []
        self.pulses: list[tuple[float, str, dict]] = []
        self.initial = initial
        self.aim_start = tuple(initial.get("aim", (0.0, 0.0)))
        self.pointer_start = tuple(initial.get("pointer", (0.5, 0.5)))
        self._build()

    def _time(self, beat, action, key="at"):
        window = beat["end"] - beat["start"]
        t = beat["start"] + action.get(key, 0) * window
        if key == "at":
            t += action.get("atS", 0)
        return t

    def _build(self):
        actions = []
        for beat in self.beats:
            actions.append((beat["start"], 0, {"step": beat["beat"]["step"]}, beat))
            for order, action in enumerate(beat["beat"]["actions"]):
                actions.append((self._time(beat, action), order + 1, action, beat))
        actions.sort(key=lambda item: (item[0], item[1]))
        aim = self.aim_start
        pointer = self.pointer_start
        latest: dict[str, float] = {}
        for t, _, action, beat in actions:
            end = self._time(beat, action, "to") if "to" in action else t
            if "tap" in action:
                self.presses[action["tap"]].append([t, t + 0.14])
            if "double" in action:
                self.presses[action["double"]] += [[t, t + 0.13], [t + 0.25, t + 0.38]]
            if "press" in action:
                self.presses[action["press"]].append([t, None])
            if "release" in action:
                open_presses = [p for p in self.presses[action["release"]] if p[1] is None]
                open_presses[-1][1] = t
            if "light" in action:
                self.lights.append((t, action["light"]))
            if "step" in action:
                self.steps.append((t, action["step"]))
            if "set" in action:
                for key, value in action["set"].items():
                    self.values.setdefault(key, []).append((t, value))
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        self.numbers.setdefault(key, []).append(("set", t, float(value)))
                        latest[key] = float(value)
            if "animate" in action:
                for key, target in action["animate"].items():
                    start = latest.get(key, float(self.initial.get(key, 0.0)))
                    self.numbers.setdefault(key, []).append(("animate", t, max(end, t + 1e-3), start, float(target), action.get("ease", "inOut")))
                    latest[key] = float(target)
            if "pulse" in action:
                self.pulses.append((t, action["pulse"], {k: v for k, v in action.items() if k not in ("at", "to", "atS", "pulse")} | {"until": end}))
            if "turn" in action:
                target = tuple(action["turn"])
                self.aim_segments.append((t, end, _line(aim, target, action.get("ease", "inOut"))))
                aim = target
            if "circle" in action:
                fn, aim = _circle(aim, action["circle"], action.get("turns", 1), action.get("radius", 6), action.get("startAngle", -90))
                self.aim_segments.append((t, end, fn))
            if "nudge" in action:
                self.aim_segments.append((t, end, _nudge(aim, action["nudge"])))
            if "point" in action or "jump" in action:
                target = tuple(action.get("point") or action.get("jump"))
                finish = end if "point" in action else t + 0.12
                self.pointer_segments.append((t, finish, _line(pointer, target, "inOut" if "point" in action else "out")))
                if "point" in action:
                    goal = ((target[0] - 0.5) * AIM_FROM_POINTER[0], (target[1] - 0.5) * AIM_FROM_POINTER[1])
                    self.aim_segments.append((t, finish, _line(aim, goal, "inOut")))
                    aim = goal
                pointer = target
        for presses in self.presses.values():
            for press in presses:
                if press[1] is None:
                    press[1] = self.duration + 1

    # -- queries
    def value_at(self, key, t, default=None):
        value = self.initial.get(key, default)
        for when, item in self.values.get(key, []):
            if when <= t:
                value = item
        return value

    def changed_at(self, key, t):
        times = [when for when, _ in self.values.get(key, []) if when <= t]
        return times[-1] if times else None

    def number(self, key, t, default=0.0):
        """Numbers combine `set` jumps and `animate` moves, applied in time order."""
        value = float(self.initial.get(key, default))
        for event in self.numbers.get(key, []):
            if event[0] == "set":
                if event[1] <= t:
                    value = event[2]
                continue
            _, t0, t1, start, target, kind = event
            if t < t0:
                continue
            if t >= t1:
                value = target
                continue
            u = ease(kind, (t - t0) / (t1 - t0))
            if kind == "steps":
                span = target - start
                value = start + math.copysign(math.floor(abs(span) * u + 1e-9), span)
            else:
                value = start + (target - start) * u
        return value

    def pressed(self, button, t):
        return any(a <= t < b for a, b in self.presses[button])

    def light(self, t):
        mode = "idle"
        for when, item in self.lights:
            if when <= t:
                mode = item
        return mode

    def step(self, t):
        index = 0
        for when, item in self.steps:
            if when <= t:
                index = item
        return index

    def step_changed(self, t):
        times = [when for when, _ in self.steps if when <= t]
        return times[-1] if times else 0.0

    def aim(self, t):
        value = self.aim_start
        for t0, t1, fn in self.aim_segments:
            if t0 <= t:
                value = fn(1.0 if t >= t1 else (t - t0) / max(1e-6, t1 - t0))
        return value

    def pointer(self, t):
        value = self.pointer_start
        for t0, t1, fn in self.pointer_segments:
            if t0 <= t:
                value = fn(1.0 if t >= t1 else (t - t0) / max(1e-6, t1 - t0))
        return value

    def active_pulses(self, t, name=None, lasting=1.2):
        for when, pulse, params in self.pulses:
            until = max(params.get("until", when), when + lasting)
            if (name is None or pulse == name) and when <= t <= until:
                yield (t - when, pulse, params)


def _line(start, end, kind):
    def fn(u):
        e = ease(kind, u)
        return (start[0] + (end[0] - start[0]) * e, start[1] + (end[1] - start[1]) * e)
    return fn


def _circle(start, direction, turns, radius, start_angle=-90):
    # Ethan's north->east / east->north examples share the same centre.
    # Screen coordinates (y down): increasing angle draws clockwise.
    initial = math.radians(start_angle)
    centre = (start[0] - radius * math.cos(initial), start[1] - radius * math.sin(initial))
    sign = 1 if direction == "cw" else -1

    def fn(u):
        angle = initial + sign * 2 * math.pi * turns * u
        return (centre[0] + radius * math.cos(angle), centre[1] + radius * math.sin(angle))
    return fn, fn(1.0)


def _nudge(start, direction):
    distance = 4.0 if direction == "down" else -4.0

    def fn(u):
        return (start[0], start[1] + distance * math.sin(math.pi * min(1, u)))
    return fn


# --------------------------------------------------------------------------- painter

FILES = [("wand-scene.mjs", 2), ("app.mjs", 2), ("styles.css", 1), ("README.md", 1)]
APP_COLOURS = {"VS Code": (36, 120, 205), "Chrome": (52, 168, 83), "Codex": (40, 40, 40), "Agent Flow": (20, 20, 22), "Music": (232, 64, 96), "Finder": (70, 140, 230)}


class Painter:
    def __init__(self, timeline: Timeline, manifest: dict, wand: dict):
        self.tl = timeline
        self.tutorial = timeline.tutorial
        self.manifest = manifest
        self.wand = wand
        lights = {light["mode"]: light for light in wand["lights"]}
        self.light_rgb = {mode: hex_rgb(light["display"]) for mode, light in lights.items()}
        self.light_name = {mode: light["name"] for mode, light in lights.items()}
        files = next(v for v in lights["app"].get("variants", []) if v["name"] == "File staging")
        self.light_rgb["files"] = hex_rgb(files["display"])
        self.light_name["files"] = files["name"]
        self.light_name["idle"] = "Off"
        self.buttons = {button["id"]: button for button in wand["buttons"]}
        self.button_rgb = {bid: self.light_rgb[self.buttons[bid]["light"]] for bid in self.buttons}
        self.hold_seconds = wand["tuning"]["holdMs"] / 1000
        self.hud = self._hud_layout()
        self.background = self._background()
        self.screen_mask = self._screen_mask()

    # -- static parts
    def _hud_layout(self):
        data = json.loads((ROOT / "data" / "agentic-mouse-hud.json").read_text())
        pages = json.loads((ROOT / "tutorials" / "render" / "hud-pages.json").read_text())
        cards = {card["cell"]: {"title": card["title"], "fill": hex_rgb(card["fill"])} for card in data["cards"]}
        for cell, override in self.wand["hud"].get("cardOverrides", {}).items():
            cards[int(cell)]["title"] = override["title"]
        # Wand-only native cards, from the Agentic Mouse integration patches.
        cards[13] = {"title": "Review changes", "fill": (65, 201, 122)}
        cards[14] = {"title": "Stage files", "fill": (180, 105, 235)}
        cards[15] = {"title": "Play/Pause", "fill": (214, 74, 128)}
        keys = {card["cell"]: {"title": card["title"], "fill": hex_rgb(card["fill"])} for card in pages["keys"]["cards"]}
        return {"default": cards, "keys": keys, "keysTitle": pages["keys"]["title"], "rows": data["rows"]}

    def hud_rows(self, page, vscode):
        rows = [list(row) for row in self.hud["rows"]]
        if page == "default":
            rows[0].append(15)
            if vscode:
                rows[1] += [13, 14]
        return rows

    def _background(self):
        image = Image.new("RGB", (W * S, H * S), NIGHT)
        pen = Pen(image)
        for x in range(22, W, 22):
            for y in range(22, H, 22):
                pen.circle(x, y, 0.9, fill=(255, 255, 255, 14))
        pen.text(44, 52, self.tutorial["question"], "big-shoulders-display", 44, 800, CHALK, "ls")
        chip = "Control V2 · Illustrated guide"
        width = text_width("atkinson-hyperlegible-mono", 14, 500, chip)
        pen.rect((1240 - width - 28, 26, 1240, 56), fill=DEEP, radius=15)
        pen.text(1240 - width - 14, 41, chip, "atkinson-hyperlegible-mono", 14, 500, HAZE, "lm")
        x0, y0, x1, y1 = SCREEN
        pen.rect((x0 - 8, y0 - 8, x1 + 8, y1 + 8), fill=(10, 8, 21), radius=22)
        pen.rect((x0 - 9, y0 - 9, x1 + 9, y1 + 9), outline=(255, 255, 255, 22), width=1, radius=23)
        pen.rect(BAND, fill=DEEP, radius=18)
        pen.rect(INSET, fill=DEEP, radius=18)
        ix0, iy0, ix1, _ = INSET
        pen.text(ix0 + 20, iy0 + 22, "BUTTONS", "atkinson-hyperlegible-mono", 12, 600, HAZE, "lm")
        pen.text(ix1 - 20, iy0 + 22, "LAST 3 S", "atkinson-hyperlegible-mono", 12, 500, (120, 112, 160), "rm")
        # Side view of the grip, matching the website schematic: Bottom, Middle, then Top nearest the shaft.
        pen.rect((ix0 + 22, iy0 + 46, ix0 + 318, iy0 + 72), fill=GRIP, outline=(255, 255, 255, 30), radius=13)
        pen.rect((ix0 + 314, iy0 + 53, ix1 - 22, iy0 + 65), fill=CARBON, radius=3)
        pen.text(ix1 - 22, iy0 + 84, "to the tip", "atkinson-hyperlegible-mono", 11, 500, (120, 112, 160), "rm")
        for lane, bid in enumerate(("top", "middle", "bottom")):
            y = iy0 + 132 + lane * 22
            pen.text(ix0 + 22, y, self.buttons[bid]["name"], "atkinson-hyperlegible-mono", 12, 600, HAZE, "lm")
            pen.rect((ix0 + 96, y - 7, ix1 - 22, y + 7), fill=(255, 255, 255, 10), radius=7)
        return image

    def _screen_mask(self):
        x0, y0, x1, y1 = SCREEN
        mask = Image.new("L", ((x1 - x0) * S, (y1 - y0) * S), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, (x1 - x0) * S - 1, (y1 - y0) * S - 1), radius=14 * S, fill=255)
        return mask

    # -- frame
    def frame(self, t: float) -> Image.Image:
        image = self.background.copy()
        screen = self.draw_screen(t)
        image.paste(screen, (SCREEN[0] * S, SCREEN[1] * S), self.screen_mask)
        pen = Pen(image)
        self.draw_wand(image, pen, t)
        self.draw_inset(pen, t)
        self.draw_band(pen, t)
        return image.reduce(S)

    # -- wand illustration
    def tip_at(self, t):
        yaw, pitch = self.tl.aim(t)
        return (TIP_REST[0] + yaw * PX_PER_DEGREE, TIP_REST[1] + pitch * PX_PER_DEGREE)

    def draw_wand(self, image, pen, t):
        mode = self.tl.light(t)
        rgb = self.light_rgb.get(mode, self.light_rgb["idle"])
        lit = mode != "idle"
        # Mode label above the wand.
        pen.text(806, 90, "LIGHT", "atkinson-hyperlegible-mono", 12, 600, HAZE, "lm")
        pen.circle(866, 90, 7, fill=rgb if lit else (60, 54, 88))
        pen.text(880, 90, self.light_name.get(mode, mode), "atkinson-hyperlegible-next", 19, 650, CHALK, "lm")
        tip = self.tip_at(t)
        gx, gy = GRIP_END
        dx, dy = tip[0] - gx, tip[1] - gy
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        nx, ny = uy, -ux  # Perpendicular; with the tip up and left this points up and right.
        if ny > 0:
            nx, ny = -nx, -ny
        # Tip trail: where the tip has been, so turns, circles and nudges are visible.
        steps = int(TRAIL_SECONDS * 30)
        trail = [self.tip_at(t - TRAIL_SECONDS + TRAIL_SECONDS * i / steps) for i in range(steps + 1)]
        trail_rgb = rgb if lit else HAZE
        for i, (x, y) in enumerate(trail[:-1]):
            alpha = int(30 + 170 * (i / steps) ** 1.5)
            pen.circle(x, y, 2.2 + 2.2 * i / steps, fill=(*trail_rgb, alpha))
        if lit:
            paste_glow(image, tip[0], tip[1], rgb, 78, 0.55)
        grip_front = (gx + ux * length * 0.3, gy + uy * length * 0.3)
        # Shaft: tapered carbon fibre with a faint twill.
        w0, w1 = 6.0, 4.2
        pen.poly([(grip_front[0] + nx * w0, grip_front[1] + ny * w0), (tip[0] + nx * w1, tip[1] + ny * w1),
                  (tip[0] - nx * w1, tip[1] - ny * w1), (grip_front[0] - nx * w0, grip_front[1] - ny * w0)], CARBON)
        segments = int(length * 0.7 / 9)
        for i in range(segments):
            f = 0.3 + 0.7 * i / segments
            cx, cy = gx + ux * length * f, gy + uy * length * f
            w = w0 + (w1 - w0) * (f - 0.3) / 0.7
            pen.line([(cx + nx * w * 0.9, cy + ny * w * 0.9), (cx + ux * 4 - nx * w * 0.9, cy + uy * 4 - ny * w * 0.9)], (64, 61, 74), 1.2)
        pen.line([(grip_front[0] + nx * w0 * 0.6, grip_front[1] + ny * w0 * 0.6), (tip[0] + nx * w1 * 0.6, tip[1] + ny * w1 * 0.6)], (110, 106, 126, 120), 1.2)
        # Grip with three buttons along its upper side.
        gw = 15.0
        pen.poly([(gx + nx * gw, gy + ny * gw), (grip_front[0] + nx * gw * 0.9, grip_front[1] + ny * gw * 0.9),
                  (grip_front[0] - nx * gw * 0.9, grip_front[1] - ny * gw * 0.9), (gx - nx * gw, gy - ny * gw)], GRIP)
        pen.circle(gx, gy, gw, fill=GRIP)
        pen.line([(gx + nx * gw * 0.8, gy + ny * gw * 0.8), (grip_front[0] + nx * gw * 0.75, grip_front[1] + ny * gw * 0.75)], (70, 64, 92, 160), 1.5)
        for bid, f in (("bottom", 0.07), ("middle", 0.15), ("top", 0.23)):
            cx = gx + ux * length * f + nx * gw * 0.95
            cy = gy + uy * length * f + ny * gw * 0.95
            down = self.tl.pressed(bid, t)
            if down:
                paste_glow(image, cx, cy, self.button_rgb[bid], 26, 0.7)
            pen.circle(cx, cy, 6.5, fill=self.button_rgb[bid] if down else (58, 52, 80), outline=(255, 255, 255, 60), width=1)
        # Puck.js lying flat at the tip, with its light.
        pen.ellipse(tip[0], tip[1] + 2, 25, 12, fill=(196, 190, 210))
        pen.ellipse(tip[0], tip[1], 25, 12, fill=(236, 232, 244), outline=(150, 144, 170), width=1)
        pen.circle(tip[0], tip[1] - 2, 4.2, fill=rgb if lit else (42, 36, 64))

    # -- button inset
    def draw_inset(self, pen, t):
        ix0, iy0, ix1, _ = INSET
        for bid, x in (("bottom", ix0 + 70), ("middle", ix0 + 160), ("top", ix0 + 250)):
            down = self.tl.pressed(bid, t)
            rgb = self.button_rgb[bid]
            shift = 3 if down else 0
            if down:
                paste_glow(pen.image, x, iy0 + 40, rgb, 34, 0.6)
            pen.rect((x - 22, iy0 + 34 + shift, x + 22, iy0 + 47 + shift), fill=rgb if down else (58, 52, 80),
                     outline=(255, 255, 255, 70 if down else 40), width=1, radius=5)
            pen.text(x, iy0 + 88, self.buttons[bid]["name"], "big-shoulders-display", 21, 700, CHALK if down else HAZE, "mm")
            pen.text(x, iy0 + 107, self.buttons[bid]["pin"], "atkinson-hyperlegible-mono", 11, 500, (120, 112, 160), "mm")
        x0, x1 = ix0 + 96, ix1 - 22
        for lane, bid in enumerate(("top", "middle", "bottom")):
            y = iy0 + 132 + lane * 22
            rgb = self.button_rgb[bid]
            for a, b in self.tl.presses[bid]:
                if b < t - ROLL_SECONDS or a > t:
                    continue
                left = x1 - (t - a) / ROLL_SECONDS * (x1 - x0)
                right = x1 - (t - min(b, t)) / ROLL_SECONDS * (x1 - x0)
                left, right = max(x0, left), min(x1, max(right, left + 4))
                pen.rect((left, y - 6, right, y + 6), fill=rgb, radius=6)
                held = min(b, t) - a
                if held >= self.hold_seconds and right - left > 34:
                    pen.text(left + 7, y, "HOLD", "atkinson-hyperlegible-mono", 10, 700, (12, 9, 25), "lm")

    # -- instruction band
    def draw_band(self, pen, t):
        steps = self.tutorial["steps"]
        index = self.tl.step(t)
        x0, y0, x1, y1 = BAND
        pen.text(x0 + 24, y0 + 26, f"STEP {index + 1} OF {len(steps)}", "atkinson-hyperlegible-mono", 13, 600, HAZE, "lm")
        for i in range(len(steps)):
            cx = x1 - 24 - (len(steps) - 1 - i) * 18
            pen.circle(cx, y0 + 26, 4.5, fill=CHALK if i == index else (RULE if i > index else HAZE))
        since = t - self.tl.step_changed(t)
        fade = min(1.0, since / 0.18) if since >= 0 else 1.0
        size = 36
        while text_width("atkinson-hyperlegible-next", size, 650, steps[index]) > x1 - x0 - 48 and size > 24:
            size -= 2
        colour = (*CHALK, round(255 * fade))
        pen.text(x0 + 24, y0 + 74, steps[index], "atkinson-hyperlegible-next", size, 650, colour, "lm")

    # -- simulated screen
    def draw_screen(self, t):
        x0, y0, x1, y1 = SCREEN
        sw, sh = x1 - x0, y1 - y0
        image = Image.new("RGB", (sw * S, sh * S), WELL)
        pen = Pen(image)
        tl = self.tl
        base = self.tutorial["base"]
        app = tl.value_at("app", t, None)
        getattr(self, f"base_{base}")(pen, t, sw, sh)
        if tl.value_at("hud.open", t, False):
            self.overlay_hud(pen, t, sw, sh)
        if tl.value_at("switcher.open", t, False):
            self.overlay_switcher(pen, t, sw, sh)
        if tl.value_at("recording", t, False):
            self.overlay_recorder(pen, t, sw, sh)
        badge = tl.value_at("badge", t, None)
        if badge:
            self.overlay_badge(pen, t, sw, sh, badge)
        self.overlay_toast(pen, t, sw, sh)
        # Menu bar last, so app names stay readable.
        pen.rect((0, 0, sw, 24), fill=(0, 0, 0, 120))
        pen.text(14, 12, app or {"vscode": "VS Code", "chat": "Codex", "player": "Music", "document": "Notes", "timeline": "Clips"}.get(base, "Finder"),
                 "atkinson-hyperlegible-next", 12.5, 700, CHALK, "lm")
        if tl.value_at("recording", t, False):
            pen.circle(sw - 92, 12, 4, fill=self.light_rgb["recording"])
            pen.text(sw - 84, 12, "Agent Flow", "atkinson-hyperlegible-next", 12, 600, CHALK, "lm")
        self.overlay_pointer(pen, t, sw, sh)
        return image

    def pointer_px(self, t, sw, sh):
        px, py = self.tl.pointer(t)
        return px * sw, py * sh

    # ---- bases
    def base_desktop(self, pen, t, sw, sh):
        pen.rect((0, 0, sw, sh), fill=(28, 34, 70))
        pen.circle(sw * 0.18, sh * 0.25, 220, fill=(60, 44, 120, 120))
        pen.circle(sw * 0.86, sh * 0.85, 260, fill=(30, 90, 140, 90))
        pen.rect((60, 60, 380, 300), fill=(30, 28, 44, 230), radius=12)
        pen.rect((60, 60, 380, 86), fill=(46, 43, 64), radius=12)
        for i in range(6):
            pen.rect((84, 106 + i * 28, 84 + (220 if i % 2 else 280), 116 + i * 28), fill=(255, 255, 255, 30), radius=5)
        pen.rect((sw / 2 - 150, sh - 52, sw / 2 + 150, sh - 12), fill=(255, 255, 255, 40), radius=14)
        for i, rgb in enumerate([(70, 140, 230), (36, 120, 205), (52, 168, 83), (232, 64, 96), (40, 40, 40), (255, 170, 0)]):
            pen.rect((sw / 2 - 132 + i * 46, sh - 46, sw / 2 - 100 + i * 46, sh - 18), fill=rgb, radius=8)
        for age, _, params in self.tl.active_pulses(t, "search", 0.4):
            until = params["until"] - (t - age)
            px, py = self.pointer_px(t, sw, sh)
            for ring in range(3):
                phase = (age * 1.4 + ring / 3) % 1
                pen.circle(px, py, 10 + phase * 60, outline=(*CHALK, round(160 * (1 - phase))), width=2)
        for age, _, _ in self.tl.active_pulses(t, "centre", 0.9):
            cx, cy = sw / 2, sh / 2
            alpha = round(220 * max(0, 1 - age / 0.9))
            pen.line([(cx - 34, cy), (cx + 34, cy)], (*CHALK, alpha), 2)
            pen.line([(cx, cy - 34), (cx, cy + 34)], (*CHALK, alpha), 2)
            pen.circle(cx, cy, 22 + age * 40, outline=(*self.light_rgb["mouse"], alpha), width=3)

    def base_dialog(self, pen, t, sw, sh):
        self.base_desktop(pen, t, sw, sh)
        pen.rect((90, 50, sw - 90, sh - 70), fill=(36, 34, 50), radius=12)
        pen.rect((90, 50, sw - 90, 78), fill=(52, 49, 70), radius=12)
        pen.text(sw / 2, 64, "Notes", "atkinson-hyperlegible-next", 13, 700, HAZE, "mm")
        for i in range(8):
            pen.rect((124, 100 + i * 26, 124 + (420 if i % 3 else 330), 110 + i * 26), fill=(255, 255, 255, 34), radius=5)
        saved_at = self.tl.changed_at("saved", t) if self.tl.value_at("saved", t, False) else None
        if saved_at is None:
            pen.rect((0, 0, sw, sh), fill=(0, 0, 0, 70))
            bx0, by0, bx1, by1 = sw * 0.24, sh * 0.3, sw * 0.86, sh * 0.76
            pen.rect((bx0, by0, bx1, by1), fill=(48, 45, 66), outline=(255, 255, 255, 40), width=1, radius=14)
            pen.text(bx0 + 28, by0 + 38, "Save changes to “Notes”?", "atkinson-hyperlegible-next", 19, 700, CHALK, "lm")
            pen.text(bx0 + 28, by0 + 66, "Your changes will be lost if you don’t save them.", "atkinson-hyperlegible-next", 13, 500, HAZE, "lm")
            buttons = [("Don’t Save", 0.31, False), ("Cancel", 0.55, False), ("Save", 0.71, True)]
            for label, cx, primary in buttons:
                cxp, cyp = cx * sw, 0.66 * sh
                hover = math.hypot(*(a - b for a, b in zip(self.pointer_px(t, sw, sh), (cxp, cyp)))) < 40
                fill = (64, 105, 255) if primary else (78, 74, 100)
                if hover and primary:
                    fill = (96, 132, 255)
                pen.rect((cxp - 52, cyp - 17, cxp + 52, cyp + 17), fill=fill, radius=9)
                pen.text(cxp, cyp, label, "atkinson-hyperlegible-next", 14, 650, CHALK, "mm")
        else:
            age = t - saved_at
            alpha = round(255 * min(1, age / 0.2))
            pen.rect((sw / 2 - 90, sh * 0.42, sw / 2 + 90, sh * 0.58), fill=(34, 180, 110, round(alpha * 0.9)), radius=16)
            pen.text(sw / 2, sh * 0.5, "Saved", "atkinson-hyperlegible-next", 22, 700, (*CHALK, alpha), "mm")

    def base_files(self, pen, t, sw, sh):
        self.base_desktop(pen, t, sw, sh)
        scroll = self.tl.number("scrollY", t)
        pen.rect((40, 48, 380, sh - 64), fill=(34, 32, 48), radius=12)
        pen.rect((40, 48, 380, 74), fill=(50, 47, 68), radius=12)
        pen.text(210, 61, "Documents", "atkinson-hyperlegible-next", 13, 700, HAZE, "mm")
        for i in range(16):
            y = 96 + i * 30 - scroll
            if 80 < y < sh - 76:
                pen.rect((62, y - 9, 82, y + 9), fill=(120, 140, 200), radius=3)
                pen.rect((94, y - 5, 94 + (180 if i % 2 else 220), y + 5), fill=(255, 255, 255, 40), radius=4)
        folder = (0.74 * sw, 0.43 * sh)
        dropped = self.tl.value_at("dropped", t, False)
        drop_age = t - (self.tl.changed_at("dropped", t) or t)
        bounce = 1 + 0.12 * math.sin(min(1, drop_age / 0.35) * math.pi) if dropped and drop_age < 0.35 else 1
        fx, fy = folder
        pen.rect((fx - 34 * bounce, fy - 22 * bounce, fx + 34 * bounce, fy + 26 * bounce), fill=(92, 160, 245), radius=7)
        pen.rect((fx - 34 * bounce, fy - 30 * bounce, fx - 6 * bounce, fy - 18 * bounce), fill=(92, 160, 245), radius=4)
        pen.text(fx, fy + 46, "Archive", "atkinson-hyperlegible-next", 13, 650, CHALK, "mm")
        if dropped:
            pen.circle(fx + 30, fy - 24, 11, fill=(255, 90, 90))
            pen.text(fx + 30, fy - 24, "1", "atkinson-hyperlegible-next", 12, 700, CHALK, "mm")
        else:
            if self.tl.value_at("grab", t, False):
                px, py = self.pointer_px(t, sw, sh)
                ix, iy = px - 12, py - 30
            else:
                ix, iy = 0.25 * sw, 0.42 * sh - 10
            pen.rect((ix - 18, iy - 22, ix + 18, iy + 22), fill=(236, 232, 244), radius=4)
            pen.poly([(ix + 6, iy - 22), (ix + 18, iy - 10), (ix + 6, iy - 10)], (190, 184, 205))
            for k in range(4):
                pen.rect((ix - 11, iy - 6 + k * 7, ix + 10, iy - 3 + k * 7), fill=(150, 144, 170), radius=1)
            pen.text(ix, iy + 36, "notes.txt", "atkinson-hyperlegible-next", 12.5, 650, CHALK, "mm")

    def base_document(self, pen, t, sw, sh):
        pen.rect((0, 0, sw, sh), fill=(24, 22, 36))
        scroll = self.tl.number("scrollY", t)
        page_x0, page_x1 = 150, sw - 150
        pen.rect((page_x0, 24, page_x1, sh), fill=(240, 237, 246))
        sections = ["Getting started", "Pointing", "Scrolling", "The HUD", "Speech", "Review", "Lights", "Updates"]
        y = 60 - scroll
        index = 0
        while y < sh + 40:
            if y > -60:
                if index % 7 == 0:
                    pen.text(page_x0 + 34, y, f"{index // 7 + 1}. {sections[(index // 7) % len(sections)]}", "big-shoulders-display", 26, 800, (40, 32, 70), "ls")
                else:
                    width = (page_x1 - page_x0 - 68) * (0.92 if index % 3 else 0.7)
                    pen.rect((page_x0 + 34, y - 12, page_x0 + 34 + width, y - 4), fill=(170, 164, 192), radius=4)
            y += 34 if index % 7 else 46
            index += 1
        # Scroll position.
        pen.rect((sw - 22, 34, sw - 14, sh - 10), fill=(255, 255, 255, 25), radius=4)
        position = (scroll % 2400) / 2400
        pen.rect((sw - 22, 34 + position * (sh - 110), sw - 14, 34 + position * (sh - 110) + 66), fill=(255, 255, 255, 120), radius=4)
        self._motion_arrows(pen, t, sw, sh, "scrollY", vertical=True)

    def base_timeline(self, pen, t, sw, sh):
        pen.rect((0, 0, sw, sh), fill=(22, 20, 34))
        scroll = self.tl.number("scrollX", t)
        pen.text(28, 54, "Clips", "big-shoulders-display", 24, 800, CHALK, "lm")
        for track in range(3):
            y = 110 + track * 96
            pen.rect((0, y - 34, sw, y + 34), fill=(255, 255, 255, 10))
            for i in range(-2, 60):
                x = 40 + i * 132 - scroll
                if -140 < x < sw + 10:
                    rgb = [(90, 120, 230), (230, 120, 70), (70, 190, 160)][(i + track) % 3]
                    pen.rect((x, y - 28, x + 118, y + 28), fill=(*rgb, 210), radius=8)
                    if track == 0:
                        pen.text(x + 10, y - 14, f"Clip {i + 1}", "atkinson-hyperlegible-next", 12.5, 700, CHALK, "lm")
        for i in range(-2, 80):
            x = 40 + i * 66 - scroll
            if 0 < x < sw:
                pen.line([(x, sh - 50), (x, sh - (40 if i % 2 else 56))], (*HAZE, 140), 1.2)
                if i % 4 == 0:
                    pen.text(x + 4, sh - 30, f"0:{(i // 2) * 5:02d}" if i < 24 else f"{i // 24}:{((i // 2) * 5) % 60:02d}", "atkinson-hyperlegible-mono", 11, 500, HAZE, "lm")
        self._motion_arrows(pen, t, sw, sh, "scrollX", vertical=False)

    def _motion_arrows(self, pen, t, sw, sh, key, vertical):
        velocity = (self.tl.number(key, t + 0.05) - self.tl.number(key, t - 0.05)) / 0.1
        if abs(velocity) < 30:
            return
        alpha = round(min(1, abs(velocity) / 400) * 200)
        direction = -1 if velocity > 0 else 1  # Content moves opposite to the scroll position.
        px, py = self.pointer_px(t, sw, sh)
        for k in range(3):
            offset = 34 + k * 16
            if vertical:
                y = py + direction * offset
                pen.poly([(px - 9, y - 5 * direction), (px + 9, y - 5 * direction), (px, y + 6 * direction)], (*self.light_rgb["scroll"], alpha))
            else:
                x = px + direction * offset
                pen.poly([(x - 5 * direction, py - 9), (x - 5 * direction, py + 9), (x + 6 * direction, py)], (*self.light_rgb["scroll"], alpha))

    def base_app(self, pen, t, sw, sh):
        self.base_desktop(pen, t, sw, sh)
        app = self.tl.value_at("app", t, "VS Code")
        changed = self.tl.changed_at("app", t)
        rgb = APP_COLOURS.get(app, (60, 60, 80))
        pen.rect((70, 34, sw - 70, sh - 66), fill=(30, 28, 42), radius=12)
        # A tall title bar keeps the frontmost app readable above an open HUD.
        pen.rect((70, 34, sw - 70, 84), fill=mix(rgb, (30, 28, 42), 0.2), radius=12)
        pen.rect((86, 45, 114, 73), fill=rgb, outline=(255, 255, 255, 90), width=1, radius=7)
        pen.text(100, 59, app[:1], "big-shoulders-display", 20, 800, CHALK, "mm")
        pen.text(126, 59, app, "big-shoulders-display", 26, 800, CHALK, "lm")
        pen.rect((sw / 2 - 46, sh / 2 - 60, sw / 2 + 46, sh / 2 + 32), fill=rgb, radius=20)
        pen.text(sw / 2, sh / 2 - 14, app[:1], "big-shoulders-display", 48, 800, CHALK, "mm")
        pen.text(sw / 2, sh / 2 + 64, app, "big-shoulders-display", 30, 800, CHALK, "mm")
        if changed is not None and t - changed < 0.7:
            alpha = round(220 * (1 - (t - changed) / 0.7))
            pen.rect((70, 34, sw - 70, 84), outline=(*CHALK, alpha), width=3, radius=12)

    def base_chat(self, pen, t, sw, sh):
        self.base_desktop(pen, t, sw, sh)
        pen.rect((60, 40, sw - 60, sh - 30), fill=(26, 26, 30), radius=12)
        pen.rect((60, 40, sw - 60, 66), fill=(38, 38, 44), radius=12)
        pen.text(sw / 2, 53, "Codex", "atkinson-hyperlegible-next", 13, 700, HAZE, "mm")
        pen.rect((sw - 330, 90, sw - 90, 136), fill=(54, 54, 64), radius=14)
        pen.rect((sw - 314, 106, sw - 130, 116), fill=(255, 255, 255, 60), radius=4)
        pen.rect((100, 160, 420, 230), fill=(40, 40, 48), radius=14)
        for k in range(3):
            pen.rect((118, 176 + k * 16, 118 + (260 if k < 2 else 160), 184 + k * 16), fill=(255, 255, 255, 50), radius=4)
        box = (90, sh - 106, sw - 90, sh - 52)
        pasted_at = self.tl.changed_at("pasted", t) if self.tl.value_at("pasted", t, False) else None
        pen.rect(box, fill=(44, 44, 52), outline=(255, 255, 255, 30), width=1, radius=14)
        if pasted_at is None:
            pen.text(box[0] + 18, (box[1] + box[3]) / 2, "Message", "atkinson-hyperlegible-next", 15, 500, (120, 120, 130), "lm")
        else:
            alpha = round(255 * min(1, (t - pasted_at) / 0.25))
            if t - pasted_at < 0.8:
                pen.rect(box, outline=(*self.light_rgb["recording"], round(200 * (1 - (t - pasted_at) / 0.8))), width=2, radius=14)
            pen.text(box[0] + 18, (box[1] + box[3]) / 2, "Can you add how-to videos to the wand website?", "atkinson-hyperlegible-next", 15, 600, (*CHALK, alpha), "lm")

    def base_vscode(self, pen, t, sw, sh):
        pen.rect((0, 0, sw, sh), fill=(30, 30, 30))
        pen.rect((0, 24, 40, sh), fill=(44, 44, 44))
        for k in range(4):
            pen.rect((12, 44 + k * 38, 28, 60 + k * 38), fill=(120, 120, 120) if k != 2 else (220, 220, 220), radius=3)
        pen.rect((40, 24, 250, sh), fill=(37, 37, 38))
        mode = self.tl.value_at("review.mode", t, None)
        unit = self.tl.value_at("review.unit", t, "hunk")
        positions = [(f, h) for f, (_, hunks) in enumerate(FILES) for h in range(hunks)] if unit == "hunk" else [(f, 0) for f in range(len(FILES))]
        pos = int(self.tl.number("review.pos", t))
        pos = max(0, min(len(positions) - 1, pos))
        current_file, current_hunk = positions[pos]
        staged = list(self.tl.value_at("staged", t, []) or [])
        start = max(int(self.tl.value_at("review.start", t, 0) or 0), (max(staged) + 1) if staged else 0)
        if mode is None:
            pending = set()
        elif unit == "hunk":
            pending = {f for f in range(start, current_file) if f not in staged}
        else:
            pending = {f for f in range(start, current_file + 1) if f not in staged}
        pen.text(52, 44, "SOURCE CONTROL", "atkinson-hyperlegible-mono", 10.5, 700, (200, 200, 200), "lm")
        y = 70
        stage_pulse = list(self.tl.active_pulses(t, "stage", 0.8))
        if staged:
            pen.text(52, y, "Staged Changes", "atkinson-hyperlegible-next", 12, 700, (220, 220, 220), "lm")
            y += 24
            for f in staged:
                if stage_pulse:
                    pen.rect((44, y - 11, 246, y + 11), fill=(*self.light_rgb["files" if unit == "file" else "app"], round(90 * (1 - stage_pulse[0][0] / 0.8))), radius=4)
                pen.text(62, y, FILES[f][0], "atkinson-hyperlegible-next", 12.5, 600, (190, 230, 200), "lm")
                pen.text(236, y, "A", "atkinson-hyperlegible-mono", 11, 700, (110, 200, 130), "rm")
                y += 24
            y += 8
        pen.text(52, y, "Changes", "atkinson-hyperlegible-next", 12, 700, (220, 220, 220), "lm")
        y += 24
        accent = self.light_rgb["files" if mode == "files" else "app"]
        for f, (name, _) in enumerate(FILES):
            if f in staged:
                continue
            is_current = mode is not None and f == current_file
            if is_current:
                pen.rect((44, y - 11, 246, y + 11), fill=(*accent, 60), radius=4)
            if f in pending:
                pen.rect((44, y - 11, 49, y + 11), fill=accent, radius=2)
            pen.text(62, y, name, "atkinson-hyperlegible-next", 12.5, 600, (230, 230, 230), "lm")
            tag = "viewing" if is_current and unit == "hunk" else ("in set" if f in pending else "M")
            pen.text(236, y, tag, "atkinson-hyperlegible-mono", 10.5, 700, accent if tag != "M" else (226, 192, 100), "rm")
            y += 24
        # Editor with the current file's hunks.
        ex0 = 262
        pen.rect((250, 24, sw, 50), fill=(37, 37, 38))
        pen.rect((250, 24, 420, 50), fill=(30, 30, 30))
        pen.text(266, 37, FILES[current_file][0], "atkinson-hyperlegible-next", 12.5, 600, (230, 230, 230), "lm")
        line_y = 70
        hunks = FILES[current_file][1]
        for h in range(hunks):
            top = line_y
            for k in range(3):
                pen.rect((ex0 + 30, line_y - 4, ex0 + 30 + (230 if k % 2 else 310), line_y + 4), fill=(110, 110, 110), radius=3)
                line_y += 22
            for k in range(2):
                pen.rect((ex0, line_y - 10, sw - 16, line_y + 10), fill=(120, 40, 40, 140))
                pen.rect((ex0 + 30, line_y - 4, ex0 + 30 + 260, line_y + 4), fill=(230, 130, 130), radius=3)
                line_y += 22
            for k in range(3):
                pen.rect((ex0, line_y - 10, sw - 16, line_y + 10), fill=(40, 110, 50, 140))
                pen.rect((ex0 + 30, line_y - 4, ex0 + 30 + (290 if k % 2 else 220), line_y + 4), fill=(140, 220, 150), radius=3)
                line_y += 22
            if mode is not None and (unit == "file" or h == current_hunk):
                pen.rect((ex0 - 6, top - 14, sw - 10, line_y - 10), outline=accent, width=2.5, radius=6)
            line_y += 26

    def base_player(self, pen, t, sw, sh):
        self.base_desktop(pen, t, sw, sh)
        playing = self.tl.value_at("playing", t, True)
        changed = self.tl.changed_at("playing", t)
        x0, y0, x1, y1 = 150, 70, sw - 150, sh - 80
        pen.rect((x0, y0, x1, y1), fill=(24, 22, 32), radius=18)
        pen.rect((x0 + 28, y0 + 28, x0 + 188, y0 + 188), fill=(214, 74, 128), radius=14)
        pen.circle(x0 + 108, y0 + 108, 52, fill=(255, 255, 255, 50))
        pen.circle(x0 + 108, y0 + 108, 14, fill=(24, 22, 32))
        pen.text(x0 + 214, y0 + 60, "Night Drive", "big-shoulders-display", 30, 800, CHALK, "lm")
        pen.text(x0 + 214, y0 + 92, "Example track", "atkinson-hyperlegible-next", 15, 500, HAZE, "lm")
        progress = 0.18 + 0.03 * self._played(t)
        pen.rect((x0 + 214, y0 + 150, x1 - 30, y0 + 156), fill=(255, 255, 255, 40), radius=3)
        pen.rect((x0 + 214, y0 + 150, x0 + 214 + (x1 - x0 - 244) * progress, y0 + 156), fill=CHALK, radius=3)
        cx, cy = (x0 + x1) / 2, y1 - 52
        pen.circle(cx, cy, 30, fill=CHALK)
        if playing:
            pen.rect((cx - 10, cy - 13, cx - 3, cy + 13), fill=(24, 22, 32), radius=2)
            pen.rect((cx + 3, cy - 13, cx + 10, cy + 13), fill=(24, 22, 32), radius=2)
        else:
            pen.poly([(cx - 8, cy - 14), (cx - 8, cy + 14), (cx + 14, cy)], (24, 22, 32))
        if changed is not None and t - changed < 0.6:
            pen.circle(cx, cy, 34 + (t - changed) * 50, outline=(*CHALK, round(200 * (1 - (t - changed) / 0.6))), width=3)
        pen.text(cx, y1 - 100, "Playing" if playing else "Paused", "atkinson-hyperlegible-mono", 13, 600, HAZE, "mm")
        # Now Playing strip below the HUD, so the result stays visible while the HUD is open.
        bx0, by0, bx1, by1 = sw / 2 - 150, sh - 58, sw / 2 + 150, sh - 14
        pen.rect((bx0, by0, bx1, by1), fill=(12, 10, 20, 245), outline=(255, 255, 255, 50), width=1, radius=14)
        icx, icy = bx0 + 24, (by0 + by1) / 2
        if playing:
            pen.rect((icx - 7, icy - 9, icx - 2, icy + 9), fill=CHALK, radius=1.5)
            pen.rect((icx + 2, icy - 9, icx + 7, icy + 9), fill=CHALK, radius=1.5)
        else:
            pen.poly([(icx - 6, icy - 10), (icx - 6, icy + 10), (icx + 9, icy)], CHALK)
        pen.text(bx0 + 46, icy, "Night Drive", "atkinson-hyperlegible-next", 14, 700, CHALK, "lm")
        pen.text(bx1 - 16, icy, "Playing" if playing else "Paused", "atkinson-hyperlegible-mono", 12.5, 600,
                 self.light_rgb["scroll"] if playing else HAZE, "rm")
        if changed is not None and t - changed < 0.7:
            pen.rect((bx0 - 4, by0 - 4, bx1 + 4, by1 + 4), outline=(*CHALK, round(220 * (1 - (t - changed) / 0.7))), width=3, radius=17)

    def _played(self, t):
        total, last, playing = 0.0, 0.0, self.tl.initial.get("playing", True)
        for when, value in self.tl.values.get("playing", []):
            if when > t:
                break
            if playing:
                total += when - last
            last, playing = when, value
        if playing:
            total += t - last
        return total

    # ---- overlays
    def overlay_hud(self, pen, t, sw, sh):
        tl = self.tl
        page = tl.value_at("hud.page", t, "default")
        vscode = bool(tl.value_at("hud.vscode", t, False))
        rows = self.hud_rows(page, vscode)
        cards = self.hud["default"] if page == "default" else self.hud["keys"]
        pen.rect((0, 0, sw, sh), fill=(0, 0, 0, 105))
        columns = max(len(row) for row in rows)
        panel_w = min(sw - 50, 90 + columns * 100)
        gap = 10
        card_w = (panel_w - 36 - gap * (columns - 1)) / columns
        card_h = 62
        panel_h = 48 + len(rows) * card_h + (len(rows) - 1) * gap + 22
        px0, py0 = (sw - panel_w) / 2, (sh - panel_h) / 2 + 8
        pen.rect((px0, py0, px0 + panel_w, py0 + panel_h), fill=(14, 11, 28, 238), outline=(255, 255, 255, 34), width=1, radius=16)
        title = "Default mode" if page == "default" else self.hud["keysTitle"]
        pen.text(sw / 2, py0 + 24, title, "atkinson-hyperlegible-mono", 12, 600, HAZE, "mm")
        origin = (px0 + 18, py0 + 44)

        def box(col, row):
            x = origin[0] + col * (card_w + gap)
            y = origin[1] + row * (card_h + gap)
            return x, y, x + card_w, y + card_h

        highlight = {params.get("cell"): age for age, _, params in tl.active_pulses(t, "highlight", 0.7)}
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                card = cards.get(cell, {"title": str(cell), "fill": (80, 80, 100)})
                x0, y0, x1, y1 = box(c, r)
                pen.rect((x0, y0, x1, y1), fill=(*mix(card["fill"], (0, 0, 0), 0.18), 235), radius=9)
                self._wrap(pen, card["title"], x0 + 8, y1 - 9, card_w - 14)
                if cell in highlight:
                    age = highlight[cell]
                    alpha = round(230 * math.sin(min(1, age / 0.7) * math.pi))
                    pen.rect((x0 - 4, y0 - 4, x1 + 4, y1 + 4), outline=(*CHALK, alpha), width=3, radius=12)
        cx = tl.number("hud.x", t, 3)
        cy = tl.number("hud.y", t, 1)
        pull_x = tl.number("hud.pullX", t, 0.0)
        pull_y = tl.number("hud.pullY", t, 0.0)
        col_f, row_f = cx + pull_x * 0.18, cy + pull_y * 0.18
        x0 = origin[0] + col_f * (card_w + gap) - 5
        y0 = origin[1] + row_f * (card_h + gap) - 5
        stretch_x = abs(pull_x) * 0.12 * card_w
        stretch_y = abs(pull_y) * 0.12 * card_h
        outline = (x0 - (stretch_x if pull_x < 0 else 0), y0 - (stretch_y if pull_y < 0 else 0),
                   x0 + card_w + 10 + (stretch_x if pull_x > 0 else 0), y0 + card_h + 10 + (stretch_y if pull_y > 0 else 0))
        held = tl.value_at("hud.pressed", t, False) or self._middle_operating(t)
        if held:
            pen.dashed_rect(outline, CHALK, 3)
        else:
            pen.rect(outline, outline=CHALK, width=3.5, radius=12)
        for age, _, params in tl.active_pulses(t, "use", 0.5):
            col, row = round(cx), round(cy)
            if 0 <= row < len(rows) and 0 <= col < len(rows[row]):
                x0, y0, x1, y1 = box(col, row)
                pen.rect((x0, y0, x1, y1), fill=(255, 255, 255, round(150 * (1 - age / 0.5))), radius=9)

    def _middle_operating(self, t):
        """A Middle hold that began with the HUD already open operates the card (dashed outline).
        A hold that opened the HUD is still navigating, so its outline stays solid."""
        opened = self.tl.changed_at("hud.open", t)
        for a, b in self.tl.presses["middle"]:
            if a <= t < b and t - a >= self.hold_seconds:
                return opened is not None and a > opened
        return False

    def _wrap(self, pen, text, x, bottom, width):
        words, lines, line = text.split(), [], ""
        for word in words:
            trial = (line + " " + word).strip()
            if text_width("atkinson-hyperlegible-next", 11, 700, trial) > width and line:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
        lines = lines[-3:]
        for i, part in enumerate(reversed(lines)):
            pen.text(x, bottom - i * 13, part, "atkinson-hyperlegible-next", 11, 700, CHALK, "ls")

    def overlay_switcher(self, pen, t, sw, sh):
        apps = self.tl.value_at("switcher.apps", t, [])
        index = int(self.tl.number("switcher.index", t, 1))
        tile, gap = 74, 18
        width = len(apps) * tile + (len(apps) - 1) * gap + 40
        x0, y0 = (sw - width) / 2, sh / 2 - 70
        pen.rect((x0, y0, x0 + width, y0 + 140), fill=(40, 38, 52, 235), outline=(255, 255, 255, 50), width=1, radius=22)
        for i, app in enumerate(apps):
            x = x0 + 20 + i * (tile + gap)
            if i == index:
                pen.rect((x - 8, y0 + 14, x + tile + 8, y0 + 126), fill=(255, 255, 255, 50), radius=14)
            rgb = APP_COLOURS.get(app, (80, 80, 100))
            pen.rect((x, y0 + 22, x + tile, y0 + 22 + tile), fill=rgb, radius=16)
            pen.text(x + tile / 2, y0 + 22 + tile / 2, app[:1], "big-shoulders-display", 34, 800, CHALK, "mm")
            pen.text(x + tile / 2, y0 + 114, app, "atkinson-hyperlegible-next", 11.5, 650, CHALK if i == index else HAZE, "mm")

    def overlay_recorder(self, pen, t, sw, sh):
        x0, y0, x1, y1 = sw / 2 - 120, sh - 54, sw / 2 + 120, sh - 14
        pen.rect((x0, y0, x1, y1), fill=(8, 8, 10, 245), outline=(255, 255, 255, 40), width=1, radius=20)
        pen.circle(x0 + 22, (y0 + y1) / 2, 6, fill=self.light_rgb["recording"])
        for k in range(22):
            height = 4 + 11 * abs(math.sin(t * 7.3 + k * 0.9) * math.sin(t * 2.1 + k * 0.37))
            x = x0 + 44 + k * 8
            pen.rect((x, (y0 + y1) / 2 - height, x + 4, (y0 + y1) / 2 + height), fill=(230, 230, 236), radius=2)

    def overlay_badge(self, pen, t, sw, sh, text):
        width = text_width("atkinson-hyperlegible-next", 13, 650, text) + 44
        x1, y1 = sw - 16, sh - 66 if self.tl.value_at("recording", t, False) else sh - 16
        x0, y0 = x1 - width, y1 - 32
        mode = self.tl.value_at("review.mode", t, None)
        rgb = self.light_rgb["files"] if mode == "files" else self.light_rgb["app"]
        for age, _, _ in self.tl.active_pulses(t, "badge", 1.0):
            pen.rect((x0 - 6, y0 - 6, x1 + 6, y1 + 6), outline=(*CHALK, round(220 * math.sin(min(1, age) * math.pi))), width=3, radius=20)
        pen.rect((x0, y0, x1, y1), fill=(14, 11, 28, 240), outline=(*rgb, 160), width=1.5, radius=16)
        pen.circle(x0 + 18, (y0 + y1) / 2, 5, fill=rgb)
        pen.text(x0 + 30, (y0 + y1) / 2, text, "atkinson-hyperlegible-next", 13, 650, CHALK, "lm")

    def overlay_toast(self, pen, t, sw, sh):
        for age, _, params in self.tl.active_pulses(t, "use", 1.4):
            cards = self.hud["default"]
            page = self.tl.value_at("hud.page", t, "default")
            if page == "keys":
                cards = self.hud["keys"]
            rows = self.hud_rows(page, bool(self.tl.value_at("hud.vscode", t, False)))
            col, row = round(self.tl.number("hud.x", t, 3)), round(self.tl.number("hud.y", t, 1))
            title = cards.get(rows[row][col], {}).get("title", "") if 0 <= row < len(rows) and 0 <= col < len(rows[row]) else ""
            alpha = round(255 * min(1, age / 0.15, max(0, (1.4 - age) / 0.3)))
            width = text_width("atkinson-hyperlegible-next", 14, 700, title) + 40
            pen.rect((sw / 2 - width / 2, 34, sw / 2 + width / 2, 66), fill=(*CHALK, alpha), radius=16)
            pen.text(sw / 2, 50, title, "atkinson-hyperlegible-next", 14, 700, (19, 14, 41, alpha), "mm")

    def overlay_pointer(self, pen, t, sw, sh):
        tl = self.tl
        px, py = self.pointer_px(t, sw, sh)
        for age, _, _ in tl.active_pulses(t, "follow", 0.7):
            pen.circle(px, py, 8 + age * 50, outline=(*self.light_rgb["mouse"], round(230 * (1 - age / 0.7))), width=3)
        for age, _, _ in tl.active_pulses(t, "dwell", 0.25):
            sweep = min(1, age / 0.22)
            pen.draw.arc((pen.s(px - 16), pen.s(py - 16), pen.s(px + 16), pen.s(py + 16)), -90, -90 + 360 * sweep,
                         fill=(*CHALK, 220), width=pen.s(3))
        for age, _, _ in tl.active_pulses(t, "click", 0.5):
            pen.circle(px, py, 6 + age * 60, outline=(*CHALK, round(240 * (1 - age / 0.5))), width=3)
        if tl.value_at("hud.open", t, False) or tl.value_at("switcher.open", t, False):
            return
        down = tl.value_at("pointer.down", t, False)
        scale = 0.9 if down else 1.0
        points = [(0, 0), (0, 23), (5.6, 17.6), (9.4, 26.4), (13.2, 24.8), (9.6, 16.4), (17, 16.4)]
        shape = [(px + x * scale, py + y * scale) for x, y in points]
        pen.poly([(x + 1.5, y + 2) for x, y in shape], (0, 0, 0, 90))
        pen.line(shape + [shape[0]], (255, 255, 255), 2.4)
        pen.poly(shape, (0, 0, 0))
        if down:
            pen.circle(px + 18, py + 26, 6, fill=self.light_rgb["mouse"], outline=CHALK, width=1.5)
