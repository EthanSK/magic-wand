/*
 * Sense host for the canonical Puck program ("virtual Puck").
 *
 * The XIAO nRF52840 Sense runs its own complete saved firmware (wand_sense.ino)
 * that only reports buttons and motion and obeys light/sensor/sleep commands.
 * Ethan's gestures stay in the one canonical implementation: the unchanged Puck
 * base program, mode bridge and power policy run here, on the Mac, through the
 * website's Espruino shim (docs/sim/espruino.js). Nothing in this file decides a
 * gesture. It supplies real pins, real gravity and gyro readings, real timers,
 * the status light, sensor power and button-wake standby.
 *
 * Load order in one realm: docs/sim/espruino.js, then this file. The native
 * side supplies `native` with: now(), schedule(id, ms, repeat), cancel(id),
 * text(line), light(r, g, b), imu(mode), sleep(), log(text).
 * No gesture timing is buffered: every reading is applied as soon as it arrives.
 */
(function (root) {
  "use strict";

  // Logical control mask, matching the Puck @IMU mask: mouse button 1, HUD button 2,
  // speech button 4.
  var PINS = [["D1", 1], ["D2", 2], ["D30", 4]];

  function create(G, native) {
    var timers = {}, nextTimer = 1, dead = false, booting = true, bootErrors = 0;
    var override; // Device-aligned reading time while one telemetry frame is applied.
    var linkUp = false, imuMode = -1, lastLight = "", lastDelivered = -Infinity;
    var batteryVolts, batteryPercent;
    var lightOwnerPins = { mouse: "D1", scroll: "D1", hud: "D2", app: "D2", recording: "D30" };
    var lightDemoTimer, lightDemoStarted = 0, lightDemoContext;
    var clickLightTimer, clickBlue = 0;

    var host = {
      now: function () { return override !== undefined ? override : native.now(); },
      setTimeout: function (fn, ms) { var id = nextTimer++; timers[id] = { fn: fn, repeat: false }; native.schedule(id, Math.max(0, +ms || 0), false); return id; },
      setInterval: function (fn, ms) { var id = nextTimer++; timers[id] = { fn: fn, repeat: true }; native.schedule(id, Math.max(1, +ms || 0), true); return id; },
      clearTimeout: function (id) { if (timers[id]) { delete timers[id]; native.cancel(id); } },
      clearInterval: function (id) { if (timers[id]) { delete timers[id]; native.cancel(id); } },
      emit: function (events) {
        if (dead) return;
        for (var i = 0; i < events.length; i++) {
          var e = events[i];
          // The HID mouse path does not exist on the Sense; the receiver's
          // handshake replaces mouse.send with @WAND UART lines before use.
          if (e.type !== "line") continue;
          if (/^Uncaught /.test(e.text)) { if (booting) bootErrors++; native.log(e.text); }
          if (booting) continue; // A boot is not a connection: the receiver hears nothing until its handshake.
          native.text(e.text);
        }
      },
      onError: function () {},
      afterDispatch: function () { sync(); }
    };
    var device = root.WandEspruino.install(G, host);

    // Real sensor power: Puck.accelOn(1.6) is accelerometer-only, >=12.5 Hz adds the gyro.
    var accelOn = G.Puck.accelOn, accelOff = G.Puck.accelOff;
    G.Puck.accelOn = function (rate) { accelOn(rate); setIMU((rate || 12.5) >= 12.5 ? 2 : 1); };
    G.Puck.accelOff = function () { accelOff(); setIMU(0); };
    // sensorHold: the receiver's debug pause keeps full-rate readings flowing to
    // the dashboard; deliver() still follows the program's own requested rate.
    var sensorHold = false, sentIMU;
    function setIMU(mode) { if (mode !== imuMode) { imuMode = mode; sendIMU(); } }
    function sendIMU() { var m = sensorHold ? 2 : imuMode; if (!dead && m >= 0 && m !== sentIMU) { sentIMU = m; native.imu(m); } }

    // Real link and button-wake standby. NRF.sleep() on the Puck stops the radio;
    // on the Sense it asks the saved firmware for button-wake power-off.
    G.NRF.getSecurityStatus = function () { return { connected: linkUp }; };
    G.NRF.sleep = function () { if (!dead && !booting) native.sleep(); };
    G.NRF.wake = function () {};
    G.NRF.getBattery = function () { return batteryVolts; };
    G.E.getBattery = function () { return batteryPercent; };

    function lightContext() {
      return [G.wandLastLightState, !!G.wandRecording, G.digitalRead(G.D1), G.digitalRead(G.D2), G.digitalRead(G.D30)].join(":");
    }
    function stopLightDemo(reason) {
      if (lightDemoTimer === undefined) return;
      host.clearInterval(lightDemoTimer); lightDemoTimer = undefined;
      native.log("LIGHT_DEMO_" + reason);
    }
    function lightDemoAllowed() {
      return !dead && !booting && linkUp && !G.WAND_UPDATING && G.wandMotionReady !== false &&
        !G.calibrationLit && !G.wandDeskSleeping && !G.wandPowerStandby && G.wandPowerWarnPhase === undefined &&
        ["idle", "mouse", "hud", "app", "recording", "scroll"].indexOf(G.wandLastLightState) >= 0;
    }
    function stopClickLight() {
      if (clickLightTimer !== undefined) host.clearTimeout(clickLightTimer);
      clickLightTimer = undefined;
    }
    // Ethan's sent-click acknowledgement: dip an already-blue mouse light,
    // otherwise briefly show dim blue (including from recording red). Only
    // outgoing RGB changes; the current mode is restored from live state.
    function clickLight() {
      if (!lightDemoAllowed() || lightDemoTimer !== undefined) return false;
      stopClickLight();
      clickBlue = G.wandLastLightState === "mouse" ? 0.025 : 0.25;
      clickLightTimer = host.setTimeout(function () { clickLightTimer = undefined; sync(); }, 90);
      sync(); native.log("CLICK_LIGHT"); return true;
    }
    // An explicitly requested, bounded hardware demonstration. Only the emitted
    // RGB value changes: canonical mode state, controls and stored firmware do not.
    function lightDemo(on) {
      if (!on) { stopLightDemo("CANCELLED"); sync(); return true; }
      if (!lightDemoAllowed() || lightDemoTimer !== undefined) return false;
      lightDemoStarted = native.now(); lightDemoContext = lightContext();
      lightDemoTimer = host.setInterval(sync, 50);
      native.log("LIGHT_DEMO_STARTED"); sync(); return true;
    }
    function sync() {
      if (dead) return;
      var levels = [G.LED1.level, G.LED2.level, G.LED3.level].map(function (v) { return Math.max(0, Math.min(1, Number(v) || 0)); });
      // Ethan: keep a dim version of the current mode, then brighten it while
      // that mode's own button is held. The canonical bridge still chooses the
      // mode and hue; this Sense output adapter only changes brightness.
      // Power warnings write the LEDs directly and must retain their full flash.
      var owner = lightOwnerPins[G.wandLastLightState];
      if (owner && linkUp && !booting && G.wandPowerWarnPhase === undefined && !G.wandPowerStandby && G.digitalRead(G[owner])) {
        levels = levels.map(function (v) { return v * 0.35; });
      }
      if (lightDemoTimer !== undefined) {
        var elapsed = native.now() - lightDemoStarted;
        if (!lightDemoAllowed() || lightContext() !== lightDemoContext) stopLightDemo("CANCELLED");
        else if (elapsed >= 8) stopLightDemo("FINISHED");
        else if (elapsed < 1) levels = [1, 0, 0];
        else if (elapsed < 2) levels = [0, 1, 0];
        else if (elapsed < 3) levels = [0, 0, 1];
        else {
          var brightness = elapsed < 5 ? .15 + .85 * (elapsed - 3) / 2 : elapsed < 7 ? 1 - .85 * (elapsed - 5) / 2 : .15;
          levels = [brightness, brightness, brightness];
        }
      }
      if (clickLightTimer !== undefined) {
        if (!lightDemoAllowed()) stopClickLight();
        else levels = [0, 0, clickBlue];
      }
      var key = levels.join(",");
      if (key !== lastLight) { lastLight = key; native.light(levels[0], levels[1], levels[2]); }
    }

    // Espruino console semantics for the receiver's queue(): Ctrl-C clears pending
    // input, DLE hides echo, and a statement runs once its brackets are complete.
    var pending = "";
    function complete(text) {
      var depth = 0, quote = null, escape = false, line = false, block = false;
      for (var i = 0; i < text.length; i++) {
        var c = text[i], n = text[i + 1];
        if (line) { if (c === "\n") line = false; continue; }
        if (block) { if (c === "*" && n === "/") { block = false; i++; } continue; }
        if (quote) { if (escape) escape = false; else if (c === "\\") escape = true; else if (c === quote) quote = null; continue; }
        if (c === "/" && n === "/") { line = true; i++; continue; }
        if (c === "/" && n === "*") { block = true; i++; continue; }
        if (c === "'" || c === '"' || c === "`") { quote = c; continue; }
        if (c === "{" || c === "(" || c === "[") depth++;
        else if (c === "}" || c === ")" || c === "]") depth--;
      }
      return depth <= 0 && !quote && !block;
    }
    function repl(text) {
      if (dead) return;
      var parts = String(text).split("\n");
      for (var i = 0; i < parts.length; i++) {
        var part = parts[i];
        var cancel = part.lastIndexOf("\u0003");
        if (cancel >= 0) { pending = ""; part = part.slice(cancel + 1); }
        part = part.replace(/\u0010/g, "");
        if (!part.trim() && !pending) continue;
        pending += (pending ? "\n" : "") + part;
        if (complete(pending)) { var code = pending; pending = ""; device.evaluate(code); }
      }
    }

    // Also used after a bridge reload, which resets CONFIG.gain. The caller
    // invokes this once per freshly loaded bridge, never per sensor reading.
    function configurePointer(gain) {
      device.evaluate("CONFIG.ySign=1;global.wandRawBias=undefined;CONFIG.gain*=" + gain + ";");
    }
    function boot(base, bridge, power, zero, runtime, revision, options) {
      var gain = options && isFinite(options.pointerGain) && options.pointerGain >= 0.25 && options.pointerGain <= 4 ? +options.pointerGain : 1;
      device.load(base);
      device.evaluate("global.wandRawPointer=true;");
      // The saved Puck boot order: base, bridge, power policy, then the stored zero.
      device.loadFragments(bridge.split("\n").filter(function (l) { return l.indexOf("WAND_MODE_ROUTING_READY") < 0; }).join("\n"));
      // Ethan verified horizontal travel, but vertical travel was inverted on
      // this Sense mounting. Apply the shared vertical direction before the
      // receiver's @ZERO configuration: pointer, HUD and scroll stay aligned.
      configurePointer(gain);
      // Ethan's Sense pointer sensitivity (receiver WandSenseTuning): pointer
      // gain only, also before @ZERO. HUD, review and scrolling use angles.

      linkUp = true; // The Sense link already exists; never arm the Puck's offline timers here.
      device.loadFragments(power);
      if (zero) device.evaluate("global.restoreWandCalibration(" + zero + ");");
      var ok = bootErrors === 0 && G.wandMotionReady === true && G.WAND_POWER_POLICY_VERSION === 4 &&
        typeof G.wandEnterDeepStandby === "function" && G.wandPowerWatches && G.wandPowerWatches.length === 3;
      // Never advertise a ready bridge after a failed boot; the receiver then
      // reloads it through its normal checked path or stays unavailable.
      device.evaluate("global.WAND_RUNTIME_VERSION=" + JSON.stringify(runtime) + ";" +
        (ok ? "global.WAND_BRIDGE_REVISION=" + JSON.stringify(revision) + ";" : "") +
        "global.WAND_PERSISTENT_IMAGE='sense-host';global.WAND_UPDATING=false;updateLights();");
      booting = false;
      device.connect(); // Bridge onConnect and power-policy connect handlers, as on a real connection.
      sync();
      return ok;
    }

    // One telemetry frame: button state first (its watches see the same time),
    // then one reading. acc in Puck units (8192 per g), gyro in Puck units (134 per deg/s).
    function deliver(time, mask, acc, gyro) {
      if (dead) return;
      override = time;
      try {
        for (var i = 0; i < PINS.length; i++) device.setPin(PINS[i][0], mask & PINS[i][1] ? 0 : 1);
        if (acc && device.awake) {
          var rate = device.sampleRate || 12.5;
          // Accelerometer-only desk sensing follows the requested low rate.
          if (rate >= 12.5 || time - lastDelivered >= 1 / rate - 0.002) {
            lastDelivered = time;
            var sample = { acc: { x: acc[0], y: acc[1], z: acc[2] } };
            if (rate >= 12.5 && gyro) sample.gyro = { x: gyro[0], y: gyro[1], z: gyro[2] };
            var listeners = G.Puck["#onaccel"];
            listeners = typeof listeners === "function" ? [listeners] : (listeners || []);
            for (var j = 0; j < listeners.length; j++) {
              try { listeners[j](sample); }
              catch (error) { G.print("Uncaught " + (error && error.message ? error.message : String(error))); }
            }
          }
        }
      } finally { override = undefined; sync(); }
    }

    function fire(id) {
      var timer = timers[id];
      if (dead || !timer) return;
      if (!timer.repeat) delete timers[id];
      timer.fn();
    }

    return {
      boot: boot, repl: repl, deliver: deliver, fire: fire, configurePointer: configurePointer, lightDemo: lightDemo, clickLight: clickLight,
      holdSensor: function (on) { sensorHold = !!on; sendIMU(); },
      battery: function (volts, percent) { batteryVolts = volts; batteryPercent = percent; },
      teardown: function () { stopClickLight(); stopLightDemo("CANCELLED"); dead = true; timers = {}; },
      state: function () { return { awake: device.awake, rate: device.sampleRate, imu: imuMode, light: lastLight, link: linkUp, ready: G.wandMotionReady === true }; },
      device: device
    };
  }

  root.WandSenseHost = { create: create };
})(typeof self !== "undefined" ? self : globalThis);
