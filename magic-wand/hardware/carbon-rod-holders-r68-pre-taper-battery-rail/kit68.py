"""Complete R68 key-holder plate: the R67 kit with the new carrier on R64's battery ties.

Thirteen pieces: key holder, touch paddle, split rod grip, standard and snug hinge pins,
centre clip and spare, the existing slide-in OP1 retainer, two-post bar, both touch-board
clips and both socket backing strips. Only the carrier mesh is new; every other part is
the identical R64/R67 file in the same print pose and bed position.

Base panel: R68 restores the pre-taper battery rail, so the carrier panel is R64's exactly.
R64 moved R63's two fins off the 0.8 mm battery lips (where R63 took heavy twisting to free)
onto the solid outer corner: one under the outboard wall foot (X -24.0) and one on the
battery roof plate (X -23.8). The R63 keep-clear box keeps every fin out of the pouch mouth
and off the spring-root post face. R66 and R67 moved those fins only because their taper
had removed that corner.
"""
from os.path import relpath
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r67-diagonal-battery-corner'))
import kit67  # noqa: E402

import design68  # noqa: E402

kit64 = kit67.kit64
printer = kit67.printer
COMPLETE = kit67.COMPLETE
TITLE = 'R68 key holder with the full battery rail and complete fittings'
# The two battery-corner fins, as R64 placed them on the pre-taper rail.
CORNER_TIES = (dict(face='-y', at=-24.0, height=2.4), dict(face='+y', at=-23.8, height=2.2))


def carrier_panel(panel):
    """R64's carrier panel, unchanged; checked to hold both corner fins."""
    for tie in CORNER_TIES:
        assert tie in panel['ties'], ('R64 battery-corner fin missing', tie)
    return dict(panel)


def parts():
    rows = kit64.parts()
    names = [row['name'] for row in rows]
    if set(names) != COMPLETE or len(names) != len(set(names)):
        raise ValueError(f'Incomplete kit: {names}')
    for row in rows:
        if row['name'] == 'Key_Carrier':
            source = OUT / design68.HOLDER
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
