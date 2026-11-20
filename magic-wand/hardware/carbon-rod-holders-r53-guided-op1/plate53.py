"""Pack the complete change on a single A1 mini plate, with seven independent bases."""
import argparse
import math
import os
from pathlib import Path

import numpy as np
from native_layout53 import HERE, HARDWARE, load_solid, write_layout

LABELS = {
    'Key_Carrier': 'Key holder with open hinge seats',
    'Touch_Paddle': 'Paddle with built-in pivot',
    'Hinge_Cap': 'Sliding hinge cap',
    'OP1_Lid': 'OP1 board retainer',
    'DFR_Post_Bar': 'Two-post touch-board bar',
    'DFR_Clip_Left': 'First touch-board clip',
    'DFR_Clip_Right': 'Second touch-board clip',
}
# Centre, pad size, rotation around X and final plan rotation around Z.
# Coordinates describe the plate as seen from above with its front edge at Y=0.
PLACEMENTS = {
    'Key_Carrier': ((50.5,155.5),(96,44),-90,0),
    'Touch_Paddle': ((139.6,155.5),(75,44),180,90),
    'Hinge_Cap': ((97.5,35.0),(48,63.5),180,0),
    'DFR_Post_Bar': ((150.5,35.0),(51.5,63.5),0,0),
    'OP1_Lid': ((31,101.6),(56.5,56.5),0,0),
    'DFR_Clip_Left': ((90.5,101.1),(55,56.5),0,0),
    'DFR_Clip_Right': ((150,101.1),(55.5,56.5),0,0),
}
TOWER = dict(position=(18.9,18.9),brim_mm=16.1,extra_rib_mm=22)


def pose_for(source, rx, rz):
    a,b = map(math.radians,(rx,rz))
    c,s,d,t=[round(n,10) for n in (math.cos(a),math.sin(a),math.cos(b),math.sin(b))]
    pose=np.array([[d,-t*c,t*s,0],[t,d*c,-d*s,0],[0,s,c,0],[0,0,0,1.]],float)
    pose[2,3] -= load_solid(source).transform(pose[:3]).bounding_box()[2]
    return pose


def placement_parts(meshes):
    """Return the seven independent pieces and their packed bed poses."""
    parts=[]
    for name,(centre,size,rx,rz) in PLACEMENTS.items():
        is_clip = name in ('DFR_Clip_Left','DFR_Clip_Right')
        if is_clip:
            side=name.rsplit('_',1)[1].lower()
            source=HARDWARE/'carbon-rod-holders-r48-edge-click/exports/guide'/f'dfr-clip-{side}.stl'
        else:
            source=meshes/(name+'-assembly.stl')
        panel=dict(size=size,ties=[(-1,0),(1,0)],tie_width=3.1)
        if is_clip:
            panel.update(clip_mouth=[0,1],ties=[(0,-1)],tie_width=3.0)
        parts.append(dict(name=name,source=source,assembly_to_print=pose_for(source,rx,rz),
                          mesh_reference=os.path.relpath(source,HERE/"exports") if is_clip else source.name,
                          bed_center=centre,panel=panel))
    return parts


def prepare(meshes, layout):
    write_layout(placement_parts(meshes),layout,TOWER,'OP1 holder and open hinge')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('meshes',type=Path)
    p.add_argument('layout',type=Path)
    a=p.parse_args()
    prepare(a.meshes,a.layout)
