"""Repack the R48 print with separate tear-off feet and open-sided support ribs."""

import argparse
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import manifold3d as mf
import numpy as np
from shapely import MultiPoint, Polygon, STRtree, affinity, box, simplify, union_all, voronoi_polygons

CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
MODEL = "3D/3dmodel.model"
SETTINGS = "Metadata/model_settings.config"
TITLE = "Magic Wand R49 wide feet and open support ribs - A1 mini PETG"
TWO_LAYER_FEET = {"Battery_End_Door", "XIAO_Near_Keeper"}
HELPERS = {"External_cradle", "Release_tabs", "Front_pull_shelf", "Rear_pull_shelf"}
BED = box(3, 3, 177, 177)
# Includes the previous measured Smooth tower and conservative bead clearance.
TOWER = box(114, 14, 142, 41)
R48 = Path(__file__).resolve().parent.parent / "carbon-rod-holders-r48-edge-click"


def fields(element):
    return {entry.get("key"): entry.get("value") for entry in element.findall("metadata")}


def set_fields(element, updates):
    for key, value in updates.items():
        node = element.find(f"metadata[@key='{key}']")
        if node is None:
            node = ET.SubElement(element, "metadata", key=key)
        node.set("value", value)


def solid(node):
    mesh = node.find("{*}mesh")
    vertices = np.array([[float(v.get(k)) for k in "xyz"] for v in mesh.find("{*}vertices")])
    triangles = np.array([[int(t.get(k)) for k in ("v1", "v2", "v3")]
                          for t in mesh.find("{*}triangles")], dtype=np.uint64)
    result = mf.Manifold(mf.Mesh64(vertices, triangles))
    assert result.status() == mf.Error.NoError, node.attrib
    return result


def write_mesh(object_node, shape):
    original = object_node.find("{*}mesh")
    if original is not None:
        object_node.remove(original)
    data = shape.to_mesh64()
    mesh = ET.SubElement(object_node, f"{{{CORE}}}mesh")
    vertices = ET.SubElement(mesh, f"{{{CORE}}}vertices")
    triangles = ET.SubElement(mesh, f"{{{CORE}}}triangles")
    for row in data.vert_properties[:, :3]:
        ET.SubElement(vertices, f"{{{CORE}}}vertex", **{
            key: f"{value:.12g}" for key, value in zip("xyz", row, strict=True)})
    for row in data.tri_verts:
        ET.SubElement(triangles, f"{{{CORE}}}triangle", **{
            key: str(value) for key, value in zip(("v1", "v2", "v3"), row, strict=True)})


def polygons(shape):
    if isinstance(shape, Polygon):
        if not shape.is_empty:
            yield shape
    else:
        for child in getattr(shape, "geoms", ()):
            yield from polygons(child)


def planar(section):
    shells = []
    holes = []
    for ring in section.to_polygons():
        if len(ring) >= 3:
            contour = Polygon(ring)
            (shells if contour.exterior.is_ccw else holes).append(contour)
    if not shells:
        return Polygon()
    # Each Manifold hole belongs to its nearest enclosing shell. Assign
    # rings in one pass rather than overlaying thousands of tiny bead gaps.
    tree = STRtree(shells)
    interiors = [[] for _ in shells]
    for hole in holes:
        containing = tree.query(hole, predicate="covered_by")
        if not len(containing):
            # Touching rings can differ by less than geometric tolerance.
            containing = tree.query(hole.representative_point(), predicate="within")
        parent = min(containing, key=lambda i: shells[i].area)
        interiors[parent].append(hole.exterior.coords)
    return union_all([Polygon(shell.exterior.coords, rings).buffer(0)
                      for shell, rings in zip(shells, interiors, strict=True)])


def footprint(shape):
    # The new feet stay out of vertical apertures and open clips.
    return union_all([Polygon(p.exterior) for p in polygons(planar(shape.project()))])


def extrude(region, height):
    rings = []
    for poly in polygons(region):
        poly = poly.normalize()
        # Shapely normalizes exteriors clockwise. Positive winding for Manifold.
        rings.append(list(poly.exterior.coords)[-2::-1])
        rings.extend(list(hole.coords)[-2::-1] for hole in poly.interiors)
    return mf.CrossSection(rings).extrude(height)


def territories(grounds, gap=1.0):
    # Use all boundaries, not one centroid per part. Long holders and small
    # clips can then share the plate without clipping the long holders' ends.
    point_owners = {}
    for key, region in grounds.items():
        for poly in polygons(region):
            line = poly.exterior
            for distance in np.arange(0, line.length, 1.6):
                point = line.interpolate(float(distance))
                xy = tuple(round(v, 5) for v in point.coords[0])
                point_owners.setdefault(xy, key)
    cells = voronoi_polygons(MultiPoint(list(point_owners)), extend_to=BED, ordered=True)
    assert len(cells.geoms) == len(point_owners)
    by_owner = {key: [] for key in grounds}
    for key, cell in zip(point_owners.values(), cells.geoms, strict=True):
        by_owner[key].append(cell)
    return {key: union_all(parts).intersection(BED).buffer(-gap)
            for key, parts in by_owner.items()}


def side_ties(body):
    """Use only the two lateral outer lands of the flat door and keeper."""
    base = planar(body.slice(.1)) & planar(body.slice(.3))
    x0, y0, x1, y1 = base.bounds
    sides = []
    for left in (True, False):
        ties = []
        edge = x0 if left else x1
        x_range = (edge - 2.6, edge + .23) if left else (edge - .23, edge + 2.6)
        for target in (.23, .77):
            y_target = y0 + (y1-y0)*target
            locations = sorted(np.arange(y0+.5, y1-.4, .10), key=lambda y: abs(y-y_target))
            for y in locations:
                neck = box(x_range[0], y-.57, x_range[1], y+.57)
                if (neck & base).area > .20 and all(neck.distance(other) > 1.5 for other in ties):
                    ties.append(neck)
                    break
        assert ties
        sides.append(union_all(ties))
    return sides


def window_has_printable_edges(original, candidate, slot, bottom, ridge):
    lower = candidate.slice(bottom - .1)
    original_lower = original.slice(bottom - .1)
    slot_xy = slot.project().offset(.60)
    for top in np.arange(bottom + .2, ridge + .42, .2):
        height = float(top) - .1
        current = candidate.slice(height)
        old = original.slice(height)
        # Check what changed near the cut. An inherited contact tip outside
        # this window does not determine whether the new wall is supported.
        old_overhang = old - original_lower.offset(.24)
        new_overhang = (current - lower.offset(.24)) ^ slot_xy
        if (new_overhang - old_overhang.offset(.04)).area() > .009:
            return False
        for island in current.decompose():
            if island.offset(-.5).is_empty() and (island ^ slot_xy).area() > .005:
                original_island = next((p for p in old.decompose() if (p ^ island).area() > .001), None)
                if original_island is None or (original_island - island).area() > .01:
                    return False
        lower, original_lower = current, old
    return True


def open_ribs(shape, rib_rotation):
    """Cut narrow side windows with tapered roofs while keeping top contacts."""
    edited = []
    removal = 0.
    windows = 0
    for piece in shape.decompose():
        aligned = piece.rotate((0, 0, -rib_rotation))
        x0,y0,z0,x1,y1,z1 = aligned.bounding_box()
        if z0 < .001 and (z1-z0) > 5 and (y1-y0) > 5 and piece.volume() > 18:
            protected_top = aligned - aligned.translate((0, 0, -1.8))
            old_volume = aligned.volume()
            best_shape, best_loss = None, 2.
            for half_width_limit, height in ((3.8,10.),(2.4,7.),(1.35,4.5)):
                half_width = min(half_width_limit, (y1-y0)*.22)
                shoulder = min(z1*.32,height)
                for fraction in (.5,.3,.7,.4,.6):
                    middle = y0 + fraction*(y1-y0)
                    bottom = 1.2
                    ridge = shoulder + half_width*1.3
                    profile = [(middle-half_width,bottom), (middle+half_width,bottom),
                               (middle+half_width,shoulder), (middle,ridge),
                               (middle-half_width,shoulder)]
                    slot = mf.CrossSection([profile]).extrude(x1-x0+2).transform(
                        ((0,0,1,x0-1),(1,0,0,0),(0,1,0,0)))
                    if (slot ^ protected_top).volume() > .0001:
                        continue
                    candidate = aligned - slot
                    loss = old_volume - candidate.volume()
                    if (loss > best_loss and len(candidate.decompose()) == 1
                            and window_has_printable_edges(aligned, candidate, slot, bottom, ridge)):
                        best_shape, best_loss = candidate, loss
            if best_shape is not None:
                piece = best_shape.rotate((0,0,rib_rotation))
                removal += best_loss
                windows += 1
        edited.append(piece)
    return mf.Manifold.compose(edited), {"windows": windows, "removed_mm3": removal}


def removal_shadow(region, travel_y):
    rectangles = []
    for shape in polygons(region):
        points = list(shape.exterior.coords)
        rectangles.append(shape)
        rectangles.append(affinity.translate(shape, yoff=travel_y))
        for a, b in zip(points, points[1:]):
            rectangles.append(Polygon([a,b,(b[0],b[1]+travel_y),(a[0],a[1]+travel_y)]))
    return union_all([area for area in rectangles if area.is_valid and area.area > 0])


def dfr_loading_keepout(name, body):
    sys.path.insert(0, str(R48))
    import build48  # Configure the archived R48 assembly before evaluating its routes.
    import audit42
    import trimesh

    exports = R48 / "exports"
    record = json.loads((exports / "manifest.json").read_text())["parts"][name]
    reference = trimesh.load_mesh(exports / f"{name}-SOURCE-REQUIRES-PREPARATION.stl")
    shift = (np.asarray(body.bounding_box()).reshape(2, 3) - reference.bounds).mean(0)
    tolerance = np.asarray(body.bounding_box()).reshape(2, 3) - (reference.bounds + shift)
    assert np.abs(tolerance).max() < .001, "Bracket print frame differs from the archived source"
    inverse = np.linalg.inv(np.asarray(record["print_to_assembly"]))[:3]
    loading = audit42.routes()[0][name]["DFRobot PCB and connector-pin loading"]
    spans = []
    for pose in loading.poses():
        keepout = pose.transform(inverse).translate(shift)
        bed_slab = keepout.trim_by_plane((0, 0, 1), -.03).trim_by_plane((0, 0, -1), -.43)
        if not bed_slab.is_empty():
            spans.append(planar(bed_slab.project()))
    result = union_all(spans)
    assert result.area > 1., "Empty bed keepout for DFRobot loading"
    return result


def expand_seed(seed, cell, blockers, blocker_gap=0.625):
    # Keep long fingers and other remnants narrower than two bead widths
    # from being exported as an independent bed island.
    candidate = cell - blockers.buffer(blocker_gap)
    free = candidate.union(seed)
    opened = free.buffer(-.75).buffer(.75)
    connected = [poly for poly in polygons(opened) if poly.intersection(seed).area > .6]
    grown = simplify(union_all(connected), .035, preserve_topology=True)
    return (grown & candidate) | seed


def separate_feet(seeds, cell, blockers, grow=None):
    if len(seeds) == 1:
        return expand_seed(seeds[0], cell, blockers)
    local_cells = territories(dict(enumerate(seeds)), gap=.7)
    widened = []
    for index, seed in enumerate(seeds):
        if grow is not None and not grow(seed):
            widened.append(seed)
            continue
        neighbors = union_all([other for i, other in enumerate(seeds) if i != index])
        widening = expand_seed(seed, cell & local_cells[index], blockers | neighbors)
        # Existing source clearances can be under the spacing for new pads.
        # New area must not join any other slice island.
        assert ((widening - seed) & neighbors.buffer(.35)).area < .00005
        widened.append(widening)
    assert all((a & b).area < .00001 for i, a in enumerate(widened) for b in widened[i+1:])
    return union_all(widened)


def prepare(source, target, report):
    ET.register_namespace("", CORE)
    with ZipFile(source) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    model = ET.fromstring(files[MODEL])
    roots = model.find("{*}resources")
    resources = {obj.get("id"): obj for obj in roots}
    settings = ET.fromstring(files[SETTINGS])
    cfg = {obj.get("id"): obj for obj in settings.findall("object")}
    build = {}
    for item in model.find("{*}build"):
        object_id = item.get("objectid")
        transform = tuple(map(float, item.get("transform").split()))
        assert transform[:9] == (1,0,0,0,1,0,0,0,1)
        assert transform[-1] == 0.
        shift = transform[9:]
        record = cfg[object_id]
        part = resources[object_id]
        names = {p.get("id"): fields(p).get("name") for p in record.findall("part")
                 if p.get("subtype") == "normal_part"}
        assert names
        parts = part.find("{*}components")
        originals = []
        for element in parts:
            key = element.get("objectid")
            if key in names:
                assert not element.get("transform")
                originals.append((key, solid(resources[key]).translate(shift)))
        name = fields(record)["name"]
        body_id, body = originals[0]
        ground = union_all([planar(p.slice(.1)) for _,p in originals])
        build[name] = dict(geometry=body, body_id=body_id, config=record, shift=shift,
                           model_parts=parts, originals=originals, ground=ground,
                           silhouette=footprint(body))
    # Include two-layer solids and the occupied wipe tower in the allocation.
    cells = territories({**{name: row["ground"] for name,row in build.items()}, "Tower":TOWER})
    bracket = "DFRobot_Hole_Bracket"
    loading_space = dfr_loading_keepout(bracket, build[bracket]["geometry"])
    carrier_ground = build["Key_Carrier"]["ground"]
    evidence = {}
    next_id = max(map(int, resources)) + 1
    # The thin carrier pad stays in place while both shelves are extracted.
    # Allocate it first so the two shelf routes account for its final shape.
    ordered = sorted(build, key=lambda name: name != "Release_tabs")
    for name in ordered:
        row = build[name]
        body = row["geometry"]
        blockers = union_all([other["silhouette"] for n,other in build.items()
                              if not (n == name and name in HELPERS)] + [TOWER])
        foreign_ground = union_all([other["ground"] for n,other in build.items() if n != name])
        blockers |= foreign_ground | loading_space
        initial = row["ground"].area
        previous = row["originals"][1:]
        # Key carrier's thin anchor is a separate owner called Release_tabs.
        if name == "Key_Carrier":
            continue
        if previous:
            assert len(previous) == 1
            anchor_id, existing = previous[0]
            seeds = list(polygons(planar(existing.slice(.1))))
        elif name in TWO_LAYER_FEET:
            anchor_id, existing = None, mf.Manifold()
            seeds = side_ties(body)
            set_fields(row["config"], {"brim_type":"no_brim"})
        else:
            # Only already disposable helpers may be widened in their own
            # mesh. Require separate tear-off resources for finished parts.
            assert name in HELPERS, name
            anchor_id, existing = row["body_id"], body
            seeds = list(polygons(row["ground"]))
        if name in ("Front_pull_shelf", "Rear_pull_shelf"):
            travel = 175 if name == "Front_pull_shelf" else -175
            nearby_fixed = [build[key]["geometry"] for key in
                            ("Key_Carrier", "External_cradle", "Release_tabs")]
            opposite = "Rear_pull_shelf" if name == "Front_pull_shelf" else "Front_pull_shelf"
            nearby_fixed.append(build[opposite]["geometry"])
            snap_shadow = union_all([planar(shape.trim_by_plane((0,0,-1),-.45).project())
                                     for shape in nearby_fixed])
            blockers |= removal_shadow(snap_shadow, travel)
            blockers |= removal_shadow(release_tab_foot, travel)
        if name == "Release_tabs":
            # Keep the full sliding routes of the original shelf feet. A
            # stationary foot can obstruct a moving shelf even if their
            # printable territories are separated perfectly on the bed.
            blockers |= removal_shadow(build["Front_pull_shelf"]["ground"], -175)
            blockers |= removal_shadow(build["Rear_pull_shelf"]["ground"], 175)
            # Preserve the inherited lands. Widen only the ones that have
            # deliberate overlap with the key carrier's first layer.
            enlarged = separate_feet(
                seeds, cells[name], blockers, grow=lambda seed: (seed & carrier_ground).area > .05)
        else:
            enlarged = separate_feet(seeds, cells[name], blockers)
        if name == "Release_tabs":
            release_tab_foot = enlarged
        original_feet = union_all(seeds)
        # Do not invent low support plastic inside another existing owner.
        added = enlarged - original_feet
        new_shape = extrude(enlarged, .2 if name == "Release_tabs" else .4)
        assert new_shape.status() == mf.Error.NoError
        if name == "External_cradle":
            # Open the load-bearing ribs before bonding the widened bed feet.
            assert anchor_id == row["body_id"]
            body, window_report = open_ribs(body, 29.)
            existing = body
        elif name == "Front_pull_shelf":
            assert anchor_id == row["body_id"]
            body, window_report = open_ribs(body, 0.)
            existing = body
        else:
            window_report = {"windows":0,"removed_mm3":0.}
        if anchor_id is None:
            anchor_id = str(next_id)
            next_id += 1
            resource = ET.SubElement(roots, f"{{{CORE}}}object", id=anchor_id, type="model")
            resources[anchor_id] = resource
            ET.SubElement(row["model_parts"], f"{{{CORE}}}component", objectid=anchor_id)
            anchor = ET.SubElement(row["config"], "part", id=anchor_id, subtype="normal_part")
            set_fields(anchor, {"name":f"REMOVE AFTER PRINT - {name} wide feet"})
        result = existing + new_shape
        assert result.status() == mf.Error.NoError
        write_mesh(resources[anchor_id], result.translate(tuple(-v for v in row["shift"])))
        evidence[name] = {"before_first_layer_mm2":initial,
                          "after_first_layer_mm2":float(row["ground"].union(enlarged).area),
                          "new_pad_mm2":float(added.area), "remodeled_support":window_report,
                          "independent_feet": len(seeds)}
    set_fields(settings.find("plate"), {"plater_name":TITLE})
    files[MODEL] = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    files[SETTINGS] = ET.tostring(settings, encoding="utf-8", xml_declaration=True)
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name,content)
    data = {"nominal_bed_clearance_between_territories_mm":2.,
            "key_carrier_bed_anchor":"Release_tabs wide foot", "parts":evidence}
    report.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path)
    parser.add_argument("target",type=Path)
    parser.add_argument("report",type=Path)
    args=parser.parse_args()
    prepare(args.source,args.target,args.report)
