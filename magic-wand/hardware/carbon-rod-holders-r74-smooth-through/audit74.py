"""Probe both ends of the new battery slot against actual Bambu extrusion."""
import json
from pathlib import Path
import sys

import kit74
import audit72


def routes():
    groups = audit72.routes()
    holder = groups['Key_Carrier']
    # Use the same allowance for the spring and finite bead resolution as the
    # checked R72 seated gauge. Extend it through the front opening in one piece.
    seated = holder['battery_seated'][0]
    x0, _, z0, x1, _, z1 = seated.bounding_box()
    _, ymin, _, _, ymax, _ = kit74.kit73.model.b.load(kit74.OUT / kit74.HOLDER).bounding_box()
    holder['battery_end_to_end'] = [audit72.a.b.box(x0, x1, ymin - 1., ymax + 1., z0, z1)]
    return groups


def audit(folder):
    old = kit74.kit73.model
    ref = json.loads((old.design.OUT / 'print-mechanisms/r70-base-reference.json').read_text())
    base = audit72.a.a61
    base.audit(folder, kit74.parts, kit74.OUT, expected_names=kit74.base_plate.COMPLETE,
               route_builder=routes, spring_probe=audit72.spring_opening, base_minima=dict(base.MINIMA),
               expected_fin_count=5, seam_layers=25, seam_reference_area_mm2=ref['reference_area_mm2'])
    path = folder / 'fin-design.json'
    fins = json.loads(path.read_text())
    fins['removal'] = json.loads((old.OUT / 'print-mechanisms' / path.name).read_text())['removal']
    path.write_text(json.dumps(fins, indent=2) + '\n')


if __name__ == '__main__':
    audit(Path(sys.argv[1]))
