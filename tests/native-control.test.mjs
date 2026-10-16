import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
test(
  "native rough loops, release jolt buffer, dwell, desk detection and review lifecycle",
  { skip: process.platform !== "darwin" },
  () => {
    const dir = mkdtempSync(join(tmpdir(), "wand-controls-"));
    try {
      const source = fileURLToPath(
        new URL(
          "../receiver/Sources/WandPointerControl.swift",
          import.meta.url,
        ),
      );
      const main = fileURLToPath(
        new URL("native-control-main.swift", import.meta.url),
      );
      // Swift requires the top-level executable source to be named main.swift.
      const copy = spawnSync("cp", [main, join(dir, "main.swift")], {
        encoding: "utf8",
      });
      assert.equal(copy.status, 0, copy.stderr);
      const built = spawnSync(
        "swiftc",
        ["-O", source, join(dir, "main.swift"), "-o", join(dir, "check")],
        { encoding: "utf8" },
      );
      assert.equal(built.status, 0, built.stderr);
      const run = spawnSync(
        join(dir, "check"),
        [fileURLToPath(new URL("rough-motion-fixtures.json", import.meta.url))],
        { encoding: "utf8" },
      );
      assert.equal(run.status, 0, run.stderr + run.stdout);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  },
);
