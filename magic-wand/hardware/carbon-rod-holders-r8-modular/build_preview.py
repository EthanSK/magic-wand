#!/usr/bin/env python3
"""Compose the R8 viewer from the exact exported parts and frozen bought CAD."""
import json
import trimesh
import cad

def data(shape):
    m=shape if isinstance(shape,trimesh.Trimesh) else cad.mesh(shape)
    return {'vertices':m.vertices.round(6).tolist(),'faces':m.faces.tolist()}

def build():
    out=cad.HERE/'exports';manifest=json.loads((out/'manifest.json').read_text())
    geometry={name:data(trimesh.load_mesh(out/(name+'-assembly.stl'))) for name in manifest['parts']}
    geometry.update({name:data(shape) for name,shape in cad.seated_hardware().items()})
    geometry['cap']=data(cad.rr(16.6,17.5,1.4,6.1,9.1))
    geometry['cell']=data(cad.battery_shape())
    geometry['rod']=data(cad.tube_y(3.5,4,-.5,.5))
    refs=cad.references()
    for name in ['pcb','usb','wire']: geometry[name]=data(refs[name])
    geometry['sensor_rod']=data(cad.tube_y(3.5,4,-9,23.4))
    mass=out/'mass-modular.json'
    scene={'geometry':geometry,'manifest':manifest,'parameters':cad.P,'key_positions':cad.key_positions(),
           'mass':json.loads(mass.read_text()) if mass.exists() else None,
           'battery_poses':{orientation:{end:{'y':cad.battery_position(flipped,end),
               'direction':1 if cad.battery_position(flipped,end)>0 else -1} for end in ['three','two']}
               for orientation,flipped in [('three-toward-tip',True),('two-toward-tip',False)]},
           'sources':{'cad_sha256':cad.sha(cad.HERE/'cad.py'),'generator_sha256':cad.sha(cad.HERE/'build_preview.py'),'manifest_sha256':cad.sha(out/'manifest.json')}}
    (out/'review-scene.json').write_text(json.dumps(scene,separators=(',',':')))

if __name__=='__main__': build()
