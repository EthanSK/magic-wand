#!/usr/bin/env python3
"""R21 cable clip: a split figure of eight, printed flat for continuous spring paths.

Run through the repository geometry runner. R20 and its active print stay frozen.
The rod loop reuses the R7 spring profile; the cable loop is a loose guide, not
strain relief. Actual wire sizes, clip force and fatigue remain unmeasured.
"""
from pathlib import Path
from functools import lru_cache
import hashlib
import json
import math
import sys
import numpy as np
import trimesh
import manifold3d as mf

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
R19 = HERE.parent / 'carbon-rod-holders-r19-lightweight'
sys.path.insert(0, str(R19))
import holder19 as h19  # noqa: E402

r7 = h19.base.r15.base.r7
NAME = 'Cable_Clip_4mm'
P = {'rod_mm': 8.0, 'rod_bore_mm': 7.9, 'rod_root_wall_mm': 1.4,
     'axial_width_mm': 2.4, 'cable_bore_mm': 4.0, 'cable_wall_mm': 1.0,
     'cable_entry_gap_mm': .8, 'centres_mm': 7.4, 'cable_chamfer_mm': .2,
     'pad_thickness_mm': .4, 'tie_width_mm': .7}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def clip() -> mf.Manifold:
    # Ethan's "double eight / infinity" has two independent sideways openings.
    # Put the rod opening away from the cable loop; share the thick fixed root.
    width = P['axial_width_mm']
    rod = r7.ring(0, P['rod_bore_mm'], width, P['rod_root_wall_mm'])
    rod = rod.rotate((-90, 0, 0)).translate((0, 0, width / 2)).rotate((0, 0, -90))
    inner = P['cable_bore_mm'] / 2
    wall = P['cable_wall_mm']
    centre_radius = inner + wall / 2
    half_gap = math.asin((P['cable_entry_gap_mm'] + wall) / (2 * centre_radius))
    angles = np.linspace(half_gap, 2 * math.pi - half_gap, 180)
    outer = np.c_[(inner + wall) * np.cos(angles), (inner + wall) * np.sin(angles)]
    inside = np.c_[inner * np.cos(angles[::-1]), inner * np.sin(angles[::-1])]
    section = mf.CrossSection([np.vstack((outer, inside))])
    for angle in (angles[0], angles[-1]):
        section += mf.CrossSection.circle(wall / 2, 40).translate((centre_radius * math.cos(angle), centre_radius * math.sin(angle)))
    cable = mf.Manifold.extrude(section, width).translate((P['centres_mm'], 0, 0))
    result = rod + cable
    # Gentle bore lead-ins protect insulation; no roof or support enters a loop.
    chamfer = P['cable_chamfer_mm']
    result -= mf.Manifold.cylinder(chamfer, inner + chamfer, inner, 96).translate((P['centres_mm'], 0, 0))
    result -= mf.Manifold.cylinder(chamfer, inner, inner + chamfer, 96).translate((P['centres_mm'], 0, width - chamfer))
    assert result.status() == mf.Error.NoError and len(result.decompose()) == 1
    return result


def anchors() -> mf.Manifold:
    # Two small pads attach only through narrow bed-layer ties at the fixed waist.
    # Snip at Y +/-3.7, away from both spring arms and every functional opening.
    pieces = []
    for sign in (-1, 1):
        low, high = sorted((sign * 4.5, sign * 7.0))
        pieces.append(h19.box(3.5, 6.5, low, high, 0, P['pad_thickness_mm']))
        low, high = sorted((sign * .8, sign * 4.7))
        pieces.append(h19.box(4.9 - P['tie_width_mm'] / 2, 4.9 + P['tie_width_mm'] / 2, low, high, 0, P['pad_thickness_mm']))
    return mf.Manifold.batch_boolean(pieces, mf.OpType.Add)


def export() -> None:
    out = HERE / 'exports'
    out.mkdir(exist_ok=True)
    part, pads = clip(), anchors()
    combined = part + pads
    assert len(combined.decompose()) == 1, 'An adhesion tie is disconnected'
    bounds = np.asarray(combined.bounding_box())
    shift = np.r_[-bounds[:2], 0.]
    transform = np.eye(4)
    transform[:3, 3] = -shift
    records = {}
    for label, solid in [('part', part), ('pads', pads)]:
        mesh = h19.mesh(solid.translate(tuple(shift)))
        assert mesh.is_watertight and mesh.volume > 0
        suffix = 'SOURCE-REQUIRES-PREPARATION' if label == 'part' else 'ANCHOR-REMOVE-AFTER-PRINT'
        path = out / f'{NAME}-{suffix}.stl'
        mesh.export(path)
        records[label] = {'sha256': sha(path), 'volume_mm3': float(mesh.volume), 'bounds_mm': mesh.bounds.tolist()}
    h19.mesh(part).export(out / f'{NAME}-assembly.stl')
    report = {'revision': 'R21 split cable clip', 'parameters': P, 'plate_parts': [NAME],
              'sources': {'clip21.py': sha(Path(__file__)), '../carbon-rod-holders-r7-spring-clips/cad.py': sha(r7.HERE / 'cad.py'), '../carbon-rod-holders-r7-spring-clips/parameters.json': sha(r7.HERE / 'parameters.json')},
              'parts': {NAME: {'print_to_assembly': transform.tolist(), 'stl_sha256': records['part']['sha256'],
                               'volume_mm3': records['part']['volume_mm3'], 'solid_PETG_g': records['part']['volume_mm3'] * .00127,
                               'print_height_mm': P['axial_width_mm'], 'body_count': 1, 'watertight': True}},
              'exports': records, 'physical_fit_verified': False, 'physical_strength_verified': False,
              'wire_size_basis': '4 mm loose guide based on the earlier provisional 3 mm wire corridor; actual cable bundle is unmeasured.'}
    (out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'mass_g': report['parts'][NAME]['solid_PETG_g'], 'height_mm': P['axial_width_mm'], 'exports': records}), flush=True)


if __name__ == '__main__':
    export()
