// Exercise complete component recipes and the actual shared-menu inputs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { validateGuide, sampledPose, identity, groupKeys } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';
import { legacyR20 } from '../hardware/carbon-rod-holders/assembly/legacy-r20.mjs';
import { GUIDED_CAPTURE, HOLDER_SNAP, UPPER_KEY_SHIFT } from '../hardware/carbon-rod-holders/assembly/keycap-concepts.mjs';
import { CIRQUE_LAYOUT } from '../hardware/carbon-rod-holders/assembly/cirque-keycap.mjs';

test('R25 Keys opens seated with the centre paddle and four capped Choc switches', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const version = catalog.versions.find(entry => entry.id === 'r25');
  const guide = JSON.parse(readFileSync(new URL(version.guide, directory)));
  assert.equal(version.groupKeys, true);
  const { modules, views } = groupKeys(guide.modules);
  assert.equal(Object.keys(modules)[0], 'keys');
  assert.equal(modules.keys.label, 'Keys');
  assert.ok(Object.keys(views).every(id => !Object.hasOwn(modules, id)));
  validateGuide({ ...guide, modules: views });
  for (const view of Object.values(views)) {
    assert.deepEqual(view.helperActions[0].actors, ['keycap_0', 'keycap_2', 'keycap_3', 'keycap_4']);
    assert.equal(view.helperActions[0].hideLabel, 'Hide other keycaps');
  }
  for (const id of ['centre', 'centre_shallow', 'centre_deep']) {
    const view = views[id];
    const original = guide.modules[id];
    const last = sampledPose(view, view.steps.length - 1, 1);
    assert.equal(view.openSeated, true);
    assert.deepEqual(last.paddle, original.steps.at(-1).samples.at(-1).paddle);
    assert.equal(view.actors.paddle.file, original.actors.paddle.file);
    for (const key of [0, 2, 3, 4]) {
      assert.equal(view.actors[`switch_${key}`].frame, true);
      assert.deepEqual(last[`switch_${key}`], original.steps.at(-1).samples.at(-1)[`switch_${key}`]);
      assert.deepEqual(last[`socket_${key}`], guide.modules.key.steps.at(-1).samples.at(-1)[`socket_${key}`]);
      assert.ok(view.actors[`keycap_${key}`].geometry.faces.length > 0);
      assert.deepEqual(last[`keycap_${key}`], last[`switch_${key}`]);
    }
  }
  assert.deepEqual(views.key.steps.slice(0, -1).map(step => step.title), guide.modules.key.steps.map(step => step.title));
  const capStep = views.key.steps.length - 1;
  assert.equal(views.key.steps[capStep].title, 'Fit the Keycaps');
  for (const key of [0, 2, 3, 4]) {
    const start = sampledPose(views.key, capStep, 0)[`keycap_${key}`];
    const end = sampledPose(views.key, capStep, 1)[`keycap_${key}`];
    assert.equal(start[11] - end[11], 18);
    assert.deepEqual(end, sampledPose(views.key, capStep, 1)[`switch_${key}`]);
  }
});

test('R25 concept views press and return beside the same capped keys', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const guide = JSON.parse(readFileSync(new URL(catalog.versions.find(entry => entry.id === 'r25').guide, directory)));
  const { views } = groupKeys(guide.modules);
  const variants = Object.entries(views).filter(([, view]) => view.concept);
  assert.deepEqual(variants.map(([id]) => id), [
    'concept_slider', 'concept_flexure', 'concept_pivot', 'concept_direct', 'concept_carrier', 'concept_touch',
  ]);
  const seated = views.centre.steps.at(-1).samples.at(-1);
  for (const [id, view] of variants) {
    validateGuide({ ...guide, modules: { [id]: view } });
    const pressIndex = view.steps.findIndex(step => step.title.startsWith('Press'));
    const press = view.steps[pressIndex];
    const rest = press.samples[0], down = press.samples.at(-1);
    const returned = view.steps[pressIndex + 1].samples.at(-1);
    assert.deepEqual(rest.cap, returned.cap);
    assert.notDeepEqual(rest.cap, down.cap);
    assert.equal(rest.plunger[11], 0);
    assert.ok(down.plunger[11] < 0);
    assert.deepEqual(rest.board, down.board);
    assert.equal(rest.board[5], id === 'concept_touch' ? 1 : -1);
    for (const key of [0, 2, 3, 4]) {
      const expected = [...seated[`keycap_${key}`]];
      if (['concept_carrier', 'concept_touch'].includes(id) && key >= 3) expected[3] += key === 3 ? -UPPER_KEY_SHIFT : UPPER_KEY_SHIFT;
      assert.deepEqual(down[`keycap_${key}`], expected);
    }
    for (const actor of Object.values(view.actors)) {
      for (const mesh of [actor.geometry, actor.morphGeometry, ...(actor.morphGeometries ?? [])].filter(Boolean)) {
        assert.ok(mesh.vertices.flat().every(Number.isFinite));
        if (mesh.faces) assert.ok(mesh.faces.flat().every(i => i >= 0 && i < mesh.vertices.length));
      }
    }
    assert.equal(view.annotations.length, 2);
    assert.ok(view.annotations.every(annotation => view.actors[annotation.actor]));
    for (let index = 1; index < view.steps.length; index++) {
      const from = view.steps[index - 1].samples.at(-1), to = view.steps[index].samples[0];
      for (const actor of Object.keys(view.actors)) {
        assert.ok(from[actor].every((n, i) => Math.abs(n - to[actor][i]) < 1e-8), `${id}/${index}/${actor}`);
        const before = [from.morphs?.[actor] ?? 0].flat(), after = [to.morphs?.[actor] ?? 0].flat();
        for (let i = 0; i < Math.max(before.length, after.length); i++) {
          assert.ok(Math.abs((before[i] ?? 0) - (after[i] ?? 0)) < 1e-8, `${id}/${index}/${actor} flex`);
        }
      }
    }
  }
  const guided = views.concept_slider;
  const { pinZ, pinRadius, slotBottom, slotTop, travel } = GUIDED_CAPTURE;
  assert.ok(pinZ - pinRadius - slotBottom > 0 && pinZ - pinRadius - slotBottom < .1);
  assert.ok(slotTop - travel > pinZ + pinRadius);
  const pinStep = guided.steps.find(step => step.title === 'Slide In Both Keeper Pins');
  assert.equal(pinStep.samples[0].keeperRight[3] - pinStep.samples.at(-1).keeperRight[3], 5);
  const pressed = guided.steps.at(-2).samples.at(-1);
  assert.equal(pressed.keeperRight[11], 0);
  assert.equal(pressed.cap[11], -travel);
  assert.equal(views.concept_direct.comparisonOnly, true);
  const holder = views.concept_carrier;
  assert.equal(holder.actors.hinge, undefined);
  const { axisY, axisZ, supportInner, supportOuter, boreRadius, pinTip, pinRadius: snapRadius, squeeze } = HOLDER_SNAP;
  assert.ok(pinTip - supportInner > .39 && pinTip < supportOuter);
  assert.ok(pinTip - squeeze < supportInner && boreRadius > snapRadius);
  const motion = holder.steps.flatMap(step => step.samples);
  const flexStep = holder.steps.find(step => step.title === 'Squeeze Both Arms In');
  const snapStep = holder.steps.find(step => step.title === 'Let the Pins Snap Outward');
  const removeStep = holder.steps.find(step => step.title === 'Remove and Refit the Cap');
  assert.equal(flexStep.samples.at(-1).morphs.snapRight, 1);
  assert.equal(snapStep.samples.at(-1).morphs.snapRight, 0);
  assert.ok(removeStep.samples.some(sample => sample.cap[11] > 0 && sample.morphs.snapRight === 1));
  const keyGapHalf = 9.35 + UPPER_KEY_SHIFT - 16.6 / 2;
  assert.ok(keyGapHalf > supportOuter && keyGapHalf < 2);
  for (const id of ['cap', 'snapLeft', 'snapRight', 'hingeSupports']) {
    const actor = holder.actors[id];
    for (const sample of motion) for (const [index, [x, y, z]] of actor.geometry.vertices.entries()) {
      const m = sample[id];
      const along = y * m[5] + z * m[6] + m[7];
      const openedX = actor.morphGeometry?.vertices[index][0] ?? x;
      const worldX = x + (openedX - x) * (sample.morphs?.[id] ?? 0) + m[3];
      if (along >= 17.8 - 17.5 / 2) assert.ok(Math.abs(worldX) <= keyGapHalf);
      if (actor.morphGeometry) {
        assert.ok(Math.sign(worldX) === Math.sign(x), 'squeezed arms stay on opposite sides');
        const height = y * m[9] + z * m[10] + m[11];
        if (Math.abs(worldX) >= supportInner && Math.abs(along - axisY) <= 1.36 && height <= axisZ + 1.34) {
          assert.ok(Math.hypot(along - axisY, height - axisZ) < boreRadius, 'moving arm clears the fixed socket wall');
        }
      }
    }
  }
  const stopTop = Math.max(...holder.actors.stops.geometry.vertices.map(([, , z]) => z));
  assert.ok(stopTop - 11.04 < 3);
});

test('R25 Cirque cap clears its neighbours and releases after unplugging the ribbon', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const guideUrl = new URL(catalog.versions.find(entry => entry.id === 'r25').guide, directory);
  const { modules } = JSON.parse(readFileSync(guideUrl));
  const { views } = groupKeys(modules);
  const view = views.concept_touch;
  const { actors, steps } = view;
  const { pinTip, armInner, squeeze, switchX, attachLift, disconnect, stopX, sensorDepth, sensorRadius, top } = CIRQUE_LAYOUT;
  assert.ok(pinTip - armInner > .40 && pinTip - squeeze < armInner);
  assert.match(view.status, /physical fit unverified/);
  const press = steps.find(step => step.title === 'Press to Click');
  const release = steps.find(step => step.title === 'Disconnect and Lift Off');
  const rest = press.samples[0];
  const bodyRight = Math.max(...actors.body.geometry.vertices.map(vertex => vertex[0])) + switchX;
  const frontStops = actors.stops.geometry.vertices.filter(vertex => vertex[1] < 0);
  const frontStopTop = Math.max(...frontStops.map(vertex => vertex[2]));
  function points(id, sample) {
    const { geometry, morphGeometry, morphGeometries } = actors[id], pose = sample[id];
    const targets = morphGeometries ?? (morphGeometry ? [morphGeometry] : []);
    const weights = [sample.morphs?.[id] ?? 0].flat();
    return geometry.vertices.map((vertex, index) => {
      const v = vertex.map((value, axis) => targets.reduce((coordinate, target, i) =>
        coordinate + (weights[i] ?? 0) * (target.vertices[index][axis] - value), value));
      return [0, 4, 8].map(j => pose[j] * v[0] + pose[j + 1] * v[1] + pose[j + 2] * v[2] + pose[j + 3]);
    });
  }
  const rightKey = Math.min(...points('keycap_2', rest).map(vertex => vertex[0]));
  const upperKeyFront = Math.min(...points('keycap_4', rest).map(vertex => vertex[1]));
  const upperKeyInner = Math.min(...points('keycap_4', rest).map(vertex => vertex[0]));
  function meshExtent(id, axis) {
    const mesh = readFileSync(new URL(actors[id].file, guideUrl)), pose = rest[id];
    const row = axis * 4;
    let min = Infinity, max = -Infinity;
    for (let triangle = 0; triangle < mesh.readUInt32LE(80); triangle++) {
      for (let corner = 0; corner < 3; corner++) {
        const offset = 96 + triangle * 50 + corner * 12;
        const value = pose[row] * mesh.readFloatLE(offset) + pose[row + 1] * mesh.readFloatLE(offset + 4)
          + pose[row + 2] * mesh.readFloatLE(offset + 8) + pose[row + 3];
        min = Math.min(min, value);
        max = Math.max(max, value);
      }
    }
    return [min, max];
  }
  const [boardFront, boardBack] = meshExtent('board', 1);
  const [, plugBack] = meshExtent('plug', 1);
  const [upperSwitchFront] = meshExtent('switch_3', 1);
  const [plugBottom] = meshExtent('plug', 2);
  const [, rodTop] = meshExtent('rod', 2);
  assert.ok(upperSwitchFront - boardBack > .25 && plugBack < boardFront + 4);
  assert.ok(plugBottom - rodTop > .5);
  assert.equal(Math.max(...points('sensorBoard', rest).map(vertex => vertex[0])), sensorRadius);
  assert.ok(Math.abs(top - Math.min(...points('sensorConnector', rest).map(vertex => vertex[2])) - sensorDepth) < 1e-8);
  // The first mesh in the cradle is the support ring. Its bottom inner
  // row is the actual polygon that the connector must clear on insertion.
  const cradle = actors.cap.geometry.vertices;
  const ringSections = cradle.findIndex(vertex => vertex[2] !== cradle[0][2]);
  const opening = cradle.slice(6 * ringSections, 7 * ringSections);
  function clearsOpening([x, y]) {
    let inside = false;
    for (let i = 0; i < opening.length; i++) {
      const [ax, ay] = opening[i], [bx, by] = opening[(i + 1) % opening.length];
      if ((ay > y) !== (by > y) && x < ax + (bx - ax) * (y - ay) / (by - ay)) inside = !inside;
    }
    return inside;
  }
  assert.ok(points('sensorConnector', rest).every(clearsOpening), 'connector corners clear the support ledge');
  const feed = steps.find(step => step.title === 'Seat the Touchpad');
  for (const sample of feed.samples) {
    assert.ok(points('ribbon', sample).every(clearsOpening), 'straight ribbon feeds through the ledge opening');
  }
  for (const sample of steps.flatMap(step => step.samples)) {
    for (const id of ['cap', 'sensorSurface', 'sensorBoard', 'sensorConnector', 'snapLeft', 'snapRight', 'hingeSupports', 'ribbon']) {
      for (const [x, y] of points(id, sample)) {
        assert.ok(Math.abs(x) < rightKey, `${id} clears the side keys`);
        if (y >= upperKeyFront) assert.ok(Math.abs(x) < upperKeyInner, `${id} clears the upper keys`);
      }
    }
    assert.ok(points('sensorConnector', sample).every(([x]) => x - bodyRight >= .5));
    assert.ok(points('ribbon', sample).every(([x]) => x > bodyRight + .5));
  }
  for (const sample of press.samples) {
    const feet = points('cap', sample).filter(([x, , z]) => Math.abs(Math.abs(x) - stopX) <= .631 && z < 15);
    assert.ok(feet.length > 0 && feet.every(([, , z]) => z >= frontStopTop - 1e-8));
    assert.deepEqual(points('ribbon', sample).slice(-4), points('ribbon', rest).slice(-4));
  }
  const pressed = press.samples.at(-1);
  const footZ = Math.min(...points('cap', pressed).filter(([x]) => Math.abs(Math.abs(x) - stopX) <= .631).map(vertex => vertex[2]));
  assert.ok(Math.abs(footZ - frontStopTop) < 1e-8);
  assert.ok(Math.abs(pressed.plunger[11] - rest.plunger[11] + .47) < 1e-8);
  for (const sample of release.samples.filter(sample => sample.cap[11] > 0)) {
    assert.equal(sample.flexDock[3] - rest.flexDock[3], disconnect);
    assert.equal(sample.morphs.hingeSupports, 1);
  }
  assert.equal(release.samples.at(-1).cap[11], attachLift);
  assert.equal(steps.at(-1).samples.at(-1).cap[11], 0);
});

test('printed-parts catalog includes every assembly and preserves physical-fit limits', async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async url => new Response(readFileSync(url));
  try {
    const guide = validateGuide(await legacyR20());
    assert.deepEqual(Object.keys(guide.modules), ['xiao', 'battery', 'keys', 'finger_guard', 'cable']);
    assert.equal(guide.physical_fit_verified, false);
    assert.match(guide.modules.xiao.note, /reused the R19 keeper/);
    assert.match(guide.modules.xiao.note, /still needs checking/);
    assert.match(guide.modules.cable.note, /unmeasured/);
    for (const module of Object.values(guide.modules)) {
      for (const actor of Object.values(module.actors)) if (actor.file) assert.ok(readFileSync(new URL(actor.file, actor.baseUrl)).length > 84);
      for (let i = 0; i < module.steps.length - 1; i++) {
        const end = sampledPose(module, i, 1), start = sampledPose(module, i + 1, 0);
        for (const id of Object.keys(module.actors)) for (let j = 0; j < 12; j++) assert.ok(Math.abs(end[id][j] - start[id][j]) < 1e-8, `${module.label}/${id}`);
      }
    }
    const guard = guide.modules.finger_guard;
    assert.equal(sampledPose(guard, 0, 0).guard[7], -60);
    assert.deepEqual(sampledPose(guard, 0, 1).guard, identity());
    assert.throws(() => sampledPose(guard, -1, 0));
    assert.throws(() => sampledPose(guard, 0, NaN));
    assert.throws(() => validateGuide({ ...guide, units: 'inches' }));
  } finally { globalThis.fetch = oldFetch; }
});

test('tower illustration is tied to actual R20 extrusion and handles leading decimals', () => {
  const base = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const data = JSON.parse(readFileSync(new URL('tower-r20.json', base)));
  const hash = file => createHash('sha256').update(readFileSync(new URL(file, base))).digest('hex');
  assert.equal(data.source_sha256, hash('../../carbon-rod-holders-r20-finger-guard/exports/R20-A1-mini-PETG.gcode.3mf'));
  assert.equal(data.generator_sha256, hash('tower_paths.py'));
  assert.ok(data.segments.length > 20000);
  assert.equal(data.bounds_mm[0][2], .2);
  assert.equal(data.bounds_mm[1][2], 35.2);
  assert.ok(data.segments.every(segment => segment.length === 6 && segment.every(Number.isFinite)));
});

test('R23 assembly stays tied to the exported carrier and fit variants', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const read = url => JSON.parse(readFileSync(url));
  const sha = url => createHash('sha256').update(readFileSync(url)).digest('hex');
  const catalog = read(new URL('catalog.json', directory));
  assert.ok(catalog.versions.some(version => version.id === catalog.current));
  const version = catalog.versions.find(version => version.id === 'r23');
  const guideURL = new URL(version.guide, directory);
  const guide = validateGuide(read(guideURL));
  const manifestURL = new URL('manifest.json', guideURL);
  const manifest = read(manifestURL);
  assert.equal(guide.revision, manifest.revision);
  assert.equal(guide.sources.manifest_sha256, sha(manifestURL));
  assert.equal(guide.sources.centre_motion_sha256, sha(new URL('centre-motion.json', guideURL)));
  assert.equal(guide.sources.generator_sha256, sha(new URL('../assembly23.py', guideURL)));
  assert.equal(guide.physical_fit_verified, false);
  const meshes = guide.sources.meshes_sha256;
  for (const module of Object.values(guide.modules)) {
    for (const { file } of Object.values(module.actors)) {
      assert.equal(meshes[file], sha(new URL(file, guideURL)), file);
    }
  }
  for (const [name, part] of Object.entries(manifest.parts)) {
    assert.equal(meshes[`${name}-assembly.stl`], part.assembly_stl_sha256, name);
  }
  assert.notEqual(guide.modules.centre_shallow.actors.paddle.file, guide.modules.centre_deep.actors.paddle.file);
  for (const id of ['battery', 'battery_easy']) {
    const { actors, steps } = guide.modules[id];
    assert.equal(actors.spacer, undefined);
    const door = steps.find(step => step.title === 'Drop In the Door').samples.map(sample => sample.door);
    assert.ok(door.every(pose => pose[3] === 0 && pose[7] === 0));
    assert.ok(door[0][11] > 0 && door.at(-1)[11] === 0);
  }
  assert.notEqual(guide.modules.battery.actors.door.file, guide.modules.battery_easy.actors.door.file);
  if (version.helper) {
    const tower = read(new URL(version.helper, directory));
    assert.equal(tower.source_sha256, sha(new URL('R23-A1-mini-PETG.gcode.3mf', guideURL)));
    assert.ok(tower.segments.length > 0);
  }
});

test('the original XIAO catch flexes and releases in both assembly views', () => {
  const hardware = new URL('../hardware/', import.meta.url);
  const path = new URL('carbon-rod-holders-r22-integrated-guard/exports/assembly-guide.json', hardware);
  const { modules } = validateGuide(JSON.parse(readFileSync(path)));
  const guidePath = new URL('carbon-rod-holders-r23-hybrid-centre/exports/assembly-guide.json', hardware);
  const reused = validateGuide(JSON.parse(readFileSync(guidePath)));
  const read = (file, base = path) => readFileSync(new URL(file, base));
  for (const [module, nextModule] of [[modules.xiao, reused.modules.xiao], [modules.xiao_latch, reused.modules.xiao_latch]]) {
    const { file, morphFile } = module.actors.keeper;
    const rest = read(file), raised = read(morphFile);
    assert.equal(raised.readUInt32LE(80), rest.readUInt32LE(80));
    assert.deepEqual(read(nextModule.actors.keeper.morphFile, guidePath), raised);
    let lifted = 0;
    for (let face = 84; face < rest.length; face += 50) {
      for (let vertex = face + 12; vertex < face + 48; vertex += 12) {
        assert.equal(raised.readFloatLE(vertex), rest.readFloatLE(vertex));
        assert.equal(raised.readFloatLE(vertex + 4), rest.readFloatLE(vertex + 4));
        lifted = Math.max(lifted, raised.readFloatLE(vertex + 8) - rest.readFloatLE(vertex + 8));
      }
    }
    assert.ok(lifted > .4);
    const insert = module.steps.find(step => step.samples.some(pose => pose.morphs?.keeper > 0));
    const release = module.steps.at(-1);
    assert.equal(insert.samples.at(-1).keeper[7], 0);
    assert.equal(insert.samples.at(-1).morphs.keeper, 0);
    const movement = step => step.samples.map(({ keeper, morphs }) => [keeper, morphs.keeper]);
    assert.deepEqual(movement(release), movement(insert).reverse());
    assert.equal(insert.checks.max_overlap_with_drawn_bend_mm3, 0);
    assert.ok(insert.checks.max_rigid_overlap_mm3 > .05);
  }
});

test('R25 shows the stopped pull, deliberate lift and board removal', () => {
  const path = new URL('../hardware/carbon-rod-holders-r25-keeper-release/exports/assembly-guide.json', import.meta.url);
  const { modules } = validateGuide(JSON.parse(readFileSync(path)));
  for (const module of [modules.xiao, modules.xiao_latch]) {
    const samples = title => module.steps.find(step => step.title === title).samples;
    const stop = samples('Pull Gently to Check the Stop').at(-1);
    const lift = samples('Lift the Rounded Tab');
    const slide = samples('Slide the Keeper Out');
    assert.ok(stop.keeper[7] < 0 && stop.morphs.keeper === 0);
    assert.ok(lift.every(pose => pose.keeper[7] === stop.keeper[7]));
    assert.equal(lift.at(-1).morphs.keeper, 1);
    assert.ok(slide.every(pose => pose.morphs.keeper === 1));
    assert.ok(slide.at(-1).keeper[7] < stop.keeper[7]);
    assert.equal(samples('Let the Tab Settle').at(-1).morphs.keeper, 0);
  }
  assert.ok(modules.xiao.steps.some(step => step.title === 'Lift the Board Out'));
  assert.ok(modules.xiao.steps.some(step => step.title === 'Slide the Holder Off the Rod'));
  assert.ok(modules.battery_spacer && modules.centre);
});
