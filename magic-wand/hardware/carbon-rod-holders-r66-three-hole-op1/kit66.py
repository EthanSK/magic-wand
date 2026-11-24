"""Complete R66 key-holder plate: the R64 fittings and a new carrier. No loose OP1 seat.

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
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r64-under-entry'))
import kit64  # noqa: E402

import design66  # noqa: E402

printer = kit64.kit63.plate.printer
COMPLETE = kit64.COMPLETE
TITLE = 'R66 key holder with the three-hole OP1 seat and complete fittings'
# R64 rooted one underside fin on the outboard battery wall foot at the bed face (X -24.0).
# R66 ends that wall before the bed face, so the fin moves under the retained spring-root
# post beside it. Every other station, height and the 1.70 mm fin are R64's.
MOVED_TIE = (('-y', -24.0), dict(face='-y', at=-22.68, height=2.4))


def carrier_panel(panel):
    station, replacement = MOVED_TIE
    ties, moved = [], 0
    for tie in panel['ties']:
        if (tie['face'], tie['at']) == station:
            tie, moved = dict(replacement), moved + 1
        ties.append(dict(tie))
    assert moved == 1, 'R64 tie stations changed'
    # The battery mouth itself stays free of base material. At the bed face the leaf is
    # inside its root post, so the reserved box starts just outside the pouch.
    xo, xi = design66.old.PACK_X
    z0, z1 = design66.old.PACK_Z
    mouth = [xo - .20, z0 - .15, xi + .15, z1 + .14]
    keep = [box for box in panel['keep_clear'] if not (abs(box[2] - mouth[2]) < 1e-6 and abs(box[1] - mouth[1]) < 1e-6)]
    assert len(keep) == len(panel['keep_clear']) - 1, 'R63 battery keep-clear box not found'
    return dict(panel, ties=ties, keep_clear=keep + [mouth])


def parts():
    rows = kit64.parts()
    names = [row['name'] for row in rows]
    if set(names) != COMPLETE or len(names) != len(set(names)):
        raise ValueError(f'Incomplete kit: {names}')
    for row in rows:
        if row['name'] == 'Key_Carrier':
            source = OUT / design66.HOLDER
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
