// Preview of the printed loop wand. Loads the exported STLs and manifest, places each part with
// its print-to-assembly transform, and shows the push-and-twist joint. Units are millimetres.
// URL parameters: ?profile=xiao|puck-legacy and ?view=both|<assembly key>, e.g. ?view=mug.
import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';
import { ViewInput, MODES, frameBounds } from './view-input.mjs';

const EXPORTS = new URL('../exports/', import.meta.url);
const COLORS = {
  handle: 0x7c6cf0, 'button-pod-pilot': 0xf0a35c, 'shaft-lower': 0x4a4460, 'shaft-upper': 0x4a4460,
  'tip-cradle': 0xd9d4e8, 'tip-cap': 0xb7aef0, 'tip-xiao': 0xd9d4e8, 'puck-case': 0xece8f4, 'xiao-board': 0x40a06e,
};
const EXPLODE = { // Offsets in mm for the exploded view.
  'button-pod-pilot': [0, 30, 0], 'shaft-upper': [0, 0, 30], 'tip-cradle': [0, 0, 60], 'tip-cap': [0, 28, 60],
  'tip-xiao': [0, 0, 60], 'puck-case': [0, 14, 60], 'xiao-board': [0, 16, 60],
};
// Generic part role, so every profile's parts get the right colour and exploded offset.
function role(name) {
  for (const [prefix, r] of [['handle-', 'handle'], ['button-pod', 'button-pod-pilot'], ['shaft-lower', 'shaft-lower'], ['shaft-upper', 'shaft-upper']]) {
    if (name.startsWith(prefix)) return r;
  }
  return name;
}
const STACK = 130; // Assemblies shown together are stacked this far apart in -Y, mm.
const MODE_KEY = 'printed-loop-wand-preview-mode'; // Remembers Turn/Move/Zoom for this page.
const LIVE_VIEW_KEY = 'printed-loop-wand-live-view';
const HINTS = {
  turn: 'Drag or scroll to turn · Pinch to zoom',
  move: 'Drag or scroll to move · Pinch to zoom',
  zoom: 'Drag or scroll to zoom',
};

const view = document.getElementById('view');
const message = document.getElementById('message');
const ui = {
  profiles: document.getElementById('profiles'), handles: document.getElementById('handles'), grip: document.getElementById('grip'),
  joint: document.getElementById('joint'), jointText: document.getElementById('jointText'),
  exploded: document.getElementById('exploded'), section: document.getElementById('section'),
  checks: document.getElementById('checks'), parts: document.getElementById('parts'), tags: document.getElementById('tags'),
  modes: document.getElementById('modes'), zoomButtons: document.querySelectorAll('[data-zoom]'),
  resetView: document.getElementById('resetView'), hint: document.getElementById('hint'),
};

function show(text) {
  message.textContent = text;
  message.style.display = 'grid';
}

function parseStl(buffer) {
  const data = new DataView(buffer);
  const count = data.getUint32(80, true);
  const positions = new Float32Array(count * 9);
  for (let i = 0; i < count; i++) {
    const offset = 84 + i * 50 + 12;
    for (let k = 0; k < 9; k++) positions[i * 9 + k] = data.getFloat32(offset + k * 4, true);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  return geometry;
}

function matrixFrom(rows) {
  const m = new THREE.Matrix4();
  m.set(...rows.flat());
  return m;
}

function describeChecks(manifest, profile) {
  const { meshes_passed: meshes } = manifest.checks;
  const joint = manifest.checks[manifest.profiles[profile].joint_kind === 'mirrored' ? 'tapered_joint' : 'joint'];
  const assembly = Object.values(manifest.checks.assembly).filter((a) => a.profile === profile);
  const angles = joint.insertable_angles_deg.map((a) => a - joint.entry_angle_deg);
  const spread = Math.max(...angles.map(Math.abs));
  const wires = assembly.every((a) => Object.values(a.wire_probe_overlap_mm3).every((v) => v < 0.01));
  const clear = assembly.every((a) => a.unexpected.length === 0);
  return [
    `Pushes in only within ±${spread}° of the entry angle`,
    `Twist overlap is the cam only: up to ${joint.twist_max_axial_overlap_mm} mm`,
    'Locked: pulling out or twisting further collides',
    clear ? 'No unintended collisions in these assemblies' : 'Unintended collisions found',
    wires ? 'A 3 mm wire path clears every part' : 'Wire path blocked',
    meshes ? 'Every part is a closed solid that fits the bed' : 'Mesh check failed',
  ];
}

function readState(manifest) {
  const params = new URLSearchParams(location.search);
  const profile = manifest.profiles[params.get('profile')] ? params.get('profile') : manifest.current_profile;
  const keys = manifest.profiles[profile].assemblies.map((id) => id.slice(profile.length + 1));
  const view = keys.includes(params.get('view')) ? params.get('view') : 'both';
  return { profile, view };
}

function link(state) {
  const params = new URLSearchParams();
  params.set('profile', state.profile);
  if (state.view !== 'both') params.set('view', state.view);
  return `?${params}`;
}

async function main() {
  let manifest;
  try {
    manifest = await (await fetch(new URL('manifest.json', EXPORTS), { cache: 'no-store' })).json();
  } catch {
    show("Couldn't load the exports. Serve the repository root, as in the README.");
    return;
  }
  const parts = Object.fromEntries(manifest.parts.map((p) => [p.name, p]));
  let state = readState(manifest);

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
  } catch {
    show('3D preview needs WebGL.');
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.localClippingEnabled = true;
  view.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x121018);
  scene.add(new THREE.HemisphereLight(0xf4f0ff, 0x24202e, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(300, 400, 200);
  scene.add(sun);
  const camera = new THREE.PerspectiveCamera(32, 1, 5, 6000);

  const clip = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0); // Keeps x <= 0: a cut through the middle.
  const materials = {};
  const material = (key, color) => {
    if (!materials[key]) {
      materials[key] = new THREE.MeshStandardMaterial({ color, roughness: 0.65, metalness: 0, side: THREE.DoubleSide, flatShading: true });
    }
    return materials[key];
  };

  // Geometry is loaded once per part and shared by every assembly that uses it.
  const geometries = {};
  async function geometry(name) {
    if (!geometries[name]) {
      geometries[name] = fetch(new URL(parts[name].file, EXPORTS), { cache: 'no-store' }).then((r) => r.arrayBuffer()).then((buffer) => {
        const g = parseStl(buffer);
        g.applyMatrix4(matrixFrom(parts[name].print_to_assembly));
        g.computeVertexNormals();
        return g;
      });
    }
    return geometries[name];
  }
  function reference(kind) {
    const { layout } = manifest;
    let mesh;
    if (kind === 'xiao-board') {
      mesh = new THREE.Mesh(new THREE.BoxGeometry(...layout.xiao.board_size), material(kind, COLORS[kind]));
      mesh.position.set(...layout.xiao.board_center);
    } else {
      const m = material(kind, COLORS[kind]);
      m.transparent = true;
      m.opacity = 0.55;
      mesh = new THREE.Mesh(new THREE.CylinderGeometry(layout.puck_case.diameter / 2, layout.puck_case.diameter / 2, layout.puck_case.height, 48), m);
      mesh.position.set(...layout.puck_center);
    }
    mesh.name = kind;
    return mesh;
  }

  // One group per assembly: handle and pod stay put; the wand group twists into the socket.
  const instances = {};
  for (const [id, a] of Object.entries(manifest.assemblies)) {
    const group = new THREE.Group();
    const wand = new THREE.Group();
    const meshes = await Promise.all(a.parts.map(async (name) => {
      const continuous = manifest.profiles[a.profile].continuous_body && role(name).startsWith('shaft-');
      const materialKey = continuous || role(name) === 'handle' ? 'handle' : name;
      const mesh = new THREE.Mesh(await geometry(name), material(materialKey, continuous ? COLORS.handle : COLORS[name] ?? COLORS[role(name)] ?? COLORS.handle));
      mesh.name = name;
      return mesh;
    }));
    for (const mesh of meshes) (mesh.name.startsWith('handle-') || mesh.name === 'button-pod-pilot' ? group : wand).add(mesh);
    wand.add(reference(manifest.profiles[a.profile].reference));
    group.add(wand);
    group.visible = false;
    scene.add(group);
    const tag = document.createElement('div');
    tag.className = 'tag';
    tag.textContent = a.label;
    ui.tags.append(tag);
    const home = new Map([...group.children, ...wand.children].filter((m) => m.isMesh).map((m) => [m, m.position.clone()]));
    instances[id] = { group, wand, tag, home, profile: a.profile, key: id.slice(a.profile.length + 1), label: a.label, handle: a.parts[0] };
  }

  const twist = manifest.layout.twist_deg;
  const travel = 40; // How far out the spigot starts, mm.
  const target = new THREE.Vector3();
  let savedMode = null;
  try { savedMode = localStorage.getItem(MODE_KEY); } catch { /* Storage can be unavailable. */ }
  const input = new ViewInput({ fov: camera.fov, mode: savedMode ?? 'turn' });
  let shown = [];

  function navigate(next, push = true) {
    const framing = next.profile !== state.profile || next.view !== state.view;
    state = next;
    if (push) history.pushState(null, '', link(state));
    update();
    if (framing) { reset(); render(); }
  }
  function choice(text, next, current) {
    const a = document.createElement('a');
    a.href = link(next);
    a.textContent = text;
    if (current) a.setAttribute('aria-current', 'true');
    a.addEventListener('click', (e) => { e.preventDefault(); navigate(next); });
    return a;
  }

  function fillPanel() {
    const profile = manifest.profiles[state.profile];
    ui.profiles.replaceChildren(...Object.entries(manifest.profiles).map(([key, p]) =>
      choice(p.label, { profile: key, view: 'both' }, key === state.profile)));
    const keys = profile.assemblies.map((id) => id.slice(state.profile.length + 1));
    ui.handles.replaceChildren(
      choice((profile.overview ?? keys).length === 2 ? 'Both' : 'All', { profile: state.profile, view: 'both' }, state.view === 'both'),
      ...keys.map((k) => choice(manifest.assemblies[`${state.profile}-${k}`].label, { profile: state.profile, view: k }, state.view === k)),
    );
    ui.grip.textContent = state.view === 'both'
      ? (profile.reference === 'xiao-board' ? 'Green is the documented XIAO outline, for reference only.' : 'Legacy Puck.js tip, kept for the original wand.')
      : parts[manifest.assemblies[`${state.profile}-${state.view}`].parts[0]].role;
    ui.checks.replaceChildren(...describeChecks(manifest, state.profile).map((text) => {
      const li = document.createElement('li');
      li.textContent = text;
      return li;
    }));
    const used = new Set(profile.assemblies.flatMap((id) => manifest.assemblies[id].parts));
    const pods = [...used].some((n) => role(n) === 'button-pod-pilot');
    const usesPart = (p) => used.has(p.name) || (p.group === 'pod' && pods)
      || (p.group === 'coupon' && (p.profile === state.profile || (p.profile === 'shared' && !state.profile.startsWith('tapered'))));
    ui.parts.replaceChildren(...manifest.parts.filter(usesPart).map((part) => {
      const row = document.createElement('tr');
      const name = document.createElement('td');
      name.textContent = part.name;
      name.title = `${part.role}. ${part.print_orientation}. Supports: ${part.supports}.`;
      const size = document.createElement('td');
      size.textContent = part.mesh.print_size_mm.map((v) => Math.round(v)).join(' × ');
      row.append(name, size);
      return row;
    }));
  }

  function update() {
    fillPanel();
    const overview = manifest.profiles[state.profile].overview;
    shown = Object.values(instances).filter((i) => i.profile === state.profile &&
      (state.view === 'both' ? !overview || overview.includes(i.key) : i.key === state.view));
    for (const i of Object.values(instances)) i.group.visible = shown.includes(i);
    shown.forEach((i, k) => { i.group.position.set(0, -STACK * k, 0); });

    const t = Number(ui.joint.value) / 100;
    const push = Math.min(t / 0.5, 1);
    const turn = Math.max((t - 0.5) / 0.5, 0);
    const entry = manifest.profiles[state.profile].joint_kind === 'mirrored' ? twist : -twist;
    const angle = entry * (1 - turn); // The mirrored socket turns in the opposite direction.
    for (const i of shown) {
      i.wand.rotation.z = THREE.MathUtils.degToRad(-angle);
      i.wand.position.z = travel * (1 - push);
      const spread = ui.exploded.checked;
      for (const [mesh, base] of i.home) {
        const offset = spread ? EXPLODE[mesh.name] ?? EXPLODE[role(mesh.name)] ?? [0, 0, 0] : [0, 0, 0];
        mesh.position.set(base.x + offset[0], base.y + offset[1], base.z + offset[2]);
      }
    }
    ui.jointText.value = t === 0 ? 'Out' : t < 0.5 ? 'Pushing in' : t === 0.5 ? 'Pushed in' : t < 1 ? `Twisted ${Math.round(twist * turn)}°` : 'Locked';
    for (const m of Object.values(materials)) m.clippingPlanes = ui.section.checked ? [clip] : [];
    render();
  }

  function reset(preserveView = false) {
    const bounds = new THREE.Box3();
    for (const i of shown) bounds.union(new THREE.Box3().setFromObject(i.group));
    if (!bounds.isEmpty()) input.setHome(frameBounds(bounds.min.toArray(), bounds.max.toArray(), {
      aspect: view.clientWidth / Math.max(view.clientHeight, 1), fov: camera.fov,
      yaw: manifest.profiles[state.profile].view_yaw ?? 1.3,
      pitch: manifest.profiles[state.profile].view_pitch ?? 0.22,
    }), preserveView);
  }

  const anchor = new THREE.Vector3();
  function render() {
    camera.position.set(...input.camera());
    camera.lookAt(target.set(...input.target));
    renderer.render(scene, camera);
    const { clientWidth: w, clientHeight: h } = view;
    for (const i of Object.values(instances)) {
      i.tag.style.display = shown.includes(i) ? 'block' : 'none';
      if (!shown.includes(i)) continue;
      anchor.set(0, 36, 40).add(i.group.position).project(camera);
      i.tag.style.left = `${((anchor.x + 1) / 2) * w}px`;
      i.tag.style.top = `${((1 - anchor.y) / 2) * h}px`;
    }
  }

  function resize() {
    const { clientWidth: w, clientHeight: h } = view;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(h, 1);
    camera.updateProjectionMatrix();
    reset(true);
    render();
  }

  const canvas = renderer.domElement;
  canvas.tabIndex = 0;
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', '3D view of the wand. Arrow keys turn, move or zoom by the selected mode; plus and minus zoom; 0 resets. T, M and Z choose Turn, Move or Zoom.');
  canvas.setAttribute('aria-describedby', 'hint');

  function showMode() {
    for (const button of ui.modes.querySelectorAll('[data-mode]')) button.setAttribute('aria-pressed', String(button.dataset.mode === input.mode));
    canvas.dataset.mode = input.mode;
    ui.hint.textContent = HINTS[input.mode];
  }
  function chooseMode(mode) {
    if (!input.setMode(mode)) return;
    try { localStorage.setItem(MODE_KEY, mode); } catch { /* Not remembered without storage. */ }
    showMode();
  }

  canvas.addEventListener('pointerdown', (e) => {
    input.pointerDown(e.pointerId, e.clientX, e.clientY);
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (input.pointerMove(e.pointerId, e.clientX, e.clientY, view.clientHeight)) render();
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    canvas.addEventListener(type, (e) => input.pointerUp(e.pointerId));
  }
  window.addEventListener('blur', () => input.cancel());
  // Only the 3D view takes scrolling; the sidebar and page scroll normally.
  canvas.addEventListener('wheel', (e) => {
    if (input.wheel(e, view.clientHeight, window.innerHeight)) {
      e.preventDefault();
      render();
    }
  }, { passive: false });
  canvas.addEventListener('keydown', (e) => {
    if (e.metaKey || e.altKey || e.ctrlKey) return; // Leave browser shortcuts, such as page zoom, alone.
    const before = input.mode;
    if (!input.key(e, view.clientHeight)) return;
    e.preventDefault();
    if (input.mode !== before) chooseMode(input.mode);
    render();
  });
  canvas.addEventListener('dblclick', () => { reset(); render(); });
  ui.modes.addEventListener('click', (e) => {
    const mode = e.target.closest('[data-mode]')?.dataset.mode;
    if (MODES.includes(mode)) chooseMode(mode);
  });
  for (const button of ui.zoomButtons) {
    button.addEventListener('click', () => { input.zoomSteps(Number(button.dataset.zoom)); render(); });
  }
  ui.resetView.addEventListener('click', () => { reset(); render(); });
  showMode();
  window.addEventListener('popstate', () => navigate(readState(manifest), false));

  ui.joint.addEventListener('input', update);
  ui.exploded.addEventListener('change', update);
  ui.section.addEventListener('change', update);
  new ResizeObserver(resize).observe(view);
  update();
  reset();
  resize();
  try {
    const saved = JSON.parse(sessionStorage.getItem(LIVE_VIEW_KEY) ?? 'null');
    sessionStorage.removeItem(LIVE_VIEW_KEY);
    if (saved?.url === location.href) {
      ui.joint.value = saved.joint;
      ui.exploded.checked = saved.exploded;
      ui.section.checked = saved.section;
      update();
      input.restore(saved.view);
      showMode();
      render();
    }
  } catch { /* An unavailable or malformed saved view does not block the model. */ }

  // The local CAD viewer should show regenerated models without asking Ethan to reload.
  // Preserve his camera and assembly choices, and never reload during a pointer drag.
  if (['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) {
    const loaded = JSON.stringify(manifest);
    let checking = false;
    setInterval(async () => {
      if (checking || document.hidden || input.pointers.size) return;
      checking = true;
      try {
        const response = await fetch(new URL('manifest.json', EXPORTS), { cache: 'no-store' });
        if (!response.ok) return;
        const next = await response.json();
        if (JSON.stringify(next) !== loaded && !input.pointers.size) {
          sessionStorage.setItem(LIVE_VIEW_KEY, JSON.stringify({ url: location.href, view: input.snapshot(),
            joint: ui.joint.value, exploded: ui.exploded.checked, section: ui.section.checked }));
          location.reload();
        }
      } catch { /* Keep the working view while exports are temporarily unavailable. */ }
      finally { checking = false; }
    }, 2000);
  }
}

main();
