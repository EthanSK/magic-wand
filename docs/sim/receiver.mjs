// The Mac side of the wand, for the website demo.
//
// A JavaScript port of Wand Receiver's message handling (receiver/Sources/main.swift): it turns
// the Puck's UART lines into pointer, click and wheel events, runs the HUD session timing, and
// forwards speech presses. Here the "native events" go to the simulated screen instead of macOS.

import { PointerRouter, DwellClick } from "./pointer.mjs";
const finite = (value) =>
  Number.isFinite(value) && Math.abs(value) <= 7_200_000;

function parseTriple(payload) {
  const fields = payload.split(",");
  if (fields.length !== 3) return null;
  const x = Number(fields[1]);
  const y = Number(fields[2]);
  return finite(x) && finite(y) ? { phase: fields[0], x, y } : null;
}

/** Agent Flow's Primary recording control: the first press starts, a later press stops on release. */
export class AgentFlowModel {
  constructor({ onRecordingChange = () => {} } = {}) {
    this.recording = false;
    this.startedOnDown = false;
    this.armed = false;
    this.onRecordingChange = onRecordingChange;
  }

  primary(down) {
    if (down) {
      if (!this.recording) {
        this.recording = true;
        this.startedOnDown = true;
        this.onRecordingChange(true);
      } else {
        this.armed = true;
      }
      return;
    }
    if (this.startedOnDown) {
      this.startedOnDown = false;
      return;
    }
    if (this.armed) {
      this.armed = false;
      this.recording = false;
      this.onRecordingChange(false);
    }
  }

  cancel() {
    this.startedOnDown = false;
    this.armed = false;
  }
}

/** Persistent HUD commands with the receiver's id/sequence rules. */
export class ControlTransport {
  constructor({ hud, agentFlow, makeId }) {
    this.hud = hud;
    this.agentFlow = agentFlow;
    this.makeId = makeId || (() => Math.random().toString(36).slice(2, 12));
    this.persistentId = this.makeId();
    this.sequence = 0;
    this.speechPressed = false;
  }

  persistent(phase, x = 0, y = 0) {
    if (["open", "navigate", "press", "dismiss"].includes(phase)) {
      this.persistentId = this.makeId();
      this.sequence = 0;
    }
    this.sequence += 1;
    this.hud.handle({ phase, id: this.persistentId, seq: this.sequence, x, y });
  }

  speech(down) {
    if (down === this.speechPressed) return true;
    this.agentFlow.primary(down);
    this.speechPressed = down;
    return true;
  }

  cancel() {
    this.persistent("dismiss");
    if (this.speechPressed) this.agentFlow.cancel();
    this.speechPressed = false;
  }
}

export class WandReceiverModel {
  /**
   * @param {object} options
   * @param {object} options.tuning wand.json tuning
   * @param {object} options.timers {now, setTimeout, clearTimeout, setInterval, clearInterval}
   * @param {ControlTransport} options.controls
   * @param {object} options.mac {location(), mouse(type, point, clickCount), scroll(dx, dy)}
   * @param {(command: string) => void} options.queue send one REPL command to the Puck
   */
  constructor({ tuning, timers, controls, mac, queue }) {
    this.tuning = tuning;
    this.timers = timers;
    this.controls = controls;
    this.mac = mac;
    this.queue = queue;
    this.contextActive = false;
    this.buttons = 0;
    this.lastClickTime = -Infinity;
    this.lastClickPoint = { x: -1e9, y: -1e9 };
    this.clickCount = 0;
    this.pointerInHUD = false;
    this.middleOperating = false;
    this.hudSession = false;
    this.hudEntryPress = false;
    this.hudEntryPressStarted = 0;
    this.pointerRouter = new PointerRouter({lowDelay:tuning.lowMotionDelayMs/1000});
    this.dwell = new DwellClick();
    this.lowDelayTimer = null;
    this.dwellTimer = null;
    this.circleLight = false;
    this.bottomHeld = false;
    this.circleTimer = null;
    this.navX = 0;
    this.navY = 0;
    this.navOriginX = 0;
    this.navOriginY = 0;
    this.operationOriginX = 0;
    this.operationOriginY = 0;
    this.middleX = 0;
    this.middleY = 0;
    this.middleHold = null;
    this.middleTap = null;
    this.hudActive = false;
    this.hudLastUpdate = -Infinity;
    this.hudWatchdog = null;
    this.navigationOpenedHUD = false;
    this.scrollActive = false;
    this.scrollX = 0;
    this.scrollY = 0;
    this.scrollFractionX = 0;
    this.scrollFractionY = 0;
    this.scrollUpdated = -Infinity;
    this.scrollWatchdog = null;
    this.lightMode = "unknown";
    this.recording = false;
  }

  get doubleClickInterval() {
    return Math.max(0.25, Math.min(0.3, this.tuning.macDoubleClickSeconds));
  }

  /** The receiver's handshake once the device code and bridge are ready. */
  ready() {
    this.queue(
      "E.setFlags({pretokenise:1});global.wandDoubleClickSeconds=" +
        Math.min(0.3, this.tuning.macDoubleClickSeconds) +
        ";",
    );
    this.syncRecordingLight();
    if (this.contextActive) {
      this.hudSession = true;
      this.resumeHUDNavigation();
    }
    this.queue(
      "global.WAND_UPDATING=false;setHUDOpen(" +
        this.contextActive +
        ");updateLights();",
    );
  }

  /** Agentic Mouse reports whether it owns a wand HUD (the private context socket). */
  setContext(active) {
    if (active === this.contextActive) return;
    this.contextActive = active;
    if (!active && this.hudSession) {
      this.hudSession = false;
      this.hudEntryPress = false;
      this.hudActive = false;
      this.navX = 0;
      this.navY = 0;
      this.stopHUDWatchdog();
      this.clearTimer("middleTap");
      this.clearTimer("middleHold");
      this.pointerInHUD = false;
      this.middleOperating = false;
    }
    if (active && !this.hudSession) {
      this.hudSession = true;
      this.navX = 0;
      this.navY = 0;
      this.resumeHUDNavigation();
    }
    this.queue("if(typeof setHUDOpen==='function')setHUDOpen(" + active + ");");
  }

  setRecording(active) {
    this.dwell.reset();
    this.scheduleDwell();
    this.recording = active;
    this.syncRecordingLight();
  }

  syncRecordingLight() {
    this.queue("setWandRecording(" + this.recording + ");");
  }

  handleLine(line) {
    const at = (marker) => {
      const index = line.indexOf(marker);
      return index < 0 ? null : line.slice(index + marker.length);
    };
    const light = at("WAND_LIGHT_STATE ");
    if (light !== null) {
      const mode = light.split(/\s/)[0];
      if (
        [
          "update",
          "calibration",
          "disconnected",
          "scroll",
          "mouse",
          "hud",
          "recording",
          "idle",
        ].includes(mode)
      )
        this.lightMode = mode;
    }
    if (line.endsWith("@POINTER_MODE")) this.enterPointerMode();
    let payload;
    if (
      (payload = at("@FOLLOW ")) !== null &&
      ["0", "1"].includes(payload.trim())
    ) {
      this.dwell.follow(payload.trim() === "1");
      this.scheduleDwell();
    }
    if (
      (payload = at("@BOTTOM ")) !== null &&
      ["0", "1"].includes(payload.trim())
    ) {
      this.bottomHeld = payload.trim() === "1";
      this.dwell.reset();
      this.scheduleDwell();
      this.performPointer(this.pointerRouter.bottom(this.bottomHeld));
    }
    if ((payload = at("@IMU ")) !== null) {
      const fields = payload.split(",");
      if (fields.length === 6 && ["0", "1"].includes(fields[5])) {
        this.dwell.intent(fields[5] === "1", this.timers.now());
        this.scheduleDwell();
      }
    }
    if ((payload = at("@MIDDLE ")) !== null) {
      this.cancelCircleScroll();
      this.handleMiddle(payload);
    }
    if ((payload = at("@NAV ")) !== null) this.handleNavigation(payload);
    if ((payload = at("@SCROLL ")) !== null) this.handleScroll(payload);
    if ((payload = at("@MOVE ")) !== null) this.handleMove(payload);
    if ((payload = at("@STT ")) !== null) {
      this.cancelCircleScroll();
      const value = payload.trim();
      if (value === "0" || value === "1") this.controls.speech(value === "1");
    }
    if ((payload = at("@WAND ")) !== null) {
      const [x, y, b] = payload.split(",").map(Number);
      this.handleFrame(x, y, b);
    }
  }

  clearTimer(name) {
    if (this[name] !== null) this.timers.clearTimeout(this[name]);
    this[name] = null;
  }

  // MIDDLE latches the HUD, then operates the selected card.
  handleMove(payload) {
    if (this.scrollActive) return;
    const parsed = parseTriple(payload);
    if (!parsed) return;
    this.middleX = parsed.x / 1000;
    this.middleY = parsed.y / 1000;
    switch (parsed.phase) {
      case "B":
        if (this.middleTap !== null) {
          this.clearTimer("middleTap");
          this.clearTimer("middleHold");
          this.pointerInHUD = false;
          this.middleOperating = false;
          this.stopHUDWatchdog();
          this.releaseButtons();
          this.controls.persistent("dismiss");
          this.hudSession = false;
          this.hudEntryPress = false;
          this.hudActive = false;
          this.queue("setHUDOpen(false);");
          return;
        }
        if (!(this.contextActive || this.hudSession)) return;
        this.pointerInHUD = true;
        this.middleOperating = false;
        this.middleHold = this.timers.setTimeout(() => {
          this.middleHold = null;
          if (!this.pointerInHUD || !(this.contextActive || this.hudSession))
            return;
          this.middleOperating = true;
          this.controls.persistent("press");
          this.controls.persistent("motion", this.middleX, this.middleY);
        }, this.tuning.receiverHoldMs);
        this.startHUDWatchdog();
        break;
      case "U":
        if (!this.pointerInHUD) return;
        this.hudLastUpdate = this.timers.now();
        if (this.middleOperating)
          this.controls.persistent("motion", this.middleX, this.middleY);
        break;
      case "E":
        if (!this.pointerInHUD) return;
        this.pointerInHUD = false;
        this.clearTimer("middleHold");
        this.stopHUDWatchdog();
        if (this.middleOperating) {
          this.controls.persistent("motion", this.middleX, this.middleY);
          this.controls.persistent("release");
          this.resumeHUDNavigation();
        } else {
          this.middleTap = this.timers.setTimeout(() => {
            this.middleTap = null;
            if (!this.contextActive) return;
            this.controls.persistent("press");
            this.controls.persistent("release");
            this.resumeHUDNavigation();
          }, this.doubleClickInterval * 1000);
        }
        this.middleOperating = false;
        break;
      default:
        break;
    }
  }

  enterPointerMode() {
    this.hudSession = false;
    this.hudEntryPress = false;
    this.hudActive = false;
    this.pointerInHUD = false;
    this.middleOperating = false;
    this.clearTimer("middleTap");
    this.clearTimer("middleHold");
    this.stopHUDWatchdog();
    this.controls.persistent("dismiss");
  }

  handleMiddle(payload) {
    if (this.scrollActive) return;
    switch (payload.trim()) {
      case "1":
        if (!this.hudSession && !this.contextActive) {
          this.hudSession = true;
          this.hudEntryPress = true;
          this.hudEntryPressStarted = this.timers.now();
          this.navigationOpenedHUD = true;
          this.navX = 0;
          this.navY = 0;
          this.controls.persistent("open");
          this.resumeHUDNavigation();
          this.queue("setHUDOpen(true);");
          return;
        }
        this.hudSession = true;
        this.hudEntryPress = false;
        if (this.hudActive) {
          this.controls.persistent("park");
          this.hudActive = false;
          this.stopHUDWatchdog();
        }
        this.operationOriginX = this.navX;
        this.operationOriginY = this.navY;
        this.handleMove("B,0,0");
        break;
      case "0":
        if (this.hudEntryPress) {
          this.hudEntryPress = false;
          this.navigationOpenedHUD = false;
          if (
            this.timers.now() - this.hudEntryPressStarted >=
            (this.tuning.holdMs - this.tuning.middleReportDelayMs) / 1000
          ) {
            this.controls.persistent("park");
            this.hudActive = false;
            this.stopHUDWatchdog();
            this.controls.persistent("press");
            this.controls.persistent("release");
            this.resumeHUDNavigation();
          }
          return;
        }
        this.handleMove(
          "E," +
            (this.navX - this.operationOriginX) * 1000 +
            "," +
            (this.navY - this.operationOriginY) * 1000,
        );
        break;
      default:
        break;
    }
  }

  handleNavigation(payload) {
    const fields = payload.split(",");
    if (fields.length !== 2) return;
    const x = Number(fields[0]);
    const y = Number(fields[1]);
    if (!finite(x) || !finite(y)) return;
    this.navX = x / 1000;
    this.navY = y / 1000;
    if (this.scrollActive || !this.hudSession) return;
    if (this.pointerInHUD) {
      this.handleMove(
        "U," +
          (this.navX - this.operationOriginX) * 1000 +
          "," +
          (this.navY - this.operationOriginY) * 1000,
      );
    } else if (this.hudActive) {
      this.hudLastUpdate = this.timers.now();
      this.controls.persistent(
        "motion",
        this.navX - this.navOriginX,
        this.navY - this.navOriginY,
      );
    }
  }

  resumeHUDNavigation() {
    if (!this.hudSession || this.scrollActive) return;
    this.navOriginX = this.navX;
    this.navOriginY = this.navY;
    this.hudActive = true;
    this.controls.persistent("navigate");
    this.startHUDWatchdog();
  }

  startHUDWatchdog() {
    this.hudLastUpdate = this.timers.now();
    this.stopHUDWatchdog();
    this.hudWatchdog = this.timers.setInterval(() => {
      if (this.timers.now() - this.hudLastUpdate > 0.8) {
        this.clearTimer("middleHold");
        this.clearTimer("middleTap");
        this.controls.persistent("dismiss");
        this.hudActive = false;
        this.pointerInHUD = false;
        this.middleOperating = false;
        this.stopHUDWatchdog();
      }
    }, 250);
  }

  stopHUDWatchdog() {
    if (this.hudWatchdog !== null) this.timers.clearInterval(this.hudWatchdog);
    this.hudWatchdog = null;
  }

  // Ordinary wheel events, in line units like Agentic Mouse, keeping fractional lines.
  handleScroll(payload) {
    const parsed = parseTriple(payload);
    if (!parsed) return;
    const { phase, x, y } = parsed;
    if (phase === "B") {
      this.cancelCircleScroll();
      this.finishScroll();
      this.hudEntryPress = false;
      this.clearTimer("middleTap");
      this.clearTimer("middleHold");
      if (this.hudActive) {
        this.controls.persistent("park");
        if (this.navigationOpenedHUD) {
          this.controls.persistent("dismiss");
          this.hudSession = false;
          this.queue("setHUDOpen(false);");
        }
      } else if (this.middleOperating) {
        this.controls.persistent("release");
      }
      this.hudActive = false;
      this.pointerInHUD = false;
      this.middleOperating = false;
      this.navigationOpenedHUD = false;
      this.stopHUDWatchdog();
      this.releaseButtons();
      this.scrollActive = true;
      this.scrollX = x / 1000;
      this.scrollY = y / 1000;
      this.scrollFractionX = 0;
      this.scrollFractionY = 0;
      this.scrollUpdated = this.timers.now();
      this.scrollWatchdog = this.timers.setInterval(() => {
        if (this.timers.now() - this.scrollUpdated > 0.8) this.finishScroll();
      }, 250);
      return;
    }
    if (phase !== "U" && phase !== "E") return;
    if (!this.scrollActive) return;
    this.scrollUpdated = this.timers.now();
    const gain = this.tuning.hostScrollGain;
    this.scrollFractionX += (x / 1000 - this.scrollX) * gain;
    this.scrollFractionY += (y / 1000 - this.scrollY) * gain;
    this.scrollX = x / 1000;
    this.scrollY = y / 1000;
    const dx = Math.max(
      -4096,
      Math.min(4096, Math.trunc(this.scrollFractionX)),
    );
    const dy = Math.max(
      -4096,
      Math.min(4096, Math.trunc(this.scrollFractionY)),
    );
    this.scrollFractionX -= dx;
    this.scrollFractionY -= dy;
    // One wheel event per axis: native views can drop the smaller axis of a mixed event.
    if (dx !== 0) this.mac.scroll(dx, 0);
    if (dy !== 0) this.mac.scroll(0, dy);
    if (phase === "E") this.finishScroll();
  }

  finishScroll() {
    const wasActive = this.scrollActive;
    this.scrollActive = false;
    if (this.scrollWatchdog !== null)
      this.timers.clearInterval(this.scrollWatchdog);
    this.scrollWatchdog = null;
    if (wasActive) this.resumeHUDNavigation();
  }

  /** One mouse report: buttons first, then relative movement from the current location. */
  handleFrame(x, y, b) {
    if (
      ![x, y, b].every(Number.isInteger) ||
      Math.abs(x) > 127 ||
      Math.abs(y) > 127 ||
      b < 0 ||
      b > 3
    )
      return;
    if (this.scrollActive) return;
    const routed = this.pointerRouter.frame(
      x,
      y,
      b,
      this.hudSession,
      this.timers.now(),
    );
    this.dwell.move(
      x,
      y,
      this.timers.now(),
      !this.bottomHeld && b === 0 && !this.hudSession && !this.scrollActive,
    );
    this.scheduleDwell();
    this.transition(routed.buttons, this.mac.location());
    this.performPointer(routed.actions);
  }
  performPointer(actions) {
    for (const a of actions) {
      if (a.type === "move") {
        const p = this.mac.location();
        this.mac.mouse(
          this.buttons & 1 ? "drag" : "move",
          { x: p.x + a.dx, y: p.y + a.dy },
          this.clickCount,
        );
      } else if (a.type === "scroll") this.mac.scroll(0, -a.lines);
      else this.setCircleLight(a.on);
    }
    this.clearTimer("lowDelayTimer");
    const due = this.pointerRouter.nextDue;
    if (due !== undefined)
      this.lowDelayTimer = this.timers.setTimeout(
        () => {
          this.lowDelayTimer = null;
          this.performPointer(this.pointerRouter.drain(this.timers.now()));
        },
        Math.max(0.001, due - this.timers.now()) * 1000,
      );
  }
  scheduleDwell() {
    this.clearTimer("dwellTimer");
    const due = this.dwell.nextDue;
    if (due === null) return;
    this.dwellTimer = this.timers.setTimeout(
      () => {
        this.dwellTimer = null;
        if (
          !this.bottomHeld &&
          !this.hudSession &&
          !this.scrollActive &&
          this.buttons === 0 &&
          this.dwell.tick(this.timers.now())
        ) {
          const p = this.mac.location();
          this.transition(1, p);
          this.transition(0, p);
        }
      },
      Math.max(0.001, due - this.timers.now()) * 1000,
    );
  }
  setCircleLight(active) {
    if (this.circleLight === active) return;
    this.circleLight = active;
    this.queue("global.wandCircleScrolling=" + active + ";updateLights();");
    if (active && this.circleTimer === null)
      this.circleTimer = this.timers.setInterval(
        () => this.performPointer(this.pointerRouter.tick(this.timers.now())),
        100,
      );
    else if (!active) {
      this.timers.clearInterval(this.circleTimer);
      this.circleTimer = null;
    }
  }
  cancelCircleScroll() {
    this.dwell.reset();
    this.scheduleDwell();
    this.performPointer(this.pointerRouter.interrupt());
    this.setCircleLight(false);
  }

  transition(next, point) {
    if ((this.buttons & 1) !== (next & 1)) {
      const down = (next & 1) !== 0;
      if (down) {
        const now = this.timers.now();
        const close =
          Math.hypot(
            point.x - this.lastClickPoint.x,
            point.y - this.lastClickPoint.y,
          ) <= 4;
        this.clickCount =
          close && now - this.lastClickTime <= this.tuning.macDoubleClickSeconds
            ? this.clickCount + 1
            : 1;
        this.lastClickTime = now;
        this.lastClickPoint = point;
      }
      this.mac.mouse(down ? "down" : "up", point, this.clickCount);
    }
    this.buttons = next;
  }

  releaseButtons() {
    this.transition(0, this.mac.location());
  }
}
