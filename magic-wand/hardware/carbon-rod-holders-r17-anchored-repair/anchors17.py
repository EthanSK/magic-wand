#!/usr/bin/env python3
"""Removable bed anchors, one labelled mesh per printed part, in that part's print frame.

Each anchor is a multi-layer flange a real gap away from the part, joined to it only by short
fused necks on fixed faces. The flange outline is built from the part's filled first-layer outline,
so it cannot enter a bore, clip gap or window. slice17.py proves the printed result from the G-code.
"""
import json
import numpy as np
import trimesh
import manifold3d as mf
import holder17 as h

A = h.LOCAL['anchors']


def polygon_area(p):
    p = np.asarray(p); a, b = p, np.roll(p, -1, axis=0)
    return float((a[:, 0] * b[:, 1] - b[:, 0] * a[:, 1]).sum() / 2)


def rect(x0, x1, y0, y1):
    return mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def filled_outline(section, ring_axis=None, ring_radius=0.):
    """Outer contours only, with the clip ring's bore and mouth closed by a disc."""
    outer = mf.CrossSection([p for p in section.to_polygons() if polygon_area(p) > 0])
    if ring_axis is not None:
        outer += mf.CrossSection.circle(ring_radius, 96).translate(tuple(ring_axis))
    return outer


def plan(name):
    """Per-part flange keep boxes and neck rectangles, in print coordinates (X, Y)."""
    w = A['neck_width_mm'] / 2; o = A['neck_overlap_mm']; g = A['gap_mm']
    def direct(sites):
        """Each neck's joining direction: from the part face through the gap into the flange."""
        return ['x' if nx else 'y' for _, _, nx, ny in sites]
    def outward(x, y, nx, ny):
        """Neck from `o` inside the part face at (x, y) to `o` inside the flange, along (nx, ny)."""
        a = (x - nx * o, y - ny * o); b = (x + nx * (g + o), y + ny * (g + o))
        if nx: return rect(min(a[0], b[0]), max(a[0], b[0]), y - w, y + w)
        return rect(x - w, x + w, min(a[1], b[1]), max(a[1], b[1]))
    if name == 'Battery_Holder':
        axis = (14.6, 4.83)
        sites = [(6.0, 17.18, 0, 1), (23.2, 17.18, 0, 1), (2.4, 13.0, -1, 0), (26.8, 13.0, 1, 0), (5.0, 9.0, 0, -1), (24.2, 9.0, 0, -1)]
        keep = rect(-20, 50, 3.0, 40) - rect(6.8, 22.4, -10, 8.9)
        return dict(axis=axis, radius=5.4, keep=keep, sites=sites, flat=False, necks=[outward(*s) for s in sites], axes=direct(sites))
    if name == 'XIAO_Rod_Holder':
        axis = (14.6, 4.83)
        sites = [(2.6, 12.7, -1, 0), (26.6, 12.7, 1, 0), (4.6, 16.68, 0, 1), (24.6, 16.68, 0, 1)]
        necks = [outward(*s) for s in sites]
        # Under the angled end bars the face is not axis-aligned: reach from just inside the bar to the flange.
        for x in (5.6, 23.6):
            necks.append(rect(x - w, x + w, 8.55, 10.45))
        sites += [(5.6, 10.0, 0, -1), (23.6, 10.0, 0, -1)]
        # Two separate side pieces: nothing crosses the middle, where the USB plug and rod side stay clear.
        keep = rect(-20, 50, 3.0, 40) - rect(8.0, 21.2, -10, 9.6) - rect(7.6, 21.6, 9.0, 40)
        return dict(axis=axis, radius=5.4, keep=keep, sites=sites, flat=False, necks=necks, axes=direct(sites))
    if name == 'Battery_End_Gate':
        sites = [(7.2, 6.0, 0, 1), (19.3, 6.0, 0, 1)]
        return dict(flat=True, strip=(3.2, 23.3, 7.0, 10.0), necks=[rect(6.2, 8.2, 5.6, 7.4), rect(18.3, 20.3, 5.6, 7.4)], sites=sites, axes=direct(sites))
    if name == 'XIAO_Top_Retainer':
        # The two ears behind the grooves carry the necks; their rear faces are nowhere near a fit surface.
        sites = [(1.65, 10.0, 0, 1), (25.25, 10.0, 0, 1)]
        return dict(flat=True, strip=(.5, 26.4, 11.0, 14.0), necks=[rect(.65, 2.65, 9.6, 11.4), rect(24.25, 26.25, 9.6, 11.4)], sites=sites, axes=direct(sites))
    raise KeyError(name)


def anchor(name):
    m = trimesh.load_mesh(h.HERE / 'exports' / (name + '-SOURCE-REQUIRES-PREPARATION.stl'))
    part = mf.Manifold(mf.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32))); section = part.slice(.1); p = plan(name)
    r = A['corner_radius_mm']
    if p['flat']:
        t = A['flat_part_thickness_mm']
        x0, x1, y0, y1 = p['strip']; flange = rect(x0 + r, x1 - r, y0 + r, y1 - r).offset(r, mf.JoinType.Round)
    else:
        t = A['thickness_mm']
        outline = filled_outline(section, p['axis'], p['radius'])
        band = outline.offset(A['gap_mm'] + A['band_mm'], mf.JoinType.Round) - outline.offset(A['gap_mm'], mf.JoinType.Round)
        band = band ^ p['keep']
        flange = band.offset(-r, mf.JoinType.Round).offset(r * 2, mf.JoinType.Round).offset(-r, mf.JoinType.Round)
        flange = flange ^ (outline.offset(A['gap_mm'] + A['band_mm'] + 1., mf.JoinType.Round) - outline.offset(A['gap_mm'], mf.JoinType.Round))
    plan_shape = (flange + mf.CrossSection.batch_boolean(p['necks'], mf.OpType.Add)).simplify(.01)
    solid = mf.Manifold.extrude(plan_shape, t)
    bodies = solid.decompose(); assert all(any((mf.CrossSection.batch_boolean([n], mf.OpType.Add) ^ b.slice(.1)).area() > .1 for n in p['necks']) for b in bodies), (name, 'an anchor piece has no neck')
    # Outside the necks, the anchor must stay the designed gap away from the part.
    flange_clear = (flange ^ section.offset(A['gap_mm'] - .02, mf.JoinType.Round)).area()
    assert flange_clear < 1e-3, (name, 'flange inside designed gap', flange_clear)
    record = {'thickness_mm': t, 'flange_area_mm2': round(flange.area(), 2), 'plan_area_mm2': round(plan_shape.area(), 2), 'volume_mm3': round(solid.volume(), 2),
              'solid_PETG_g': round(solid.volume() / 1000 * h.base.r15.P['print']['density_g_cm3'], 4), 'neck_count': len(p['necks']), 'neck_sites_print_xy_outward_mm': p['sites'],
              'first_layer_area_mm2': round(section.area(), 2)}
    return solid, flange, p, section, record


def main():
    out = h.HERE / 'exports'; records = {}
    for name in h.PLATE:
        solid, flange, p, section, record = anchor(name)
        target = out / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl'); h.mesh(solid).export(target)
        check = trimesh.load_mesh(target); assert check.is_watertight, name
        record['stl_sha256'] = h.sha(target); records[name] = record
    (out / 'anchors.json').write_text(json.dumps({'generator_sha256': h.sha(h.HERE / 'anchors17.py'), 'parameters': A, 'parts': records, 'physical_adhesion_verified': False}, indent=2) + '\n')
    print({k: (v['plan_area_mm2'], v['solid_PETG_g'], v['neck_count']) for k, v in records.items()}, flush=True)


if __name__ == '__main__':
    main()
