#!/usr/bin/env python3
"""Check R14's compact pyramid, bought interfaces, routes, springs and poses."""
import json
from itertools import product
import numpy as np
import trimesh
import manifold3d as mf
import cad

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
    seats={};routes={};joints=[];pokes={};travel={}
    for i,(x,y) in enumerate(cad.key_positions()):
        for name,shape in {**hw,'max_socket':maximum}.items():
            seats[f'{i}_{name}']=overlap(keys,shape.translate((x,y,z)))
        for name,shape in [('nominal',hw['socket']),('maximum',maximum)]:
            routes[f'{i}_{name}']=max(overlap(keys,shape.translate((x+px,y+py,z+pz))) for px,py,pz in route)
        seat=cad.key_seat(outer_side=1 if x>0 else -1 if x<0 else 0).translate((x,y,z))
        rail=cad.rib((x-8.2,y-9.4,z+1.4),(x+8.2,y-9.4,z+1.4),1.25)
        joints.append(overlap(seat,rail))
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
        'front_rail_seat_overlap_mm3':joints,'removed_outer_pokes_mm3':pokes,'illustrative_cap_travel_mm3':travel,
        'side_key_half_spacing_mm':cad.P['keys']['upper_half_spacing'],'purchased_cap_travel_verified':False}
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
    report['pyramid_layout']={'centres_mm':positions,'default_orientation':'two-toward-tip',
        'reference_cap_size_mm':[c['reference_width_mm'],c['reference_length_mm']],
        'independent_stroke_mm':c['stroke_mm'],'side_allowance_per_cap_mm':margin,
        'minimum_swept_envelope_gap_mm':min(gaps.values()),'pairwise_swept_envelope_gaps_mm':gaps,
        'bought_cap_dimensions_and_play_verified':False,'physical_comfort_verified':False}
    lands={}
    for x,y in product([-7.15,7.15],repeat=2):
        probe=cad.box(x-.08,x+.08,y-.08,y+.08,z+2.05,z+2.25)
        lands[f'{x},{y}']=float((probe-keys).volume())
    assert max(lands.values())<.0001,lands
    report['key_interface']['missing_four_flange_corner_lands_mm3']=lands
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
