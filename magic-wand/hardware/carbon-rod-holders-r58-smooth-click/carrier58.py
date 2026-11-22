"""R58 key holder: lowered key seats, deeper finger-rest beams, less dead material and an
integral battery tray. Millimetres, R53 assembly frame (X < 0 is the user's left).

1. Flush key seats
   R43 raised the four outer Choc seats and R44 settled them 1.42 mm above the centre deck. R53
   then lowered the touch board, which left the keycaps standing above it. Ethan: "get rid of that
   little elevated thing where the actual keys go".
   Everything in the two key banks (|X| > 12.7) above Z 6.4 moves down 1.42 mm as one rigid piece:
   seat plate, clip pockets, backplate and every print fix made to them since R45. The holder
   prints rear face down, so this is a shift inside each print layer.

2. Less dead material
   The move leaves the old frame's bottom 1.42 mm hanging under the seats (Z 5.85 to 7.27). The
   R42-height design never had it. It is removed, except in rounded columns over every guard leg
   and rest member that comes up from below.

3. Deeper finger-rest beams
   The rounded beams under the keys were 1.9 mm round. Every guard and rest member under the banks
   is extended 0.8 mm downward, so each beam becomes a 1.9 x 2.7 mm rounded section and its legs
   and joints deepen with it. Nothing grows upward or sideways, so no socket path narrows.

4. The socket, tape and loading spaces are cut again 1.42 mm lower with the same printed clearance.

5. Battery tray under the upper-left key
   For the Micron 72217 pouch, 27 x 11.8 x 3.9 mm, lying across the holder behind the upper-left
   socket. It slides in from the left. A sprung finger cut from the rear wall hooks behind the
   pouch end. Nothing squeezes the pouch. Every face is a vertical wall or a 45 degree slope in
   the rear-down print.

6. Socket backers (two loose tools, not part of the holder)
   Straight up between the rest beams is mostly blocked, so each tool is a flat tongue that
   follows a lower socket's own sideways loading path and sits under the seated socket while its
   switch is pushed in from above.

7. Upper row nearer the lower row
   The upper keys' part of each seat slab moves toward the lower row by the largest of 1.4, 1.2
   or 1.0 mm that passes every check. Only the slab above the relieved layer moves. Every guard
   and rest member, and the slab directly over it, stays in place, and the rear rim is extended
   forward behind the moved block. If no move passes, the unshifted holder is built.

Not changed here: socket directions. Nothing is a claim of physical fit or strength.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

import build58 as n

m, b = n.m, n.b
import checks53 as k  # noqa: E402

SPLIT_Z = 6.4            # below every seated socket and its tape; above the round guard ribs
PRESS_TRAVEL = 3.0       # Kailh Choc v1 full travel
TOL = 0.01
PETG = 1.27e-3           # g per mm3, solid

# ---- finger rest
REST_ROWS = (0.2, 3.45, 6.7, 9.95)   # beam centre lines along Y; centre height 1.25, radius 0.95
REST_Z, REST_R = 1.25, 0.95
DEEPER = 0.8                         # every guard member grows this far downward
GUARD_TOP = 4.6
WITNESS_X = 13.2                     # the R57 finger_rest view point [13.2, 3.45, 1.25] and its mirror
KEEP = 0.6                           # the dead layer stays within this distance of a member below it

# ---- battery tray
PACK = (27.0, 11.8, 3.9)             # Micron 72217: along X, along Y, thickness
ROOM = (28.10, 12.90, 4.55)          # fitting space kept for it
END_X = -9.5                         # inboard end of the fitting space; the wire lane starts at X -8.5
REAR_Y = 31.65                       # inner face of the rear wall; the print bed face is Y 32.65
FLOOR_Z = 0.65                       # top of the shelf
SHELF = 1.2
WALL = 0.8
SOCKET_PATH = (-15.9, -31.9, 20.6)   # the shelf stays behind Y 20.6 between these X stations
RAMP = 1.2                           # front ramp height and length
HOOK = 1.2                           # latch hook reach into the pouch space
LEAF = (-26.5, 1.6, 4.3)             # latch finger root X, and its Z band
TRAY_TOP = 7.5                       # rear wall and roof rib reach the live backplate
ROOM_X = (END_X - ROOM[0], END_X)
ROOM_Y = (REAR_Y - ROOM[1], REAR_Y)
ROOM_Z = (FLOOR_Z, FLOOR_Z + ROOM[2])
MOUTH_X = ROOM_X[0] - HOOK - 0.05
BED_Y = b.CARRIER_REAR

# ---- socket backer
FIN = (7.0, 0.8)                     # straight-up probe fin: length along X and thickness
FIN_Y = ((REST_ROWS[0] + REST_ROWS[1]) / 2, (REST_ROWS[1] + REST_ROWS[2]) / 2)
BACKER_LOW = -2.5                    # probe fins start this far down
TONGUE = 1.7                         # the sideways tongue fills this much under a seated socket
TONGUE_GRIP = 12.0                   # how far it stands out past the socket's outer end


# ---- upper row nearer the lower row
ROW_NEARER = (1.4, 1.2, 1.0)         # tried in this order; the first that passes every gate is built
ROW_BACK = 30.3                      # behind every upper key space; the rear rim starts here
WEB_MIN = 0.8                        # the web left between the rows is at least this thick
WEB_SHARE = 0.6                      # and keeps at least this share of its present section
UPPER = ("key_3_", "key_4_")
_CACHE = {}

# ---- seam between the lowered banks and the centre deck
SEAM = 1.0                           # the strip of centre deck inspected beside each bank
SEAM_REACH = 1.5                     # the strip of centre deck that may be trimmed beside each bank
SEAM_Y = (9.0, 16.0)                 # behind the lid rails and their ramps, in front of the hinge cheeks
SEAM_OPEN = 0.4                      # anything above the deck narrower than twice this in plan is removed
SEAM_STEP = 0.2                      # the trimmed end starts one layer high
SEAM_RAMP = 0.7                      # and reaches full height over this length

# ---- wall facing the inboard end of the upper-left socket: (set back, along Y from the socket's
#      front edge, up from the socket's underside). The native witness is 1.8 to 2.0 mm along, 2.05 mm up.
SOCKET_EASE = (0.25, (1.3, 2.5), (1.45, 2.65))


def placed(space, name, drop, nearer):
    """One inherited key space at its R58 position: 1.42 mm lower, upper keys also nearer the lower row."""
    move = (0.0, -nearer if name.startswith(UPPER) else 0.0, -drop)
    if hasattr(space, "offsets"):
        return type(space)(space.solid.translate(move), space.offsets)
    return space.translate(move)


def poses(space):
    return list(space.poses()) if hasattr(space, "poses") else [space]


def banks(bank_x, z0, z1):
    return b.mirrored(b.box(bank_x, 60, -60, 60, z0, z1))


def drop_seats(source, drop, bank_x):
    upper = source ^ banks(bank_x, SPLIT_Z, 60)
    return upper, (source - upper) + upper.translate((0, 0, -drop))


def relieve(stage, bank_x, layer):
    """Remove the dead layer under the lowered seats, keeping a rounded column over each member below."""
    low, top = layer
    members = stage ^ banks(bank_x, low - 1.2, low - 0.05)
    footprint = members.project().offset(KEEP, mf.JoinType.Round, 2.0, 32)
    keep = mf.Manifold.extrude(footprint, top - low + 0.04).translate((0, 0, low - 0.02))
    dead = (stage ^ banks(bank_x, low - 0.02, top)) - keep
    return stage - dead, dead, footprint


def blend_seam(solid, bank_x, deck):
    """Give whatever stands on the centre deck a printable end where it meets a lowered bank.

    A low wall of the OP1 pocket crosses the right bank seam at a shallow angle, 0.65 mm above the
    deck. It used to end against the raised seat platform. With the seat lowered, its cut end is a
    thin wedge: in the rear-down print it first becomes wide enough to lay down when it is already
    full height, with nothing under it. Two bounded cuts, beside both banks, Y 9 to 16 only:
      1. the wedge tip is removed back to where the wall is 0.8 mm wide in plan;
      2. the new end is ramped at 45 degrees, so it starts one layer high and grows a layer at a time.
    Nothing is added, and nothing below deck height or outside the 1.5 mm strip is touched.
    """
    low = deck + 0.005
    side_box = lambda sign, reach, y0, y1: b.box(*sorted((sign * (bank_x - reach), sign * (bank_x + 0.02))), y0, y1, low, 14.5)
    cuts = []
    for sign in (1.0, -1.0):
        target = side_box(sign, SEAM_REACH, *SEAM_Y)
        # 1. Take away what is too narrow in plan to print as a wall. Measured on a wider patch so
        #    the edges of the target box are not mistaken for edges of the part.
        plan = (solid ^ side_box(sign, SEAM_REACH + 1.7, SEAM_Y[0] - 3.0, SEAM_Y[1] + 3.0)).project()
        if plan.is_empty():
            continue
        sound = plan.offset(-SEAM_OPEN, mf.JoinType.Round, 2.0, 24).offset(SEAM_OPEN, mf.JoinType.Round, 2.0, 24)
        thin = mf.Manifold.extrude(plan - sound, 14.5 - low).translate((0, 0, low)) ^ target ^ solid
        cuts.append(thin)
        # 2. Ramp the new rear end at 45 degrees so it grows from deck height, one layer at a time.
        rest = (solid - thin) ^ target
        if rest.is_empty():
            continue
        end = float(rest.bounding_box()[4])
        line = lambda y: low + SEAM_STEP + (end - y)
        ramp = b.prism_yz([(end + 0.1, line(end + 0.1)), (end - SEAM_RAMP, line(end - SEAM_RAMP)), (end - SEAM_RAMP, 14.5), (end + 0.1, 14.5)],
                          *sorted((sign * (bank_x - SEAM_REACH), sign * (bank_x + 0.02))))
        cuts.append(ramp ^ rest)
    cut = b.union(cuts)
    return (solid - cut, cut) if not cut.is_empty() else (solid, cut)


def ease_socket_end(solid, socket):
    """A small pocket in the wall facing the inboard end of the upper-left socket.

    The native slice laid one inner-wall bead against the largest-tolerance socket at its seated
    position, at about X -16.69, Y 13.45 to 13.65, Z 7.65. The CAD wall clears the socket; the
    bead is the slicer rounding a thin wall up to a whole line. The wall face is set back
    SOCKET_EASE[0] mm over a patch placed from the socket's own corner, so it follows the key.
    """
    x0, y0, z0, x1, y1, z1 = (float(v) for v in socket.bounding_box())
    depth, along, up = SOCKET_EASE
    pocket = b.box(x1 - 0.02, x1 + depth, y0 + along[0], y0 + along[1], z0 + up[0], z0 + up[1])
    cut = solid ^ pocket
    report = dict(wall_set_back_mm=depth, pocket_x_mm=[round(x1 - 0.02, 3), round(x1 + depth, 3)],
                  pocket_y_mm=[round(y0 + along[0], 3), round(y0 + along[1], 3)], pocket_z_mm=[round(z0 + up[0], 3), round(z0 + up[1], 3)],
                  removed_mm3=round(float(cut.volume()), 4), native_witness_xyz_mm=[-16.694, 13.6502, 7.6473])
    return solid - pocket, report


def seam_starts(solid, bank_x, deck, step=0.2, line=0.4):
    """Deposited area beside the two bank seams that starts with nothing under it.

    Each print layer is first reduced to what a 0.4 mm line can lay down (features narrower than
    0.32 mm drop out, as in the slicer), then compared with the layer under it.
    """
    inner, outer, floor, top = bank_x - SEAM - 0.6, bank_x + 0.6, deck - 3.0, 14.0
    window = b.mirrored(b.box(inner, outer, -60, 60, floor, top))
    turned = (solid ^ window).transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]])     # slice(y) gives (X, Z)
    front, radius = float(solid.bounding_box()[1]), 0.4 * line
    below, found = None, []
    for index, y in enumerate(np.arange(BED_Y - step / 2, front, -step)):
        here = turned.slice(float(y))
        laid = here.offset(-radius, mf.JoinType.Round, 2.0, 12).offset(radius, mf.JoinType.Round, 2.0, 12)
        if below is not None:
            for piece in (laid - below.offset(0.1, mf.JoinType.Round, 2.0, 8)).decompose():
                area = float(piece.area())
                x0, z0, x1, z1 = piece.bounds()
                # Pieces on the window's own edges continue outside it and are not judged here.
                edge = min(abs(abs(x0) - inner), abs(abs(x1) - inner), abs(abs(x0) - outer), abs(abs(x1) - outer), z0 - floor, top - z1) < 0.03
                if area >= 0.03 and not edge and z0 >= deck - 0.05:
                    found.append(dict(print_layer=index + 1, y_mm=round(float(y), 2), x_mm=[round(float(x0), 2), round(float(x1), 2)],
                                      z_mm=[round(float(z0), 2), round(float(z1), 2)], area_mm2=round(area, 3)))
        below = laid
    return found


def web_plan(slab, sign, nearer):
    """Where one bank's seat slab is cut between the rows, and how much web is left after the move.

    The cut is placed where the most slab section runs unbroken from WEB_MIN in front of the
    moved block's new front face to the cut itself. That section is the web that remains.
    """
    half = slab ^ (b.box(0, 60, -60, 60, -60, 60) if sign > 0 else b.box(-60, 0, -60, 60, -60, 60))
    turned = half.transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]])           # slice(y) gives (X, Z)
    stations = [round(float(y), 2) for y in np.arange(8.0, 12.61, 0.1)]
    sections = [turned.slice(y) for y in stations]

    def through(y0, y1):
        common = None
        for y, section in zip(stations, sections):
            if y0 - 1e-6 <= y <= y1 + 1e-6:
                common = section if common is None else common ^ section
        return 0.0 if common is None else float(common.area())

    now = max(through(y, y + WEB_MIN) for y in stations if y + WEB_MIN <= 12.6)
    choices = [(through(cut - nearer - WEB_MIN, cut), cut) for cut in stations if cut - nearer >= 8.8 and cut <= 12.5]
    kept, cut = max(choices)
    return dict(cut_y_mm=cut, web_section_now_mm2=round(now, 2), web_section_kept_mm2=round(kept, 2),
                web_kept_share=round(kept / now, 3) if now > 0 else 0.0, kept_web_thickness_at_least_mm=WEB_MIN)


def move_upper_row(stage, bank_x, top, nearer, plan, footprint):
    """Move the upper keys' part of each seat slab toward the lower row.

    Only the slab above the relieved layer moves. Every guard and rest member below it stays, and
    so does the slab material directly over each member, so no root is left on a thin overlap.
    The rear rim is extended forward to fill behind the moved block.
    """
    roots = mf.Manifold.extrude(footprint, 14.0 - top).translate((0, 0, top - 0.02))
    out = stage
    for side, sign in (("right", 1.0), ("left", -1.0)):
        cut = plan[side]["cut_y_mm"]
        bank = b.box(bank_x, 60, -60, 60, top, 60) if sign > 0 else b.box(-60, -bank_x, -60, 60, top, 60)
        slab = stage ^ bank
        block = slab ^ b.box(-60, 60, cut, ROW_BACK, -60, 60)
        rim = slab ^ b.box(-60, 60, ROW_BACK, ROW_BACK + 0.2, -60, 60)
        fill = b.union(rim.translate((0, -float(t), 0)) for t in np.arange(0.2, nearer + 0.19, 0.2))
        out = (out - (bank ^ b.box(-60, 60, cut - nearer, ROW_BACK, -60, 60))) + block.translate((0, -nearer, 0)) + fill + (slab ^ roots)
    return out


def root_evidence(before, after, footprint, top):
    """Slab section over each member that rises into the upper-row region, unshifted against shifted."""
    z = top + 0.15
    old, new = before.slice(z), after.slice(z)
    rows = []
    for piece in footprint.decompose():
        x0, y0, x1, y1 = piece.bounds()
        if y1 < 8.0 or y0 > ROW_BACK:
            continue
        near = piece.offset(1.0, mf.JoinType.Round, 2.0, 16)
        a, c, a2, c2 = (float((section ^ zone).area()) for section, zone in ((old, piece), (new, piece), (old, near), (new, near)))
        if a > 0.3:
            rows.append(dict(at_xy_mm=[round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)], over_the_member_mm2=dict(unshifted=round(a, 2), shifted=round(c, 2)),
                             within_1_mm_mm2=dict(unshifted=round(a2, 2), shifted=round(c2, 2))))
    return rows


def seat_stage(shared, nearer):
    """Everything up to the re-cut key spaces, for one upper-row move. The tray is added later."""
    q, h, r, d, d44, drop, bank_x, layer, source, working, raw_cutters, _ = shared
    upper, moved = drop_seats(source, drop, bank_x)
    relieved, dead, footprint = relieve(moved, bank_x, layer)
    rowed, plan = relieved, {}
    if nearer > 0:
        slab = relieved ^ banks(bank_x, layer[1], 60)
        plan = {side: web_plan(slab, sign, nearer) for side, sign in (("right", 1.0), ("left", -1.0))}
        if min(row["web_kept_share"] for row in plan.values()) < WEB_SHARE:
            return dict(plan=plan, thin=True)
        rowed = move_upper_row(relieved, bank_x, layer[1], nearer, plan, footprint)
    stage = deepen(rowed, bank_x, h.base.rod() + working["external_wire_bus"])
    cutters = {name: placed(space, name, drop, nearer) for name, space in raw_cutters.items()}
    carved = d44.r22.spaces16.carve(stage, cutters, f"R58 key seats, upper row {nearer:g} mm nearer")
    return dict(upper=upper, moved=moved, relieved=relieved, dead=dead, footprint=footprint, rowed=rowed, plan=plan, stage=stage, carved=carved, thin=False)


def deepen(stage, bank_x, keep_out):
    """Extend every guard and rest member under the banks downward, outside the rod and wire lane."""
    zone = banks(bank_x, -6, GUARD_TOP) + b.mirrored(b.box(8.0, bank_x, -1.5, 12.0, -6, GUARD_TOP))
    zone ^= b.box(-60, 60, -1.5, 19.5, -6, GUARD_TOP)
    guard = stage ^ zone
    return stage + (b.union(guard.translate((0, 0, -float(t))) for t in np.arange(0.2, DEEPER + 0.01, 0.2)) - keep_out)


def room():
    return b.box(ROOM_X[0], ROOM_X[1], ROOM_Y[0], ROOM_Y[1], ROOM_Z[0], ROOM_Z[1])


def pack():
    """The bought pouch resting on the shelf, centred in its fitting space."""
    x, y = sum(ROOM_X) / 2, sum(ROOM_Y) / 2
    return b.box(x - PACK[0] / 2, x + PACK[0] / 2, y - PACK[1] / 2, y + PACK[1] / 2, FLOOR_Z, FLOOR_Z + PACK[2])


def latch_hook():
    """Hook on the tip of the sprung finger: a ramp toward the mouth, a square face toward the pouch."""
    y = REAR_Y
    return b.prism_xy([(MOUTH_X, y + 0.2), (MOUTH_X, y), (ROOM_X[0] - 0.05, y - HOOK), (ROOM_X[0], y - HOOK), (ROOM_X[0], y + 0.2)], LEAF[1], LEAF[2])


def tray():
    inner, outer, edge = SOCKET_PATH
    roof = ROOM_Z[1]
    low = FLOOR_Z - SHELF
    inboard = END_X + WALL
    rear = b.box(MOUTH_X, inboard, REAR_Y, BED_Y, low, roof + 0.8) + b.box(-30.0, inboard, REAR_Y, BED_Y, roof, TRAY_TOP)
    # Two slits free a finger of the rear wall. It bends rearward as the pouch passes the hook.
    for z in (LEAF[1] - 0.6, LEAF[2]):
        rear -= b.box(MOUTH_X - 1, LEAF[0], REAR_Y - 0.05, BED_Y + 1, z, z + 0.6)
    shelf = b.box(MOUTH_X, inboard, edge, REAR_Y + 0.05, low, FLOOR_Z)
    front = ROOM_Y[0] - RAMP
    horns = b.box(inner, inboard, front, edge + 0.05, low, FLOOR_Z) + b.box(MOUTH_X, outer, front, edge + 0.05, low, FLOOR_Z)
    # Low front ramps: 45 degrees on the pouch side, which is the side that prints first.
    ramp = lambda x0, x1: b.prism_yz([(ROOM_Y[0], FLOOR_Z - 0.01), (front, FLOOR_Z - 0.01), (front, FLOOR_Z + RAMP)], x0, x1)
    ramps = ramp(inner, inboard) + ramp(MOUTH_X, outer)
    strip = b.box(MOUTH_X, inboard, REAR_Y - 3.0, REAR_Y + 0.05, roof, roof + 0.8)
    # Roof rib under the solid bank behind the switch posts. Its rear face rises at 45 degrees.
    rise = TRAY_TOP - roof
    rib = b.prism_yz([(24.6 + rise, TRAY_TOP), (24.6, roof), (23.3, roof), (23.3, TRAY_TOP)], -30.0, -13.6)
    end = b.box(END_X, inboard, 25.0, BED_Y, low, 7.3)
    return rear + shelf + horns + ramps + strip + rib + end + latch_hook()


def fin(x0, x1, y, top):
    return b.box(x0, x1, y - FIN[1] / 2, y + FIN[1] / 2, BACKER_LOW, top)


def clear_runs(near, x0, x1, y, top):
    """Stretches along one slot where a 1 mm long fin rises from 10 mm below to the socket untouched."""
    lifts = (0.0, 2.0, 4.0, 6.0, 8.0, 10.0)
    starts = np.arange(x0, x1 - 0.99, 0.5)
    free = [max(k.vol(fin(float(s), float(s) + 1.0, y, top).translate((0, 0, -dz)), near) for dz in lifts) < 1e-4 for s in starts]
    runs, begin = [], None
    for index, ok in enumerate([*free, False]):
        if ok and begin is None:
            begin = index
        if not ok and begin is not None:
            runs.append((float(starts[begin]), float(starts[index - 1]) + 1.0))
            begin = None
    return runs, "".join("#" if ok else "." for ok in free)


# ------------------------------------------------------------------ evidence
def properties(section):
    """Area, depth and bending figures of one closed section in (Y, Z), for a load along Z."""
    area = moment = second = 0.0
    low, high = np.inf, -np.inf
    for poly in section.to_polygons():
        p = np.asarray(poly, float)
        q = np.roll(p, -1, axis=0)
        cross = p[:, 0] * q[:, 1] - q[:, 0] * p[:, 1]
        area += cross.sum() / 2
        moment += ((p[:, 1] + q[:, 1]) * cross).sum() / 6
        second += ((p[:, 1] ** 2 + p[:, 1] * q[:, 1] + q[:, 1] ** 2) * cross).sum() / 12
        low, high = min(low, p[:, 1].min()), max(high, p[:, 1].max())
    if area < 1e-6:
        return None
    centre = moment / area
    inertia = second - area * centre ** 2
    return dict(area_mm2=round(area, 3), depth_mm=round(high - low, 3), second_moment_mm4=round(inertia, 3),
                section_modulus_mm3=round(inertia / max(high - centre, centre - low), 3))


def along_x(solid):
    return solid.transform([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]])     # slice(x) then gives (Y, Z)


def beam(turned, x, row):
    """The rest beam section at one X station: the piece round the beam centre line."""
    window = mf.CrossSection.square((3.2, 5.4)).translate((row - 1.6, -2.4))
    for piece in (turned.slice(float(x)) ^ window).decompose():
        x0, z0, x1, z1 = piece.bounds()
        if x0 <= row <= x1 and z0 <= REST_Z <= z1:
            return properties(piece)
    return None


def rest_evidence(before, after):
    old, new = along_x(before), along_x(after)
    witness, weakest = {}, {}
    for side, sign in (("right", 1), ("left", -1)):
        for row in REST_ROWS:
            pairs, lost = [], []
            for x in np.arange(9.5, 27.01, 0.5):
                a, c = beam(old, sign * x, row), beam(new, sign * x, row)
                if a and a["area_mm2"] > 0.8:
                    if c:
                        pairs.append((float(x), a, c))
                    else:
                        lost.append(round(sign * float(x), 1))
            if lost:
                weakest[f"{side}_y_{row:g}"] = dict(stations=len(pairs), beam_missing_at_x_mm=lost, smallest_gain=0.0)
                continue
            if not pairs:
                continue
            thin = min(pairs, key=lambda item: item[2]["section_modulus_mm3"])
            weakest[f"{side}_y_{row:g}"] = dict(
                stations=len(pairs), at_x_mm=round(sign * thin[0], 1), r57=min(p[1]["section_modulus_mm3"] for p in pairs),
                r58=thin[2]["section_modulus_mm3"], smallest_gain=round(min(p[2]["section_modulus_mm3"] / p[1]["section_modulus_mm3"] for p in pairs), 2),
                smallest_area_mm2=dict(r57=min(p[1]["area_mm2"] for p in pairs), r58=min(p[2]["area_mm2"] for p in pairs)))
        witness[side] = dict(point_mm=[sign * WITNESS_X, REST_ROWS[1], REST_Z], r57=beam(old, sign * WITNESS_X, REST_ROWS[1]),
                             r58=beam(new, sign * WITNESS_X, REST_ROWS[1]))
    return witness, weakest


def print_overhang(solid, step=0.2):
    """Area that starts with nothing under it, layer by layer in the rear-down print (a proxy)."""
    turned = solid.transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0]])     # slice(y) gives (X, Z)
    front = float(solid.bounding_box()[1])
    below, total, largest = None, 0.0, 0.0
    for y in np.arange(BED_Y - step / 2, front, -step):
        here = turned.slice(float(y))
        if below is not None:
            for piece in (here - below.offset(0.35, mf.JoinType.Round, 2.0, 12)).decompose():
                if piece.area() > 0.05:
                    total += piece.area()
                    largest = max(largest, piece.area())
        below = here
    return dict(total_mm2=round(total, 1), largest_patch_mm2=round(largest, 2))


def lowered(space, drop):
    return placed(space, "", drop, 0.0)


def evaluate(output, shared, nearer):
    """Build and check the holder with the upper row `nearer` mm closer. Writes only an attempt mesh."""
    q, h, r, d, d44, drop, bank_x, layer, source, working, raw_cutters, hang_r57 = shared
    vol = k.vol
    volume = lambda shape: float(shape.volume())
    where = {name: placed(space, name, drop, nearer) for name, space in working.items() if name.startswith("key_")}
    made = seat_stage(shared, nearer)
    plan = made["plan"]
    if made["thin"]:
        return dict(failed=["the web left between the rows would be too thin"], plan=plan)
    upper, moved, relieved, dead, rowed, stage, carved = (made[x] for x in ("upper", "moved", "relieved", "dead", "rowed", "stage", "carved"))
    if nearer == 0:
        _CACHE["unshifted"] = carved
    added = tray()
    deck = float(d44.r22.base.plate_top())
    unblended = carved + added
    whole, blend = blend_seam(unblended, bank_x, deck)
    whole, socket_relief = ease_socket_end(whole, where["key_3_maximum_socket"])
    print("EASE " + json.dumps(socket_relief), flush=True)
    pieces = sorted(whole.decompose(), key=lambda s: -s.volume())
    loose = [round(volume(p), 5) for p in pieces[1:]]
    print("upper row", nearer, "mm nearer: pieces", len(pieces), loose[:8], flush=True)
    if any(v > 0.11 for v in loose) or sum(loose) > 0.6:
        return dict(failed=[f"detached material {loose[:6]}"], plan=plan)
    final = pieces[0]
    path = output / "Key_Carrier-attempt.stl"
    mesh = b.save_closed(path, final)
    C = b.load(path)
    tools = {}

    failed = []

    def gate(name, passed):
        if not passed:
            failed.append(name)

    # --- seats
    centre = b.box(-8.0, 8.0, -60, 60, -60, 60)
    cut = stage - carved
    change = dict(
        r57_volume_mm3=round(volume(source), 1), r58_volume_mm3=round(float(mesh.volume), 1),
        battery_tray_volume_mm3=round(volume(added - carved), 1),
        moved_down_mm=drop, moved_volume_mm3=round(volume(upper), 1),
        recut_for_the_lower_sockets_mm3=round(volume(cut), 2),
        middle_16_mm_differs_from_r57_before_the_tray_mm3=round(volume((carved - source) ^ centre) + volume((source - carved) ^ centre), 3),
        discarded_skin_mm3=round(sum(loose), 5))
    gate("the middle of the holder is the R57 middle", change["middle_16_mm_differs_from_r57_before_the_tray_mm3"] < volume(cut ^ centre) + 0.1)
    seats = rowed ^ banks(bank_x, layer[1] + 0.03, 60)
    change["moved_seat_material_lost_mm3"] = round(volume(seats - carved), 3)
    gate("seat material is the R57 material", change["moved_seat_material_lost_mm3"] < change["recut_for_the_lower_sockets_mm3"] + 0.05)

    # --- every inherited key space, 1.42 mm lower, pose by pose, against the finished holder
    names = sorted(x for x in working if x.startswith("key_"))
    entered, checked = {}, 0
    for name in names:
        amounts = [vol(C, pose) for pose in poses(where[name])]
        checked += len(amounts)
        if max(amounts) > TOL:
            entered[name] = round(max(amounts), 4)
    spaces = dict(poses_checked=checked, lowered_spaces_entered_by_the_holder_mm3=entered)
    gate("lowered key spaces are clear of the holder and tray", not entered)

    # --- dead layer
    r42 = d44.previous.geometry()[0]
    in_layer = banks(bank_x, layer[0], layer[1])
    relief = dict(layer_z_mm=[round(v, 2) for v in layer], removed_mm3=round(volume(dead), 1), kept_over_members_mm3=round(volume(carved ^ in_layer), 1),
                  r57_had_in_this_layer_after_the_drop_mm3=round(volume(moved ^ in_layer), 1),
                  r42_height_design_had_in_this_layer_mm3=round(volume(r42.translate((0, 0, 0)) ^ in_layer), 1),
                  kept_within_mm_of_a_member_below=KEEP,
                  seat_plate_and_backplate_above_the_layer_changed_mm3=change["moved_seat_material_lost_mm3"])

    # --- finger rest
    witness, weakest = rest_evidence(source, C)
    deeper = stage - rowed
    rest = dict(members_extended_down_mm=DEEPER, underside_plane_z_mm=dict(r57=round(REST_Z - REST_R, 2), r58=round(REST_Z - REST_R - DEEPER, 2)),
                added_mm3=round(volume(deeper), 1), witness_sections=witness, weakest_section_along_each_beam=weakest,
                fracture_site_known=False, strength_measured=False)
    gains = [row["smallest_gain"] for row in weakest.values()]
    gate("every rest beam section is at least as strong in bending as R57", bool(gains) and min(gains) >= 0.999)
    gate("the witness sections are deeper", all(w["r57"] and w["r58"] and w["r58"]["section_modulus_mm3"] > 1.5 * w["r57"]["section_modulus_mm3"]
                                                for w in witness.values()))

    # --- the click parts on this holder
    load = lambda folder, name: b.load(folder / f"{name}-assembly.stl")
    P, PLAIN, STOP = (load(output, name) for name in ("Touch_Paddle", "OP1_Lid_Plain", "OP1_Lid_Stop"))
    PIN, CLIP, BAR = (load(n.R57 / "exports", name) for name in ("Hinge_Pin", "Pin_Clip", "DFR_Post_Bar"))
    M = q.hardware()
    op1 = d.union(M[x] for x in ("board", "sockets", "housing", "plug", "terminals", "op1_wire", "switch", "plunger"))
    fitted = d.union(where[f"key_{i}_{item}"] for i in (0, 2, 3, 4) for item in ("switch", "maximum_socket", "socket_tape_zone"))
    keys = fitted + d.union(where[f"key_{i}_cap_travel"] for i in (0, 2, 3, 4))
    shift = (0.0, r.CLICK_SHIFT, 0.0)
    touch = k.moved(r.sensor() + q.gravity_pins() + r.connector(), shift)
    riding = P + BAR + touch + k.moved(r.clips(), shift)
    cheeks = b.box(-12, 12, 25.2, 33, 10, 22)
    sweep = max(vol(m.posed(riding, a), (C - cheeks) + keys) for a in np.linspace(-6.0, 1.45, 31))
    rod, lane = h.base.rod(), working["external_wire_bus"]
    static = dict(holder_to_op1_and_switch=vol(C, op1), holder_to_paddle=vol(C, P + BAR), holder_to_pin=vol(C, PIN),
                  holder_to_pin_clip=vol(C, CLIP), holder_to_plain_retainer=vol(C, PLAIN), holder_to_stop_retainer=vol(C, STOP),
                  paddle_to_lowered_keys=vol(riding, keys), paddle_sweep_from_6_deg_lift_to_full_press=sweep,
                  tray_to_rod=vol(added, rod), tray_to_wire_lane=vol(added, lane), tray_to_op1_and_lead=vol(added, op1),
                  holder_in_rod_and_wire_lane_more_than_r57=max(0.0, vol(C, rod + lane) - vol(source, rod + lane)))
    gate("click parts, rod and wire lane clear the holder", max(static.values()) < TOL)
    hinge_pin_past_keys = vol(PIN.translate((12.0, 0, 0)) + PIN.translate((-12.0, 0, 0)), keys)

    # --- the battery
    space = room()
    hook_zone = b.box(MOUTH_X - 0.1, ROOM_X[0] + 0.01, REAR_Y - HOOK - 0.1, REAR_Y + 0.3, LEAF[1] - 0.05, LEAF[2] + 0.05)
    slide = max(vol(space.translate((-float(dx), 0, 0)), C - hook_zone) for dx in np.arange(0.0, 33.1, 1.0))
    blocked = {}
    for name in names:
        if hasattr(working[name], "offsets"):
            amount = max(vol(space, pose) for pose in poses(where[name]))
            if amount > TOL:
                blocked[name] = round(amount, 2)
    edge = float((carved ^ b.box(-60, 0, ROOM_Y[0], BED_Y, 8, 12)).bounding_box()[0])
    battery = dict(
        pack_mm=list(PACK), fitting_space_mm=list(ROOM), fitting_space_x_mm=list(ROOM_X), fitting_space_y_mm=list(ROOM_Y), fitting_space_z_mm=list(ROOM_Z),
        fitting_space_to_holder_mm3=vol(space, C - hook_zone), fitting_space_to_fitted_switches_sockets_and_tape_mm3=vol(space, fitted),
        fitting_space_to_rod_and_wire_lane_mm3=vol(space, rod + lane),
        slide_in_from_the_left_33_mm_mm3=slide, latch_hook_reach_mm=HOOK, latch_finger_length_mm=round(LEAF[0] - MOUTH_X, 2),
        latch_finger_strain_at_full_bend=round(1.5 * (BED_Y - REAR_Y) * HOOK / (LEAF[0] - MOUTH_X) ** 2, 4),
        play_round_the_pouch_mm=dict(along=round(ROOM[0] - PACK[0], 2), across=round(ROOM[1] - PACK[1], 2), thickness=round(ROOM[2] - PACK[2], 2)),
        holder_left_edge_x_mm=round(edge, 2), pouch_end_past_the_holder_edge_mm=round(edge - (ROOM_X[0] + (ROOM[0] - PACK[0]) / 2), 2),
        tray_past_the_holder_edge_mm=round(edge - MOUTH_X, 2),
        socket_loading_paths_that_need_the_battery_out_mm3=blocked,
        free_space_beyond_the_left_end_12_mm_mm3=vol(b.box(MOUTH_X - 12.0, MOUTH_X - 0.1, ROOM_Y[0] - 2, ROOM_Y[1], ROOM_Z[0], ROOM_Z[1] + 4), C + fitted + rod),
        lead_exit=dict(left_end="open mouth; the plug stays outside", inboard_end="open in front of the end wall, Y 18.75 to 25; leads lie in from the front",
                       which_end_the_leads_leave="not confirmed on the bought pack"))
    gate("the pouch space is clear when seated", max(battery["fitting_space_to_holder_mm3"], battery["fitting_space_to_fitted_switches_sockets_and_tape_mm3"],
                                                    battery["fitting_space_to_rod_and_wire_lane_mm3"]) < TOL)
    gate("the pouch slides in from the left", slide < TOL)
    gate("only the upper-left socket path needs the battery out", all(name.startswith("key_3_") for name in blocked))

    # --- backing the two lower sockets from below
    access = {}
    for label, i in (("bottom_left", 0), ("bottom_right", 2)):
        socket = where[f"key_{i}_maximum_socket"]
        x0, y0, z0, x1, y1, _ = (float(v) for v in socket.bounding_box())
        near = C ^ b.box(x0 - 6, x1 + 6, y0 - 6, y1 + 6, -20, z0 + 2)
        column = b.box(x0, x1, y0, y1, BACKER_LOW, z0 - 0.05)
        open_area = (x1 - x0) * (y1 - y0) - float((near ^ column).project().area())
        maps = {f"y_{y:g}": clear_runs(near, x0, x1, y, z0)[1] for y in FIN_Y}
        row = dict(socket_underside_z_mm=round(z0, 2), socket_x_mm=[round(x0, 2), round(x1, 2)], socket_footprint_mm2=round((x1 - x0) * (y1 - y0), 1),
                   open_straight_below_mm2=round(open_area, 1), slot_width_between_beams_mm=round(REST_ROWS[1] - REST_ROWS[0] - 2 * REST_R, 2),
                   straight_up_between_the_beams_in_half_mm_steps=maps,
                   straight_up_note="'#' is clear for a 0.8 mm fin from 10 mm below; most of each slot is blocked by rest members")
        # A tongue that follows the socket's own sideways loading path and backs it from below.
        side = 1.0 if x0 + x1 > 0 else -1.0
        inner, outer = (x0, x1) if side > 0 else (x1, x0)
        span = sorted((inner + side * 0.5, outer + side * TONGUE_GRIP))
        wide = (y0 + 0.35, y1 - 0.35)
        tongue = b.box(span[0], span[1], wide[0], wide[1], z0 - TONGUE, z0 - 0.1)
        keels = b.union(b.box(span[0], span[1], y - 0.6, y + 0.6, REST_Z + REST_R + 0.1, z0 - TONGUE + 0.05) for y in REST_ROWS[1:3])
        local = C ^ b.box(min(span) - 30, max(span) + 30, y0 - 6, y1 + 6, -20, z0 + 4)
        # The tongue lies where this socket's own tape would be; every other fitted part must stay clear.
        others = d.union(where[f"key_{j}_{item}"] for j in (0, 2, 3, 4) for item in ("switch", "maximum_socket")
                         if (j, item) != (i, "maximum_socket"))
        route = lambda tool: max(vol(tool.translate((side * float(dx), 0, 0)), local + others) for dx in np.arange(0.0, 26.1, 2.0))
        options = (("tongue riding on two rest beams", tongue + keels), ("tongue only", tongue))
        chosen = next(((name, tool) for name, tool in options if route(tool) < 1e-3), None)
        row["sideways_backer"] = dict(
            fits=chosen is not None, form=None if chosen is None else chosen[0], enters_from="right" if side > 0 else "left",
            tongue_mm=dict(x=[round(v, 2) for v in span], y=[round(v, 2) for v in wide], z=[round(z0 - TONGUE, 2), round(z0 - 0.1, 2)]),
            path_to_holder_and_other_fitted_parts_mm3={name: round(route(tool), 4) for name, tool in options},
            socket_area_backed_mm2=0.0 if chosen is None else round(vol(tongue.translate((0, 0, 0.3)), socket) / 0.2, 1),
            gap_under_socket_mm=0.1)
        if chosen is not None:
            tools[f"Socket_Backer_{'Right' if side > 0 else 'Left'}"] = chosen[1]
        access[label] = row
    gate("a backer reaches both lower sockets", all(row["sideways_backer"]["fits"] and row["sideways_backer"]["socket_area_backed_mm2"] > 30.0 for row in access.values()))

    # --- print proxy and mass
    hang = dict(r57=hang_r57, r58=print_overhang(C), note="counts bridges too; a proxy until the native slice is audited")
    gate("no large new unsupported start", hang["r58"]["total_mm2"] < 1.25 * hang["r57"]["total_mm2"] + 5.0)
    old_tray = [b.load(n.HERE.parent / "carbon-rod-holders-r48-edge-click/exports" / f"{name}-assembly.stl") for name in ("Battery_Holder", "Battery_End_Door")]
    grams = lambda value: round(value * PETG, 2)
    tray_only = volume(added - carved)
    mass = dict(solid_petg_g_per_cm3=1.27, note="solid CAD volume, not sliced weight",
                r57_holder_g=grams(volume(source)), r58_holder_without_tray_g=grams(float(mesh.volume) - tray_only), r58_tray_g=grams(tray_only),
                r58_holder_with_tray_g=grams(float(mesh.volume)),
                removed_separate_r48_battery_holder_and_door_g=grams(sum(volume(part) for part in old_tray)),
                dead_layer_removed_g=grams(volume(dead)), rest_beams_added_g=grams(volume(deeper)))

    # --- heights. Bought-part heights are model estimates.
    cap_top = d44.CHOC_TOP_R42
    bank_top = float((C ^ b.box(-22, -20, -9.2, -8.0, 0, 30)).bounding_box()[5])
    deck_top = float((C ^ b.box(-12.69, -11.6, 14, 24, 0, 30)).bounding_box()[5])
    lever = lambda y: (m.AXIS_Y - y) * np.sin(np.radians(1.4307))
    heights = dict(
        estimates=True,
        seat_bank_top_mm=dict(r57=round(bank_top + drop, 3), r58=round(bank_top, 3)), centre_deck_top_beside_the_bank_mm=round(deck_top, 3),
        keycap_top_released_mm=dict(r57=round(cap_top + drop, 3), r58=cap_top),
        keycap_top_pressed_mm=dict(r57=round(cap_top + drop - PRESS_TRAVEL, 3), r58=round(cap_top - PRESS_TRAVEL, 3)),
        touch_surface_released_mm=b.BOARD_TOP,
        touch_surface_at_full_click_mm={name: round(b.BOARD_TOP - float(lever(y)), 3) for name, y in (("beside_the_bottom_row", 0.0), ("beside_the_top_row", 21.35 - nearer))},
        released_keycap_minus_released_touch_surface_mm=dict(r57=round(cap_top + drop - b.BOARD_TOP, 3), r58=round(cap_top - b.BOARD_TOP, 3)),
        history=dict(r42_keycap_below_touch_mm=1.72, r44_keycap_below_touch_mm=0.30, note="R53 lowered the touch surface 0.74 mm; the seats stayed"))
    gate("bank top is flush with the centre deck", abs(bank_top - deck_top) < 0.05)

    # --- the seam between each lowered bank and the centre deck
    if "r57_seam" not in _CACHE:
        _CACHE["r57_seam"] = seam_starts(source, bank_x, deck)
    before, after = seam_starts(unblended, bank_x, deck), seam_starts(C, bank_x, deck)
    inherited = lambda row: any(abs(row["y_mm"] - old["y_mm"]) < 0.5 and abs(row["x_mm"][0] - old["x_mm"][0]) < 0.6 and abs(row["z_mm"][0] - old["z_mm"][0]) < 0.6
                                for old in _CACHE["r57_seam"])
    cut_box = [round(float(v), 3) for v in blend.bounding_box()] if not blend.is_empty() else None
    seam_report = dict(trim=dict(strip_beside_each_bank_mm=SEAM_REACH, y_mm=list(SEAM_Y), only_above_deck_z_mm=deck, removed_if_narrower_in_plan_mm=2 * SEAM_OPEN,
                                 new_end_starts_mm=SEAM_STEP, new_end_ramp_deg=45),
                       removed_mm3=round(volume(blend), 4), removed_bounds_mm=cut_box,
                       removed_left_of_centre_mm3=round(volume(blend ^ b.box(-60, 0, -60, 60, -60, 60)), 4),
                       deposited_starts_with_nothing_under_them=dict(r57=_CACHE["r57_seam"], r58_before_the_chamfer=before, r58=after,
                                                                    window="above deck height, 1.6 mm of centre deck and 0.6 mm of bank beside each seam",
                                                                    note="CAD estimate of a 0.4 mm line at 0.2 mm layers; the native slice is the real test"))
    gate("nothing beside the bank seams starts in mid-air that R57 did not have", all(inherited(row) for row in after))

    # --- upper row: the slab over every member that rises into it, against the unshifted R58
    roots = []
    if nearer > 0:
        if "unshifted" not in _CACHE:
            _CACHE["unshifted"] = seat_stage(shared, 0.0)["carved"]
        roots = root_evidence(_CACHE["unshifted"], carved, made["footprint"], layer[1])
        gate("the slab over every guard and rest root is kept", bool(roots) and all(
            row["over_the_member_mm2"]["shifted"] >= 0.8 * row["over_the_member_mm2"]["unshifted"]
            and row["within_1_mm_mm2"]["shifted"] >= 0.75 * row["within_1_mm_mm2"]["unshifted"] for row in roots))
    top_y = round(21.35 - nearer, 3)
    cap_gap = lambda a, c: round(float(where[f"key_{c}_cap_travel"].bounding_box()[1] - where[f"key_{a}_cap_travel"].bounding_box()[4]), 3)
    socket_gap = round(float(where["key_3_maximum_socket"].bounding_box()[1] - where["key_0_maximum_socket"].bounding_box()[4]), 3)
    upper_row = dict(
        built=nearer > 0, moved_toward_the_lower_row_mm=nearer,
        row_pitch_mm=dict(r57=21.35, r58=top_y, smallest_with_0_6_mm_between_keycaps=18.0),
        keycap_envelope_gap_mm=dict(left=cap_gap(0, 3), right=cap_gap(2, 4)), left_socket_to_socket_gap_mm=socket_gap,
        slab_cut_and_web=plan, roots=roots,
        how=("Only the seat slab above the relieved layer moves. Every guard and rest member, and the slab directly over it, stays in place. "
             "The rear rim is extended forward behind the moved block.") if nearer > 0 else None,
        limit=("Calculated, not built: the upper-left socket loads from below through Y 12.6 and up, cut 0.25 mm oversize. Past about 1.45 mm nearer, "
               "that path starts to cut the rest beam whose rear edge is at Y 10.9. "
               "The 18.0 mm pitch needs the socket directions and the members under the banks redesigned together."))
    key_poses = {f"key_{i}": dict(centre_xy_mm=[x, y], moved_mm=[0.0, -nearer if i in (3, 4) else 0.0, -drop], socket_turn_deg=turn)
                 for i, x, y, turn in ((0, -21.0, 0.0, 0), (2, 21.0, 0.0, 0), (3, -21.0, top_y, 180), (4, 21.0, top_y, 0))}

    result = dict(physical_acceptance=False, sha256=sha256(path.read_bytes()).hexdigest(), source_r57_sha256=k.file_hash(n.R57 / "exports/Key_Carrier-assembly.stl"),
                  bounds_mm=[round(float(v), 3) for v in final.bounding_box()], change=change, key_spaces=spaces, dead_layer_relief=relief,
                  finger_rest=rest, lower_socket_access=access, print_overhang_proxy=hang, mass=mass, static_interference_mm3=static,
                  hinge_pin_through_fitted_upper_keycaps_mm3=hinge_pin_past_keys, battery=battery, heights=heights,
                  key_layout=dict(row_centres_y_mm=[0.0, top_y], column_centres_x_mm=[-21.0, 21.0], row_pitch_mm=top_y,
                                  keycap_envelope_gap_between_rows_mm=round(3.95 - nearer, 3),
                                  socket_turn_deg=dict(bottom_left=0, bottom_right=0, top_left=180, top_right=0), changed_in_r58=nearer > 0),
                  key_poses=key_poses, upper_row_shift=upper_row, seam_cleanup=seam_report,
                  upper_left_socket_end_relief=socket_relief, failed=failed, passes=not failed)
    return dict(failed=failed, plan=plan, result=result, tools=tools, attempt=path)


def main(output=None):
    output = Path(output) if output else n.EXPORT
    k.old.configure_new_op1()
    q, h, r, d = k.q, k.h, k.r, k.d
    d44 = h.d
    drop, bank_x = d44.KEY_RAISE_MM, d44.OUTER_BANK_START
    slab_bottom = float(d44.r22.base.slab_bottom())
    assert abs(drop - 1.42) < 1e-9 and abs(bank_x - 12.7) < 1e-9 and abs(slab_bottom - 7.27) < 1e-6
    source = b.load(n.R57 / "exports/Key_Carrier-assembly.stl")
    working = d44.geometry()[1]
    raw_cutters = {name: space for name, space in d44.socket_print_cutters(working).items() if name.startswith("key_")}
    shared = (q, h, r, d, d44, drop, bank_x, (slab_bottom - drop, slab_bottom), source, working, raw_cutters, print_overhang(source))

    # The nearest upper row that passes every gate is built. The unshifted holder is the fallback.
    attempts, chosen = [], None
    for nearer in (*ROW_NEARER, 0.0):
        try:
            outcome = evaluate(output, shared, float(nearer))
        except Exception as error:      # a failed trial geometry must not stop the fallback
            outcome = dict(failed=[f"{type(error).__name__}: {error}"], plan={})
        attempts.append(dict(upper_row_nearer_mm=nearer, failed=outcome["failed"], slab_cut_and_web=outcome.get("plan")))
        print("attempt", json.dumps(attempts[-1]), flush=True)
        if outcome["failed"] and "result" in outcome:
            print("SEAM " + json.dumps(outcome["result"]["seam_cleanup"]), flush=True)
        if not outcome["failed"]:
            chosen = outcome
            break
    if chosen is None:
        raise SystemExit("R58 key holder checks need attention: " + json.dumps(attempts))
    result = chosen["result"]
    result["upper_row_shift"]["attempts"] = attempts
    chosen["attempt"].replace(output / "Key_Carrier-assembly.stl")
    b.save_closed(output / "Battery_Pack-assembly.stl", pack())
    for name, tool in chosen["tools"].items():
        b.save_closed(output / f"{name}-assembly.stl", tool)
    (output / "carrier.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("change", "upper_row_shift", "key_layout", "print_overhang_proxy", "mass", "failed")}, indent=1), flush=True)
    print("SEAM " + json.dumps(result["seam_cleanup"]), flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
