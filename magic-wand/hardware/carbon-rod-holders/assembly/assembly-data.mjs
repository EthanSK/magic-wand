// Render the same discrete poses used by the owning model's assembly checks.
// Keep all components in one menu; adding a component to its guide includes it
// here without maintaining another list of model names in the user interface.
import { potentialKeyViews } from './keycap-concepts.mjs?v=cirque-cap-view';

export const identity = () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0];
export const translated = (x = 0, y = 0, z = 0) => [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z];

export function sampledPose(module, index, fraction) {
  if (!Number.isInteger(index) || !module.steps[index] || !Number.isFinite(fraction)) throw new TypeError('Invalid assembly step');
  const samples = module.steps[index].samples;
  return samples[Math.round(Math.max(0, Math.min(1, fraction)) * (samples.length - 1))];
}

// Milky-white Choc slim keycap (Adafruit 5737). Use the project’s 16.6 × 17.5 mm
// Choc outline, which agrees with the vendor's quarter-scale photo. The exposed
// cap height above the illustrative switch stem is a mounted-photo estimate.
// https://www.adafruit.com/product/5737
const CHOC_STEM_TOP = 8.05;
const CHOC_CAP_RISE = 3;
const CHOC_CAP_OUTLINE = [16.6, 17.5];

function chocCapGeometry(base = CHOC_STEM_TOP, top = CHOC_STEM_TOP + CHOC_CAP_RISE, skirt = .85) {
  const [halfX, halfY] = CHOC_CAP_OUTLINE.map(size => size / 2);
  const corners = (inset, z) => [
    [-halfX + inset, -halfY + inset, z], [halfX - inset, -halfY + inset, z],
    [halfX - inset, halfY - inset, z], [-halfX + inset, halfY - inset, z],
  ];
  const vertices = [
    ...corners(0, base), ...corners(0, base + skirt),
    ...corners(1.45, top), [0, 0, top - .25],
  ];
  const faces = [[0, 2, 1], [0, 3, 2]];
  for (let i = 0; i < 4; i++) {
    const j = (i + 1) % 4;
    faces.push([i, j, j + 4], [i, j + 4, i + 4]);
    faces.push([i + 4, j + 4, j + 8], [i + 4, j + 8, i + 8]);
    faces.push([i + 8, j + 8, 12]);
  }
  return { vertices, faces };
}

export function groupKeys(modules) {
  const { key, centre, centre_shallow, centre_deep, dfr, ...others } = modules;
  const seated = key.steps.at(-1).samples.at(-1);
  const sockets = Object.fromEntries(Object.entries(key.actors).filter(([id]) => id.startsWith('socket_')));
  const socketPoses = Object.fromEntries(Object.keys(sockets).map(id => [id, seated[id]]));
  const capGeometry = chocCapGeometry();
  const caps = {}, capPoses = {};
  for (const id of Object.keys(key.actors).filter(id => id.startsWith('switch_'))) {
    const capId = id.replace('switch_', 'keycap_');
    caps[capId] = { label: 'Choc keycap (reference)', color: '#e5dbc9', geometry: capGeometry };
    capPoses[capId] = seated[id];
  }
  const liftedCaps = height => Object.fromEntries(Object.entries(capPoses).map(([id, pose]) => {
    const lifted = [...pose];
    lifted[11] += height;
    return [id, lifted];
  }));
  const capFit = {
    title: 'Fit the Keycaps',
    caption: 'Line up the two pegs on each outer cap and press it straight onto its Choc stem.',
    duration: 2,
    samples: Array.from({ length: 25 }, (_, index) => ({ ...seated, ...liftedCaps(18 * (1 - index / 24)) })),
  };
  const keySteps = key.steps.map(step => ({
    ...step,
    samples: step.samples.map(pose => ({ ...pose, ...liftedCaps(18) })),
  }));

  function paddleView(module, label) {
    const actors = { ...sockets, ...module.actors, ...caps };
    // The centre installation guide already carries the four seated switches.
    // Include them in the camera bounds when the keys are shown together.
    for (const id of Object.keys(actors).filter(id => id.startsWith('switch_'))) {
      actors[id] = { ...actors[id], frame: true };
    }
    const steps = module.steps.map(step => ({
      ...step,
      samples: step.samples.map(pose => ({ ...socketPoses, ...pose, ...capPoses })),
    }));
    const note = 'The Choc caps use a reference shape and estimated seated height. The OP1 board, plug and switch also use estimated dimensions.';
    return { ...module, label, note, actors, steps, openSeated: true, rotation: [.92, 0, .34] };
  }

  const fitChoc = {
    ...key, label: 'Fit Choc switches and caps', note: 'Fit the outer switches and sockets, then press on the four keycaps.',
    actors: { ...key.actors, ...caps }, steps: [...keySteps, capFit],
  };
  const views = dfr ? {
    dfr: { ...paddleView(dfr, dfr.label), note: dfr.note }, key: fitChoc,
  } : {
    centre: paddleView(centre, 'Standard paddle'),
    centre_shallow: paddleView(centre_shallow, 'Shallow paddle'),
    centre_deep: paddleView(centre_deep, 'Deep paddle'),
    key: fitChoc,
  };
  if (!dfr) Object.assign(views, potentialKeyViews(views.centre, chocCapGeometry(18.7, 19.92, .3)));
  // Model-specific helper actions name the actors they affect. The viewer can
  // add controls from this data without knowing which parts make up a model.
  const otherKeycaps = {
    id: 'other-keycaps', hideLabel: 'Hide other keycaps', showLabel: 'Show other keycaps', actors: Object.keys(caps),
  };
  for (const view of Object.values(views)) view.helperActions = [otherKeycaps];
  return { modules: { keys: { ...(views.dfr ?? views.centre), label: 'Keys' }, ...others }, views };
}

export function validateGuide(guide) {
  if (guide.schema_version !== 2 || guide.units !== 'mm' || !guide.modules || !Object.keys(guide.modules).length) throw new Error('Assembly guide is incomplete');
  for (const [name, module] of Object.entries(guide.modules)) {
    if (!module.label || !Object.keys(module.actors || {}).length || !module.steps?.length) throw new Error(`Missing component: ${name}`);
    if (module.rotation && (module.rotation.length !== 3 || !module.rotation.every(Number.isFinite))) throw new Error(`Invalid assembly view: ${name}`);
    for (const action of module.helperActions ?? []) {
      if (!action.id || !action.hideLabel || !action.showLabel || !action.actors?.length
          || action.actors.some(id => !Object.hasOwn(module.actors, id))) throw new Error(`Invalid helper action: ${name}`);
    }
    for (const step of module.steps) {
      if (!step.title || !step.caption || !(step.duration > 0) || !step.samples?.length) throw new Error(`Missing assembly steps: ${name}`);
      for (const sample of step.samples) {
        for (const actor of Object.keys(module.actors)) {
          const matrix = sample[actor];
          if (!Array.isArray(matrix) || matrix.length !== 12 || !matrix.every(Number.isFinite)) throw new Error(`Missing part pose: ${name}/${actor}`);
        }
        for (const [actor, weight] of Object.entries(sample.morphs ?? {})) {
          const record = module.actors[actor];
          const count = record?.morphGeometries?.length ?? (record?.morphFile || record?.morphGeometry ? 1 : 0);
          const weights = Array.isArray(weight) ? weight : [weight];
          if (!count || weights.length !== count || weights.some(value => !Number.isFinite(value) || value < 0 || value > 1)
              || weights.reduce((sum, value) => sum + value, 0) > 1 + 1e-8) throw new Error(`Invalid spring pose: ${name}/${actor}`);
        }
      }
    }
  }
  return guide;
}
