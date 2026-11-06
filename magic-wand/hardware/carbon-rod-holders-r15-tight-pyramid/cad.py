#!/usr/bin/env python3
"""R15 composes frozen R12 interfaces and reinforces local fixed load paths.

Keep bought interfaces; centre two upper keys over the lower three. The added far-end frame and
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

if __name__ == '__main__':
    # working_spaces imports "cad". Reuse this module instead of executing a
    # second full copy (about 160 MB of imports, hardware and caches).
    sys.modules.setdefault('cad', sys.modules[__name__])

HERE = Path(__file__).resolve().parent
def load(name, folder):
    spec = importlib.util.spec_from_file_location('r15_' + name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

base = load('cad', HERE.parent / 'carbon-rod-holders-r12-closer-thumb')
LOCAL = json.loads((HERE / 'parameters.json').read_text())
P = {**base.P, **LOCAL, 'keys':{**base.P['keys'],**LOCAL['key_layout']},
     'assembly':{**base.P['assembly'],**LOCAL['assembly']}}
# Frozen R12 functions read their module parameters; one merged layout owns both.
base.P = P
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
        # Tighter neighbouring frames merge at their rear post seams and
        # upper front edges. Close only small sealed internal voids there;
        # all bought interfaces and complete insertion routes are rechecked.
        post=abs(body.volume())<.3 and any(np.all(lo>=[x+sign*7.9-.9,y+8.6,z-4.5])and
                   np.all(hi<=[x+sign*7.9+.9,y+9.2,z+.3])
                   for x,y,z in positions for sign in [-1,1])
        front=abs(body.volume())<.04 and any(y and np.all(lo>=[x-.3,y-9.51,z-2.5])and
                   np.all(hi<=[x+.3,y-8.8,z-1.7])for x,y,z in positions)
        numerical=abs(body.volume())<1e-7 and np.max(hi-lo)<.01
        assert post or front or numerical,('Cavity outside sealed frame seams',body.volume(),lo,hi)
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
    # Exactly the rails minus key 1's complete working spaces, moved to this
    # local seat; the 189-pose socket routes are subtracted pose by pose.
    keepouts={n:s.translate((0,0,-k['pcb_z']))for n,s in working_spaces.regions('Key_Carrier',None,(1,)).items()if n.startswith('key_1_')}
    carved=working_spaces.carve(rails,keepouts,'key_load_rails')
    bodies=carved.decompose();large=[b for b in bodies if b.volume()>1]
    # The sampled insertion sweep cuts tiny detached lower-edge remnants.
    # They are not load rails and must never become unprintable loose chips.
    assert len(large)==2 and all(abs(b.volume())<.03 for b in bodies if b.volume()<=1)
    return union(large)

def front_plane() -> float:
    return P['finger_recess']['front_plane_y_mm']

def carrier_clip_centres(option: str = 'modular') -> list[float]:
    # The front clip's leading face shares the recessed front plane (the print
    # bed). R12's ring sat 5.8 mm further out, where the index finger wraps.
    return [front_plane()+P['rod']['ring_width']/2, base.carrier_clip_centres(option)[-1]]

def plate_top() -> float:
    k=P['keys'];return k['pcb_z']+k['plate_bottom']+k['plate_thickness']

def references(option: str = 'modular') -> dict:
    # The cap's 17.5 mm side lies along the switch stem-post axis (X): sourced
    # Choc V1 posts are 5.7 mm apart along X and Adafruit 5737 stem sockets
    # lie along its wider side. R7's reference was rotated. Size is inferred
    # from the same-family 5111 listing, not measured on Ethan's caps.
    refs=base.references(option);c=P['cap_clearance_screen'];z=P['keys']['pcb_z']
    for i,(x,y) in enumerate(key_positions()):
        refs[f'key_{i}_cap']=rr(c['reference_width_mm'],c['reference_length_mm'],1.4,z+6.1,z+9.1).translate((x,y,0))
    return refs

def chin() -> tuple:
    f=P['finger_recess'];y0=front_plane()
    zf,yl,zl=f['chin_front_z_mm'],f['chin_back_y_mm'],f['chin_bottom_z_mm']
    assert abs((zf-zl)-(yl-y0))<1e-9,'The finger-relief chin must stay at 45 degrees'
    return y0,zf,yl,zl

def bumper_half() -> float:
    return P['keys']['pitch']+P['finger_recess']['bumper_key_offset_mm']

def front_bumper(half=None) -> mf.Manifold:
    # Ethan: the "frame edge below the bottom row" must be recessed and
    # comfortable. One continuous bar, behind the cap fronts, replaces the
    # protruding round rail, deep webs and leg ends. Its lower front is a
    # 45-degree chin receding 1.7 mm, the finger relief this front-down print
    # can make without supports. A lip shelf below the switch housing
    # restores the bar's depth behind that chin and rejoins the front clip
    # ties the chin notches. Its neck stays at least 0.85 mm thick so the
    # first lip layer prints instead of vanishing as a sliver.
    f=P['finger_recess'];y0,zf,yl,zl=chin();y1=f['bumper_back_y_mm'];z1=plate_top()
    ct=f['top_edge_chamfer_mm'];zt=f['lip_top_z_mm'];yb=f['lip_back_y_mm'];half=half or bumper_half()
    assert zt-(zf-(y1-y0))>=.85-1e-9,'Lip neck behind the bumper would print as a vanishing sliver'
    assert yb>yl
    return prism_yz([(y0,zf),(yl,zl),(yb,zl),(yb,zt),(y1,zt),(y1,z1),(y0+ct,z1),(y0,z1-ct)],-half,half)

def chin_cut() -> mf.Manifold:
    # Everything under the 45-degree chin, above its lowest edge: rail heads,
    # leg remnants and tie ends must not poke out below the softened bar.
    y0,zf,yl,zl=chin()
    return prism_yz([(y0-1,zl),(yl,zl),(y0-1,zf+1)],-40,40)

def clip_crown_chamfer(clip_diameter=None) -> mf.Manifold:
    # Soften only the front clip's FIXED crown edge between its two ties.
    # The free spring arms, bore, gap and friction profile stay unchanged.
    f=P['finger_recess'];c=f['clip_crown_edge_chamfer_mm'];hw=f['clip_crown_chamfer_half_width_mm']
    outer=(clip_diameter or P['rod']['clip_diameter'])/2+P['rod']['clip_root_wall'];y0=front_plane()
    band=cyl(outer+.2,0,c+.01)-mf.Manifold.cylinder(c+.01,outer-c,outer+.01,128)
    return band.rotate((-90,0,0)).translate((0,y0,0))^box(-hw,hw,y0-1,y0+c+1,0,10)

def spine_layouts() -> dict:
    # One definition of both fixed spines, shared by the CAD and the strength
    # audit's neck scan. Each spine is the hull of a crown seed inside its
    # clip ring and a root box in the socket floor, minus the rigid rod bore.
    f=P['finger_recess'];k=P['keys'];half=f['spine_half_width_mm'];upper=k['row_spacing']-.5
    front,rear=carrier_clip_centres()[0],carrier_clip_centres()[-1]
    return {'front':{'ring_y_mm':front,'crown_y_mm':front,'root_y_mm':(-1.6,-.3),'root_x_mm':(-half,half)},
            'rear':{'ring_y_mm':rear,'crown_y_mm':rear+f['rear_spine_crown_y_offset_mm'],
                    'root_y_mm':(upper-.5,upper+.3),'root_x_mm':tuple(f['rear_spine_root_x_mm'])}}

def spine_crown(y: float) -> mf.Manifold:
    # Reviewer N16: the former flat crown box (Z 4.3-5.2) left a neck of about
    # 1.2 mm where each spine leaves its clip ring, below the 1.25 mm screen.
    # Seed the crown up to an arc just inside the ring's own outer crown, and
    # slightly lower, so the hull stays thicker than that through the neck.
    # The seed lies wholly inside the fixed ring crown; the free spring arms,
    # bore, gap and friction profile are unchanged.
    f=P['finger_recess'];rod=P['rod'];hw=f['spine_crown_half_width_mm'];r=f['spine_crown_outer_radius_mm']
    corner=math.atan2(math.sqrt(r*r-hw*hw),hw);inner=rod['clip_diameter']/2
    outer=inner+rod['clip_tip_wall']+(rod['clip_root_wall']-rod['clip_tip_wall'])*((math.sin(corner)+1)/2)**2
    assert r<=outer-.03,('Spine crown seed must stay inside the fixed ring crown',r,outer)
    return box(-hw,hw,y-.1,y+.1,f['spine_crown_bottom_z_mm'],r)^cyl(r,-80,80).rotate((-90,0,0))

def fixed_spine(name: str) -> mf.Manifold:
    # Hull of the crown seed and the floor root. Its sides stay at or below
    # 45 degrees in the rod-vertical print. The caller subtracts the rod bore.
    k=P['keys'];s=spine_layouts()[name];hw=P['finger_recess']['spine_crown_half_width_mm']
    floor0=k['pcb_z']+k['socket_floor_bottom'];floor1=k['pcb_z']+k['socket_floor_top']
    (x0,x1),(r0,r1),y=s['root_x_mm'],s['root_y_mm'],s['crown_y_mm']
    # The steepest side runs from the seed's rear corner to the root's front corner.
    rise=r0-(y+.1)
    assert max(-x0-hw,x1-hw)<rise,(name,'Fixed spine sides must stay at or below 45 degrees')
    return mf.Manifold.batch_hull([spine_crown(y),box(x0,x1,r0,r1,floor0,floor1)])

def rear_floor_spine() -> mf.Manifold:
    # Reviewer N12: the upper-left socket floor began as a free tongue, and
    # the right floor as an island on its aid. Grow a tapered fixed spine
    # from inside the rear clip crown into both upper floor fronts, above the
    # rod and below every upper switch/socket route.
    rod=P['rod']
    return fixed_spine('rear')-cyl((rod['diameter']+rod['diametral_clearance'])/2,-80,80).rotate((-90,0,0))

def prism_yz(points,x0,x1):
    # Extrude a counter-clockwise YZ outline along X.
    solid=mf.Manifold.extrude(mf.CrossSection([points]),x1-x0)
    return solid.transform(np.array([[0,0,1,x0],[1,0,0,0],[0,1,0,0]],dtype=float))

def prism_xy(points,z0,z1):
    return mf.Manifold.extrude(mf.CrossSection([points]),z1-z0).translate((0,0,z0))

def front_ring_ties() -> mf.Manifold:
    # Two flat-fronted diagonals start on the bed and carry the front clip
    # into the fixed load rails and bumper. A tapered spine joins the clip
    # crown to the central socket floor, above the rod and below every
    # socket/switch route. The lower spring arms stay free.
    f=P['finger_recess'];r=f['ring_tie_radius_mm'];y=f['ring_tie_y_mm']
    pieces=[rib((sign*3.8,y,4.1),(sign*f['ring_tie_outer_x_mm'],y,f['ring_tie_outer_z_mm']),r)for sign in [-1,1]]
    # recessed_front subtracts the rod bore from this spine.
    pieces.append(fixed_spine('front'))
    return union(pieces)

def front_edge_cuts() -> mf.Manifold:
    # Soften the bumper's top edge (outside the flat flange lands) and both
    # outer front corners. Each cut is a 45-degree plane on the bed edge.
    # Bounded triangular prisms; only the front edge material lies inside them.
    f=P['finger_recess'];y0=front_plane();z1=plate_top();ct=f['top_edge_chamfer_mm']
    top=prism_yz([(y0-3,z1-ct-3),(y0+ct+3,z1+3),(y0-3,z1+3)],-40,40)
    x0=outer_corner_cut_x()
    corner=prism_xy([(x0-3,y0-3),(x0+5,y0-3),(x0+5,y0+5)],-20,30)
    return union([top,corner,corner.mirror((1,0,0))])

def outer_corner_cut_x() -> float:
    # The outer rails begin exactly on the bed at this X, then grow at 45 degrees.
    return P['keys']['pitch']+P['finger_recess']['outer_corner_cut_key_offset_mm']

def recessed_front(shape,positions,option='modular',clip_diameter=None,bumper_half=None):
    # Remove everything ahead of the recessed front plane: R12's front clip,
    # its diagonals, the round front rail, deep webs and leg ends.
    k=P['keys'];f=P['finger_recess'];ahead=box(-80,80,-80,front_plane(),-80,80)
    shape=shape-ahead
    # The trimmed R7 front legs leave tapered teeth below the bumper. Remove
    # them there, retaining the fixed load-rail leads and every new tie.
    rails=union([key_load_rails().translate((x,y,k['pcb_z']))for x,y in positions if not y])
    shape-=box(-40,40,front_plane()-1,front_plane()+1.4,-10,f['chin_bottom_z_mm'])-rails
    rod=P['rod'];front_clip=carrier_clip_centres(option)[0]
    added=union([front_bumper(bumper_half),front_ring_ties()-ahead])
    added-=cyl((rod['diameter']+rod['diametral_clearance'])/2,-80,80).rotate((-90,0,0))
    shape=(shape+added)-chin_cut()-front_edge_cuts()
    # As in R12: keep the generous rigid bore, then add the undersized
    # flexible arms and cut their gap; never cut a full bore through them.
    shape+=ring(front_clip,clip_diameter)
    shape-=clip_crown_chamfer(clip_diameter)
    shape-=clip_gap(front_clip)
    return shape-wire_bus(-80,80)

@lru_cache(maxsize=4)
def carrier(option: str = 'modular', clip_diameter: float | None = None) -> mf.Manifold:
    # Ethan's "pyramid" puts two keys centred toward the tip above three.
    # Keep R13 fixed load rails and deeper joints below the mounting plane.
    # The lower edge is recessed behind the cap fronts; see recessed_front.
    shape=base.carrier(option,clip_diameter);k=P['keys'];top=plate_top()
    shape-=union([key_post_trim().translate((x,y,k['pcb_z']))for x,y in key_positions()if y])
    bottom=top-P['reinforcement']['upper_joint_depth_mm'];pieces=[shape]
    pieces.extend(key_load_rails().translate((x,y,k['pcb_z']))for x,y in key_positions())
    for sign in [-1,1]:
        for dx in [-7.5,7.5]:
            a=rr(2.5,2.5,.6,bottom,top).translate((sign*(k['pitch']+dx),8.8,0))
            b=rr(2.5,2.5,.6,bottom,top).translate((sign*(k['upper_half_spacing']+dx),k['row_spacing']-8.8,0))
            pieces.append(mf.Manifold.batch_hull([a,b]))
    pieces.append(rear_floor_spine())
    joined=recessed_front(union(pieces),key_positions(),option,clip_diameter)
    result=close_post_seams(joined,[(x,y,k['pcb_z'])for x,y in key_positions()])
    # Ethan's closer rows/keys make adjacent fixed frames overlap. Carve the
    # complete bought-part and loading spaces from the FINAL joined solid,
    # so a neighbour's rail cannot refill another key's socket or switch.
    # The sampled socket routes are subtracted pose by pose (exactly the same
    # result) so their swept envelope is never built in empty space.
    import working_spaces
    return working_spaces.carve(result,working_spaces.regions('Key_Carrier',clip_diameter),f'carrier:{option}:{clip_diameter}')

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
    import working_spaces
    manifest={'revision':P['revision'], 'source_sha256':{os.path.relpath(p,HERE):sha(p) for p in dependencies},
              'parts':records,'physical_fit_verified':False,'physical_strength_verified':False,
              'physical_comfort_verified':False,
              'working_space_carve':working_spaces.CARVE_LOG,
              'working_space_method':'Sampled socket routes are exact unions of all their poses, subtracted from material pose by pose; no swept 3D union and no cropping.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print({n:round(v['solid_PETG_g'],3) for n,v in records.items()},flush=True)

if __name__=='__main__':
    export()
