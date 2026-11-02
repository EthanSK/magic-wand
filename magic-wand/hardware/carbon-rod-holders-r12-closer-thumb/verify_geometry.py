#!/usr/bin/env python3
"""Check R12's separate bodies, bought-part seats, reversible poses and free clips."""
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
            pokes[str(i)]=overlap(keys,probe)
    assert max(seats.values())<.002,seats
    assert max(routes.values())<.002,routes
    assert min(joints)>1,joints
    assert max(pokes.values())<.002,pokes
    assert max(travel.values())<.002,travel
    report['key_interface']={'bought_part_intersections_mm3':seats,'sampled_socket_routes_mm3':routes,
        'front_rail_seat_overlap_mm3':joints,'removed_outer_pokes_mm3':pokes,'illustrative_cap_travel_mm3':travel,
        'side_key_half_spacing_mm':cad.P['keys']['upper_half_spacing'],'purchased_cap_travel_verified':False}
    e=cad.P['ergonomics'];half=e['opening_width_mm']/2
    y0,y1=e['rest_region_y_mm'];z0,z1=e['rest_region_z_mm']
    opening=cad.box(-half,half,y0,y1,z0,z1)
    clearance={'frame':overlap(keys,opening)}
    for i,(x,y) in enumerate(cad.key_positions()):
        for name,shape in cad.seated_hardware().items():
            clearance[f'{i}_{name}']=overlap(opening,shape.translate((x,y,z)))
        clearance[f'{i}_cap']=overlap(opening,cad.references()[f'key_{i}_cap'])
    assert max(clearance.values())<.002,clearance
    left=(keys^cad.box(-80,0,y0,y1,z0,z1)).bounding_box()[3]
    right=(keys^cad.box(0,80,y0,y1,z0,z1)).bounding_box()[0]
    report['thumb_clearance']={'required_width_mm':e['opening_width_mm'],'centred_clear_width_mm':2*min(-left,right),
        'left_inner_x_mm':left,'right_inner_x_mm':right,'checked_y_mm':[y0,y1],'checked_z_mm':[z0,z1],
        'intersection_mm3':clearance,'physical_comfort_verified':False}
    assert report['thumb_clearance']['centred_clear_width_mm']>=e['opening_width_mm']-.001
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
    report['passed']=True
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"PASS: {e['opening_width_mm']:g} mm thumb opening, five socket routes, free spring arms and 16 battery-above-keys poses/loading paths.")

if __name__=='__main__': check()
