import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const files = new URL('../hardware/carbon-rod-holders-r68-pre-taper-battery-rail/exports/', import.meta.url);
const r67Files = new URL('../hardware/carbon-rod-holders-r67-diagonal-battery-corner/exports/', import.meta.url);
const r64Files = new URL('../hardware/carbon-rod-holders-r64-under-entry/exports/', import.meta.url);
const bytes = (path, base = files) => readFileSync(new URL(path, base));
const load = (path, base = files) => JSON.parse(bytes(path, base));
const sha = (path, base = files) => createHash('sha256').update(bytes(path, base)).digest('hex');
const guide = validateGuide(load('assembly-guide.json'));
const r67Guide = load('assembly-guide.json', r67Files);
const reports = Object.fromEntries(['restore', 'battery', 'saddle', 'op1-route', 'carrier']
  .map(name => [name, load(name + '.json')]));

test('R68 ships the complete 13-piece kit with hash-bound meshes', () => {
  const names = ['Key_Carrier', 'Touch_Paddle', 'Rod_Collet', 'Hinge_Pin', 'Hinge_Pin_Snug', 'Pin_Clip',
    'Pin_Clip_Spare', 'OP1_Lid_Stop', 'DFR_Post_Bar', 'DFR_Clip_Left', 'DFR_Clip_Right',
    'Socket_Backer_Left', 'Socket_Backer_Right'];
  assert.equal(guide.revision, 'R68');
  assert.equal(guide.physical_fit_verified, false);
  assert.deepEqual([...guide.print_components.keys].sort(), names.sort());
  for (const [path, expected] of Object.entries(guide.sources.meshes_sha256)) assert.equal(sha(path), expected, path);
  assert.equal(guide.sources.meshes_sha256['Key_Carrier-assembly.stl'], sha('Key_Carrier-assembly.stl'));
  assert.equal(guide.sources.route_report_sha256, sha('op1-route.json'));
});

test('every CAD report checks this exact carrier: R67 outside the restore box, R64 inside it', () => {
  const carrier = sha('Key_Carrier-assembly.stl');
  for (const [name, report] of Object.entries(reports)) {
    assert.equal(report.carrier_sha256, carrier, name);
    assert.equal(report.passes, true, name);
    assert.equal(report.physical_fit_verified, false, name);
  }
  assert.equal(load('click-fit.json').carrier_sha256, carrier);
  assert.deepEqual(load('click-fit.json').overlap_mm3, load('click-fit.json', r67Files).overlap_mm3);
  const source = load('source-reproduction.json');
  assert.equal(source.carrier_sha256, carrier);
  assert.equal(source.reproduced_sha256, carrier);
  const restore = reports.restore;
  assert.equal(restore.r67_carrier_sha256, sha('Key_Carrier-assembly.stl', r67Files));
  assert.equal(restore.r64_carrier_sha256, sha('Key_Carrier-assembly.stl', r64Files));
  assert.ok(restore.sections_outside_box_against_r67.max_area_mm2 < 0.0025);
  assert.ok(restore.sections_inside_box_against_r64.max_area_mm2 < 0.0025);
  assert.ok(Math.abs(restore.volume_identity_mm3.difference) < 0.01);
  for (const volume of Object.values(restore.pre_taper_in_box_mm3)) assert.ok(Math.abs(volume - restore.volume_mm3.r64_in_box) < 0.001);
  assert.ok(Math.abs(restore.box_beyond_taper_mm3.r64 - restore.box_beyond_taper_mm3.r67) < 0.005);
  assert.equal(restore.components, 1);
  assert.equal(reports.carrier.key_poses_checked, 336);
  assert.deepEqual(reports.carrier.key_obstructions, []);
});

test('the outer battery rail runs at full depth to the rear face, exactly as before the taper', () => {
  const battery = reports.battery;
  for (const key of ['outboard_full_depth_y_mm', 'outboard_lip_under_pack_y_mm', 'inboard_full_depth_y_mm',
    'shoe_preload_overlap_mm3', 'retention_pack_dropped_0_3mm_mm3', 'spring_root_post_mm3', 'bed_face_area_in_corner_mm2']) {
    assert.deepEqual(battery[key].r68, battery[key].r64, key);
  }
  for (const [y, edge] of Object.entries(battery.outboard_edge_x_mm)) assert.equal(edge.r68, edge.r64, y);
  assert.ok(battery.outboard_full_depth_y_mm.r68[1] > battery.outboard_full_depth_y_mm.r67[1] + 10);
  assert.ok(battery.retention_pack_dropped_0_3mm_mm3.r68.outboard > battery.retention_pack_dropped_0_3mm_mm3.r67.outboard);
  assert.ok(battery.spring_leaf_and_shoe_xor_r64_mm3 < 0.01);
  assert.equal(battery.pack_slide_from_rear_to_carrier_outside_spring_mm3, 0);
});

test('base fins sit on the restored corner and keep the free lip ends clear', () => {
  const fins = reports.battery.base_fins;
  assert.equal(fins.fin_material_in_holder_mm3.outer_free_lip, 0);
  assert.equal(fins.fin_material_in_holder_mm3.inner_free_lip, 0);
  assert.ok(fins.fin_material_in_holder_mm3.root_below > 0.5 && fins.fin_material_in_holder_mm3.root_above > 0.5);
  const stations = fins.fins.map(f => `${f.face}${f.at}`);
  assert.ok(stations.includes('-y-24') && stations.includes('+y-23.8'));
  assert.equal(fins.backed_pieces, 1);
});

test('R67 saddle cleanup and OP1 lead-in are kept', () => {
  const saddle = reports.saddle;
  assert.ok(!saddle.pieces_in_box.r68.some(([volume, free]) => free && volume > 0.6));
  for (const [name, [before, after]] of Object.entries(saddle.unchanged_mm3)) assert.ok(Math.abs(before - after) < 0.002, name);
  const lead = reports['op1-route'].lead_in;
  const r67Lead = load('op1-route.json', r67Files).lead_in;
  assert.equal(lead.removed_mm3, r67Lead.removed_mm3);
  assert.deepEqual(lead.stops.r68, lead.stops.r66);
  lead.three_holes.r68.forEach((hole, i) => assert.deepEqual(hole['z8.3'], lead.three_holes.r66[i]['z8.3']));
  assert.deepEqual(Object.keys(reports['op1-route'].three_holes).sort(), ['r63', 'r68']);
  for (const row of Object.values(reports['op1-route'].seat_support_mm2)) {
    assert.deepEqual(Object.keys(row).sort(), ['r63', 'r68']);
  }
});

test('the guide plays R67 motions unchanged with the R68 carrier', () => {
  assert.deepEqual(Object.keys(guide.modules).sort(), Object.keys(r67Guide.modules).sort());
  for (const [id, module] of Object.entries(guide.modules)) {
    const before = r67Guide.modules[id];
    assert.deepEqual(module.steps.map(s => s.title), before.steps.map(s => s.title), id);
    module.steps.forEach((step, i) => assert.deepEqual(step.samples, before.steps[i].samples, id + ' / ' + step.title));
  }
  assert.match(guide.modules.battery.note, /Both rails run the full length/);
  for (const name of ['op1_lead_thread', 'op1_lead_turned', 'op1_lead_drop', 'op1_lead_route']) {
    assert.equal(sha(`guide/${name}.stl`), sha(`guide/${name}.stl`, r67Files), name);
  }
});
