"""Print poses for the five R53 bodies and a layer-by-layer check of what each layer rests on.

The plate, bed-contact bases, slicing and the printer file belong to the packaging step.
This script fixes each body's orientation, exports it in that pose and reports every
section that starts in mid-air or grows faster than 45 degrees at a 0.2 mm layer.
"""
import json
from hashlib import sha256
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
import trimesh

import build53 as b

LAYER = 0.2
# name: (Euler rotation in degrees applied in the assembly frame, face on the bed, face that ends up on top)
POSES = {
    "Key_Carrier": ((-90, 0, 0), "rear face, as R52", "front edge under the three-key row"),
    "Touch_Paddle": ((180, 0, 90), "flat top that carries the touch board", "sleeve rim, crowns and axle"),
    "Hinge_Cap": ((180, 0, 0), "flat top", "flat journal retainer and latch groove"),
    "OP1_Lid": ((0, 0, 0), "flat underside", "two towers and one grip rib"),
    "OP1_Lid_Close": ((0, 0, 0), "flat underside", "two towers and two grip ribs"),
    "DFR_Post_Bar": ((0, 0, 0), "underside of the bar", "two posts"),
}
SUPPORT = {
    "Key_Carrier": "Support disabled. Every finished component has its own removable external base.",
    "Touch_Paddle": "None.", "Hinge_Cap": "None.", "OP1_Lid": "None.", "OP1_Lid_Close": "None.",
    "DFR_Post_Bar": "None. The two post necks keep the R48 shape so the existing clips fit.",
}


def pose(solid, angles):
    turned = solid.rotate(tuple(float(a) for a in angles))
    low = np.asarray(turned.bounding_box()[:3])
    matrix = trimesh.transformations.euler_matrix(*np.deg2rad(angles))
    matrix[:3, 3] = -low
    return turned.translate(tuple(-low)), matrix


def layers(body):
    """Per layer: section area, area starting in mid-air, area beyond a 45 degree step."""
    height = body.bounding_box()[5]
    previous = None
    rows = []
    for index, z in enumerate(np.arange(LAYER / 2, height, LAYER), start=1):
        section = body.slice(float(z))
        if previous is None:
            rows.append(dict(layer=index, area=section.area(), islands=[], steep=[]))
        else:
            grown = previous.offset(LAYER + 0.012, mf.JoinType.Round, 2.0, 16)
            islands, steep = [], []
            for part in section.decompose():
                if part.area() >= 0.03 and (part ^ previous).area() < 0.004:
                    islands.append(part)
            beyond = section - grown
            for part in beyond.decompose():
                if part.area() >= 0.03:
                    steep.append(part)
            rows.append(dict(layer=index, area=section.area(), islands=islands, steep=steep))
        previous = section
    return rows


def to_assembly(bounds, z, inverse):
    x0, y0, x1, y1 = bounds
    corners = np.array([[x, y, zz, 1.0] for x in (x0, x1) for y in (y0, y1) for zz in (z - LAYER / 2, z + LAYER / 2)])
    world = corners @ inverse.T
    return [round(float(v), 2) for v in (*world[:, :3].min(axis=0), *world[:, :3].max(axis=0))]


def summarise(rows, inverse, limit=None):
    out = dict(islands=[], steep=[])
    for row in rows:
        z = (row["layer"] - 0.5) * LAYER
        for kind in ("islands", "steep"):
            for part in row[kind]:
                box = to_assembly(part.bounds(), z, inverse)
                if limit is not None and not (limit[0] <= (box[0] + box[3]) / 2 <= limit[1]):
                    continue
                out[kind].append(dict(layer=row["layer"], area_mm2=round(part.area(), 3), assembly_bounds_mm=box))
    return out


def merge(items, reach=0.6):
    """Group per-layer findings into features so the report stays readable."""
    groups = []
    for item in items:
        box = np.array(item["assembly_bounds_mm"])
        for group in groups:
            g = group["box"]
            if np.all(box[:3] <= g[3:] + reach) and np.all(g[:3] <= box[3:] + reach):
                g[:3] = np.minimum(g[:3], box[:3])
                g[3:] = np.maximum(g[3:], box[3:])
                group["layers"].add(item["layer"])
                group["peak"] = max(group["peak"], item["area_mm2"])
                break
        else:
            groups.append(dict(box=box.copy(), layers={item["layer"]}, peak=item["area_mm2"]))
    return [dict(assembly_bounds_mm=[round(float(v), 2) for v in g["box"]], layers=[min(g["layers"]), max(g["layers"])],
                 peak_area_mm2=g["peak"]) for g in sorted(groups, key=lambda g: -g["peak"])]


def main(source=None):
    source = Path(source) if source else b.EXPORT
    out = source / "print"
    out.mkdir(parents=True, exist_ok=True)
    spec = dict(units="mm", layer_height_mm=LAYER, physical_print_verified=False, parts={})
    for name, (angles, bed_face, top_face) in POSES.items():
        solid = b.load(source / f"{name}-assembly.stl")
        body, matrix = pose(solid, angles)
        path = out / f"{name}-print.stl"
        b.save(path, body)
        mesh = trimesh.load_mesh(path)
        if not mesh.is_volume:
            indexed = body.to_mesh()
            vertices = np.array(indexed.vert_properties[:, :3], dtype=np.float64)
            _, groups, counts = np.unique(vertices, axis=0, return_inverse=True, return_counts=True)
            same = counts[groups] > 1
            vertices[same] += np.random.default_rng(53).uniform(-0.00018, 0.00018, (same.sum(), 3))
            trimesh.Trimesh(vertices, indexed.tri_verts, process=False).export(path)
            mesh = trimesh.load_mesh(path)
        if not mesh.is_volume:
            raise ValueError(f"{name} print pose is not a closed solid")
        inverse = np.linalg.inv(matrix)
        rows = layers(body)
        centre_only = (b.ZONE[0], b.ZONE[1]) if name == "Key_Carrier" else None
        found = summarise(rows, inverse, centre_only)
        size = [round(float(v), 3) for v in body.bounding_box()[3:]]
        record = dict(
            file=f"print/{name}-print.stl", sha256=sha256(path.read_bytes()).hexdigest(),
            assembly_to_print=[[round(float(v), 9) for v in row] for row in matrix.tolist()],
            size_mm=size, bed_face=bed_face, top_face=top_face, first_layer_contact_mm2=round(rows[0]["area"], 2),
            volume_mm3=round(float(mesh.volume), 2), support=SUPPORT[name],
            sections_starting_in_air=merge(found["islands"]), sections_steeper_than_45_degrees=merge(found["steep"]))
        if name == "Key_Carrier":
            record["scope"] = ("Findings are listed for the revised centre only. The four key zones are the R52 "
                               "carrier with print-facing clearance at the leading lips. See the full native path audit.")
            everywhere = summarise(rows, inverse)
            record["inherited_key_zone_sections_starting_in_air"] = [g for g in merge(everywhere["islands"])
                                                                     if not b.ZONE[0] <= (g["assembly_bounds_mm"][0] + g["assembly_bounds_mm"][3]) / 2 <= b.ZONE[1]]
            baseline, _ = pose(b.load(b.R52 / "exports/Key_Carrier-assembly.stl"), angles)
            before = summarise(layers(baseline), inverse, centre_only)
            record["r52_centre_for_comparison"] = dict(
                sections_starting_in_air=len(merge(before["islands"])), sections_steeper_than_45_degrees=len(merge(before["steep"])))
        spec["parts"][name] = record
        print(name, size, "contact", record["first_layer_contact_mm2"], "air starts", len(record["sections_starting_in_air"]),
              "steep", len(record["sections_steeper_than_45_degrees"]), flush=True)
    (source / "print-spec.json").write_text(json.dumps(spec, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
