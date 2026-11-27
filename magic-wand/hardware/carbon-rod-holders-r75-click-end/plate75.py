"""Prepare and inspect the R75 carrier with its eight compatible kit pieces."""
from os.path import relpath
from pathlib import Path
import sys
import json
import design75 as design
import kit74
import audit74

OUT = design.OUT


def parts(carrier_dir=OUT):
    rows = kit74.parts()
    for row in rows:
        if row['name'] == 'Key_Carrier':
            row['source'] = carrier_dir / design.HOLDER
            row['assembly_to_print'] = kit74.base_plate.printer.pose_for(
                row['source'], *kit74.base_plate.kit64.PRINT_POSES['Key_Carrier'])
        row['mesh_reference'] = relpath(row['source'], carrier_dir)
    return rows


def layout(folder):
    folder.mkdir(parents=True, exist_ok=True)
    kit74.layout(folder / 'layout.3mf', parts(), title='R75 click-end finger rest')


def audit(folder):
    base = audit74.audit72.a.a61
    reference = json.loads((design.prior.r71.OUT / 'print-mechanisms/r70-base-reference.json').read_text())
    base.audit(folder, parts, OUT, expected_names=kit74.base_plate.COMPLETE,
               route_builder=audit74.routes, spring_probe=audit74.audit72.spring_opening,
               base_minima=dict(base.MINIMA), expected_fin_count=5, seam_layers=25,
               seam_reference_area_mm2=reference['reference_area_mm2'])


if __name__=='__main__':
    {'layout':layout, 'audit':audit}[sys.argv[1]](Path(sys.argv[2]))
