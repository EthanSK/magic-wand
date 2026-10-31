import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createHmac } from "node:crypto";

// Builds a bare check executable in a temporary directory; it never opens
// Bluetooth or USB, writes a request into the real support folder, or touches hardware.
test("wireless Sense preparation stays off-main and rejects stale sessions", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-sense-update-"));
  try {
    const source = (name) => fileURLToPath(new URL(`../receiver/Sources/${name}`, import.meta.url));
    copyFileSync(fileURLToPath(new URL("native-sense-preparation-main.swift", import.meta.url)), join(dir, "main.swift"));
    const built = spawnSync("swiftc", ["-O", ...["WandReceiverSenseUpdate.swift", "WandSenseUpdate.swift", "WandSenseProtocol.swift", "WandCalibration.swift", "WandRunLoop.swift"].map(source), join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, "check"), [], { encoding: "utf8", timeout: 60000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    assert.match(run.stdout, /PASS: completion checks fresh battery/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
