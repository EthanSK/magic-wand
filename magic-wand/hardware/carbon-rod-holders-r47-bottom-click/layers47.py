"""Compare two carriers as the slicer sees them: closed mid-layer sections, standing.

Imports no revision module, so both build47.py (R47 parameters) and
check46.py (R46 parameters) use the same comparison.
"""
import json
import math
from pathlib import Path

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
R46_FRAME = HERE.parent / 'carbon-rod-holders-r46-middle-to-edge/exports/key-holder-only/frame.json'
CLOSING = .049              # the selected profile's slice_closing_radius
LAYER = .2
PRINT_DETAIL = .2           # Comparison screen only; actual Arachne paths remain decisive.
NOISE = .005                # boundary noise ignored: >1000x float32 error, <1/80 bead
# R45 standing_relief45.make: the four lower-floor lip-relief windows (print
# x, width, z range), all in the lower-floor band print y 11.78-13.60.
R45_LIP_WINDOWS = ((-.3, 20.1, 14.8, 23.4), (-.3, 20.1, 26.8, 35.5), (46., 14.4, 5.8, 13.8), (46., 14.4, 27.0, 35.5))
R45_FLOOR_BAND = (11.78 - .3, 13.60 + .3)


def print_frame():
    """The standing print frame shared by R45, R46 and R47 (print -> assembly)."""
    return np.array(json.loads(R46_FRAME.read_text())['print_to_assembly'])


def layer_differences(before, after, layer=LAYER, closing=CLOSING):
    """Per-layer change between two carriers (assembly frame), sliced standing as printed.

    Each mid-layer section is closed by the slicer's slice-closing radius.
    R45's lip relief steps the lower floor layer by layer, leaving strips
    0.03-0.11 mm wide that a float32 STL resolves slightly differently. So
    the change is also reported after opening by PRINT_DETAIL / 2 (what is
    left is wider than half a bead) and outside R45's lower-floor band.
    """
    inverse = np.linalg.inv(print_frame())[:3].tolist()
    a, b = before.transform(inverse), after.transform(inverse)
    x0, _, _, x1, _, z1 = a.bounding_box()
    band = mf.CrossSection.square((x1 - x0 + 4., R45_FLOOR_BAND[1] - R45_FLOOR_BAND[0])).translate(
        (x0 - 2., R45_FLOOR_BAND[0]))

    def closed(section):
        return section.offset(closing).offset(-closing)

    rows = []
    for k in range(1, int(math.ceil(max(z1, b.bounding_box()[5]) / layer)) + 1):
        z = (k - .5) * layer
        sa, sb = closed(a.slice(z)), closed(b.slice(z))
        # Boundaries shared by both meshes differ by float32 rounding (under
        # 4 um here); ignore differences narrower than NOISE along them.
        change = (sa - sb.offset(NOISE, mf.JoinType.Miter)) + (sb - sa.offset(NOISE, mf.JoinType.Miter))
        # A piece holding a PRINT_DETAIL-wide disc has at least that disc's
        # area, so only such pieces need the (costly) opening.
        disc = math.pi * (PRINT_DETAIL / 2) ** 2
        candidates = [piece for piece in change.decompose() if piece.area() >= disc * .95]
        wide = sum(piece.offset(-PRINT_DETAIL / 2, mf.JoinType.Miter).offset(PRINT_DETAIL / 2, mf.JoinType.Miter).area()
                   for piece in candidates)
        rows.append((round(z, 3), change.area(), wide, (change - band).area()))
    worst = max(rows, key=lambda row: row[1])
    wide = max(rows, key=lambda row: row[2])
    outside = max(rows, key=lambda row: row[3])
    return {'print_layers_compared': len(rows), 'slice_closing_radius_mm': closing, 'boundary_noise_ignored_mm': NOISE,
            'largest_layer_change_mm2': round(worst[1], 5), 'at_print_z_mm': worst[0],
            'layers_changed_over_0.01mm2': sum(row[1] > .01 for row in rows),
            'largest_change_wider_than_0.2mm_mm2': round(wide[2], 5), 'wider_change_at_print_z_mm': wide[0],
            'largest_change_outside_r45_floor_band_mm2': round(outside[3], 5), 'outside_change_at_print_z_mm': outside[0],
            'r45_floor_band_print_y_mm': list(R45_FLOOR_BAND)}


def prints_alike(report, tolerance=.005):
    return (report['largest_change_wider_than_0.2mm_mm2'] < tolerance
            and report['largest_change_outside_r45_floor_band_mm2'] < tolerance)
