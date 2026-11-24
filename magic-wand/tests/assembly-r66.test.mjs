import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const files = new URL('../hardware/carbon-rod-holders-r66-three-hole-op1/exports/', import.meta.url);
const bytes = path => readFileSync(new URL(path, files));
const load = path => JSON.parse(bytes(path));
const sha = path => createHash('sha256').update(bytes(path)).digest('hex');
const guide = validateGuide(load('assembly-guide.json'));
const OP1 = ['board', 'sockets', 'housing', 'plug'];
const INSERT = ['Thread the white plug up from below', 'Turn the plug upright above the holder',
  'Push the board onto the plug', 'Lower the board into its three holes', 'Press the lead into its channel'];
const REMOVE = ['Free the lead from its channel', 'Lift the board straight up', 'Pull the board off the plug',
  'Tip the plug so its lead hangs down', 'Lower the plug back through the opening'];
const close = (a, b, tolerance = 1e-5) => a.length === b.length && a.every((v, i) => Math.abs(v - b[i]) < tolerance);

function stlVertices(path) {
  const data = bytes(path);
  const count = data.readUInt32LE(80);
  const out = new Float32Array(count * 9);
  for (let t = 0; t < count; t++) {
    for (let k = 0; k < 9; k++) out[t * 9 + k] = data.readFloatLE(84 + t * 50 + 12 + k * 4);
  }
  return out;
}

test('R66 ships the complete 13-piece kit, with no loose OP1 seat, and hash-bound meshes', () => {
  const names = ['Key_Carrier', 'Touch_Paddle', 'Rod_Collet', 'Hinge_Pin', 'Hinge_Pin_Snug', 'Pin_Clip',
    'Pin_Clip_Spare', 'OP1_Lid_Stop', 'DFR_Post_Bar', 'DFR_Clip_Left', 'DFR_Clip_Right',
    'Socket_Backer_Left', 'Socket_Backer_Right'];
  assert.equal(guide.revision, 'R66');
  assert.equal(guide.physical_fit_verified, false);
  assert.deepEqual([...guide.print_components.keys].sort(), names.sort());
  for (const [path, expected] of Object.entries(guide.sources.meshes_sha256)) assert.equal(sha(path), expected, path);
  assert.equal(guide.sources.meshes_sha256['Key_Carrier-assembly.stl'], sha('Key_Carrier-assembly.stl'));
  assert.equal(guide.sources.route_report_sha256, sha('op1-route.json'));
  for (const module of Object.values(guide.modules)) assert.ok(!('op1_seat' in module.actors));
});

test('every CAD report checks this exact carrier and its R66 mechanisms pass', () => {
  const carrier = sha('Key_Carrier-assembly.stl');
  const reports = Object.fromEntries(['op1-route', 'battery', 'socket-backing', 'carrier']
    .map(name => [name, load(name + '.json')]));
  for (const [name, report] of Object.entries(reports)) {
    assert.equal(report.carrier_sha256, carrier, name);
    assert.equal(report.passes, true, name);
    assert.equal(report.physical_fit_verified, false, name);
  }
  const route = reports['op1-route'];
  assert.equal(route.three_holes.r66.length, 3);
  route.three_holes.r66.forEach((hole, i) => {
    for (const z of ['z9.05', 'z8.3', 'z7.6']) assert.equal(hole[z].clear_radius, route.three_holes.r63[i][z].clear_radius);
  });
  assert.equal(route.deck_change_from_r63_in_op1_zone_mm3.added, 0);
  assert.ok(route.not_feasible.mated_board_from_above.closed_ring_heights_mm.length > 0);
  assert.ok(route.not_feasible.plug_pushed_up_into_seated_housing.straight_up_overlap_with_full_rod_mm3 > 0);
  const cell = reports.battery;
  assert.ok(cell.inboard_full_depth_y_mm[1] >= 43);
  assert.ok(cell.outboard_full_depth_y_mm[1] < cell.inboard_full_depth_y_mm[1] - 5);
  assert.ok(cell.spring_root.volume_r66_mm3 > 0.85 * cell.spring_root.volume_r64_mm3);
  const backing = reports['socket-backing'];
  assert.equal(backing.collet_insertion.to_backing_max_mm3, 0);
  assert.ok(backing.collet_push_in_stroke.added_by_backing_max_mm3 <= 1e-4);
  assert.ok(backing.backing_beyond_bed_face_mm <= 1e-4 && backing.seat_taper_faces.identical);
  assert.equal(reports.carrier.key_poses_checked, 336);
  assert.deepEqual(reports.carrier.key_obstructions, []);
});

test('each OP1 guide threads the plug from below, plugs the board on above and lowers it into the holes', () => {
  for (const id of ['dfr', 'op1_clips', 'pin_hinge']) {
    const {steps, stagedActors} = guide.modules[id];
    assert.ok(stagedActors);
    assert.deepEqual(steps.slice(0, 5).map(s => s.title), INSERT, id);
    assert.ok(!steps.some(s => s.title === 'Seat the OP1 board' || s.title === 'Lift the OP1 board'));
    const [thread, turn, push, lower, press] = steps;
    for (const s of thread.samples) {
      assert.ok(!s.board && !s.housing && !s.sockets && !s.switch && !s.lid && s.rod && s.carrier);
      assert.equal(s.morphs.op1_lead, 0);
    }
    const rise = thread.samples.map(s => s.plug[11]);
    assert.ok(rise.every((z, i) => i === 0 || z > rise[i - 1]) && rise.at(-1) - rise[0] >= 30, id);
    assert.equal(turn.samples[0].morphs.op1_lead, 0);
    assert.equal(turn.samples.at(-1).morphs.op1_lead, 1);
    // The board waits above and descends onto the plug, which stays put.
    for (const s of push.samples) assert.deepEqual(s.plug, push.samples[0].plug);
    assert.ok(push.samples[0].board[11] > push.samples.at(-1).board[11]);
    // Lowering: the plugged group drops straight down by 16 mm, without turning.
    const top = lower.samples[0], seated = lower.samples.at(-1);
    for (const actor of OP1) {
      assert.ok(close(top[actor].filter((_, i) => i % 4 !== 3), seated[actor].filter((_, i) => i % 4 !== 3)), actor);
      assert.ok(Math.abs(top[actor][11] - seated[actor][11] - 16) < 1e-5 && top[actor][3] === seated[actor][3]);
    }
    for (const s of press.samples) for (const actor of OP1) assert.deepEqual(s[actor], seated[actor]);
    assert.equal(press.samples.at(-1).morphs.op1_wire, 1);
    const fitSwitch = steps.find(s => s.title === 'Fit the mouse switch');
    for (const actor of [...OP1, 'op1_wire']) assert.ok(close(fitSwitch.samples[0][actor], press.samples.at(-1)[actor]), actor);
  }
});

test('removal plays the five OP1 motions exactly in reverse', () => {
  const {steps} = guide.modules.op1_clips;
  const start = steps.findIndex(s => s.title === REMOVE[0]);
  assert.ok(start > 4);
  assert.deepEqual(steps.slice(start, start + 5).map(s => s.title), REMOVE);
  for (let i = 0; i < 5; i++) {
    assert.deepEqual(steps[start + i].samples, [...steps[4 - i].samples].reverse(), REMOVE[i]);
  }
});

test('installed actors and lead shapes stay continuous between neighbouring steps', () => {
  for (const id of ['dfr', 'op1_clips', 'pin_hinge']) {
    const {steps, actors} = guide.modules[id];
    for (let i = 1; i < steps.length; i++) {
      const end = steps[i - 1].samples.at(-1), start = steps[i].samples[0];
      for (const key of Object.keys(actors)) {
        if (key in start && key in end) assert.ok(close(start[key], end[key]), id + ' / ' + steps[i].title + ' / ' + key);
        if (start.morphs?.[key] !== undefined && end.morphs?.[key] !== undefined) {
          assert.equal(start.morphs[key], end.morphs[key], id + ' / ' + steps[i].title + ' / morph ' + key);
        }
      }
    }
  }
  // The turned lead (shown above the holder) is the dropping lead raised by the 16 mm lift,
  // so the hand-over to the moving board group is seamless. Morph pairs share topology.
  const turned = stlVertices('guide/op1_lead_turned.stl'), drop = stlVertices('guide/op1_lead_drop.stl');
  assert.equal(turned.length, drop.length);
  assert.ok(turned.every((v, i) => Math.abs(v - drop[i] - (i % 3 === 2 ? 16 : 0)) < 1e-4));
  assert.equal(stlVertices('guide/op1_lead_thread.stl').length, turned.length);
  assert.equal(stlVertices('guide/op1_lead_route.stl').length, drop.length);
  const {actors} = guide.modules.op1_clips;
  assert.equal(actors.op1_lead.morphFile, 'guide/op1_lead_turned.stl');
  assert.equal(actors.op1_wire.morphFile, 'guide/op1_lead_route.stl');
});
