"""Complete R69 key-holder plate: twelve pieces, three of them new.

New: the key holder, the touch paddle and the OP1 retainer. Unchanged files, poses and bed
positions: standard and snug hinge pins, centre clip and spare, two-post bar, both
touch-board clips and both socket backing strips.

The loose rod grip (Rod_Collet) is no longer printed. R69 grips the rod with the two
rings restored in the holder itself, so there is nothing for the wedge to do. The holder
keeps the tapered rear socket as its rear funnel, and the R64 collet file still fits it.

Base panels. The holder keeps R64's panel exactly, as R68 did: its bed face is unchanged.
The paddle's panel leaves the same open lane for the leads, now from the R69 lead route.
 — Claude Fable 5.2"""
from os.path import relpath
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r68-pre-taper-battery-rail'))
import kit68  # noqa: E402

import design69  # noqa: E402
import hinge69  # noqa: E402

kit64 = kit68.kit64
printer = kit68.printer
DROPPED = {'Rod_Collet'}
COMPLETE = kit68.COMPLETE - DROPPED
NEW = {'Key_Carrier': design69.HOLDER, 'Touch_Paddle': hinge69.PADDLE, 'OP1_Lid_Stop': hinge69.LID}
TITLE = 'R69 key holder with the restored rod grip, short hinge, low retainer and complete fittings'


def layout(path):
    sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r65-op1-seat'))
    from plate_preview import embed
    printer.write_layout(parts(), Path(path), kit64.kit63.plate.plate60.prior.p58.TOWER, TITLE, panel_builder=panel_builder)
    embed(Path(path))


def parts():
    rows = []
    for row in kit68.parts():
        name = row['name']
        if name in DROPPED:
            continue
        row = dict(row)
        if name in NEW:
            source = OUT / NEW[name]
            row['source'] = source
            if name in kit64.PRINT_POSES:
                row['assembly_to_print'] = printer.pose_for(source, *kit64.PRINT_POSES[name])
        if name == 'Key_Carrier':
            row['panel'] = kit68.carrier_panel(row['panel'])
        if name == 'OP1_Lid_Stop':
            # Keep the proven contact area after the lower posts shortened the printed footprint.
            # Found and fixed by GPT-6.1 Sol.
            row['panel'] = dict(row['panel'], size=(29, 39))
        row['mesh_reference'] = relpath(row['source'], OUT)
        rows.append(row)
    names = [row['name'] for row in rows]
    if set(names) != COMPLETE or len(names) != len(set(names)):
        raise ValueError(f'Incomplete kit: {names}')
    return rows


def panel_builder(body, options):
    panel = printer.panel_builder(body, options)
    if options.get('wire_exit'):
        pose = printer.pose_for(OUT / hinge69.PADDLE, *kit64.PRINT_POSES['Touch_Paddle'])
        clearance = hinge69.wired_lead().transform(pose[:3]).project().offset(.65).extrude(1).translate((0, 0, -.2))
        panel -= clearance - body
    return panel

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path, help='destination .3mf; its layout.frame.json is written beside it')
    layout(parser.parse_args().layout)
