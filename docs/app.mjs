// Magic Wand demo: the visitor's mouse, touch or keys become the wand's rotation and buttons.
// The wand's own device code runs in a worker (sim/worker.js); the Mac side is simulated by the
// receiver, HUD and Agent Flow ports in sim/, and drawn on the light board.
import { createPipeline } from "./sim/pipeline.mjs";
import { MacScreen } from "./sim/mac.mjs";
import { LightBoard } from "./board.mjs";
import { createWandScene } from "./wand-scene.mjs";

const $ = (selector) => document.querySelector(selector);
const root = document.documentElement;
const demo = $("#demo");
const stage = $("#stage");
const stageMessage = $("#stage-message");
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const urls = Object.fromEntries(
  Object.entries(JSON.parse($("#asset-urls").textContent)).map(([key, value]) => [key, new URL(value, document.baseURI).href]),
);

const AIM_LIMIT = { yaw: 48, pitch: 32 };
const AIM_SPAN = 96; // Degrees across the stage's width.
const SLEW = 260; // Degrees per second: re-entering the stage sweeps rather than jumps.
const ARROW_SPEED = 32;
const ARROW_SLOW = 7;
const SCREEN_CENTRE_Y = 0.39; // Pointing here aims at the middle of the simulated screen.

const fetchJson = (url) => fetch(url).then((response) => {
  if (!response.ok) throw new Error(`Couldn't load ${new URL(url).pathname} (${response.status})`);
  return response.json();
});

function showMessage(text, error = false) {
  stageMessage.textContent = text;
  stageMessage.classList.toggle("error", error);
  stageMessage.hidden = !text;
}

async function main() {
  const [manifest, layout] = await Promise.all([fetchJson(urls.wand), fetchJson(urls.hud)]);
  const lights = Object.fromEntries(manifest.lights.map((light) => [light.mode, light]));
  const buttons = Object.fromEntries(manifest.buttons.map((button) => [button.id, button]));
  const keyToButton = Object.fromEntries(manifest.buttons.map((button) => [button.key.toLowerCase(), button.id]));
  const chord = manifest.chords[0];

  // ------------------------------------------------------------ screen, board and HUD view
  const mac = new MacScreen();
  const board = new LightBoard($("#board"), { mac, reducedMotion: reducedMotion.matches });
  const hud = $("#hud");
  const hudGrid = $("#hud-grid");
  const hudOutline = $("#hud-outline");
  const hudAction = $("#hud-action");
  $("#hud-title").textContent = layout.title;
  const cardElements = new Map();
  for (const row of layout.rows) {
    for (const cell of row) {
      const card = layout.cards.find((item) => item.cell === cell);
      const element = document.createElement("div");
      element.className = "hud-card";
      element.textContent = card.title;
      element.style.setProperty("--card", card.fill);
      element.style.setProperty("--card-border", card.border);
      element.style.setProperty("--card-text", card.foreground);
      hudGrid.append(element);
      cardElements.set(cell, element);
    }
  }
  let hudState = { open: false, cell: manifest.hud.startCell, pullX: 0, pullY: 0, pressed: false, adjusting: null, action: null };
  let lastActionAt = null;
  let actionTimer = 0;

  function drawHud() {
    hud.hidden = !hudState.open;
    if (!hudState.open) return;
    const card = cardElements.get(hudState.cell);
    for (const [cell, element] of cardElements) element.classList.toggle("selected", cell === hudState.cell);
    const hudBox = hud.getBoundingClientRect();
    const box = card.getBoundingClientRect();
    // Liquid progress: the outline leans and stretches toward the next card before it moves.
    const pullX = Math.max(-1, Math.min(1, hudState.pullX));
    const pullY = Math.max(-1, Math.min(1, hudState.pullY));
    const inset = Math.max(3, box.width * 0.035);
    const stretchX = Math.abs(pullX) * 0.14 * box.width;
    const stretchY = Math.abs(pullY) * 0.14 * box.height;
    const x = box.left - hudBox.left - inset + Math.min(0, pullX) * 0.14 * box.width + pullX * 0.06 * box.width;
    const y = box.top - hudBox.top - inset + Math.min(0, pullY) * 0.14 * box.height + pullY * 0.06 * box.height;
    hudOutline.style.width = `${box.width + inset * 2 + stretchX}px`;
    hudOutline.style.height = `${box.height + inset * 2 + stretchY}px`;
    hudOutline.style.transform = `translate(${x}px, ${y}px)`;
    hudOutline.classList.toggle("pressed", hudState.pressed && !hudState.adjusting);
    hudOutline.classList.toggle("adjusting", Boolean(hudState.adjusting));
    hudOutline.style.setProperty("--adjust", layout.cards.find((item) => item.cell === hudState.cell).fill);
    if (hudState.action && hudState.action.at !== lastActionAt) {
      lastActionAt = hudState.action.at;
      hudAction.textContent = hudState.action.text;
      hudAction.classList.add("visible");
      clearTimeout(actionTimer);
      actionTimer = setTimeout(() => hudAction.classList.remove("visible"), 1500);
      announce(hudState.action.text);
    }
  }

  // ------------------------------------------------------------ wand visual and light
  // The simulation starts at once; the drawn wand joins when Three.js has loaded.
  let wand = {
    resize() {}, setAim() {}, setPressed() {}, setLight() {},
    tipScreen: () => ({ x: stage.clientWidth * 0.58, y: stage.clientHeight * 0.78 }),
  };
  async function loadWand() {
    let next;
    try {
      next = await createWandScene($("#wand-canvas"));
    } catch {
      next = createFallbackWand();
    }
    wand = next;
    wand.resize();
    wand.setAim(aim.yaw, aim.pitch);
    wand.setLight(currentLight.display, currentLight.strength);
    refreshKeys();
    placeGlow();
  }

  function createFallbackWand() {
    $("#wand-canvas").hidden = true;
    const fallback = $("#wand-fallback");
    fallback.hidden = false;
    const rod = fallback.querySelector(".fallback-wand");
    let angle = -150;
    let length = 0.52;
    return {
      resize() {},
      setAim(yaw, pitch) {
        // Same quarter-scale motion as the 3D wand.
        angle = -150 + yaw * 0.275;
        length = 0.52 - pitch * 0.0015;
        rod.style.setProperty("--fallback-angle", `${angle}deg`);
        rod.style.setProperty("--fallback-length", `${length * 100}%`);
      },
      setPressed() {},
      setLight() {},
      tipScreen() {
        const width = stage.clientWidth;
        const height = stage.clientHeight;
        const radians = (angle * Math.PI) / 180;
        return { x: width * 0.92 + Math.cos(radians) * length * width, y: height * 1.18 + Math.sin(radians) * length * width };
      },
    };
  }

  let lightMode = "idle";
  let currentLight = { display: lights.idle.display, strength: 0 };
  function setLight(mode) {
    const light = lights[mode] || lights.idle;
    const strength = mode === "idle" ? 0 : mode === "disconnected" ? 0.35 : 1;
    currentLight = { display: light.display, strength };
    root.style.setProperty("--led-lit", light.display);
    root.style.setProperty("--led-strength", String(strength));
    wand.setLight(light.display, strength);
    if (mode !== lightMode) {
      lightMode = mode;
      updateReadout();
    }
  }

  function placeGlow() {
    const tip = wand.tipScreen();
    stage.style.setProperty("--tip-x", `${tip.x}px`);
    stage.style.setProperty("--tip-y", `${tip.y}px`);
  }

  // ------------------------------------------------------------ readout and announcements
  const announcer = $("#announcer");
  let deviceState = null;
  let lastAnnouncement = "";
  let announceTimer = 0;
  function announce(text) {
    clearTimeout(announceTimer);
    announceTimer = setTimeout(() => {
      if (text === lastAnnouncement) return;
      lastAnnouncement = text;
      announcer.textContent = text;
    }, 450);
  }

  function detailText() {
    const state = deviceState || {};
    switch (lightMode) {
      case "mouse":
        if (state.dragging) return "Dragging";
        if (state.tapPending) return "Clicking";
        if (state.gesture === "enable" || state.gesture === "clutch") return "Moving while held";
        return state.moveLatched ? "Following" : "";
      case "hud": {
        const card = layout.cards.find((item) => item.cell === hudState.cell);
        if (!card) return "";
        if (hudState.adjusting && hudState.action && hudState.action.kind === "wheel") return hudState.action.text;
        return hudState.pressed ? `Holding ${card.title}` : card.title;
      }
      case "scroll": return "Both directions";
      case "recording": return "Agent Flow";
      case "calibration": return "Keep still";
      default: return "";
    }
  }

  function updateReadout() {
    const name = (lights[lightMode] || lights.idle).name;
    const detail = detailText();
    $("#mode-name").textContent = name;
    $("#mode-detail").textContent = detail;
    announce(detail && lightMode !== "mouse" ? `${name}, ${detail}` : name);
  }

  // ------------------------------------------------------------ simulation session
  let session = null;

  function sessionTimers() {
    const timeouts = new Set();
    const intervals = new Set();
    return {
      now: () => performance.now() / 1000,
      setTimeout(fn, ms) {
        const id = setTimeout(() => { timeouts.delete(id); fn(); }, ms);
        timeouts.add(id);
        return id;
      },
      clearTimeout(id) { clearTimeout(id); timeouts.delete(id); },
      setInterval(fn, ms) { const id = setInterval(fn, ms); intervals.add(id); return id; },
      clearInterval(id) { clearInterval(id); intervals.delete(id); },
      clearAll() {
        timeouts.forEach((id) => clearTimeout(id));
        intervals.forEach((id) => clearInterval(id));
        timeouts.clear();
        intervals.clear();
      },
    };
  }

  function startSession() {
    const timers = sessionTimers();
    const worker = new Worker(urls.worker);
    let ready = false;
    let stopped = false;
    const pipeline = createPipeline({
      send: (code) => worker.postMessage({ type: "eval", code }),
      timers,
      manifest,
      layout,
      mac,
      onHud: (state) => {
        const settled = state.cell !== hudState.cell || state.open !== hudState.open;
        hudState = state;
        drawHud();
        updateReadout();
        if (settled && state.open) announce(`HUD, ${layout.cards.find((item) => item.cell === state.cell).title}`);
      },
      onRecording: (active) => { $("#recording-chip").hidden = !active; },
    });
    worker.onmessage = ({ data }) => {
      if (stopped) return; // A message already queued when Reset stopped this session.
      switch (data.type) {
        case "events":
          pipeline.handle(data.events);
          if (pipeline.receiver.lightMode !== lightMode) setLight(pipeline.receiver.lightMode);
          break;
        case "state":
          deviceState = data.state;
          updateReadout();
          break;
        case "ready":
          ready = true;
          pipeline.receiver.ready();
          demo.dataset.state = "ready";
          showMessage("");
          for (const pin of ["D1", "D2", "D30"]) if (pinPressed(pin)) worker.postMessage({ type: "pin", pin, value: 0 });
          postAim();
          break;
        case "fatal":
        case "device-error":
          demo.dataset.state = "error";
          showMessage(`The simulation stopped: ${String(data.message).replace(/\.$/, "")}. Reset starts it again.`, true);
          break;
        default:
          break;
      }
    };
    worker.onerror = (event) => {
      if (stopped) return;
      demo.dataset.state = "error";
      showMessage(`The simulation stopped: ${String(event.message || "worker error").replace(/\.$/, "")}. Reset starts it again.`, true);
    };
    worker.postMessage({ type: "init", urls: { shim: urls.shim, device: urls.device, bridge: urls.bridge } });
    return {
      get ready() { return ready; },
      sendPin(pin, pressed) { worker.postMessage({ type: "pin", pin, value: pressed ? 0 : 1 }); },
      sendAim(yaw, pitch) { worker.postMessage({ type: "aim", yaw, pitch }); },
      pause(paused) { worker.postMessage({ type: "pause", paused }); },
      stop() { stopped = true; worker.terminate(); timers.clearAll(); },
    };
  }

  // ------------------------------------------------------------ buttons
  const holders = { D1: new Set(), D2: new Set(), D30: new Set() };
  const pinFor = (id) => buttons[id].pin;
  const pinPressed = (pin) => holders[pin].size > 0;
  const keyElements = [...document.querySelectorAll(".grip .key")];

  function refreshKeys() {
    for (const element of keyElements) {
      const pressed = element.dataset.chord
        ? chord.buttons.every((id) => pinPressed(pinFor(id)))
        : pinPressed(pinFor(element.dataset.button));
      element.setAttribute("aria-pressed", String(pressed));
    }
    wand.setPressed(Object.fromEntries(manifest.buttons.map((button) => [button.id, pinPressed(button.pin)])));
  }

  function hold(id, who) {
    const pin = pinFor(id);
    const was = pinPressed(pin);
    holders[pin].add(who);
    if (!was && session) session.sendPin(pin, true);
    refreshKeys();
  }

  function release(id, who) {
    const pin = pinFor(id);
    if (!holders[pin].delete(who)) return;
    if (!pinPressed(pin) && session) session.sendPin(pin, false);
    refreshKeys();
  }

  function releaseWhere(predicate) {
    for (const button of manifest.buttons) {
      for (const who of [...holders[button.pin]]) if (predicate(who)) release(button.id, who);
    }
  }

  let chordTimer = 0;
  function holdChord(who) {
    const [first, second] = chord.buttons;
    hold(first, who);
    clearTimeout(chordTimer);
    chordTimer = setTimeout(() => { if (holders[pinFor(first)].has(who)) hold(second, who); }, 30);
  }
  function releaseChord(who) {
    clearTimeout(chordTimer);
    for (const id of chord.buttons) release(id, who);
  }

  // ------------------------------------------------------------ aim
  const aim = { yaw: 0, pitch: 0 };
  const target = { yaw: 0, pitch: 0 };
  const arrows = new Set();
  let slow = false;
  let frame = 0;
  let lastFrame = 0;
  const clampAim = () => {
    target.yaw = Math.max(-AIM_LIMIT.yaw, Math.min(AIM_LIMIT.yaw, target.yaw));
    target.pitch = Math.max(-AIM_LIMIT.pitch, Math.min(AIM_LIMIT.pitch, target.pitch));
  };
  const degreesPerPixel = () => AIM_SPAN / Math.max(1, stage.clientWidth);

  function postAim() {
    wand.setAim(aim.yaw, aim.pitch);
    placeGlow();
    if (session) session.sendAim(aim.yaw, aim.pitch);
  }

  function step(time) {
    frame = 0;
    const dt = Math.min(0.05, lastFrame ? (time - lastFrame) / 1000 : 0.016);
    lastFrame = time;
    if (arrows.size) {
      const speed = slow ? ARROW_SLOW : ARROW_SPEED;
      if (arrows.has("ArrowLeft")) target.yaw -= speed * dt;
      if (arrows.has("ArrowRight")) target.yaw += speed * dt;
      if (arrows.has("ArrowUp")) target.pitch -= speed * dt;
      if (arrows.has("ArrowDown")) target.pitch += speed * dt;
      clampAim();
    }
    const dy = target.yaw - aim.yaw;
    const dp = target.pitch - aim.pitch;
    const distance = Math.hypot(dy, dp);
    if (distance > 0.0005) {
      const move = Math.min(1, (SLEW * dt) / distance);
      aim.yaw += dy * move;
      aim.pitch += dp * move;
      postAim();
    }
    if (arrows.size || Math.hypot(target.yaw - aim.yaw, target.pitch - aim.pitch) > 0.0005) requestStep();
    else lastFrame = 0;
  }
  function requestStep() { if (!frame) frame = requestAnimationFrame(step); }

  function aimAtPoint(clientX, clientY) {
    const rect = stage.getBoundingClientRect();
    const perPixel = AIM_SPAN / Math.max(1, rect.width);
    target.yaw = (clientX - rect.left - rect.width / 2) * perPixel;
    target.pitch = (clientY - rect.top - rect.height * SCREEN_CENTRE_Y) * perPixel;
    clampAim();
    requestStep();
  }
  function turnBy(dx, dy) {
    target.yaw += dx * degreesPerPixel();
    target.pitch += dy * degreesPerPixel();
    clampAim();
    requestStep();
  }

  // Stage: the mouse is the wand (left = Bottom, right = Middle, wheel button = Top); touch drags turn it.
  const mouseButtons = [["bottom", 1], ["middle", 2], ["top", 4]];
  const touches = new Map();
  function syncMouseButtons(mask) {
    for (const [id, bit] of mouseButtons) {
      const who = `mouse-${id}`;
      if (mask & bit) { if (!holders[pinFor(id)].has(who)) hold(id, who); } else release(id, who);
    }
  }
  stage.addEventListener("pointerdown", (event) => {
    stage.focus({ preventScroll: true });
    if (event.pointerType === "touch") {
      touches.set(event.pointerId, { x: event.clientX, y: event.clientY });
      stage.setPointerCapture(event.pointerId);
      return;
    }
    event.preventDefault();
    stage.setPointerCapture(event.pointerId);
    aimAtPoint(event.clientX, event.clientY);
    syncMouseButtons(event.buttons);
  });
  stage.addEventListener("pointermove", (event) => {
    if (event.pointerType === "touch") {
      const last = touches.get(event.pointerId);
      if (!last) return;
      turnBy((event.clientX - last.x) / touches.size, (event.clientY - last.y) / touches.size);
      touches.set(event.pointerId, { x: event.clientX, y: event.clientY });
      return;
    }
    aimAtPoint(event.clientX, event.clientY);
    if (stage.hasPointerCapture(event.pointerId)) syncMouseButtons(event.buttons);
  });
  const endStagePointer = (event) => {
    if (event.pointerType === "touch") { touches.delete(event.pointerId); return; }
    syncMouseButtons(event.type === "pointerup" ? event.buttons : 0);
  };
  stage.addEventListener("pointerup", endStagePointer);
  stage.addEventListener("pointercancel", endStagePointer);
  stage.addEventListener("lostpointercapture", (event) => { if (event.pointerType !== "touch") syncMouseButtons(0); });
  stage.addEventListener("contextmenu", (event) => event.preventDefault());
  stage.addEventListener("auxclick", (event) => event.preventDefault());
  stage.addEventListener("mousedown", (event) => { if (event.button === 1) event.preventDefault(); }); // No autoscroll.

  // Grip keys: press and hold; dragging while holding turns the wand.
  for (const element of keyElements) {
    const press = (who) => (element.dataset.chord ? holdChord(who) : hold(element.dataset.button, who));
    const lift = (who) => (element.dataset.chord ? releaseChord(who) : release(element.dataset.button, who));
    const drags = new Map();
    element.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      event.preventDefault();
      element.focus({ preventScroll: true });
      element.setPointerCapture(event.pointerId);
      drags.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (event.pointerType === "touch" && navigator.vibrate) navigator.vibrate(8);
      press(`grip-${event.pointerId}`);
    });
    element.addEventListener("pointermove", (event) => {
      const last = drags.get(event.pointerId);
      if (!last) return;
      turnBy(event.clientX - last.x, event.clientY - last.y);
      drags.set(event.pointerId, { x: event.clientX, y: event.clientY });
    });
    const end = (event) => {
      if (!drags.delete(event.pointerId)) return;
      lift(`grip-${event.pointerId}`);
    };
    element.addEventListener("pointerup", end);
    element.addEventListener("pointercancel", end);
    element.addEventListener("lostpointercapture", end);
    element.addEventListener("contextmenu", (event) => event.preventDefault());
    element.addEventListener("click", (event) => event.preventDefault());
    element.addEventListener("keydown", (event) => {
      if (event.key !== " " && event.key !== "Enter") return;
      event.preventDefault();
      event.stopPropagation();
      if (!event.repeat) press("grip-keyboard");
    });
    element.addEventListener("keyup", (event) => {
      if (event.key !== " " && event.key !== "Enter") return;
      event.preventDefault();
      lift("grip-keyboard");
    });
  }

  // Letter keys and arrows work while focus is in the demo.
  document.addEventListener("keydown", (event) => {
    if (!demo.contains(document.activeElement) || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === "Shift") { slow = true; return; }
    const id = keyToButton[event.key.toLowerCase()];
    if (id) {
      event.preventDefault();
      if (!event.repeat) hold(id, `key-${event.code}`);
      return;
    }
    if (event.key.startsWith("Arrow")) {
      event.preventDefault();
      arrows.add(event.key);
      requestStep();
    }
  });
  document.addEventListener("keyup", (event) => {
    if (event.key === "Shift") { slow = false; return; }
    const id = keyToButton[event.key.toLowerCase()];
    if (id) release(id, `key-${event.code}`);
    arrows.delete(event.key);
  });

  // Never leave a button stuck down when the page loses focus or hides.
  const releaseAll = () => {
    releaseWhere(() => true);
    arrows.clear();
    touches.clear();
    slow = false;
  };
  window.addEventListener("blur", releaseAll);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) releaseAll();
    if (session) session.pause(document.hidden);
  });

  $("#reset").addEventListener("click", () => {
    releaseAll();
    if (session) session.stop();
    aim.yaw = aim.pitch = target.yaw = target.pitch = 0;
    hudState = { ...hudState, open: false, action: null };
    drawHud();
    $("#recording-chip").hidden = true;
    mac.reset();
    setLight("idle");
    deviceState = null;
    demo.dataset.state = "loading";
    showMessage("Loading the wand…");
    session = startSession();
    postAim();
    stage.focus({ preventScroll: true });
  });

  new ResizeObserver(() => {
    wand.resize();
    board.resize();
    drawHud();
    postAim();
  }).observe(stage);
  reducedMotion.addEventListener("change", () => { board.reducedMotion = reducedMotion.matches; });

  setLight("idle");
  session = startSession();
  postAim();
  loadWand();
}

main().catch((error) => {
  demo.dataset.state = "error";
  showMessage(`The demo couldn’t start: ${error.message}`, true);
});
