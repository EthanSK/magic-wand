"""Compare the six assembly faces at the real layer pitch before committing to a native slice."""
import argparse
import hashlib
import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

ROTATIONS = {
    "bottom_down": (0, 0, 0), "face_down": (180, 0, 0),
    "front_down": (90, 0, 0), "rear_down": (-90, 0, 0),
    "left_down": (0, -90, 0), "right_down": (0, 90, 0),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_solid(path):
    mesh = trimesh.load_mesh(path)
    raw = mf.Mesh(np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces, np.uint32))
    raw.merge()
    solid = mf.Manifold(raw)
    if solid.is_empty() or solid.status() != mf.Error.NoError:
        raise ValueError(f"Invalid body: {path.name}, {solid.status()}")
    return solid


def oriented(solid, name):
    angles = ROTATIONS[name]
    turned = solid.rotate(angles)
    low = np.asarray(turned.bounding_box()[:3])
    rotation = trimesh.transformations.euler_matrix(*np.deg2rad(angles))
    rotation[:3, 3] = -low
    return turned.translate(-low), rotation


def inspect(source):
    solid = load_solid(source)
    rows = {}
    for name in ROTATIONS:
        body, frame = oriented(solid, name)
        _, _, _, w, d, h = body.bounding_box()
        previous = mf.CrossSection()
        need = mf.CrossSection()
        islands = []
        unsupported = []
        material = 0.0
        for layer, z in enumerate(np.arange(0.1, h, 0.2), start=1):
            section = body.slice(float(z))
            material += section.area() * .2
            if layer == 1:
                contact = section.area()
            else:
                # Half a nozzle at each 0.2 mm rise permits a 45-degree self-supporting face.
                unsupported_area = section - previous.offset(.20)
                if unsupported_area.area() > .02:
                    need += unsupported_area
                    unsupported.append((layer, unsupported_area.area()))
                for part in section.decompose():
                    if part.area() >= .10 and (part ^ previous).area() < .012:
                        islands.append({"layer": layer, "area_mm2": round(part.area(), 3),
                                        "bounds": [round(v, 3) for v in part.bounds()]})
            previous = section
        rows[name] = dict(size_mm=[round(v, 3) for v in (w,d,h)], bed_contact_mm2=round(contact, 2),
                          downward_projected_area_mm2=round(need.area(), 2),
                          total_overhang_section_area_mm2=round(sum(v for _,v in unsupported),2),
                          isolated_section_starts=islands,
                          min_layer_mm=.2, assembly_to_print=frame.tolist(), volume_mm3=round(material,2))
        print(name,rows[name]["size_mm"],round(contact,2),round(need.area(),2),len(islands),flush=True)
    return dict(source=source.name, source_sha256=digest(source), faces=rows,
                scope="CAD sections predict candidate orientations. First-layer retention, actual bridge lines and any native support are checked separately.")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.source),indent=2)+"\n")
