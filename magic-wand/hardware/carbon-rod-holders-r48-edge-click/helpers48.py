"""Independently peel the finger-rest and switch-aperture supports.

The fingertip rests only had two guide pieces in R47, and one comb pulled
several deep recess contacts at once. Slits divide measured contact patches
and the external grips. The release directions stay aligned with each recess.
"""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import manifold3d as mf
import numpy as np
import trimesh

import comb_pieces45
import standing_aperture45
import standing_comb45
from native48 import digest
from shelf45 import band, box, span

FRONT = (
    ('Left finger-rest comb', 'R48-front-left-comb.stl'),
    ('Middle finger-rest comb', 'R48-front-middle-comb.stl'),
    ('Right finger-rest comb', 'R48-front-right-comb.stl'),
)
WEB = ('Left guard web prop', 'R45-left-guard-web-prop.stl')
REAR = (
    ('Outer switch-aperture tine', 'R48-rear-outer-tine.stl'),
    ('Inner switch-aperture tines', 'R48-rear-aperture-tines.stl'),
)
FRONT_SLOTS = ((11.12, .9), (33.00, .95))
REAR_SLOTS = ((9.20, .9),)
FRONT_SIDE_GAP = .49
REAR_SIDE_GAP = .49


def separated(shape, cuts):
    bounds = shape.bounding_box()
    for centre, width in cuts:
        slot = mf.Manifold.cube((width, bounds[4] - bounds[1] + 2., bounds[5] - bounds[2] + 2.)).translate(
            (centre - width / 2, bounds[1] - 1., bounds[2] - 1.))
        shape -= slot
    parts = sorted(shape.decompose(), key=lambda piece: piece.bounding_box()[0])
    assert len(parts) == len(cuts) + 1, [(s.volume(), s.bounding_box()) for s in parts]
    for piece in parts:
        assert piece.status() == mf.Error.NoError and piece.volume() > 1.
        assert not piece.slice(.1).offset(-.6).is_empty(), ('Each removable strip needs a usable bed foot', piece.bounding_box())
    return parts


def release_clear(moving, fixed, delta):
    """The entire swept solid must clear the other part at every slab."""
    a, b = moving.bounding_box(), fixed.bounding_box()
    if a[3] < b[0] - .001 or b[3] < a[0] - .001:
        return True
    heights = np.unique(np.round(np.asarray(moving.to_mesh().vert_properties)[:, 2], 5))
    for lo, hi in zip(heights, heights[1:]):
        if hi - lo >= .00005:
            swept = span(moving.slice(float((lo + hi)/2)), 0., delta)
            if (swept ^ band(fixed, float(lo)-.00001, float(hi)+.00001)).area() > .0001:
                return False
    return True


def record(out, pieces, direction):
    remaining = list(pieces)
    records = []
    while remaining:
        for i, ((name, filename), piece) in enumerate(remaining):
            others = remaining[:i] + remaining[i+1:]
            if all(release_clear(piece, other, direction * 72.) for _, other in others):
                break
        else:
            raise ValueError('Remaining support pieces interlock')
        mesh = piece.to_mesh()
        trimesh.Trimesh(mesh.vert_properties[:,:3], mesh.tri_verts, process=False).export(out / filename)
        records.append({
            'name': name, 'file': filename, 'sha256': digest(out / filename),
            'direction_print': [0, direction, 0], 'translation_mm': 72.,
            'bounds': piece.bounding_box(), 'volume_mm3': piece.volume(),
            'bed_face_area_mm2': piece.slice(.1).area(), 'has_1p2mm_grip_land': True,
            'removal_order': len(records)+1, 'other_pieces_remaining': [r[0][0] for r in others],
            'whole_cad_conflicts_with_remaining_pieces': [],
        })
        remaining.pop(i)
    return records


@contextmanager
def arrangement(out):
    import plate45
    import tab_cleanup48
    from native48 import read
    old_cradle=plate45.underside_cradle
    def make_cradle(body,frame):
        import cradle_turn48
        from native48 import write
        cradle,tabs=old_cradle(body,frame)
        cradle,roof_support=cradle_turn48.shape(cradle,body)
        write(out / "cradle-turn-cad.json",roof_support)
        target=read(out.parent / "stage/r47-checks.json")["backup_angle_deg"]
        return cradle,tab_cleanup48.trim_bed_tabs(tabs,body,frame,target,out)

    front = standing_comb45.make
    flare = comb_pieces45.flare
    rear = standing_aperture45.make
    prepared = {}

    def make_front(*args):
        return front(*args, lateral_clearance=FRONT_SIDE_GAP)

    def grip_tab(piece, cx, cy, clearance):
        # A four-layer paddle lets both tweezer jaws engage from outside.
        # Only the rooted ankle touches the support, never the finished part.
        outline = mf.CrossSection.square((3.,3.6),True).offset(.50,mf.JoinType.Round).translate((cx,cy))
        pad = (outline-clearance).extrude(.80)
        assert (pad ^ piece).volume() > .6, (cx,cy,'Pinch grip lost its root')
        result = piece + pad
        assert result.status()==mf.Error.NoError and len(result.decompose())==1
        return result

    def flare_and_split(shape,body,tabs,cradle):
        shelf, tabs, details = flare(shape,body,tabs,cradle)
        comb, web = sorted(shelf.decompose(), key=lambda p: -p.volume())
        fingers = separated(comb, FRONT_SLOTS)
        clearance = span(band(body+tabs,-.001,.801).offset(.49),0,72.) + cradle.project().offset(.68)
        fingers = [grip_tab(piece,cx,-5.65,clearance) for cx,piece in zip((4.,22.,40.),fingers,strict=True)]
        prepared['front'] = list(zip(FRONT, fingers, strict=True)) + [(WEB, web)]
        return mf.Manifold.batch_boolean([*fingers, web], mf.OpType.Add), tabs, details

    def front_records(directory, shelf, report):
        report.update(removable_pieces=record(directory, prepared['front'], -1),
                      piece_checker_sha256=digest(Path(comb_pieces45.__file__)),
                      r48_splitter_sha256=digest(Path(__file__)), peel_slots_print_x_mm=FRONT_SLOTS)
        assert abs(shelf.volume()-sum(s.volume() for _,s in prepared['front'])) < .001

    def make_rear(body, tabs, cradle, front_shelf):
        prop, info = rear(body, tabs, cradle, front_shelf, lateral_clearance=REAR_SIDE_GAP)
        tines = separated(prop, REAR_SLOTS)
        # Give the freed, 18.2 mm-high outer tine an ankle and pinch tab
        # on the exterior. It adds only two first layers, away from the
        # recess. Keep both early peel directions clear.
        pad = mf.CrossSection.square((3.35, 4.25)).translate((5.4, 21.25))
        keepout = span(band(body + tabs, -.001, .401).offset(.49), 0., -72.)
        keepout += cradle.project().offset(.68)
        keepout += span(band(front_shelf, -.001, .401).offset(.68), 0., -72.)
        pad -= keepout
        before = tines[0].slice(.1).area()
        tines[0] += pad.extrude(.4)
        assert len(tines[0].decompose()) == 1 and tines[0].slice(.1).area() >= 14.
        info['outer_tine_foot'] = {'before_mm2':before, 'after_mm2':tines[0].slice(.1).area(),
                                   'bed_layers':2}
        keepout = span(band(body+tabs,-.001,.801).offset(.49),0,-72.) + cradle.project().offset(.68)
        keepout += span(band(front_shelf,-.001,.801).offset(.68),0,-72.)
        tines[1] = grip_tab(tines[1],14.25,24.20,keepout)
        combined = mf.Manifold.batch_boolean(tines, mf.OpType.Add)
        info.update(removable_pieces=record(out, list(zip(REAR, tines, strict=True)), 1),
                    piece_checker_sha256=digest(Path(comb_pieces45.__file__)),
                    r48_splitter_sha256=digest(Path(__file__)), peel_slots_print_x_mm=REAR_SLOTS,
                    volume_mm3=combined.volume())
        return combined, info

    with patch.object(plate45,'underside_cradle',make_cradle), \
         patch.object(standing_comb45, 'make', make_front), \
         patch.object(comb_pieces45, 'flare', flare_and_split), \
         patch.object(comb_pieces45, 'record', front_records), \
         patch.object(standing_aperture45, 'make', make_rear):
        yield


def assess_removal(archive, scratch):
    """Bind the new recess coupling and individual rear withdrawal to G-code."""
    import audit42
    import audit45
    import lateral45
    import single44
    from native48 import read, write
    out = archive.parent
    core = read(out / 'candidate-audit.json')
    assert core['archive_sha256'] == digest(archive) and core['individual_front_piece_release']['clear']
    frame = read(out / 'frame.json')
    engine = audit45.common.load_checker().audit
    data, features, _, _, offset, *_ = engine.read_project(archive)
    xyz = data[:, :3] + offset - frame['bed_translation']
    names = np.asarray(features)[data[:, 5].astype(int)]
    normal = audit42.common.model_mask(names)
    owners = single44.previous.owners(archive)
    rear = normal & (data[:, 6] == owners['Rear_pull_shelf'])
    fixed = normal & np.isin(data[:, 6], [owners['Key_Carrier'], owners['Release_tabs']])
    # The verified full rear owner already withdraws in +Y. Check each lane
    # independently against all stationary material and the yet-unpulled lane.
    records = read(out / 'rear-shelf-cad.json')['removable_pieces']
    assert len(records) == 2 and records[0]['direction_print'] == records[1]['direction_print'] == [0,1,0]
    groups = [rear & (xyz[:, 0] < REAR_SLOTS[0][0]), rear & (xyz[:, 0] >= REAR_SLOTS[0][0])]
    actual = []
    for i, (row, group) in enumerate(zip(records, groups, strict=True)):
        assert digest(out / row['file']) == row['sha256']
        assert row['file'] == REAR[i][1], 'Native rear order/assignment changed'
        lo, hi = row['bounds'][0] - .02, row['bounds'][3] + .02
        assert (xyz[group, 0] >= lo).all() and (xyz[group, 0] <= hi).all()
        others = fixed | (groups[1] if i == 0 else np.zeros_like(group))
        release = lateral45.inspect(engine, data, xyz, others, group, '+y')
        base = audit42.common.footprint(engine, data, xyz, group & (abs(data[:, 7] - .2) < .001))
        actual.append({'piece':row['name'], 'samples':int(group.sum()), 'bed_face_mm2':base.area(),
                       'receives_1p2mm_foot':not base.offset(-.6).is_empty(), 'withdrawal':release})

    baseline = read(scratch / 'contact-regression/r47/result.json')
    # The baseline is bound to the physically tried R47 archive and to the
    # corrected checker so the old, erroneous zero-contact report cannot pass.
    import contact45
    assert baseline['checker_sha256'] == digest(Path(contact45.__file__))
    bounds = {}
    for owner, reportname in [('Front_pull_shelf','shelf-contact-areas.json'),('Rear_pull_shelf','rear-shelf-contact-areas.json')]:
        previous = baseline['all_peel_pieces'][owner]
        rows = read(out / reportname)['peel_pieces']
        peak = max(r['projected_contact_area_sum_mm2'] for r in rows)
        patch = max(r['largest_continuous_contact_patch_mm2'] for r in rows)
        old_peak = max(r['projected_contact_area_sum_mm2'] for r in previous)
        old_patch = max(r['largest_continuous_contact_patch_mm2'] for r in previous)
        bounds[owner] = {'peak_contact_on_one_pull_mm2':peak, 'r47_peak_mm2':old_peak,
                         'peak_change_fraction':(peak-old_peak)/old_peak,
                         'largest_patch_mm2':patch, 'r47_largest_patch_mm2':old_patch,
                         'individual_contacts_mm2':{r['removable_piece']:r['projected_contact_area_sum_mm2'] for r in rows},
                         'passed':bool(peak < old_peak*.85 and patch < old_patch*.9 and
                                       all(r['projected_contact_area_sum_mm2'] > .03 for r in rows))}
    front = core['individual_front_piece_release']['pieces']
    from grip48 import grips, actual_access
    access = actual_access(grips(out), out, engine, data, xyz, normal, owners)
    passed = (all(r['grip'] and r['grip']['native_passed'] for r in access) and all(r['actual_bead_withdrawal']['clear'] and r['actual_1p2mm_land'] for r in front)
              and all(r['withdrawal']['clear'] and r['receives_1p2mm_foot'] for r in actual)
              and all(row['passed'] for row in bounds.values()))
    result={'archive_sha256':digest(archive), 'r47_archive_sha256':baseline['archive_sha256'],
            'external_tweezer_access':access, 'independent_front_pieces':len(front), 'independent_rear_pieces':actual,
            'contact_comparison':bounds, 'passed':passed, 'physical_removal_verified':False}
    write(out/'recess-support-removal.json',result)
    if not passed:
        raise ValueError(f'Recess support did not improve enough or its extraction is obstructed: {bounds}')
