"""Standalone R60 plate, including both detachable backers and the spare pin clip."""
import argparse
from pathlib import Path

import design60 as design
import plate59 as prior

REMOVED = {'Battery_Cap', 'Finger_Guard_Left', 'Finger_Guard_Right'}
LABELS = {name: title for name, title in prior.LABELS.items() if name not in REMOVED}
LABELS['Key_Carrier'] = 'Key holder with integral rounded guards and battery rails'
MINIMA = {name: value for name, value in prior.MINIMUM_BASE_MM2.items() if name in LABELS}


def parts():
    result = []
    for row in prior.placement_parts59():
        if row['name'] not in LABELS:
            continue
        if row['name'] == 'Key_Carrier':
            src = design.OUT / 'Key_Carrier-assembly.stl'
            rotation = prior.p57.pose_for(src, -90, 0)
            # Keep every tear-off fin away from the battery's bearing surfaces.
            panel = dict(row['panel'], fin_thickness=1.35)
            panel['ties'] = [dict(t, at=-23.1) if t['at']==-14.2 else t for t in panel['ties']]
            row = dict(row, source=src, assembly_to_print=rotation, panel=panel)
        result.append(row)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    args = parser.parse_args()
    prior.p57.write_layout(parts(),args.layout,prior.p58.TOWER,'R60 integral finger beams',
                           panel_builder=prior.p57.panel_builder)
