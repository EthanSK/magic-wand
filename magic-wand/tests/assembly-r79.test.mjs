import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { validateGuide } from '../hardware/carbon-rod-holders/assembly/assembly-data.mjs';

const root = new URL('../hardware/carbon-rod-holders-r79-hinge-release/exports/', import.meta.url);
const read = path => JSON.parse(readFileSync(new URL(path, root)));
const hash = path => createHash('sha256').update(readFileSync(new URL(path, root))).digest('hex');
const guide = validateGuide(read('assembly-guide.json'));
const fit = read('fit79.json');
const frame = read('print-mechanisms/layout.frame.json').parts;
const pkg = read('print-mechanisms/print-only.json');

test('R79 shows and slices both actual pre-spring clips and the reinforced carrier', () => {
  assert.equal(guide.revision, 'R79');
  for (const [file, digest] of Object.entries(guide.sources.meshes_sha256)) assert.equal(hash(file), digest);
  for (const side of ['Left','Right']) {
    const name = 'DFR_Clip_' + side;
    const original = '../../carbon-rod-holders-r59-flipped-guard/exports/' + name + '-assembly.stl';
    assert.equal(frame[name].source_sha256, hash(original));
    assert.equal(fit.clips[side].mesh_sha256, hash(original));
    for (const id of ['dfr','pin_hinge']) {
      const mod = guide.modules[id];
      assert.equal(hash(mod.actors['clip_'+side.toLowerCase()].file), hash(original));
      assert.doesNotMatch(mod.steps.find(step => step.title === 'Slide on the two small clips').caption, /feet|spring/i);
    }
  }
  assert.equal(hash('Key_Carrier-assembly.stl'), frame.Key_Carrier.source_sha256);
  assert.deepEqual(Object.keys(frame).sort(), guide.print_components.keys.toSorted());
  assert.equal(frame.Touch_Paddle, undefined);
  assert.ok(guide.modules.pin_hinge.actors.cap);
  assert.ok(pkg.gcode_bytes_unchanged);
  assert.equal(hash('print-mechanisms/'+pkg.file),pkg.sha256);
});

test('fixed pin ears and both flat clip mouths stay open in both native slices', () => {
  for (const prefix of ['', 'reopened-']) {
    const reports = name => read('print-mechanisms/'+prefix+name+'.json');
    const parts = reports('fit').parts;
    for (const side of ['Left','Right']) {
      const bore = parts.Key_Carrier['pin_go_gauge_through_'+side.toLowerCase()+'_cheek'];
      assert.ok(bore.nearby_samples > 25);
      assert.deepEqual(bore.obstructed_poses, []);
      const clip = parts['DFR_Clip_'+side];
      assert.deepEqual(clip.post_clip_bore_and_mouth.obstructed_poses, []);
      assert.deepEqual(clip.post_head_during_slide.obstructed_poses, []);
    }
    assert.equal(reports('fin-design').fins_on_hinge, 0);
    assert.equal(reports('layers').native_support_moves, 0);
  }
});

test('the release-tab measurements match the shipped carrier and both native archives', () => {
  const hinge = read('hinge79.json');
  assert.equal(hinge.carrier_sha256, frame.Key_Carrier.source_sha256);
  const slices = read('print-mechanisms/review.json').slices;
  for (const [prefix, slice] of [['', slices.primary], ['reopened-', slices.reopened]]) {
    const contacts = read('print-mechanisms/' + prefix + 'release-contacts.json');
    assert.equal(contacts.archive_sha256, slice.archive_sha256);
    const tabs = contacts.replacement_contacts_mm2;
    const oldRight = contacts.r78_contacts_mm2['+y at 17'];
    const right = tabs['+y at 17'];
    assert.ok(right > 0 && right < oldRight / 2);
    assert.ok(Math.abs(right - tabs['+y at -17']) < 0.4);
    assert.equal(Object.keys(tabs).filter(name => name !== 'hinge_bay').length, 6);
  }
});
