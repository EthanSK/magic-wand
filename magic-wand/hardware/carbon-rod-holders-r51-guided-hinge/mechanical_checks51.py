"""Exercise the R51 printed meshes, bought hardware and hardware insertion routes, in mm."""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

import build51 as d


def vol(a,b):
    return max(0.,float((a^b).volume()))


def onset(test, limits):
    """Bracket a rising contact; smaller than one slicer micron in these travels."""
    lo,hi=limits
    if test(lo) or not test(hi):
        raise ValueError(f'Unbracketed contact in [{lo}, {hi}]')
    for _ in range(23):
        mid=(lo+hi)/2
        if test(mid):
            hi=mid
        else:
            lo=mid
    return (lo+hi)/2


def roll_at_hinge(shape, roll, dx=0., dz=0.):
    return shape.translate((0.,-d.AXIS_WORLD_Y,-d.AXIS_Z)).rotate((0.,roll,0.)).translate((dx,d.AXIS_WORLD_Y,d.AXIS_Z+dz))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checks(out):
    d.configure_new_op1()
    q,r,h=d.q,d.r,d.h
    C=d.baseline.b.load(out/'Key_Carrier-assembly.stl')
    P=d.baseline.b.load(out/'DFRobot_Hole_Bracket-assembly.stl')
    hardware={name:d.baseline.b.load(out/(name+'.stl')) for name in d.pivot_hardware()}
    pf=hardware['pivot-sleeve']
    ma=d.union(hardware.values())
    M=q.hardware()
    board=d.union(M[k] for k in ('board','sockets','housing','plug'))
    mouse=d.union(M[k] for k in ('switch','plunger','terminals'))
    stationary=d.union(M[k] for k in ('board','sockets','housing','plug','switch','terminals','fasteners','op1_wire'))
    # The heels limit rotation directly against these fixed carrier faces.
    feet=C^d.box(-11.,11.,-10.,-5.,12.2,13.11)
    heel=P^d.box(-11.,11.,-12.5,-8.,13.1,15.)
    nub=P^q.pusher()
    button=M['plunger']
    sensor_group=r.sensor()+r.connector()+r.electrode()+r.gravity_lead()+r.clips()+q.gravity_pins()
    # The face is a narrow rounded foot. CAD contact uses the first touching
    # point of the actual foot on the finite plunger (including at a tilted edge).
    def geom(s,a,roll=0.,dx=0.,dz=0.):
        return roll_at_hinge(d.world(s,a),roll,dx,dz)
    def drop(Pw):
        if vol(button,Pw)<1e-8:
            return 0.
        return onset(lambda delta: vol(button.translate((0,0,-delta)),Pw)<1e-8,(0.,1.35))
    def stop(roll,dx,dz):
        return onset(lambda angle: vol(feet,geom(heel,angle,roll,dx,dz))>1e-8,(-.4,.85))
    rest=onset(lambda angle:vol(button,geom(nub,angle))>1e-8,(-1.5,-.55))
    fixed=stop(0.,0.,0.)
    radial=d.BEARING_RADIUS-d.SLEEVE_RADIUS
    span=2*d.BEARING_HALF
    roll=math.degrees(math.atan(2*radial/span))
    free_side=(2*d.FORK_INNER-span)/2
    cases={}
    for name,angle,dx,dz in [('centre',0.,0.,0.),('copper_left',roll,-free_side,0.),
                              ('copper_right',-roll,free_side,0.),
                              ('vertical_float_high',0.,0.,radial),('vertical_float_low',0.,0.,-radial)]:
        last=stop(angle,dx,dz)
        face=geom(nub,last,angle,dx,dz)
        active=geom(P,last-.002,angle,dx,dz)
        cases[name]={'roll_deg':angle,'lateral_shift_mm':dx,'vertical_offset_mm':dz,'fixed_limit_deg':last,
                     'plunger_travel_at_first_heel_mm':drop(face),
                     'bracket_to_other_op1_mm3':vol(active,stationary)}
    cap_files=['Key_Carrier-assembly.stl','DFRobot_Hole_Bracket-assembly.stl',
               'op1_wire.stl','op1-wire-hanging.stl',*(n+'.stl' for n in hardware)]
    op1= {n:vol(C,m) for n,m in M.items() if n!='fasteners'}
    op1['fastener_heads']=vol(C,M['fasteners']^d.box(-40,40,-40,40,q.PCB_TOP+.01,40))
    pin_sweep=d.union(q.gravity_pins(max(q.PIN_TAILS),dx,dy) for dx in (-q.PIN_X_TOLERANCE,0.,q.PIN_X_TOLERANCE)
                      for dy in (-q.PIN_Y_TOLERANCE,0.,q.PIN_Y_TOLERANCE))
    static_touch={'pcb':r.sensor(),'copper':r.electrode(),'plug':r.connector(),'wire':r.gravity_lead(),
                  'pin_tolerance':pin_sweep,'two_clips':r.clips()}
    angles=np.linspace(rest-.03,fixed-.01,13)
    sweep={
       'paddle_to_carrier':max(vol(d.world(P,a),C) for a in angles),
       'paddle_to_other_op1':max(vol(d.world(P,a),stationary) for a in angles),
       'board_and_gravity_lead_to_carrier_axle_and_op1':max(vol(d.world(sensor_group+pin_sweep,a),C+ma+stationary) for a in angles),
       'paddle_to_axle_stack':max(vol(d.world(P,a),ma) for a in angles)}
    wk=h.d.geometry()[1]
    keys=d.union(wk[f'key_{i}_{p}'] for i in (0,2,3,4) for p in ('switch','maximum_socket','cap_travel'))
    wire_slot=d.baseline.cable48.check(h,C)
    # Real frame leaves a few micron-scale mesh fragments. Report actual
    # volumes and allow 0.001 mm3 signed tessellation round-off.
    tol=.001
    clear={'outer_keys_to_carrier':vol(keys,C),'outer_keys_to_mechanism':max(vol(keys,ma),vol(keys,stationary)),
           'op1_drop_with_plug_before_outer_keys':max(vol(board.translate((0.,0.,z)),C) for z in np.linspace(0,16,33)),
           'mouse_drop':max(vol(mouse.translate((0.,0.,z)),C+keys) for z in np.linspace(0,9,19)),
           'axle_to_carrier':vol(ma,C),
           'paddle_and_sleeve_drop':max(vol((d.world(P,rest)+pf).translate((0,0,z)),C+stationary) for z in np.linspace(0,14,29)),
           'dfr_board_to_paddle_drop':max(vol((r.sensor()+pin_sweep).translate((0,0,z)),P) for z in np.linspace(0,12,25)),
           'changing_dfr_hole_pitch':max(vol(r.sensor(pitch),P) for pitch in r.PITCH_RANGE)}
    for part,sign in [('pivot-screw',-1.),('pivot-locknut',1.)]:
        clear[part+'_insertion_without_outer_keys']=max(vol(hardware[part].translate((sign*x,0,0)),C+d.world(P,rest)+stationary) for x in np.linspace(0,32,33))
    bought_to_rod={k:float(M[k].min_gap(h.base.rod(),10.)) for k in ('op1_wire','plug','sockets','terminals')}
    # Working root sections across the two formerly separate outside guides.
    # Each reported section is attributable to just one fan, above its underside.
    # Inspect the old oblong reinforcements separately from working clearances.
    # The reference is a curved analytic boolean. STL facets can coincide with
    # its skin; verify the interior at 0.06 mm also, well inside a PETG bead.
    old_stock=d.projecting_chin_stock()
    core=old_stock
    for vector in ((.06,0,0),(-.06,0,0),(0,.06,0),(0,-.06,0),(0,0,.06),(0,0,-.06)):
        core ^= old_stock.translate(vector)
    original=d.baseline.b.load(d.INPUT/'Key_Carrier-assembly.stl')
    trim={'old_protrusions_mm3':vol(old_stock,original),'R51_reference_skin_mm3':vol(old_stock,C),
          'depth_0.06mm_core_remaining_mm3':vol(core,C)}
    areas={}
    for sign in (-1,1):
        patch=P^d.box(0 if sign>0 else -10.1,10.1 if sign>0 else 0,7,24.1,16.,19.2)
        side=patch.rotate((90,0,0))
        areas[str(sign)]={str(station):side.slice(station).area() for station in (13.9,16.5,19.,21.1,23.3)}
    cycle=[float(v) for v in np.linspace(rest,fixed,11)]
    cycle=cycle+cycle[-2::-1]
    guide_frames=[{'angle_deg':a,'plunger_drop_mm':drop(geom(nub,a))} for a in cycle]
    wire_mesh=trimesh.load_mesh(out/'op1_wire.stl',process=False)
    hanging_mesh=trimesh.load_mesh(out/'op1-wire-hanging.stl',process=False)
    results={
        'model':'R51','physical_fit_tested':False,'printed':False,'units':'mm',
        'dimensions':d.shifts(),'files':{n:file_hash(out/n) for n in cap_files},
        'hardware':['M2 × 20 mm socket-head screw (3.8 mm head diameter)','3 mm OD × 2.1 mm ID × 12.0 mm smooth metal spacer','M2 nylon-insert locknut, 4 mm across flats × 2.5 mm'],
        'bearing':{'bore_mm':2*d.BEARING_RADIUS,'effective_span_mm':span,'radial_clearance_mm':radial,
                   'max_roll_deg':roll,'roll_only_edge_excursion_mm_at_copper_edge':9.75*math.sin(math.radians(roll)),
                   'opposite_edges_vertical_difference_from_roll_mm':19.5*math.sin(math.radians(roll)),
                   'unclamped_total_axial_slack_mm':2*free_side,'total_axial_slack_with_cheeks_on_spacer_mm':d.SLEEVE_LENGTH-span,
                   'spacer_entry_clearance_per_side_mm':d.FORK_INNER-d.SLEEVE_LENGTH/2,
                   'assumptions':'Rigid parts at CAD dimensions with spacer fixed to cheeks; print tolerance, component flex and wear are unmeasured.'},
        'contact':{'first_contact_deg':rest,'fixed_heel_contact_deg':fixed,'plunger_model_at_zero_deg_mm':q.DEPRESSION,
                   'lever_mm':q.LEVER,'press_cases':cases,'trigger_note':'0.48 mm is the project design target. The actual fitted microswitch electrical actuation and endurance are unmeasured.'},
        'intersections_mm3':{'seated_op1':op1,'paddle_to_dfr_parts':{n:vol(P,s) for n,s in static_touch.items()},
                              'moving':sweep,'assembly':clear},'op1_harness_outlet':wire_slot,
        'trimmed_chin':trim,'op1_rod_gaps_mm':bought_to_rod,'fan_sections_mm2':areas,
        'viewer':{'click_path':guide_frames,'paddle_rest_matrix':d.placement(rest).tolist(),
                  'assembly_order':['OP1 and its lead','spacer into loose paddle','paddle and spacer between cheeks','axle screw from negative X','locknut from positive X','DFRobot board and two clips','outer Choc switches']}}
    results['gates']={
       'no_early_stop_before_design_depression_including_corner_press':min(v['plunger_travel_at_first_heel_mm'] for v in cases.values())>.48,
       'nominal_heel_catches_before_plunger_fully_retracted':max(v['plunger_travel_at_first_heel_mm'] for v in cases.values())<.86,
       'even_corner_press_clears_switch_housing':max(v['bracket_to_other_op1_mm3'] for v in cases.values())<tol,
       'installed_op1_and_pad_clear':max([*op1.values(),*(vol(P,s) for s in static_touch.values())])<tol,
       'pad_clears_other_parts_through_stroke':max(sweep.values())<tol,
       'printed_boards_wire_and_axle_clear_insertion_paths':max(clear.values())<tol and wire_slot['passes'],
       'old_chin_runners_and_saddle_projections_removed':trim['old_protrusions_mm3']>80 and trim['R51_reference_skin_mm3']/trim['old_protrusions_mm3']<.001 and trim['depth_0.06mm_core_remaining_mm3']<tol,
       'electronics_clear_rod':min(bought_to_rod.values())>.2,
       'both_fans_have_broad_continuous_sections':min(a for row in areas.values() for a in row.values())>5.,
       'op1_wire_morph_matches_triangle_order':np.array_equal(wire_mesh.faces,hanging_mesh.faces) and len(wire_mesh.vertices)==len(hanging_mesh.vertices)}
    return results


if __name__=='__main__':
    directory=Path(sys.argv[1]) if len(sys.argv)>1 else d.EXPORT
    result=checks(directory)
    for name,group in result['intersections_mm3'].items(): print(name,group,flush=True)
    print('contact',result['contact'],flush=True)
    print('gates',result['gates'],flush=True)
    if not all(result['gates'].values()):
        raise SystemExit('Mechanical audit did not pass.')
    result['generator_sha256']={path.name:file_hash(path) for path in (Path(__file__),Path(d.__file__))}
    (directory/'mechanical-fit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
