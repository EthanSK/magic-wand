"""Reuse the complete R72 kit and its removable adhesion bases, replacing only the carrier."""
from os.path import relpath
from pathlib import Path
import sys

import design73 as model
import kit72 as previous


def parts():
    rows=previous.parts()
    for row in rows:
        if row['name']=='Key_Carrier':
            row['source']=model.OUT/model.HOLDER
            p=previous.previous
            row['assembly_to_print']=p.printer.pose_for(row['source'],*p.kit64.PRINT_POSES['Key_Carrier'])
        row['mesh_reference']=relpath(row['source'],model.OUT)
    return rows


def layout(path):
    from plate_preview import embed
    p=previous.previous
    p.printer.write_layout(parts(),path,p.kit64.kit63.plate.plate60.prior.p58.TOWER,
                           'R73 complete key holder',panel_builder=p.panel_builder)
    embed(path)


if __name__=='__main__':
    layout(Path(sys.argv[1]))
