#!/usr/bin/env python3
"""Check the complete assembly against deposited Bambu paths, including adhesion."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import trimesh

from plate32 import BRIM_WIDTH, HERE, OUTER_BRIM, PAD_SUFFIX, SOURCE_SUFFIX, digest, read_json


def load_checker():
    path = HERE.parent / "carbon-rod-holders-r31-rear-hinge" / "audit-print.py"
    spec = importlib.util.spec_from_file_location("r31_print_audit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bead_bounds(xy, widths):
    radius = widths[:, None] / 2
    return (xy - radius).min(0), (xy + radius).max(0)


def pad_join_checks(q, starts, solid, pads, xyz, widths, tops):
    """Check the two printed pad layers from the sliced bead footprints."""
    result = []
    for layer_top in (.2, .4):
        row = np.abs(tops - layer_top) < .001
        footprint = starts.bead_footprints(q, xyz[row, :2], widths[row])
        z = layer_top - .1
        model_section, pad_section = solid.slice(z), pads.slice(z)
        beads = (footprint ^ (model_section + pad_section)).decompose()
        for number, pad in enumerate(pad_section.decompose()):
            connected = any((bead ^ pad).area() > .4 and (bead ^ model_section).area() > 1. for bead in beads)
            result.append({"layer_top_mm": layer_top, "pad": number + 1, "joined": connected})
    assert result
    return result


def route_hits(q, region, xyz, widths, heights, kinds, features, frame, keep):
    to_print = np.linalg.inv(frame)[:3, :]
    poses = region.poses() if hasattr(region, "poses") else [region]
    print_poses = [pose.transform(to_print) for pose in poses]
    if len(print_poses) > 1:
        # A bead outside the aggregate bounds cannot meet any pose's existing
        # inspect_region candidate test. Keep every bead that can meet a pose.
        bounds = np.asarray([pose.bounding_box() for pose in print_poses])
        low, high = bounds[:, :3].min(0), bounds[:, 3:].max(0)
        radius = widths[:, None] / 2
        near_xy = ((xyz[:, :2] >= low[:2] - radius) & (xyz[:, :2] <= high[:2] + radius)).all(1)
        middle = xyz[:, 2] - heights / 2
        keep = keep & near_xy & (middle > low[2] + q.Z_GUARD) & (middle < high[2] - q.Z_GUARD)
    samples = xyz[keep], widths[keep], heights[keep], kinds[keep]
    results = (q.inspect_region(pose, *samples, features, frame, limit=2) for pose in print_poses)
    worst = max(results, key=lambda result: (sum(result["violations"].values()), result["checked_samples"]))
    return {**worst, "poses_checked": len(print_poses)}


def inspect(archive, staged_exports, key_routes, layout_report, removable_support=None):
    checks31 = load_checker()
    import holder23
    import slice22
    import slice23

    old = holder23.h22
    q, starts = checks31.audit.q, checks31.audit.start_audit
    data, features, stats, settings, offset, objects, _, _ = checks31.audit.read_project(archive)
    manifest = read_json(staged_exports / "manifest.json")
    anchors = read_json(staged_exports / "anchors.json")["parts"]
    assert set(objects) == set(manifest["parts"]) == set(layout_report["build_list"])
    assert settings["timelapse_type"] == "1" and settings["enable_prime_tower"] == "1"
    for key, expected in layout_report["effective_filament_settings"].items():
        assert settings[key] == expected, (key, settings[key], expected)
    positions = data[:, :3] + offset
    feature_ids = data[:, 5].astype(int)
    names = np.asarray(features)[feature_ids]
    tower = names == "Prime tower"
    assert tower.sum() > 500, "Smooth timelapse has no deposited wipe tower"
    tower_low, tower_high = bead_bounds(positions[tower, :2], data[tower, 3])
    assert (tower_low >= 0).all() and (tower_high <= 180).all()
    support = np.char.startswith(names, "Support")
    brim = np.char.startswith(names, "Brim")
    support_report = None
    if removable_support is None:
        assert not support.any(), "Unexpected generated support on the complete plate"
    else:
        support_report = removable_support(data, positions, names, objects, q, starts)
        assert support_report["passed"], support_report
    routes, critical = key_routes()
    routes = {
        **routes,
        **{name: old.h20.part_regions(name) for name in ("XIAO_Rod_Holder", "Battery_Holder")},
        **{name: old.h18.regions(name) for name in ("XIAO_Near_Keeper", "Battery_End_Door")},
    }
    failures, parts = [], {}
    for name, record in manifest["parts"].items():
        path = staged_exports / f"{name}{SOURCE_SUFFIX}"
        assert digest(path) == record["stl_sha256"]
        mesh = trimesh.load_mesh(path)
        saved = objects[name]
        shift = (saved["vertices"].max(0) + saved["vertices"].min(0) - mesh.bounds.sum(0)) / 2
        assert np.array_equal(saved["faces"], mesh.faces), (name, "sliced triangles differ")
        assert np.abs(saved["vertices"] - shift - mesh.vertices).max() < .0002, name
        frame = np.asarray(record["print_to_assembly"])
        solid = q.solid(mesh.vertices, mesh.faces)
        body, pads = solid, None
        if name in anchors:
            path = staged_exports / f"{name}{PAD_SUFFIX}"
            assert digest(path) == anchors[name]["stl_sha256"], name
            pad = trimesh.load_mesh(path)
            pads = q.solid(pad.vertices, pad.faces)
            body = solid + pads
            actual_pad, label = slice22.previous.slice19.anchor_in_project(archive, name, shift)
            assert "REMOVE AFTER PRINT" in label
            assert abs((pads - actual_pad).volume()) + abs((actual_pad - pads).volume()) < .05, name
        local = positions - shift
        low, high = np.asarray(body.bounding_box()).reshape(2, 3)
        margin = BRIM_WIDTH + .65 if name in OUTER_BRIM else .55
        xy_margin = [margin, margin, .4]
        near = (local >= low - xy_margin).all(1) & (local <= high + xy_margin).all(1) & ~tower
        xyz = local[near]
        widths, heights, tops, kinds = (data[near, 3], data[near, 4], data[near, 7], feature_ids[near])
        model = ~brim[near] & ~np.char.startswith(names[near], "Skirt") & ~support[near]
        first = model & (abs(tops - .2) < .001)
        assert first.any(), (name, "no first-layer model paths")
        supported_part = support_report is not None and support_report["part"] == name
        gap = support_report["top_gap_mm"] if supported_part else .24
        row = starts.inspect(q, body, xyz, heights, kinds, features, tops, frame, widths, gap=gap)
        row["first_layer_mm2"] = round(starts.bead_footprints(q, xyz[first, :2], widths[first]).area(), 3)
        row["brim_samples"] = int(brim[near].sum())
        if name in OUTER_BRIM and row["brim_samples"] == 0:
            failures.append([name, "expected outer brim absent"])
        if row["floating_components"] or row["missing_printed_components"]:
            failures.append([name, "floating or missing layers"])
        part_low, part_high = bead_bounds(positions[near, :2], widths)
        gap = np.maximum(np.maximum(part_low - tower_high, tower_low - part_high), 0)
        row["tower_gap_mm"] = round(float(np.linalg.norm(gap)), 3)
        if row["tower_gap_mm"] <= 0:
            failures.append([name, "tower meets object or adhesion"])
        if pads is not None:
            row["pad_ties"] = pad_join_checks(q, starts, solid, pads, xyz[model], widths[model], tops[model])
            if not all(item["joined"] for item in row["pad_ties"]):
                failures.append([name, "pad does not join the object"])
        row["working_spaces"] = {}
        for label, region in routes.get(name, {}).items():
            # A designated removable helper is checked independently before
            # assessing the clearances of the finished assembly.
            keep = ~support[near] if supported_part else np.ones(len(xyz), dtype=bool)
            if label in ("external_wire_bus", "reverse_wire_bus") and pads is not None:
                # These labelled pads are cut off before wiring. Preserve every
                # nearby model bead and exclude only the pad-only portions.
                pad_only = pads.slice(.1).offset(.25) - solid.slice(.1).offset(.25)
                keep &= ~((tops <= .401) & q._inside(pad_only, xyz[:, :2]))
            hit = route_hits(q, region, xyz, widths, heights, kinds, features, frame, keep)
            row["working_spaces"][label] = hit
            if hit["violations"]:
                failures.append([name, label, hit["violations"]])
        row["critical_material"] = {
            label: checks31.material_coverage(q, starts, region.transform(np.linalg.inv(frame)[:3, :]) ^ solid,
                                              xyz[model], widths[model], heights[model], tops[model])
            for label, region in critical.get(name, {}).items()
        }
        for label, coverage in row["critical_material"].items():
            if coverage["minimum_layer_fraction"] < .9:
                failures.append([name, label, "less than 90% of a critical cross-section printed", coverage])
        if name == "XIAO_Near_Keeper":
            tooth = slice23.inspect_keeper_tooth(holder23, slice22, xyz[model], widths[model], tops[model], frame)
            row["keeper_tooth"] = tooth
            if tooth["min_tooth_core_coverage"] < .9:
                failures.append([name, "keeper catch tooth underfilled"])
        elif name == "Cable_Clip_12_Wire":
            cable = slice22.cable_check(xyz[model], widths[model], tops[model], frame)
            row["cable_layers"] = cable
            if any(max(layer["opening_intrusion_mm2"].values()) > .01 or layer["components"] != 1
                   or layer["pads_joined"] is False for layer in cable):
                failures.append([name, "cable clip opening or connection"])
        elif "through_openings" in record.get("geometry_checks", {}):
            spacer = slice23.inspect_spacer(slice22, solid, xyz, widths, tops,
                                            record["geometry_checks"]["through_openings"])
            row["patterned_openings"] = spacer
            if spacer["open_through_both_layers"] != spacer["holes"] or spacer["minimum_layer_material_coverage"] < .9:
                failures.append([name, "spacer windows or material incomplete"])
        parts[name] = row
        print(name, "first layer", row["first_layer_mm2"], "brim", row["brim_samples"],
              "findings", [item[1:] for item in failures if item[0] == name], flush=True)
    studio = checks31.project22.studio.p19
    warnings = studio.slice_info_warnings(archive)
    if warnings:
        failures.append(["plate", "archive warnings", warnings])
    if layout_report.get("warnings"):
        failures.append(["plate", "Bambu slicing warnings", layout_report["warnings"]])
    return {
        "archive_sha256": digest(archive), "manifest_sha256": digest(staged_exports / "manifest.json"),
        "checker_sha256": digest(Path(__file__)), "bom_sha256": layout_report["bom_sha256"],
        "tower_bounds_mm": [tower_low.tolist(), tower_high.tolist()], "statistics": stats,
        "parts": parts, "failures": failures, "passed": not failures,
        "startup": studio.command_audit(archive, settings), "archive_warnings": warnings,
        "physical_fit_verified": False,
        **({"removable_support": support_report} if support_report is not None else {}),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("scratch", type=Path, help="The scratch directory created by plate32.py")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    from holder32 import print_routes

    report = inspect(args.archive, args.scratch / "build-source" / "exports", print_routes,
                     read_json(args.scratch / "print-checks.json"))
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    if report["failures"]:
        raise SystemExit("See the full plate audit for the remaining issues")
