// Check the R70 exported assembly and CAD receipts with node --test. — Claude Fable 5.2
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide, assemblyComponents} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const files = new URL('../hardware/carbon-rod-holders-r70-short-holder/exports/', import.meta.url);
const r69Files = new URL('../hardware/carbon-rod-holders-r69-snug-rod-clean-op1/exports/', import.meta.url);
const bytes = (path, base = files) => readFileSync(new URL(path, base));
const load = (path, base = files) => JSON.parse(bytes(path, base));
const sha = (path, base = files) => createHash('sha256').update(bytes(path, base)).digest('hex');
const guide = validateGuide(load('assembly-guide.json'));
const r69Guide = load('assembly-guide.json', r69Files);
const names = ['hinge', 'short', 'battery', 'keys', 'posts', 'edges', 'base', 'carrier'];
const reports = Object.fromEntries(names.map(name => [name, load(name + '.json')]));
const meshes = ['Key_Carrier-assembly.stl', 'Touch_Paddle-assembly.stl', 'DFR_Post_Bar-assembly.stl', 'Gravity_Wires-assembly.stl',
  'OP1_Lid_Stop-assembly.stl'];
const kit = ['Key_Carrier', 'Touch_Paddle', 'Hinge_Pin', 'Pin_Clip', 'Pin_Clip_Spare', 'OP1_Lid_Stop', 'DFR_Post_Bar', 'DFR_Clip_Left',
  'DFR_Clip_Right'].sort();
const optional = ['Hinge_Pin_Snug', 'Socket_Backer_Left', 'Socket_Backer_Right'];

test('every R70 report measured the exported meshes and passes; nothing claims a slice or a fit', () => {
  for (const [name, report] of Object.entries(reports)) {
    for (const mesh of meshes) assert.equal(report.meshes_sha256[mesh], sha(mesh), `${name} ${mesh}`);
    assert.equal(report.passes, true, name);
    assert.ok(report.gates.every(Boolean), name);
    assert.equal(report.physical_fit_verified, false, name);
  }
  const summary = load('checks.json');
  assert.equal(summary.passes, true);
  assert.equal(summary.sliced, false);
  const source = load('source-reproduction.json');
  for (const mesh of meshes) assert.equal(source.meshes[mesh].reproduced_sha256, sha(mesh), mesh);
  assert.notEqual(sha('Key_Carrier-assembly.stl'), sha('Key_Carrier-assembly.stl', r69Files));
  assert.equal(reports.carrier.r69_carrier_sha256, sha('Key_Carrier-assembly.stl', r69Files));
  assert.equal(sha('OP1_Lid_Stop-assembly.stl'), sha('OP1_Lid_Stop-assembly.stl', r69Files), 'the retainer is the fitted R69 file');
  assert.equal(sha('Gravity_Wires-assembly.stl'), sha('Gravity_Wires-assembly.stl', r69Files));
});

test('the holder ends 4.15 mm behind the pin line on plain bearing blocks, with the same rod rings', () => {
  const short = reports.short;
  assert.equal(short.rear_face_y_mm.r69, 43.65);
  assert.equal(short.rear_face_y_mm.r70, 36.45);
  assert.ok(Math.abs(short.behind_the_pin_line_mm.r70 - 4.15) < 0.01 && short.behind_the_pin_line_mm.r69 > 11);
  assert.ok(Math.abs(short.holder_length_and_print_height_mm.r69 - short.holder_length_and_print_height_mm.r70 - 7.20) < 0.01);
  for (const side of ['left', 'right']) {
    const now = short.bearing_blocks.r70[side], then = short.bearing_blocks.r69[side];
    assert.ok(now.on_the_rear_face_mm2 > 3 * then.on_the_rear_face_mm2, side);
    assert.equal(now.top_z_mm, then.top_z_mm);
  }
  assert.ok(short.bearing_blocks.wall_behind_each_open_bearing_mm >= 0.8);
  for (const ring of ['front_ring', 'saddle', 'rear_ring', 'behind']) {
    assert.deepEqual(short.rod.zones[ring].r70.bore_diameter_mm, short.rod.zones[ring].r69.bore_diameter_mm, ring);
  }
  assert.ok(short.rod.rear_face_bore_mm.r70 >= 9);
  assert.ok(Math.abs(short.rod.nominal_8mm_rod_overlap_mm3.r70 - short.rod.nominal_8mm_rod_overlap_mm3.r69) < 0.02);
});

test('the click is the fitted R69 click and the arm-to-barrel joints are stronger', () => {
  const {click_values: values, joints, far_end_press: press, click} = reports.hinge;
  for (const key of Object.keys(values.r69)) assert.ok(Math.abs(values.r70[key] - values.r69[key]) < 0.02, key);
  for (const side of ['left', 'right']) assert.ok(joints.throat_mm2.r70[side] >= 1.3 * joints.throat_mm2.r69[side], side);
  assert.ok(joints.added_in_the_joint_zone_mm3 > 15 && Math.abs(joints.change_outside_the_joint_zone_mm3) < 0.02);
  for (const part of ['plug', 'housing', 'leads']) {
    assert.ok(joints.gaps_to_fitted_parts_mm.r70[part] >= joints.gaps_to_fitted_parts_mm.r69[part] - 0.005, part);
  }
  assert.equal(press.max_overlap_with_retainer_mm3, 0);
  assert.ok(press.least_gap_to_retainer_mm >= 0.15);
  assert.ok(Object.values(click.overlap_mm3).every(v => v < 0.012));
  assert.equal(click.paddle_layer_backing.unsupported_new_sections.length, 0);
  assert.deepEqual(reports.hinge.common_straight_pin_diameter_mm.r70, reports.hinge.common_straight_pin_diameter_mm.r69);
});

test('the pouch keeps its place, stands 12.45 mm out and the rebuilt spring is as stiff', () => {
  const {seat, spring} = reports.battery;
  assert.equal(seat.r70.pouch_behind_the_rear_face_mm, 12.45);
  assert.equal(seat.r69.pouch_behind_the_rear_face_mm, 5.25);
  assert.ok(seat.r70.seated_overlap_with_the_spring_mm3 > 0 && seat.r70.seated_overlap_without_the_spring_mm3 < 0.01);
  assert.ok(seat.r70.slide_in_from_the_rear_without_the_spring_mm3 < 0.01);
  assert.ok(spring.stiffness_r70_over_r69 > 0.9 && spring.stiffness_r70_over_r69 < 1.1);
  assert.equal(spring.preload_mm, 0.21);
  assert.ok(reports.battery.rail_sections_in_front_of_the_new_rear_face_against_r69.max_area_mm2 < 0.01);
  assert.match(reports.battery.cover, /^none/);
});

test('the right upper key is 2 mm nearer, every key route is clear, and the left key is honestly unmoved', () => {
  const keys = reports.keys;
  assert.equal(keys.right_key_shift_mm, 2);
  assert.equal(keys.key_poses_checked, 336);
  assert.deepEqual(keys.key_obstructions, []);
  assert.ok(Math.max(...Object.values(keys.fitted_switches_and_sockets_to_holder_mm3)) < 0.01);
  assert.ok(Math.max(...Object.values(keys.socket_backer_sweeps_mm3)) < 0.01);
  const rows = keys.row_distance_centre_to_centre_mm;
  assert.ok(Math.abs(rows.right.r69 - rows.right.r70 - 2) < 0.01);
  assert.equal(rows.left.r70, rows.left.r69);
  assert.ok(keys.gap_between_cap_travel_envelopes_mm.right.r70 >= 0.5);
  assert.ok(keys.left_key.largest_free_shift_tested_mm < 0.5, 'the check must show what stops the left key');
  assert.ok(keys.left_key.rows.at(-1).into_fixed_plastic_mm3 > 0.5);
  const kept = keys.kept_in_place;
  assert.ok(kept.right_guard_arm_root_on_the_deck_mm2.r70 >= kept.right_guard_arm_root_on_the_deck_mm2.r69 - 0.05);
  assert.ok(Math.abs(kept.plastic_inside_the_op1_connector_window_mm3.r70 - kept.plastic_inside_the_op1_connector_window_mm3.r69) < 0.01);
  assert.ok(kept.plug_margin_on_the_r69_route_mm.r70 >= kept.plug_margin_on_the_r69_route_mm.r69 - 0.02);
  assert.ok(Object.values(kept.seated_op1_hardware_to_holder_mm3).every(v => v < 0.01));
});

test('the posts grip a 3.0 mm hole, allow a small crest squeeze in a 3.2 mm CAD hole and are otherwise the R57 bar', () => {
  const posts = reports.posts;
  const [three, , wide] = posts.fit_by_hole_diameter.map(row => row.rib_interference_at_seat_mid_top_mm);
  assert.ok(three[0] > 0.05 && three[0] < 0.3 && three[2] < 0, 'a lead-in at the board top, a grip at the seat');
  assert.ok(Math.abs(wide[0]) <= 0.05);
  assert.equal(posts.through_the_paddle_holes_mm3, 0);
  assert.ok(posts.bar_outside_the_board_thickness_against_r57_mm3 < 0.002);
  for (const side of ['Left', 'Right']) assert.equal(posts.clips_on_the_posts_mm3[side].r70, posts.clips_on_the_posts_mm3[side].r57);
  assert.equal(posts.fit_by_hole_pitch_at_the_seat.length, 6, 'the pitch table states what a 15 or 16 mm board would do');
  assert.match(posts.not_measured, /hole diameter and pitch/);
});

test('the lower edge of both key banks is round where R69 was square', () => {
  const {lower_edge: lower, upper_edge: upper} = reports.edges;
  assert.ok(lower.r69.round_share < 0.1, 'the check must reproduce the square R69 edge');
  assert.ok(lower.r70.round_share >= 0.8);
  assert.deepEqual(lower.r70.square, []);
  assert.deepEqual(upper.r70.square, []);
  assert.ok(upper.r70.round_share > upper.r69.round_share);
  assert.ok(lower.r70.stations > 80);
  assert.ok(Math.abs(reports.edges.removed_further_than_the_radius_from_the_outline_mm3) < 0.02);
  assert.ok(reports.edges.crest_highest_z_mm.r70 < reports.edges.crest_highest_z_mm.r69 - 0.3);
});

test('nine pieces, and no base fin is rooted in thin plastic', () => {
  const base = reports.base;
  assert.deepEqual([...base.pieces.r70].sort(), kit);
  assert.deepEqual(base.pieces.no_longer_printed, optional);
  const least = rev => Math.min(...base.plastic_behind_each_fin[rev].map(row => row.least_plastic_behind_the_fin_mm));
  assert.ok(least('r69') < 1.3, 'the check must reproduce the R69 fins on the battery roof');
  assert.ok(least('r70') >= 1.6);
  const fins = base.holder_base.r70.fins;
  assert.equal(fins.length, 5);
  assert.equal(fins.filter(fin => fin.necked).length, 2);
  for (const fin of fins.filter(fin => fin.necked)) assert.ok(Math.abs(fin.at_x_mm + 23.1) < 0.01 && fin.weakest_section_mm2 < fin.full_section_mm2);
  assert.ok(base.holder_base.r70.holder_first_layer_mm2 > base.holder_base.r69.holder_first_layer_mm2);
  assert.equal(base.holder_base.r70.base_volume_in_hinge_bay_mm3, 0);
  assert.equal(base.sliced, false);
});

test('everything outside the changed zones is R69, and the kit uses less plastic', () => {
  const carrier = reports.carrier;
  for (const [zone, row] of Object.entries(carrier.unchanged_zones_sections_against_r69)) assert.ok(row.max_area_mm2 < 0.01, zone);
  assert.equal(carrier.components, 1);
  assert.ok(carrier.mass_total_g.r70 < carrier.mass_total_g.r69);
});

test('the guide ships nine parts, moves only the right upper key and drops the backing-strip steps', () => {
  assert.equal(guide.revision, 'R70');
  assert.equal(guide.physical_fit_verified, false);
  assert.deepEqual([...guide.print_components.keys].sort(), kit);
  assert.deepEqual([...guide.optional_components.keys].sort(), optional);
  for (const [path, expected] of Object.entries(guide.sources.meshes_sha256)) assert.equal(sha(path), expected, path);
  for (const module of Object.values(guide.modules)) {
    assert.ok(!('left_backer' in module.actors));
    assert.ok(!module.steps.some(step => /backing strip|outside-facing socket/.test(step.title)));
  }
  const actors = guide.modules.pin_hinge.actors;
  assert.equal(actors.carrier.file, 'Key_Carrier-assembly.stl');
  assert.equal(actors.cap.file, 'Touch_Paddle-assembly.stl');
  assert.equal(actors.post_bar.file, 'DFR_Post_Bar-assembly.stl');
  assert.equal(actors.lid.file, 'OP1_Lid_Stop-assembly.stl');
  let moved = 0;
  for (const [id, module] of Object.entries(guide.modules)) {
    const before = Object.fromEntries(r69Guide.modules[id].steps.map(step => [step.title, step]));
    for (const step of module.steps) {
      step.samples.forEach((sample, i) => {
        const old = before[step.title].samples[i];
        for (const [actor, pose] of Object.entries(sample)) {
          if (actor === 'morphs') continue;
          const shift = ['socket_4', 'switch_4'].includes(actor) ? -2 : 0;
          pose.forEach((value, j) => assert.ok(Math.abs(value - old[actor][j] - (j === 7 ? shift : 0)) < 1e-5, `${id} / ${step.title} / ${actor}`));
          moved += shift ? 1 : 0;
        }
      });
    }
  }
  assert.equal(moved, guide.r70_changes.poses_moved);
  assert.ok(moved > 100);
  assert.equal(guide.r70_changes.left_upper_key_moved, false);
});

test('R70 carries every installed actor and lead shape continuously between steps', () => {
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

test('the grouped viewer composes the integral rod grip without obsolete collet steps', () => {
  const components = assemblyComponents(guide, true);
  assert.ok(components.keys && components.whole);
  const whole = components.whole.views.whole;
  assert.ok(whole.steps.length > guide.modules.whole.steps.length);
  assert.ok(!whole.steps.some(step => /Clip the grip|Seat the rod grip/.test(step.title)));
});
