"""Deposited-path gauges for the R63 battery seat, side leaf, hinge line and left backing strip.

Every gauge is a solid in assembly coordinates, built from the constants in design63, so the CAD
and the audit use the same numbers. `deposited_routes()` is merged over the inherited holder
gauges: it replaces the old battery, leaf, cheek-pin and barrel-lowering entries by name.
"""
import numpy as np

from design63 import (BACKER, BED, LEAF_X, LIP_TOP, OUT, PACK, PACK_X, PACK_Y0, PACK_Z, WALL_FACE, b, hinge_gauges)

SHOE_Y = (PACK_Y0 + 6.0, PACK_Y0 + 7.0, PACK_Y0 + 8.0)     # stations on the leaf's shoe


def free_core():
    """The whole pack less the leaf shoe's working strip, as in the R60 audit."""
    return b.box(PACK_X[0] + 0.25, PACK_X[1] - 0.03, PACK_Y0, PACK_Y0 + PACK[1], PACK_Z[0] + 0.03, PACK_Z[1] - 0.03)


def deposited_routes():
    core = free_core()
    routes = {
        'battery_seated': [core],
        'battery_slides_in_from_the_rear': [core.translate((0, float(t), 0)) for t in np.arange(0, 31)],
        # A 0.40 mm window in the 0.68 mm gap behind the leaf, and the slot between the leaf and the lip under it.
        'side_leaf_can_flex': [b.box(WALL_FACE + 0.14, WALL_FACE + 0.54, PACK_Y0 + 2.5, BED - 5.9, PACK_Z[0] + 0.66, PACK_Z[1] - 0.65)],
        'leaf_is_free_of_floor': [b.box(LEAF_X[0] + 0.25, LEAF_X[1] - 0.15, PACK_Y0 + 2.7, BED - 5.9, LIP_TOP + 0.12, LIP_TOP + 0.40)],
    }
    routes.update(hinge_gauges())
    strip = OUT / BACKER
    if strip.exists():
        tool = b.load(strip)
        routes['backing_strip_Left'] = [tool.translate((-float(dx), 0, 0)) for dx in np.arange(0, 27)]
    return routes


def spring_opening(points, position):
    """Opposing deposited faces at mid height of the pack, across the leaf shoe. Same method as the R60 audit."""
    assert np.allclose(position[:3, :3], [[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    x0, y0, z0 = position[:3, 3]
    probe = y0 + (PACK_Z[0] + PACK_Z[1]) / 2
    centre = points[(points[:, 0] > x0 + PACK_X[0] - 3) & (points[:, 0] < x0 + PACK_X[1] + 3)
                    & (abs(points[:, 1] - probe) < points[:, 3] / 2)]
    rows = []
    for depth in SHOE_Y:
        line = centre[abs(z0 - centre[:, 2] - depth) < 0.11]
        dx = np.sqrt(np.maximum(0, (line[:, 3] / 2) ** 2 - (line[:, 1] - probe) ** 2))
        on_spring = line[:, 0] < x0 + sum(PACK_X) / 2
        assert on_spring.any() and (~on_spring).any()
        opening = float((line[~on_spring, 0] - dx[~on_spring]).min() - (line[on_spring, 0] + dx[on_spring]).max())
        rows.append(dict(depth_mm=round(depth, 2), opening_mm=round(opening, 3), nominal_pack_interference_mm=round(PACK[0] - opening, 3)))
    assert all(0 < r['nominal_pack_interference_mm'] < 0.35 for r in rows), rows
    return rows
