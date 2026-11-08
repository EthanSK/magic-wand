// Source/scene integrity and assembly placement only. These checks do not establish printed fit.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const here = path.resolve(__dirname, '../hardware/carbon-rod-holders-r16-repair');
const read = name => JSON.parse(fs.readFileSync(path.resolve(here, name), 'utf8'));
const hash = name => crypto.createHash('sha256').update(fs.readFileSync(path.resolve(here, name))).digest('hex');
const near = (a, b) => assert.ok(Math.abs(a - b) < 0.0001, `${a} != ${b}`);

test('R16 viewer uses the checked exports, current references and one axial assembly', () => {
  const scene = read('exports/review-scene.json');
  const manifest = read('exports/manifest.json');
  const geometry = read('exports/geometry-checks.json');
  const printed = read('exports/R16-A1-mini-PETG-print-checks.json');
  assert.deepEqual(scene.manifest, manifest);
  assert.equal(scene.parameters.revision, manifest.revision);
  for (const [key, file] of Object.entries({
    generator_sha256: 'build_preview.py', renderer_sha256: 'preview/preview.mjs',
    html_sha256: 'preview/index.html', manifest_sha256: 'exports/manifest.json',
    geometry_encoder_sha256: '../carbon-rod-holders-r12-closer-thumb/build_preview.py',
    project_sha256: `exports/${printed.sliced_project_filename}`,
  })) assert.equal(scene.sources[key], hash(file), key);
  assert.deepEqual(Object.keys(scene.sources.assembly_mesh_sha256).sort(), Object.keys(manifest.parts).sort());
  for (const [name, digest] of Object.entries(scene.sources.assembly_mesh_sha256)) {
    assert.equal(digest, hash(`exports/${name}-assembly.stl`));
    const vertices = scene.geometry[name].vertices;
    assert.ok(vertices.length > 0 && scene.geometry[name].faces.length > 0, name);
    for (let axis = 0; axis < 3; axis++) {
      near(vertices.reduce((v, p) => Math.min(v, p[axis]), Infinity), manifest.parts[name].bounds_mm[0][axis]);
      near(vertices.reduce((v, p) => Math.max(v, p[axis]), -Infinity), manifest.parts[name].bounds_mm[1][axis]);
    }
  }
  assert.equal(scene.key_positions.length, 5);
  assert.deepEqual(scene.key_rotations_degrees, geometry.parts.Key_Carrier.key_rotations_degrees);
  const keys = manifest.parts.Key_Carrier.bounds_mm;
  const battery = manifest.parts.Battery_Holder.bounds_mm;
  const sensor = manifest.parts.XIAO_Rod_Holder.bounds_mm;
  const gap = scene.parameters.assembly.battery_end_clearance;
  near(scene.battery_poses['two-toward-tip'].y, keys[1][1] + gap + battery[1][1]);
  near(scene.battery_poses['three-toward-tip'].y, -keys[0][1] + gap + battery[1][1]);
  near(scene.xiao_y, scene.battery_poses['two-toward-tip'].y - battery[0][1] + gap - sensor[0][1]);
  assert.equal(scene.mass.source, printed.sliced_project_filename);
  assert.ok(Number.isFinite(scene.mass.total_g) && scene.mass.total_g > 0);
  const current = read('../carbon-rod-holders/preview/current.json');
  if (current.revision === manifest.revision) assert.equal(current.scene_sha256, hash('exports/review-scene.json'));
});
