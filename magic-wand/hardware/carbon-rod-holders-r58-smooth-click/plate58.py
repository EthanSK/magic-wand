"""Lay out the R58 pieces on one A1 mini plate, each on its own removable pad.

The key carrier, paddle, lift-stop retainer, socket backing strips and optional snug pin print on separate pads.
The standard pin, pin clip and touch-board fittings can be reused from R57.
"""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r57-pin-hinge'))

import plate57 as p  # noqa: E402  (also puts the R53 to R55 plate tools on the path)

LABELS = {
    'Key_Carrier': 'Key holder with flush seats and battery tray',
    'Touch_Paddle': 'Paddle with one long contact bar',
    'OP1_Lid_Stop': 'OP1 board retainer with lift stop',
    'Hinge_Pin_Snug': 'Hinge pin 3.2 mm (optional)',
    'Socket_Backer_Left': 'Backing strip for the lower-left socket',
    'Socket_Backer_Right': 'Backing strip for the lower-right socket',
}
# Ethan found the holder base secure but a little hard to remove. Ease each rim tab
# by half one nozzle width, preserving the wide pad and open hinge bay.
wire_clear, hinge_bay = p.CARRIER_BASE['keep_clear']
x0, y0, x1, y1 = hinge_bay
# Keep deposited beads out of the bay as well as the CAD pad.
CARRIER_BASE = dict(p.CARRIER_BASE, fin_thickness=1.47,
                    keep_clear=[wire_clear, [x0 - .5, y0 - .5, x1 + .5, y1]])
TOWER = dict(p.TOWER, position=(22.4, 22.4), brim_mm=19.6)
# name: (bed centre, pad size, (rx, rz), tear tabs, tab width, minimum connected first-layer area)
PLACEMENTS = {
    'Key_Carrier': ((50.5, 155.5), (96, 44), (-90, 0), None, None, 2849),
    'Touch_Paddle': ((139.6, 155.5), (75, 44.5), (180, 90), [(-1, 0), (1, 0)], 3.0, 2849),
    'OP1_Lid_Stop': ((31.0, 101.6), (28, 39), (0, 0), [(-1, 0), (1, 0)], 3.1, 840),
    'Hinge_Pin_Snug': ((97.5, 35.0), (32, 12), (0, 0), [(-1, 0), (1, 0)], 3.0, 220),
    'Socket_Backer_Left': ((68.0, 101.6), (32, 12), (0, 0), [(-1, 0), (1, 0)], 1.4, 220),
    'Socket_Backer_Right': ((107.0, 101.6), (32, 12), (0, 0), [(-1, 0), (1, 0)], 1.4, 220),
}
MINIMUM_BASE_MM2 = {name: row[5] for name, row in PLACEMENTS.items() if row[5] != 2849}


def placement_parts58(meshes=MODEL):
    parts = []
    for name, (centre, size, pose, ties, width, _minimum) in PLACEMENTS.items():
        source = Path(meshes) / (name + '-assembly.stl')
        if name == 'Key_Carrier':
            assert tuple(CARRIER_BASE['size']) == tuple(size)
            panel = dict(CARRIER_BASE, holder_release='R55')
        else:
            panel = dict(size=size, ties=ties, tie_width=width)
        parts.append(dict(name=name, source=source, assembly_to_print=p.pose_for(source, *pose), mesh_reference=source.name,
                          bed_center=centre, panel=panel))
    return parts


def prepare(layout, meshes=MODEL):
    p.write_layout(placement_parts58(meshes), layout, TOWER, 'R58 carrier, paddle, stop retainer, snug pin and socket backers',
                   panel_builder=p.panel_builder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    parser.add_argument('--meshes', type=Path, default=MODEL)
    args = parser.parse_args()
    prepare(args.layout, args.meshes)
