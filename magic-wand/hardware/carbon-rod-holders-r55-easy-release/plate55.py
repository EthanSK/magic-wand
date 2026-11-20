"""Slice all seven R53 mechanism parts with the easier-release holder pad."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
R53 = HERE.parent / 'carbon-rod-holders-r53-guided-op1'
R54 = HERE.parent / 'carbon-rod-holders-r54-reinforced-base'
MODEL = R53 / 'exports'
for directory in (R54, R53):
    sys.path.insert(0, str(directory))

from native_layout53 import write_layout
from panel55 import CARRIER_BASE, backed_panel55
from panels53 import backed_panel
from plate53 import LABELS, TOWER, placement_parts


def panel_builder(body, panel):
    if panel.get('holder_release') == 'R55':
        return backed_panel55(body, panel)
    return backed_panel(body, panel)


def placement_parts55():
    entries = placement_parts(MODEL)
    for entry in entries:
        if entry['name'] == 'Key_Carrier':
            assert tuple(CARRIER_BASE['size']) == tuple(entry['panel']['size'])
            entry['panel'] = dict(CARRIER_BASE, holder_release='R55')
    return entries


def prepare(layout):
    entries = placement_parts55()
    write_layout(entries, layout, TOWER, 'R55 complete hinge and OP1 kit',
                 panel_builder=panel_builder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    prepare(parser.parse_args().layout)
