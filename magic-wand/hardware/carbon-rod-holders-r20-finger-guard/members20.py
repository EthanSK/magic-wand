#!/usr/bin/env python3
"""Member-by-member load-path checks for the two parts the independent review questioned.

Finger_Guard: in every print layer, which members are joined into one piece, how tall each rim is at each bay
centre, and the section of each rail. Key_Carrier: the section of every print layer, and of its socket-board
level alone, against the accepted R16 part. A whole-layer area that sums separate islands shows none of this.

`check()` reads the exported meshes. `beads()` applies the same measures to actual sliced beads and is called by
slice20.py. Sections and counts only: no force, fatigue or strength is claimed.
"""
import sys
sys.dont_write_bytecode = True
import json
import numpy as np, manifold3d as mf
import holder20 as h

OUT = h.HERE / 'exports'; G = h.G; LAYER = G['layer_mm']; base = h.base


def square(x, z, half=.3):
    """Probe in the (x, -z) frame of a section cut across the rod."""
    return mf.CrossSection([[[x - half, -z - half], [x + half, -z - half], [x + half, -z + half], [x - half, -z + half]]])


def strip(points):
    return mf.CrossSection([base.ccw([(x, -z) for x, z in points])])


def guard_probes():
    f = h.frame(); t = G['face_thickness_mm']; w = G['rail_width_mm']; xg, xo = G['gunwale_inner_x_mm'], G['gunwale_outer_x_mm']; out = {'keel': square(0., h.wing_point(0., t / 2)[1] - .35), 'bays': {}, 'rails': {}, 'gunwale': {}}
    for sign, side in ((1, '+X'), (-1, '-X')):
        out['gunwale'][side] = square(sign * (xg + xo) / 2, 5.0)
        for i, (ua, ub) in enumerate(f['bays']):
            x, z = h.wing_point((ua + ub) / 2, t / 2); out['bays'][f'{side} bay {i}'] = square(sign * x, z)
        for i, u in enumerate(f['rails']):
            out['rails'][f'{side} rail {i}'] = strip([(sign * x, z) for x, z in (h.wing_point(u - w / 2 - .2, -.2), h.wing_point(u + w / 2 + .2, -.2), h.wing_point(u + w / 2 + .2, t + .2), h.wing_point(u - w / 2 - .2, t + .2))])
    return out


def guard_members(section_at, ys):
    """`section_at(y)` returns the plastic in the layer at assembly Y, in the (x, -z) frame."""
    pr = guard_probes(); rows = []
    for y in ys:
        sec = section_at(float(y)); pieces = [p for p in sec.decompose() if p.area() > .05]; hit = lambda probe: next((i for i, p in enumerate(pieces) if (p ^ probe).area() > .12), None)
        keel = hit(pr['keel']); gun = {s: hit(q) for s, q in pr['gunwale'].items()}
        rows.append({'y': float(y), 'pieces': len(pieces), 'tied': {s: keel is not None and gun[s] == keel for s in gun}, 'bay_filled': {n: (sec ^ q).area() > .15 for n, q in pr['bays'].items()}, 'rail_mm2': {n: float((sec ^ q).area()) for n, q in pr['rails'].items()}})
    rear = sorted(rows, key=lambda r: -r['y']); front = sorted(rows, key=lambda r: r['y'])
    def run(ordered, test):      # consecutive layers from one end for which `test` holds
        n = 0
        for r in ordered:
            if not test(r): break
            n += 1
        return n
    tied = {end: {s: run(order, lambda r, s=s: r['tied'][s]) for s in ('+X', '-X')} for end, order in (('rear', rear), ('front', front))}
    rim = {end: {n: round(run(order, lambda r, n=n: r['bay_filled'][n]) * LAYER, 2) for n in pr['bays']} for end, order in (('rear', rear), ('front', front))}
    open_rows = [r for r in rows if not any(r['tied'].values())]
    rails = {n: round(min(r['rail_mm2'][n] for r in open_rows), 3) for n in pr['rails']} if open_rows else {}
    return {'layers': len(rows), 'layers_where_gunwale_and_keel_are_one_piece': tied, 'rim_height_at_each_bay_centre_mm': rim, 'layers_with_separate_members_only': len(open_rows), 'pieces_in_those_layers': sorted({r['pieces'] for r in open_rows}),
            'smallest_rail_section_in_those_layers_mm2': rails, 'rail_section_as_designed_mm2': round(G['rail_width_mm'] * G['face_thickness_mm'], 3)}


def assert_guard(facts, fraction=1.):
    """Both rims must be whole across every bay and tie gunwale to keel; rails must carry their section."""
    need_rear = int(round(G['rear_rim_mm'] / LAYER)); need_front = int(round(G['front_rim_mm'] / LAYER))
    for side in ('+X', '-X'):
        assert facts['layers_where_gunwale_and_keel_are_one_piece']['rear'][side] >= need_rear - 1 and facts['layers_where_gunwale_and_keel_are_one_piece']['front'][side] >= need_front - 1, facts['layers_where_gunwale_and_keel_are_one_piece']
    assert min(facts['rim_height_at_each_bay_centre_mm']['rear'].values()) >= G['rear_rim_mm'] - LAYER - 1e-6 and min(facts['rim_height_at_each_bay_centre_mm']['front'].values()) >= G['front_rim_mm'] - LAYER - 1e-6, facts['rim_height_at_each_bay_centre_mm']
    assert min(facts['smallest_rail_section_in_those_layers_mm2'].values()) >= fraction * .9 * facts['rail_section_as_designed_mm2'], facts['smallest_rail_section_in_those_layers_mm2']


def key_layers(section_at, ys):
    """Whole section and socket-board-level section of every layer, (x, -z) frame."""
    bottom, top = base.slab_bottom(), base.PCB_Z; band = mf.CrossSection.square((80, top - bottom)).translate((-40, -top)); rows = []
    for y in ys:
        sec = section_at(float(y)); b = sec ^ band; rows.append({'y': round(float(y), 3), 'whole_mm2': float(sec.area()), 'board_mm2': float(b.area()), 'board_pieces': len([p for p in b.decompose() if p.area() > .05])})
    return rows


def key_compare(new, old):
    assert [r['y'] for r in new] == [r['y'] for r in old]; out = {}
    for field in ('whole_mm2', 'board_mm2'):
        ratios = [(n[field] / o[field], n['y'], n[field], o[field]) for n, o in zip(new, old) if o[field] > 1.]; worst = min(ratios)
        low_n = min(new, key=lambda r: r[field] if r[field] > 1. else 9e9); low_o = min(old, key=lambda r: r[field] if r[field] > 1. else 9e9)
        out[field] = {'smallest_r20_over_r16': round(worst[0], 3), 'at_y_mm': worst[1], 'r20_mm2': round(worst[2], 2), 'r16_mm2': round(worst[3], 2), 'layers_reduced_by_more_than_2_percent': sum(1 for r in ratios if r[0] < .98),
                      'smallest_layer_r20_mm2': round(low_n[field], 2), 'smallest_layer_r20_at_y_mm': low_n['y'], 'smallest_layer_r16_mm2': round(low_o[field], 2), 'smallest_layer_r16_at_y_mm': low_o['y']}
    lower = [(n, o) for n, o in zip(new, old) if n['y'] < 7.0]
    out['lower_row_board_level'] = {'layers': len(lower), 'largest_area_loss_mm2': round(max(o['board_mm2'] - n['board_mm2'] for n, o in lower), 3), 'layers_split_into_more_pieces_than_r16': sum(1 for n, o in lower if n['board_pieces'] > o['board_pieces'])}
    # Runs of consecutive layers that lose more than 2 percent: how the cuts are spread up the print.
    runs = []; cur = None
    for n, o in zip(new, old):
        ratio = n['whole_mm2'] / o['whole_mm2'] if o['whole_mm2'] > 1. else 1.; lost = ratio < .98
        if lost: cur = [n['y'], n['y'], ratio] if cur is None else [cur[0], n['y'], min(cur[2], ratio)]
        elif cur: runs.append(cur); cur = None
    if cur: runs.append(cur)
    out['bands_of_layers_that_lose_section'] = [{'y_mm': [round(min(a, b), 2), round(max(a, b), 2)], 'smallest_r20_over_r16': round(r, 3)} for a, b, r in runs]
    return out


def assert_key(facts):
    assert facts['lower_row_board_level']['largest_area_loss_mm2'] < .05 and facts['lower_row_board_level']['layers_split_into_more_pieces_than_r16'] == 0, facts['lower_row_board_level']
    for field in ('whole_mm2', 'board_mm2'):
        assert facts[field]['smallest_layer_r20_mm2'] >= facts[field]['smallest_layer_r16_mm2'] - .6, (field, 'R20 must not create a new weakest layer', facts[field])
    assert facts['whole_mm2']['smallest_r20_over_r16'] >= .84, facts['whole_mm2']


def mesh_section(name, folder=None):
    solid = h.read((folder or OUT) / (name + '-assembly.stl')).rotate((90, 0, 0)); return lambda y: solid.slice(y)


def layer_ys(y_front, y_rear): return [y_rear - (k + .5) * LAYER for k in range(int(round((y_rear - y_front) / LAYER)))]


def check():
    rep = {'manifest_sha256': h.sha(OUT / 'manifest.json'), 'checker_sha256': h.sha(h.HERE / 'members20.py'), 'scope': 'Exported meshes. slice20.py repeats both on actual beads.', 'physical_strength_verified': False}
    guard = guard_members(mesh_section('Finger_Guard'), layer_ys(G['y_front_mm'], G['y_rear_mm'])); assert_guard(guard); rep['Finger_Guard'] = guard
    s = h.P['slab']; ys = layer_ys(s['front_y_mm'], s['rear_y_mm'])
    key = key_compare(key_layers(mesh_section('Key_Carrier'), ys), key_layers(mesh_section('Key_Carrier', h.R16 / 'exports'), ys)); assert_key(key); rep['Key_Carrier_against_R16'] = key
    rep['passed'] = True; (OUT / 'member-checks.json').write_text(json.dumps(rep, indent=2) + '\n'); print(json.dumps(rep, indent=1), flush=True)


def beads(assembly, q, bead_footprints):
    """The same measures on actual beads. `assembly[name]` is (points in the assembly frame, widths); a layer is one Y value."""
    out = {}
    def by_layer(name):
        pts, widths = assembly[name]; keys = np.round(pts[:, 1], 3); cache = {}
        def at(y):
            # Assembly Y decreases as print Z rises. Bead coordinates are at
            # the layer top; compare the mesh at its middle, as slice16's
            # layer_section/path_scan do. A boundary face can double its area.
            sel = np.abs(keys - round(y - LAYER / 2, 3)) < .06
            if y not in cache: cache[y] = bead_footprints(q, pts[sel][:, [0, 2]] * np.array([1, -1]), widths[sel]) if sel.any() else mf.CrossSection()
            return cache[y]
        return at, sorted({float(v) + LAYER / 2 for v in keys})
    at, ys = by_layer('Finger_Guard'); guard = guard_members(at, ys); assert_guard(guard, .9); out['Finger_Guard'] = guard
    at, ys = by_layer('Key_Carrier'); mesh = mesh_section('Key_Carrier'); old = mesh_section('Key_Carrier', h.R16 / 'exports'); rows = key_layers(at, ys); mesh_rows = key_layers(mesh, ys); old_rows = key_layers(old, ys)
    printed = [(b['whole_mm2'] / m['whole_mm2'], b['y']) for b, m in zip(rows, mesh_rows) if m['whole_mm2'] > 1.]
    # The inherited saddle uses sparse infill: unchanged layers need not be
    # 80% solid. Apply that material screen to every section reduced by the new
    # windows, and retain the all-layer minimum-material comparison below.
    changed = [(b['whole_mm2'] / m['whole_mm2'], b['y']) for b, m, old_ in zip(rows, mesh_rows, old_rows)
               if old_['whole_mm2'] > 1. and m['whole_mm2'] < .98 * old_['whole_mm2']]
    low = min(rows, key=lambda r: r['whole_mm2'] if r['whole_mm2'] > 1. else 9e9); low_old = min(old_rows, key=lambda r: r['whole_mm2'] if r['whole_mm2'] > 1. else 9e9)
    assert len(changed) > 20 and min(changed)[0] >= .8 and low['whole_mm2'] >= .85 * low_old['whole_mm2'], (min(changed), low, low_old)
    out['Key_Carrier'] = {'layers': len(rows), 'section_plane': 'layer middle', 'smallest_printed_fraction_of_a_layer_section': round(min(printed)[0], 3), 'at_y_mm': min(printed)[1],
                          'changed_layers_checked': len(changed), 'smallest_printed_fraction_in_changed_sections': round(min(changed)[0], 3), 'changed_section_at_y_mm': min(changed)[1],
                          'smallest_printed_layer_mm2': round(low['whole_mm2'], 2), 'smallest_printed_layer_at_y_mm': low['y'], 'smallest_r16_mesh_layer_mm2': round(low_old['whole_mm2'], 2),
                          'sparse_infill_note': 'Whole-layer sums include unchanged sparse saddle infill. Window-reduced sections are checked separately; this is not a breaking-force result.'}
    return out


if __name__ == '__main__':
    check()
