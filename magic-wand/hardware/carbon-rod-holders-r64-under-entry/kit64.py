"""Build a complete key-holder plate with all separate hinge and board fittings."""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
R63 = HERE.parent / 'carbon-rod-holders-r63-open-hinge'
sys.path.insert(0, str(R63))
import kit63
import hinge64

HINGE_HARDWARE = {
    'Hinge_Pin', 'Hinge_Pin_Snug', 'Pin_Clip', 'Pin_Clip_Spare',
    'OP1_Lid_Stop', 'DFR_Post_Bar', 'DFR_Clip_Left', 'DFR_Clip_Right',
}
COMPLETE = HINGE_HARDWARE | {
    'Key_Carrier', 'Touch_Paddle', 'Rod_Collet', 'Socket_Backer_Left', 'Socket_Backer_Right',
}
PRINT_POSES = {k: kit63.PRINT_POSES[k] for k in ('Key_Carrier', 'Touch_Paddle', 'Rod_Collet')}


def carrier_panel(panel):
    # On R63 the “base grip” loaded the two 0.8 mm lips at the battery entrance.
    # Put those ties on the solid outer corner post, above and below the root.
    moved = {('-y', -19.2): ('-y', -24.0, 2.4), ('-y', -11.0): ('+y', -23.8, 2.2)}
    ties = []
    for tie in panel['ties']:
        replacement = moved.get((tie['face'], tie['at']))
        if replacement:
            face, station, height = replacement
            tie = dict(face=face, at=station, height=height)
        ties.append(tie)
    return dict(panel, ties=ties)


def parts():
    previous = {p['name']: p for p in kit63.parts()}
    rows = []
    for old in kit63.kit62.parts():
        row = dict(previous.get(old['name'], old))
        if row['name'] == 'Key_Carrier':
            row['panel'] = carrier_panel(row['panel'])
        # The wider backing-strip pad sits between the snug pin and the centre
        # clip. Share the 2 mm spacing adjustment across these two neighbours.
        if row['name'] in ('Hinge_Pin_Snug', 'Socket_Backer_Left'):
            x, y = row['bed_center']
            row['bed_center'] = (x, y + (1.0 if row['name']=='Socket_Backer_Left' else -1.0))
        if row['name'] in ('Hinge_Pin', 'Hinge_Pin_Snug'):
            # Narrow end ties free from the taper without leaving wide tabs
            # across the part of the pin that enters the three hinge bores.
            row['panel'] = dict(row['panel'], tie_width=1.6)
        rows.append(row)
    rows.append(dict(previous['Rod_Collet'], bed_center=(66.0, 99.0)))
    for row in rows:
        if row['name'] in PRINT_POSES:
            src = OUT / row['source'].name
            row.update(source=src, assembly_to_print=kit63.plate.printer.pose_for(src, *PRINT_POSES[row['name']]))
    names = [row['name'] for row in rows]
    if len(names) != len(set(names)) or set(names) != COMPLETE:
        raise ValueError(f'Incomplete or duplicate standalone kit: {names}')
    return rows


def panel_builder(body, options):
    panel = kit63.plate.printer.panel_builder(body, options)
    if options.get("wire_exit"):
        pose = kit63.plate.printer.pose_for(OUT / "Touch_Paddle-assembly.stl", *PRINT_POSES["Touch_Paddle"])
        clearance = hinge64.wired_lead().transform(pose[:3]).project().offset(.65).extrude(1).translate((0, 0, -.2))
        panel -= clearance - body
    return panel


def layout(path):
    kit63.plate.printer.write_layout(parts(), path, kit63.plate.plate60.prior.p58.TOWER,
                                     'R64 complete key holder and hinge fittings',
                                     panel_builder=panel_builder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    layout(parser.parse_args().layout)
