#!/usr/bin/env python3
"""Check the real tear-off ties, tower gap and individual bridge spans."""
import importlib.util
import json
import math
from pathlib import Path
import sys
from zipfile import ZipFile

import numpy as np
import trimesh

spec = importlib.util.spec_from_file_location("print_audit", Path(__file__).with_name("audit-print.py"))
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)
audit = audit_module.audit
q, starts = audit.q, audit.start_audit

archive, source, layer_report, report_path = map(Path, sys.argv[1:5])
data, features, _, settings, offset, parts, text, _ = audit.read_project(archive)
body_name = sys.argv[5] if len(sys.argv) > 5 else "Key_Carrier"
part = parts[body_name]
exports = source / "exports"
report = json.loads(layer_report.read_text())["parts"]
records = {}
points = data[:, :3] + offset
features_array = np.asarray(features)
names = features_array[data[:, 5].astype(int)]
tower = names == "Prime tower"
rad = data[:, 3] / 2.
tower_min = (points[tower, :2] - rad[tower, None]).min(0)
tower_max = (points[tower, :2] + rad[tower, None]).max(0)
tower_gaps = {}
for name, saved in parts.items():
    mesh = trimesh.load_mesh(exports / f"{name}-SOURCE-REQUIRES-PREPARATION.stl")
    shift = (saved["vertices"].max(0) + saved["vertices"].min(0) - mesh.bounds.sum(0)) / 2
    anchor = exports / f"{name}-ANCHOR-REMOVE-AFTER-PRINT.stl"
    support_pads = trimesh.load_mesh(anchor) if anchor.exists() else None
    bounds = mesh.bounds.copy()
    if support_pads is not None:
        bounds[0] = np.minimum(bounds[0], support_pads.bounds[0])
        bounds[1] = np.maximum(bounds[1], support_pads.bounds[1])
    low, high = (bounds + shift)[:, :2]
    gap = np.maximum(np.maximum(low - tower_max, tower_min - high), 0.)
    tower_gaps[name] = round(float(np.linalg.norm(gap)), 3)
    if support_pads is None:
        continue
    local = points - shift
    on_part = ((local >= bounds[0] - .6).all(1) & (local <= bounds[1] + .6).all(1) & ~tower)
    pad_mesh = q.solid(support_pads.vertices, support_pads.faces)
    part_solid = q.solid(mesh.vertices, mesh.faces)
    layer_ties = []
    for top in (.2, .4):
        keep = on_part & (abs(data[:, 7] - top) < .001)
        footprints = starts.bead_footprints(q, local[keep, :2], data[keep, 3])
        core = part_solid.slice(top - .1)
        pads = pad_mesh.slice(top - .1)
        printed = (core + pads) ^ footprints
        printed_components = printed.decompose()
        for pad in pads.decompose():
            attached = any((pad ^ piece).area() > .4 and (core ^ piece).area() > 1. for piece in printed_components)
            layer_ties.append({"layer_top_mm":top,"pad_bounds": [round(v, 3) for v in pad.bounds()],
                               "joined_in_actual_beads": attached})
    records[name] = layer_ties

# For every wide partially unsupported region, check if actual deposited lines
# span the opening with contact at both ends, or run short overhangs at an edge.
regions = {}
for row in report[body_name]["partial_overhangs"]:
    if row["unbacked_mesh_area_mm2"] >= (8. if body_name == "Key_Carrier" else .5):
        regions.setdefault(row["layer_top_mm"], []).append(row)
mesh = trimesh.load_mesh(exports / f"{body_name}-SOURCE-REQUIRES-PREPARATION.stl")
shift = (part["vertices"].max(0) + part["vertices"].min(0) - mesh.bounds.sum(0)) / 2
body = q.solid(mesh.vertices, mesh.faces)
local = points - shift
backing_by_layer = {}
for top in regions:
    below = (abs(data[:, 7] - (top - .2)) < .001) & ~tower
    near = (local[:, :2] >= mesh.bounds[0, :2] - .8).all(1) & (local[:, :2] <= mesh.bounds[1, :2] + .8).all(1)
    beads = starts.bead_footprints(q, local[below & near, :2], data[below & near, 3])
    backing_by_layer[top] = (beads ^ body.slice(top - .3)).offset(.18, q.JoinType.Round)

samples = {top: [] for top in regions}
position = np.zeros(3)
feature = ""
layer = None
last_continuous = None
for line in text.splitlines():
    if line.startswith("; FEATURE:"):
        feature = line[11:].strip()
    elif line.startswith("; Z_HEIGHT:"):
        layer = round(float(line.split(":", 1)[1]), 4)
        last_continuous = None
    elif line.startswith(("G0 ", "G1 ", "G2 ", "G3 ")):
        raw = line.split(";", 1)[0].split()
        words = {s[0]: float(s[1:]) for s in raw[1:] if s[0] in "XYZEIJR"}
        end = np.array([words.get(k, position[i]) for i, k in enumerate("XYZ")])
        if layer in regions and words.get("E", 0) > 0 and np.linalg.norm(end[:2] - position[:2]) > .03:
            p0, p1 = position + offset - shift, end + offset - shift
            if raw[0] in ("G2", "G3"):
                centre, r, angle, sweep = q._arc(position, end, words, raw[0] == "G2")
                length = abs(sweep) * r
                angles = angle + sweep * np.linspace(0, 1, max(2, math.ceil(length / .08)))
                vertices = centre + np.c_[np.cos(angles), np.sin(angles)] * r + offset[:2] - shift[:2]
            else:
                length = np.linalg.norm(p1[:2] - p0[:2])
                vertices = np.linspace(p0[:2], p1[:2], max(2, math.ceil(length / .08)))
            if feature not in ("Prime tower", "Custom", "Flush", ""):
                if last_continuous is not None and np.linalg.norm(last_continuous[-1][-1] - vertices[0]) < .02:
                    last_continuous.append(vertices[1:])
                else:
                    last_continuous = [vertices]
                    samples[layer].append(last_continuous)
        elif np.linalg.norm(end - position) > .03 or words.get("E", 0) < 0:
            last_continuous = None
        position = end

bridges = []
for top, zones in regions.items():
    for row in zones:
        lo_x, lo_y, hi_x, hi_y = row["print_xy_bounds_mm"]
        groups = []
        for chain in samples[top]:
            vertices = np.concatenate(chain)
            within = ((vertices >= (lo_x - .10,lo_y - .10)).all(1)
                      & (vertices <= (hi_x + .10,hi_y + .10)).all(1))
            if not within.any():
                continue
            backed = q._inside(backing_by_layer[top], vertices)
            edges = np.diff(np.r_[False, ~backed, False].astype(int))
            for a,b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
                if not within[a:b].any():
                    continue
                lo, hi = max(0,a-1), min(len(vertices),b+1)
                chain_mm = np.linalg.norm(np.diff(vertices[lo:hi],axis=0),axis=1).sum()
                groups.append({"span_mm": round(float(chain_mm),3),
                               "ends_backed": int(a>0)+int(b<len(vertices)),
                               "ends": np.round(vertices[[lo,hi-1]],3).tolist()})
        selected = sorted(groups, key=lambda item: item["span_mm"], reverse=True)
        entry = {"layer_top_mm":top,"bounds_mm":row["print_xy_bounds_mm"],"longest":selected[:7]}
        bridges.append(entry)
        print(entry, flush=True)

output = {"tower_clearance_by_part_mm":tower_gaps,"pad_ties":records,"bridge_segments":bridges}
report_path.write_text(json.dumps(output, indent=2) + "\n")
print("Tower",tower_gaps, "ties", {part: [v["joined_in_actual_beads"] for v in row] for part,row in records.items()},flush=True)
