// Exercise owned job cleanup and complete query batching without scientific
// dependencies or the original large workload. Keep this in the root check.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

test('geometry checks retain all query results and clean up owned jobs', () => {
  const suite = path.resolve(__dirname, '../../.agents/skills/printability-audit/tests/test_geometry_budget.py');
  const result = spawnSync('python3', ['-B', suite], { encoding: 'utf8', timeout: 30000 });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /geometry-budget-tests=16/);
});
