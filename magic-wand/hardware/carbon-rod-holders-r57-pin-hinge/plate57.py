"""Lay out the changed R57 pieces on one A1 mini plate, each with its own removable pad.

On the plate: key holder (R55 open-bay base), touch paddle, hinge pin, pin clip and one spare,
longer post bar, and two optional tall post clips. The OP1 lid and both 0.8 mm post clips are
unchanged and are reused from the earlier print.
"""
import argparse
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
HARDWARE = HERE.parent
MODEL = HERE / 'exports'
for name in ('carbon-rod-holders-r55-easy-release', 'carbon-rod-holders-r54-reinforced-base',
             'carbon-rod-holders-r53-guided-op1'):
    sys.path.insert(0, str(HARDWARE / name))

from native_layout53 import load_solid, write_layout  # noqa: E402
from panel55 import CARRIER_BASE, backed_panel55  # noqa: E402
from panels53 import backed_panel  # noqa: E402
from plate53 import TOWER, pose_for  # noqa: E402

LABELS = {
    'Key_Carrier': 'Key holder with two hinge holes',
    'Touch_Paddle': 'Paddle with hinge barrel',
    'Hinge_Pin': 'Hinge pin',
    'Pin_Clip': 'Pin clip',
    'Pin_Clip_Spare': 'Pin clip (spare)',
    'DFR_Post_Bar': 'Two-post bar with longer necks',
    'DFR_Tall_Clip_A': 'Tall post clip (optional)',
    'DFR_Tall_Clip_B': 'Tall post clip (optional)',
}
# name: (mesh, bed centre, pad size, pose, tear tabs, minimum connected first-layer area)
# Poses: (rx, rz) in degrees as in the R53 plate, or 'side' for a part laid on its flat side.
PLACEMENTS = {
    'Key_Carrier': ('Key_Carrier', (50.5, 155.5), (96, 44), (-90, 0), None, 2849),
    # 0.5 mm deeper than the R53 pad: the lighter R57 paddle left the 75 x 44 pad 13 mm2 short of 2849.
    # Grown in Y only, away from the holder pad, so the 3.4 mm gap between the two pads is unchanged.
    'Touch_Paddle': ('Touch_Paddle', (139.6, 155.5), (75, 44.5), (180, 90), [(-1, 0), (1, 0)], 2849),
    'DFR_Post_Bar': ('DFR_Post_Bar', (150.5, 35.0), (32, 18), (90, 0), [(-1, 0), (1, 0)], 300),
    'Hinge_Pin': ('Hinge_Pin', (97.5, 35.0), (32, 12), (0, 0), [(-1, 0), (1, 0)], 220),
    'Pin_Clip': ('Pin_Clip', (31.0, 101.6), (15, 15), 'side', [(0, 1)], 120),
    'Pin_Clip_Spare': ('Pin_Clip', (62.0, 101.6), (15, 15), 'side', [(0, 1)], 120),
    'DFR_Tall_Clip_A': ('DFR_Tall_Clip', (93.0, 101.1), (12, 12), (0, 0), [(0, -1)], 100),
    'DFR_Tall_Clip_B': ('DFR_Tall_Clip', (124.0, 101.1), (12, 12), (0, 0), [(0, -1)], 100),
}
MINIMUM_BASE_MM2 = {name: row[5] for name, row in PLACEMENTS.items() if row[5] != 2849}


def side_pose(source):
    """Assembly X becomes the print height: the pin clip lies on its flat face."""
    pose = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1.]], float)
    pose[2, 3] -= load_solid(source).transform(pose[:3]).bounding_box()[2]
    return pose


def panel_builder(body, panel):
    if panel.get('holder_release') == 'R55':
        return backed_panel55(body, panel)
    return backed_panel(body, panel)


def placement_parts57(meshes=MODEL):
    parts = []
    for name, (mesh, centre, size, pose, ties, _minimum) in PLACEMENTS.items():
        source = Path(meshes) / (mesh + '-assembly.stl')
        if name == 'Key_Carrier':
            assert tuple(CARRIER_BASE['size']) == tuple(size)
            panel = dict(CARRIER_BASE, holder_release='R55')
        else:
            panel = dict(size=size, ties=ties, tie_width=3.0)
            if mesh == 'DFR_Tall_Clip':
                panel.update(clip_mouth=[0, 1])
        matrix = side_pose(source) if pose == 'side' else pose_for(source, *pose)
        parts.append(dict(name=name, source=source, assembly_to_print=matrix, mesh_reference=source.name,
                          bed_center=centre, panel=panel))
    return parts


def prepare(layout, meshes=MODEL):
    write_layout(placement_parts57(meshes), layout, TOWER, 'R57 pin hinge and longer posts',
                 panel_builder=panel_builder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path)
    parser.add_argument('--meshes', type=Path, default=MODEL)
    args = parser.parse_args()
    prepare(args.layout, args.meshes)
