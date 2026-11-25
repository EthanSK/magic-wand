// Check the R69 exported assembly and fit receipts with node --test. — GPT-6.1 Sol
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const files = new URL('../hardware/carbon-rod-holders-r69-snug-rod-clean-op1/exports/', import.meta.url);
const r68Files = new URL('../hardware/carbon-rod-holders-r68-pre-taper-battery-rail/exports/', import.meta.url);
const bytes = (path, base = files) => readFileSync(new URL(path, base));
const load = (path, base = files) => JSON.parse(bytes(path, base));
const sha = (path, base = files) => createHash('sha256').update(bytes(path, base)).digest('hex');
const guide = validateGuide(load('assembly-guide.json'));
const r68Guide = load('assembly-guide.json', r68Files);
const names = ['hinge', 'keeper', 'op1', 'rod', 'carrier'];
const reports = Object.fromEntries(names.map(name => [name, load(name + '.json')]));
const meshes = ['Key_Carrier-assembly.stl', 'Touch_Paddle-assembly.stl', 'OP1_Lid_Stop-assembly.stl', 'Gravity_Wires-assembly.stl'];

test('every R69 report measured the exported meshes and passes', () => {
  for (const [name, report] of Object.entries(reports)) {
    for (const mesh of meshes) assert.equal(report.meshes_sha256[mesh], sha(mesh), `${name} ${mesh}`);
    assert.equal(report.passes, true, name);
    assert.ok(report.gates.every(Boolean), name);
    assert.equal(report.physical_fit_verified, false, name);
  }
  assert.equal(load('checks.json').passes, true);
  const source = load('source-reproduction.json');
  for (const mesh of meshes) assert.equal(source.meshes[mesh].reproduced_sha256, sha(mesh), mesh);
  assert.notEqual(sha('Key_Carrier-assembly.stl'), sha('Key_Carrier-assembly.stl', r68Files));
  assert.equal(reports.carrier.r68_carrier_sha256, sha('Key_Carrier-assembly.stl', r68Files));
});

test('the hinge sits closer to the touch board and the rear web is gone', () => {
  const {r68, r69, barrel_print_bridge: bridge, click} = reports.hinge;
  for (const key of ['edge_to_barrel_front_mm', 'edge_to_pin_axis_mm', 'edge_to_paddle_rear_end_mm', 'edge_to_cheek_block_rear_mm']) {
    assert.ok(r69[key] < r68[key] - 1, key);
  }
  assert.ok(r68.edge_to_paddle_rear_end_mm > 10 && r69.edge_to_paddle_rear_end_mm < 10);
  assert.ok(r69.edge_to_nominal_lead_rear_mm < 10);
  assert.ok(r69.mated_plug_to_paddle_gap_mm > 0.35);
  assert.equal(bridge.rear_web_volume_mm3, 0);
  assert.ok(bridge.span_mm <= 8 && bridge.posts_on_bed === 2);
  assert.equal(reports.hinge.holder_length_changed, false);
  assert.ok(click.button_contact_deg > 0 && click.button_contact_deg < click.case_stop_deg);
  assert.ok(click.plunger_travel_at_case_mm > click.lowest_operating_point_travel_mm);
  assert.ok(Object.values(click.overlap_mm3).every(v => v < 0.012));
  assert.equal(click.paddle_layer_backing.unsupported_new_sections.length, 0);
});

test('a far-end press that touches the R68 retainer clears the R69 one', () => {
  const {far_end_press: press, rest, hook, retention} = reports.keeper;
  assert.ok(press.r68.max_overlap_with_retainer_mm3 > 0, 'the check must reproduce the R68 fault');
  assert.equal(press.r69.max_overlap_with_retainer_mm3, 0);
  assert.ok(press.r69.least_gap_to_retainer_mm >= 0.15);
  assert.ok(press.r69.max_overlap_with_carrier_and_board_mm3 < 0.001);
  for (const side of ['left', 'right']) {
    assert.ok(rest.r69[side].room_mm >= rest.r68[side].room_mm + 1.2, side);
    assert.ok(rest.r69[side].room_mm > reports.keeper.travel_at_posts_full_stroke_mm + 1.2, side);
  }
  assert.equal(rest.r69.left.room_mm, rest.r69.right.room_mm);
  assert.ok(hook.post_top_z_mm < hook.r59_tower_top_z_mm - 1.2);
  assert.ok(hook.lip_over_foot_mm > hook.r59_lip_over_flange_mm && hook.lip_to_leg_face_mm >= 0.6);
  assert.ok(hook.lift_stop_deg > 0.5 && hook.lift_stop_deg < 1.6);
  assert.equal(retention.retainer_pieces, 1);
  for (const side of ['left', 'right']) {
    const section = retention.tine_sections.r69[side];
    assert.ok(section.samples[0].v_mm <= -4.5 && section.samples.at(-1).v_mm >= 2,
      'measure the complete notch, including the short necks outside the posts');
    assert.ok(section.minimum_area_mm2 >= retention.tine_sections.r59[side].minimum_area_mm2 * 0.95,
      'the lowered keeper must not restore the thin-neck regression');
  }
});

test('the OP1 seat has three simple holes and one window, and the plug has more room', () => {
  const op1 = reports.op1;
  const openings = op1.seat_openings_inside_board_outline;
  const small = rows => rows.filter(row => row.area_mm2 < 12).length;
  assert.equal(openings.r69.length, 4);
  assert.equal(small(openings.r69), 3);
  assert.ok(small(openings.r68) < 3, 'R68 had a locator pocket joined to a socket hole');
  const plug = op1.largest_plug_margin_per_side;
  assert.ok(plug.r69.margin_mm >= plug.r68.margin_mm + 0.5);
  const room = op1.room_outboard_of_plug_path_mm;
  for (const z of ['z0.5', 'z1.5', 'z2.5', 'z3.5']) assert.ok(room.r69[z] >= room.r68[z] + 2, z);
  const seat = op1.seat_support_mm2['z9.3'];
  assert.ok(seat.r69.whole > seat.r68.whole);
  for (const zone of ['switch_left', 'switch_right', 'plunger']) assert.ok(seat.r69[zone] >= seat.r68[zone] - 0.5, zone);
  op1.three_holes.r69.forEach((hole, i) => assert.ok(hole['z8.3'].clear_radius >= op1.three_holes.r68[i]['z8.3'].clear_radius - 0.01));
  assert.ok(Object.values(op1.seated_hardware_to_carrier_mm3).every(v => v < 0.01));
  assert.ok(op1.guard_arm.old_arm_left_below_deck_mm3 < 0.01 && op1.guard_arm.new_arm_core_missing_mm3 < 0.05);
});

test('the rod bore is R62\'s grip up to the rear ring and stays open at the bed face', () => {
  const {zones} = reports.rod;
  for (const ring of ['front_ring', 'rear_ring']) {
    zones[ring].r69.bore_diameter_mm.forEach((v, i) => assert.ok(Math.abs(v - zones[ring].r62.bore_diameter_mm[i]) < 0.01, ring));
    assert.ok(zones[ring].r68.bore_diameter_mm[0] > zones[ring].r69.bore_diameter_mm[0] + 0.5, ring);
  }
  assert.ok(reports.rod.r58_to_r62_radius_difference_mm < 0.02);
  assert.ok(reports.rod.r69_to_r62_radius_difference_to_y31_75_mm < 0.02);
  assert.ok(zones.behind.r69.bore_diameter_mm[0] > zones.behind.r62.bore_diameter_mm[0]);
  assert.ok(reports.rod.bed_face_bore_mm >= 9);
  const overlap = reports.rod.nominal_8mm_rod_overlap_mm3;
  assert.equal(overlap.r68, 0);
  assert.ok(Math.abs(overlap.r69 - overlap.r62) < 0.1);
});

test('key deck windows are closed and everything outside the changed zones is R68', () => {
  const carrier = reports.carrier;
  for (const side of ['left', 'right']) {
    assert.ok(carrier.key_deck.strips[side].r68_open_mm3 > 5 && carrier.key_deck.strips[side].r69_open_mm3 < 0.01, side);
  }
  assert.equal(carrier.key_poses_checked, 336);
  assert.deepEqual(carrier.key_obstructions, []);
  assert.ok(Math.max(...Object.values(carrier.socket_backer_sweeps_mm3)) < 0.01);
  assert.ok(carrier.battery_box_sections_against_r68.max_area_mm2 < 0.0025);
  assert.ok(carrier.outside_changed_zones_sections_against_r68.max_area_mm2 < 0.01);
  assert.equal(carrier.components, 1);
  assert.ok(carrier.mass_total_g.r69 < carrier.mass_total_g.r68);
});

test('the guide ships twelve parts, no collet, and carries the hinge move', () => {
  const kit = ['Key_Carrier', 'Touch_Paddle', 'Hinge_Pin', 'Hinge_Pin_Snug', 'Pin_Clip', 'Pin_Clip_Spare', 'OP1_Lid_Stop',
    'DFR_Post_Bar', 'DFR_Clip_Left', 'DFR_Clip_Right', 'Socket_Backer_Left', 'Socket_Backer_Right'];
  assert.equal(guide.revision, 'R69');
  assert.equal(guide.physical_fit_verified, false);
  assert.deepEqual([...guide.print_components.keys].sort(), kit.sort());
  for (const [path, expected] of Object.entries(guide.sources.meshes_sha256)) assert.equal(sha(path), expected, path);
  for (const module of Object.values(guide.modules)) {
    assert.ok(!('rod_collet' in module.actors));
    assert.ok(!module.steps.some(step => /rod grip|Clip the grip/.test(step.title)));
  }
  const actors = guide.modules.pin_hinge.actors;
  assert.equal(actors.carrier.file, 'Key_Carrier-assembly.stl');
  assert.equal(actors.cap.file, 'Touch_Paddle-assembly.stl');
  assert.equal(actors.lid.file, 'OP1_Lid_Stop-assembly.stl');
  assert.equal(actors.sensor_lead.file, 'Gravity_Wires-assembly.stl');
  // The pin sits 1.3 mm nearer the board in every sampled pose; the holder does not move. — Claude Fable 5.2
  const step = title => (g => g.modules.pin_hinge.steps.find(s => s.title === title));
  const seated = step('Press in the pin clip');
  const before = seated(r68Guide).samples.at(-1), after = seated(guide).samples.at(-1);
  assert.ok(Math.abs((after.hinge_pin[7] - before.hinge_pin[7]) - guide.sources.hinge_shift_mm[1]) < 1e-6);
  assert.deepEqual(after.carrier, before.carrier);
  assert.ok(guide.sources.hinge_shift_mm[1] < -1);
  const tried = guide.sources.plug_line.holder_overlap_tried_mm3;
  assert.ok(tried[String(guide.sources.plug_line.turn_about_new_line_deg.toFixed(1))] < 0.001);
});

test('R69 carries every installed actor and lead shape continuously between steps', () => {
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
