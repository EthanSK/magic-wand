/*
 * A small Espruino-shaped host for the wand's own device code.
 *
 * The website's Web Worker and the Node tests both load this file, then evaluate the unmodified
 * device source and bridge in that realm's global scope, exactly as the Puck's REPL would. Only
 * the APIs the wand uses are provided. Puck sensors, pins, LEDs and Bluetooth are simulated;
 * nothing here talks to real hardware.
 */
(function (root) {
  "use strict";

  var FORWARDER = typeof Symbol === "function" ? Symbol("wandForwarder") : "__wandForwarder";

  /*
   * Espruino's Function.replaceWith swaps a function's code in place, so watches and timers that
   * hold the old reference run the new code. JavaScript cannot do that, so every top-level device
   * function becomes a stable forwarder whose target the bridge can replace.
   */
  function prepareFirmware(source) {
    var names = [];
    var declaration = /^function ([A-Za-z_$][\w$]*)\s*\(/gm;
    var match;
    while ((match = declaration.exec(source))) names.push(match[1]);
    if (!/\nonInit\(\);\s*$/.test(source)) throw new Error("Device source must end with onInit();");
    var renamed = source.replace(declaration, function (_whole, name) {
      return "function __wandOriginal_" + name + "(";
    });
    var forwarders = "var __wandPatch={};" + names.map(function (name) {
      return "__wandPatch." + name + "=__wandOriginal_" + name + ";" +
        "function " + name + "(){return __wandPatch." + name + ".apply(this,arguments)}" +
        name + ".replaceWith=function(f){__wandPatch." + name + "=f};" +
        name + ".toString=function(){return __wandPatch." + name + ".toString()};" +
        "__wandMarkForwarder(" + name + ");";
    }).join("");
    return forwarders + "\n" + renamed;
  }

  function install(G, host) {
    var pins = { D1: 1, D2: 1, D30: 1 };
    var watches = {};
    var nextWatch = 1;
    var accelListeners = [];
    var nrfListeners = { connect: [], disconnect: [] };
    var awake = false;
    var sampleRate = 0;
    var outbox = [];
    var depth = 0;

    function push(event) {
      outbox.push(event);
      flush();
    }
    function flush() {
      if (depth === 0 && outbox.length) {
        var events = outbox;
        outbox = [];
        host.emit(events);
      }
    }
    // Every entry from the host runs through here, like one Espruino event-loop task.
    function dispatch(fn, args) {
      depth++;
      try {
        return fn.apply(null, args || []);
      } catch (error) {
        outbox.push({ type: "line", text: "Uncaught " + (error && error.stack ? String(error.message) : String(error)) });
        if (host.onError) host.onError(error);
      } finally {
        depth--;
        flush();
        // Timers can change device state without printing; let the host notice.
        if (depth === 0 && host.afterDispatch) host.afterDispatch();
      }
    }
    function lamp(name) {
      return {
        name: name, level: 0,
        set: function () { this.level = 1; },
        reset: function () { this.level = 0; },
        write: function (value) { this.level = Number(value); },
        read: function () { return this.level > 0; }
      };
    }

    G.global = G;
    G.D1 = "D1"; G.D2 = "D2"; G.D30 = "D30";
    G.LED1 = lamp("red"); G.LED2 = lamp("green"); G.LED3 = lamp("blue");
    G.__wandMarkForwarder = function (fn) { fn[FORWARDER] = true; };
    G.Function.prototype.replaceWith = function () {
      if (!this[FORWARDER]) throw new Error("This simulation can only replace top-level device functions");
    };

    G.getTime = function () { return host.now(); };
    G.print = function () {
      var text = Array.prototype.map.call(arguments, function (value) {
        return typeof value === "string" ? value : JSON.stringify(value);
      }).join(" ");
      push({ type: "line", text: text });
    };
    G.Bluetooth = { println: function (text) { push({ type: "line", text: String(text) }); } };
    G.require = function (name) {
      if (name !== "ble_hid_mouse") throw new Error("Module not available in the simulation: " + name);
      return {
        report: [],
        // The receiver replaces this with a UART report; frames carry the same x, y and buttons.
        send: function (x, y, b, callback) {
          push({ type: "frame", x: x, y: y, b: b });
          if (callback) callback();
        }
      };
    };

    G.digitalRead = function (pin) { return pins[pin]; };
    G.pinMode = function () {};
    G.analogWrite = function (pin, value) { pin.level = Number(value); };
    G.setWatch = function (callback, pin, options) {
      var id = nextWatch++;
      watches[id] = { pin: pin, cb: callback, edge: (options && options.edge) || "both" };
      return id;
    };
    G.clearWatch = function (id) {
      if (id === undefined) watches = {};
      else delete watches[id];
    };

    function wrap(callback) { return function () { dispatch(callback); }; }
    G.setTimeout = function (callback, ms) { return host.setTimeout(wrap(callback), ms); };
    G.setInterval = function (callback, ms) { return host.setInterval(wrap(callback), ms); };
    G.clearTimeout = function (id) { host.clearTimeout(id); };
    G.clearInterval = function (id) { host.clearInterval(id); };

    function listenerList(list) { return list.length === 1 ? list[0] : list.slice(); }
    G.NRF = {
      setServices: function () {},
      setAdvertising: function () {},
      setConnectionInterval: function () {},
      on: function (name, fn) { (nrfListeners[name] = nrfListeners[name] || []).push(fn); },
      removeListener: function (name, fn) {
        var list = nrfListeners[name] || [];
        var index = list.indexOf(fn);
        if (index >= 0) list.splice(index, 1);
      }
    };
    Object.defineProperty(G.NRF, "#onconnect", { get: function () { return nrfListeners.connect.length ? listenerList(nrfListeners.connect) : undefined; } });
    Object.defineProperty(G.NRF, "#ondisconnect", { get: function () { return nrfListeners.disconnect.length ? listenerList(nrfListeners.disconnect) : undefined; } });

    G.Puck = {
      accelOn: function (rate) { awake = true; sampleRate = rate || 12.5; },
      accelOff: function () { awake = false; },
      on: function (name, fn) { if (name === "accel") accelListeners.push(fn); },
      removeListener: function (name, fn) {
        var index = accelListeners.indexOf(fn);
        if (name === "accel" && index >= 0) accelListeners.splice(index, 1);
      }
    };
    Object.defineProperty(G.Puck, "#onaccel", { get: function () { return accelListeners.length ? listenerList(accelListeners) : undefined; } });

    G.E = { setFlags: function () {}, internal: {} };
    Object.defineProperty(G.E.internal, "watches", {
      get: function () {
        var copy = {};
        Object.keys(watches).forEach(function (id) { copy[id] = { pin: watches[id].pin, cb: watches[id].cb }; });
        return copy;
      }
    });

    var evaluate = G.eval; // Indirect eval: global scope, like the Puck's REPL.
    return {
      /** Evaluate one REPL command. */
      evaluate: function (code) { return dispatch(function () { return evaluate(code); }); },
      /** Load the readable device program, preserving its functions for the bridge. */
      load: function (source) { return dispatch(function () { return evaluate(prepareFirmware(source)); }); },
      /** Send a compacted bridge exactly as the receiver does: one statement per command. */
      loadFragments: function (text) {
        text.split("\n").forEach(function (line) { if (line.trim()) dispatch(function () { evaluate(line); }); });
      },
      setPin: function (pin, value) {
        if (!(pin in pins)) throw new Error("Unknown pin " + pin);
        value = value ? 1 : 0;
        if (pins[pin] === value) return;
        pins[pin] = value;
        var time = host.now();
        Object.keys(watches).forEach(function (id) {
          var watch = watches[id];
          if (!watch || watch.pin !== pin) return;
          if (watch.edge === "rising" && !value) return;
          if (watch.edge === "falling" && value) return;
          dispatch(watch.cb, [{ state: !!value, time: time }]);
        });
      },
      /** Deliver one gyro reading (raw units: degrees per second × 134) while the sensor is on. */
      accel: function (gyro) {
        if (!awake) return false;
        var sample = { acc: { x: 0, y: 0, z: 8192 }, gyro: gyro };
        accelListeners.slice().forEach(function (listener) { dispatch(listener, [sample]); });
        return true;
      },
      connect: function () { nrfListeners.connect.slice().forEach(function (fn) { dispatch(fn); }); },
      disconnect: function () { nrfListeners.disconnect.slice().forEach(function (fn) { dispatch(fn); }); },
      get awake() { return awake; },
      get sampleRate() { return sampleRate; },
      pin: function (pin) { return pins[pin]; },
      lights: function () { return [G.LED1.level, G.LED2.level, G.LED3.level]; },
      watchCount: function () { return Object.keys(watches).length; }
    };
  }

  root.WandEspruino = { install: install, prepareFirmware: prepareFirmware };
})(typeof self !== "undefined" ? self : globalThis);
