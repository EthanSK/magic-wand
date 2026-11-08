#!/usr/bin/env python3
"""Separate tear-off bed pads, each joined to a strong fixed face by a 1.0 x 0.4 mm tie."""
import json
import numpy as np, trimesh, manifold3d as mf
import holder18 as h

A = h.LOCAL['anchors']; rect = h.rect
SITES = {'Battery_Holder': [(6.0, 17.18, 0, 1), (23.2, 17.18, 0, 1), (2.4, 13.0, -1, 0), (26.8, 13.0, 1, 0), (5.0, 9.0, 0, -1), (24.2, 9.0, 0, -1)]}


def xiao_sites(section):
    b = section.bounds(); return [(2.6, 12.9, -1, 0), (26.6, 12.9, 1, 0), (2.6, 17.4, -1, 0), (26.6, 17.4, 1, 0), (9.6, b[3], 0, 1), (19.6, b[3], 0, 1)]


def plan(name, section):
    sites = SITES.get(name) or xiao_sites(section); w, o, g, L, d, T = A['tie_width_mm'] / 2, A['tie_overlap_mm'], A['gap_mm'], A['pad_half_length_mm'], A['pad_depth_mm'], A['pull_tab_length_mm']
    necks, pads = [], []
    for x, y, nx, ny in sites:
        reach = lambda a, b: (x + nx * a, y + ny * a, x + nx * b, y + ny * b)
        def r(a, b, half):
            p = reach(a, b)
            return rect(min(p[0], p[2]), max(p[0], p[2]), y - half, y + half) if nx else rect(x - half, x + half, min(p[1], p[3]), max(p[1], p[3]))
        necks.append(r(-o, g + o, w)); pads.append(r(g, g + d, L) + r(g + d - .1, g + d + T, 2.5))
    return dict(sites=sites, necks=necks, pads=pads, axes=['x' if s[2] else 'y' for s in sites])


def anchor(name):
    m = trimesh.load_mesh(h.HERE / 'exports' / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); part = h17_solid(m); section = part.slice(.1); p = plan(name, section); r = 1.
    outline = mf.CrossSection([q for q in section.to_polygons() if area(q) > 0]) + mf.CrossSection.circle(5.4, 96).translate((14.6, 4.83))
    flange = mf.CrossSection.batch_boolean(p['pads'], mf.OpType.Add).offset(-.6, mf.JoinType.Round).offset(.6, mf.JoinType.Round) - outline.offset(A['gap_mm'], mf.JoinType.Round)
    shape = (flange + mf.CrossSection.batch_boolean(p['necks'], mf.OpType.Add)).simplify(.01); solid = mf.Manifold.extrude(shape, A['thickness_mm'])
    for b in solid.decompose(): assert any((n ^ b.slice(.1)).area() > .1 for n in p['necks']), (name, 'pad without a tie')
    return solid, flange, p, section, {'thickness_mm': A['thickness_mm'], 'flange_area_mm2': round(flange.area(), 2), 'tie_section_each_mm2': round(A['tie_width_mm'] * A['thickness_mm'], 3), 'tie_count': len(p['necks']), 'separate_pads': len(solid.decompose()), 'solid_PETG_g': round(solid.volume() / 1000 * 1.27, 4), 'first_layer_area_mm2': round(section.area(), 2), 'sites_print_xy_outward': p['sites']}


def area(p):
    p = np.asarray(p); a, b = p, np.roll(p, -1, axis=0); return float((a[:, 0] * b[:, 1] - b[:, 0] * a[:, 1]).sum() / 2)
def h17_solid(m): return mf.Manifold(mf.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32)))


def main():
    out = h.HERE / 'exports'; rec = {}
    for name in h.ANCHORED:
        solid, _, _, _, r = anchor(name); t = out / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl'); h.mesh(solid).export(t); assert trimesh.load_mesh(t).is_watertight; r['stl_sha256'] = h.sha(t); rec[name] = r
    r17_tie = 2.2 * .8
    (out / 'anchors.json').write_text(json.dumps({'generator_sha256': h.sha(h.HERE / 'anchors18.py'), 'parameters': A, 'parts': rec, 'r17_neck_section_each_mm2': r17_tie, 'r17_neck_count_each_holder': 6, 'physical_adhesion_or_release_verified': False}, indent=2) + '\n')
    print(rec, flush=True)


if __name__ == '__main__':
    main()
