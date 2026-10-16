// Repository-level checks, so `node --test tests/` covers everything: generated files are fresh,
// vendored files match their lock, the privacy and website checks pass, and the 3D framing works.
import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as THREE from "../docs/lib/three-0.185.1/three.module.min.js";
import { buildRig, makeCamera, RIG } from "../docs/wand-scene.mjs";

const root = fileURLToPath(new URL("..", import.meta.url));
const python = (script, ...args) => spawnSync("python3", ["-I", script, ...args], { cwd: root, encoding: "utf8" });

for (const [script, args] of [["scripts/build.py", ["--check"]], ["scripts/vendor.py", ["--check"]], ["scripts/check.py", []]]) {
  test(`${script} ${args.join(" ")}`.trim(), () => {
    const result = python(script, ...args);
    assert.equal(result.status, 0, result.stdout + result.stderr);
  });
}

test("the website names every manifest button and keeps the demo boundary", () => {
  const html = readFileSync(new URL("../docs/index.html", import.meta.url), "utf8");
  const manifest = JSON.parse(readFileSync(new URL("../wand.json", import.meta.url), "utf8"));
  for (const button of manifest.buttons) {
    assert.match(html, new RegExp(`data-button="${button.id}"[^>]*aria-keyshortcuts="${button.key}"`));
    assert(html.includes(`<span class="pin">${button.pin}</span>`));
  }
  assert(html.includes("Nothing connects to a wand, Bluetooth or your Mac."));
  assert(!/\bwhether\b/i.test(html), "Ethan’s wording rule: never use “whether”");
  assert(!/\bwhether\b/i.test(JSON.stringify(manifest)));
});

test("the 3D wand keeps its tip in view across the whole aim range", () => {
  for (const aspect of [1.75, 1.25, 1.0]) {
    const camera = makeCamera(THREE, aspect);
    camera.updateMatrixWorld();
    const rig = buildRig(THREE);
    const tip = (yaw, pitch) => { rig.setAim(yaw, pitch); return rig.tipWorld().clone().project(camera); };
    for (const yaw of [-24, 0, 24]) {
      for (const pitch of [-18, 0, 18]) {
        const point = tip(yaw, pitch);
        assert(Math.abs(point.x) < 0.95 && Math.abs(point.y) < 0.95, `tip visible at ${yaw}, ${pitch} (aspect ${aspect})`);
      }
    }
    assert(tip(24, 0).x > tip(0, 0).x && tip(0, 0).x > tip(-24, 0).x, "turning right moves the tip right");
    assert(tip(0, 18).y < tip(0, 0).y && tip(0, 0).y < tip(0, -18).y, "turning down moves the tip down");
    const centre = tip(0, 0);
    assert(centre.y < -0.35 && centre.y > -0.75, "at rest the tip sits low, under the simulated screen");
    const hand = new THREE.Vector3(...RIG.pivot).project(camera);
    assert(hand.y < -0.85, "the grip enters from the bottom edge");
  }
});

test("pressing a grip button lowers its cap", () => {
  const rig = buildRig(THREE);
  const rest = rig.buttons.bottom.mesh.position.y;
  rig.setPressed({ bottom: true, middle: false, top: false });
  assert(rig.buttons.bottom.mesh.position.y < rest);
  assert.equal(rig.buttons.middle.mesh.position.y, rest);
});
