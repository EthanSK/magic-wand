import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, copyFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

// Builds the panel logic with the generated guide; no window is opened.
test("wand guide content, placement, agent requests and close choice", { skip: process.platform !== "darwin" }, () => {
  const dir = mkdtempSync(join(tmpdir(), "wand-guide-"));
  try {
    copyFileSync(fileURLToPath(new URL("native-guide-main.swift", import.meta.url)), join(dir, "main.swift"));
    const source = fileURLToPath(new URL("../receiver/Sources/WandGuidePanel.swift", import.meta.url));
    const built = spawnSync("swiftc", ["-Onone", source, join(dir, "main.swift"), "-o", join(dir, "check")], { encoding: "utf8" });
    assert.equal(built.status, 0, built.stderr);
    const guide = fileURLToPath(new URL("../device/generated/wand-guide.json", import.meta.url));
    const run = spawnSync(join(dir, "check"), [guide], { encoding: "utf8", timeout: 30000 });
    assert.equal(run.status, 0, run.stderr + run.stdout);
    assert.match(run.stdout, /visibility and saved choice/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
