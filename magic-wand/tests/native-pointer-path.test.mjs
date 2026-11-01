// Runs inert pointer-math and click-isolation regressions; never sends live input.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// Bare check executable in a temporary directory: pointer maths only, no native input.
test("direct Sense pointer retains slow motion, separate click evidence, units, axes and held gain", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-pointer-path-"));
  try {
    copyFileSync(fileURLToPath(new URL("native-pointer-path-main.swift", import.meta.url)), join(dir, "main.swift"));
    const source = fileURLToPath(new URL("../receiver/Sources/WandPointerControl.swift", import.meta.url));
    const built = spawnSync("swiftc", ["-O", source, join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, "check"), [], { encoding: "utf8", timeout: 30000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    assert.match(run.stdout, /tuned path unchanged/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

// Ethan's jump-back reports (2026-10-30) turned off repeats; the jumps were a
// cursor-origin defect. Ethan (2026-11-01) asked again: "if I haven't moved at
// all, then it should repeat the click". The Sense session repeats every
// 300 ms; the dwell is constructed single-shot, so the Puck stays single-shot.
test("Sense stop-to-click repeats every 300 ms; the Puck stays single-shot", () => {
  const main = readFileSync(fileURLToPath(new URL("../receiver/Sources/main.swift", import.meta.url)), "utf8");
  const constructor = main.match(/\blet dwell\s*=\s*WandDwellClick\(([^)]*)\)/);
  assert.ok(constructor, "the live receiver creates its ordinary dwell controller");
  assert.doesNotMatch(constructor[1], /\brepeatInterval\s*:/, "the shared constructor stays single-shot for the Puck");
  const sense = readFileSync(fileURLToPath(new URL("../receiver/Sources/WandReceiverSense.swift", import.meta.url)), "utf8");
  assert.match(sense, /dwell\.repeatInterval = WandDwellClick\.senseRepeatInterval/);
  assert.match(sense, /dwell\.repeatInterval = nil/);
  const control = readFileSync(fileURLToPath(new URL("../receiver/Sources/WandPointerControl.swift", import.meta.url)), "utf8");
  assert.match(control, /static let senseRepeatInterval=0\.3\b/);
});
