import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// Ethan (2026-10-31): the physical button release is the boundary; drop obsolete
// pre-release motion rather than waiting for or replaying it. The receiver's own
// senseLine routes synthetic frames into the canonical program in JavaScriptCore,
// and its @RAW output goes through the real pointer filter. The frozen-150 routing
// is built alongside as the failing reference. A bare executable in a temporary
// directory: no transport, hardware or native input.
test("Sense release frames never replay obsolete stroke motion into the pointer", { skip: process.platform !== "darwin" }, (t) => {
  const source = (name) => fileURLToPath(new URL(`../receiver/Sources/${name}`, import.meta.url));
  const sense = readFileSync(source("WandReceiverSense.swift"), "utf8");
  const start = sense.indexOf("    func senseLine(");
  assert(start >= 0, "senseLine");
  let end = sense.indexOf("{", start) + 1, depth = 1;
  while (depth) { if (sense[end] === "{") depth++; if (sense[end] === "}") depth--; end++; }
  const fixed = sense.slice(start, end);
  const policy = /\/\/ This frame's own mask is the physical boundary[\s\S]*?screenshot: screenshot\.ownsPointer\)/;
  assert.match(fixed, policy, "the frame-mask policy is the routing under test");
  const original = fixed.replace(policy, "let dropLate = dwell.following && !hudSession && !scrollActive && !heldScroll.active &&\n                !pointerRouter.mouseButtonHeld && !screenshot.ownsPointer");
  const main = readFileSync(new URL("native-sense-release-frames-main.swift", import.meta.url), "utf8");
  const component = fileURLToPath(new URL("..", import.meta.url));
  const results = {};
  for (const [name, body] of [["fixed", fixed], ["original", original]]) {
    const dir = mkdtempSync(join(tmpdir(), "wand-release-frames-"));
    try {
      writeFileSync(join(dir, "main.swift"), main.replace("/*SENSE_LINE*/", body));
      const built = spawnSync("swiftc", ["-O", source("WandSenseProtocol.swift"), source("WandSenseUpdate.swift"), source("WandRunLoop.swift"),
        source("WandCalibration.swift"), source("WandVirtualPuck.swift"), source("WandActionPause.swift"), source("WandPointerControl.swift"),
        join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
      assert.equal(built.status, 0, built.stderr);
      const run = spawnSync(join(dir, "check"), [component, join(component, "..")], { encoding: "utf8", timeout: 60000 });
      assert.equal(run.status, 0, name + ": " + run.stderr + run.stdout);
      assert.match(run.stdout, /DONE/);
      results[name] = Object.fromEntries([...run.stdout.matchAll(/^RESULT (\w+) (.*)$/gm)].map((m) => [m[1], JSON.parse(m[2])]));
    } finally { rmSync(dir, { recursive: true, force: true }); }
  }
  t.diagnostic(JSON.stringify(results));
  const { fixed: f, original: o } = results;
  // Merged run containing the release.
  assert.ok(o.merged.obsoleteRaw > 0 && o.merged.obsoleteCounts > 100,
    `reference: the replayed release run reaches the pointer after the release (${JSON.stringify(o.merged)})`);
  assert.equal(f.merged.obsoleteRaw, 0, `no @RAW from a release-containing merged run (${JSON.stringify(f.merged)})`);
  assert.equal(f.merged.obsoleteCounts, 0);
  assert.equal(f.merged.heldReplayed, 4, "a held merged run keeps every reading for the scroll");
  assert.equal(o.merged.heldReplayed, 4);
  // Fresh post-release motion resumes at the first reading after the existing
  // 70 ms switch settle, with a filter reset; nothing extra waits.
  assert.ok(f.merged.firstFreshMs >= 70 && f.merged.firstFreshMs < 70 + 1000 / 104 + 2, `fresh motion at the first post-settle reading (${f.merged.firstFreshMs} ms)`);
  assert.ok((f.merged.firstFreshFlags & 2) !== 0 && (f.merged.firstFreshFlags & 1) === 0, "first fresh report resets the filter and is unheld");
  assert.ok(f.merged.freshCounts > 0, "fresh post-release motion moves the pointer");
  // Late post-release backlog delivered with the release.
  assert.ok(o.batch.expectedAllPastPause > o.batch.expectedFreshPastPause, `scenario has late readings past the pause (${JSON.stringify(o.batch)})`);
  assert.equal(o.batch.batchRaw, o.batch.expectedAllPastPause, `reference replays late post-release readings (${JSON.stringify(o.batch)})`);
  assert.equal(o.batch.staleDropped, 0);
  assert.equal(f.batch.batchRaw, f.batch.expectedFreshPastPause, `only readings within the stale limit reach the pointer (${JSON.stringify(f.batch)})`);
  assert.equal(f.batch.staleDropped, f.batch.expectedStale, "late readings are counted as dropped, as in ordinary follow");
  assert.ok(f.batch.batchCounts < o.batch.batchCounts);
});
