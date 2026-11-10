#!/usr/bin/env python3
"""Tear-off bed pads for the four R20 objects: the R19 recipe, each pad on a 1.0 x 0.4 mm tie.

Battery and XIAO keep their R19 sites. The key holder gets four on its slab edge. The guard's four sit inside
the V on the wings' inner faces, so no tie stub is left where a finger rests. No pad may reach a rod ring.
"""
import sys
sys.dont_write_bytecode = True
import json
import numpy as np, trimesh, manifold3d as mf
import holder20 as h
sys.path.insert(0, str(h.R19))
import anchors19  # noqa: E402

A = h.LOCAL['anchors']; rect = h.rect; OUT = h.HERE / 'exports'
assert all(A[k] == anchors19.A[k] for k in anchors19.A), 'R20 uses the R19 pad recipe'


def column(section, x):
    """Printed pieces of the first layer on the vertical line at print X, lowest first, as (y0, y1)."""
    b = section.bounds(); strip = section ^ rect(x - .01, x + .01, b[1] - 1, b[3] + 1)
    return sorted((p.bounds()[1], p.bounds()[3]) for p in strip.decompose() if p.area() > 1e-4)


def sites(name, section, rod_x):
    """(print X, print Y, outward x, outward y) for each tie."""
    b = section.bounds()
    if name == 'Battery_Holder': return [(rod_x + x, y, nx, ny) for x, y, nx, ny in anchors19.SITES[name]]
    if name == 'XIAO_Rod_Holder': return [(rod_x + x, y, nx, ny) for x, y, nx, ny in anchors19.xiao_sites(section)]
    out = []
    for x, where, nx, ny in A['sites_assembly_x_print_y_outward'][name]:
        if isinstance(x, str):       # 'bay1' / '-bay2': centre of that guard window bay, at mid wing thickness
            ua, ub = h.frame()['bays'][int(x[-1])]; x = (-1 if x.startswith('-') else 1) * h.wing_point((ua + ub) / 2, 0.)[0]
        cols = column(section, rod_x + x); assert cols, (name, x, 'no plastic on this line')
        y = {'slab_top': cols[-1][1], 'slab_bottom': cols[-1][0], 'wing_inner': cols[0][1]}[where]; out.append((rod_x + x, y, nx, ny))
    return out


def plan(name, section, rod_x):
    w, o, g, L, d, T = A['tie_width_mm'] / 2, A['tie_overlap_mm'], A['gap_mm'], A['pad_half_length_mm'], A['pad_depth_mm'], A['pull_tab_length_mm']; necks, pads = [], []; where = sites(name, section, rod_x)
    for x, y, nx, ny in where:
        def r(a, b, half):
            p = (x + nx * a, y + ny * a, x + nx * b, y + ny * b)
            return rect(min(p[0], p[2]), max(p[0], p[2]), y - half, y + half) if nx else rect(x - half, x + half, min(p[1], p[3]), max(p[1], p[3]))
        necks.append(r(-o, g + o, w)); pads.append(r(g, g + d, L) + r(g + d - .1, g + d + T, 2.5))
    return dict(sites=where, necks=necks, pads=pads, axes=['x' if s[2] else 'y' for s in where])


def anchor(name):
    record = json.loads((OUT / 'manifest.json').read_text())['parts'][name]; lo = record['bounds_mm'][0]; rod = (-lo[0], -lo[2])     # rod axis in the print plan
    part = h.read(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); section = part.slice(.1); p = plan(name, section, rod[0])
    outline = mf.CrossSection([q for q in section.to_polygons() if anchors19.area(q) > 0]) + mf.CrossSection.circle(5.4, 96).translate(rod)
    flange = mf.CrossSection.batch_boolean(p['pads'], mf.OpType.Add).offset(-.6, mf.JoinType.Round).offset(.6, mf.JoinType.Round) - outline.offset(A['gap_mm'], mf.JoinType.Round)
    shape = (flange + mf.CrossSection.batch_boolean(p['necks'], mf.OpType.Add)).simplify(.01); solid = mf.Manifold.extrude(shape, A['thickness_mm'])
    for body in solid.decompose(): assert any((n ^ body.slice(.1)).area() > .1 for n in p['necks']), (name, 'pad without a tie')
    ring = mf.CrossSection.circle(h.BORE + .3, 64).translate(rod); assert (shape ^ ring).area() < 1e-6, (name, 'pad or tie inside a rod bore')
    return solid, flange, p, section, {'thickness_mm': A['thickness_mm'], 'flange_area_mm2': round(flange.area(), 2), 'tie_section_each_mm2': round(A['tie_width_mm'] * A['thickness_mm'], 3), 'tie_count': len(p['necks']), 'separate_pads': len(solid.decompose()),
                                       'solid_PETG_g': round(solid.volume() / 1000 * 1.27, 4), 'first_layer_area_mm2': round(section.area(), 2), 'rod_axis_print_xy': [round(v, 3) for v in rod], 'sites_print_xy_outward': p['sites'], 'tie_sites': anchors19.tie_sites_report(name, part, section, p)}


def main():
    rec = {}
    for name in h.ANCHORED:
        solid, _, _, _, r = anchor(name); t = OUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl')
        limit = 3. if name == 'Finger_Guard' else .25      # the guard's ties stand on a sloped wing, reached from above inside the V
        for row in r['tie_sites']: assert row['part_volume_in_cutter_corridor_mm3'] < limit, (name, 'cutter corridor blocked', row)
        h.mesh(solid).export(t); assert trimesh.load_mesh(t).is_watertight; r['stl_sha256'] = h.sha(t); rec[name] = r
    r19 = json.loads((h.R19 / 'exports/anchors.json').read_text())['parts']
    same = {n: bool(abs(rec[n]['flange_area_mm2'] - r19[n]['flange_area_mm2']) < .01 and np.allclose(np.array(rec[n]['sites_print_xy_outward'], float), np.array(r19[n]['sites_print_xy_outward'], float), atol=1e-6)) for n in ('Battery_Holder', 'XIAO_Rod_Holder')}; assert all(same.values()), same
    (OUT / 'anchors.json').write_text(json.dumps({'generator_sha256': h.sha(h.HERE / 'anchors20.py'), 'parameters': {k: v for k, v in A.items() if k != 'note'}, 'parts': rec, 'pads_identical_to_r19': same, 'physical_adhesion_or_release_verified': False}, indent=2) + '\n')
    print({n: (v['flange_area_mm2'], v['first_layer_area_mm2'], v['separate_pads'], [(round(s[0], 2), round(s[1], 2)) for s in v['sites_print_xy_outward']], [(t['solid_depth_behind_tie_at_three_lines_mm'], t['part_volume_in_cutter_corridor_mm3']) for t in v['tie_sites']]) for n, v in rec.items()}, same, flush=True)


if __name__ == '__main__':
    main()
