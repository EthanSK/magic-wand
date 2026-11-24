import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const files = new URL('../hardware/carbon-rod-holders-r67-diagonal-battery-corner/exports/', import.meta.url);
const r66Files = new URL('../hardware/carbon-rod-holders-r66-three-hole-op1/exports/', import.meta.url);
const bytes = (path, base = files) => readFileSync(new URL(path, base));
const load = (path, base = files) => JSON.parse(bytes(path, base));
const sha = (path, base = files) => createHash('sha256').update(bytes(path, base)).digest('hex');
const guide = validateGuide(load('assembly-guide.json'));
const r66Guide = load('assembly-guide.json', r66Files);
const reports = Object.fromEntries(['subtraction', 'battery', 'saddle', 'op1-route', 'carrier']
  .map(name => [name, load(name + '.json')]));

test('R67 ships the complete 13-piece kit with hash-bound meshes', () => {
  const names = ['Key_Carrier', 'Touch_Paddle', 'Rod_Collet', 'Hinge_Pin', 'Hinge_Pin_Snug', 'Pin_Clip',
    'Pin_Clip_Spare', 'OP1_Lid_Stop', 'DFR_Post_Bar', 'DFR_Clip_Left', 'DFR_Clip_Right',
    'Socket_Backer_Left', 'Socket_Backer_Right'];
  assert.equal(guide.revision, 'R67');
  assert.equal(guide.physical_fit_verified, false);
  assert.deepEqual([...guide.print_components.keys].sort(), names.sort());
  for (const [path, expected] of Object.entries(guide.sources.meshes_sha256)) assert.equal(sha(path), expected, path);
  assert.equal(guide.sources.meshes_sha256['Key_Carrier-assembly.stl'], sha('Key_Carrier-assembly.stl'));
  assert.equal(guide.sources.route_report_sha256, sha('op1-route.json'));
});

test('every CAD report checks this exact carrier, made only by removing three regions from R66', () => {
  const carrier = sha('Key_Carrier-assembly.stl');
  for (const [name, report] of Object.entries(reports)) {
    assert.equal(report.carrier_sha256, carrier, name);
    assert.equal(report.passes, true, name);
    assert.equal(report.physical_fit_verified, false, name);
  }
  assert.equal(load('click-fit.json').carrier_sha256, carrier);
  const sub = reports.subtraction;
  assert.equal(sub.r66_carrier_sha256, sha('Key_Carrier-assembly.stl', r66Files));
  assert.deepEqual(Object.keys(sub.removed_from_r66_mm3).sort(), ['battery_corner', 'plug_lead_in', 'saddle_stubs']);
  const removed = Object.values(sub.removed_from_r66_mm3).reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(sub.volume_mm3.difference - removed) < 0.01);
  assert.ok(sub.sections_against_r66_minus_cutters.max_area_mm2 < 0.0025);
  assert.equal(sub.components, 1);
  assert.equal(reports.carrier.key_poses_checked, 336);
  assert.deepEqual(reports.carrier.key_obstructions, []);
});

test('the battery corner is a diagonal; the leaf, the post front and the pouch side are unchanged', () => {
  const corner = reports.battery.diagonal_corner;
  const edge = corner.outboard_edge_x_mm;
  assert.equal(edge.y38.r67, edge.y38.r66);
  assert.equal(edge.y40.r67, edge.y40.r66);
  assert.ok(edge.y41.r67 > edge.y41.r66 && edge.y42.r67 > edge.y41.r67 && edge.y43.r67 > edge.y42.r67);
  assert.ok(edge['y43.6'].r67 > -22.7 && edge['y43.6'].r66 < -24.3);
  assert.equal(corner.root_post_front_to_y40_mm3.r67, corner.root_post_front_to_y40_mm3.r66);
  assert.equal(corner.pouch_side_of_post_mm3.r67, corner.pouch_side_of_post_mm3.r66);
  assert.ok(corner.print_overhang_from_vertical_deg <= 35);
  assert.ok(reports.battery.spring_leaf_and_shoe_unchanged_xor_mm3 < 0.01);
  assert.equal(reports.battery.pack_slide_from_rear_to_carrier_outside_spring_mm3, 0);
});

test('the three free stubs beside the front saddle are gone and nothing round them changed', () => {
  const saddle = reports.saddle;
  assert.equal(saddle.stub_in_r66.length, 1);
  assert.ok(saddle.stub_in_r66[0].touches_only_saddle_face);
  assert.deepEqual(saddle.history.R59, []);
  for (const rev of ['R60', 'R63', 'R64', 'R66']) assert.equal(saddle.history[rev].length, 1, rev);
  assert.ok(!saddle.pieces_in_box.r67.some(([volume, free]) => free && volume > 0.6));
  for (const [name, [before, after]] of Object.entries(saddle.unchanged_mm3)) assert.ok(Math.abs(before - after) < 0.002, name);
});

test('the OP1 opening keeps R66 above its underside lead-in', () => {
  const route = reports['op1-route'];
  const lead = route.lead_in;
  assert.ok(lead.removed_max_z_mm <= lead.top_z_mm + 0.01 && lead.top_z_mm < lead.board_seat_z_mm - 0.9);
  assert.deepEqual(lead.stops.r67, lead.stops.r66);
  for (const z of Object.keys(lead.seat_support_mm2)) assert.deepEqual(lead.seat_support_mm2[z].r67, lead.seat_support_mm2[z].r66);
  lead.three_holes.r67.forEach((hole, i) => assert.deepEqual(hole['z8.3'], lead.three_holes.r66[i]['z8.3']));
  assert.equal(route.deck_change_from_r63_in_op1_zone_mm3.added, 0);
  assert.ok(route.not_feasible.mated_board_from_above.closed_ring_heights_mm.length > 0);
  assert.ok(route.not_feasible.plug_pushed_up_into_seated_housing.straight_up_overlap_with_full_rod_mm3 > 0);
  assert.ok(route.approach_below_deck.narrowest_mm > 3.1);
});

test('the guide plays R66 motions unchanged with the R67 carrier', () => {
  assert.deepEqual(Object.keys(guide.modules).sort(), Object.keys(r66Guide.modules).sort());
  for (const [id, module] of Object.entries(guide.modules)) {
    const before = r66Guide.modules[id];
    assert.deepEqual(module.steps.map(s => s.title), before.steps.map(s => s.title), id);
    module.steps.forEach((step, i) => assert.deepEqual(step.samples, before.steps[i].samples, id + ' / ' + step.title));
    assert.equal(module.actors.carrier?.file ?? 'Key_Carrier-assembly.stl', 'Key_Carrier-assembly.stl', id);
  }
  for (const name of ['op1_lead_thread', 'op1_lead_turned', 'op1_lead_drop', 'op1_lead_route']) {
    assert.equal(sha(`guide/${name}.stl`), sha(`guide/${name}.stl`, r66Files), name);
  }
});
