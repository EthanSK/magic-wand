#!/usr/bin/env python3
"""Render R6's exported carrier and dimensioned comparison: `python render.py`.

The per-pixel depth-buffer method is adapted from the original carbon-holder
verify_and_render.py. Pillow composes the panels without a browser or GUI.
The 20mm comparison uses the same corrected R4 seats, not legacy R2 seats.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh
import cad

BACKGROUND = (245, 244, 239)
INK = (25, 38, 49)


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def projection(bounds: np.ndarray, width: int, height: int, angles: tuple[float, float]) -> tuple:
    """Extraction of the existing raster camera math for accurate dimension marks."""
    elevation, azimuth = np.radians(angles)
    front = np.array([np.cos(elevation)*np.cos(azimuth), np.cos(elevation)*np.sin(azimuth), np.sin(elevation)])
    right = np.array([-np.sin(azimuth), np.cos(azimuth), 0])
    basis = np.array([right, np.cross(front, right), front]).T
    corners = np.array([[x, y, z] for x in bounds[:, 0] for y in bounds[:, 1] for z in bounds[:, 2]]) @ basis
    lo, hi = corners[:, :2].min(0), corners[:, :2].max(0)
    scale = min((width-40)/(hi[0]-lo[0]), (height-40)/(hi[1]-lo[1]))
    centre = (lo+hi)/2
    return basis, scale, centre


def raster(objects: list, width: int = 900, height: int = 610,
           bounds: np.ndarray | None = None, angles: tuple[float, float] = (48, -67)) -> Image.Image:
    """Render actual triangle meshes with the established holder depth buffer."""
    if bounds is None:
        bounds = np.array([[-32, -23, -11], [32, 53, 21]])
    basis, scale, centre = projection(bounds, width, height, angles)
    image = np.full((height, width, 3), BACKGROUND, dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    for mesh, color in objects:
        shade = .62 + .38 * np.clip(mesh.face_normals @ np.array([.3, -.35, .9]), 0, 1)
        colors = shade[:, None] * np.array(color)
        triangles = mesh.triangles @ basis
        triangles[:, :, :2] = (triangles[:, :, :2] - centre) * scale + [width/2, height/2]
        triangles[:, :, 1] = height - triangles[:, :, 1]
        for triangle, rgb in zip(triangles, colors):
            x0, y0 = np.maximum(0, np.floor(triangle[:, :2].min(0)).astype(int))
            x1, y1 = np.minimum([width-1, height-1], np.ceil(triangle[:, :2].max(0)).astype(int))
            if x1 < x0 or y1 < y0:
                continue
            a, b, c = triangle
            denominator = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
            if abs(denominator) < 1e-10:
                continue
            yy, xx = np.mgrid[y0:y1+1, x0:x1+1]
            xx, yy = xx+.5, yy+.5
            wa = ((b[1]-c[1])*(xx-c[0]) + (c[0]-b[0])*(yy-c[1]))/denominator
            wb = ((c[1]-a[1])*(xx-c[0]) + (a[0]-c[0])*(yy-c[1]))/denominator
            wc = 1-wa-wb
            zz = wa*a[2] + wb*b[2] + wc*c[2]
            region = depth[y0:y1+1, x0:x1+1]
            mask = (wa >= -1e-6) & (wb >= -1e-6) & (wc >= -1e-6) & (zz > region)
            region[mask] = zz[mask]
            image[y0:y1+1, x0:x1+1][mask] = rgb.astype(np.uint8)
    return Image.fromarray(image)


def objects(carrier: trimesh.Trimesh, pitch: float, loaded: bool = True) -> list:
    result = [(carrier, (36, 157, 162))]
    for name, shape in cad.references(pitch).items():
        if not loaded and name != "rod":
            continue
        color = (48, 55, 65) if name == "rod" else (113, 128, 150) if name == "battery" else (226, 229, 233)
        result.append((cad.r4.mesh(shape), color))
    return result


def render_placement() -> None:
    """Show the actual butt-zero GLB and the assumed lower cap edge on its full rod."""
    scene = trimesh.load(cad.OUT / "Assembly-reference.glb", force="scene")
    shapes = []
    for node in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node]
        mesh = scene.geometry[geometry_name].copy()
        mesh.apply_transform(transform)
        color = (36, 157, 162) if node == "Key_Battery_Carrier" else (48, 55, 65) if node == "REFERENCE_rod" else (113, 128, 150) if node == "REFERENCE_battery" else (237, 166, 73) if node == "XIAO_Rod_Holder" else (54, 110, 75) if node == "REFERENCE_pcb" else (175, 74, 60) if node == "REFERENCE_provisional_wire_route" else (187, 192, 202) if node == "REFERENCE_usb" else (226, 229, 233)
        shapes.append((mesh, color))
    placement = cad.reference_placement()
    length = placement["overall_length"]
    tube_length = placement["rod_length"]
    overhang = placement["tip_seating"]["positive_end_overhang_mm"]
    edge = placement["lower_cap_edge_from_butt_mm"]
    canvas = Image.new("RGB", (1800, 700), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((45, 25), f"Physical {placement['physical_brief_alias']} brief: {length:g} mm overall design envelope", fill=INK, font=font(39))
    draw.text((45, 80), f"{tube_length:g} mm tube + {overhang:g} mm provisional tip-wire envelope; lower cap edge {edge:g} mm from butt", fill=INK, font=font(25))
    draw.text((45, 116), f"Carrier moved {abs(placement['carrier_move_from_existing_layout_mm']):g} mm toward the butt from the existing 100 mm cap edge; hand fit unmeasured.", fill=INK, font=font(18))
    bounds = np.array([[-35, -5, -12], [35, length+5, 22]])
    width, height, left, top = 1700, 390, 50, 140
    canvas.paste(raster(shapes, width, height, bounds, (90, 0)), (left, top))
    basis, scale, centre = projection(bounds, width, height, (90, 0))
    def screen_x(y: float) -> float:
        return float(((np.array([0, y, 0]) @ basis)[0] - centre[0])*scale + width/2 + left)
    start, end, cap_edge = screen_x(0), screen_x(length), screen_x(edge)
    for y, a, b in [(545, start, end), (595, start, cap_edge)]:
        draw.line((a, y, b, y), fill=INK, width=2)
        for x in [a, b]:
            draw.line((x, y-10, x, y+10), fill=INK, width=2)
    draw.text((start, 505), "Butt: 0 mm", fill=INK, font=font(23))
    draw.text((end-220, 505), f"Overall end: {length:g} mm", fill=INK, font=font(23))
    draw.text(((start+end)/2-100, 550), f"{length:g} mm overall", fill=INK, font=font(23))
    draw.text(((start+cap_edge)/2-90, 603), f"{edge:g} mm to cap edge", fill=INK, font=font(22))
    draw.text((45, 657), "Includes the unchanged tip frame, board, USB and provisional wire route. Fit and end allowance are not physically measured.",
              fill=(112, 67, 31), font=font(21))
    canvas.save(cad.OUT / "Assembly-placement.png")


def render() -> None:
    keys = cad.P["keys"]
    baseline_pitch, candidate_pitch = keys["baseline_pitch"], keys["pitch"]
    reduction = baseline_pitch - candidate_pitch
    manifest = json.loads((cad.OUT / "manifest.json").read_text())
    actual = trimesh.load_mesh(cad.OUT / "Key_Battery_Carrier-assembly.stl")
    assert cad.r4.sha(cad.OUT / "Key_Battery_Carrier-assembly.stl") == manifest["parts"]["Key_Battery_Carrier"]["assembly_stl_sha256"]
    baseline = cad.r4.mesh(cad.carrier(baseline_pitch))
    canvas = Image.new("RGB", (1800, 1580), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text((45, 30), "Three keys, closer together", fill=INK, font=font(44))
    draw.text((45, 88), f"R6 close-up | {candidate_pitch:g} mm centres | full tube and placement shown in Assembly-placement.png", fill=INK, font=font(24))
    for xy, title, shapes in [((0, 155), f"{baseline_pitch:g} mm reference spacing", objects(baseline, baseline_pitch)),
                              ((900, 155), f"{candidate_pitch:g} mm proposed spacing", objects(actual, candidate_pitch)),
                              ((0, 820), "R6 actual exported frame", objects(actual, candidate_pitch, False))]:
        canvas.paste(raster(shapes), xy)
        draw.text((xy[0]+45, xy[1]-5), title, fill=INK, font=font(29))
    draw.text((945, 820), "Dimensioned top view - cap envelopes", fill=INK, font=font(27))
    # This diagram is deliberately labelled as an envelope, separate from the
    # exact STL panels. Both rows use one drawing scale and the same cap size.
    for y, pitch in [(905, baseline_pitch), (1170, candidate_pitch)]:
        scale, cx = 11, 1335
        half_width = keys["cap_reference_width"] * scale / 2
        cap_length = keys["cap_reference_length"] * scale
        for x in [-pitch, 0, pitch]:
            px = cx+x*scale
            draw.rounded_rectangle((px-half_width, y, px+half_width, y+cap_length), radius=13,
                                   fill=(224, 228, 230), outline=(90, 105, 115), width=2)
            draw.ellipse((px-3, y+cap_length/2-3, px+3, y+cap_length/2+3), fill=INK)
        left, right = cx-pitch*scale, cx+pitch*scale
        draw.line((left, y-18, right, y-18), fill=INK, width=2)
        for x in [left, cx, right]:
            draw.line((x, y-28, x, y-8), fill=INK, width=2)
        draw.text((965, y+202), f"{pitch:g} mm centres / {2*pitch:g} mm outer span", fill=INK, font=font(24))
    draw.text((45, 1450), f"{reduction:g} mm less travel to the next key; {2*reduction:g} mm less between the outer keys ({100*reduction/baseline_pitch:g}%).", fill=INK, font=font(26))
    draw.text((45, 1500), "CAD prototype only. White cap underside, full travel, print fit, strength and comfort remain unverified.",
              fill=(112, 67, 31), font=font(23))
    canvas.save(cad.OUT / "Design-preview.png")
    render_placement()
    receipt = {"generator_sha256": cad.r4.sha(Path(__file__)), "manifest_sha256": cad.r4.sha(cad.OUT / "manifest.json"),
               "image_sha256": cad.r4.sha(cad.OUT / "Design-preview.png"),
               "placement_image_sha256": cad.r4.sha(cad.OUT / "Assembly-placement.png"),
               "assembly_glb_sha256": cad.r4.sha(cad.OUT / "Assembly-reference.glb"),
               "candidate_uses_exported_stl": True, "baseline_uses_same_corrected_seats_at_20mm": True,
               "source_renderer": "../carbon-rod-holders/verify_and_render.py"}
    (cad.OUT / "render-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Rendered exported R6 carrier and dimensioned 20/18.5 mm comparison.")


if __name__ == "__main__":
    render()
