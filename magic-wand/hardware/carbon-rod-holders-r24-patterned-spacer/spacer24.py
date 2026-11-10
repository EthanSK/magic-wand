#!/usr/bin/env python3
"""R24 patterned 0.4 mm cell spacer: the R18/R22 floor layer with a rosette of negative space.

Basis: holder18.spacer(0.4), reused byte-for-byte by R19 and R22. The battery holder, cell path
and both doors are unchanged; R24 carries the same R22 holder. This part only removes material
from that envelope, so it cannot fit more tightly than the printed original.

Pattern (plan view, centred on the middle floor bar over the keel):
- a small central eye inside a solid hub;
- eight pointed lens petals, with the solid spokes between them on the keel and bar axes;
- eight round dots between the petal tips, inside a continuous solid ring;
- four short ray windows above and four below that ring, separated by radial webs;
- one dot in each far corner.
A continuous frame runs round the whole outline, including the wire notch. Corners and the
notch are rounded. The two far-edge nicks still mark the two 0.2 mm layers.
"""

import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R23 = HERE.parent / "carbon-rod-holders-r23-hybrid-centre"
sys.path.insert(0, str(R23))
import holder23 as h  # noqa: E402

H18 = h.h22.h18
BASE = H18.base
SP = H18.SP
NAME = "Battery_Spacer_0p4mm_Patterned"
REFERENCE = h.R22 / "exports" / "Battery_Spacer_0p4mm-assembly.stl"
OUT = HERE / "exports" / "spacer"
ROUND, SEG = mf.JoinType.Round, 64

# Spacer-specific design values (mm). Kept here so the parent's parameters.json is untouched.
T = 0.4                  # one trial thickness: two 0.2 mm layers
CORNER_R = 2.0           # outline corners (R18 used 1.2)
NOTCH_R = 1.0            # fillet at the inner corners of the wire notch
MOUTH_R = 0.5            # rounding where the notch meets the near edge
FRAME = 1.6              # continuous perimeter kept solid
WINDOW_R = 0.3           # rounding of every window corner
CENTRE = (0.0, 0.6)      # middle floor bar strip (cap y 0.0, strip 1.2) over the keel
EYE_R = 0.8
PETALS = {"count": 8, "first_deg": 22.5, "r_in": 2.5, "r_out": 6.5, "half_width": 0.85}
DOTS = {"count": 8, "first_deg": 0.0, "radius_at": 6.9, "r": 0.75}
RAYS = {"r_in": 9.0, "r_out_far": 10.5, "r_out_near": 10.3, "span_deg": 15.0,
        "far_centres_deg": [78, 102, 54, 126], "near_centres_deg": [258, 282, 234, 306]}
CORNER_DOTS = {"xy": [(7.3, 10.9), (-7.3, 10.9)], "r": 0.8}

# Check limits (mm). 0.42 mm lines: 1.2 mm leaves room for two beads plus gap fill.
MIN_WEB = 1.2
MIN_OPENING = 1.2
MAX_OPENING = 2.5        # largest circle that fits in any window, so the pouch cannot sag far
SLIVER_MM2 = 0.15        # allowance for tiny convex-corner slivers at nicks and notch mouth


def rect(x0, x1, y0, y1):
    return mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def rounded(section, r):
    return section.offset(-r, ROUND, 2., SEG).offset(r, ROUND, 2., SEG)


def lens(r_in, r_out, half_width, angle_deg):
    """Pointed petal along +X from r_in to r_out, rotated to angle_deg about CENTRE."""
    length = r_out - r_in
    radius = (length ** 2 / 4 + half_width ** 2) / (2 * half_width)
    off = radius - half_width
    mid = (r_in + r_out) / 2
    a = mf.CrossSection.circle(radius, 128).translate((mid, off))
    b = mf.CrossSection.circle(radius, 128).translate((mid, -off))
    return (a ^ b).rotate(angle_deg).translate(CENTRE)


def sector(r0, r1, a0_deg, a1_deg, n=32):
    angles = np.radians(np.linspace(a0_deg, a1_deg, n))
    outer = [(CENTRE[0] + r1 * math.cos(a), CENTRE[1] + r1 * math.sin(a)) for a in angles]
    inner = [(CENTRE[0] + r0 * math.cos(a), CENTRE[1] + r0 * math.sin(a)) for a in angles[::-1]]
    return mf.CrossSection([BASE.ccw(outer + inner)])


def circle(x, y, r):
    return mf.CrossSection.circle(r, 64).translate((x, y))


def outline():
    """R18 envelope with rounder corners and filleted notch; no windows or nicks."""
    hw, (y0, y1) = SP["half_x_mm"], SP["y_mm"]
    cx, cy = SP["protection_notch_half_x_mm"], SP["protection_end_y_mm"]
    body = rounded(rect(-hw, hw, y0, y1), CORNER_R)
    notch = rounded(rect(-cx, cx, y0 - 1, cy), NOTCH_R)
    return rounded(body - notch, MOUTH_R)


def nicks():
    """Same layer-count nicks as holder18.spacer: one per 0.2 mm layer on the far edge."""
    n = round(T / .2)
    return [mf.CrossSection.circle(.45, 16).translate(((i - (n - 1) / 2) * 2., SP["y_mm"][1])) for i in range(n)]


def windows():
    p, d, r = PETALS, DOTS, RAYS
    items = [circle(*CENTRE, EYE_R)]
    items += [lens(p["r_in"], p["r_out"], p["half_width"], p["first_deg"] + 360 / p["count"] * k) for k in range(p["count"])]
    for k in range(d["count"]):
        a = math.radians(d["first_deg"] + 360 / d["count"] * k)
        items.append(circle(CENTRE[0] + d["radius_at"] * math.cos(a), CENTRE[1] + d["radius_at"] * math.sin(a), d["r"]))
    half = r["span_deg"] / 2
    items += [sector(r["r_in"], r["r_out_far"], c - half, c + half) for c in r["far_centres_deg"]]
    items += [sector(r["r_in"], r["r_out_near"], c - half, c + half) for c in r["near_centres_deg"]]
    items += [circle(x, y, CORNER_DOTS["r"]) for x, y in CORNER_DOTS["xy"]]
    cut = mf.CrossSection.batch_boolean(items, mf.OpType.Add)
    inside = outline().offset(-FRAME, ROUND, 2., SEG)
    return rounded(cut ^ inside, WINDOW_R), cut


def plan():
    cut, _ = windows()
    return mf.CrossSection.batch_boolean([outline(), cut, *nicks()], mf.OpType.Subtract)


def spacer():
    z = BASE.cage_levels()["floor_top"]
    return BASE.clean(mf.Manifold.extrude(plan(), T).translate((0, 0, z)), NAME)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def signed_area(poly):
    x, y = np.asarray(poly, float).T
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def inscribed_diameter(section):
    lo, hi = 0., 15.
    for _ in range(16):
        m = (lo + hi) / 2
        if section.offset(-m, ROUND, 2., SEG).is_empty():
            hi = m
        else:
            lo = m
    return 2 * lo


def verify(new, reference):
    z = BASE.cage_levels()["floor_top"]
    box = new.bounding_box()
    assert abs(box[2] - z) < 1e-3 and abs(box[5] - z - T) < 1e-3, box
    # Fit: only material removed from the reused original.
    outside = h.vol(new - reference)
    assert outside < .01, outside
    # One body, through openings counted on the mid-layer section.
    assert len(new.decompose()) == 1
    polys = new.slice(z + T / 2).to_polygons()
    outer = [p for p in polys if signed_area(p) > 0]
    holes = [p for p in polys if signed_area(p) < 0]
    assert len(outer) == 1, len(outer)
    sizes = sorted(round(inscribed_diameter(mf.CrossSection([BASE.ccw([tuple(q) for q in p])])), 3) for p in holes)
    assert sizes and sizes[0] >= MIN_OPENING and sizes[-1] <= MAX_OPENING, sizes
    expected = 1 + PETALS["count"] + DOTS["count"] + len(RAYS["far_centres_deg"]) + len(RAYS["near_centres_deg"]) + len(CORNER_DOTS["xy"])
    assert len(holes) == expected, (len(holes), expected)
    # Windows stayed whole: the frame clip and rounding only trimmed corners.
    clipped, raw = windows()
    assert clipped.area() > .97 * raw.area(), (clipped.area(), raw.area())
    # Minimum web: material lost to a MIN_WEB opening is only corner slivers.
    section = plan()
    thin = section - section.offset(-MIN_WEB / 2, ROUND, 2., SEG).offset(MIN_WEB / 2, ROUND, 2., SEG)
    # The R18 nick pair leaves a 1.1 mm edge tooth between them by design; judge webs elsewhere.
    thin -= mf.CrossSection.batch_boolean([n.offset(MIN_WEB, ROUND, 2., SEG) for n in nicks()], mf.OpType.Add)
    thin_pieces = [signed_area(p) for p in thin.to_polygons() if signed_area(p) > 0]
    assert max(thin_pieces, default=0.) < SLIVER_MM2, max(thin_pieces)
    # Continuous frame: the full perimeter band is solid apart from the layer nicks.
    ring = (outline() - outline().offset(-FRAME, ROUND, 2., SEG)) ^ reference.slice(z + T / 2)
    missing = (ring - section).area() - (ring ^ mf.CrossSection.batch_boolean(nicks(), mf.OpType.Add)).area()
    assert abs(missing) < .01, missing
    density = BASE.r15.P["print"]["density_g_cm3"]
    v_ref, v_new = h.vol(reference), h.vol(new)
    return {
        "thickness_mm": T, "layers_at_0p2mm": round(T / .2),
        "reference_volume_mm3": round(v_ref, 3), "patterned_volume_mm3": round(v_new, 3),
        "mass_removed_mm3": round(v_ref - v_new, 3),
        "mass_removed_PETG_g": round((v_ref - v_new) / 1000 * density, 4),
        "mass_removed_fraction": round((v_ref - v_new) / v_ref, 3),
        "patterned_PETG_g": round(v_new / 1000 * density, 4),
        "volume_outside_reference_mm3": round(outside, 6),
        "bodies": 1, "through_openings": len(holes),
        "opening_inscribed_diameters_mm": {"min": sizes[0], "max": sizes[-1]},
        "min_web_mm": MIN_WEB, "largest_sliver_below_min_web_mm2": round(max(thin_pieces, default=0.), 4),
        "continuous_frame_mm": FRAME, "frame_missing_mm2_excluding_nicks": round(missing, 4),
        "status": "CAD geometry only. Sag into windows, bed release of the lace and fit are not physically verified.",
    }


def export():
    reference = h.h22.read(REFERENCE)
    original = H18.spacer(T)
    assert h.vol(reference ^ original) > h.vol(reference) - .01 and abs(h.vol(reference) - h.vol(original)) < .01, "R22 spacer is not the holder18 envelope"
    candidate = (spacer() ^ reference).simplify(.0001)
    OUT.mkdir(parents=True, exist_ok=True)
    assembly = OUT / f"{NAME}-assembly.stl"
    source = OUT / f"{NAME}-SOURCE-REQUIRES-PREPARATION.stl"
    model, print_model, assembly_to_print = h.h22.to_print(candidate, NAME)
    inverse = np.linalg.inv(assembly_to_print)
    _, assembly_drift = h.write_checked_stl(model, assembly, candidate, np.eye(4))
    written, print_drift = h.write_checked_stl(print_model, source, candidate, inverse)
    checks = verify(h.h22.read(assembly), reference)
    assert abs(float(written.bounds[1][2]) - T) < 1e-3
    manifest = {
        "model": NAME, "revision": json.loads((HERE / "parameters.json").read_text())["revision"],
        "replaces_on_plate": "Battery_Spacer_0p4mm (R22 copy of the R18 flat spacer)",
        "stl_sha256": h.sha(source), "assembly_stl_sha256": h.sha(assembly),
        "print_to_assembly": inverse.tolist(), "print_height_mm": round(float(written.bounds[1][2]), 4),
        "assembly_export_drift_mm3": assembly_drift, "print_export_drift_mm3": print_drift,
        "reference_assembly_stl_sha256": h.sha(REFERENCE),
        "source_sha256": {"spacer24.py": h.sha(Path(__file__)),
                          "holder18.py": h.sha(H18.HERE / "holder18.py"),
                          "r18-parameters.json": h.sha(H18.HERE / "parameters.json")},
        "geometry_checks": checks,
        "physical_fit_verified": False,
    }
    (OUT / "manifest.json").write_text(json.dumps({
        "revision": manifest["revision"], "parts": {NAME: manifest},
        "physical_fit_verified": False,
    }, indent=2) + "\n")
    print(json.dumps(checks), flush=True)


if __name__ == "__main__":
    export()
