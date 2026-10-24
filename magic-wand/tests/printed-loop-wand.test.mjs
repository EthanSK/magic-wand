// Printed loop wand exports (hardware/printed-loop-wand): checks the committed STL, GLB and
// manifest against each other and the current parameters, without the Python geometry toolchain.
// The full geometry rebuild and joint checks run with `python wand_cad.py --check`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const folder = join(dirname(fileURLToPath(import.meta.url)), "..", "hardware", "printed-loop-wand");
const exportsDir = join(folder, "exports");
const manifest = JSON.parse(readFileSync(join(exportsDir, "manifest.json"), "utf8"));
const dimensions = JSON.parse(readFileSync(join(folder, "dimensions.json"), "utf8"));
const sha256 = (buffer) => createHash("sha256").update(buffer).digest("hex");

function readStl(file) {
  const buffer = readFileSync(join(exportsDir, file));
  const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  const count = view.getUint32(80, true);
  assert.equal(buffer.length, 84 + count * 50, `${file} length matches its triangle count`);
  const corners = new Float32Array(count * 9);
  for (let i = 0; i < count; i++) {
    for (let k = 0; k < 9; k++) corners[i * 9 + k] = view.getFloat32(84 + i * 50 + 12 + k * 4, true);
  }
  return { buffer, count, corners };
}

test("exports were built from the current parameters and source", () => {
  assert.equal(manifest.source.dimensions_sha256, sha256(readFileSync(join(folder, "dimensions.json"))));
  assert.equal(manifest.source.script_sha256, sha256(readFileSync(join(folder, "wand_cad.py"))));
  for (const entry of manifest.glb) {
    const glb = readFileSync(join(exportsDir, entry.file));
    assert.equal(sha256(glb), entry.sha256, entry.file);
    assert.equal(glb.readUInt32LE(0), 0x46546c67, `${entry.file} GLB magic`);
  }
});

test("every STL matches the manifest, is closed and fits the reference bed", () => {
  const bed = dimensions.printer_reference.bed;
  const margin = dimensions.printer_reference.margin;
  assert.ok(manifest.parts.length >= 14);
  for (const part of manifest.parts) {
    const { buffer, count, corners } = readStl(part.file);
    assert.equal(sha256(buffer), part.sha256, part.name);
    assert.equal(count, part.mesh.triangles, part.name);
    // Every undirected edge must be shared by exactly two triangles, in opposite directions.
    const ids = new Map();
    const id = (i) => {
      const key = `${corners[i]},${corners[i + 1]},${corners[i + 2]}`;
      if (!ids.has(key)) ids.set(key, ids.size);
      return ids.get(key);
    };
    const edges = new Map();
    let lo = [Infinity, Infinity, Infinity];
    let hi = [-Infinity, -Infinity, -Infinity];
    for (let t = 0; t < count; t++) {
      const v = [id(t * 9), id(t * 9 + 3), id(t * 9 + 6)];
      for (let k = 0; k < 3; k++) {
        const a = v[k];
        const b = v[(k + 1) % 3];
        const key = a < b ? `${a}-${b}` : `${b}-${a}`;
        edges.set(key, (edges.get(key) ?? 0) + (a < b ? 1 : 1000));
      }
      for (let c = 0; c < 9; c++) {
        lo[c % 3] = Math.min(lo[c % 3], corners[t * 9 + c]);
        hi[c % 3] = Math.max(hi[c % 3], corners[t * 9 + c]);
      }
    }
    const open = [...edges.values()].filter((n) => n !== 1001).length;
    assert.equal(open, 0, `${part.name}: ${open} edges not paired`);
    assert.ok(Math.abs(lo[2]) < 1e-3, `${part.name} sits on the bed`);
    hi.forEach((h, axis) => assert.ok(h - lo[axis] <= bed[axis] - 2 * margin, `${part.name} fits the bed`));
  }
});

test("recorded geometry checks passed", () => {
  const { checks } = manifest;
  assert.equal(checks.meshes_passed, true);
  assert.equal(checks.joint.passed, true);
  assert.equal(checks.joint.insertion_at_entry_angle_max_mm3, 0);
  assert.ok(checks.joint.insertable_angles_deg.every((a) => Math.abs(a - checks.joint.entry_angle_deg) <= 4));
  for (const [variant, result] of Object.entries(checks.assembly)) {
    assert.equal(result.passed, true, variant);
    assert.deepEqual(result.unexpected, [], variant);
  }
  const expected = Object.entries(dimensions.profiles).filter(([k]) => k !== "current")
    .flatMap(([profile, spec]) => Object.keys(spec.assemblies).map((key) => `${profile}-${key}`));
  assert.deepEqual(Object.keys(checks.assembly).sort(), expected.sort());
});

test("the no-loop handle shares the joint and uses less material than every loop handle", () => {
  const parts = Object.fromEntries(manifest.parts.map((p) => [p.name, p]));
  const plain = parts["handle-straight"];
  assert.ok(plain, "handle-straight is exported");
  assert.equal(plain.mesh.bodies, 1);
  for (const loop of ["handle-round", "handle-oval", "handle-angled"]) {
    assert.ok(plain.mesh.volume_mm3 < parts[loop].mesh.volume_mm3, loop);
    assert.ok(plain.mesh.print_size_mm[1] < parts[loop].mesh.print_size_mm[1], `${loop} footprint`);
  }
  for (const id of ["xiao-plain", "puck-legacy-straight"]) {
    assert.equal(manifest.checks.assembly[id].opening, null, id);
    assert.ok(Object.values(manifest.checks.assembly[id].wire_probe_overlap_mm3).every((v) => v < 0.01), id);
  }
});

test("the current XIAO profile pairs the mug and plain handles with the open XIAO tip", () => {
  assert.equal(manifest.current_profile, "xiao");
  const profile = manifest.profiles.xiao;
  assert.deepEqual(profile.tip_parts, ["tip-xiao"]);
  assert.deepEqual(profile.components, dimensions.profiles.xiao.components);
  assert.equal(profile.glb, "assembly.glb");
  assert.deepEqual(profile.assemblies, ["xiao-mug", "xiao-plain"]);
  assert.equal(manifest.assemblies["xiao-mug"].label, "Mug handle");
  assert.equal(manifest.assemblies["xiao-plain"].label, "Plain handle (no loop)");
  // Ethan's mug is the full-hand loop, not the small two-finger round loop.
  assert.deepEqual(manifest.assemblies["xiao-mug"].parts, ["handle-oval", "shaft-lower", "shaft-upper", "tip-xiao"]);
  assert.deepEqual(manifest.assemblies["xiao-plain"].parts, ["handle-straight", "shaft-lower", "shaft-upper", "tip-xiao"]);
  const mug = manifest.checks.assembly["xiao-mug"].opening;
  assert.ok(mug.length_mm > 95 && mug.height_mm > 28, `mug opening ${mug.length_mm} × ${mug.height_mm} mm`);
  assert.ok(mug.area_mm2 > 2 * manifest.checks.assembly["puck-legacy-round"].opening.area_mm2);
  for (const id of profile.assemblies) {
    const parts = manifest.assemblies[id].parts;
    assert.ok(!parts.some((p) => /puck|cradle|cap/.test(p)), `${id} has no Puck parts`);
    assert.ok(!parts.some((p) => p.startsWith("button-pod")), `${id} has no button pod`);
    assert.ok(!Object.keys(manifest.checks.assembly[id].overlaps_mm3).some((pair) => pair.includes("pod")), `${id} checks no pod`);
    const overlaps = manifest.checks.assembly[id].overlaps_mm3;
    for (const [pair, v] of Object.entries(overlaps)) {
      if (/xiao-(board|components)/.test(pair)) assert.equal(v, 0, `${id}: ${pair}`);
    }
  }
  const tip = manifest.parts.find((p) => p.name === "tip-xiao");
  assert.equal(tip.profile, "xiao");
  assert.equal(tip.mesh.bodies, 1);
  // The legacy Puck profile and its parts remain available.
  assert.deepEqual(manifest.profiles["puck-legacy"].tip_parts, ["tip-cradle", "tip-cap"]);
  for (const id of manifest.profiles["puck-legacy"].assemblies) {
    assert.ok(manifest.assemblies[id].parts.includes("button-pod-pilot"), `${id} keeps its button pod`);
  }
  assert.equal(manifest.layout.xiao.board_size[0], dimensions.xiao_tip.board_width);
  assert.equal(manifest.layout.xiao.board_size[2], dimensions.xiao_tip.board_length);
});

test("printable meshes stay byte-identical across profile changes", () => {
  // Changing which parts a profile assembles must not regenerate any printable part.
  const pinned = {
    "coupon-male.stl": "738b2fdc928b0f0a", "coupon-female-a.stl": "98e37c7f8007d801",
    "coupon-female-b.stl": "2c77b8b12a2a4dbf", "coupon-female-c.stl": "1aebf42e865d2cb2",
    "coupon-puck-ring.stl": "685850b7f83fdc42", "handle-round.stl": "25a4b131c066c4d7",
    "handle-oval.stl": "4cdf65278dd0d790", "handle-angled.stl": "e34b1664c26ceacc",
    "handle-straight.stl": "9ced549dd21b4b09", "shaft-lower.stl": "701d244fb58425a0",
    "shaft-upper.stl": "71eed26fcdb41e03", "tip-cradle.stl": "770b8b5da61882db",
    "tip-cap.stl": "959da4a6d81e175e", "tip-xiao.stl": "35bc25a06cabf68e",
    "button-pod-pilot.stl": "345900f62cfbe16e", "button-pod-blank.stl": "b879529561350331",
  };
  for (const file of Object.keys(pinned)) assert.ok(manifest.parts.some((p) => p.file === file), `${file} remains exported`);
  for (const [file, prefix] of Object.entries(pinned)) {
    assert.equal(sha256(readFileSync(join(exportsDir, file))).slice(0, 16), prefix, file);
  }
});

test("the tapered profile preserves a continuous body, two ribs, and a wired thumb shelf", () => {
  const profile = manifest.profiles["tapered-xiao"];
  assert.equal(profile.joint_kind, "mirrored");
  assert.deepEqual(profile.assemblies, ["tapered-xiao-spiral", "tapered-xiao-smooth"]);
  const { tapered, tapered_joint: joint } = manifest.checks;
  assert.equal(tapered.passed, true);
  assert.equal(joint.passed, true);
  assert.ok(joint.entry_angle_deg > 0, "preview must use the mirrored entry direction");
  const radii = Object.values(tapered.radius_mm).slice(0, 4);
  assert.ok(radii.every((r, i) => i === 0 || r < radii[i - 1]), "body gets thinner towards the tip");
  assert.ok(Object.values(tapered.seam_max_radius_step_mm).every((r) => r < 0.2), "no handle bulge at the joins");
  for (const peaks of Object.values(tapered.rib_peaks_deg)) {
    assert.equal(peaks.length, 2);
    assert.ok(Math.abs(peaks[1] - peaks[0] - 180) < 6);
  }
  assert.equal(tapered.thumb_shelf.mirrors_exactly, true);
  assert.equal(tapered.thumb_shelf.hand, "both");
  assert.ok(tapered.thumb_shelf.width_mm > 50 && tapered.thumb_shelf.width_mm < 56);
  assert.ok(tapered.thumb_shelf.reach_minus_x_mm > tapered.radius_mm.handle_face + 10);
  assert.ok(tapered.thumb_shelf.reach_plus_x_mm > tapered.radius_mm.handle_face + 10);
  for (const [style, zones] of Object.entries(tapered.thumb_shelf.flat_top_zones)) {
    assert.deepEqual(Object.keys(zones), ["left", "centre", "right"], style);
    for (const [zone, v] of Object.entries(zones)) {
      assert.ok(v.below_mm3 > 0.199 && v.above_mm3 < 0.001, `${style} ${zone}: same flat top plane`);
    }
  }
  assert.ok(Object.values(tapered.spiral_extra_mm3).every((v) => v > 0));
  for (const id of profile.assemblies) {
    const a = manifest.assemblies[id];
    assert.equal(a.parts.length, 4);
    assert.ok(a.parts.includes("tip-xiao"));
    assert.ok(!a.parts.some((p) => p.includes("button-pod")));
    assert.equal(manifest.checks.assembly[id].opening, null, "no mug loop on the continuous wand");
    assert.ok(Object.values(manifest.checks.assembly[id].wire_probe_overlap_mm3).every((v) => v < 0.01));
  }
});
