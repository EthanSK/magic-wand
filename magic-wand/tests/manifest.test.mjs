// wand.json is the one maintained description of the wand. These checks fail when it drifts
// from the device code, the bridge, the receiver or the generated files.
import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { createWand, read } = require("./harness.cjs");
const manifest = JSON.parse(read("wand.json"));
const device = read("device/wand-mouse-prototype.js");
const bridge = read("device/wand-mode-bridge.js");
const swift = read("receiver/Sources/main.swift");
const pointer = read("receiver/Sources/WandPointerControl.swift");
const sha256 = (text) => createHash("sha256").update(text).digest("hex");
const number = (pattern, source, label) => {
  const match = source.match(pattern);
  assert(match, `Could not find ${label}`);
  return Number(match[1]);
};

test("versions match the sources and the receiver bundle", () => {
  const body = device.slice(device.indexOf("// Adjust only"));
  assert.equal(manifest.versions.deviceRuntime, "wand-" + sha256(body).slice(0, 12));
  assert.equal(manifest.versions.deviceRuntime, read("device/generated/wand-runtime-version.txt"));
  assert.equal(manifest.versions.bridgeRevision, sha256(read("device/generated/wand-mode-bridge.compact.js")));
  const plist = read("receiver/Info.plist");
  const value = (key) => plist.match(new RegExp(`<key>${key}</key>\\s*<string>([^<]+)</string>`))[1];
  assert.equal(manifest.versions.receiver, value("CFBundleShortVersionString"));
  assert.equal(manifest.versions.receiverBuild, value("CFBundleVersion"));
});

test("button pins and pull-ups match the device code", () => {
  const pins = Object.fromEntries(manifest.buttons.map((button) => [button.id, button.pin]));
  assert.match(device, new RegExp(`var HUD_PIN=${pins.middle}, STT_PIN=${pins.top};`));
  assert.match(device, new RegExp(`var MOVE_PIN=${pins.bottom};`));
  for (const pin of Object.values(pins)) assert.match(device, new RegExp(`pinMode\\(${pin},"input_pullup"\\)`));
  assert.deepEqual(manifest.buttons.map((button) => button.key), ["T", "M", "B"]);
  assert.deepEqual(manifest.chords, [], "current independent controls have no combined-button chord");
  assert.match(bridge,/checkScrollChord\.replaceWith\(function\(\)\{return false;\}\)/);
  assert.doesNotMatch(bridge,/@LEFTCLICK/,"Ethan rejected the mouse button + HUD button click chord");
});

test("tuning matches the running device code and the receiver", () => {
  const wand = createWand({ bridge: "fragments" });
  wand.calibrate();
  wand.loadBridge();
  const { CONFIG } = wand.ctx;
  const t = manifest.tuning;
  assert.equal(number(/init\(lowDelay:Double=([\d.]+)/, pointer, "LOW delay") * 1000, t.lowMotionDelayMs);
  assert.equal(number(/init\(pause:Double=([\d.]+)/, pointer, "HIGH dwell") * 1000, t.highDwellMs);
  assert.equal(CONFIG.gain, t.pointerGain);
  assert.equal(CONFIG.heldPointerGain, t.heldPointerGain);
  assert.equal(number(/yawScale=min\(([\d.]+),length\/across\)/, pointer, "maximum heading correction"), t.orientationCompensation.maxHeadingGain);
  assert.equal(CONFIG.releaseClickPause, t.releaseClickPauseSeconds);
  assert.equal(CONFIG.slackDegrees, t.slackDegrees);
  assert.equal(CONFIG.slackRecentre, t.slackRecentreSeconds);
  assert.equal(CONFIG.slackQuietSpeed, t.slackQuietSpeedDegreesPerSecond);
  assert.equal(number(/gain:(\d+)/, device, "original gain"), t.previousPointerGain);
  assert.equal(Math.round((1 - t.pointerGain / t.previousPointerGain) * 100), 20, "20 percent lower gain");
  assert.equal(CONFIG.yGain, t.verticalRatio);
  assert.equal(CONFIG.fineGain, t.fineGain);
  assert.equal(CONFIG.fineSpeed, t.fineSpeedDegreesPerSecond);
  assert.equal(CONFIG.fullSpeed, t.fullSpeedDegreesPerSecond);
  assert.equal(CONFIG.deadZone, t.maximumNoiseZoneDegreesPerSecond);
  assert.equal(CONFIG.sampleRate, t.sensorRequestHz);
  assert.equal(Math.round(CONFIG.tapSeconds * 1000), t.holdMs);
  assert.equal(Math.round(CONFIG.doubleTapSeconds * 1000), t.clickDecisionMs);
  assert.equal(wand.ctx.wandHorizontalScrollBoost, t.horizontalScrollBoost);
  assert.equal(wand.ctx.wandDoubleClickSeconds, t.macDoubleClickSeconds);
  const guard = bridge.match(/e\.state\?([\d.]+):([\d.]+)/);
  assert.equal(Math.round(Number(guard[1]) * 1000), t.releaseGuardMs);
  assert.equal(Math.round(Number(guard[2]) * 1000), t.pressGuardMs);
  assert.equal(Math.round(number(/wandMotionReadyAt=lastTime\+([\d.]+)/, bridge, "cold settle") * 1000), t.coldSettleMs);
  assert.equal(number(/if\(!moveLatched&&!hudOpen&&!scrollHeld&&!global\.wandReviewTracking&&!global\.wandShot\)global\.wandPowerDownGyro\(\);\s*\},(\d+)\)/, bridge, "sensor grace"), t.sensorIdleGraceMs);
  assert.equal(number(/NRF\.setConnectionInterval\((\d+)\)/, device, "connection interval"), t.bluetoothIntervalMs);
  assert.equal(number(/if\(hudHeld\)middlePress\(\);\},(\d+)\)/, device, "middle delay"), t.middleReportDelayMs);
  assert.equal(number(/hudTimer=setInterval\(hudReport,(\d+)\)/, device, "HUD report"), t.reportIntervalMs);
  assert.equal(number(/scrollTimer=setInterval\(function\(\)\{scrollReport\('U'\);\},(\d+)\)/, device, "scroll report"), t.reportIntervalMs);
  assert.match(device, new RegExp(`samples>=CONFIG\\.sampleRate\\*${t.calibrationSeconds}\\)`));
  assert.equal(number(/scrollFractionX\+=\(x\/1000-scrollX\)\*([\d.]+)/, swift, "host scroll gain"), t.hostScrollGain);
  assert.equal(Math.round(number(/hudButtonHold=WandRunLoop\.commonTimer\(interval:([\d.]+)/, swift, "receiver hold") * 1000), t.receiverHoldMs);
});

test("V3 held-scroll speed range matches the native controller", () => {
  const t = manifest.tuning.sustainedScroll;
  const sustained = pointer.slice(pointer.indexOf("final class WandSustainedScroll"), pointer.indexOf("final class WandHeldScroll"));
  assert.equal(number(/var ordinaryMaxRate=([\d.]+)/, sustained, "ordinary maximum"), t.ordinaryMaxLinesPerSecond);
  assert.equal(number(/var highSpeedFrom=([\d.]+)/, sustained, "high-speed start"), t.highSpeedFromDegreesPerSecond);
  assert.equal(number(/highSpeedFull=([\d.]+)/, sustained, "high-speed full"), t.highSpeedFullDegreesPerSecond);
  assert.equal(number(/var maxRate=([\d.]+)/, sustained, "maximum"), t.maxLinesPerSecond);
  assert.equal(number(/var horizontalGain=([\d.]+)/, sustained, "horizontal gain"), t.horizontalGain);
  assert.equal(number(/var horizontalMaxRate=([\d.]+)/, sustained, "horizontal maximum"), t.horizontalMaxLinesPerSecond);
  assert.equal(number(/var horizontalGainFrom=([\d.]+)/, sustained, "horizontal gain start"), t.horizontalGainFromDegreesPerSecond);
  assert.equal(number(/horizontalGainFull=([\d.]+)/, sustained, "horizontal gain full"), t.horizontalGainFullDegreesPerSecond);
  assert.equal(number(/var horizontalGainLevelSlope=([\d.]+)/, sustained, "horizontal full-gain slope"), t.horizontalGainLevelSlope);
  assert.equal(number(/init\(linesPerDegree:Double=([\d.]+)/, sustained, "gain"), t.linesPerDegree);
  assert.equal(number(/wheel1:Int32\(clamping:Int64\(y\)\*(\d+)\)/, swift, "points per line"), t.pointsPerLine);
});

test("micro-circle tuning matches native geometry and preserves pointer noise guards", () => {
  const t = manifest.tuning.microCircles;
  const held = pointer.slice(pointer.indexOf("final class WandHeldScroll"), pointer.indexOf("struct WandReviewExitGesture"));
  const review = pointer.slice(pointer.indexOf("struct WandReviewCircle"));
  for (const [key, re] of [
    ["heldHeadingSegmentDegrees", /tuning.segment=([\d.]+)/],
    ["heldMinimumPathDegrees", /tuning.minPath=([\d.]+)/],
    ["heldMinimumExtentDegrees", /tuning.minExtent=([\d.]+)/],
    ["heldAxisAcquisitionDegrees", /hypot\(directionTravelX,directionTravel\)>=([\d.]+)/],
    ["heldQuietSpeedDegreesPerSecond", /guard hypot\(x,y\)>([\d.]+)/],
  ]) assert.equal(number(re, held, key), t[key]);
  for (const [key,re] of [
    ["reviewHeadingSegmentDegrees",/minimumSegment = ([\d.]+)/],
    ["reviewMinimumSidewaysDegrees",/minimumSideways = ([\d.]+)/],
    ["reviewMinimumPathDegrees",/minimumPath = ([\d.]+)/],
    ["reviewFirstTurnDegrees",/firstTurnDegrees = ([\d.]+)/],
    ["reviewQuarterTurnDegrees",/quarterTurnDegrees = ([\d.]+)/],
    ["reviewCuspTurnDegrees",/cuspTurnDegrees = ([\d.]+)/],
    ["reviewSegmentFraction",/segmentFraction = ([\d.]+)/],
    ["reviewMinimumSegmentFraction",/partialSegment = ([\d.]+)/],
    ["reviewNoiseSegmentFactor",/noiseSegment = ([\d.]+)/],
  ]) assert.equal(number(re,review,key),t[key]);
  assert.equal(number(/static let seconds = ([\d.]+)/,pointer,"desk sleep"),manifest.tuning.deskSleepSeconds);
  assert.equal(number(/static let deepSeconds = ([\d.]+)/,pointer,"deep sleep"),manifest.tuning.deepSleepSeconds);
});

test("light modes, priority and RGB levels match the bridge", () => {
  const chain = bridge.match(/var mode=(.+);\n/)[1];
  const order = [...chain.matchAll(/'([a-z]+)'/g)].map((m) => m[1]);
  assert.deepEqual(manifest.lights.map((light) => light.mode), order, "manifest order is the bridge's priority");
  const wand = createWand({ bridge: "readable" });
  wand.calibrate();
  wand.loadBridge();
  const { ctx } = wand;
  const set = (state) => {
    Object.assign(ctx, { WAND_UPDATING: false, connected: true, calibrationLit: false, scrollHeld: false, moveLatched: false, hudOpen: false, wandRecording: false, wandAppMode: undefined, wandReviewFiles: false, wandDeskSleeping:false }, state);
    ctx.updateLights();
    return wand.colors();
  };
  const states = {
    update: { WAND_UPDATING: true },
    disconnected: { connected: false },
    calibration: { calibrationLit: true },
    sleep:{wandDeskSleeping:true},
    scroll: { scrollHeld: true },
    app: {wandAppMode:"vsCode"},
    mouse: { moveLatched: true },
    hud: { hudOpen: true },
    recording: { wandRecording: true },
    idle: {},
  };
  for (const light of manifest.lights) {
    assert.deepEqual(set(states[light.mode]), light.levels, `${light.mode} levels`);
    assert.match(light.display, /^#[0-9a-f]{6}$/);
  }
  assert.deepEqual(set({wandAppMode:"vsCode",wandReviewFiles:true}), [1,0,1], "file staging is purple");
  for (const button of [...manifest.buttons, ...manifest.chords]) {
    assert(manifest.lights.some((light) => light.mode === button.light), `${button.id} names a real light`);
  }
});

test("HUD start card and wand-adjustable wheels exist in the synced Agentic Mouse labels", () => {
  const hud = JSON.parse(read("data/agentic-mouse-hud.json"));
  const start = hud.cards.find((card) => card.cell === manifest.hud.startCell);
  assert.equal(start.title, "Switch App");
  assert.deepEqual(hud.rows.flat().sort((a, b) => a - b), hud.cards.map((card) => card.cell));
  const wheels = new Set(hud.cards.filter((card) => card.wheel).map((card) => card.wheel.id));
  for (const id of manifest.hud.adjustableWheels) assert(wheels.has(id), `${id} is a Default wheel card`);
});

test("public text never states unmeasured performance", () => {
  const text = readFileSync(new URL("../wand.json", import.meta.url), "utf8").toLowerCase();
  for (const phrase of ["low latency", "zero latency", "maximum accuracy", "pixel-perfect", "battery lasts", "hours of battery"]) {
    assert(!text.includes(phrase), phrase);
  }
});


test("wand Enter is the same plain Enter card the mice use", () => {
  // Ethan retired the wand-only Command-Enter / Steer override (2026-10-20).
  const shared = JSON.parse(read("data/agentic-mouse-hud.json"));
  const generated = JSON.parse(read("docs/data/hud.json"));
  assert.equal(shared.cards.find(card => card.cell === 7).title, "Enter");
  assert.equal(generated.cards.find(card => card.cell === 7).title, "Enter");
  assert.equal(manifest.hud.cardOverrides?.["7"], undefined);
  for (const card of shared.cards) {
    assert.deepEqual(generated.cards.find(value => value.cell === card.cell), card);
  }
});
