// Read the exact binary STL exports for assembly inspection without another
// geometry snapshot. Reject truncated/non-binary files before allocating arrays.
import { BufferGeometry, BufferAttribute } from '../../../../docs/lib/three-0.185.1/three.module.min.js';

export function parseBinaryStl(buffer) {
  if (buffer.byteLength < 84) throw new Error('Invalid STL');
  const data = new DataView(buffer), count = data.getUint32(80, true);
  if (buffer.byteLength !== 84 + count * 50) throw new Error('Invalid STL');
  const positions = new Float32Array(count * 9);
  for (let i = 0; i < count; i++) for (let k = 0; k < 9; k++) {
    const value = data.getFloat32(84 + i * 50 + 12 + k * 4, true);
    if (!Number.isFinite(value)) throw new Error('Invalid STL coordinates');
    positions[i * 9 + k] = value;
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  return geometry;
}
