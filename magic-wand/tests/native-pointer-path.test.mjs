import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

// Bare check executable in a temporary directory: pointer maths only, no native input.
test("direct Sense pointer keeps normal motion, quiet stopping, units, axes and held gain", { skip: process.platform !== "darwin" }, () => {
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
