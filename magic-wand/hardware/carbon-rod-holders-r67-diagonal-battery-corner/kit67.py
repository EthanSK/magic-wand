"""Complete R67 key-holder plate: the R66 kit with the new carrier.

Thirteen pieces: key holder, touch paddle, split rod grip, standard and snug hinge pins,
centre clip and spare, the existing slide-in OP1 retainer, two-post bar, both touch-board
clips and both socket backing strips. Only the carrier mesh is new.
"""
from os.path import relpath
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r66-three-hole-op1'))
import kit66  # noqa: E402

import design67  # noqa: E402

kit64 = kit66.kit64
printer = kit66.printer
COMPLETE = kit66.COMPLETE
TITLE = 'R67 key holder with the diagonal battery corner and complete fittings'
# The diagonal cut removes the bed-face corner where two R66 fins were rooted: one under the
# spring-root post (X -22.68) and one on the battery roof plate (X -23.8). Both move onto the
# plastic that remains at the bed face. Heights and the 1.70 mm fin are unchanged.
MOVED_TIES = {('-y', -22.68): dict(face='-y', at=-22.4, height=2.4),
              ('+y', -23.8): dict(face='+y', at=-22.0, height=2.2)}


def carrier_panel(panel):
    panel = kit66.carrier_panel(panel)
    ties, moved = [], 0
    for tie in panel['ties']:
        replacement = MOVED_TIES.get((tie['face'], tie['at']))
        if replacement:
            tie, moved = dict(replacement), moved + 1
        ties.append(dict(tie))
    assert moved == len(MOVED_TIES), 'R66 tie stations changed'
    return dict(panel, ties=ties)


def parts():
    rows = kit64.parts()
    names = [row['name'] for row in rows]
    if set(names) != COMPLETE or len(names) != len(set(names)):
        raise ValueError(f'Incomplete kit: {names}')
    for row in rows:
        if row['name'] == 'Key_Carrier':
            source = OUT / design67.HOLDER
            row.update(source=source, panel=carrier_panel(row['panel']),
                       assembly_to_print=printer.pose_for(source, *kit64.PRINT_POSES['Key_Carrier']))
        row['mesh_reference'] = relpath(row['source'], OUT)
    return rows


def panel_builder(body, options):
    return kit64.panel_builder(body, options)


def layout(path):
    # Reuse the headless plate previews from the preceding complete holder kit.
    sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r65-op1-seat'))
    from plate_preview import embed
    printer.write_layout(parts(), Path(path), kit64.kit63.plate.plate60.prior.p58.TOWER, TITLE,
                         panel_builder=panel_builder)
    embed(Path(path))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path, help='destination .3mf; its layout.frame.json is written beside it')
    layout(parser.parse_args().layout)
