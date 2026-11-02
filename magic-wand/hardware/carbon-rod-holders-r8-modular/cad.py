#!/usr/bin/env python3
"""R8 separates the sliding battery from the five-key grip; run cad.py to export.

The R7 bought-part interfaces, source CAD and light XIAO holder stay unchanged.
This revision owns its modular frame; preserved R7 exports are never rewritten.
"""
from pathlib import Path
import importlib.util
import json
import math
import sys
import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
def load(name, folder):
    spec=importlib.util.spec_from_file_location('r8_'+name,folder/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module
r7=load('cad',HERE.parent/'carbon-rod-holders-r7-spring-clips')
# Bought interfaces remain owned by the frozen R7 parameters. R8 stores only
# its changed assembly choices; do not maintain two copies of nominal sizes.
P={**r7.P,**json.loads((HERE/'parameters.json').read_text())}
# Compose the frozen interfaces rather than maintaining a second socket model.
for name in ['box','rr','rib','cyl','tube_y','union','mesh','sha','source_hardware','seated_hardware','ring','clip_gap','wire_bus','key_positions']:
    globals()[name]=getattr(r7,name)
r2=r7.r2
OPTIONS={'modular':'Independent sliding modules'}

def key_seat(opening: float | None = None, outer_side: int = 0) -> mf.Manifold:
    # Keep the actual bought-part recess and flange lands. Only soften the
    # exposed floor corners away from the socket and the rear support posts.
    shape=r7.key_seat(opening,outer_side)
    k=P['keys']
    original=rr(15.6,12,1.1,k['socket_floor_bottom'],k['socket_floor_top']).translate((2.5,5.5,0))
    rounded=rr(15.6,12,3,k['socket_floor_bottom'],k['socket_floor_top']).translate((2.5,5.5,0))
    shape-=(original-rounded)^box(-20,20,-2,2.2,-10,0)
    for x in [-7.9,7.9]:
        # A 0.02 mm overcut avoids an enclosed Boolean seam where the old
        # square corner met the load rail; final one-body checks stay strict.
        shape-=box(x-.72,x+.72,8.78,10.42,-4.52,k['plate_bottom']+.62)
        shape+=rib((x,9.6,-4.5),(x,9.6,k['plate_bottom']+.6),.85)
    return shape

def carrier_clip_centres(option: str = 'modular') -> list[float]:
    return [-12,11.5]

def carrier(option: str = 'modular', clip_diameter: float | None = None) -> mf.Manifold:
    k = P['keys']; z = k['pcb_z']; r = P['structure']['rail_radius']
    pieces = [key_seat(outer_side=1 if x > 0 else -1 if x < 0 else 0).translate((x, y, z)) for x, y in key_positions()]
    for row, half in [(0, k['pitch']), (k['row_spacing'], k['upper_half_spacing'])]:
        # Two separated load rails make a shallow truss, rather than relying
        # on one thin rod. The upper centre stays open for Ethan's thumb.
        spans = [(-half - 8.2, half + 8.2)] if row == 0 else [(-half - 8.2, -half + 8.2), (half - 8.2, half + 8.2)]
        for x0, x1 in spans:
            pieces.append(rib((x0, row - 9.4, z + 1.4), (x1, row - 9.4, z + 1.4), r))
            pieces.append(rib((x0, row + 10.5, z - 4.5), (x1, row + 10.5, z - 4.5), r))
    # Deck bridges under the gaps provide a second direct load path between
    # neighbouring seats. Their top shares the mounting plane, below caps.
    for sign in [-1, 1]:
        for yy in [-4, 7.3]:
            pieces.append(box(min(sign*7.8, sign*(k['pitch']-7.8)), max(sign*7.8, sign*(k['pitch']-7.8)), yy-1.5, yy+1.5, z+k['plate_bottom'], z+2.25))
        for dx in [-7.5, 7.5]:
            a=rr(2.5,2.5,.6,z+k['plate_bottom'],z+2.25).translate((sign*(k['pitch']+dx),8.8,0))
            b=rr(2.5,2.5,.6,z+k['plate_bottom'],z+2.25).translate((sign*(k['upper_half_spacing']+dx),k['row_spacing']-8.8,0))
            pieces.append(mf.Manifold.batch_hull([a,b]))
        # Deep, thin webs beside the central ring resist bending/twist. Round
        # rails alone looked connected but left outer seats on a long lever.
        for yy in [-9.4,10.5]:
            pieces.append(box(min(sign*7,sign*k['pitch']),max(sign*7,sign*k['pitch']),yy-.7,yy+.7,z-4.5,z+2.25))
    for sign in [-1, 1]:
        # Outer and inner diagonals connect each top key to the lower row.
        for dx in [-7.8, 7.8]:
            pieces.append(rib((sign * (k['pitch'] + dx), 9.7, z - 4.5),
                              (sign * (k['upper_half_spacing'] + dx), k['row_spacing'] - 8, z + 1.5), 1.2))
        # The inner rear braces sit below the sockets as the upper keys move
        # inward. Keep their centre clear of the battery reserve.
        path = [(sign * 7.8, 10.5, z + 1.0), (sign * 13.6, 14, z - 5.2),
                (sign * 13.6, k['row_spacing'] + 11.5, z - 5.2),
                (sign * (k['upper_half_spacing'] - 8.2), k['row_spacing'] + 11.5, z - 5.2),
                (sign * (k['upper_half_spacing'] - 7.8), k['row_spacing'] + 10.5, z - 5.2)]
        pieces.extend(rib(a, b, 1.2) for a, b in zip(path[:-1], path[1:]))
    for y in [-12, 11.5]:
        for sign in [-1, 1]:
            target_y = -10.5 if y == -12 else 10.5
            pieces.append(rib((sign * 3.8, y, 4.1), (sign * 7.8, target_y, z + 1.1), 1.6))
    # Ethan can reverse this five-key grip. Keep the rounded thumb brace
    # with the keys; the separately sliding cell never carries finger load.
    pieces.append(rib((-7.8, 11.5, z + 1.35), (7.8, 11.5, z + 1.35), 1.3))
    shape = union(pieces)
    # A flat common print face keeps every mounting lip on the bed.
    shape ^= box(-80,80,-90,90,-40,z+2.25)
    rod = P['rod']
    shape -= cyl((rod['diameter'] + rod['diametral_clearance']) / 2, -80, 80).rotate((-90, 0, 0))
    # Keep the rigid frame's generous bore, then add the undersized flexible
    # contact arms. Cutting a full-size bore last would erase their preload.
    shape += union([ring(y,clip_diameter) for y in carrier_clip_centres(option)])
    for y in carrier_clip_centres(option): shape -= clip_gap(y)
    return shape - wire_bus(-80, 80)

def battery_clip_centres() -> list[float]:
    # Keep both clips inside the cell cradle's axial footprint, rather than
    # projecting beyond it on diagonals inherited from the integrated frame.
    b=P['battery'];half=(b['reserve_length']+2*b['clearance_per_side'])/2
    return [-half+1,half-1]

def battery_module(clip_diameter: float | None = None) -> mf.Manifold:
    b=P['battery'];w=b['reserve_width']+2*b['clearance_per_side']
    half=(b['reserve_length']+2*b['clearance_per_side'])/2
    z=b['floor_z']+P['assembly']['battery_floor_raise_mm']
    parts=[]
    for sign in [-1,1]:
        # No projecting tape eyes: wrap two bands through the open floor,
        # around the cell and both side rails, leaving the carbon tube free.
        parts.append(rr(1.4,2*half+2,.7,z-b['floor_thickness'],z+2).translate((sign*(w/2+.7),0,0)))
    for y in [-half-.5,-half/3,half/3,half+.5]:
        parts.append(rib((-w/2,y,z-.7),(w/2,y,z-.7),.7))
    for y in [-half-.5,half+.5]:
        for sign in [-1,1]:
            parts.append(rr(2.8,1.4,.6,z-.7,z+2).translate((sign*(w/2-1.3),y,0)))
    shape=union(parts)
    shape-=cyl((P['rod']['diameter']+P['rod']['diametral_clearance'])/2,-80,80).rotate((-90,0,0))
    shape+=union([ring(y,clip_diameter) for y in battery_clip_centres()])
    for y in battery_clip_centres(): shape-=clip_gap(y)
    return shape-wire_bus(-80,80)

def battery_shape(reserve: bool = False) -> mf.Manifold:
    return r7.battery_shape('lower',reserve).translate((0,36.2,P['assembly']['battery_floor_raise_mm']))

def sensor_holder() -> mf.Manifold:
    return r7.sensor_holder()

def references(option='modular'):
    refs=r7.references('front')
    refs['battery']=battery_shape()
    return refs

def part_shapes() -> dict[str, mf.Manifold]:
    return {'Key_Carrier':carrier(),'Battery_Holder':battery_module(),'XIAO_Rod_Holder':sensor_holder()}

def battery_position(flipped: bool = True, end: str = 'three', extra: float = 0) -> float:
    # Y is the tube axis. 'Three-key end' remains meaningful after turning the
    # key module 180 degrees around Z; screen up/down would be misleading.
    keys=carrier().rotate((0,0,180 if flipped else 0)).bounding_box()
    battery=battery_module().bounding_box()
    sign=(1 if flipped else -1)*(1 if end=='three' else -1)
    gap=P['assembly']['battery_end_clearance']+extra
    return keys[4]+gap-battery[1] if sign>0 else keys[1]-gap-battery[4]

def export() -> None:
    out=HERE/'exports';out.mkdir(exist_ok=True);record={}
    for name,shape in part_shapes().items():
        shape=shape.simplify(.0001);assert shape.status()==mf.Error.NoError,(name,shape.status())
        m=mesh(shape);assert m.is_watertight and len(m.split())==1,name
        m.export(out/(name+'-assembly.stl'))
        oriented=m.copy();rot=trimesh.transformations.rotation_matrix(math.pi,[1,0,0]);oriented.apply_transform(rot)
        shift=trimesh.transformations.translation_matrix(-oriented.bounds[0]);oriented.apply_transform(shift)
        normal=mf.Manifold(mf.Mesh(np.asarray(np.round(oriented.vertices,6),dtype=np.float32),np.asarray(oriented.faces,dtype=np.uint32))).simplify(.000001)
        change=abs(normal.volume()-oriented.volume);assert normal.status()==mf.Error.NoError and change<.01,(name,change)
        mesh(normal).export(out/(name+'.stl'));final=trimesh.load_mesh(out/(name+'.stl'))
        assert final.is_watertight and len(final.split())==1,name
        record[name]={'bounds_mm':m.bounds.tolist(),'volume_mm3':m.volume,'solid_PETG_g':m.volume/1000*P['print']['density_g_cm3'],'stl_float32_volume_change_mm3':change,'body_count':1,'watertight':True,'stl_sha256':sha(out/(name+'.stl')),'print_to_assembly':np.linalg.inv(shift@rot).tolist()}
    dependencies=[HERE/'cad.py',HERE/'parameters.json']+[r7.HERE/path for path in json.loads((r7.HERE/'exports/manifest.json').read_text())['source_sha256']]
    # The base CAD imports this seat helper even when R8 reuses only its
    # primitive/sensor functions; keep that transitive source in provenance.
    dependencies.append(HERE.parent/'printed-loop-wand/shard-tube-r2/direct_switches.py')
    manifest={'revision':P['revision'],'source_sha256':{str(Path(__import__('os').path.relpath(p,HERE))):sha(p) for p in dependencies},'parts':record,'physical_fit_verified':False,'physical_strength_verified':False,'physical_comfort_verified':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print({n:round(r['solid_PETG_g'],3) for n,r in record.items()},flush=True)
if __name__=='__main__': export()
