// The whole-rod slider evaluates both the assembly and its framing at the
// requested time. No transition depends on the last frame that was rendered.
import { Matrix4, Quaternion } from '../../../../docs/lib/three-0.185.1/three.module.min.js';

const lerp = (a, b, t) => a + (b - a) * t;
const close = (a, b) => Math.abs(a - b) < 1e-8;
const same = (a, b) => a === b || (a && b && a.length === b.length && a.every((x, i) => close(x, b[i])));
const rotationIndices = [0, 1, 2, 4, 5, 6, 8, 9, 10];
const scalarWeights = weight => Array.isArray(weight) ? weight : [weight ?? 0];

function posesDiffer(a, b) {
  for (const id of new Set([...Object.keys(a), ...Object.keys(b)])) {
    if (id !== 'morphs' && !same(a[id], b[id])) return true;
  }
  return [...new Set([...Object.keys(a.morphs ?? {}), ...Object.keys(b.morphs ?? {})])].some(id =>
    !same(scalarWeights(a.morphs?.[id]), scalarWeights(b.morphs?.[id])));
}

export function joinRodSteps(steps, defaultBounds) {
  const joined = [];
  for (const next of steps) {
    const previous = joined.at(-1);
    if (previous) {
      const start = previous.samples.at(-1), end = next.samples[0];
      const from = previous.frameBounds ?? defaultBounds, to = next.frameBounds ?? defaultBounds;
      if (posesDiffer(start, end) || !same(from[0], to[0]) || !same(from[1], to[1])) {
        const intro = joined.length === 1 && previous.samples.length === 1;
        if (intro) joined.pop();
        joined.push({
          title: intro ? previous.title : 'Up next · ' + next.title,
          caption: intro ? 'Start with the bare rod. The loose key parts come into view beside its free end.' : next.caption,
          duration: 2, samples: [start, end], frameBounds: from, transitionTo: to,
        });
      }
    }
    joined.push(next);
  }
  return joined;
}

function blendMatrix(a, b, t) {
  if (same(a, b)) return a;
  const result = [...a];
  if (rotationIndices.some(i => !close(a[i], b[i]))) {
    const rotation = m => new Quaternion().setFromRotationMatrix(new Matrix4().set(...m, 0, 0, 0, 1));
    const matrix = new Matrix4().makeRotationFromQuaternion(rotation(a).slerp(rotation(b), t)).transpose();
    for (const index of rotationIndices) result[index] = matrix.elements[index];
  }
  for (const i of [3, 7, 11]) result[i] = lerp(a[i], b[i], t);
  return result;
}

export function rodFrame(step, fraction, defaultBounds) {
  const f = Math.max(0, Math.min(1, fraction));
  const u = step.transitionTo ? f * f * (3 - 2 * f) : f;
  const x = u * (step.samples.length - 1);
  const i = Math.floor(x), t = x - i, a = step.samples[i], b = step.samples[Math.ceil(x)];
  const from = step.frameBounds ?? defaultBounds, to = step.transitionTo ?? from;
  const bounds = from === to || u === 0 ? from : u === 1 ? to
    : from.map((corner, j) => corner.map((value, k) => lerp(value, to[j][k], u)));
  if (t === 0) return { pose: a, opacity: {}, bounds };
  const pose = {}, opacity = {};
  for (const id of new Set([...Object.keys(a), ...Object.keys(b)])) {
    if (id === 'morphs') continue;
    if (a[id] && b[id]) pose[id] = blendMatrix(a[id], b[id], t);
    else {
      const weight = a[id] ? 1 - t : t;
      const m = [...(a[id] ?? b[id])];
      // Introduce loose parts from above, keeping the group together.
      m[11] += 18 * (1 - weight);
      pose[id] = m;
      opacity[id] = weight;
    }
  }
  pose.morphs = {};
  for (const id of new Set([...Object.keys(a.morphs ?? {}), ...Object.keys(b.morphs ?? {})])) {
    const wa = a.morphs?.[id], wb = b.morphs?.[id];
    const arrA = scalarWeights(wa), arrB = scalarWeights(wb);
    const weights = Array.from({ length: Math.max(arrA.length, arrB.length) }, (_, j) =>
      lerp(arrA[j] ?? 0, arrB[j] ?? 0, t));
    pose.morphs[id] = Array.isArray(wa) || Array.isArray(wb) ? weights : weights[0];
  }
  return { pose, opacity, bounds };
}
