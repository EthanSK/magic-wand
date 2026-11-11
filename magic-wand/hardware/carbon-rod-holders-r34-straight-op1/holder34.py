"""Straight OP1 board, with the same PCB height and rear snap hinge as R33."""

from functools import lru_cache
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
R33 = HERE.parent / 'carbon-rod-holders-r33-crosswise-guards'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R33))
import holder33 as previous

h32, r, H = previous.previous, previous.r31, previous.H
box, union = previous.box, previous.union
PCB_X = 7.45
STOP_X = 9.4
STOP_Z = r.d.STOP_Z
PLUG_RISE = 9.


def straighten(part):
    """Keep the actual board, socket, pin and screw geometry from R32."""
    y = h32.ACTUATOR_Y
    return part.translate((0., -y, 0.)).rotate((0., 0., -h32.PCB_YAW)).translate((PCB_X, y, 0.))


def stop_posts():
    foot = r.d.wedge(STOP_X - 1.12, STOP_X + 1.12, [(-8.75, 8.35), (-6.59, 8.35),
                    (-7.12, STOP_Z), (-8.43, STOP_Z)])
    return foot + foot.mirror((1., 0., 0.))


@lru_cache(maxsize=1)
def bracket():
    old_feet = r.mirrored(box(5.7, 7.4, -4.15, 5.05, 12.8, 18.52))
    old_pusher = box(-1.21, 1.21, r.d.PUSH_Y - 1.1, r.d.PUSH_Y + 1.8, 17.4, 18.53)
    pusher = r.d.wedge(PCB_X - .75, PCB_X + .85, [(r.d.PUSH_Y - 1.8, 19.16),
                     (r.d.PUSH_Y - .48, r.d.PUSH_Z), (r.d.PUSH_Y + .48, r.d.PUSH_Z),
                     (r.d.PUSH_Y + 2., 19.16)])
    stop = r.d.wedge(STOP_X - .71, STOP_X + .71, [(-11.62, 19.26), (-11.35, STOP_Z),
                     (-10.60, STOP_Z), (-9.68, 19.26)])
    return H.base.clean((previous.bracket() - old_feet - old_pusher) + pusher + stop + stop.mirror((1., 0., 0.)),
                        'DFRobot_Hole_Bracket')


@lru_cache(maxsize=1)
def hardware():
    body, plunger = h32.switch()
    return {name: straighten(solid) for name, solid in {
        'board': h32.board(), 'sockets': h32.sockets(), 'housing': h32.white_housing(),
        'plug': h32.plug(), 'op1_wire': h32.cable(), 'switch': body, 'terminals': h32.terminals(),
        'plunger': plunger, 'fasteners': h32.screws(),
    }.items()}


@lru_cache(maxsize=1)
def geometry():
    original, working = r.geometry()
    _, _, ribs, old_runners = previous.rib_candidates()
    deck = box(-7.1, 7.1, r.h28.BOTTOM_EDGE, r.k27.REAR, 7.24, 11.35)
    fixed = (original - (old_runners - previous.old.carrier_base() - previous.edge_rails())) + deck
    a, b = h32.EYELETS
    y = h32.ACTUATOR_Y
    seat_backing = r.d.wedge(PCB_X - 3.2, PCB_X + 3.2, [(b + y - 3.35, 6.05),
                            (b + y + 4.2, 6.05), (b + y + 3.05, h32.PCB_Z),
                            (b + y - 3.35, h32.PCB_Z)])
    slot, sockets, connector = (straighten(part) for part in h32.reliefs())
    pilots = straighten(h32.screw_pilots(h32.PCB_Z - 3.75))
    wire = hardware()['plug'] + straighten(h32.cable(1.55))
    drop = mf.Manifold.batch_hull([wire, wire.translate((0., 0., -PLUG_RISE))])
    existing_stops = r.k27.towards_top(r.d.stop_posts())
    fixed = ((fixed - existing_stops + seat_backing - slot) + straighten(h32.mount_saddles())
             + stop_posts()) - sockets - connector - drop - pilots
    fixed = r.h29.r.spaces16.carve(fixed, working, 'r34 straight OP1 mount')
    guard = {name: rib - sockets - connector - drop for name, rib in ribs.items()}
    carrier = H.base.clean(fixed + union(guard.values()), 'Key_Carrier')
    return carrier, working, fixed, guard


def checks():
    carrier, working, fixed, ribs = geometry()
    parts = hardware()
    board = union(parts[name] for name in ('board', 'sockets', 'housing'))
    plug = parts['plug'] + parts['op1_wire']
    mouse = union(parts[name] for name in ('switch', 'terminals', 'plunger'))
    rod = working['unloaded_clip_bore']
    keys = union(working[f'key_{index}_{part}'] for index in (0, 2, 3, 4)
                 for part in ('switch', 'maximum_socket', 'cap_travel'))
    no_caps = union(working[f'key_{index}_{part}'] for index in (0, 2, 3, 4)
                    for part in ('switch', 'maximum_socket'))
    assembly = carrier + keys + rod
    installed = assembly + board + plug + parts['switch'] + parts['terminals'] + parts['fasteners']
    attach = carrier + no_caps + rod
    moving = bracket() + r.sensor() + r.connector() + r.clips()
    overlap = {
        'pcb_drop': r._max((board.translate((0., 0., z)), attach) for z in np.linspace(0., h32.BOARD_RISE, 57)),
        'plug_install': r._max((plug.translate((0., 0., z)), attach + board) for z in np.linspace(-PLUG_RISE, 0., 37)),
        'switch_install': r._max((mouse.translate((0., 0., z)), assembly + parts['board'] + parts['sockets'] + parts['fasteners'])
                                 for z in np.linspace(0., 8., 33)),
        'hinge_stroke': r._max((r.world(moving, a), installed) for a in np.linspace(-r.REST, 0., 33)),
        'hinge_insert': r._max((r.world(r.bent(bracket())).translate((0., 0., z)), installed)
                               for z in np.linspace(0., 8., 33)),
        'hinge_release_arms': r._max((r.world(r.bent(bracket(), bend)), installed) for bend in np.linspace(1., 0., 17)),
        'touch_cable_stroke': r._max((r.world(r.gravity_lead(), a), installed) for a in np.linspace(-r.REST, 0., 25)),
        'hinge_mount_to_touch_pcb': r._vol(r.sensor() ^ bracket()),
        'rod_housing_and_wire': r._vol(rod ^ (parts['housing'] + plug)),
    }
    pusher = r._vol(r.world(bracket(), .20) ^ parts['plunger'].translate((0., 0., -r.d.DEPRESSION)))
    stops = [r._vol(r.world(bracket(), .25) ^ stop) for stop in stop_posts().decompose()]
    guard = previous.rib_metrics(fixed, ribs)
    support = [(straighten(h32.board()).translate((0., 0., -.2)) ^ carrier
                ^ box(PCB_X - 3.2, PCB_X + 3.2, eye + h32.ACTUATOR_Y - 2.9,
                      eye + h32.ACTUATOR_Y + 2.9, h32.PCB_Z - .25, h32.PCB_Z + .1)).volume() for eye in h32.EYELETS]
    fingertip = previous.fingertip_reaches(carrier)
    return {'board_yaw_degrees': 0., 'board_offset_mm': PCB_X, 'board_bottom_mm': h32.PCB_Z,
            'overlap_mm3': overlap, 'pusher_contact_mm3': pusher, 'stop_contacts_mm3': stops,
            'pcb_seat_contacts_mm3': support, 'finger_contact_probes_reaching_terminals': fingertip, 'ribs': guard,
            'passed': bool(max(overlap.values()) < .035 and pusher > .01 and min(stops) > .01 and min(support) > .1
                           and not any(fingertip.values()) and all(part['pieces'] == 1 and
                               min(part['rod_mount_contact_mm3'], part['edge_contact_mm3']) > 1. for part in guard.values()))}


if __name__ == '__main__':
    print(json.dumps(checks(), indent=2))
