import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

// Reproduce the actual Bluefruit characteristic clamp, including its misleading
// full-length return value. USB identity success cannot qualify Bluetooth.
test('Sense Bluetooth output preserves complete lines across real packet limits', () => {
  const folder = mkdtempSync(join(tmpdir(), 'wand-ble-output-'));
  try {
    const include = fileURLToPath(new URL('../device/sense/wand_sense/', import.meta.url));
    const fixture = fileURLToPath(new URL('./fixtures/sense-ble-output-main.cpp', import.meta.url));
    const binary = join(folder, 'check');
    const compile = spawnSync('c++', ['-std=c++17', '-I', include, fixture, '-o', binary], {encoding: 'utf8'});
    assert.equal(compile.status, 0, compile.stdout + compile.stderr);
    const run = spawnSync(binary, [], {encoding: 'utf8'});
    assert.equal(run.status, 0, run.stdout + run.stderr);
  } finally {
    rmSync(folder, {recursive: true, force: true});
  }
});
