// Render the same discrete poses used by the owning model's assembly checks.
// Keep all components in one menu; adding a component to its guide includes it
// here without maintaining another list of model names in the user interface.
export const identity = () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0];
export const translated = (x = 0, y = 0, z = 0) => [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z];

export function sampledPose(module, index, fraction) {
  if (!Number.isInteger(index) || !module.steps[index] || !Number.isFinite(fraction)) throw new TypeError('Invalid assembly step');
  const samples = module.steps[index].samples;
  return samples[Math.round(Math.max(0, Math.min(1, fraction)) * (samples.length - 1))];
}

export function groupKeys(modules) {
  const { key, centre, centre_shallow, centre_deep, ...others } = modules;
  const seated = key.steps.at(-1).samples.at(-1);
  const sockets = Object.fromEntries(Object.entries(key.actors).filter(([id]) => id.startsWith('socket_')));
  const socketPoses = Object.fromEntries(Object.keys(sockets).map(id => [id, seated[id]]));

  function paddleView(module, label) {
    const actors = { ...sockets, ...module.actors };
    // The centre installation guide already carries the four seated switches.
    // Include them in the camera bounds when the keys are shown together.
    for (const id of Object.keys(actors).filter(id => id.startsWith('switch_'))) {
      actors[id] = { ...actors[id], frame: true };
    }
    const steps = module.steps.map(step => ({
      ...step,
      samples: step.samples.map(pose => ({ ...socketPoses, ...pose })),
    }));
    return { ...module, label, actors, steps, openSeated: true };
  }

  const views = {
    centre: paddleView(centre, 'Standard paddle'),
    centre_shallow: paddleView(centre_shallow, 'Shallow paddle'),
    centre_deep: paddleView(centre_deep, 'Deep paddle'),
    key: { ...key, label: 'Fit Choc switches', note: 'Fit the four outer switches and their sockets.' },
  };
  return { modules: { keys: { ...views.centre, label: 'Keys' }, ...others }, views };
}

export function validateGuide(guide) {
  if (guide.schema_version !== 2 || guide.units !== 'mm' || !guide.modules || !Object.keys(guide.modules).length) throw new Error('Assembly guide is incomplete');
  for (const [name, module] of Object.entries(guide.modules)) {
    if (!module.label || !Object.keys(module.actors || {}).length || !module.steps?.length) throw new Error(`Missing component: ${name}`);
    if (module.rotation && (module.rotation.length !== 3 || !module.rotation.every(Number.isFinite))) throw new Error(`Invalid assembly view: ${name}`);
    for (const step of module.steps) {
      if (!step.title || !step.caption || !(step.duration > 0) || !step.samples?.length) throw new Error(`Missing assembly steps: ${name}`);
      for (const sample of step.samples) {
        for (const actor of Object.keys(module.actors)) {
          const matrix = sample[actor];
          if (!Array.isArray(matrix) || matrix.length !== 12 || !matrix.every(Number.isFinite)) throw new Error(`Missing part pose: ${name}/${actor}`);
        }
        for (const [actor, weight] of Object.entries(sample.morphs ?? {})) {
          if (!module.actors[actor]?.morphFile || !Number.isFinite(weight) || weight < 0 || weight > 1) throw new Error(`Invalid spring pose: ${name}/${actor}`);
        }
      }
    }
  }
  return guide;
}
