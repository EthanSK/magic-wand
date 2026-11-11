// Exercise complete component recipes and the actual shared-menu inputs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { validateGuide, sampledPose, identity, groupKeys, assemblyComponents, selectAssemblyComponent } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';
import { legacyR20 } from '../hardware/carbon-rod-holders/assembly/legacy-r20.mjs';
import { GUIDED_CAPTURE, HOLDER_SNAP, UPPER_KEY_SHIFT } from '../hardware/carbon-rod-holders/assembly/keycap-concepts.mjs';
import { CIRQUE_LAYOUT } from '../hardware/carbon-rod-holders/assembly/cirque-keycap.mjs';

test('the selected assembly lists each component once and retains its original recipes', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const r31 = catalog.versions.find(entry => entry.id === 'r31');
  const guide = JSON.parse(readFileSync(new URL(r31.guide, directory)));
  const components = assemblyComponents(guide, r31.groupKeys);
  assert.deepEqual(Object.keys(components), ['keys', 'xiao', 'battery', 'cable']);
  assert.deepEqual(Object.values(components).map(component => component.label),
    ['Keys', 'XIAO holder', 'Battery holder', 'Cable clip']);
  assert.equal(components.keys.defaultView, 'dfr');
  assert.equal(components.keys.views.snap_hinge.actors, guide.modules.snap_hinge.actors);
  assert.equal(components.xiao.views.xiao_latch.steps, guide.modules.xiao_latch.steps);
  assert.equal(components.battery.views.battery_spacer.actors.spacer,
    guide.modules.battery_spacer.actors.spacer);
  assert.equal(components.battery.defaultView, 'battery');
  assert.equal(components.keys.views.dfr.compareCapHeights, true);
  assert.equal(components.keys.views.key.compareCapHeights, false);
  assert.ok(!components.keys.views.snap_hinge.compareCapHeights);

  const dfr = guide.modules.dfr, [firstStep] = dfr.steps, [firstPose] = firstStep.samples;
  const lifted = [...components.keys.views.dfr.steps[0].samples[0].keycap_3];
  lifted[11] += 18;
  const liftStep = { ...firstStep, samples: [{ ...firstPose, keycap_3: lifted }, ...firstStep.samples.slice(1)] };
  const withLift = groupKeys({ ...guide.modules, dfr: { ...dfr, steps: [liftStep, ...dfr.steps.slice(1)] } });
  assert.deepEqual(withLift.views.dfr.steps[0].samples[0].keycap_3, lifted);
  assert.deepEqual(withLift.views.dfr.steps[0].samples[1].keycap_3, components.keys.views.dfr.steps[0].samples[1].keycap_3);

  const assemblyWithSpacer = assemblyComponents({ ...guide, defaultViews: { battery: 'battery_spacer' } }, true);
  assert.deepEqual(selectAssemblyComponent(assemblyWithSpacer, 'battery', null, true),
    { component: 'battery', view: 'battery_spacer' });
  assert.throws(() => assemblyComponents({ ...guide, defaultViews: { battery: 'missing' } }, true),
    /Missing default assembly view/);

  const r24 = catalog.versions.find(entry => entry.id === 'r24');
  const archive = assemblyComponents(JSON.parse(readFileSync(new URL(r24.guide, directory))), r24.groupKeys);
  assert.ok(!Object.hasOwn(archive, 'cable'));
  assert.deepEqual(selectAssemblyComponent(archive, 'key'), { component: 'keys', view: 'key' });
  assert.deepEqual(selectAssemblyComponent(archive, 'centre_shallow'), { component: 'keys', view: 'centre_shallow' });
});

test('old component and key-view links resolve inside the new component groups', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const r31 = catalog.versions.find(entry => entry.id === 'r31');
  const components = assemblyComponents(JSON.parse(readFileSync(new URL(r31.guide, directory))), r31.groupKeys);
  for (const [requestedComponent, requestedView, component, view] of [
    ['snap_hinge', null, 'keys', 'snap_hinge'],
    ['xiao_latch', null, 'xiao', 'xiao_latch'],
    ['battery_easy', null, 'battery', 'battery_easy'],
    ['battery_spacer', null, 'battery', 'battery_spacer'],
    ['keys', 'key', 'keys', 'key'],
    ['key', null, 'keys', 'dfr'],
    ['battery', 'snap_hinge', 'battery', 'battery'],
  ]) {
    assert.deepEqual(selectAssemblyComponent(components, requestedComponent, requestedView, true),
      { component, view });
  }
});

test('R25 Keys opens seated with the centre paddle and four capped Choc switches', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const version = catalog.versions.find(entry => entry.id === 'r25');
  const guide = JSON.parse(readFileSync(new URL(version.guide, directory)));
  assert.equal(version.groupKeys, true);
  const { modules, views } = groupKeys(guide.modules);
  assert.equal(Object.keys(modules)[0], 'keys');
  assert.equal(modules.keys.label, 'Keys');
  assert.ok(modules.cable);
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

test('R26 uses the printed DFRobot parts and moves only the lower outer keys', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const version = catalog.versions.find(entry => entry.id === 'r26');
  const guide = JSON.parse(readFileSync(new URL(version.guide, directory)));
  const { modules, views } = groupKeys(guide.modules);
  validateGuide({ ...guide, modules: views });
  assert.ok(modules.cable && modules.battery && modules.xiao);
  assert.equal(modules.keys.actors.paddle.file, 'DFRobot_Paddle-assembly.stl');
  assert.equal(modules.keys.actors.keeper.file, 'DFRobot_Front_Keeper-assembly.stl');
  assert.equal(modules.keys.actors.op1_latch.file, 'OP1_Board_Latch-assembly.stl');
  const animation = views.dfr;
  const rest = sampledPose(animation, animation.steps.length - 1, 1);
  assert.deepEqual([0, 2, 3, 4].map(key => rest[`keycap_${key}`][3]), [-21.5, 21.5, -9.35, 9.35]);
  assert.deepEqual(animation.helperActions[0].actors, ['keycap_0', 'keycap_2', 'keycap_3', 'keycap_4']);
  const press = animation.steps.findIndex(step => step.title === 'Touch, Click and Release');
  const down = sampledPose(animation, press, .5);
  assert.ok(down.plunger[11] < -.45);
  assert.deepEqual(down.sensor, down.paddle);
  assert.deepEqual(down.board, rest.board);
  assert.deepEqual(down.op1_latch, identity());
  const release = animation.steps.findIndex(step => step.title === 'Release the OP1 Latch');
  assert.equal(sampledPose(animation, release, 1).op1_latch[11], 7);
  assert.equal(sampledPose(animation, release + 1, 1).board[7], -33);
  for (let i = 1; i < animation.steps.length; i++) {
    const previous = animation.steps[i - 1].samples.at(-1);
    const next = animation.steps[i].samples[0];
    for (const actor of Object.keys(animation.actors)) {
      assert.ok(previous[actor].every((n, j) => Math.abs(n - next[actor][j]) < 1e-8), `${i}/${actor}`);
    }
  }
});

test('R26 copper insert stays locked for the click and slides out after disconnecting', () => {
  const dir = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', dir)));
  const url = new URL(catalog.versions.find(entry => entry.id === 'r26').guide, dir);
  const guide = JSON.parse(readFileSync(url));
  const { views } = groupKeys(guide.modules);
  const view = views.copper;
  validateGuide({ ...guide, modules: { copper: view } });
  const measured = JSON.parse(readFileSync(new URL('copper-insert-checks.json', url)));
  assert.equal(measured.passed, true);
  assert.equal(measured.touch_sensitivity_verified, false);
  assert.equal(measured.print_validated, false);
  const at = title => view.steps.findIndex(step => step.title === title);
  const press = at('Press and Release');
  const down = sampledPose(view, press, .5);
  assert.ok(down.plunger[11] < -.45);
  assert.deepEqual(down.foil, down.cap);
  assert.deepEqual(down.insert, down.cap);
  assert.deepEqual(down.terminal, identity());
  assert.deepEqual(sampledPose(view, press, 0).cap, sampledPose(view, press, 1).cap);
  const disconnect = at('Disconnect the Lead');
  assert.ok(disconnect < at('Lift the Cap Off') && disconnect < at('Slide the Insert Out'));
  assert.deepEqual(sampledPose(view, disconnect, 1).morphs.wire, [0, 0]);
  const removed = sampledPose(view, at('Slide the Insert Out'), 1);
  assert.ok(removed.insert[7] - removed.cap[7] > 17);
  assert.deepEqual(removed.foil, removed.insert);
  for (let i = 1; i < view.steps.length; i++) {
    const end = sampledPose(view, i - 1, 1), start = sampledPose(view, i, 0);
    assert.equal(JSON.stringify(end), JSON.stringify(start), view.steps[i].title);
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

test('R28 carries the DFR0030 on the R27 click behind a flat bottom and services it in place', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const url = new URL(catalog.versions.find(entry => entry.id === 'r28').guide, directory);
  const guide = JSON.parse(readFileSync(url));
  const { modules, views } = groupKeys(guide.modules);
  validateGuide({ ...guide, modules: views });
  assert.ok(modules.cable && modules.battery && modules.xiao);
  const sha = file => createHash('sha256').update(readFileSync(new URL(file, url))).digest('hex');
  for (const module of Object.values(guide.modules)) {
    for (const { file } of Object.values(module.actors)) if (file) assert.equal(guide.sources.meshes_sha256[file], sha(file), file);
  }
  const report = JSON.parse(readFileSync(new URL('geometry-checks.json', url)));
  const { checks } = report;
  assert.equal(checks.passed, true);
  assert.equal(report.print_validated, false);
  assert.equal(report.physical_fit_verified, false);
  assert.ok(checks.released_front_alignment_error_mm < .001);
  assert.ok(checks.min_front_clear_of_bottom_over_stroke_mm > .15);
  assert.ok(checks.side_clearance_to_choc_caps_mm >= .7);
  for (const key of Object.keys(checks).filter(key => key.endsWith('overlap_mm3'))) assert.ok(checks[key] < .035, key);
  const view = views.dfr;
  const end = sampledPose(view, view.steps.length - 1, 1);
  assert.deepEqual([0, 2, 3, 4].map(i => [end[`keycap_${i}`][3], end[`keycap_${i}`][7]]), checks.choc_centres_mm);
  for (const key of [0, 2]) {
    const front = Math.min(...view.actors[`keycap_${key}`].geometry.vertices.map(([, y]) => y)) + end[`keycap_${key}`][7];
    assert.ok(Math.abs(checks.released_front_mm - front) < .001);
  }
  const at = title => view.steps.findIndex(step => step.title === title);
  const press = at('Touch, Click and Release');
  const down = sampledPose(view, press, .5);
  assert.ok(down.plunger[11] < -.45);
  for (const id of ['sensor', 'electrode', 'connector', 'touch_pin']) assert.deepEqual(down[id], down.cap);
  assert.deepEqual(down.board, end.board);
  assert.ok(at('Unplug the Gravity Lead') < at('Push Out the Keeper Pin'));
  assert.ok(at('Push Out the Keeper Pin') < at('Slide Out the Touch Board'));
  const out = sampledPose(view, at('Slide Out the Touch Board'), 1);
  assert.deepEqual(out.cap, end.cap);
  assert.ok(out.sensor[7] - out.cap[7] > 40);
  for (let i = 1; i < view.steps.length; i++) {
    const before = view.steps[i - 1].samples.at(-1), after = view.steps[i].samples[0];
    for (const actor of Object.keys(view.actors)) {
      assert.ok(before[actor].every((n, j) => Math.abs(n - after[actor][j]) < 1e-8), `${view.steps[i].title}/${actor}`);
    }
  }
});

test('R29 tray arms bend their real vertices and snap their tabs into the fixed supports', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const url = new URL(catalog.versions.find(entry => entry.id === 'r29').guide, directory);
  const guide = JSON.parse(readFileSync(url));
  const { views } = groupKeys(guide.modules);
  validateGuide({ ...guide, modules: views });
  const { checks } = JSON.parse(readFileSync(new URL('geometry-checks.json', url)));
  assert.equal(checks.passed, true);
  assert.ok(checks.released_tab_axial_engagement_mm >= .6 && checks.squeezed_tab_clear_of_support_mm > .2);
  assert.ok(checks.straight_lift_retention_contact_mm3 > .04);
  assert.equal(Object.keys(checks.guard_runners).length, 6);
  for (const key of Object.keys(checks).filter(key => key.endsWith('overlap_mm3'))) assert.ok(checks[key] < .035, key);
  const view = views.dfr;
  assert.equal(view.actors.carrier.morphFile, undefined);
  const closeUp = guide.modules.snap_hinge;
  validateGuide({ ...guide, modules: { snap_hinge: closeUp } });
  assert.deepEqual(Object.keys(closeUp.actors).sort(), ['cap', 'carrier']);
  for (const step of closeUp.steps) {
    const full = view.steps.find(candidate => candidate.title === step.title);
    assert.equal(step.samples.length, full.samples.length);
    for (const [i, pose] of step.samples.entries()) {
      for (const field of ['cap', 'carrier', 'morphs']) assert.deepEqual(pose[field], full.samples[i][field]);
    }
  }
  const read = file => readFileSync(new URL(file, url));
  const rest = read(view.actors.cap.file), pinched = read(view.actors.cap.morphFile);
  assert.equal(rest.readUInt32LE(80), pinched.readUInt32LE(80));
  let moved = 0, most = 0;
  const movedSides = new Set();
  for (let triangle = 84; triangle < rest.length; triangle += 50) {
    for (const offset of [triangle + 12, triangle + 24, triangle + 36]) {
      const restX = rest.readFloatLE(offset);
      const pinchedX = pinched.readFloatLE(offset);
      assert.equal(pinched.readFloatLE(offset + 4), rest.readFloatLE(offset + 4));
      assert.equal(pinched.readFloatLE(offset + 8), rest.readFloatLE(offset + 8));
      const dx = Math.abs(pinchedX - restX);
      if (dx > 1e-6) {
        assert.ok(Math.abs(pinchedX) < Math.abs(restX));
        movedSides.add(Math.sign(restX));
        moved++;
      }
      most = Math.max(most, dx);
    }
  }
  assert.equal(movedSides.size, 2);
  assert.ok(moved > 0 && most > .95 && most < 1.15);
  const at = title => view.steps.findIndex(step => step.title === title);
  const lowered = view.steps[at('Lower Between the Supports')].samples;
  assert.ok(lowered.every(sample => sample.morphs.cap === 1));
  assert.equal(sampledPose(view, at('Let the Tabs Snap Into the Holes'), 1).morphs.cap, 0);
  assert.ok(at('Slide Out the Touch Board') < at('Pinch to Release the Tabs'));
  assert.ok(sampledPose(view, at('Lift Off the Empty Tray'), 1).cap[11] > 7);
  for (let i = 1; i < view.steps.length; i++) {
    const before = view.steps[i - 1].samples.at(-1), after = view.steps[i].samples[0];
    for (const actor of Object.keys(view.actors)) {
      assert.ok(before[actor].every((n, j) => Math.abs(n - after[actor][j]) < 1e-8), `${view.steps[i].title}/${actor}`);
    }
    assert.ok(Math.abs((before.morphs?.cap ?? 0) - (after.morphs?.cap ?? 0)) < 1e-8, `${view.steps[i].title} flex`);
  }
});

for (const [revision, hingeShift] of [['r30', 2], ['r31', 21.05]]) {
  test(`${revision.toUpperCase()} holds the DFR0030 through its two holes and the hinge detail beside Keys shows the same bracket`, () => {
    const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
    const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
    const version = catalog.versions.find(entry => entry.id === revision);
    assert.equal(version.groupKeys, true);
    const url = new URL(version.guide, directory);
    const guide = JSON.parse(readFileSync(url));
    const { modules, views } = groupKeys(guide.modules);
    validateGuide({ ...guide, modules: views });
    validateGuide({ ...guide, modules });
    assert.deepEqual(Object.keys(modules).slice(0, 2), ['keys', 'snap_hinge']);
    assert.equal(modules.keys.label, 'Keys · full assembly');
    assert.equal(modules.snap_hinge.label, 'Keys · snap hinge detail');
    assert.ok(modules.cable && modules.battery && modules.xiao);
    const sha = file => createHash('sha256').update(readFileSync(new URL(file, url))).digest('hex');
    for (const module of Object.values(guide.modules)) {
      for (const actor of Object.values(module.actors)) {
        for (const file of [actor.file, actor.morphFile].filter(Boolean)) assert.equal(guide.sources.meshes_sha256[file], sha(file), file);
      }
    }
    const report = JSON.parse(readFileSync(new URL('geometry-checks.json', url)));
    const { checks } = report;
    assert.equal(checks.passed, true);
    assert.equal(report.print_validated, false);
    assert.equal(report.physical_fit_verified, false);
    assert.deepEqual(checks.board_outline_mm, [22, 35]);
    for (const key of Object.keys(checks).filter(key => key.endsWith('overlap_mm3'))) assert.ok(checks[key] < .035, key);
    for (const value of Object.values(checks.board_on_posts_overlap_by_pitch_mm3)) assert.ok(value < .035);
    assert.ok(checks.board_lateral_capture_contact_mm3 > .04 && checks.board_along_capture_contact_mm3 > .04);
    assert.ok(checks.board_to_clip_lift_contact_mm3 > .04 && checks.clip_head_capture_contact_mm3 > .04);
    assert.ok(checks.released_tab_axial_engagement_mm >= .6 && checks.squeezed_tab_clear_of_support_mm > .2);
    assert.equal(Object.keys(checks.guard_runners).length, 6);
    const view = views.dfr;
    assert.equal(view.actors.touch_pin, undefined);
    assert.equal(view.actors.op1_latch, undefined);
    assert.equal(view.actors.keeper_pin, undefined);
    assert.ok(Math.abs(checks.hinge_moved_towards_two_key_end_mm - hingeShift) < 1e-8);
    assert.ok(view.actors.clip_left && view.actors.clip_right);
    const closeUp = guide.modules.snap_hinge;
    assert.deepEqual(Object.keys(closeUp.actors).sort(), ['cap', 'carrier']);
    assert.equal(closeUp.actors.cap.file, view.actors.cap.file);
    assert.equal(closeUp.actors.cap.morphFile, view.actors.cap.morphFile);
    assert.ok(closeUp.steps.length >= 6);
    for (const module of [view, closeUp]) {
      for (const annotation of module.annotations.filter(item => item.step)) {
        assert.equal(module.steps.filter(step => step.title === annotation.step).length, 1, annotation.title);
      }
    }
    for (const step of closeUp.steps) {
      const full = view.steps.find(candidate => candidate.title === step.title);
      assert.equal(step.samples.length, full.samples.length);
      for (const [i, pose] of step.samples.entries()) {
        for (const field of ['cap', 'carrier', 'morphs']) assert.deepEqual(pose[field], full.samples[i][field]);
      }
    }
    const at = title => view.steps.findIndex(step => step.title === title);
    const end = sampledPose(view, view.steps.length - 1, 1);
    for (const id of ['sensor', 'electrode', 'connector', 'clip_left', 'clip_right']) assert.deepEqual(end[id], end.cap);
    const down = sampledPose(view, at('Touch, Click and Release'), .5);
    assert.ok(down.plunger[11] < -.45);
    for (const id of ['sensor', 'electrode', 'connector', 'clip_left', 'clip_right']) assert.deepEqual(down[id], down.cap);
    assert.ok(at('Let the Tabs Snap Into the Holes') < at('Fit the Board Over the Posts'));
    assert.ok(at('Fit the Board Over the Posts') < at('Clip the Posts'));
    assert.ok(at('Pull Off the Clips') < at('Lift the Board Off the Posts'));
    assert.ok(at('Lift the Board Off the Posts') < at('Pinch to Release the Tabs'));
    const off = sampledPose(view, at('Lift the Board Off the Posts'), 1);
    assert.ok(off.sensor[11] - off.cap[11] > 10);
    assert.ok(view.steps[at('Lower Between the Supports')].samples.every(sample => sample.morphs.cap === 1));
    for (let i = 1; i < view.steps.length; i++) {
      const before = view.steps[i - 1].samples.at(-1), after = view.steps[i].samples[0];
      for (const actor of Object.keys(view.actors)) {
        assert.ok(before[actor].every((n, j) => Math.abs(n - after[actor][j]) < 1e-8), `${view.steps[i].title}/${actor}`);
      }
      assert.ok(Math.abs((before.morphs?.cap ?? 0) - (after.morphs?.cap ?? 0)) < 1e-8, `${view.steps[i].title} flex`);
    }
  });
}

test('R27 fits the copper keys closer and loads the OP1 behind a flat bottom', () => {
  const directory = new URL('../hardware/carbon-rod-holders/assembly/', import.meta.url);
  const catalog = JSON.parse(readFileSync(new URL('catalog.json', directory)));
  const version = catalog.versions.find(entry => entry.id === 'r27');
  const url = new URL(version.guide, directory);
  const guide = JSON.parse(readFileSync(url));
  const { modules, views } = groupKeys(guide.modules);
  validateGuide({ ...guide, modules: views });
  assert.ok(modules.cable && modules.battery && modules.xiao);
  assert.deepEqual(modules.keys.steps, views.copper.steps);
  const view = views.copper;
  const end = sampledPose(view, view.steps.length - 1, 1);
  const report = JSON.parse(readFileSync(new URL('geometry-checks.json', url)));
  assert.equal(report.checks.passed, true);
  assert.ok(report.checks.pcb_clear_of_bottom_mm >= .75);
  assert.equal(view.actors.cap.file, "Aligned_Copper_Cap.stl");
  for (const key of [0, 2]) {
    const front = Math.min(...view.actors[`keycap_${key}`].geometry.vertices.map(([, y]) => y))
      + end[`keycap_${key}`][7];
    assert.ok(Math.abs(report.checks.centre_cap_bottom_released_mm - front) < .001);
  }
  assert.ok(report.checks.min_cap_clear_of_bottom_over_stroke_mm > .15);
  assert.equal(report.checks.centre_cap_released_height_change_mm, 0);
  assert.ok(report.checks.foil_slide_overlap_mm3 < .001);
  assert.equal(report.checks.board_slide_overlap_mm3, 0);
  assert.equal(report.checks.click_and_lead_overlap_mm3, 0);
  assert.equal(report.print_validated, false);
  assert.deepEqual([0, 2, 3, 4].map(i => [end[`keycap_${i}`][3], end[`keycap_${i}`][7]]),
    report.checks.choc_centres_mm);
  assert.equal(end.board[5], -1);
  assert.ok(sampledPose(view, 0, 0).board[7] - end.board[7] >= 42);
  const press = view.steps.findIndex(step => step.title === 'Press and Release');
  const down = sampledPose(view, press, .5);
  assert.deepEqual(down.board, end.board);
  assert.deepEqual(down.foil, down.cap);
  assert.ok(down.plunger[11] < -.45);
  for (let i = 1; i < view.steps.length; i++) {
    assert.deepEqual(JSON.stringify(view.steps[i - 1].samples.at(-1)), JSON.stringify(view.steps[i].samples[0]),
      view.steps[i].title);
  }
});
