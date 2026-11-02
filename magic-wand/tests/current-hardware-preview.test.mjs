// Exercise the permanent holder viewer's update and recovery behavior without WebGL.
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { followCurrent, modelURL, watchCurrent } from '../hardware/carbon-rod-holders/preview/current.mjs';

const base = 'http://localhost/magic-wand/hardware/carbon-rod-holders/preview/';
const record = (revision, hash = 'a') => ({ revision, scene_sha256: hash.repeat(64) });

test('an already-open visible viewer detects updates without a focus change', () => {
  const browserWindow = new EventTarget();
  const browserDocument = new EventTarget();
  browserDocument.hidden = false;
  const timers = new Map();
  let next = 0, checks = 0;
  browserWindow.setInterval = (callback, delay) => {
    assert.equal(delay, 1000);
    timers.set(++next, callback);
    return next;
  };
  browserWindow.clearInterval = id => timers.delete(id);
  watchCurrent(() => checks++, browserWindow, browserDocument);
  assert.equal(checks, 1);
  timers.values().next().value();
  assert.equal(checks, 2, 'visible-page update checking must not depend on focus');
  browserWindow.dispatchEvent(new Event('focus'));
  assert.equal(timers.size, 1, 'focus must not create duplicate watchers');
  browserDocument.hidden = true;
  browserDocument.dispatchEvent(new Event('visibilitychange'));
  assert.equal(timers.size, 0, 'hidden viewers must stop regular checks');
  browserDocument.hidden = false;
  browserDocument.dispatchEvent(new Event('visibilitychange'));
  assert.equal(checks, 4);
  assert.equal(timers.size, 1);
  browserWindow.dispatchEvent(new Event('pagehide'));
  assert.equal(timers.size, 0);
});

test('the current viewer keeps its camera until the generated model changes', async () => {
  let value = record('carbon-rod-holders-r11-average-thumb');
  const loads = [];
  let reloads = 0;
  const frame = { set src(url) { loads.push(url); }, hidden: true };
  const status = { hidden: false };
  const refresh = followCurrent({ frame, status, base, reload: () => reloads++, fetchCurrent: async (url, options) => {
    assert.equal(url.href, `${base}current.json`);
    assert.equal(options.cache, 'no-store');
    return { ok: true, json: async () => value };
  } });
  await refresh();
  const first = loads[0];
  await refresh();
  assert.equal(loads.length, 1, 'unchanged refresh must not reload the inspection camera');
  value = record('carbon-rod-holders-r12-next-model', 'b');
  await refresh();
  assert.equal(loads.length, 1, 'retain the current embedded model until its fresh page loads');
  assert.equal(reloads, 1, 'a changed revision refreshes the same permanent page');
  assert.match(first, /r11-average-thumb\/preview\/\?v=a{64}$/);
  assert.equal(status.hidden, true);
});

test('a failed update preserves the working model and can recover on the next check', async () => {
  let failed = false;
  const frame = { hidden: true };
  const status = {};
  const refresh = followCurrent({ frame, status, base, fetchCurrent: async () => {
    if (failed) throw new Error('offline');
    return { ok: true, json: async () => record('carbon-rod-holders-r11-average-thumb') };
  } });
  await refresh();
  const previous = frame.src;
  failed = true;
  await refresh();
  assert.equal(frame.src, previous);
  assert.equal(frame.hidden, false);
  assert.equal(status.hidden, false);
  assert.match(status.textContent, /offline/);
  failed = false;
  await refresh();
  assert.equal(status.hidden, true);
});

test('invalid pointers cannot navigate the model frame to an unrelated page', () => {
  for (const revision of ['../../other', 'https://example.com', 'carbon-rod-holders-r11-x/../../x']) {
    assert.throws(() => modelURL(record(revision), base), /Invalid model revision/);
  }
  assert.throws(() => modelURL({ revision: 'carbon-rod-holders-r11-x', scene_sha256: 'bad' }, base));
});

test('regenerating an archived model cannot roll the current viewer backward', () => {
  const publisher = fileURLToPath(new URL('../hardware/carbon-rod-holders/preview/publish.py', import.meta.url));
  execFileSync('python3', ['-c', `
from pathlib import Path
import importlib.util,json,tempfile
spec=importlib.util.spec_from_file_location('publisher',${JSON.stringify(publisher)})
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);dest=root/'current';dest.mkdir()
 for name in ['carbon-rod-holders-r11-average-thumb','carbon-rod-holders-r12-next-model']:
  revision=root/name;(revision/'exports').mkdir(parents=True)
  (revision/'exports/review-scene.json').write_text(json.dumps({'parameters':{'revision':name}}))
  p.publish(revision,dest)
 newer=(dest/'current.json').read_bytes()
 p.publish(root/'carbon-rod-holders-r11-average-thumb',dest)
 assert (dest/'current.json').read_bytes()==newer
 assert not (dest/'current.json.tmp').exists()
`]);
});
