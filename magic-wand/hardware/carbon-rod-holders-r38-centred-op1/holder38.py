"""R38: OP1 mouse-switch board centred over the rod.

Run assembly38.py to check and export the two edited parts and the guide.

Frame: X across the keys, +Y towards the two-key top row, +Z up from the
rod centre. The OP1 board is straight on X = 0 (R37: X = 7.45).

Two measured packaging adjustments make the exact centre possible:

- OP1_LIFT raises only the OP1 seat, so the photo-derived 5.9 mm coupled
  connector clears the crown of the 8 mm rod by 0.2 mm. The Choc seats,
  rod clips, hinge axis and stops keep their R37 heights.
- The Grove board, its two screw seats and its plug pocket move GROVE_X to
  the left, so the Grove socket hanging under that board passes beside the
  OP1 board. GROVE_LIFT raises the Grove seat by the same amount as the OP1
  seat, which keeps a printable roof between the switch plunger and the PCB.

The left-shifted Grove board then sets the Choc seat spacing. KEY_SHIFT is
the largest inward move that keeps 0.7 mm between that board and the caps.

The carrier is composed directly from the R22 parametric base. Obsolete
centre features from R26-R34 (old stop recess, rear-loading board channels,
side OP1 mount and its wire drop) are not carried over. Every hardware
opening is cut after the unions. OP1 board, connector and wire sizes remain
photo-derived envelopes.
"""

from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R37 = HERE.parent / "carbon-rod-holders-r37-adjustable-op1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(R37))
import holder37 as prior

grove = prior.base            # holder36: Seeed Grove board, plug and bracket seats
old = grove.old               # holder35: touch web
h = prior.h                   # holder34: straight OP1 hardware
r = prior.r                   # holder31: rear snap hinge
h32, h33 = h.h32, h.previous
h29, h28 = r.h29, r.h28
r22 = h28.r                   # holder22: parametric carrier base
H = h.H
box, union = h.box, h.union
BRACKET = prior.BRACKET
CARRIER = "Key_Carrier"

# --- layout -----------------------------------------------------------------
R37_KEY_X = 21.1
KEY_SHIFT = .1                # limited by the left-shifted Grove board; see checks()
KEY_X = round(R37_KEY_X - KEY_SHIFT, 3)
R37_PCB_X = 7.45
PCB_X = 0.                    # OP1 board centre line
OP1_LIFT = .9                 # local seat lift: plug bottom 4.2 over the 4.0 rod crown
GROVE_X = -2.                 # Grove PCB, both screw seats and plug pocket
GROVE_LIFT = .9               # Grove seat only; hinge, feet and stops unchanged
GROVE_SHIFT = (GROVE_X, 0., GROVE_LIFT)
ROD_R = 4.0                   # bought 8 mm carbon rod
DECK_HALF, DECK_TOP = 7.1, prior.DECK_TOP
RIB_RADIUS = .95              # 1.9 mm rounded guards, with fuller printed root joints
# Adjustable stop, moved beside the board: its old centre landing is now
# occupied by the OP1 board's front screw and the switch body.
STOP_X = 8.3
STOP_Y = -7.15                # bracket frame; world Y is STOP_Y + CLICK_SHIFT
STOP_HALF = 2.0
STOP_BOSS_BOTTOM = prior.STOP_BOSS_BOTTOM
BRACKET_HALF = 10.6
START_TURNS, PITCH = prior.START_TURNS, prior.PITCH
EARLY_ANGLE = prior.EARLY_ANGLE
SAMPLE_TURNS = tuple(np.linspace(0., START_TURNS, 10))
SWITCH_FREE_REFERENCE = prior.SWITCH_FREE_REFERENCE
BOARD_Z, BOARD_Y, HOLES = grove.BOARD_Z + GROVE_LIFT, grove.BOARD_Y, grove.HOLES
SERVICE_LIFT = grove.SERVICE_LIFT

# The earlier revisions read these module values when their solids are first
# built. Set them before any geometry is requested.
assert h.hardware.cache_info().currsize == 0 and h.bracket.cache_info().currsize == 0
assert h29.geometry.cache_info().currsize == 0 and r22.carrier_base.cache_info().currsize == 0
h.PCB_X = PCB_X
h28.KEY_X = KEY_X

def moved(shape):
    """Bracket-frame Grove part at this revision's seat."""
    return shape.translate(GROVE_SHIFT)


# Grove references at the shifted seat, for the checks and guide generator.
def board(): return moved(grove.board())
def electrode(): return moved(grove.electrode())
def housing(): return moved(grove.housing())
def plug(): return moved(grove.plug())
def components(): return moved(grove.components())
def lead(radius=1.1, lift=0.): return moved(grove.lead(radius, lift))
def fastener(y): return moved(grove.fastener(y))
def fasteners(): return moved(grove.fasteners())
def boss(y): return moved(grove.boss(y))
def pilot(): return moved(grove.pilot())
cylinder = grove.cylinder


def rod():
    return mf.Manifold.cylinder(140., ROD_R, ROD_R, 96).rotate((-90, 0, 0)).translate((0., -40., 0.))


# --- bought OP1 parts ---------------------------------------------------------
def op1_cable(radius=1.3):
    """Two-wire lead exits the plug end before turning beside the rod.

    The kit photo supports a longitudinal outlet, not the old draft's
    arbitrary +X corner start. Outlet height and bend stiffness remain
    photo-derived: this is a fit-trial envelope, not a measured harness.
    https://endgamegear.com/products/op1-universal-switch-set
    """
    y = h32.ACTUATOR_Y + h32.MATE_Y[1]
    z = (h32.PCB_Z - h32.PLUG_DEPTH + h32.MATE_TOP) / 2 + OP1_LIFT
    points = [(PCB_X, y - .2, z), (PCB_X, y + .8, z),
              (PCB_X + .5, y + 1.4, z), (PCB_X + 1.4, y + 1.7, z),
              (PCB_X + 3.5, y + 1.7, z), (PCB_X + 5.8, y + 1.7, z),
              (PCB_X + 7.3, y + 1.7, z - 1.2),
              (PCB_X + 8.1, y + 1.7, z - 3.2), (PCB_X + 8.1, y + 1.7, z - 6.8)]
    balls = [mf.Manifold.sphere(radius, 24).translate(p) for p in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))


@lru_cache(maxsize=1)
def wired_install_relief():
    """Keep the entire plugged-in lead clear while lowering or lifting the PCB."""
    lead_space = op1_cable(1.6)
    return union(lead_space.translate((0., 0., z))
                 for z in np.linspace(0., h32.BOARD_RISE, 33))


@lru_cache(maxsize=1)
def hardware():
    parts = {name: solid.translate((0., 0., OP1_LIFT)) for name, solid in h.hardware().items()}
    parts["op1_wire"] = op1_cable()
    return parts


def op1_seats():
    return h.straighten(h32.mount_saddles()).translate((0., 0., OP1_LIFT))


def op1_reliefs():
    """Openings for the board, three socket barrels, white housing, plug and wire."""
    y = h32.ACTUATOR_Y
    slot = box(PCB_X - 5.65, PCB_X + 5.65, y + h32.PCB_Y[0] - .65, y + h32.PCB_Y[1] + .65,
               h32.PCB_Z - .02, 16.5)
    barrels = h.straighten(h32.board_frame(h32.socket_local(.35, sweep=True)))
    white = box(PCB_X - h32.PLUG_HALF_X - .52, PCB_X + h32.PLUG_HALF_X + .52,
                y + h32.PLUG_Y[0] - .5, y + h32.PLUG_Y[1] + .55, h32.MATE_TOP - .35, 16.5)
    # Nothing is printed between the plug and the rod: the rod itself is the
    # limit for the coupled connector depth.
    mate = box(PCB_X - h32.MATE_HALF_X - .45, PCB_X + h32.MATE_HALF_X + .45,
               y + h32.MATE_Y[0] - .4, y + h32.MATE_Y[1] + .4, 2., h32.MATE_TOP + .15)
    wire = box(PCB_X - 1., PCB_X + 8.4, y + h32.MATE_Y[0] - .3, y + h32.PLUG_Y[1] + 1.3, -12., 5.9)
    pilots = h.straighten(h32.screw_pilots(h32.PCB_Z - 3.75))
    up = (0., 0., OP1_LIFT)
    # Keep the plug and wire openings down to the rod after lifting the seat.
    return (slot.translate(up), barrels.translate(up) + barrels,
            (white + mate + wire).translate(up) + mate + wire + wired_install_relief(),
            pilots.translate(up))


# --- carrier --------------------------------------------------------------------
def shift_x(x):
    """Move features that belong to a Choc seat with that seat."""
    return x - math.copysign(KEY_SHIFT, x) if abs(x) >= 13.2 else x


def rib_at(row, number, side):
    """R33 crosswise guard centres, with the outer part following the seats."""
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
        points.extend(((25.5, 9.55, 2.65), (27.45, 10.65, 4.15), (28.10, 11.8, 5.75),
                       (28.85, 12.95, 6.98), (29.05, 14.40, 7.65), (29.2, 15.4, 7.65)))
    return h33.rounded_run([(side * shift_x(x), y, z) for x, y, z in points], radius=RIB_RADIUS)


def edge_rails():
    """The outside pair of R23 runners, regrown on the narrower base."""
    source = next(beam for beam in r22.G["beams"] if beam["name"] == "R3")
    right = {**source, "plan_y_x_mm": [[y, shift_x(x)] for y, x in source["plan_y_x_mm"]]}
    left = {**source, "name": "L3", "root_y_mm": 16.,
            "plan_y_x_mm": [[16., shift_x(-28.3)], [-9., shift_x(-28.3)]]}
    return union(r.d.guard23._grow([beam])[0] for beam in (right, left))


def set_key_layout():
    """holder29.geometry's parameter edits, with this revision's seat spacing."""
    p = r22.P
    assert (p["keys"]["pitch"], p["keys"]["upper_half_spacing"], p["keys"]["row_spacing"]) == (18.7, 9.35, 17.8)
    slab = p["slab"]
    slab["lower_half_x_mm"] += KEY_X - p["keys"]["pitch"]
    slab["upper_half_x_mm"] += KEY_X - p["keys"]["upper_half_spacing"]
    p["keys"]["pitch"] = p["keys"]["upper_half_spacing"] = KEY_X
    p["keys"]["row_spacing"] += r.CLICK_SHIFT
    slab["front_y_mm"], slab["rear_y_mm"] = h28.BOTTOM_EDGE, h28.REAR
    rear_band = p["carrier_rings"]["rear_band_y_mm"]
    p["carrier_rings"]["rear_band_y_mm"] = [value + h28.REAR - r22.REAR for value in rear_band]
    p["carrier_rings"]["saddle_y_mm"][-1] = h28.REAR
    r22.REAR = h28.REAR
    r22.K["shoulder_curve"]["length_mm"] = 17.5


def saddle_cheek():
    """Carry the rod saddle past the plug opening on the side away from the wire.

    The plug sits 0.2 mm above the rod, so the saddle cannot continue under it.
    """
    y = h32.ACTUATOR_Y
    # The previous 0.4 mm margin made a knife edge at the rod contour.
    # Moving this whole cheek outward leaves room for the actual outer bead.
    inner = PCB_X - h32.MATE_HALF_X - .6
    outer = inner - 1.55
    rear, front = y + h32.MATE_Y[1] + 1.2, y + h32.MATE_Y[0] - 1.2
    # Rear-down print: widen at 45 degrees from the rear saddle.
    plan = mf.CrossSection([[(inner, rear + 1.55), (outer, rear), (outer, front), (inner, front)]])
    bottom = 1.
    cheek = mf.Manifold.extrude(plan, r22.base.slab_bottom() - bottom).translate((0., 0., bottom))
    return cheek - r22.base.corridor()


def stop_landing():
    """Raised pad for the adjustment screw head, beside the OP1 board slot."""
    y = STOP_Y + r.CLICK_SHIFT
    return box(STOP_X - 2.05, STOP_X + 2.05, y - 2.1, y + 2.1, 10.9, DECK_TOP)


def grove_pocket():
    """R36 plug pocket and R37 longer-press sweep, at the shifted Grove seat."""
    swing = union(r.world(part, angle)
                  for part in (grove.lead(1.57), grove.plug(), grove.housing())
                  for angle in np.linspace(EARLY_ANGLE, .85, 13))
    pocket = (grove.carrier_pocket() + swing).translate((GROVE_X, 0., 0.))
    # The plug still passes at the old height while the board is lowered.
    return pocket + pocket.translate((0., 0., GROVE_LIFT))


@lru_cache(maxsize=1)
def geometry():
    """Return carrier, working spaces, fixed body and the six guard ribs."""
    set_key_layout()
    bottom, rear = h28.BOTTOM_EDGE, h28.REAR
    working = {name: shape for name, shape in r22.carrier_regions().items()
               if not name.startswith("key_1_")}
    base = r22.carrier_base()
    deck = box(-DECK_HALF, DECK_HALF, bottom, rear, r22.base.slab_bottom() - .01, DECK_TOP)
    # Close the unused centre Choc bay and its clip relief.
    bay_fill = box(-7.94, 7.94, -7.28, 7.28, 8.85, 10.02)
    slot, barrels, connector, pilots = op1_reliefs()
    # R31's slicer relief at the upper-left socket follows that seat.
    socket_relief = box(-17.15 + KEY_SHIFT, -16.05 + KEY_SHIFT, 14.50, 16.35, 6.85, 7.82)
    fixed = union((base, deck, bay_fill, r.supports(), h.stop_posts(), stop_landing(),
                   op1_seats(), edge_rails(), saddle_cheek()))
    fixed -= union((slot, barrels, connector, pilots, socket_relief, grove_pocket(),
                    working["unloaded_clip_bore"]))
    fixed ^= box(-40., 40., bottom, rear, -12., 30.)
    fixed = r22.spaces16.carve(fixed, working, "r38 centred OP1")
    keepouts = union((r22.guard_keepout(), r22.slab_cutters(), barrels, connector, grove_pocket(),
                      working["key_3_socket_tape_zone"]))
    ribs = {}
    for number, row in enumerate(h33.RIB_ROWS):
        for name, sign in (("R", 1), ("L", -1)):
            ribs[f"{name}{number + 1}"] = rib_at(row, number, sign) - keepouts
    saddle_tip = box(-5., 5., 16.80, 19., 3., 9.)
    ribs["R3"] -= saddle_tip
    ribs["L3"] -= saddle_tip
    for name, sign, y in (("L2", -1, 15.6), ("L3", -1, 16.4), ("R3", 1, 16.4)):
        web = h33.rounded_run([(sign * 2.75, y + 1.6, 4.45), (sign * 3.0, y + .55, 4.85),
                               (sign * 3.42, y - .6, 5.55)], radius=.67)
        ribs[name] += web - keepouts
    # The socket clearance leaves a 0.14 mm sliver on this rail at print
    # height 19.8 mm. Remove that unprintable leading tip; the next section
    # starts on the explicitly selected removable support in plate38.py.
    tip_relief = box(-29.5, -26.8, 12.85, 13.1, 4.6, 5.3)
    # Local bead clearance in the saddle transition. The two 7.8 mm gripping
    # bands remain unchanged; this 0.8 mm axial recess is between them.
    # Without it, four outer-wall beads intruded into the unloaded rod path.
    rod_relief = mf.Manifold.cylinder(.8, 4.1, 4.1, 96).rotate((-90., 0., 0.)).translate((0., 20.05, 0.))
    fixed -= tip_relief + rod_relief
    ribs = {name: rib - tip_relief - rod_relief for name, rib in ribs.items()}
    carrier = H.base.clean(fixed + union(ribs.values()), CARRIER)
    return carrier, working, fixed, ribs


def carrier():
    return geometry()[0]


# --- bracket --------------------------------------------------------------------
def stop_stock():
    """Screw boss under the front web. Front-down print: 45 degree underside."""
    front = old.TOUCH_WEB_FRONT
    run = 18.4 - 1.2 - STOP_BOSS_BOTTOM
    return r.d.wedge(STOP_X - STOP_HALF, STOP_X + STOP_HALF, [
        (front, 17.2), (front + run, STOP_BOSS_BOTTOM), (STOP_Y + 2.2, STOP_BOSS_BOTTOM),
        (STOP_Y + 2.2, 17.1), (STOP_Y + .9, 18.4), (front, 18.4),
    ])


def stop_pilot(radius=.85):
    return cylinder(STOP_X, STOP_Y, STOP_BOSS_BOTTOM - .08, STOP_BOSS_BOTTOM + 4.25, radius)


def stop_screw(turns=START_TURNS / 2):
    """ISO 4762 M2 x 4, 3.8 mm head, 2 mm tall, 0.4 mm pitch."""
    return prior.stop_screw(turns).translate((STOP_X, STOP_Y - prior.STOP_Y, 0.))


KEEL = [(3.05, BOARD_Z - .76), (7.9, BOARD_Z - 1.35), (9.8, BOARD_Z - 3.25),
        (HOLES[1] + 1.25, BOARD_Z - 3.25), (HOLES[1] + 1.25, BOARD_Z), (3.05, BOARD_Z)]
ROOF_BOTTOM = BOARD_Z - 1.35          # underside over the lifted switch body
ROOF_X, ROOF_Y = 3.3, (-5.8, 7.75)    # bracket frame, round the switch body
PUSH_Z = r.d.PUSH_Z + OP1_LIFT
LEFT_RAIL_BOTTOM = 18.6               # stays above the cap travel through the backup stroke
LEFT_RAIL = (GROVE_X - 10., -10.55)   # outer face flush with the shifted PCB edge


@lru_cache(maxsize=1)
def bracket():
    """R36 Grove seats on the R35 bracket, shifted and raised over the centred switch."""
    gx = GROVE_X
    base = old.bracket() - box(-13., 13., -13., 16.1, BOARD_Z, 25.)
    pocket = box(gx - 8.9, gx - 3.15, BOARD_Y - 5.55, BOARD_Y + 5.55, 6., BOARD_Z + .1)
    smd = box(gx - 8.9, gx - 5.15, BOARD_Y - 9.85, BOARD_Y + 9.85, BOARD_Z - 1.55, BOARD_Z + .1)
    # The rear screw rib passes beside and over the switch body. Keep it
    # shallow there, then drop at 45 degrees to carry the rear screw boss.
    keel = r.d.wedge(gx - 1.62, gx + 1.62, KEEL)
    under_keel = r.d.wedge(gx - 3., gx + 3., [(3., 10.), (KEEL[1][0], 10.), KEEL[1], KEEL[2], (KEEL[2][0], 10.)])
    under_keel += box(gx - 3., gx + 3., 2., KEEL[1][0], 10., ROOF_BOTTOM)
    rear_boss = boss(HOLES[1]) - under_keel
    pilot_floor = box(gx - 2.35, gx + 2.35, old.TOUCH_WEB_FRONT, -7.3, 15.88 + GROVE_LIFT, 18.47 + GROVE_LIFT)
    # Join the raised front seat to the bed-side web below it.
    pilot_floor += box(gx - 2.35, gx + 2.35, old.TOUCH_WEB_FRONT, -7.3, 18.3, BOARD_Z)
    solder_floor = r.d.wedge(gx - 9.30, gx - 4.98, [
        (-10.22, 18.25), (-9.19, 17.23), (-4.76, 17.23), (-4.76, 18.49 + GROVE_LIFT), (-10.22, 18.49 + GROVE_LIFT),
    ])
    # Roof between the plunger and the Grove PCB. Its front rises at 45
    # degrees from the web for the front-down print.
    roof = r.d.wedge(-ROOF_X, ROOF_X, [(ROOF_Y[0] - .75, 19.4), (ROOF_Y[0], BOARD_Z - .05),
                                       (ROOF_Y[1], BOARD_Z - .05), (ROOF_Y[1], ROOF_BOTTOM),
                                       (ROOF_Y[0] - .75, ROOF_BOTTOM)])
    switch_relief = box(-ROOF_X, ROOF_X, ROOF_Y[0] - .75, ROOF_Y[1], 0., ROOF_BOTTOM)
    pusher = r.d.wedge(PCB_X - .75, PCB_X + .85, [
        (r.d.PUSH_Y - 1.8, ROOF_BOTTOM + .1), (r.d.PUSH_Y - .48, PUSH_Z), (r.d.PUSH_Y + .48, PUSH_Z),
        (r.d.PUSH_Y + 2., ROOF_BOTTOM + .1)])
    heel_relief = r.mirrored(box(8.50, 10.30, -12., -9.85, 12.80, 13.59))
    # The shifted socket pocket removes the old left seat rail, which is the
    # load path from the left hinge arm to the front. Carry it outside the
    # socket, under the edge of the shifted PCB.
    left_rail = box(LEFT_RAIL[0], LEFT_RAIL[1], old.TOUCH_WEB_FRONT, r.ARM_ROOT_Y, LEFT_RAIL_BOTTOM, BOARD_Z)
    shape = base + left_rail + keel + pilot_floor + solder_floor + boss(HOLES[0]) + rear_boss + stop_stock() + roof
    shape = (shape - switch_relief) + pusher
    shape = shape - pocket - smd - pilot() - stop_pilot() - heel_relief
    shape ^= box(LEFT_RAIL[0], BRACKET_HALF, old.TOUCH_WEB_FRONT, 40., 0., 28.)
    return H.base.clean(shape, BRACKET)


# --- checks ---------------------------------------------------------------------
def clip_bands():
    """The two sprung C-clip rings and the lead-in skirt between them."""
    rings = r22.P["carrier_rings"]
    (m0, m1), (r0, r1) = rings["mid_band_y_mm"], rings["rear_band_y_mm"]
    return box(-8., 8., m0 - .01, m1 + 8.3, -8., 4.4) + box(-8., 8., r0 - .01, r1 + .01, -8., 4.4)


def _max(pairs):
    return round(max(float((a ^ b).volume()) for a, b in pairs), 6)


def motion_limit(static, screw=None):
    moving = bracket() if screw is None else bracket() + screw
    low, high = EARLY_ANGLE, 1.1
    for _ in range(14):
        angle = (low + high) / 2
        if (r.world(moving, angle) ^ static).volume() > .0002:
            high = angle
        else:
            low = angle
    return low, high


def actuator_travel(angle):
    paddle = r.world(bracket(), angle)
    plunger = hardware()["plunger"]
    low, high = 0., 1.
    for _ in range(15):
        travel = (low + high) / 2
        if (paddle ^ plunger.translate((0., 0., -travel))).volume() > .00002:
            low = travel
        else:
            high = travel
    return low


def reference_guard(key, parts, bar=None):
    """Make sure the rod reference really passes under the assembly.

    A misplaced rod makes every rod clearance check pass vacuously.
    """
    bar = rod() if bar is None else bar
    def aabb(solid):
        return [round(float(v), 3) for v in solid.bounding_box()]
    rod_box, carrier_box = aabb(bar), aabb(key)
    bought = {name: aabb(solid) for name, solid in parts.items()}
    low = min([carrier_box[1]] + [b[1] for b in bought.values()])
    high = max([carrier_box[4]] + [b[4] for b in bought.values()])
    probe = box(-.5, .5, (low + high) / 2 - .5, (low + high) / 2 + .5, -.5, .5)
    hit = float((probe ^ bar).volume())
    grip = float((bar ^ key).volume())
    passed = bool(rod_box[1] <= low - 1. and rod_box[4] >= high + 1.
                  and abs(rod_box[0] + ROD_R) < 1e-3 and abs(rod_box[3] - ROD_R) < 1e-3
                  and abs(rod_box[2] + ROD_R) < 1e-3 and abs(rod_box[5] - ROD_R) < 1e-3
                  and hit > .99 and grip > 1.)
    return {"rod_aabb_mm": rod_box, "carrier_aabb_mm": carrier_box, "bought_op1_aabb_mm": bought,
            "installed_y_span_mm": [round(low, 3), round(high, 3)],
            "centred_probe_in_rod_mm3": round(hit, 4), "rod_in_clip_rings_mm3": round(grip, 4),
            "passed": passed}


def connector_report():
    """Photo-derived coupled connector against the rod at the kept height."""
    parts = hardware()
    bar = rod()
    overlap = {name: round(float((parts[name] ^ bar).volume()), 4)
               for name in ("sockets", "terminals", "housing", "plug", "op1_wire")}
    low, high = 0., 6.
    for _ in range(18):
        lift = (low + high) / 2
        if (parts["plug"].translate((0., 0., lift)) ^ bar).volume() > 1e-6:
            low = lift
        else:
            high = lift
    plug_x = parts["plug"].bounding_box()
    crown = max(math.sqrt(max(ROD_R ** 2 - x * x, 0.)) for x in np.linspace(plug_x[0], plug_x[3], 201))
    return {
        "board_underside_above_rod_centre_mm": h32.PCB_Z + OP1_LIFT,
        "board_underside_r37_mm": h32.PCB_Z, "local_op1_seat_lift_mm": OP1_LIFT,
        "photo_derived_coupled_depth_mm": h32.PLUG_DEPTH,
        "rod_top_under_plug_mm": round(crown, 4),
        "depth_available_to_rod_mm": round(h32.PCB_Z + OP1_LIFT - crown, 4),
        "plug_to_rod_clearance_mm": round(parts["plug"].bounding_box()[2] - crown, 4),
        "overlap_with_rod_mm3": overlap,
        "further_raise_needed_mm": round(high, 3),
        "basis": "The 5.9 mm coupled depth was scaled from product photos. Ethan's hands-on trial suggests "
                 "the real connector is shallower. Neither has been measured with calipers.",
        "resolved": bool(max(overlap.values()) < 1e-4),
    }


@lru_cache(maxsize=1)
def checks():
    key, working, fixed, ribs = geometry()
    paddle = bracket()
    parts = hardware()
    bar = rod()
    switches = union(working[f"key_{i}_{part}"] for i in (0, 2, 3, 4) for part in ("switch", "maximum_socket"))
    keys = switches + union(working[f"key_{i}_cap_travel"] for i in (0, 2, 3, 4))
    op1_fixed = union(parts[name] for name in ("board", "sockets", "housing", "plug", "op1_wire",
                                               "switch", "terminals", "fasteners"))
    static = key + keys + op1_fixed
    installed = static + working["unloaded_clip_bore"]
    pcb_group = board() + housing() + components() + electrode()
    touch = pcb_group + plug() + fasteners()
    moving = paddle + touch
    angles = np.linspace(-r.REST, 0., 25)
    wired_board = union(parts[name] for name in ("board", "sockets", "housing", "plug", "op1_wire"))
    mouse = union(parts[name] for name in ("switch", "terminals", "plunger"))
    clearance = {
        "op1_wired_board_drop": _max((wired_board.translate((0., 0., z)), key + switches)
                                     for z in np.linspace(0., h32.BOARD_RISE, 57)),
        "op1_prewired_lead_drop": _max((parts["op1_wire"].translate((0., 0., z)), key + keys)
                                      for z in np.linspace(0., h32.BOARD_RISE, 57)),
        "op1_seated_wire": _max([(parts["op1_wire"], key + keys)]),
        "op1_switch_install": _max((mouse.translate((0., 0., z)),
                                    key + keys + parts["board"] + parts["sockets"] + parts["fasteners"])
                                   for z in np.linspace(0., 8., 33)),
        "op1_pins_in_sockets": _max([(parts["terminals"], parts["sockets"])]),
        "op1_screw_heads_to_switch": _max([(parts["fasteners"], parts["switch"])]),
        "hinge_stroke": _max((r.world(moving, a), installed) for a in angles),
        "grove_cable_stroke": _max((r.world(lead(), a), installed + r.world(paddle, a)) for a in angles),
        "pinched_bracket_drop": _max((r.world(r.bent(paddle)).translate((0., 0., z)), installed)
                                     for z in np.linspace(0., 8., 21)),
        "bracket_arm_release": _max((r.world(r.bent(paddle, b)), installed) for b in np.linspace(0., 1., 13)),
        "preplugged_grove_board_drop": _max(
            (r.world((pcb_group + plug()).translate((0., 0., z))), installed + r.world(paddle))
            for z in np.linspace(0., SERVICE_LIFT, 25)),
        "wired_grove_board_feed": _max(
            (r.world(lead(1.45, lift=z)), installed + r.world(paddle))
            for z in np.linspace(0., SERVICE_LIFT, 25)),
        "grove_board_on_rod": _max((r.world(pcb_group + plug() + lead(), a), bar) for a in angles),
        # The 7.8 mm clip bore grips the 8 mm rod by design. Everything
        # else on the carrier stays outside the rod.
        "rod_to_carrier_outside_clip_rings": _max([(bar, key - clip_bands())]),
        "rod_to_sockets_pins_housing": _max([(bar, parts["sockets"] + parts["terminals"] + parts["housing"])]),
        "rod_to_op1_wire": _max([(bar, parts["op1_wire"])]),
    }
    # Adjustable stop: the screw head must land before any printed contact.
    limit_static = key + bar + keys + union(v for name, v in parts.items() if name != "plunger")
    settings = []
    for turns in SAMPLE_TURNS:
        screw = stop_screw(turns)
        stop, contact = motion_limit(limit_static, screw)
        travel = actuator_travel(stop)
        settings.append({
            "turns_out": float(turns), "angle_deg": round(stop, 5),
            "nominal_plunger_travel_mm": round(travel, 4),
            "stop_height_above_switch_base_mm": round(SWITCH_FREE_REFERENCE - travel, 4),
            "screw_contacts_landing_mm3": (r.world(screw, contact) ^ key).volume(),
            "plastic_before_screw_contact_mm3": (r.world(paddle, contact) ^ limit_static).volume(),
        })
    steps = np.diff([row["nominal_plunger_travel_mm"] for row in reversed(settings)])
    backup, beyond = motion_limit(limit_static)
    backup_stops = [(r.world(paddle, beyond + .01) ^ post).volume() for post in h.stop_posts().decompose()]
    sweep = np.linspace(EARLY_ANGLE, backup, 29)
    full_stroke = {
        "grove_board_and_cable": _max((r.world(touch + lead(1.45), a), installed) for a in sweep),
        "bracket": _max((r.world(paddle, a), installed) for a in sweep),
        "pinched_install_with_screw": _max(
            (r.world(r.bent(paddle) + stop_screw(turns)).translate((0., 0., z)), installed)
            for turns in (0., START_TURNS) for z in np.linspace(0., 8., 21)),
        "stop_screw_to_grove_parts": max((stop_screw(t) ^ (touch + lead())).volume() for t in SAMPLE_TURNS),
    }
    guard = h33.rib_metrics(fixed, ribs)
    fingertip = h33.fingertip_reaches(key)
    seats = [(parts["board"].translate((0., 0., -.2)) ^ key
              ^ box(PCB_X - 3.2, PCB_X + 3.2, eye + h32.ACTUATOR_Y - 2.9, eye + h32.ACTUATOR_Y + 2.9,
                    h32.PCB_Z + OP1_LIFT - .25, h32.PCB_Z + OP1_LIFT + .1)).volume() for eye in h32.EYELETS]
    bonds = {
        "grove_screw_bosses_mm3": [(paddle ^ boss(y)).volume() for y in HOLES],
        "stop_boss_mm3": (paddle ^ stop_stock()).volume(),
        "hinge_supports_mm3": (key ^ r.supports()).volume(),
        "edge_stops_mm3": [(key ^ post).volume() for post in h.stop_posts().decompose()],
        "saddle_cheek_mm3": (key ^ saddle_cheek()).volume(),
        "op1_seat_contacts_mm3": seats,
    }
    squeezed = r.bent(paddle)
    tab_box = box(2.4, h29.TAB_TIP + .5, r.AXIS_Y - .8, r.AXIS_Y + .8, h29.AXIS_Z - .8, h29.AXIS_Z + .8)
    hinge = {
        "released_tab_axial_engagement_mm": round((paddle ^ tab_box).bounding_box()[3] - h29.SUPPORT_X[0], 4),
        "squeezed_tab_clear_of_support_mm": round(h29.SUPPORT_X[0] - (squeezed ^ tab_box).bounding_box()[3], 4),
        "straight_lift_retention_contact_mm3": round(float(
            (r.world(paddle).translate((0., 0., .3)) ^ key).volume()), 5),
        "arm_bending_estimate": h29.arm_estimate(),
    }
    caps = np.asarray([working[f"key_{i}_cap_travel"].bounding_box() for i in (0, 2, 3, 4)])
    seats_xy = [list(map(float, q)) for i, q in enumerate(r22.base.key_positions()) if i != 1]
    layout = {
        "op1_board_centre_x_mm": PCB_X, "op1_board_centre_x_r37_mm": R37_PCB_X,
        "op1_board_yaw_degrees": 0., "op1_board_underside_z_mm": h32.PCB_Z + OP1_LIFT,
        "op1_seat_lift_mm": OP1_LIFT, "grove_board_shift_x_mm": GROVE_X, "grove_seat_lift_mm": GROVE_LIFT,
        "grove_electrode_centre_x_mm": round(sum(electrode().bounding_box()[0::3]) / 2, 3),
        "grove_housing_to_op1_board_gap_mm": round(
            parts["board"].bounding_box()[0] - r.world(housing(), 0.).bounding_box()[3], 4),
        "grove_board_side_to_cap_mm": round(KEY_X - h28.CHOC_HALF_X + r.world(board(), 0.).bounding_box()[0], 4),
        "plunger_to_grove_pcb_roof_mm": round(BOARD_Z - .05 - PUSH_Z, 4),
        "plunger_to_dfrobot_seat_roof_r37_mm": round(19.2 - r.d.PUSH_Z, 4),
        "choc_seat_and_rod_clip_height_change_mm": 0.,
        "hinge_axis_height_change_mm": 0.,
        "grove_touch_face_top_at_stop_mm": round(r.world(board() + electrode(), 0.).bounding_box()[5], 4),
        "grove_touch_face_top_at_stop_r37_mm": round(r.world(grove.board() + grove.electrode(), 0.).bounding_box()[5], 4),
        "grove_touch_face_top_released_mm": round(r.world(board() + electrode()).bounding_box()[5], 4),
        "choc_cap_top_mm": h28.CHOC_TOP,
        "op1_board_edge_to_grove_plug_gap_mm": round(
            parts["board"].bounding_box()[0] - r.world(plug(), 0.).bounding_box()[3], 4),
        "op1_actuator_y_mm": h32.ACTUATOR_Y,
        "choc_centres_mm": seats_xy, "choc_seat_x_r37_mm": R37_KEY_X,
        "cap_travel_span_x_mm": round(float(caps[:, 3].max() - caps[:, 0].min()), 4),
        "bracket_side_to_cap_mm": round(KEY_X - h28.CHOC_HALF_X - max(paddle.bounding_box()[3], -paddle.bounding_box()[0]), 4),
        "left_rail_section_beside_socket_mm": [round(GROVE_X - 8.9 - LEFT_RAIL[0], 3), round(BOARD_Z - LEFT_RAIL_BOTTOM, 3)],
        "bracket_side_to_cap_travel_envelope_mm": round(float(caps[:, 0][caps[:, 0] > 0].min())
                                                        - paddle.bounding_box()[3], 4),
        "pivot_world_y_mm": r.AXIS_Y + r.CLICK_SHIFT,
        "switch_lever_arm_mm": round(r.AXIS_Y - r.d.PUSH_Y, 4),
        "stop_screw_lever_arm_mm": round(r.AXIS_Y - STOP_Y, 4),
        "grove_board_front_released_y_mm": round(r.world(board()).bounding_box()[1], 4),
        "carrier_bottom_plane_y_mm": round(key.bounding_box()[1], 4),
    }
    connector = connector_report()
    guard_report = reference_guard(key, parts)
    misplaced = reference_guard(key, parts, rod().translate((0., 140., 0.)))
    guard_report["misplaced_rod_is_rejected"] = not misplaced["passed"]
    guard_report["passed"] = bool(guard_report["passed"] and not misplaced["passed"])
    cad = bool(
        max(clearance.values()) < .035 and max(full_stroke.values()) < .035
        and len(key.decompose()) == len(paddle.decompose()) == 1
        and min(bonds["grove_screw_bosses_mm3"]) > 25. and bonds["stop_boss_mm3"] > 15.
        and min(bonds["edge_stops_mm3"]) > 1. and min(seats) > .1
        and len(backup_stops) == 2 and min(backup_stops) > .0002
        and settings[0]["stop_height_above_switch_base_mm"] < 6.65
        and settings[-1]["stop_height_above_switch_base_mm"] > 7.15
        and min(steps) > 0. and max(steps) < .11
        and all(row["screw_contacts_landing_mm3"] > .00015
                and row["plastic_before_screw_contact_mm3"] < .00015 for row in settings)
        and hinge["released_tab_axial_engagement_mm"] >= .6
        and hinge["squeezed_tab_clear_of_support_mm"] > .2
        and hinge["straight_lift_retention_contact_mm3"] > .04
        and not any(fingertip.values())
        and all(part["pieces"] == 1 and min(part["rod_mount_contact_mm3"], part["edge_contact_mm3"]) > 1.
                for part in guard.values())
        and layout["op1_board_edge_to_grove_plug_gap_mm"] > .3
        and layout["grove_housing_to_op1_board_gap_mm"] > .3
        and min(layout["bracket_side_to_cap_mm"], layout["grove_board_side_to_cap_mm"]) >= .7 - 1e-9
        and guard_report["passed"]
        and abs(layout["carrier_bottom_plane_y_mm"] - h28.BOTTOM_EDGE) < .001
    )
    return {
        "layout": layout,
        "clearance_overlap_mm3": clearance,
        "full_stroke_overlap_mm3": full_stroke,
        "stop_settings": settings,
        "max_plunger_change_per_quarter_turn_mm": round(float(max(steps)), 4),
        "screw_engagement_at_start_mm": 4. - START_TURNS * PITCH,
        "backup_angle_deg": round(backup, 5),
        "backup_nominal_plunger_travel_mm": round(actuator_travel(backup), 4),
        "backup_stop_contacts_mm3": backup_stops,
        "bonds": bonds,
        "hinge": hinge,
        "ribs": guard,
        "finger_contact_probes_reaching_terminals": fingertip,
        "rod_grip_interference_in_clip_rings_mm3": round(float((bar ^ key).volume()), 4),
        "op1_connector_to_rod": connector,
        "reference_guard": guard_report,
        "cad_checks_passed": cad,
        "unresolved": [] if connector["resolved"] else [
            "An OP1 connector or wire envelope still overlaps the rod."],
        "passed": bool(cad and connector["resolved"]),
    }
