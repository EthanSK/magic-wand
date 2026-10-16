#!/usr/bin/env python3
"""Draw the Magic Wand mark (SVG and PNG sizes) and the social card from one set of shapes.

    python3 scripts/make_images.py

Needs Pillow. The mark is original artwork: the Wand Receiver icon's night violet, a carbon shaft
and a Puck.js tip ringed by the wand's four mode colours. It replaces the emoji-based receiver icon
for public use. The card uses the vendored fonts.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MANIFEST = json.loads((ROOT / "wand.json").read_text())
NIGHT = "#1f173d"
DISPLAY = {light["mode"]: light["display"] for light in MANIFEST["lights"]}
RING = [DISPLAY["mouse"], DISPLAY["hud"], DISPLAY["recording"], DISPLAY["scroll"]]  # Pointer, HUD, speech, scroll

# The mark, in a 64-unit square.
MARK = {
    "radius": 14,
    "grip": ((10, 55), (19, 46), 7),
    "shaft": ((17, 48), (42, 23), 3.4),
    "tip": (46, 19),
    "puck": 6.4,
    "led": 2.1,
    "ring": 10,
    "ring_width": 2.3,
}


def mark_svg() -> str:
    (gx1, gy1), (gx2, gy2), gw = MARK["grip"]
    (sx1, sy1), (sx2, sy2), sw = MARK["shaft"]
    tx, ty = MARK["tip"]
    r = MARK["ring"]
    arcs = []
    for index, color in enumerate(RING):
        start = -135 + index * 90 + 8
        end = start + 74
        import math
        x1 = tx + r * math.cos(math.radians(start))
        y1 = ty + r * math.sin(math.radians(start))
        x2 = tx + r * math.cos(math.radians(end))
        y2 = ty + r * math.sin(math.radians(end))
        arcs.append(f'<path d="M{x1:.2f} {y1:.2f}A{r} {r} 0 0 1 {x2:.2f} {y2:.2f}" stroke="{color}"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <title>Magic Wand</title>
  <defs><radialGradient id="glow"><stop offset="0" stop-color="{DISPLAY['mouse']}" stop-opacity=".55"/><stop offset="1" stop-color="{DISPLAY['mouse']}" stop-opacity="0"/></radialGradient></defs>
  <rect width="64" height="64" rx="{MARK['radius']}" fill="{NIGHT}"/>
  <circle cx="{tx}" cy="{ty}" r="16" fill="url(#glow)"/>
  <line x1="{sx1}" y1="{sy1}" x2="{sx2}" y2="{sy2}" stroke="#3a3744" stroke-width="{sw}" stroke-linecap="round"/>
  <line x1="{sx1 + 0.6}" y1="{sy1 - 0.9}" x2="{sx2 + 0.3}" y2="{sy2 - 0.6}" stroke="#6f6a80" stroke-width=".8" stroke-linecap="round"/>
  <line x1="{gx1}" y1="{gy1}" x2="{gx2}" y2="{gy2}" stroke="#0f0c16" stroke-width="{gw}" stroke-linecap="round"/>
  <g fill="none" stroke-width="{MARK['ring_width']}" stroke-linecap="round">{''.join(arcs)}</g>
  <circle cx="{tx}" cy="{ty}" r="{MARK['puck']}" fill="#ece8f4"/>
  <circle cx="{tx}" cy="{ty}" r="{MARK['led']}" fill="{DISPLAY['mouse']}"/>
</svg>
"""


def draw_mark(size: int, background: bool = True) -> Image.Image:
    scale = size / 64 * 4  # Supersample for clean edges.
    canvas = int(64 * scale)
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    s = lambda value: value * scale  # noqa: E731
    if background:
        draw.rounded_rectangle((0, 0, canvas - 1, canvas - 1), radius=s(MARK["radius"]), fill=NIGHT)
    tx, ty = MARK["tip"]
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((s(tx - 9), s(ty - 9), s(tx + 9), s(ty + 9)), fill=DISPLAY["mouse"] + "a0")
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s(5))))

    def stroke(points, width, color):
        (x1, y1), (x2, y2) = points
        draw.line((s(x1), s(y1), s(x2), s(y2)), fill=color, width=round(s(width)))
        for x, y in points:
            draw.ellipse((s(x) - s(width) / 2, s(y) - s(width) / 2, s(x) + s(width) / 2, s(y) + s(width) / 2), fill=color)

    stroke(MARK["shaft"][:2], MARK["shaft"][2], "#3a3744")
    stroke(MARK["grip"][:2], MARK["grip"][2], "#0f0c16")
    r = MARK["ring"]
    for index, color in enumerate(RING):
        start = -135 + index * 90 + 8
        draw.arc((s(tx - r), s(ty - r), s(tx + r), s(ty + r)), start, start + 74, fill=color, width=round(s(MARK["ring_width"])))
    p = MARK["puck"]
    draw.ellipse((s(tx - p), s(ty - p), s(tx + p), s(ty + p)), fill="#ece8f4")
    led = MARK["led"]
    draw.ellipse((s(tx - led), s(ty - led), s(tx + led), s(ty + led)), fill=DISPLAY["mouse"])
    return image.resize((size, size), Image.LANCZOS)


def font(name: str, size: int, weight: int) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(str(DOCS / "fonts" / name), size)
    try:
        face.set_variation_by_axes([weight])
    except OSError:
        pass
    return face


def social_card() -> Image.Image:
    width, height = 1200, 630
    image = Image.new("RGBA", (width, height), NIGHT)
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((760, 70, 1100, 410), fill=DISPLAY["mouse"] + "90")
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))
    draw = ImageDraw.Draw(image)
    # Dot grid, as on the demo stage.
    for x in range(30, width, 30):
        for y in range(30, height, 30):
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(255, 255, 255, 18))
    # The wand, large, rising from the lower right toward the glow.
    supersample = 3
    wand = Image.new("RGBA", (width * supersample, height * supersample), (0, 0, 0, 0))
    w = ImageDraw.Draw(wand)
    k = supersample
    shaft = [(1150 * k, 700 * k), (930 * k, 240 * k)]
    w.line(shaft[0] + shaft[1], fill="#3a3744", width=16 * k)
    w.line(((1144 + 3) * k, 700 * k, (925 + 3) * k, 240 * k), fill="#6f6a80", width=3 * k)
    w.line((1200 * k, 800 * k, 1135 * k, 668 * k), fill="#0f0c16", width=34 * k)
    for index, color in enumerate(RING):
        start = -135 + index * 90 + 8
        w.arc((870 * k, 170 * k, 1010 * k, 310 * k), start, start + 74, fill=color, width=7 * k)
    w.ellipse((894 * k, 194 * k, 986 * k, 286 * k), fill="#ece8f4")
    w.ellipse((928 * k, 228 * k, 952 * k, 252 * k), fill=DISPLAY["mouse"])
    image.alpha_composite(wand.resize((width, height), Image.LANCZOS))
    title = font("big-shoulders-display.woff2", 168, 800)
    body = font("atkinson-hyperlegible-next.woff2", 34, 600)
    small = font("atkinson-hyperlegible-mono.woff2", 24, 500)
    draw.text((72, 132), "Magic Wand", font=title, fill="#f2eff9")
    tagline = MANIFEST["tagline"]
    words, lines, line = tagline.split(), [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=body) > 640:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    for index, text in enumerate(lines):
        draw.text((76, 342 + index * 46), text, font=body, fill="#f2eff9")
    draw.text((76, 540), "ethansk.github.io/magic-wand", font=small, fill="#aea7cf")
    return image.convert("RGB")


def main() -> None:
    (DOCS / "assets").mkdir(exist_ok=True)
    (DOCS / "icon.svg").write_text(mark_svg())
    for size in (32, 180, 192, 512):
        draw_mark(size).save(DOCS / "assets" / f"icon-{size}.png", optimize=True)
    social_card().save(DOCS / "assets" / "social.png", optimize=True)
    draw_mark(1024).save(ROOT / "receiver" / "AppIcon.icns", format="ICNS")
    print("Wrote docs/icon.svg, docs/assets/icon-{32,180,192,512}.png docs/assets/social.png and receiver/AppIcon.icns")


if __name__ == "__main__":
    main()
