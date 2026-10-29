import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

// Opening the receiver's menu-bar menu must not stop the Sense heartbeat (the
// board ends its session after 2 s without one, showing orange).
test("Sense link supervision runs while a menu is tracked", { skip: process.platform !== "darwin" }, () => {
  const link = readFileSync(new URL("../receiver/Sources/WandSenseLink.swift", import.meta.url), "utf8");
  assert.match(link, /tick = WandRunLoop\.commonTimer\(/, "the heartbeat/supervision tick uses the common-mode timer");
  assert.doesNotMatch(link, /Timer\.scheduledTimer/, "no default-mode timer owns the Sense link");
  const receiver = readFileSync(new URL("../receiver/Sources/main.swift", import.meta.url), "utf8");
  assert.doesNotMatch(receiver, /Timer\.scheduledTimer/, "recording refresh, clicks, held-button safety and gesture deadlines also survive menu tracking");
  const dir = mkdtempSync(join(tmpdir(), "wand-runloop-"));
  try {
    copyFileSync(fileURLToPath(new URL("native-runloop-main.swift", import.meta.url)), join(dir, "main.swift"));
    const source = fileURLToPath(new URL("../receiver/Sources/WandRunLoop.swift", import.meta.url));
    const built = spawnSync("swiftc", ["-Onone", source, join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, "check"), [], { encoding: "utf8", timeout: 30000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    assert.match(run.stdout, /heartbeat survives menu tracking/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
