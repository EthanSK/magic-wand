"""Check the complete R69 kit against deposited PETG in a native slice.

`click` runs without a slice; `audit` checks the exact native deposition. The inherited
auditors were written for R64's hinge line, R66's
plug route and a rod bore that is clear everywhere. R69 changes all three, so this file
rebuilds their inputs instead of reusing R68's:

* hinge: every pin, clip, barrel and lead gauge is built on the R69 pin line (hinge69);
* OP1: the plug rises on the line checks69 found, with 0.4 mm round the estimated plug;
  the board, sockets, housing, plug and lead still drop exactly as in R66;
* rod: the restored contact rings and short saddle are meant to print under 8 mm. Every
  tight layer is compared with the fitted R58 nominal shape; the bed-face funnel stays open;
* retainer: the paddle's far-end press poses are added as routes against the retainer;
* kit: twelve parts, no Rod_Collet.

    audit69.py click                       CAD click, lift and assembly fit (writes click-fit.json)
    audit69.py audit SLICE_DIRECTORY       every deposited-bead check on one native slice
    audit69.py release PRIMARY REOPENED    package the reviewed, matching pair of slices
 — Claude Fable 5.2; GPT-6.1 Sol"""
import argparse
import json
import math
from pathlib import Path
from shutil import copyfile

import numpy as np
from shapely.geometry import LineString, Point

import audit68
import checks69
import design69 as d
import hinge69
import kit69

a66 = audit68.prior                 # audit66
a64 = a66.prior                     # audit64
v, a61, b, o = audit68.v, audit68.a61, d.b, d.old
OUT = kit69.OUT
REPORTS = (*audit68.REPORTS, 'mechanical-sections.json')
PRINT_NAME = 'R69-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'
CAD_REPORTS = ('hinge.json', 'keeper.json', 'op1.json', 'rod.json', 'carrier.json')
PLUG_ROUTE_MARGIN = 0.40
RING_PRINT_HEIGHTS = (o.BED - 19.75, o.BED - 9.25)       # the front ring, as heights above the bed


def audit(folder):
    for name in CAD_REPORTS:
        report = v.read(OUT / name)
        assert report['carrier_sha256'] == v.digest(OUT / d.HOLDER) and report['passes'], name
    mounts(folder)
    verify_base(folder)
    backers = {r['name'].split('_')[-1]: r['source'] for r in kit69.parts() if r['name'].startswith('Socket_Backer')}
    a61.audit(folder, kit69.parts, OUT, expected_names=kit69.COMPLETE, route_builder=routes,
              spring_probe=a66.prior.spring_opening, backer_rows=backers, base_minima=dict(a61.MINIMA))
    fit_report = v.read(folder / 'fit.json')
    fit_report['guide_sha256'] = v.digest(OUT / 'assembly-guide.json')
    v.write(folder / 'fit.json', fit_report)
    audit68.fin_removal_note(folder)
    seat = printed_seat_report(folder, render=True)
    assert seat['passes'], seat


def release(primary, reopened):
    carrier = v.digest(OUT / d.HOLDER)
    for name in (*CAD_REPORTS, 'click-fit.json'):
        report = v.read(OUT / name)
        assert report['carrier_sha256'] == carrier, name
        if name != 'click-fit.json':
            assert report['passes'], name
    sources = {row['source'].name: row['source'] for row in kit69.parts()}
    sources[hinge69.WIRES] = OUT / hinge69.WIRES
    fitted = v.read(OUT / 'click-fit.json')['assembled_sha256']
    assert all(v.digest(sources[name]) == sha for name, sha in fitted.items())
    for folder in (primary, reopened):
        assert v.read(folder / 'printed-seat.json')['passes'] and v.read(folder / 'battery-base.json')['passes']
        supplemental = v.read(folder / 'supplemental-evidence.json')
        assert supplemental['passes'] and supplemental['archive_sha256'] == v.digest(folder / v.ARCHIVE)
        assert supplemental['carrier_sha256'] == carrier and supplemental['guide_sha256'] == v.digest(OUT / 'assembly-guide.json')
        assert supplemental['checker_sha256'] == v.digest(Path(__file__).with_name('evidence69.py'))
        assert v.read(folder / 'fit.json')['guide_sha256'] == v.digest(OUT / 'assembly-guide.json')
        sections = v.read(folder / 'mechanical-sections.json')
        assert sections['coverage_complete'] and sections['archive_sha256'] == v.digest(folder / v.ARCHIVE)
        assert sections['cheek_overlap']['passes'] and not sections['cheek_overlap']['bridge_or_flake_runs']
        assert sections['frame_sha256'] == v.digest(folder / 'layout.frame.json')
        assert sections['checker_sha256'] == v.digest(Path(__file__).with_name('sections69.py'))
        assert sections['image_sha256'] == v.digest(folder / 'bridge-and-keeper-layers.png')
        audit68.fin_removal_note(folder)
    kit69.kit64.kit63.kit62.release61.release(primary, reopened, OUT, kit69.parts, PRINT_NAME, reports=REPORTS)
    copyfile(primary / 'op1-seat-comparison.png', OUT / 'print-mechanisms/op1-seat-comparison.png')
    copyfile(primary / 'bridge-and-keeper-layers.png', OUT / 'print-mechanisms/bridge-and-keeper-layers.png')
    copyfile(reopened / 'bridge-and-keeper-layers.png', OUT / 'print-mechanisms/reopened-bridge-and-keeper-layers.png')


def click():
    bind()
    fit = checks69.fit.run(OUT / d.HOLDER, OUT / hinge69.PADDLE, OUT / hinge69.WIRES, OUT / hinge69.LID)
    fit.update(revision='R69', carrier_sha256=v.digest(OUT / d.HOLDER))
    (OUT / 'click-fit.json').write_text(json.dumps(fit, indent=2, default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x)) + '\n')
    return fit


def cad_routes():
    """The same routes against the CAD meshes, before any slice exists: worst overlap per route. — Claude Fable 5.2"""
    meshes = {'Key_Carrier': b.load(OUT / d.HOLDER), 'Touch_Paddle': b.load(OUT / hinge69.PADDLE), 'OP1_Lid_Stop': b.load(OUT / hinge69.LID)}
    names = ('op1_', 'pin_go', 'barrel', 'wired_connector', 'rear_clip', 'seated_wire', 'paddle_far_end')
    rows = {}
    for part, group in routes().items():
        if part not in meshes:
            continue
        for name, solids in group.items():
            if name.startswith(names):
                rows[f'{part}/{name}'] = round(max(float((meshes[part] ^ s).volume()) for s in solids), 4)
    return rows


def routes():
    bind()
    groups = a61.gauges()
    a64.audit63.key_routes(groups)
    holder, paddle = groups['Key_Carrier'], groups['Touch_Paddle']
    holder.update(a64.deposited_routes())
    for name in ('board', 'sockets', 'housing', 'plug'):
        del holder[name + '_from_above']
    holder['seated_wire_outlet'] = [d.r66.hardware()['op1_wire']]
    holder.update(op1_routes())
    for name in ('both_cheeks', 'left_cheek', 'right_cheek'):
        key = 'pin_go_gauge_through_' + name
        holder[key] = [solid.translate(hinge69.MOVE) for solid in holder[key]]
    moving = b.load(OUT / hinge69.PADDLE)
    bearing = moving ^ b.box(-hinge69.JOURNAL_OUT - .01, hinge69.JOURNAL_OUT + .01, hinge69.AXIS - 3.4, hinge69.REAR + .01,
                             hinge69.KEEPER_Z - 3.4, hinge69.KEEPER_Z + 3.4)
    holder['barrel_between_cheeks_from_above'] = [bearing.translate((0, 0, z)) for z in np.arange(0, 12.1, 1)]
    cable = hinge69.r61.housing() + hinge69.r61.plug() + hinge69.wired_lead()
    rear_clip = hinge69.clip()
    for group in (holder, paddle):
        group['wired_connector_lowering'] = [cable.translate((0, 0, z)) for z in np.arange(0, 12.1, .5)]
        group['rear_clip_from_behind'] = [rear_clip.translate((0, dy, 0)) for dy in np.arange(0, 11.1, .5)]
    paddle['pin_go_gauge_through_barrel'] = [hinge69.disc(1.60, -hinge69.JOURNAL_OUT - .6, hinge69.JOURNAL_OUT + .6)]
    paddle.pop('pin_clip_well', None)
    stop = json.loads((OUT / 'hinge.json').read_text())['click']['case_stop_deg']
    legs = moving ^ b.box(-12, 12, -12, 6, 11.5, 17.6)
    groups.setdefault('OP1_Lid_Stop', {})['paddle_far_end_press'] = far_end_poses(legs, stop)
    guide = v.read(OUT / 'assembly-guide.json')
    for name in (d.HOLDER, hinge69.PADDLE, hinge69.LID):
        assert guide['sources']['meshes_sha256'][name] == v.digest(OUT / name)
    retainer = b.load(OUT / hinge69.LID)
    insertion, through_paddle = [], []
    for step in guide['modules']['pin_hinge']['steps']:
        if step['title'] not in ('Fit the OP1 retainer', 'Remove the OP1 retainer'):
            continue
        for sample in step['samples']:
            lid_pose, paddle_pose = np.eye(4), np.eye(4)
            lid_pose[:3] = np.asarray(sample['lid']).reshape(3, 4)
            paddle_pose[:3] = np.asarray(sample['cap']).reshape(3, 4)
            insertion.append(retainer.transform(lid_pose[:3]))
            through_paddle.append(retainer.transform((np.linalg.inv(paddle_pose) @ lid_pose)[:3]))
    assert len(insertion) >= 40
    holder['actual_retainer_insertion_and_removal'] = insertion
    paddle['actual_retainer_insertion_and_removal'] = through_paddle
    return groups


def bind():
    """Point the inherited hinge readers at the R69 pin line. — Claude Fable 5.2"""
    a64.hinge = hinge69
    a64.pin_fit64.h = hinge69
    a66.hinge_fit64.h = hinge69
    checks69.fit.h = hinge69


def op1_routes():
    best = json.loads((OUT / 'op1.json').read_text())['largest_plug_margin_per_side']['r69']
    x, y = best['centre_world_xy_mm']
    column = [checks69.plug_box(PLUG_ROUTE_MARGIN, best['wide_side_yaw_deg']).translate((x, y, float(z))) for z in np.arange(-14., 13.01, .5)]
    routes = {'op1_plug_rises_through_window': column, 'op1_lead_in_channel': [d.r66.lead_solid('route')]}
    for name in ('board', 'sockets', 'housing', 'plug', 'lead'):
        routes[f'op1_{name}_lowered_onto_seat'] = [d.r66.drop_route(name, bearing_skin=.20 if name == 'board' else 0.0)]
    return routes


def far_end_poses(paddle, stop_deg):
    station = np.array([0., b.STATION[1], b.FREE_TOP - .8])
    poses = []
    for roll in (-.8, .8):
        for shift in (-.20, .20):
            pose = hinge69.rotate(paddle, stop_deg + .25)
            heel = math.degrees(.35 / (hinge69.AXIS - station[1]))
            poses.append(pose.translate(-station).rotate((heel, roll, 0)).translate(station + np.array([shift, 0, 0])))
    return poses


def battery_regions():
    return audit68.battery_regions()


def mounts(folder):
    bind()
    passages = a64.passage63.inspect(folder, hinge69.AXIS, axis_z=hinge69.KEEPER_Z)
    pins = a64.passage63.shaft_envelopes(folder)
    passages['fresh_pins'] = pins
    for name, diameter in pins['straight_shaft_envelope_diameter_mm'].items():
        passages['clearance_over_' + name + '_mm'] = round(passages['assembled_clear_diameter_mm'] - diameter, 3)
    grip = dict(expected_tightest_print_height_mm=list(RING_PRINT_HEIGHTS), profile=rod_grip_profile(folder),
                tightest_in_front_ring=bool(RING_PRINT_HEIGHTS[0] - .3 <= passages['rod_limiting_layer_top_mm'] <= RING_PRINT_HEIGHTS[1] + .3))
    passages['rod_grip_rings'] = grip
    v.write(folder / 'passages.json', passages)
    assert 7.4 <= passages['rod_min_clear_diameter_mm'] <= 7.9 and grip['tightest_in_front_ring'], passages
    assert grip['profile']['passes'], grip
    assert passages['assembled_clear_diameter_mm'] >= 3.30 and passages['clearance_over_Hinge_Pin_mm'] > .1, passages
    directional = a64.pin_fit64.check(folder)
    # The inherited checker called its frame digest a layout digest. Keep both correctly named.
    # Found by Claude Opus 5.5. Fixed by GPT-6.1 Sol.
    assert directional['layout_sha256'] == v.digest(folder / 'layout.frame.json')
    directional['frame_sha256'] = directional['layout_sha256']
    directional['layout_sha256'] = v.digest(folder / 'layout.3mf')
    v.write(folder / 'pin-fit.json', directional)
    assert directional['passes'], directional


def rod_grip_profile(folder: Path) -> dict:
    """Check every tight layer against the fitted R58 contact shape, including its saddle.

    A count of the two rings missed R58's short saddle contact and layer-edge rounding.
    Check locations and diameters instead; the rigid rear funnel must remain open.
    Found and fixed by GPT-6.1 Sol. — GPT-6.1 Sol
    """
    points, _ = v.read_native(folder / v.ARCHIVE)
    frame = np.asarray(v.read(folder / 'layout.frame.json')['parts']['Key_Carrier']['assembly_to_machine'])
    assert np.allclose(frame[:3, 1], [0, 0, -1])
    local = points[(abs(points[:, 0] - frame[0, 3]) < 5.5) & (abs(points[:, 1] - frame[1, 3]) < 5.5)]
    radius = np.hypot(local[:, 0] - frame[0, 3], local[:, 1] - frame[1, 3]) - local[:, 3] / 2 - .06
    reference = b.load(d.HARDWARE / 'carbon-rod-holders-r58-smooth-click' / 'exports' / d.HOLDER).rotate((90, 0, 0))
    rows = []
    for top in sorted(set(local[:, 2])):
        mask = local[:, 2] == top
        diameter = 2 * float(radius[mask].min())
        if diameter >= 8:
            continue
        height = float(local[mask, 4].max())
        ys = frame[2, 3] - np.array([top, top - height / 2, top - height])
        diameters = []
        for y in ys:
            section = reference.slice(float(y)) ^ d.mf.CrossSection.circle(5.6, 96)
            polygons = section.to_polygons()
            assert polygons
            diameters.append(2 * min(Point(0, 0).distance(LineString(np.vstack((p, p[0])))) for p in polygons))
        nominal = min(diameters)
        rows.append(dict(layer_top_mm=round(float(top), 3), assembly_y_mm=round(float(ys[1]), 3),
                         printed_diameter_mm=round(diameter, 3), r58_nominal_diameter_mm=round(nominal, 3),
                         passes=bool(ys.min() >= 8.9 and ys.max() <= 32.75 and nominal <= 8.3 and diameter >= nominal - .30)))
    return dict(reference='R58 fitted grip, including its short saddle contact', all_bead_types=True,
                bead_sampling_allowance_mm=.06, max_diameter_deficit_mm=.30, layers=rows,
                passes=bool(len(rows) > 20 and all(row['passes'] for row in rows)))


def verify_base(folder):
    frame = v.read(folder / 'layout.frame.json')
    row = frame['parts']['Key_Carrier']
    body = v.load_solid(OUT / row['source'])
    pose = np.asarray(row['assembly_to_machine'])
    oriented = pose[:3].copy()
    oriented[:2, 3] = 0
    base, _, _ = v.base54(body.transform(oriented), v.settings(row['adhesion_panel']))
    regions = battery_regions()
    archive = folder / v.ARCHIVE
    joint = v.seam(archive, frame, body, regions=regions, regional_base=base.translate((*pose[:2, 3], 0)))
    areas = joint['regional_joint_area_mm2']
    report = dict(archive_sha256=v.digest(archive), regions=regions, contacts_mm2=areas, passes=bool(
        all(areas[n] < .05 for n in ('outer_free_lip', 'inner_free_lip')) and all(areas[n] > .4 for n in ('root_below', 'root_above'))))
    v.write(folder / 'battery-base.json', report)
    assert report['passes'], areas


def printed_seat_report(folder, render=False):
    """Deposited plastic 0.10 mm under the board, R69 against the R63 and R64 slices. — author unverified"""
    k64 = kit69.kit64
    dirs = {'R63': k64.kit63.OUT / 'print-mechanisms', 'R64': k64.OUT / 'print-mechanisms', 'R69': folder}
    seat = audit68.printed_seat
    outline = seat.board_outline()
    shapes = {}
    for label, path in dirs.items():
        archive = path / v.ARCHIVE
        native = audit68.read_native(archive)
        shapes[label] = seat.printed_contact(path, archive, native, d.b.PCB_Z - .10).intersection(outline)
        del native
    results = {label: dict(seat.metrics(shape), socket_rings=a66.socket_rings(shape),
                           direct_plunger_contact_mm2=round(shape.intersection(audit68.box(-1.45, -.6, 1.45, .6)).area, 2))
               for label, shape in shapes.items()}
    baseline, r69 = results['R63'], results['R69']
    keeps = lambda result, fraction: result['plunger_inside_support_polygon'] and all(
        result['area_mm2'][key] >= baseline['area_mm2'][key] * fraction for key in baseline['area_mm2'])
    report = dict(archive_sha256=v.digest(folder / v.ARCHIVE), plane_below_board_mm=.10, versions=results,
                  r69_fraction_of_r63={key: round(r69['area_mm2'][key] / baseline['area_mm2'][key], 3) for key in baseline['area_mm2'] if baseline['area_mm2'][key]},
                  known_bad_r64_rejected=not keeps(results['R64'], .80))
    report['passes'] = bool(report['known_bad_r64_rejected'] and keeps(r69, .95)
                            and r69['direct_plunger_contact_mm2'] >= .95 * baseline['direct_plunger_contact_mm2']
                            and all(n['plastic_fraction'] >= p['plastic_fraction'] - .05 for n, p in zip(r69['socket_rings'], baseline['socket_rings'])))
    if render:
        seat.draw(folder / 'op1-seat-comparison.png', shapes, results)
    v.write(folder / 'printed-seat.json', report)
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    actions = parser.add_subparsers(dest='action', required=True)
    actions.add_parser('click')
    actions.add_parser('audit').add_argument('folder', type=Path)
    pack = actions.add_parser('release')
    pack.add_argument('primary', type=Path)
    pack.add_argument('reopened', type=Path)
    args = parser.parse_args()
    if args.action == 'click':
        print(json.dumps(click(), indent=2, default=str))
    elif args.action == 'audit':
        audit(args.folder)
    else:
        release(args.primary, args.reopened)
