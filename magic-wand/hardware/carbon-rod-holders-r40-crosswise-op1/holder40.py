"""R40: the OP1 click board turned 90 degrees, crosswise between the key rows.

Composes R39 (stronger hinge, rounded front edge, lower battery door) and its
R38 OP1/Grove geometry. Run assembly40.py through geometry_budget.py to check
and export; it writes nothing for printing by itself.

Frame: X across the keys, +Y towards the two-key row, +Z up from the rod centre.

Each change below follows from the requested quarter turn:

- The bought OP1 envelopes (PCB, two eyelets and screws, three socket barrels,
  white socket, plug and switch) are R39's, turned +90 degrees about the
  plunger as one rigid group. The 30 mm board now runs across the rod, centred
  on it, and the plug hangs to the left of the rod instead of over it.
- 30 mm is wider than the 27 mm between the Choc bodies, so the board sits
  between the rows. Only the two upper keys move outward, UPPER_KEY_SHIFT per
  side, so the board slot keeps a plate ring beside their openings. The three
  lower controls, Choc seat and rod-clip heights, hinge and Grove board stay.
- The board is OP1_DROP lower. Turned, the switch body passes under the rear
  Grove screw; lowering it keeps that screw tip clear through the press. The
  socket barrels still clear the rod.
- The plunger is nearer the hinge, so the pusher, rest angle, adjustable stop
  range and early-lift angle are recalculated from that shorter lever.
- The plug no longer sits over the rod, so the harness is pushed up into the
  white socket from below after the board is screwed down. Its lead leaves the
  plug end to the left and turns towards the two-key end under the deck.

OP1 board, connector and lead sizes remain photo-derived envelopes; the bought
kit is Endgame Gear EGG-SP-U1 and has no dimensioned drawing.
"""
from functools import lru_cache
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R39 = HERE.parent / 'carbon-rod-holders-r39-retention'
sys.dont_write_bytecode = True
sys.path.insert(0, str(R39))
import holder39 as r39  # noqa: E402

base = r39.previous           # holder38: canonical OP1, Grove and carrier composition
h, r, h32, h33, h28, r22 = base.h, base.r, base.h32, base.h33, base.h28, base.r22
grove, H, box, union, mf = base.grove, base.H, base.box, base.union, base.mf
BRACKET, CARRIER = base.BRACKET, base.CARRIER
BATTERY, DOOR, battery_door = r39.BATTERY, r39.DOOR, r39.battery_door

# --- layout -----------------------------------------------------------------
OP1_YAW = 90.                         # plug end to the left (-X), switch to the right
R39_PLUNGER = (base.PCB_X, h32.ACTUATOR_Y)
PLUNGER_XY = (5.95, 15.0)             # world; centres the 30 mm board on the rod (X -15..15)
OP1_DROP = 1.3                        # board underside 10.1 -> 8.8
PCB_Z = h32.PCB_Z + base.OP1_LIFT - OP1_DROP
PCB_TOP = h32.PCB_TOP + base.OP1_LIFT - OP1_DROP
UPPER_KEY_SHIFT = 3.2                 # each upper key moves outward; lower row unchanged
UPPER_KEY_X = round(base.KEY_X + UPPER_KEY_SHIFT, 3)
SHOULDER_START_Y, SHOULDER_LENGTH = 6.0, 6.0   # slab widens before the upper seats begin

# --- click geometry, from the shorter lever ---------------------------------
PUSH_Y = PLUNGER_XY[1] - r.CLICK_SHIFT        # bracket frame
LEVER = r.AXIS_Y - PUSH_Y
FREE_TOP = PCB_TOP + h32.PLUNGER_H            # nominal free plunger top
DEPRESSION = .53                              # plunger depression at the modelled angle 0
PUSH_Z = FREE_TOP - DEPRESSION
REST = math.degrees(math.asin(DEPRESSION / LEVER))   # bracket resting on the free plunger
EARLY_ANGLE = -(REST + math.degrees(.095 / LEVER))   # same 0.095 mm over-lift as R37-R39
START_TURNS = 3.25
PITCH = base.PITCH
SAMPLE_TURNS = tuple(np.linspace(0., START_TURNS, 14))
SWITCH_CLEARANCE = .3                         # bracket to switch body at the deepest press
PRESS_LIMIT = 1.0                             # degrees; beyond the backup stop contact


def crosswise(shape):
    """R39 OP1 part (board along Y) turned about its plunger into the R40 seat."""
    return (shape.translate((-R39_PLUNGER[0], -R39_PLUNGER[1], 0.)).rotate((0., 0., OP1_YAW))
            .translate((PLUNGER_XY[0], PLUNGER_XY[1], -OP1_DROP)))


def r39_frame(shape):
    """Undo crosswise(); used to prove the hardware group stayed rigid."""
    return (shape.translate((-PLUNGER_XY[0], -PLUNGER_XY[1], OP1_DROP)).rotate((0., 0., -OP1_YAW))
            .translate((R39_PLUNGER[0], R39_PLUNGER[1], 0.)))


# --- bought OP1 parts ---------------------------------------------------------
PLUG_END = (PLUNGER_XY[0] - h32.MATE_Y[1], PLUNGER_XY[1],
            (h32.PCB_Z - h32.PLUG_DEPTH + h32.MATE_TOP) / 2 + base.OP1_LIFT - OP1_DROP)
LEAD_X = -16.4                        # lead run under the deck, beside the upper-left key


def op1_cable(radius=1.3):
    """Two-wire lead from the plug end, routed to the two-key end under the deck.

    It leaves the real plug end along the board, bends 90 degrees with about
    1.5 mm radius, runs under the deck past the upper-left key, then drops
    beside the rod behind the carrier. Diameter and bend stiffness are not
    measured; this is a fit-trial envelope.
    """
    x, y, z = PLUG_END
    points = [(x + .2, y, z), (x - .8, y, z), (x - 1.4, y + .5, z), (LEAD_X, y + 1.4, z),
              (LEAD_X, y + 4., z), (LEAD_X, 29., z), (LEAD_X + .6, 33., z - .6),
              (LEAD_X + 4., 36.5, z - 2.6), (-9., 39., z - 4.2), (-7.2, 41., z - 4.6)]
    balls = [mf.Manifold.sphere(radius, 24).translate(p) for p in points]
    return union(mf.Manifold.batch_hull([a, b]) for a, b in zip(balls, balls[1:]))


R39_HARDWARE = base.hardware         # canonical straight R38/R39 OP1 envelopes


@lru_cache(maxsize=1)
def hardware():
    parts = {name: crosswise(solid) for name, solid in R39_HARDWARE().items() if name != 'op1_wire'}
    parts['op1_wire'] = op1_cable()
    return parts


def op1_seats():
    return crosswise(base.op1_seats())


def op1_reliefs():
    """Board slot, barrels, white socket and the plug's path from below, pilots."""
    y, up = h32.ACTUATOR_Y, (0., 0., base.OP1_LIFT)
    x = base.PCB_X
    slot = box(x - 5.65, x + 5.65, y + h32.PCB_Y[0] - .65, y + h32.PCB_Y[1] + .65,
               h32.PCB_Z - .02, 30.)
    barrels = h.straighten(h32.board_frame(h32.socket_local(.35, sweep=True)))
    white = box(x - h32.PLUG_HALF_X - .52, x + h32.PLUG_HALF_X + .52,
                y + h32.PLUG_Y[0] - .5, y + h32.PLUG_Y[1] + .55, h32.MATE_TOP - .35, 30.)
    # The plug is pushed up into the white socket from below; keep its whole
    # approach open (R32's underside entry).
    mate = box(x - h32.MATE_HALF_X - .45, x + h32.MATE_HALF_X + .45,
               y + h32.MATE_Y[0] - .4, y + h32.MATE_Y[1] + .4, -12., h32.MATE_TOP + .15)
    pilots = h.straighten(h32.screw_pilots(h32.PCB_Z - 3.75))
    lead = op1_cable(1.6)
    lead = union(mf.Manifold.batch_hull([a, a.translate((0., 0., -9.))]) for a in [lead])
    pilots = crosswise(pilots.translate(up))
    roofs = []
    for bore in pilots.decompose():
        x0,y0,z0,x1,y1,z1 = bore.bounding_box()
        cx,cy,radius = (x0+x1)/2,(y0+y1)/2,(x1-x0)/2
        # The screw axis lies sideways on the print bed. A 45-degree point
        # towards -Y (print-up) keeps the round pilot core open without making
        # the thread pilot wider or bridging a flat roof across it.
        section=mf.CrossSection([[(cx-radius,cy),(cx,cy-radius*math.sqrt(2)),(cx+radius,cy)]])
        roofs.append(mf.Manifold.extrude(section,z1-z0).translate((0.,0.,z0)))
    return (crosswise(slot.translate(up)), crosswise(barrels.translate(up)),
            crosswise((white + mate).translate(up)) + lead, pilots + union(roofs))


# --- carrier --------------------------------------------------------------------
def set_key_layout():
    """R38's seat spacing, then the two upper keys outward and a wider upper slab."""
    base.set_key_layout()
    p = r22.P
    p['keys']['upper_half_spacing'] += UPPER_KEY_SHIFT
    p['slab']['upper_half_x_mm'] += UPPER_KEY_SHIFT
    p['slab']['lower_rear_y_mm'] = SHOULDER_START_Y
    r22.K['shoulder_curve']['length_mm'] = SHOULDER_LENGTH


def upper_left_socket_relief():
    """R31's slicer relief at the upper-left socket, moved with that seat."""
    dx = base.KEY_SHIFT - UPPER_KEY_SHIFT
    return box(-17.15 + dx, -16.05 + dx, 14.50, 16.35, 6.85, 7.82)


def guard_rib(row, number, side):
    """Keep the rounded R38 guards, taking their inner roots in front of the
    crosswise socket barrels. A cut through a tube is not a load path: move
    its inner run first, then subtract the actual component spaces."""
    shape = base.rib_at(row, number, side)
    shift = 14.8 + .8 * number - 12.1
    def forward(points):
        moved = points.copy()
        moved[:, 1] -= shift * np.clip((10.5 - abs(points[:, 0])) / 6.8, 0., 1.)
        return moved
    shape = shape.warp_batch(forward)
    return shape


@lru_cache(maxsize=1)
def carrier_parts():
    """holder38.geometry with the crosswise OP1 mount and the wider upper row.

    R38's straight-board slot, over-rod plug opening and wired-drop relief are
    not carried over; the deck they cut is restored.
    """
    set_key_layout()
    bottom, rear = h28.BOTTOM_EDGE, h28.REAR
    working = {name: shape for name, shape in r22.carrier_regions().items()
               if not name.startswith('key_1_')}
    body = r22.carrier_base()
    deck = box(-base.DECK_HALF, base.DECK_HALF, bottom, rear, r22.base.slab_bottom() - .01, base.DECK_TOP)
    bay_fill = box(-7.94, 7.94, -7.28, 7.28, 8.85, 10.02)
    slot, barrels, connector, pilots = op1_reliefs()
    fixed = union((body, deck, bay_fill, r.supports(), h.stop_posts(), base.stop_landing(),
                   op1_seats(), base.edge_rails(), base.saddle_cheek()))
    fixed -= union((slot, barrels, connector, pilots, upper_left_socket_relief(), base.grove_pocket(),
                    working['unloaded_clip_bore']))
    fixed ^= box(-40., 40., bottom, rear, -12., 30.)
    fixed = r22.spaces16.carve(fixed, working, 'r40 crosswise OP1')
    keepouts = union((r22.guard_keepout(), r22.slab_cutters(), barrels, connector, base.grove_pocket(),
                      working['key_3_socket_tape_zone']))
    ribs = {}
    for number, row in enumerate(h33.RIB_ROWS):
        for name, sign in (('R', 1), ('L', -1)):
            ribs[f'{name}{number + 1}'] = guard_rib(row, number, sign) - keepouts
    saddle_tip = box(-5., 5., 16.80, 19., 3., 9.)
    ribs['R3'] -= saddle_tip
    ribs['L3'] -= saddle_tip
    tip_relief = box(-29.5, -26.8, 12.85, 13.1, 4.6, 5.3)
    rod_relief = mf.Manifold.cylinder(.8, 4.1, 4.1, 96).rotate((-90., 0., 0.)).translate((0., 20.05, 0.))
    # The widened upper slab has a tiny new contact with the rod outside the
    # two friction rings. Clear it without changing those intended grips.
    outside_rod = base.rod() - base.clip_bands()
    fixed -= tip_relief + rod_relief + outside_rod
    ribs = {name: rib - tip_relief - rod_relief - outside_rod for name, rib in ribs.items()}
    # The three left guards share this terminal junction. Give it a short
    # 45-degree web below the Choc seat rather than relying on the small
    # round tip's underfilled interior. Carve the actual working spaces last.
    web = r.d.wedge(-31., -27., [(13.4,7.65),(15.5,7.65),(15.5,6.95),(13.55,5.)])
    web = r22.spaces16.carve(web, working, 'R40 left guard web')
    existing = fixed + union(ribs.values())
    web = union(piece for piece in web.decompose() if (piece ^ existing).volume() > .1)
    assert len(web.decompose()) == 1 and (web ^ fixed).volume() > 1.
    # Preserve both real attachment interfaces before unioning the web into
    # the carrier. Intersecting two already-unioned groups would count the
    # entire web as its own bond and miss a weak beam-to-web connection.
    joints = {'left guard web-to-frame bond':web ^ fixed,
              **{f'{name} guard-to-web bond':web ^ rib for name,rib in ribs.items() if name.startswith('L')}}
    fixed = fixed + web
    ribs = {name: rib + web if name.startswith('L') else rib for name,rib in ribs.items()}
    carrier = H.base.clean(fixed + union(ribs.values()), CARRIER)
    return carrier, working, fixed, ribs, web, joints


@lru_cache(maxsize=1)
def base_geometry():
    return carrier_parts()[:4]


def guard_web_interfaces():
    parts = carrier_parts()
    return {'left guard reinforcement web':parts[4], **parts[5]}


def geometry():
    return r39.geometry()


def carrier():
    return geometry()[0]


# --- bracket ----------------------------------------------------------------------
def inverse_placement(angle):
    m = np.eye(4)
    m[:3] = r.placement(angle)
    return np.linalg.inv(m)[:3]


@lru_cache(maxsize=1)
def switch_relief():
    """Bracket-frame room swept by the turned switch body from early lift to beyond the backup stop."""
    x0, y0, z0, x1, y1, z1 = hardware()['switch'].bounding_box()
    c = SWITCH_CLEARANCE
    grown = box(x0 - c, x1 + c, y0 - c, y1 + c, 0., z1 + c)
    return mf.Manifold.batch_hull([grown.transform(inverse_placement(a).tolist())
                                   for a in np.linspace(EARLY_ANGLE, PRESS_LIMIT, 7)])


PUSHER_X = (PLUNGER_XY[0] - .55, PLUNGER_XY[0] + .55)   # inside the plunger's 1.2 mm width
PUSHER_RISE = 1.2


def pusher():
    """Short pad hanging from the right root brace, which already crosses over
    the turned plunger. No new beam or axle. Its flanks rise at 45 degrees for
    the front-down print; only the pad reaches below the switch clearance, and
    only over the plunger."""
    top = PUSH_Z + PUSHER_RISE
    run = .48 + PUSHER_RISE
    shape = r.d.wedge(*PUSHER_X, [(PUSH_Y - run, top), (PUSH_Y - .48, PUSH_Z),
                                 (PUSH_Y + .48, PUSH_Z), (PUSH_Y + run, top)])
    # Remove the knife-edge ends that the 0.4 mm nozzle omitted. The contact
    # face and 45-degree flanks stay; each end now starts with 0.7 mm of stock.
    return shape ^ box(*PUSHER_X, PUSH_Y-run+.7, PUSH_Y+run-.7, PUSH_Z, top)


def old_pusher_space():
    """The R38/R39 pusher and the empty room beneath R38's switch roof."""
    return box(-base.ROOF_X, base.ROOF_X, base.ROOF_Y[0] - .75, base.ROOF_Y[1], 0., base.ROOF_BOTTOM)


@lru_cache(maxsize=1)
def bracket():
    shape = r39.bracket() - old_pusher_space()
    shape = (shape - switch_relief()) + pusher()
    return H.base.clean(shape, BRACKET)


def install():
    """Point the shared R38/R39 functions at this revision before any solid is built.

    R39's repaired arms and bend come first; then the R40 carrier base, bracket,
    OP1 hardware and the rest angle of the shorter lever.
    """
    r39.install_checks()
    r39.BASE_GEOMETRY = base_geometry
    base.geometry = r39.geometry
    base.bracket = bracket
    base.hardware = hardware
    r.REST = REST
    base.EARLY_ANGLE = EARLY_ANGLE


assert base.geometry.cache_info().currsize == 0 and R39_HARDWARE.cache_info().currsize == 0
install()


def __getattr__(name):
    """Unchanged interfaces stay owned by the R39/R38 composition."""
    return getattr(r39, name)


# --- checks -------------------------------------------------------------------
def _max(pairs):
    return base._max(pairs)


def _gap(a, b, search=3.):
    return round(float(a.min_gap(b, search)), 4)


def r39_carrier():
    """R39's exported carrier, for the invariant key-aperture comparison."""
    return BATTERY.read(R39 / 'exports' / f'{CARRIER}-assembly.stl')


def key_apertures(key):
    """Each Choc seat neighbourhood against R39's, after undoing the upper-row move."""
    old = r39_carrier()
    rows = {}
    for i, (x, y) in enumerate(r22.base.key_positions()):
        if i == 1:
            continue
        dx = math.copysign(UPPER_KEY_SHIFT, x) if y else 0.
        # Compare the complete 14.1 mm opening and its 0.65 mm seat land.
        # The old 17 mm square also included the deliberately reshaped outer
        # shoulder; that is not an invariant bought-switch interface.
        region = box(x - dx - 7.7, x - dx + 7.7, y - 7.7, y + 7.7, 7.7, 12.0)
        new = key.translate((-dx, 0., 0.)) ^ region
        was = old ^ region
        rows[f'key_{i}'] = {'centre_mm': [round(x, 3), round(y, 3)], 'moved_x_mm': round(dx, 3),
                            'difference_mm3': round(float((new - was).volume() + (was - new).volume()), 4),
                            'seat_volume_mm3': round(float(new.volume()), 3)}
    return rows


def slot_rings(key):
    """Plastic left between the board slot and each upper Choc opening."""
    slot = op1_reliefs()[0]
    sx = slot.bounding_box()[3]
    plate = r22.P['keys']['opening'] / 2
    relief = r22.P['bay']['clip_relief_half_x_mm']
    return {'plate_ring_mm': round(UPPER_KEY_X - plate - sx, 3),
            'under_plate_wall_mm': round(UPPER_KEY_X - relief - sx, 3)}


def press_travel(angle_from, angle_to):
    """Vertical travel of the Grove board's front edge and electrode centre."""
    point = np.array([*electrode_centre(), 1.])
    front = np.array([0., grove.BOARD_Y - 10. - .8, base.BOARD_Z + 1.6, 1.])
    out = {}
    for name, p in (('electrode_centre', point), ('board_front_edge', front)):
        a = r.placement(angle_from) @ p
        b = r.placement(angle_to) @ p
        out[name] = round(float(a[2] - b[2]), 4)
    return out


def electrode_centre():
    x0, y0, _, x1, y1, z1 = base.electrode().bounding_box()
    return (x0 + x1) / 2, (y0 + y1) / 2, z1


def plunger_travel(angle):
    return base.actuator_travel(angle)


@lru_cache(maxsize=1)
def checks():
    key, working, fixed, ribs = geometry()
    paddle = bracket()
    parts = hardware()
    bar = base.rod()
    switches = union(working[f'key_{i}_{part}'] for i in (0, 2, 3, 4) for part in ('switch', 'maximum_socket'))
    keys = switches + union(working[f'key_{i}_cap_travel'] for i in (0, 2, 3, 4))
    op1_fixed = union(parts[n] for n in ('board', 'sockets', 'housing', 'plug', 'op1_wire', 'switch', 'terminals', 'fasteners'))
    static = key + keys + op1_fixed
    installed = static + working['unloaded_clip_bore']
    pcb_group = base.board() + base.housing() + base.components() + base.electrode()
    touch = pcb_group + base.plug() + base.fasteners()
    moving = paddle + touch
    angles = np.linspace(-REST, 0., 25)
    board_group = union(parts[n] for n in ('board', 'sockets', 'housing'))
    harness = parts['plug'] + parts['op1_wire']
    mouse = union(parts[n] for n in ('switch', 'terminals', 'plunger'))
    clearance = {
        'choc_switches_and_sockets_to_carrier': _max([(switches, key)]),
        'op1_board_drop': _max((board_group.translate((0., 0., z)), key + switches)
                               for z in np.linspace(0., h32.BOARD_RISE, 57)),
        'op1_plug_from_below': _max((harness.translate((0., 0., z)),
                                     key + keys + bar + board_group + parts['fasteners'])
                                    for z in np.linspace(-9., 0., 37)),
        'op1_seated_lead': _max([(parts['op1_wire'], key + keys + bar)]),
        'op1_switch_install': _max((mouse.translate((0., 0., z)),
                                    key + keys + parts['board'] + parts['sockets'] + parts['fasteners'])
                                   for z in np.linspace(0., 8., 33)),
        'op1_pins_in_sockets': _max([(parts['terminals'], parts['sockets'])]),
        'op1_screw_heads_to_switch': _max([(parts['fasteners'], parts['switch'])]),
        'hinge_stroke': _max((r.world(moving, a), installed) for a in angles),
        'grove_cable_stroke': _max((r.world(base.lead(), a), installed + r.world(paddle, a)) for a in angles),
        'pinched_bracket_drop': _max((r.world(r.bent(paddle)).translate((0., 0., z)), installed)
                                     for z in np.linspace(0., 8., 21)),
        'bracket_arm_release': _max((r.world(r.bent(paddle, b)), installed) for b in np.linspace(0., 1., 13)),
        'preplugged_grove_board_drop': _max(
            (r.world((pcb_group + base.plug()).translate((0., 0., z))), installed + r.world(paddle))
            for z in np.linspace(0., base.SERVICE_LIFT, 25)),
        'wired_grove_board_feed': _max(
            (r.world(base.lead(1.45, lift=z)), installed + r.world(paddle))
            for z in np.linspace(0., base.SERVICE_LIFT, 25)),
        'grove_board_on_rod': _max((r.world(pcb_group + base.plug() + base.lead(), a), bar) for a in angles),
        'rod_to_carrier_outside_clip_rings': _max([(bar, key - base.clip_bands())]),
        'rod_to_sockets_pins_housing': _max([(bar, parts['sockets'] + parts['terminals'] + parts['housing'] + parts['plug'])]),
        'rod_to_op1_wire': _max([(bar, parts['op1_wire'])]),
    }
    limit_static = key + bar + keys + union(v for n, v in parts.items() if n != 'plunger')
    settings = []
    for turns in SAMPLE_TURNS:
        screw = base.stop_screw(turns)
        stop, contact = base.motion_limit(limit_static, screw)
        travel = plunger_travel(stop)
        settings.append({
            'turns_out': round(float(turns), 4), 'angle_deg': round(stop, 5),
            'nominal_plunger_travel_mm': round(travel, 4),
            'stop_height_above_switch_base_mm': round(base.SWITCH_FREE_REFERENCE - travel, 4),
            'screw_contacts_landing_mm3': (r.world(screw, contact) ^ key).volume(),
            'plastic_before_screw_contact_mm3': (r.world(paddle, contact) ^ limit_static).volume(),
        })
    steps = np.diff([row['nominal_plunger_travel_mm'] for row in reversed(settings)])
    backup, beyond = base.motion_limit(limit_static)
    backup_stops = [(r.world(paddle, beyond + .01) ^ post).volume() for post in h.stop_posts().decompose()]
    sweep = np.linspace(EARLY_ANGLE, backup, 29)
    full_stroke = {
        'grove_board_and_cable': _max((r.world(touch + base.lead(1.45), a), installed) for a in sweep),
        'bracket': _max((r.world(paddle, a), installed) for a in sweep),
        # The free plunger deliberately intersects its pusher during a click;
        # its depression is checked separately by actuator_travel(). The fixed
        # switch housing, however, must never touch any of the bracket.
        'bracket_to_switch_body': _max((r.world(paddle, a), parts['switch']) for a in sweep),
        'pinched_install_with_screw': _max(
            (r.world(r.bent(paddle) + base.stop_screw(turns)).translate((0., 0., z)), installed)
            for turns in (0., START_TURNS) for z in np.linspace(0., 8., 21)),
        'stop_screw_to_grove_parts': max((base.stop_screw(t) ^ (touch + base.lead())).volume() for t in SAMPLE_TURNS),
    }
    switch_gap_at_backup = _gap(r.world(paddle - box(*PUSHER_X, PUSH_Y - 2., PUSH_Y + 2., 0., PUSH_Z + .3), backup),
                                parts['switch'])
    guard = h33.rib_metrics(fixed, ribs)
    fingertip = h33.fingertip_reaches(key)
    seats = []
    for eye in h32.EYELETS:
        zone = box(base.PCB_X - 3.2, base.PCB_X + 3.2, eye + h32.ACTUATOR_Y - 2.9, eye + h32.ACTUATOR_Y + 2.9,
                   h32.PCB_Z + base.OP1_LIFT - .25, h32.PCB_Z + base.OP1_LIFT + .1)
        seats.append((parts['board'].translate((0., 0., -.2)) ^ key ^ crosswise(zone)).volume())
    r39_bracket = r39.bracket() - old_pusher_space() - switch_relief()
    root_region = box(-8.7, 8.7, r.ARM_ROOT_Y - 3.2, r.ARM_ROOT_Y + 2., 16., 20.)
    bonds = {
        'grove_screw_bosses_mm3': [(paddle ^ base.boss(y)).volume() for y in base.HOLES],
        'stop_boss_mm3': (paddle ^ base.stop_stock()).volume(),
        'pusher_to_existing_brace_mm3': round(float((pusher() ^ r39_bracket).volume()), 4),
        'hinge_supports_mm3': (key ^ r.supports()).volume(),
        'edge_stops_mm3': [(key ^ post).volume() for post in h.stop_posts().decompose()],
        'op1_seat_contacts_mm3': seats,
        'root_fan_removed_by_switch_relief_mm3': round(float(((r39.bracket() - paddle) ^ root_region).volume()), 4),
    }
    squeezed = r.bent(paddle)
    tab_box = box(2.4, r.h29.TAB_TIP + .5, r.AXIS_Y - .8, r.AXIS_Y + .8, r.h29.AXIS_Z - .8, r.h29.AXIS_Z + .8)
    arm = r.h29.arm_estimate()
    free_length = arm['root_to_tab_mm'] - 1.5
    arm['nominal_unfilleted_strain_percent_estimate'] = arm['root_strain_percent_estimate']
    arm['conservative_free_length_mm'] = round(free_length, 3)
    arm['root_strain_percent_estimate'] = round(arm['root_strain_percent_estimate'] * (arm['root_to_tab_mm'] / free_length) ** 2, 2)
    arm['physical_strength_verified'] = False
    hinge = {
        'released_tab_axial_engagement_mm': round((paddle ^ tab_box).bounding_box()[3] - r.h29.SUPPORT_X[0], 4),
        'squeezed_tab_clear_of_support_mm': round(r.h29.SUPPORT_X[0] - (squeezed ^ tab_box).bounding_box()[3], 4),
        'straight_lift_retention_contact_mm3': round(float((r.world(paddle).translate((0., 0., .3)) ^ key).volume()), 5),
        'arm_bending_estimate': arm,
    }
    middle = settings[len(settings) // 2]
    caps = np.asarray([working[f'key_{i}_cap_travel'].bounding_box() for i in (0, 2, 3, 4)])
    seats_xy = [[round(float(v), 3) for v in q] for i, q in enumerate(r22.base.key_positions()) if i != 1]
    stroke_parts = r.world(touch + base.lead(), backup)
    layout = {
        'op1_board_yaw_degrees': OP1_YAW, 'op1_plunger_xy_mm': list(PLUNGER_XY),
        'op1_plunger_xy_r39_mm': [base.PCB_X, h32.ACTUATOR_Y],
        'op1_board_bounds_mm': [round(v, 3) for v in parts['board'].bounding_box()],
        'op1_board_underside_z_mm': round(PCB_Z, 3), 'op1_board_underside_z_r39_mm': h32.PCB_Z + base.OP1_LIFT,
        'upper_key_shift_each_side_mm': UPPER_KEY_SHIFT, 'lower_key_shift_mm': 0.,
        'choc_centres_mm': seats_xy, 'upper_slab_half_width_mm': r22.P['slab']['upper_half_x_mm'],
        'slot_to_upper_key_openings_mm': slot_rings(key),
        'cap_travel_span_x_mm': round(float(caps[:, 3].max() - caps[:, 0].min()), 4),
        'lower_cap_travel_span_x_mm': round(float(caps[:2, 3].max() - caps[:2, 0].min()), 4),
        'switch_lever_arm_mm': round(LEVER, 4), 'switch_lever_arm_r39_mm': round(r.AXIS_Y - r.d.PUSH_Y, 4),
        'rest_angle_deg': round(REST, 4), 'rest_angle_r39_deg': round(math.degrees(math.asin(r.d.DEPRESSION / (r.AXIS_Y - r.d.PUSH_Y))), 4),
        'early_lift_angle_deg': round(EARLY_ANGLE, 4),
        'press_travel_rest_to_middle_stop_mm': press_travel(-REST, middle['angle_deg']),
        'press_travel_rest_to_backup_mm': press_travel(-REST, backup),
        'grove_touch_face_top_released_mm': round(r.world(base.board() + base.electrode()).bounding_box()[5], 4),
        'grove_touch_face_top_at_backup_mm': round(r.world(base.board() + base.electrode(), backup).bounding_box()[5], 4),
        'choc_cap_top_mm': h28.CHOC_TOP,
        'grove_plug_to_op1_board_at_backup_mm': _gap(r.world(base.plug(), backup), parts['board']),
        'grove_parts_to_op1_at_backup_mm': _gap(stroke_parts, op1_fixed),
        'rear_grove_screw_to_switch_at_backup_mm': _gap(r.world(base.fastener(base.HOLES[1]), backup), parts['switch']),
        'bracket_to_switch_body_at_backup_mm': switch_gap_at_backup,
        'op1_sockets_to_rod_mm': round(parts['sockets'].bounding_box()[2] - base.ROD_R, 4),
        'op1_plug_to_rod_mm': _gap(parts['plug'], bar),
        'op1_lead_to_rod_mm': _gap(parts['op1_wire'], bar),
        'op1_lead_to_carrier_mm': _gap(parts['op1_wire'], key),
        'op1_lead_to_upper_left_socket_mm': _gap(parts['op1_wire'], working['key_3_maximum_socket']),
        'pusher_contact_y_mm': round(PUSH_Y + r.CLICK_SHIFT, 4), 'pusher_bottom_z_mm': round(PUSH_Z, 4),
        'free_plunger_top_z_mm': round(FREE_TOP, 4), 'depression_at_modelled_angle_mm': DEPRESSION,
        'bracket_side_to_cap_travel_envelope_mm': round(float(caps[:, 0][caps[:, 0] > 0].min()) - paddle.bounding_box()[3], 4),
        'carrier_bottom_plane_y_mm': round(key.bounding_box()[1], 4),
        'carrier_width_mm': round(key.bounding_box()[3] - key.bounding_box()[0], 4),
        'choc_seat_and_rod_clip_height_change_mm': 0., 'hinge_axis_height_change_mm': 0.,
    }
    guard_report = base.reference_guard(key, parts)
    misplaced = base.reference_guard(key, parts, base.rod().translate((0., 140., 0.)))
    guard_report['misplaced_rod_is_rejected'] = not misplaced['passed']
    guard_report['passed'] = bool(guard_report['passed'] and not misplaced['passed'])
    apertures = key_apertures(key)
    rigid = max(float((r39_frame(parts[n]) - R39_HARDWARE()[n]).volume() + (R39_HARDWARE()[n] - r39_frame(parts[n])).volume())
                for n in parts if n != 'op1_wire')
    cad = bool(
        max(clearance.values()) < .035 and max(full_stroke.values()) < .035
        and len(key.decompose()) == len(paddle.decompose()) == 1
        and min(bonds['grove_screw_bosses_mm3']) > 25. and bonds['stop_boss_mm3'] > 15.
        and bonds['pusher_to_existing_brace_mm3'] > 1.
        and min(bonds['edge_stops_mm3']) > 1. and min(seats) > .1
        and len(backup_stops) == 2 and min(backup_stops) > .0002
        and settings[0]['stop_height_above_switch_base_mm'] < 6.65
        and settings[-1]['stop_height_above_switch_base_mm'] > 7.15
        and min(steps) > 0. and max(steps) < .11
        and all(row['screw_contacts_landing_mm3'] > .00015
                and row['plastic_before_screw_contact_mm3'] < .00015 for row in settings)
        and hinge['released_tab_axial_engagement_mm'] >= .6
        and hinge['squeezed_tab_clear_of_support_mm'] > .2
        and hinge['straight_lift_retention_contact_mm3'] > .04
        and not any(fingertip.values())
        and all(part['pieces'] == 1 and min(part['rod_mount_contact_mm3'], part['edge_contact_mm3']) > 1.
                for part in guard.values())
        and min(layout['slot_to_upper_key_openings_mm'].values()) >= .7
        and layout['op1_sockets_to_rod_mm'] >= .45
        and layout['grove_plug_to_op1_board_at_backup_mm'] > .3
        and layout['bracket_to_switch_body_at_backup_mm'] > .2
        and layout['rear_grove_screw_to_switch_at_backup_mm'] > .2
        and max(row['difference_mm3'] for row in apertures.values()) < .05
        and rigid < 1e-3
        and guard_report['passed']
        and abs(layout['carrier_bottom_plane_y_mm'] - h28.BOTTOM_EDGE) < .001
    )
    return {
        'layout': layout,
        'clearance_overlap_mm3': clearance,
        'full_stroke_overlap_mm3': full_stroke,
        'stop_settings': settings,
        'max_plunger_change_per_step_mm': round(float(max(steps)), 4),
        'screw_engagement_at_start_mm': round(4. - START_TURNS * PITCH, 3),
        'backup_angle_deg': round(backup, 5),
        'backup_nominal_plunger_travel_mm': round(plunger_travel(backup), 4),
        'backup_stop_contacts_mm3': backup_stops,
        'bonds': bonds,
        'hinge': hinge,
        'ribs': guard,
        'key_apertures_vs_r39': apertures,
        'op1_group_rigid_turn_error_mm3': round(rigid, 6),
        'finger_contact_probes_reaching_terminals': fingertip,
        'rod_grip_interference_in_clip_rings_mm3': round(float((bar ^ key).volume()), 4),
        'reference_guard': guard_report,
        'basis': ('OP1 board, socket, plug and lead envelopes are photo-derived (Endgame Gear EGG-SP-U1); '
                  'the 7.35 mm free and 6.7-7.1 mm operating heights are the reference switch. '
                  'Stop and travel values are nominal CAD, not measured force, feel or fatigue.'),
        'cad_checks_passed': cad,
        'passed': cad,
    }
