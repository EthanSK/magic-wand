#!/usr/bin/env python3
"""Check R15's compact pyramid, bought interfaces, routes, springs and poses."""
import json
from itertools import product
import numpy as np
import trimesh
import manifold3d as mf
import cad
import working_spaces

OUT=cad.HERE/'exports'

def overlap(a, b):
    return max(0., float((a ^ b).volume()))

def read(name):
    m=trimesh.load_mesh(OUT/(name+'-assembly.stl'))
    return mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))

def check():
    manifest=json.loads((OUT/'manifest.json').read_text())
    report={'manifest_sha256':cad.sha(OUT/'manifest.json'),'checker_sha256':cad.sha(cad.HERE/'verify_geometry.py'),
            'parts':{},'poses':[],'physical_fit_verified':False,'physical_strength_verified':False,'physical_comfort_verified':False}
    for path,digest in manifest['source_sha256'].items(): assert cad.sha(cad.HERE/path)==digest,path
    solids={name:read(name) for name in manifest['parts']}
    keys=solids['Key_Carrier'];battery=solids['Battery_Holder']
    hw=cad.seated_hardware();k=cad.P['keys'];z=k['pcb_z']
    # Retain the sourced flat-back seat, then inspect the whole key frame too.
    bx=np.array(hw['socket'].bounding_box());centre=(bx[:3]+bx[3:])/2
    maximum=hw['socket'].translate((-centre[0],-centre[1],-bx[2])).scale((13.55/13.15,6.95/6.85,3.25/3.05)).translate((centre[0],centre[1],k['socket_pocket_bottom']))
    route=[(-2.5,-4.824,dz) for dz in np.linspace(12,.6,115)]
    route += [(-2.5*(1-t),-4.824*(1-t),.6) for t in np.linspace(0,1,61)]
    route += [(0,0,dz) for dz in np.linspace(.6,0,13)]
    # The CAD carve, helpers and bead checks evaluate the shared route pose by
    # pose. It must stay identical to this independent 189-pose route.
    shared_route=working_spaces.socket_route()
    assert len(route)==189 and np.array_equal(np.asarray(route,dtype=float),shared_route),'Working-space socket route differs from the independent route'
    # The exported carrier's carve used every whole pose of all ten routes.
    carve=manifest['working_space_carve']['carrier:modular:None']
    assert sorted(carve)==sorted(f'key_{i}_{label}'for i in range(len(cad.key_positions()))for label in ['socket_loading','maximum_socket_loading']),carve
    assert all(v['poses']==len(route)for v in carve.values()),carve
    seats={};routes={};joints=[];pokes={};travel={}
    for i,(x,y) in enumerate(cad.key_positions()):
        for name,shape in {**hw,'max_socket':maximum}.items():
            seats[f'{i}_{name}']=overlap(keys,shape.translate((x,y,z)))
        for name,shape in [('nominal',hw['socket']),('maximum',maximum)]:
            routes[f'{i}_{name}']=max(overlap(keys,shape.translate((x+px,y+py,z+pz))) for px,py,pz in route)
        seat=cad.key_seat(outer_side=1 if x>0 else -1 if x<0 else 0).translate((x,y,z))
        if y:
            # Upper keys keep their R12 front rail between the rows.
            rail=cad.rib((x-8.2,y-9.4,z+1.4),(x+8.2,y-9.4,z+1.4),1.25)
            joints.append(overlap(seat,rail))
        else:
            # Lower keys: both fixed side rails must reach the recessed
            # bumper in the actual final carrier, not in a seat-only model.
            for sign in [-1,1]:
                lo,hi=sorted([x+sign*7.7,x+sign*9.1])
                joints.append(overlap(keys,cad.box(lo,hi,cad.front_plane(),-6.8,7.95,10.25)))
        travel[str(i)]=overlap(keys,cad.references()[f'key_{i}_cap'].translate((0,0,-3)))
        # Moved-out side corners are exposed again; check all four outer ends.
        if x:
            probe=mf.Manifold.sphere(.55,16).translate((x+(7.9 if x>0 else -7.9),y-9.7,z-4.5))
            # In the staggered layout a neighbouring rear post occupies this
            # coordinate legitimately. Check the offending seat corner itself;
            # full-frame moving cap and hardware routes are checked separately.
            pokes[str(i)]=overlap(seat,probe)
    assert max(seats.values())<.002,seats
    assert max(routes.values())<.002,routes
    assert min(joints)>1,joints
    assert max(pokes.values())<.002,pokes
    assert max(travel.values())<.002,travel
    report['key_interface']={'bought_part_intersections_mm3':seats,'sampled_socket_routes_mm3':routes,
        'upper_front_rail_seat_and_lower_rail_to_bumper_overlap_mm3':joints,'removed_outer_pokes_mm3':pokes,'illustrative_cap_travel_mm3':travel,
        'side_key_half_spacing_mm':cad.P['keys']['upper_half_spacing'],'purchased_cap_travel_verified':False,
        'socket_route_poses_checked':len(route),'working_space_route_identical':True,'exported_carve_route_poses':carve}
    # Ethan's "frame edge below the bottom row": nothing may sit ahead of the
    # recessed plane; the plane stays behind the lower reference cap fronts.
    f=cad.P['finger_recess'];front=cad.front_plane();top=cad.plate_top()
    cap_front=min(cad.references()[f'key_{i}_cap'].bounding_box()[1]for i,(x,y)in enumerate(cad.key_positions())if not y)
    ahead=overlap(keys,cad.box(-60,60,-60,front-.001,-60,60))
    assert ahead<.002 and abs(keys.bounding_box()[1]-front)<.002,(ahead,keys.bounding_box())
    # With the corrected cap orientation, its 16.6 mm side runs along Y, so
    # the inferred cap front is at Y -8.3. The bumper must still carry the
    # switch flange land to Y -7.5, so its face cannot sit far behind that
    # cap front. Require a real step ahead of the bumper, and also
    # require the flange land and the receding chin below.
    assert front-cap_front>=.35,(front,cap_front)
    flange_front=-7.5;assert front<=flange_front-.35,(front,flange_front)
    y0,zf,yl,zl=cad.chin()
    # The continuous bumper core and its lip below the switch housing must be
    # present across all three lower keys.
    core=cad.box(-25,25,front+.05,f['bumper_back_y_mm']-.05,zf+.05,top-f['top_edge_chamfer_mm']-.05)
    # The lip lies above the chin line; probe its rear part and the shelf
    # behind the chin that rejoins the notched front clip ties.
    lip=cad.box(-25,25,yl-.5,f['lip_back_y_mm']-.05,zf-(yl-.5-y0)+.05,f['lip_top_z_mm']-.05)
    lip+=cad.box(-25,25,yl,f['lip_back_y_mm']-.05,zl+.05,f['lip_top_z_mm']-.05)
    missing_core=max(0.,(core-keys).volume());assert missing_core<.002,missing_core
    missing_lip=max(0.,(lip-keys).volume());assert missing_lip<.002,missing_lip
    # Finger relief: below the 45-degree chin nothing may remain between its
    # lowest edge and the front plane, including rail heads and tie ends.
    chin_material=overlap(keys,cad.chin_cut()^cad.box(-40,40,front-.01,yl,zl,zf+.01))
    assert chin_material<.002,chin_material
    # Softened edges: the sharp bed-edge corners must be absent.
    edges={'top_front':overlap(keys,cad.box(-25,25,front,front+.15,top-.15,top))}
    for x,y in cad.key_positions():
        if y:continue
        half=5.5 if x==0 else 6.
        edges[f'chin_front_{x}']=overlap(keys,cad.box(x-half,x+half,front,front+.15,zl,zf-.2))
    x0=cad.outer_corner_cut_x()
    for sign in [-1,1]:
        lo,hi=sorted([sign*(x0+.1),sign*(x0+1.5)])
        edges[f'outer_corner_{sign}']=overlap(keys,cad.box(lo,hi,front,front+.1,6,top))
    # The fixed clip crown edge between the ties is chamfered at the front face.
    edges['front_clip_crown_edge']=overlap(keys,cad.box(-1,1,front,front+.1,5.2,5.6))
    assert max(edges.values())<.002,edges
    # The front clip ties and spine exist in the final solid.
    ties={}
    for name,(px,py,pz) in {'left_diagonal':(-6.2,front+.3,6.15),'right_diagonal':(6.2,front+.3,6.15),
                            'spine_left':(-3,-3,4.8),'spine_right':(3,-3,4.8),'spine_root':(0,-1.2,4.9)}.items():
        probe=cad.box(px-.1,px+.1,py-.1,py+.1,pz-.1,pz+.1);ties[name]=float((probe-keys).volume())
    assert max(ties.values())<.0001,ties
    # Reviewer N12: a fixed spine from the rear clip crown grows both upper
    # socket floor fronts, including the formerly free upper-left tongue.
    rear={}
    for name,(px,py,pz) in {'rear_spine_left':(-3.,15.,4.9),'rear_spine_right':(2.5,15.,4.9),
                            'rear_spine_root_left':(-4.5,17.,4.85),'upper_left_floor_join':(-3.,17.5,4.85),
                            'rear_spine_root_right':(5.,16.6,4.85),'upper_right_floor_join':(6.6,17.5,4.85)}.items():
        probe=cad.box(px-.1,px+.1,py-.1,py+.1,pz-.1,pz+.1);rear[name]=float((probe-keys).volume())
    assert max(rear.values())<.0001,rear
    # Reviewer N16: each fixed spine's true neck is where it leaves its clip
    # ring, not at the probes above. Native vertical ray sections at X=0 from
    # just behind each ring back face (0.05 mm off the 0.1 mm face grid); the
    # strength audit scans every span completely with actual layer tracks.
    def vertical_section(px,py,pz=4.9):
        hits=sorted(keys.ray_cast((px,py,pz-100),(px,py,pz+100)),key=lambda h:h.distance)
        for a,b in zip(hits[::2],hits[1::2]):
            if a.distance<.5<b.distance:return float(np.array(b.position)[2]-np.array(a.position)[2])
        raise AssertionError(('Spine neck probe is not in material',px,py,pz))
    necks={};seeds={};screen=f['spine_neck_minimum_section_mm']
    for name,s in cad.spine_layouts().items():
        back=s['ring_y_mm']+cad.P['rod']['ring_width']/2
        necks[name]={f'{back+.05+.1*j:.2f}':round(vertical_section(0.,back+.05+.1*j),4)for j in range(12)}
        assert min(necks[name].values())>=screen-.02,(name,necks[name],screen)
        # The crown seed lies wholly inside its fixed ring crown.
        seeds[name]=max(0.,(cad.spine_crown(s['crown_y_mm'])-cad.ring(s['ring_y_mm'])).volume())
    assert max(seeds.values())<.002,seeds
    # The crown chamfer must not touch the free spring arms: the front ring's
    # complete lower half, apart from its designed gap, is still present.
    fy=cad.carrier_clip_centres()[0]
    arms=max(0.,((cad.ring(fy)^cad.box(-8,8,fy-2,fy+2,-8,-.05))-cad.clip_gap(fy)-keys).volume())
    assert arms<.002,arms
    report['lower_front_recess']={'front_plane_y_mm':front,'lower_reference_cap_front_y_mm':cap_front,
        'recess_behind_reference_cap_front_mm':front-cap_front,'material_ahead_of_plane_mm3':ahead,
        'switch_flange_land_front_y_mm':flange_front,
        'chin':{'front_y_mm':y0,'front_z_mm':zf,'back_y_mm':yl,'bottom_z_mm':zl,'angle_degrees':45.0,
                'recess_at_chin_bottom_behind_reference_cap_front_mm':yl-cap_front},
        'missing_continuous_bumper_core_mm3':missing_core,'missing_lip_below_switch_housing_mm3':missing_lip,
        'material_under_chin_mm3':chin_material,'softened_edge_corner_material_mm3':edges,
        'missing_front_clip_tie_and_spine_probe_mm3':ties,'missing_rear_floor_spine_probe_mm3':rear,
        'spine_neck_vertical_sections_at_x0_mm':necks,'spine_neck_screen_mm':screen,'spine_crown_seed_outside_ring_mm3':seeds,
        'missing_front_clip_free_arm_mm3':arms,'front_clip_y_mm':fy,
        'previous_front_clip_y_mm':-12.0,'previous_front_y_mm':-13.8,
        'note':'Geometric recess and edge screening only. Reference cap dimensions are inferred, not measured; finger comfort is not measured.',
        'physical_comfort_verified':False}
    c=cad.P['cap_clearance_screen'];positions=cad.key_positions();gaps={}
    # AABB swept envelopes contain every independent 0..stroke Z position,
    # including corners. Side allowance is provisional, not measured cap play.
    envelopes=[]
    for i in range(5):
        ref=cad.references()[f'key_{i}_cap'];bb=ref.bounding_box();margin=c['lateral_allowance_per_cap_side_mm']
        assert abs(bb[3]-bb[0]-c['reference_width_mm'])<1e-5
        assert abs(bb[4]-bb[1]-c['reference_length_mm'])<1e-5
        envelopes.append((bb[0]-margin,bb[1]-margin,bb[2]-c['stroke_mm'],bb[3]+margin,bb[4]+margin,bb[5]))
        assert overlap(keys,cad.box(*[bb[0]-margin,bb[3]+margin,bb[1]-margin,bb[4]+margin,bb[2]-c['stroke_mm'],bb[5]]))<.002
    for i in range(5):
        for j in range(i+1,5):
            a,b=envelopes[i],envelopes[j]
            separation=[max(a[d]-b[d+3],b[d]-a[d+3],0)for d in range(3)]
            gap=float(np.linalg.norm(separation));gaps[f'{i}_{j}']=gap
    assert min(gaps.values())>=c['minimum_residual_gap_mm']-1e-5,gaps
    assert positions[3][0]==-positions[4][0] and abs(positions[3][0])==k['pitch']/2
    assert cad.P['assembly']['default_key_orientation']=='two-toward-tip'
    # Reviewer N11: Choc V1 caps are longer along the stem-post axis. The
    # sourced switch mesh has two 1.2 x 3.0 mm post footprints; find them and
    # require the cap's longer reference side along their spacing axis.
    data=json.loads((cad.base.r7.HERE/'references/switch.json').read_text());v=np.asarray(data['vertices'])
    posts={}
    for sign in [-1,1]:
        corners=[(sign*a,b)for a in [2.25,3.45]for b in [-1.5,1.5]]
        found=[bool(np.any(np.all(np.abs(v[:,:2]-p)<.01,axis=1)&(v[:,2]>7.5)))for p in corners]
        assert all(found),(sign,found);posts[sign]=np.mean(corners,axis=0)
    axis=np.abs(posts[1]-posts[-1]);assert axis[0]>5 and axis[1]<1e-9,axis
    assert c['reference_width_mm']>c['reference_length_mm'],'Longer cap side must lie along X, the stem-post axis'
    assert c['purchased_cap_dimensions_verified'] is False and c['mounted_cap_measurement_required_before_print'] is True
    for axis_index,pitch,size in [(0,k['pitch'],c['reference_width_mm']),(1,k['row_spacing'],c['reference_length_mm'])]:
        assert pitch-size-2*c['lateral_allowance_per_cap_side_mm']>=c['minimum_residual_gap_mm']-1e-9,(axis_index,pitch,size)
    report['cap_orientation']={'stem_post_centres_mm':{str(s):p.tolist()for s,p in posts.items()},
        'stem_post_axis':'X','reference_cap_x_mm':c['reference_width_mm'],'reference_cap_y_mm':c['reference_length_mm'],
        'nominal_cap_gap_x_mm':k['pitch']-c['reference_width_mm'],'nominal_cap_gap_y_mm':k['row_spacing']-c['reference_length_mm'],
        'dimension_source':c['dimension_source'],'evidence':c['orientation_evidence'],
        'purchased_cap_dimensions_verified':False,'mounted_cap_measurement_required_before_print':True}
    report['pyramid_layout']={'centres_mm':positions,'default_orientation':'two-toward-tip',
        'reference_cap_size_mm':[c['reference_width_mm'],c['reference_length_mm']],
        'independent_stroke_mm':c['stroke_mm'],'side_allowance_per_cap_mm':margin,
        'minimum_swept_envelope_gap_mm':min(gaps.values()),'pairwise_swept_envelope_gaps_mm':gaps,
        'bought_cap_dimensions_and_play_verified':False,'physical_comfort_verified':False}
    lands={}
    for i,(cx,cy) in enumerate(positions):
        for x,y in product([-7.15,7.15],repeat=2):
            probe=cad.box(cx+x-.08,cx+x+.08,cy+y-.08,cy+y+.08,z+2.05,z+2.25)
            lands[f'{i}:{x},{y}']=float((probe-keys).volume())
    assert max(lands.values())<.0001,lands
    report['key_interface']['missing_flange_corner_lands_mm3']=lands
    reserve=overlap(battery,cad.battery_shape(True));assert reserve<.002,reserve
    report['battery_reserve_intersection_mm3']=reserve
    for name,source,anchors in [('Key_Carrier',cad.carrier(),cad.carrier_clip_centres()),
                                ('Battery_Holder',cad.battery_module(),cad.battery_clip_centres())]:
        solid=solids[name];checks={}
        assert overlap(solid,cad.wire_bus(-80,80))<.002
        if name=='Battery_Holder':
            assert overlap(solid,cad.wire_bus(-80,80).mirror((1,0,0)))<.002
        assert overlap(solid,cad.cyl(cad.P['rod']['clip_diameter']/2-.001,-85,85).rotate((-90,0,0)))<.002
        fitted=(cad.carrier if name=='Key_Carrier' else cad.battery_module)(clip_diameter=cad.P['rod']['diameter'])
        assert overlap(fitted,cad.cyl(3.999,-85,85).rotate((-90,0,0)))<.002
        for y in anchors:
            shell=cad.tube_y(3.94,5.5,y-1.8,y+1.8)^cad.box(-6,6,y-2,y+2,-6,-.05)
            extra=overlap(source-cad.ring(y),shell)
            gap=overlap(solid,cad.clip_gap(y))
            band=cad.ring(y)^cad.tube_y(4.25,5.35,y-.4,y+.4)
            missing=max(0.,(band-solid).volume())
            assert max(extra,gap,missing)<.002,(name,y,extra,gap,missing)
            checks[str(y)]={'lower_arm_extra_material_mm3':extra,'gap_intersection_mm3':gap,'missing_clip_mm3':missing}
        report['parts'][name]={'spring_clips':checks,'clip_diameter_mm':cad.P['rod']['clip_diameter']}
    # Keep modules on separate axial intervals. The checked minimum end gap
    # makes every larger outward slide clear; do not suggest sliding through
    # the keys to swap order while components and wiring remain installed.
    entry=cad.P['assembly']['battery_entry_rotation_z_degrees']
    for flipped,angle in product([False,True],[0,90,180,270]):
        key_pose=keys.rotate((0,0,180 if flipped else 0))
        for extra in [0,cad.P['assembly']['extra_slide_range']]:
            y=cad.battery_position(flipped,extra)
            batt_pose=battery.rotate((0,0,entry)).rotate((0,angle,0)).translate((0,y,0))
            cell=cad.battery_shape(True).rotate((0,0,entry)).rotate((0,angle,0)).translate((0,y,0))
            kb=key_pose.bounding_box();bb=batt_pose.bounding_box()
            gap=bb[1]-kb[4]
            collisions={'frames':overlap(key_pose,batt_pose),'cell':overlap(key_pose,cell)}
            assert gap>=cad.P['assembly']['battery_end_clearance']-.001,(flipped,angle,extra,gap)
            assert max(collisions.values())<.002,collisions
            route=max(overlap(key_pose,cad.battery_shape(True).translate((0,dy,0)).rotate((0,0,entry)).rotate((0,angle,0)).translate((0,y,0))) for dy in np.linspace(-34,0,35))
            assert route<.002,route
            report['poses'].append({'flipped':flipped,'battery_end':'tip-above-keys','battery_roll_degrees':angle,'extra_slide_mm':extra,'battery_y_mm':y,'axial_frame_gap_mm':gap,'intersection_mm3':collisions,'whole_cell_loading_past_keys_mm3':route})
    report['whole_battery_turn_clearance']='The checked axial frame gap is invariant under battery rotation about Y. Larger outward slides preserve that gap. Nesting underneath the key frame is not an intended placement.'
    sensor=solids['XIAO_Rod_Holder'];refs=cad.references()
    sensor_clear={n:overlap(sensor,refs[n]) for n in ['pcb','usb','wire']}
    assert max(sensor_clear.values())<.002,sensor_clear
    assert refs['usb'].bounding_box()[1]>17
    assert overlap(refs['wire'],cad.cyl(4,-50,60).rotate((-90,0,0)))<.002
    report['sensor_board_usb_external_wire_clearance_mm3']=sensor_clear
    report['usb_direction']='positive Y toward tip and computer'
    # Gate removed: slide the complete reserve from outside the cage.
    loading=max(overlap(battery,cad.battery_shape(True).translate((0,y,0))) for y in np.linspace(-50,0,101))
    assert loading<.002,loading
    gate=cad.battery_gate(True)
    gate_loading=max(overlap(battery,gate.translate((0,0,dz))) for dz in np.linspace(0,15,61))
    assert gate_loading<.002,gate_loading
    relaxed=overlap(battery,solids['Battery_End_Gate'])
    assert .005<relaxed<2,relaxed
    stop=overlap(gate,cad.battery_shape().translate((0,-6,0)))
    assert stop>1,stop
    far_stop=overlap(battery,cad.battery_shape().translate((0,6,0)))
    assert far_stop>1,far_stop
    report['battery_loading']={'reserve_route_intersection_mm3':loading,'idealized_fitted_gate_route_intersection_mm3':gate_loading,'intentional_gate_wedge_interference_mm3':relaxed,'nominal_cell_stopped_by_gate_mm3':stop,'nominal_cell_stopped_at_far_end_mm3':far_stop,'gate_force_and_retention_physically_verified':False}
    previous=cad.base.sensor_holder();width=cad.P['rod']['sensor_clip_width']
    lower=cad.union([cad.box(-7,7,y-width/2,y+width/2,-6,0)for y in [-3.8,22.2]])
    difference=overlap(sensor-previous,lower)+overlap(previous-sensor,lower)
    assert difference<.002,difference
    report['sensor_lower_spring_arm_change_mm3']=difference
    report['passed']=True
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print("PASS: centred 3+2 pyramid, independent cap envelopes, five socket routes, free springs and 16 battery poses.")

if __name__=='__main__': check()
