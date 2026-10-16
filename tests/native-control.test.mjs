import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { PointerRouter } from "../docs/sim/pointer.mjs";
test("optional zero-buffer LOW motion has no delay or release replay", () => {
  const router = new PointerRouter({lowDelay:0});
  router.bottom(true);
  assert.deepEqual(router.frame(4, 3, 0, false, 10).actions, [{type: "move", dx: 4, dy: 3}]);
  assert.equal(router.nextDue, undefined);
  router.bottom(false);
  assert.deepEqual(router.drain(11), []);
  assert.equal(router.frame(0, 0, 1, false, 11).buttons, 1);
});
test(
  "native held-only buffering, immediate HIGH, rough loops, dwell, desk detection and review lifecycle",
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


test("held-only 90 ms buffer discards release flick but bypasses HIGH and dragging", () => {
 const r=new PointerRouter({lowDelay:0.09});r.bottom(true);
 assert.deepEqual(r.frame(4,3,0,false,10).actions,[]);
 assert.deepEqual(r.drain(10.08),[]);
 assert.deepEqual(r.drain(10.1),[{type:"move",dx:4,dy:3}]);
 r.frame(0,-50,0,false,11);r.bottom(false);
 assert.deepEqual(r.drain(12),[]);
 assert.deepEqual(r.frame(8,0,0,false,12).actions,[{type:"move",dx:8,dy:0}]);
 r.bottom(true);
 assert.deepEqual(r.frame(8,0,1,false,13).actions,[{type:"move",dx:8,dy:0}]);
 assert.deepEqual(r.frame(0,8,0,true,14).actions,[{type:"move",dx:0,dy:8}]);
});
