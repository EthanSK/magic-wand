// A checked source/project/report snapshot must not silently go stale. This
// guards the R12 support-exclusion failure and R13's mixed-artifact failure.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const here = path.resolve(__dirname, '../hardware/carbon-rod-holders-r13-printability');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const read = file => JSON.parse(fs.readFileSync(path.join(here, file), 'utf8'));
const out = path.join(here, 'exports');
const fileHash = name => hash(path.join(here, name));

function projectNameFor(directory) { return read(`${directory}/print-checks.json`).sliced_project_filename; }
function checkSlice(slice, directory, projectName = projectNameFor(directory)) {
  assert.equal(slice.project_sha256, fileHash(`${directory}/${projectName}`));
  assert.equal(slice.manifest_sha256, fileHash(`${directory}/manifest.json`));
  assert.equal(slice.checker_sha256, fileHash('verify_slice.py'));
  assert.equal(slice.start_auditor_sha256, fileHash('start_audit.py'));
  assert.equal(slice.side_gap_checker_sha256, fileHash('side_gap.py'));
  assert.equal(slice.working_spaces_sha256, fileHash('working_spaces.py'));
  assert.equal(slice.parser_sha256, hash(path.resolve(here, '../printed-loop-wand/shard-tube-r2/check_sliced_paths.py')));
  assert.equal(slice.passed, true);
  assert.equal(slice.physical_fit_verified, false);
  assert.equal(Object.keys(slice.slice_images_sha256).length,Object.keys(slice.parts).length);
  for(const [file,digest]of Object.entries(slice.slice_images_sha256))assert.equal(fileHash(`${directory}/${file}`),digest);
  for (const part of Object.values(slice.parts)) {
    for (const check of Object.values(part.checks)) assert.deepEqual(check.violations, {});
    assert.deepEqual(part.whole_print_layer_starts.floating_components, []);
    assert.deepEqual(part.whole_print_layer_starts.missing_printed_components, []);
    assert.equal(part.helper_side_gap.violating_samples, 0);
    assert.ok(part.normal_mesh_difference_mm3 < .08);
    assert.ok(part.helper_mesh_difference_mm3 < .08);
  }
}

function checkProject(directory) {
  const print = read(`${directory}/print-checks.json`);
  assert.equal(print.generator_sha256, fileHash('print_project.py'));
  assert.equal(print.layout_sha256, fileHash(`${directory}/Holder-R13-layout.3mf`));
  assert.match(print.sliced_project_filename,/^(PRINT-FIRST-|AFTER-KEY-TEST-)/);
  assert.equal(print.sliced_project_sha256, fileHash(`${directory}/${print.sliced_project_filename}`));
  assert.equal(print.delivered_settings_registration.values_unchanged,true);
  for(const key of ['enable_support','brim_type','layer_height','wall_loops','sparse_infill_density','bridge_no_support','max_bridge_length'])
    assert.ok(print.delivered_settings_registration.registered_keys.includes(key));
  for (const [file, digest] of Object.entries(print.helper_sha256)) {
    assert.equal(fileHash(`${directory}/${file}`), digest, file);
  }
  const slice = read(`${directory}/slice-clearances.json`);
  checkSlice(slice, directory);
  const strength = read(`${directory}/strength-checks.json`);
  assert.equal(strength.passed, true);
  assert.equal(strength.project_sha256, print.sliced_project_sha256);
  assert.equal(strength.manifest_sha256, fileHash(`${directory}/manifest.json`));
  assert.equal(strength.checker_sha256, fileHash('strength_audit.py'));
  assert.equal(strength.physical_strength_verified, false);
  for (const name of Object.keys(read(`${directory}/manifest.json`).parts)) {
    assert.ok(strength.per_part_weak_point_decisions[name].length >= 2, name);
    for (const row of strength.per_part_weak_point_decisions[name]) assert.ok(row.minimum_sampled_track_count >= 2);
  }
  const decision = read(`${directory}/overhang-review.json`);
  assert.equal(decision.project_sha256, print.sliced_project_sha256);
  assert.equal(decision.slice_sha256, fileHash(`${directory}/slice-clearances.json`));
  assert.equal(decision.decisions_sha256, fileHash('overhang-decisions.json'));
  assert.equal(decision.qualifier_sha256, fileHash('qualify.py'));
  assert.equal(decision.test_recipe_audited, true);
  assert.equal(decision.full_set_ready, false);
  assert.deepEqual(decision.unreviewed_cases, []);
  assert.deepEqual(decision.obsolete_decisions, []);
  assert.deepEqual(decision.unreviewed_warnings, []);
  const views=read(`${directory}/view-checks.json`);
  assert.equal(views.generator_sha256,fileHash('review_views.py'));
  assert.equal(views.project_sha256,print.sliced_project_sha256);
  assert.equal(views.slice_audit_sha256,fileHash(`${directory}/slice-clearances.json`));
  for(const [file,digest]of Object.entries(views.images_sha256))assert.equal(fileHash(`${directory}/${file}`),digest);
  if(strength.key_to_clip_load_paths)for(const row of Object.values(strength.key_to_clip_load_paths)){
    assert.ok(row.minimum_mesh_area_mm2>=8);assert.ok(row.minimum_printed_area_mm2>=5);
  }
}

test('R13 exact model, all-bead scans, weak points and trial recipes stay qualified', () => {
  const manifest = read('exports/manifest.json');
  for (const [file, digest] of Object.entries(manifest.source_sha256)) {
    assert.equal(hash(path.resolve(here, file)), digest, file);
  }
  assert.equal(Object.keys(manifest.parts).length, 4);
  const changes = read('exports/design-differences.json');
  assert.equal(changes.generator_sha256, fileHash('compare_revision.py'));
  assert.equal(changes.manifest_sha256, fileHash('exports/manifest.json'));
  for (const [name, part] of Object.entries(changes.parts)) {
    assert.equal(part.r13_sha256, fileHash(`exports/${name}-assembly.stl`));
    assert.equal(part.r12_sha256, hash(path.resolve(here, `../carbon-rod-holders-r12-closer-thumb/exports/${name}-assembly.stl`)));
  }
  for (const [name, part] of Object.entries(manifest.parts)) {
    assert.equal(hash(path.join(out, `${name}-SOURCE-REQUIRES-PREPARATION.stl`)), part.stl_sha256, name);
    assert.equal(part.body_count, 1);
    assert.equal(part.watertight, true);
  }
  const scene = read('exports/review-scene.json');
  assert.equal(scene.sources.cad_sha256, fileHash('cad.py'));
  assert.equal(scene.sources.generator_sha256, fileHash('build_preview.py'));
  assert.equal(scene.sources.manifest_sha256, fileHash('exports/manifest.json'));
  const current = JSON.parse(fs.readFileSync(path.resolve(here, '../carbon-rod-holders/preview/current.json')));
  assert.ok(Number(current.revision.match(/-r(\d+)-/)[1]) >= 13);
  if (current.revision === manifest.revision) assert.equal(current.scene_sha256, fileHash('exports/review-scene.json'));
  const geometry = read('exports/geometry-checks.json');
  assert.equal(geometry.passed, true);
  assert.equal(geometry.manifest_sha256, fileHash('exports/manifest.json'));
  assert.equal(geometry.checker_sha256, fileHash('verify_geometry.py'));
  assert.equal(geometry.inherited_checker_sha256, hash(path.resolve(here, '../carbon-rod-holders-r12-closer-thumb/verify_geometry.py')));
  assert.ok(geometry.sensor_lower_spring_arm_change_mm3 < .002);
  assert.ok(geometry.sensor_fixed_axial_rail_added_lower_volume_mm3 > 20);
  const projects = ['exports', 'exports/fit-coupon', 'exports/fit-coupon-8.0', 'exports/fit-coupon-8.1',
    'exports/trial-Key_Carrier', 'exports/trial-Battery_Holder-Battery_End_Gate', 'exports/trial-XIAO_Rod_Holder'];
  for (const directory of projects) {
    checkProject(directory);
    const local = read(`${directory}/manifest.json`);
    if (directory.includes('fit-coupon')) {
      assert.equal(local.coupon, true);
      assert.equal(local.source_manifest_sha256, fileHash('exports/manifest.json'));
      assert.equal(local.generator_sha256, fileHash('fit_coupon.py'));
      assert.deepEqual(local.key_indices, [1]);
    } else if (directory !== 'exports') {
      assert.equal(local.subset_test, true);
      assert.equal(local.source_manifest_sha256, fileHash('exports/manifest.json'));
    }
  }
  const strength = read('exports/strength-checks.json');
  assert.equal(strength.passed, true);
  assert.equal(strength.project_sha256, fileHash(`exports/${projectNameFor('exports')}`));
  assert.equal(strength.manifest_sha256, fileHash('exports/manifest.json'));
  assert.equal(strength.checker_sha256, fileHash('strength_audit.py'));
  assert.equal(strength.physical_strength_verified, false);
  assert.equal(strength.full_set_physically_ready, false);
  for (const name of Object.keys(manifest.parts)) {
    assert.ok(strength.per_part_weak_point_decisions[name].length >= 2, name);
    for (const row of strength.per_part_weak_point_decisions[name]) {
      assert.ok(row.minimum_sampled_track_count >= 2);
      assert.ok(row.minimum_sampled_section_mm > 0);
      assert.ok(row.required_physical_test);
    }
  }
  const regressions = read('exports/start-audit-regressions.json');
  assert.equal(regressions.passed, true);
  assert.equal(regressions.tests_run, 8);
  assert.equal(regressions.checker_sha256, fileHash('start_audit.py'));
  assert.equal(regressions.regressions_sha256, fileHash('test_start_audit.py'));
  const old = read('exports/r12-negative-control.json');
  assert.equal(old.passed, false);
  assert.equal(old.checker_sha256, fileHash('verify_slice.py'));
  assert.equal(old.start_auditor_sha256, fileHash('start_audit.py'));
  assert.equal(old.negative_control.generator_sha256,fileHash('negative_control.py'));
  assert.ok(Object.values(old.parts).some(part => Object.values(part.checks)
    .some(check => Object.keys(check.violations).some(name => name.startsWith('Support')))));
  const reopen = read('exports/reopen-checks.json');
  assert.equal(reopen.input_project_sha256, fileHash(`exports/${projectNameFor('exports')}`));
  assert.equal(reopen.generator_sha256, fileHash('reopen_project.py'));
  assert.equal(reopen.effective_settings_equal, true);
  assert.equal(reopen.actual_paths_passed, true);
  assert.equal(reopen.gui_test_performed, false);
  const reopened = read('exports/reopened-clearances.json');
  assert.equal(reopened.project_sha256, reopen.reopened_project_sha256);
  assert.equal(reopen.actual_paths_report_sha256, fileHash('exports/reopened-clearances.json'));
  assert.equal(reopened.passed, true);
  assert.equal(reopened.checker_sha256, fileHash('verify_slice.py'));
  const views = read('exports/view-checks.json');
  assert.equal(views.generator_sha256, fileHash('review_views.py'));
  assert.equal(views.project_sha256, fileHash(`exports/${projectNameFor('exports')}`));
  assert.equal(views.slice_audit_sha256, fileHash('exports/slice-clearances.json'));
  for (const [file, digest] of Object.entries(views.images_sha256)) assert.equal(fileHash(`exports/${file}`), digest);
  const overview = read('exports/overview-checks.json');
  assert.equal(overview.generator_sha256, fileHash('audit_views.py'));
  assert.equal(overview.manifest_sha256, fileHash('exports/manifest.json'));
  assert.equal(overview.project_sha256, fileHash(`exports/${projectNameFor('exports')}`));
  assert.equal(Object.keys(overview.images_sha256).length, 4);
  assert.equal(Object.keys(overview.source_meshes_sha256).length, 7);
  for (const [file, digest] of Object.entries({...overview.source_meshes_sha256, ...overview.images_sha256}))
    assert.equal(fileHash(`exports/${file}`), digest);
  assert.doesNotMatch(fs.readFileSync(path.join(here, 'preview/index.html'), 'utf8'), /href="[^"\n]*\.stl"/i);
});
