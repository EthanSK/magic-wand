"""Recreate the selected changed-parts plate from its CAD and measured support paths."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import numpy as np
import trimesh

from orient51 import digest, load_solid, oriented
from plate51 import CENTER, compose
from props51 import search

HERE=Path(__file__).resolve().parent
PUBLIC=HERE/'exports'
EVIDENCE=PUBLIC/'print-trial'


def build(output, *, slice_it=False, original=None):
    output.mkdir(parents=True,exist_ok=True)
    props=output/'props';props.mkdir(exist_ok=True)
    control=EVIDENCE/'support-free-control.json'
    path_source=EVIDENCE/'external-prop-paths.json'
    sources=tuple(PUBLIC/n for n in ('Key_Carrier-assembly.stl','DFRobot_Hole_Bracket-assembly.stl'))
    for src,record in zip(sources,json.loads(control.read_text())['parts'].values()):
        assert digest(src)==record['source_sha256'],f"Changed source requires a new support-free comparison: {src.name}"
    body,frame=oriented(load_solid(sources[0]),'rear_down')
    x,y,_,x2,y2,_=body.bounding_box()
    off=np.asarray(CENTER[0])-[(x+x2)/2,(y+y2)/2]
    generation=json.loads(path_source.read_text())
    shapes,verified_paths=search(body,frame,off)
    assert len(shapes)==sum(r['found'] for r in generation)
    for expected,actual in zip(generation,verified_paths):
        assert expected['found']==actual['found'] and expected['xy']==actual['xy']
        if expected['found']:
            assert np.allclose(expected['foot_xy'],actual['foot_xy'],atol=1e-8)
    for i,shape in enumerate(shapes):
        mesh=shape.to_mesh()
        trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False).export(props/f'prop-{i}.stl')
    (props/'props.json').write_text(path_source.read_text())
    layout=output/'R51-changed-parts.3mf'
    compose(sources,('rear_down','front_down'),'clear',layout,PUBLIC/'Battery_End_Door-print.stl',control,props)
    if original:
        with ZipFile(original) as a,ZipFile(layout) as b:
            for file in ('3D/3dmodel.model','Metadata/model_settings.config','Metadata/project_settings.config','Metadata/layer_config_ranges.xml'):
                if file not in a.namelist() and file not in b.namelist():continue
                same=a.read(file)==b.read(file)
                print(file,'identical' if same else 'different',flush=True)
                if not same:raise ValueError(f'{file} differs from selected layout')
    if slice_it:
        runner=HERE.parent/'carbon-rod-holders-r45-open-keyways/slice45.py'
        subprocess.run([sys.executable,str(runner),str(layout),str(output/'R51-changed-parts.gcode.3mf')],check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--slice',action='store_true')
    parser.add_argument('--compare',type=Path,help='Optional original editable layout to compare source data exactly')
    args=parser.parse_args()
    build(args.output,slice_it=args.slice,original=args.compare)
