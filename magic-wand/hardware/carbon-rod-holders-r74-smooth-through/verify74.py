"""Test the complete battery travel in the exported carrier, plus every bought-key pose."""
from hashlib import sha256
from pathlib import Path
import json
import sys

import numpy as np
import kit74
import checks71
import audit71
import design74

prior = kit74.kit73.model
pouch_design = prior.design
b = prior.b
INBOARD = prior.prior.INBOARD


def battery_lane(body, margin=0.0):
    # The old test stopped at the installed position. Sweep the whole pack
    # until its trailing end clears the front of the actual holder.
    pack = pouch_design.pack().translate((INBOARD, 0, 0))
    x0, _, z0, x1, _, z1 = pack.bounding_box()
    _, ymin, _, _, ymax, _ = body.bounding_box()
    return b.box(x0 - margin, x1 + margin, ymin - 1, ymax + 1, z0 - margin, z1 + margin)


def guard_comparison(body):
    # A side-on projection can hide a sideways detour. Compare both solids
    # below the bought socket, across the exposed lower fork and its two tips.
    region = b.box(12.5, 31., -6.5, 4.8, -8., 5.1)
    right = body ^ region
    left_reflected = body.mirror((1., 0., 0.)) ^ region
    return dict(left_mm3=left_reflected.volume(), right_mm3=right.volume(),
                difference_mm3=(left_reflected - right).volume() + (right - left_reflected).volume())


def exit_clearance(body, pack):
    # The rail may touch the pouch while it holds it. Once the nose leaves
    # the seated position, measure the extra room round its four long edges.
    x0, y0, z0, x1, _, z1 = pack.bounding_box()
    front = body.bounding_box()[1] - 1.
    margins = (0., .05, .10, .15, .20, .25, .30)
    return {f'{gap:.2f}': max(0., (body ^ b.box(x0-gap, x1+gap, front, y0,
                                                   z0-gap, z1+gap)).volume()) for gap in margins}


def exposed_fork(body):
    # This box includes the whole former hanging tip in the user's underside
    # view. Every bit of exposed carrier here should belong to a guard beam.
    region = b.box(-31., -10., -8.8, 15., -3., 6.9)
    branches = [design74.outer_leg(), design74.inner_branch(), design74.rear_leg()]
    intended = b.union(branches)
    deck = b.box(-31., -10., -9.4, 15., 7.28, 8.87)
    return dict(extra_mm3=max(0., ((body - intended) ^ region).volume()),
                missing_mm3=max(0., ((intended - body) ^ region).volume()),
                joined_beam_solids=len(intended.decompose()),
                embedded_roots_mm3=[max(0., (member ^ body ^ deck).volume()) for member in branches])


def verify():
    export = kit74.OUT / kit74.HOLDER
    carrier = b.load(export)
    old = b.load(prior.OUT / kit74.HOLDER)
    lane = battery_lane(carrier)
    # Only the intended contact shoe may spring aside while the cell passes.
    shoe = pouch_design.shoe().translate((INBOARD, 0, 0))
    pack = pouch_design.pack().translate((INBOARD, 0, 0))
    rigid = carrier - shoe
    modules = json.loads((prior.OUT / 'assembly-guide.json').read_text())['modules']
    bought = modules['key']
    seated = bought['steps'][-1]['samples'][-1]
    hardware = {}
    for name, actor in bought['actors'].items():
        if name == 'rod' or name.startswith(('socket_', 'switch_')):
            shape = b.load(prior.OUT / actor['file']).transform(np.array(seated[name]).reshape(3, 4))
            hardware[name] = max(0., (shape ^ lane).volume())
    # The battery is fitted last, with the centre assembly already on its pin.
    # Include the connectors and harness where they are actually illustrated.
    centre = modules['dfr']
    at_rest = centre['steps'][-2]['samples'][-1]
    for name in ('cap', 'lid', 'sensor', 'board', 'connector', 'gravity_plug', 'op1_wire', 'sensor_lead'):
        shape = b.load(prior.OUT / centre['actors'][name]['file']).transform(np.array(at_rest[name]).reshape(3, 4))
        hardware[name] = max(0., (shape ^ lane).volume())
    pouch_design.old.k.old.configure_new_op1()
    spaces = checks71.c70.placed_spaces()
    poses, hits = checks71.c70.routes(carrier, spaces)
    for key in ('key_0', 'key_3'):
        for name, route in spaces.items():
            if name.startswith(key) and ('soldered_socket' in name or name.endswith('socket_tape_zone')):
                hardware[name] = max(0., (route[-1] ^ lane).volume())
    op1 = {name: max((carrier ^ pose).volume() for pose in route)
           for name, route in audit71.op1_routes().items()}
    report = dict(revision='R74', carrier_sha256=sha256(export.read_bytes()).hexdigest(),
                  physical_fit_verified=False, solids=len(carrier.decompose()),
                  key_poses=poses, key_obstructions=hits, op1_intersections_mm3=op1,
                  lane_bounds_mm=lane.bounding_box(), old_lane_overlap_mm3=((old - shoe) ^ lane).volume(),
                  rigid_lane_overlap_mm3=(rigid ^ lane).volume(), spring_contact_mm3=(carrier ^ shoe ^ pack).volume(),
                  front_exit_overlap_by_extra_clearance_mm3=exit_clearance(rigid, pack),
                  fitted_hardware_lane_overlap_mm3=hardware,
                  guard=guard_comparison(carrier), old_guard=guard_comparison(old),
                  exported_fork=exposed_fork(carrier))
    fork = report['exported_fork']
    report['passes'] = bool(report['solids'] == 1 and carrier.status() == prior.mf.Error.NoError
                            and poses == 336 and not hits and max(op1.values()) < .01
                            and report['old_lane_overlap_mm3'] > 50 and report['rigid_lane_overlap_mm3'] < .01
                            and .1 < report['spring_contact_mm3'] < 4 and max(hardware.values()) < .01
                            and fork['extra_mm3'] < .01 and fork['missing_mm3'] < .01
                            and fork['joined_beam_solids'] == 1 and min(fork['embedded_roots_mm3']) > .5)
    (kit74.OUT / 'fit74.json').write_text(json.dumps(report, indent=2) + '\n')
    if not report['passes']:
        raise ValueError(report)


if __name__ == '__main__':
    verify()
