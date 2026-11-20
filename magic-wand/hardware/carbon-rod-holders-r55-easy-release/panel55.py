"""R55 holder base: the R54 braced panel with nothing attached to, or close around, the hinge.

R54 stayed on the plate for all 257 layers. Two of its six fins were rooted in the outer faces
of the hinge yoke, in the corner between the yoke and the rear rim, and the panel closed round
the yoke 1.5 mm away. That corner was hard to free by hand.

R55 keeps the four R54 fins on the rear rim unchanged. The two yoke fins move to the rim
underside, 24.5 mm out from the rod, so the total fin section stays at the R54 value. A bay
3 mm wider than the yoke on each side is left open from the rim to the edge of the panel. The
panel is then one C-shaped piece: nothing touches or surrounds the hinge, a thumb fits above
it, and the two wings fold away once the fins are nipped.

Geometry, checks and the bed frame are those of panel54 (print X = assembly X, print Y =
assembly Z, rod axis at the origin). The holder mesh is not changed.
"""
from pathlib import Path
import sys

import manifold3d as mf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "carbon-rod-holders-r54-reinforced-base"))
import panel54 as p54  # noqa: E402

YOKE_HALF = 11.5     # outer faces of the hinge yoke
BAY_MARGIN = 3.0     # open width left beside each yoke face
BAY = [-(YOKE_HALF + BAY_MARGIN), 11.0, YOKE_HALF + BAY_MARGIN, 60.0]   # x0, y0, x1, y1; runs past the panel edge
# Fin stations. Heights are the R54 values as printed; the two +y fins stop below the keycaps.
CARRIER_BASE = {
    "size": [96, 44],
    "keep_clear": [list(p54.WIRE_LANE), BAY],
    "ties": [
        {"face": "+y", "at": 21.5, "height": 2.4}, {"face": "+y", "at": -21.5, "height": 2.4},
        {"face": "-y", "at": 14.2, "height": 3.0}, {"face": "-y", "at": -14.2, "height": 3.0},
        # Replace the two R54 yoke fins. Same 2.4 mm height, so they end below print Z 3.0
        # where the upper-right socket space begins.
        {"face": "-y", "at": 24.5, "height": 2.4}, {"face": "-y", "at": -24.5, "height": 2.4},
    ],
}


def settings(panel=None):
    """CARRIER_BASE with any caller overrides. An empty or missing panel gives the R55 design."""
    merged = {key: value for key, value in CARRIER_BASE.items()}
    merged.update(panel or {})
    return merged


def _hinge_zone(panel):
    origin = panel.get("origin", (0.0, 0.0))
    x0, y0, x1, y1 = BAY
    return p54._solid(p54._box(origin[0] + x0, origin[1] + y0, origin[0] + x1, origin[1] + y1), -1, 80)


def _check(body, panel):
    """R55 rules on top of the R54 ones: no fin on the yoke and no base material in the hinge bay."""
    if any(tie["face"][1] == "x" for tie in panel["ties"]):
        raise ValueError("R55 has no fin on the hinge yoke")
    base, necks, lay = p54.base54(body, panel)
    inside = float((base ^ _hinge_zone(panel)).volume())
    if inside > 1e-6:
        raise ValueError(f"Base material inside the hinge bay: {inside:.4f} mm3")
    return base, necks, lay


def backed_panel55(body, panel=None):
    """Bed-oriented holder joined to its R55 base as one solid."""
    panel = settings(panel)
    _check(body, panel)
    return p54.backed_panel54(body, panel)


def report55(body, panel=None):
    """The R54 report plus the hinge-area evidence and the removal order."""
    panel = settings(panel)
    base, necks, lay = _check(body, panel)
    report = p54.report54(body, panel)
    origin = panel.get("origin", (0.0, 0.0))
    x0, y0, x1, y1 = BAY
    # The hinge itself: everything of the holder inside the yoke width, above the rim.
    yoke = body ^ p54._solid(p54._box(origin[0] - YOKE_HALF - 0.01, origin[1] + 12.6, origin[0] + YOKE_HALF + 0.01, origin[1] + 60), -1, 80)
    edge = lay["outline"].bounds()
    report.update(
        revision="R55",
        hinge_bay_xy=[x0, y0, x1, round(float(edge[3]) - origin[1], 2)],
        hinge_bay_open_to_panel_edge=bool(edge[3] - origin[1] < y1),
        base_volume_in_hinge_bay_mm3=round(float((base ^ _hinge_zone(panel)).volume()), 6),
        nearest_base_to_hinge_mm=round(float(base.min_gap(yoke, 12.0)), 2),
        fins_on_hinge=0,
        panel_pieces=len([s for s in lay["sheet"].decompose() if s.area() > 0.5]),
        removal=[
            "Nip the two fins on the rim underside nearest the ends (X +/-24.5).",
            "Nip the two fins on the rim underside nearer the rod (X +/-14.2).",
            "Nip the two fins on top of the rim (X +/-21.5).",
            "Fold the two wings of the panel away from the hinge bay. Nothing is attached at the hinge.",
        ])
    return report
