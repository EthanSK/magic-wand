"""Check real Bambu deposition at each part and at its functional openings."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

import manifold3d as mf
import numpy as np
import trimesh

sys.dont_write_bytecode = True
HARDWARE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARDWARE / "carbon-rod-holders-r28-dfrobot-touch"))
import holder28 as baseline
import slice16 as audit
import project22

def r30_routes(directory):
    sys.path.insert(0, str(directory))
    import holder30 as h
    _, working = h.geometry()
    hinge = h.mirrored(h.d.axis_oval(
        h.AXIS_Y + h.CLICK_SHIFT, h.AXIS_Z, h.h29.TAB_R + .03, *h.h29.SUPPORT_X))
    pcb = h.k27.op1(h.H.board())
    sockets = h.k27.op1(h.H.barrels())
    switch, _ = (h.k27.op1(part) for part in h.H.switch())
    guide = {
        "Key_Carrier": {**working, "Snap hinge holes": hinge,
                        "OP1 board": pcb, "OP1 solder sockets": sockets, "OP1 switch": switch,
                        "OP1 connector and lead": h.k27.op1(h.H.plug()) + h.k27.lead()},
        "DFRobot_Hole_Bracket": {
            "PCB underside and both mounting holes": h.sensor(),
            "DFRobot connector": h.connector(),
            "Both clip insertion paths": mf.Manifold.batch_hull([h.clip(-1), h.clip(-1).translate((0.,-5.,0.))])
               + mf.Manifold.batch_hull([h.clip(1), h.clip(1).translate((0.,-5.,0.))])
               - h.union(h.post().translate((sign * h.POST_X, h.hole_y(), 0.))
                         for sign in (-1, 1)),
        },
    }
    for name in ("DFR0030_Post_Clip", "DFR0030_Post_Clip_2"):
        guide[name] = {"Clip opening": mf.Manifold.cylinder(h.CLIP_T + .1, h.NECK_R, h.NECK_R, 48)
                       .translate((0., 0., h.NECK[0] - .05))}
    clips = {name: {"Both jaws": h.clip_local()} for name in guide if "Post_Clip" in name}
    key_mount = h.supports()
    bracket = {
        "Both flex arms and root contact": h.arms(),
        "Left post and neck": h.post().translate((-h.POST_X, h.hole_y(), 0.)),
        "Right post and neck": h.post().translate((h.POST_X, h.hole_y(), 0.)),
    }
    material = {**clips, "Key_Carrier": {"Fixed hinge support walls": key_mount},
                "DFRobot_Hole_Bracket": bracket}
    return guide, material


def material_coverage(q, starts, target, xyz, widths, height, tops):
    layers = []
    for layer in np.unique(tops):
        on_layer = abs(tops - layer) < .001
        section = target.slice(float(layer) - float(height[on_layer][0]) / 2)
        if section.area() < .1:
            continue
        low_x, low_y, high_x, high_y = section.bounds()
        near = on_layer & (xyz[:, 0] >= low_x - .6) & (xyz[:, 0] <= high_x + .6)
        near &= (xyz[:, 1] >= low_y - .6) & (xyz[:, 1] <= high_y + .6)
        fill = starts.bead_footprints(q, xyz[near, :2], widths[near])
        layers.append((section.area(), (section ^ fill).area()))
    areas = np.array(layers)
    assert len(layers)
    return {"layers": len(layers), "coverage_fraction": round(float(areas[:, 1].sum() / areas[:, 0].sum()), 4),
            "minimum_layer_fraction": round(float((areas[:, 1] / areas[:, 0]).min()), 4)}


def inspect(archive, directory, check_routes=False):
    data, features, _, settings, offset, parts, _, _ = audit.read_project(archive)
    source = directory / "exports"
    manifest = json.loads((source / "manifest.json").read_text())
    assert set(parts) == set(manifest["parts"])
    q, starts = audit.q, audit.start_audit
    points = data[:, :3] + offset
    kinds = data[:, 5].astype(int)
    tower = np.array([name == "Prime tower" for name in features])[kinds]
    normal = np.array([not name.startswith(("Brim", "Skirt", "Support")) for name in features])[kinds] & ~tower
    routes, material = r30_routes(directory) if check_routes else ({}, {})
    output = {}
    for name, part in parts.items():
        record = manifest["parts"][name]
        mesh = trimesh.load_mesh(source / f"{name}-SOURCE-REQUIRES-PREPARATION.stl")
        assert baseline.H.sha(source / f"{name}-SOURCE-REQUIRES-PREPARATION.stl") == record["stl_sha256"]
        vertices = part["vertices"]
        shift = (vertices.max(0) + vertices.min(0) - mesh.bounds.sum(0)) / 2
        assert np.array_equal(part["faces"], mesh.faces)
        assert np.abs(vertices - shift - mesh.vertices).max() < .0002, name
        local = points - shift
        solid = q.solid(mesh.vertices, mesh.faces)
        anchor = source / f"{name}-ANCHOR-REMOVE-AFTER-PRINT.stl"
        pad_solid = None
        if anchor.is_file():
            pad = trimesh.load_mesh(anchor)
            pad_solid = q.solid(pad.vertices, pad.faces)
            solid += pad_solid
        lo, hi = np.asarray(solid.bounding_box()).reshape(2, 3)
        nearby = ((local >= lo - [5., 5., .4]).all(1)
                  & (local <= hi + [5., 5., .4]).all(1) & ~tower)
        transform = np.asarray(record["print_to_assembly"])
        selected = local[nearby]
        report = starts.inspect(q, solid, selected, data[nearby, 4], kinds[nearby],
                                features, data[nearby, 7], transform, data[nearby, 3], gap=.24)
        first = nearby & normal & (abs(data[:, 7] - .2) < .001)
        if check_routes:
            report["working_spaces"] = {}
            to_print = np.linalg.inv(transform)[:3, :]
            for label, region in routes[name].items():
                poses = region.poses() if hasattr(region, "poses") else [region]
                keep = np.ones(len(selected), dtype=bool)
                if label == "external_wire_bus" and pad_solid is not None:
                    first_two_layers = selected[:, 2] <= .401
                    on_pads = q._inside(pad_solid.slice(.1).offset(.25), selected[:, :2])
                    keep = ~(first_two_layers & on_pads)
                hits = [q.inspect_region(pose.transform(to_print), selected[keep], data[nearby, 3][keep],
                                         data[nearby, 4][keep], kinds[nearby][keep], features, transform, limit=1)
                        for pose in poses]
                worst = max(hits, key=lambda item: sum(item["violations"].values()))
                report["working_spaces"][label] = worst
            print(name, "working-space findings", {
                label: report["working_spaces"][label]["violations"]
                for label in report["working_spaces"] if report["working_spaces"][label]["violations"]
            }, flush=True)
            beads = nearby & normal
            report["critical_material"] = {
                label: material_coverage(q, starts, region.transform(to_print) ^ solid, local[beads],
                                         data[beads, 3], data[beads, 4], data[beads, 7])
                for label, region in material[name].items()
            }
            print(name, "critical material", report["critical_material"], flush=True)
        report["first_layer_mm2"] = round(starts.bead_footprints(q, local[first, :2], data[first, 3]).area(), 3)
        print(name, "floating", report["floating_components"],
              "missing", report["missing_printed_components"][:5],
              "first_layer", report["first_layer_mm2"], flush=True)
        output[name] = report
    studio = project22.studio.p19
    return {"source_sha256": baseline.H.sha(archive), "parts": output,
            "startup": studio.command_audit(archive, settings),
            "slice_info_warnings": studio.slice_info_warnings(archive),
            "physical_fit_verified": False}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check-routes", action="store_true")
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.archive, args.source, args.check_routes), indent=2) + "\n")
