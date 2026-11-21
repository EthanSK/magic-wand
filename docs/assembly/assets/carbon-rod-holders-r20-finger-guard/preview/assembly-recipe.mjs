// The animation advances through the same quarter-millimetre CAD samples as
// the clearance report. The ring-end demonstration never crosses an obstruction.
export function routePose(data, direction, fraction) {
  const path = data.paths[direction];
  if (!path || !Number.isFinite(fraction)) throw new TypeError('Invalid route');
  const progress = Math.max(0, Math.min(1, fraction));
  const index = Math.round(progress * path.stop_index);
  return { ...path.samples[index], index, blocked: direction === 'rings' && progress === 1 };
}

export const recipes = {
  hand: [{ duration: 7, title: 'Slide from the Open Hand End', caption: 'Slide toward the keys from the open end. The guard stops just before the first key-holder ring.' }],
  rings: [{ duration: 5, title: 'Stop Before the Rings', caption: 'This approach is blocked. The guard cannot pass through the key-holder rings; use the other end.' }],
};
