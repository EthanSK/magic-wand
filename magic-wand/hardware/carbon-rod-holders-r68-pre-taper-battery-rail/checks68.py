"""CAD checks for the R68 carrier: R67 everywhere except the battery restore box, R64 inside it.

* restore.json      the export equals R67 outside the restore box and R64 inside it, section
                    by section; R63, R64 and R65 are identical inside it; the box reverts
                    nothing R66 and R67 left unchanged
* battery.json      the outboard wall and lip at full depth to the bed face, the spring leaf,
                    shoe, root post, slide and retention, all against R64; and the base fins
                    at the battery corner, clear of both lips
* saddle.json       the R67 saddle checks run on R68 (the stubs stay removed)
* op1-route.json    the R67 OP1 checks run on R68 (three holes, seat, stops, lead-in, route)
* carrier.json      summary, key socket routes and the bound carrier SHA-256

In saddle.json and op1-route.json the current carrier's values sit under `r68` keys and the
R66 reference under `r66`. Exits non-zero when a gate fails. Slice checks live in audit68.py.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import design68 as d
import kit68
import checks66 as c66
import checks67 as c67

r66, r67, b, old = d.r66, d.r67, d.b, d.old
OUT = d.OUT
HARDWARE = d.HARDWARE
mm3 = c66.mm3
vol = c67.vol
R65_CARRIER = HARDWARE / 'carbon-rod-holders-r65-op1-seat' / 'exports' / d.HOLDER


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def relabel(value):
    """R67 report fields name the current carrier `r67`; here the current carrier is R68."""
    if isinstance(value, dict):
        return {('r68' if k == 'r67' else k): relabel(v) for k, v in value.items()}
    if isinstance(value, list):
        return [relabel(v) for v in value]
    return value


# ----------------------------------------------------------------------- restore
def restore(body, r67_body, r64_body):
    box = d.restore_region()
    outside = b.box(-200, 200, -200, 200, -200, 200) - box
    taper_region = b.box(*r66.OUTBOARD_ZONE) + r67.battery_corner_cutter()
    elsewhere_in_box = box - taper_region
    others = {'R63': b.load(r66.R63_CARRIER), 'R65': b.load(R65_CARRIER)}
    report = dict(
        revision='R68', physical_fit_verified=False, restore_box_mm=[round(v, 3) for v in d.RESTORE_BOX],
        r67_carrier_sha256=d.R67_SHA256, r64_carrier_sha256=d.R64_SHA256,
        volume_mm3=dict(r67=vol(r67_body), r68=vol(body), r64_in_box=vol(r64_body ^ box), r67_in_box=vol(r67_body ^ box),
                        r68_in_box=vol(body ^ box)),
        sections_outside_box_against_r67=c67.section_difference(r67_body ^ outside, body ^ outside),
        sections_inside_box_against_r64=c67.section_difference(r64_body ^ box, body ^ box),
        pre_taper_in_box_mm3={k: vol(m ^ box) for k, m in others.items()},
        pre_taper_sections_against_r64={k: c67.section_difference(r64_body ^ box, m ^ box) for k, m in others.items()},
        design66_outboard_original_against_r64_zone_mm3=[
            vol(r66.outboard_original() - (r64_body ^ b.box(*r66.OUTBOARD_ZONE))),
            vol((r64_body ^ b.box(*r66.OUTBOARD_ZONE)) - r66.outboard_original())],
        # Material in the box outside R66's zone and R67's corner cut: the box reverts nothing there.
        box_beyond_taper_mm3=dict(r64=vol(r64_body ^ elsewhere_in_box), r67=vol(r67_body ^ elsewhere_in_box)),
        restored_mm3=round(float((r64_body ^ box).volume() - (r67_body ^ box).volume()), 4),
        components=len(body.decompose()))
    r = report
    v = r['volume_mm3']
    identity = v['r67'] - v['r67_in_box'] + v['r64_in_box']
    r['volume_identity_mm3'] = dict(expected=round(identity, 4), actual=v['r68'], difference=round(v['r68'] - identity, 4))
    r['gates'] = [abs(r['volume_identity_mm3']['difference']) < .01,
                  r['sections_outside_box_against_r67']['max_area_mm2'] < .0025,
                  r['sections_inside_box_against_r64']['max_area_mm2'] < .0025,
                  all(abs(x - v['r64_in_box']) < .001 for x in r['pre_taper_in_box_mm3'].values()),
                  all(s['max_area_mm2'] < .0025 for s in r['pre_taper_sections_against_r64'].values()),
                  max(r['design66_outboard_original_against_r64_zone_mm3']) < .01,
                  abs(r['box_beyond_taper_mm3']['r64'] - r['box_beyond_taper_mm3']['r67']) < .005,
                  r['components'] == 1]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- battery
def base_fins(body_path):
    """The kit68 base fins round the battery in the bed frame: none on either lip."""
    sys.path.insert(0, str(HARDWARE / 'carbon-rod-holders-r55-easy-release'))
    import panel55
    row = next(r for r in kit68.parts() if r['name'] == 'Key_Carrier')
    pose = np.asarray(row['assembly_to_print'], float)[:3].copy()
    pose[:2, 3] = 0
    body = b.load(body_path).transform(pose.tolist())
    base, necks, lay = panel55.p54.base54(body, panel55.settings(row['panel']))
    windows = {'outer_free_lip': [-21.55, old.LOW - .1, -18.7, old.LIP_TOP + .05],
               'inner_free_lip': [-11.95, old.LOW - .1, -9.55, old.LIP_TOP + .05],
               'root_below': [-25.5, old.LOW - 1, -22.4, old.LOW + 1.1],
               'root_above': [-25.5, old.DECK - .35, -22.4, old.DECK + 2.5]}
    joined = b.union([n ^ body for n in necks])
    fins = [dict(face=root['tie']['face'], at=root['tie']['at'], height=root['tie']['height'],
                 into_holder_mm3=round(float((n ^ body).volume()), 3)) for root, n in zip(lay['roots'], necks)]
    contact = {k: round(float((joined ^ b.box(x0, x1, y0, y1, -1, 10)).volume()), 3) for k, (x0, y0, x1, y1) in windows.items()}
    return dict(windows_bed_frame_xy=windows, fins=fins, fin_material_in_holder_mm3=contact,
                base_pieces=len(base.decompose()), backed_pieces=len(kit68.panel_builder(body, row['panel']).decompose()))


def battery(body, r64_body, r67_body):
    pack = old.pack()
    leaf_zone = b.box(old.LEAF_X[0] - .01, old.PACK_X[0] + .3, old.PACK_Y0, old.BED - 5.5, old.PACK_Z[0], old.DECK)
    lip = old.LIP_TOP + .01
    rows = {k: c66.rail_profile(m) for k, m in (('r64', r64_body), ('r67', r67_body), ('r68', body))}
    slide = [pack.translate((0, dy, 0)) for dy in np.arange(0, 30.1, .5)]
    drop = pack.translate((0, 0, -.30))     # pouch pushed away from the deck
    inboard = b.box(old.PACK_X[1] - old.LIP_W, old.PACK_X[1] + 1, 15, 50, -1, old.PACK_Z[0])
    outboard = b.box(old.WALL_FACE - 1, old.PACK_X[0] + old.LIP_W, 15, 50, -1, old.PACK_Z[0])
    root_zone = b.box(old.WALL_FACE - .02, old.PACK_X[0] - .37, old.BED - 5.5, old.BED, old.LIP_TOP - .02, old.DECK + .01)
    bed_corner = mf.CrossSection.square((10, 12)).translate((-26, -12))
    each = lambda f: {k: f(m) for k, m in (('r64', r64_body), ('r67', r67_body), ('r68', body))}
    report = dict(
        revision='R68', physical_fit_verified=False,
        outboard_full_depth_y_mm={k: c66.extent(v, 'outboard_wall_bottom', old.LOW + .05) for k, v in rows.items()},
        outboard_lip_under_pack_y_mm={k: c66.extent(v, 'outboard_lip_bottom', lip) for k, v in rows.items()},
        inboard_full_depth_y_mm={k: c66.extent(v, 'inboard_rail_bottom', old.LOW + .05) for k, v in rows.items()},
        inboard_lip_y_mm={k: c66.extent(v, 'inboard_lip_bottom', lip) for k, v in rows.items()},
        outboard_edge_x_mm={f'y{y:g}': each(lambda m: c67.outboard_edge(m, y)) for y in (30.0, 34.0, 38.0, 41.0, 43.0, 43.6)},
        # The leaf shoe deliberately stands 0.21 mm into the nominal pouch: that is the spring preload.
        shoe_preload_overlap_mm3=each(lambda m: mm3(pack, m ^ leaf_zone)),
        spring_leaf_and_shoe_xor_r64_mm3=round(float(((body ^ leaf_zone) - (r64_body ^ leaf_zone)).volume()
                                                     + ((r64_body ^ leaf_zone) - (body ^ leaf_zone)).volume()), 5),
        pack_seated_to_carrier_outside_spring_mm3=mm3(pack, body - leaf_zone),
        pack_slide_from_rear_to_carrier_outside_spring_mm3=max(mm3(p, body - leaf_zone) for p in slide),
        pack_to_deck_gap_mm=round(old.DECK - old.PACK_Z[1], 3),
        pack_beyond_bed_face_mm=round(old.PACK_Y0 + old.PACK[1] - old.BED, 2),
        retention_pack_dropped_0_3mm_mm3=each(lambda m: dict(inboard=mm3(drop, m ^ inboard), outboard=mm3(drop, m ^ outboard))),
        spring_root_post_mm3=each(lambda m: vol(m ^ root_zone)),
        bed_face_area_in_corner_mm2=each(lambda m: round((m.rotate((90, 0, 0)).slice(old.BED - .02) ^ bed_corner).area(), 3)),
        base_fins=base_fins(OUT / d.HOLDER),
        profile_every_0_5mm=rows['r68'])
    r = report
    fins = r['base_fins']['fin_material_in_holder_mm3']
    r['gates'] = [r['outboard_full_depth_y_mm']['r68'] == r['outboard_full_depth_y_mm']['r64'],
                  r['outboard_full_depth_y_mm']['r68'][1] >= old.BED - .6,
                  r['outboard_lip_under_pack_y_mm']['r68'] == r['outboard_lip_under_pack_y_mm']['r64'],
                  r['inboard_full_depth_y_mm']['r68'] == r['inboard_full_depth_y_mm']['r64'],
                  all(e['r68'] == e['r64'] for e in r['outboard_edge_x_mm'].values()),
                  abs(r['shoe_preload_overlap_mm3']['r68'] - r['shoe_preload_overlap_mm3']['r64']) < .001,
                  r['spring_leaf_and_shoe_xor_r64_mm3'] < .01,
                  r['pack_seated_to_carrier_outside_spring_mm3'] < .001,
                  r['pack_slide_from_rear_to_carrier_outside_spring_mm3'] < .001,
                  r['retention_pack_dropped_0_3mm_mm3']['r68'] == r['retention_pack_dropped_0_3mm_mm3']['r64'],
                  abs(r['spring_root_post_mm3']['r68'] - r['spring_root_post_mm3']['r64']) < .005,
                  fins['outer_free_lip'] == 0 and fins['inner_free_lip'] == 0,
                  fins['root_below'] > .5 and fins['root_above'] > .5,
                  r['base_fins']['backed_pieces'] == 1]
    r['passes'] = all(r['gates'])
    return report


# ----------------------------------------------------------------------- R67 checks on R68
def saddle(body, r66_body):
    report = relabel(c67.saddle(body, r66_body))
    report['revision'] = 'R68'
    return report


def op1(body, r66_body, r63):
    report = relabel(c67.op1(body, r66_body, r63))
    # The inherited R66 checker labels its current-body measurements r66;
    # these top-level rows measure R68, unlike the lead-in reference. GPT-6.1 Sol.
    report['three_holes']['r68'] = report['three_holes'].pop('r66')
    for row in report['seat_support_mm2'].values():
        row['r68'] = row.pop('r66')
    report['revision'] = 'R68'
    return report


# ----------------------------------------------------------------------- main
def write(name, report, carrier):
    report['carrier_sha256'] = carrier
    report['generator_sha256'] = digest(d.__file__)
    (OUT / name).write_text(json.dumps(report, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)) + '\n')
    print(name, 'passes', report['passes'], report.get('gates'), flush=True)


def main():
    body = b.load(OUT / d.HOLDER)
    r67_body = d.r67_carrier()
    r64_body = d.pre_taper_carrier()
    r66_body = r67.r66_carrier()
    r63 = b.load(r66.R63_CARRIER)
    carrier = digest(OUT / d.HOLDER)
    results = {}
    for name, make in (('restore.json', lambda: restore(body, r67_body, r64_body)),
                       ('battery.json', lambda: battery(body, r64_body, r67_body)),
                       ('saddle.json', lambda: saddle(body, r66_body)),
                       ('op1-route.json', lambda: op1(body, r66_body, r63))):
        results[name] = make()
        write(name, results[name], carrier)
    checked, obstructions, sweeps = c66.key_routes(body)
    summary = dict(revision='R68', physical_fit_verified=False, carrier_sha256=carrier,
                   r67_carrier_sha256=d.R67_SHA256, r64_carrier_sha256=d.R64_SHA256,
                   generator_sha256=digest(d.__file__), checks_sha256=digest(__file__),
                   carrier_components=len(body.decompose()), key_poses_checked=checked, key_obstructions=obstructions,
                   socket_backer_sweeps_mm3=sweeps, restored_mm3=results['restore.json']['restored_mm3'],
                   **{k.replace('.json', '').replace('-', '_') + '_passes': v['passes'] for k, v in results.items()})
    summary['passes'] = bool(all(v['passes'] for v in results.values()) and not obstructions and checked == 336
                             and max(sweeps.values()) < .01 and summary['carrier_components'] == 1)
    (OUT / 'carrier.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=1), flush=True)
    if not summary['passes']:
        sys.exit('R68 carrier checks failed')


if __name__ == '__main__':
    main()
