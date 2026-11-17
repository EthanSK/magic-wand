"""Verify the free-edge click load path in the selected DFRobot bracket beads."""
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import trimesh

import build48 as design
import audit42
import audit_parts47
from native48 import digest, read, write

h = design.h


def bracket_targets():
    paddle = h.p.bracket()
    pusher = h.q.pusher()
    root = h.q.pusher_root()
    old_floor = h.q.old.bracket() - h.q.old_pusher_space() - h.q.switch_relief()
    floor = h.front_floor() if h.FRONT_FLOOR else old_floor
    targets = {
        'diagonal switch pusher': pusher ^ paddle,
        'pusher brace bond': (pusher + root) ^ floor ^ paddle,
        'pusher to root bond': pusher ^ root ^ paddle,
        'pusher root stock': root ^ paddle,
        'pusher root-to-floor bond': root ^ floor ^ paddle,
    }
    if h.FRONT_FLOOR:
        targets['free-edge crossbar'] = floor ^ paddle
        x = h.r.RAIL_X[0]
        for side, label in ((-1, 'left'), (1, 'right')):
            limits = sorted((side * (x - .5), side * (x + .5)))
            # Cross the nominal rail/crossbar seam, including real bracket
            # material to both sides. A merely touching edge cannot pass.
            targets[f'{label} crossbar-to-rail root'] = paddle ^ h.box(
                *limits, *h.FLOOR_FRONT, 18.50, 19.20)
    import hinge48
    targets.update(hinge48.native_targets(h))
    return targets


def bracket_support_removal(archive, original, solid, checker, data, local, model, support, record, **kwargs):
    coarse = original(solid, checker, data, local, model, support, record, **kwargs)
    if coarse['passed'] or coarse['reachable_fraction'] < .98:
        return coarse

    # A sparse 0.5 mm grid on a very small single-layer support can miss
    # cores. Keep that result and ask the identical 0.8 mm fragment both
    # questions again at 0.25 mm, plus test the whole support as one piece.
    if coarse['support_core_cells'] >= 20 or data[support, 7].max() > .201:
        return coarse
    fine = original(solid, checker, data, local, model, support, record, step=.25, **kwargs)
    # Reparse the first native layer at five times the normal spatial
    # resolution. Both exact per-move widths and owner assignments survive.
    pitch = .03
    with ZipFile(archive) as z:
        text = z.read('Metadata/plate_1.gcode').decode()
    first_layer, separator, _ = text.partition('; Z_HEIGHT: 0.4\n')
    assert separator
    paths, names, _ = checker.q.extrusion_points(first_layer, pitch)
    names = np.asarray(names)[paths[:, 5].astype(int)]
    support_id, = set(data[support, 6])
    native_support = np.char.startswith(names, 'Support') & (paths[:, 6] == support_id)
    assert np.all(paths[native_support, 7] <= .201)
    coords = paths[:, :3] + (local[0] - data[0, :3])
    low = coords[native_support, :2].min(0) - 1.
    high = coords[native_support, :2].max(0) + 1.
    near = ((coords[:, :2] >= low) & (coords[:, :2] <= high)).all(1)
    layer = near & (paths[:, 7] <= .201)
    base = layer & audit42.common.model_mask(names)
    brim = layer & (np.char.startswith(names, 'Brim') | np.char.startswith(names, 'Skirt'))
    pad = audit42.common.footprint(checker, paths, coords, native_support)
    permanent = audit42.common.footprint(checker, paths, coords, base)
    # Include half the native sampling pitch plus the maximum distance from
    # the inscribed 12-sided footprint to the true bead circle. Nothing is
    # below z=0. Pulling directly downward stays within this one slab or
    # outside the entire printed part, after the part comes off the bed.
    guard = pitch / 2 + float(paths[near, 3].max()) / 2 * (1 - np.cos(np.pi / 12)) + .0002
    support_bound = pad.offset(guard, audit42.common.mf.JoinType.Round)
    base_bound = permanent.offset(guard, audit42.common.mf.JoinType.Round)
    cad_bound = solid.trim_by_plane((0, 0, -1), -.2).project()
    overlap = (support_bound ^ (base_bound + cad_bound)).area()
    # The base recipe calls for removing the brim before support. Retain
    # its measured footprint separately from the permanent obstruction.
    brim_overlap = (support_bound ^ audit42.common.footprint(checker, paths, coords, brim)).area() if brim.any() else 0.
    complete_release = bool(pad.area() > 1. and overlap < .0001)
    fine.update(coarse_grid=coarse, native_resampling_pitch_mm=pitch, first_layer_support_area_mm2=pad.area(),
                whole_support_downward_withdrawal_overlap_mm2=overlap, brim_overlap_mm2=brim_overlap,
                per_footprint_guard_mm=guard, whole_support_downward_withdrawal_clear=complete_release)
    fine['passed'] = bool(fine['passed'] and fine['reachable_fraction'] == 1. and complete_release)
    return fine


def check(archive, scratch, output):
    targets = bracket_targets()
    assert all(shape.volume() > .15 for shape in targets.values()), {
        name: shape.volume() for name, shape in targets.items()}
    import battery48
    import battery_print48
    directory, parts = battery_print48.inputs(scratch)
    replacement_sources = {name: {**row, **{k: directory / row[k] for k in
                                          ('print_stl','assembly_stl','pad_stl') if row.get(k)}}
                           for name, row in parts.items()}
    cell_spaces, cell_material = battery48.routes()
    assert set(cell_spaces) == set(parts) and set(cell_material) == set(parts)
    assert all(row for row in cell_spaces.values()) and all(row for row in cell_material.values())
    inherited = audit42.routes

    def routes():
        gaps, material = inherited()
        return gaps, {**material, **cell_material, h.BRACKET: {**material[h.BRACKET], **targets}}

    original_grid = audit42.support_removal_grid
    with patch.object(audit42, 'routes', routes), \
         patch.object(audit42, 'support_removal_grid', lambda *a, **kw: bracket_support_removal(archive, original_grid, *a, **kw)):
        audit_parts47.check(archive, scratch, output, replacement_sources=replacement_sources,
                            replacement_routes=cell_spaces)

    engine = audit_parts47.common.load_checker().audit
    data, features, _, _, offset, objects, *_ = engine.read_project(archive)
    labels = np.asarray(features)[data[:, 5].astype(int)]
    normal = audit42.common.model_mask(labels) & (
        data[:, 6] == audit42.native_support_owners(archive)[h.BRACKET])
    exports = output / 'build-source/exports'
    record = read(exports / 'manifest.json')['parts'][h.BRACKET]
    mesh = trimesh.load_mesh(exports / (h.BRACKET + audit_parts47.common.SOURCE_SUFFIX))
    inverse = np.linalg.inv(np.asarray(record['print_to_assembly']))[:3]
    local = audit42.common.local_points(data, offset, objects[h.BRACKET], mesh)
    # Source CAD targets are deliberately independent of the deposited paths.
    printed_targets = {label: solid.transform(inverse) for label, solid in targets.items()}
    report = audit42.pusher_connectivity(engine, data, local, normal, printed_targets)
    report.update(archive_sha256=digest(archive),
                  source_cap_sha256=digest(scratch / 'stage/R47-DFRobot_Hole_Bracket-cap.stl'),
                  checker_sha256=digest(Path(__file__)))
    write(output / 'edge-click-load-path.json', report)
    if not report['passed']:
        fails = {name: [row['layer_top_mm'] for row in rows if not row['passed']]
                 for name, rows in report['regions'].items()}
        raise ValueError(f'Poorly connected click load path at native layers: {fails}')
