// Continuous camera-relative orbit for accessory inspection. Quaternion rotation
// crosses either pole without a stop or an upside-down camera flip; the existing
// ViewInput remains unchanged for the other wand previews that depend on it.
import { Euler, Quaternion, Vector3 } from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { ViewInput } from './view-input.mjs';

const TURN_PER_PIXEL = 0.006;
const axis = (x, y, z, rotation) => new Vector3(x, y, z).applyQuaternion(rotation);

export const VIEW_ANGLES = {
  isometric: [-Math.atan(1 / Math.sqrt(2)), Math.PI / 4, 0],
  front: [0, 0, 0], back: [0, Math.PI, 0],
  left: [0, -Math.PI / 2, 0], right: [0, Math.PI / 2, 0],
  top: [-Math.PI / 2, 0, 0], bottom: [Math.PI / 2, 0, 0],
};

export class FreeViewInput extends ViewInput {
  reset() {
    super.reset();
    this.rotation = new Quaternion().setFromEuler(new Euler(-this.pitch, this.yaw, 0, 'YXZ'));
  }

  camera() {
    return axis(0, 0, this.distance, this.rotation).add(new Vector3(...this.target)).toArray();
  }

  cameraUp() { return axis(0, 1, 0, this.rotation).toArray(); }

  cameraBasis() {
    return { right: axis(1, 0, 0, this.rotation).toArray(), up: this.cameraUp(), back: axis(0, 0, 1, this.rotation).toArray() };
  }

  keepZoomAnchor(x, y, aspect, previousDistance) {
    const delta = (previousDistance - this.distance) * Math.tan(this.fov * Math.PI / 360);
    const shift = axis(1, 0, 0, this.rotation).multiplyScalar(x * aspect * delta)
      .add(axis(0, 1, 0, this.rotation).multiplyScalar(y * delta));
    this.target = new Vector3(...this.target).add(shift).toArray();
  }

  syncAngles() {
    const back = axis(0, 0, 1, this.rotation);
    this.yaw = Math.atan2(back.x, back.z);
    this.pitch = Math.asin(Math.max(-1, Math.min(1, back.y)));
  }

  turn(dx, dy) {
    // Apply both axes relative to the camera, not a world-up axis that reverses
    // horizontal dragging after crossing the top or bottom of the object.
    const delta = new Quaternion().setFromEuler(new Euler(-dy * TURN_PER_PIXEL, -dx * TURN_PER_PIXEL, 0, 'YXZ'));
    this.rotation.multiply(delta).normalize();
    this.syncAngles();
  }

  move(dx, dy, viewHeight) {
    const scale = 2 * this.distance * Math.tan(this.fov * Math.PI / 360) / Math.max(viewHeight, 1);
    const offset = axis(1, 0, 0, this.rotation).multiplyScalar(-dx * scale)
      .add(axis(0, 1, 0, this.rotation).multiplyScalar(dy * scale));
    this.target = new Vector3(...this.target).add(offset).toArray();
  }

  setView(name) {
    if (!Object.hasOwn(VIEW_ANGLES, name)) return false;
    this.rotation.setFromEuler(new Euler(...VIEW_ANGLES[name], 'YXZ'));
    this.syncAngles();
    this.cancel();
    return true;
  }

  fitBounds(min, max, { aspect = 1, padding = 1.18 } = {}) {
    const target = min.map((v, i) => (v + max[i]) / 2);
    const right = axis(1, 0, 0, this.rotation), up = axis(0, 1, 0, this.rotation), back = axis(0, 0, 1, this.rotation);
    const tanY = Math.tan(this.fov * Math.PI / 360), tanX = tanY * Math.max(aspect, 0.01);
    let distance = this.minDistance;
    for (let bits = 0; bits < 8; bits++) {
      const point = new Vector3(...target.map((v, i) => ((bits & (1 << i)) ? max[i] : min[i]) - v));
      distance = Math.max(distance, point.dot(back) + padding * Math.max(Math.abs(point.dot(right)) / tanX, Math.abs(point.dot(up)) / tanY));
    }
    this.target = target;
    this.distance = Math.min(this.maxDistance, distance);
    this.cancel();
  }

  snapshot() { return { ...super.snapshot(), rotation: this.rotation.toArray() }; }

  restore(value) {
    const rotation = value?.rotation;
    const norm = Array.isArray(rotation) ? rotation.reduce((sum, n) => sum + n * n, 0) : 0;
    if (rotation !== undefined && (!Array.isArray(rotation) || rotation.length !== 4
      || !rotation.every(Number.isFinite) || !Number.isFinite(norm) || norm < 1e-12)) return false;
    if (!super.restore(value)) return false;
    this.rotation = rotation === undefined
      ? new Quaternion().setFromEuler(new Euler(-this.pitch, this.yaw, 0, 'YXZ'))
      : new Quaternion(...rotation).normalize();
    this.syncAngles();
    this.cancel();
    return true;
  }

  pointerDown(id, x, y, dragMode = this.mode) {
    super.pointerDown(id, x, y);
    this.pointers.get(id).dragMode = dragMode;
  }

  pointerMove(id, x, y, viewHeight, viewWidth = viewHeight) {
    if (this.pointers.size >= 2) return super.pointerMove(id, x, y, viewHeight);
    const last = this.pointers.get(id);
    if (!last) return false;
    const dragMode = last.dragMode ?? this.mode;
    this.pointers.set(id, { x, y, dragMode });
    const dx = x - last.x, dy = y - last.y;
    if (dragMode === 'move') this.move(dx, dy, viewHeight);
    else if (dragMode === 'zoom') this.zoom(Math.exp(dy * .004));
    else {
      // One full dragged turn spans the short side of the viewport. Keyboard
      // and wand-wheel gains are unchanged; this scales direct dragging only.
      const scale = 2 * Math.PI / Math.max(180, Math.min(viewHeight, viewWidth)) / TURN_PER_PIXEL;
      this.turn(dx * scale, dy * scale);
    }
    return true;
  }
}
