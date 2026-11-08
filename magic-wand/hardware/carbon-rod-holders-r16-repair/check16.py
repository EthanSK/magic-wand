#!/usr/bin/env python3
"""Check that every R16 receipt binds to the exact current sources, meshes, project and images.

Standalone (hashlib/json only) so it can run without the CAD environment. Fails closed on any
stale or missing proof; never asserts physical readiness.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def check():
    manifest = read(OUT / 'manifest.json')
    for path, digest in manifest['source_sha256'].items():
        assert sha(HERE / path) == digest, ('Stale model source', path)
    for name, part in manifest['parts'].items():
        assert part['stl_sha256'] == sha(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')), name
    manifest_sha = sha(OUT / 'manifest.json')
    geometry = read(OUT / 'geometry-checks.json')
    assert geometry['passed'] and geometry['manifest_sha256'] == manifest_sha and geometry['checker_sha256'] == sha(HERE / 'verify16.py')
    printed = read(OUT / 'R16-A1-mini-PETG-print-checks.json')
    project = OUT / printed['sliced_project_filename']
    assert printed['generator_sha256'] == sha(HERE / 'project16.py') and printed['sliced_project_sha256'] == sha(project)
    assert printed['delivered_settings_registration']['values_unchanged'] and not printed['warnings'], printed.get('warnings')
    audit = read(OUT / 'slice-clearances.json')
    assert audit['passed'] and audit['project_sha256'] == sha(project) and audit['manifest_sha256'] == manifest_sha
    assert audit['checker_sha256'] == sha(HERE / 'slice16.py') and audit['spaces_sha256'] == sha(HERE / 'spaces16.py')
    for filename, digest in audit['images_sha256'].items():
        assert sha(OUT / filename) == digest, filename
    for name, part in audit['parts'].items():
        assert not part['unclassified_overhangs'], (name, 'unreviewed overhang rows')
        assert all(not c['violations'] for c in part['checks'].values()), name
        assert not part['layer_starts']['floating_components'] and not part['layer_starts']['missing_printed_components'], name
    arms = read(OUT / 'arm-stiffness-screen.json')
    assert arms['generator_sha256'] == sha(HERE / 'arm_stiffness16.py') and arms['slice_audit_sha256'] == sha(OUT / 'slice-clearances.json')
    assert arms['physical_force_verified'] is False
    # Outline-aware XIAO seat: contact under every corner through the full play, stops engaged, ligaments on every key.
    xiao = geometry['parts']['XIAO_Rod_Holder']
    assert xiao['board_outline_mm']['length'] == 20.955 and xiao['board_outline_mm']['corner_radius'] == 1.905
    assert all(c['minimum_area_mm2'] >= .3 and c['minimum_y_extent_mm'] >= .4 for c in xiao['cradle_contact_under_board'].values()), 'cradle contact'
    assert all(row['near_+x_mm3'] + row['near_-x_mm3'] > .05 and row['far_+x_mm3'] + row['far_-x_mm3'] > .05 for row in xiao['stop_engagement_0p2_past_travel_mm3'].values())
    assert all(abs(t['near_mm'] - t['analytic_near_mm']) < .03 and abs(t['far_mm'] - t['analytic_far_mm']) < .03 for t in xiao['free_travel_mm'].values())
    assert geometry['parts']['Key_Carrier']['minimum_window_ligament_mm'] >= 1.2
    assert all(v['minimum_mm'] >= 1.2 for v in geometry['parts']['Key_Carrier']['window_ligaments'].values())
    # Final-delivered-project reload and re-slice roundtrip, bound to this exact project and audit.
    roundtrip = read(OUT / 'roundtrip-checks.json')
    assert roundtrip['generator_sha256'] == sha(HERE / 'roundtrip16.py') and roundtrip['slice_checker_sha256'] == sha(HERE / 'slice16.py')
    assert roundtrip['input_project_sha256'] == sha(project) and roundtrip['input_is_layout_archive'] is False
    assert roundtrip['registered_slice_audit_sha256'] == sha(OUT / 'slice-clearances.json')
    assert roundtrip['passed'] and roundtrip['functional_summary_equivalent'] and roundtrip['modifier_parts_identical'] and all(roundtrip['part_meshes_identical'].values())
    assert all(roundtrip['effective_settings_identical'].values()) and not roundtrip['slicer_warnings']
    recipe = audit['band_recipe_actual']
    assert recipe['features_faster_than_requested'] == [] and recipe['actual_in_bands'], 'Local recipe speeds not verified in the G-code'
    for part, rings in audit['strength']['rings'].items():
        for label, ring in rings.items():
            if 'band_start_backing' in ring:
                assert ring['band_start_backing']['lateral_expansion_mm'] == 0.0 and ring['band_start_backing']['directly_backed_fraction'] >= .9, (part, label)
    for part, scans in audit['strength']['path_scans'].items():
        for scan in scans:
            assert scan['minimum_mesh_section_mm2'] >= scan['screen_area_mm2'] and scan['minimum_printed_fraction'] >= scan['screen_fraction'], scan['feature']
    views = read(OUT / 'view-checks.json')
    assert views['manifest_sha256'] == manifest_sha and views['generator_sha256'] == sha(HERE / 'views16.py')
    for filename, digest in views['images_sha256'].items():
        assert sha(OUT / filename) == digest, filename
    settings = audit['settings']
    assert settings['printer_settings_id'] == 'Bambu Lab A1 mini 0.4 nozzle' and settings['filament_settings_id'] == ['Generic PETG @BBL A1M']
    assert settings['layer_height'] == '0.2' and settings['wall_loops'] == '3' and settings['sparse_infill_density'] == '20%'
    assert settings['enable_support'] == '0' and settings['brim_type'] == 'no_brim'
    result = {'checker_sha256': sha(Path(__file__)), 'manifest_sha256': manifest_sha, 'geometry_sha256': sha(OUT / 'geometry-checks.json'),
              'project_sha256': sha(project), 'project': project.name, 'slice_audit_sha256': sha(OUT / 'slice-clearances.json'),
              'views_sha256': sha(OUT / 'view-checks.json'), 'print_checks_sha256': sha(OUT / 'R16-A1-mini-PETG-print-checks.json'),
              'arm_stiffness_screen_sha256': sha(OUT / 'arm-stiffness-screen.json'), 'roundtrip_checks_sha256': sha(OUT / 'roundtrip-checks.json'),
              'passed': True, 'physical_acceptance_verified': False,
              'qualification': 'Consistent source, mesh, project, audit and image receipts. Physical fit, cleanup, strength, retention, friction and comfort require the real print.'}
    (OUT / 'delivery-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Consistent R16 source, mesh, project, slice-audit and image receipts.')


if __name__ == '__main__':
    check()
