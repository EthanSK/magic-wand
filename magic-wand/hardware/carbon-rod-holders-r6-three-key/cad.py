#!/usr/bin/env python3
"""Build R6's three-key carrier with `python cad.py`.

Ethan's 'keys a bit closer together' means the original transverse three-key
row, not the later five-key studies. Compose R4's corrected bought-part seats
and front battery cradle, keeping their dimensions in the original source.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
from functools import lru_cache
from importlib.metadata import version
import importlib.util
import json
import platform
from pathlib import Path
import shutil
import sys

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
SPEC = json.loads((HERE / "parameters.json").read_text())
BASE = (HERE / SPEC["base_parameters"]).resolve().parent
spec = importlib.util.spec_from_file_location("r6_source_r4_cad", BASE / "cad.py")
r4 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r4
spec.loader.exec_module(r4)
P = deepcopy(r4.P)
P["revision"] = SPEC["revision"]
P["keys"].update(SPEC["keys"])
# R4 functions intentionally consume one effective parameter set; its source
# files and reference directory remain unchanged. No R5 source is imported.
r4.P = P

ATTRIBUTION = {
    "source": "https://github.com/kiswitch/kiswitch",
    "revision": "aefcf65038d48d2666ff14530d482be3c350fa6e",
    "license": "CC BY-SA 4.0 with the KiCad exception",
    "license_file": "../carbon-rod-holders-r4/references/LICENSE-CC-BY-SA.txt",
    "authority": "Community CAD cross-checked with Kailh drawings; purchased batch unmeasured",
}


def key_positions(pitch: float | None = None) -> list[tuple[float, float]]:
    spacing = P["keys"]["pitch"] if pitch is None else pitch
    return [(-spacing, 0.0), (0.0, 0.0), (spacing, 0.0)]


def carrier(pitch: float | None = None) -> mf.Manifold:
    """Keep only the three-key row; compose the proven R4 structural recipe."""
    k = P["keys"]
    z = k["pcb_z"]
    spacing = k["pitch"] if pitch is None else pitch
    positions = key_positions(spacing)
    parts = [r4.key_seat(outer_side=1 if x > 0 else -1 if x < 0 else 0).translate((x, y, z))
             for x, y in positions]
    # Retain R4's front/rear rails, flat deck bridges and deep webs. The gap
    # bridges follow the actual key centres instead of R4's fixed 20mm value.
    for y, height in [(-9.4, z + 1.4), (10.5, z - 4.5)]:
        parts.append(r4.rib((-spacing - 8.2, y, height), (spacing + 8.2, y, height), P["structure"]["rail_radius"]))
    for side in [-1, 1]:
        for y in [-4.0, 7.3]:
            ends = [side * 7.8, side * (spacing - 7.8)]
            parts.append(r4.box(min(ends), max(ends), y - 1.5, y + 1.5,
                                z + k["plate_bottom"], z + 2.25))
        for y in [-9.4, 10.5]:
            ends = [side * 7.0, side * spacing]
            parts.append(r4.box(min(ends), max(ends), y - .7, y + .7, z - 4.5, z + 2.25))
    for y, target_y in [(-12.0, -10.5), (11.5, 10.5)]:
        parts.append(r4.ring(y))
        for side in [-1, 1]:
            parts.append(r4.rib((side * 3.8, y, 4.1), (side * 7.8, target_y, z + 1.1), 1.6))
    # The thumb brace carries load into the frame, never into the LiPo pouch.
    parts.append(r4.rib((-7.8, 11.5, z + 1.35), (7.8, 11.5, z + 1.35), 1.3))
    parts.append(r4.battery_cradle("front"))
    shape = r4.union(parts)
    shape ^= r4.box(-80, 80, -90, 90, -40, z + 2.25)
    radius = (P["rod"]["diameter"] + P["rod"]["diametral_clearance"]) / 2
    shape -= r4.cyl(radius, -80, 80).rotate((-90, 0, 0))
    return shape - r4.wire_bus(-80, 80)


@lru_cache(maxsize=1)
def canonical_tip() -> tuple[dict[str, trimesh.Trimesh], dict]:
    """Recover R2's actual exported seating and provisional tip-wire envelope."""
    source = HERE.parent / "carbon-rod-holders-r2/exports/Assembly-reference.glb"
    scene = trimesh.load(source, force="scene")
    def world_mesh(node: str) -> trimesh.Trimesh:
        transform, name = scene.graph[node]
        result = scene.geometry[name].copy()
        result.apply_transform(transform)
        return result
    rod = world_mesh("REFERENCE_rod")
    old_frame = world_mesh("XIAO_Rod_Holder")
    frame = trimesh.load_mesh(OUT / "XIAO_Rod_Holder-assembly.stl")
    # The source CAD translates the frame by 451.6mm. Recover that mapping
    # from its meshes, rounding only the GLB's float32 coordinate noise.
    origin = round(float(old_frame.bounds[0, 1] - frame.bounds[0, 1]), 3)
    tube_end_local = round(float(rod.bounds[1, 1] - origin), 3)
    assert np.isclose(old_frame.bounds[1, 1], rod.bounds[1, 1], atol=1e-4)
    parts = {"XIAO_Rod_Holder": frame}
    for node in ["REFERENCE_pcb", "REFERENCE_usb", "REFERENCE_provisional_wire_route"]:
        parts[node] = world_mesh(node)
        parts[node].apply_translation((0, -origin, 0))
    max_end = max(float(part.bounds[1, 1]) for part in parts.values())
    overhang = max(0.0, round(max_end - tube_end_local, 3))
    return parts, {"source": "../carbon-rod-holders-r2/exports/Assembly-reference.glb",
                   "source_frame_translation_y_mm": origin, "tube_end_local_y_mm": tube_end_local,
                   "positive_end_overhang_mm": overhang,
                   "overhang_owner": "R2 provisional 3mm wire-route envelope",
                   "seating": "frame upper sleeve end flush with tube end, preserving the R2 export mapping",
                   "physical_end_overhang_measured": False}


def reference_placement() -> dict:
    """Map the physical V3 brief to one stated cap edge, never a grip pivot.

    'V3' is Ethan's new physical brief alias, not Control V3 or holder R3.
    Carrier-local Y=0 is the key centre; the lower illustrative cap edge is
    at -cap_length/2. The existing layout was reported near 100mm from the
    butt. At the selected 180mm overall length, that position collides with
    the tip hardware; the proposed 85mm position retains 2.05mm frame space.
    """
    brief = SPEC["assembly_reference"]
    tip_parts, tip = canonical_tip()
    tube_length = brief["overall_length"] - tip["positive_end_overhang_mm"]
    tip_origin = tube_length-tip["tube_end_local_y_mm"]
    centre = brief["lower_key_cluster_edge_from_butt"] + P["keys"]["cap_reference_length"] / 2
    def placed_bounds(name: str) -> np.ndarray:
        bounds = tip_parts[name].bounds.copy()
        bounds[:, 1] += tip_origin
        return bounds
    pcb_bounds = placed_bounds("REFERENCE_pcb")
    return {**brief, "rod_length": tube_length, "tip_seating": tip,
            "tip_local_origin_from_butt_mm": tip_origin,
            "carrier_local_origin_from_butt_mm": centre,
            "carrier_move_from_existing_layout_mm": brief["lower_key_cluster_edge_from_butt"]-brief["existing_lower_key_cluster_edge_from_butt"],
            "lower_cap_edge_from_butt_mm": centre - P["keys"]["cap_reference_length"] / 2,
            "rod_local_y_bounds_mm": [-centre, tube_length - centre],
            "butt_reference_y_mm": 0.0, "tube_tip_reference_y_mm": tube_length,
            "overall_tip_reference_y_mm": brief["overall_length"],
            "pcb_reference_bounds_mm": pcb_bounds.tolist(),
            "pcb_reference_center_from_butt_mm": float(pcb_bounds[:, 1].mean()),
            "usb_reference_bounds_mm": placed_bounds("REFERENCE_usb").tolist(),
            "tip_frame_reference_bounds_mm": placed_bounds("XIAO_Rod_Holder").tolist(),
            "grip_pivot_from_butt_mm": None}


def references(pitch: float | None = None) -> dict[str, mf.Manifold]:
    hardware = r4.seated_hardware()
    k = P["keys"]
    z = k["pcb_z"]
    rod_start, rod_end = reference_placement()["rod_local_y_bounds_mm"]
    result = {"rod": r4.tube_y(3.5, 4.0, rod_start, rod_end), "battery": r4.battery_shape("front")}
    for i, (x, y) in enumerate(key_positions(pitch)):
        for name, shape in hardware.items():
            result[f"key_{i}_{name}"] = shape.translate((x, y, z))
        # Match R4's illustrative external cap. Its underside and mounting
        # height are not measured; this is never a bought-part fit claim.
        result[f"key_{i}_cap"] = r4.rr(k["cap_reference_width"], k["cap_reference_length"], 1.4,
                                       z + 6.1, z + 6.1 + k["cap_reference_thickness"]).translate((x, y, 0))
    return result


def source_paths() -> list[Path]:
    modules = [Path(r4.__file__), Path(r4.r2.__file__), Path(r4.base.__file__), Path(r4.base.ds.__file__)]
    own = [HERE / name for name in ["cad.py", "parameters.json", "verify_geometry.py", "render.py", "requirements.txt"]]
    parameters = [path.parent / "parameters.json" for path in modules if (path.parent / "parameters.json").exists()]
    references = sorted((BASE / "references").glob("*.json")) + sorted((BASE / "references").glob("*.stp"))
    inherited_meshes = [BASE / "exports" / f"XIAO_Rod_Holder{suffix}.stl" for suffix in ["", "-assembly"]]
    helpers = [BASE / "requirements.txt", BASE / "exports/manifest.json", Path(r4.base.__file__).parent / "verify_and_render.py",
               HERE.parent / "carbon-rod-holders-r2/exports/Assembly-reference.glb"]
    return sorted(set(own + modules + parameters + references + inherited_meshes + helpers + [BASE / "references/LICENSE-CC-BY-SA.txt"]))


def spacing_comparison() -> dict:
    k = P["keys"]
    cases = []
    for pitch in [k["baseline_pitch"], k["pitch"]]:
        cases.append({"pitch_mm": pitch, "centres_xy_mm": key_positions(pitch),
                      "outer_centre_span_mm": 2 * pitch,
                      "reference_cap_gap_mm": round(pitch - k["cap_reference_width"], 6),
                      "conservative_cap_gap_mm": round(pitch - k["cap_conservative_width"], 6),
                      "switch_body_gap_mm": pitch - 15.0,
                      "opening_bridge_mm": round(pitch - k["opening"], 6)})
    return {"key_count": 3, "cases": cases, "adjacent_travel_reduction_mm": k["baseline_pitch"] - k["pitch"],
            "outer_travel_reduction_mm": 2 * (k["baseline_pitch"] - k["pitch"]),
            "travel_reduction_percent": 100 * (1 - k["pitch"] / k["baseline_pitch"]),
            "cap_dimensions_measured": False, "physical_thumb_travel_measured": False}


def export() -> None:
    OUT.mkdir(exist_ok=True)
    records = {}
    solids = {"Key_Battery_Carrier": carrier()}
    for name, solid in solids.items():
        if name == "Key_Battery_Carrier":
            solid = solid.simplify(.0001)
        assert solid.status() == mf.Error.NoError, (name, solid.status())
        assembly = r4.mesh(solid)
        assert assembly.is_watertight and assembly.is_winding_consistent and len(assembly.split()) == 1, name
        assembly.export(OUT / f"{name}-assembly.stl")
        printed = assembly.copy()
        rotation = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
        printed.apply_transform(rotation)
        translation = trimesh.transformations.translation_matrix(-printed.bounds[0])
        printed.apply_transform(translation)
        # Match R4: normalise after STL float32 rounding and bound its change.
        rounded = mf.Manifold(mf.Mesh(np.asarray(printed.vertices, dtype=np.float32), np.asarray(printed.faces, dtype=np.uint32)))
        volume_change = abs(rounded.volume() - printed.volume)
        assert rounded.status() == mf.Error.NoError and volume_change < .01, (name, volume_change)
        printed = r4.mesh(rounded)
        printed.export(OUT / f"{name}.stl")
        final = trimesh.load_mesh(OUT / f"{name}.stl")
        assert final.is_watertight and final.is_winding_consistent and len(final.split()) == 1, name
        records[name] = {"bounds_mm": assembly.bounds.tolist(), "volume_mm3": float(assembly.volume),
                         "solid_PETG_g": float(assembly.volume / 1000 * P["print"]["density_g_cm3"]),
                         "watertight": True, "body_count": 1, "stl_float32_volume_change_mm3": volume_change,
                         "stl_sha256": r4.sha(OUT / f"{name}.stl"),
                         "assembly_stl_sha256": r4.sha(OUT / f"{name}-assembly.stl"),
                         "print_to_assembly": np.linalg.inv(translation @ rotation).tolist()}
    # The request changes only the key carrier. Preserve the supplied XIAO
    # holder bytes and its checked transform, rather than retessellating it.
    inherited = json.loads((BASE / "exports/manifest.json").read_text())["parts"]["XIAO_Rod_Holder"]
    for suffix in ["", "-assembly"]:
        shutil.copyfile(BASE / "exports" / f"XIAO_Rod_Holder{suffix}.stl", OUT / f"XIAO_Rod_Holder{suffix}.stl")
    records["XIAO_Rod_Holder"] = {**inherited, "assembly_stl_sha256": r4.sha(OUT / "XIAO_Rod_Holder-assembly.stl"), "inherited_unchanged_from": "R4 / R2"}
    export_reference(records)
    (HERE / "spacing-comparison.json").write_text(json.dumps(spacing_comparison(), indent=2) + "\n")
    print(json.dumps({"exported": list(records), "key_count": 3, "pitch_mm": P["keys"]["pitch"]}))


def export_reference(records: dict) -> None:
    """Extraction of existing export GLB/manifest code, with butt-zero placement.

    A reference-only update verifies the existing STLs and does not rewrite
    them. The new transform positions the cap edge from the user's brief;
    it does not modify the carrier or invent a measured hand pivot.
    """
    for name, record in records.items():
        for suffix, digest in [("", "stl_sha256"), ("-assembly", "assembly_stl_sha256")]:
            assert r4.sha(OUT / f"{name}{suffix}.stl") == record[digest], (name, suffix)
    placement = reference_placement()
    offset = placement["carrier_local_origin_from_butt_mm"]
    transform = trimesh.transformations.translation_matrix((0, offset, 0))
    assembly = trimesh.load_mesh(OUT / "Key_Battery_Carrier-assembly.stl")
    placement["printed_carrier_y_bounds_from_butt_mm"] = (assembly.bounds[:, 1] + offset).tolist()
    assembly.apply_transform(transform)
    assembly.visual.vertex_colors = [36, 157, 162, 255]
    scene = trimesh.Scene(metadata={"reference_license": ATTRIBUTION, "physical_fit_verified": False,
                                   "assembly_reference": placement})
    scene.add_geometry(assembly, node_name="Key_Battery_Carrier")
    for name, shape in references().items():
        item = r4.mesh(shape)
        item.apply_transform(transform)
        color = [48, 55, 65, 255] if name == "rod" else [113, 128, 150, 255] if name == "battery" else [226, 229, 233, 255]
        item.visual.vertex_colors = color
        scene.add_geometry(item, node_name="REFERENCE_" + name)
    tip_transform = trimesh.transformations.translation_matrix((0, placement["tip_local_origin_from_butt_mm"], 0))
    for name, part in canonical_tip()[0].items():
        item = part.copy()
        item.apply_transform(tip_transform)
        color = [237, 166, 73, 255] if name == "XIAO_Rod_Holder" else [54, 110, 75, 255] if name == "REFERENCE_pcb" else [175, 74, 60, 255] if name == "REFERENCE_provisional_wire_route" else [187, 192, 202, 255]
        item.visual.vertex_colors = color
        scene.add_geometry(item, node_name=name)
    scene.export(OUT / "Assembly-reference.glb")
    # The manifest is the canonical numeric assembly receipt. Read bounds
    # from the actual GLB, including its float32 quantisation, for the maths.
    exported_scene = trimesh.load(OUT / "Assembly-reference.glb", force="scene")
    def exported_bounds(node: str) -> np.ndarray:
        matrix, name = exported_scene.graph[node]
        item = exported_scene.geometry[name].copy()
        item.apply_transform(matrix)
        return item.bounds
    pcb_bounds = exported_bounds("REFERENCE_pcb")
    placement["pcb_reference_bounds_mm"] = pcb_bounds.tolist()
    placement["pcb_reference_center_from_butt_mm"] = float(pcb_bounds[:, 1].mean())
    placement["usb_reference_bounds_mm"] = exported_bounds("REFERENCE_usb").tolist()
    placement["tip_frame_reference_bounds_mm"] = exported_bounds("XIAO_Rod_Holder").tolist()
    placement["bounds_source"] = "exported Assembly-reference.glb readback"
    import os
    manifest = {"revision": SPEC["revision"], "parts": records, "key_count": 3,
                "source_sha256": {os.path.relpath(path, HERE): r4.sha(path) for path in source_paths()},
                "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                            "trimesh": trimesh.__version__, "manifold3d": version("manifold3d")},
                "assembly_reference": placement, "carrier_local_to_reference": transform.tolist(),
                "tip_local_to_reference": tip_transform.tolist(),
                "print_to_assembly_space": "carrier-local; compose carrier_local_to_reference for the butt-zero GLB",
                "assembly_glb_sha256": r4.sha(OUT / "Assembly-reference.glb"),
                "reference_attribution": ATTRIBUTION, "physical_fit_verified": False,
                "physical_strength_verified": False, "sliced": False}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-only", action="store_true", help="Update GLB/manifest while preserving every STL")
    args = parser.parse_args()
    if args.reference_only:
        export_reference(json.loads((OUT / "manifest.json").read_text())["parts"])
        print("Updated the selected overall assembly reference; existing STL files were verified and preserved.")
    else:
        export()
