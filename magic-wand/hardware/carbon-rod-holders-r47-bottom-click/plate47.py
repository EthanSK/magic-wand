"""Lay out the R47 carrier with R45's standing helpers, generated from the R47 body.

Usage (through geometry_budget.py): plate47.py BUILD SCRATCH
SCRATCH/stage must hold build47.py's carrier and checks. BUILD receives the
editable Bambu Studio layout and the helper meshes, under the inherited R45
file names (the inherited slicing and audit tools expect them).

R46's plate46.py fed its carrier into R45's generator unchanged. R47 does the
same: the 270-degree standing frame, the pull-off cradle, the finger-side comb
and the switch-aperture prop are all derived from the R47 body. Two inputs
are replaced so they describe R47 rather than R42-R46:

- the carrier's hardware routes (the cradle keeps out of them), which here
  include the moved OP1, its pre-fitted drop and the R47 touch-board sweep
  to R47's own backup angle;
- R45's three standing repairs, which already form part of the R47 body
  (build47 runs R45's chamfer, lip relief and web generators on it; the old
  OP1 ledge relief is not applied), so they pass it through.

R42's two OP1 seat solid-infill selectors, inherited through R44's layout,
are rebuilt around the moved seats. R46's two solid-infill selectors for its
brace joints are kept, and one is added for the new right guard-leg landing.
The body plate45 writes into the layout (after its 1e-5 mm simplify) is
compared with the checked carrier at every print layer.
"""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import manifold3d as mf
import numpy as np

import holder47 as h
import build47 as b

R45 = h.HERE.parent / 'carbon-rod-holders-r45-open-keyways'
sys.path.insert(0, str(R45))
import plate45  # noqa: E402
import standing45  # noqa: E402
import standing_board45  # noqa: E402
import standing_web45  # noqa: E402
import holder45  # noqa: E402

d, q, r = h.d, h.q, h.r
SOLID = {'sparse_infill_density': '100%', 'wall_loops': '4', 'inner_wall_line_width': '0.34',
         'outer_wall_line_width': '0.34', 'internal_solid_infill_line_width': '0.34'}


def routes_for(backup):
    working = d.geometry()[1]
    gaps = b.carrier_gaps(working, np.linspace(q.EARLY_ANGLE, backup, 29))
    gaps.pop('bracket swing to the press limit')
    carrier = b.r45_zones(gaps)
    return lambda: ({d.CARRIER: carrier}, {d.CARRIER: {}})


def prepare(build, scratch):
    stage = scratch / 'stage'
    assembly = b.load(stage / 'R47-Key-Carrier-assembly.stl')
    checks = json.loads((stage / 'r47-checks.json').read_text())
    assert checks['r47']['passed'], 'build47 checks must pass before laying out the plate'
    note = {'feature': 'R47 carrier from build47.py; R45 standing repairs and R46 braces are already in it',
            'removed_mm3': 0., 'added_mm3': 0.}

    def body(solid, frame, out):
        return assembly.transform(np.linalg.inv(frame)[:3]), dict(note)

    with patch.object(standing45, 'prepare', body), \
         patch.object(standing_web45, 'prepare', lambda solid, frame, out: (solid, {})), \
         patch.object(standing_board45, 'prepare', lambda solid, frame, out: solid), \
         patch.object(holder45.inherited, 'routes', routes_for(checks['backup_angle_deg'])):
        plate45.layout(build)
    frame = json.loads((build / 'frame.json').read_text())
    r46 = json.loads((b.R46_EXPORTS / 'frame.json').read_text())
    assert np.allclose(frame['print_to_assembly'], r46['print_to_assembly']), 'standing frame moved'
    # plate45 simplifies the body (1e-5 mm) before writing the layout; the
    # body in the layout must still print as the checked carrier.
    laid = b.load(build / 'R45-Key-Carrier-assembly.stl')
    fidelity = b.layer_differences(assembly, laid)
    assert (fidelity['largest_change_wider_than_0.2mm_mm2'] < .005
            and fidelity['largest_change_outside_r45_floor_band_mm2'] < .005), fidelity
    return add_selectors(build, np.array(frame['print_to_assembly']), stage, fidelity)


def add_selectors(build, frame, stage, fidelity):
    project = build / 'R45-Key-Carrier-layout.3mf'
    with ZipFile(project) as z:
        files = {n: z.read(n) for n in z.namelist()}
    settings = ET.fromstring(files[plate45.SETTINGS])
    model = ET.fromstring(files[plate45.MODEL])
    resources = model.find('./{*}resources')
    parts = resources.find('./{*}object[@id="2"]/{*}components')
    # Refresh only this revision's selectors when reusing a checked layout.
    # Native mesh bytes, helper geometry and all inherited selectors stay put.
    for number in range(460, 466):
        for parent, selector in ((resources, f'./{{*}}object[@id="{number}"]'),
                                 (parts, f'./{{*}}component[@objectid="{number}"]'),
                                 (settings.find('object'), f"part[@id='{number}']")):
            old = parent.find(selector)
            if old is not None:
                parent.remove(old)
    inverse = np.linalg.inv(frame)[:3]
    # R42's OP1 seat solid-infill selectors (parts 142/143, inherited through
    # R44's layout) still box the old seats. Rebuild them R42's way, from
    # each moved R47 seat's print-frame bounds grown 0.15 mm.
    retargeted = {}
    for number, seat in zip((142, 143), q.op1_seats().decompose()):
        old = resources.find(f'./{{*}}object[@id="{number}"]')
        part = settings.find(f"object/part[@id='{number}']")
        label = part.find("metadata[@key='name']").get('value')
        assert label == f'OP1 mounting seat {number - 141} solid infill', label
        resources.remove(old)
        lo, hi = np.array(seat.transform(inverse).bounding_box()[:3]) - .15, np.array(seat.transform(inverse).bounding_box()[3:]) + .15
        plate45.mesh_resource(resources, number, label, mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo)))
        retargeted[label] = [round(float(v), 3) for v in (*lo, *hi)]
    sources = [(460, b.load(b.R46_EXPORTS / 'R46-L-deck-return-base-bond.stl'), 'Solid left deck landing'),
               (461, b.load(b.R46_EXPORTS / 'R46-R-cross-brace.stl'), 'Solid right middle-to-edge brace'),
               (462, h.rib_landing().transform(inverse), 'Solid right guard-leg landing')]
    # Moving the OP1 pocket removes the accidental solid-fill islands that
    # R46 had at Ethan's left finger-rest joints. Make their density explicit.
    _, fixed, ribs = d._base_geometry()
    for number, name in enumerate(('L1', 'L2', 'L3'), 463):
        joint = fixed ^ ribs[name] ^ h.box(-9., 0., -12., 35., 0., 13.)
        assert joint.volume() > 1., (name, 'empty rod-side joint')
        sources.append((number, joint.transform(inverse), f'Solid {name} rod-side guard joint'))
    for number, shape, label in sources:
        lo, hi = np.array(shape.bounding_box()[:3]), np.array(shape.bounding_box()[3:])
        region = mf.Manifold.cube(tuple(hi - lo + 1.2)).translate(tuple(lo - .6))
        plate45.mesh_resource(resources, number, label, region)
        ET.SubElement(parts, plate45.tag('component'), objectid=str(number))
        part = ET.SubElement(settings.find('object'), 'part', id=str(number), subtype='modifier_part')
        for key, value in {'name': label, **SOLID}.items():
            ET.SubElement(part, 'metadata', key=key, value=value)
    files[plate45.MODEL] = ET.tostring(model, encoding='utf-8', xml_declaration=True)
    settings.find("plate/metadata[@key='plater_name']").set('value', 'R47 bottom-click key carrier')
    files[plate45.SETTINGS] = ET.tostring(settings, encoding='utf-8', xml_declaration=True)
    with ZipFile(project, 'w', ZIP_DEFLATED) as z:
        for n, v in files.items():
            z.writestr(n, v)
    path = build / 'frame.json'
    info = json.loads(path.read_text())
    info.update(op1_seat_selectors_print_bounds_mm=retargeted, layout_body_vs_checked_carrier=fidelity,
                layout_sha256=plate45.digest(project),
                carrier_assembly_sha256=plate45.digest(stage / 'R47-Key-Carrier-assembly.stl'),
                checks_sha256=plate45.digest(stage / 'r47-checks.json'))
    path.write_text(json.dumps(info, indent=2) + '\n')
    return project


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('build', type=Path)
    a.add_argument('scratch', type=Path)
    args = a.parse_args()
    print(prepare(args.build, args.scratch))
