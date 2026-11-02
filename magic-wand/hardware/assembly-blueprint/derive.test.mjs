// Focused checks for unknown-data handling and the blueprint's physical units.
import test from 'node:test';
import assert from 'node:assert/strict';
import { massProperties, tubeGeometry, lengthCase } from './derive.mjs';

test('unknown mass never becomes an assembled total or balance claim', () => {
  const result = massProperties([{ mass_g: 2, centre_mm: [0, 10, 0] },
    { mass_g: null, centre_mm: null }], [0, 0, 0]);
  assert.equal(result.known_subtotal_g, 2);
  assert.equal(result.total_g, null);
  assert.equal(result.centre_of_mass_mm, null);
  assert.equal(result.inertia_about_grip_x_g_mm2, null);
});

test('centre of mass and pivot inertia use mass weighting and parallel-axis rule', () => {
  const points = [{ mass_g: 2, centre_mm: [0, 0, 0], intrinsic_x_g_mm2: 4 },
    { mass_g: 1, centre_mm: [0, 30, 0] }];
  assert.deepEqual(massProperties(points, [0, 0, 0]), {
    known_subtotal_g: 3, total_g: 3, centre_of_mass_mm: [0, 10, 0],
    inertia_about_grip_x_g_mm2: 904,
  });
  assert.equal(massProperties(points, [0, 10, 0]).inertia_about_grip_x_g_mm2, 604);
});

test('an 8/7 mm tube is hollow and unknown length remains unknown', () => {
  const short = tubeGeometry(8, 7, 300);
  const long = tubeGeometry(8, 7, 500);
  assert.equal(short.wall_mm, 0.5);
  assert.ok(Math.abs(long.volume_cm3 - 5.89048622548) < 1e-10);
  assert.ok(Math.abs(short.volume_cm3 / long.volume_cm3 - 0.6) < 1e-10);
  assert.equal(tubeGeometry(8, 7, null).volume_cm3, null);
  assert.throws(() => tubeGeometry(7, 8, 500));
  assert.throws(() => massProperties([{ mass_g: NaN, centre_mm: [0, 0, 0] }]));
});

test('unknown tube extent blocks inertia without hiding a measured total', () => {
  const value = massProperties([{ mass_g: 9, centre_mm: [0, 200, 0],
    intrinsic_x_g_mm2: null }], [0, 0, 0]);
  assert.equal(value.total_g, 9);
  assert.deepEqual(value.centre_of_mass_mm, [0, 200, 0]);
  assert.equal(value.inertia_about_grip_x_g_mm2, null);
});

test('hypothetical length comparison keeps packages and units explicit', () => {
  const long = lengthCase(8, 7, 500, 1.6, 4, 17, 90);
  const short = lengthCase(8, 7, 300, 1.6, 4, 17, 90);
  assert.ok(Math.abs(long.tube_mass_g - 9.42477796077) < 1e-10);
  assert.ok(Math.abs(long.horizontal_gravity_torque_N_m - 0.030871) < 1e-7);
  assert.ok(short.inertia_about_grip_x_g_mm2 / long.inertia_about_grip_x_g_mm2 > 0.20);
  assert.ok(short.inertia_about_grip_x_g_mm2 / long.inertia_about_grip_x_g_mm2 < 0.23);
  // The assumed near-grip mass affects total mass, but at this declared pivot
  // it must not falsely contribute rotational inertia or gravity torque.
  const heavyGrip = lengthCase(8, 7, 500, 1.6, 4, 34, 90);
  assert.equal(heavyGrip.inertia_about_grip_x_g_mm2, long.inertia_about_grip_x_g_mm2);
  assert.equal(heavyGrip.horizontal_gravity_torque_N_m, long.horizontal_gravity_torque_N_m);
  assert.throws(() => lengthCase(8, 7, 50, 1.6, 4, 17, 90));
});
