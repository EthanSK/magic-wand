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
  const glb = readFileSync(join(exportsDir, manifest.glb.file));
  assert.equal(sha256(glb), manifest.glb.sha256);
  assert.equal(glb.readUInt32LE(0), 0x46546c67, "GLB magic");
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
  assert.deepEqual(Object.keys(checks.assembly).sort(), Object.keys(dimensions.handle.variants).sort());
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
  assert.equal(manifest.checks.assembly.straight.opening, null);
  assert.ok(Object.values(manifest.checks.assembly.straight.wire_probe_overlap_mm3).every((v) => v < 0.01));
});
