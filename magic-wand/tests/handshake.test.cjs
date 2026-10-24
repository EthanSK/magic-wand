// The receiver's connect handshake, taken from receiver/Sources/main.swift and run against a
// stand-in device. Ported from the wand's original handshake check.
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("vm");
const { read } = require("./harness.cjs");

test("handshake reconfigures only on a version mismatch and is idempotent", () => {
  const swift = read("receiver/Sources/main.swift");
  const expression = swift.match(/let handshake = (.+)\n/)[1];
  const parts = expression.split(" + runtimeVersion + ");
  assert.equal(parts.length, 2, "handshake joins two Swift string literals around the runtime version");
  const version = read("device/generated/wand-runtime-version.txt");
  const command = JSON.parse(parts[0]) + version + JSON.parse(parts[1]);

  let out = [];
  let connects = 0;
  const original = () => {};
  const ctx = { mouse: { send: original }, Bluetooth: { println: (x) => out.push(x) }, print: (x) => out.push(x), connected: false, onConnect: () => { connects++; } };
  ctx.global = ctx;
  vm.createContext(ctx);

  vm.runInContext(command, ctx);
  assert.deepEqual(out, ["WAND_NEEDS_CONFIG"], "a different runtime asks for an upload");
  assert.equal(ctx.mouse.send, original);

  out = [];
  ctx.WAND_RUNTIME_VERSION = version;
  vm.runInContext(command, ctx);
  assert.equal(connects, 1, "a matching runtime is connected without re-uploading");
  assert.equal(ctx.wandBridgeOriginalSend, original);
  ctx.mouse.send(2, -4, 1, () => {});
  assert.deepEqual(out, ["WAND_BRIDGE_READY", "@WAND 2,-4,1"], "mouse reports travel over UART");

  out = [];
  ctx.connected = true;
  vm.runInContext(command, ctx);
  assert.equal(connects, 1, "an existing link is not recalibrated");
  assert.equal(ctx.wandBridgeOriginalSend, original, "the original sender is kept once");
});
