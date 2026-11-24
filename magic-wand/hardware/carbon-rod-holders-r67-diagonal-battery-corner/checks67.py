"""CAD checks for the R67 carrier: the exact R66 carrier minus three local regions.

* subtraction.json  the export equals R66 minus the three cutters, section by section,
                    and nothing else changed
* battery.json      the R66 battery checks, plus the diagonal corner, the root post and
                    the pouch-side face
* saddle.json       the three free rib stubs beside the front saddle, their R33/R60
                    origin, and the unchanged rod ring, saddle and guard
* op1-route.json    the R66 OP1 route checks on R67, plus the underside lead-in, the
                    three holes and the board bearing against R66, and the free space
                    round the plug's path below the deck
* carrier.json      summary, key socket routes and the bound carrier SHA-256

Exits non-zero when a gate fails. Slice-based checks live in audit67.py.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import design67 as d
import checks66 as c66

r66, b, old = d.r66, d.b, d.old
OUT = d.OUT
HARDWARE = d.HARDWARE
mm3 = c66.mm3


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def vol(solid):
    return round(float(solid.volume()), 4)


def cutters():
    return dict(battery_corner=d.battery_corner_cutter(), saddle_stubs=d.saddle_stub_cutter(), plug_lead_in=d.plug_lead_in())


# ----------------------------------------------------------------------- subtraction
def section_difference(expected, actual, spacing=.2):
    """Symmetric section difference at every print layer (Y), whole carrier."""
    before, after = [s.rotate((90, 0, 0)) for s in (expected, actual)]
    lo, hi = before.bounding_box()[2], before.bounding_box()[5]
    heights = np.arange(lo + .03, hi, spacing)
    areas = [((before.slice(float(h)) - after.slice(float(h))).area() + (after.slice(float(h)) - before.slice(float(h))).area())
             for h in heights]
    worst = int(np.argmax(areas))
    return dict(sections=len(heights), spacing_mm=spacing, max_area_mm2=round(float(areas[worst]), 6),
                worst_y_mm=round(float(heights[worst]), 3), sum_area_times_step_mm3=round(float(sum(areas) * spacing), 6))


def subtraction(body, before):
    cut = cutters()
    removed = {k: mm3(before, c) for k, c in cut.items()}
    names = list(cut)
    pairwise = {f'{a}+{c}': mm3(before ^ cut[a], cut[c]) for i, a in enumerate(names) for c in names[i + 1:]}
    expected = before - b.union(list(cut.values()))
    report = dict(
        revision='R67', physical_fit_verified=False, r66_carrier_sha256=d.R66_SHA256,
        removed_from_r66_mm3=removed, cutters_overlap_in_r66_mm3=pairwise,
        left_inside_cutters_mm3={k: mm3(body, c) for k, c in cut.items()},
        volume_mm3=dict(r66=vol(before), r67=vol(body), difference=round(float(before.volume() - body.volume()), 4)),
        sections_against_r66_minus_cutters=section_difference(expected, body),
        components=len(body.decompose()))
    r = report
    r['gates'] = [abs(r['volume_mm3']['difference'] - sum(removed.values())) < .01,
                  max(pairwise.values()) < 1e-4, max(r['left_inside_cutters_mm3'].values()) < .001,
                  r['sections_against_r66_minus_cutters']['max_area_mm2'] < .0025,
                  r['sections_against_r66_minus_cutters']['sum_area_times_step_mm3'] < .002,
                  r['components'] == 1]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- battery
def outboard_edge(body, y, z0=old.LOW - .05, z1=d.ROOF_TOP + .05):
    s = body ^ b.box(-30, old.PACK_X[0], y - .02, y + .02, z0, z1)
    return None if s.is_empty() else round(float(s.bounding_box()[0]), 3)


def battery(body, before, r64_body):
    report = c66.battery(body, r64_body)
    report['revision'] = 'R67'
    p1, p2, _, _ = d.corner_line()
    root = b.box(old.WALL_FACE - .02, old.PACK_X[0] - .37, old.BED - 5.5, old.BED, old.LIP_TOP - .02, old.DECK + .01)
    pouch_face = b.box(-22.1, old.PACK_X[0] - .37, old.BED - 5.5, old.BED, old.LIP_TOP - .02, old.DECK + .01)
    post_front = b.box(old.WALL_FACE - .02, old.PACK_X[0] - .37, old.BED - 5.5, d.CORNER_START_Y, old.LIP_TOP - .02, old.DECK + .01)
    corner = dict(
        line_xy_mm=[[round(float(v), 3) for v in p1], [round(float(v), 3) for v in p2]],
        angle_from_rod_axis_deg=round(float(np.degrees(np.arctan2(p2[0] - p1[0], p2[1] - p1[1]))), 1),
        print_overhang_from_vertical_deg=round(float(np.degrees(np.arctan2(p2[0] - p1[0], p2[1] - p1[1]))), 1),
        edge_radius_mm=d.CORNER_EDGE_R,
        removed_mm3=mm3(before, d.battery_corner_cutter()),
        outboard_edge_x_mm={f'y{y:g}': dict(r66=outboard_edge(before, y), r67=outboard_edge(body, y))
                            for y in (38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 43.6)},
        root_post_mm3=dict(r66=vol(before ^ root), r67=vol(body ^ root)),
        root_post_front_to_y40_mm3=dict(r66=vol(before ^ post_front), r67=vol(body ^ post_front)),
        pouch_side_of_post_mm3=dict(r66=vol(before ^ pouch_face), r67=vol(body ^ pouch_face)),
        bed_face_area_in_corner_mm2=dict(
            r66=round((before.rotate((90, 0, 0)).slice(old.BED - .02) ^ mf.CrossSection.square((10, 12)).translate((-26, -12))).area(), 3),
            r67=round((body.rotate((90, 0, 0)).slice(old.BED - .02) ^ mf.CrossSection.square((10, 12)).translate((-26, -12))).area(), 3)))
    report['diagonal_corner'] = corner
    gates = [corner['outboard_edge_x_mm']['y43.6']['r67'] >= d.CORNER_BED_X - .05,
             corner['outboard_edge_x_mm']['y38']['r67'] == corner['outboard_edge_x_mm']['y38']['r66'],
             abs(corner['root_post_front_to_y40_mm3']['r67'] - corner['root_post_front_to_y40_mm3']['r66']) < .005,
             abs(corner['pouch_side_of_post_mm3']['r67'] - corner['pouch_side_of_post_mm3']['r66']) < .005,
             corner['print_overhang_from_vertical_deg'] <= 35]
    report['gates'] = report['gates'] + gates
    report['passes'] = all(report['gates'])
    return report


# ----------------------------------------------------------------------- saddle stubs
def stub_history():
    """The same free piece in earlier exported carriers: present from R60, absent before."""
    rows = {}
    for rev in ('r59-flipped-guard', 'r60-rounded-beams', 'r63-open-hinge', 'r64-under-entry', 'r66-three-hole-op1'):
        body = b.load(HARDWARE / f'carbon-rod-holders-{rev}' / 'exports' / d.HOLDER)
        free = [r for r in d.zone_pieces(body) if r['free'] and r['volume'] > 1.0]
        rows[rev.split('-')[0].upper()] = [dict(volume_mm3=round(r['volume'], 2), x_mm=[round(r['lo'][0], 2), round(r['hi'][0], 2)],
                                                y_mm=[round(r['lo'][1], 2), round(r['hi'][1], 2)]) for r in free]
    return rows


def saddle(body, before):
    rod = c66.full_rod()
    ring = old.lay(mf.Manifold.cylinder(24, d.RING_KEEP_R, d.RING_KEEP_R, 128), -2)
    stem = b.box(-3.85, 3.85, -2, 22, -6, 8)
    # The guard roots beside the stubs, outside the stub cutter, and the right-hand station
    # below the deck (the plug lead-in only touches deck material above Z 7.25).
    guard = b.box(-16, -7.8, 8, 20, 1, 7.27) - d.saddle_stub_cutter()
    right = b.box(4.75, 12.5, .5, 19.5, 1.0, 7.2)
    rows_before = [(round(r['volume'], 3), r['free']) for r in d.zone_pieces(before)]
    rows_after = [(round(r['volume'], 3), r['free']) for r in d.zone_pieces(body)]
    stubs = [r for r in d.zone_pieces(before) if r['free'] and r['volume'] > 1.0]
    report = dict(
        revision='R67', physical_fit_verified=False,
        origin=('R33 ran three rounded crosswise guard ribs on each side from the outer rails to the front rod saddle. '
                'R60 rebuilt the guards and removed the old ribs only outboard of |X| 9.3 '
                '(design60.py: bare -= mirrored(box(9.3, bank, -3, 14.5, -8, 3.4)) ^ ribs). '
                'On the left the inboard rib roots stayed as three diagonal strips hanging from the saddle side wall, '
                'ending in air. R61-R66 copied them unchanged.'),
        search_box_mm=list(d.STUB_ZONE), ring_keep_radius_mm=d.RING_KEEP_R,
        stub_in_r66=[dict(volume_mm3=round(r['volume'], 3), lo=r['lo'].round(2).tolist(), hi=r['hi'].round(2).tolist(),
                          touches_only_saddle_face=r['free']) for r in stubs],
        history=stub_history(),
        removed_mm3=mm3(before, d.saddle_stub_cutter()),
        pieces_in_box=dict(r66=rows_before, r67=rows_after),
        unchanged_mm3=dict(rod_ring=[vol(before ^ ring), vol(body ^ ring)], saddle_and_stem=[vol(before ^ stem), vol(body ^ stem)],
                           left_guard=[vol(before ^ guard), vol(body ^ guard)], right_side_material=[vol(before ^ right), vol(body ^ right)]),
        right_side_mirror_overlap_mm3=mm3(stubs[0]['solid'].mirror((1, 0, 0)), before ^ right) if stubs else None,
        full_rod_overlap_mm3=dict(r66=mm3(before, rod), r67=mm3(body, rod)))
    r = report
    free_after = [v for v, free in rows_after if free and v > .6]
    r['gates'] = [len(stubs) == 1, abs(r['removed_mm3'] - stubs[0]['volume']) < .05 if stubs else False,
                  not free_after,
                  all(abs(a - c) < .002 for a, c in r['unchanged_mm3'].values()),
                  r['full_rod_overlap_mm3']['r67'] == r['full_rod_overlap_mm3']['r66'],
                  not r['history']['R59'] and all(r['history'][k] for k in ('R60', 'R63', 'R64', 'R66'))]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- OP1
def free_radius(section, centre, limit=12.0):
    lo, hi = 0.0, limit
    for _ in range(26):
        mid = (lo + hi) / 2
        if (section ^ mf.CrossSection.circle(mid, 96).translate(centre)).area() > 1e-5:
            hi = mid
        else:
            lo = mid
    return round(lo, 2)


def approach(body):
    """Free radius round the vertical line the tipped plug's lead exit follows, below the deck,
    with the 500 mm rod and fitted keys in place (switch out)."""
    rod = c66.full_rod()
    keys = d.r66.r64.fitted_key_hardware()
    keys.pop('rod')
    obstacles = b.union([body, rod, *keys.values()])
    centre = tuple(float(v) for v in r66.THREAD_XY)
    rows = {f'z{z:g}': free_radius(obstacles.slice(float(z)), centre) for z in np.arange(-16.0, 7.01, 1.0)}
    return dict(axis_xy_mm=list(r66.THREAD_XY), free_radius_by_height_mm=rows, narrowest_mm=min(rows.values()),
                note='Largest empty circle centred on the path; the tipped plug is 3.1 x 6.2 mm (photo estimate).')


def op1(body, before, r63):
    report = c66.op1_route(body, r63)
    report['revision'] = 'R67'
    lead = d.plug_lead_in()
    removed = before ^ lead
    report['lead_in'] = dict(
        size_mm=d.LEAD_IN, top_z_mm=d.LEAD_IN_TOP, floor_z_mm=d.LEAD_IN_FLOOR, board_seat_z_mm=b.PCB_Z,
        removed_mm3=mm3(before, lead), removed_max_z_mm=round(float(removed.bounding_box()[5]), 3) if not removed.is_empty() else None,
        seat_support_mm2={f'z{z}': dict(r66=c66.seat_support(before, z), r67=c66.seat_support(body, z)) for z in (8.8, 9.05, 9.3)},
        three_holes=dict(r66=c66.socket_holes(before), r67=c66.socket_holes(body)),
        stops=dict(r66=r66.r64.seating_measurements(before, r63)['board_shift_1mm_into_stops_at_0_2mm_lift_mm3'],
                   r67=report['lid']['board_shift_1mm_into_stops_at_0_2mm_lift_mm3']))
    report['approach_below_deck'] = approach(body)
    report['plug_evidence'] = ('Endgame Gear OP1 Universal Switch Set (EGG-SP-U1 / PER-EGG-01645). No dimensioned drawing of the '
                               'plug or housing exists in the project; the 3.1 x 6.2 x 3.65 mm plug is estimated from photos.')
    li = report['lead_in']
    same_seat = all(v['r67'] == v['r66'] for v in li['seat_support_mm2'].values())
    same_holes = all(a[k] == c[k] for a, c in zip(li['three_holes']['r66'], li['three_holes']['r67']) for k in ('z9.05', 'z8.3'))
    report['gates'] = report['gates'] + [li['removed_max_z_mm'] is not None and li['removed_max_z_mm'] <= d.LEAD_IN_TOP + .01,
                                         same_seat, same_holes, li['stops']['r66'] == li['stops']['r67'],
                                         report['approach_below_deck']['narrowest_mm'] > 0]
    report['passes'] = all(report['gates'])
    return report


# ----------------------------------------------------------------------- main
def write(name, report, carrier):
    report['carrier_sha256'] = carrier
    report['generator_sha256'] = digest(d.__file__)
    (OUT / name).write_text(json.dumps(report, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)) + '\n')
    print(name, 'passes', report['passes'], report.get('gates'), flush=True)


def main():
    body = b.load(OUT / d.HOLDER)
    before = d.r66_carrier()
    r63 = b.load(r66.R63_CARRIER)
    r64_body = b.load(r66.R64_OUT / d.HOLDER)
    carrier = digest(OUT / d.HOLDER)
    results = {}
    for name, make in (('subtraction.json', lambda: subtraction(body, before)),
                       ('battery.json', lambda: battery(body, before, r64_body)),
                       ('saddle.json', lambda: saddle(body, before)),
                       ('op1-route.json', lambda: op1(body, before, r63))):
        results[name] = make()
        write(name, results[name], carrier)
    checked, obstructions, sweeps = c66.key_routes(body)
    summary = dict(revision='R67', physical_fit_verified=False, carrier_sha256=carrier, r66_carrier_sha256=d.R66_SHA256,
                   generator_sha256=digest(d.__file__), checks_sha256=digest(__file__),
                   carrier_components=len(body.decompose()), key_poses_checked=checked, key_obstructions=obstructions,
                   socket_backer_sweeps_mm3=sweeps,
                   removed_from_r66_mm3=results['subtraction.json']['removed_from_r66_mm3'],
                   **{k.replace('.json', '').replace('-', '_') + '_passes': v['passes'] for k, v in results.items()})
    summary['passes'] = bool(all(v['passes'] for v in results.values()) and not obstructions and checked == 336
                             and max(sweeps.values()) < .01 and summary['carrier_components'] == 1)
    (OUT / 'carrier.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=1), flush=True)
    if not summary['passes']:
        sys.exit('R67 carrier checks failed')


if __name__ == '__main__':
    main()
