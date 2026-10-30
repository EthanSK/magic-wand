#!/usr/bin/env python3
"""R2: reverse USB and route nominal leads beneath the PCB into the tube.

Compose the preserved R1 carrier/frame; dimensions live in parameters.json.
Ethan's 'by the hole' means USB points towards the near sleeve opening (-Y).
Reference wires are a provisional 3 mm bundle, not measured solder geometry.
"""
from pathlib import Path
import importlib.util, json, sys
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'carbon-rod-holders'

def load(name):
    spec=importlib.util.spec_from_file_location('r2_'+name,BASE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    return m

base=load('cad');original_sensor=base.sensor_holder;original_refs=base.references
P=json.loads((HERE/'parameters.json').read_text());base.P=P;base.HERE=HERE
for name in ['union','box','cyl','rr','rib','tube_y','mesh','sha','carrier','ds','C']:
    globals()[name]=getattr(base,name)

def wire_route(radius=None):
    p=P['sensor']['wire_centerline_mm'];r=radius if radius is not None else P['sensor']['wire_bundle_diameter']/2
    return union([rib(a,b,r)for a,b in zip(p,p[1:])])

def sensor_holder():
    # Trim only the nominal lead sweep from the final R1 structural union.
    # The two ring bores and all edge ledges remain at their accepted positions.
    return original_sensor()-wire_route(P['sensor']['wire_bundle_diameter']/2+P['sensor']['wire_clearance'])

def references():
    refs=original_refs();r=P['rod']
    refs['rod']=tube_y(r['inside_diameter']/2,r['diameter']/2,-25,475)
    refs['usb']=refs['usb'].rotate((0,0,180)).translate((0,23.6,0))
    return refs

def export(out):
    base.sensor_holder=sensor_holder;base.references=references
    base.export(out)
    import trimesh
    scene=trimesh.load(out/'Assembly-reference.glb',force='scene')
    w=mesh(wire_route());w.apply_translation((0,451.6,0));w.visual.vertex_colors=[175,74,60,255]
    scene.add_geometry(w,node_name='REFERENCE_provisional_wire_route');scene.export(out/'Assembly-reference.glb')
    path=out/'manifest.json';manifest=json.loads(path.read_text())
    manifest['source_sha256']['../carbon-rod-holders/cad.py']=sha(BASE/'cad.py')
    manifest['revision']=P['revision'];manifest['wire_envelope_measured']=False
    path.write_text(json.dumps(manifest,indent=2)+'\n')

base.sensor_holder=sensor_holder;base.references=references
if __name__=='__main__':export(HERE/'exports')
