#!/usr/bin/env python3
"""Check the DFRobot fit envelopes and the exact deposited R26 paths."""

import argparse
from functools import lru_cache
import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

import holder26 as d
from plate26 import LABEL
import slice22 as s


def sweep_y(solid, dy):
    return mf.Manifold.batch_hull([solid, solid.translate((0., dy, 0.))])


@lru_cache(maxsize=1)
def lead():
    # Extra loop at the nose lets the sensor move while its lead is anchored
    # to the fixed harness on the right. This models space, not a bend test.
    points = [(0., -23., 24.), (0., -30.2, 24.), (2.2, -34., 22.8),
              (6.1, -35., 18.), (8.3, -32., 10.5), (8.4, -27., 4.1),
              (8.2, -20., 2.7), (8., -12., 2.4)]
    spheres = [mf.Manifold.sphere(1.25, 20).translate(point) for point in points]
    return d.union(mf.Manifold.batch_hull([a, b]) for a, b in zip(spheres, spheres[1:]))


def keeper_pin():
    return d.axis_oval(*d.KEEPER_PIN, .875, -8.04, 8.04)


def keeper_motion():
    # Front removal is possible after pushing the pin sideways out of its bore.
    return sweep_y(d.keeper(), -7.0)


def working_material(name):
    if name == d.CARRIER:
        return {f"hinge pin {side}": d.spring_tongues() ^ d.box(lo, hi, 5.8, 7.2, 17.8, 19.2)
                for side, lo, hi in (("left", -d.PIN_TIP, -d.ARM_INNER),
                                     ("right", d.ARM_INNER, d.PIN_TIP))}
    if name == d.PADDLE:
        return {"left PCB rail": d.box(-12.2, -10.5, -23., 4., 19.28, 20.18),
                "right PCB rail": d.box(10.5, 12.2, -23., 4., 19.28, 20.18),
                "left stop foot": d.box(-7.1, -6., d.STOP_Y0, d.STOP_Y1, d.STOP_Z, d.STOP_Z + .5),
                "right stop foot": d.box(6., 7.1, d.STOP_Y0, d.STOP_Y1, d.STOP_Z, d.STOP_Z + .5)}
    return {"keeper lower bridge": d.box(-4.8, 4.8, -27.2, -26.14, 17.2, 17.5)}


def deposited_material(target, xyz, widths, tops):
    areas = []
    for layer in np.unique(tops):
        section = target.slice(float(layer) - .1)
        if section.area() < .04:
            continue
        hit = abs(tops - layer) < .001
        plastic = s.START.bead_footprints(s.Q, xyz[hit, :2], widths[hit])
        areas.append((section.area(), (section ^ plastic).area()))
    intended, printed = np.sum(areas, axis=0) if areas else (0., 0.)
    return {"layers": len(areas), "deposited_fraction": round(printed / intended, 4) if intended else 0.}


def classify_overhangs(name, rows):
    if name != d.CARRIER:
        return [dict(row, matched_r23_choc_roof=False) for row in rows]
    r23 = json.loads((d.R23 / "exports/slice-clearances.json").read_text())
    reference = r23["parts"][d.CARRIER]["layer_starts"]["partial_overhangs"]
    roofs = []
    for row in reference:
        layer = row["layer_top_mm"]
        if layer not in (16.4, 34.2):
            continue
        x0, y0, x1, y1 = row["print_xy_bounds_mm"]
        # Rear-down: the upper row keeps assembly X. The widening moves its
        # print origin by 2.8 mm. The lower seats move by another ±2.8 mm.
        shift = d.LOWER_SHIFT if layer == 16.4 else (2 * d.LOWER_SHIFT if x0 > 30 else 0.)
        roofs.append((layer, np.array([x0 + shift, y0, x1 + shift, y1])))
    result = []
    for row in rows:
        bounds = np.asarray(row["print_xy_bounds_mm"])
        match = any(row["layer_top_mm"] == layer and (bounds[:2] >= roof[:2] - .08).all()
                    and (bounds[2:] <= roof[2:] + .08).all() for layer, roof in roofs)
        result.append(dict(row, matched_r23_choc_roof=match))
    return result


def spaces():
    h = d.h
    carrier = {name: shape for name, shape in h.h22.carrier_regions().items()
               if not name.startswith("key_1_")}
    hw = [h.board(), *h.barrels().decompose(), *h.switch(), h.plug()]
    carrier["OP1 board, plugged switch and cable"] = d.union(
        [sweep_y(part, -30.) for part in hw] + [h.cable()])
    front_pin = keeper_pin()
    return {
        d.CARRIER: carrier,
        d.PADDLE: {
            "DFR0030 slide": sweep_y(d.sensor(), -34.),
            "Gravity connector": d.box(*d.CONNECTOR),
            "Keeper slide": keeper_motion(),
            "Keeper filament pin": front_pin,
            "Hinge pin bore": d.mirrored(d.axis_oval(d.HINGE_Y, d.HINGE_Z, .88,
                                                    d.ARM_INNER, d.ARM_OUTER)),
        },
        d.KEEPER: {"Keeper filament pin": front_pin},
    }


def geometry():
    carrier = d.h.h22.read(d.OUT / f"{d.CARRIER}-assembly.stl")
    paddle, keeper = d.paddle(), d.keeper()
    # Choc cap travel is the existing sourced-cap envelope at the new seats.
    moving = paddle + keeper + d.sensor() + d.box(*d.CONNECTOR)
    routes = spaces()
    choc = d.union(value for key, value in routes[d.CARRIER].items() if key.endswith("_cap_travel"))
    body, _ = d.h.switch()
    samples = []
    for angle in np.linspace(-d.REST, 0., 25):
        transform = d.pose(angle).tolist()
        shape = moving.transform(transform)
        samples.append({
            "degrees": round(float(angle), 4),
            "carrier_overlap_mm3": round((shape ^ carrier).volume(), 5),
            "Choc_travel_overlap_mm3": round((shape ^ choc).volume(), 5),
            "OP1_body_overlap_mm3": round((shape ^ body).volume(), 5),
            "DFRobot_lead_to_carrier_overlap_mm3": round((lead().transform(transform) ^ carrier).volume(), 5),
        })
    pins = d.spring_tongues()
    fixed = carrier - pins
    squeezed = fixed + pins.warp_batch(lambda points: points + d.flex(points))
    insertion = []
    for z in np.linspace(0., 8., 25):
        incoming = moving.translate((0., 0., float(z)))
        removed = moving.transform(d.pose(-d.REST).tolist()).translate((0., 0., float(z)))
        insertion.append(max((incoming ^ squeezed).volume(), (removed ^ squeezed).volume()))
    # A small virtual over-press must run into both designed stops before
    # any electronics. The real switch travel still needs a fit check.
    overpress = paddle.transform(d.pose(.25).tolist())
    stop_hits = [(overpress ^ post).volume() for post in d.stop_posts().decompose()]
    static = {
        "DFR0030_slide": round((paddle ^ routes[d.PADDLE]["DFR0030 slide"]).volume(), 5),
        "OP1_slide": round((carrier ^ routes[d.CARRIER]["OP1 board, plugged switch and cable"]).volume(), 5),
        "keeper_slide": round((paddle ^ keeper_motion()).volume(), 5),
        "keeper_blocks_board_forward": round((keeper ^ d.sensor().translate((0, -.7, 0))).volume(), 5),
        "board_below_rail_lip_clearance_mm": round(22.22 - d.BOARD_BOTTOM - d.BOARD_THICKNESS, 3),
        "bore_radial_clearance_mm": round(d.BORE_R - d.PIN_R, 3),
        "hinge_pin_engagement_mm": round(d.PIN_TIP - d.ARM_INNER, 3),
        "hinge_pin_insertion_clearance_mm": round(d.ARM_INNER + d.SQUEEZE - d.PIN_TIP, 3),
        "pinched_install_remove_max_overlap_mm3": round(max(insertion), 5),
        "nominal_click_stop_depression_mm": d.DEPRESSION,
        "both_stops_contact_at_0p25deg_overpress_mm3": [round(value, 5) for value in stop_hits],
        "upper_Choc_centres": d.h.base.key_positions()[3:],
        "lower_Choc_centres": [d.h.base.key_positions()[i] for i in d.LOWER_INDICES],
        "pinch_tongue_min_width_mm": round(d.PIN_ROOT - .75, 3),
        "pinch_tongue_relaxed_gap_mm": 1.5,
        "nominal_side_clearance_to_lower_cap_mm": round(d.h.base.key_positions()[2][0] - 8.3 - d.PADDLE_X, 3),
    }
    ok = (max(max(value for name, value in row.items() if name.endswith("_mm3")) for row in samples) < .03
          and all(static[name] < .03 for name in ("DFR0030_slide", "OP1_slide", "keeper_slide",
                                                "pinched_install_remove_max_overlap_mm3"))
          and static["keeper_blocks_board_forward"] > .1
          and len(stop_hits) == 2 and min(stop_hits) > .01)
    d.save_json("geometry-checks.json", {"passed": bool(ok), "physical_fit_verified": False,
                                        "manifest_sha256": d.h.sha(d.OUT / "manifest.json"),
                                        "static": static, "press_path": samples})
    print({"geometry": bool(ok), "static": static,
           "worst": {key: max(row[key] for row in samples) for key in samples[0] if key.endswith("_mm3")}},
          flush=True)
    return ok


def inspect(project, output):
    manifest = json.loads((d.OUT / "manifest.json").read_text())
    anchors = json.loads((d.OUT / "anchors.json").read_text())["parts"]
    data, features, _, settings, offset, objects, _, _ = s.previous.s16.read_project(project)
    from project22 import studio
    commands = studio.p19.command_audit(project, settings)
    assert set(objects) == set(d.PARTS)
    assert settings["timelapse_type"] == "1" and settings["enable_prime_tower"] == "1"
    assert commands["passed"] and commands["first_object_nozzle_target_c"] == 255
    assert commands["first_object_bed_target_c"] == 70 and not studio.p19.slice_info_warnings(project)
    points = data[:, :3] + offset
    kinds = data[:, 5].astype(int)
    tower = kinds == features.index("Prime tower")
    brim = np.array([value.startswith("Brim") for value in features])[kinds]
    support = np.array([value.startswith("Support") for value in features])[kinds]
    radius = data[tower, 3, None] / 2
    tower_min = (points[tower, :2] - radius).min(0)
    tower_max = (points[tower, :2] + radius).max(0)
    assert (tower_min >= 0).all() and (tower_max <= 180).all()
    routes = spaces()
    failures, records = [], {}
    for name in d.PARTS:
        meshfile = d.OUT / f"{name}-SOURCE-REQUIRES-PREPARATION.stl"
        assert d.h.sha(meshfile) == manifest["parts"][name]["stl_sha256"]
        mesh = trimesh.load_mesh(meshfile)
        obj = objects[name]
        assert np.array_equal(obj["faces"], mesh.faces)
        shift = (obj["vertices"].min(0) + obj["vertices"].max(0) - mesh.bounds.sum(0)) / 2
        assert np.abs(obj["vertices"] - shift - mesh.vertices).max() < .0002
        solid = s.Q.solid(mesh.vertices, mesh.faces)
        pads = None
        if name in anchors:
            pad_file = d.OUT / f"{name}-ANCHOR-REMOVE-AFTER-PRINT.stl"
            assert d.h.sha(pad_file) == anchors[name]["stl_sha256"]
            pads = d.h.h22.read(pad_file)
            saved, label = s.previous.slice19.anchor_in_project(project, name, shift)
            assert (pads - saved).volume() + (saved - pads).volume() < .03
        model_and_pads = solid + pads if pads is not None else solid
        lo, hi = np.asarray(model_and_pads.bounding_box()).reshape(2, 3)
        local = points - shift
        nearby = ((local >= lo - [4.7, 4.7, .4]).all(1)
                  & (local <= hi + [4.7, 4.7, .4]).all(1) & ~tower)
        xyz, widths, heights, ids, tops = (local[nearby], data[nearby, 3], data[nearby, 4],
                                          kinds[nearby], data[nearby, 7])
        model = ~brim[nearby] & ~support[nearby]
        first = model & (abs(tops - .2) < .001)
        low, high = (points[nearby, :2] - widths[:, None] / 2).min(0), (points[nearby, :2] + widths[:, None] / 2).max(0)
        gap = np.maximum(np.maximum(low - tower_max, tower_min - high), 0.)
        transform = np.asarray(manifest["parts"][name]["print_to_assembly"])
        to_print = np.linalg.inv(transform)[:3, :]
        starts = s.START.inspect(s.Q, model_and_pads, xyz, heights, ids, features, tops, transform, widths)
        pad_beads = np.zeros(len(xyz), dtype=bool)
        if pads is not None:
            for layer in (.2, .4):
                on_layer = abs(tops - layer) < .001
                p = pads.slice(layer - .1).offset(.26)
                permanent = solid.slice(layer - .1).offset(.26)
                pad_beads[on_layer] = s.Q._inside(p, xyz[on_layer, :2]) & ~s.Q._inside(permanent, xyz[on_layer, :2])
        report = {
            "first_layer_mm2": round(s.START.bead_footprints(s.Q, xyz[first, :2], widths[first]).area(), 3),
            "brim_samples": int(brim[nearby].sum()), "support_samples": int(support[nearby].sum()),
            "tear_off_pad_samples": int(pad_beads.sum()),
            "timelapse_tower_clearance_mm": round(float(np.linalg.norm(gap)), 3),
            "layer_starts": starts, "working_spaces": {},
        }
        report["layer_starts"]["partial_overhangs"] = classify_overhangs(name, starts["partial_overhangs"])
        if any(not row["matched_r23_choc_roof"] for row in starts["partial_overhangs"]):
            failures.append([name, "new partial overhang"])
        if pads is not None:
            s.previous.anchors20.OUT = d.h.R22 / "exports"
            old_frame = xyz - np.asarray(anchors[name]["pad_transform"])[:3, 3]
            report["pad_ties"] = s.previous.neck_audit(name, old_frame, widths, tops)
        if support[nearby].any():
            support_xyz = trimesh.transform_points(xyz[support[nearby]], transform)
            report["support_centrelines_assembly_bounds_mm"] = np.round(
                [support_xyz.min(0), support_xyz.max(0)], 3).tolist()
        report["critical_material"] = {
            label: deposited_material(region.transform(to_print) ^ solid, xyz[model], widths[model], tops[model])
            for label, region in working_material(name).items()
        }
        for label, material in report["critical_material"].items():
            if material["deposited_fraction"] < .65:
                failures.append([name, label, "too little deposited material", material])
        for label, region in routes[name].items():
            poses = region.poses() if isinstance(region, d.h.h22.spaces16.Swept) else [region]
            keep = ~pad_beads if label in ("external_wire_bus", "reverse_wire_bus") else np.ones(len(xyz), dtype=bool)
            checks = [s.Q.inspect_region(pose.transform(to_print), xyz[keep], widths[keep], heights[keep], ids[keep],
                                         features, transform, limit=2) for pose in poses]
            worst = max(checks, key=lambda row: sum(row["violations"].values()))
            report["working_spaces"][label] = {"poses": len(checks), "worst": worst}
            if worst["violations"]:
                failures.append([name, label, worst["violations"]])
        if starts["floating_components"] or starts["missing_printed_components"]:
            failures.append([name, "floating or missing components",
                             len(starts["floating_components"]), len(starts["missing_printed_components"])])
        if (report["first_layer_mm2"] <= 0 or report["brim_samples"] + report["tear_off_pad_samples"] == 0
                or report["timelapse_tower_clearance_mm"] <= 0):
            failures.append([name, "first layer, brim or tower clearance"])
        records[name] = report
        print(name, report["first_layer_mm2"], report["brim_samples"], failures, flush=True)
    output.write_text(json.dumps({
        "passed": not failures, "project_sha256": d.h.sha(project), "commands": commands,
        "parts": records, "failures": failures, "physical_print_verified": False,
    }, indent=2) + "\n")
    return not failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--receipt", type=Path, default=d.OUT / "slice-clearances.json")
    args = parser.parse_args()
    d.set_lower_seats()
    if args.project:
        ok = inspect(args.project, args.receipt)
    else:
        ok = geometry()
    raise SystemExit(0 if ok else 1)
