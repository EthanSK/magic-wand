"""Lay out the complete R59 key-holder kit on one A1 mini plate, each part on its own removable pad.

Nothing is borrowed from an earlier print. Fifteen separately named parts:
  R59               Key_Carrier, Finger_Guard_Left, Finger_Guard_Right, Battery_Cap, OP1_Lid_Stop,
                    Pin_Clip, Pin_Clip_Spare, DFR_Clip_Left, DFR_Clip_Right
  R58, unchanged    Touch_Paddle, Hinge_Pin_Snug, Socket_Backer_Left, Socket_Backer_Right (optional strips)
  R57, unchanged    Hinge_Pin, DFR_Post_Bar
The two flat strips are optional: with a guard off, the lower socket is open to a fingertip.
A strip backs a socket from the side when the guard is left on.

Poses, pad sizes and tab widths of the reused parts are the ones already printed. The guards
print flat, finger side down. The cap prints on its closed end.
"""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
MODEL = HERE / 'exports'
R58 = HARDWARE / 'carbon-rod-holders-r58-smooth-click'
for name in ('carbon-rod-holders-r58-smooth-click', 'carbon-rod-holders-r57-pin-hinge', 'carbon-rod-holders-r56-small-pads'):
    sys.path.insert(0, str(HARDWARE / name))

import plate58 as p58  # noqa: E402  (eased holder base, tower; also puts the R53 to R57 plate tools on the path)
import plate57 as p57  # noqa: E402

LABELS = {
    'Key_Carrier': 'Key holder with guard rails and battery sleeve',
    'Finger_Guard_Left': 'Slide-on finger guard, left',
    'Finger_Guard_Right': 'Slide-on finger guard, right',
    'Battery_Cap': 'Slip-on cap for the battery end',
    'Touch_Paddle': 'Paddle with one long contact bar (R58)',
    'OP1_Lid_Stop': 'OP1 board retainer with lift stop',
    'Hinge_Pin': 'Hinge pin 3.0 mm (R57)',
    'Hinge_Pin_Snug': 'Hinge pin 3.2 mm, optional (R58)',
    'Pin_Clip': 'Pin clip with lowered grip',
    'Pin_Clip_Spare': 'Pin clip with lowered grip, spare',
    'DFR_Post_Bar': 'Two-post bar for the touch board (R57)',
    'DFR_Clip_Left': 'Touch-board post clip 1.4 mm, left',
    'DFR_Clip_Right': 'Touch-board post clip 1.4 mm, right',
    'Socket_Backer_Left': 'Optional backing strip, lower-left socket (R58)',
    'Socket_Backer_Right': 'Optional backing strip, lower-right socket (R58)',
}
# Minimum first-layer areas of the three new pads are 57% of the pad, the ratio the printed pin pad uses (220 of 384 mm2).
# New or moved parts: (mesh folder, bed centre, pad size, (rx, rz), tear tabs, tab width, minimum first-layer area)
PLACEMENTS = {
    'Key_Carrier': (MODEL, (50.5, 155.5), (96, 44), (-90, 0), None, None, 2849),
    'Touch_Paddle': (R58 / 'exports', (139.6, 155.5), (75, 44.5), (180, 90), [(-1, 0), (1, 0)], 3.0, 2849),
    'OP1_Lid_Stop': (MODEL, (31.0, 101.6), (28, 39), (0, 0), [(-1, 0), (1, 0)], 3.1, 840),
    'Finger_Guard_Left': (MODEL, (66.0, 101.6), (26, 28), (0, 0), [(-1, 0), (1, 0)], 3.0, 420),
    'Finger_Guard_Right': (MODEL, (98.0, 101.6), (26, 28), (0, 0), [(-1, 0), (1, 0)], 3.0, 420),
    'Battery_Cap': (MODEL, (130.0, 101.6), (24, 16), (-90, 0), [(-1, 0), (1, 0)], 3.0, 220),
    'Hinge_Pin_Snug': (R58 / 'exports', (97.5, 52.0), (32, 12), (0, 0), [(-1, 0), (1, 0)], 3.0, 220),
    'Pin_Clip': (MODEL, (126.0, 56.0), (15, 15), 'side', [(0, 1)], 3.0, 120),
    'Pin_Clip_Spare': (MODEL, (146.0, 56.0), (15, 15), 'side', [(0, 1)], 3.0, 120),
    'DFR_Clip_Left': (MODEL, (156.0, 94.0), (12, 12), (0, 0), [(0, -1)], 3.0, 100),
    'DFR_Clip_Right': (MODEL, (156.0, 110.0), (12, 12), (0, 0), [(0, -1)], 3.0, 100),
    'Socket_Backer_Left': (R58 / 'exports', (97.5, 70.0), (32, 12), (0, 0), [(-1, 0), (1, 0)], 1.4, 220),
    'Socket_Backer_Right': (R58 / 'exports', (140.0, 74.0), (32, 12), (0, 0), [(-1, 0), (1, 0)], 1.4, 220),
}
# Reused entries keep their body pose and pad; only the bed centre moves.
# The stabilising tower and its 19.6 mm brim fill the corner out to about X 80, Y 66 (the slicer reports a path conflict inside it), so nothing else stands there.
MOVED = {
    'Hinge_Pin': ('r57', (97.5, 35.0)), 'DFR_Post_Bar': ('r57', (150.5, 35.0)),
}
# The left sleeve wall now stands where the R55 outer underside tab met the holder,
# so move that tab onto the plain rim. Shorter front tabs keep the attachment below
# the measured R57 joint area without shrinking the broad adhesion pad.
CARRIER_BASE = dict(p58.CARRIER_BASE, fin_thickness=1.10,
                    ties=[dict(tie, height=2.0) if tie['face'] == '+y'
                          else dict(tie, at=-26.2 if tie['at'] == -24.5 else tie['at'])
                          for tie in p58.CARRIER_BASE['ties']])
MINIMUM_BASE_MM2 = {name: row[6] for name, row in PLACEMENTS.items() if row[6] != 2849}
MINIMUM_BASE_MM2.update(Hinge_Pin=220, DFR_Post_Bar=300)


def placement_parts59(meshes=MODEL):
    parts = []
    for name, (folder, centre, size, pose, ties, width, _minimum) in PLACEMENTS.items():
        mesh = 'Pin_Clip' if name == 'Pin_Clip_Spare' else name
        source = Path(meshes if folder == MODEL else folder) / (mesh + '-assembly.stl')
        if name == 'Key_Carrier':
            assert tuple(CARRIER_BASE['size']) == tuple(size)
            panel = dict(CARRIER_BASE, holder_release='R55')
        else:
            panel = dict(size=size, ties=ties, tie_width=width)
            if name.startswith('DFR_Clip'):
                panel.update(clip_mouth=[0, 1])
        parts.append(dict(name=name, source=source, assembly_to_print=p57.side_pose(source) if pose == 'side' else p57.pose_for(source, *pose),
                          mesh_reference=source.name, bed_center=centre, panel=panel))
    old = {'r57': {entry['name']: entry for entry in p57.placement_parts57()}}
    for name, (origin, centre) in MOVED.items():
        entry = dict(old[origin][name], bed_center=centre)
        parts.append(entry)
    assert {entry['name'] for entry in parts} == set(LABELS)
    return parts


def prepare(layout, meshes=MODEL):
    p57.write_layout(placement_parts59(meshes), layout, p58.TOWER, 'R59 complete key-holder kit', panel_builder=p57.panel_builder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    parser.add_argument('--meshes', type=Path, default=MODEL)
    args = parser.parse_args()
    prepare(args.layout, args.meshes)
