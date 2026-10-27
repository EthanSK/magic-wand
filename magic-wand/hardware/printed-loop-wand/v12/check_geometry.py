"""Geometric fit checks; this does not simulate PETG force or establish physical fit."""
from pathlib import Path
import importlib.util,json,math,hashlib,numpy as np
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('print_v12_cad',HERE/'wand_cad.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
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
checks['top_slide_button']={}
for hand,right in [('left',False),('right',True)]:
 h=c.handle_left(right)
 for name,angle,z in c.HAND_BUTTONS:
  angle=-angle if right else angle
  plate=c.cassette_on_handle(c.socket_carrier(),angle,z)
  a=math.radians(angle);axis=(math.sin(a),math.cos(a),0.)
  up={str(d):(h^plate.translate((0,0,d))).volume() for d in (0,.25,1,2,4,6,8.4,10.)}
  radial=(h^plate.translate(tuple(.5*x for x in axis))).volume()
  down=(h^plate.translate((0,0,-.6))).volume()
  checks['top_slide_button'][hand+'_'+name]={'upward_release_path_mm3':up,'radial_pull_blocked_mm3':radial,'downward_stop_mm3':down}
  assert max(abs(v) for v in up.values())<.01,(hand,name,'top entry collision',up)
  assert radial>.05 and down>.05,(hand,name,'not captured',radial,down)
# Bought socket and lower switch housing envelopes. Catches sit above the
# socket; the switch body prevents the seated plate lifting once installed.
checks['socket_and_switch']={}
for name,angle,z in c.HAND_BUTTONS:
 h=c.handle_left()
 socket=c.mount_local(c.box(-8.3,-1.3,-7.8,2.4,-4.4,-2.6),angle,z)
 switch=c.local(c.box(-6.85,6.85,12.6,15.4,-6.85,6.85),angle,z)
 checks['socket_and_switch'][name]={'socket_rest_mm3':(h^socket).volume(),'switch_housing_rest_mm3':(h^switch).volume(),'switch_up_1mm_stop_mm3':(h^switch.translate((0,0,1.))).volume()}
 assert abs((h^socket).volume())<.01 and abs((h^switch).volume())<.01,(name,'component collision')
 assert (h^switch.translate((0,0,1.))).volume()>.01,(name,'no upward stop with switch installed')
checks['button_neighbour_clearance']={}
for right in (False,True):
 parts=[]
 for name,angle,z in c.HAND_BUTTONS:
  angle=-angle if right else angle
  parts.append((name,c.cassette_on_handle(c.socket_carrier(),angle,z),c.local(c.box(-8.3,8.3,18.8,24.,-8.75,8.75),angle,z)))
 for name,plate,cap in parts:
  others=c.union([p+cap for other,p,cap in parts if other!=name])
  collisions={str(d):(plate.translate((0,0,d))^others).volume() for d in (0,2.,4.,6.,8.4)}
  checks['button_neighbour_clearance'][('right_' if right else 'left_')+name]=collisions
  assert max(collisions.values())<.01,(right,name,'other button blocks top slide',collisions)
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
checks['slot_open_probes']={};checks['solid_helix_probes']={};checks['axial_land_probes']={}
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
   value=(part^q).volume();checks['axial_land_probes'][zone+'_'+str(z)+'_'+str(a)]=value;assert value>.002
checks['loop_contact_airflow']={}
for i,a in enumerate(c.loop_air_ports()):
 n=np.array(a['inward']);center=np.array(a['center']);q=c.cyl(.8,-9.,9.).transform(np.column_stack([np.array([1.,0.,0.]),np.array(a['tangent']),n,center]))
 value=(loop^q).volume();checks['loop_contact_airflow'][str(i)]=value;assert value<.001
# This is a geometric release envelope, not a PETG force/fatigue simulation.
latch=c.loop_release_latch();me=latch.to_mesh();v=np.array(me.vert_properties[:,:3],np.float32)
v[:,0]+=1.8*np.clip((v[:,2]-110.5)/16.3,0,1)**2
flex=c.Manifold(c.mf.Mesh(v,np.asarray(me.tri_verts,dtype=np.uint32)))
released=(loop-latch)+flex;checks['detachable_loop']={}
for hand,right in [('left',False),('right',True)]:
 stem=c.handle_left(right);rest=(stem^loop).volume();assert rest<.001
 slide={str(d):(stem^released.translate((0,0,d))).volume() for d in [0,.25,.5,1,2,5,10,15,20,22,25]}
 assert max(slide.values())<.001
 radial=(stem^loop.translate((0,-1,0))).volume();lift=(stem^loop.translate((0,0,.6))).volume()
 assert radial>1. and lift>.1
 caps=c.union([c.local(c.box(-8.3,8.3,13.,24.,-8.75,8.75),-a if right else a,z) for _,a,z in c.HAND_BUTTONS])
 cap_path={str(d):(caps^released.translate((0,0,d))).volume() for d in [0,5,10,15,22,25]};assert max(cap_path.values())<.001
 checks['detachable_loop'][hand]={'rest_overlap_mm3':rest,'released_slide_mm3':slide,'radial_capture_mm3':radial,'unreleased_upward_capture_mm3':lift,'keycap_release_path_mm3':cap_path,'latch_deflection_envelope_mm':1.8}
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
