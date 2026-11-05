#!/usr/bin/env python3
"""R13 composes frozen R12 interfaces and reinforces local fixed load paths.

Keep bought interfaces and assembly positions. The added far-end frame and
longitudinal ribs shorten printed bridges and carry loads into the cage rails.
Print transforms are part of this revision, not an implicit slicer auto-orient.
"""
from pathlib import Path
from functools import lru_cache
import importlib.util
import json
import math
import os
import sys
import numpy as np
import trimesh
import manifold3d as mf
import deliverables

HERE = Path(__file__).resolve().parent
def load(name, folder):
    spec = importlib.util.spec_from_file_location('r13_' + name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

base = load('cad', HERE.parent / 'carbon-rod-holders-r12-closer-thumb')
LOCAL = json.loads((HERE / 'parameters.json').read_text())
P = {**base.P, **LOCAL}
OPTIONS = base.OPTIONS
for name in ['box', 'rr', 'rib', 'cyl', 'tube_y', 'union', 'mesh', 'sha',
             'source_hardware', 'seated_hardware', 'ring', 'clip_gap', 'wire_bus',
             'key_positions', 'key_seat', 'carrier_clip_centres', 'carrier',
             'battery_gate', 'battery_shape',
             'external_wire_route', 'sensor_holder', 'references']:
    globals()[name] = getattr(base, name)

def key_post_trim():
    # R12's corner replacement left a detached 0.27 mm leading strip in
    # one sliced layer. Trim only that obsolete remnant, outside the 1.9 mm
    # rounded post and bought interfaces; preserve the real fixed column.
    return box(-9.10,-8.67,8.69,9.03,-4.59,1.205)

def key_seat(opening=None,outer_side=0):
    return close_post_seams((base.key_seat(opening,outer_side)-key_post_trim())+key_load_rails(),[(0,0,0)])

def close_post_seams(shape,positions):
    # The new rail closes R12's tiny post-corner Boolean overcuts. Fill only
    # these measured sealed voids, never a functional opening or fit route.
    bodies=shape.decompose();kept=[]
    for body in bodies:
        if body.volume()>=0:kept.append(body);continue
        lo=np.array(body.bounding_box()[:3]);hi=np.array(body.bounding_box()[3:])
        assert abs(body.volume())<.2,('Unexpected enclosed cavity',body.volume())
        assert any(np.all(lo>=[x+sign*7.9-.9,y+8.6,z-4.5])and
                   np.all(hi<=[x+sign*7.9+.9,y+9.2,z+.1])
                   for x,y,z in positions for sign in [-1,1]),('Cavity outside post seam',lo,hi)
    return union(kept)

@lru_cache(maxsize=1)
def key_load_rails():
    # Ethan's "nothing too weak" includes the entire key-to-clip load path.
    # Keep the mounting land and spring/latch interface; fixed outboard rails
    # connect front and rear bodies without relying on the thin plate rims.
    import working_spaces
    k=P['keys'];r=P['reinforcement'];outer=r['key_load_rail_outer_x_mm']
    pieces=[]
    for lo,hi in [(7.7,outer),(-outer,-7.7)]:
        # Grow the added depth at 45 degrees from the existing front rail,
        # rather than starting its whole underside as a short cantilever.
        lead=box(lo,hi,-9.3,-9.1,.25,1.4)
        full=box(lo,hi,-7.25,-7.05,r['key_load_rail_bottom_mm'],1.4)
        pieces += [mf.Manifold.batch_hull([lead,full]),box(lo,hi,-7.25,10.2,r['key_load_rail_bottom_mm'],1.4)]
    rails=union(pieces)
    keepouts=union([s for n,s in working_spaces.regions('Key_Carrier',None,(1,)).items()if n.startswith('key_1_')])
    carved=rails-keepouts.translate((0,0,-k['pcb_z']))
    bodies=carved.decompose();large=[b for b in bodies if b.volume()>1]
    # The sampled insertion sweep cuts tiny detached lower-edge remnants.
    # They are not load rails and must never become unprintable loose chips.
    assert len(large)==2 and all(abs(b.volume())<.03 for b in bodies if b.volume()<=1)
    return union(large)

def carrier(option: str = 'modular', clip_diameter: float | None = None) -> mf.Manifold:
    # Ethan's "bottom two" are the thumb-side pair. Reinforce only their
    # fixed row joints below the existing mounting plane; all seats stay put.
    shape=base.carrier(option,clip_diameter);k=P['keys'];top=k['pcb_z']+k['plate_bottom']+k['plate_thickness']
    shape-=union([key_post_trim().translate((x,y,k['pcb_z']))for x,y in key_positions()if y])
    bottom=top-P['reinforcement']['upper_joint_depth_mm'];pieces=[shape]
    pieces.extend(key_load_rails().translate((x,y,k['pcb_z']))for x,y in key_positions())
    for sign in [-1,1]:
        for dx in [-7.5,7.5]:
            a=rr(2.5,2.5,.6,bottom,top).translate((sign*(k['pitch']+dx),8.8,0))
            b=rr(2.5,2.5,.6,bottom,top).translate((sign*(k['upper_half_spacing']+dx),k['row_spacing']-8.8,0))
            pieces.append(mf.Manifold.batch_hull([a,b]))
    return close_post_seams(union(pieces),[(x,y,k['pcb_z'])for x,y in key_positions()])

def battery_module(clip_diameter: float | None = None) -> mf.Manifold:
    shape = base.battery_module(clip_diameter)
    b = P['battery']; z = b['floor_z'] + P['assembly']['battery_floor_raise_mm']
    half = (b['reserve_length'] + 2 * b['clearance_per_side']) / 2
    inner = (b['reserve_width'] + 2 * b['clearance_per_side']) / 2
    roof = z + b['reserve_thickness'] + P['battery_cage']['roof_clearance']
    r = P['reinforcement']['battery_rib_radius_mm']
    far = P['reinforcement']['battery_far_frame_y_mm']
    entry = P['reinforcement']['battery_stringer_entry_y_mm']
    x = inner + r
    # Move the far ring to share the actual end-down first layer.
    old_far = base.battery_clip_centres()[-1]
    shape -= cyl(6.0,old_far-1.81,old_far+1.81).rotate((-90,0,0))
    pieces = [shape]
    # Preserve the inner cell envelope while adding material on the outside.
    for y in [-half-.5, -half/3, half/3, half+.5]:
        pieces.append(rib((-x,y,z-r), (x,y,z-r), r))
    for y in [-8,0,8]:
        pieces += [rib((-x,y,roof+r), (x,y,roof+r), r)]
        for sign in [-1,1]:
            pieces.append(rib((sign*x,y,z), (sign*x,y,roof+r), r))
    # The far-end frame prints on the bed. Roof stringers stop behind the
    # gate's upward removal path; a front roof rail would trap the gate.
    for level in [z-r,roof+r]:
        pieces.append(rib((-x,far,level), (x,far,level), r))
        y0 = entry if level > z else -half-.5
        pieces.append(rib((0,y0,level), (0,far,level), r))
        for sign in [-1,1]:
            pieces.append(rib((sign*x,y0,level), (sign*x,far,level), r))
    for sign in [-1,1]:
        pieces.append(rib((sign*x,far,z-r), (sign*x,far,roof+r), r))
    # Strengthen only the outside guide wall. Its slot and complete upward
    # gate route stay fixed. A diagonal carries the tall guide's first face
    # into the existing roof post instead of leaving it cantilevered.
    slot_edge=13.4+P['battery_cage']['gate_slot_width']/2
    outer=slot_edge+P['reinforcement']['gate_guide_outer_wall_mm'];inner_edge=11.8
    for sign in [-1,1]:
        pieces.append(rr(outer-inner_edge,4.4,.6,z-1.4,z+6.6).translate((sign*(outer+inner_edge)/2,-16.3,0)))
        pieces.append(rib((sign*(outer-.6),-14.5,z+6),(sign*(x+1),-8,roof+r),P['reinforcement']['gate_guide_brace_radius_mm']))
    result = union(pieces)
    # New rail material must never refill the inherited gate slots or bore.
    limit = 13.4 + P['battery_cage']['gate_slot_width']/2
    for sign in [-1,1]:
        result -= box(0 if sign>0 else -limit, limit if sign>0 else 0,
                      -17.35,-15.25,z+.35,z+8)
    result -= cyl((P['rod']['diameter'] + P['rod']['diametral_clearance'])/2,
                  -80,80).rotate((-90,0,0))
    result += union([ring(y,clip_diameter) for y in battery_clip_centres()])
    for y in battery_clip_centres():
        result -= clip_gap(y)
    return result - wire_bus(-80,80)

def battery_clip_centres() -> list[float]:
    return [base.battery_clip_centres()[0], P['reinforcement']['battery_far_clip_y_mm']]

def sensor_holder() -> mf.Manifold:
    """Reinforce fixed outer rails and roots without moving PCB bearing faces."""
    shape=base.sensor_holder();z=base.r7.r2.P['sensor']['board_z'];half=base.r7.r2.P['sensor']['board_width']/2
    pieces=[shape]
    for sign in [-1,1]:
        x=sign*(half+.9)
        # Thicken the long fixed rail between the rings, stopping before
        # their free arm regions. Do not change the intended spring profile.
        pieces.append(rib((sign*5.2,-1.4,0),(sign*5.2,19.8,0),1.))
        pieces.append(box(half+.3,half+2.3,1,23.2,z-1.6,z+1.2).mirror((1,0,0)) if sign<0 else box(half+.3,half+2.3,1,23.2,z-1.6,z+1.2))
        for y,yy in [(-4,2),(21.8,21.8)]:
            pieces.append(rib((sign*3.7,y,3.5),(x,yy,z-1.1),1.05))
            pieces.append(rib((0,y,5.15),(x,yy,z-1.1),1.05))
    result=union(pieces)-cyl(4.2,-40,50).rotate((-90,0,0))
    for y in [-3.8,22.2]:
        width=P['rod']['sensor_clip_width']
        result+=ring(y,None,width,P['rod']['sensor_clip_root_wall'])
        result-=clip_gap(y,width)
    return result

def battery_gate(fitted: bool = False) -> mf.Manifold:
    # A thicker central grab bar avoids making the 1.2 mm sliding wedges the
    # handle. Keep the added material outside the pouch and both guides.
    z=P['battery']['floor_z']+P['assembly']['battery_floor_raise_mm']
    return base.battery_gate(fitted)+rib((-10.8,-17.3,z+3),(10.8,-17.3,z+3),.9)

def part_shapes() -> dict[str, mf.Manifold]:
    return {'Key_Carrier':carrier(), 'Battery_Holder':battery_module(),
            'Battery_End_Gate':battery_gate(), 'XIAO_Rod_Holder':sensor_holder()}

def battery_position(flipped: bool = True, extra: float = 0) -> float:
    keys=carrier().rotate((0,0,180 if flipped else 0)).bounding_box()
    battery=battery_module().rotate((0,0,P['assembly']['battery_entry_rotation_z_degrees'])).bounding_box()
    return keys[4] + P['assembly']['battery_end_clearance'] + extra - battery[1]

def export() -> None:
    out=HERE/'exports'; out.mkdir(exist_ok=True); records={}
    for name,shape in part_shapes().items():
        shape=shape.simplify(.0001)
        m=mesh(shape); assert m.is_watertight and len(m.split())==1,name
        m.export(out/(name+'-assembly.stl'))
        # The gate's original common flat face stays on the bed; its new
        # outside grab bar grows upward instead of lifting the wedges.
        angle=-90 if name in {'Battery_Holder','Battery_End_Gate'} else 90
        rotation=trimesh.transformations.rotation_matrix(math.radians(angle),[1,0,0])
        oriented=m.copy(); oriented.apply_transform(rotation)
        shift=trimesh.transformations.translation_matrix(-oriented.bounds[0]); oriented.apply_transform(shift)
        normal=mf.Manifold(mf.Mesh(np.asarray(np.round(oriented.vertices,6),np.float32),np.asarray(oriented.faces,np.uint32))).simplify(.000001)
        change=abs(normal.volume()-oriented.volume)
        assert normal.status()==mf.Error.NoError and change<.01,(name,change)
        mesh(normal).export(out/deliverables.normal_name(name))
        final=trimesh.load_mesh(out/deliverables.normal_name(name))
        assert final.is_watertight and len(final.split())==1,name
        records[name]={'bounds_mm':m.bounds.tolist(),'volume_mm3':m.volume,
                       'solid_PETG_g':m.volume/1000*P['print']['density_g_cm3'],
                       'stl_float32_volume_change_mm3':change,'body_count':1,'watertight':True,
                       'stl_sha256':sha(out/deliverables.normal_name(name)),
                       'print_to_assembly':np.linalg.inv(shift@rotation).tolist()}
    dependencies=[HERE/'cad.py',HERE/'parameters.json',HERE/'working_spaces.py',HERE/'deliverables.py']
    previous=json.loads((base.HERE/'exports/manifest.json').read_text())
    dependencies += [base.HERE/path for path in previous['source_sha256']]
    manifest={'revision':P['revision'], 'source_sha256':{os.path.relpath(p,HERE):sha(p) for p in dependencies},
              'parts':records,'physical_fit_verified':False,'physical_strength_verified':False,
              'physical_comfort_verified':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print({n:round(v['solid_PETG_g'],3) for n,v in records.items()},flush=True)

if __name__=='__main__':
    export()
