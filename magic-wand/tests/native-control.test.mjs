import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { PointerRouter, DwellClick } from "../../docs/sim/pointer.mjs";
test("optional zero-buffer LOW motion has no delay or release replay", () => {
  const router = new PointerRouter({lowDelay:0});
  router.mouseButton(true);
  assert.deepEqual(router.frame(4, 3, 0, false, 10).actions, [{type: "move", dx: 4, dy: 3}]);
  assert.equal(router.nextDue, undefined);
  router.mouseButton(false);
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
 const r=new PointerRouter({lowDelay:0.09});r.mouseButton(true);
 assert.deepEqual(r.frame(4,3,0,false,10).actions,[]);
 assert.deepEqual(r.drain(10.08),[]);
 assert.deepEqual(r.drain(10.1),[{type:"move",dx:4,dy:3}]);
 r.frame(0,-50,0,false,11);r.mouseButton(false);
 assert.deepEqual(r.drain(12),[]);
 assert.deepEqual(r.frame(8,0,0,false,12).actions,[{type:"move",dx:8,dy:0}]);
 r.mouseButton(true);
 assert.deepEqual(r.frame(8,0,1,false,13).actions,[{type:"move",dx:8,dy:0}]);
 assert.deepEqual(r.frame(0,8,0,true,14).actions,[{type:"move",dx:0,dy:8}]);
});


test("recognized scrolling keeps the pointer locked through pauses and straight motion until release", () => {
 const r=new PointerRouter();r.mouseButton(true);let x=80,y=0;
 for(let i=1;i<=105;i++){const a=i/35*Math.PI*2,nx=80*Math.cos(a),ny=80*Math.sin(a);r.frame(Math.round(nx-x),Math.round((ny-y)*1.4),0,false,10+i/35);x=nx;y=ny;}
 assert(r.circle.active);
 assert.deepEqual(r.tick(16),[]);
 for(let i=0;i<100;i++)assert(!r.frame(8,0,0,false,17+i/35).actions.some(a=>a.type==='move'));
 assert(r.circle.active);
 assert.deepEqual(r.mouseButton(false),[{type:'light',on:false}]);
 assert.equal(r.frame(0,0,1,false,21).buttons,0,'no click after scrolling');
 assert(r.frame(4,0,0,false,22).actions.some(a=>a.type==='move'));
});

test("HIGH clicks after 200 ms rest, but not during slow motion or twice at rest", () => {
 const d=new DwellClick();d.follow(true);
 assert.equal(d.tick(1),false);
 d.move(20,0,10,true);
 assert.equal(d.tick(10.199),false);
 assert.equal(d.tick(10.201),true);
 assert.equal(d.tick(11),false);
 d.move(1,0,12,true);assert.equal(d.tick(13),false);
 d.move(20,0,20,true);d.intent(true,20.1);
 assert.equal(d.tick(20.4),false);
 d.intent(false,20.5);d.intent(false,20.6);
 assert.equal(d.tick(20.699),false);assert.equal(d.tick(20.701),true);
 d.move(20,0,30,true);d.move(1,0,30.15,true);
 assert.equal(d.tick(30.201),false);assert.equal(d.tick(30.351),true);
 d.move(20,0,40,true);d.follow(false);assert.equal(d.tick(41),false);
});
