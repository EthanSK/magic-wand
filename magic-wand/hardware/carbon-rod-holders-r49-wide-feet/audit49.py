"""Run the R48 native geometry checks against the R49 slice and feet."""

import argparse
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import manifold3d as mf
import numpy as np
import trimesh
from shapely import STRtree, box, distance, points

from prepare49 import MODEL, SETTINGS, solid

HERE = Path(__file__).resolve().parent
R48 = HERE.parent / "carbon-rod-holders-r48-edge-click"
BASELINE = R48 / "exports/complete-plate"
sys.path.insert(0, str(R48))

import build48  # Register the checked R48 parts before loading their audit.
import audit_parts47
import bracket_paths48
import helper_starts45
import lateral45
import native48
import release45
import roof_strokes45
import scope47
from audit45 import common as key_checks
from compose47 import FUNCTIONAL

LEAD_ROUTE = "shifted Grove lead operating stroke"


def tiled_footprint_builder(footprints):
    def build(q, xy, bead_width):
        if len(xy) <= 2000:
            return footprints(q, xy, bead_width)
        # Union dense pad layers in local batches. Each bead is retained
        # whole and the final union uses the same positive fill rule.
        tiles = np.floor(xy / 5).astype(int)
        order = np.lexsort(tiles.T)
        starts = np.flatnonzero(np.any(np.diff(tiles[order], axis=0), axis=1)) + 1
        regions = [footprints(q, xy[group], bead_width[group])
                   for group in np.split(order, starts)]
        return q.CrossSection.batch_boolean(regions, mf.OpType.Add)
    return build


def source_feet(layout):
    with ZipFile(layout) as z:
        parts = ET.fromstring(z.read(SETTINGS))
        mesh_root = ET.fromstring(z.read(MODEL)).find("{*}resources")
    for obj in parts.findall("object"):
        name = obj.find("metadata[@key='name']").get("value")
        for candidate in obj.findall("part[@subtype='normal_part']"):
            title = candidate.find("metadata[@key='name']").get("value")
            if title.startswith("REMOVE AFTER PRINT"):
                yield name, solid(mesh_root.find("{*}object[@id='%s']" % candidate.get("id")))


def actual_plate_clearance(archive):
    check = audit_parts47.common.load_checker().audit
    data, features, _, settings, offset, _, _, _ = check.read_project(archive)
    with ZipFile(archive) as z:
        root = ET.fromstring(z.read("Metadata/slice_info.config"))
    owners = {o.get("name"): int(o.get("identify_id")) for o in root.findall("plate/object")}
    assert FUNCTIONAL <= set(owners)
    labels = np.asarray(features)[data[:, 5].astype(int)]
    positions = data[:, :2] + offset[:2]
    # Adjacent samples are spaced by at most STEP. Add half that distance
    # to each bead radius to enclose the plastic between sample centres.
    radii = (data[:, 3, None] + check.STEP) / 2
    assert (positions-radii).min() >= 0 and (positions+radii).max() <= 180
    masks = {name: data[:, 6] == owners[name] for name in FUNCTIONAL - {"Key_Carrier"}}
    masks["Key carrier and removable helpers"] = np.isin(
        data[:, 6], [identity for name, identity in owners.items() if name not in masks])
    masks["Timelapse tower"] = labels == "Prime tower"
    taken = np.stack(list(masks.values()))
    assert np.all(taken.sum(axis=0) == 1), "Extrusion outside defined groups"
    assert settings["timelapse_type"] == "1" and settings["enable_prime_tower"] == "1"
    layers = {}
    for top in (.2, .4):
        paths = {}
        for name, owner in masks.items():
            on_layer = owner & (np.abs(data[:, 7]-top) < .001)
            if on_layer.any():
                paths[name] = (STRtree(points(positions[on_layer])), radii[on_layer, 0])
        pairwise = []
        for i, (name, (tree, widths)) in enumerate(paths.items()):
            for other, (other_tree, other_widths) in list(paths.items())[i+1:]:
                a, b = other_tree.query_nearest(tree.geometries, all_matches=False)
                centre_dist = distance(tree.geometries[a], other_tree.geometries[b])
                lower_bound = float(centre_dist.min() - widths.max() - other_widths.max())
                if lower_bound > 4:
                    pairwise.append({"parts": [name, other], "gap": lower_bound})
                    continue
                upper_bound = float((centre_dist - widths[a] - other_widths[b]).min())
                a, b = other_tree.query(tree.geometries, predicate="dwithin",
                                        distance=upper_bound + widths.max() + other_widths.max() + 1e-7)
                centre_dist = distance(tree.geometries[a], other_tree.geometries[b])
                gap = float((centre_dist - widths[a] - other_widths[b]).min())
                pairwise.append({"parts": [name, other], "gap": gap})
        layers[f"{top:.1f}"] = {"pairwise_gap_mm": pairwise}
    upper_profiles = {}
    for name, mask in masks.items():
        rows = mask & (data[:, 7] > .401)
        if rows.any():
            lo = (positions[rows] - radii[rows]).min(0)
            hi = (positions[rows] + radii[rows]).max(0)
            upper_profiles[name] = box(*lo,*hi)
    gaps = [a.distance(b) for i,a in enumerate(upper_profiles.values())
            for b in list(upper_profiles.values())[i+1:]]
    min_low = min(pair["gap"] for layer in layers.values() for pair in layer["pairwise_gap_mm"])
    return {"archive_sha256": native48.digest(archive), "first_two_layers":layers,
            "minimum_gap_at_pad_height_mm":min_low, "minimum_gap_above_feet_mm":min(gaps),
            "passed":min_low > .65 and min(gaps) > .65, "actual_deposition_inside_bed":True}


def check_hardware(archive, scratch, layout, *, retained_outer_brims=()):
    ordinary = audit_parts47.common.inspect

    def inspect(path, exports, *args, **kwargs):
        anchors_path = exports / "anchors.json"
        anchors = native48.read(anchors_path)
        for name, pad in source_feet(layout):
            mesh = pad.to_mesh64()
            reference = exports / (name + audit_parts47.common.PAD_SUFFIX)
            trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False).export(reference)
            anchors["parts"].setdefault(name, {})["stl_sha256"] = native48.digest(reference)
        native48.write(anchors_path, anchors)
        import slice22
        import audit42

        checker = audit_parts47.common.load_checker().audit
        actual, features, _, _, offset, objects, *_ = checker.read_project(path)
        original_cable = slice22.cable_check
        name = "Cable_Clip_12_Wire"
        owner = audit42.native_support_owners(path)[name]
        labels = np.asarray(features)[actual[:, 5].astype(int)]
        cable = (actual[:, 6] == owner) & key_checks.model_mask(labels)
        cable_mesh = trimesh.load_mesh(exports / (name + audit_parts47.common.SOURCE_SUFFIX))
        cable_local = audit42.common.local_points(actual, offset, objects[name], cable_mesh)

        def cable_by_owner(_samples, _widths, _tops, transform):
            # A broad neighbouring foot can lie inside the clip's XY
            # rectangle. It cannot count as a disconnected clip wall.
            return original_cable(cable_local[cable], actual[cable, 3], actual[cable, 7], transform)

        starts = checker.start_audit
        tiled = tiled_footprint_builder(starts.bead_footprints)
        with patch.object(starts, "bead_footprints", tiled), \
             patch.object(slice22, "cable_check", cable_by_owner):
            return ordinary(path, exports, *args, **kwargs)

    output = archive.parent / "hardware-audit"
    output.mkdir(exist_ok=True)
    plate = actual_plate_clearance(archive)
    native48.write(archive.parent / "plate-clearance.json", plate)
    assert plate["passed"], "Crowded bed or interleaved pads touch in the actual slice"

    ordinary_parts = audit_parts47.check

    def evaluate(actual_archive, case, destination, **kwargs):
        # The archived rectangular screen treats interleaved bounds as
        # collisions. The footprint and upper-profile checks above measure
        # the same owners with the wider irregular feet in the actual slice.
        try:
            ordinary_parts(actual_archive, case, destination, **kwargs)
        except AssertionError:
            last = destination / "other-parts-audit.json"
            if not last.exists():
                raise
            results = native48.read(last)
            assert results["complete_archive_sha256"] == plate["archive_sha256"]
            if results["failures"] or results["complete_plate_layout"]["passed"]:
                raise
            results["complete_plate_layout"]["precise_pad_height_coverage"] = plate
            results["passed"] = True
            native48.write(last, results)

    measure_release = bracket_paths48.bracket_support_removal

    def narrow_support_release(archive, original, solid, checker, data, local, model, support, record):
        def count_cores(solid, checker, data, local, model, support, record, *, step=.5):
            # The wider pads make the full first layer expensive. Beads
            # outside the fragment lattice plus its probe radius cannot
            # affect this flood. Keep the complete CAD and native support.
            support_x = local[support, 0]
            x0, x1 = support_x.min(), support_x.max()
            _, y0, _, _, y1, _ = solid.bounding_box()
            margin = 3.5 + float(data[:, 3].max()) / 2
            near = ((local[:, 0] >= x0 - margin) & (local[:, 0] <= x1 + margin)
                    & (local[:, 1] >= y0 - margin) & (local[:, 1] <= y1 + margin))
            near |= support
            # Keep the 20-core minimum. The 0.25 mm grid only hit eleven
            # cells in the two thin footprints even with 100% reachability.
            fine_step = .15 if step == .25 else step
            return original(solid, checker, data[near], local[near], model[near], support[near],
                            record, step=fine_step)

        return measure_release(archive, count_cores, solid, checker, data, local, model, support, record)

    with patch.object(bracket_paths48, "bracket_support_removal", narrow_support_release), \
         patch.object(audit_parts47.common, "inspect", inspect), \
         patch.object(audit_parts47, "check", evaluate), \
         patch.object(audit_parts47.common, "OUTER_BRIM",
                      (set(audit_parts47.common.OUTER_BRIM) - {"Battery_End_Door", "XIAO_Near_Keeper"})
                      | set(retained_outer_brims)):
        bracket_paths48.check(archive, scratch, output)


def check_key(archive, scratch):
    out = archive.parent
    frame = native48.read(BASELINE / "frame.json")
    native48.write(out / "frame.json", frame)
    shutil.copyfile(BASELINE / "R45-Key-Carrier-layout.3mf", out / "R45-Key-Carrier-layout.3mf")
    with scope47.key_group(archive) as engine:
        checker = engine.audit
        actual = checker.read_project(archive)
        data, features, _, _, offset, *_ = actual
        tiled = tiled_footprint_builder(checker.start_audit.bead_footprints)
        with patch.object(checker, "read_project", return_value=actual), \
             patch.object(checker.start_audit, "bead_footprints", tiled):
            starts = out / "helper-starts.json"
            if not starts.exists() or native48.read(starts)["archive_sha256"] != native48.digest(archive):
                helper_starts45.inspect(archive)
            release_tab_feet(archive, checker, data, features, offset)
            roof_strokes45.inspect(archive)
            with patch.object(native48, "SELECTED", archive.name):
                native48.compare_roofs(out)
            key_release_and_clearance(archive, checker, data, features, offset, frame, scratch)


def release_tab_feet(archive, checker, data, features, offset):
    import single44

    owner = single44.previous.owners(archive)
    normal = key_checks.model_mask(np.asarray(features)[data[:, 5].astype(int)])
    ground = normal & (np.abs(data[:, 7] - .2) < .001)
    tabs = ground & (data[:, 6] == owner["Release_tabs"])
    carrier = ground & (data[:, 6] == owner["Key_Carrier"])
    xy = data[:, :2] + offset[:2]
    footprints = checker.start_audit.bead_footprints
    bead_pads = footprints(checker.q, xy[tabs], data[tabs, 3])
    carrier_contacts = footprints(checker.q, xy[carrier], data[carrier, 3])
    pieces = [{"bed_area_mm2": patch.area(), "carrier_overlap_mm2": (patch ^ carrier_contacts).area()}
              for patch in bead_pads.decompose()]
    carrier_grounded = (carrier_contacts ^ bead_pads).area() > .001
    written = {"archive_sha256": native48.digest(archive), "bed_islands": pieces,
               "carrier_grounded": carrier_grounded}
    native48.write(archive.parent / "key-tab-feet.json", written)


def key_release_and_clearance(archive, checker, data, features, offset, frame, scratch):
    out = archive.parent
    xyz = data[:, :3] + offset - frame["bed_translation"]
    kinds = data[:, 5].astype(int)
    labels = np.asarray(features)[kinds]
    import single44
    owners = single44.previous.owners(archive)
    normal = key_checks.model_mask(labels)
    masks = {name: normal & (data[:, 6] == owner) for name, owner in owners.items()}
    carrier = masks["Key_Carrier"]
    cradle = masks["External_cradle"]
    tabs = masks["Release_tabs"]
    front = masks["Front_pull_shelf"]
    rear = masks["Rear_pull_shelf"]
    release = {
        "cradle": release45.whole_bead_release(checker, data, xyz, carrier | tabs | front | rear, cradle),
        "front_shelf": lateral45.inspect(checker, data, xyz, carrier | tabs | rear, front, "-y"),
        "rear_shelf": lateral45.inspect(checker, data, xyz, carrier | tabs, rear, "+y"),
    }
    passed = all(row["clear"] for row in release.values())
    archive_hash = native48.digest(archive)
    native48.write(out / "key-release.json", {
        "archive_sha256": archive_hash,
        "removal": release,
        "passed": passed,
    })
    if not passed:
        return
    import plate47
    import route_audit45
    import tab_cleanup48
    from spaces47 import deposited_overlap

    h, b = build48.h, build48.b
    stop = native48.read(scratch / "stage/r47-checks.json")["backup_angle_deg"]
    openings, _ = plate47.routes_for(stop)()
    r = h.r
    bore = r.mirrored(r.d.axis_oval(r.AXIS_Y + r.CLICK_SHIFT, r.AXIS_Z,
        r.h29.BORE_R, r.h29.SUPPORT_X[0] - .5, r.h29.SUPPORT_X[1] + .5))
    routes = {**openings[h.CARRIER], "complete hinge bore surfaces": bore,
              tab_cleanup48.ROUTE: b.Poses([r.world(h.p.bracket(), angle)
                  for angle in np.linspace(h.q.EARLY_ANGLE, stop, 29)])}
    helpers = {"External_cradle": cradle, "Front_pull_shelf": front, "Rear_pull_shelf": rear}
    transform = np.asarray(frame["print_to_assembly"])
    keep = labels != "Prime tower"
    with tab_cleanup48.classify(archive):
        check = {name: route_audit45.inspect(checker, route, name, transform, xyz, data, kinds,
                                            features, keep, helpers, tabs, True)
                 for name, route in routes.items()}
    inverse = np.linalg.inv(transform)[:3]
    for name, row in check.items():
        if row["maximum_checked_samples_per_pose"]:
            continue
        # At empty positions a centre-point scan alone does not prove an
        # opening. Test the guarded interior against the full bead slabs.
        route = routes[name]
        poses = route.poses() if hasattr(route, "poses") else [route]
        overlap = 0.
        for pose in poses:
            target = pose.transform(inverse)
            _, _, low, _, _, high = target.bounding_box()
            if name.endswith("_mount_opening"):
                guard = checker.q.Z_GUARD + .1002
                target = target.trim_by_plane((0, 0, 1), low + guard)
                target = target.trim_by_plane((0, 0, -1), -high + guard)
            assert target.volume() > .0001, name
            volume, _, _ = deposited_overlap(checker, target, xyz[keep], data[keep])
            overlap = max(overlap, volume)
        row["guarded_interior_overlap_mm3"] = overlap
        row["unacceptable_obstruction"] |= overlap >= .0001
    qualify_lead_tabs(archive, checker, data, features, xyz, transform, keep, masks,
                      routes[LEAD_ROUTE], check[LEAD_ROUTE])
    native48.write(out / "key-working-spaces.json", {
        "archive_sha256": archive_hash,
        "parts": check,
        "passed": not any(row["unacceptable_obstruction"] for row in check.values()),
    })


def qualify_lead_tabs(archive, checker, data, features, xyz, transform, keep, masks, route, row):
    """Test the lead again after removing the very same first-layer material."""
    import route_audit45
    import tab_cleanup48

    if not row["unacceptable_obstruction"]:
        return
    # Only the labelled peel-off tabs are in question. Other contacts must
    # keep the normal route result and cannot be waived by this check.
    hits = {label for pose in row["pose_obstructions"] for label in pose["hits_by_owner_and_feature"]}
    if not hits or any(not label.startswith("release tabs /") for label in hits):
        return
    tabs = masks["Release_tabs"]
    after = keep & ~tabs
    for name in ("External_cradle", "Front_pull_shelf", "Rear_pull_shelf"):
        after &= ~masks[name]
    receipt = tab_cleanup48.check(archive, checker, route, transform, data, xyz, masks["Key_Carrier"], tabs)
    final = route_audit45.inspect(checker, route, LEAD_ROUTE, transform, xyz, data, data[:, 5].astype(int),
                                 features, after, {}, tabs, True)
    receipt["lead_clear_after_tab_removal"] = not final["pose_obstructions"]
    receipt["passed"] = bool(receipt["passed"] and receipt["affected_tabs"] and receipt["lead_clear_after_tab_removal"])
    native48.write(archive.parent / "lead-tab-removal.json", receipt)
    if receipt["passed"]:
        row.update(unacceptable_obstruction=False, requires_print_helper_removal=True,
                   temporary_hard_space_obstruction=True,
                   clear_after_all_print_helpers_and_tabs_removed=True,
                   acceptance_basis="The exact lead sweep clears after the labelled exterior tabs are removed. The grip and remaining edge are checked in lead-tab-removal.json.")


def check_saved_lead(archive, scratch):
    """Update just the lead route when the other exact-archive results exist."""
    import plate47
    import single44

    out = archive.parent
    report = native48.read(out / "key-working-spaces.json")
    release = native48.read(out / "key-release.json")
    assert report["archive_sha256"] == release["archive_sha256"] == native48.digest(archive)
    assert release["passed"]
    frame = native48.read(out / "frame.json")
    stop = native48.read(scratch / "stage/r47-checks.json")["backup_angle_deg"]
    route = plate47.routes_for(stop)()[0][build48.h.CARRIER][LEAD_ROUTE]
    with scope47.key_group(archive) as engine:
        checker = engine.audit
        data, features, _, _, offset, *_ = checker.read_project(archive)
        xyz = data[:, :3] + offset - frame["bed_translation"]
        labels = np.asarray(features)[data[:, 5].astype(int)]
        model = key_checks.model_mask(labels)
        masks = {name: model & (data[:, 6] == owner)
                 for name, owner in single44.previous.owners(archive).items()}
        tiled = tiled_footprint_builder(checker.start_audit.bead_footprints)
        with patch.object(checker.start_audit, "bead_footprints", tiled):
            qualify_lead_tabs(archive, checker, data, features, xyz, np.asarray(frame["print_to_assembly"]),
                              labels != "Prime tower", masks, route, report["parts"][LEAD_ROUTE])
    report["passed"] = not any(row["unacceptable_obstruction"] for row in report["parts"].values())
    native48.write(out / "key-working-spaces.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("key", "hardware", "lead"))
    parser.add_argument("archive", type=Path)
    parser.add_argument("layout", type=Path)
    parser.add_argument("r48_scratch", type=Path)
    args = parser.parse_args()
    if args.phase == "hardware":
        check_hardware(args.archive, args.r48_scratch, args.layout)
    elif args.phase == "lead":
        check_saved_lead(args.archive, args.r48_scratch)
    else:
        check_key(args.archive, args.r48_scratch)
