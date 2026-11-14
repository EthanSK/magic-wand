import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, mkdir, rm, utimes, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

test('a normal reload gets current viewer scripts even when their timestamp is unchanged', { timeout: 10_000 }, async t => {
  const directory = await mkdtemp(join(tmpdir(), 'wand-assembly-'));
  const viewer = join(directory, 'magic-wand/hardware/carbon-rod-holders/assembly');
  const shared = join(directory, 'magic-wand/hardware/printed-loop-wand/preview');
  const dependency = join(shared, 'controls.mjs');
  const timestamp = new Date('2025-01-01T00:00:00Z');
  t.after(() => rm(directory, { recursive: true, force: true }));
  await mkdir(viewer, { recursive: true });
  await mkdir(shared, { recursive: true });
  await writeFile(join(viewer, 'index.html'), '<script type="module" src="viewer.mjs"></script>');
  await writeFile(join(viewer, 'viewer.mjs'), 'import "../../printed-loop-wand/preview/controls.mjs";');
  await writeFile(dependency, 'document.title = "old";');
  await utimes(dependency, timestamp, timestamp);

  const launcher = fileURLToPath(new URL('../scripts/serve_assembly.py', import.meta.url));
  const server = spawn('python3', [launcher, '--port', '0', '--directory', directory],
    { stdio: ['ignore', 'pipe', 'inherit'] });
  await once(server, 'spawn', { signal: t.signal });
  const lines = createInterface({ input: server.stdout });
  t.after(async () => {
    lines.close();
    if (server.kill()) await once(server, 'exit');
  });
  const [url] = await once(lines, 'line', { signal: t.signal });
  for (const path of ['', 'viewer.mjs']) {
    const response = await fetch(new URL(path, url));
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    await response.arrayBuffer();
  }

  const moduleUrl = new URL('../../printed-loop-wand/preview/controls.mjs', url);
  const initial = await fetch(moduleUrl);
  assert.equal(await initial.text(), 'document.title = "old";');
  const lastModified = initial.headers.get('last-modified');
  assert.equal(lastModified, timestamp.toUTCString());

  await writeFile(dependency, 'document.title = "new";');
  await utimes(dependency, timestamp, timestamp);
  const refreshed = await fetch(moduleUrl, { headers: { 'If-Modified-Since': lastModified } });
  assert.equal(refreshed.status, 200);
  assert.equal(refreshed.headers.get('cache-control'), 'no-store');
  assert.equal(await refreshed.text(), 'document.title = "new";');
});
