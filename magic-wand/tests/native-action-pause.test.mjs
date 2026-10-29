import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// Bare check executable in a temporary directory: no native input, listener or hardware.
test("debug pause blocks every lane, resumes only fresh presses and accepts only private requests", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-pause-"));
  try {
    const source = (name) => fileURLToPath(new URL(`../receiver/Sources/${name}`, import.meta.url));
    copyFileSync(fileURLToPath(new URL("native-action-pause-main.swift", import.meta.url)), join(dir, "main.swift"));
    const built = spawnSync("swiftc", [source("WandActionPause.swift"), source("WandControlTransport.swift"), join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, "check"), [], { encoding: "utf8", timeout: 30000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    assert.match(run.stdout, /suspended transport refuses/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
