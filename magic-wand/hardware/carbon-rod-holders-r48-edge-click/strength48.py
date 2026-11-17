"""Load paths beside the triangular paddle opening and below the forward OP1 eyelet."""
from functools import lru_cache


@lru_cache(maxsize=1)
def triangle_rails(h):
    """Continue both thin sides of the triangular window into their hinge-root fans.

    The R47 window begins with two 2.0 × 0.8 mm tabs. Grow the new portions
    from the existing front crossbar in the front-down print, and end them
    inside the rigid fan, ahead of the flexible arms and their squeeze stop.
    """
    fan = h.r.ARM_ROOT_Y
    # (Y, inner X, outer X, bottom Z). The upper face stays below the board.
    stations = ((-6.1, 8.15, 10.15, 18.60), (-3.7, 6.85, 10.15, 17.39),
                (.9, 6.25, 10.15, 17.32), (3.6, 5.65, 10.15, 17.30),
                (6.7, 4.85, 10.15, 17.12), (fan - 4.35, 3.35, 8.18, 17.12),
                (fan - 1.25, 2.65, 6.25, 17.12), (fan - .23, 2.55, 5.65, 17.35))
    sections = [h.box(inner, outer, y - .12, y + .12, bottom, 19.19)
                for y, inner, outer, bottom in stations]
    rail = h.union(h.mf.Manifold.batch_hull([a, b]) for a, b in zip(sections, sections[1:]))
    return h.r.mirrored(rail) - h.p.pin_relief() - h.q.switch_relief()


@lru_cache(maxsize=1)
def chin_runners(h):
    """Under the open board slot, carry the screw-end floor past its old 1.2 mm root."""
    # Follow the fitted OP1 rather than the fixed rod or a revision-specific
    # yaw. Two tapered longitudinal ribs leave the screw and socket bores open.
    front = h.h32.EYELETS[0]
    side_ribs = []
    for sign in (-1, 1):
        stations = ((3.1, front - 1.05, 7.72, .85),
                    (3.5, front + .65, 7.36, 1.24),
                    (3.7, front + 4.1, 7.08, 1.55),
                    (3.65, front + 8.8, 7.08, 1.55),
                    (3.5, front + 12.8, 7.38, 1.15),
                    (3.4, front + 14.3, 7.70, .85))
        profiles = [h.mf.Manifold.sphere(1., 24).scale((1.62, 1., radius)).translate(
            (*h.q.board_point(sign * x, y), z)) for x, y, z, radius in stations]
        side_ribs.append(h.union(h.mf.Manifold.batch_hull([a, b]) for a, b in zip(profiles, profiles[1:])))
    return h.union(side_ribs) - h.union(h.q.op1_reliefs())


def witness_boxes(h):
    """Interior material crossing each joint, independent of what the slicer deposits.

    A core in the new triangle and chin must exist in full. On the older
    shaped roots we use the actual STL intersected with the named window.
    The thickness of a spring is deliberately preserved.
    """
    def box(*limits):
        return h.box(*limits)

    def sided(sign, inner, outer, *rest):
        return box(*sorted((inner * sign, outer * sign)), *rest)

    targets = {h.BRACKET: {}, h.CARRIER: {}}
    for side, sign in (('left', -1), ('right', 1)):
        targets[h.BRACKET][f'{side} rail to front paddle'] = (
            sided(sign, 7.2, 9.7, -2.1, .35, 17.62, 18.96), True)
        targets[h.BRACKET][f'{side} triangular opening rail'] = (
            sided(sign, 6.30, 9.70, 4.9, 7.2, 17.52, 18.96), True)
        for station, label in ((h.h32.EYELETS[0] + 3.6, 'eyelet'), (h.h32.EYELETS[0] + 8.1, 'deck')):
            targets[h.CARRIER][f'{side} OP1 chin runner to {label}'] = (
                h.q.board_frame(sided(sign, 3.10, 4.05, station - 1.65, station + 1.65, 6.37, 8.24)), True)
        # R46's independent deck return and front cross brace meet the finger
        # rest at the same three-way junction, on each of the two sides.
        spine = abs(h.d.finger_rest_paths()[side[0].upper()]['spine'][0][0])
        targets[h.CARRIER][f'{side} finger-rest brace junction'] = (
            sided(sign, spine - .9, spine + .9, 9.20, 10.55, .70, 2.03), False)

    for part, bands in (('XIAO_Rod_Holder', ((-4.4, -3.1), (20.5, 22.7))),
                        ('Battery_Holder', ((-17.1, -14.9), (12.3, 14.5)))):
        targets[part] = {f'{end} rod clip crown to body': (
            box(-2.3, 2.3, *span, 4.05, 5.75), False)
            for end, span in zip(('near', 'far'), bands)}
    targets['XIAO_Near_Keeper'] = {'tongue to fixed keeper': (
        box(-7.3, -5.85, -.50, .65, 10.87, 11.79), False)}
    from battery48 import routes as battery_routes
    battery_material = battery_routes()[1]
    targets['Battery_End_Door'] = {name: (shape, True)
                                  for name, shape in battery_material['Battery_End_Door'].items()}
    targets['Cable_Clip_12_Wire'] = {'bridge joining the two clip rings': (
        box(4.47, 5.46, -.76, .76, .45, 1.96), False)}
    for name in (h.CLIP, h.CLIP + '_2'):
        targets[name] = {'heel connecting the retaining jaws': (
            box(-1.15, 1.15, -1.70, -1.16, 21.08, 21.57), False)}
    return targets


def measure_layers(engine, data, xyz, solid, window, require_full):
    """Measure fused cross-section and overlap with the immediately prior layer."""
    import audit42
    import numpy as np

    target = solid ^ window
    box = np.asarray(window.bounding_box()).reshape(2, 3)
    # One nozzle-width margin retains every bead meeting this local joint.
    # Keep a two-bead surrounding halo so the edge of the ROI cannot split
    # the stock just beside the witness.
    selected = np.all((xyz[:, :2] >= box[0, :2] - 1.) & (xyz[:, :2] <= box[1, :2] + 1.), axis=1)
    data, xyz = data[selected], xyz[selected]
    rows = []
    for top in np.unique(data[:, 7]):
        on = abs(data[:, 7] - top) < .001
        height = float(np.median(data[on, 4]))
        mid = float(top) - height / 2
        if not box[0, 2] < mid < box[1, 2]:
            continue
        core = window.slice(mid)
        nominal = target.slice(mid)
        # End slivers of the oblique PCB-frame selectors are outside their
        # full-width witness. The central layers carry the actual test.
        if core.area() < .5:
            continue
        area = nominal.area()
        actual = audit42.common.footprint(engine, data, xyz, on)
        prior = abs(data[:, 7] - (top - height)) < .001
        below = audit42.common.footprint(engine, data, xyz, prior)
        largest = max(((p ^ nominal).area() for p in actual.decompose()), default=0.)
        prior_overlap = (actual ^ below ^ nominal).area()
        digital = area / core.area()
        rows.append({'top_mm': round(float(top), 3), 'nominal_mm2': round(area, 4),
                     'single_deposited_area_mm2': round(largest, 4),
                     'previous_layer_contact_mm2': round(prior_overlap, 4),
                     'solid_core_fraction': round(digital, 4),
                     'passed': bool(area >= .35 and (not require_full or digital >= .97) and
                                    largest >= .90 * area and prior_overlap >= .84 * area)})
    return {'layers': rows, 'passed': bool(len(rows) >= 2 and all(row['passed'] for row in rows))}


def check_native(archive, scratch):
    """Check all nine pieces in the selected, reopened plate, including every changed rigid joint."""
    from pathlib import Path

    import build48 as design  # Establish the inherited CAD and native audit imports.
    import audit42
    import audit_parts47
    from native48 import digest, read, write
    import numpy as np
    import trimesh

    h = design.h
    out = archive.parent
    archive_hash = digest(archive)
    source = out / 'other-audit/build-source/exports'
    other = read(out / 'other-audit/other-parts-audit.json')
    assert other['complete_archive_sha256'] == archive_hash
    manifest = read(source / 'manifest.json')['parts']
    engine = audit_parts47.common.load_checker().audit
    data, features, _, _, offset, objects, *_ = engine.read_project(archive)
    model = audit42.common.model_mask(np.asarray(features)[data[:, 5].astype(int)])
    owners = audit42.native_support_owners(archive)
    parts = {}
    source_digests = {}
    targets = witness_boxes(h)
    assert set(targets) == set(manifest) | {h.CARRIER}
    for part, regions in targets.items():
        rows = data[model & (data[:, 6] == owners[part])]
        assert len(rows), f'No model deposition for {part}'
        if part == h.CARRIER:
            frame = read(out / 'frame.json')
            path = scratch / 'stage/R47-Key-Carrier-assembly.stl'
            inverse = np.linalg.inv(np.asarray(frame['print_to_assembly']))[:3]
            solid = design.b.load(path).transform(inverse)
            xyz = rows[:, :3] + offset - frame['bed_translation']
        else:
            path = source / (part + audit_parts47.common.SOURCE_SUFFIX)
            inverse = np.linalg.inv(np.asarray(manifest[part]['print_to_assembly']))[:3]
            mesh = trimesh.load_mesh(path)
            solid = h.mf.Manifold(h.mf.Mesh64(mesh.vertices, np.asarray(mesh.faces, np.uint64)))
            xyz = audit42.common.local_points(rows, offset, objects[part], mesh)
        source_digests[part] = digest(path)
        parts[part] = {label: measure_layers(engine, rows, xyz, solid, region.transform(inverse), full)
                       for label, (region, full) in regions.items()}
    failed = [(name, joint) for name, joints in parts.items() for joint, row in joints.items() if not row['passed']]
    report = {'archive_sha256': archive_hash, 'checker_sha256': digest(Path(__file__)),
              'mesh_sha256': source_digests, 'parts': parts, 'failures': failed,
              'passed': not failed, 'physical_strength_verified': False}
    write(out / 'strength-paths.json', report)
    if failed:
        raise ValueError(f'Native structural joints failed: {failed}')


def check_cad(h, cap, carrier):
    """Measure the actual staged meshes at both ends of the fractured-window candidate."""
    from math import inf
    from numpy import arange

    # Sections normal to assembly Y, the bracket's stacking direction.
    bracket = cap.rotate((90., 0., 0.))
    area_by_side = {}
    for name, (y0, y1, minimum) in {
        'forward rail transition': (-2.12, .36, 4.9),
        'broad triangle end': (4.74, 7.35, 9.5),
        'triangle sides to hinge fans': (7.35, 15.41, 9.4),
    }.items():
        lowest = [inf, inf]
        for y in arange(y0, y1, .12):
            cross = bracket.slice(float(y))
            for index, left in enumerate((-10.61, 3.0)):
                region = h.mf.CrossSection.square((7.61, 2.50)).translate((left, -19.45))
                lowest[index] = min(lowest[index], (cross ^ region).area())
        area_by_side[name] = {'left_min_mm2': round(lowest[0], 3), 'right_min_mm2': round(lowest[1], 3),
                              'minimum_mm2': minimum, 'passed': min(lowest) >= minimum}

    # A rectangle through the old 7.30 mm underside must be fully present in
    # the exported carrier. A runner touching the old floor only at its face
    # cannot pass this test on either side of the old chin/deck transition.
    chin = {name: round((carrier ^ selector).volume() / selector.volume(), 5)
            for name, (selector, full) in witness_boxes(h)[h.CARRIER].items() if full}
    return {'triangle_sections': area_by_side, 'chin_transfer_core_fractions': chin,
            'passed': all(item['passed'] for item in area_by_side.values()) and min(chin.values()) >= .97,
            'physical_strength_verified': False}
