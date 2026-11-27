"""R77 key layout, finger contact surface and straight DFRobot wire exit."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import json
import sys

import numpy as np
import manifold3d as mf

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r76-matched-finger-rest'))
import design76 as old
import hinge70
import checks71

b = old.b
base = old.prior.r71.r70.base
DECK = old.prior.DECK
HOLDER = old.HOLDER
hinge = hinge70.h69
PADDLE, WIRES = hinge.PADDLE, hinge.WIRES
PITCH = old.prior.KEYS['key_4'][1]
UPPER_MOVE = PITCH - old.prior.KEYS['key_3'][1]
KEY0 = old.prior.KEYS['key_0']


def unturn(shape):
    x, y = KEY0
    return shape.translate((-x, -y, 0)).rotate((0, 0, -90)).translate((x, y, 0))


def lower_slide():
    # The soldered socket clears both round forks if it enters 1.5 mm toward
    # the hinge, then centres below its holes before its final upward press.
    return (
        [(x, 1.5, -1.8) for x in np.linspace(-22.0, 0.0, 42)]
        + [(0.0, y, -1.8) for y in np.linspace(1.5, 0.0, 5)[1:]]
        + [(0.0, 0.0, z) for z in np.linspace(-1.8, 0.0, 6)[1:]]
    )


def places(name, poses):
    if name.startswith('key_3_'):
        return [p.translate((0, UPPER_MOVE, 0)) for p in poses]
    if name.startswith('key_0_'):
        if name.endswith('soldered_socket_slide'):
            # Keep the approach from outside the holder while turning the socket itself.
            seated = unturn(poses[-1])
            return [seated.translate(v) for v in lower_slide()]
        return [unturn(p) for p in poses]
    return poses


@lru_cache(maxsize=1)
def spaces():
    old.prior.r71.old.k.old.configure_new_op1()
    return {k: places(k, v) for k, v in checks71.c70.placed_spaces().items()}


def finger_rest():
    # The black socket no longer needs the kink at the outside edge. Keep the
    # two curves where the finger rests, and open the outer lobe for assembly.
    root = b.box(-31.0, -9.0, -10.0, 16.0, -4.0, DECK + 0.44)
    fork = (old.mirrored_return(14.2) + old.mirrored_return(28.3)) ^ root
    r62 = old.prior.r71.r62
    # Shorten the back of the small remaining eye. The upper black socket
    # needs to come up through the opening on this bank at the closer pitch.
    start = np.array(r62.CROWN_START, float)
    end = np.array(r62.CROWN_END, float)
    start[1] -= old.EYE_SHIFT + 1.6
    end[1] -= old.EYE_SHIFT
    bars = [
        old.prior.r71.r61.curve([start, (x, 6.85, 0.88), (x, 4.91, 0.88), end], 1.26)
        for x in (15.1, 22.1)
    ]
    eye = b.union(bars).mirror((1, 0, 0))
    rear = old.old.click_end.rounded_beam(
        [
            (-13.60, 16.30, 7.85, 1.30, 1.32, 1.30),
            (-13.15, 14.45, 6.94, 1.25, 1.29, 1.23),
            (-13.25, 12.70, 6.27, 1.21, 1.25, 1.17),
            (-13.42, 11.13, 5.93, 1.17, 1.21, 1.14),
            (-13.70, 10.48, 5.31, 1.16, 1.16, 1.14),
            (-14.09, 9.70, 4.04, 1.17, 1.18, 1.17),
            (-14.75, 8.90, 2.78, 1.20, 1.20, 1.20),
            (-16.55, 8.42, 1.73, 1.23, 1.23, 1.22),
            (-18.66, 8.10, 1.02, 1.26, 1.25, 1.24),
            (-20.40, 7.55, 0.88, 1.26, 1.26, 1.26),
        ]
    )
    return fork + eye + rear


def cap_stock(old_body):
    # Rebuild the two actual key seats inside the moulded perimeter. The rounded
    # front and side edge belongs to the shell and follows the original section.
    # The R16 teardrop cutters point toward print-up in either socket orientation.
    x0, x1 = -29.95, -12.05
    plate_top = base.plate_top()
    zone = b.box(x0, x1, -9.45, 28.25, DECK - 0.002, plate_top + 0.003)
    a = old_body ^ zone
    # Each bank has a convex exterior around the lower and upper mounts.
    # Use short sections along the rounded body's perimeter, preserving the
    # exterior taper at the battery corner. Fill old cutouts only in the key bay.
    limits = [-9.45, 8.95, 28.25]
    filled = []
    for lo, hi in zip(limits, limits[1:]):
        # Use an intact outer shell at each height; do not grow across the
        # deck's front or side radius when restoring the old socket openings.
        band = b.box(x0, x1, lo, hi, DECK - 0.002, plate_top + 0.003)
        body_band = a ^ band
        filled.append(body_band.hull())
    stock = b.union(filled)
    cuts = []
    for y, rot in ((0, 0), (PITCH, 180)):
        z0 = base.PCB_Z
        bay = base.P['bay']
        local = [
            base.rr(
                bay['plate_opening_mm'],
                bay['plate_opening_mm'],
                0.2,
                z0 + bay['plate_bottom_mm'] - 0.01,
                plate_top + 0.1,
            ),
            base.rr(
                2 * bay['clip_relief_half_x_mm'],
                2 * bay['clip_relief_half_y_mm'],
                0.5,
                z0,
                z0 + bay['plate_bottom_mm'] + 0.01,
            ),
        ]
        cuts.append(b.union(local).rotate((0, 0, rot)).translate((-21.0, y, 0)))
        for hx, hy, r in base.backplate_hole_centres(rot):
            cuts.append(base.teardrop(-21 + hx, y + hy, r, DECK - 0.10, z0 + 1))
    return (old_body + stock) - b.union(cuts)


def carrier():
    orig = b.load(old.OUT / HOLDER)
    bare = orig - b.box(-30.8, -10.8, -9.2, 16.9, -4.0, DECK - 0.002)
    body = cap_stock(bare)
    # Flatten the old socket pad and discarded guard remnants projecting below
    # the nominal underside. Keep the battery rails, springs and rod saddle.
    face = b.box(-30.1, -12.2, -8.90, old.prior.r71.RAIL_FROM_Y - 0.01, DECK - 0.70, DECK)
    body -= face
    # Returning this key to the working right-hand orientation also returns
    # its two socket bosses and solder tab to the proven backplate openings.
    # Copy that key seat above the underside, keeping the rounded outer edge.
    lower_seat = b.box(-29.6, -11.55, -8.8, 8.65, DECK - 0.002, base.plate_top() + 0.02)
    right_seat = orig.translate((-42.0, 0.0, 0.0))
    body = (body - lower_seat) + (right_seat ^ lower_seat)
    # Move the upper seat with its existing self-supporting underside. Cutting
    # a plain square backplate here leaves a long unbacked roof across the key.
    upper_seat = b.box(
        -29.8, -11.8, PITCH - 8.8, PITCH + 8.8, DECK - 0.002, base.plate_top() + 0.02
    )
    upper_donor = orig.translate((0, UPPER_MOVE, 0))
    body = (body - upper_seat) + (upper_donor ^ upper_seat)
    # The outer shelf above the former battery wall stayed behind when R72
    # shifted the rails 8 mm inboard. Follow the opposite rounded shoulder
    # outside today's rail. The disposable base now lands on the shoulder.
    shoulder = b.box(12.0, 31.0, 26.6, 36.6, 5.7, base.plate_top() + 0.02)
    keep = (orig ^ shoulder).mirror((1, 0, 0))
    trim = b.box(-31.0, -20.43, 26.65, 36.6, 5.7, base.plate_top() + 0.02)
    body = (body - trim) + (keep ^ trim)
    keys = spaces()
    clearance = b.union([b.union(ps) for k, ps in keys.items() if k.startswith(('key_0', 'key_3'))])
    body -= clearance
    return body + finger_rest()


def straight_wires():
    # The three conductors leave the end of the plug toward the top of the
    # keypad. Rise over the axle and clip without a sideways branch.
    start = hinge.wire_paths()[0][0][1]
    z = hinge.b.SEAT_Z - 2.85
    strands = []
    for x in (-2.0, 0.0, 2.0):
        points = [(x, start, z), (x, hinge.PLUG_REAR_Y, z)]
        for t in np.linspace(0, 1, 25)[1:]:
            points.append((x, hinge.PLUG_REAR_Y + 4.8 * t, z + (19.1 - z) * t * t * (3 - 2 * t)))
        points.append((x, hinge.AXIS + 13.0, 19.1))
        strands.append(hinge.r61.run(points, hinge.r61.LEAD_R))
    return b.union(strands)


def paddle():
    path = old.prior.r71.OUT / PADDLE
    body = b.load(path)
    # Both beams can use the wider, reinforced left post once the wire bundle
    # no longer turns behind the right journal. Copy only the rear hinge.
    aft = b.box(
        -12, 12, hinge.AXIS - 4.65, hinge.REAR + 0.25, hinge.KEEPER_Z - 3.5, hinge.b.SEAT_Z + 0.01
    )
    left = body ^ aft ^ b.box(-12, 0, hinge.AXIS - 5, hinge.REAR + 0.5, 7.0, 25.0)
    return (body - aft) + left + left.mirror((1, 0, 0))


def build():
    OUT.mkdir(exist_ok=True)
    guard = finger_rest()
    print(
        'guard routes',
        [
            (k, round(max((guard ^ p).volume() for p in ps), 3))
            for k, ps in spaces().items()
            if k.startswith(('key_0', 'key_3'))
        ],
        flush=True,
    )
    body = carrier()
    pcs = sorted(body.decompose(), key=lambda p: -p.volume())
    print(
        'components',
        [(p.volume(), p.bounding_box()) for p in pcs[1:] if abs(p.volume()) > 0.0001],
        flush=True,
    )
    if sum(abs(p.volume()) for p in pcs[1:]) > 0.025:
        raise ValueError('Detached carrier detail')
    shape = old.old.clean_export(OUT / HOLDER, pcs[0])
    old.old.clean_export(OUT / PADDLE, paddle())
    b.save_closed(OUT / WIRES, straight_wires())
    n, hits = checks71.c70.routes(shape, spaces())
    print('poses', n, len(hits), hits[:: max(1, len(hits) // 10)], flush=True)
    return shape


if __name__ == '__main__':
    build()
