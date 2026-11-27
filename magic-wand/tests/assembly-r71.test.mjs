// Check the R71 exported assembly and CAD receipts with node --test. — Claude Fable 5.2
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide, assemblyComponents} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const files = new URL('../hardware/carbon-rod-holders-r71-contained-battery/exports/', import.meta.url);
const r70Files = new URL('../hardware/carbon-rod-holders-r70-short-holder/exports/', import.meta.url);
const r59Files = new URL('../hardware/carbon-rod-holders-r59-flipped-guard/exports/', import.meta.url);
const bytes = (path, base = files) => readFileSync(new URL(path, base));
const load = (path, base = files) => JSON.parse(bytes(path, base));
const sha = (path, base = files) => createHash('sha256').update(bytes(path, base)).digest('hex');
const guide = validateGuide(load('assembly-guide.json'));
const r70Guide = load('assembly-guide.json', r70Files);
const names = ['carrier', 'battery', 'base'];
const reports = Object.fromEntries(names.map(name => [name, load(name + '.json')]));
const copied = ['Gravity_Wires-assembly.stl', 'OP1_Lid_Stop-assembly.stl'];
const clips = ['DFR_Clip_Left-assembly.stl', 'DFR_Clip_Right-assembly.stl'];
const meshes = ['Key_Carrier-assembly.stl', 'Touch_Paddle-assembly.stl', 'DFR_Post_Bar-assembly.stl', ...clips, ...copied];
const kit = ['Key_Carrier', 'Touch_Paddle', 'Hinge_Pin', 'Pin_Clip', 'Pin_Clip_Spare', 'OP1_Lid_Stop', 'DFR_Post_Bar', 'DFR_Clip_Left',
  'DFR_Clip_Right'].sort();

test('every R71 report measured the exported meshes and passes; nothing claims a slice or a fit', () => {
  for (const [name, report] of Object.entries(reports)) {
    for (const mesh of meshes) assert.equal(report.meshes_sha256[mesh], sha(mesh), `${name} ${mesh}`);
    assert.equal(report.passes, true, name);
    assert.ok(report.gates.every(Boolean), name);
    assert.equal(report.physical_fit_verified, false, name);
  }
  const summary = load('checks.json');
  assert.equal(summary.passes, true);
  assert.equal(summary.sliced, false);
  assert.equal(summary.physical_fit_verified, false);
  const source = load('source-reproduction.json');
  assert.equal(source.passes, true);
  for (const mesh of meshes) assert.equal(source.meshes[mesh].reproduced_sha256, sha(mesh), mesh);
  for (const mesh of copied) assert.equal(sha(mesh), sha(mesh, r70Files), `${mesh} is R70's file`);
  for (const mesh of ['Key_Carrier-assembly.stl', 'Touch_Paddle-assembly.stl', 'DFR_Post_Bar-assembly.stl']) assert.notEqual(sha(mesh), sha(mesh, r70Files), mesh);
  assert.equal(sha('Key_Carrier-assembly.stl'), '2a7e2047f1f960c38f71fbb778b9d4a26c347ba9154d6dfbae47a3253bca8160', 'the clip repair leaves the holder untouched');
  for (const mesh of clips) assert.notEqual(sha(mesh), sha(mesh, r59Files), mesh);
  assert.equal(reports.carrier.r70_carrier_sha256, sha('Key_Carrier-assembly.stl', r70Files));
});

test('the pouch ends at the rear face, under the solder allowance, clear of every fitted part', () => {
  const {placement, limits, fitted_parts: fitted} = reports.battery;
  assert.equal(placement.behind_the_rear_face_mm.r71, 0);
  assert.equal(placement.behind_the_rear_face_mm.r70, 12.45);
  assert.equal(placement.moved_outward_mm, 6.2);
  assert.ok(placement.held_by_the_rail_mm.r71 >= placement.held_by_the_rail_mm.r70);
  assert.ok(placement.outer_rail_mm.r71 < 1 && placement.outer_rail_mm.r70 > 3);
  const measured = limits.measured_on_the_fitted_models;
  assert.deepEqual([measured.socket_underside_z_mm, measured.tape_underside_z_mm, measured.solder_allowance_underside_z_mm], [5.6, 5.2, 4.37]);
  assert.ok(limits.above.pads_to_the_allowance_mm >= 0.14 && limits.above.pouch_to_the_allowance_mm >= 0.19);
  assert.ok(limits.above.pouch_to_the_tape_margin_mm >= 1 && limits.above.pouch_to_the_fitted_switches_and_sockets_mm >= 1.4);
  assert.ok(limits.above.at_the_tape_margin_instead.into_the_solder_allowance_mm3 > 1, 'the report must show why the higher place was not used');
  assert.ok(Object.values(fitted.pouch_to_switches_and_sockets_mm3).every(v => v < 0.001));
  assert.ok(fitted.pouch_to_tape_and_solder_allowance_mm3 < 0.001 && fitted.rail_and_guard_to_tape_and_solder_allowance_mm3 < 0.001);
  assert.match(reports.battery.pouch, /not measured/);
});

test('the placement table states what each height allows, with and without the guard change', () => {
  const tried = reports.battery.other_places_tried;
  const least = tried.least_behind_the_rear_face_mm;
  assert.ok(least['against the deck (R70)'].hardware_only > 12);
  assert.ok(least['under the switch posts'].hardware_only > 9);
  assert.ok(least['under the tape margin'].hardware_only > 6);
  assert.equal(least['under the solder allowance (R71)'].hardware_only, 0);
  const here = tried.rows.find(row => row.height === 'under the solder allowance (R71)' && row.pouch_x0_mm === -27.45);
  assert.ok(here.hardware_and_the_r70_guard.behind_the_rear_face_mm > 3, 'R70\'s guard is what the re-route removes');
  assert.equal(tried.rows.length, 16);
});

test('every key route is open with the pouch out, and the pouch seats, slides and stops', () => {
  const {loading, seat, removal, spring} = reports.battery;
  assert.equal(loading.key_poses_checked, 336);
  assert.deepEqual(loading.key_obstructions, []);
  assert.deepEqual(Object.keys(loading.routes_crossing_the_seated_pouch_mm3.r70), []);
  const crossing = Object.keys(loading.routes_crossing_the_seated_pouch_mm3.r71);
  assert.ok(crossing.length > 0 && crossing.every(name => /^key_3_.*(loading|dogleg)$|^key_0_soldered_socket_slide$/.test(name)), 'only the two left sockets pass the pouch');
  assert.match(loading.order, /take the pouch out/);
  assert.ok(seat.seated_overlap_with_the_spring_mm3 > 0 && seat.seated_overlap_without_the_spring_mm3 < 0.01);
  assert.ok(seat.slide_in_from_the_rear_without_the_spring_mm3 < 0.01 && seat.slide_in_poses > 50);
  assert.ok(seat.slide_in_against_switches_sockets_tape_and_solder_mm3 < 0.001);
  assert.ok(seat.widest_pouch_seated_mm3 < 0.01 && seat.pushed_0_2mm_past_the_stop_mm3 > 0.02);
  assert.ok(seat.lips_under_the_pouch_mm2.r71 >= seat.lips_under_the_pouch_mm2.r70 && seat.bearing_over_the_pouch_mm2.r71 > 30);
  assert.ok(removal.underside_share_open >= 0.5 && removal.covered_inside_that_window_mm2 < 0.01);
  assert.equal(removal.nothing_behind_the_pouch_end_mm3, 0);
  assert.equal(placement().spring.preload_mm, 0.21);
  assert.ok(spring.room_behind_the_tongue_to_the_guard_mm > 0.5);
});

function placement() { return reports.battery.placement; }

test('the left guard keeps its root, sections and height; only the arm and the crown hub move', () => {
  const g = reports.carrier.left_guard;
  assert.ok(g.new_members_core_missing_mm3 < 0.02 && g.old_arm_and_bars_left_mm3 < 0.02);
  assert.ok(g.arm_root_section_changed_mm2 < 0.05);
  assert.equal(g.lowest_z_mm.r71, g.lowest_z_mm.r70);
  assert.equal(g.moved.hub_moved_toward_the_lower_row_mm, 2.7);
  assert.ok(g.slot_between_the_crown_and_the_pouch_nose_mm < 1);
  assert.ok(g.steepest_descent_from_the_print_axis_deg.r71 <= g.steepest_descent_from_the_print_axis_deg.r70 + 1);
  assert.ok(g.sideways_run_to_the_hub.r71.rise_deg >= g.sideways_run_to_the_hub.r70.rise_deg - 0.5);
  const {limits} = reports.battery;
  assert.ok(limits.forward.nose_to_the_arm_mm >= 0.03 && limits.forward.nose_to_the_arm_mm <= 0.08);
  assert.ok(limits.inboard.arm_to_the_pouch_side_mm >= placement().spring.width_allowance_mm);
  assert.equal(limits.below.left_guard_lowest_z_mm.r71, limits.below.left_guard_lowest_z_mm.r70);
  assert.ok(limits.inboard.guard_to_the_solder_allowance_mm > 1 && limits.inboard.guard_to_the_tape_margin_mm > 0.5);
});

test('everything outside the changed zones is R70, and the rear shoulders mirror each other', () => {
  const carrier = reports.carrier;
  for (const [zone, row] of Object.entries(carrier.unchanged_zones_sections_against_r70)) assert.ok(row.max_area_mm2 < 0.05, zone);
  assert.ok(carrier.left_bank_inside_the_mirrored_outline.removed_mm3 < 0.05, 'the taper must not copy an opening into the left backplate');
  const outline = carrier.rear_outline_left_against_mirrored_right;
  assert.ok(outline.r70.plate_above_the_deck_edge_round.left_only_mm2 > 20);
  assert.ok(outline.r71.plate_above_the_deck_edge_round.left_only_mm2 < 1 && outline.r71.plate_above_the_deck_edge_round.right_only_mm2 < 1);
  assert.ok(outline.removed_for_the_taper_mm3 > 50);
  assert.equal(carrier.components, 1);
  assert.ok(carrier.lower_edge.round_share >= 0.75);
  assert.deepEqual(carrier.lower_edge.square, []);
  assert.ok(Object.values(carrier.unchanged_parts).every(Boolean));
});

test('the hinge has more room above and below the journals and the same click', () => {
  const hinge = reports.carrier.hinge;
  for (const key of Object.keys(hinge.click_values.r70)) assert.ok(Math.abs(hinge.click_values.r71[key] - hinge.click_values.r70[key]) < 0.02, key);
  assert.ok(hinge.journal_room_above_and_below_mm.r71 > hinge.journal_room_above_and_below_mm.r70 + 0.05);
  assert.equal(hinge.journal_room_fore_and_aft_mm, 0.15);
  assert.ok(Math.max(...Object.values(hinge.journal_travel_each_way_mm)) < 0.19);
  for (const side of ['left', 'right']) assert.ok(hinge.joint_throat_mm2.r71[side] >= 0.9 * hinge.joint_throat_mm2.r70[side], side);
  assert.match(hinge.report, /not identified/);
});

test('the post ribs keep their printed first-layer size through the whole lift the clip allows', () => {
  const posts = reports.carrier.posts;
  assert.equal(posts.full_section_layers, 3);
  assert.equal(posts.full_section_height_mm, 0.6);
  assert.ok(posts.largest_lift_under_the_clip_mm + 0.15 <= posts.full_section_height_mm);
  const [first, second, third] = posts.layers;
  assert.equal(first.r70_native_mm, 3.049, 'the comparison starts from the native R70 measurement');
  for (const row of [first, second, third]) {
    assert.equal(row.r71_same_section_as_r70_first_layer, true);
    assert.equal(row.cad_mm.r71, first.cad_mm.r70);
  }
  assert.ok(second.cad_mm.r70 < first.cad_mm.r70 - 0.04, 'R70 tapered from its first layer');
  const three = posts.holes.find(row => row.hole_mm === 3);
  assert.ok(three.seated_squeeze_on_diameter_mm > 0);
  assert.equal(three.at_the_wing_stop_squeeze_on_diameter_mm, three.seated_squeeze_on_diameter_mm);
  assert.ok(Math.max(...three.r70_at_the_same_lift_expected_mm) < 0.03, 'R70 lost its grip 0.2 mm up');
  assert.ok(posts.holes.find(row => row.hole_mm === 3.1).seated_squeeze_on_diameter_mm < 0, 'a larger hole is honestly reported clear');
  assert.equal(posts.pushed_up_through_the_paddle_mm3, 0);
  assert.equal(posts.seated_in_the_paddle_mm3, 0);
  assert.ok(posts.post_above_the_board_fits_a_circle_of_mm <= 2.75);
  assert.ok(posts.unchanged_outside_ribs_and_nose_mm3 < 0.002);
  assert.ok(posts.layers.at(-1).cad_mm.r71 <= posts.layers.at(-1).cad_mm.r70 + 0.02, 'the entry end is no larger');
  assert.match(posts.source, /not been sliced/);
});

test('the spring clip presses the board down, never jams under the head and still stops a lift', () => {
  for (const side of ['Left', 'Right']) {
    const clip = reports.carrier.clips[side];
    assert.equal(clip.frame_mm.r71, 2);
    assert.equal(clip.layers.r71, 10);
    assert.equal(clip.print_height_layers, 12);
    assert.equal(clip.free_lift_under_the_clip_mm.r71, 0);
    assert.equal(clip.exported_pose.into_the_post_mm3, 0);
    assert.ok(clip.exported_pose.feet_into_the_board_model_mm3 > 0.15, 'unbent feet reach below the board top: that is the spring travel');
    assert.equal(clip.fitted_pose.into_the_post_mm3, 0);
    assert.ok(clip.fitted_pose.into_the_board_mm3 < 0.02);
    assert.ok(clip.frame_rise_to_the_ledges_mm >= 0.19 && clip.frame_rise_to_the_ledges_mm <= 0.22);
    assert.ok(clip.bearing_under_the_ledges_mm2.r71 >= 0.5 && clip.bearing_under_the_ledges_mm2.r71 > clip.bearing_under_the_ledges_mm2.with_the_r70_head);
    assert.equal(clip.pressed_flat.into_the_post_at_home_mm3, 0);
    assert.equal(clip.pressed_flat.into_the_ledges_while_sliding_on_mm3, 0);
    assert.ok(clip.pressed_flat.room_under_the_ledges_mm >= 0.18);
    assert.equal(clip.snap_throat_overlap_per_mm_of_thickness_mm3.r71, clip.snap_throat_overlap_per_mm_of_thickness_mm3.r59);
    assert.ok(clip.arm.bent_when_seated_mm > 0 && clip.arm.bent_while_pressed_flat_mm > clip.arm.bent_when_seated_mm);
    assert.ok(clip.slots.least_gap_between_arm_and_frame_mm >= 0.34 && clip.slots.clip_inside_those_spaces_mm3 === 0);
    assert.deepEqual(clip.print_layers.islands_starting_on_nothing, []);
    assert.equal(clip.print_layers.largest_overhang_beyond_0_3_mm_mm2, 0);
    assert.equal(clip.r59_clip_on_this_post.into_the_post_at_home_mm3, 0);
    assert.ok(clip.r59_clip_on_this_post.lift_before_the_ledges_mm >= 0.75, 'the flat clip remains a fallback');
    assert.match(clip.reading, /neither is a measurement/);
    assert.match(clip.press_where, /between its two feet/);
    assert.ok(clip.free_on_the_board.prong_tips_above_the_board_mm > clip.free_on_the_board.room_under_the_head_for_them_mm, 'why the rear bar is the wrong place to press');
  }
  const sweep = reports.carrier.fasteners_through_the_click;
  assert.equal(sweep.into_holder_retainer_pin_and_op1_mm3, 0);
  assert.ok(sweep.least_gap_mm.r71 >= 1);
  assert.equal(sweep.clip_plan_beyond_the_board_edge_mm2, 0);
  assert.equal(sweep.paddle_with_fasteners_lowered_into_the_holder_mm3, 0);
});

test('the spring arms bend at most half as hard as the first spring clip\'s, largest in the plain strip', () => {
  for (const side of ['Left', 'Right']) {
    const clip = reports.carrier.clips[side];
    const arm = clip.arm, first = arm.first_spring_clip;
    const said = first.loaded_at_the_middle_of_the_foot_as_first_reported;
    assert.deepEqual([said.bending_strain_while_pressed_flat, said.bending_strain_when_seated], [0.0438, 0.0219], 'the comparison reproduces the first clip\'s own report');
    assert.ok(first.loaded_at_the_heel.bending_strain_while_pressed_flat > said.bending_strain_while_pressed_flat, 'loading the heel is the stricter estimate');
    assert.ok(arm.bending_strain_while_pressed_flat <= 0.5 * said.bending_strain_while_pressed_flat);
    assert.ok(arm.bending_strain_when_seated <= 0.5 * said.bending_strain_when_seated);
    assert.ok(arm.pressed_flat_strain_over_the_first_spring_clip <= 0.4);
    assert.equal(arm.largest_strain_in_the_plain_arm, true);
    assert.equal(arm.root_steps.length, 3);
    for (const step of arm.root_steps) {
      assert.ok(step.strain_in_front_while_pressed_flat < arm.bending_strain_while_pressed_flat, `step at ${step.in_front_of_the_rear_bar_mm} mm`);
      assert.ok(Math.abs(step.thickness_mm.behind - step.thickness_mm.in_front - 0.2) < 1e-9, 'one layer at a time');
    }
    assert.ok(arm.strain_at_the_rear_bar_while_pressed_flat <= 0.5 * arm.bending_strain_while_pressed_flat);
    assert.deepEqual([arm.layers, arm.thickness_mm, arm.width_mm, arm.root_width_mm], [3, 0.6, 0.8, 1.8]);
    assert.ok(arm.sliding_friction.adds_while_pressed_flat > 0, 'the friction estimate is stated, not hidden');
    assert.ok(clip.hold_down.one_clip_over_that_weight >= 10);
    assert.ok(clip.hold_down_per_clip_n < clip.first_spring_clip.hold_down_per_clip_n && clip.press_to_fit_per_clip_n <= 5);
    assert.ok(clip.rear_bar.depth_mm.r71 > clip.rear_bar.depth_mm.first_spring_clip);
    assert.ok(clip.rear_bar.arm_root_moment_while_pressed_flat_n_mm.r71 <= 0.5 * clip.rear_bar.arm_root_moment_while_pressed_flat_n_mm.first_spring_clip);
    assert.match(clip.hold_down.reading, /assumption, not a weighing/);
    assert.match(arm.method, /bending only/);
    assert.deepEqual(clip.size_mm, [5.9, 8.2, 2.4]);
  }
});

test('nine pieces, and every base fin has one neck, beside the holder, weaker than its plate end', () => {
  const base = reports.base;
  assert.deepEqual([...base.pieces.r71].sort(), kit);
  const fins = base.holder_base.r71.fins;
  assert.equal(fins.length, 5);
  for (const fin of fins) {
    assert.equal(fin.at_the_plate_mm2, fin.full_section_mm2, `${fin.face} ${fin.at_x_mm}: full width at the plate`);
    assert.ok(fin.at_the_holder_mm2 <= 0.75 * fin.at_the_plate_mm2, `${fin.face} ${fin.at_x_mm}: the holder neck is the weak point`);
  }
  assert.equal(base.holder_base.r70.fins.filter(fin => fin.at_the_holder_mm2 === fin.full_section_mm2).length, 3, 'the check must reproduce the full-width R70 joins');
  for (const row of base.necks) {
    assert.equal(row.necks.length, 1);
    assert.equal(row.necks[0].end, 'holder');
    assert.ok(row.necks[0].from_holder_face_mm[1] <= 0.5, 'what can stay on the holder is short');
  }
  assert.match(base.break_order[0], /beside the holder/);
  assert.ok(Math.min(...base.plastic_behind_each_fin.r71.map(row => row.least_plastic_behind_the_fin_mm)) >= 1.6);
  assert.ok(base.holder_base.r71.weakest_path_mm2 >= 0.9 * base.holder_base.r70.weakest_path_mm2);
  assert.equal(base.holder_base.r71.weakest_path_mm2, base.holder_base.r71.total_at_the_holder_mm2);
  assert.equal(base.holder_base.r71.first_layer_pieces, 1);
  assert.equal(base.holder_base.r71.base_volume_in_hinge_bay_mm3, 0);
  assert.equal(base.sliced, false);
});

test('the guide ships nine parts, moves only the battery and re-bases only the clips', () => {
  assert.equal(guide.revision, 'R71');
  assert.equal(guide.physical_fit_verified, false);
  assert.deepEqual([...guide.print_components.keys].sort(), kit);
  for (const [path, expected] of Object.entries(guide.sources.meshes_sha256)) assert.equal(sha(path), expected, path);
  assert.equal(guide.sources.battery_report_sha256, sha('battery.json'));
  const actors = guide.modules.pin_hinge.actors;
  assert.equal(actors.carrier.file, 'Key_Carrier-assembly.stl');
  assert.equal(actors.cap.file, 'Touch_Paddle-assembly.stl');
  assert.equal(actors.post_bar.file, 'DFR_Post_Bar-assembly.stl');
  assert.equal(actors.lid.file, 'OP1_Lid_Stop-assembly.stl');
  assert.equal(actors.clip_left.file, 'DFR_Clip_Left-assembly.stl');
  assert.equal(actors.clip_right.file, 'DFR_Clip_Right-assembly.stl');
  const shift = guide.r71_changes.battery_moved_mm;
  assert.deepEqual(shift, [-6.2, -12.45, -3.05]);
  let moved = 0, rebased = 0;
  for (const [id, module] of Object.entries(guide.modules)) {
    assert.deepEqual(Object.keys(module.actors), Object.keys(r70Guide.modules[id].actors), id);
    const before = Object.fromEntries(r70Guide.modules[id].steps.map(step => [step.title, step]));
    assert.equal(module.steps.length, r70Guide.modules[id].steps.length, id);
    for (const step of module.steps) {
      step.samples.forEach((sample, i) => {
        const old = before[step.title].samples[i];
        for (const [actor, pose] of Object.entries(sample)) {
          if (actor === 'morphs') continue;
          const clip = actor === 'clip_left' || actor === 'clip_right';
          pose.forEach((value, j) => {
            const axis = j % 4 === 3 ? (j - 3) / 4 : -1;
            let expected = old[actor][j];
            if (actor === 'battery' && axis >= 0) expected += shift[axis];
            if (clip && axis >= 0) expected += old[actor][axis * 4 + 1] * -3.55;        // R59's guide clip was its assembly clip moved -3.55 mm along Y
            assert.ok(Math.abs(value - expected) < 1e-4, `${id} / ${step.title} / ${actor} / ${j}`);
          });
          moved += actor === 'battery' ? 1 : 0;
          rebased += clip ? 1 : 0;
        }
      });
    }
  }
  assert.equal(moved, guide.r71_changes.battery_poses_moved);
  assert.equal(rebased, guide.r71_changes.clip_poses_rebased);
  assert.ok(moved > 100 && rebased > 100);
  const seat = guide.modules.battery.steps[0].samples.at(-1).battery;
  assert.deepEqual([seat[3], seat[7], seat[11]], shift, 'the battery ends at its checked seat');
  const start = guide.modules.battery.steps[0].samples[0].battery;
  assert.ok(Math.abs(start[7] - seat[7] - guide.r71_changes.battery_slide_mm) < 1e-6);
});

test('the guide says how the battery goes in and comes out, and no word claims a fit', () => {
  const words = Object.values(guide.modules).flatMap(module => [module.note ?? '', ...module.steps.map(step => step.caption ?? '')]).join(' ');
  assert.match(words, /Fit the battery last/);
  assert.match(words, /Do not pull it by the leads/);
  assert.match(words, /Press down on the front half of the clip, between its two feet/);
  assert.match(words, /Do not press on the rear bar/);
  assert.match(words, /Press each clip down between its two feet and slide it back/);
  assert.equal(guide.modules.pin_hinge.actors.post_bar.label, 'Two-post bar with a third ledge under each head');
  assert.equal(guide.r71_changes.clip_spring.arms_bent_when_fitted_mm, 0.2);
  assert.equal(guide.r71_changes.clip_spring.drawn, 'arms unbent');
  assert.equal(guide.r71_changes.clip_spring.arms_bent_while_pressed_flat_mm, 0.4);
  assert.match(guide.r71_changes.clip_spring.press, /between the two feet/);
  assert.doesNotMatch(words, /13 mm of it stays behind|whether/i);
  for (const module of Object.values(guide.modules)) if (module.status) assert.equal(module.status, 'R71 design · physical fit untested');
});

test('R71 carries every installed actor and lead shape continuously between steps', () => {
  for (const [id, {steps, actors}] of Object.entries(guide.modules)) {
    for (let i = 1; i < steps.length; i++) {
      const end = steps[i - 1].samples.at(-1), start = steps[i].samples[0];
      for (const actor of Object.keys(actors)) {
        if (actor in start && actor in end) {
          assert.ok(start[actor].every((value, j) => Math.abs(value - end[actor][j]) < 1e-5), `${id} / ${steps[i].title} / ${actor}`);
        }
        if (start.morphs?.[actor] !== undefined && end.morphs?.[actor] !== undefined) {
          assert.equal(start.morphs[actor], end.morphs[actor], `${id} / ${steps[i].title} / morph ${actor}`);
        }
      }
    }
  }
});

test('the grouped viewer composes R71 and keeps its guide available after later revisions', () => {
  const components = assemblyComponents(guide, true);
  assert.ok(components.keys && components.whole);
  const catalog = JSON.parse(readFileSync(new URL('../hardware/carbon-rod-holders/assembly/catalog.json', import.meta.url)));
  const r71 = catalog.versions.find(version => version.id === 'r71');
  assert.equal(r71?.guide, '../../carbon-rod-holders-r71-contained-battery/exports/assembly-guide.json');
  assert.ok(catalog.versions.some(version => version.id === 'r70'), 'R70 stays available');
});
