"""Check the right middle finger-rest branch where it meets the third guard leg."""
from pathlib import Path
from zipfile import ZipFile
import json
import math

import manifold3d as mf
import numpy as np
import trimesh


JOINT = 'R44 R middle branch-to-inner leg bond'
SAMPLE = .03
EROSION = .075


def cutting_plane(point, normal):
    pose = trimesh.geometry.align_vectors(normal / np.linalg.norm(normal), [0., 0., 1.])
    pose[:3, 3] = -pose[:3, :3] @ point
    return pose[:3]


def native_samples(archive, frame, bounds, *, sequences=False):
    import audit42
    import audit45
    import single44

    checker = audit45.common.load_checker().audit
    low, high = np.asarray(bounds).reshape(2, 3)
    def marker(z):
        return '; Z_HEIGHT: ' + f'{z:.1f}'.rstrip('0').rstrip('.') + '\n'
    with ZipFile(archive) as z:
        text = z.read('Metadata/plate_1.gcode').decode()
        settings = json.loads(z.read('Metadata/project_settings.config'))
    # Include a full preceding and following layer outside the test block.
    start = math.floor((low[2] - .4) / .2) * .2
    end = math.ceil((high[2] + .4) / .2) * .2
    text = text[text.index(marker(start)):text.index(marker(end))]
    data, features, _ = checker.q.extrusion_points(text, SAMPLE)
    delta = np.array([float(v) for v in settings['extruder_offset'][0].split('x')])
    xy = data[:, :2] + delta - frame['bed_translation'][:2]
    owner = single44.previous.owners(archive)['Key_Carrier']
    active = (data[:, 6] == owner) & audit42.common.model_mask(np.asarray(features)[data[:, 5].astype(int)])
    active &= ((xy >= low[:2] - 1.) & (xy <= high[:2] + 1.)).all(axis=1)
    sequence = None
    if sequences:
        from native_order45 import map_moves
        sequence = map_moves(checker.q, text, len(data), step=SAMPLE)[1][active]
    return checker, data[active], xy[active], sequence, np.flatnonzero(active)


def native_layers(archive, frame, bounds):
    checker, data, xy, _, _ = native_samples(archive, frame, bounds)
    for top in np.unique(data[:, 7]):
        at = np.isclose(data[:, 7], top, atol=.001)
        height = round(float(data[at, 4][0]), 3)
        assert height == .2 and np.allclose(data[at, 4], height)
        yield round(float(top), 3), height, checker.start_audit.bead_footprints(checker.q, xy[at], data[at, 3])


def measure(archive, evidence, design, *, current):
    from native48 import digest, read

    h, d = design.h, design.h.d
    directory = archive.parent
    frame_path = directory / 'frame.json'
    frame = read(frame_path)
    matrix = np.asarray(frame['print_to_assembly'])
    inverse = np.linalg.inv(matrix)[:3]
    carrier_path = directory / 'R45-Key-Carrier.stl'
    carrier = design.b.load(carrier_path)
    assert evidence['archive_sha256'] == digest(archive)
    branch_path = np.asarray(d.finger_rest_paths()['R']['middle branch'])
    radius = d.RIB_RADIUS
    # Both revisions use the same R44 shaft centres. The fitted board and
    # outlet cut different portions from this pre-union cylinder overlap.
    branch = d.h33.rounded_run(branch_path, radius=radius)
    row = d.h33.RIB_ROWS[2]
    leg = d.base.rib_at(row, 2, 1)
    target = (branch ^ leg ^ d._side_box(1, 8., 11.6, d.FINGER_REST_Y-1.4, d.FINGER_REST_Y+1.4)).transform(inverse) ^ carrier
    witness_volume = evidence['target_geometry'][JOINT]['source_volume_mm3']
    assert abs(target.volume() - witness_volume) < .001, 'Guard/branch overlap differs from the full source witness'

    root = 14.8 + .8 * 2
    end = np.array((11.05, root-.87*(root-row), 1.35))
    junction = branch_path[0]
    branch_axis, leg_axis = branch_path[1]-junction, end-junction
    normal = branch_axis / np.linalg.norm(branch_axis) - leg_axis / np.linalg.norm(leg_axis)
    # The two outgoing cylinders meet across this angular bisector. Sampling
    # along their shared centre tip would measure the disappearing old shaft.
    face = cutting_plane(junction, normal)
    box = h.box(2., 16.2, 5.7, 16.8, -.15, 6.45)
    members = branch + leg
    checks = [('branch shaft', junction+.50*branch_axis, branch_axis, branch, radius),
              ('finger rest past the junction', branch_path[1]+.30*(branch_path[2]-branch_path[1]),
               branch_path[2]-branch_path[1], branch, radius),
              ('third guard shaft', junction+.65*leg_axis, leg_axis, leg, radius)]
    if current:
        landing = h.rib_landing()
        members += landing
        nodes = np.asarray(h.LANDING_RUN)
        for index, fraction, name in ((2, .30, 'replacement landing'), (4, .35, 'landing at fixed deck')):
            start, finish = nodes[index:index+2]
            checks.append((name, start+fraction*(finish-start), finish-start, landing, h.LANDING_RADIUS))
    else:
        old_inside = np.array((8.95, root-.60*(root-row), 4.45))
        checks.append(('original inboard guard shaft', (junction+old_inside)/2,
                       old_inside-junction, leg, radius))

    cut = (members ^ box).transform(inverse) ^ carrier
    slabs, eroded_slabs, layers = [], [], []
    previous = mf.CrossSection()
    for top, height, film in native_layers(archive, frame, cut.bounding_box()):
        nominal = target.slice(top-height/2)
        if nominal.area() >= .1:
            actual = film ^ nominal
            touching = [p for p in film.decompose() if (p ^ nominal).area() > .001]
            layers.append({'top_mm': top, 'cad_mm2': nominal.area(), 'native_mm2': actual.area(),
                           'native_fraction': actual.area()/nominal.area(),
                           'prior_contact_inside_witness_mm2': (previous ^ actual).area(),
                           'touching_bead_islands_mm2': [p.area() for p in touching],
                           'each_islands_prior_contact_mm2': [(previous ^ p).area() for p in touching]})
        # Each slab extends one nanometre past its coincident layer boundary.
        for footprint, parts in ((film, slabs), (film.offset(-EROSION), eroded_slabs)):
            slab = footprint.extrude(height+.000002).translate((0., 0., top-height-.000001))
            parts.append(slab ^ cut)
        previous = film
    deposited = mf.Manifold.batch_boolean(slabs, mf.OpType.Add)
    robust = mf.Manifold.batch_boolean(eroded_slabs, mf.OpType.Add)
    # Intersect with the unsplit solid to preserve internal voids.
    backbone = max(robust.decompose(), key=lambda p: p.volume(), default=mf.Manifold()) ^ robust
    def face_section(solid, pose):
        return solid.transform(pose @ matrix).slice(0.)
    def reading(nominal, actual, core):
        area = nominal.area()
        patches = (nominal ^ actual).decompose()
        largest = max((p.area() for p in patches), default=0.)
        area_on_core = (nominal ^ actual ^ core).area()
        return {'cad_mm2': area, 'native_mm2': (nominal ^ actual).area(), 'native_largest_mm2': largest,
                'largest_fraction': largest/area if area else 0., 'common_eroded_core_mm2': area_on_core,
                'common_eroded_core_fraction': area_on_core/area if area else 0.}

    bend = reading(face_section(target, face), face_section(deposited, face), face_section(backbone, face))
    continuations = {}
    for name, point, normal, member, r in checks:
        pose = cutting_plane(point, normal)
        nominal = face_section(member.transform(inverse) ^ carrier, pose) ^ mf.CrossSection.circle(r, 96)
        continuations[name] = reading(nominal, face_section(deposited, pose), face_section(backbone, pose))
    return {'archive_sha256': digest(archive), 'layout_frame_sha256': digest(frame_path),
            'print_carrier_sha256': digest(carrier_path), 'inherited_stated_coverage': evidence['critical_material'][JOINT],
            'intended_witness_mm3': witness_volume, 'exact_reconstructed_witness_mm3': target.volume(),
            'native_overlap_mm3': (deposited ^ target).volume(), 'joint_layers': layers,
            'bisecting_face': bend, 'guard_shaft_full_area_mm2': math.pi*radius**2,
            'common_eroded_stock_mm3': backbone.volume(), 'source_shaft_planes': continuations}


def check_seams(archive):
    """Track native centre lines and stock through both former modifier faces."""
    import build48 as design
    from native48 import digest, read, write

    archive = Path(archive)
    out = archive.parent
    frame = read(out/'frame.json')
    matrix = np.asarray(frame['print_to_assembly'])
    inverse = np.linalg.inv(matrix)[:3]
    d = design.h.d
    points = d.finger_rest_paths()['R']['middle branch']
    shaft = d.h33.rounded_run(points, radius=d.RIB_RADIUS)
    # Assembly X planes in the old native metadata for "Solid right guard-leg
    # landing" and "Solid right middle-to-edge brace" respectively.
    seams = (11.80, 13.82)
    box = design.h.box(11.15, 14.6, 8.75, 11.15, -.1, 3.8)
    carrier_path = out/'R45-Key-Carrier.stl'
    carrier = design.b.load(carrier_path)
    shaft = (shaft ^ box).transform(inverse) ^ carrier
    checker, data, xy, sequences, source_ids = native_samples(archive, frame, shaft.bounding_box(), sequences=True)
    crossings = {x: [] for x in seams}
    core_slabs = []
    for top in np.unique(data[:,7]):
        at = np.flatnonzero(abs(data[:,7]-top) < .001)
        height = round(float(data[at[0],4]), 3)
        top = round(float(top), 3)
        mid = top-height/2
        section = shaft.slice(mid)
        if section.is_empty():
            continue
        film = checker.start_audit.bead_footprints(checker.q, xy[at], data[at,3])
        core = film.offset(-EROSION).extrude(height+.000002).translate((0.,0.,top-height-.000001))
        core_slabs.append(core ^ shaft)
        inside = at[checker.q._inside(section, xy[at])]
        if not len(inside):
            continue
        world_x = (np.c_[xy[inside], np.full(len(inside), mid), np.ones(len(inside))] @ matrix.T)[:,0]
        # Splitting on lost samples prevents crediting two separate excursions
        # from the same long perimeter as a crossing of the shaft.
        breaks = np.r_[0, 1+np.flatnonzero((np.diff(source_ids[inside]) != 1) |
                                          (np.diff(sequences[inside]) != 0)), len(inside)]
        for x in seams:
            runs = [int(sequences[inside[a]]) for a,b in zip(breaks[:-1],breaks[1:])
                    if world_x[a:b].min() <= x-.20 and world_x[a:b].max() >= x+.20]
            if runs:
                crossings[x].append({'top_mm': top, 'uninterrupted_sequences': len(set(runs))})
    core = mf.Manifold.batch_boolean(core_slabs, mf.OpType.Add)
    connected = max(core.decompose(), key=lambda p: p.volume(), default=mf.Manifold()) ^ core
    sections = {}
    # Opposite side of each former interface on the same eroded body.
    for x in (seams[0]-.35, seams[0]+.35, seams[1]-.35, seams[1]+.35):
        pose = cutting_plane(np.array((x,0.,0.)), np.array((1.,0.,0.))) @ matrix
        original = shaft.transform(pose).slice(0.)
        same_core = connected.transform(pose).slice(0.) ^ original
        sections[str(round(x,3))] = {'cad_mm2': original.area(), 'connected_eroded_mm2': same_core.area(),
                                    'fraction': same_core.area()/original.area() if original.area() else 0.}
    result = {'archive_sha256': digest(archive), 'checker_sha256': digest(Path(__file__)),
              'frame_sha256': digest(out/'frame.json'), 'carrier_sha256': digest(carrier_path),
              'sample_pitch_mm': SAMPLE, 'required_centreline_reach_each_side_mm': .2,
              'footprint_erosion_mm': EROSION, 'crossing_layers_at_assembly_x': {str(x):v for x,v in crossings.items()},
              'one_eroded_body_at_assembly_x': sections,
              'passed': all(len(levels) >= 2 for levels in crossings.values())
                        and all(row['fraction'] >= .50 for row in sections.values())}
    write(out/'guard-seams.json', result)
    return result


def inspect(archive, scratch):
    import build48 as design
    import audit42, audit45, single44, native_order45
    from native48 import digest, read, write

    archive, scratch = Path(archive), Path(scratch)
    out = archive.parent
    raw_path = out / 'carrier-before-joint-review.json'
    original = design.PREVIOUS / 'exports/complete-plate'
    old_raw = original / 'candidate-audit.json'
    control = measure(original / 'R47-Complete-A1-mini-PETG.gcode.3mf', read(old_raw), design, current=False)
    measured = measure(archive, read(raw_path), design, current=True)
    seams = check_seams(archive)
    bend = measured['bisecting_face']
    continuations = measured['source_shaft_planes']
    gates = {
        'continuous_shaft_through_both_former_process_boundaries': seams['passed'],
        'published_R47_control_at_least_one_full_guard_shaft': control['bisecting_face']['native_largest_mm2']
            >= control['guard_shaft_full_area_mm2'],
        'retained_join_has_one_full_guard_shaft_of_connected_plastic': bend['native_largest_mm2']
            >= measured['guard_shaft_full_area_mm2'] and bend['largest_fraction'] >= .90,
        'same_eroded_body_crosses_join_and_both_shafts_into_fixed_landing':
            bend['common_eroded_core_fraction'] >= .50
            and all(v['largest_fraction'] >= .90 and v['common_eroded_core_fraction'] >= .50
                    for v in continuations.values()),
        'every_local_printed_island_is_bonded_to_previous_layer':
            bool(measured['joint_layers']) and all(v['touching_bead_islands_mm2'] and
                min(v['each_islands_prior_contact_mm2']) > .1 for v in measured['joint_layers']),
    }
    engine = audit45.common.load_checker().audit
    sources = [Path(__file__), Path(design.__file__), Path(design.h.__file__), Path(design.h.d.__file__),
               Path(design.h.d.base.__file__), Path(design.h.d.h33.__file__), Path(audit42.common.__file__),
               Path(engine.q.__file__), Path(engine.start_audit.__file__), Path(single44.previous.__file__),
               Path(native_order45.__file__)]
    report = {'archive_sha256': digest(archive), 'checker_sha256': digest(Path(__file__)),
              'geometry_receipt_sha256': digest(scratch/'stage/r47-checks.json'),
              'native_seam_check_sha256': digest(out/'guard-seams.json'),
              'selected_raw_audit_sha256': digest(raw_path), 'R47_raw_audit_sha256': digest(old_raw),
              'source_sha256': {v.relative_to(design.HERE.parent).as_posix(): digest(v) for v in sources},
              'sample_pitch_mm': SAMPLE, 'eroded_bead_edge_mm': EROSION, 'current_joint': measured,
              'R47_control': control, 'gates': gates, 'passed': all(gates.values()), 'physical_strength_verified': False}
    write(out / 'guard-bond.json', report)
    return report
