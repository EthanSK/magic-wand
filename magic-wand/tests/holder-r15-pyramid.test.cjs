// Guard the delivered source/project evidence, not an assumption that a
// watertight mesh or a completed slice proves a physical print works.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const here = path.resolve(__dirname, '../hardware/carbon-rod-holders-r15-tight-pyramid');
const file = name => path.resolve(here, name);
const hash = name => crypto.createHash('sha256').update(fs.readFileSync(file(name))).digest('hex');
const read = name => JSON.parse(fs.readFileSync(file(name), 'utf8'));

test('R15 pyramid trials, source receipts and effective viewer defaults stay current', () => {
  const manifest = read('exports/manifest.json');
  for (const [name, digest] of Object.entries(manifest.source_sha256)) assert.equal(hash(name), digest, name);
  assert.equal(Object.keys(manifest.parts).length, 4);
  for (const [name, part] of Object.entries(manifest.parts)) {
    assert.equal(hash(`exports/${name}-SOURCE-REQUIRES-PREPARATION.stl`), part.stl_sha256);
    assert.equal(part.body_count, 1); assert.equal(part.watertight, true);
  }
  // Sampled socket routes stay complete: every key's two 189-pose routes are carved pose by pose, never cropped.
  const carve = manifest.working_space_carve;
  assert.equal(Object.keys(carve['carrier:modular:None']).length, 10);
  assert.deepEqual(Object.keys(carve.key_load_rails).sort(), ['key_1_maximum_socket_loading', 'key_1_socket_loading']);
  for (const log of [carve['carrier:modular:None'], carve.key_load_rails]) for (const route of Object.values(log)) {
    assert.equal(route.poses, 189); assert.ok(route.poses_meeting_material >= 0 && route.poses_meeting_material <= 189);
  }
  const geometry = read('exports/geometry-checks.json');
  assert.equal(geometry.key_interface.socket_route_poses_checked, 189); assert.equal(geometry.key_interface.working_space_route_identical, true);
  assert.equal(geometry.manifest_sha256, hash('exports/manifest.json'));
  assert.equal(geometry.checker_sha256, hash('verify_geometry.py')); assert.equal(geometry.passed, true);
  assert.ok(geometry.pyramid_layout.minimum_swept_envelope_gap_mm >= .39999);
  assert.equal(geometry.pyramid_layout.bought_cap_dimensions_and_play_verified, false);
  assert.equal(Object.keys(geometry.key_interface.missing_flange_corner_lands_mm3).length, 20);
  for (const missing of Object.values(geometry.key_interface.missing_flange_corner_lands_mm3)) assert.ok(missing<.0001);
  // Reviewer N11: the longer inferred cap side lies along the switch stem-post axis (X); size stays unmeasured.
  const caps = geometry.cap_orientation;
  assert.equal(caps.stem_post_axis, 'X'); assert.ok(caps.reference_cap_x_mm > caps.reference_cap_y_mm);
  assert.ok(caps.nominal_cap_gap_x_mm >= 1.19999 && caps.nominal_cap_gap_y_mm >= 1.19999);
  assert.equal(caps.purchased_cap_dimensions_verified, false); assert.equal(caps.mounted_cap_measurement_required_before_print, true);
  assert.deepEqual(geometry.pyramid_layout.reference_cap_size_mm, [caps.reference_cap_x_mm, caps.reference_cap_y_mm]);
  // Ethan's "Frame edge below the bottom row": recessed behind the lower cap fronts, softened, no projection.
  const recess = geometry.lower_front_recess;
  assert.ok(recess.material_ahead_of_plane_mm3 < .002); assert.ok(recess.recess_behind_reference_cap_front_mm >= .35);
  assert.ok(recess.front_plane_y_mm <= recess.switch_flange_land_front_y_mm - .35);
  assert.equal(recess.chin.angle_degrees, 45); assert.ok(recess.chin.recess_at_chin_bottom_behind_reference_cap_front_mm >= 2);
  assert.ok(recess.missing_continuous_bumper_core_mm3 < .002); assert.ok(recess.missing_lip_below_switch_housing_mm3 < .002);
  assert.ok(recess.material_under_chin_mm3 < .002); assert.ok(recess.missing_front_clip_free_arm_mm3 < .002);
  for (const value of Object.values(recess.softened_edge_corner_material_mm3)) assert.ok(value < .002);
  assert.ok('front_clip_crown_edge' in recess.softened_edge_corner_material_mm3);
  for (const value of Object.values(recess.missing_front_clip_tie_and_spine_probe_mm3)) assert.ok(value < .0001);
  // Reviewer N12: both upper socket floors grow from a fixed rear spine.
  assert.equal(Object.keys(recess.missing_rear_floor_spine_probe_mm3).length, 6);
  for (const value of Object.values(recess.missing_rear_floor_spine_probe_mm3)) assert.ok(value < .0001);
  // Reviewer N16: the true spine necks leave each clip ring; screen 1.25 mm with the retained .02 allowance.
  assert.equal(recess.spine_neck_screen_mm, 1.25);
  assert.deepEqual(Object.keys(recess.spine_neck_vertical_sections_at_x0_mm).sort(), ['front', 'rear']);
  for (const sections of Object.values(recess.spine_neck_vertical_sections_at_x0_mm)) {
    assert.equal(Object.keys(sections).length, 12);
    for (const value of Object.values(sections)) assert.ok(value >= recess.spine_neck_screen_mm - .02);
  }
  for (const value of Object.values(recess.spine_crown_seed_outside_ring_mm3)) assert.ok(value < .002);
  assert.ok(Math.abs(recess.front_clip_y_mm - (recess.front_plane_y_mm + 1.8)) < 1e-9); assert.equal(recess.physical_comfort_verified, false);
  const scene = read('exports/review-scene.json');
  for (const [key, source] of Object.entries({cad_sha256:'cad.py', generator_sha256:'build_preview.py',
    renderer_sha256:'preview/preview.mjs', html_sha256:'preview/index.html', manifest_sha256:'exports/manifest.json',
    geometry_encoder_sha256:'../carbon-rod-holders-r12-closer-thumb/build_preview.py'})) assert.equal(scene.sources[key], hash(source));
  assert.equal(scene.parameters.assembly.default_key_orientation, 'two-toward-tip');
  assert.deepEqual(scene.key_positions, geometry.pyramid_layout.centres_mm);
  const html = fs.readFileSync(file('preview/index.html'), 'utf8');
  assert.match(html, /value="two-toward-tip" selected/);
  assert.doesNotMatch(html, /value="three-toward-tip" selected|href="[^"\n]*\.stl"/i);
  const current = read('../carbon-rod-holders/preview/current.json');
  assert.ok(Number(current.revision.match(/-r(\d+)-/)[1]) >= 15);
  if (current.revision === manifest.revision) assert.equal(current.scene_sha256, hash('exports/review-scene.json'));
  const delivery = read('exports/delivery-checks.json');
  assert.equal(delivery.passed, true); assert.equal(delivery.physical_acceptance_verified, false);
  assert.equal(delivery.checker_sha256, hash('check_delivery.py'));
  assert.equal(delivery.geometry_sha256, hash('exports/geometry-checks.json'));
  assert.equal(delivery.overview_sha256, hash('exports/overview-checks.json'));
  assert.equal(delivery.scene_sha256, hash('exports/review-scene.json'));
  for (const directory of ['exports', 'exports/trial-Key_Carrier']) {
    const print = read(`${directory}/print-checks.json`); const project = `${directory}/${print.sliced_project_filename}`;
    assert.equal(print.generator_sha256, hash('print_project.py'));
    assert.equal(print.layout_sha256, hash(`${directory}/Holder-R15-layout.3mf`));
    assert.equal(print.sliced_project_sha256, hash(project)); assert.equal(print.delivered_settings_registration.values_unchanged, true);
    // Reviewer N13: helper-contact faces stay off Bambu's layer-middle sampling planes.
    const guard = print.helper_contact_face_midplane_guard; assert.ok(guard.minimum_distance_required_mm >= .04);
    assert.ok(guard.faces.Key_Carrier.length >= 10);
    for (const faces of Object.values(guard.faces)) for (const face of faces)
      assert.ok(face.distance_from_slicing_midplane_mm >= guard.minimum_distance_required_mm, face.label);
    for (const [name,digest] of Object.entries(print.helper_sha256)) assert.equal(hash(`${directory}/${name}`), digest);
    const slice = read(`${directory}/slice-clearances.json`); assert.equal(slice.passed, true);
    // All 34 key-carrier working spaces (51 across the full set) are checked; swept routes keep every pose.
    assert.equal(Object.keys(slice.parts.Key_Carrier.checks).length, 34);
    if (directory === 'exports') assert.equal(Object.values(slice.parts).reduce((sum, part) => sum + Object.keys(part.checks).length, 0), 51);
    const routes = slice.parts.Key_Carrier.swept_space_poses; assert.equal(Object.keys(routes).length, 10);
    for (const count of Object.values(routes)) assert.equal(count, 189);
    assert.equal(slice.project_sha256, hash(project)); assert.equal(slice.manifest_sha256, hash(`${directory}/manifest.json`));
    for (const [key,source] of Object.entries({checker_sha256:'verify_slice.py', start_auditor_sha256:'start_audit.py',
      side_gap_checker_sha256:'side_gap.py', working_spaces_sha256:'working_spaces.py', parser_sha256:'../printed-loop-wand/shard-tube-r2/check_sliced_paths.py'})) assert.equal(slice[key],hash(source));
    for (const part of Object.values(slice.parts)) {
      for (const check of Object.values(part.checks)) assert.deepEqual(check.violations, {});
      assert.deepEqual(part.whole_print_layer_starts.floating_components, []);
      assert.deepEqual(part.whole_print_layer_starts.missing_printed_components, []);
      assert.equal(part.helper_side_gap.violating_samples, 0);
      for (const scope of ['layer_starts','whole_print_layer_starts']) for (const [kind,areaKey] of
        [['partial_overhangs','unbacked_mesh_area_mm2'],['support_backed_islands','area_mm2']]) for (const patch of part[scope][kind]) {
        assert.ok(patch.direct_backed_fraction>=0 && patch.direct_backed_fraction<=1);
        assert.ok(Math.abs(patch.direct_backed_area_mm2+patch.residual_unbacked_area_mm2-patch[areaKey])<.001);
      }
    }
    const strength=read(`${directory}/strength-checks.json`);
    assert.equal(strength.passed,true);assert.equal(strength.physical_strength_verified,false);
    assert.equal(strength.checker_sha256,hash('strength_audit.py'));assert.equal(strength.project_sha256,hash(project));
    assert.equal(Object.keys(strength.key_socket_floor_sampled_sections_mm).length,5);
    const floors=strength.per_part_weak_point_decisions.Key_Carrier.find(row=>row.feature==='All five socket floors including leading edges');
    assert.equal(floors.probes.length,20);assert.ok(floors.minimum_sampled_track_count>=2);
    for (const label of ['Recessed lower front bumper','Front clip ties to fixed rails','Front clip to central floor spine','Rear clip to upper floor spine']) {
      const row=strength.per_part_weak_point_decisions.Key_Carrier.find(item=>item.feature===label);
      assert.ok(row,label);assert.ok(row.minimum_sampled_track_count>=2);assert.equal(row.physical_strength_verified,false);
    }
    // Reviewer N16: both spines are scanned over their whole crown-to-root span, not only at convenient probes.
    for (const label of ['Front clip to central floor spine','Rear clip to upper floor spine']) {
      const row=strength.per_part_weak_point_decisions.Key_Carrier.find(item=>item.feature===label);
      const scan=row.neck_scan;assert.ok(scan,label);assert.equal(scan.screen_mm,1.25);assert.equal(scan.screen_allowance_mm,.02);
      assert.ok(scan.span_assembly_y_mm[0]<scan.clip_ring_back_face_y_mm&&scan.clip_ring_back_face_y_mm<scan.span_assembly_y_mm[1],label);
      assert.equal(scan.mesh_ray_step_mm,.1);assert.ok(scan.mesh_rays>=200,label);assert.ok(scan.printed_layers.length>=20,label);
      assert.ok(scan.minimum_STL_section_mm>=scan.screen_mm-scan.screen_allowance_mm,label);assert.ok(scan.minimum_track_count>=2,label);
      for (const layer of scan.printed_layers) {assert.equal(layer.rays.length,5);assert.ok(layer.minimum_track_count>=2);}
      assert.ok(row.minimum_sampled_section_mm<=scan.minimum_STL_section_mm&&row.minimum_sampled_section_mm>=1.23,label);
    }
    for (const key of Object.values(strength.key_to_clip_load_paths)) {assert.ok(key.minimum_mesh_area_mm2>=8);assert.ok(key.minimum_printed_area_mm2>=5);}
    const decision=read(`${directory}/overhang-review.json`);
    assert.equal(decision.project_sha256,hash(project));assert.equal(decision.slice_sha256,hash(`${directory}/slice-clearances.json`));
    assert.equal(decision.qualifier_sha256,hash('qualify.py'));assert.equal(decision.decisions_sha256,hash('overhang-decisions.json'));
    assert.equal(decision.test_recipe_audited,true);assert.equal(decision.full_set_ready,false);
    for (const key of ['unreviewed_cases','obsolete_decisions','unreviewed_warnings'])assert.deepEqual(decision[key],[]);
    const view=read(`${directory}/view-checks.json`);
    assert.equal(view.project_sha256,hash(project));assert.equal(view.generator_sha256,hash('review_views.py'));
    assert.equal(view.slice_audit_sha256,hash(`${directory}/slice-clearances.json`));
    for (const [name,digest] of Object.entries({...view.images_sha256,...slice.slice_images_sha256}))assert.equal(hash(`${directory}/${name}`),digest);
    const reopen=read(`${directory}/reopen-checks.json`);
    assert.equal(reopen.input_project_sha256,hash(project));assert.equal(reopen.generator_sha256,hash('reopen_project.py'));
    assert.equal(reopen.effective_settings_equal,true);assert.equal(reopen.actual_paths_passed,true);assert.equal(reopen.gui_test_performed,false);
    assert.equal(reopen.actual_paths_report_sha256,hash(`${directory}/reopened-clearances.json`));
    const reopened=read(`${directory}/reopened-clearances.json`);assert.equal(reopened.passed,true);
    for (const key of ['checker_sha256','parser_sha256','start_auditor_sha256','side_gap_checker_sha256','working_spaces_sha256'])
      assert.equal(reopened[key],slice[key],key);
    assert.equal(delivery.projects[directory].project_sha256,hash(project));
    assert.equal(delivery.projects[directory].view_receipt_sha256,hash(`${directory}/view-checks.json`));
    assert.equal(delivery.projects[directory].reopen_receipt_sha256,hash(`${directory}/reopen-checks.json`));
  }
  const regressions=read('exports/start-audit-regressions.json');
  assert.equal(regressions.passed,true);assert.equal(regressions.tests_run,9);
  assert.equal(regressions.checker_sha256,hash('start_audit.py'));
  assert.equal(regressions.regressions_sha256,hash('test_start_audit.py'));
});
