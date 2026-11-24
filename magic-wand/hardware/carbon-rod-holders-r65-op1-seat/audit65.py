"""Check the entire fitting plate plus positive support for the loaded OP1."""
from pathlib import Path
from shutil import copyfile
import sys

import numpy as np

import kit65
import audit64 as prior
import design65
import hinge_fit64
import printed_seat

v = prior.v
OUT = kit65.OUT


def routes():
    groups = prior.routes()
    carrier = groups['Key_Carrier']
    for actor in design65.ACTORS:
        carrier[actor + '_under_entry'] = [design65.entry_check_solid(actor, bearing_skin=.20)]
    # On the loose sled the three projecting sockets, fixed housing and wired
    # plug must pass through real printed clearance as the board seats.
    groups['OP1_Seat_Sled'] = {name + '_board_loading': [prior.entry.sweep(
        name, offsets=[(0,0,design65.LOAD_HEIGHT),(0,0,0)])] for name in
        ('sockets','housing','plug','op1_wire')}
    return groups


def check_unchanged_mounts(folder):
    hinge = prior.hinge
    report = prior.passage63.inspect(folder, hinge.AXIS, axis_z=hinge.KEEPER_Z)
    assert report['assembled_clear_diameter_mm'] >= 3.30 and report['rod_min_clear_diameter_mm'] >= 8.20
    v.write(folder/'passages.json', report)
    pins = prior.pin_fit64.check(folder)
    assert pins['passes']
    v.write(folder/'pin-fit.json', pins)
    frames = v.read(folder/'layout.frame.json')
    carrier = frames['parts']['Key_Carrier']
    solid = v.load_solid(OUT/carrier['source'])
    pose = np.asarray(carrier['assembly_to_machine'])
    oriented = pose[:3].copy()
    oriented[:2,3] = 0
    base, _, _ = v.base54(solid.transform(oriented), v.settings(carrier['adhesion_panel']))
    d = prior.entry.old
    regions = {'outer_free_lip': [-21.55,d.LOW-.1,-18.7,d.LIP_TOP+.05],
               'inner_free_lip': [-11.95,d.LOW-.1,-9.55,d.LIP_TOP+.05],
               'root_below': [-25.5,d.LOW-1,-22.4,d.LOW+1.1], 'root_above': [-25.5,d.DECK-.35,-22.4,d.DECK+2.5]}
    archive = folder/v.ARCHIVE
    seam = v.seam(archive, frames, solid, regions=regions, regional_base=base.translate((*pose[:2,3],0)))
    areas = seam['regional_joint_area_mm2']
    assert all(areas[k] < .05 for k in ('outer_free_lip','inner_free_lip'))
    assert all(areas[k] > .4 for k in ('root_above','root_below'))
    v.write(folder/'battery-base.json', dict(archive_sha256=v.digest(archive), regions=regions, contacts_mm2=areas))


def audit(folder):
    rows = kit65.parts()
    contact = printed_seat.compare(folder, render=True)
    backers = {row['name'].split('_')[-1]: row['source'] for row in rows if row['name'].startswith('Socket_Backer_')}
    name_set = {row['name'] for row in rows}
    prior.a61.audit(folder, kit65.parts, OUT, expected_names=name_set, route_builder=routes,
                    spring_probe=prior.spring_opening, backer_rows=backers,
                    base_minima=dict(prior.a61.MINIMA, Rod_Collet=150, OP1_Seat_Sled=200))
    check_unchanged_mounts(folder)
    assert contact['passes'], contact


def carrier_checks():
    parts = {row['name']: row['source'] for row in kit65.parts()}
    carrier = prior.b.load(parts['Key_Carrier'])
    d = prior.entry
    spaces = d.old.k.h.d.geometry()[1]
    key_count = 0
    for name, space in spaces.items():
        if name.startswith('key_'):
            for pose in d.old.c.poses(d.old.placed(space, name)):
                assert d.mm3(carrier, pose) < .01, name
                key_count += 1
    assert key_count == 336
    v.write(OUT/'carrier.json', dict(carrier_sha256=v.digest(parts['Key_Carrier']),
                                     key_poses_checked=key_count, key_obstructions=[]))


def click_checks():
    parts = {row['name']: row['source'] for row in kit65.parts()}
    click = hinge_fit64.run(parts['Key_Carrier'], parts['Touch_Paddle'], kit65.kit64.OUT/'Gravity_Wires-assembly.stl',
                            parts['OP1_Lid_Stop'])
    sled = prior.b.load(parts['OP1_Seat_Sled'])
    hinge = hinge_fit64.h
    paddle = prior.b.load(parts['Touch_Paddle'])
    touch_board = hinge_fit64.k.r.sensor().translate((0,hinge_fit64.k.r.CLICK_SHIFT,0)).transform(hinge.r61.FLIP)
    fitted = prior.b.union([paddle, touch_board, hinge.r61.housing(), hinge.r61.plug(),
        prior.b.load(kit65.kit64.OUT/'Gravity_Wires-assembly.stl'),
        *(prior.b.load(parts[name]) for name in ('DFR_Post_Bar','DFR_Clip_Left','DFR_Clip_Right'))])
    clearances = []
    for sign in (-1,0,1):
        moving = fitted.translate(-hinge.PIVOT).rotate((0,sign*.45,0)).translate(
            hinge.PIVOT + np.array([sign*.10,0,abs(sign)*.055]))
        for angle in np.linspace(-click['lift_stop_deg'], click['case_stop_deg'], 21):
            clearances.append(hinge.rotate(moving,angle).min_gap(sled,5))
    switch = hinge_fit64.k.q.hardware()
    seated = prior.b.union([switch[name] for name in ('switch','terminals','plunger')])
    click['moving_hardware_to_sled_min_gap_mm'] = round(min(clearances),3)
    click['switch_to_sled_min_gap_mm'] = round(sled.min_gap(seated,5),3)
    click['assembled_sha256'][design65.SLED_FILE] = v.digest(parts['OP1_Seat_Sled'])
    assert min(click['moving_hardware_to_sled_min_gap_mm'], click['switch_to_sled_min_gap_mm']) > .10
    click.update(revision='R65', carrier_sha256=v.digest(parts['Key_Carrier']))
    v.write(OUT/'click-fit.json', click)


def release(primary, reopened):
    support = v.read(OUT/'support.json')
    assert support.get('passes') and all(v.digest(OUT/name) == sha for name,sha in support['mesh_sha256'].items())
    click = v.read(OUT/'click-fit.json')
    sources = {row['source'].name:row['source'] for row in kit65.parts()}
    sources['Gravity_Wires-assembly.stl'] = kit65.kit64.OUT/'Gravity_Wires-assembly.stl'
    assert all(v.digest(sources[name]) == digest for name,digest in click['assembled_sha256'].items())
    assert min(click['moving_hardware_to_sled_min_gap_mm'],click['switch_to_sled_min_gap_mm']) > .10
    for folder in (primary, reopened):
        assert v.read(folder/'printed-seat.json')['passes']
    printer = kit65.kit64.kit63.kit62.release61
    name = 'R65-Complete-Key-Holder-A1-mini-PETG-print-only.3mf'
    printer.release(primary,reopened,OUT,kit65.parts,name,reports=(*prior.REPORTS,'printed-seat.json'))
    copyfile(primary/'op1-seat-comparison.png', OUT/'print-mechanisms/op1-seat-comparison.png')


if __name__ == '__main__':
    if sys.argv[1:] == ['carrier']:
        carrier_checks()
    elif sys.argv[1:] == ['click']:
        click_checks()
    elif len(sys.argv) == 3 and sys.argv[1] == 'audit':
        audit(Path(sys.argv[2]))
    elif len(sys.argv) == 4 and sys.argv[1] == 'release':
        release(Path(sys.argv[2]),Path(sys.argv[3]))
    else:
        raise SystemExit('Use carrier, click, audit SLICE_DIRECTORY, or release PRIMARY REOPENED')
