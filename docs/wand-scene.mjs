// The 3D wand: a schematic carbon-fibre shaft with three grip buttons and a Puck.js at the tip.
// Proportions follow the real wand loosely (about 50 cm, Puck at the tip); details are illustrative.
// Three.js loads on demand; buildRig() is pure so tests can check the framing without WebGL.

export const RIG = {
  length: 0.5,
  pivot: [0.15, -0.24, -0.5], // The hand, in front of and below the camera.
  aimAt: [0.02, -0.08, -1.4], // At rest the tip sits just under the simulated screen.
  fov: 30, // Widened on narrow screens so the whole aim range stays in view.
  // The drawn wand turns a quarter as far as the simulated sensor, so the tip stays below the HUD
  // instead of sweeping across the screen. The device code still receives the full rotation.
  visualScale: 0.25,
  buttons: { bottom: 0.035, middle: 0.07, top: 0.105 }, // Top sits nearest the shaft.
};

/** Build the wand meshes. Returns handles for aiming, buttons and the light. */
export function buildRig(THREE, { twill = null } = {}) {
  const group = new THREE.Group();
  group.position.set(...RIG.pivot);
  const along = (geometry) => geometry.rotateX(Math.PI / 2); // Cylinders run along +Z, toward the tip.

  const gripMaterial = new THREE.MeshStandardMaterial({ color: 0x17141f, roughness: 0.82, metalness: 0 });
  const grip = new THREE.Mesh(along(new THREE.CylinderGeometry(0.0135, 0.0145, 0.15, 40)), gripMaterial);
  grip.position.z = 0.075;
  group.add(grip);
  const endCap = new THREE.Mesh(new THREE.SphereGeometry(0.0145, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2).rotateX(-Math.PI / 2), gripMaterial);
  group.add(endCap);

  const buttons = {};
  for (const [id, z] of Object.entries(RIG.buttons)) {
    const material = new THREE.MeshStandardMaterial({ color: 0x3a3450, roughness: 0.5, metalness: 0.05, emissive: 0x000000 });
    const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.0048, 0.0052, 0.004, 28), material);
    cap.position.set(0, 0.0148, z);
    group.add(cap);
    buttons[id] = { mesh: cap, material, restY: 0.0148 };
  }

  const shaftMaterial = new THREE.MeshPhysicalMaterial({
    color: twill ? 0xffffff : 0x2c2a34,
    map: twill,
    roughness: 0.32,
    metalness: 0.15,
    clearcoat: 1,
    clearcoatRoughness: 0.22,
  });
  const shaftLength = 0.355;
  const shaft = new THREE.Mesh(along(new THREE.CylinderGeometry(0.0055, 0.0062, shaftLength, 28, 1, true)), shaftMaterial);
  shaft.position.z = 0.15 + shaftLength / 2;
  group.add(shaft);

  // Puck.js lies flat at the tip; its gyro axes map yaw and pitch to the pointer.
  const profile = [
    [0, -0.0056], [0.0158, -0.0056], [0.0178, -0.0042], [0.0182, 0], [0.0178, 0.0042], [0.0158, 0.0058], [0, 0.0062],
  ].map(([x, y]) => new THREE.Vector2(x, y));
  const puckMaterial = new THREE.MeshStandardMaterial({ color: 0xece8f4, roughness: 0.78, metalness: 0, emissive: 0x000000 });
  const puck = new THREE.Mesh(new THREE.LatheGeometry(profile, 48), puckMaterial);
  puck.position.z = RIG.length + 0.012;
  group.add(puck);

  const ledMaterial = new THREE.MeshBasicMaterial({ color: 0x2a2440, toneMapped: false });
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.0034, 16, 12), ledMaterial);
  led.position.set(0, 0.0046, RIG.length + 0.012);
  group.add(led);

  const light = new THREE.PointLight(0xffffff, 0, 0.35, 2);
  light.position.set(0, 0.012, RIG.length + 0.012);
  group.add(light);

  const pivot = new THREE.Vector3(...RIG.pivot);
  const base = new THREE.Vector3(...RIG.aimAt).sub(pivot).normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const target = new THREE.Vector3();
  const tip = new THREE.Vector3();

  return {
    group,
    puck,
    led,
    ledMaterial,
    puckMaterial,
    light,
    buttons,
    /** +yaw turns right and +pitch turns down, in degrees. */
    setAim(yaw, pitch) {
      yaw *= RIG.visualScale;
      pitch *= RIG.visualScale;
      const direction = base.clone();
      const right = new THREE.Vector3().crossVectors(direction, up).normalize();
      direction.applyAxisAngle(right, (-pitch * Math.PI) / 180);
      direction.applyAxisAngle(up, (-yaw * Math.PI) / 180);
      target.copy(pivot).add(direction);
      group.lookAt(target);
    },
    setPressed(pressed) {
      for (const [id, button] of Object.entries(buttons)) {
        button.mesh.position.y = pressed[id] ? button.restY - 0.0016 : button.restY;
      }
    },
    tipWorld() {
      group.updateMatrixWorld(true);
      return led.getWorldPosition(tip);
    },
  };
}

export const fieldOfView = (aspect) => (aspect < 1.3 ? RIG.fov * 1.25 : RIG.fov);

export function makeCamera(THREE, aspect) {
  const camera = new THREE.PerspectiveCamera(fieldOfView(aspect), aspect, 0.02, 10);
  camera.position.set(0, 0, 0);
  camera.lookAt(0, 0, -1);
  return camera;
}

/** A dim, faintly violet room for reflections on the clear-coated shaft. */
function environment(THREE) {
  const scene = new THREE.Scene();
  const geometry = new THREE.SphereGeometry(5, 32, 16);
  const colors = [];
  const low = new THREE.Color(0x0b0a10);
  const high = new THREE.Color(0x56526a);
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i++) {
    const t = (position.getY(i) / 5 + 1) / 2;
    const color = low.clone().lerp(high, t * t);
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  scene.add(new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ side: THREE.BackSide, vertexColors: true })));
  const softbox = (width, height, x, y, z, strength) => {
    const material = new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(strength), side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
    mesh.position.set(x, y, z);
    mesh.lookAt(0, 0, 0);
    scene.add(mesh);
  };
  softbox(3, 1.2, -2, 3, 1.5, 3);
  softbox(1.4, 3, 3.5, 0.5, -1, 1.6);
  return scene;
}

function twillTexture(THREE) {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 32;
  const c = canvas.getContext("2d");
  c.fillStyle = "#2a2832";
  c.fillRect(0, 0, 32, 32);
  c.fillStyle = "#3d3a47";
  for (let row = 0; row < 4; row++) {
    for (let column = 0; column < 4; column++) {
      if ((column + row) % 4 < 2) c.fillRect(column * 8, row * 8, 8, 8);
    }
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(3, 56);
  texture.magFilter = THREE.LinearFilter;
  return texture;
}

/**
 * Create the renderer. Throws when WebGL is unavailable; the caller shows the flat fallback.
 * Renders only when something changes.
 */
export async function createWandScene(canvas) {
  const THREE = await import("three");
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(environment(THREE), 0.04).texture;
  pmrem.dispose();
  scene.add(new THREE.HemisphereLight(0xd8d4ea, 0x121019, 0.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.5);
  key.position.set(-0.6, 1, 0.5);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xb3acd6, 1.1);
  rim.position.set(0.7, 0.25, -1);
  scene.add(rim);

  const rig = buildRig(THREE, { twill: twillTexture(THREE) });
  scene.add(rig.group);
  const camera = makeCamera(THREE, 1);
  const lit = new THREE.Color();
  const dark = new THREE.Color(0x2a2440);
  let frame = 0;
  let width = 0;
  let height = 0;

  const glowTexture = (() => {
    const glow = document.createElement("canvas");
    glow.width = glow.height = 128;
    const c = glow.getContext("2d");
    const gradient = c.createRadialGradient(64, 64, 0, 64, 64, 64);
    gradient.addColorStop(0, "rgba(255,255,255,1)");
    gradient.addColorStop(0.25, "rgba(255,255,255,0.45)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    c.fillStyle = gradient;
    c.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(glow);
  })();
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture, color: 0xffffff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }));
  sprite.scale.set(0.07, 0.07, 1);
  sprite.position.copy(rig.led.position);
  rig.group.add(sprite);

  const render = () => {
    frame = 0;
    renderer.render(scene, camera);
  };
  const request = () => { if (!frame) frame = requestAnimationFrame(render); };

  return {
    resize() {
      const rect = canvas.getBoundingClientRect();
      if (rect.width === width && rect.height === height) return;
      width = rect.width;
      height = rect.height;
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(1, height);
      camera.fov = fieldOfView(camera.aspect);
      camera.updateProjectionMatrix();
      request();
    },
    setAim(yaw, pitch) { rig.setAim(yaw, pitch); request(); },
    setPressed(pressed) { rig.setPressed(pressed); request(); },
    /** color: CSS hex; strength 0..1. */
    setLight(color, strength) {
      lit.set(color);
      rig.ledMaterial.color.copy(strength > 0 ? lit : dark);
      rig.puckMaterial.emissive.copy(lit).multiplyScalar(0.22 * strength);
      rig.light.color.copy(lit);
      rig.light.intensity = 0.012 * strength;
      sprite.material.color.copy(lit);
      sprite.material.opacity = 0.9 * strength;
      request();
    },
    /** Tip position in canvas CSS pixels, for the page glow. */
    tipScreen() {
      const point = rig.tipWorld().clone().project(camera);
      return { x: ((point.x + 1) / 2) * width, y: ((1 - point.y) / 2) * height };
    },
    dispose() {
      if (frame) cancelAnimationFrame(frame);
      renderer.dispose();
    },
  };
}
