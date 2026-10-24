#!/usr/bin/env python3
"""Printed loop wand: the one parametric source for every printable part.

Reads dimensions.json, builds solids with manifold3d, writes binary STL files in print
orientation, an assembly GLB and manifest.json, then checks the geometry.

    python wand_cad.py              build into exports/
    python wand_cad.py --check      rebuild in memory, compare with exports/, run every check
    python wand_cad.py --out DIR    build into another directory (reproducibility comparison)

Geometry checks prove the model, not a printed part. Fit, strength and comfort still need
the printed coupons and handles.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
import manifold3d as mf
from manifold3d import CrossSection, Manifold

HERE = Path(__file__).resolve().parent
DIMENSIONS = HERE / "dimensions.json"
D = json.loads(DIMENSIONS.read_text())
SEG = 64  # Fixed circle resolution keeps output reproducible.

SEC, H, J, S, TIP, CAP, POD, CPN = (D[k] for k in ("section", "handle", "joint", "shaft", "tip", "cap", "pod", "coupons"))
T, C = SEC["thickness"], SEC["chamfer"]
L = H["length"]  # Handle mouth plane.


# ----------------------------------------------------------------------------- primitives

def direction(theta: float) -> tuple[float, float]:
    """Unit (x, y) for a wand angle measured from +Y toward +X."""
    return math.sin(math.radians(theta)), math.cos(math.radians(theta))


def spin(m: Manifold, theta: float) -> Manifold:
    """Rotate about the wand axis by a wand angle (+Y toward +X, clockwise seen from the tip)."""
    return m.rotate((0.0, 0.0, -theta))


def union(parts: list[Manifold]) -> Manifold:
    return Manifold.batch_boolean(parts, mf.OpType.Add)


def cyl_z(r: float, z0: float, z1: float, r1: float | None = None, x: float = 0.0, y: float = 0.0) -> Manifold:
    return Manifold.cylinder(z1 - z0, r, r if r1 is None else r1, SEG).translate((x, y, z0))


def cyl_y(r: float, y0: float, y1: float, x: float = 0.0, z: float = 0.0, r1: float | None = None) -> Manifold:
    """Cylinder along +Y from y0 to y1 (r at y0, r1 at y1)."""
    return Manifold.cylinder(y1 - y0, r, r if r1 is None else r1, SEG).rotate((-90.0, 0.0, 0.0)).translate((x, y0, z))


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Manifold:
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def prism_z(poly: list[tuple[float, float]], z0: float, z1: float) -> Manifold:
    return Manifold.extrude(CrossSection([poly]), z1 - z0).translate((0.0, 0.0, z0))


def octagon(across_flats: float) -> list[tuple[float, float]]:
    """Regular octagon with flats facing +-X and +-Y."""
    r = across_flats / 2 / math.cos(math.radians(22.5))
    return [(r * math.cos(math.radians(22.5 + 45 * k)), r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]


def teardrop_cs(r: float, flat: float | None = None) -> CrossSection:
    """Circle with a 45-degree peak toward local +X, optionally cut flat at x = flat."""
    s, apex = r / math.sqrt(2), r * math.sqrt(2)
    shape = CrossSection.circle(r, SEG) + CrossSection([[(0.0, 0.0), (s, -s), (apex, 0.0), (s, s)]])
    if flat is not None and flat < apex:
        shape = shape ^ CrossSection.square((flat + r + 1, 2 * r + 2)).translate((-r - 1, -r - 1))
    return shape


def teardrop_z(r: float, z0: float, z1: float, apex_theta: float, flat: float | None = None) -> Manifold:
    """Horizontal-print bore along Z whose peak points at a wand angle (the print's up direction)."""
    m = Manifold.extrude(teardrop_cs(r, flat), z1 - z0).translate((0.0, 0.0, z0))
    return spin(m, apex_theta - 90.0)


def teardrop_y(r: float, y0: float, y1: float, z: float, apex_x: float = 1.0) -> Manifold:
    """Bore along +Y whose peak points along +X (or -X)."""
    m = Manifold.extrude(teardrop_cs(r), y1 - y0)
    u, v, w = (apex_x, 0.0, 0.0), (0.0, 0.0, -apex_x), (0.0, 1.0, 0.0)  # right-handed
    mat = np.array([[u[0], v[0], w[0], 0.0], [u[1], v[1], w[1], y0], [u[2], v[2], w[2], z]])
    return m.transform(mat)


def arc_points(r: float, t0: float, t1: float, z: float, step: float = 2.0, outer: bool = True) -> list[tuple[float, float, float]]:
    n = max(2, int(math.ceil(abs(t1 - t0) / step)) + 1)
    rr = r / math.cos(math.radians((t1 - t0) / (n - 1) / 2)) if outer else r
    out = []
    for i in range(n):
        x, y = direction(t0 + (t1 - t0) * i / (n - 1))
        out.append((rr * x, rr * y, z))
    return out


def sector(r: float, t0: float, t1: float, z0: float, z1: float) -> Manifold:
    """Pie-slice prism (convex for spans under 180 degrees)."""
    pts = [(0.0, 0.0, z0), (0.0, 0.0, z1)] + arc_points(r, t0, t1, z0) + arc_points(r, t0, t1, z1)
    return Manifold.hull_points(pts)


def element(r: float) -> Manifold:
    """Chamfered disc, round in the YZ plane and T thick along X; hulling these sweeps the slab section."""
    a = Manifold.cylinder(T - 2 * C, r, r, SEG, True)
    b = Manifold.cylinder(T, r - C, r - C, SEG, True)
    return Manifold.batch_hull([a, b]).rotate((0.0, 90.0, 0.0))


def chain(points_zy: list[tuple[float, float]], r: float) -> Manifold:
    e = element(r)
    hulls = [Manifold.batch_hull([e.translate((0.0, y0, z0)), e.translate((0.0, y1, z1))])
             for (z0, y0), (z1, y1) in zip(points_zy[:-1], points_zy[1:])]
    return union(hulls)


def closed_mesh(verts: list, tris: list, what: str) -> Manifold:
    vp = np.array(verts, dtype=np.float32)
    tv = np.array(tris, dtype=np.uint32)
    for faces in (tv, np.ascontiguousarray(tv[:, ::-1])):
        m = Manifold(mf.Mesh(vert_properties=vp, tri_verts=faces))
        if m.status() == mf.Error.NoError and m.volume() > 0:
            return m
    raise RuntimeError(f"{what}: mesh invalid")


def min_curvature_radius(path: list[tuple[float, float]]) -> float:
    p = np.array(path, float)
    best = math.inf
    for a, b, c in zip(p[:-2], p[1:-1], p[2:]):
        ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        cross = abs((b - a)[0] * (c - a)[1] - (b - a)[1] * (c - a)[0])
        if cross > 1e-12:
            best = min(best, ab * bc * ca / (2 * cross))
    return best


def sweep(path_zy: list[tuple[float, float]], r: float) -> Manifold:
    """Chamfered-rectangle section (2r in the loop plane, T across) swept along a path in the YZ plane."""
    if min_curvature_radius(path_zy) <= r + 0.5:
        raise RuntimeError("loop path bends tighter than the bar radius")
    p = np.array(path_zy, float)
    tangent = np.gradient(p, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)  # (z, y) rotated 90 degrees.
    h = T / 2
    section = [(-r, -h + C), (-r + C, -h), (r - C, -h), (r, -h + C), (r, h - C), (r - C, h), (-r + C, h), (-r, h - C)]
    verts = [(x, pz[1] + s * nz[1], pz[0] + s * nz[0]) for pz, nz in zip(p, normal) for s, x in section]
    k = len(section)
    tris = []
    for i in range(len(p) - 1):
        a, b = k * i, k * (i + 1)
        for j in range(k):
            j1 = (j + 1) % k
            tris += [(a + j, a + j1, b + j1), (a + j, b + j1, b + j)]
    last = k * (len(p) - 1)
    tris += [(0, j + 1, j) for j in range(1, k - 1)] + [(last, last + j, last + j + 1) for j in range(1, k - 1)]
    return closed_mesh(verts, tris, "loop sweep")


def catmull_rom(points: list[list[float]], spacing: float = 2.5) -> list[tuple[float, float]]:
    """Centripetal Catmull-Rom curve through the control points."""
    p = [np.array(q, float) for q in points]
    p = [2 * p[0] - p[1]] + p + [2 * p[-1] - p[-2]]
    out: list[np.ndarray] = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        t0 = 0.0
        t1 = t0 + float(np.linalg.norm(p1 - p0)) ** 0.5
        t2 = t1 + float(np.linalg.norm(p2 - p1)) ** 0.5
        t3 = t2 + float(np.linalg.norm(p3 - p2)) ** 0.5
        n = max(2, int(math.ceil(float(np.linalg.norm(p2 - p1)) / spacing)))
        for k in range(n):
            t = t1 + (t2 - t1) * k / n
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(p[-2])
    return [(round(float(q[0]), 6), round(float(q[1]), 6)) for q in out]


def loop_path(name: str) -> list[tuple[float, float]]:
    spec = H["variants"][name]
    if "circle" in spec:
        (zc, yc), rad, end_y = spec["circle"]["center"], spec["circle"]["radius"], spec["circle"]["end_y"]
        half = math.degrees(math.acos((yc - end_y) / rad))
        n = int(math.ceil(2 * math.radians(half) * rad / 2.5))
        return [(round(zc + rad * math.sin(math.radians(-half + 2 * half * k / n)), 6),
                 round(yc - rad * math.cos(math.radians(-half + 2 * half * k / n)), 6)) for k in range(n + 1)]
    return catmull_rom(spec["points"])


# ----------------------------------------------------------------------------- derived layout

R_SPIGOT = J["spigot_diameter"] / 2
R_BORE = R_SPIGOT + J["bore_clearance"] / 2
R_TIP = R_SPIGOT + J["pin_height"]
R_GROOVE = R_TIP + J["groove_radial_clearance"]
HW_PIN = math.degrees(J["pin_width"] / 2 / R_SPIGOT)
HW_SLOT = HW_PIN + math.degrees(J["slot_clearance"] / R_TIP)
D_FRONT = J["pin_center_depth"] - J["pin_axial"] / 2  # Pin face toward the mouth, depth when seated.
D_BACK = D_FRONT + J["pin_axial"]
D_GROOVE = D_BACK + J["groove_floor_clearance"]
Z_SPIGOT = L - J["spigot_length"]  # Spigot end face rests on the socket floor here.
Z_OCT0 = L + J["mouth_gap"]

AF = S["across_flats"]
X_FLAT = AF / 2 - S["print_flat"]  # Shared print flat on the shaft's +X face.
R_CASE = TIP["puck_case_diameter"] / 2
R_POCKET = R_CASE + TIP["pocket_clearance"]
R_CRADLE = R_POCKET + TIP["wall"]
R_CAP = R_CRADLE + CAP["wall"]
Y_BOT = -AF / 2
Y_FLOOR = Y_BOT + TIP["floor"]
Y_CASE_TOP = Y_FLOOR + TIP["puck_case_height"]
Y_RIM = Y_CASE_TOP - TIP["case_above_rim"]
Z_TIP = D["overall"]["length"] - R_CAP  # Puck centre.
Z_HALF_FRONT = Z_TIP - R_CAP - TIP["cap_gap"]
Z_TONGUE = Z_HALF_FRONT - TIP["tongue_length"]
GAP_FACE, GAP_END, LAP = S["lap_face_gap"], S["lap_end_gap"], S["lap_length"]
Z_LAP = (Z_SPIGOT + Z_HALF_FRONT) / 2
POD_Y0 = H["spine_radius"]
POD_Z1 = POD["front_z"]
POD_Z0 = POD_Z1 - POD["length"]
BUTTONS = {"bottom": (POD_Z0 + POD_Z1) / 2 - POD["button_pitch"],
           "middle": (POD_Z0 + POD_Z1) / 2,
           "top": (POD_Z0 + POD_Z1) / 2 + POD["button_pitch"]}
Z_RETAIN = POD_Z0 + POD["end_wall"] / 2
RAIL = POD["rail"]


def rail_polygon(grow: float = 0.0) -> list[tuple[float, float]]:
    """45-degree dovetail on the spine's top face, extended into the spine for overlap."""
    y0, h, top = POD_Y0, RAIL["height"], RAIL["top"] / 2
    below = 1.0
    poly = [(-(top - h - below), y0 - below), (top - h - below, y0 - below), (top, y0 + h), (-top, y0 + h)]
    if not grow:
        return poly
    return CrossSection([poly]).offset(grow, mf.JoinType.Miter).to_polygons()[0].tolist()


# ----------------------------------------------------------------------------- joint

def cam_pieces(lock: float, crest: float) -> list[tuple[float, float, float, float]]:
    """(angle0, angle1, gap0, gap1) along one groove. Positive gap is clearance, negative is interference."""
    cam = J["cam"]
    entry = lock - J["twist"]
    a = entry + HW_SLOT
    pocket = lock - HW_PIN - 0.1  # The pocket starts just behind a locked pin's trailing edge.
    ridge = pocket - cam["ridge"]
    ramp = a + cam["ramp_start"] * (ridge - a)
    g = cam["entry_gap"]
    return [(entry - HW_SLOT, ramp, g, g), (ramp, ridge, g, -crest), (ridge, pocket, -crest, -crest),
            (pocket, lock + HW_SLOT, -cam["pocket_interference"], -cam["pocket_interference"])]


def groove_stations(lock: float, crest: float) -> list[tuple[float, float]]:
    """(angle, ceiling z) along one groove; the ceiling is the retaining wall's underside."""
    step = J["step_degrees"]
    out: list[tuple[float, float]] = []
    for t0, t1, g0, g1 in cam_pieces(lock, crest):
        if t1 - t0 <= 1e-6:
            continue
        n = max(1, int(math.ceil((t1 - t0) / step)))
        for k in range(n + 1):
            t, g = t0 + (t1 - t0) * k / n, g0 + (g1 - g0) * k / n
            if out and abs(t - out[-1][0]) < 1e-9:
                if abs(L - (D_FRONT - g) - out[-1][1]) < 1e-9:
                    continue
                t += 0.02  # A step in the ceiling: keep stations distinct.
            out.append((t, L - (D_FRONT - g)))
    return out


def swept_groove(stations: list[tuple[float, float]]) -> Manifold:
    """Closed ring-segment mesh: constant floor and radii, ceiling height varying by angle."""
    r_in, r_out, zf = R_BORE - 0.3, R_GROOVE, L - D_GROOVE
    verts = []
    for t, zt in stations:
        x, y = direction(t)
        verts += [(r_in * x, r_in * y, zf), (r_out * x, r_out * y, zf), (r_out * x, r_out * y, zt), (r_in * x, r_in * y, zt)]
    tris = []
    for i in range(len(stations) - 1):
        a, b = 4 * i, 4 * (i + 1)
        for k in range(4):
            k1 = (k + 1) % 4
            tris += [(a + k, a + k1, b + k1), (a + k, b + k1, b + k)]
    last = 4 * (len(stations) - 1)
    tris += [(0, 3, 2), (0, 2, 1), (last, last + 1, last + 2), (last, last + 2, last + 3)]
    return closed_mesh(verts, tris, "groove")


def socket_void(crest: float) -> Manifold:
    """Everything removed from a handle (or female coupon) for the twist-lock socket and wiring."""
    voids = [cyl_z(R_BORE, Z_SPIGOT, L + 1.0),
             teardrop_z(R_BORE, Z_SPIGOT, L + 1.0, 90.0, H["teardrop_flat"]),
             cyl_z(R_BORE, L - J["lead_in"], L + 0.01, R_BORE + J["lead_in"] + 0.01)]
    for lock in J["pin_angles"]:
        entry = lock - J["twist"]
        voids.append(sector(R_GROOVE, entry - HW_SLOT, entry + HW_SLOT, L - D_GROOVE, L + 1.0))
        voids.append(swept_groove(groove_stations(lock, crest)))
    floor_z = Z_SPIGOT - H["socket_floor"]
    bay_z = floor_z - H["bay_length"]
    voids += [teardrop_z(H["floor_hole_diameter"] / 2, floor_z - 0.5, Z_SPIGOT + 0.5, 90.0),
              teardrop_z(H["bay_diameter"] / 2, bay_z, floor_z, 90.0, H["teardrop_flat"]),
              teardrop_z(H["channel_diameter"] / 2, H["channel_rear"], bay_z + 1.0, 90.0),
              teardrop_y(H["rail_wire_hole"]["diameter"] / 2, 0.0, POD_Y0 + RAIL["height"] + 0.5, H["rail_wire_hole"]["z"]),
              cyl_y(POD["retaining_pin_diameter"] / 2, POD_Y0 - 4.0, POD_Y0 + RAIL["height"] + 0.5, z=Z_RETAIN)]
    return union(voids)


def spigot_end() -> Manifold:
    """Male half of the joint, on the lower shaft, in assembly position (locked)."""
    lead = J["spigot_chamfer"]
    # The spigot stops at the mouth; a slimmer neck joins the octagon so the round spigot never
    # sits exactly tangent inside the octagon's flats (that tangency makes a degenerate union).
    parts = [cyl_z(R_SPIGOT - lead, Z_SPIGOT, Z_SPIGOT + lead, R_SPIGOT), cyl_z(R_SPIGOT, Z_SPIGOT + lead, L),
             cyl_z(R_SPIGOT - 0.3, L - 0.1, Z_OCT0 + 1.0)]
    z_lead = L - J["pin_center_depth"] - J["pin_axial"] / 2
    z_back = z_lead + J["pin_axial"]
    ch = J["pin_lead_chamfer"]
    for lock in J["pin_angles"]:
        pts = []
        for r, z in ((J["pin_root"], z_lead), (J["pin_root"], z_back), (R_TIP - ch, z_lead), (R_TIP, z_lead + ch), (R_TIP, z_back)):
            pts += arc_points(r, lock - HW_PIN, lock + HW_PIN, z, step=4.0, outer=False)
        parts.append(Manifold.hull_points(pts))
    return union(parts)


# ----------------------------------------------------------------------------- parts (assembly frame)

def has_loop(variant: str) -> bool:
    return "grip_radius" not in H["variants"][variant]


def rounded_spine(radius: float) -> Manifold:
    """No-loop grip: round section printed on its side. The -X side is a flat on the bed, reached by
    45-degree tangent faces so the rounded underside needs no support. The butt is rounded in side view."""
    flat = T / 2  # Same bed plane as the slab handles, so the rail stop still reaches the bed.
    t = radius / math.sqrt(2)
    a = 2 * t - flat
    seat = RAIL["top"] / 2 - 2.0  # Flat on top where the rail sits, so the wire hole stays inside the rail.
    profile = (CrossSection.circle(radius, SEG) + CrossSection([[(0.0, 0.0), (-flat, a), (-flat, -a)]])
               + CrossSection([[(0.0, 0.0), (seat, radius), (-seat, radius)]])).hull()
    profile = profile ^ CrossSection.square((2 * radius + flat + 2, 2 * radius + 2)).translate((-flat, -radius - 1))
    body = Manifold.extrude(profile, L)
    side = CrossSection.circle(radius, SEG).translate((radius, 0.0)) + CrossSection.square((L, 2 * radius + 2)).translate((radius, -radius - 1))
    # Side-view outline (local x = wand Z, local y = wand Y) extruded across the grip along -X.
    end = Manifold.extrude(side, 2 * radius + 4).transform(np.array([[0.0, 0.0, -1.0, radius + 2],
                                                                     [0.0, 1.0, 0.0, 0.0],
                                                                     [1.0, 0.0, 0.0, 0.0]]))
    return body ^ end


def handle(variant: str | None, z_from: float | None = None, crest: float | None = None, marks: int = 0) -> Manifold:
    r = H["spine_radius"]
    if variant and not has_loop(variant):
        solid = [rounded_spine(H["variants"][variant]["grip_radius"])]
    else:
        solid = [chain([(r, 0.0), (L + r, 0.0)], r).trim_by_plane((0.0, 0.0, -1.0), -L)]
    if variant and has_loop(variant):
        solid.append(sweep(loop_path(variant), H["loop_radius"]))
    solid.append(prism_z(rail_polygon(), RAIL["rear_z"], POD_Z1 + 0.5))
    # Pod stop: full slab width so it stands on the bed when the handle prints on its side.
    solid.append(box(-T / 2, T / 2, POD_Y0 - C, POD_Y0 + POD["height"] - 4.0, POD_Z1, POD_Z1 + POD["stop_length"]))
    body = union(solid)
    if z_from is not None:
        body = body.trim_by_plane((0.0, 0.0, 1.0), z_from)
    body = body - socket_void(J["cam"]["crest_interference"] if crest is None else crest)
    for k in range(marks):  # Variant marks on a coupon's back face.
        x = -4.0 + 4.0 * k
        body = body - box(x - 0.75, x + 0.75, -r - 1.0, -r + 1.5, z_from - 1.0, z_from + 1.5)
    return body


def octagon_prism(z0: float, z1: float, keep: str = "full") -> Manifold:
    m = prism_z(octagon(AF), z0, z1)
    if keep == "low":
        m = m.trim_by_plane((0.0, -1.0, 0.0), GAP_FACE / 2)
    elif keep == "high":
        m = m.trim_by_plane((0.0, 1.0, 0.0), GAP_FACE / 2)
    return m


def shaft_finish(m: Manifold, z0: float, z1: float) -> Manifold:
    m = m.trim_by_plane((-1.0, 0.0, 0.0), -X_FLAT)
    return m - teardrop_z(S["wire_bore"] / 2, z0 - 1.0, z1 + 1.0, 270.0)


def shaft_lower(z_to: float | None = None) -> Manifold:
    if z_to is not None:  # Male coupon: spigot plus a short stub.
        return shaft_finish(union([spigot_end(), octagon_prism(Z_OCT0, z_to)]), Z_SPIGOT, z_to)
    lap0, lap1 = Z_LAP - LAP / 2, Z_LAP + LAP / 2
    body = union([spigot_end(), octagon_prism(Z_OCT0, lap0 - GAP_END), octagon_prism(lap0 - GAP_END, lap1, "low")])
    return shaft_finish(body, Z_SPIGOT, lap1)


def shaft_upper() -> Manifold:
    lap0, lap1 = Z_LAP - LAP / 2, Z_LAP + LAP / 2
    front = Z_TONGUE - GAP_END
    body = union([octagon_prism(lap0, lap1 + GAP_END, "high"), octagon_prism(lap1 + GAP_END, front),
                  octagon_prism(front, Z_HALF_FRONT, "high")])
    return shaft_finish(body, lap0, Z_HALF_FRONT)


def tip_cradle() -> Manifold:
    tongue = octagon_prism(Z_TONGUE, Z_TIP, "low").trim_by_plane((-1.0, 0.0, 0.0), -X_FLAT)
    body = union([cyl_y(R_CRADLE, Y_BOT, Y_RIM - 0.5, z=Z_TIP), cyl_y(R_CRADLE, Y_RIM - 0.5, Y_RIM, z=Z_TIP, r1=R_CRADLE - 0.5),
                  tongue])
    w = TIP["notch_width"] / 2
    rn = TIP["thumb_notch_radius"]
    voids = [cyl_y(R_POCKET, Y_FLOOR, Y_RIM + 1.0, z=Z_TIP),
             teardrop_z(S["wire_bore"] / 2, Z_TONGUE - 1.0, Z_TIP - R_POCKET + 1.0, 270.0),
             box(-w, w, -S["wire_bore"] / 2, Y_RIM + 1.0, Z_TIP - R_CRADLE - 1.0, Z_TIP - R_POCKET + 1.0),
             cyl_z(rn, Z_TIP - 7.0, Z_TIP + 7.0, x=R_POCKET + TIP["wall"] / 2, y=Y_RIM + 1.0),
             cyl_z(rn, Z_TIP - 7.0, Z_TIP + 7.0, x=-(R_POCKET + TIP["wall"] / 2), y=Y_RIM + 1.0),
             Manifold.cube((1.6, 3.0, 1.6), True).rotate((0.0, 45.0, 0.0)).translate((0.0, Y_RIM, Z_TIP + R_CRADLE))]
    return body - union(voids)


def tip_cap() -> Manifold:
    y_lip = Y_CASE_TOP - CAP["squeeze"]
    y_top = y_lip + CAP["lip"]
    outer = union([cyl_y(R_CAP, CAP["skirt_bottom_y"], y_top - 0.8, z=Z_TIP), cyl_y(R_CAP, y_top - 0.8, y_top, z=Z_TIP, r1=R_CAP - 0.8)])
    voids = [cyl_y(R_CRADLE - CAP["fit_interference"] / 2, CAP["skirt_bottom_y"] - 1.0, y_lip, z=Z_TIP),
             cyl_y(R_CASE - CAP["lip_overlap"], y_lip - 1.0, y_top + 1.0, z=Z_TIP),
             box(-4.0, 4.0, CAP["skirt_bottom_y"] - 1.0, CAP["skirt_bottom_y"] + 1.5, Z_TIP + R_CRADLE - 1.0, Z_TIP + R_CAP + 1.0)]
    return outer - union(voids)


def puck_dummy() -> Manifold:
    """Stock-case envelope used only for interference checks; not exported for printing."""
    return cyl_y(R_CASE, Y_FLOOR, Y_CASE_TOP, z=Z_TIP)


def pod(pilots: bool) -> Manifold:
    y0, h, w = POD_Y0, POD["height"], POD["width"] / 2
    y1 = y0 + h
    outline = [(-w, y0), (w, y0), (w, y1 - 2.0), (w - 2.0, y1), (-(w - 2.0), y1), (-w, y1 - 2.0)]
    body = prism_z(outline, POD_Z0, POD_Z1)
    cw = POD["cavity_width"] / 2
    voids = [prism_z(rail_polygon(RAIL["clearance"]), POD_Z0 - 1.0, POD_Z1 + 1.0),
             box(-cw, cw, y0 + RAIL["height"], y1 - POD["top_skin"], POD_Z0 + POD["end_wall"], POD_Z1 - POD["end_wall"]),
             cyl_y(POD["retaining_pin_diameter"] / 2, y0 + 1.0, y1 + 1.0, z=Z_RETAIN)]
    if pilots:
        voids += [cyl_y(POD["pilot_diameter"] / 2, y1 - POD["top_skin"] - 0.5, y1 + 1.0, z=z) for z in BUTTONS.values()]
    return body - union(voids)


# XIAO tip (current profile). It reuses the Puck tip's tongue, so the unchanged upper shaft laps
# over it exactly as before; only the part in front of the shaft differs.
XT = D["xiao_tip"]
Z_DECK0 = Z_HALF_FRONT + XT["shaft_gap"]
Z_BOARD0 = Z_DECK0 + XT["rear_wall"] + XT["clearance"]
Z_BOARD1 = Z_BOARD0 + XT["board_length"]
Z_DECK1 = Z_BOARD1 - XT["usb_setback"]  # Deck stops short of the USB end so a plug isn't blocked.
Y_DECK = XT["deck_top_y"]
HALF_POCKET = XT["board_width"] / 2 + XT["clearance"]
HALF_DECK = HALF_POCKET + XT["lip_wall"]


def tip_xiao() -> Manifold:
    """Open U-shaped deck for a bare XIAO board: low side lips locate it, tape through the side
    notches holds it, the rear wall stops it and passes the wires. No battery holder."""
    tongue = octagon_prism(Z_TONGUE, Z_DECK0 + 1.0, "low").trim_by_plane((-1.0, 0.0, 0.0), -X_FLAT)
    solid = [tongue,
             box(-HALF_DECK, HALF_DECK, Y_BOT, Y_DECK, Z_DECK0, Z_DECK1),
             box(-HALF_DECK, HALF_DECK, Y_DECK - 0.1, Y_DECK + XT["rear_wall_height"], Z_DECK0, Z_BOARD0 - XT["clearance"])]
    for side in (-1.0, 1.0):
        x0, x1 = sorted((side * HALF_POCKET, side * HALF_DECK))
        solid.append(box(x0, x1, Y_DECK - 0.1, Y_DECK + XT["lip_height"], Z_DECK0, Z_DECK1))
    body = union(solid)
    w, n = XT["wire_slot_width"] / 2, XT["tape_notch"]
    ri = XT["relief_inset"]
    voids = [teardrop_z(S["wire_bore"] / 2, Z_TONGUE - 1.0, Z_DECK0 + 2.0, 270.0),
             box(-w, w, -S["wire_bore"] / 2, Y_DECK + XT["rear_wall_height"] + 1.0, Z_HALF_FRONT - 1.0, Z_BOARD0 + 3.0),
             box(-XT["board_width"] / 2 + ri, XT["board_width"] / 2 - ri, Y_DECK - XT["relief_depth"], Y_DECK + 0.1,
                 Z_BOARD0 + ri, Z_BOARD1 - ri)]
    for f in n["at"]:
        zc = Z_BOARD0 + f * XT["board_length"]
        for side in (-1.0, 1.0):
            x0, x1 = sorted((side * (HALF_DECK - n["depth"]), side * (HALF_DECK + 1.0)))
            voids.append(box(x0, x1, Y_BOT - 1.0, Y_DECK + 2.0, zc - n["width"] / 2, zc + n["width"] / 2))
    return body - union(voids)


def xiao_board() -> Manifold:
    """Reference only: the documented 21 x 17.8 mm outline with a provisional PCB thickness."""
    return box(-XT["board_width"] / 2, XT["board_width"] / 2, Y_DECK, Y_DECK + XT["pcb_thickness"], Z_BOARD0, Z_BOARD1)


def xiao_envelope() -> Manifold:
    """Reference only: provisional space for components above the board, kept clear of every part."""
    top = Y_DECK + XT["pcb_thickness"]
    return box(-XT["board_width"] / 2, XT["board_width"] / 2, top, top + XT["component_clearance"], Z_BOARD0, Z_BOARD1)


def puck_ring() -> Manifold:
    """Print-frame coupon: the pocket and rim of the tip cradle, to test the stock case fit."""
    h = CPN["puck_ring_height"]
    return cyl_z(R_CRADLE, 0.0, h) - cyl_z(R_POCKET, 1.2, h + 1.0) - cyl_z(R_POCKET - 3.0, -1.0, 2.0)


# ----------------------------------------------------------------------------- part registry

ORIENT = {  # Assembly -> print rotation (degrees about one axis) and its meaning.
    "x-down": ((0.0, 90.0, 0.0), "Lying on the flat +X face"),
    "x-up": ((0.0, -90.0, 0.0), "Lying on its side (-X face down), loop flat on the bed"),
    "x-up-grip": ((0.0, -90.0, 0.0), "Lying on its side on the -X bed flat, rail sideways"),
    "y-up": ((90.0, 0.0, 0.0), "Pocket opening up"),
    "y-down": ((-90.0, 0.0, 0.0), "Top face down"),
    "as-is": ((0.0, 0.0, 0.0), "Flat, as modelled"),
}
V = CPN["female_variants"]
PARTS = [  # (name, builder, orientation, group, role). Order is the suggested print order.
    ("coupon-male", lambda: shaft_lower(Z_OCT0 + CPN["male_stub"]), "x-down", "coupon", "Joint coupon: shaft spigot with the three locking pins"),
    ("coupon-female-a", lambda: handle(None, L - CPN["female_length"], V["a"], 1), "x-up", "coupon", f"Joint coupon: handle socket, {V['a']} mm cam interference, 1 notch"),
    ("coupon-female-b", lambda: handle(None, L - CPN["female_length"], V["b"], 2), "x-up", "coupon", f"Joint coupon: handle socket, {V['b']} mm cam interference (default), 2 notches"),
    ("coupon-female-c", lambda: handle(None, L - CPN["female_length"], V["c"], 3), "x-up", "coupon", f"Joint coupon: handle socket, {V['c']} mm cam interference, 3 notches"),
    ("coupon-puck-ring", puck_ring, "as-is", "coupon", "Puck pocket coupon: tip cradle pocket and rim"),
    ("handle-round", lambda: handle("round"), "x-up", "handle", H["variants"]["round"]["grip"]),
    ("handle-oval", lambda: handle("oval"), "x-up", "handle", H["variants"]["oval"]["grip"]),
    ("handle-angled", lambda: handle("angled"), "x-up", "handle", H["variants"]["angled"]["grip"]),
    ("handle-straight", lambda: handle("straight"), "x-up-grip", "handle", H["variants"]["straight"]["grip"]),
    ("shaft-lower", shaft_lower, "x-down", "shaft", "Lower shaft: twist-lock spigot and half-lap"),
    ("shaft-upper", shaft_upper, "x-down", "shaft", "Upper shaft: half-laps to the lower shaft and the tip"),
    ("tip-cradle", tip_cradle, "y-up", "tip", "Tip cradle for the stock Puck.js case"),
    ("tip-cap", tip_cap, "y-down", "tip", "Removable cap ring; light and Puck button stay uncovered"),
    ("tip-xiao", tip_xiao, "y-up", "tip", "Open deck for a bare XIAO board, taped on; USB end uncovered, no battery holder"),
    ("button-pod-pilot", lambda: pod(True), "y-down", "pod", "Button carrier with 2 mm pilot holes at the button centres"),
    ("button-pod-blank", lambda: pod(False), "y-down", "pod", "Button carrier with no holes, to mark and drill by hand"),
]
SUPPORTS = {
    "coupon-male": "Support under pin overhangs; Bambu Studio flags floating regions without it",
    "coupon-female-a": "Support at rail/socket overhangs; remove completely before fitting",
    "coupon-female-b": "Support at rail/socket overhangs; remove completely before fitting",
    "coupon-female-c": "Support at rail/socket overhangs; remove completely before fitting",
    "coupon-puck-ring": "None",
    "handle-round": "Support at rail/socket overhangs; Bambu Studio flags a floating cantilever without it",
    "handle-oval": "Support at rail/socket overhangs; Bambu Studio flags a floating cantilever without it",
    "handle-angled": "Support at rail/socket overhangs; Bambu Studio flags a floating cantilever without it",
    "handle-straight": "45-degree grip underside; support at shared rail/socket overhangs",
    "shaft-lower": "Support under small pin overhangs", "shaft-upper": "None expected",
    "tip-cradle": "None expected", "tip-cap": "None", "tip-xiao": "None expected; not yet sliced", "button-pod-pilot": "None expected", "button-pod-blank": "None expected",
}
# Profiles pair a tip with handles. Ethan's "mug" handle is handle-round (the mug-style loop) and
# "without the handle" means the plain no-loop grip, handle-straight; both keep the same socket.
PROFILES = D["profiles"]
CURRENT = PROFILES["current"]
PROFILE_NAMES = [k for k in PROFILES if k != "current"]
SHARED_PARTS = ["button-pod-pilot", "shaft-lower", "shaft-upper"]
PART_PROFILES = {"tip-cradle": "puck-legacy", "tip-cap": "puck-legacy", "coupon-puck-ring": "puck-legacy", "tip-xiao": "xiao"}
COLORS = {"handle": (124, 108, 240), "button-pod-pilot": (240, 163, 92), "shaft-lower": (70, 64, 96), "shaft-upper": (70, 64, 96),
          "tip-cradle": (217, 212, 232), "tip-cap": (183, 174, 240), "tip-xiao": (217, 212, 232),
          "puck-case": (236, 232, 244), "xiao-board": (64, 160, 110)}
REFERENCES = {"puck-case": lambda: puck_dummy(), "xiao-board": lambda: xiao_board()}


def assemblies() -> dict[str, dict]:
    """Every (profile, handle) pairing, keyed profile-key, e.g. xiao-mug."""
    out = {}
    for profile in PROFILE_NAMES:
        spec = PROFILES[profile]
        for key, a in spec["assemblies"].items():
            out[f"{profile}-{key}"] = {"label": a["label"], "profile": profile, "handle": a["handle"],
                                      "parts": [f"handle-{a['handle']}"] + SHARED_PARTS + spec["tip_parts"],
                                      "reference": spec["reference"]}
    return out


def rotation(deg: tuple[float, float, float]) -> np.ndarray:
    ax = [i for i, a in enumerate(deg) if a]
    if not ax:
        return np.eye(3)
    assert len(ax) == 1, "single-axis print rotations only"
    i, a = ax[0], math.radians(deg[ax[0]])
    c, s = round(math.cos(a), 12), round(math.sin(a), 12)
    return [np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])][i].astype(float)


def canonical_triangles(m: Manifold) -> np.ndarray:
    """Triangle soup in a canonical order, so identical geometry always writes identical bytes."""
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    t = np.asarray(mesh.tri_verts, dtype=np.int64)
    # Booleans can leave collapsed triangles whose corners coincide. Merge coincident corners
    # and drop those triangles; their two remaining edges cancel, so the surface stays closed.
    grid = np.round(v * 1e4).astype(np.int64)
    points, inverse = np.unique(grid, axis=0, return_inverse=True)
    f = inverse.reshape(-1)[t]
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    tri = (points[f] / 1e4).astype(np.float32)
    q = tri.astype(np.float64)
    rows = np.arange(len(q))

    def less(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return (a[:, 0] < b[:, 0]) | ((a[:, 0] == b[:, 0]) & ((a[:, 1] < b[:, 1]) | ((a[:, 1] == b[:, 1]) & (a[:, 2] < b[:, 2]))))

    first = np.zeros(len(q), dtype=np.int64)
    for k in (1, 2):
        first = np.where(less(q[:, k], q[rows, first]), k, first)
    tri = tri[rows[:, None], (first[:, None] + np.arange(3)[None, :]) % 3]
    return tri[np.lexsort(tri.reshape(len(tri), 9).T[::-1])]


def stl_bytes(tri: np.ndarray, name: str) -> bytes:
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]).astype(np.float64)
    length = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.where(length > 0, n / np.maximum(length, 1e-30), 0.0)
    rec = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    header = f"printed-loop-wand {name} (mm)".encode("ascii").ljust(80, b" ")
    return header + struct.pack("<I", len(tri)) + rec.tobytes()


def build_parts() -> dict:
    out = {}
    for name, builder, orient, group, role in PARTS:
        m = builder()
        if m.status() != mf.Error.NoError:
            raise RuntimeError(f"{name}: {m.status()}")
        rot, meaning = ORIENT[orient]
        p = m.rotate(rot) if any(rot) else m
        x0, y0, z0, x1, y1, z1 = p.bounding_box()
        shift = np.array([-(x0 + x1) / 2, -(y0 + y1) / 2, -z0])
        p = p.translate(tuple(shift))
        r = rotation(rot)
        to_assembly = np.eye(4)
        to_assembly[:3, :3] = r.T
        to_assembly[:3, 3] = -r.T @ shift
        out[name] = {"assembly": m, "print": p, "tri": canonical_triangles(p), "group": group, "role": role,
                     "orientation": meaning, "to_assembly": to_assembly}
    return out


# ----------------------------------------------------------------------------- checks

def r4(x: float) -> float:
    return round(float(x), 4)


def mesh_checks(tri: np.ndarray, bodies: int) -> dict:
    import trimesh
    n = len(tri)
    tm = trimesh.Trimesh(vertices=tri.reshape(-1, 3).astype(np.float64), faces=np.arange(3 * n).reshape(-1, 3), process=True)
    edges = np.sort(tm.edges, axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    normals = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]).astype(np.float64)
    area2 = np.linalg.norm(normals, axis=1)
    nz = np.where(area2 > 0, normals[:, 2] / np.maximum(area2, 1e-30), 0.0)
    lifted = tri[:, :, 2].mean(axis=1) > 0.2
    flat = lifted & (nz < -0.999)
    steep = lifted & ~flat & (nz < -math.cos(math.radians(45)) - 0.01)
    lo, hi = tri.reshape(-1, 3).min(axis=0), tri.reshape(-1, 3).max(axis=0)
    return {
        "watertight": bool(tm.is_watertight), "winding_consistent": bool(tm.is_winding_consistent),
        "every_edge_shared_twice": bool((counts == 2).all()), "bodies": bodies,
        "volume_mm3": r4(tm.volume), "area_mm2": r4(tm.area), "triangles": n,
        "print_size_mm": [r4(v) for v in (hi - lo)],
        "downward_flat_mm2": r4(area2[flat].sum() / 2), "downward_steeper_than_45_mm2": r4(area2[steep].sum() / 2),
    }


def overlap(a: Manifold, b: Manifold, zone: tuple[float, float] | None = None) -> tuple[float, float]:
    """Intersection volume and its thickness along the wand axis, optionally within a Z band."""
    i = a ^ b
    if zone is not None:
        i = i ^ box(-50.0, 50.0, -50.0, 50.0, zone[0], zone[1])
    v = i.volume()
    if v <= 1e-6:
        return 0.0, 0.0
    bb = i.bounding_box()
    return r4(v), r4(bb[5] - bb[2])


def joint_checks() -> dict:
    male = shaft_lower(Z_OCT0 + CPN["male_stub"])
    female = {k: handle(None, L - CPN["female_length"], c) for k, c in V.items()}
    tw = J["twist"]
    crest = J["cam"]["crest_interference"]
    fb = female["b"]

    def pose(angle: float, lift: float) -> Manifold:
        return spin(male, angle).translate((0.0, 0.0, lift))

    pins = (L - D_GROOVE - 0.5, L - 0.2)  # Pin and groove band, clear of the floor contact.

    insertion = [overlap(pose(-tw, d), fb)[0] for d in np.arange(0.0, J["spigot_length"] + 1.0, 0.5)]
    turn = [(a, *overlap(pose(a, 0.0), fb, pins)) for a in range(-tw, 1)]
    pulled = overlap(pose(0.0, 0.6), fb)[0]
    over = overlap(pose(6.0, 0.0), fb)[0]
    backed = overlap(pose(-tw + 2, 2.0), fb)[0]
    open_angles = [a for a in range(-180, 180, 2) if overlap(pose(a, 3.0), fb)[0] < 0.05]
    locked = {k: overlap(pose(0.0, 0.0), f, pins) for k, f in female.items()}
    floor = overlap(pose(0.0, 0.0), fb, (Z_SPIGOT - 1.0, Z_SPIGOT + 1.0))[0]
    result = {
        "insertion_at_entry_angle_max_mm3": max(insertion),
        "twist_max_overlap_mm3": max(t[1] for t in turn),
        "twist_max_axial_overlap_mm": max(t[2] for t in turn),
        "twist_profile": [{"angle": a, "overlap_mm3": v, "axial_mm": z} for a, v, z in turn],
        "locked_pull_out_0_6mm_overlap_mm3": pulled,
        "over_twist_6deg_overlap_mm3": over,
        "locked_overlap_by_coupon": {k: {"overlap_mm3": v, "axial_mm": z} for k, (v, z) in locked.items()},
        "floor_contact_overlap_mm3": floor,
        "partly_inserted_2deg_off_entry_overlap_mm3": backed,
        "insertable_angles_deg": open_angles,
        "entry_angle_deg": -tw,
    }
    result["passed"] = bool(
        result["insertion_at_entry_angle_max_mm3"] < 0.01
        and result["twist_max_axial_overlap_mm"] <= crest + 0.02
        and pulled > 1.0 and over > 1.0 and backed < 0.01 and floor < 0.01
        and all(z <= J["cam"]["pocket_interference"] + 0.01 for _, z in locked.values())
        and open_angles and all(abs(a + tw) <= 4 for a in open_angles))
    return result


def wire_probe(profile: str = "puck-legacy", radius: float = 1.5) -> Manifold:
    y_pod = POD_Y0 + RAIL["height"] + 2.0
    zw = H["rail_wire_hole"]["z"]
    low = -S["wire_bore"] / 2 + radius + 0.1  # Along the groove floor under the cap skirt.
    if profile == "xiao":  # From above the board's rear edge, down through the rear-wall slot.
        y_over = Y_DECK + XT["pcb_thickness"] + XT["component_clearance"] + radius + 0.2
        z_drop = Z_DECK0 + radius + 0.1  # Drops just in front of the shaft's end, then runs back in the groove.
        start = [(0, y_over, Z_BOARD0 + 2), (0, y_over, z_drop), (0, low, z_drop)]
    else:
        start = [(0, low, Z_TIP - 14)]
    pts = start + [(0, low, Z_TONGUE + 4), (0, 0, Z_LAP), (0, 0, Z_SPIGOT - 1), (0, 0, L - 30),
                   (0, 0, zw), (0, y_pod, zw), (0, y_pod, BUTTONS["top"])]
    ball = Manifold.sphere(radius, 24)
    return union([Manifold.batch_hull([ball.translate(a), ball.translate(b)]) for a, b in zip(pts[:-1], pts[1:])])


def opening(m: Manifold) -> dict:
    """Finger opening of a handle, from its mid-plane section."""
    polys = m.rotate((0.0, -90.0, 0.0)).slice(0.0).to_polygons()

    def area(p: np.ndarray) -> float:
        x, y = p[:, 0], p[:, 1]
        return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    holes = sorted((p for p in polys if area(p) < 0), key=area)
    if not holes:
        return {}
    h = holes[0]
    return {"length_mm": r4(h[:, 0].max() - h[:, 0].min()), "height_mm": r4(h[:, 1].max() - h[:, 1].min()), "area_mm2": r4(-area(h))}


def assembly_checks(parts: dict) -> dict:
    expected = {("handle", "shaft-lower"): "Cam pocket preload", ("tip-cradle", "tip-cap"): "Cap press fit"}
    probes = {profile: wire_probe(profile) for profile in PROFILE_NAMES}
    refs = {"puck-case": puck_dummy(), "xiao-board": xiao_board(), "xiao-components": xiao_envelope()}
    out = {}
    for aid, a in assemblies().items():
        variant, probe = a["handle"], probes[a["profile"]]
        solids = {"handle": parts[f"handle-{variant}"]["assembly"]}
        solids.update({("pod" if n == "button-pod-pilot" else n): parts[n]["assembly"] for n in a["parts"][1:]})
        if a["reference"] == "xiao-board":
            solids["xiao-board"], solids["xiao-components"] = refs["xiao-board"], refs["xiao-components"]
        else:
            solids["puck-case"] = refs["puck-case"]
        pairs, unexpected = {}, []
        keys = list(solids)
        for i, x in enumerate(keys):
            for y in keys[i + 1:]:
                v, _ = overlap(solids[x], solids[y])
                label = expected.get((x, y))
                pairs[f"{x} + {y}"] = v
                if v >= 0.01 and not label:
                    unexpected.append(f"{x} + {y}")
        wires = {k: overlap(probe, s)[0] for k, s in solids.items() if k not in REFERENCES and k != "xiao-components"}
        out[aid] = {"label": a["label"], "profile": a["profile"], "handle": variant,
                    "overlaps_mm3": pairs, "expected_overlaps": {f"{x} + {y}": t for (x, y), t in expected.items() if x in solids and y in solids},
                        "unexpected": unexpected, "wire_probe_overlap_mm3": wires,
                        "opening": opening(solids["handle"]) if has_loop(variant) else None,
                        "passed": not unexpected and all(v < 0.01 for v in wires.values())}
    return out


# ----------------------------------------------------------------------------- outputs

def glb_bytes(parts: dict, profile: str) -> bytes:
    import trimesh
    scene = trimesh.Scene()

    def make(name: str, solid: Manifold, color: tuple[int, int, int]) -> "trimesh.Trimesh":
        tri = canonical_triangles(solid)
        n = len(tri)
        mesh = trimesh.Trimesh(vertices=tri.reshape(-1, 3).astype(np.float64) * 0.001, faces=np.arange(3 * n).reshape(-1, 3), process=True)
        mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            name=name, baseColorFactor=[*color, 255], metallicFactor=0.0, roughnessFactor=0.7))
        return mesh

    solids = {name: parts[name]["assembly"] for name in parts}
    for ref, make_ref in REFERENCES.items():
        solids[f"{ref}-reference"] = make_ref()
    chosen = [(aid, a) for aid, a in assemblies().items() if a["profile"] == profile]
    for k, (aid, a) in enumerate(chosen):
        offset = np.eye(4)
        offset[1, 3] = -0.13 * k  # Assemblies stacked 130 mm apart, so a side view shows each handle.
        items = [(n, COLORS["handle"] if n.startswith("handle-") else COLORS[n]) for n in a["parts"]]
        items.append((f"{a['reference']}-reference", COLORS[a["reference"]]))
        for name, color in items:
            node = f"{aid}/{name}"
            if name not in scene.geometry:
                scene.add_geometry(make(name, solids[name], color), geom_name=name, node_name=node, transform=offset)
            else:
                scene.graph.update(frame_to=node, frame_from=scene.graph.base_frame, matrix=offset, geometry=name)
    return scene.export(file_type="glb")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(run_checks: bool = True) -> tuple[dict[str, bytes], dict]:
    import trimesh
    parts = build_parts()
    files: dict[str, bytes] = {}
    entries = []
    margin = D["printer_reference"]["margin"]
    bed = D["printer_reference"]["bed"]
    for name, *_ in PARTS:
        p = parts[name]
        data = stl_bytes(p["tri"], name)
        files[f"{name}.stl"] = data
        checks = mesh_checks(p["tri"], len(p["print"].decompose()))
        fits = all(s <= b - 2 * margin for s, b in zip(checks["print_size_mm"], bed))
        entries.append({
            "name": name, "file": f"{name}.stl", "sha256": sha256(data), "bytes": len(data), "group": p["group"],
            "role": p["role"], "profile": PART_PROFILES.get(name, "shared"), "print_orientation": p["orientation"], "supports": SUPPORTS[name],
            "fits_bed": fits, "mesh": checks,
            "print_to_assembly": [[r4(v) for v in row] for row in p["to_assembly"].tolist()],
        })
    glbs = {}
    for profile in PROFILE_NAMES:
        name = "assembly.glb" if profile == CURRENT else f"assembly-{profile}.glb"
        glbs[profile] = (name, glb_bytes(parts, profile))
        files[name] = glbs[profile][1]
    manifest = {
        "schema": 1, "name": D["name"], "units": "mm", "status": D["status"], "frame": D["frame"],
        "source": {"dimensions_sha256": sha256(DIMENSIONS.read_bytes()), "script_sha256": sha256(Path(__file__).read_bytes()),
                   "tools": {name: metadata.version(name) for name in ("manifold3d", "trimesh", "numpy")}},
        "printer_reference": D["printer_reference"],
        "layout": {"overall_length": D["overall"]["length"], "handle_mouth_z": L, "spigot_end_z": Z_SPIGOT, "lap_center_z": r4(Z_LAP),
                   "tongue_rear_z": r4(Z_TONGUE), "puck_center": [0.0, r4(Y_FLOOR + TIP["puck_case_height"] / 2), r4(Z_TIP)],
                   "puck_case": {"diameter": TIP["puck_case_diameter"], "height": TIP["puck_case_height"]},
                   "buttons_z": BUTTONS, "pod_z": [POD_Z0, POD_Z1], "twist_deg": J["twist"], "pin_angles_deg": J["pin_angles"],
                   "xiao": {"board_center": [0.0, r4(Y_DECK + XT["pcb_thickness"] / 2), r4((Z_BOARD0 + Z_BOARD1) / 2)],
                            "board_size": [XT["board_width"], XT["pcb_thickness"], XT["board_length"]],
                            "board_front_z": r4(Z_BOARD1), "deck_top_y": Y_DECK,
                            "component_clearance": XT["component_clearance"], "boards": XT["boards"]}},
        "current_profile": CURRENT,
        "profiles": {k: {"label": PROFILES[k]["label"], "tip_parts": PROFILES[k]["tip_parts"], "reference": PROFILES[k]["reference"],
                         "glb": glbs[k][0], "assemblies": [f"{k}-{a}" for a in PROFILES[k]["assemblies"]]} for k in PROFILE_NAMES},
        "assemblies": {aid: {"label": a["label"], "profile": a["profile"], "parts": a["parts"]} for aid, a in assemblies().items()},
        "glb": [{"file": glbs[k][0], "profile": k, "sha256": sha256(glbs[k][1]), "bytes": len(glbs[k][1]),
                 "units": "metres, Y up, wand along +Z; assemblies stacked 130 mm apart in -Y"} for k in PROFILE_NAMES],
        "parts": entries,
    }
    if run_checks:
        manifest["checks"] = {"joint": joint_checks(), "assembly": assembly_checks(parts),
                              "meshes_passed": all(e["mesh"]["watertight"] and e["mesh"]["winding_consistent"] and e["mesh"]["every_edge_shared_twice"]
                                                   and e["mesh"]["bodies"] == 1 and e["mesh"]["volume_mm3"] > 0 and e["fits_bed"] for e in entries)}
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    return files, manifest


def summarize(manifest: dict) -> list[str]:
    lines, problems = [], []
    for e in manifest["parts"]:
        m = e["mesh"]
        lines.append(f"  {e['name']:18s} {m['triangles']:6d} tris  {m['volume_mm3']:9.0f} mm3  size {m['print_size_mm']}  "
                     f"ceilings {m['downward_flat_mm2']:.0f} mm2  steep {m['downward_steeper_than_45_mm2']:.0f} mm2")
    c = manifest.get("checks", {})
    if c:
        j = c["joint"]
        lines.append(f"  joint: insertion {j['insertion_at_entry_angle_max_mm3']} mm3, twist axial {j['twist_max_axial_overlap_mm']} mm, "
                     f"pull-out {j['locked_pull_out_0_6mm_overlap_mm3']} mm3, over-twist {j['over_twist_6deg_overlap_mm3']} mm3, "
                     f"insertable angles {j['insertable_angles_deg']}")
        for v, a in c["assembly"].items():
            lines.append(f"  {v}: opening {a['opening']}, unexpected {a['unexpected']}, wires {a['wire_probe_overlap_mm3']}")
        if not c["meshes_passed"]:
            problems.append("mesh checks")
        if not j["passed"]:
            problems.append("joint checks")
        problems += [f"assembly {v}" for v, a in c["assembly"].items() if not a["passed"]]
    return lines + ([f"FAILED: {', '.join(problems)}"] if problems else ["All geometry checks passed"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare with exports/")
    ap.add_argument("--out", type=Path, default=HERE / "exports")
    args = ap.parse_args()
    files, manifest = build()
    report = summarize(manifest)
    print("\n".join(report))
    failed = report[-1].startswith("FAILED")
    if args.check:
        stale = [n for n, data in files.items() if not (args.out / n).is_file() or (args.out / n).read_bytes() != data]
        extra = sorted(p.name for p in args.out.glob("*") if p.name not in files)
        if stale or extra:
            print(f"Exports differ from a fresh build: {stale + extra}", file=sys.stderr)
            return 1
        print("Exports match a fresh build byte for byte")
        return 1 if failed else 0
    args.out.mkdir(parents=True, exist_ok=True)
    for n, data in files.items():
        (args.out / n).write_bytes(data)
    print(f"Wrote {len(files)} files")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
