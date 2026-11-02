// Show the actual R2/R3 accessory meshes. Mouse scroll zooms; the explicit
// wand override turns immediately, preserving drag modes and direct input.
import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { frameBounds, MODES } from '../../printed-loop-wand/preview/view-input.mjs';
import { FreeViewInput as ViewInput } from '../../printed-loop-wand/preview/free-view-input.mjs';
import { bindFreeViewControls, installViewTools } from '../../printed-loop-wand/preview/free-view-controls.mjs';
import { applyViewerWheel } from '../../carbon-rod-holders-r4/preview/wheel-input.mjs';

const view = document.querySelector('#view');
const ui = Object.fromEntries(['revision', 'parts', 'references', 'status', 'modes', 'plus', 'minus', 'reset', 'error'].map(id => [id, document.getElementById(id)]));
const input = new ViewInput({ minDistance: 15, maxDistance: 1500 });
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x12151c);
scene.add(new THREE.HemisphereLight(0xe8f4ff, 0x424154, 2.1));
const light = new THREE.DirectionalLight(0xffffff, 3);

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
view.prepend(renderer.domElement);
const canvas = renderer.domElement;
canvas.tabIndex = 0; canvas.setAttribute('aria-label', '3D model. Drag to rotate; Shift or right drag to pan; scroll to zoom. F frames; 0 resets; R, P and Z select modes.');
const camera = new THREE.PerspectiveCamera(32, 1, .1, 3000);
// A camera-attached key light keeps the back and underside readable.
camera.add(light, light.target); scene.add(camera);
light.position.set(-1, 1, 1); light.target.position.set(0, 0, -1);
const target = new THREE.Vector3();
const models = new THREE.Group(); scene.add(models);
let data;
let viewTools;
let hasFramed = false;
const override = document.getElementById('wand-scroll');
function hint() {
  const names = { turn: 'rotate', move: 'pan', zoom: 'zoom' };
  document.querySelector('.hint').textContent = 'Drag to ' + names[input.mode] + ' · Shift/right-drag to pan · ' + (override.checked ? 'Scroll rotates · Pinch zooms' : 'Scroll or pinch to zoom');
}
override.addEventListener('change', hint); hint();

function render() {
  camera.position.set(...input.camera()); camera.up.set(...input.cameraUp()); camera.lookAt(target.set(...input.target)); renderer.render(scene, camera); viewTools?.update();
}
function homeForModels() {
  const bounds = new THREE.Box3().setFromObject(models);
  return frameBounds(bounds.min.toArray(), bounds.max.toArray(), { aspect: camera.aspect, yaw: .38, pitch: .6, fov: camera.fov, padding: 1.2 });
}
function reset() { if (!models.children.length) return; input.setHome(homeForModels()); render(); }
function fit() {
  if (!models.children.length) return;
  const bounds = new THREE.Box3().setFromObject(models);
  input.fitBounds(bounds.min.toArray(), bounds.max.toArray(), { aspect: camera.aspect });
  render();
}
function chooseMode(mode) {
  if (!input.setMode(mode)) return;
  for (const b of ui.modes.children) b.setAttribute('aria-pressed', String(b.dataset.mode === mode));
  hint(); render();
}
function update({ reframe = false } = {}) {
  if (!data) return;
  for (const child of [...models.children]) { models.remove(child); child.geometry.dispose(); child.material.dispose(); }
  const revision = data[ui.revision.value];
  document.getElementById('description').textContent = ui.revision.value === 'r3'
    ? 'Three keys below, two above. The battery sits between the upper keys.'
    : 'Three keys side by side. The battery sits above the middle key.';
  const exportFolder = ui.revision.value === 'r3' ? '../exports/' : '../../carbon-rod-holders-r2/exports/';
  for (const [id, file] of [['carrier-file', 'Key_Battery_Carrier.stl'], ['sensor-file', 'XIAO_Rod_Holder.stl'], ['project-file', 'Holder-pair-sliced.3mf']]) {
    document.getElementById(id).href = exportFolder + file;
  }
  for (const item of revision.items) {
    if (ui.parts.value !== 'both' && item.part !== ui.parts.value) continue;
    if (!ui.references.checked && item.reference) continue;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(item.vertices.flat(), 3));
    geometry.setIndex(item.faces.flat()); geometry.computeVertexNormals();
    const color = !item.reference ? (item.part === 'carrier' ? 0x38b4bb : 0xe8a749)
      : item.name === 'rod' ? 0x303944 : item.name === 'pcb' ? 0x37835e
      : item.name === 'battery' ? 0x64758b : item.name === 'wire' ? 0xc76754 : 0xd9e0e7;
    const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: .55, metalness: .05 }));
    mesh.name = item.name;
    if (ui.parts.value === 'both') mesh.position.x = item.part === 'carrier' ? -32 : 54;
    models.add(mesh);
  }
  const masses = revision.mass?.object_printed_parts_g;
  ui.status.textContent = masses ? `Carrier ${masses.Key_Battery_Carrier.toFixed(2)} g · XIAO holder ${masses.XIAO_Rod_Holder.toFixed(2)} g. Printed plastic, excluding brim.` : 'Model loaded. Print estimate unavailable.';
  if (!hasFramed) input.setHome(homeForModels());
  else {
    const distance = input.distance;
    input.setHome(homeForModels(), true);
    input.distance = distance; // Visibility and design comparisons keep the exact inspection view.
    input.cancel();
  }
  if (reframe && hasFramed) fit();
  else render();
  hasFramed = true;
}
new ResizeObserver(() => {
  renderer.setSize(view.clientWidth, view.clientHeight);
  camera.aspect = view.clientWidth / Math.max(1, view.clientHeight); camera.updateProjectionMatrix();
  if (data) { input.setHome(homeForModels(), true); render(); }
}).observe(view);
bindFreeViewControls({ canvas, input, height: () => view.clientHeight, width: () => view.clientWidth, render, chooseMode, fit,
  wheel: event => applyViewerWheel(input, event, view.clientHeight, window.innerHeight, override.checked) });
viewTools = installViewTools({ view, input, fit, render });
ui.modes.addEventListener('click', e => { const mode = e.target.closest('button')?.dataset.mode; if (MODES.includes(mode)) chooseMode(mode); });
ui.plus.addEventListener('click', () => { input.zoomSteps(1); render(); });
ui.minus.addEventListener('click', () => { input.zoomSteps(-1); render(); });
ui.reset.addEventListener('click', reset);
for (const id of ['revision', 'parts', 'references']) ui[id].addEventListener('change', () => update({ reframe: id === 'parts' }));
try {
  const result = await fetch('../exports/review-scene.json', { cache: 'no-store' });
  if (!result.ok) throw new Error(`Model request failed (${result.status})`);
  data = await result.json(); update();
} catch (error) { ui.error.style.display = 'grid'; ui.error.textContent = `Unable to load model: ${error.message}`; }
