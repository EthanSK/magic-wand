import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

test("Switch App winding continues the chosen direction and HUD terminals arrive in order", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-switch-winding-"));
  try {
    const source = (name) => fileURLToPath(new URL(`../receiver/Sources/${name}`, import.meta.url));
    copyFileSync(fileURLToPath(new URL("native-switch-winding-main.swift", import.meta.url)), join(dir, "main.swift"));
    const built = spawnSync("swiftc", ["-O", source("WandPointerControl.swift"), source("WandControlTransport.swift"), join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, "check"), [], { encoding: "utf8", timeout: 30000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    assert.match(run.stdout, /motion is never queued/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
