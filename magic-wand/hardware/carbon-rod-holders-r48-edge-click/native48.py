"""Prepare and audit the R48 nine-part plate with the established native slicer.

Run each action under the project's CAD lease. Native slicing and reopening
each need their own isolated AGENT_SCRATCH_DIR (slice45). No printer commands.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
R47 = HERE.parent / 'carbon-rod-holders-r47-bottom-click'
LAYOUT = 'R48-Complete-A1-mini-PETG-layout.3mf'
INITIAL = 'R48-first-complete.gcode.3mf'
SELECTED = 'R48-Complete-A1-mini-PETG.gcode.3mf'
SEALED = 'R48-All-Components-print-only.3mf'
TITLE = 'Magic Wand R48 complete assembly - A1 mini PETG'
RED_PETG_SWATCH = '#A72D32'  # Illustrative swatch for the loaded metallic red PETG.
REPORTS = (
    'candidate-audit.json', 'helper-starts.json', 'roof-strokes.json',
    'roof-residual-context.json', 'contact-areas.json', 'shelf-contact-areas.json',
    'rear-shelf-contact-areas.json', 'empty-space-checks.json', 'delivery-checks.json',
    'swing-tab-removal.json', 'front-shelf-warning.json', 'front-roof-strokes.json', 'strength-paths.json', 'guard-bond.json', 'guard-seams.json', 'rod-clip-shoulder.json', 'wire-feed-path.json', 'recess-support-removal.json', 'other-audit/other-parts-audit.json', 'other-audit/edge-click-load-path.json',
)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def stage_checks(scratch):
    receipt = read(scratch / 'stage/r47-checks.json')
    assert receipt['r47']['passed'] and receipt['r48']['passed'], 'R48 source checks must pass'
    source = receipt['r48']['source_sha256']
    geometry = {'R47-DFRobot_Hole_Bracket-cap.stl', 'R47-Key-Carrier-assembly.stl',
                'R48-DFRobot_Hole_Bracket-seated.stl'}
    assert {'build48.py', 'mechanics48.py'} | geometry <= source.keys()
    for name, sha in source.items():
        owner = scratch / 'stage' if name in geometry else HERE
        assert digest(owner / name) == sha, f'{name} changed after checking geometry'
    return receipt


def set_filament_swatch(layout):
    config_name = 'Metadata/project_settings.config'
    with ZipFile(layout) as z:
        files = {name: z.read(name) for name in z.namelist()}
    previous = json.loads(files[config_name])
    assert previous['filament_type'] == ['PETG'] and len(previous['filament_colour']) == 1
    fields = ('filament_colour', 'extruder_colour')
    current = {**previous, **{key: [RED_PETG_SWATCH] for key in fields}}
    assert {k for k in current if current[k] != previous[k]} <= set(fields)
    files[config_name] = json.dumps(current, indent=2).encode()
    temporary = layout.with_suffix('.new.3mf')
    with ZipFile(temporary, 'w', ZIP_DEFLATED) as z:
        for key, value in files.items():
            z.writestr(key, value)
    temporary.replace(layout)
    composition_path = layout.with_suffix('.composition.json')
    composition = read(composition_path)
    composition.update(layout_sha256=digest(layout), colour_change={
        'fields': list(fields), 'swatch': RED_PETG_SWATCH,
        'reason': 'Illustrative red swatch for the external Flashforge HS PETG Metallic spool.',
        'print_process_settings_changed': False,
    })
    write(composition_path, composition)


def layout(scratch, out, *, reuse_prepared_key=False):
    import plate47
    import bracket47
    import compose47
    import battery_print48

    key = scratch / 'final-key-layout'
    import helpers48
    if reuse_prepared_key:
        frame = read(key / 'frame.json')
        assert frame['layout_sha256'] == digest(key / 'R45-Key-Carrier-layout.3mf')
        assert frame['checks_sha256'] == digest(scratch / 'stage/r47-checks.json')
        assert frame['carrier_assembly_sha256'] == digest(scratch / 'stage/R47-Key-Carrier-assembly.stl')
        for filename in ('shelf-cad.json','rear-shelf-cad.json'):
            metadata = read(key / filename)
            assert metadata['r48_splitter_sha256'] == digest(Path(helpers48.__file__))
            for row in metadata['removable_pieces']:
                assert row['sha256'] == digest(key / row['file'])
    else:
        with helpers48.arrangement(key):
            plate47.prepare(key, scratch)
    stage = scratch / 'stage'
    checks = stage / 'r47-checks.json'
    cap = stage / 'R47-DFRobot_Hole_Bracket-cap.stl'
    r42 = HERE.parent / 'carbon-rod-holders-r42-lower-diagonal/exports'
    template = r42 / 'print-trial/R42-Complete-A1-mini-PETG-layout.3mf'
    bracket = out / 'R48-Bracket-and-Clips-layout.3mf'
    target = out / LAYOUT
    set_fields = compose47.set_fields

    def set_current_title(node, fields):
        if fields.get('plater_name'):
            fields = {**fields, 'plater_name': fields['plater_name'].replace('R47', 'R48')}
        set_fields(node, fields)

    # Emit the correct plate title in the editable project before hashing it.
    with patch.object(compose47, 'set_fields', set_current_title):
        bracket47.prepare(template, cap, checks, bracket)
        battery = battery_print48.prepare(r42 / 'print-jobs/battery/R42-battery-A1-mini-PETG-layout.3mf',
                                           scratch, out / 'R48-Micron-battery-layout.3mf')
        compose47.compose(template, key / 'R45-Key-Carrier-layout.3mf', bracket, target, battery)
    battery_print48.strengthen_small_parts(target)
    import shelf_warning48
    import guard_process48
    shelf_warning48.configure_layout(target)
    guard_process48.configure(target, out / 'guard-process.json', read(key / 'frame.json'))
    set_filament_swatch(target)
    with ZipFile(target) as z:
        config = ET.fromstring(z.read('Metadata/model_settings.config'))
        assert config.find("plate/metadata[@key='plater_name']").get('value') == TITLE
    for file in key.iterdir():
        if file.suffix in ('.stl', '.json') or file.name == 'R45-Key-Carrier-layout.3mf':
            shutil.copyfile(file, out / file.name)
    frame = read(out / 'frame.json')
    frame.update(battery_manifest_sha256=digest(scratch / 'battery48/manifest.json'), key_subproject_bed_translation=frame['bed_translation'],
                 bed_translation=[18., 113., 0.], combined_layout_sha256=digest(target),
                 geometry_receipt_sha256=digest(checks), bracket_assembly_sha256=digest(cap),
                 scope='R48 complete plate. R45-prefixed files are local inputs to the standing-support checker.')
    write(out / 'frame.json', frame)


def check_plate_inputs(scratch, out):
    frame = read(out / 'frame.json')
    stage = scratch / 'stage'
    assert frame['battery_manifest_sha256'] == digest(scratch / 'battery48/manifest.json')
    assert frame['geometry_receipt_sha256'] == digest(stage / 'r47-checks.json')
    assert frame['bracket_assembly_sha256'] == digest(stage / 'R47-DFRobot_Hole_Bracket-cap.stl')
    assert frame['carrier_assembly_sha256'] == digest(stage / 'R47-Key-Carrier-assembly.stl')
    assert frame['combined_layout_sha256'] == digest(out / LAYOUT)
    assert read((out / LAYOUT).with_suffix('.composition.json'))['layout_sha256'] == digest(out / LAYOUT)


def audit(scratch, out, action):
    import bracket_paths48
    import delivery47
    import reopen47
    import roof_context46
    import scope47
    import screen47
    import slice45
    import spaces47

    archive = out / SELECTED
    check_plate_inputs(scratch, out)
    if action == 'slice':
        slice45.run(out / LAYOUT, out / INITIAL)
        receipt = read((out / INITIAL).with_suffix('.native.json'))
        write(out / 'initial-input.json', {'editable_layout_sha256': digest(out / LAYOUT),
                                           'initial_archive_sha256': receipt['archive_sha256']})
        return
    source = read(out / 'initial-input.json')
    assert source['initial_archive_sha256'] == digest(out / INITIAL)
    assert source['editable_layout_sha256'] == digest(out / LAYOUT)
    if action == 'reopen':
        reopen47.run(out / INITIAL, archive)
        import roof_strokes45
        import scope47
        with scope47.key_group(archive):
            roof_strokes45.inspect(archive, focus_layers={22.,27.6}, report_path=out / 'two-roof-diagnostic.json')
            roof_strokes45.inspect(archive, owner_name='Front_pull_shelf',
                                   support_owners=('Key_Carrier','External_cradle'),
                                   focus_layers={.4,15.8,16.2}, report_path=out / 'front-three-layer-diagnostic.json')
        return
    reopened = read(out / 'reopen-checks.json')
    assert reopened['initial_archive_sha256'] == source['initial_archive_sha256']
    assert reopened['selected_archive_sha256'] == digest(archive)
    if action == 'carrier':
        import audit47, review47, carrier_screen48
        import tab_cleanup48
        with tab_cleanup48.classify(archive), scope47.key_group(archive):
            audit47.check(archive,scratch)
            review47.review(archive)
        carrier_screen48.snapshot(archive,scratch)
        carrier_screen48.qualify(archive,scratch)
        label_current_reports(out)
    elif action == 'carrier-joint':
        import carrier_screen48
        carrier_screen48.qualify(archive,scratch)
        label_current_reports(out)
    elif action == 'others':
        bracket_paths48.check(archive, scratch, out / 'other-audit')
    elif action in ('finish', 'delivery'):
        import shoulder_paths48
        import helpers48
        import strength48
        import shelf_warning48
        if action == 'finish':
            helpers48.assess_removal(archive, scratch)
            shelf_warning48.compare(archive, scratch)
            strength48.check_native(archive, scratch)
            shoulder_paths48.check(archive, scratch)
            spaces47.inspect(archive, scratch)
            with scope47.key_group(archive):
                roof_context46.inspect(archive)
        # Separate heavy checks may also run in individual guarded jobs. The
        # delivery-only action accepts their files only for this native archive.
        archive_hash = digest(archive)
        for name in REPORTS:
            if name != 'delivery-checks.json':
                assert read(out / name)['archive_sha256'] == archive_hash, name
        delivery47.inspect(archive)
        compare_roofs(out)


def label_current_reports(out):
    # Archived R47 routines called their active result 'r47'. Preserve the
    # R46 controls and identify the current measurements in the public report.
    active = {
        'r47': 'r48', 'r47_landing_sections': 'r48_landing_sections',
        'r47_geometry_receipt_sha256': 'r48_geometry_receipt_sha256',
        'r47_export_sha256': 'r48_export_sha256',
        **{f'R47 {name}': f'R48 {name}' for name in (
            'right guard landing', 'landing to fixed deck', 'complete chin', 'chin to original deck')}
    }
    def current(value):
        if isinstance(value, dict):
            return {active.get(k, k): current(v) for k, v in value.items()}
        if isinstance(value, list):
            return [current(v) for v in value]
        return value

    for filename in ('candidate-audit.json', 'material.json', 'helper-comparison.json'):
        path = out / filename
        data = current(read(path))
        data['revision'] = 'r48'
        if filename == 'material.json':
            from material47 import per_object
            reference_archive = R47 / 'exports/complete-plate/R47-Complete-A1-mini-PETG.gcode.3mf'
            reference = per_object(reference_archive)
            present = data['r48']
            data['r47_reference_archive_sha256'] = digest(reference_archive)
            data['r47_reference'] = reference
            data['r48_minus_r47_g'] = {k: round(present[k] - reference[k], 3)
                                      for k in ('helper_estimated_g', 'slicer_declared_total_g')}
        write(path, data)


def endpoint_gap(row, reference):
    """XY discrepancy of the least displaced pairing, allowing reversed traversal."""
    from math import dist
    a, b = row['start_xy'], row['end_xy']
    x, y = reference['start_xy'], reference['end_xy']
    return min(max(dist(a, x), dist(b, y)), max(dist(a, y), dist(b, x)))


def compare_roofs(out):
    """Distinguish new unsupported native strokes from known trial residuals."""
    baseline = R47 / 'exports/complete-plate/roof-strokes.json'
    reference = read(baseline)
    current = read(out / 'roof-strokes.json')
    assert current['archive_sha256'] == digest(out / SELECTED)
    assert reference['archive_sha256'] == digest(baseline.parent / 'R47-Complete-A1-mini-PETG.gcode.3mf')
    previous = reference['sequence_gaps']
    unanchored = [r for r in previous if not r['before'] and not r['after']]
    unknown = []
    for row in current['sequence_gaps']:
        length = row['mm']
        if not row['before'] and not row['after']:
            same = [r for r in unanchored if r['z'] == row['z'] and abs(r['mm'] - length) <= .02
                    and endpoint_gap(row, r) <= .05]
            if len(same) != 1:
                unknown.append(row)
        elif row['before'] != row['after']:
            if length > 1.057:
                unknown.append(row)
        elif row['classification'] == 'beyond screened anchored span':
            if length > 13.565 or row['deviation_from_chord_mm'] >= .1:
                unknown.append(row)
        elif row['classification'] == 'unsupported bend outside bead corridor':
            if length > 2.732:
                unknown.append(row)
        elif row['classification'] != 'short straight two-ended bridge':
            unknown.append(row)
    report = {'archive_sha256': current['archive_sha256'], 'comparison_archive_sha256': reference['archive_sha256'],
              'comparison_file_sha256': digest(baseline), 'sequence_count': len(current['sequence_gaps']),
              'unqualified_sequences': unknown, 'within_previous_trial_envelope': not unknown,
              'scope': 'Unanchored moves must match previous location, layer and length. Rooted moves retain the R47 trial limits. Physical sag and support cleanup require a print.'}
    write(out / 'roof-comparison.json', report)
    return report


def seal(scratch, out):
    import plate38
    from compose47 import FUNCTIONAL

    check_plate_inputs(scratch, out)
    archive = out / SELECTED
    archive_hash = digest(archive)
    baselines = {r: read(scratch / 'contact-regression' / r / 'result.json') for r in ('r46', 'r47')}
    current_contacts = read(out / 'shelf-contact-areas.json')['peel_pieces']
    assert all(row['projected_contact_area_sum_mm2'] > 0. for row in current_contacts)
    shared_checker = HERE.parent / 'carbon-rod-holders-r45-open-keyways/contact45.py'
    assert all(row['passed'] and row['checker_sha256'] == digest(shared_checker) for row in baselines.values())
    write(out / 'contact-frame-regression.json', {
        'archive_sha256': archive_hash, 'older_fixtures': baselines,
        'r48_front_pieces_mm2': {row['removable_piece']: row['projected_contact_area_sum_mm2'] for row in current_contacts},
        'shared_checker_sha256': digest(shared_checker),
    })
    import battery_print48
    battery_dir, _ = battery_print48.inputs(scratch)
    battery_receipt = read(battery_dir / 'manifest.json')
    reports = {name: read(out / name) for name in REPORTS}
    assert all(r['archive_sha256'] == archive_hash for r in reports.values())
    core=reports['candidate-audit.json']
    assert core['screen_passed']
    assert all(core['r48_gate_results'].values()) and reports['guard-bond.json']['passed']
    assert reports['guard-seams.json']['passed']
    assert reports['guard-bond.json']['checker_sha256'] == digest(HERE / 'guard_bond48.py')
    assert reports['guard-bond.json']['native_seam_check_sha256'] == digest(out / 'guard-seams.json')
    assert read(out / 'guard-process.json')['generator_sha256'] == digest(HERE / 'guard_process48.py')
    assert core['right_guard_joint_report_sha256'] == digest(out / 'guard-bond.json')
    assert core['raw_carrier_evidence_sha256'] == digest(out / 'carrier-before-joint-inputs.json')
    assert read(out / 'carrier-before-joint-inputs.json')['raw_audit_sha256'] == digest(out / 'carrier-before-joint-review.json')
    corner = core['op1_pocket_terminal_corner']
    assert corner['checker_sha256'] == digest(HERE / 'pocket_corner48.py') and not corner['unqualified']
    assert len(corner['qualified']) == len(core['layer_starts']['missing_printed_components'])
    structural_sources=[HERE.parent / 'carbon-rod-holders-r46-middle-to-edge/audit46.py', R47 / 'audit47.py']
    assert core['folded_landing_checker_sha256']=={p.name:digest(p) for p in structural_sources}
    assert all(row['folded_landing']['passed'] for row in core['r48_landing_sections'])
    turn = read(out / 'cradle-turn-cad.json')
    assert turn['sha256'] == digest(HERE / 'cradle_turn48.py') and turn['covered_target_after_mm2'] > 1.25
    tab_cad = read(out / 'tab-sweep-cad.json')
    assert tab_cad['sha256'] == digest(HERE / 'tab_cleanup48.py')
    assert tab_cad['after_overlap_mm2'] < .0001 and tab_cad['before_foot_area_mm2'] > tab_cad['after_foot_area_mm2']
    assert reports['swing-tab-removal.json']['passed']
    assert reports['swing-tab-removal.json']['total_actual_tab_bond_mm2'] > .10
    assert reports['strength-paths.json']['passed']
    assert reports['recess-support-removal.json']['passed']
    assert reports['front-shelf-warning.json']['passed']
    assert reports['front-shelf-warning.json']['omission_checker_sha256'] == digest(HERE / 'support_tip48.py')
    assert reports['wire-feed-path.json']['passed'] and reports['rod-clip-shoulder.json']['passed']
    assert reports['rod-clip-shoulder.json']['checker_sha256'] == digest(HERE / 'shoulder_paths48.py')
    assert reports['other-audit/other-parts-audit.json']['passed']
    assert reports['other-audit/edge-click-load-path.json']['passed']
    assert reports['empty-space-checks.json']['maximum_interior_overlap_mm3'] < .0001
    assert not read(out / 'cad-starts.json')
    assert all(not row['unrooted_actual_components'] for row in reports['helper-starts.json']['owners'].values())
    for helper in reports['helper-starts.json']['owners'].values():
        for start in helper['starts_backed_across_one_empty_layer']:
            attributable = start['lower_owner_areas_mm2']
            assert attributable and all(area > 0 for area in attributable.values())
    delivery = reports['delivery-checks.json']
    assert sorted(delivery['functional_parts']) == sorted(FUNCTIONAL)
    reference = read(R47 / 'exports/complete-plate/delivery-checks.json')
    assert not delivery['archive_slice_warnings'], delivery['archive_slice_warnings']
    excessive = set(delivery['native_slice_warning_messages']) - set(reference['native_slice_warning_messages'])
    import shelf_warning48
    if shelf_warning48.WARNING in excessive and reports['front-shelf-warning.json']['passed']:
        excessive = excessive - {shelf_warning48.WARNING}
    assert not excessive, f'New or changed native warnings need review: {excessive}'
    assert delivery['startup']['first_object_nozzle_target_c'] == 245
    assert delivery['startup']['first_object_bed_target_c'] == 60
    assert delivery['smooth_timelapse_selected'] and delivery['actual_tower_present']
    with ZipFile(archive) as z, ZipFile(out / LAYOUT) as layout:
        settings_name = 'Metadata/project_settings.config'
        native_config = json.loads(z.read(settings_name))
        editable_config = json.loads(layout.read(settings_name))
        for field in ('filament_colour', 'filament_settings_id', 'filament_type', 'filament_ids'):
            assert native_config[field] == editable_config[field], field
        info = ET.fromstring(z.read('Metadata/slice_info.config'))
        spool, = info.findall('./plate/filament')
        assert spool.get('type') == 'PETG' and spool.get('color').upper().startswith(RED_PETG_SWATCH)
    assert compare_roofs(out)['within_previous_trial_envelope'], 'Review new roof features before sealing'
    shared_sources = [*structural_sources, shared_checker, shared_checker.with_name('standing_comb45.py'),
                      shared_checker.with_name('standing_aperture45.py'), shared_checker.with_name('roof_strokes45.py'),
                      shared_checker.with_name('helper_starts45.py'),
                      HERE.parent / 'carbon-rod-holders-r42-lower-diagonal/audit42.py',
                      R47 / 'audit_parts47.py', R47 / 'screen47.py',
                      HERE.parent / 'carbon-rod-holders-r32-complete-assembly/audit_plate32.py']
    shared_hashes = {p.relative_to(HERE.parent).as_posix(): digest(p) for p in shared_sources}
    write(out / 'trial-review.json', {
        'selected_archive_sha256': archive_hash,
        'geometry_receipt_sha256': digest(scratch / 'stage/r47-checks.json'),
        'digital_path_checks_passed': True, 'physical_acceptance_verified': False,
        'shared_checker_sha256': shared_hashes,
        'functional_parts': sorted(FUNCTIONAL),
        'battery_generation_manifest_sha256': digest(battery_dir / 'manifest.json'),
        'battery_geometry_checks_sha256': battery_receipt['checks_sha256'],
        'report_sha256': {name: digest(out / name) for name in (*REPORTS, 'roof-comparison.json', 'cradle-turn-cad.json', 'tab-sweep-cad.json', 'contact-frame-regression.json')},
    })
    reopen = read(out / 'reopen-checks.json')
    assert reopen['selected_archive_sha256'] == archive_hash
    reopen.update(own_final_deposition_audited=True, trial_review_sha256=digest(out / 'trial-review.json'),
                  scope='The native project was reopened, resliced and the selected output independently checked.')
    write(out / 'reopen-checks.json', reopen)

    exports = HERE / 'exports'
    guide = exports / 'assembly-guide.json'
    manifest_path = exports / 'manifest.json'
    geometry_path = exports / 'geometry-checks.json'
    guide_sources = read(guide)['sources']
    assert guide_sources['selected_native_archive_sha256'] == archive_hash
    assert guide_sources['geometry_receipt_sha256'] == digest(scratch / 'stage/r47-checks.json')
    assert all(digest(exports / name) == sha for name, sha in guide_sources['meshes_sha256'].items())
    manifest, geometry = read(manifest_path), read(geometry_path)
    target = HERE / 'exports/complete-plate'
    target.mkdir(parents=True, exist_ok=True)
    names = {SELECTED, LAYOUT, 'R45-Key-Carrier-layout.3mf'}
    for file in out.iterdir():
        if file.is_file() and (file.suffix in ('.json', '.stl') or file.name in names):
            shutil.copyfile(file, target / file.name)
    other = target / 'other-audit'
    other.mkdir(exist_ok=True)
    for name in ('other-parts-audit.json', 'edge-click-load-path.json'):
        shutil.copyfile(out / 'other-audit' / name, other / name)
    shutil.copytree(scratch / 'parent-audit-targets/r45-standing', target / 'r45-standing', dirs_exist_ok=True)
    sealed = plate38.recipe.make_print_only(target / SELECTED, target)
    sealed.replace(target / SEALED)
    receipt = read(target / 'print-only.json')
    receipt.update(file=SEALED, sha256=digest(target / SEALED), generator_sha256=digest(Path(__file__)))
    write(target / 'print-only.json', receipt)
    with ZipFile(target / SEALED) as package, ZipFile(archive) as native:
        assert package.read('Metadata/plate_1.gcode') == native.read('Metadata/plate_1.gcode')
        assert receipt['source_sha256'] == archive_hash
        (target / 'plate-preview.png').write_bytes(native.read('Metadata/plate_1.png'))
    sources = {f.name: digest(f) for f in sorted(HERE.glob('*.py')) + [HERE / 'complete-assembly.json']}
    manifest.update(digital_complete_plate_checks_passed=True, selected_archive_sha256=archive_hash,
                    physical_acceptance_verified=False, source_sha256=sources)
    write(manifest_path, manifest)
    geometry.update(sliced=True, selected_native_archive_sha256=archive_hash,
                    native_trial_review='complete-plate/trial-review.json')
    write(geometry_path, geometry)
    evidence = {
        'selected_archive_sha256': archive_hash, 'print_only_sha256': digest(target / SEALED),
        'guide_sha256': digest(guide), 'physical_acceptance_verified': False,
        'shared_checker_sha256': shared_hashes,
        'source_sha256': sources, 'manifest_sha256': digest(manifest_path),
        'geometry_sha256': digest(geometry_path),
        'files_sha256': {f.relative_to(target).as_posix(): digest(f) for f in sorted(target.rglob('*'))
                         if f.is_file() and f.name != 'evidence.json'},
    }
    write(target / 'evidence.json', evidence)
    print(target / SEALED, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('layout', 'compose', 'slice', 'reopen', 'carrier', 'carrier-joint', 'others', 'finish', 'delivery', 'seal'))
    parser.add_argument('scratch', type=Path)
    args = parser.parse_args()
    import build48  # Configure current geometry once before importing ancestral checkers.
    scratch = args.scratch.resolve()
    stage_checks(scratch)
    out = scratch / 'complete-plate'
    out.mkdir(exist_ok=True)
    if args.action in ('layout','compose'):
        layout(scratch, out, reuse_prepared_key=args.action == 'compose')
    elif args.action == 'seal':
        seal(scratch, out)
    else:
        audit(scratch, out, args.action)


if __name__ == '__main__':
    main()
