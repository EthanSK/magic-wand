// Exercise complete component recipes and the actual shared-menu inputs.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { validateGuide, sampledPose, identity, groupKeys } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';
import { legacyR20 } from '../hardware/carbon-rod-holders/assembly/legacy-r20.mjs';
import { UPPER_KEY_SHIFT } from '../hardware/carbon-rod-holders/assembly/keycap-concepts.mjs';

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
    'concept_slider', 'concept_flexure', 'concept_pivot', 'concept_direct', 'concept_carrier',
  ]);
  const seated = views.centre.steps.at(-1).samples.at(-1);
  for (const [id, view] of variants) {
    validateGuide({ ...guide, modules: { [id]: view } });
    const [rest, down, returned] = view.steps.map(step => step.samples.at(-1));
    assert.deepEqual(rest.cap, returned.cap);
    assert.notDeepEqual(rest.cap, down.cap);
    assert.equal(rest.plunger[11], 0);
    assert.ok(down.plunger[11] < 0);
    assert.deepEqual(rest.board, down.board);
    assert.equal(rest.board[5], -1);
    for (const key of [0, 2, 3, 4]) {
      const expected = [...seated[`keycap_${key}`]];
      if (id === 'concept_carrier' && key >= 3) expected[3] += key === 3 ? -UPPER_KEY_SHIFT : UPPER_KEY_SHIFT;
      assert.deepEqual(down[`keycap_${key}`], expected);
    }
    for (const actor of Object.values(view.actors)) {
      for (const mesh of [actor.geometry, actor.morphGeometry].filter(Boolean)) {
        assert.ok(mesh.vertices.flat().every(Number.isFinite));
        if (mesh.faces) assert.ok(mesh.faces.flat().every(i => i >= 0 && i < mesh.vertices.length));
      }
    }
  }
  const holder = views.concept_carrier;
  const motion = holder.steps.flatMap(step => step.samples);
  for (const id of ['cap', 'hinge', 'hingeSupports']) {
    for (const sample of motion) for (const [x, y, z] of holder.actors[id].geometry.vertices) {
      const m = sample[id];
      const along = y * m[5] + z * m[6] + m[7];
      if (along >= 17.8 - 17.5 / 2) assert.ok(Math.abs(x) <= 9.35 + UPPER_KEY_SHIFT - 16.6 / 2);
    }
  }
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
