"""Follow the R48 rod-clip shoulder into the original clip in native PETG paths."""
from pathlib import Path

import numpy as np
import manifold3d as mf

import build48 as design
import audit42
import audit45
import single44
from native48 import digest, read, write


def path_near_section(row, section):
    """Credit a full bead corridor, including moves crossing both boundaries."""
    radius = row['median_bead_width_mm'] / 2
    circle = mf.CrossSection.circle(radius, 32)
    points = row['sampled_path_xy']
    for start, end in zip(points, points[1:]):
        segment = mf.CrossSection.batch_hull([circle.translate(start), circle.translate(end)])
        if (segment ^ section).area() > 1.e-7:
            return True
    return False


def stroke_corridor(row):
    """Conservative envelope between samples, including the full bead width."""
    radius = row['median_bead_width_mm'] / 2 + .075
    circle = mf.CrossSection.circle(radius, 32)
    points = row['sampled_path_xy']
    return mf.CrossSection.batch_boolean([
        mf.CrossSection.batch_hull([circle.translate(a), circle.translate(b)])
        for a, b in zip(points, points[1:])], mf.OpType.Add)


def reference_turn():
    """The short, two-ended PETG bearing turn on the successfully printed R47."""
    path = design.PREVIOUS / 'exports/complete-plate/roof-strokes.json'
    record = read(path)
    archive = path.with_name('R47-Complete-A1-mini-PETG.gcode.3mf')
    assert record['archive_sha256'] == digest(archive)
    [control] = [r for r in record['sequence_gaps'] if r['z'] == 22.0 and
                 np.allclose(r['start_xy'], [39.671, 7.906], atol=.002)]
    assert control['before'] and control['after'] and control['features'] == ['Overhang wall']
    return control, record['archive_sha256']


def turn_envelope(row, control, mid, forward):
    """Bound a comparable bowed return and conservatively sweep possible sag."""
    width = row['median_bead_width_mm']
    comparison = {
        'two_anchored_ends': row['before'] and row['after'],
        'same_overhang_feature': row['features'] == control['features'],
        'full_width': row['minimum_bead_width_mm'] >= control['minimum_bead_width_mm'],
        'span_within_one_nozzle_of_control': row['anchored_span_mm'] <= control['anchored_span_mm'] + .4,
        'length_within_one_bead_of_control': row['mm'] <= control['mm'] + width,
        'lateral_bow_within_control': row['deviation_from_chord_mm'] <= control['deviation_from_chord_mm'],
        'feed_no_higher_than_control': max(row['commanded_feed_range_mm_s']) <= max(control['commanded_feed_range_mm_s']),
        'full_fan': min(row['last_commanded_part_fan_fraction_range']) == 1,
    }
    ink = stroke_corridor(row)
    drop = row['anchored_span_mm'] / 2 + width
    sag = ink.extrude(drop + .2).translate((0, 0, mid - .1 - drop)).transform(forward)
    keepouts = {'rod': design.h.base.rod(), **design.q.hardware()}
    clearances = {name: solid.min_gap(sag, 3.) for name, solid in keepouts.items()}
    return ink, {'comparison': comparison, 'sag_test_downwards_mm': drop,
                 'hardware_gaps_from_sag_envelope_mm': clearances,
                 'passed': all(comparison.values()) and min(clearances.values()) > .05}


def check_feed(archive, inverse, xyz, data, labels, owner_ids, pitch, *, cradle_release_report=None):
    """Enclose every printed move in boxes, then bound the open wire radius.

    Print Y is assembly Z, so the wire cylinder runs parallel to print Y.
    Each sampled line/arc lies within half the sampling pitch of a sample.
    Enlarging the bead by that radius makes the acceptance conservative.
    """
    axis = inverse[:, 2]
    assert np.allclose(axis, [0., 1., 0.], atol=1.e-7)
    from cable48 import centres, outlet
    bounds = outlet(design.h).bounding_box()
    a, b = map(np.asarray, centres(design.h))
    samples = np.asarray([a,(a+b)/2.,b])
    endpoints = np.asarray([[inverse @ [*xy, end, 1.] for end in (bounds[2], bounds[5])] for xy in samples])
    y0, y1 = sorted(endpoints[0, :, 1])
    assert np.allclose(endpoints[:, :, 1], endpoints[0, :, 1])
    radius = data[:, 3] / 2 + pitch / 2 + .0001
    near_ends = (xyz[:, 1] >= y0 - radius) & (xyz[:, 1] <= y1 + radius)
    # Most extrusion is planar. Include the full bead height and half the
    # sampling pitch in Z as well, which also bounds a sloped move.
    upper = np.maximum(data[:, 7], xyz[:, 2] + pitch / 2)
    lower = np.minimum(data[:, 7], xyz[:, 2] - pitch / 2) - data[:, 4]
    # Exact continuous 2-D segment-to-rectangle distance in the X/Z
    # cross-section. Each rectangle conservatively bounds one actual bead
    # sample, including its width, full layer height and interpolation guard.
    # Intersections are zero. Disjoint closest pairs are either a segment
    # endpoint against a box face, or a box corner against the segment.
    min_x,max_x=xyz[:,0]-radius,xyz[:,0]+radius
    x0,_,z0=endpoints[0,0];x1,_,z1=endpoints[-1,0]
    vx,vz=x1-x0,z1-z0
    assert abs(vx)>.00001 and abs(vz)>.00001
    enter=np.maximum(0.,np.maximum(np.minimum((min_x-x0)/vx,(max_x-x0)/vx),
                                   np.minimum((lower-z0)/vz,(upper-z0)/vz)))
    leave=np.minimum(1.,np.minimum(np.maximum((min_x-x0)/vx,(max_x-x0)/vx),
                                   np.maximum((lower-z0)/vz,(upper-z0)/vz)))
    permanent = data[:, 6] == owner_ids['Key_Carrier']
    distances=np.full(len(data),np.inf);stations={}
    for i,(x,_,z) in enumerate(endpoints[:,0]):
        dx=np.maximum(0.,np.maximum(min_x-x,x-max_x))
        dz=np.maximum(0.,np.maximum(lower-z,z-upper))
        away=np.hypot(dx,dz)
        stations[str(i/2.)]=float(away[permanent & near_ends].min())
        if i!=1:np.minimum(distances,away,out=distances)
    for xx,zz in ((min_x,lower),(min_x,upper),(max_x,lower),(max_x,upper)):
        t=np.clip(((xx-x0)*vx+(zz-z0)*vz)/(vx*vx+vz*vz),0.,1.)
        np.minimum(distances,np.hypot((xx-x0)-t*vx,(zz-z0)-t*vz),out=distances)
    distances[enter<=leave]=0.
    cable = 1.5 * (1. + 2. / np.sqrt(3.))
    tolerance = .15
    target = cable / 2 + tolerance
    if cradle_release_report is None:
        core = read(archive.parent / 'candidate-audit.json')
        # This digital wire-path evidence depends only on this archive and its
        # verified helper removal. Sealing independently needs all carrier gates.
        assert core['archive_sha256'] == digest(archive)
        assert core['whole_rib_downward_release']['mechanical_release_geometry_clear']
        removable = {
            'External_cradle': core['whole_bead_release']['clear'],
            'Front_pull_shelf': core['whole_shelf_bead_release']['clear'] and core['individual_front_piece_release']['clear'],
            'Rear_pull_shelf': core['whole_rear_shelf_bead_release']['clear'],
        }
    else:
        # Later plates measure the full native cradle withdrawal directly.
        # Only that object can be discounted from this wire-path check.
        release = read(cradle_release_report)
        assert release['archive_sha256'] == digest(archive) and release['passed']
        cradle = release['removal']['cradle']
        assert cradle['clear'] and not cradle['collisions']
        removable = {'External_cradle': True}
    owners = {v: k for k, v in owner_ids.items()}
    rows, required = {}, []
    passed = True
    for n in np.unique(data[:, 6]):
        owner = owners.get(n, f'Unassigned owner {int(n)}')
        on = (data[:, 6] == n) & near_ends
        gap = float(distances[on].min()) if on.any() else None
        inc = on & (distances <= target)
        clutter = sorted(set(labels[inc].tolist()))
        if clutter and removable.get(owner):
            required.append(owner)
        elif clutter:
            passed = False
        rows[owner] = {'minimum_guaranteed_clear_radius_mm': gap,
                       'total_owner_samples': int((data[:, 6] == n).sum()),
                       'features_inside_guard': clutter}
    return {'archive_sha256': digest(archive), 'slot_end_centres_assembly_xy_mm': [a.tolist(), b.tolist()],
            'permanent_carrier_clear_radii_at_ends_and_middle_mm': stations,
            'continuous_slot_sampling_bound_mm': 0., 'continuous_distance_method':'Exact segment-to-rectangle distance against conservative bead envelopes',
            'assumed_wire_count': 3, 'wire_outside_diameter_mm': 1.5,
            'bundle_diameter_mm': float(cable), 'additional_radial_clearance_mm': tolerance,
            'guard_diameter_mm': float(target * 2), 'sampling_pitch_mm': pitch,
            'print_axis_first_and_last_station_mm': endpoints[[0,-1]].tolist(), 'all_native_owners': rows,
            'helpers_that_must_be_removed': required, 'physically_tested': False, 'passed': passed}


def check(archive, scratch, *, cradle_release_report=None):
    out = archive.parent
    frame = read(out / 'frame.json')
    inverse = np.linalg.inv(np.asarray(frame['print_to_assembly']))[:3]
    source = scratch / 'stage/R47-Key-Carrier-assembly.stl'
    checked = design.b.load(source)
    original, *_ = design.geometry_previous()
    shoulder = design.shoulder(design.h) ^ checked
    # Keep the seam witness independent of the slicer's mesh. This is
    # material belonging to both the new shoulder and the original body.
    joint = shoulder ^ original
    addition = shoulder - original
    assert joint.volume() > 1. and addition.volume() > 1., (joint.volume(), addition.volume())
    shapes = {k: shape.transform(inverse) for k, shape in
              [('shoulder', shoulder), ('joint', joint), ('added', addition)]}
    engine = audit45.common.load_checker().audit
    data, features, _, _, offset, *_ = engine.read_project(archive)
    labels = np.asarray(features)[data[:, 5].astype(int)]
    owners = single44.previous.owners(archive)
    normal = (data[:, 6] == owners['Key_Carrier']) & audit42.common.model_mask(labels)
    xyz = data[:, :3] + offset - frame['bed_translation']
    feed = check_feed(archive, inverse, xyz, data, labels, owners, engine.STEP,
                      cradle_release_report=cradle_release_report)
    write(out / 'wire-feed-path.json', feed)
    if not feed['passed']:
        raise ValueError('Native model or unqualified paths intrude on the wire bundle')
    roofs = read(out / 'roof-strokes.json')
    assert roofs['archive_sha256'] == digest(archive)
    control, control_hash = reference_turn()
    rows = []; layers=[]; core_slabs=[]
    worst_case_slabs = []
    for top in np.unique(data[normal, 7]):
        top = float(top)
        on = normal & (abs(data[:, 7] - top) < .001)
        height = float(np.median(data[on, 4]))
        mid = top - height / 2
        nominal = shapes['shoulder'].slice(mid)
        if nominal.area() < .001:
            continue
        actual = audit42.common.footprint(engine, data, xyz, on)
        previous = normal & (abs(data[:, 7] - (top - height)) < .001)
        below = audit42.common.footprint(engine, data, xyz, previous)
        clipped = actual ^ nominal
        rooted = [{'area_mm2': piece.area(), 'prior_overlap_mm2': (piece ^ below).area()}
                  for piece in clipped.decompose() if piece.area() >= .02]
        regions = {}
        for name, shape in shapes.items():
            target = shape.slice(mid)
            if target.area() >= .001:
                regions[name] = audit42.connected_section(target, actual)
        # If the original and new stock are both present, they must share a
        # bead island. Checking two regions separately could miss a split.
        edge = shapes['added'].slice(mid)
        bond = shapes['joint'].slice(mid)
        shared = None
        if edge.area() >= .04 and bond.area() >= .04:
            shared = any((part ^ edge).area() >= .9 * edge.area() and
                         (part ^ bond).area() >= .9 * bond.area() for part in actual.decompose())
        # Reconstruct the actual, eroded native load path through the full
        # height, including contiguous stock within 1 mm of this shoulder.
        # Only deposited material earns credit. Requiring a finite core
        # prevents adjacent perimeter lines touching at a sample from joining it.
        upper=round(top,3); height=round(height,3)
        load_window=nominal.offset(1.)
        inner=(actual^load_window).offset(-.075)
        assert height==.2 and abs(upper/.2-round(upper/.2))<1e-6
        # Integer layer coordinates share exact faces without growing them.
        layers.append((mid,nominal,clipped,{name:shape.slice(mid) for name,shape in shapes.items()}))
        specific = [g for g in roofs['sequence_gaps'] if abs(g['z'] - top) < .001 and
                    path_near_section(g, nominal)]
        risk = mf.CrossSection()
        turn_rows = []
        for g in specific:
            if g['classification'] == 'unsupported bend outside bead corridor':
                ink, evidence = turn_envelope(g, control, mid, np.asarray(frame['print_to_assembly'])[:3])
                risk = risk + ink
                turn_rows.append(evidence)
        layer_index = round(upper/.2) - 1
        if not inner.is_empty():
            core_slabs.append(inner.extrude(1.).translate((0.,0.,layer_index)))
            # Completely discard the bowed return and its immediate bead
            # corridor. All remaining area must still connect up the clip.
            conservative = ((actual ^ load_window) - risk).offset(-.075)
            if not conservative.is_empty():
                worst_case_slabs.append(conservative.extrude(1.).translate((0.,0.,layer_index)))
        valid_spans = all(g['before'] and g['after'] and
                          g['classification'] == 'short straight two-ended bridge' for g in specific)
        rows.append({'layer_top_mm': round(top, 3), 'regions': regions,
                     'added_and_old_stock_share_native_piece': shared,
                     'native_previous_layer_ancestry': rooted,
                     'two_ended_return_assessment': turn_rows,
                     'unsupported_intervals_on_this_shoulder': specific,
                     'passed': bool(all(r['passed'] for r in regions.values()) and
                                    shared is not False and rooted and
                                    all(r['prior_overlap_mm2'] >= .01 for r in rooted) and valid_spans)})
    full=mf.Manifold.batch_boolean(core_slabs,mf.OpType.Add).scale((1.,1.,.2))
    common=max(full.decompose(),key=lambda piece:piece.volume()) ^ full
    worst=mf.Manifold.batch_boolean(worst_case_slabs,mf.OpType.Add).scale((1.,1.,.2))
    residual=max(worst.decompose(),key=lambda piece:piece.volume()) ^ worst
    for row,(mid,nominal,clipped,targets) in zip(rows,layers,strict=True):
        core=common.slice(mid)
        lobes=[]
        for lobe in clipped.decompose():
            if lobe.area()<.02:continue
            overlap=(lobe^core).area()
            eroded=lobe.offset(-.075)
            available=eroded.area()
            lobes.append({'deposited_lobe_mm2':lobe.area(),'common_eroded_core_mm2':overlap,
                          'fraction':overlap/lobe.area(),'available_eroded_lobe_mm2':available,
                          'connected_fraction_of_available_core':(eroded^core).area()/available if available>1e-6 else 0.})
        sections={}
        for name,r in row['regions'].items():
            target=targets[name]
            if target.area()<.08:
                # Nominal taper tips barely wider than a sample still have
                # to meet the independent same-plane coverage/bond check.
                accepted=r['passed']
            else:
                raw=r['coverage_fraction']
                share=(target^core).area()/target.area()
                sections[name]=share
                accepted=raw>=.9 and share>=.50
            if not accepted:break
        else:accepted=True
        ready=all(v['available_eroded_lobe_mm2']>.012 and
                  v['connected_fraction_of_available_core']>=.90 for v in lobes)
        row['three_dimensional_load_path']={'probe_z_mm':mid,'common_eroded_core_volume_mm3':common.volume(),
            'same_component_fraction_by_region':sections,'individual_native_lobes':lobes,
            'passed':bool(accepted and lobes and ready)}
        row['same_plane_strict_gate']=row['passed']
        residual_slice=residual.slice(mid)
        post_loss={name:(target^residual_slice).area() for name,target in targets.items() if target.area()>=.08}
        # A short return may curl during a physical print. Even after losing
        # its entire corridor and one sample of margin, the fixed shoulder
        # must stay connected through the actual PETG in the layers on both
        # sides. Stock and addition are separate witnesses; small tapers
        # must still retain a real positive piece of the common core.
        residual_gate=all(area>=min(.08,.4*targets[name].area()) for name,area in post_loss.items())
        row['load_path_with_bowed_edges_removed']={'common_core_area_by_region_mm2':post_loss,
                                                    'passed':residual_gate}
        valid_types={'short straight two-ended bridge','unsupported bend outside bead corridor'}
        row['passed']=bool(row['three_dimensional_load_path']['passed'] and residual_gate and
                           all(r['prior_overlap_mm2']>=.01 for r in row['native_previous_layer_ancestry']) and
                           all(g['before'] and g['after'] and g['classification'] in valid_types
                               for g in row['unsupported_intervals_on_this_shoulder']) and
                           all(x['passed'] for x in row['two_ended_return_assessment']))
    passed = bool(rows and any(row['added_and_old_stock_share_native_piece'] for row in rows) and
                  all(row['passed'] for row in rows))
    report = {'archive_sha256': digest(archive), 'source_mesh_sha256': digest(source),
              'checker_sha256': digest(Path(__file__)), 'source_shape_sha256': digest(design.HERE / 'shoulder48.py'),
              'eroded_common_component_mm3':common.volume(),'native_lobe_erosion_mm':.075,
              'common_component_after_discarding_curved_edges_mm3':residual.volume(),
              'printed_comparison_archive_sha256':control_hash,'printed_comparison_turn':control,
              'prior_clip_overlap_mm3': joint.volume(), 'additional_stock_mm3': addition.volume(),
              'layers': rows, 'passed': passed, 'physical_strength_verified': False}
    write(out / 'rod-clip-shoulder.json', report)
    if not passed:
        raise ValueError(f'Native clip shoulder requires review at {[r["layer_top_mm"] for r in rows if not r["passed"]]}')
