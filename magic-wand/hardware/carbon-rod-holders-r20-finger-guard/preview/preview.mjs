import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { FreeViewInput } from '../../printed-loop-wand/preview/free-view-input.mjs';
import { bindFreeViewControls, installViewTools } from '../../printed-loop-wand/preview/free-view-controls.mjs';
import { applyViewerWheel } from '../../carbon-rod-holders-r7-spring-clips/preview/wheel-input.mjs';
import { parseBinaryStl } from '../../printed-loop-wand/preview/stl-geometry.mjs';
import { recipes, routePose } from './assembly-recipe.mjs';

const view = document.getElementById('view'), select = document.getElementById('module');
const input = new FreeViewInput({ minDistance: 15, maxDistance: 900 });
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x12151c);
scene.add(new THREE.HemisphereLight(0xe8f4ff, 0x424154, 2.5));
const camera = new THREE.PerspectiveCamera(32, 1, .1, 2000); scene.add(camera);
const light = new THREE.DirectionalLight(0xffffff, 3); light.position.set(-1, 2, 3); camera.add(light);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); view.prepend(renderer.domElement);
const canvas = renderer.domElement; canvas.tabIndex = 0;
canvas.setAttribute('aria-label', '3D guard fitting. Drag to rotate; scroll or pinch to zoom.');
let data, guard, key, tools, direction = 'hand';
function render() {
  camera.position.set(...input.camera()); camera.up.set(...input.cameraUp()); camera.lookAt(...input.target);
  renderer.render(scene, camera); tools?.update();
}
function fit() {
  const bounds = new THREE.Box3().expandByObject(key).expandByObject(guard).expandByScalar(3);
  input.fitBounds(bounds.min.toArray(), bounds.max.toArray(), { aspect: camera.aspect }); render();
}
function reset() { input.rotation.setFromEuler(new THREE.Euler(.95, 0, .65, 'ZXY')); input.syncAngles(); fit(); }
function mesh(geometry, color, opacity = 1) {
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: .5,
    metalness: .08, flatShading: true, transparent: opacity < 1, opacity, depthWrite: opacity === 1 }));
}
async function part(name, color, opacity) {
  const response = await fetch('../exports/' + name + '-assembly.stl');
  if (!response.ok) throw new Error('Model could not be loaded');
  return mesh(parseBinaryStl(await response.arrayBuffer()), color, opacity);
}
function dimension(from, to, color) {
  const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...from), new THREE.Vector3(...to)]);
  scene.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color })));
  for (const point of [from, to]) {
    const cap = mesh(new THREE.SphereGeometry(.5, 12, 8), color); cap.position.set(...point); scene.add(cap);
  }
}
function updateAssembly({ fraction }) {
  const pose = routePose(data, direction, fraction);
  guard.position.y = pose.offset_mm;
  guard.material.color.setHex(pose.blocked ? 0xff625f : 0xee9842);
  document.body.dataset.fraction = String(fraction);
  document.body.dataset.offset = String(pose.offset_mm);
  document.body.dataset.blocked = String(pose.blocked);
  document.getElementById('measurement').textContent = pose.blocked
    ? `Blocked beyond ${pose.offset_mm.toFixed(2)} mm from the seated position. Do not force it.`
    : `Guard offset: ${pose.offset_mm.toFixed(2)} mm · seated ring gap: ${data.nominal_stop_gap_mm.toFixed(1)} mm`;
  render();
}
function chooseDirection() {
  direction = select.value;
  document.body.dataset.module = direction;
  document.getElementById('part-note').textContent = `Guard length: ${data.guard_length_mm.toFixed(1)} mm. Rod diameter: ${data.rod_diameter_mm.toFixed(1)} mm. At the seated position, the guard ends at Y ${data.guard_rear_y_mm.toFixed(1)} mm and the key-holder ring starts at Y ${data.key_ring_start_y_mm.toFixed(1)} mm.`;
  tools.assembly.setSteps(recipes[direction]);
  fit();
}
try {
  const response = await fetch('../exports/assembly-guide.json', { cache: 'no-store' });
  if (!response.ok) throw new Error('Assembly data could not be loaded');
  data = await response.json();
  if (data.revision !== 'R20') throw new Error('Incorrect model revision');
  key = await part('Key_Carrier', 0x8fa3c4, .65); guard = await part('Finger_Guard', 0xee9842, 1);
  scene.add(key, guard);
  for (const [name, record] of Object.entries(data.hardware)) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(record.vertices.flat(), 3));
    geometry.setIndex(record.faces.flat()); geometry.computeVertexNormals();
    scene.add(mesh(geometry, name.endsWith('_switch') ? 0x78c894 : 0x46574f, .55));
  }
  scene.add(mesh(new THREE.CylinderGeometry(data.rod_diameter_mm / 2, data.rod_diameter_mm / 2, 160, 48), 0x737d87, .25));
  dimension([32, data.guard_rear_y_mm - data.guard_length_mm, -8], [32, data.guard_rear_y_mm, -8], 0xee9842);
  dimension([0, data.guard_rear_y_mm, 0], [0, data.key_ring_start_y_mm, 0], 0xffdb6e);
  tools = installViewTools({ view, input, fit, render, assembly: { host: document.getElementById('assembly'), steps: recipes.hand, onFrame: updateAssembly } });
  bindFreeViewControls({ canvas, input, height: () => view.clientHeight, width: () => view.clientWidth, render,
    chooseMode: mode => { input.setMode(mode); for (const button of document.querySelectorAll('[data-mode]')) button.setAttribute('aria-pressed', String(button.dataset.mode === mode)); render(); },
    fit, wheel: event => applyViewerWheel(input, event, document.getElementById('wand-scroll').checked) });
  for (const button of document.querySelectorAll('[data-mode]')) button.addEventListener('click', () => {
    input.setMode(button.dataset.mode);
    for (const other of document.querySelectorAll('[data-mode]')) other.setAttribute('aria-pressed', String(other === button)); render();
  });
  document.getElementById('plus').addEventListener('click', () => { input.zoom(.82); render(); });
  document.getElementById('minus').addEventListener('click', () => { input.zoom(1 / .82); render(); });
  document.getElementById('reset').addEventListener('click', reset);
  select.addEventListener('change', chooseDirection);
  new ResizeObserver(() => { camera.aspect = view.clientWidth / view.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(view.clientWidth, view.clientHeight, false); render(); }).observe(view);
  chooseDirection(); reset(); document.body.dataset.ready = 'true';
} catch (error) {
  document.getElementById('error').style.display = 'grid'; document.getElementById('error').textContent = error.message;
  document.body.dataset.ready = 'error';
}
