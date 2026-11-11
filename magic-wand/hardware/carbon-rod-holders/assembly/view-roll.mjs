// Roll for the assembly viewer: a two-finger twist turns the current view about
// its own view axis, without replacing orbit, pan or pinch. The shared free-view
// files stay byte-identical because archived revisions pin their hashes.
//
// Every listener is on the canvas, so page scrolling and browser zoom elsewhere
// keep their native behaviour. Input paths differ by engine:
// - WebKit (Safari) reports a trackpad twist and pinch together as GestureEvent
//   rotation and scale. Its pinch is handled here so a twist cannot zoom the page.
// - Touch screens report each finger as a PointerEvent; the pair's angle rolls.
// - Chromium and Firefox give pages no trackpad rotation (pinch arrives only as
//   Ctrl + wheel), so Option/Alt + scroll is the stated fallback there.
import { Quaternion, Vector3 } from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { FreeViewInput } from '../../printed-loop-wand/preview/free-view-input.mjs';
import { normalizeWheel } from '../../printed-loop-wand/preview/view-input.mjs';
import { applyViewerWheel } from '../../carbon-rod-holders-r7-spring-clips/preview/wheel-input.mjs';

const VIEW_AXIS = new Vector3(0, 0, 1);
const DEGREES = Math.PI / 180;
// Same rate as the shared scroll-to-turn path (0.4 × 0.006 radians per pixel).
export const ROLL_PER_WHEEL_PIXEL = 0.0024;
const IDLE_GESTURE = { rotation: 0, scale: 1 };

const finite = Number.isFinite;
const wrap = angle => Math.atan2(Math.sin(angle), Math.cos(angle));
function pairAngle(pointers) {
  const [a, b] = pointers.values();
  return Math.atan2(b.y - a.y, b.x - a.x);
}

export class RollingViewInput extends FreeViewInput {
  /** Turn the model clockwise on screen by `radians` about the view axis. */
  roll(radians) {
    if (!finite(radians) || radians === 0) return false;
    // The camera turns anticlockwise about its own back axis, so the model
    // appears to turn clockwise. Target, distance and mode are unchanged.
    this.rotation.multiply(new Quaternion().setFromAxisAngle(VIEW_AXIS, radians)).normalize();
    this.syncAngles();
    return true;
  }

  pointerMove(id, x, y, viewHeight, viewWidth = viewHeight) {
    // Exactly two touch fingers keep the shared pinch zoom and pan, and their
    // change in angle (screen y points down, so clockwise is positive) rolls.
    const twist = this.pointers.size === 2 && this.pointers.has(id);
    const before = twist ? pairAngle(this.pointers) : 0;
    const used = super.pointerMove(id, x, y, viewHeight, viewWidth);
    if (used && twist && this.pointers.size === 2) this.roll(wrap(pairAngle(this.pointers) - before));
    return used;
  }
}

/** Option/Alt + scroll rolls. Pinch (Ctrl) and Command keep their usual meaning. */
export function rollWheel(input, event, pageHeight) {
  if (!event.altKey || event.ctrlKey || event.metaKey) return false;
  const { dx, dy } = normalizeWheel(event, pageHeight);
  const delta = Math.abs(dx) > Math.abs(dy) ? dx : dy;
  // Content follows the fingers, as scroll-to-turn does: with natural
  // scrolling, moving the fingers right or down turns the model clockwise.
  return input.roll(-delta * ROLL_PER_WHEEL_PIXEL);
}

/** Wheel routing for the assembly viewer. Returns true when the event was used. */
export function routeAssemblyWheel(input, event, { gestureActive = false, height, pageHeight, wandRotate = false } = {}) {
  // A WebKit pinch already zooms through gesture scale; consuming a matching
  // Ctrl + wheel prevents a double zoom in engines that send both.
  if (event.ctrlKey && gestureActive) return true;
  if (event.altKey && !event.ctrlKey && !event.metaKey) return rollWheel(input, event, pageHeight);
  return applyViewerWheel(input, event, height, pageHeight, wandRotate);
}

function anchorZoom(canvas, input, { clientX, clientY }, previousDistance) {
  if (!finite(clientX) || !finite(clientY) || typeof canvas.getBoundingClientRect !== 'function') return;
  const bounds = canvas.getBoundingClientRect();
  if (!(bounds.width > 0 && bounds.height > 0)) return;
  input.keepZoomAnchor(2 * (clientX - bounds.left) / bounds.width - 1,
    1 - 2 * (clientY - bounds.top) / bounds.height, bounds.width / bounds.height, previousDistance);
}

/** WebKit trackpad twist and pinch over the canvas. */
export function bindTwistGestures({ canvas, input, render, changed = () => {}, blurTarget = globalThis.window }) {
  let last = null;
  const read = (event, previous) => ({
    rotation: finite(event.rotation) ? event.rotation : previous.rotation,
    scale: finite(event.scale) && event.scale > 0 ? event.scale : previous.scale,
  });
  canvas.addEventListener('gesturestart', event => {
    event.preventDefault();
    last = read(event, IDLE_GESTURE);
  }, { passive: false });
  canvas.addEventListener('gesturechange', event => {
    event.preventDefault();
    // A change without its start (for example after a window blur) begins a
    // new baseline instead of jumping by the gesture's whole rotation.
    if (!last) { last = read(event, IDLE_GESTURE); return; }
    const previous = last;
    last = read(event, previous);
    // Two touch fingers already pinch, pan and twist through PointerEvents.
    if (input.pointers.size >= 2) return;
    const distance = input.distance;
    const rolled = input.roll((last.rotation - previous.rotation) * DEGREES);
    input.zoom(previous.scale / last.scale);
    if (input.distance !== distance) anchorZoom(canvas, input, event, distance);
    if (rolled || input.distance !== distance) { changed(); render(); }
  }, { passive: false });
  canvas.addEventListener('gestureend', event => { event.preventDefault(); last = null; });
  blurTarget?.addEventListener?.('blur', () => { last = null; });
  return { get active() { return last !== null; } };
}

/** Which roll inputs this browser can actually deliver to the page. */
export function rollSupport(win = globalThis.window, nav = globalThis.navigator) {
  const platform = nav?.userAgentData?.platform || nav?.platform || '';
  const gestures = Boolean(win) && ('GestureEvent' in win || 'ongesturestart' in win);
  return { twist: gestures || (nav?.maxTouchPoints ?? 0) > 0, mac: /mac|iphone|ipad|ipod/i.test(platform) };
}

/** Short hint naming only the roll inputs that work here. */
export function rollHint({ twist = false, mac = true } = {}) {
  const scroll = `${mac ? 'Option' : 'Alt'}-scroll`;
  return twist ? `Twist or ${scroll} to roll` : `${scroll} to roll`;
}
