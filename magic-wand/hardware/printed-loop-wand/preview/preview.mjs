// Preview of the printed loop wand. Loads the exported STLs and manifest, places each part with
// its print-to-assembly transform, and shows the push-and-twist joint. Units are millimetres.
// URL parameters: ?profile=xiao|puck-legacy and ?view=both|<assembly key>, e.g. ?view=mug.
import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';

const EXPORTS = new URL('../exports/', import.meta.url);
const COLORS = {
  handle: 0x7c6cf0, 'button-pod-pilot': 0xf0a35c, 'shaft-lower': 0x4a4460, 'shaft-upper': 0x4a4460,
  'tip-cradle': 0xd9d4e8, 'tip-cap': 0xb7aef0, 'tip-xiao': 0xd9d4e8, 'puck-case': 0xece8f4, 'xiao-board': 0x40a06e,
};
const EXPLODE = { // Offsets in mm for the exploded view.
  'button-pod-pilot': [0, 30, 0], 'shaft-upper': [0, 0, 30], 'tip-cradle': [0, 0, 60], 'tip-cap': [0, 28, 60],
  'tip-xiao': [0, 0, 60], 'puck-case': [0, 14, 60], 'xiao-board': [0, 16, 60],
};
const STACK = 130; // Assemblies shown together are stacked this far apart in -Y, mm.

const view = document.getElementById('view');
const message = document.getElementById('message');
const ui = {
  profiles: document.getElementById('profiles'), handles: document.getElementById('handles'), grip: document.getElementById('grip'),
  joint: document.getElementById('joint'), jointText: document.getElementById('jointText'),
  exploded: document.getElementById('exploded'), section: document.getElementById('section'),
  checks: document.getElementById('checks'), parts: document.getElementById('parts'), tags: document.getElementById('tags'),
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
  const { joint, meshes_passed: meshes } = manifest.checks;
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
    manifest = await (await fetch(new URL('manifest.json', EXPORTS))).json();
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
      geometries[name] = fetch(new URL(parts[name].file, EXPORTS)).then((r) => r.arrayBuffer()).then((buffer) => {
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
      const mesh = new THREE.Mesh(await geometry(name), material(name.startsWith('handle-') ? 'handle' : name, COLORS[name] ?? COLORS.handle));
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
  const orbit = { yaw: 1.3, pitch: 0.22, distance: 900 };
  let shown = [];

  function navigate(next, push = true) {
    const framing = next.profile !== state.profile || next.view !== state.view;
    state = next;
    if (push) history.pushState(null, '', link(state));
    if (framing) reset();
    update();
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
      choice(keys.length === 2 ? 'Both' : 'All', { profile: state.profile, view: 'both' }, state.view === 'both'),
      ...keys.map((k) => choice(manifest.assemblies[`${state.profile}-${k}`].label, { profile: state.profile, view: k }, state.view === k)),
    );
    ui.grip.textContent = state.view === 'both'
      ? (state.profile === 'xiao' ? 'Green is the documented XIAO outline, for reference only.' : 'Legacy Puck.js tip, kept for the original wand.')
      : parts[manifest.assemblies[`${state.profile}-${state.view}`].parts[0]].role;
    ui.checks.replaceChildren(...describeChecks(manifest, state.profile).map((text) => {
      const li = document.createElement('li');
      li.textContent = text;
      return li;
    }));
    ui.parts.replaceChildren(...manifest.parts.filter((p) => p.profile === 'shared' || p.profile === state.profile).map((part) => {
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
    shown = Object.values(instances).filter((i) => i.profile === state.profile && (state.view === 'both' || i.key === state.view));
    for (const i of Object.values(instances)) i.group.visible = shown.includes(i);
    shown.forEach((i, k) => { i.group.position.set(0, -STACK * k, 0); });

    const t = Number(ui.joint.value) / 100;
    const push = Math.min(t / 0.5, 1);
    const turn = Math.max((t - 0.5) / 0.5, 0);
    const angle = -twist * (1 - turn); // Wand angle: clockwise seen from the tip is positive.
    for (const i of shown) {
      i.wand.rotation.z = THREE.MathUtils.degToRad(-angle);
      i.wand.position.z = travel * (1 - push);
      const spread = ui.exploded.checked;
      for (const [mesh, base] of i.home) {
        const offset = spread ? EXPLODE[mesh.name] ?? [0, 0, 0] : [0, 0, 0];
        mesh.position.set(base.x + offset[0], base.y + offset[1], base.z + offset[2]);
      }
    }
    ui.jointText.value = t === 0 ? 'Out' : t < 0.5 ? 'Pushing in' : t === 0.5 ? 'Pushed in' : t < 1 ? `Twisted ${Math.round(twist * turn)}°` : 'Locked';
    for (const m of Object.values(materials)) m.clippingPlanes = ui.section.checked ? [clip] : [];
    render();
  }

  function reset() {
    const count = Object.values(instances).filter((i) => i.profile === state.profile && (state.view === 'both' || i.key === state.view)).length;
    target.set(0, -10 - (STACK * (count - 1)) / 2, 250);
    Object.assign(orbit, { yaw: 1.3, pitch: 0.22, distance: 850 + 140 * (count - 1) });
  }

  const anchor = new THREE.Vector3();
  function render() {
    const { yaw, pitch, distance } = orbit;
    camera.position.set(
      target.x + distance * Math.cos(pitch) * Math.sin(yaw),
      target.y + distance * Math.sin(pitch),
      target.z + distance * Math.cos(pitch) * Math.cos(yaw),
    );
    camera.lookAt(target);
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
    render();
  }

  let drag = null;
  const canvas = renderer.domElement;
  canvas.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', (e) => {
    if (!drag) return;
    orbit.yaw -= (e.clientX - drag.x) * 0.006;
    orbit.pitch = Math.max(-1.45, Math.min(1.45, orbit.pitch + (e.clientY - drag.y) * 0.006));
    drag = { x: e.clientX, y: e.clientY };
    render();
  });
  canvas.addEventListener('pointerup', () => { drag = null; });
  canvas.addEventListener('pointercancel', () => { drag = null; });
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    orbit.distance = Math.max(80, Math.min(3000, orbit.distance * Math.exp(e.deltaY * 0.001)));
    render();
  }, { passive: false });
  canvas.addEventListener('dblclick', () => { reset(); render(); });
  window.addEventListener('popstate', () => navigate(readState(manifest), false));

  ui.joint.addEventListener('input', update);
  ui.exploded.addEventListener('change', update);
  ui.section.addEventListener('change', update);
  new ResizeObserver(resize).observe(view);
  reset();
  update();
  resize();
}

main();
