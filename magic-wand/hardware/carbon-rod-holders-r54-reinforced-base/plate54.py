"""Lay out one R53 key holder with the reinforced R54 removable base."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
R53 = HERE.parent / 'carbon-rod-holders-r53-guided-op1'
sys.path.insert(0, str(R53))

from native_layout53 import load_solid, write_layout
from panel54 import TIES, WIRE_LANE, backed_panel54
from plate53 import TOWER, pose_for

CARRIER = R53 / 'exports/Key_Carrier-assembly.stl'
LABELS = {'Key_Carrier': 'Key holder'}
# The two fins on the upper rim stop a layer below the moving keycaps.
BASE = {'size': (100, 50), 'keep_clear': [WIRE_LANE],
        'ties': [dict(tie, height=2.4) if tie['face'] == '+y' else dict(tie)
                 for tie in TIES]}


def prepare(layout):
    carrier = dict(name='Key_Carrier', source=CARRIER,
                   mesh_reference='../../carbon-rod-holders-r53-guided-op1/exports/Key_Carrier-assembly.stl',
                   assembly_to_print=pose_for(CARRIER, -90, 0),
                   bed_center=(96, 135), panel=BASE)
    write_layout([carrier], layout, TOWER, 'Key holder with reinforced base',
                 panel_builder=backed_panel54)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    args = parser.parse_args()
    prepare(args.layout)
