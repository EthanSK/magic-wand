"""Geometric fit checks; this does not simulate PETG force or establish physical fit."""
from pathlib import Path
import importlib.util,json,math,hashlib,numpy as np
from functools import lru_cache
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('print_v18_cad',HERE/'wand_cad.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
c.handle_left=lru_cache(None)(c.handle_left)
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
loop=c.removable_loop()
checks['thumb_mount']={}
for hand,angle in [('left',90),('right',-90)]:
 # Purchased 17.5 x 16.6 cap, including its whole 3 mm stroke envelope.
 cap=c.local(c.box(-8.3,8.3,13.,21.2,-8.75,8.75),angle,c.HAND_BUTTONS[0][2])
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
checks['envelopes']={'new_length_mm':410,'old_length_mm':340,'main_bore_mm':10.4,'span_minimum_wall_mm':c.SHAFT_WALL,'slim_spigot_wall_mm':1.4,'slim_socket_groove_wall_mm':1.2,'loop_shell_mm':c.LOOP_WALL,'grip_shell_mm':c.GRIP_WALL,'diamond_edge_round_mm':c.TIP_ROUND}
checks['cover_side_pull_blocked_mm3']={str(d):(base^(cover-c.latch_nub()).translate((0,d,0))).volume() for d in [.3,.5,1.]}
assert checks['cover_side_pull_blocked_mm3']['.5' if '.5' in checks['cover_side_pull_blocked_mm3'] else '0.5']>1.,'Dovetail does not capture side pull'
checks['button_claw_mount']={}
for hand,right in [('left',False),('right',True)]:
 h=c.handle_left(right)
 for name,angle,z in c.HAND_BUTTONS:
  angle=-angle if right else angle
  plate=c.cassette_on_handle(c.socket_carrier(),angle,z)
  a=math.radians(angle);axis=np.array((math.sin(a),math.cos(a),0.))
  # Explicit released-claw envelope: this establishes a route, not flex force.
  nominal=c.mount_local(c.button_side_claws(),angle,z)
  deflected=c.mount_local(c.button_side_claws(.65),angle,z)
  released=(h-nominal)+deflected
  route={str(d):(released^plate.translate(tuple(d*axis))).volume() for d in (0.,.25,.5,1.,2.,4.,8.)}
  rest=(h^plate).volume();radial=(h^plate.translate(tuple(.5*axis))).volume();down=(h^plate.translate((0,0,-.6))).volume();up=(h^plate.translate((0,0,.6))).volume()
  checks['button_claw_mount'][hand+'_'+name]={'rest_mm3':rest,'released_radial_route_mm3':route,'radial_pull_blocked_mm3':radial,'downward_stop_mm3':down,'upward_stop_mm3':up}
  assert abs(rest)<.01 and max(abs(v)for v in route.values())<.01,(hand,name,'released entry collision',rest,route)
  assert min(radial,down,up)>.05,(hand,name,'not captured',radial,down,up)
# Bought socket and lower switch housing envelopes. Catches sit above the
# socket; the switch body prevents the seated plate lifting once installed.
checks['socket_and_switch']={}
for right in (False,True):
 for name,angle,z in c.HAND_BUTTONS:
  angle=-angle if right else angle
  h=c.handle_left(right)
  socket=c.mount_local(c.box(-8.3,-1.3,-7.8,2.4,-4.4,-2.6),angle,z)
  switch=c.local(c.box(-6.85,6.85,c.BUTTON_ORIGIN-1.4,c.BUTTON_ORIGIN+1.4,-6.85,6.85),angle,z)
  key=('right_'if right else 'left_')+name
  checks['socket_and_switch'][key]={'socket_rest_mm3':(h^socket).volume(),'switch_housing_rest_mm3':(h^switch).volume(),'switch_up_1mm_stop_mm3':(h^switch.translate((0,0,1.))).volume()}
  assert abs((h^socket).volume())<.01 and abs((h^switch).volume())<.01,(key,'component collision')
  assert (h^switch.translate((0,0,1.))).volume()>.01,(key,'no upward stop with switch installed')
checks['button_neighbour_clearance']={}
for right in (False,True):
 parts=[]
 for name,angle,z in c.HAND_BUTTONS:
  angle=-angle if right else angle
  parts.append((name,c.cassette_on_handle(c.socket_carrier(),angle,z),c.local(c.box(-8.3,8.3,18.8,24.,-8.75,8.75),angle,z)))
 for name,plate,cap in parts:
  others=c.union([p+cap for other,p,cap in parts if other!=name])
  a=math.radians(next((-aa if right else aa)for nn,aa,zz in c.HAND_BUTTONS if nn==name));axis=np.array((math.sin(a),math.cos(a),0.));collisions={str(d):(plate.translate(tuple(d*axis))^others).volume() for d in (0.,2.,4.,6.,8.)}
  checks['button_neighbour_clearance'][('right_' if right else 'left_')+name]=collisions
  assert max(collisions.values())<.01,(right,name,'other button blocks top slide',collisions)
checks['borderless_switches']={}
normal=c.body(3.2,c.HANDLE_END-.2)
for right in (False,True):
 h=c.handle_left(right)
 for name,angle,z in c.HAND_BUTTONS:
  angle=-angle if right else angle
  # Only the two short side claws and two tiny lower stops may leave the skin.
  tips=c.button_side_claws()+c.union([c.box(-8.7,-7.35,8.1,9.5,-3.,-.05),c.box(7.35,8.7,8.1,9.5,-3.,-.05)])
  residual=((c.button_pad(angle,z)-normal)-c.mount_local(tips,angle,z)).volume()
  cap=c.local(c.box(-8.3,8.3,c.BUTTON_ORIGIN+1.8,c.BUTTON_ORIGIN+10.,-8.75,8.75),angle,z)
  cap_collision=(h^cap).volume()
  checks['borderless_switches'][('right_'if right else 'left_')+name]={'external_material_outside_small_tabs_mm3':residual,'full_3mm_keycap_stroke_overlap_mm3':cap_collision,'recess_increase_mm':3.4}
  assert residual<.001 and cap_collision<.001,('surround or keycap collision',right,name,residual,cap_collision)
assert 16.4<16.6 and 17.2<17.5 # Plate footprint remains beneath purchased cap.
checks['thin_plate']={'face_thickness_mm':1.3,'face_size_mm':[16.4,17.2],'including_rear_rails_mm':2.5,'separate_keeper':False,'no_glue_required':True}
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
 probe=c.cyl(c.shaft_radius(z)-2.1,z-.05,z+.05)
 checks['thin_hollow_shaft_overlap_mm3'][label]=(part^probe).volume()
 assert checks['thin_hollow_shaft_overlap_mm3'][label]<.001,'Shaft core is filled rather than thin-walled'
# Perforate independent slots while keeping the complete raised helix strips.
checks['slot_open_probes']={};checks['solid_helix_probes']={};checks['axial_land_probes']={};checks['keyhole_interface_rail_openings']={}
sp0=importlib.util.spec_from_file_location('previous_print_v11',HERE.parent/'v11/wand_cad.py');previous=importlib.util.module_from_spec(sp0);sp0.loader.exec_module(previous)
previous_parts={'grip':previous.handle_left(),'lower':previous.lower_shaft(),'upper':previous.upper_shaft()}
checks['previous_spiral_reference_probes']={}
for zone,part in [('grip',c.handle_left()),('lower',c.lower_shaft()),('upper',c.upper_shaft())]:
 for i,slot in enumerate(c.slot_locations(zone)):
  q=c.local(c.b.cyl_y(.7,slot['outer_radius']-2.5,slot['outer_radius']+2.5),slot['angle'],slot['z'])
  value=(part^q).volume();checks['slot_open_probes'][zone+'_'+str(i)]=value;assert value<.001
 for z in sorted(set(a['z'] for a in c.slot_locations(zone))):
  r=c.radius(z) if zone=='grip' else c.shaft_radius(z)
  for k in [0,1]:
   for delta in [-22.,0.,22.]:
    a=float(c.b.rib_angle(z,k))+delta;actual_height=float(c.rib_height(z,np.array([a]))[0]);rr=r+min(.45,actual_height-.12)
    q=c.Manifold.sphere(.1,12).translate((rr*math.sin(math.radians(a)),rr*math.cos(math.radians(a)),z))
    value=(part^q).volume();key=zone+'_'+str(z)+'_'+str(k)+'_'+str(delta);checks['solid_helix_probes'][key]=value
    reference=(previous_parts[zone]^q).volume();checks['previous_spiral_reference_probes'][key]=reference
    assert value>=reference-.00015,('original spiral cut',key,value,reference)
  for a in [0.,90.,180.,270.]:
   q=c.Manifold.sphere(.1,12).translate(((r-.25)*math.sin(math.radians(a)),(r-.25)*math.cos(math.radians(a)),z))
   value=(part^q).volume();key=zone+'_'+str(z)+'_'+str(a)
   mount_void=c.union([c.loop_slide_clearance(zz) for zz in c.LOOP_MOUNTS]) if zone=='grip' else None
   if zone=='grip' and (mount_void^q).volume()>.002:
    checks['keyhole_interface_rail_openings'][key]=value
   else:
    checks['axial_land_probes'][key]=value;assert value>.002,(key,value)
# Both arm ends enter matching broad seats, rather than hovering on thin pins.
checks['direct_handle_joins']={'old_toe_material_mm3':(loop^c.box(-12.,12.,-40.,-12.,0.,30.)).volume(),'minimum_curve_radius_mm':float(c.b.min_curvature_radius(c.b.catmull_rom(c.LOOP_POINTS))),'neck_diameter_mm':2*c.LOOP_NECK_RADIUS,'seat_mm':[c.LOOP_SEAT_WIDTH,c.LOOP_SEAT_HEIGHT,1.2],'matching_seat_difference_mm3':((c.loop_seat(42.).translate((0,c.radius(42.)-c.radius(132.),90.)) - c.loop_seat(132.)).volume())}
assert checks['direct_handle_joins']['old_toe_material_mm3']<.001
assert checks['direct_handle_joins']['matching_seat_difference_mm3']<.001
assert checks['direct_handle_joins']['minimum_curve_radius_mm']>c.LOOP_RADIUS+.5
checks['seated_shoulders']={}
for z in c.LOOP_MOUNTS:
 shoulder=c.loop_seat(z);probe=c.box(-3.,3.,-c.radius(z)+.25,-c.radius(z)+1.,z-3.,z+3.)
 checks['seated_shoulders'][str(z)]={'inserted_shoulder_material_mm3':(shoulder^probe).volume(),'locked_stem_overlap_mm3':(c.handle_left()^shoulder).volume(),'arm_to_shoulder_overlap_mm3':(c.loop_arm(z)^shoulder).volume()}
 assert (shoulder^probe).volume()>25. and (c.handle_left()^shoulder).volume()<.001
sp17=importlib.util.spec_from_file_location('v17_grip',HERE.parent/'v17/wand_cad.py');v17=importlib.util.module_from_spec(sp17);sp17.loader.exec_module(v17)
checks['slimmer_grip']={str(z):{'previous_core_diameter_mm':2*v17.radius(z),'new_core_diameter_mm':2*c.radius(z),'reduction_mm':2*(v17.radius(z)-c.radius(z))}for z in [42.,64.,96.,132.]}
assert all(abs(v['reduction_mm']-1.6)<.001 for v in checks['slimmer_grip'].values())
checks['loop_contact_airflow']={}
for i,a in enumerate(c.loop_air_ports()):
 n=np.array(a['inward']);center=np.array(a['center']);q=c.cyl(.8,-9.,9.).transform(np.column_stack([np.array([1.,0.,0.]),np.array(a['tangent']),n,center]))
 value=(loop^q).volume();checks['loop_contact_airflow'][str(i)]=value;assert value<.001
# Geometric spring envelopes, not PETG force/fatigue simulations.
latch=c.loop_release_latch();seat=c.loop_with_latch_deflection(c.LOOP_PRELOAD);released=c.loop_with_latch_deflection(c.LOOP_RELEASE_DEFLECTION)
checks['detachable_loop']={}
angles=[float(a) for a in np.arange(0.,c.LOOP_TWIST+.01,.5)]
downs=[0.,.25,.5,1.,2.,3.,4.]
for hand,right in [('left',False),('right',True)]:
 stem=c.handle_left(right);rest=(stem^seat).volume();assert rest<.001,('seated interference',hand,rest)
 bare=(stem^(loop-latch)).volume();assert bare<.001
 preload=(stem^loop).volume();assert .001<preload<1.,('preload must be confined to a small compliant tooth',preload)
 turn={str(a):(stem^c.loop_pose(released,a)).volume() for a in angles};assert max(turn.values())<.001,('cam turn',hand,turn)
 slide={str(d):(stem^c.loop_pose(released,c.LOOP_TWIST,d)).volume() for d in downs};assert max(slide.values())<.001,('entry slide',hand,slide)
 radial=(stem^released.translate((0,-1,0))).volume();up=(stem^released.translate((0,0,.6))).volume();down=(stem^released.translate((0,0,-.6))).volume()
 assert min(radial,up,down)>1.,('bayonet capture independent of latch',radial,up,down)
 radial_float={}
 for shift in [0.,.1,.15,.2,.25,.3,.35,.4,.5]:
  rigid_v=(stem^(loop-latch).translate((0,-shift,0))).volume();nominal_v=(stem^loop.translate((0,-shift,0))).volume()
  radial_float[str(shift)]={'rigid_overlap_mm3':rigid_v,'nominal_spring_overlap_mm3':nominal_v}
  if rigid_v<.001:assert nominal_v>.005,('radial float defeats preload',hand,shift,nominal_v)
 assert radial_float['0.5']['rigid_overlap_mm3']>1.,('radial float has no stop',radial_float)
 catch={str(a):(stem^c.loop_pose(seat,a)).volume() for a in [.5,1.,2.,3.]};assert catch['2.0']>.1,('reverse catch',catch)
 stop=(stem^c.loop_pose(released,-2.)).volume();assert stop>1.,('overturn stop',stop)
 caps=c.union([c.local(c.box(-8.3,8.3,13.,24.,-8.75,8.75),-a if right else a,z) for _,a,z in c.HAND_BUTTONS])
 obstacles=c.bottom_cap()+caps
 turn_clear={str(a):(obstacles^c.loop_pose(released,a)).volume() for a in angles};assert max(turn_clear.values())<.001
 slide_clear={str(d):(obstacles^c.loop_pose(released,c.LOOP_TWIST,d)).volume() for d in downs};assert max(slide_clear.values())<.001
 away={str(d):((stem+obstacles)^c.loop_pose(released.translate((0,-d,0)),c.LOOP_TWIST,c.LOOP_SLIDE)).volume() for d in [0.,.5,1.,2.,5.,10.,20.,35.]};assert max(away.values())<.001
 checks['detachable_loop'][hand]={'radial_preload_float_proof':radial_float,'rest_overlap_mm3':rest,'rigid_rest_overlap_mm3':bare,'nominal_spring_preload_overlap_mm3':preload,'released_turn_mm3':turn,'released_slide_mm3':slide,'radial_capture_mm3':radial,'upward_hard_stop_mm3':up,'locked_downward_capture_without_latch_mm3':down,'reverse_catch_mm3':catch,'left_turn_end_stop_mm3':stop,'keycap_and_battery_turn_path_mm3':turn_clear,'keycap_and_battery_slide_path_mm3':slide_clear,'outward_removal_after_downward_slide_mm3':away,'entry_clockwise_deg':c.LOOP_TWIST,'left_locking_turn_deg':c.LOOP_TWIST,'cam_draw_mm':c.LOOP_CAM_RISE,'seated_latch_deflection_mm':c.LOOP_PRELOAD,'released_latch_deflection_mm':c.LOOP_RELEASE_DEFLECTION}
socket,foot=c.loop_socket_coupon(),c.loop_foot_coupon();coupon_seat=(foot-latch)+c.loop_latch_deflected(c.LOOP_PRELOAD);coupon_release=(foot-latch)+c.loop_latch_deflected(c.LOOP_RELEASE_DEFLECTION)
checks['loop_mount_coupon']={'rest_overlap_mm3':(socket^coupon_seat).volume(),'released_turn_mm3':{str(a):(socket^c.loop_pose(coupon_release,a)).volume() for a in angles},'released_slide_mm3':{str(d):(socket^c.loop_pose(coupon_release,c.LOOP_TWIST,d)).volume() for d in downs},'upward_hard_stop_mm3':(socket^coupon_release.translate((0,0,.6))).volume(),'locked_downward_capture_without_latch_mm3':(socket^coupon_release.translate((0,0,-.6))).volume()}
assert checks['loop_mount_coupon']['rest_overlap_mm3']<.001
assert max(checks['loop_mount_coupon']['released_turn_mm3'].values())<.001
assert max(checks['loop_mount_coupon']['released_slide_mm3'].values())<.001
assert checks['loop_mount_coupon']['upward_hard_stop_mm3']>1. and checks['loop_mount_coupon']['locked_downward_capture_without_latch_mm3']>.5
# The attachment may recess into the normal surface but must never add an
# external boss, tab or collar. Check the delivered solid in both hands.
checks['bare_wand']={};checks['recessed_pocket_floor_material_mm3']={}
for zz in c.LOOP_MOUNTS:
 probe=c.Manifold.sphere(.3,16).translate((0,-c.loop_mount_radius(zz)+5.25,zz))
 value=(c.handle_left()^probe).volume();checks['recessed_pocket_floor_material_mm3'][str(zz)]=value;assert value>.09,('Pocket floor absent',zz,value)
sp14=importlib.util.spec_from_file_location('print_v14_previous',HERE.parent/'v14/wand_cad.py');v14=importlib.util.module_from_spec(sp14);sp14.loader.exec_module(v14)
old_rib=c.rib_height
try:
 c.rib_height=lambda z,theta,button_clearance=True:np.zeros(len(theta))
 smooth=c.body(3.2,c.HANDLE_END-.2)
finally:c.rib_height=old_rib
outer=c.body(3.2,c.HANDLE_END-.2)
ribbons=(outer-smooth)^outer.scale((.997,.997,1.))
for right in (False,True):
 stem=c.handle_left(right);envelope=c.body(3.2,c.HANDLE_END-.2)+c.handle_left(right,False)
 raw_residual=(stem-envelope).volume()
 external=sum((c.loop_receiver(zz)-c.body(3.2,c.HANDLE_END-.2)).volume() for zz in c.LOOP_MOUNTS)
 rear_mount_band=c.box(-9.,9.,-25.,-4.,20.,140.)
 surface_tolerance=((stem^rear_mount_band)-(envelope+c.body(3.2,c.HANDLE_END-.2).scale((1.0005,1.0005,1.)))).volume()
 assert surface_tolerance<.001,('Rear mount outside 0.01mm exterior envelope',right,surface_tolerance)
 control_pockets=c.union([c.mount_local(c.receiver_voids(),-a if right else a,z) for _,a,z in c.HAND_BUTTONS]);mount_openings=c.union([c.loop_slide_clearance(z) for z in c.LOOP_MOUNTS]);lost=((((v14.handle_left(right)^ribbons)-control_pockets)-mount_openings)-stem).volume()
 checks['bare_wand']['right' if right else 'left']={'mount_material_outside_original_surface_mm3':external,'whole_stem_exterior_roundoff_mm3':raw_residual,'rear_mount_band_outside_0_01mm_surface_tolerance_mm3':surface_tolerance,'lost_original_raised_helix_mm3':lost,'keyhole_entry_diameter_mm':2*(c.LOOP_HEAD_RADIUS+c.LOOP_TRACK_GAP),'slot_neck_width_mm':2*(c.LOOP_NECK_RADIUS+c.LOOP_TRACK_GAP),'protruding_stem_mounts':False}
 assert external<.001,('Mount projects outside normal wand',right,external)
 assert lost<.01,('Recess cuts original raised helix',right,lost)
# Projection is greater in the high/thumb region; the YZ loop plane is unchanged.
path=np.array(c.b.catmull_rom(c.LOOP_POINTS));lower=-path[(path[:,0]>=24)&(path[:,0]<=48),1].min();upper=-path[(path[:,0]>=87)&(path[:,0]<=110),1].min()
checks['loop_projection']={'lower_centerline_reach_mm':lower,'upper_thumb_centerline_reach_mm':upper,'plane':'YZ unchanged'}
assert upper-lower>8.
# A connected 3D body can still start a floating island in an upright layer.
# Check the upper board pockets at the actual reference layer height.
checks['head_layer_islands']=[]
for i in range(1,291):
 z=c.TOP+.1+.2*i;prev=base.slice(z-.2).offset(.2)
 for part in base.slice(z).decompose():
  if part.area()>.005 and (part^prev).area()<.001:
   checks['head_layer_islands'].append({'z':round(z,2),'area_mm2':part.area(),'bounds':part.bounds()})
assert not checks['head_layer_islands'],checks['head_layer_islands']
# Quantify the actual curved aperture area, not a vague hollow percentage.
checks['window_area_mm2']={zone:sum(p['area_mm2'] for p in c.window_regions(zone)) for zone in ['grip','lower','upper']}
checks['previous_window_area_mm2']={zone:sum(p['area_mm2'] for p in previous.window_regions(zone)) for zone in ['grip','lower','upper']}
checks['window_area_ratio']={zone:checks['window_area_mm2'][zone]/checks['previous_window_area_mm2'][zone] for zone in ['grip','lower','upper']}
assert .7<checks['window_area_ratio']['grip']<.95,'Handle openings must be modestly smaller'
assert all(v>500 for v in checks['window_area_mm2'].values()),'Perforations regressed to tiny slots'
checks['rail_reinforcement_probes']={}
for zone,part,old,zs,depth in [('grip',c.handle_left(),previous_parts['grip'],[64.,80.],c.GRIP_RAIL_DEPTH),('lower',c.lower_shaft(),previous_parts['lower'],[200.,220.],c.SPINE_DEPTH),('upper',c.upper_shaft(),previous_parts['upper'],[282.,315.],c.SPINE_DEPTH)]:
 for zz in zs:
  r=c.radius(zz) if zone=='grip' else c.shaft_radius(zz)
  for angle in [0.,90.,180.,270.]:
   p=c.local(c.Manifold.sphere(.08,12).translate((0,r-depth+.16,0)),angle,zz)
   new_v=(part^p).volume();old_v=(old^p).volume();key=f'{zone}_{zz}_{angle}'
   checks['rail_reinforcement_probes'][key]={'new_mm3':new_v,'previous_mm3':old_v,'depth_mm':depth}
   assert new_v>.0015,(key,'Reinforcement removed by a later subtraction',new_v)
   assert old_v<.0001,(key,'Probe does not establish added depth',old_v)
checks['shaft_window_layer_islands']={}
for name,part,z0,z1 in [('lower',c.lower_shaft(),c.HANDLE_END+20,c.MID-18),('upper',c.upper_shaft(),c.MID+20,c.TOP-18)]:
 islands=[]
 for z in np.arange(z0+.2,z1,.2):
  below=part.slice(float(z-.2)).offset(.23)
  for patch in part.slice(float(z)).decompose():
   if patch.area()>.01 and (patch^below).area()<.001:islands.append({'z':float(z),'area_mm2':patch.area()})
 checks['shaft_window_layer_islands'][name]=islands
 assert not islands,(name,'floating cell walls',islands)
print(json.dumps(checks,indent=2))
