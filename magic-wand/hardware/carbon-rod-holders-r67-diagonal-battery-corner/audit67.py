"""Check the complete R67 kit against deposited PETG in a native slice.

The R66 kit audit with the R67 carrier: the same OP1 routes (the tipped plug threaded
up beside the rod, turned above the holder, the mated board lowered onto its three holes
and the lead laid in its channel), the same key socket routes and pins, and the printed
seat under the board compared with the R63 and R64 slices. The battery base witness
follows the two bed ties moved off the new diagonal corner.

    audit67.py click                       CAD click and hinge fit with the R67 carrier
    audit67.py audit SLICE_DIRECTORY       every deposited-bead check on one native slice
    audit67.py release PRIMARY REOPENED    package the reviewed, matching pair of slices
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from shutil import copyfile

from shapely.geometry import box

import audit66 as prior
import design67 as d
import kit67
import printed_seat
from openings53 import read_native

v = prior.v
a61 = prior.a61
o = d.old
OUT = kit67.OUT
REPORTS = (*prior.REPORTS, 'supplemental-evidence.json')
PRINT_NAME = 'R67-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'
CAD_REPORTS = ('subtraction.json', 'battery.json', 'saddle.json', 'op1-route.json', 'carrier.json')


def routes():
    return prior.routes()


def battery_regions():
    """Bed-frame windows (print X = assembly X, print Y = assembly Z) at the bed face."""
    under, above = (kit67.MOVED_TIES[k]['at'] for k in (('-y', -22.68), ('+y', -23.8)))
    half = .85 + .1
    return {'outer_free_lip': [-21.55, o.LOW - .1, -18.7, o.LIP_TOP + .05],
            'inner_free_lip': [-11.95, o.LOW - .1, -9.55, o.LIP_TOP + .05],
            # The two fins that R66 rooted on the removed corner, at their R67 stations.
            'spring_root_below': [under - half, o.LIP_TOP - 1.0, min(under + half, o.PACK_X[0] - .3), o.LIP_TOP + 1.1],
            'root_above': [above - half, o.DECK - .35, above + half, o.DECK + 2.5]}


def verify_base(folder):
    frame = v.read(folder / 'layout.frame.json')
    row = frame['parts']['Key_Carrier']
    body = v.load_solid(OUT / row['source'])
    pose = prior.np.asarray(row['assembly_to_machine'])
    oriented = pose[:3].copy()
    oriented[:2, 3] = 0
    base, _, _ = v.base54(body.transform(oriented), v.settings(row['adhesion_panel']))
    regions = battery_regions()
    archive = folder / v.ARCHIVE
    joint = v.seam(archive, frame, body, regions=regions, regional_base=base.translate((*pose[:2, 3], 0)))
    areas = joint['regional_joint_area_mm2']
    report = dict(archive_sha256=v.digest(archive), regions=regions, contacts_mm2=areas,
                  moved_ties=[dict(t) for t in kit67.MOVED_TIES.values()], passes=bool(
                      all(areas[n] < .05 for n in ('outer_free_lip', 'inner_free_lip'))
                      and all(areas[n] > .4 for n in ('spring_root_below', 'root_above'))))
    v.write(folder / 'battery-base.json', report)
    assert report['passes'], areas


def printed_seat_report(folder, render=False):
    """Deposited plastic 0.10 mm under the board, R67 against the R63 and R64 slices."""
    k64 = kit67.kit64
    dirs = {'R63': k64.kit63.OUT / 'print-mechanisms', 'R64': k64.OUT / 'print-mechanisms', 'R67': folder}
    outline = printed_seat.board_outline()
    shapes = {}
    for label, path in dirs.items():
        archive = path / v.ARCHIVE
        native = read_native(archive)
        shapes[label] = printed_seat.printed_contact(path, archive, native, d.b.PCB_Z - .10).intersection(outline)
        del native
    results = {label: dict(printed_seat.metrics(shape), socket_rings=prior.socket_rings(shape),
                           direct_plunger_contact_mm2=round(shape.intersection(box(-1.45, -.6, 1.45, .6)).area, 2))
               for label, shape in shapes.items()}
    baseline = results['R63']

    def keeps(result, fraction):
        return result['plunger_inside_support_polygon'] and all(
            result['area_mm2'][k] >= baseline['area_mm2'][k] * fraction for k in baseline['area_mm2'])

    r67 = results['R67']
    report = dict(archive_sha256=sha256((folder / v.ARCHIVE).read_bytes()).hexdigest(),
                  plane_below_board_mm=.10, versions=results,
                  r67_fraction_of_r63={k: round(r67['area_mm2'][k] / baseline['area_mm2'][k], 3)
                                       for k in baseline['area_mm2'] if baseline['area_mm2'][k]},
                  known_bad_r64_rejected=not keeps(results['R64'], .80))
    report['passes'] = bool(report['known_bad_r64_rejected'] and keeps(r67, .95)
                            and r67['direct_plunger_contact_mm2'] >= .95 * baseline['direct_plunger_contact_mm2']
                            and all(n['plastic_fraction'] >= p['plastic_fraction'] - .05
                                    for n, p in zip(r67['socket_rings'], baseline['socket_rings'])))
    if render:
        printed_seat.draw(folder / 'op1-seat-comparison.png', shapes, results)
    v.write(folder / 'printed-seat.json', report)
    return report


def audit(folder):
    for name in CAD_REPORTS:
        report = v.read(OUT / name)
        assert report['carrier_sha256'] == v.digest(OUT / d.HOLDER) and report['passes'], name
    audit_deposited_plastic(folder)


def audit_deposited_plastic(folder):
    """Audit paths in the exact archive independently of the solid-model calculations."""
    prior.mounts(folder)
    verify_base(folder)
    backers = {r['name'].split('_')[-1]: r['source'] for r in kit67.parts() if r['name'].startswith('Socket_Backer')}
    a61.audit(folder, kit67.parts, OUT, expected_names=kit67.COMPLETE, route_builder=routes,
              spring_probe=prior.prior.spring_opening, backer_rows=backers, base_minima=dict(a61.MINIMA, Rod_Collet=150))
    fin_removal_note(folder)
    seat = printed_seat_report(folder, render=True)
    assert seat['passes'], seat


def fin_removal_note(folder):
    """Replace inherited four/two wording with the R67 plate's actual six ties."""
    path = folder / 'fin-design.json'
    report = v.read(path)
    counts = {face: sum(fin['face'] == face for fin in report['fins']) for face in ('-y', '+y')}
    assert counts == {'-y': 3, '+y': 3}, counts
    report['removal'] = [
        'Cut all six thin fins flush: three on each side of the exposed rim.',
        'Cut the two battery-corner ties before peeling; do not twist against the spring-root post.',
        'Peel the two sides of the base away from the open hinge bay.']
    v.write(path, report)


def click():
    parts = {row['name']: row['source'] for row in kit67.parts()}
    fit = prior.hinge_fit64.run(parts['Key_Carrier'], parts['Touch_Paddle'], kit67.kit64.OUT / 'Gravity_Wires-assembly.stl',
                                parts['OP1_Lid_Stop'])
    fit.update(revision='R67', carrier_sha256=v.digest(parts['Key_Carrier']))
    v.write(OUT / 'click-fit.json', fit)
    assert max(fit['overlap_mm3'].values()) < .013 and 0 < fit['button_contact_deg'] < fit['case_stop_deg'], fit
    return fit


def release(primary, reopened):
    carrier = v.digest(OUT / d.HOLDER)
    for name in (*CAD_REPORTS, 'click-fit.json'):
        report = v.read(OUT / name)
        assert report['carrier_sha256'] == carrier, name
        if name != 'click-fit.json':
            assert report['passes'], name
    sources = {row['source'].name: row['source'] for row in kit67.parts()}
    sources['Gravity_Wires-assembly.stl'] = kit67.kit64.OUT / 'Gravity_Wires-assembly.stl'
    fitted = v.read(OUT / 'click-fit.json')['assembled_sha256']
    assert all(v.digest(sources[name]) == sha for name, sha in fitted.items())
    for folder in (primary, reopened):
        assert v.read(folder / 'printed-seat.json')['passes'] and v.read(folder / 'battery-base.json')['passes']
        supplement = v.read(folder / 'supplemental-evidence.json')
        assert supplement['passes'] and supplement['carrier_sha256'] == carrier
        assert supplement['archive_sha256'] == v.digest(folder / v.ARCHIVE)
        assert supplement['checker_sha256'] == v.digest(Path(__file__).with_name('evidence67.py'))
        fin_removal_note(folder)
    kit67.kit64.kit63.kit62.release61.release(primary, reopened, OUT, kit67.parts, PRINT_NAME, reports=REPORTS)
    copyfile(primary / 'op1-seat-comparison.png', OUT / 'print-mechanisms/op1-seat-comparison.png')


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
        print(json.dumps(click(), indent=2))
    elif args.action == 'audit':
        audit(args.folder)
    else:
        release(args.primary, args.reopened)
