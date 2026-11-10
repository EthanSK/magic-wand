#!/usr/bin/env python3
"""Check the exact deposited paths through the catch, lift edge and spring slit."""

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

import catch25 as catch
import slice22 as audit


def path_layers(archive, name, zones):
    data, features, _, _, offset, objects, _, _ = audit.previous.s16.read_project(archive)
    record = json.loads((catch.OUT / "manifest.json").read_text())["parts"][name]
    solid_file = catch.OUT / f"{name}-SOURCE-REQUIRES-PREPARATION.stl"
    assert catch.h.sha(solid_file) == record["stl_sha256"]
    mesh = trimesh.load_mesh(solid_file)
    solid = catch.h.h22.read(solid_file)
    obj = objects[name]
    shift = (obj["vertices"].min(0) + obj["vertices"].max(0) - mesh.bounds.sum(0)) / 2
    assert np.array_equal(obj["faces"], mesh.faces)
    assert np.abs(obj["vertices"] - shift - mesh.vertices).max() < .0002
    to_print = np.linalg.inv(np.asarray(record["print_to_assembly"]))[:3, :]
    regions = {label: volume.transform(to_print) for label, volume in zones.items()}

    local = data[:, :3] + offset - shift
    in_box = np.all(local >= mesh.bounds[0] - .55, axis=1) & np.all(local <= mesh.bounds[1] + .55, axis=1)
    material = np.array([not f.startswith(("Brim", "Prime tower")) for f in features])
    keep = in_box & material[data[:, 5].astype(int)]
    xy, widths, tops = local[keep, :2], data[keep, 3], data[keep, 7]
    rows = {label: [] for label in zones}
    for top in np.unique(np.round(tops, 4)):
        z = float(top) - .10
        active = {label: region.slice(z) for label, region in regions.items()}
        if all(section.is_empty() for section in active.values()):
            continue
        selected = abs(tops - top) < .001
        beads = audit.START.bead_footprints(audit.Q, xy[selected], widths[selected])
        for label, section in active.items():
            if section.is_empty():
                continue
            rows[label].append({"print_layer_top_mm": round(float(top), 3),
                                "design_filled_fraction": round((section ^ solid.slice(z)).area() / section.area(), 4),
                                "bead_filled_fraction": round((section ^ beads).area() / section.area(), 4)})
    return rows


def check(archive):
    h = catch.h
    tooth_floor = catch.old_latch.TOOTH_Z0
    stop = h.box(-1.3, 1.3, catch.STOP_Y - .66, catch.STOP_Y + .42,
                 tooth_floor + .04, catch.STOP_TOP_Z - .035)
    holder = path_layers(archive, catch.HOLDER, {"stop": stop})
    before = [row for row in holder["stop"] if row["design_filled_fraction"] < .01]
    after = [row for row in holder["stop"] if row["design_filled_fraction"] > .97]
    assert len(before) >= 2 and len(after) >= 2, holder
    assert max(row["bead_filled_fraction"] for row in before) < .08, before
    assert min(row["bead_filled_fraction"] for row in after) > .90, after

    tongue = catch.old_latch
    slit = h.box(tongue.ROOT_X + .2, tongue.TIP_X - .2,
                 tongue.TY0 - .45, tongue.TY0 - .15, 10.80, 11.92)
    tab_x = catch.TAB_X[0] + .27, catch.TAB_X[1] - .27
    root = h.box(*tab_x, 1.03, 1.27, 11.0, 11.87)
    edge = h.box(*tab_x, 2.10, 2.26, 11.34, 11.87)
    keeper = path_layers(archive, catch.KEEPER, {"spring_slit": slit, "lift_root": root, "lift_edge": edge})
    assert all(keeper.values())
    assert max(row["bead_filled_fraction"] for row in keeper["spring_slit"]) < .10, keeper
    for part in ("lift_root", "lift_edge"):
        assert min(row["bead_filled_fraction"] for row in keeper[part]) > .90, keeper[part]
    return {"archive_sha256": h.sha(archive), **holder, **keeper}


def untouched_clearances():
    # A zero-sample path check needs geometry evidence that the changed
    # parts stayed clear of the inherited rod, USB and wire envelopes.
    h = catch.h
    changes = []
    for part in (catch.HOLDER, catch.KEEPER):
        name = f"{part}-assembly.stl"
        changes.append(h.h22.read(catch.OUT / name) - h.h22.read(catch.OLD / name))
    report = json.loads((catch.OUT / "slice-clearances.json").read_text())
    spaces = h.h22.h20.part_regions(catch.HOLDER)
    rows = {}
    for name, record in report["parts"][catch.HOLDER]["working_spaces"].items():
        if record["worst"]["checked_samples"] != 0:
            continue
        region = spaces[name]
        poses = region.poses() if isinstance(region, h.h22.spaces16.Swept) else [region]
        rows[name] = round(max(h.vol(change ^ pose) for pose in poses for change in changes), 6)
    assert rows and max(rows.values()) < .002, rows
    return rows


def main(reopened):
    project = catch.OUT / "R25-XIAO-Catch-A1-mini-PETG.gcode.3mf"
    checks = {"delivered": check(project), "reopened": check(reopened),
              "added_material_overlap_mm3_in_zero_sample_regions": untouched_clearances(),
              "checker_sha256": catch.h.sha(__file__), "passed": True,
              "physical_retention_verified": False}
    (catch.OUT / "catch-path-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reopened", type=Path)
    main(parser.parse_args().reopened)
