// Keep the free end at the original mounting plane so animated holders can still slide on.
import { placed } from './rod-build.mjs';
import blueprint from '../../assembly-blueprint/manifest.json' with { type: 'json' };

export const stockLength = blueprint.products.tube.nominal_stock_length_mm;
export const stockRodUrl = new URL('../exports/carbon-stock-tube.stl', import.meta.url);

function mountPose(record, module, id) {
  const oldHalf = record.primitive ? record.primitive.length / 2 : undefined;
  if (id === 'whole') return [1,0,0,0, 0,-1,0,175, 0,0,-1,0];
  if (record.primitive?.axis === 'z' || record.file?.endsWith('rod_z.stl')) {
    return [1,0,0,0, 0,0,1,0, 0,-1,0,oldHalf ?? 22];
  }
  // Some guides feed the tube in from below the holder's Y origin.
  // The old horizontal reference mesh ran from -30 to +60 mm.
  const poses = module.steps.flatMap(step => step.samples.map(sample => sample.rod?.[7]).filter(Number.isFinite));
  const fromNegative = poses[0] < -1 || poses[0] < poses.at(-1) - 1;
  if (fromNegative) return [1,0,0,0, 0,-1,0,oldHalf ?? 60, 0,0,-1,0];
  return [1,0,0,0, 0,1,0,-(oldHalf ?? 30), 0,0,1,0];
}

export function withStockRods(guide, mesh = stockRodUrl.href) {
  const modules = { ...guide.modules };
  for (const [id, module] of Object.entries(modules)) {
    const record = module.actors?.rod;
    if (!record || record.file?.endsWith('/carbon-stock-tube.stl')) continue;
    const { primitive, baseUrl, ...appearance } = record;
    const rod = { ...appearance, file: mesh, label: 'Carbon tube · ' + stockLength + ' mm' };
    const local = mountPose(record, module, id);
    const steps = module.steps.map(step => ({
      ...step, samples: step.samples.map(sample => sample.rod
        ? { ...sample, rod: placed(sample.rod, local) } : sample),
    }));
    const updated = { ...module, actors: { ...module.actors, rod }, steps };
    if (id === 'whole' && module.frameBounds) {
      const [lo, hi] = module.frameBounds;
      updated.frameBounds = [[lo[0], Math.min(lo[1], local[7] - stockLength - 5), lo[2]], [...hi]];
    }
    modules[id] = updated;
  }
  return { ...guide, modules };
}
