"""Review pictures of the exported R53 bodies with the bought-part references.

Run in a fresh process after build53.py. Writes PNG files into exports/review.
"""
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import build53 as b

sys.path.insert(0, str(b.R52))
sys.path.insert(0, str(b.R51))
import build52 as d  # noqa: E402

COLOURS = dict(carrier="#b03a2e", paddle="#e67e22", cap="#f4d03f", lid="#48c9b0", post_bar="#af7ac5", board="#1e8449",
               sockets="#b7950b", housing="#ecf0f1", plug="#bdc3c7", switch="#34495e", plunger="#e74c3c", wire="#8e44ad",
               touch="#2e86c1", clips="#f7dc6f")


def triangles(solid):
    mesh = solid.to_mesh()
    return np.asarray(mesh.vert_properties)[:, :3][np.asarray(mesh.tri_verts)]


def render(items, direction, up, scale, size, centre):
    forward = np.array(direction, float)
    forward /= np.linalg.norm(forward)
    right = np.cross(np.array(up, float), forward)
    right /= np.linalg.norm(right)
    upward = np.cross(forward, right)
    basis = np.stack((right, upward, forward))
    points = np.concatenate([t for t, _ in items])
    colours = np.concatenate([np.broadcast_to(c, (len(t), 3)) for t, c in items])
    normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    facing = normals @ forward > 1e-9
    points, normals, colours = points[facing], normals[facing], colours[facing]
    normals /= np.maximum(1e-10, np.linalg.norm(normals, axis=1))[:, None]
    light = 0.80 * forward - 0.34 * right + 0.45 * upward
    light /= np.linalg.norm(light)
    rgb = np.clip(colours * (0.50 + 0.50 * np.maximum(0, normals @ light))[:, None], 0, 255).astype("uint8")
    view = (points - np.asarray(centre, float)) @ basis.T
    width, height = size
    xy = view[:, :, :2] * [scale, -scale] + np.array(size) / 2
    vertices = np.concatenate((xy, view[:, :, 2:3]), axis=2)
    pixels = np.full((height, width, 3), (24, 31, 37), np.uint8)
    depth = np.full((height, width), -np.inf)
    low = np.maximum(np.ceil(xy.min(axis=1) - 0.5).astype(int), 0)
    high = np.minimum(np.floor(xy.max(axis=1) - 0.5).astype(int), [width - 1, height - 1])
    for i in np.flatnonzero(np.all(high >= low, axis=1)):
        x, y = low[i]
        xx, yy = high[i]
        a, bb, c = vertices[i]
        u, v = bb - a, c - a
        det = u[0] * v[1] - u[1] * v[0]
        if abs(det) < 1e-10:
            continue
        dx = np.arange(x, xx + 1) + 0.5 - a[0]
        dy = np.arange(y, yy + 1)[:, None] + 0.5 - a[1]
        s = (dx * v[1] - dy * v[0]) / det
        t = (u[0] * dy - u[1] * dx) / det
        z = a[2] + s * u[2] + t * v[2]
        window = depth[y:yy + 1, x:xx + 1]
        hit = (s >= -1e-9) & (t >= -1e-9) & (s + t <= 1 + 1e-9) & (z > window)
        window[hit] = z[hit]
        pixels[y:yy + 1, x:xx + 1][hit] = rgb[i]
    return Image.fromarray(pixels)


def main(source=None):
    source = Path(source) if source else b.EXPORT
    out = source / "review"
    out.mkdir(exist_ok=True)
    d.old.configure_new_op1()
    hardware = d.q.hardware()
    shift = (0.0, d.r.CLICK_SHIFT, 0.0)
    solids = dict(
        carrier=b.load(source / "Key_Carrier-assembly.stl"), paddle=b.load(source / "Touch_Paddle-assembly.stl"),
        cap=b.load(source / "Hinge_Cap-assembly.stl"), lid=b.load(source / "OP1_Lid-assembly.stl"),
        post_bar=b.load(source / "DFR_Post_Bar-assembly.stl"), board=hardware["board"], sockets=hardware["sockets"],
        housing=hardware["housing"], plug=hardware["plug"], switch=hardware["switch"], plunger=hardware["plunger"],
        wire=hardware["op1_wire"], touch=(d.r.sensor() + d.r.connector()).translate(shift), clips=d.r.clips().translate(shift))
    riding = ("paddle", "post_bar", "touch", "clips")
    stop = 1.466

    def scene(names, clip=None, angle=0.0):
        items = []
        for name in names:
            solid = solids[name]
            if angle and name in riding:
                solid = b.posed(solid, angle)
            if clip:
                solid = solid ^ b.box(*clip)
            if not solid.is_empty():
                items.append((triangles(solid), tuple(bytes.fromhex(COLOURS[name][1:]))))
        return items

    everything = list(solids)
    views = {
        "assembly-front-left": ("Assembled, front left", everything, None, 0, (-0.5, -0.7, 0.55), (0, 0, 1), 22, (1400, 940), (0, 10, 13)),
        "assembly-rear-right": ("Assembled, rear right, touch board hidden", [n for n in everything if n not in ("touch", "clips")], None, 0,
                                (0.55, 0.7, 0.5), (0, 0, 1), 22, (1400, 940), (0, 12, 13)),
        "carrier-centre": ("Key holder centre: pocket, lid rails and hinge yoke", ["carrier"], (-14, 15, -20, 34, -10, 30), 0,
                           (-0.5, -0.7, 0.55), (0, 0, 1), 28, (1400, 1100), (0, 8, 11)),
        "carrier-rear": ("Hinge yoke from the rear", ["carrier"], (-14, 15, -20, 34, -10, 30), 0, (-0.5, 0.75, 0.5), (0, 0, 1), 28, (1400, 1100), (0, 14, 12)),
        "paddle-underside": ("Paddle underside: sleeve, two crowns, axle bar", ["paddle"], None, 0, (-0.5, 0.5, -0.7), (0, 0, -1), 28, (1400, 1000), (0, 10, 17)),
        "loose-parts": ("Hinge cap, post bar and lid", ["cap", "post_bar", "lid"], None, 0, (-0.4, -0.6, 0.7), (0, 0, 1), 28, (1400, 940), (0, 10, 15)),
        "section-rest": ("Section through the plunger, at rest", everything, (-40, 0.4, -40, 60, -10, 40), 0, (1, 0, 0), (0, 0, 1), 32, (1600, 600), (0, 11, 13)),
        "section-pressed": ("Section through the plunger, pressed onto the switch case", everything, (-40, 0.4, -40, 60, -10, 40), stop,
                            (1, 0, 0), (0, 0, 1), 32, (1600, 600), (0, 11, 13)),
        "section-journal": ("Section through one axle journal", everything, (-40, 8.5, -40, 60, -10, 40), 0, (1, 0, 0), (0, 0, 1), 56, (1000, 720), (0, 29, 17)),
        "section-towers": ("Section across the switch at the lid towers", everything, (-40, 40, -5, 60, -10, 40), 0, (0, -1, 0), (0, 0, 1), 42, (1400, 660), (0, 0, 14)),
        "top-without-paddle": ("Top view with the paddle removed", ["carrier", "lid", "board", "switch", "plunger", "wire", "housing"],
                               (-14, 15, -16, 34, -10, 30), 0, (0, 0, 1), (0, 1, 0), 28, (1000, 1400), (0.5, 9, 10)),
    }
    font = ImageFont.load_default(size=22)
    for name, (label, names, clip, angle, direction, up, scale, size, centre) in views.items():
        image = render(scene(names, clip, angle), direction, up, scale, size, centre)
        ImageDraw.Draw(image).text((14, 10), label, font=font, fill="white")
        image.save(out / f"R53-{name}.png")
        print(name, flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
