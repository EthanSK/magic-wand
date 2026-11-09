// Inspect and animate the actual R19 exports. Playback changes transforms only;
// the checked print models, plate orientation and printer are never modified.
import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { FreeViewInput } from '../../printed-loop-wand/preview/free-view-input.mjs';
import { bindFreeViewControls, installViewTools } from '../../printed-loop-wand/preview/free-view-controls.mjs';
import { applyViewerWheel } from '../../carbon-rod-holders-r7-spring-clips/preview/wheel-input.mjs';
import { parseBinaryStl } from '../../printed-loop-wand/preview/stl-geometry.mjs';
import { recipes, assemblyPose } from './assembly-recipe.mjs';

const view = document.getElementById('view'), select = document.getElementById('module');
const input = new FreeViewInput({ minDistance: 15, maxDistance: 900 });
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x12151c);
scene.add(new THREE.HemisphereLight(0xe8f4ff, 0x424154, 2.5));
const camera = new THREE.PerspectiveCamera(32, 1, .1, 2000); scene.add(camera);
const light = new THREE.DirectionalLight(0xffffff, 3); light.position.set(-1, 2, 3); camera.add(light);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); view.prepend(renderer.domElement);
const canvas = renderer.domElement; canvas.tabIndex = 0;
canvas.setAttribute('aria-label', '3D assembly. Drag to rotate; scroll or pinch to zoom.');
const groups = {}, actors = {}, override = document.getElementById('wand-scroll');
let data, viewTools, kind = 'xiao';

function render() {
  camera.position.set(...input.camera()); camera.up.set(...input.cameraUp()); camera.lookAt(...input.target);
  renderer.render(scene, camera); viewTools?.update();
}
function fit() {
  // Frame the parts at this step; exclude the illustrative rod's distant end.
  // Never reframe during playback, so orbit/pan/zoom stay under user control.
  const a = actors[kind], bounds = new THREE.Box3();
  for (const object of [a.holder, a.retainer, a.board, a.cell, a.spacer].filter(Boolean)) bounds.expandByObject(object);
  bounds.expandByScalar(2);
  input.fitBounds(bounds.min.toArray(), bounds.max.toArray(), { aspect: camera.aspect }); render();
}
function reset() {
  // These CAD exports use Z for height and Y for the rod. Start above the tray
  // with Z visibly up, rather than inheriting the older viewer's Y-up pose.
  input.rotation.setFromEuler(new THREE.Euler(.95, 0, .65, 'ZXY'));
  input.syncAngles(); fit();
}
function chooseMode(mode) {
  input.setMode(mode);
  for (const b of document.querySelectorAll('[data-mode]')) b.setAttribute('aria-pressed', String(b.dataset.mode === mode));
  render();
}
function mesh(geometry, color, opacity = 1) {
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: .5, metalness: .08,
    flatShading: true, transparent: opacity < 1, opacity, depthWrite: opacity === 1 }));
}
function reference(name, color) {
  const g = data.geometry[name], geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(g.vertices.flat(), 3));
  geometry.setIndex(g.faces.flat()); geometry.computeVertexNormals();
  return mesh(geometry, color);
}
async function part(name, color) {
  const response = await fetch('../exports/' + name + '-assembly.stl');
  if (!response.ok) throw new Error('Model could not be loaded');
  return mesh(parseBinaryStl(await response.arrayBuffer()), color);
}
function updateAssembly({ index, fraction }) {
  const pose = assemblyPose(kind, index, fraction, data), a = actors[kind];
  if (kind === 'xiao') {
    const pivot = new THREE.Vector3(...data.board.pivot);
    a.board.rotation.x = pose.boardAngle;
    a.board.position.copy(pivot).sub(pivot.clone().applyAxisAngle(new THREE.Vector3(1, 0, 0), pose.boardAngle));
    a.board.position.y += pose.boardY; a.board.position.z += pose.boardZ;
    a.retainer.position.y = pose.keeperY;
  } else {
    a.cell.position.set(0, pose.cellY, pose.cellZ);
    a.spacer.position.y = pose.cellY; a.retainer.position.z = pose.doorZ;
  }
  a.rod.visible = pose.rodVisible; a.rod.position.y = 10 + pose.rodY;
  document.body.dataset.step = String(index); document.body.dataset.fraction = String(fraction);
  render();
}
function chooseModule() {
  kind = select.value;
  for (const [name, g] of Object.entries(groups)) g.visible = name === kind;
  document.getElementById('part-note').textContent = kind === 'xiao'
    ? 'Both ring bands are 2.4 mm wide. One has a sloping print lead-in, so it looks wider. The triangular hoop holes save weight; the keeper uses the side grooves.'
    : 'The spacer sits underneath the battery. To open the door, push its centre tab outward from the cell side and lift by the top bar.';
  document.body.dataset.module = kind;
  viewTools.assembly.setSteps(recipes[kind]); reset();
}

try {
  const response = await fetch('../exports/assembly-guide.json', { cache: 'no-store' });
  if (!response.ok) throw new Error('Assembly data could not be loaded');
  data = await response.json();
  if (data.revision !== 'carbon-rod-holders-r19-lightweight') throw new Error('Incorrect model revision');
  for (const name of ['xiao', 'battery']) {
    const group = new THREE.Group(); groups[name] = group; scene.add(group);
    const holder = await part(name === 'xiao' ? 'XIAO_Rod_Holder' : 'Battery_Holder', 0x29a5b7);
    const retainer = await part(name === 'xiao' ? 'XIAO_Near_Keeper' : 'Battery_End_Door', 0xee9842);
    const rod = mesh(new THREE.CylinderGeometry(data.rod.diameter_mm / 2, data.rod.diameter_mm / 2, data.rod.length_mm, 48), 0x737d87, .55);
    group.add(holder, retainer, rod); actors[name] = { holder, retainer, rod };
    if (name === 'xiao') {
      const board = new THREE.Group(); board.add(reference('board', 0x78c894));
      for (const component of data.board.components) board.add(reference(component, component === 'usb_c' ? 0xe5e7eb : 0x384453));
      group.add(board); actors[name].board = board;
    } else {
      const cell = reference('cell', 0x78c894), spacer = await part('Battery_Spacer_0p4mm', 0xbb9ce3);
      group.add(cell, spacer); Object.assign(actors[name], { cell, spacer });
    }
  }
  viewTools = installViewTools({ view, input, fit, render, assembly: { host: document.getElementById('assembly'), steps: recipes.xiao, onFrame: updateAssembly } });
  chooseModule();
  bindFreeViewControls({ canvas, input, height: () => view.clientHeight, width: () => view.clientWidth, render, chooseMode, fit,
    wheel: event => applyViewerWheel(input, event, override.checked) });
  for (const b of document.querySelectorAll('[data-mode]')) b.addEventListener('click', () => chooseMode(b.dataset.mode));
  document.getElementById('plus').addEventListener('click', () => { input.zoom(.82); render(); });
  document.getElementById('minus').addEventListener('click', () => { input.zoom(1 / .82); render(); });
  document.getElementById('reset').addEventListener('click', reset);
  select.addEventListener('change', chooseModule);
  const resize = () => { camera.aspect = view.clientWidth / view.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(view.clientWidth, view.clientHeight, false); render(); };
  new ResizeObserver(resize).observe(view); resize(); reset();
  document.body.dataset.ready = 'true';
  // No audio/video element: canvas playback must not take Spotify's media keys.
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches && !document.hidden) viewTools.assembly.play();
} catch (error) {
  document.getElementById('error').style.display = 'grid';
  document.getElementById('error').textContent = error.message;
  document.body.dataset.ready = 'error';
}
