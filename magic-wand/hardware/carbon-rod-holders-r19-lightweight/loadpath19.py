#!/usr/bin/env python3
"""Direct load-path checks for the R19 open trusses, replacing R18's whole-panel section screens.

Layers are assembly-Y planes, as printed. For each holder this measures islands per layer, the smallest
member, layer-to-layer overlap, the path from each rod ring to the bed, narrow necks inside islands, and
how far any island stands free before it is braced. R16 and R18 layer facts are listed for context.

These are geometric screens. The free-span figure restarts at every member merge, so it describes one local
run, not the whole holder. It must not be compared between revisions as stiffness, and it is not a force.
"""
import json, math
import numpy as np, trimesh, manifold3d as mf
import holder19 as h

OUT = h.HERE / 'exports'; LAYER = .2; E_MPA = 2000.; NOZZLE_FORCE_N = 1.
NECK_HALF_WIDTH = .59  # Finds connections narrower than 1.18 mm, just under the 1.2 mm sections the design intends.
MIN_OVERLAP = .05


def read(p):
    m = trimesh.load_mesh(p); return mf.Manifold(mf.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32)))


def imin(section):
    """Smallest principal second moment of area of a cross-section, holes included."""
    A = Sx = Sy = Ixx = Iyy = Ixy = 0.
    for poly in section.to_polygons():
        p = np.asarray(poly); q = np.roll(p, -1, axis=0); c = p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1]
        A += c.sum() / 2; Sx += ((p[:, 0] + q[:, 0]) * c).sum() / 6; Sy += ((p[:, 1] + q[:, 1]) * c).sum() / 6
        Ixx += ((p[:, 1] ** 2 + p[:, 1] * q[:, 1] + q[:, 1] ** 2) * c).sum() / 12; Iyy += ((p[:, 0] ** 2 + p[:, 0] * q[:, 0] + q[:, 0] ** 2) * c).sum() / 12
        Ixy += ((p[:, 0] * q[:, 1] + 2 * p[:, 0] * p[:, 1] + 2 * q[:, 0] * q[:, 1] + q[:, 0] * p[:, 1]) * c).sum() / 24
    if abs(A) < 1e-9: return 0.
    cx, cy = Sx / A, Sy / A; a = abs(Ixx - A * cy ** 2); b = abs(Iyy - A * cx ** 2); d = Ixy - A * cx * cy
    return float((a + b) / 2 - math.hypot((a - b) / 2, d))


def inscribed_width(section):
    """Width of the widest circle-swept core: twice the largest inward offset that leaves material."""
    lo, hi = 0., 8.
    for _ in range(11):
        mid = (lo + hi) / 2
        if section.offset(-mid, mf.JoinType.Round).is_empty(): hi = mid
        else: lo = mid
    return 2 * lo


def stack(solid):
    """Islands of every printed layer, bed first."""
    upright = solid.rotate((90, 0, 0)); box = solid.bounding_box(); y1 = box[4]; y0 = box[1]; n = int(round((y1 - y0) / LAYER)); rows = []
    for k in range(n):
        y = y1 - (k + .5) * LAYER; section = upright.slice(float(y)); items = []
        for part in section.decompose():
            if part.area() < .02: continue
            items.append({'section': part, 'area': float(part.area()), 'bounds': part.bounds(), 'imin': imin(part)})
        rows.append({'k': k, 'y': float(y), 'islands': items})
    return rows


def link(rows):
    """Overlap of every island with the islands of the layer below."""
    for prev, cur in zip(rows, rows[1:]):
        for a in cur['islands']:
            a['parents'] = []
            for j, b in enumerate(prev['islands']):
                if a['bounds'][0] > b['bounds'][2] or a['bounds'][2] < b['bounds'][0] or a['bounds'][1] > b['bounds'][3] or a['bounds'][3] < b['bounds'][1]: continue
                o = float((a['section'] ^ b['section']).area())
                if o > MIN_OVERLAP: a['parents'].append((j, o))
    for i in rows[0]['islands']: i['parents'] = []
    for row in rows:
        for i in row['islands']: i['children'] = 0
    for prev, cur in zip(rows, rows[1:]):
        for a in cur['islands']:
            for j, _ in a['parents']: prev['islands'][j]['children'] += 1


def free_standing(rows):
    """How far each island stands above its last brace. Only a merge of separate members braces: a branch leaving a member does not restrain it.

    Tip deflection integrates the actual section of every layer in the span, so a wide base counts as stiff."""
    worst = None; tallest = 0.
    for k, row in enumerate(rows):
        for island in row['islands']:
            p = island['parents']
            if k == 0 or len(p) >= 2 or not p: island['chain'] = [island['imin']]
            else: island['chain'] = rows[k - 1]['islands'][p[0][0]]['chain'] + [island['imin']]
            n = len(island['chain']); L = (n - 1) * LAYER; island['free'] = L; tallest = max(tallest, L)
            d = sum((L - j * LAYER) ** 2 * LAYER / (E_MPA * max(i, 1e-6)) for j, i in enumerate(island['chain'])) * NOZZLE_FORCE_N
            if worst is None or d > worst['beam_tip_deflection_per_N_mm']:
                b = island['bounds']; worst = {'beam_tip_deflection_per_N_mm': round(d, 4), 'free_height_mm': round(L, 2), 'smallest_Imin_in_span_mm4': round(min(island['chain']), 3), 'island_area_mm2': round(island['area'], 2), 'assembly_y_mm': round(row['y'], 2), 'x_range_mm': [round(b[0], 2), round(b[2], 2)], 'z_range_mm': [round(-b[3], 2), round(-b[1], 2)]}
    return {'worst_cantilever': worst, 'tallest_unbraced_island_mm': round(tallest, 2)}


def neck_scan(rows, half_width):
    """Narrow connections inside an island: eroding it by half_width splits it into separate pieces of real size."""
    found = []
    for row in rows:
        for island in row['islands']:
            pieces = [p for p in island['section'].offset(-half_width, mf.JoinType.Round).decompose() if p.area() > .05]
            if len(pieces) >= 2:
                b = island['bounds']; lo, hi = 0., half_width
                for _ in range(9):
                    mid = (lo + hi) / 2
                    if len([p for p in island['section'].offset(-mid, mf.JoinType.Round).decompose() if p.area() > .05]) >= 2: hi = mid
                    else: lo = mid
                found.append((round(row['y'], 2), round(b[0], 2), round(b[2], 2), round(-b[3], 2), round(-b[1], 2), len(pieces), round(2 * hi, 3)))
    groups = []
    for y, x0, x1, z0, z1, n, w in found:
        for g in groups:
            if abs(g['x_range_mm'][0] - x0) < 3. and abs(g['x_range_mm'][1] - x1) < 3. and abs(g['y_range_mm'][1] - y) < .45:
                g['y_range_mm'][1] = y; g['layers'] += 1; g['narrowest_neck_mm'] = min(g['narrowest_neck_mm'], w); break
        else: groups.append({'y_range_mm': [y, y], 'x_range_mm': [x0, x1], 'z_range_mm': [z0, z1], 'layers': 1, 'pieces_after_erosion': n, 'narrowest_neck_mm': w})
    return {'neck_narrower_than_mm': round(2 * half_width, 2), 'layers_with_a_neck': len(found), 'groups': groups}


def layer_report(rows):
    smallest, thin = None, None; counts = []; overlap_ratio = 1.; total_min = None
    for row in rows:
        counts.append(len(row['islands'])); total = sum(i['area'] for i in row['islands'])
        if total_min is None or total < total_min[0]: total_min = (total, row['y'])
        for island in row['islands']:
            if smallest is None or island['area'] < smallest[0]: smallest = (island['area'], row['y'], island['bounds'])
            if row['k'] and island['parents']:
                r = sum(o for _, o in island['parents']) / island['area']; overlap_ratio = min(overlap_ratio, r)
    # Inscribed width is slower; sample the islands most likely to be thinnest.
    for row in rows:
        for island in sorted(row['islands'], key=lambda i: i['area'])[:3]:
            w = inscribed_width(island['section'])
            if thin is None or w < thin[0]: thin = (w, row['y'], island['bounds'], island['area'])
    return {'layers': len(rows), 'most_islands_in_a_layer': max(counts), 'smallest_island_mm2': round(smallest[0], 2), 'smallest_island_assembly_y_mm': round(smallest[1], 2), 'smallest_island_x_range_mm': [round(smallest[2][0], 2), round(smallest[2][2], 2)],
            'least_widest_inscribed_core_mm': round(thin[0], 2), 'least_widest_inscribed_core_note': 'Widest circle that fits inside the island with the slimmest core. Not a minimum section: see necks.', 'least_core_assembly_y_mm': round(thin[1], 2), 'least_core_x_range_mm': [round(thin[2][0], 2), round(thin[2][2], 2)], 'least_core_island_area_mm2': round(thin[3], 2),
            'least_whole_layer_section_mm2': round(total_min[0], 2), 'least_whole_layer_section_y_mm': round(total_min[1], 2), 'minimum_layer_to_layer_overlap_of_an_island': round(overlap_ratio, 3)}


def trace_to_bed(rows, y_start, point):
    """From the ring's own island, walk every member down to the bed. Reports the layer where the path has reached both sides."""
    k0 = min(range(len(rows)), key=lambda k: abs(rows[k]['y'] - y_start)); probe = mf.CrossSection.square((.1, .1), True).translate(point)
    start = [j for j, i in enumerate(rows[k0]['islands']) if not (i['section'] ^ probe).is_empty()]; assert start, ('no ring island at', y_start, point)
    active = set(start); series = []; both = None; members = {}
    for k in range(k0, -1, -1):
        items = rows[k]['islands']; area = sum(items[j]['area'] for j in active); series.append((rows[k]['y'], area, len(active)))
        lo = min(items[j]['bounds'][0] for j in active); hi = max(items[j]['bounds'][2] for j in active)
        if both is None and lo < -9. and hi > 9.: both = rows[k]['y']
        if k:
            below = set()
            for j in active:
                for p, _ in items[j]['parents']: below.add(p)
            active = below; assert active, ('ring path ends above the bed', rows[k]['y'])
    before = [s for s in series if both is None or s[0] <= both]; worst = min(before, key=lambda s: s[1])
    return {'ring_layer_y_mm': round(rows[k0]['y'], 2), 'reaches_both_sides_at_y_mm': round(both, 2) if both is not None else None, 'smallest_total_section_on_the_way_mm2': round(worst[1], 2), 'at_y_mm': round(worst[0], 2), 'most_parallel_members': max(s[2] for s in before), 'layers_walked_to_bed': len(series)}


def ring_joint(solid, band, z=4.6):
    """Where the ring crown meets the body: the horizontal plan section in the ring band."""
    y0, y1 = band
    sec = solid.translate((0, 0, -z)).slice(0.) ^ mf.CrossSection.square((40, y1 - y0)).translate((-20, y0))
    b = sec.bounds() if not sec.is_empty() else [0, 0, 0, 0]
    return {'plan_section_mm2': round(float(sec.area()), 2), 'x_width_mm': round(float(b[2] - b[0]), 2)}


def holder_report(path, bands, current=True):
    solid = read(path); rows = stack(solid); link(rows); report = layer_report(rows)
    report['islands_without_a_parent_above_bed'] = sum(1 for r in rows[1:] for i in r['islands'] if not i['parents']); report['volume_mm3'] = round(float(solid.volume()), 1); report['body_count'] = len(solid.decompose())
    if not current: return report
    report.update(free_standing(rows)); report['necks'] = neck_scan(rows, NECK_HALF_WIDTH); report['rings'] = {}
    for label, band in bands.items():
        report['rings'][label] = {**trace_to_bed(rows, (band[0] + band[1]) / 2, (0., -4.6)), 'crown_joint_at_z_4p6': ring_joint(solid, band)}
    return report


def bands():
    return {'Battery_Holder': {'near': h.CAGE['near_band_y_mm'], 'far': h.CAGE['far_band_y_mm']}, 'XIAO_Rod_Holder': {'near': h.S['near_band_y_mm'], 'far': h.S['far_band_y_mm']}}


def bead_islands(solid, pts, widths, footprints, q):
    """Actual extrusion against every island of every layer: a member the slicer thins or drops shows up here."""
    upright = solid.rotate((90, 0, 0)); ys = np.unique(np.round(pts[:, 1], 4)); worst_fraction = None; worst_printed = None; n = 0
    for y in ys:
        section = upright.slice(float(y) + .1); sel = abs(pts[:, 1] - y) < .01
        if section.is_empty() or sel.sum() < 2: continue
        beads = footprints(q, pts[sel][:, [0, 2]] * np.array([1, -1]), widths[sel])
        for island in section.decompose():
            if island.area() < .3: continue
            n += 1; printed = float((beads ^ island).area()); fr = printed / island.area()
            if worst_fraction is None or fr < worst_fraction[0]: worst_fraction = (fr, float(y), island.area())
            if worst_printed is None or printed < worst_printed[0]: worst_printed = (printed, float(y), island.area())
    return {'islands_checked': n, 'smallest_printed_fraction_of_an_island': round(worst_fraction[0], 3), 'at_layer_top_y_mm': round(worst_fraction[1], 2), 'island_area_mm2': round(worst_fraction[2], 2), 'smallest_printed_area_of_an_island_mm2': round(worst_printed[0], 2), 'smallest_printed_island_layer_y_mm': round(worst_printed[1], 2), 'method': 'Actual bead footprints inside each mesh island in each layer. Screening only; not a breaking force.'}


def main():
    result = {'generator_sha256': h.sha(h.HERE / 'loadpath19.py'), 'parameters_sha256': h.sha(h.HERE / 'parameters.json'), 'manifest_sha256': h.sha(OUT / 'manifest.json'), 'layer_height_mm': LAYER, 'local_free_span_screen': {'modulus_MPa': E_MPA, 'tip_force_N': NOZZLE_FORCE_N, 'status': 'Local screen of one R19 run between member merges. Not whole-holder stiffness, not comparable between revisions, and not a measured force.'}, 'physical_strength_verified': False, 'parts': {}}
    for name, band in bands().items():
        rows = {'R19': holder_report(OUT / (name + '-assembly.stl'), band), 'R18_layer_facts': holder_report(h.h18.HERE / 'exports' / (name + '-assembly.stl'), band, False), 'R16_layer_facts': holder_report(h.R16 / 'exports' / (name + '-assembly.stl'), band, False)}
        result['parts'][name] = rows; r = rows['R19']
        assert r['body_count'] == 1 and r['islands_without_a_parent_above_bed'] == 0, (name, r['body_count'], r['islands_without_a_parent_above_bed'])
        assert r['smallest_island_mm2'] >= 3.5, (name, 'smallest island', r['smallest_island_mm2'])
        assert r['least_widest_inscribed_core_mm'] >= 1.0, (name, 'least core', r['least_widest_inscribed_core_mm'])
        assert r['most_islands_in_a_layer'] <= 5, (name, 'islands', r['most_islands_in_a_layer'])
        for label, ring in r['rings'].items(): assert ring['reaches_both_sides_at_y_mm'] is not None and ring['crown_joint_at_z_4p6']['plan_section_mm2'] >= 8., (name, label, ring)
    target = OUT / 'load-paths.json'; target.write_text(json.dumps(result, indent=2) + '\n')
    for name, rows in result['parts'].items():
        r = rows['R19']
        print(name, {k: r[k] for k in ['volume_mm3', 'most_islands_in_a_layer', 'smallest_island_mm2', 'least_widest_inscribed_core_mm', 'least_whole_layer_section_mm2', 'minimum_layer_to_layer_overlap_of_an_island', 'tallest_unbraced_island_mm']}, r['worst_cantilever'], flush=True)
        print('   rings', json.dumps(r['rings']), flush=True); print('   necks', json.dumps(r['necks']), flush=True)


if __name__ == '__main__':
    main()
