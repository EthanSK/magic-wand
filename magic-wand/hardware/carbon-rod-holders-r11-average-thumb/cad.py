#!/usr/bin/env python3
"""R11 returns to a compact average-thumb opening, with the battery above.

The R7 switch/socket interfaces and spring profiles are reused. This revision
owns the compact frame, battery cage and external-wire sensor support; preserved
R7 exports are never rewritten.
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
    spec=importlib.util.spec_from_file_location('r11_'+name,folder/(name+'.py'))
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module
r7=load('cad',HERE.parent/'carbon-rod-holders-r7-spring-clips')
# Bought interfaces remain owned by the frozen R7 parameters. R11 stores only
# its changed assembly choices; do not maintain two copies of nominal sizes.
LOCAL=json.loads((HERE/'parameters.json').read_text())
P={**r7.P,**LOCAL,'keys':{**r7.P['keys'],**LOCAL['key_layout']}}
# Compose the frozen interfaces rather than maintaining a second socket model.
for name in ['box','rr','rib','cyl','tube_y','union','mesh','sha','source_hardware','seated_hardware','ring','clip_gap','wire_bus']:
    globals()[name]=getattr(r7,name)
r2=r7.r2
OPTIONS={'modular':'Compact thumb opening and slide-in battery cage'}

def key_positions():
    k=P['keys'];return [(-k['pitch'],0),(0,0),(k['pitch'],0),(-k['upper_half_spacing'],k['row_spacing']),(k['upper_half_spacing'],k['row_spacing'])]

def key_seat(opening: float | None = None, outer_side: int = 0) -> mf.Manifold:
    # Keep the actual bought-part recess and flange lands. Only soften the
    # exposed floor corners away from the socket and the rear support posts.
    shape=r7.key_seat(opening,outer_side)
    k=P['keys']
    original=rr(15.6,12,1.1,k['socket_floor_bottom'],k['socket_floor_top']).translate((2.5,5.5,0))
    rounded=rr(15.6,12,3,k['socket_floor_bottom'],k['socket_floor_top']).translate((2.5,5.5,0))
    shape-=(original-rounded)^box(-20,20,-2,2.2,-10,0)
    for x in [-7.9,7.9]:
        # The widened diagonal meets this replaced post corner. A bounded
        # overcut removes its microscopic sealed Boolean seam; the rounded
        # replacement post remains and final one-body checks stay strict.
        shape-=box(x-.78,x+.78,8.72,10.48,-4.58,k['plate_bottom']+.68)
        shape+=rib((x,9.6,-4.5),(x,9.6,k['plate_bottom']+.6),.95)
        # Keep the tiny replacement foot closed against the floor when a
        # diagonal crosses this corner. Without it, the final union enclosed
        # a microscopic void. This is below the socket recess.
        shape+=rr(1.8,.6,.2,k['socket_floor_bottom'],k['socket_floor_bottom']+.6).translate((x,8.85,0))
    return shape

# Ethan's "bottom two" are the side pair at local +Y, below the row of three
# in the default 180-degree turned assembly. Size their opening from the real
# inner seat/floor reach, not only the narrower illustrative keycaps.
e=P['ergonomics']
e['opening_width_mm']=e['design_thumb_width_mm']+2*e['side_clearance_mm']
inner_reach=max(key_seat(outer_side=-1).bounding_box()[3],
                -key_seat(outer_side=1).bounding_box()[0],
                8.2+P['structure']['rail_radius'])
P['keys']['upper_half_spacing']=math.ceil((inner_reach+e['opening_width_mm']/2)/e['spacing_grid_mm'])*e['spacing_grid_mm']

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
        # The old battery-driven inner braces are gone. Two short bridges
        # and diagonal load paths join each aligned side key to the main row.
    for y in [-12, 11.5]:
        for sign in [-1, 1]:
            target_y = -10.5 if y == -12 else 10.5
            pieces.append(rib((sign * 3.8, y, 4.1), (sign * 7.8, target_y, z + 1.1), 1.6))
    # No extra thumb bar projects into the space between the two side keys.
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
        # Compact side rails join the open floor, roof hoops and end guides.
        parts.append(rr(1.4,2*half+2,.7,z-b['floor_thickness'],z+2).translate((sign*(w/2+.7),0,0)))
    for y in [-half-.5,-half/3,half/3,half+.5]:
        parts.append(rib((-w/2,y,z-.7),(w/2,y,z-.7),.7))
    for y in [-half-.5,half+.5]:
        for sign in [-1,1]:
            if y>0:parts.append(rr(2.8,1.4,.6,z-.7,z+2).translate((sign*(w/2-1.3),y,0)))
    roof=z+b['reserve_thickness']+P['battery_cage']['roof_clearance']
    for y in [-8,0,8]:
        for sign in [-1,1]:parts.append(rib((sign*12.5,y,z),(sign*12.5,y,roof+.7),.7))
        parts.append(rib((-12.5,y,roof+.7),(12.5,y,roof+.7),.7))
    # The distal stop is outside the pouch reserve; leads can leave above it.
    for sign in [-1,1]:parts.append(rib((sign*4,half+.5,z+3),(sign*12.5,half+.5,z+3),.9))
    for sign in [-1,1]:parts.append(rib((sign*12.5,half+.5,z+1),(sign*12.5,half+.5,z+3),.7))
    for sign in [-1,1]:
        guide=rr(3.2,4.4,.6,z-1.4,z+6.6).translate((sign*13.4,-16.3,0))
        parts.append(guide)
    shape=union(parts)
    # Cut the guide route after the rail union, so a side rail cannot refill
    # its lower end and obstruct the gate. The pouch reserve stays untouched.
    limit=13.4+P['battery_cage']['gate_slot_width']/2
    for sign in [-1,1]:shape-=box(0 if sign>0 else -limit,limit if sign>0 else 0,-17.35,-15.25,z+.35,z+8)
    shape-=cyl((P['rod']['diameter']+P['rod']['diametral_clearance'])/2,-80,80).rotate((-90,0,0))
    shape+=union([ring(y,clip_diameter) for y in battery_clip_centres()])
    for y in battery_clip_centres(): shape-=clip_gap(y)
    return shape-wire_bus(-80,80)

def battery_gate(fitted: bool = False) -> mf.Manifold:
    """A removable end bar; wedges act on the guides, never on the pouch."""
    z=P['battery']['floor_z']+P['assembly']['battery_floor_raise_mm']
    width=P['battery_cage']['gate_fitted_width' if fitted else 'gate_relaxed_width']/2
    pieces=[]
    for sign in [-1,1]:
        x=sign*13.4;lo=z+.5;hi=z+7.3
        points=[(x-.6,lo),(x+.6,lo),(x+width,lo+.8),(x+width,lo+1.8),(x+.6,hi),
                (x-.6,hi),(x-width,lo+1.8),(x-width,lo+.8)]
        profile=mf.CrossSection([points]).offset(-.08).offset(.08)
        pieces.append(mf.Manifold.extrude(profile,1.6).rotate((90,0,0)).translate((0,-15.5,0)))
    # The broad XZ face prints flat; all pieces share the same 1.6 mm depth.
    pieces.append(rr(28.0,1.8,.8,-.8,.8).rotate((90,0,0)).translate((0,-16.3,z+3)))
    return union(pieces)

def battery_shape(reserve: bool = False) -> mf.Manifold:
    return r7.battery_shape('lower',reserve).translate((0,36.2,P['assembly']['battery_floor_raise_mm']))

def external_wire_route(radius=1.5):
    # A provisional external loom beside the PCB and rod. Exact solder-pad
    # bends are unmeasured; no part of this reference enters the carbon tube.
    points=[(-12,20,4),(-12,-10,4),(-7,-18,2),(-7,-27,2)]
    return union([rib(a,b,radius) for a,b in zip(points[:-1],points[1:])])

def sensor_holder() -> mf.Manifold:
    # Start before R2's internal wire cut. The original board orientation has
    # USB at +Y, towards the tip/computer, away from the keys at -Y.
    shape=r2.original_sensor();p=P['rod'];width=p['sensor_clip_width']
    for y in [-3.8,22.2]:
        shape-=tube_y(4.19,5.41,y-width/2-.01,y+width/2+.01)
        shape+=ring(y,None,width,p['sensor_clip_root_wall'])
        for sign in [-1,1]:shape+=rib((sign*3.5,y,3.5),(sign*4.5,y,4.2),.65)
        shape-=clip_gap(y,width)
    return shape

def references(option='modular'):
    refs=r2.original_refs()
    refs['battery']=battery_shape()
    for i,(x,y) in enumerate(key_positions()):
        for name,shape in seated_hardware().items():refs[f'key_{i}_{name}']=shape.translate((x,y,P['keys']['pcb_z']))
        refs[f'key_{i}_cap']=rr(16.6,17.5,1.4,6.1,9.1).translate((x,y,P['keys']['pcb_z']))
    refs['wire']=external_wire_route()
    return refs

def part_shapes() -> dict[str, mf.Manifold]:
    return {'Key_Carrier':carrier(),'Battery_Holder':battery_module(),'Battery_End_Gate':battery_gate(),'XIAO_Rod_Holder':sensor_holder()}

def battery_position(flipped: bool = True, extra: float = 0) -> float:
    # Ethan's "above the keys" means +Y toward the tip/computer, regardless
    # of which key row points that way. The grip remains below the keys.
    keys=carrier().rotate((0,0,180 if flipped else 0)).bounding_box()
    battery=battery_module().rotate((0,0,P['assembly']['battery_entry_rotation_z_degrees'])).bounding_box()
    gap=P['assembly']['battery_end_clearance']+extra
    return keys[4]+gap-battery[1]

def export() -> None:
    out=HERE/'exports';out.mkdir(exist_ok=True);record={}
    for name,shape in part_shapes().items():
        shape=shape.simplify(.0001);assert shape.status()==mf.Error.NoError,(name,shape.status())
        m=mesh(shape);assert m.is_watertight and len(m.split())==1,name
        m.export(out/(name+'-assembly.stl'))
        oriented=m.copy();rot=trimesh.transformations.rotation_matrix(math.pi/2 if name=='Battery_End_Gate' else math.pi,[1,0,0]);oriented.apply_transform(rot)
        shift=trimesh.transformations.translation_matrix(-oriented.bounds[0]);oriented.apply_transform(shift)
        normal=mf.Manifold(mf.Mesh(np.asarray(np.round(oriented.vertices,6),dtype=np.float32),np.asarray(oriented.faces,dtype=np.uint32))).simplify(.000001)
        change=abs(normal.volume()-oriented.volume);assert normal.status()==mf.Error.NoError and change<.01,(name,change)
        mesh(normal).export(out/(name+'.stl'));final=trimesh.load_mesh(out/(name+'.stl'))
        assert final.is_watertight and len(final.split())==1,name
        record[name]={'bounds_mm':m.bounds.tolist(),'volume_mm3':m.volume,'solid_PETG_g':m.volume/1000*P['print']['density_g_cm3'],'stl_float32_volume_change_mm3':change,'body_count':1,'watertight':True,'stl_sha256':sha(out/(name+'.stl')),'print_to_assembly':np.linalg.inv(shift@rot).tolist()}
    coupons=out/'fit-coupons';coupons.mkdir(exist_ok=True)
    easy=mesh(battery_gate(True));easy.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));easy.apply_translation(-easy.bounds[0])
    assert easy.is_watertight and len(easy.split())==1
    easy.export(coupons/'Battery-Gate-easier-fit.stl')
    dependencies=[HERE/'cad.py',HERE/'parameters.json',HERE/'ergonomics.json']+[r7.HERE/path for path in json.loads((r7.HERE/'exports/manifest.json').read_text())['source_sha256']]
    # The base CAD imports this seat helper even when R11 reuses only its
    # primitive/sensor functions; keep that transitive source in provenance.
    dependencies.append(HERE.parent/'printed-loop-wand/shard-tube-r2/direct_switches.py')
    manifest={'revision':P['revision'],'source_sha256':{str(Path(__import__('os').path.relpath(p,HERE))):sha(p) for p in dependencies},'parts':record,'fit_coupons':{'fit-coupons/Battery-Gate-easier-fit.stl':sha(coupons/'Battery-Gate-easier-fit.stl')},'physical_fit_verified':False,'physical_strength_verified':False,'physical_comfort_verified':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print({n:round(r['solid_PETG_g'],3) for n,r in record.items()},flush=True)
if __name__=='__main__': export()
