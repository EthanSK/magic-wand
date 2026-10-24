// Camera input for the 3D preview, kept free of the DOM and Three.js so it can be tested.
// One mode decides what dragging and scrolling do: turn (default), move or zoom. Scrolling
// therefore turns the model by default; the wand's Bottom hold arrives as scroll events over this
// page, so holding and moving it turns the model instead of zooming. Pinch (Ctrl+scroll) and the
// zoom buttons always zoom. Every input applies immediately: no smoothing, inertia or delay.

export const MODES = ['turn', 'move', 'zoom'];
const LINE = 16; // Pixels per wheel line (deltaMode 1).
const MAX_STEP = 240; // Largest wheel movement used from one event, in pixels per axis.
const TURN_PER_PIXEL = 0.006; // Radians per dragged pixel.
const WHEEL_TURN = 0.4; // Scrolling turns at this fraction of the drag rate.
const ZOOM_PER_PIXEL = 0.004; // Drag/scroll zoom: distance multiplies by exp(pixels × this).
const PINCH_PER_PIXEL = 0.01; // Ctrl+scroll arrives in smaller steps.
const KEY_STEP = 40; // Pixels of equivalent drag per arrow key press.
const PITCH_LIMIT = 1.45;

/** Frame all box corners using the actual viewport, including tall side-panel views. */
export function frameBounds(min, max, { aspect, fov = 32, yaw = 1.3, pitch = 0.22, padding = 1.18 }) {
  const target = min.map((v, i) => (v + max[i]) / 2);
  const sy = Math.sin(yaw), cy = Math.cos(yaw), sp = Math.sin(pitch), cp = Math.cos(pitch);
  const right = [cy, 0, -sy], up = [-sp * sy, cp, -sp * cy], back = [cp * sy, sp, cp * cy];
  const tanY = Math.tan(fov * Math.PI / 360), tanX = tanY * Math.max(aspect, 0.01);
  let distance = 80;
  for (let bits = 0; bits < 8; bits++) {
    const p = target.map((v, i) => ((bits & (1 << i)) ? max[i] : min[i]) - v);
    const dot = (axis) => p.reduce((sum, v, i) => sum + v * axis[i], 0);
    distance = Math.max(distance, dot(back) + padding * Math.max(Math.abs(dot(right)) / tanX, Math.abs(dot(up)) / tanY));
  }
  return { yaw, pitch, distance, target };
}

/** Convert a wheel event's deltas to pixels and limit single-event spikes. */
export function normalizeWheel({ deltaX = 0, deltaY = 0, deltaMode = 0 }, pageHeight = 800) {
  const unit = deltaMode === 1 ? LINE : deltaMode === 2 ? pageHeight : 1;
  const clamp = (v) => Math.max(-MAX_STEP, Math.min(MAX_STEP, Number.isFinite(v) ? v * unit : 0));
  return { dx: clamp(deltaX), dy: clamp(deltaY) };
}

export class ViewInput {
  constructor({ fov = 32, minDistance = 80, maxDistance = 3000, mode = 'turn' } = {}) {
    this.fov = fov;
    this.minDistance = minDistance;
    this.maxDistance = maxDistance;
    this.mode = MODES.includes(mode) ? mode : 'turn';
    this.home = { yaw: 1.3, pitch: 0.22, distance: 900, target: [0, 0, 0] };
    this.pointers = new Map();
    this.pinch = null;
    this.reset();
  }

  setHome(home, preserveView = false) {
    const scale = home.distance / this.home.distance;
    this.home = { ...home, target: [...home.target] };
    if (preserveView) this.distance *= scale;
    else this.reset();
  }

  reset() {
    this.yaw = this.home.yaw;
    this.pitch = this.home.pitch;
    this.distance = this.home.distance;
    this.target = [...this.home.target];
  }

  setMode(mode) {
    if (!MODES.includes(mode)) return false;
    this.mode = mode;
    this.cancel(); // A drag in progress restarts from the next movement instead of jumping.
    return true;
  }

  cancel() {
    this.pointers.clear();
    this.pinch = null;
  }

  /** Camera position for the current yaw, pitch, distance and target. */
  camera() {
    const [x, y, z] = this.target;
    const c = Math.cos(this.pitch);
    return [x + this.distance * c * Math.sin(this.yaw), y + this.distance * Math.sin(this.pitch), z + this.distance * c * Math.cos(this.yaw)];
  }

  turn(dx, dy) {
    this.yaw -= dx * TURN_PER_PIXEL;
    this.pitch = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, this.pitch + dy * TURN_PER_PIXEL));
  }

  /** Move the view so the model follows the pointer by (dx, dy) screen pixels. */
  move(dx, dy, viewHeight) {
    const perPixel = (2 * this.distance * Math.tan((this.fov * Math.PI) / 360)) / Math.max(viewHeight, 1);
    const sy = Math.sin(this.yaw), cy = Math.cos(this.yaw), sp = Math.sin(this.pitch), cp = Math.cos(this.pitch);
    const right = [cy, 0, -sy];
    const back = [cp * sy, sp, cp * cy];
    const up = [back[1] * right[2] - back[2] * right[1], back[2] * right[0] - back[0] * right[2], back[0] * right[1] - back[1] * right[0]];
    for (let i = 0; i < 3; i++) this.target[i] += (-right[i] * dx + up[i] * dy) * perPixel;
  }

  zoom(factor) {
    if (!Number.isFinite(factor) || factor <= 0) return;
    this.distance = Math.max(this.minDistance, Math.min(this.maxDistance, this.distance * factor));
  }

  /** Zoom in (positive steps) or out (negative), as the + and - buttons do. */
  zoomSteps(steps) {
    this.zoom(Math.exp(-steps * 0.18));
  }

  drag(dx, dy, viewHeight) {
    if (this.mode === 'turn') this.turn(dx, dy);
    else if (this.mode === 'move') this.move(dx, dy, viewHeight);
    else this.zoom(Math.exp(dy * ZOOM_PER_PIXEL));
  }

  /** Apply a wheel event. Returns true when it was used (the caller then prevents page scrolling). */
  wheel(event, viewHeight, pageHeight = viewHeight) {
    const { dx, dy } = normalizeWheel(event, pageHeight);
    if (!dx && !dy) return false;
    if (event.ctrlKey) { // Trackpad pinch arrives as Ctrl+scroll.
      this.zoom(Math.exp(dy * PINCH_PER_PIXEL));
      return true;
    }
    // Scrolling moves the model the way it would move a page: content goes opposite to the delta.
    if (this.mode === 'turn') this.turn(-dx * WHEEL_TURN, -dy * WHEEL_TURN);
    else if (this.mode === 'move') this.move(-dx, -dy, viewHeight);
    else this.zoom(Math.exp(dy * ZOOM_PER_PIXEL));
    return true;
  }

  pointerDown(id, x, y) {
    this.pointers.set(id, { x, y });
    this.pinch = this.pointers.size === 2 ? this.#pinchState() : null;
  }

  pointerMove(id, x, y, viewHeight) {
    const last = this.pointers.get(id);
    if (!last) return false;
    this.pointers.set(id, { x, y });
    if (this.pointers.size >= 2) { // Two fingers: spread to zoom, move together to move the view.
      const now = this.#pinchState();
      if (this.pinch && now.spread > 0 && this.pinch.spread > 0) {
        this.zoom(this.pinch.spread / now.spread);
        this.move(now.x - this.pinch.x, now.y - this.pinch.y, viewHeight);
      }
      this.pinch = now;
      return true;
    }
    this.drag(x - last.x, y - last.y, viewHeight);
    return true;
  }

  pointerUp(id) {
    this.pointers.delete(id);
    this.pinch = this.pointers.size === 2 ? this.#pinchState() : null;
  }

  /** Keyboard handling for the focused view. Returns true when the key was used. */
  key({ key, shiftKey = false }, viewHeight) {
    const step = shiftKey ? KEY_STEP * 3 : KEY_STEP;
    const arrows = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (arrows[key]) {
      this.drag(...arrows[key], viewHeight);
      return true;
    }
    if (key === '+' || key === '=') { this.zoomSteps(1); return true; }
    if (key === '-' || key === '_') { this.zoomSteps(-1); return true; }
    if (key === '0' || key === 'Home') { this.reset(); return true; }
    const modeKey = { t: 'turn', m: 'move', z: 'zoom' }[key.toLowerCase?.() ?? key];
    return modeKey ? this.setMode(modeKey) : false;
  }

  #pinchState() {
    const [a, b] = [...this.pointers.values()];
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, spread: Math.hypot(a.x - b.x, a.y - b.y) };
  }
}
