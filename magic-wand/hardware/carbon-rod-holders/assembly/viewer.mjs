// All holder components share the existing Three.js controls. Each CAD revision
// supplies exact actors and sampled assembly transforms, never another drawing.
import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { FreeViewInput } from '../../printed-loop-wand/preview/free-view-input.mjs';
import { bindFreeViewControls, installViewTools } from '../../printed-loop-wand/preview/free-view-controls.mjs';
import { applyViewerWheel } from '../../carbon-rod-holders-r7-spring-clips/preview/wheel-input.mjs';
import { parseBinaryStl } from '../../printed-loop-wand/preview/stl-geometry.mjs';
import { sampledPose, validateGuide, identity } from './assembly-data.mjs';
import { legacyR20 } from './legacy-r20.mjs';

const base = new URL('./', import.meta.url), view = document.getElementById('view');
const versions = document.getElementById('version'), modules = document.getElementById('module');
const input = new FreeViewInput({ minDistance: 8, maxDistance: 900 });
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x12151c);
scene.add(new THREE.HemisphereLight(0xe8f4ff, 0x424154, 2.5));
const camera = new THREE.PerspectiveCamera(32, 1, .1, 2000); scene.add(camera);
const light = new THREE.DirectionalLight(0xffffff, 3); light.position.set(-1, 2, 3); camera.add(light);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); view.prepend(renderer.domElement);
const canvas = renderer.domElement; canvas.tabIndex = 0;
canvas.setAttribute('aria-label', '3D assembly. Drag to rotate; scroll or pinch to zoom.');
let guide, guideUrl, group, actors = {}, module, tools, catalog, loadId = 0, versionLoadId = 0;
const geometries = new Map();

function render() {
  camera.position.set(...input.camera());
  camera.up.set(...input.cameraUp());
  camera.lookAt(...input.target);
  renderer.render(scene, camera);
  tools?.update();
}
function fit() {
  if (!group) return;
  const bounds = new THREE.Box3();
  for (const [id, object] of Object.entries(actors)) if (module.actors[id].frame !== false) bounds.expandByObject(object);
  if (bounds.isEmpty()) bounds.setFromObject(group);
  bounds.expandByScalar(2); input.fitBounds(bounds.min.toArray(), bounds.max.toArray(), { aspect: camera.aspect }); render();
}
function reset() {
  input.rotation.setFromEuler(new THREE.Euler(...(module?.rotation ?? [.95, 0, .65]), 'ZXY'));
  input.syncAngles();
  fit();
}
function chooseMode(mode) { input.setMode(mode); for (const button of document.querySelectorAll('[data-mode]')) button.setAttribute('aria-pressed', String(button.dataset.mode === mode)); render(); }
function applyPose({ index, fraction }) {
  const sample = sampledPose(module, index, fraction);
  for (const [id, object] of Object.entries(actors)) {
    const m = sample[id] || identity();
    object.matrix.set(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10], m[11], 0, 0, 0, 1);
    object.matrixWorldNeedsUpdate = true;
    if (object.morphTargetInfluences) object.morphTargetInfluences[0] = sample.morphs?.[id] ?? 0;
  }
  document.body.dataset.step = String(index); document.body.dataset.fraction = String(fraction); render();
}
async function geometry(record, sourceUrl) {
  if (record.geometry) {
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(record.geometry.vertices.flat(), 3));
    if (record.geometry.faces) { g.setIndex(record.geometry.faces.flat()); g.computeVertexNormals(); }
    return g;
  }
  if (record.primitive) {
    const p = record.primitive;
    if (p.type !== 'cylinder') throw new Error('Unsupported reference shape');
    const g = new THREE.CylinderGeometry(p.radius, p.radius, p.length, 48);
    if (p.axis === 'z') g.rotateX(Math.PI / 2);
    return g;
  }
  const url = new URL(record.file, record.baseUrl || sourceUrl).href;
  if (!geometries.has(url)) {
    const pending = fetch(url).then(async response => {
      if (!response.ok) throw new Error('Model could not be loaded');
      return parseBinaryStl(await response.arrayBuffer());
    }).catch(error => {
      geometries.delete(url);
      throw error;
    });
    geometries.set(url, pending);
  }
  return geometries.get(url);
}
async function chooseModule() {
  const request = ++loadId; tools?.assembly.pause(); document.body.dataset.ready = 'loading';
  const next = guide.modules[modules.value], sourceUrl = guideUrl, nextActors = {}, nextGroup = new THREE.Group();
  try {
    for (const [id, record] of Object.entries(next.actors)) {
      const rest = await geometry(record, sourceUrl);
      const color = record.color || '#29a5b7', opacity = record.opacity ?? 1;
      let g = rest;
      if (record.morphFile) {
        const target = await geometry({ file: record.morphFile, baseUrl: record.baseUrl }, sourceUrl);
        const positions = target.getAttribute('position');
        if (positions.count !== rest.getAttribute('position').count) throw new Error('Assembly spring shapes do not match');
        // The target shares the exact STL vertex order. Only this component owns
        // the morph binding, so an ordinary view can still reuse the cached STL.
        g = rest.clone();
        g.morphAttributes.position = [positions];
      }
      const material = record.lines ? new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity }) : new THREE.MeshStandardMaterial({ color, roughness: .5, metalness: .08, flatShading: true, transparent: opacity < 1, opacity, depthWrite: opacity === 1 });
      const object = record.lines ? new THREE.LineSegments(g, material) : new THREE.Mesh(g, material);
      object.userData.ownedGeometry = !record.file || Boolean(record.morphFile);
      object.matrixAutoUpdate = false; nextGroup.add(object); nextActors[id] = object;
    }
    if (request !== loadId) { disposeGroup(nextGroup); return; }
    if (group) { scene.remove(group); disposeGroup(group); }
    group = nextGroup; actors = nextActors; module = next; scene.add(group);
    document.getElementById('part-note').textContent = module.note;
    document.getElementById('parts').replaceChildren(...Object.entries(module.actors).map(([id, actor]) => {
      const item = document.createElement('li'); item.textContent = actor.label || id.replaceAll('_', ' '); item.style.setProperty('--part-color', actor.color || '#29a5b7'); return item;
    }));
    document.body.dataset.module = modules.value;
    tools.assembly.setSteps(module.steps); reset();
    const url = new URL(location.href); url.searchParams.set('version', versions.value); url.searchParams.set('component', modules.value); history.replaceState(null, '', url);
    document.body.dataset.ready = 'true'; document.getElementById('error').style.display = 'none';
  } catch (error) {
    disposeGroup(nextGroup);
    if (request === loadId) showError(error);
  }
}
function disposeGroup(value) {
  // Fetched STL geometries are cached for reuse; transient references belong to
  // their component and can be released as soon as the user switches away.
  for (const object of value.children) {
    object.material.dispose();
    if (object.userData.ownedGeometry) object.geometry.dispose();
  }
}
function showError(error) { const box = document.getElementById('error'); box.style.display = 'grid'; box.textContent = error.message; document.body.dataset.ready = 'error'; }
async function chooseVersion(preferred) {
  const versionRequest = ++versionLoadId; ++loadId;
  tools?.assembly.pause();
  modules.disabled = true;
  const version = catalog.versions.find(item => item.id === versions.value);
  const nextGuideUrl = version.guide ? new URL(version.guide, base) : base;
  const nextGuide = validateGuide(version.legacy ? await legacyR20() : await fetch(nextGuideUrl, { cache: 'no-store' }).then(response => { if (!response.ok) throw new Error('Assembly guide could not be loaded'); return response.json(); }));
  if (version.helper) {
    const helperUrl = new URL(version.helper, base), response = await fetch(helperUrl);
    if (!response.ok) throw new Error('Print-helper view could not be loaded');
    const helper = await response.json();
    const actor = { label: 'Disposable timelapse wipe tower', geometry: { vertices: helper.segments.flatMap(segment => [segment.slice(0, 3), segment.slice(3)]) }, lines: true, color: '#cb9f76' };
    nextGuide.modules.wipe_tower = { label: 'Wipe tower · discard', note: 'This upright piece is a print helper, not part of the wand. It catches nozzle ooze between smooth-timelapse photos. The lines show its actual sliced paths.', actors: { tower: actor }, steps: [{ title: 'Remove After Printing', caption: 'Let the plate cool, then remove and discard the tower. It does not attach to any holder.', duration: 2, samples: [{ tower: identity() }] }] };
  }
  if (versionRequest !== versionLoadId) return;
  guideUrl = nextGuideUrl; guide = nextGuide;
  modules.replaceChildren(...Object.entries(guide.modules).map(([id, value]) => new Option(value.label, id)));
  modules.disabled = false;
  modules.value = guide.modules[preferred] ? preferred : Object.keys(guide.modules)[0];
  document.getElementById('revision').textContent = version.label + ' · Assembly'; document.body.dataset.version = version.id;
  await chooseModule();
}

try {
  catalog = await fetch(new URL('catalog.json', base), { cache: 'no-store' }).then(response => response.json());
  const requested = new URLSearchParams(location.search);
  versions.replaceChildren(...catalog.versions.map(version => new Option(version.label, version.id)));
  versions.value = catalog.versions.some(version => version.id === requested.get('version')) ? requested.get('version') : catalog.current;
  // installViewTools emits the first frame immediately; an inert initial recipe
  // avoids accessing actors before their own source data has finished loading.
  tools = installViewTools({ view, input, fit, render, assembly: { host: document.getElementById('assembly'), steps: [{ title: 'Loading', caption: 'Loading assembly', duration: 1 }], onFrame: state => { if (module) applyPose(state); } } });
  bindFreeViewControls({ canvas, input, height: () => view.clientHeight, width: () => view.clientWidth, render, chooseMode, fit, wheel: event => applyViewerWheel(input, event, document.getElementById('wand-scroll').checked) });
  for (const button of document.querySelectorAll('[data-mode]')) button.addEventListener('click', () => chooseMode(button.dataset.mode));
  document.getElementById('plus').addEventListener('click', () => { input.zoom(.82); render(); });
  document.getElementById('minus').addEventListener('click', () => { input.zoom(1 / .82); render(); });
  document.getElementById('reset').addEventListener('click', reset);
  modules.addEventListener('change', () => chooseModule());
  versions.addEventListener('change', () => {
    const requestedVersion = versions.value;
    chooseVersion(modules.value).catch(error => {
      if (versions.value !== requestedVersion) return;
      if (guide) {
        versions.value = document.body.dataset.version;
        modules.disabled = false;
      }
      showError(error);
    });
  });
  new ResizeObserver(() => { camera.aspect = view.clientWidth / view.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(view.clientWidth, view.clientHeight, false); render(); }).observe(view);
  await chooseVersion(requested.get('component'));
} catch (error) { showError(error); }
