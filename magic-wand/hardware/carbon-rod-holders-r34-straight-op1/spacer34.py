"""Angled vent slots in the existing 0.4 mm battery spacer envelope."""

from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

R24 = Path(__file__).resolve().parent.parent / 'carbon-rod-holders-r24-patterned-spacer'
sys.path.insert(0, str(R24))
import spacer24 as stock

NAME = stock.NAME
ROW_Y = (-8.55, -4.30, -.05, 4.20, 8.45)


def windows():
    # Ethan's "panel that goes in front of the battery" is this thin optional
    # spacer. Keep the cutouts like straight-edged vents, with small fillets.
    slot = stock.rounded(mf.CrossSection([[(-2.25, -.45), (-1.78, -.95), (1.78, -.95),
                                          (2.25, -.45), (2.25, .45), (1.78, .95),
                                          (-1.78, .95), (-2.25, .45)]]), .18)
    centres = ((-5.75, 24.), (0., 0.), (5.75, -24.))
    return mf.CrossSection.batch_boolean([slot.rotate(angle).translate((x, y)) for y in ROW_Y for x, angle in centres], mf.OpType.Add)


def export(out):
    reference = stock.h.h22.read(stock.REFERENCE)
    z = stock.BASE.cage_levels()['floor_top']
    cut = windows()
    outline = stock.outline()
    inner = outline.offset(-stock.FRAME, stock.ROUND, 2., stock.SEG)
    assert (cut - inner).area() < .001, 'Vent slots must stay inside the continuous rim.'
    plan = mf.CrossSection.batch_boolean([outline, cut, *stock.nicks()], mf.OpType.Subtract)
    candidate = stock.BASE.clean(mf.Manifold.extrude(plan, stock.T).translate((0, 0, z)) ^ reference, NAME)
    section = candidate.slice(z + stock.T / 2)
    holes = [p for p in section.to_polygons() if stock.signed_area(p) < 0]
    assert len(holes) == len(ROW_Y) * 3
    hole_widths = [stock.inscribed_diameter(mf.CrossSection([stock.BASE.ccw([tuple(q) for q in p])])) for p in holes]
    assert min(hole_widths) >= stock.MIN_OPENING and max(hole_widths) <= stock.MAX_OPENING
    thin = section - stock.rounded(section, stock.MIN_WEB / 2)
    for nick in stock.nicks():
        thin -= nick.offset(stock.MIN_WEB, stock.ROUND, 2., stock.SEG)
    assert max((p.area() for p in thin.decompose()), default=0.) < stock.SLIVER_MM2
    assert (candidate - reference).volume() < .01

    assembly = out / f'{NAME}-assembly.stl'
    source = out / f'{NAME}-SOURCE-REQUIRES-PREPARATION.stl'
    model, printable, to_print = stock.h.h22.to_print(candidate, NAME)
    to_assembly = np.linalg.inv(to_print)
    stock.h.write_checked_stl(model, assembly, candidate, np.eye(4))
    written, _ = stock.h.write_checked_stl(printable, source, candidate, to_assembly)
    assert abs(float(written.bounds[1][2]) - stock.T) < .001
    return {'stl_sha256': stock.h.sha(source), 'assembly_stl_sha256': stock.h.sha(assembly),
            'print_to_assembly': to_assembly.tolist(), 'print_height_mm': stock.T,
            'geometry_checks': {'through_openings': len(holes), 'patterned_volume_mm3': round(candidate.volume(), 4),
                                'hole_width_mm': [round(min(hole_widths), 3), round(max(hole_widths), 3)],
                                'minimum_web_mm': stock.MIN_WEB, 'continuous_rim_mm': stock.FRAME},
            'reference_assembly_stl_sha256': stock.h.sha(stock.REFERENCE), 'physical_fit_verified': False}
