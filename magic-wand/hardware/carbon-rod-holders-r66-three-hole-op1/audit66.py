"""Check the complete R66 kit against deposited PETG in a native slice.

The R64 kit audit with R66's own OP1 routes: the tipped white plug rising beside the
installed rod and through the deck opening, its turn above the holder, the mated board
lowered onto the three fixed socket holes and the lead pressed into its channel. R64's
under-entry gauges are removed because R66 restores R63's closed deck. The battery base
witness follows the moved bed tie under the retained spring-root post, and the printed
seat under the board is compared with the R63 and R64 slices.

    audit66.py click                       CAD click and hinge fit with the R66 carrier
    audit66.py audit SLICE_DIRECTORY       every deposited-bead check on one native slice
    audit66.py release PRIMARY REOPENED    package the reviewed, matching pair of slices
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from shutil import copyfile

import manifold3d as mf
import numpy as np
from shapely.geometry import Point, box

import audit64 as prior
import checks66
import design66 as d
import hinge_fit64
import kit66
import printed_seat
from openings53 import read_native

v = prior.v
a61 = prior.a61
b = d.b
o = d.old
OUT = kit66.OUT
REPORTS = (*prior.REPORTS, 'printed-seat.json')
PRINT_NAME = 'R66-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'
CAD_REPORTS = ('op1-route.json', 'battery.json', 'socket-backing.json', 'carrier.json')


def _mesh(vertices, faces):
    return mf.Manifold(mf.Mesh(np.asarray(vertices, np.float32), np.asarray(faces, np.uint32)))


def op1_routes():
    """R66's OP1 movements, exactly the motions checked in CAD by checks66."""
    plug = d.hardware()['plug']
    turn = checks66.turn_poses(51)
    first, faces = d.preview_lead_vertices('thread')
    last, _ = d.preview_lead_vertices('turn_end')
    routes = {
        'op1_plug_threads_up_from_below': [d.thread_route()],
        'op1_plug_turns_above_holder': [d.pose(plug, m) for m in turn],
        'op1_lead_while_plug_turns': [_mesh((1 - t) * first + t * last, faces) for t in np.linspace(0, 1, len(turn))],
        'op1_lead_in_channel': [d.lead_solid('route')],
    }
    for name in ('board', 'sockets', 'housing', 'plug', 'lead'):
        # The board rests on the deck; only the 0.20 mm skin above its seat is excused.
        routes[f'op1_{name}_lowered_onto_seat'] = [d.drop_route(name, bearing_skin=.20 if name == 'board' else 0.0)]
    return routes


def routes():
    groups = prior.routes()
    holder = groups['Key_Carrier']
    for name in d.r64.ACTORS:
        del holder[name + '_under_entry']
    holder.update(op1_routes())
    return groups


def battery_regions():
    """Bed-frame windows (print X = assembly X, print Y = assembly Z) at the bed face."""
    return {'outer_free_lip': [-21.55, o.LOW - .1, -18.7, o.LIP_TOP + .05],
            'inner_free_lip': [-11.95, o.LOW - .1, -9.55, o.LIP_TOP + .05],
            # R66 ends the outboard wall before the bed face. The -y tie now lands under
            # the retained spring-root post at X -22.68.
            'spring_root_below': [o.WALL_FACE - .1, o.LIP_TOP - 1.0, o.PACK_X[0] - .3, o.LIP_TOP + 1.1],
            'root_above': [-25.5, o.DECK - .35, -22.4, o.DECK + 2.5]}


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
    report = dict(archive_sha256=v.digest(archive), regions=regions, contacts_mm2=areas,
                  moved_tie=kit66.MOVED_TIE[1], passes=bool(
                      all(areas[n] < .05 for n in ('outer_free_lip', 'inner_free_lip'))
                      and all(areas[n] > .4 for n in ('spring_root_below', 'root_above'))))
    v.write(folder / 'battery-base.json', report)
    assert report['passes'], areas


def mounts(folder):
    passages = prior.passage63.inspect(folder, prior.hinge.AXIS, axis_z=prior.hinge.KEEPER_Z)
    pins = prior.passage63.shaft_envelopes(folder)
    passages['fresh_pins'] = pins
    for name, diameter in pins['straight_shaft_envelope_diameter_mm'].items():
        passages['clearance_over_' + name + '_mm'] = round(passages['assembled_clear_diameter_mm'] - diameter, 3)
    v.write(folder / 'passages.json', passages)
    assert passages['rod_min_clear_diameter_mm'] >= 8.2 and not passages['rod_layers_under_8mm'], passages
    assert passages['assembled_clear_diameter_mm'] >= 3.30 and passages['clearance_over_Hinge_Pin_mm'] > .1, passages
    directional = prior.pin_fit64.check(folder)
    v.write(folder / 'pin-fit.json', directional)
    assert directional['passes'], directional


def socket_rings(seat):
    """Printed plastic in a 1 mm ring just outside each of the three socket holes (board frame)."""
    rows = []
    for y in b.SOCKET_Y:
        ring = Point(0, y).buffer(1.74 + 1.0, 96).difference(Point(0, y).buffer(1.74, 96))
        rows.append(dict(board_y=y, plastic_fraction=round(seat.intersection(ring).area / ring.area, 3)))
    return rows


def printed_seat_report(folder, render=False):
    """Deposited plastic 0.10 mm under the board, R66 against the R63 and R64 slices."""
    dirs = {'R63': kit66.kit64.kit63.OUT / 'print-mechanisms', 'R64': kit66.kit64.OUT / 'print-mechanisms', 'R66': folder}
    outline = printed_seat.board_outline()
    shapes = {}
    for label, path in dirs.items():
        archive = path / v.ARCHIVE
        native = read_native(archive)
        shapes[label] = printed_seat.printed_contact(path, archive, native, b.PCB_Z - .10).intersection(outline)
        del native
    results = {label: dict(printed_seat.metrics(shape), socket_rings=socket_rings(shape),
                           direct_plunger_contact_mm2=round(shape.intersection(box(-1.45, -.6, 1.45, .6)).area, 2))
               for label, shape in shapes.items()}
    baseline = results['R63']

    def keeps(result, fraction):
        return result['plunger_inside_support_polygon'] and all(
            result['area_mm2'][k] >= baseline['area_mm2'][k] * fraction for k in baseline['area_mm2'])

    r66 = results['R66']
    report = dict(archive_sha256=sha256((folder / v.ARCHIVE).read_bytes()).hexdigest(),
                  plane_below_board_mm=.10, versions=results,
                  r66_fraction_of_r63={k: round(r66['area_mm2'][k] / baseline['area_mm2'][k], 3)
                                       for k in baseline['area_mm2'] if baseline['area_mm2'][k]},
                  known_bad_r64_rejected=not keeps(results['R64'], .80))
    report['passes'] = bool(report['known_bad_r64_rejected'] and keeps(r66, .95)
                            and r66['direct_plunger_contact_mm2'] >= .95 * baseline['direct_plunger_contact_mm2']
                            and all(n['plastic_fraction'] >= p['plastic_fraction'] - .05
                                    for n, p in zip(r66['socket_rings'], baseline['socket_rings'])))
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
    mounts(folder)
    verify_base(folder)
    backers = {r['name'].split('_')[-1]: r['source'] for r in kit66.parts() if r['name'].startswith('Socket_Backer')}
    a61.audit(folder, kit66.parts, OUT, expected_names=kit66.COMPLETE, route_builder=routes,
              spring_probe=prior.spring_opening, backer_rows=backers, base_minima=dict(a61.MINIMA, Rod_Collet=150))
    seat = printed_seat_report(folder, render=True)
    assert seat['passes'], seat


def click():
    parts = {row['name']: row['source'] for row in kit66.parts()}
    fit = hinge_fit64.run(parts['Key_Carrier'], parts['Touch_Paddle'], kit66.kit64.OUT / 'Gravity_Wires-assembly.stl',
                          parts['OP1_Lid_Stop'])
    fit.update(revision='R66', carrier_sha256=v.digest(parts['Key_Carrier']))
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
    sources = {row['source'].name: row['source'] for row in kit66.parts()}
    sources['Gravity_Wires-assembly.stl'] = kit66.kit64.OUT / 'Gravity_Wires-assembly.stl'
    fitted = v.read(OUT / 'click-fit.json')['assembled_sha256']
    assert all(v.digest(sources[name]) == sha for name, sha in fitted.items())
    for folder in (primary, reopened):
        assert v.read(folder / 'printed-seat.json')['passes'] and v.read(folder / 'battery-base.json')['passes']
    kit66.kit64.kit63.kit62.release61.release(primary, reopened, OUT, kit66.parts, PRINT_NAME, reports=REPORTS)
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
