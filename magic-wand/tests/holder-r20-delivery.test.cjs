// Keep the exact R20 delivery tied to its actual-bead and archive roundtrip
// evidence. These checks prevent stale evidence; they do not prove physical fit.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const here = path.resolve(__dirname, '../hardware/carbon-rod-holders-r20-finger-guard');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(path.resolve(here, file))).digest('hex');
const read = file => JSON.parse(fs.readFileSync(path.resolve(here, file), 'utf8'));
const parts = ['Key_Carrier', 'Battery_Holder', 'XIAO_Rod_Holder', 'Finger_Guard'];
const project = 'exports/R20-A1-mini-PETG.gcode.3mf';

test('R20 four-part geometry and every delivered mesh retain their checked identity', () => {
  const manifest = read('exports/manifest.json');
  assert.deepEqual(manifest.plate_parts, parts);
  for (const [file, digest] of Object.entries(manifest.source_sha256)) assert.equal(hash(file), digest, file);
  for (const name of parts) {
    const part = manifest.parts[name];
    assert.equal(hash(`exports/${name}-SOURCE-REQUIRES-PREPARATION.stl`), part.stl_sha256);
    assert.equal(hash(`exports/${name}-assembly.stl`), part.assembly_stl_sha256);
    assert.equal(part.body_count, 1); assert.equal(part.watertight, true);
  }
  const geometry = read('exports/geometry-checks.json');
  assert.equal(geometry.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(geometry.checker_sha256, hash('verify20.py'));
  assert.equal(geometry.passed, true);
  const members = read('exports/member-checks.json');
  assert.equal(members.checker_sha256, hash('members20.py'));
  assert.equal(members.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(members.passed, true);
  assert.equal(members.Key_Carrier_against_R16.lower_row_board_level.layers_split_into_more_pieces_than_r16, 0);
  const views = read('exports/view-checks.json');
  assert.equal(views.generator_sha256, hash('views20.py'));
  assert.equal(views.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(views.geometry_sha256, hash('exports/geometry-checks.json'));
  for (const [file, digest] of Object.entries(views.images_sha256)) assert.equal(hash(`exports/${file}`), digest, file);
  assert.equal(manifest.physical_fit_verified, false);
  assert.equal(manifest.physical_strength_verified, false);
});

test('R20 actual commands, clear openings, removable ties and ring tracks bind to the final slice', () => {
  const recipe = read('exports/R20-A1-mini-PETG-print-checks.json');
  assert.equal(recipe.generator_sha256, hash('project20.py'));
  assert.equal(recipe.layout_sha256, hash('exports/R20-A1-mini-PETG-layout.3mf'));
  assert.equal(recipe.sliced_project_sha256, hash(project));
  assert.deepEqual(recipe.parts, parts);
  assert.deepEqual(recipe.warnings, []); assert.deepEqual(recipe.slice_info_warnings, []);
  assert.equal(recipe.printer, 'Bambu Lab A1 mini 0.4 nozzle');
  assert.deepEqual(recipe.filament, ['Generic PETG @BBL A1M']);
  const audit = read('exports/slice-clearances.json');
  assert.equal(audit.project_sha256, hash(project));
  assert.equal(audit.checker_sha256, hash('slice20.py'));
  assert.equal(audit.member_checker_sha256, hash('members20.py'));
  assert.equal(audit.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(audit.anchors_sha256, hash('exports/anchors.json'));
  const anchors = read('exports/anchors.json');
  assert.equal(anchors.generator_sha256, hash('anchors20.py'));
  // The generator's broad cutter screen is not the delivery limit: keep the
  // new bay-centre ties away from the rails in every future prepared plate.
  for (const tie of anchors.parts.Finger_Guard.tie_sites) {
    assert.ok(tie.part_volume_in_cutter_corridor_mm3 < .5, 'Guard tie cutter route regressed');
  }
  assert.equal(audit.passed, true); assert.equal(audit.physical_print_verified, false);
  assert.deepEqual(Object.keys(audit.parts), parts);
  const commands = audit.executable_commands;
  assert.equal(commands.passed, true); assert.equal(commands.project_sha256, hash(project));
  assert.equal(commands.first_object_nozzle_target_c, 255);
  assert.equal(commands.first_object_bed_target_c, 70);
  assert.equal(commands.printing_temperature_wait_present, true);
  assert.deepEqual(commands.ending_heater_targets_c, [0, 0]);
  assert.ok(!audit.features.some(f => /^(Support|Brim|Skirt)/.test(f)));
  assert.ok(audit.features.includes('Prime tower'));
  assert.deepEqual(audit.slice_info_warnings, []);
  assert.ok(audit.timelapse_tower.path_samples > 500);
  for (const gap of Object.values(audit.timelapse_tower.gap_to_part_and_pad_bounds_mm)) assert.ok(gap > 5);
  for (const [name, part] of Object.entries(audit.parts)) {
    assert.ok(part.path_samples > 500 && part.pad_bead_samples > 0, name);
    for (const row of Object.values({...part.working_space_checks, ...part.pad_beads_against_keep_clear})) assert.deepEqual(row.violations, {}, name);
    assert.deepEqual(part.layer_starts.floating_components, [], name);
    assert.deepEqual(part.layer_starts.missing_printed_components, [], name);
    assert.equal(part.ties.smallest_centre_line_bead_coverage, 1);
    assert.ok(part.ties.smallest_pad_to_part_bead_gap_away_from_ties_mm >= .35);
  }
  assert.deepEqual(Object.keys(audit.strength.rings), parts);
  for (const [name, rings] of Object.entries(audit.strength.rings)) for (const ring of Object.values(rings)) {
    for (const tracks of Object.values(ring.radial_track_centres_mm)) assert.ok(tracks.length >= 2, name);
    if (ring.band_start_backing) assert.ok(ring.band_start_backing.directly_backed_fraction >= .9, name);
  }
  for (const row of Object.values(audit.strength.whole_sections)) {
    assert.ok(row.layers_scanned >= 20 && row.minimum_printed_fraction >= row.screen_fraction);
  }
  const members = audit.strength.members_actual_beads;
  assert.equal(Object.keys(members.Finger_Guard.smallest_rail_section_in_those_layers_mm2).length, 4);
  assert.ok(members.Key_Carrier.layers > 100);
  assert.equal(members.Key_Carrier.section_plane, 'layer middle');
  assert.ok(members.Key_Carrier.changed_layers_checked > 20);
  assert.ok(members.Key_Carrier.smallest_printed_fraction_in_changed_sections >= .8);
  for (const [file, digest] of Object.entries(audit.images_sha256)) assert.equal(hash(`exports/${file}`), digest, file);
});

test('R20 exact delivered archive survives a new slice with settings and routes intact', () => {
  const roundtrip = read('exports/roundtrip-checks.json');
  assert.equal(roundtrip.generator_sha256, hash('roundtrip20.py'));
  assert.equal(roundtrip.input_project_sha256, hash(project));
  assert.equal(roundtrip.registered_audit_sha256, hash('exports/slice-clearances.json'));
  assert.equal(roundtrip.passed, true);
  for (const same of Object.values(roundtrip.effective_settings_identical)) assert.equal(same, true);
  for (const same of Object.values(roundtrip.modifier_effective_bounds_identical)) assert.equal(same, true);
  assert.equal(roundtrip.modifier_settings_identical, true);
  assert.equal(roundtrip.resliced_actual_bead_audit_passed, true);
  assert.deepEqual(roundtrip.slicer_warnings, []);
  assert.deepEqual(roundtrip.slice_info_warnings_delivered, []);
  assert.deepEqual(roundtrip.slice_info_warnings_resliced, []);
  assert.equal(roundtrip.gui_reopen_verified, false);
  assert.equal(roundtrip.physical_print_verified, false);
  for (const [file, projectHash] of [
    ['exports/guard-path-checks.json', hash(project)],
    ['exports/guard-path-roundtrip-checks.json', roundtrip.resliced_project_sha256],
  ]) {
    const route = read(file);
    assert.equal(route.project_sha256, projectHash);
    assert.equal(route.checker_sha256, hash('guard_paths20.py'));
    assert.equal(route.manifest_sha256, hash('exports/manifest.json'));
    assert.equal(route.slice_audit_sha256, hash('exports/slice-clearances.json'));
    assert.equal(route.roundtrip_audit_sha256, hash('exports/roundtrip-checks.json'));
    assert.equal(route.passed, true); assert.deepEqual(route.violations, {});
    assert.equal(route.positions, 77); assert.ok(route.references_per_position >= 30);
    assert.ok(route.sample_count > 500 && route.candidate_samples > 1000);
    assert.ok(route.positive_control_intrusion_samples > 0);
    assert.equal(route.physical_fit_verified, false);
  }
});
