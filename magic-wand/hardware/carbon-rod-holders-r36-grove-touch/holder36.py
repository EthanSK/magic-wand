"""Fit the Seeed Grove touch board to the reinforced R35 keys.

Run assembly36.py to check and export the complete assembly and its motions.
"""

from functools import lru_cache
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R35 = HERE.parent / "carbon-rod-holders-r35-backed-roots"
sys.path.insert(0, str(R35))
import holder35 as old

h = old.prior
r = h.r
box, union = h.box, h.union
BRACKET = "Grove_Touch_Bracket"
# +Y points towards the two-key end in the viewer. Seeed's 20 mm hole
# pitch runs along Y after rotating its module. Both screws stay on X = 0.
BOARD_Y = .8
BOARD_Z = 19.35
HOLES = (BOARD_Y - 10., BOARD_Y + 10.)
SERVICE_LIFT = 14.
PILOT_DEPTH = 2.95
BOSS_DEPTH = 3.45
# The exact supplier part is Seeed 101020037, Pi Hut 103326. The seller
# photos show V1.1, with a straight DIP socket under the electrode face.
# Board/drill dimensions are from Seeed's drawing and V1.0 Eagle file.
# The 2.7 mm plug projection and PCB underside component cover are envelopes
# for first-fit, pending measurement of the actual mated cable.


def cylinder(x, y, z0, z1, radius):
    return mf.Manifold.cylinder(z1 - z0, radius, radius, 48).translate((x, y, z0))

def board():
    profile = mf.CrossSection.square((20., 20.),center=True).offset(-.8).offset(.8,mf.JoinType.Round)
    profile += mf.CrossSection.circle(2.1,48).translate((0., 10.))
    profile += mf.CrossSection.circle(2.1,48).translate((0., -10.))
    for x in (-10., 10.):
        profile -= mf.CrossSection.circle(2.1,48).translate((x,0.))
    for y in (-10., 10.):
        profile -= mf.CrossSection.circle(1.1,48).translate((0., y))
    return mf.Manifold.extrude(profile,1.6).translate((0., BOARD_Y, BOARD_Z))

def electrode():
    return cylinder(1.6,BOARD_Y,BOARD_Z+1.59,BOARD_Z+1.68,5.8)

def housing():
    return box(-8.6,-3.6,BOARD_Y-5.,BOARD_Y+5.,BOARD_Z-7.7,BOARD_Z)

def plug():
    return box(-8.55,-3.65,BOARD_Y-4.8,BOARD_Y+4.8,BOARD_Z-10.4,BOARD_Z-7.7)

def components():
    return box(-8.9,-5.45,BOARD_Y-9.65,BOARD_Y+9.65,BOARD_Z-1.35,BOARD_Z)

def lead(radius=1.1, lift=0.):
    # The socket faces the rod side. Bend the wire towards the three-key
    # end where it has an open route beside the rod and finger-guard ribs.
    points = [(-6.25, BOARD_Y, BOARD_Z - 9.8 + lift),(-6.30,BOARD_Y,BOARD_Z-12.15),
              (-6.5,BOARD_Y-1.15,BOARD_Z-13.25),(-6.85,BOARD_Y-3.40,BOARD_Z-13.7),
              (-7.40,BOARD_Y-6.7,BOARD_Z-13.7),(-9.6,BOARD_Y-9.0,BOARD_Z-13.3)]
    spheres = [mf.Manifold.sphere(radius,24).translate(point) for point in points]
    return union(mf.Manifold.batch_hull([a,b]) for a,b in zip(spheres,spheres[1:]))

def fastener(y):
    return (cylinder(0., y, BOARD_Z - 2.4, BOARD_Z + 1.6, 1.)
            + cylinder(0., y, BOARD_Z + 1.6, BOARD_Z + 2.55, 1.9))


def fasteners():
    return union(fastener(y) for y in HOLES)

def pilot():
    return union(cylinder(0., y, BOARD_Z - PILOT_DEPTH, BOARD_Z + .1, .85) for y in HOLES)

def boss(y):
    support = cylinder(0., y, BOARD_Z - BOSS_DEPTH, BOARD_Z, 2.25)
    taper = r.d.wedge(-1.55,1.55,[(y-2.65,BOARD_Z-.32),
                     (y-.25,BOARD_Z-2.72),(y+1.4,BOARD_Z-2.72),
                     (y+1.4,BOARD_Z)])
    return support+taper

@lru_cache(maxsize=1)
def bracket():
    # Keep the R35 hinge, actuator, reinforced front feet, and their two tear-off ties.
    base = old.bracket() - box(-11.,11.,-13.,16.1,BOARD_Z,25.)
    pocket = box(-9.2,-3.15,BOARD_Y-5.55,BOARD_Y+5.55,6.,BOARD_Z+.1)
    smd = box(-9.15,-5.15,BOARD_Y-9.85,BOARD_Y+9.85,BOARD_Z-1.55,BOARD_Z+.1)
    # Carry the rear screw from the existing floor on a central rib. A
    # transverse bar would start as an unsupported span between the rails
    # in the front-down print orientation.
    keel = r.d.wedge(-1.62, 1.62, [
        (3.05, BOARD_Z - .76),
        (5.85, BOARD_Z - 3.25),
        (HOLES[1] + 1.25, BOARD_Z - 3.25),
        (HOLES[1] + 1.25, BOARD_Z),
        (3.05, BOARD_Z),
    ])
    # Keep a backed load path below the forward pilot and the solder
    # relief. The left branch ends where the socket pocket begins.
    pilot_floor = box(-2.35, 2.35, old.TOUCH_WEB_FRONT, -7.3, 15.88, 18.47)
    solder_floor = r.d.wedge(-9.30, -4.98, [
        (-10.22, 18.25), (-9.19, 17.23), (-4.76, 17.23),
        (-4.76, 18.49), (-10.22, 18.49),
    ])
    shape = (base + keel + pilot_floor + solder_floor + union(boss(y) for y in HOLES)) - pocket - smd - pilot()
    return h.H.base.clean(shape - box(-12., 12., -15., old.TOUCH_WEB_FRONT, 0., 28.), BRACKET)

def carrier_pocket():
    # Open the deck for the mated plug and the forward exit. The board is
    # unplugged above the bracket during service, after the wires are fed back.
    socket = box(-9.05,-3.15,BOARD_Y-5.40,BOARD_Y+5.40,BOARD_Z-8.1,BOARD_Z)
    mate = box(-9.0,-3.2,BOARD_Y-5.20,BOARD_Y+5.2,BOARD_Z-10.8,BOARD_Z-7.2)
    feed = lead(1.5)
    entry = mf.Manifold.batch_hull([mate, mate.translate((0.,0.,3.2))])
    sweep = union(r.world(part,angle) for part in (socket,entry,feed)
                  for angle in (-r.REST, -r.REST/2, 0.))
    return sweep

@lru_cache(maxsize=1)
def carrier():
    return h.H.base.clean(old.geometry()[0] - carrier_pocket(), "Key_Carrier")


def checks():
    """Check the whole stroke and the paths to fit the two removable assemblies."""
    original, working, fixed, guards = old.geometry()
    key = carrier()
    paddle = bracket()
    hardware = h.hardware()
    rod = working["unloaded_clip_bore"]
    keys = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4)
                 for part in ("switch", "maximum_socket", "cap_travel"))
    static = key + rod + keys + union(solid for name, solid in hardware.items() if name != "plunger")
    pcb_group = board() + housing() + components() + electrode()
    moving = paddle + pcb_group + plug() + fasteners()
    angles = np.linspace(-r.REST, 0., 25)
    clearance = {
        "hinge_stroke": r._max((r.world(moving, a), static) for a in angles),
        "cable_stroke": r._max((r.world(lead(), a), static + r.world(paddle, a)) for a in angles),
        "pinched_bracket_drop": r._max(
            (r.world(r.bent(paddle)).translate((0., 0., z)), static)
            for z in np.linspace(0., 8., 21)),
        "bracket_arm_release": r._max((r.world(r.bent(paddle, b)), static)
                                      for b in np.linspace(0., 1., 13)),
        "preplugged_board_drop": r._max(
            (r.world((pcb_group + plug()).translate((0., 0., z))), static + r.world(paddle))
            for z in np.linspace(0., SERVICE_LIFT, 25)),
        # The free tail is already fed through the opening, so only the
        # length of cable between the plug and the bend changes.
        "wired_board_feed": r._max(
            (r.world(lead(1.45, lift=z)), static + r.world(paddle))
            for z in np.linspace(0., SERVICE_LIFT, 25)),
        "grove_board_on_rod": r._max((r.world(pcb_group + plug() + lead(), a), rod) for a in angles),
    }
    protected = {**guards, **{name: solid for name, (solid, _) in old.key_braces().items()},
                 "OP1 mounting shoulders": h.straighten(h.h32.mount_saddles()),
                 "fixed hinge supports": r.supports().translate((0., r.CLICK_SHIFT, 0.)),
                 "fixed click stops": h.stop_posts()}
    cut = original - key
    removed = {name: (solid ^ cut).volume() for name, solid in protected.items()}
    bonds = [(paddle ^ boss(y)).volume() for y in HOLES]
    stop_parts = h.stop_posts().decompose()
    stopped_paddle = r.world(paddle, 0.)
    stops = [(r.world(paddle, .002) ^ stop).volume() for stop in stop_parts]
    stop_overlap_at_limit = (stopped_paddle ^ h.stop_posts()).volume()
    # Measure available motion at the first hard stop. A pusher overlap
    # beyond that angle would say nothing about whether it can click.
    travel_low, travel_high = 0., .80
    for _ in range(15):
        candidate = (travel_low + travel_high) / 2
        shift = hardware["plunger"].translate((0., 0., -candidate))
        if (stopped_paddle ^ shift).volume() > .00002:
            travel_low = candidate
        else:
            travel_high = candidate
    # A straight drop of the established guards tests the radial clearance.
    # Less than 1 mm cannot be treated as free travel: the rod snaps in and
    # those ribs carry finger load and flex with the clip.
    guard = union(guards.values())
    lower = {}
    for delta in (0., .5, 1., 1.5, 2.):
        lowered = guard.translate((0., 0., -delta))
        lower[str(delta)] = (lowered ^ rod).volume()
    separation = float(keys.bounding_box()[3] - keys.bounding_box()[0])
    return {
        "pcb_width_mm": 20.,
        "screw_x_mm": 0.,
        "screw_pitch_mm": HOLES[1] - HOLES[0],
        "paddle_seat_drop_mm": r.BOARD_Z[0] - BOARD_Z,
        "key_carrier_seat_drop_mm": 0.,
        "pcb_front_y_mm": r.world(board()).bounding_box()[1],
        "key_assembly_span_mm": separation,
        "removed_carrier_mm3": cut.volume(),
        "protected_feature_removal_mm3": removed,
        "guard_overlap_with_rod_by_hypothetical_drop_mm3": lower,
        "clearance_overlap_mm3": clearance,
        "screw_boss_material_mm3": bonds,
        "measured_nominal_plunger_travel_to_stop_mm": round(travel_low, 4),
        "stop_overlap_at_limit_mm3": stop_overlap_at_limit,
        "stop_contacts_just_beyond_limit_mm3": stops,
        "screw_pilot_depth_mm": PILOT_DEPTH,
        "service_lift_mm": SERVICE_LIFT,
        "hinge_arm_bending_estimate": r.h29.arm_estimate(),
        "passed": bool(
            max(clearance.values()) < .035 and max(removed.values()) < .005
            and min(bonds) > 25. and .1 < travel_low < .5
            and stop_overlap_at_limit < .0002 and min(stops) > .0002
            and len(key.decompose()) == len(paddle.decompose()) == 1
        ),
    }
