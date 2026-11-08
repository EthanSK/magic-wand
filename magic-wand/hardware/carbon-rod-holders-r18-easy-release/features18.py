#!/usr/bin/env python3
"""Short features the broad-overhang detector cannot see: read directly from actual G-code beads, per layer."""
import json, numpy as np, trimesh
import holder18 as h
import slice16 as s16
q = s16.q; OUT = h.HERE / 'exports'


def layers(data, offset, parts, name):
    exp = trimesh.load_mesh(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); info = parts[name]; place = (info['vertices'].min(0) + info['vertices'].max(0) - exp.bounds.sum(0)) / 2; local = data[:, :3] + offset - place; lo, hi = exp.bounds; m = np.all(local >= lo - .4, 1) & np.all(local <= hi + .4, 1); return local[m], data[m, 3], data[m, 7], exp


def probe(pts, wd, tops, x0, x1, y0, y1, zlo):
    out = {}
    for t in sorted({round(float(v), 3) for v in tops if v > zlo}):
        sel = abs(tops - t) < 1e-3; b = q.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0)) ^ s16.start_audit.bead_footprints(q, pts[sel, :2], wd[sel])
        if b.area() > .01: out[t] = round(b.area(), 3)
    return out


def main():
    project = OUT / 'R18-A1-mini-PETG.gcode.3mf'; data, _, _, _, offset, parts, _, _ = s16.read_project(project); m = json.loads((OUT / 'manifest.json').read_text()); rep = {'project_sha256': h.sha(project), 'checker_sha256': h.sha(h.HERE / 'features18.py')}
    def box_print(name, lo, hi):
        pa = np.linalg.inv(np.array(m['parts'][name]['print_to_assembly'])); c = np.array([[a, b, c_] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c_ in (lo[2], hi[2])]); p = q.points(c, pa); return p.min(0), p.max(0)
    D = h.D; hw = D['tooth_half_x_mm']; pts, wd, tops, _ = layers(data, offset, parts, 'Battery_End_Door'); lo, hi = box_print('Battery_End_Door', (-hw, D['y_mm'][1], 10.85), (hw, max(p[0] for p in D['tooth_yz_mm']), 11.45)); rep['door_tooth_area_by_layer_top_mm2'] = probe(pts, wd, tops, lo[0], hi[0], lo[1], hi[1], lo[2]); assert sum(k > 1.65 for k in rep['door_tooth_area_by_layer_top_mm2']) >= 3, rep
    lo, hi = box_print('Battery_End_Door', (D['tongue_root_x_mm'], D['y_mm'][0], 10.45), (D['tongue_tip_x_mm'] - .1, D['y_mm'][1], 12.2)); rep['door_tongue_layers_with_beads'] = len(probe(pts, wd, tops, lo[0], hi[0], lo[1], hi[1], 0.)); assert rep['door_tongue_layers_with_beads'] >= 7
    T = h.K['tongue']; pts, wd, tops, _ = layers(data, offset, parts, 'XIAO_Near_Keeper'); (a, b), (c, d_), e = T['tooth_x_mm'], T['tooth_y_mm'], T['tooth_bottom_z_mm']; lo, hi = box_print('XIAO_Near_Keeper', (a, c, e), (b, d_, T['thin_from_z_mm'])); rep['keeper_tooth_area_by_layer_top_mm2'] = probe(pts, wd, tops, lo[0], hi[0], lo[1], hi[1], lo[2]); assert len(rep['keeper_tooth_area_by_layer_top_mm2']) >= 4
    (x0, x1), (y0, y1) = T['x_mm'], T['y_mm']; lo, hi = box_print('XIAO_Near_Keeper', (x0 + .2, y0 + .1, T['thin_from_z_mm']), (x1 - .2, y1 - .1, h.RET['plate_z_mm'][1])); rep['keeper_tongue_first_layer_area_mm2'] = probe(pts, wd, tops, lo[0], hi[0], lo[1], hi[1], 0.).get(.2); assert rep['keeper_tongue_first_layer_area_mm2'] and rep['keeper_tongue_first_layer_area_mm2'] > 12
    rep['physical_print_verified'] = False; (OUT / 'short-features.json').write_text(json.dumps(rep, indent=2) + '\n'); print(json.dumps(rep), flush=True)


if __name__ == '__main__':
    main()
