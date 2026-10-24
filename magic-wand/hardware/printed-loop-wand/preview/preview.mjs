// Preview of the printed loop wand. Loads the exported STLs and manifest, places each part with
// its print-to-assembly transform, and shows the push-and-twist joint. Units are millimetres.
import * as THREE from '../../../../docs/lib/three-0.185.1/three.module.min.js';

const EXPORTS = new URL('../exports/', import.meta.url);
const COLORS = { handle: 0x7c6cf0, pod: 0xf0a35c, shaft: 0x4a4460, tip: 0xd9d4e8, cap: 0xb7aef0, puck: 0xece8f4 };
const EXPLODE = { // Offsets in mm for the exploded view.
  'button-pod-pilot': [0, 30, 0], 'shaft-lower': [0, 0, 0], 'shaft-upper': [0, 0, 30],
  'tip-cradle': [0, 0, 60], 'tip-cap': [0, 28, 60], puck: [0, 14, 60],
};

const view = document.getElementById('view');
const message = document.getElementById('message');
const ui = {
  handles: document.getElementById('handles'), grip: document.getElementById('grip'),
  joint: document.getElementById('joint'), jointText: document.getElementById('jointText'),
  exploded: document.getElementById('exploded'), section: document.getElementById('section'),
  checks: document.getElementById('checks'), parts: document.getElementById('parts'),
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

function describeChecks(manifest) {
  const { joint, assembly, meshes_passed: meshes } = manifest.checks;
  const angles = joint.insertable_angles_deg.map((a) => a - joint.entry_angle_deg);
  const spread = Math.max(...angles.map(Math.abs));
  const wires = Object.values(assembly).every((a) => Object.values(a.wire_probe_overlap_mm3).every((v) => v < 0.01));
  const clear = Object.values(assembly).every((a) => a.unexpected.length === 0);
  return [
    `Pushes in only within ±${spread}° of the entry angle`,
    `Twist overlap is the cam only: up to ${joint.twist_max_axial_overlap_mm} mm`,
    `Locked: pulling out or twisting further collides`,
    clear ? 'No unintended collisions in any assembly' : 'Unintended collisions found',
    wires ? 'A 3 mm wire path clears every part' : 'Wire path blocked',
    meshes ? 'Every part is a closed solid that fits the bed' : 'Mesh check failed',
  ];
}

function fillPanel(manifest) {
  ui.checks.replaceChildren(...describeChecks(manifest).map((text) => {
    const li = document.createElement('li');
    li.textContent = text;
    return li;
  }));
  ui.parts.replaceChildren(...manifest.parts.map((part) => {
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

async function main() {
  let manifest;
  try {
    manifest = await (await fetch(new URL('manifest.json', EXPORTS))).json();
  } catch {
    show("Couldn't load the exports. Serve the repository root, as in the README.");
    return;
  }
  fillPanel(manifest);

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
  const camera = new THREE.PerspectiveCamera(32, 1, 5, 5000);

  const clip = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0); // Keeps x <= 0: a cut through the middle.
  const material = (color) => new THREE.MeshStandardMaterial({ color, roughness: 0.65, metalness: 0, side: THREE.DoubleSide, flatShading: true });
  const materials = [];
  const parts = Object.fromEntries(manifest.parts.map((p) => [p.name, p]));

  async function load(name, color) {
    const buffer = await (await fetch(new URL(parts[name].file, EXPORTS))).arrayBuffer();
    const geometry = parseStl(buffer);
    geometry.applyMatrix4(matrixFrom(parts[name].print_to_assembly));
    geometry.computeVertexNormals();
    const m = material(color);
    materials.push(m);
    const mesh = new THREE.Mesh(geometry, m);
    mesh.name = name;
    return mesh;
  }

  const variants = Object.keys(manifest.assemblies);
  const handles = {};
  const wand = new THREE.Group(); // Everything that twists into the handle.
  const loaded = await Promise.all([
    ...variants.map((v) => load(`handle-${v}`, COLORS.handle)),
    load('button-pod-pilot', COLORS.pod), load('shaft-lower', COLORS.shaft), load('shaft-upper', COLORS.shaft),
    load('tip-cradle', COLORS.tip), load('tip-cap', COLORS.cap),
  ]);
  variants.forEach((v, i) => { handles[v] = loaded[i]; scene.add(loaded[i]); });
  const [pod, lower, upper, cradle, cap] = loaded.slice(variants.length);
  scene.add(pod);
  wand.add(lower, upper, cradle, cap);
  const { puck_center: puckCenter, puck_case: puckCase } = manifest.layout;
  const puckMaterial = material(COLORS.puck);
  puckMaterial.transparent = true;
  puckMaterial.opacity = 0.55;
  materials.push(puckMaterial);
  const puck = new THREE.Mesh(new THREE.CylinderGeometry(puckCase.diameter / 2, puckCase.diameter / 2, puckCase.height, 48), puckMaterial);
  puck.position.set(...puckCenter);
  puck.name = 'puck';
  wand.add(puck);
  scene.add(wand);
  const home = new Map([pod, lower, upper, cradle, cap, puck].map((m) => [m, m.position.clone()]));

  let variant = variants.includes('straight') ? 'straight' : variants[0];
  ui.handles.replaceChildren(...variants.map((v) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = manifest.assemblies[v].label;
    button.addEventListener('click', () => { variant = v; update(); });
    button.dataset.variant = v;
    return button;
  }));

  const twist = manifest.layout.twist_deg;
  const travel = 40; // How far out the spigot starts, mm.

  function update() {
    for (const [v, mesh] of Object.entries(handles)) mesh.visible = v === variant;
    for (const button of ui.handles.children) button.setAttribute('aria-pressed', String(button.dataset.variant === variant));
    ui.grip.textContent = parts[`handle-${variant}`].role;

    const t = Number(ui.joint.value) / 100;
    const push = Math.min(t / 0.5, 1);
    const turn = Math.max((t - 0.5) / 0.5, 0);
    const angle = -twist * (1 - turn); // Wand angle: clockwise seen from the tip is positive.
    wand.rotation.z = THREE.MathUtils.degToRad(-angle);
    wand.position.z = travel * (1 - push);
    ui.jointText.value = t === 0 ? 'Out' : t < 0.5 ? 'Pushing in' : t === 0.5 ? 'Pushed in' : t < 1 ? `Twisted ${Math.round(twist * turn)}°` : 'Locked';

    const spread = ui.exploded.checked;
    for (const [mesh, base] of home) {
      const offset = spread ? EXPLODE[mesh.name] ?? [0, 0, 0] : [0, 0, 0];
      mesh.position.set(base.x + offset[0], base.y + offset[1], base.z + offset[2]);
    }
    for (const m of materials) m.clippingPlanes = ui.section.checked ? [clip] : [];
    render();
  }

  // Orbit camera around the wand.
  const target = new THREE.Vector3(0, -10, 250);
  const orbit = { yaw: 0.95, pitch: 0.32, distance: 900 };
  const reset = () => Object.assign(orbit, { yaw: 0.95, pitch: 0.32, distance: 900 });

  function render() {
    const { yaw, pitch, distance } = orbit;
    camera.position.set(
      target.x + distance * Math.cos(pitch) * Math.sin(yaw),
      target.y + distance * Math.sin(pitch),
      target.z + distance * Math.cos(pitch) * Math.cos(yaw),
    );
    camera.lookAt(target);
    renderer.render(scene, camera);
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
    orbit.distance = Math.max(80, Math.min(2500, orbit.distance * Math.exp(e.deltaY * 0.001)));
    render();
  }, { passive: false });
  canvas.addEventListener('dblclick', () => { reset(); render(); });

  ui.joint.addEventListener('input', update);
  ui.exploded.addEventListener('change', update);
  ui.section.addEventListener('change', update);
  new ResizeObserver(resize).observe(view);
  update();
  resize();
}

main();
