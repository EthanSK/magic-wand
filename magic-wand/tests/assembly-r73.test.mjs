// The fourth tip must come into the body like the other three while the wired
// lower socket still slides in. Bind both measurements to what the viewer loads.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {validateGuide} from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const current = new URL('../hardware/carbon-rod-holders-r73-inset-guard/exports/', import.meta.url);
const previous = new URL('../hardware/carbon-rod-holders-r72-inboard-battery/exports/', import.meta.url);
const json = url => JSON.parse(readFileSync(url));

test('R73 guard enters the rounded lower edge and leaves the fitted socket routes clear', () => {
  const report = json(new URL('fit73.json', current));
  const sha = createHash('sha256').update(readFileSync(new URL('Key_Carrier-assembly.stl', current))).digest('hex');
  assert.equal(report.carrier_sha256, sha);
  assert.ok(report.r72_edge.protrusion_mm > .75);
  assert.ok(report.r73_edge.protrusion_mm < .05);
  assert.ok(report.maximum_branch_forward_of_reference_mm < .10);
  assert.ok(report.minimum_exported_rail_section_mm2 > 3.9);
  assert.deepEqual(report.key_hits, []);
  assert.equal(report.key_poses, 336);
  assert.equal(report.passes, true);
});

test('R73 viewer uses the corrected guard with every R72 assembly motion and purchased part', () => {
  const guide = validateGuide(json(new URL('assembly-guide.json', current)));
  const old = validateGuide(json(new URL('assembly-guide.json', previous)));
  assert.equal(guide.revision, 'R73');
  const catalogUrl = new URL('../hardware/carbon-rod-holders/assembly/catalog.json', import.meta.url);
  const catalog = json(catalogUrl);
  const entry = catalog.versions.find(version => version.id === 'r73');
  assert.equal(new URL(entry.guide, catalogUrl).href, new URL('assembly-guide.json', current).href);
  const revisions = catalog.versions.map(version => /^r(\d+)$/.exec(version.id)).filter(Boolean);
  const newest = Math.max(...revisions.map(match => Number(match[1])));
  assert.equal(catalog.versions[0].id, catalog.current);
  assert.equal(catalog.current, 'r' + newest);
  for (const [key, module] of Object.entries(guide.modules)) {
    assert.deepEqual(module.steps, old.modules[key].steps);
  }
  for (const [name, digest] of Object.entries(guide.sources.meshes_sha256)) {
    assert.equal(createHash('sha256').update(readFileSync(new URL(name,current))).digest('hex'), digest);
  }
});
