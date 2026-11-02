// Compose exported R8 geometry and sourced component CAD. Mouse scroll zooms;
// the explicit wand override changes scroll only, preserving direct drag input.
import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { frameBounds, MODES } from '../../printed-loop-wand/preview/view-input.mjs';
import { FreeViewInput as ViewInput } from '../../printed-loop-wand/preview/free-view-input.mjs';
import { bindFreeViewControls, installViewTools } from '../../printed-loop-wand/preview/free-view-controls.mjs';
import { applyViewerWheel } from '../../carbon-rod-holders-r7-spring-clips/preview/wheel-input.mjs';

const view = document.querySelector('#view');
const ui = Object.fromEntries(['revision', 'battery-end', 'battery-side', 'spacing', 'parts', 'references', 'caps', 'status', 'modes', 'plus', 'minus', 'reset', 'error'].map(id => [id, document.getElementById(id)]));
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
const geometries = new Map();
const scrollSetting = "wand-holder-scroll-turns";
const override = document.getElementById("wand-scroll");
try { override.checked = localStorage.getItem(scrollSetting) === "true"; } catch {}
function hint() {
  const names = { turn: 'rotate', move: 'pan', zoom: 'zoom' };
  document.querySelector('.hint').textContent = 'Drag to ' + names[input.mode] + ' · Shift/right-drag to pan · ' + (override.checked ? 'Scroll rotates · Pinch zooms' : 'Scroll or pinch to zoom');
}
override.addEventListener("change", () => { try {localStorage.setItem(scrollSetting, String(override.checked));} catch {} hint(); });
hint();

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
function addMesh(parent, name, geometryName, color, position = [0, 0, 0]) {
  let geometry = geometries.get(geometryName);
  if (!geometry) {
    const source = data.geometry[geometryName];
    geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(source.vertices.flat(), 3));
    geometry.setIndex(source.faces.flat()); geometry.computeVertexNormals();
    geometries.set(geometryName, geometry);
  }
  const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: .55, metalness: .05 }));
  mesh.name = name; mesh.position.set(...position); parent.add(mesh); return mesh;
}
function update({ reframe = false } = {}) {
  if (!data) return;
  for (const child of [...models.children]) {
    child.traverse(node => node.material?.dispose()); models.remove(child);
  }
  const flipped = ui.revision.value === 'three-toward-tip';
  const keys = new THREE.Group(); keys.name = 'key-module'; keys.rotation.z = flipped ? Math.PI : 0;
  const battery = new THREE.Group(); battery.name = 'battery-module';
  const sensor = new THREE.Group(); sensor.name = 'sensor-module';
  addMesh(keys, 'keys', 'Key_Carrier', 0x38b4bb);
  addMesh(battery, 'battery-holder', 'Battery_Holder', 0xb493e5);
  addMesh(sensor, 'sensor', 'XIAO_Rod_Holder', 0xe8a749);
  if (ui.references.checked) {
    for (const [i, [x, y]] of data.key_positions.entries()) {
      for (const [name, color] of [['switch', 0x939aa4], ['socket', 0x35404c], ['cap', 0xd9e0e7]]) {
        if (name === 'cap' && !ui.caps.checked) continue;
        addMesh(keys, `key_${i}_${name}`, name, color, [x, y, data.parameters.keys.pcb_z]);
      }
    }
    addMesh(battery, 'battery', 'cell', 0x64758b);
    for (const [name, color] of [['pcb', 0x37835e], ['usb', 0xd9e0e7], ['wire', 0xc76754], ['sensor_rod', 0x303944]]) addMesh(sensor, name, name, color);
  }
  // The tip is +Y. End names follow the key module when it turns around;
  // its physical keycaps always face outwards. Battery roll is independent.
  const bounds = data.manifest.parts.Key_Carrier.bounds_mm;
  const keyMin = flipped ? -bounds[1][1] : bounds[0][1];
  const keyMax = flipped ? -bounds[0][1] : bounds[1][1];
  const batteryBounds = data.manifest.parts.Battery_Holder.bounds_mm;
  const pose = data.battery_poses[ui.revision.value][ui['battery-end'].value];
  battery.position.y = pose.y + pose.direction * Number(ui.spacing.value);
  battery.rotation.y = ui['battery-side'].value === 'reverse' ? Math.PI : 0;
  document.getElementById('spacing-value').textContent = `${Number(ui.spacing.value)} mm`;
  const selected = ui.parts.value;
  if (['all', 'assembly', 'keys'].includes(selected)) models.add(keys);
  if (['all', 'assembly', 'battery'].includes(selected)) models.add(battery);
  if (['all', 'sensor'].includes(selected)) models.add(sensor);
  // Dispose hidden groups too: repeated arrangement changes must not leak GPU
  // materials, while immutable geometry is cached for the viewer's lifetime.
  for (const group of [keys, battery, sensor]) if (!group.parent) group.traverse(node => node.material?.dispose());
  if (selected === 'all') sensor.position.x = data.parameters.assembly.sensor_display_offset_x;
  if (ui.references.checked && ['all', 'assembly', 'keys', 'battery'].includes(selected)) {
    let lo = Infinity, hi = -Infinity;
    if (keys.parent) { lo = keyMin; hi = keyMax; }
    if (battery.parent) { lo = Math.min(lo, battery.position.y + batteryBounds[0][1]); hi = Math.max(hi, battery.position.y + batteryBounds[1][1]); }
    const rod = addMesh(models, 'rod', 'rod', 0x303944, [0, (lo + hi) / 2, 0]); rod.scale.y = hi - lo + 20;
  }
  document.getElementById('description').textContent = 'Separate sliding key and battery holders. The green +Y axis points toward the tip. Try either key orientation and either battery end.';
  const mass = data.mass?.object_printed_parts_g;
  ui.status.textContent = mass ? `Keys ${mass.Key_Carrier.toFixed(2)} g · Battery holder ${mass.Battery_Holder.toFixed(2)} g · XIAO holder ${mass.XIAO_Rod_Holder.toFixed(2)} g. Printed plastic, excluding brim.` : 'Sliced mass pending.';
  if (!hasFramed) input.setHome(homeForModels());
  else { const distance = input.distance; input.setHome(homeForModels(), true); input.distance = distance; input.cancel(); }
  if (reframe && hasFramed) fit(); else render();
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
for (const id of ['revision', 'battery-end', 'battery-side', 'parts', 'references', 'caps']) ui[id].addEventListener('change', () => update({ reframe: id === 'parts' }));
ui.spacing.addEventListener('input', () => update());
try {
  const result = await fetch('../exports/review-scene.json', { cache: 'no-store' });
  if (!result.ok) throw new Error(`Model request failed (${result.status})`);
  data = await result.json(); update();
} catch (error) { ui.error.style.display = 'grid'; ui.error.textContent = `Unable to load model: ${error.message}`; }
