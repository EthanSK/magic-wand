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
test("wireless Sense update: package, preflight, authorization, legacy DFU and flow", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-sense-update-"));
  try {
    const source = (name) => fileURLToPath(new URL(`../receiver/Sources/${name}`, import.meta.url));
    copyFileSync(fileURLToPath(new URL("native-sense-update-main.swift", import.meta.url)), join(dir, "main.swift"));
    const built = spawnSync("swiftc", ["-O", ...["WandSenseUpdate.swift", "WandSenseProtocol.swift", "WandCalibration.swift", "WandRunLoop.swift"].map(source), join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const run = spawnSync(join(dir, "check"), [], { encoding: "utf8", timeout: 60000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    for (const pass of ["packages are", "legacy DFU completes", "preflight fails closed", "authorization, key store", "the update flow confirms", "session ordering and explicit reconciliation", "reviewed single-bank versions"]) assert.match(run.stdout, new RegExp(`PASS: ${pass}`));
    // The receiver signs exactly what the firmware verifies (sense-update.test.mjs uses this vector against C++).
    const key = Buffer.from([...Array(32).keys()]);
    const expected = createHmac("sha256", key).update("wand-sense-update-1|1a2b3c4d5e6f7081|00112233445566778899aabbccddeeff|7|132472|3849").digest("hex");
    assert.match(run.stdout, new RegExp(`TAG ${expected}`));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
