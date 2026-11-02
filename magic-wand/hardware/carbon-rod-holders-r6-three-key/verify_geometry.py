#!/usr/bin/env python3
"""Check the exported three-key R6 carrier with `python verify_geometry.py`.

The checks compose R4's sourced part shapes and assembly routes. They verify
CAD space and intended joints, not cap fit, printed strength or thumb comfort.
"""
import json
import numpy as np
import manifold3d as mf
import trimesh
import cad


def overlap(a: mf.Manifold, b: mf.Manifold) -> float:
    return max(0.0, float((a ^ b).volume()))


def check() -> None:
    out = cad.OUT
    manifest = json.loads((out / "manifest.json").read_text())
    for path, digest in manifest["source_sha256"].items():
        assert cad.r4.sha(cad.HERE / path) == digest, ("Stale dependency", path)
    for name, record in manifest["parts"].items():
        for suffix, key in [("", "stl_sha256"), ("-assembly", "assembly_stl_sha256")]:
            path = out / f"{name}{suffix}.stl"
            assert cad.r4.sha(path) == record[key], path
            mesh = trimesh.load_mesh(path)
            assert mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split()) == 1, path
    mesh = trimesh.load_mesh(out / "Key_Battery_Carrier-assembly.stl")
    solid = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.uint32)))
    assert solid.status() == mf.Error.NoError
    r4 = cad.r4
    k = cad.P["keys"]
    z = k["pcb_z"]
    positions = cad.key_positions()
    assert len(positions) == k["count"] == 3
    assert positions == [(-18.5, 0), (0, 0), (18.5, 0)]
    hw = r4.seated_hardware()
    bounds = np.array(hw["socket"].bounding_box())
    centre = (bounds[:3] + bounds[3:]) / 2
    max_socket = hw["socket"].translate((-centre[0], -centre[1], -bounds[2])).scale((13.55 / 13.15, 6.95 / 6.85, 3.25 / 3.05)).translate((centre[0], centre[1], k["socket_pocket_bottom"]))
    refs = cad.references()
    regions = {name: overlap(solid, shape) for name, shape in refs.items() if not name.endswith("_cap")}
    regions["battery_reserve"] = overlap(solid, r4.battery_shape("front", True))
    regions["wire_bus"] = overlap(solid, r4.wire_bus(-20, 55))
    regions["full_tube_entry"] = overlap(solid, r4.cyl(4.199, -85, 85).rotate((-90, 0, 0)))
    assert max(regions.values()) < .002, regions
    # R4 socket loading route: enter offset through the empty key aperture,
    # align below the lip, then lower onto the floor. Sample at <=0.2mm.
    poses = [(-2.5, -4.824, float(h)) for h in np.linspace(12, .6, 58)]
    poses += [(-2.5 * (1-t), -4.824 * (1-t), .6) for t in np.linspace(0, 1, 29)]
    poses += [(0, 0, float(h)) for h in np.linspace(.6, 0, 4)]
    routes, joints, clip_capture, press_stops, cap_sweeps = {}, {}, {}, {}, {}
    for i, (x, y) in enumerate(positions):
        for label, socket in [("nominal", hw["socket"]), ("maximum_size_sensitivity", max_socket)]:
            routes[f"key_{i}_{label}"] = max(overlap(solid, socket.translate((x + a, y + b, z + c))) for a, b, c in poses)
        rail = r4.rib((x - 8.2, y - 9.4, z + 1.4), (x + 8.2, y - 9.4, z + 1.4), 1.25)
        seat = r4.key_seat(outer_side=1 if x > 0 else -1 if x < 0 else 0).translate((x, y, z))
        joints[str(i)] = overlap(solid, seat ^ rail)
        clip_capture[str(i)] = overlap(solid, hw["switch"].translate((x, y, z + .4)))
        press_stops[str(i)] = overlap(solid, hw["switch"].translate((x, y, z - .25)))
        # Continuous union of the illustrative cap over its entire vertical
        # stroke. A 17.5mm square also tests the unconfirmed cap clocking.
        swept = r4.rr(k["cap_conservative_width"], k["cap_reference_length"], 1.4,
                      z + 6.1 - k["cap_travel_check"], z + 6.1 + k["cap_reference_thickness"]).translate((x, y, 0))
        cap_sweeps[str(i)] = overlap(solid, swept)
    assert max(routes.values()) < .002, routes
    assert min(joints.values()) > 1, joints
    assert min(clip_capture.values()) > .02 and min(press_stops.values()) > .02
    assert max(cap_sweeps.values()) < .002, cap_sweeps
    bands = {str(y): float((r4.tube_y(4.25, 5.35, y-.4, y+.4) - solid).volume()) for y in [-12, 11.5, 48.5]}
    assert max(bands.values()) < .002, bands
    above_face = overlap(solid, r4.box(-80, 80, -90, 90, z + 2.2501, 40))
    assert above_face < .002
    cap_pairs = {f"{i}_{j}": overlap(refs[f"key_{i}_cap"], refs[f"key_{j}_cap"]) for i in range(3) for j in range(i+1, 3)}
    assert max(cap_pairs.values()) < .002
    assert cad.r4.sha(out / "XIAO_Rod_Holder.stl") == cad.r4.sha(cad.BASE / "exports/XIAO_Rod_Holder.stl")
    comparison = json.loads((cad.HERE / "spacing-comparison.json").read_text())
    assert comparison == json.loads(json.dumps(cad.spacing_comparison()))
    scene = trimesh.load(out / "Assembly-reference.glb", force="scene")
    assert cad.r4.sha(out / "Assembly-reference.glb") == manifest["assembly_glb_sha256"]
    def world_mesh(node: str) -> trimesh.Trimesh:
        transform, name = scene.graph[node]
        item = scene.geometry[name].copy()
        item.apply_transform(transform)
        return item
    rod_bounds = world_mesh("REFERENCE_rod").bounds
    placement = manifest["assembly_reference"]
    assert np.allclose(rod_bounds[:, 1], [0, placement["rod_length"]], atol=1e-4), rod_bounds
    cap_nodes = [node for node in scene.graph.nodes_geometry if node.endswith("_cap")]
    assert len(cap_nodes) == 3
    cap_edges = {node: float(world_mesh(node).bounds[0, 1]) for node in cap_nodes}
    assert all(abs(edge-placement["lower_key_cluster_edge_from_butt"]) < 1e-4 for edge in cap_edges.values()), cap_edges
    assembled_carrier_bounds = world_mesh("Key_Battery_Carrier").bounds
    expected = mesh.bounds.copy()
    expected[:, 1] += placement["carrier_local_origin_from_butt_mm"]
    assert np.allclose(assembled_carrier_bounds, expected, atol=1e-4)
    tip_frame_bounds = world_mesh("XIAO_Rod_Holder").bounds
    assert abs(tip_frame_bounds[1, 1] - rod_bounds[1, 1]) < 1e-4
    overall_bounds = np.array([world_mesh(node).bounds for node in scene.graph.nodes_geometry])
    overall_y_bounds = [float(overall_bounds[:, 0, 1].min()), float(overall_bounds[:, 1, 1].max())]
    assert np.allclose(overall_y_bounds, [0, placement["overall_length"]], atol=1e-4), overall_y_bounds
    assert abs((overall_y_bounds[1]-rod_bounds[1, 1])-placement["tip_seating"]["positive_end_overhang_mm"]) < 1e-4
    pcb_bounds = world_mesh("REFERENCE_pcb").bounds
    usb_bounds = world_mesh("REFERENCE_usb").bounds
    assert np.allclose(pcb_bounds, placement["pcb_reference_bounds_mm"], atol=1e-4)
    assert np.allclose(usb_bounds, placement["usb_reference_bounds_mm"], atol=1e-4)
    assert abs(pcb_bounds[:, 1].mean()-placement["pcb_reference_center_from_butt_mm"]) < 1e-4
    def as_solid(item: trimesh.Trimesh) -> mf.Manifold:
        value = mf.Manifold(mf.Mesh(np.asarray(item.vertices, dtype=np.float32), np.asarray(item.faces, dtype=np.uint32)))
        assert value.status() == mf.Error.NoError
        return value
    tip_solids = {name: as_solid(world_mesh(name)) for name in
                  ["XIAO_Rod_Holder", "REFERENCE_pcb", "REFERENCE_usb", "REFERENCE_provisional_wire_route"]}
    carrier_solids = {"carrier": as_solid(world_mesh("Key_Battery_Carrier")),
                      "battery_nominal": as_solid(world_mesh("REFERENCE_battery")),
                      "battery_reserve": r4.battery_shape("front", True).translate((0, placement["carrier_local_origin_from_butt_mm"], 0))}
    carrier_solids.update({node: as_solid(world_mesh(node)) for node in scene.graph.nodes_geometry if node.startswith("REFERENCE_key_")})
    placement_tests = {}
    for label, shift in [("proposed", 0), ("existing_100mm_edge", placement["existing_lower_key_cluster_edge_from_butt"]-placement["lower_key_cluster_edge_from_butt"]),
                         ("intermediate_90mm_edge", 90-placement["lower_key_cluster_edge_from_butt"])]:
        intersections = {f"{name}__{tip_name}": overlap(item.translate((0, shift, 0)), tip_item)
                         for name, item in carrier_solids.items() for tip_name, tip_item in tip_solids.items()}
        placement_tests[label] = {"maximum_intersection_mm3": max(intersections.values()),
                                  "positive_intersections_mm3": {name: value for name, value in intersections.items() if value > .002}}
    assert placement_tests["proposed"]["maximum_intersection_mm3"] < .002, placement_tests
    frame_axial_gap = float(tip_frame_bounds[0, 1]-assembled_carrier_bounds[1, 1])
    assert frame_axial_gap >= 2.0-1e-4
    assert placement["grip_pivot_from_butt_mm"] is None
    report = {"passed": True, "key_count": 3, "pitch_mm": k["pitch"],
              "checker_sha256": r4.sha(cad.HERE / "verify_geometry.py"), "manifest_sha256": r4.sha(out / "manifest.json"),
              "bought_part_and_corridor_intersection_mm3": regions, "socket_loading_route_intersection_mm3": routes,
              "socket_route_max_sample_step_mm": .2, "front_rail_joint_overlap_mm3": joints,
              "switch_clip_capture_mm3": clip_capture, "switch_flange_stop_mm3": press_stops,
              "missing_ring_band_mm3": bands, "above_common_print_face_mm3": above_face,
              "illustrative_3_3mm_cap_swept_intersection_mm3": cap_sweeps, "illustrative_cap_pair_intersection_mm3": cap_pairs,
              "assembly_reference_rod_y_bounds_mm": rod_bounds[:, 1].tolist(),
              "assembly_reference_lower_cap_edges_from_butt_mm": cap_edges,
              "assembly_reference_carrier_y_bounds_mm": assembled_carrier_bounds[:, 1].tolist(),
              "assembly_reference_tip_frame_y_bounds_mm": tip_frame_bounds[:, 1].tolist(),
              "assembly_reference_overall_y_bounds_mm": overall_y_bounds,
              "pcb_reference_bounds_mm": pcb_bounds.tolist(), "usb_reference_bounds_mm": usb_bounds.tolist(),
              "pcb_reference_center_from_butt_mm": float(pcb_bounds[:, 1].mean()),
              "carrier_to_tip_frame_axial_gap_mm": frame_axial_gap, "placement_collision_tests": placement_tests,
              "carrier_to_usb_body_axial_gap_mm": float(usb_bounds[0, 1]-assembled_carrier_bounds[1, 1]),
              "external_usb_plug_mould_modeled": False, "charging_lead_access_verified": False,
              "charging_access_limit": "Only the USB connector body is modeled. Axial gaps and a sliding carrier do not establish clearance for an actual cable plug mould or lead bend.",
              "tip_end_overhang_is_provisional_wire_envelope": True,
              "edge_definition_is_assumed": True, "grip_pivot_is_not_claimed": True,
              "sensor_stls_unchanged": True, "community_CAD_is_not_manufacturer_certified": True,
              "purchased_cap_underside_and_full_travel_verified": False, "physical_fit_verified": False,
              "physical_strength_verified": False, "sliced": False}
    (out / "geometry-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: three sourced switch/socket seats, socket routes, joints, tube and battery clearances; physical fit unverified.")


if __name__ == "__main__":
    check()
