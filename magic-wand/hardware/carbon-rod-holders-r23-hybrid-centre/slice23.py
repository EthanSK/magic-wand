#!/usr/bin/env python3
"""Audit R23's actual Studio toolpaths, hardware openings and removal space.

The established R22 readers and bead checks still cover the retained parts.
The new checks use the R23 hardware envelopes, not the replaced Choc socket.
"""

import argparse
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np
import trimesh

from project23 import LABEL


def working_spaces(holder, name: str) -> dict:
    old = holder.h22
    if name == "Key_Carrier":
        regions = {label: region for label, region in old.carrier_regions().items()
                   if not label.startswith("key_1_")}
        body, plunger = holder.switch()
        module_parts = [holder.board(), *holder.barrels().decompose(), body, plunger, holder.plug()]
        # These hardware envelopes translate in one straight line. The hull of
        # each convex piece and its translated copy is its entire slide path.
        regions["op1_board_and_plug_slide"] = holder.union(
            mf.Manifold.batch_hull([piece, piece.translate((0, -30., 0))]) for piece in module_parts)
        regions["op1_cable_seated"] = holder.cable()
        regions["hinge_pin"] = holder.hinge_pin()
        return regions
    if name in holder.PD["variants"]:
        return {"hinge_pin": holder.hinge_pin()}
    if name in ("Battery_Holder", "XIAO_Rod_Holder"):
        return old.h20.part_regions(name)
    return {}


def inspect_guard(holder, old, actual, samples, widths, tops, transform) -> dict:
    records = json.loads((holder.OUT / "guard-members.json").read_text())
    to_print = np.linalg.inv(transform)[:3, :]
    members = {name: holder.h22.read(holder.OUT / rec["file"]).transform(to_print)
               for name, rec in records.items() if isinstance(rec, dict) and "file" in rec}
    assert len(members) == len(holder.h22.G["beams"]) == 6
    rows = {name: [] for name in members}
    previous_beads = mf.CrossSection()
    for top in np.unique(np.round(tops, 4)):
        z = float(top) - .1
        use = abs(tops - top) < .001
        beads = old.START.bead_footprints(old.Q, samples[use, :2], widths[use])
        carrier = actual.slice(z)
        sections = {name: member.slice(z) ^ carrier for name, member in members.items()}
        fixed = carrier - mf.CrossSection.batch_boolean(list(sections.values()), mf.OpType.Add)
        connected = []
        if any(section.area() >= .1 for section in sections.values()):
            connected = [(part, (part ^ fixed).area()) for part in beads.decompose()]
        for name, section in sections.items():
            area = section.area()
            if area < .1:
                continue
            deposited = section ^ beads
            core = section.offset(-.30)
            joined = [(part, fixed_area) for part, fixed_area in connected if (part ^ section).area() > .05]
            bond = max((fixed_area for _, fixed_area in joined), default=0.)
            direct_backing = (deposited ^ previous_beads).area()
            row = {"top_mm": float(top), "area_mm2": round(area, 4),
                   "deposited_mm2": round(deposited.area(), 4),
                   "section_coverage": round(deposited.area() / area, 4),
                   "backed_by_previous_layer_mm2": round(direct_backing, 4),
                   "connected_to_carrier_mm2": round(bond, 4)}
            if direct_backing <= .02 and area < .3:
                # The curved root can intersect a thin edge of an existing wall
                # a layer before the rib itself starts. Credit only that short
                # extension when its same-layer wall has direct backing.
                wall_backing = max(((part ^ previous_beads).area() for part, _ in joined), default=0.)
                edge_without_backing = (deposited - previous_beads.offset(.23)).area()
                if wall_backing > 1. and edge_without_backing < .001:
                    row["short_edge_on_backed_wall_mm2"] = round(wall_backing, 4)
            if old.GUARD_FREE_SPAN_MM[0] <= top <= old.GUARD_FREE_SPAN_MM[1]:
                assert core.area() > .1, (name, top)
                row["free_core_coverage"] = round((core ^ beads).area() / core.area(), 4)
            rows[name].append(row)
        previous_beads = beads
    return rows


def inspect_spacer(old, actual, xyz, widths, tops, expected_holes) -> dict:
    # Check the same clear core through both layers, including all nearby beads
    # such as the outer brim. A circle in one layer alone is not a through-hole.
    layer_tops = np.unique(np.round(tops, 4))
    assert len(layer_tops) == 2 and np.allclose(layer_tops, [.2, .4])
    solid = actual.slice(.1)
    holes = []
    for polygon in solid.to_polygons():
        x, y = np.asarray(polygon).T
        if np.dot(x, np.roll(y, -1)) < np.dot(y, np.roll(x, -1)):
            holes.append(mf.CrossSection([np.asarray(polygon)[::-1]]))
    assert len(holes) == expected_holes
    all_beads = []
    coverage = []
    for top in layer_tops:
        layer = abs(tops - top) < .001
        beads = old.START.bead_footprints(old.Q, xyz[layer, :2], widths[layer])
        all_beads.append(beads)
        coverage.append((beads ^ solid).area() / solid.area())
    through = mf.CrossSection.batch_boolean(all_beads, mf.OpType.Add)
    open_regions = [hole - through for hole in holes]
    clear_gauge_mm = .65
    return {"layer_tops_mm": layer_tops.tolist(), "holes": len(holes),
            "open_through_both_layers": sum(not r.offset(-clear_gauge_mm / 2).is_empty()
                                           for r in open_regions),
            "clear_gauge_mm": clear_gauge_mm,
            "smallest_remaining_opening_mm2": round(min(r.area() for r in open_regions), 4),
            "minimum_layer_material_coverage": round(min(coverage), 4)}


def inspect_keeper_tooth(holder, old, xyz, widths, tops, transform) -> dict:
    tongue = holder.h22.h18.K["tongue"]
    tooth = holder.box(*tongue["tooth_x_mm"], *tongue["tooth_y_mm"],
                      tongue["tooth_bottom_z_mm"], tongue["thin_from_z_mm"])
    tooth = tooth.transform(np.linalg.inv(transform)[:3, :])
    rows = []
    for top in np.unique(np.round(tops, 4)):
        section = tooth.slice(float(top) - .1)
        if section.is_empty():
            continue
        core = section.offset(-.24)
        selected = abs(tops - top) < .001
        beads = old.START.bead_footprints(old.Q, xyz[selected, :2], widths[selected])
        rows.append({"top_mm": float(top), "core_coverage": round((core ^ beads).area() / core.area(), 4)})
    assert rows, "Keeper tooth check found no layers"
    return {"tooth_layers": rows, "min_tooth_core_coverage": min(row["core_coverage"] for row in rows)}


def inspect(revision: Path, exports: Path, report_path: Path, *, label: str = LABEL) -> None:
    sys.path.insert(0, str(revision.resolve(strict=True)))
    import holder23 as holder
    import slice22 as old

    project = exports / f"{label}.gcode.3mf"
    manifest = json.loads((exports / "manifest.json").read_text())
    anchors = json.loads((exports / "anchors.json").read_text())["parts"]
    layout = json.loads((exports / f"{label}-print-checks.json").read_text())
    data, features, stats, settings, offset, objects, _, _ = old.previous.s16.read_project(project)
    assert set(objects) == set(manifest["plate_parts"])
    assert settings["timelapse_type"] == "1" and settings["enable_prime_tower"] == "1"
    assert layout["executable_commands"]["project_sha256"] == holder.sha(project)
    assert layout["executable_commands"]["passed"] and not layout["warnings"] and not layout["slice_info_warnings"]
    assert layout["executable_commands"]["first_object_nozzle_target_c"] == 255
    assert layout["executable_commands"]["first_object_bed_target_c"] == 70
    locations = data[:, :3] + offset
    feature_ids = data[:, 5].astype(int)
    support = np.array([value.startswith("Support") for value in features])[feature_ids]
    brim = np.array([value.startswith("Brim") for value in features])[feature_ids]
    tower = feature_ids == features.index("Prime tower")
    radius = data[tower, 3, None] / 2
    tower_lo = (locations[tower, :2] - radius).min(0)
    tower_hi = (locations[tower, :2] + radius).max(0)
    assert (tower_lo >= 0).all() and (tower_hi <= 180).all()
    failures, rows = [], {}
    old.previous.anchors20.OUT = exports
    for name in manifest["plate_parts"]:
        obj = objects[name]
        record = manifest["parts"][name]
        path = exports / f"{name}-SOURCE-REQUIRES-PREPARATION.stl"
        assert holder.sha(path) == record["stl_sha256"], name
        mesh = trimesh.load_mesh(path)
        assert np.array_equal(obj["faces"], mesh.faces), (name, "sliced triangles differ")
        shift = (obj["vertices"].min(0) + obj["vertices"].max(0) - mesh.bounds.sum(0)) / 2
        assert np.abs(obj["vertices"] - shift - mesh.vertices).max() < .0002, (name, "sliced mesh moved")
        actual = old.Q.solid(mesh.vertices, mesh.faces)
        body = actual
        pads = None
        if name in anchors:
            path = exports / f"{name}-ANCHOR-REMOVE-AFTER-PRINT.stl"
            assert holder.sha(path) == anchors[name]["stl_sha256"], name
            pads = holder.h22.read(path)
            written_pads, label = old.previous.slice19.anchor_in_project(project, name, shift)
            drift = holder.vol(pads - written_pads) + holder.vol(written_pads - pads)
            assert drift < .05 and "REMOVE AFTER PRINT" in label, name
            body = actual + pads

        low, high = np.asarray(body.bounding_box()).reshape(2, 3)
        local = locations - shift
        nearby = np.all(local >= low - [3.6, 3.6, .4], axis=1) & np.all(
            local <= high + [3.6, 3.6, .4], axis=1) & ~tower
        xyz, widths, heights, kinds, tops = (local[nearby], data[nearby, 3], data[nearby, 4],
                                            feature_ids[nearby], data[nearby, 7])
        transform = np.asarray(record["print_to_assembly"])
        starts = old.START.inspect(old.Q, body, xyz, heights, kinds, features, tops, transform, widths)
        in_body = np.all(xyz >= low - .45, axis=1) & np.all(xyz <= high + .45, axis=1)
        model = in_body & ~support[nearby] & ~brim[nearby]
        first = model & (np.abs(tops - min(tops[model])) < .001)
        first_area = old.START.bead_footprints(old.Q, xyz[first, :2], widths[first]).area()
        path_low = (locations[nearby, :2] - widths[:, None] / 2).min(0)
        path_high = (locations[nearby, :2] + widths[:, None] / 2).max(0)
        gap = np.maximum(np.maximum(path_low - tower_hi, tower_lo - path_high), 0)
        row = {"first_layer_bead_area_mm2": round(first_area, 3),
               "brim_samples": int(brim[nearby].sum()), "support_samples": int(support[nearby].sum()),
               "layer_starts": starts, "working_spaces": {}, "tower_gap_mm": round(float(np.linalg.norm(gap)), 3)}
        if starts["floating_components"] or starts["missing_printed_components"]:
            failures.append((name, "unsupported or missing starts"))
        if row["tower_gap_mm"] <= 0:
            failures.append((name, "timelapse tower bounding box meets model or brim"))
        if not pads and row["brim_samples"] == 0:
            failures.append((name, "outer brim absent"))
        clearance_transform = np.linalg.inv(transform)[:3, :]
        removable = np.zeros(len(xyz), dtype=bool)
        if pads is not None:
            for top in np.unique(tops[tops <= .401]):
                layer = abs(tops - top) < .001
                z = float(top) - .1
                removable[layer] = old.Q._inside(pads.slice(z).offset(.26), xyz[layer, :2]) & ~old.Q._inside(
                    actual.slice(z).offset(.26), xyz[layer, :2])
        for label, region in working_spaces(holder, name).items():
            poses = region.poses() if isinstance(region, holder.h22.spaces16.Swept) else [region]
            keep = ~removable if label in ("external_wire_bus", "reverse_wire_bus") else np.ones(len(xyz), dtype=bool)
            checks = [old.Q.inspect_region(pose.transform(clearance_transform), xyz[keep], widths[keep],
                                           heights[keep], kinds[keep], features, transform, limit=2)
                      for pose in poses]
            worst = max(checks, key=lambda check: sum(check["violations"].values()))
            row["working_spaces"][label] = {"poses": len(checks), "worst": worst}
            if worst["violations"]:
                failures.append((name, label, worst["violations"]))

        if name in ("Key_Carrier", "Battery_Holder", "XIAO_Rod_Holder"):
            row["ties"] = old.previous.neck_audit(name, xyz[model], widths[model], tops[model])
        if name == "Key_Carrier":
            previous_report = json.loads((holder.R22 / "exports" / "slice-clearances.json").read_text())
            existing = previous_report["parts"][name]["layer_starts"]["partial_overhangs"]
            for overhang in starts["partial_overhangs"]:
                if not any(overhang["layer_top_mm"] == old_row["layer_top_mm"]
                           and np.max(np.abs(np.asarray(overhang["print_xy_bounds_mm"])
                                             - old_row["print_xy_bounds_mm"])) < .015
                           and overhang["unbacked_mesh_area_mm2"] <= old_row["unbacked_mesh_area_mm2"] + .02
                           for old_row in existing):
                    failures.append((name, "new partial overhang", overhang["layer_top_mm"]))
            row["previous_overhang_audit_sha256"] = holder.sha(holder.R22 / "exports" / "slice-clearances.json")
            guards = inspect_guard(holder, old, actual, xyz[model], widths[model], tops[model], transform)
            row["guard_members"] = guards
            for member, layers in guards.items():
                free = [layer for layer in layers if "free_core_coverage" in layer]
                if (not layers or min(layer["section_coverage"] for layer in layers) < .65
                        or len(free) != 21 or min(layer["free_core_coverage"] for layer in free) < .95):
                    failures.append((name, member, "guard layer underfilled"))
                if layers and (any(layer["backed_by_previous_layer_mm2"] <= .02
                                   and "short_edge_on_backed_wall_mm2" not in layer for layer in layers)
                               or any(max(layer["connected_to_carrier_mm2"] for layer in end) < .1
                                      for end in (layers[:3], layers[-3:]))):
                    failures.append((name, member, "guard start or joint lacks backing"))
            backing = old.ring_backing_check(xyz[model], widths[model], tops[model], starts["partial_overhangs"])
            row["ring_backing"] = backing
            if any(layer["prior_bead_coverage"] < .8 or layer["partial_overhangs_in_window"] for layer in backing):
                failures.append((name, "ring shell lacks backing"))
        if name == holder.h22.C["name"]:
            row["cable_layers"] = old.cable_check(xyz[model], widths[model], tops[model], transform)
            if any(max(layer["opening_intrusion_mm2"].values()) > .01 or layer["components"] != 1
                   or layer["pads_joined"] is False for layer in row["cable_layers"]):
                failures.append((name, "cable opening or connection"))
        if name.startswith("Battery_Spacer_") and "geometry_checks" in record:
            windows = inspect_spacer(old, actual, xyz, widths, tops,
                                     record["geometry_checks"]["through_openings"])
            row["patterned_openings"] = windows
            if (windows["open_through_both_layers"] != windows["holes"]
                    or windows["minimum_layer_material_coverage"] < .90):
                failures.append((name, "spacer openings or material incomplete"))
        if name == "XIAO_Near_Keeper":
            tooth = inspect_keeper_tooth(holder, old, xyz[model], widths[model], tops[model], transform)
            row["keeper_tooth"] = tooth
            if tooth["min_tooth_core_coverage"] < .90:
                failures.append((name, "keeper catch tooth underfilled"))
        rows[name] = row
        print(name, "first layer", row["first_layer_bead_area_mm2"],
              "supports", row["support_samples"], "brim", row["brim_samples"],
              "issues", [item[1:] for item in failures if item[0] == name], flush=True)
    report_path.write_text(json.dumps({
        "project_sha256": holder.sha(project), "checker_sha256": holder.sha(Path(__file__)),
        "manifest_sha256": holder.sha(exports / "manifest.json"),
        "anchors_sha256": holder.sha(exports / "anchors.json"), "features": features, "statistics": stats,
        "tower_bounds_mm": [tower_lo.tolist(), tower_hi.tolist()],
        "parts": rows, "failures": failures, "passed": not failures, "physical_print_verified": False,
    }, indent=2) + "\n")
    if failures:
        raise ValueError(f"{label} toolpath checks failed: {failures}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision", type=Path)
    parser.add_argument("staged_exports", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    inspect(args.revision, args.staged_exports, args.report)
