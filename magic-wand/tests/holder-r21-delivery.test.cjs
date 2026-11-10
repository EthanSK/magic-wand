// Guard the checked cable clip against stale source, toolpath or reload evidence.
// Passing this protects the delivered files; real PETG fit remains a trial.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const here = path.resolve(__dirname, '../hardware/carbon-rod-holders-r21-cable-clip');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(path.resolve(here, file))).digest('hex');
const read = file => JSON.parse(fs.readFileSync(path.resolve(here, file), 'utf8'));
const archive = 'exports/R21-A1-mini-PETG.gcode.3mf';

test('R21 delivery retains the exact checked clip and removable pads', () => {
  const manifest = read('exports/manifest.json');
  assert.deepEqual(manifest.plate_parts, ['Cable_Clip_4mm']);
  for (const [file, digest] of Object.entries(manifest.sources)) assert.equal(hash(file), digest, file);
  for (const [key, suffix] of [['part', 'SOURCE-REQUIRES-PREPARATION'], ['pads', 'ANCHOR-REMOVE-AFTER-PRINT']]) {
    assert.equal(hash(`exports/Cable_Clip_4mm-${suffix}.stl`), manifest.exports[key].sha256);
  }
  assert.equal(manifest.parts.Cable_Clip_4mm.body_count, 1);
  assert.equal(manifest.parts.Cable_Clip_4mm.watertight, true);
  assert.equal(manifest.physical_fit_verified, false);
  assert.equal(manifest.physical_strength_verified, false);
  const recipe = read('exports/print-checks.json');
  assert.equal(recipe.generator_sha256, hash('project21.py'));
  assert.equal(recipe.project_sha256, hash(archive));
  assert.equal(recipe.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(recipe.layout_sha256, hash('exports/R21-A1-mini-PETG-layout.3mf'));
  assert.deepEqual(recipe.warnings, []);
});

test('R21 final and reloaded beads retain both bores and both entry slits', () => {
  const roundtrip = read('exports/roundtrip-checks.json');
  assert.equal(roundtrip.generator_sha256, hash('roundtrip21.py'));
  assert.equal(roundtrip.input_project_sha256, hash(archive));
  assert.equal(roundtrip.input_audit_sha256, hash('exports/slice-checks.json'));
  assert.equal(roundtrip.resliced_audit_sha256, hash('exports/roundtrip-slice-checks.json'));
  assert.equal(roundtrip.passed, true);
  assert.equal(roundtrip.normalized_gcode_identical, true);
  for (const equal of Object.values(roundtrip.settings_identical)) assert.equal(equal, true);
  for (const [file, digest] of [['slice-checks.json', hash(archive)], ['roundtrip-slice-checks.json', roundtrip.resliced_project_sha256]]) {
    const audit = read(`exports/${file}`);
    assert.equal(audit.project_sha256, digest);
    assert.equal(audit.checker_sha256, hash('check21.py'));
    assert.equal(audit.project_generator_sha256, hash('project21.py'));
    assert.equal(audit.manifest_sha256, hash('exports/manifest.json'));
    assert.equal(audit.image_sha256, hash(`exports/${audit.image}`));
    assert.equal(audit.passed, true);
    assert.deepEqual(audit.working_openings, ['rod_bore_7p7mm', 'cable_bore_3p7mm', 'rod_entry', 'cable_entry']);
    assert.ok(audit.path_samples > 500);
    assert.equal(audit.all_layers.length, 12);
    for (const layer of audit.all_layers) {
      assert.equal(layer.connected_pieces, 1);
      assert.ok(layer.source_area_printed_fraction > .8);
      for (const tracks of Object.values(layer.ring_track_centres_mm)) assert.ok(tracks.length >= 2);
      for (const fraction of layer.tie_coverage) assert.ok(fraction > .95);
    }
    assert.deepEqual(audit.layer_starts.floating_components, []);
    assert.deepEqual(audit.layer_starts.missing_printed_components, []);
    assert.deepEqual(audit.partly_backed_regions, []);
    assert.equal(audit.pad_bead_gaps.length, 2);
    for (const gap of audit.pad_bead_gaps) assert.ok(gap.minimum_bead_gap_away_from_ties_mm >= .35);
    assert.ok(audit.tower_clearance_mm > 5);
    assert.ok(!audit.features.some(feature => /^(Support|Brim|Skirt)/.test(feature)));
    assert.equal(audit.actual_commands.first_extrusion_nozzle_c, 255);
    assert.equal(audit.actual_commands.first_extrusion_bed_c, 70);
    assert.equal(audit.actual_commands.unconditional_temperature_waits, true);
    assert.deepEqual(audit.actual_commands.ending_heater_targets_c, [0, 0]);
    assert.equal(audit.physical_print_verified, false);
  }
  assert.equal(roundtrip.gui_reopen_verified, false);
  assert.equal(roundtrip.physical_print_verified, false);
});
