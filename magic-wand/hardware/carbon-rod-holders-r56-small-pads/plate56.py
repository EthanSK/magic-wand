"""Slice the R55 hinge kit with small disposable pads under the small parts."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
R55 = HERE.parent / 'carbon-rod-holders-r55-easy-release'
sys.path.insert(0, str(R55))

from plate55 import TOWER, panel_builder, placement_parts55
from native_layout53 import write_layout

# name -> ((pad X mm, pad Y mm), minimum connected first-layer area mm2).
# Bed centres, bodies, tear tabs and clip mouth lanes stay exactly as R55.
SMALL_PADS = {
    'DFR_Clip_Left': ((12.0, 12.0), 100.0),
    'DFR_Clip_Right': ((12.0, 12.0), 100.0),
    'Hinge_Cap': ((30.0, 14.0), 330.0),
    'DFR_Post_Bar': ((30.0, 17.0), 400.0),
    'OP1_Lid': ((28.0, 39.0), 840.0),
}


def prepare(layout):
    entries = placement_parts55()
    resized = set()
    for entry in entries:
        if entry['name'] in SMALL_PADS:
            size, _minimum_area_mm2 = SMALL_PADS[entry['name']]
            old = entry['panel']['size']
            assert size[0] * size[1] < old[0] * old[1], entry['name']
            entry['panel'] = dict(entry['panel'], size=size)
            resized.add(entry['name'])
    assert resized == set(SMALL_PADS), sorted(set(SMALL_PADS) - resized)
    write_layout(entries, layout, TOWER,
                 'R56 complete hinge kit with small pads',
                 panel_builder=panel_builder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    prepare(parser.parse_args().layout)
