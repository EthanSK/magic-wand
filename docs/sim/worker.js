/*
 * Runs the wand's device code off the main thread, as a stand-in Puck.js.
 *
 * The page sends button edges, the visitor's aim (degrees) and REPL commands from the receiver
 * model. The worker turns aim into gyro readings while the device code has the sensor on, and
 * posts back the device's UART lines, mouse report frames and light state.
 */
"use strict";

// The shim installs Espruino's timer functions on this same global scope, so keep the worker's own.
var nativeSetTimeout = self.setTimeout.bind(self);
var nativeSetInterval = self.setInterval.bind(self);
var nativeClearTimeout = self.clearTimeout.bind(self);
var nativeClearInterval = self.clearInterval.bind(self);

var device = null;
var aims = []; // [workerSeconds, yaw, pitch], newest last
var tick = null;
var paused = false;
var lastState = "";
var SAMPLE_MS = 16;
var RATE_WINDOW = 0.05; // Seconds of aim history per gyro reading, so uneven page frames don't spike.

function now() { return performance.now() / 1000 + 1000; }

function snapshot() {
  var G = self;
  return {
    lights: device ? Array.from(device.lights()) : [0, 0, 0],
    awake: device ? device.awake : false,
    moveLatched: Boolean(G.moveLatched),
    hudOpen: Boolean(G.hudOpen),
    scrollHeld: Boolean(G.scrollHeld),
    dragging: Boolean(G.dragging),
    tapPending: Boolean(G.tapPending),
    gesture: typeof G.moveGestureMode === "string" ? G.moveGestureMode : null,
    recording: Boolean(G.wandRecording),
    calibrated: Boolean(G.bias)
  };
}

function postState(force) {
  var state = snapshot();
  var key = JSON.stringify(state);
  if (!force && key === lastState) return;
  lastState = key;
  self.postMessage({ type: "state", state: state });
}

function aimAt(time) {
  if (!aims.length) return { yaw: 0, pitch: 0 };
  if (time >= aims[aims.length - 1][0]) return { yaw: aims[aims.length - 1][1], pitch: aims[aims.length - 1][2] };
  for (var i = aims.length - 1; i > 0; i--) {
    var a = aims[i - 1];
    var b = aims[i];
    if (time >= a[0]) {
      var f = (time - a[0]) / Math.max(1e-6, b[0] - a[0]);
      return { yaw: a[1] + (b[1] - a[1]) * f, pitch: a[2] + (b[2] - a[2]) * f };
    }
  }
  return { yaw: aims[0][1], pitch: aims[0][2] };
}

function sample() {
  if (!device || paused) return;
  var t = now();
  if (!device.awake) return;
  var current = aimAt(t);
  var previous = aimAt(t - RATE_WINDOW);
  var yawRate = (current.yaw - previous.yaw) / RATE_WINDOW;
  var pitchRate = (current.pitch - previous.pitch) / RATE_WINDOW;
  // Puck gyro units are degrees per second × 134. The wand maps yaw to −z and pitch to −x.
  device.accel({ x: -pitchRate * 134, y: 0, z: -yawRate * 134 });
  postState(false);
}

function start(urls) {
  importScripts(urls.shim);
  return Promise.all([fetch(urls.device), fetch(urls.bridge)]).then(function (responses) {
    responses.forEach(function (response) { if (!response.ok) throw new Error("Couldn't load the device code (" + response.status + ")"); });
    return Promise.all(responses.map(function (response) { return response.text(); }));
  }).then(function (sources) {
    var host = {
      now: now,
      setTimeout: nativeSetTimeout,
      setInterval: nativeSetInterval,
      clearTimeout: nativeClearTimeout,
      clearInterval: nativeClearInterval,
      emit: function (events) { self.postMessage({ type: "events", events: events }); },
      afterDispatch: function () { postState(false); },
      onError: function (error) { self.postMessage({ type: "device-error", message: String(error && error.message || error) }); }
    };
    device = self.WandEspruino.install(self, host);
    device.load(sources[0]);
    // A still wand calibrates on boot: feed two seconds of stillness at the requested rate.
    for (var i = 0; i < Math.ceil(self.CONFIG.sampleRate * 2.2) && !self.bias; i++) device.accel({ x: 0, y: 0, z: 0 });
    device.loadFragments(sources[1]);
    device.connect();
    tick = nativeSetInterval(sample, SAMPLE_MS);
    postState(true);
    self.postMessage({ type: "ready", runtime: self.WAND_RUNTIME_VERSION || null });
  });
}

self.onmessage = function (event) {
  var message = event.data;
  try {
    switch (message.type) {
      case "init":
        start(message.urls).catch(function (error) { self.postMessage({ type: "fatal", message: String(error && error.message || error) }); });
        break;
      case "aim":
        // The page only posts while the aim changes. Anchor the previous aim just before this
        // one, so a move after a pause starts now instead of spreading back into the pause.
        var last = aims[aims.length - 1];
        if (last && now() - last[0] > 0.04) aims.push([now() - 0.001, last[1], last[2]]);
        aims.push([now(), message.yaw, message.pitch]);
        while (aims.length > 2 && aims[1][0] < now() - 0.5) aims.shift();
        break;
      case "pin":
        if (device) device.setPin(message.pin, message.value);
        postState(false);
        break;
      case "eval":
        if (device) device.evaluate(message.code);
        postState(false);
        break;
      case "pause":
        paused = Boolean(message.paused);
        break;
      default:
        break;
    }
  } catch (error) {
    self.postMessage({ type: "device-error", message: String(error && error.message || error) });
  }
};
