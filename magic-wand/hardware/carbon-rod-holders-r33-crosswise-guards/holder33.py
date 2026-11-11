"""R33 crosswise finger guards and open touch-bracket crossbar, based on R32."""

from functools import lru_cache
from pathlib import Path
import json
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
R32 = HERE.parent / 'carbon-rod-holders-r32-complete-assembly'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R32))
import holder32 as previous

r31, H = previous.r31, previous.H
old = r31.h28.r
box, union = previous.box, previous.union
REVISION = HERE.name
RIB_ROWS = (.2, 3.45, 6.7)
RIB_RADIUS = .84


def rounded_run(points, radius=RIB_RADIUS):
    """A round finger-contact profile swept through the specified centres."""
    stations = [mf.Manifold.sphere(radius, 20).translate(point) for point in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(stations, stations[1:]))


def rib_at(row, number, side):
    # Y decreases as the rear-down print grows. The inner taper leaves the
    # rigid saddle. The outer taper leaves the existing edge rail so the
    # prewired switch can still slide above the rounded transverse section.
    root = 14.8 + .8 * number
    distance = root - row
    out_y = 13.2 + 1.15 * number
    out_x = 22.3 if side > 0 else 28.3
    far_x = 18.35 if side > 0 else 21.4
    points = [(3.2, root, 5.35), (6.05, root - distance * .33, 4.85),
              (8.95, root - distance * .60, 4.45),
              (11.05, root - distance * .87, 1.35), (13.2, row, 1.25),
              (far_x, row, 1.25), (far_x + 1.5, row + 2.2, 1.25)]
    if side > 0:
        points.extend(((out_x - 1.6, 9.55, 1.35), (out_x - .65, out_y - 2., out_y - 9.),
                       (out_x, out_y, out_y - 6.55)))
    else:
        # The upper-left switch's tape space crosses this whole rail. Run
        # above it until the branch has passed the front of that switch bay.
        points.extend(((25.5, 9.55, 2.65), (27.45, 10.65, 4.15), (28.10, 11.8, 5.75),
                       (28.85, 12.95, 6.98), (29.05, 14.40, 7.65), (29.2, 15.4, 7.65)))
    return rounded_run([(side * x, y, z) for x, y, z in points])


def edge_rails():
    """Preserve the outside pair of the already checked R32 runners."""
    right = next(beam for beam in old.G['beams'] if beam['name'] == 'R3')
    left = {**right, 'name': 'L3', 'root_y_mm': 16.,
            'plan_y_x_mm': [[16., -28.3], [-9., -28.3]]}
    return union(r31.d.guard23._grow([beam])[0] for beam in (right, left))


@lru_cache(maxsize=1)
def bracket():
    # Leave the middle pusher, side rails, arm roots and travel stops solid.
    # Each window closes to a point towards the higher print layers.
    profile = mf.CrossSection([[(3.2, -2.45), (6.9, -2.45), (6.9, .75),
                               (5.05, 2.65), (3.2, .75)]])
    window = mf.Manifold.extrude(profile.offset(-.35).offset(.35), .74).translate((0., 0., 18.48))
    return H.base.clean(r31.cap() - window - window.mirror((1., 0., 0.)), 'DFRobot_Hole_Bracket')


@lru_cache(maxsize=1)
def rib_candidates():
    carrier, working = previous.geometry()
    # Keep the old bonding lands where the runners overlap the original deck.
    runners = r31.h28.runners()
    fixed = carrier - (runners - old.carrier_base() - edge_rails())
    _, _, plug_opening = previous.reliefs()
    plug_and_wire = previous.plug() + previous.cable(1.6)
    plug_drop = mf.Manifold.batch_hull([plug_and_wire, plug_and_wire.translate((0., 0., -9.))])
    keepouts = union((old.guard_keepout(), old.slab_cutters(), plug_opening, plug_drop,
                      working['key_3_socket_tape_zone']))
    ribs = {}
    for number, row in enumerate(RIB_ROWS):
        for side, sign in [('R', 1), ('L', -1)]:
            ribs[f'{side}{number + 1}'] = rib_at(row, number, sign) - keepouts
    # The rounded starts extend above their landings in the rear-down build.
    # Clip the top tips and give the lower branches a rising web from already
    # printable material at the saddle or edge rail.
    saddle_tip = box(-5., 5., 16.80, 19., 3., 9.)
    ribs['R3'] -= saddle_tip
    ribs['L3'] -= saddle_tip
    for name, sign, y in (('L2', -1, 15.6), ('L3', -1, 16.4), ('R3', 1, 16.4)):
        web = rounded_run([(sign * 2.75, y + 1.6, 4.45), (sign * 3.0, y + .55, 4.85),
                           (sign * 3.42, y - .6, 5.55)], radius=.67)
        ribs[name] += web - keepouts
    return working, fixed, ribs, runners


def rib_metrics(fixed, ribs):
    result = {}
    for name, rib in ribs.items():
        sign = 1 if name.startswith('R') else -1
        inside = sorted((0., sign * 9.))
        outside = sorted((sign * 20., sign * 34.))
        bond = rib ^ fixed
        result[name] = {
            'volume_mm3': round(rib.volume(), 4),
            'pieces': len(rib.decompose()),
            'rod_mount_contact_mm3': round((bond ^ box(*inside, -12., 35., 0., 13.)).volume(), 4),
            'edge_contact_mm3': round((bond ^ box(*outside, -12., 35., 0., 13.)).volume(), 4),
            'bounds': tuple(round(x, 3) for x in rib.bounding_box()),
            'piece_bonds_mm3': [round((piece ^ fixed).volume(), 4) for piece in rib.decompose()],
        }
    return result


def route_overlaps(guard, working):
    result = {}
    for name, space in working.items():
        if isinstance(space, mf.Manifold):
            result[name] = round((guard ^ space).volume(), 5)
        else:
            result[name] = r31._max((pose, guard) for pose in space.poses())
    return result


def bracket_metrics():
    _, plunger = previous.switch()
    stops = r31.k27.towards_top(r31.d.stop_posts()).decompose()
    before, after = r31.cap(), bracket()
    depressed_plunger = plunger.translate((0., 0., -r31.d.DEPRESSION))
    return {
        'removed_mm3': round(before.volume() - after.volume(), 4),
        'arms_removed_mm3': r31._vol((before - after) ^ r31.arms()),
        'old_stop_contacts_mm3': [r31._vol(r31.world(before, .25) ^ stop) for stop in stops],
        'stop_contacts_mm3': [r31._vol(r31.world(after, .25) ^ stop) for stop in stops],
        'old_pusher_contact_mm3': r31._vol(r31.world(before, .20) ^ depressed_plunger),
        'pusher_contact_mm3': r31._vol(r31.world(after, .20) ^ depressed_plunger),
    }


def fingertip_reaches(carrier):
    radius = 5.
    finger = mf.Manifold.sphere(radius, 48)
    low_carrier = carrier ^ box(-40, 40, -20, 40, -10, 7.6)
    obstacles = low_carrier + old.cyl(4.0, -40, 100).rotate((-90, 0, 0))
    hits = {}
    for name, contact in old.h20.contact_envelopes().items():
        if not name.startswith(('key_0_', 'key_2_')):
            continue
        x0, y0, z0, x1, y1, _ = contact.bounding_box()
        points = ((x, y, z0 - radius - .01) for x in np.linspace(x0 + .2, x1 - .2, 3)
                  for y in np.linspace(y0 + .2, y1 - .2, 3))
        hits[name] = sum((finger.translate(point) ^ obstacles).volume() < .035 for point in points)
    return hits


@lru_cache(maxsize=1)
def screen():
    working, fixed, ribs, old_runners = rib_candidates()
    guard = union(ribs.values())
    carrier = H.base.clean(fixed + guard, 'Key_Carrier')
    former, _ = previous.geometry()
    stats = rib_metrics(fixed, ribs)
    overlaps = route_overlaps(guard, working)
    bracket_fit = bracket_metrics()
    fit = previous.checks(carrier, working)
    fingertip_before = fingertip_reaches(former)
    fingertip_after = fingertip_reaches(carrier)
    passed = (fit['passed'] and max(overlaps.values()) < .035
              and all(s['pieces'] == 1 and min(s['rod_mount_contact_mm3'], s['edge_contact_mm3']) > 1.
                      for s in stats.values())
              and bracket_fit['arms_removed_mm3'] < .005
              and np.allclose(bracket_fit['stop_contacts_mm3'], bracket_fit['old_stop_contacts_mm3'], atol=.005)
              and abs(bracket_fit['pusher_contact_mm3'] - bracket_fit['old_pusher_contact_mm3']) < .005
              and all(fingertip_after[name] <= before for name, before in fingertip_before.items()))
    return {
        'ribs': stats,
        'guard_previous_mm3': round(old_runners.volume(), 4),
        'crosswise_ribs_mm3': round(guard.volume(), 4),
        'carrier_removed_mm3': round(former.volume() - carrier.volume(), 4),
        'bracket_fit': bracket_fit,
        'swept_guard_overlap_mm3': overlaps,
        'fingertip_reaches_before_of_9': fingertip_before,
        'fingertip_reaches_after_of_9': fingertip_after,
        'r32_fit': fit,
        'passed': bool(passed),
    }


if __name__ == '__main__':
    print(json.dumps(screen(), indent=2))
