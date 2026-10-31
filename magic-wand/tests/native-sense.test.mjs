import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// Builds a bare check executable in a temporary directory; it never posts
// native input, opens a transport or touches hardware.
test("Sense protocol safety and the canonical program in JavaScriptCore", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-sense-"));
  try {
    const source = (name) => fileURLToPath(new URL(`../receiver/Sources/${name}`, import.meta.url));
    copyFileSync(fileURLToPath(new URL("native-sense-main.swift", import.meta.url)), join(dir, "main.swift"));
    const built = spawnSync("swiftc", ["-O", source("WandSenseProtocol.swift"), source("WandSenseUpdate.swift"), source("WandRunLoop.swift"), source("WandCalibration.swift"), source("WandVirtualPuck.swift"), join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const component = fileURLToPath(new URL("..", import.meta.url));
    const run = spawnSync(join(dir, "check"), [component, join(component, "..")], { encoding: "utf8", timeout: 60000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    assert.match(run.stdout, /canonical Puck program boots/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
