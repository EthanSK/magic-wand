"""R59 key holder: front-hung slide-on finger guards and a lengthwise battery sleeve.

Millimetres, R53 assembly frame (X < 0 is the user's left, +Y toward the upper key row, +Z up).
The holder still prints rear face down (print height = 32.65 - Y).

What is kept from R58, built by the same R58 functions: seats 1.42 mm lower, the relieved layer
under them, the upper row 1.4 mm nearer, the seam trim and the upper-left socket-end relief.
Key centres, socket directions and every switch and socket position are unchanged.

What changes
1. Finger guards
   Ethan: turn the guard supports round so they come from the bottom edge, with an outer arm on
   both sides, and leave the side toward the upper row open for reaching the sockets.
   A guard held only at the front cannot be printed as part of this holder: printing starts at the
   rear face, so the guard would be laid down before the arms that hold it. The R58 guard, its
   legs and its arms are therefore removed, and each side gets a separate guard:
     - a flat 1.8 mm shelf under the lower key, printed flat, finger side on the bed;
     - two arms at its front edge that slide onto two dovetail rails under the holder's front
       rim. The outer arm sits where the liked R58 right-hand arm was, on both sides;
     - the rails widen slightly toward the rear, so the guard wedges on by hand.
   With a guard off, the lower socket is open from every side. With it on, the socket's own
   sideways loading path still passes behind the arms and above the shelf.
2. Battery sleeve
   The Micron 72217 pouch (27 x 11.8 x 3.9 mm) lies along the rod under the upper-left key, beside
   the rod's wire lane, inside the holder's own width. The sleeve is one section extruded from
   the rear face, so every wall is fore-aft and prints straight up from the bed. The pouch goes
   in from the rear with the rod in place. It is longer than the room behind the lower key, so
   its end stands past the rear face inside a separate slip-on cap.
3. The R58 cross-wise battery tray and the R58 guard deepening are gone.

Nothing here is a claim of physical fit or strength.
"""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R58 = HERE.parent / "carbon-rod-holders-r58-smooth-click"
sys.path.insert(0, str(R58))
import carrier58 as c  # noqa: E402  (R58 seat, relief, row and seam functions; R58 files are not changed)

n, m, b, k = c.n, c.m, c.b, c.k
EXPORT = n.EXPORT if n.EXPORT != R58 / "exports" else HERE / "exports"
NEARER = 1.4
TOL = 0.01
PETG = 1.27e-3

# ---- guard rails under the front rim (right-hand X; the left is mirrored)
RAIL_X = (27.6, 14.6)                # outer rail where the R58 right arm rose; inner rail beside the seam
RAIL_Y = (-9.2, -1.5)                # front face of the bank to just in front of the switch posts
RAIL_Z = (5.0, 5.6, 6.2, 7.6)        # head bottom, head shoulder, neck start, top (inside the slab)
RAIL_NECK = 0.5                      # half widths
RAIL_HEAD = (0.95, 1.35)             # at the front end and at the rear end: the wedge

# ---- slide-on guard (right-hand X)
GUARD_X = (12.4, 30.0)
GUARD_Y = (-10.4, 8.85)              # front wall to just behind the lower socket and its tape
SHELF_Z = (-0.5, 1.3)                # the R58 rest plane, and 1.27 mm under the socket loading path
ARM_Y1 = -3.9                        # the arms stop in front of the rail's printed start ramp
ARM_TOP = 6.9
GROOVE = 1.2                         # half width of the groove round the rail head
SLOT = 0.75                          # half width of the slot round the rail neck

# ---- battery sleeve (left only)
PACK = c.PACK                        # 27.0 along, 11.8 across, 3.9 thick
ROOM = c.ROOM                        # 28.10, 12.90, 4.55
SLEEVE_X = (-22.3, -9.4)             # fitting space across; the wire lane starts at X -8.5
SLEEVE_Z = (0.65, 5.2)
SLEEVE_Y0 = 9.1                      # front end of the sleeve, behind the lower key
WALL, FLOOR, LIP = 0.8, 1.0, (1.6, 0.65)
SOCKET_WINDOW = (-16.0, 19.5)        # outboard of this X and in front of this Y the upper-left socket loads from below
STOP = 1.5                           # front stop wedge
BED_Y = c.BED_Y
ROOM_Y0 = SLEEVE_Y0 + STOP          # the fitting space starts behind the stop wedge
CAP_DEPTH = 7.55                     # cap length behind the rear face
RIDGE = (26.0, 26.8, 0.25)           # detent ridge under the sleeve floor: Y range and height
TONGUE = 0.9                         # the notch leaves 0.6 mm of it, which still prints as a wall


def hull(shapes):
    return mf.Manifold.batch_hull(list(shapes))


def rail(xc):
    z0, z1, z2, z3 = RAIL_Z
    neck = b.box(xc - RAIL_NECK, xc + RAIL_NECK, RAIL_Y[0], RAIL_Y[1], z1, z3)

    def head(y, half):
        return b.prism_xz([(xc - RAIL_NECK, z2), (xc + RAIL_NECK, z2), (xc + half, z1), (xc + half, z0), (xc - half, z0), (xc - half, z1)], y, y + 0.02)

    body = neck + hull([head(RAIL_Y[0], RAIL_HEAD[0]), head(RAIL_Y[1] - 0.02, RAIL_HEAD[1])])
    # Printed start: the rail grows from the slab at 45 degrees as the print moves forward.
    start = b.prism_yz([(RAIL_Y[1] + 0.01, 7.3), (RAIL_Y[1] + 0.01, 4.0), (RAIL_Y[1] - 3.3, 4.0)], xc - 2.5, xc + 2.5)
    return body - start


def rails():
    return b.mirrored(b.union(rail(x) for x in RAIL_X))


def arm(xc):
    y0 = GUARD_Y[0]
    block = b.box(xc - GROOVE - 1.0, xc + GROOVE + 1.0, y0, ARM_Y1, SHELF_Z[1] - 0.01, ARM_TOP)
    groove = b.prism_xz([(xc - SLOT, 7.0), (xc - SLOT, 6.35), (xc - GROOVE, 5.9), (xc - GROOVE, 4.75), (xc + GROOVE, 4.75),
                         (xc + GROOVE, 5.9), (xc + SLOT, 6.35), (xc + SLOT, 7.0)], y0 + 0.9, ARM_Y1 + 1.0)
    return block - groove


def guard(sign):
    x0, x1 = GUARD_X
    y0, y1 = GUARD_Y
    z0, z1 = SHELF_Z
    shelf = hull([b.box(x0 + 0.5, x1 - 0.5, y0 + 0.5, y1 - 0.5, z0, z0 + 0.05), b.box(x0, x1, y0, y1, z0 + 0.5, z1)])
    front = b.box(x0, x1, y0, y0 + 0.9, z1 - 0.01, 4.0)             # low stiffening wall across the front edge
    # A nose on each arm meets the front face of the holder's rim: the hard stop.
    noses = b.union(b.box(x - GROOVE - 1.0, x + GROOVE + 1.0, y0, y0 + 0.9, ARM_TOP - 0.01, 8.5) for x in RAIL_X)
    part = shelf + front + noses + b.union(arm(x) for x in RAIL_X)
    return part if sign > 0 else part.mirror((1.0, 0.0, 0.0))


def room():
    return b.box(SLEEVE_X[0], SLEEVE_X[1], ROOM_Y0, ROOM_Y0 + ROOM[0], SLEEVE_Z[0], SLEEVE_Z[1])


def pack():
    x, z = sum(SLEEVE_X) / 2, SLEEVE_Z[0]
    return b.box(x - PACK[1] / 2, x + PACK[1] / 2, ROOM_Y0 + 0.5, ROOM_Y0 + 0.5 + PACK[0], z, z + PACK[2])


def sleeve():
    x0, x1 = SLEEVE_X
    z0, z1 = SLEEVE_Z
    low, top = z0 - FLOOR, 7.6
    span = (SLEEVE_Y0, BED_Y)
    parts = [b.box(x0 - WALL, x1 + WALL, *span, low, z0),                       # floor
             b.box(x0 - WALL, x0, *span, low, top), b.box(x1, x1 + WALL, *span, low, top),   # two fore-aft walls up into the slab
             b.box(x0, x0 + LIP[0], *span, z1, z1 + LIP[1]), b.box(x1 - LIP[0], x1, *span, z1, z1 + LIP[1])]   # roof lips
    # Rounded roots: a 45 degree fillet where each wall meets the underside of the holder.
    for x, out in ((x0 - WALL, -1.0), (x1 + WALL, 1.0)):
        parts.append(b.prism_xz([(x, 7.3), (x + out * 1.2, 7.3), (x, 6.1)], *span))
    body = b.union(parts)
    # The upper-left socket loads from below through here, so nothing fixed crosses it.
    body -= b.box(x0 - 3.0, SOCKET_WINDOW[0], SLEEVE_Y0 - 0.1, SOCKET_WINDOW[1], -5, 9)
    # Front stop: a wedge that grows sideways from the inboard wall as the print rises.
    body += b.prism_xy([(x1 + 0.01, SLEEVE_Y0), (x1 - STOP, SLEEVE_Y0), (x1 + 0.01, SLEEVE_Y0 + STOP)], z0 - 0.01, z1)
    # Detent ridge for the cap, under the floor.
    y0, y1, high = RIDGE
    body += b.prism_yz([(y0, low + 0.01), (y1, low + 0.01), ((y0 + y1) / 2, low - high)], x0 - WALL, x1 + WALL)
    return body


def cap():
    """Slip-on end cap for the pouch end that stands past the rear face. Open on the inboard side for the leads."""
    x0, x1 = SLEEVE_X
    z0, z1 = SLEEVE_Z
    low = z0 - FLOOR
    rear = BED_Y + CAP_DEPTH
    out = x0 - WALL - 0.2                 # outside face of the sleeve's outboard wall, plus clearance
    under = low - 0.2                     # underside of the sleeve floor, plus clearance
    body = b.union([
        b.box(out - 1.0, x1 + 0.1, BED_Y + 0.2, rear, under - TONGUE, under),          # floor
        b.box(out - 1.0, x1 + 0.1, BED_Y + 0.2, rear, z1 + 0.2, z1 + 1.2),             # roof
        b.box(out - 1.0, out, BED_Y + 0.2, rear, under - TONGUE, z1 + 1.2),            # outboard wall
        b.box(out - 1.0, x1 - 5.0, rear - 1.0, rear, under - TONGUE, z1 + 1.2),        # rear wall, short of the lead exit
        b.box(out - 1.0, x1 + 0.1, RIDGE[0] - 1.6, BED_Y + 0.3, under - TONGUE, under),          # tongue under the sleeve floor
        b.box(out - 1.0, out, RIDGE[0] - 1.6, BED_Y + 0.3, under - TONGUE, 4.0)])                # tongue beside the outboard wall
    y0, y1, high = RIDGE
    notch = b.prism_yz([(y0 - 0.15, under + 0.01), (y1 + 0.15, under + 0.01), ((y0 + y1) / 2, under - high - 0.05)], out - 2, x1 + 1)
    return body - notch


def main(output=None):
    output = Path(output) if output else EXPORT
    output.mkdir(parents=True, exist_ok=True)
    k.old.configure_new_op1()
    q, h, r, d = k.q, k.h, k.r, k.d
    d44 = h.d
    drop, bank_x = d44.KEY_RAISE_MM, d44.OUTER_BANK_START
    slab_bottom = float(d44.r22.base.slab_bottom())
    layer = (slab_bottom - drop, slab_bottom)
    deck = float(d44.r22.base.plate_top())
    vol = k.vol
    volume = lambda shape: float(shape.volume())
    load = lambda folder, name: b.load(folder / f"{name}-assembly.stl")
    source = b.load(n.R57 / "exports/Key_Carrier-assembly.stl")
    r58 = load(R58 / "exports", "Key_Carrier")
    geometry = d44.geometry()
    working, ribs = geometry[1], b.union(list(geometry[3].values()))
    where = {name: c.placed(space, name, drop, NEARER) for name, space in working.items() if name.startswith("key_")}
    cutters = {name: c.placed(space, name, drop, NEARER) for name, space in d44.socket_print_cutters(working).items() if name.startswith("key_")}

    # --- the R58 seat work, by the R58 functions
    upper, moved = c.drop_seats(source, drop, bank_x)
    relieved, dead, footprint = c.relieve(moved, bank_x, layer)
    slab = relieved ^ c.banks(bank_x, layer[1], 60)
    plan = {side: c.web_plan(slab, sign, NEARER) for side, sign in (("right", 1.0), ("left", -1.0))}
    rowed = c.move_upper_row(relieved, bank_x, layer[1], NEARER, plan, footprint)

    # --- take the integral guard away: everything under the two bank slabs, and the inner guard legs
    under = c.banks(bank_x, -10, layer[1] - 0.02)
    blanket = b.mirrored(b.box(9.3, bank_x, -3.0, 10.0, -8, 3.4))
    legs = b.mirrored(b.box(9.3, bank_x, -3.0, 14.5, -8, 3.4)) ^ ribs
    # Room for the battery sleeve: the left inner legs and stubs beside the rod, below the deck.
    bay = b.box(SLEEVE_X[0] - WALL, SLEEVE_X[1] + WALL, SLEEVE_Y0, BED_Y + 1.0, -6, SLEEVE_Z[1] + 0.1)
    bare = rowed - under - blanket - legs - bay
    old_guard = rowed - bare
    new = rails() + sleeve()
    stage = bare + new
    carved = d44.r22.spaces16.carve(stage, cutters, "R59 key spaces")
    whole, blend = c.blend_seam(carved, bank_x, deck)
    whole, socket_relief = c.ease_socket_end(whole, where["key_3_maximum_socket"])
    pieces = sorted(whole.decompose(), key=lambda s: -s.volume())
    loose = [round(volume(p), 4) for p in pieces[1:]]
    print("pieces", len(pieces), loose[:8], flush=True)
    final = pieces[0]
    failed = []

    def gate(name, passed):
        if not passed:
            failed.append(name)

    gate("nothing is left detached", not any(v > 0.11 for v in loose) and sum(loose) < 0.6)
    attempt = output / "Key_Carrier-attempt.stl"
    mesh = b.save_closed(attempt, final)
    C = b.load(attempt)
    guards = {"Finger_Guard_Right": guard(1.0), "Finger_Guard_Left": guard(-1.0)}
    extras = {"Battery_Cap": cap(), "Battery_Pack": pack()}

    # --- every inherited key space at its R58 position, against holder, rails and sleeve
    names = sorted(where)
    entered, checked = {}, 0
    for name in names:
        amounts = [vol(C, pose) for pose in c.poses(where[name])]
        checked += len(amounts)
        if max(amounts) > TOL:
            entered[name] = round(max(amounts), 4)
    gate("key, socket and loading spaces are clear of the holder", not entered)
    fitted = d.union(where[f"key_{i}_{item}"] for i in (0, 2, 3, 4) for item in ("switch", "maximum_socket", "socket_tape_zone"))
    keys = fitted + d.union(where[f"key_{i}_cap_travel"] for i in (0, 2, 3, 4))
    rod, lane = h.base.rod(), working["external_wire_bus"]
    M = q.hardware()
    op1 = d.union(M[x] for x in ("board", "sockets", "housing", "plug", "terminals", "op1_wire", "switch", "plunger"))

    # --- what was taken away and what was added
    pocket = b.box(5.0, bank_x, 10.0, 19.0, 2.0, 7.0)
    removal = dict(old_guard_removed_mm3=round(volume(old_guard), 1), cut_from_new_rails_and_sleeve_for_key_spaces_mm3=round(volume((stage - carved) ^ new), 2),
                   op1_plug_pocket_region_changed_from_r58_mm3=round(volume((C - r58) ^ pocket) + volume((r58 - C) ^ pocket), 3),
                   middle_changed_from_r57_mm3=round(volume((C - source) ^ b.box(-5.3, 5.3, -60, 60, -60, 60)) + volume((source - C) ^ b.box(-5.3, 5.3, -60, 60, -60, 60)), 3),
                   below_the_slab_left_in_the_banks_mm3=round(volume(C ^ c.banks(bank_x, -10, layer[1] - 0.05)) - volume(new ^ c.banks(bank_x, -10, layer[1] - 0.05) ^ C), 2))
    gate("the OP1 plug pocket is untouched", removal["op1_plug_pocket_region_changed_from_r58_mm3"] < 0.05)
    gate("the middle of the holder is the R57 middle", removal["middle_changed_from_r57_mm3"] < 0.2)

    # --- click parts (R58 exports, unchanged) on this holder
    P, STOPLID, PLAIN = (load(R58 / "exports", x) for x in ("Touch_Paddle", "OP1_Lid_Stop", "OP1_Lid_Plain"))
    PIN, CLIP, BAR = (load(n.R57 / "exports", x) for x in ("Hinge_Pin", "Pin_Clip", "DFR_Post_Bar"))
    shift = (0.0, r.CLICK_SHIFT, 0.0)
    riding = P + BAR + k.moved(r.sensor() + q.gravity_pins() + r.connector(), shift) + k.moved(r.clips(), shift)
    cheeks = b.box(-12, 12, 25.2, 33, 10, 22)
    static = dict(holder_to_op1_and_switch=vol(C, op1), holder_to_paddle=vol(C, P + BAR), holder_to_pin=vol(C, PIN), holder_to_pin_clip=vol(C, CLIP),
                  holder_to_retainers=vol(C, STOPLID + PLAIN), paddle_to_keys=vol(riding, keys),
                  paddle_sweep_from_6_deg_lift_to_full_press=max(vol(m.posed(riding, a), (C - cheeks) + keys) for a in np.linspace(-6.0, 1.45, 31)),
                  holder_in_rod_and_wire_lane_more_than_r57=max(0.0, vol(C, rod + lane) - vol(source, rod + lane)))
    gate("click parts, rod and wire lane clear the holder", max(static.values()) < TOL)

    # --- the two guards
    guard_report = {}
    for name, part in guards.items():
        sign = 1.0 if name.endswith("Right") else -1.0
        eased = part.translate((0, -1.0, 0))          # 1 mm short of the wedge
        slide = max(vol(part.translate((0, -float(dy), 0)), C + fitted) for dy in np.arange(1.0, 14.1, 1.0))
        routes = max((max(vol(part, pose) for pose in c.poses(where[x])) for x in names if hasattr(where[x], "offsets")), default=0.0)
        socket = where[f"key_{0 if sign < 0 else 2}_maximum_socket"]
        sx0, sy0, sz0, sx1, sy1, _ = (float(v) for v in socket.bounding_box())
        cover = float((socket.project() ^ part.project()).area())
        guard_report[name] = dict(
            volume_mm3=round(volume(part), 1), seated_wedge_overlap_with_rails_mm3=round(vol(part, C), 4), one_mm_short_of_seated_to_holder_mm3=vol(eased, C),
            slide_on_from_the_front_14_mm_mm3=slide, to_fitted_switches_sockets_and_tape_mm3=vol(part, fitted), to_keycap_travel_mm3=vol(part, keys),
            to_every_socket_loading_pose_mm3=routes, to_rod_wire_lane_and_op1_mm3=vol(part, rod + lane + op1),
            socket_plan_area_over_the_shelf_mm2=round(cover, 1), socket_plan_area_mm2=round(float(socket.project().area()), 1),
            gap_shelf_to_socket_loading_path_mm=round(sz0 - 1.8 - 1.23 - SHELF_Z[1], 2), open_toward_the_upper_row=True)
        row = guard_report[name]
        gate(f"{name} slides on and clears every fitted part and loading path",
             max(row["one_mm_short_of_seated_to_holder_mm3"], row["slide_on_from_the_front_14_mm_mm3"], row["to_fitted_switches_sockets_and_tape_mm3"],
                 row["to_keycap_travel_mm3"], row["to_every_socket_loading_pose_mm3"], row["to_rod_wire_lane_and_op1_mm3"]) < TOL)
    both = guards["Finger_Guard_Right"] + guards["Finger_Guard_Left"]
    pitch, thick = 3.25, SHELF_Z[1] - SHELF_Z[0]
    rest = dict(r58_beam_section_modulus_mm3=1.60, r59_shelf_section_modulus_per_3_25_mm_of_width_mm3=round(pitch * thick ** 2 / 6, 2),
                shelf_thickness_mm=thick, unsupported_length_behind_the_arms_mm=round(GUARD_Y[1] - ARM_Y1, 2),
                calculated_for_10_n_at_the_rear_edge=dict(
                    deflection_mm=round(10 * (GUARD_Y[1] - ARM_Y1) ** 3 / (3 * 2000 * (GUARD_X[1] - GUARD_X[0]) * thick ** 3 / 12), 2),
                    bending_stress_mpa=round(6 * 10 * (GUARD_Y[1] - ARM_Y1) / ((GUARD_X[1] - GUARD_X[0]) * thick ** 2), 1), modulus_assumed_mpa=2000),
                rail_neck_section_per_side_mm2=round(2 * 2 * RAIL_NECK * (RAIL_Y[1] - 2.3 - RAIL_Y[0]), 1),
                left_and_right_are_mirror_images=True, strength_measured=False)

    # --- the battery
    space, pouch = room(), extras["Battery_Pack"]
    slide = max(vol(space.translate((0, float(dy), 0)), C + both) for dy in np.arange(0.0, 29.1, 1.0))
    blocked = {}
    for x in names:
        if hasattr(where[x], "offsets"):
            amount = max(vol(space, pose) for pose in c.poses(where[x]))
            if amount > TOL:
                blocked[x] = round(amount, 2)
    cap_part = extras["Battery_Cap"]
    edge = float((C ^ b.box(-60, 0, -60, 60, 8, 12)).bounding_box()[0])
    battery = dict(
        pack_mm=list(PACK), fitting_space_x_mm=list(SLEEVE_X), fitting_space_y_mm=[ROOM_Y0, round(ROOM_Y0 + ROOM[0], 2)], fitting_space_z_mm=list(SLEEVE_Z),
        fitting_space_to_holder_mm3=vol(space, C), fitting_space_to_fitted_switches_sockets_and_tape_mm3=vol(space, fitted),
        fitting_space_to_rod_wire_lane_op1_and_guards_mm3=vol(space, rod + lane + op1 + both), slide_in_from_the_rear_29_mm_mm3=slide,
        pouch_end_past_the_rear_face_mm=round(ROOM_Y0 + 0.5 + PACK[0] - BED_Y, 2), cap_end_past_the_rear_face_mm=CAP_DEPTH,
        holder_left_edge_x_mm=dict(r58_with_tray=-38.85, r59=round(float(C.bounding_box()[0]), 2), bank_edge=round(edge, 2)),
        sleeve_outer_x_mm=[round(SLEEVE_X[0] - WALL, 2), round(SLEEVE_X[1] + WALL, 2)],
        socket_loading_paths_that_need_the_battery_out_mm3=blocked,
        cap=dict(to_holder_mm3=vol(cap_part, C), to_pouch_mm3=vol(cap_part, pouch), to_rod_and_wire_lane_mm3=vol(cap_part, rod + lane),
                 detent_height_mm=RIDGE[2], tongue_strain_at_full_bend=round(1.5 * TONGUE * RIDGE[2] / (BED_Y - RIDGE[1]) ** 2, 4),
                 slides_off_rearward_mm3=max(vol(cap_part.translate((0, float(dy), 0)), C - b.box(-30, 0, RIDGE[0] - 0.3, RIDGE[1] + 0.3, -2, SLEEVE_Z[0] - FLOOR + 0.02))
                                             for dy in np.arange(0.0, 8.1, 1.0)), open_side="inboard, for the leads; the plug stays outside"),
        rod_can_stay_in=True, lead_exit_end="not confirmed on the bought pack")
    gate("the pouch space is clear when seated", max(battery["fitting_space_to_holder_mm3"], battery["fitting_space_to_fitted_switches_sockets_and_tape_mm3"],
                                                    battery["fitting_space_to_rod_wire_lane_op1_and_guards_mm3"]) < TOL)
    gate("the pouch slides in from the rear", slide < TOL)
    gate("only the upper-left socket path needs the battery out", all(x.startswith("key_3_") for x in blocked))
    gate("the cap clears holder, pouch, rod and wire lane", max(battery["cap"]["to_pouch_mm3"], battery["cap"]["to_rod_and_wire_lane_mm3"],
                                                              battery["cap"]["slides_off_rearward_mm3"]) < TOL)
    gate("the holder is no wider than its banks", battery["holder_left_edge_x_mm"]["r59"] > edge - 0.05)

    # --- seam, print proxy, mass
    seam = dict(r58_trim_removed_mm3=round(volume(blend), 4), deposited_starts_beside_the_seams=c.seam_starts(C, bank_x, deck))
    gate("nothing beside the bank seams starts in mid-air", not seam["deposited_starts_beside_the_seams"])
    hang = dict(r57=c.print_overhang(source), r58=c.print_overhang(r58), r59=c.print_overhang(C), note="counts bridges too; the native slice is the real test")
    gate("no large new unsupported start", hang["r59"]["total_mm2"] < 1.25 * hang["r57"]["total_mm2"] + 5.0)
    grams = lambda value: round(value * PETG, 2)
    mass = dict(solid_petg_g_per_cm3=1.27, note="solid CAD volume, not sliced weight", r57_holder_g=grams(volume(source)), r58_holder_with_tray_g=grams(volume(r58)),
                r59_holder_with_rails_and_sleeve_g=grams(float(mesh.volume)), r59_rails_and_sleeve_g=grams(volume(new ^ C)),
                r59_two_guards_g=grams(volume(both)), r59_cap_g=grams(volume(cap_part)), r58_guard_and_legs_removed_g=grams(volume(old_guard)))

    top_y = round(21.35 - NEARER, 3)
    result = dict(
        physical_acceptance=False, revision="R59", source_r57_sha256=k.file_hash(n.R57 / "exports/Key_Carrier-assembly.stl"),
        bounds_mm=[round(float(v), 3) for v in final.bounding_box()], change=dict(moved_down_mm=drop, upper_row_nearer_mm=NEARER, slab_cut_and_web=plan),
        key_spaces=dict(poses_checked=checked, entered_by_the_holder_mm3=entered), removal=removal, static_interference_mm3=static,
        guards=guard_report, finger_rest=rest, battery=battery, seam=seam, upper_left_socket_end_relief=socket_relief, print_overhang_proxy=hang, mass=mass,
        key_layout=dict(row_centres_y_mm=[0.0, top_y], column_centres_x_mm=[-21.0, 21.0], row_pitch_mm=top_y, keycap_envelope_gap_between_rows_mm=round(3.95 - NEARER, 3),
                        socket_turn_deg=dict(bottom_left=0, bottom_right=0, top_left=180, top_right=0), changed_from_r58=False),
        key_poses={f"key_{i}": dict(centre_xy_mm=[x, y], moved_mm=[0.0, -NEARER if i in (3, 4) else 0.0, -drop], socket_turn_deg=turn)
                   for i, x, y, turn in ((0, -21.0, 0.0, 0), (2, 21.0, 0.0, 0), (3, -21.0, top_y, 180), (4, 21.0, top_y, 0))},
        failed=failed, passes=not failed)
    print(json.dumps({key: result[key] for key in ("key_spaces", "removal", "static_interference_mm3", "guards", "finger_rest", "battery", "seam", "print_overhang_proxy", "mass", "failed")}, indent=1), flush=True)
    if failed:
        raise SystemExit("R59 key holder checks need attention: " + "; ".join(failed))
    attempt.replace(output / "Key_Carrier-assembly.stl")
    for name, part in {**guards, **extras}.items():
        b.save_closed(output / f"{name}-assembly.stl", part)
    result["sha256"] = sha256((output / "Key_Carrier-assembly.stl").read_bytes()).hexdigest()
    (output / "carrier.json").write_text(json.dumps(result, indent=2) + "\n")
    if output.resolve() != (HERE / "exports").resolve():
        (HERE / "exports").mkdir(exist_ok=True)
        for name in ("Key_Carrier", *guards, *extras):
            shutil.copy2(output / f"{name}-assembly.stl", HERE / "exports" / f"{name}-assembly.stl")
        shutil.copy2(output / "carrier.json", HERE / "exports/carrier.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
