"""Check the complete R70 kit against deposited PETG in a native slice.

`click` and `routes` check CAD meshes. `audit` checks native deposited paths using R69's auditor
pointed at the R70 parts, with what R70 changed rebuilt here:

* hinge: every pin, clip, barrel and lead gauge sits on the unchanged pin line, read from
  hinge70; the bearing blocks now stand on the rear face;
* rear face: Y 36.45, so the tight rod rings are 7.20 mm nearer the bed than in R69;
* right upper key: every inherited route of that key is moved 2 mm with it;
* OP1: the plug rises on R69's checked line, read from keys.json;
* battery spring: the two gauges for the leaf's free space and the probe across its shoe
  are rebuilt for the shorter leaf and the moved shoe;
* base: five fins. The joint windows at the bed face are R70's: both lips and the roof over
  the pouch must be free of base plastic, and both fins of the battery corner block must
  be joined. R69's plate fails the roof window, as it should;
* kit: nine parts.

    audit70.py click                       CAD click, lift and assembly fit (writes click-fit.json)
    audit70.py routes                      every route against the CAD meshes: worst overlap per route
    audit70.py audit SLICE_DIRECTORY       every deposited-bead check on one native slice
 — Claude Fable 5.2"""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile

import numpy as np

import audit69 as a69
import checks70
import design70 as d
import hinge70
import kit70

v, a61, a64, a66, audit68, b, o = a69.v, a69.a61, a69.a64, a69.a66, a69.audit68, d.b, d.old
OUT = kit70.OUT
SHIFT = (0., -d.KEY_SHIFT, 0.)
PLUG_ROUTE_MARGIN = a69.PLUG_ROUTE_MARGIN
PRINT_NAME = 'R70-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'
REPORTS=a69.REPORTS
RING_PRINT_HEIGHTS = (d.BED - 19.75, d.BED - 9.25)        # the front ring, as heights above the bed
SHOE_STATIONS = tuple(d.SHOE_Y[0] + v for v in (.8, 1.8, 2.8))   # assembly Y on the leaf's shoe (R63: Y 27.9, 28.9, 29.9)
_r69_routes = a69.routes


def bind():
    """Point R69's auditor, and through it the inherited ones, at the R70 parts. — Claude Fable 5.2"""
    a69.d, a69.hinge69, a69.kit69, a69.OUT = d, hinge70, kit70, OUT
    a69.RING_PRINT_HEIGHTS, a69.PRINT_NAME, a69.CAD_REPORTS = RING_PRINT_HEIGHTS, PRINT_NAME, checks70.REPORTS
    a69.op1_routes, a69.routes, a69.battery_regions = op1_routes, routes, battery_regions
    a69.bind()


def op1_routes():
    best = v.read(OUT / 'keys.json')['kept_in_place']['plug_margin_on_the_r69_route_mm']['route']
    x, y = best['centre_world_xy_mm']
    column = [a69.checks69.plug_box(PLUG_ROUTE_MARGIN, best['wide_side_yaw_deg']).translate((x, y, float(z))) for z in np.arange(-14., 13.01, .5)]
    found = {'op1_plug_rises_through_window': column, 'op1_lead_in_channel': [d.r66.lead_solid('route')]}
    for name in ('board', 'sockets', 'housing', 'plug', 'lead'):
        found[f'op1_{name}_lowered_onto_seat'] = [d.r66.drop_route(name, bearing_skin=.20 if name == 'board' else 0.0)]
    return found


def routes():
    """R69's routes on the R70 parts, with every route of the right upper key moved with it. — Claude Fable 5.2"""
    groups = _r69_routes()
    moved = 0
    for group in groups.values():
        for name in list(group):
            if name.startswith('key_4_'):
                group[name] = [solid.translate(SHIFT) for solid in group[name]]
                moved += 1
    assert moved >= 5, moved
    groups['Key_Carrier'].update(spring_gauges())
    return groups


def spring_gauges():
    """R63's two windows round the leaf, for the R70 leaf: a 0.40 mm window in the 0.68 mm gap
    behind it, and the slot between it and the lip under it. Both end before the new root. — Claude Fable 5.2"""
    end = d.BED - d.ROOT_LENGTH - .40
    return {'side_leaf_can_flex': [b.box(o.WALL_FACE + .14, o.WALL_FACE + .54, o.PACK_Y0 + 2.5, end, d.LEAF_Z[0] + .24, d.LEAF_Z[1] - .20)],
            'leaf_is_free_of_floor': [b.box(o.LEAF_X[0] + .25, o.LEAF_X[1] - .15, o.PACK_Y0 + 2.7, end, o.LIP_TOP + .12, d.LEAF_Z[0] - .17)]}


def spring_opening(points, position):
    """Opposing deposited faces at mid height of the pack, across the moved shoe: the method of
    the R60 and R63 audits at the R70 stations. Used in the native deposition audit. — Claude Fable 5.2"""
    assert np.allclose(position[:3, :3], [[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    x0, y0, z0 = position[:3, 3]
    probe = y0 + (o.PACK_Z[0] + o.PACK_Z[1]) / 2
    centre = points[(points[:, 0] > x0 + o.PACK_X[0] - 3) & (points[:, 0] < x0 + o.PACK_X[1] + 3) & (abs(points[:, 1] - probe) < points[:, 3] / 2)]
    rows = []
    for depth in SHOE_STATIONS:
        line = centre[abs(z0 - centre[:, 2] - depth) < .11]
        dx = np.sqrt(np.maximum(0, (line[:, 3] / 2) ** 2 - (line[:, 1] - probe) ** 2))
        on_spring = line[:, 0] < x0 + sum(o.PACK_X) / 2
        assert on_spring.any() and (~on_spring).any()
        opening = float((line[~on_spring, 0] - dx[~on_spring]).min() - (line[on_spring, 0] + dx[on_spring]).max())
        rows.append(dict(depth_mm=round(depth, 2), opening_mm=round(opening, 3), nominal_pack_interference_mm=round(o.PACK[0] - opening, 3)))
    assert all(0 < row['nominal_pack_interference_mm'] < .35 for row in rows), rows
    return rows


def cad_routes():
    """The routes against the CAD meshes, before any slice exists: worst overlap per route. — Claude Fable 5.2"""
    bind()
    meshes = {'Key_Carrier': b.load(OUT / d.HOLDER), 'Touch_Paddle': b.load(OUT / hinge70.PADDLE), 'OP1_Lid_Stop': b.load(OUT / hinge70.LID)}
    rows = {}
    for part, group in routes().items():
        if part in meshes:
            for name, solids in group.items():
                rows[f'{part}/{name}'] = round(max(float((meshes[part] ^ s).volume()) for s in solids), 4)
    return rows


def click():
    bind()
    fit = a69.checks69.fit.run(OUT / d.HOLDER, OUT / hinge70.PADDLE, OUT / hinge70.WIRES, OUT / hinge70.LID)
    fit.update(revision='R70', carrier_sha256=v.digest(OUT / d.HOLDER))
    (OUT / 'click-fit.json').write_text(json.dumps(fit, indent=2, default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x)) + '\n')
    return fit


def battery_regions():
    """Bed-frame windows (print X = assembly X, print Y = assembly Z) at the rear face. — Claude Fable 5.2"""
    return {'outer_free_lip': [-21.55, o.LOW - .1, -18.7, o.LIP_TOP + .05],
            'inner_free_lip': [-11.95, o.LOW - .1, -9.55, o.LIP_TOP + .05],
            'roof_over_the_pouch': [-21.5, o.DECK + .9, -18.4, o.DECK + 2.5],
            'root_below': [-24.4, o.LOW - 1, -21.7, o.LOW + 1.1],
            'root_above': [-24.4, o.DECK - .35, -21.7, o.DECK + 2.5]}


def verify_base(folder):
    frame = v.read(folder / 'layout.frame.json')
    row = frame['parts']['Key_Carrier']
    body = v.load_solid(OUT / row['source'])
    pose = np.asarray(row['assembly_to_machine'])
    oriented = pose[:3].copy()
    oriented[:2, 3] = 0
    panel = row['adhesion_panel']
    posed = body.transform(oriented)
    base, _, _ = v.base54(posed, v.settings(panel))
    for cut in kit70.neck_cuts(posed, panel):
        base -= cut
    regions = battery_regions()
    archive = folder / v.ARCHIVE
    joint = v.seam(archive, frame, body, regions=regions, regional_base=base.translate((*pose[:2, 3], 0)))
    areas = joint['regional_joint_area_mm2']
    free = ('outer_free_lip', 'inner_free_lip', 'roof_over_the_pouch')
    report = dict(archive_sha256=v.digest(archive), regions=regions, contacts_mm2=areas, passes=bool(
        all(areas[n] < .05 for n in free) and all(areas[n] > .4 for n in ('root_below', 'root_above'))))
    v.write(folder / 'battery-base.json', report)
    assert report['passes'], areas


def fin_removal_note(folder):
    path = folder / 'fin-design.json'
    report = v.read(path)
    counts = {face: sum(fin['face'] == face for fin in report['fins']) for face in ('-y', '+y')}
    assert counts == {'-y': 3, '+y': 2}, counts
    report['removal'] = v.read(OUT / 'base.json')['release']
    v.write(path, report)


def audit(folder):
    bind()
    for name in checks70.REPORTS:
        report = v.read(OUT / name)
        assert report['carrier_sha256'] == v.digest(OUT / d.HOLDER) and report['passes'], name
    a69.mounts(folder)
    verify_base(folder)
    reference=r69_base_reference(folder)
    a61.audit(folder, kit70.parts, OUT, expected_names=kit70.COMPLETE, route_builder=routes,
              spring_probe=spring_opening, base_minima=dict(a61.MINIMA), expected_fin_count=len(kit70.CARRIER_TIES),
              seam_layers=25,seam_reference_area_mm2=reference['regional_joint_area_mm2']['all_base_contacts'])
    fit_report = v.read(folder / 'fit.json')
    fit_report['guide_sha256'] = v.digest(OUT / 'assembly-guide.json')
    v.write(folder / 'fit.json', fit_report)
    fin_removal_note(folder)
    seat = a69.printed_seat_report(folder, render=True)
    assert seat['passes'], seat
    # The inherited plot calls its current archive R69; identify this trial
    # explicitly without changing the immutable R69 comparison source.
    seat['audited_revision']='R70'
    seat['versions']['R70']=seat['versions'].pop('R69')
    seat['r70_fraction_of_r63']=seat.pop('r69_fraction_of_r63')
    seat['plot_label_aliases']={'R69':'R70 (the current audited archive)'}
    v.write(folder/'printed-seat.json',seat)


def r69_base_reference(folder):
    """Compare complete tie heights in both the fitted and new slices, using one method.

    The inherited first-2.4-mm window missed R70's upper deck bonds. All 25 layers
    cover both sets of ties, with a neighbouring-base witness rather than crediting
    permanent walls. Found and fixed by GPT-6.1 Sol. — GPT-6.1 Sol
    """
    prior=d.r69.OUT/'print-mechanisms'
    frame=v.read(prior/'layout.frame.json');row=frame['parts']['Key_Carrier']
    body=v.load_solid(d.r69.OUT/row['source']);pose=np.asarray(row['assembly_to_machine'])
    oriented=pose[:3].copy();oriented[:2,3]=0
    base,_,_=v.base54(body.transform(oriented),v.settings(row['adhesion_panel']))
    report=v.seam(prior/v.ARCHIVE,frame,body,regions={'all_base_contacts':[-100,-100,100,100]},
                  regional_base=base.translate((*pose[:2,3],0)),max_layers=25)
    report.update(frame_sha256=v.digest(prior/'layout.frame.json'),carrier_sha256=v.digest(d.r69.OUT/row['source']),
                  seam_layers=25,physical_strength_verified=False)
    v.write(folder/'r69-base-reference.json',report)
    return report


def release(primary, reopened):
    """Package only the reviewed, matching R70 source and twice-sliced evidence.

    Reuse the established native/package checks, with R70's own CAD reports and
    section evidence rather than R69's obsolete cheek-ramp requirements.
    — GPT-6.1 Sol
    """
    release61=kit70.kit64.kit63.kit62.release61
    layout=v.digest(primary/'layout.3mf')
    archive,warning=release61.checked(primary,layout,kit70.parts,reports=REPORTS)
    other,other_warning=release61.checked(reopened,layout,kit70.parts,reports=REPORTS)
    meshes={row['source'].name:v.digest(row['source']) for row in kit70.parts()}
    for name in checks70.REPORTS:
        report=v.read(OUT/name)
        assert report['passes'] and report['carrier_sha256']==meshes[d.HOLDER],name
    source=v.read(OUT/'source-reproduction.json')
    assert source['passes'] and all(row['export_sha256']==meshes.get(name,v.digest(OUT/name))==row['reproduced_sha256'] for name,row in source['meshes'].items())
    guide=v.digest(OUT/'assembly-guide.json')
    for folder in (primary,reopened):
        sections=v.read(folder/'mechanical-sections.json')
        assert sections['passes'] and sections['checker_sha256']==v.digest(Path(__file__).with_name('sections70.py'))
        assert sections['frame_sha256']==v.digest(folder/'layout.frame.json') and set(sections['parts'])==kit70.COMPLETE
        assert all(v.digest(folder/name)==digest for name,digest in sections['images'].items())
        assert v.read(folder/'fit.json')['guide_sha256']==guide
        supplement=v.read(folder/'supplemental-evidence.json')
        assert supplement['passes'] and supplement['guide_sha256']==guide
        assert v.read(folder/'printed-seat.json')['passes'] and v.read(folder/'battery-base.json')['passes']
    review=v.read(primary/'review.json')
    assert review['archive_sha256']==archive and review['reopened_sha256']==other and review['trial_approved']
    assert set(review['per_part'])==kit70.COMPLETE
    assert review['native_warning']['reviewed_archive_warnings']=={s:w for s,w in ((archive,warning),(other,other_warning)) if w}
    assert review['native_warning']['evidence']
    dest=OUT/'print-mechanisms';dest.mkdir(exist_ok=True)
    for name in ('layout.3mf','layout.frame.json',v.ARCHIVE,'review.json','r69-base-reference.json',*REPORTS,'critical-native-layers.png','op1-seat-comparison.png'):
        copyfile(primary/name,dest/name)
    for name in (*REPORTS,'critical-native-layers.png'):
        copyfile(reopened/name,dest/('reopened-'+name))
    v.write(dest/'reopened.json',dict(layout_sha256=layout,checked_archive=archive,reopened_archive=other))
    with ZipFile(primary/v.ARCHIVE) as data:
        (dest/'tray.png').write_bytes(data.read('Metadata/top_1.png'))
    return release61.package(primary/v.ARCHIVE,dest/PRINT_NAME,kit70.COMPLETE,[dest/n for n in (*REPORTS,'review.json','reopened.json')])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('click')
    actions.add_parser('routes')
    actions.add_parser('audit').add_argument('folder', type=Path)
    pack=actions.add_parser('release')
    pack.add_argument('primary',type=Path)
    pack.add_argument('reopened',type=Path)
    args = parser.parse_args()
    if args.action == 'click':
        print(json.dumps(click(), indent=2, default=str))
    elif args.action == 'routes':
        print(json.dumps(cad_routes(), indent=1))
    elif args.action=='audit':
        audit(args.folder)
    else:
        release(args.primary,args.reopened)
