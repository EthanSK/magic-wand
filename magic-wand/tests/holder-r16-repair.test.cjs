// Guard the R16 repair evidence: exact sources, meshes, A1 mini project, actual-bead audit and
// the regressions for the R15 failures. A passing guard is not a physical print result.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const here = path.resolve(__dirname, '../hardware/carbon-rod-holders-r16-repair');
const file = name => path.resolve(here, name);
const hash = name => crypto.createHash('sha256').update(fs.readFileSync(file(name))).digest('hex');
const read = name => JSON.parse(fs.readFileSync(file(name), 'utf8'));

test('R16 repair sources, meshes, project and audits stay bound and the failure regressions hold', () => {
  const manifest = read('exports/manifest.json');
  for (const [name, digest] of Object.entries(manifest.source_sha256)) assert.equal(hash(name), digest, name);
  assert.deepEqual(Object.keys(manifest.parts).sort(), ['Battery_End_Gate', 'Battery_Holder', 'Key_Carrier', 'XIAO_Rod_Holder']);
  for (const [name, part] of Object.entries(manifest.parts)) {
    assert.equal(hash(`exports/${name}-SOURCE-REQUIRES-PREPARATION.stl`), part.stl_sha256);
    assert.equal(part.body_count, 1); assert.equal(part.watertight, true);
  }
  assert.equal(manifest.print_helpers, 'none; rings not on the bed use 45-degree arc lead-in skirts');
  // The cell is the identified PKCell LP402025 at its manufacturer maximum, still unmeasured.
  assert.deepEqual(manifest.cell.manufacturer_max_mm, {width: 20.5, length: 27.5, thickness: 4.3});
  assert.equal(manifest.cell.measured, false);
  assert.equal(manifest.cap_clearance_screen.purchased_cap_dimensions_verified, false);

  const geometry = read('exports/geometry-checks.json');
  assert.equal(geometry.passed, true);
  assert.equal(geometry.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(geometry.checker_sha256, hash('verify16.py'));
  for (const part of Object.values(geometry.working_spaces)) for (const row of Object.values(part)) {
    const worst = row.worst_pose_intersection_mm3 ?? row.intersection_mm3; assert.ok(worst < .002);
  }
  const carrier = geometry.parts.Key_Carrier;
  assert.ok(carrier.minimum_cap_gap_mm >= .39999);
  assert.deepEqual(carrier.key_rotations_degrees, [0, 0, 0, 180, 0]);
  assert.equal(carrier.socket_insertion_route_mm, 6);
  for (const ring of Object.values(carrier.rings)) assert.ok(ring.lower_arm_extra_material_mm3 < .002 && ring.gap_intersection_mm3 < .002);
  const cage = geometry.parts.Battery_Holder;
  assert.ok(cage.nominal_play_mm.width_total_mm <= .8 && cage.nominal_play_mm.length_total_mm <= .6 && cage.nominal_play_mm.thickness_total_mm <= .7);
  assert.ok(cage.gate_touching_seated_cell_mm3 < 1e-6 && cage.cell_stopped_at_closed_end_mm3 > 1 && cage.cell_stopped_by_gate_stubs_mm3 > 1);
  assert.ok(cage.gate_relaxed_wedge_interference_mm3 > .005 && cage.gate_fitted_removal_route_mm3 < .002);
  const xiao = geometry.parts.XIAO_Rod_Holder;
  for (const value of Object.values(xiao.board_usb_wire_intersection_mm3)) assert.ok(value < .002);
  // Outline-aware seat (official 20.955 x 17.78, R1.905): ledge contact under every corner through
  // the full lateral and axial play, stops engaged at every lateral pose, travel matching the model.
  assert.equal(xiao.board_outline_mm.length, 20.955); assert.equal(xiao.board_outline_mm.corner_radius, 1.905);
  assert.equal(Object.keys(xiao.cradle_contact_under_board).length, 4);
  for (const corner of Object.values(xiao.cradle_contact_under_board)) assert.ok(corner.minimum_area_mm2 >= .3 && corner.minimum_y_extent_mm >= .4, JSON.stringify(corner));
  for (const row of Object.values(xiao.stop_engagement_0p2_past_travel_mm3)) assert.ok(row['near_+x_mm3'] + row['near_-x_mm3'] > .05 && row['far_+x_mm3'] + row['far_-x_mm3'] > .05);
  for (const t of Object.values(xiao.free_travel_mm)) assert.ok(Math.abs(t.near_mm - t.analytic_near_mm) < .03 && Math.abs(t.far_mm - t.analytic_far_mm) < .03);
  assert.match(xiao.header_caveat, /rails.*gussets.*struts|struts.*gussets|gussets.*struts/i);
  // Every key's window-to-hole ligament on the final section, the turned key included.
  assert.equal(Object.keys(carrier.window_ligaments).length, 5);
  for (const key of Object.values(carrier.window_ligaments)) assert.ok(key.minimum_mm >= 1.2, JSON.stringify(key));
  assert.equal(carrier.window_ligaments.key_3.rotation_degrees, 180);
  assert.equal(geometry.physical_fit_verified, false);

  const printed = read('exports/R16-A1-mini-PETG-print-checks.json');
  assert.equal(printed.generator_sha256, hash('project16.py'));
  assert.equal(printed.sliced_project_sha256, hash(`exports/${printed.sliced_project_filename}`));
  assert.equal(printed.printer, 'Bambu Lab A1 mini 0.4 nozzle');
  assert.deepEqual(printed.filament, ['Generic PETG @BBL A1M']);
  assert.deepEqual(printed.warnings, []);
  assert.equal(printed.delivered_settings_registration.values_unchanged, true);

  const audit = read('exports/slice-clearances.json');
  assert.equal(audit.passed, true);
  assert.equal(audit.project_sha256, hash(`exports/${printed.sliced_project_filename}`));
  assert.equal(audit.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(audit.checker_sha256, hash('slice16.py')); assert.equal(audit.spaces_sha256, hash('spaces16.py'));
  assert.ok(!audit.features.some(f => /^(Support|Brim|Skirt)/.test(f)));
  for (const [name, part] of Object.entries(audit.parts)) {
    for (const check of Object.values(part.checks)) assert.deepEqual(check.violations, {}, name);
    assert.deepEqual(part.layer_starts.floating_components, [], name);
    assert.deepEqual(part.layer_starts.missing_printed_components, [], name);
    assert.deepEqual(part.unclassified_overhangs, [], name);
    for (const row of part.partial_overhangs) assert.doesNotMatch(row.decision_class, /UNCLASSIFIED/);
  }
  // The R15 failure regression: every skirted ring band starts on real plastic, with two or more
  // surviving skirt tracks, and every ring keeps at least two radial tracks at its midplane.
  for (const [name, rings] of Object.entries(audit.strength.rings)) {
    for (const [label, ring] of Object.entries(rings)) {
      for (const tracks of Object.values(ring.radial_track_centres_mm)) assert.ok(tracks.length >= 2, `${name} ${label}`);
      assert.ok(Math.min(...Object.values(ring.radial_STL_sections_mm)) > .95, `${name} ${label}`);
      assert.ok(ring.arm_bonding.crown_bonded_down_to_degrees_above_equator >= 20 && ring.arm_bonding.crown_bonded_down_to_degrees_above_equator <= 60, `${name} ${label}`);
      if (ring.lead_in_skirt) {
        assert.ok(ring.lead_in_skirt.minimum_track_count >= 2 && ring.lead_in_skirt.rays > 20, `${name} ${label}`);
        // Strict direct backing of the first true band layer, no lateral expansion credit (review finding 5).
        assert.equal(ring.band_start_backing.lateral_expansion_mm, 0);
        assert.ok(ring.band_start_backing.first_band_layer_middle_assembly_y_mm <= ring.band_start_backing.band_face_assembly_y_mm + 1e-6);
        assert.ok(ring.band_start_backing.directly_backed_fraction >= .9, `${name} ${label}`);
      }
    }
  }
  for (const rows of Object.values(audit.strength.fixed_features)) for (const row of rows) {
    if ('minimum_sampled_section_mm' in row) assert.ok(row.minimum_sampled_section_mm >= row.screen_mm - .02 && row.minimum_sampled_track_count >= row.screen_tracks, row.feature);
    else assert.ok(row.printed_fraction >= row.screen_fraction && row.mesh_section_area_mm2 >= row.screen_area_mm2, row.feature);
    assert.equal(row.physical_strength_verified ?? false, false);
  }
  // Review finding 1: the bay-roof and gate-cap bands print at the local recipe speeds in the actual G-code.
  const recipe = audit.band_recipe_actual;
  assert.deepEqual(recipe.features_faster_than_requested, []);
  assert.ok(Object.keys(recipe.actual_in_bands).includes('Key_Carrier') && Object.keys(recipe.actual_in_bands).includes('Battery_Holder'));
  for (const layers of Object.values(recipe.actual_in_bands)) for (const row of Object.values(layers)) {
    for (const [feature, speeds] of Object.entries(row.features_mm_s)) if (/wall|infill|Bridge/.test(feature)) assert.ok(Math.max(...speeds) <= 20.5, `${feature} ${speeds}`);
  }
  // Review finding 6: complete intervening-layer scans through every loaded path (the 0.8-1.3 mm
  // board cradle features span 4-6 layers; slice16 itself checks each scan covers its whole range).
  for (const [name, scans] of Object.entries(audit.strength.path_scans)) for (const scan of scans) {
    assert.ok(scan.layers_scanned >= 3 && scan.minimum_mesh_section_mm2 >= scan.screen_area_mm2 && scan.minimum_printed_fraction >= scan.screen_fraction, `${name} ${scan.feature}`);
  }
  // Run006: the eight cradle scans (four ledges under the board plane, two V tabs, two far blocks) exist and pass.
  const cradle = audit.strength.path_scans.XIAO_Rod_Holder.filter(s => /ledge, top 0.45 mm|V stop tab|stop block/.test(s.feature));
  assert.equal(cradle.length, 8);
  for (const scan of cradle) assert.ok(scan.minimum_printed_fraction >= .5 && scan.minimum_printed_area_mm2 > .4, scan.feature);
  assert.ok(Object.keys(recipe.band_feature_length_mm_by_fan).includes('Key_Carrier'));
  const arms = read('exports/arm-stiffness-screen.json');
  assert.equal(arms.generator_sha256, hash('arm_stiffness16.py')); assert.equal(arms.slice_audit_sha256, hash('exports/slice-clearances.json'));
  assert.equal(arms.physical_force_verified, false);
  for (const [filename, digest] of Object.entries(audit.images_sha256)) assert.equal(hash(`exports/${filename}`), digest, filename);
  const views = read('exports/view-checks.json');
  assert.equal(views.manifest_sha256, hash('exports/manifest.json')); assert.equal(views.generator_sha256, hash('views16.py'));
  for (const [filename, digest] of Object.entries(views.images_sha256)) assert.equal(hash(`exports/${filename}`), digest, filename);
  // Final-delivered-project roundtrip: the exact delivered gcode.3mf reloaded and re-sliced offline,
  // same meshes, same effective settings and modifiers, same functional audit results.
  const roundtrip = read('exports/roundtrip-checks.json');
  assert.equal(roundtrip.generator_sha256, hash('roundtrip16.py')); assert.equal(roundtrip.slice_checker_sha256, hash('slice16.py'));
  assert.equal(roundtrip.input_project_sha256, hash(`exports/${printed.sliced_project_filename}`));
  assert.equal(roundtrip.input_is_layout_archive, false);
  assert.equal(roundtrip.registered_slice_audit_sha256, hash('exports/slice-clearances.json'));
  assert.equal(roundtrip.passed, true); assert.equal(roundtrip.functional_summary_equivalent, true); assert.equal(roundtrip.modifier_parts_identical, true);
  for (const same of Object.values(roundtrip.part_meshes_identical)) assert.equal(same, true);
  for (const same of Object.values(roundtrip.effective_settings_identical)) assert.equal(same, true);
  assert.deepEqual(roundtrip.slicer_warnings, []);
  assert.equal(roundtrip.physical_print_verified, false);
  const delivery = read('exports/delivery-checks.json');
  assert.equal(delivery.passed, true); assert.equal(delivery.physical_acceptance_verified, false);
  assert.equal(delivery.checker_sha256, hash('check16.py'));
  assert.equal(delivery.slice_audit_sha256, hash('exports/slice-clearances.json'));
  assert.equal(delivery.geometry_sha256, hash('exports/geometry-checks.json'));
  assert.equal(delivery.roundtrip_checks_sha256, hash('exports/roundtrip-checks.json'));
  // Earlier revisions stay untouched by this repair.
  const r15 = JSON.parse(fs.readFileSync(path.resolve(here, '../carbon-rod-holders-r15-tight-pyramid/exports/manifest.json'), 'utf8'));
  assert.equal(r15.revision, 'carbon-rod-holders-r15-tight-pyramid');
});
