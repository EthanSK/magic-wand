#!/usr/bin/env python3
"""Verify final exported meshes against sourced bought-part CAD and assembly paths."""
import json
import math
import numpy as np
import trimesh
import manifold3d as mf
import cad

OUT = cad.HERE / 'exports'

def read(name):
    m = trimesh.load_mesh(OUT / (name + '-assembly.stl'))
    return mf.Manifold(mf.Mesh(np.asarray(m.vertices, dtype=np.float32), np.asarray(m.faces, dtype=np.uint32)))

def overlap(a, b):
    return max(0., float((a ^ b).volume()))

def check():
    report = {'checker_sha256': cad.sha(cad.HERE / 'verify_geometry.py'),
              'manifest_sha256': cad.sha(OUT / 'manifest.json'), 'options': {},
              'physical_fit_verified': False, 'physical_strength_verified': False,
              'community_CAD_is_not_manufacturer_certified': True}
    hw = cad.seated_hardware()
    # Source axes are +X/+Y at the PCB top, not the mirrored underside view.
    # These two pin locations match the KiSwitch top footprint after flipping
    # its down-screen Y axis. An inherited mirrored reference fails here.
    pin_material = [overlap(hw['switch'], cad.box(x-.18,x+.18,y-.18,y+.18,-2.4,-.8)) for x,y in [(0,5.9),(5,3.8)]]
    assert min(pin_material) > .03, pin_material
    report['pin_handedness_probe_mm3'] = pin_material
    seat = cad.key_seat()
    # A socket enters through the mounting opening, aligns below it, then
    # lowers between rigid side stops onto a broad flat floor. Sample at <=.1mm.
    poses = []
    for z in np.linspace(12, .6, 115): poses.append((-2.5, -4.824, z))
    for t in np.linspace(0, 1, 61): poses.append((-2.5 * (1-t), -4.824 * (1-t), .6))
    for z in np.linspace(.6, 0, 13): poses.append((0, 0, z))
    # Sensitivity test at the newer drawing's maximum overall dimensions.
    # It retains the old mesh's voids; this is not an official new-revision
    # model or a certification of the unknown purchased batch.
    bx=np.array(hw['socket'].bounding_box()); centre=(bx[:3]+bx[3:])/2
    max_socket=hw['socket'].translate((-centre[0],-centre[1],-bx[2])).scale((13.55/13.15,6.95/6.85,3.25/3.05)).translate((centre[0],centre[1],cad.P['keys']['socket_pocket_bottom']))
    route = max(overlap(seat, hw['socket'].translate(p)) for p in poses)
    max_route=max(overlap(seat,max_socket.translate(p)) for p in poses)
    assert max_route<.002,('newer maximum-size sensitivity route',max_route)
    report['newer_maximum_size_sensitivity_route_mm3']=max_route
    floor=cad.P['keys']['socket_pocket_bottom']
    pin_depth=floor+3.0-(-2.947)
    boss_gap=.054-(floor+3.25)
    assert pin_depth>=2.45 and boss_gap>=.15,(pin_depth,boss_gap)
    report['minimum_pin_depth_mm']=pin_depth
    report['maximum_socket_boss_gap_mm']=boss_gap
    report['full_frame_route_max_sample_step_mm'] = .1
    # The flange takes downward key presses; the bought switch's resilient
    # clips engage the 1.2mm plate against upward movement. Deflection during
    # insertion is deliberately left to the real factory clips, not simulated.
    capture = overlap(seat, hw['switch'].translate((0, 0, .4)))
    press_stop = overlap(seat, hw['switch'].translate((0, 0, -.25)))
    assert capture > .02 and press_stop > .02, (capture, press_stop)
    assert abs(cad.P['keys']['plate_thickness'] - 6 * cad.P['print']['layer_height']) < 1e-8
    report['socket_route_max_intersection_mm3'] = route
    report['switch_clip_capture_mm3'] = capture
    report['switch_flange_stop_mm3'] = press_stop
    report['plate_thickness_mm'] = cad.P['keys']['plate_thickness']
    report['plate_top_from_rod_axis_mm'] = cad.P['keys']['pcb_z'] + 2.25
    # Ethan's "thumb doesn't have to travel as far": compare every pair of
    # key centres, then check the illustrative full-size caps independently.
    positions = cad.key_positions()
    old_parameters = json.loads((cad.HERE.parent / 'carbon-rod-holders-r4/parameters.json').read_text())['keys']
    old_positions = [(-old_parameters['pitch'], 0), (0, 0), (old_parameters['pitch'], 0),
                     (-old_parameters['upper_half_spacing'], old_parameters['row_spacing']),
                     (old_parameters['upper_half_spacing'], old_parameters['row_spacing'])]
    distances = []
    cap_gaps = []
    for i, a in enumerate(positions):
        for j in range(i + 1, len(positions)):
            b = positions[j]
            before, after = math.dist(old_positions[i], old_positions[j]), math.dist(a, b)
            assert after < before, (i, j, before, after)
            distances.append({'keys': [i, j], 'before_mm': before, 'after_mm': after})
            gap = math.hypot(max(0, abs(a[0]-b[0])-16.6), max(0, abs(a[1]-b[1])-17.5))
            assert gap >= 1.8, (i, j, gap)
            cap_gaps.append(gap)
    report['key_centre_distances'] = distances
    report['minimum_illustrative_cap_gap_mm'] = min(cap_gaps)
    report['keycap_gap_is_not_measured_purchased_cap_fit'] = True
    for option in cad.OPTIONS:
        solid = read('Carrier_' + option)
        regions = {n: overlap(solid, s) for n, s in cad.references(option).items()
                   if n not in ['pcb', 'usb', 'wire', 'rod'] and not n.endswith('_cap')}
        regions['battery_reserve'] = overlap(solid, cad.battery_shape(option, True))
        for i,(x,y) in enumerate(cad.key_positions()):
            regions[f'key_{i}_max_socket_sensitivity']=overlap(solid,max_socket.translate((x,y,cad.P['keys']['pcb_z'])))
        assert max(regions.values()) < .002, (option, regions)
        full_routes={}
        for i,(x,y) in enumerate(cad.key_positions()):
            for label,shape in zip(['nominal','maximum_sensitivity'],[hw['socket'],max_socket]):
                full_routes[f'{i}_{label}']=max(overlap(solid,shape.translate((x+px,y+py,cad.P['keys']['pcb_z']+pz))) for px,py,pz in poses)
        assert max(full_routes.values())<.002,(option,full_routes)
        # Check intended joints, not merely final body count. Each front rail
        # must positively overlap each seat; the old .05mm gap was invisible
        # to a one-body test because a weak rear detour still connected it.
        joints=[]
        z=cad.P['keys']['pcb_z']
        for x,y in cad.key_positions():
            rail=cad.rib((x-8.2,y-9.4,z+1.4),(x+8.2,y-9.4,z+1.4),1.25)
            joints.append(overlap(cad.key_seat(outer_side=1 if x>0 else -1 if x<0 else 0).translate((x,y,z)),rail))
        assert min(joints)>1, joints
        free_ends={}
        for i,(x,y) in enumerate(cad.key_positions()):
            if x:
                probe=mf.Manifold.sphere(.55,16).translate((x+(7.9 if x>0 else -7.9),y-9.7,z-4.5))
                free_ends[str(i)]=overlap(solid,probe)
        assert max(free_ends.values())<.002,free_ends
        above=overlap(solid,cad.box(-80,80,-90,90,z+2.2501,40))
        assert above<.002,above
        # At least .2mm of flat flange bearing remains after the opening.
        land=cad.box(7.1,7.3,-5,5,z+2.15,z+2.25)
        assert overlap(solid,land)>.15
        floor_probe=cad.box(-.4,.4,4.5,6.5,4.2,5.4)
        assert float((floor_probe-solid).volume())<.002
        # Separate relaxed preload from the idealized expanded geometry.
        # This radial expansion model does not measure elastic force.
        bore = cad.cyl(cad.P['rod']['clip_diameter']/2-.001,-85,85).rotate((-90,0,0))
        assert overlap(solid,bore)<.002
        fitted = cad.carrier(option,clip_diameter=cad.P['rod']['diameter'])
        assert overlap(fitted,cad.cyl(3.999,-85,85).rotate((-90,0,0)))<.002
        preload = overlap(solid,cad.cyl(4,-85,85).rotate((-90,0,0)))
        assert .1 < preload < 30, preload
        report.setdefault('intentional_preload_mm3',{})[option]=preload
        anchors = cad.carrier_clip_centres(option)
        bands = {}; free_arm_excess = {}
        source_solid = cad.carrier(option)
        for y in anchors:
            band = cad.ring(y) ^ cad.tube_y(4.25,5.35,y-.4,y+.4)
            assert overlap(solid,cad.clip_gap(y))<.002
            bands[str(y)] = float((band - solid).volume())
            lower_shell = cad.tube_y(3.94,5.5,y-1.8,y+1.8) ^ cad.box(-6,6,y-2,y+2,-6,-.05)
            # Source Boolean probe avoids subtracting coincident float32 STL
            # triangles. Exported clip material is checked separately above.
            free_arm_excess[str(y)] = overlap(source_solid-cad.ring(y),lower_shell)
        assert max(bands.values()) < .002, (option, bands)
        assert max(free_arm_excess.values()) < .002, (option,free_arm_excess)
        # A nominal 3mm wiring corridor is separate from the carbon tube.
        wire = cad.wire_bus(-20, 55)
        assert overlap(solid, wire) < .002
        assert overlap(wire, cad.tube_y(3.5, 4, -20, 55)) < .002
        caps = [cad.references(option)[f'key_{i}_cap'] for i in range(5)]
        travel = {str(i): overlap(solid, c.translate((0, 0, -3))) for i, c in enumerate(caps)}
        assert max(travel.values()) < .002, (option, travel)
        report['options'][option] = {'bought_part_intersection_mm3': regions,
            'full_carrier_sampled_socket_loading_mm3':full_routes,'removed_outer_finger_pokes_mm3':free_ends,'front_rail_joint_overlap_mm3':joints,'above_common_print_face_mm3':above,'missing_clip_band_mm3': bands, 'illustrative_cap_at_full_travel_mm3': travel,
            'free_lower_arm_extra_material_mm3':free_arm_excess,
            'purchased_cap_underside_and_full_travel_verified': False,
            'final_stl_sha256': cad.sha(OUT / ('Carrier_' + option + '.stl'))}
    report['sensor_stl_identical_to_r2'] = cad.sha(OUT / 'XIAO_Rod_Holder.stl') == cad.sha(cad.HERE.parent / 'carbon-rod-holders-r2/exports/XIAO_Rod_Holder.stl')
    assert not report['sensor_stl_identical_to_r2']
    sensor = read('XIAO_Rod_Holder')
    sensor_refs = cad.references()
    checks = {n:overlap(sensor,sensor_refs[n]) for n in ['pcb','usb','wire']}
    assert max(checks.values())<.002, checks
    report['sensor_board_usb_wire_clearance']=checks
    sensor_free={}
    for y in [-3.8,22.2]:
        width=cad.P['rod']['sensor_clip_width']
        assert overlap(sensor,cad.clip_gap(y,width))<.002
        lower_shell=cad.tube_y(3.94,5.4,y-width/2,y+width/2) ^ cad.box(-6,6,y-2,y+2,-6,-.05)
        expected=cad.ring(y,width=width,root_wall=cad.P['rod']['sensor_clip_root_wall'])
        sensor_free[str(y)]=overlap(cad.sensor_holder()-expected,lower_shell)
    assert max(sensor_free.values())<.002,sensor_free
    report['sensor_free_lower_arm_extra_material_mm3']=sensor_free
    fitted_sensor=cad.sensor_holder(clip_diameter=cad.P['rod']['diameter'])
    assert overlap(fitted_sensor,cad.cyl(3.999,-30,60).rotate((-90,0,0)))<.002
    report['clip_bore_unloaded_mm']=cad.P['rod']['clip_diameter']
    report['nominal_tube_mm']=cad.P['rod']['diameter']
    report['radial_opening_per_arm_mm']=(cad.P['rod']['diameter']-cad.P['rod']['clip_diameter'])/2
    report['clip_design_note']='Nearly closed curved arms; end-loaded, not forced sideways over the tube. Geometry checks do not measure clamp force or creep.'
    report['passed'] = True
    (OUT / 'geometry-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: 3 layouts, switch/socket routes, open spring clips, deployed tube clearance, board/wires and battery reserve.')

if __name__ == '__main__': check()
