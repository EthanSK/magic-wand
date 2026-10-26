"""Geometric fit checks; this does not simulate PETG force or establish physical fit."""
from pathlib import Path
import importlib.util,json,math,hashlib,numpy as np
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('print_v4_cad',HERE/'wand_cad.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
base,cover=c.head_base(),c.head_cover();clip=c.board_release_clip();guides=c.board_corner_guides()
board=c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,c.BOARD0+21.)
# A static solid test: clear at rest; stops reached after designed small clearances.
checks={'resting_board_overlap_mm3':(base^board).volume(),'body_cover_overlap_mm3':(base^cover).volume()}
checks['rigid_board_stop_overlap_mm3']={}
for name,delta in {'left':(-.4,0,0),'right':(.4,0,0),'up':(0,0,.4),'down':(0,0,-.4),'out_of_seats':(0,.5,0)}.items():
 checks['rigid_board_stop_overlap_mm3'][name]=(base^board.translate(delta)).volume()
# Board removal is a pivot around the USB end after the lower spring is deflected.
# Flex is NOT simulated: explicitly subtract the spring envelope for this clearance test.
rigid=base-clip;pivot=(0,c.BOARD_Y+c.BOARD_T/2,c.BOARD0+21.)
checks['released_board_pivot_overlap_mm3']={}
for a in [0,1,2,3,5,8,10]:
 moved=board.translate(tuple(-v for v in pivot)).rotate((a,0,0)).translate(pivot)
 checks['released_board_pivot_overlap_mm3'][str(a)]=(rigid^moved).volume()
checks['cover_released_slide_overlap_mm3']={str(d):(base^(cover-c.latch_nub()).translate((0,d*c.SLIDE_SLOPE,d))).volume() for d in [.25,.5,1,2,5,10,20,35]}
plug=c.box(-6,6,c.BOARD_Y-1,c.BOARD_Y+5,c.BOARD0+21.2,412.)
solder=c.box(-5.4,5.4,c.BOARD_Y-6,c.BOARD_Y-.25,c.BOARD0+3,c.BOARD0+18)
checks['usb_12x6_plug_overlap_mm3']={'base':(base^plug).volume(),'cover':(cover^plug).volume()}
checks['rear_solder_space_overlap_mm3']={'base':(base^solder).volume(),'cover':(cover^solder).volume()}
checks['head_9mm_wire_probe_overlap_mm3']=(base^c.cyl(4.5,352.5,374.8)).volume()
checks['head_forward_6mm_wire_probe_overlap_mm3']=(base^c.cyl(3.,374.7,388.,y=2.)).volume()
loop=c.hollow_loop()[0]
checks['thumb_mount']={}
for hand,angle in [('left',90),('right',-90)]:
 # Purchased 17.5 x 16.6 cap, including its whole 3 mm stroke envelope.
 cap=c.local(c.box(-8.3,8.3,13.,21.2,-8.75,8.75),angle,129.)
 checks['thumb_mount'][hand]={'loop_overlap_mm3':(cap^loop).volume(),'minimum_loop_gap_mm':cap.min_gap(loop,15),'includes':'purchased slim keycap footprint plus 3mm stroke envelope; insert is deliberately recessed into the grip'}
# Geometric deflection envelope only: no force, strength, or print tolerance simulation.
mesh=clip.refine_to_length(.7).to_mesh();v=np.array(mesh.vert_properties[:,:3],dtype=np.float32)
v[:,2]-=1.3*np.maximum(0,1-(v[:,0]/10.)**2)**2
flexed=c.Manifold(c.mf.Mesh(v,np.asarray(mesh.tri_verts,dtype=np.uint32)))
checks['flexed_clip_status']=str(flexed.status())
checks['board_pivot_with_1_3mm_clip_deflection_mm3']={}
for a in [0,1,2,3,5,8,10]:
 moved=board.translate(tuple(-v for v in pivot)).rotate((a,0,0)).translate(pivot)
 checks['board_pivot_with_1_3mm_clip_deflection_mm3'][str(a)]=(flexed^moved).volume()
checks['physical_fit_verified']=False

assert abs(checks['resting_board_overlap_mm3'])<.0001
assert all(v>0 for v in checks['rigid_board_stop_overlap_mm3'].values())
assert all(abs(v)<.001 for v in checks['released_board_pivot_overlap_mm3'].values())
assert all(abs(v)<.001 for v in checks['cover_released_slide_overlap_mm3'].values())
assert all(abs(v)<.001 for v in checks['usb_12x6_plug_overlap_mm3'].values())
assert all(p['minimum_loop_gap_mm']>=1.9 and abs(p['loop_overlap_mm3'])<.001 for p in checks['thumb_mount'].values())

assert all(abs(v)<.001 for v in checks['board_pivot_with_1_3mm_clip_deflection_mm3'].values())
assert abs(checks['head_forward_6mm_wire_probe_overlap_mm3'])<.001

# Keep the printed V2 handle and cap reusable; new slim joints have three cams.
old=c.existing_handle();adapter=c.lower_shaft(140.)
checks['existing_handle_locked_overlap_mm3']=(old^adapter).volume()
checks['new_handle_locked_overlap_mm3']=(c.handle_left()^c.lower_shaft()).volume()
checks['slim_joint']={}
for name,male,female,z in [('middle',c.lower_shaft(),c.upper_shaft(),c.MID),('head',c.upper_shaft(),base,c.TOP)]:
 region=c.box(-20,20,-20,20,z-1,z+16.)
 male=male^region;female=female^region
 probes={}
 for a in [-38,-30,-20,-10,0,5]:probes[str(a)]=(c.b.spin(male,a)^female).volume()
 insertion={str(d):(c.b.spin(male,-38).translate((0,0,-d))^female).volume() for d in [14,10,5,1,0]}
 pull=(male.translate((0,0,-2.))^female).volume()
 checks['slim_joint'][name]={'cam_path_overlap_mm3':probes,'entry_insertion_mm3':insertion,'locked_pull_overlap_mm3':pull,'wire_9_9mm_overlap_mm3':(female^c.cyl(4.95,z-1,z+15.)).volume()}
 assert max(insertion.values())<.001, (name,'entry blocked',insertion)
 assert probes['0']<1. and probes['5']>probes['0']+1., (name,'stop',probes)
 assert pull>1., (name,'no retaining ledge')
 assert all(probes[str(a)]<1.5 for a in [-38,-30,-20,-10,0]),(name,'cam interference excessive',probes)
assert checks['existing_handle_locked_overlap_mm3']<1.
assert checks['new_handle_locked_overlap_mm3']<1.
checks['envelopes']={'new_length_mm':410,'old_length_mm':340,'main_bore_mm':10.4,'span_minimum_wall_mm':1.2,'slim_spigot_wall_mm':1.4,'slim_socket_groove_wall_mm':1.2,'loop_shell_mm':1.6,'grip_shell_mm':1.2,'diamond_edge_round_mm':c.TIP_ROUND}
checks['cover_side_pull_blocked_mm3']={str(d):(base^(cover-c.latch_nub()).translate((0,d,0))).volume() for d in [.3,.5,1.]}
assert checks['cover_side_pull_blocked_mm3']['.5' if '.5' in checks['cover_side_pull_blocked_mm3'] else '0.5']>1.,'Dovetail does not capture side pull'
checks['compact_button_insert']={}
for name,angle,z in c.HAND_BUTTONS:
 h=c.handle_left();insert=c.cassette_on_handle(c.socket_carrier()+c.socket_keeper(),angle,z)
 # Pure radial motion into/out of its seat. Side release flex is not modelled.
 a=math.radians(angle);axis=(math.sin(a),math.cos(a),0.)
 checks['compact_button_insert'][name]={'rest_overlap_mm3':(h^insert).volume(),'rear_stop_overlap_mm3':(h^insert.translate(tuple(-.5*x for x in axis))).volume(),'front_lip_overlap_mm3':(h^insert.translate(tuple(.5*x for x in axis))).volume()}
 assert abs(checks['compact_button_insert'][name]['rest_overlap_mm3'])<.01
 assert checks['compact_button_insert'][name]['rear_stop_overlap_mm3']>1.
 assert checks['compact_button_insert'][name]['front_lip_overlap_mm3']>.1
checks['shaft_taper']={}
for start in [140.,c.HANDLE_END]:
 zs=np.linspace(start,c.TOP,1001);rs=np.array([c.shaft_radius(z,start) for z in zs])
 checks['shaft_taper'][str(start)]={'start_diameter_mm':2*rs[0],'middle_diameter_mm':2*c.shaft_radius(c.MID,start),'top_diameter_mm':2*rs[-1],'maximum_outward_step_mm':float(np.max(np.diff(rs)))}
 assert np.max(np.diff(rs))<=1e-8,'Shaft widens towards the head'
checks['helix_material_probe_mm3']={}
for label,part,z in [('lower',c.lower_shaft(),201.),('upper',c.upper_shaft(),301.)]:
 angle=float(c.b.rib_angle(z,0));r=c.shaft_radius(z)+.75
 probe=c.Manifold.sphere(.12,12).translate((r*math.sin(math.radians(angle)),r*math.cos(math.radians(angle)),z))
 checks['helix_material_probe_mm3'][label]=(part^probe).volume()
 assert checks['helix_material_probe_mm3'][label]>.002,'Helix missing from generated part'
checks['thin_hollow_shaft_overlap_mm3']={}
for label,part,z in [('lower',c.lower_shaft(),211.),('upper',c.upper_shaft(),301.)]:
 probe=c.cyl(c.shaft_radius(z)-1.3,z-.05,z+.05)
 checks['thin_hollow_shaft_overlap_mm3'][label]=(part^probe).volume()
 assert checks['thin_hollow_shaft_overlap_mm3'][label]<.001,'Shaft core is filled rather than thin-walled'
print(json.dumps(checks,indent=2))
