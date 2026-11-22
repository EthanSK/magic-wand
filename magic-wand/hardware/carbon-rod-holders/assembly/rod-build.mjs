// Each assembly step reuses the component guide's CAD poses, including wire
// and latch deformation. The whole rod adds only rigid placement and travel.
import { joinRodSteps } from './rod-transitions.mjs';

function shiftY(matrix, distance) {
  const moved = [...matrix];
  moved[7] += distance;
  return moved;
}

function combine(fixed, moving) {
  return { ...fixed, ...moving, morphs: { ...fixed.morphs, ...moving.morphs } };
}

function sequence(fn) {
  return Array.from({ length: 31 }, (_, index) => fn(index / 30));
}

export function completeKeys(hinge, outer) {
  const outerIds = Object.keys(outer.actors).filter(id => !Object.hasOwn(hinge.actors, id));
  const outerPose = (pose, offset = 0) =>
    Object.fromEntries(outerIds.map(id => [id, shiftY(pose[id], offset)]));
  const ready = outer.steps[0].samples[0];
  const parked = outerPose(ready, -44);
  const press = hinge.steps.at(-1);
  const fittedHinge = press.samples[0];
  const fittedKeys = outerPose(outer.steps.at(-1).samples.at(-1));
  return {
    ...hinge, label: 'Full key assembly',
    actors: { ...outer.actors, ...hinge.actors },
    steps: [
      ...hinge.steps.slice(0, -1).map(step => ({
        ...step, samples: step.samples.map(frame => combine(frame, parked)),
      })),
      {
        title: 'Bring the outer keys to the holder',
        caption: 'With the hinge secured, bring the four sockets, switches and caps into position.',
        duration: 1.5, samples: sequence(t => combine(fittedHinge, outerPose(ready, -44 * (1 - t)))),
      },
      ...outer.steps.map(step => ({
        ...step, samples: step.samples.map(frame => combine(fittedHinge, outerPose(frame))),
      })),
      { ...press, samples: press.samples.map(frame => combine(frame, fittedKeys)) },
    ],
  };
}

// Row-major CAD transforms, with translation in the fourth column.
export function placed(parent, local) {
  const result = [];
  for (let row = 0; row < 12; row += 4) {
    for (let col = 0; col < 4; col++) {
      result.push(parent[row] * local[col] + parent[row + 1] * local[col + 4]
        + parent[row + 2] * local[col + 8] + (col === 3 ? parent[row + 3] : 0));
    }
  }
  return result;
}

export function completeRod(whole, components) {
  const actors = { ...whole.actors };
  const steps = [...whole.steps];
  let assembled = steps[0].samples[0];
  const mountingBounds = [[-47, -36, -12], [47, 268, 65]];
  for (const mount of whole.rodMounts) {
    const { id, root, placement, lastStep, mountEmpty, title, caption } = mount;
    const component = components[id];
    const ids = Object.keys(component.actors).filter(key => key !== 'rod');
    for (const key of ids) actors[id + '_' + key] = component.actors[key];
    const bench = shiftY(placement, 222 - placement[7]);
    const y = mountEmpty ? placement[7] : bench[7];
    const detailBounds = id === 'keys' ? [[-55, y-75, -8], [55, y+52, 60]]
      : [[-30, y-48, -12], [30, y+50, 45]];
    const end = component.steps.findIndex(step => step.title === lastStep);
    if (end < 0) throw new Error('Missing assembly step for ' + id + ': ' + lastStep);
    const build = component.steps.slice(0, end + 1);

    function frame(local, position, include = ids) {
      const group = { morphs: {} };
      for (const key of include) {
        const actor = id + '_' + key;
        group[actor] = placed(position, local[key]);
        if (local.morphs?.[key] !== undefined) group.morphs[actor] = local.morphs[key];
      }
      return combine(assembled, group);
    }
    const localEnd = build.at(-1).samples.at(-1);
    const slide = {
      title, caption, duration: 3, frameBounds: mountingBounds,
      samples: sequence(t => frame(mountEmpty ? build[0].samples[0] : localEnd,
        shiftY(placement, (bench[7] - placement[7]) * (1 - t)), mountEmpty ? [root] : ids)),
    };
    const details = build.map(step => ({
      ...step, frameBounds: detailBounds,
      samples: step.samples.map(sample => frame(sample, mountEmpty ? placement : bench)),
    }));
    if (mountEmpty) steps.push(slide, ...details);
    else steps.push(...details, slide);
    assembled = frame(localEnd, placement);
  }
  steps.push({ title: 'Check the assembled wand',
    caption: whole.finalCaption ?? 'All four holders are seated. Check the pad click, both keepers and the wire route.',
    duration: 2, samples: [assembled], frameBounds: whole.frameBounds });
  return { ...whole, actors, steps: joinRodSteps(steps, whole.frameBounds), stagedActors: true };
}
