// Read the canonical assembly manifest and existing CAD mass receipts without
// rebuilding CAD. Run: node derive.mjs [--repo PATH] [--profile NAME]
// [--measurements private.json] or [--scenario NAME]. Output is JSON on stdout.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

function finite(value, label, minimum = -Infinity) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < minimum) {
    throw new Error(`${label} must be a finite number >= ${minimum}`);
  }
  return value;
}

function vector(value, label) {
  if (!Array.isArray(value) || value.length !== 3) throw new Error(`${label} needs X, Y, Z`);
  return value.map((v, i) => finite(v, `${label}[${i}]`));
}

/**
 * Unknown mass/position never turns into a zero-valued complete result.
 * @param {Array<{mass_g:number|null, centre_mm:number[]|null, intrinsic_x_g_mm2?:number|null}>} points
 * @param {number[]|null} pivot
 */
export function massProperties(points, pivot = null) {
  const missingMass = points.some(p => p.mass_g === null);
  const known = points.filter(p => p.mass_g !== null);
  known.forEach(p => finite(p.mass_g, 'mass_g', 0));
  const subtotal = known.reduce((sum, p) => sum + p.mass_g, 0);
  const complete = !missingMass && points.length > 0 && subtotal > 0;
  const positioned = complete && points.every(p => p.centre_mm !== null);
  const centre = positioned ? [0, 1, 2].map(axis => points.reduce(
    (sum, p) => sum + vector(p.centre_mm, 'centre_mm')[axis] * p.mass_g, 0) / subtotal) : null;
  const origin = pivot === null ? null : vector(pivot, 'grip_pivot_mm');
  return {
    known_subtotal_g: subtotal,
    total_g: complete ? subtotal : null,
    centre_of_mass_mm: centre,
    inertia_about_grip_x_g_mm2: positioned && origin
      && points.every(p => p.intrinsic_x_g_mm2 !== null) ? points.reduce((sum, p) => {
      const c = vector(p.centre_mm, 'centre_mm');
      return sum + p.mass_g * ((c[1] - origin[1]) ** 2 + (c[2] - origin[2]) ** 2)
        + finite(p.intrinsic_x_g_mm2 ?? 0, 'intrinsic_x_g_mm2', 0);
    }, 0) : null,
  };
}

export function tubeGeometry(outer, inner, length) {
  finite(outer, 'tube outside diameter', 0);
  finite(inner, 'tube inside diameter', 0);
  if (outer <= inner) throw new Error('Tube outside diameter must exceed inside diameter');
  if (length !== null) finite(length, 'tube length', 0);
  const area = Math.PI * (outer ** 2 - inner ** 2) / 4;
  return { outside_diameter_mm: outer, inside_diameter_mm: inner,
    wall_mm: (outer - inner) / 2, section_area_mm2: area,
    volume_cm3: length === null ? null : area * length / 1000 };
}

/** Compare a declared hypothetical tube and two lumped packages, in mm/g. */
export function lengthCase(outer, inner, length, density, tipMass, gripMass, grip) {
  finite(length, 'scenario tube length', Number.MIN_VALUE);
  const tube = tubeGeometry(outer, inner, length);
  finite(density, 'density', 0);
  finite(tipMass, 'tip mass', 0);
  finite(gripMass, 'grip mass', 0);
  finite(grip, 'grip distance from butt', 0);
  if (grip > length) throw new Error('Grip cannot be beyond the tube tip');
  const tubeMass = tube.volume_cm3 * density;
  const tubeIntrinsic = tubeMass * (length ** 2 + 3 * ((outer / 2) ** 2 + (inner / 2) ** 2)) / 12;
  const properties = massProperties([
    { mass_g: tubeMass, centre_mm: [0, length / 2, 0], intrinsic_x_g_mm2: tubeIntrinsic },
    { mass_g: tipMass, centre_mm: [0, length, 0] },
    { mass_g: gripMass, centre_mm: [0, grip, 0] },
  ], [0, grip, 0]);
  return { length_mm: length, tube_mass_g: tubeMass, ...properties,
    horizontal_gravity_torque_N_m: (tubeMass * (length / 2 - grip)
      + tipMass * (length - grip)) * 9.80665 / 1e6 };
}

export function deriveScenario(manifestPath, repo, name) {
  const scenario = json(manifestPath).scenarios[name];
  if (!scenario) throw new Error(`Unknown scenario: ${name}`);
  const { rod } = json(resolve(repo, scenario.tube_parameters));
  const evaluate = (length, grip, tip) => lengthCase(rod.diameter, rod.inside_diameter,
    length, scenario.density_g_cm3, tip, scenario.near_grip_package_g, grip);
  const baseline = evaluate(scenario.baseline_length_mm, scenario.grip_from_butt_mm, scenario.tip_package_g);
  if (!(baseline.inertia_about_grip_x_g_mm2 > 0)) throw new Error('Scenario needs nonzero baseline inertia');
  const cases = scenario.candidate_lengths_mm.map(length => {
    const central = evaluate(length, scenario.grip_from_butt_mm, scenario.tip_package_g);
    const ratios = scenario.range_inputs.grip_from_butt_mm.flatMap(grip =>
      scenario.range_inputs.tip_package_g.map(tip => evaluate(length, grip, tip).inertia_about_grip_x_g_mm2
        / evaluate(scenario.baseline_length_mm, grip, tip).inertia_about_grip_x_g_mm2));
    return { ...central, inertia_fraction_of_baseline: central.inertia_about_grip_x_g_mm2
      / baseline.inertia_about_grip_x_g_mm2,
      endpoint_envelope_fraction: [Math.min(...ratios), Math.max(...ratios)] };
  });
  return { scenario: name, assumptions: scenario, baseline, cases };
}

function json(path) { return JSON.parse(readFileSync(path, 'utf8')); }
function pointer(data, path) {
  return path.split('/').slice(1).reduce((v, key) => v?.[key.replaceAll('~1', '/').replaceAll('~0', '~')], data);
}

export function derive(manifestPath, repo, profileName, supplied = null) {
  const manifest = json(manifestPath);
  if (manifest.schema_version !== 1) throw new Error('Unsupported blueprint schema');
  const profile = manifest.profiles[profileName];
  if (!profile) throw new Error(`Unknown profile: ${profileName}`);
  const measurements = supplied ?? (profileName === 'physical-current' ? manifest.physical_measurements : {});
  if (!measurements || typeof measurements !== 'object' || Array.isArray(measurements)) {
    throw new Error('Measurements must be an object');
  }
  const entries = measurements.components ?? {};
  const knownIds = new Set(profile.components.map(c => c.id));
  for (const id of Object.keys(entries)) if (!knownIds.has(id)) throw new Error(`Unknown component: ${id}`);
  const sourceChecks = [];
  const sha = path => createHash('sha256').update(readFileSync(path)).digest('hex');
  let params = null;
  if (profile.parameters) {
    params = json(resolve(repo, profile.parameters));
    const path = resolve(repo, profile.geometry_manifest);
    const geometry = json(path);
    for (const [relative, expected] of Object.entries(geometry.source_sha256)) {
      const actual = sha(resolve(dirname(path), '..', relative));
      if (actual !== expected) throw new Error(`Stale geometry source: ${relative}`);
      sourceChecks.push(relative);
    }
    const receipt = json(resolve(repo, profile.components.find(c => c.mass_ref).mass_ref.path));
    if (sha(resolve(repo, profile.sliced_archive)) !== receipt.archive_sha256) {
      throw new Error('Sliced archive does not match mass receipt');
    }
  }
  const length = measurements.tube_length_mm ?? null;
  const diameters = measurements.tube_diameters_mm;
  if (diameters && (!diameters.evidence || !['measured', 'supplier', 'estimate'].includes(diameters.basis))) {
    throw new Error('Tube dimensions require evidence and measured/supplier/estimate basis');
  }
  const tube = diameters ? tubeGeometry(diameters.outside, diameters.inside, length)
    : params ? tubeGeometry(params.rod.diameter, params.rod.inside_diameter, length) : null;
  const rows = profile.components.map(c => {
    if (!Number.isInteger(c.quantity) || c.quantity < 1) throw new Error(`Invalid quantity: ${c.id}`);
    const input = entries[c.id];
    let mass = null;
    let basis = 'unknown';
    if (input?.mass_g !== null && input?.mass_g !== undefined) {
      if (!input.evidence || !['measured', 'supplier', 'estimate'].includes(input.basis)) {
        throw new Error(`${c.id}: supplied mass requires evidence and measured/supplier/estimate basis`);
      }
      // Enter the group's fitted mass, e.g. all three switches together.
      mass = finite(input.mass_g, `${c.id} group mass`, 0);
      basis = input.basis;
    } else if (c.mass_ref) {
      mass = finite(pointer(json(resolve(repo, c.mass_ref.path)), c.mass_ref.pointer), c.id, 0) * c.quantity;
      basis = 'slicer_estimate';
    } else if (manifest.products[c.id]?.mass_g != null) {
      const product = manifest.products[c.id];
      if (!product.source) throw new Error(`${c.id}: product mass requires its supplier source`);
      mass = finite(product.mass_g, `${c.id} supplier unit mass`, 0) * c.quantity;
      basis = 'supplier';
    }
    const centre = input?.centre_mm == null ? null : vector(input.centre_mm, c.id);
    // A tube must not silently become a point mass when its length is unknown.
    let intrinsic = c.id === 'tube' ? null : 0;
    if (c.id === 'tube' && mass !== null && length !== null && tube) {
      // Uniform hollow cylinder, longitudinal axis Y; transverse inertia X.
      intrinsic = mass * (3 * ((tube.outside_diameter_mm / 2) ** 2
        + (tube.inside_diameter_mm / 2) ** 2) + length ** 2) / 12;
    } else if (input?.intrinsic_x_g_mm2 !== undefined) {
      intrinsic = finite(input.intrinsic_x_g_mm2, 'intrinsic_x_g_mm2', 0);
    }
    return { id: c.id, quantity: c.quantity, mass_g: mass, basis, centre_mm: centre,
      intrinsic_x_g_mm2: intrinsic };
  });
  // Tube dimensions in the unmeasured physical profile deliberately remain
  // unbound: a purchased nominal tube is not a measured fitted tube.
  return { profile: profileName, status: profile.status, source_checks: sourceChecks,
    tube, components: rows, missing_mass: rows.filter(r => r.mass_g === null).map(r => r.id),
    ...massProperties(rows, measurements.grip_pivot_mm ?? null),
    limitations: manifest.model_limits };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const options = {};
  while (args.length) {
    const key = args.shift();
    if (!['--repo', '--profile', '--measurements', '--scenario'].includes(key) || !args.length) {
      throw new Error('Usage: node derive.mjs [--repo PATH] [--profile NAME] [--measurements PATH] [--scenario NAME]');
    }
    options[key] = args.shift();
  }
  const here = dirname(fileURLToPath(import.meta.url));
  const manifestPath = resolve(here, 'manifest.json');
  const manifest = json(manifestPath);
  const repo = options['--repo'] ?? resolve(here, '../../..');
  if (options['--scenario'] && (options['--profile'] || options['--measurements'])) {
    throw new Error('Choose a hypothetical scenario or a measured profile, not both');
  }
  console.log(JSON.stringify(options['--scenario'] ? deriveScenario(manifestPath, repo, options['--scenario'])
    : derive(manifestPath, repo,
    options['--profile'] ?? manifest.default_profile,
    options['--measurements'] ? json(options['--measurements']) : null), null, 2));
}
