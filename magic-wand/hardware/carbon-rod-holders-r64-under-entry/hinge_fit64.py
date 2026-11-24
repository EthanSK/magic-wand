"""Check the exact assembled R64 meshes, both hinge pins and the bought reference parts."""
from hashlib import sha256
import json

import numpy as np

import hinge64 as h

b, m, r61, k = h.b, h.m, h.r61, h.previous.k
vol = h.previous.vol


def max_volume(body, fixed, translations):
    return round(max(vol(body.translate(tuple(v)), fixed) for v in translations), 5)


def directional_clearance(body, fixed, direction):
    vector = np.asarray(direction)
    lo, hi = 0., 1.
    assert vol(body.translate(vector*hi),fixed)>.001
    for _ in range(16):
        middle = (lo+hi)/2
        if vol(body.translate(vector*middle),fixed) > .00001:
            hi = middle
        else:
            lo = middle
    return round(lo, 3)


def paddle_layer_backing(paddle):
    """Geometric section check in the actual upside-down paddle print orientation."""
    shape = paddle.rotate((180,0,0)).translate((0,0,b.SEAT_Z))
    below = None
    unsupported = []
    largest = 0.
    for height in np.arange(.09,b.SEAT_Z-paddle.bounding_box()[2],.18):
        section = shape.slice(float(height))
        if below is not None:
            for ring in section.decompose():
                if (ring ^ below.offset(.1)).is_empty() and ring.area()>.015:
                    unsupported.append(dict(height_mm=round(height,3),area_mm2=round(ring.area(),3)))
            overhang = section - below.offset(.35)
            largest = max([largest]+[s.area() for s in overhang.decompose()])
        below = section
    return dict(layer_step_mm=.18,unsupported_new_sections=unsupported,
                largest_region_beyond_previous_section_by_0_35_mm2=round(largest,3))


def run(carrier_path, paddle_path, wires_path, lid_path):
    carrier, paddle, wires, lid = (b.load(path) for path in (carrier_path,paddle_path,wires_path,lid_path))
    k.old.configure_new_op1()
    purchased = k.q.hardware()
    board = k.r.sensor().translate((0,k.r.CLICK_SHIFT,0)).transform(r61.FLIP)
    bar = b.load(r61.prior.old.n.R57/'exports/DFR_Post_Bar-assembly.stl')
    clip = h.clip()
    fasteners = bar + b.union(b.load(r61.prior.PREVIOUS/'exports'/f'DFR_Clip_{side}-assembly.stl') for side in ('Left','Right'))
    plugged = board + r61.housing() + r61.plug() + wires
    moving = paddle + plugged + fasteners + clip
    fixed = carrier + lid + h.pin() + b.union(purchased[n] for n in ('board','plug','sockets','op1_wire','housing','terminals'))
    stop = k.onset(lambda a:vol(h.rotate(paddle,a),purchased['switch'])>.001, 0,4,24)
    trigger = k.onset(lambda a:vol(h.rotate(paddle,a),purchased['plunger'])>.001, 0,stop,24)
    lift = k.first_true(lambda a:vol(h.rotate(paddle,-a),lid)>.00001,list(np.linspace(0,6,61)))
    assert 0 < trigger < stop < 4 and 0 < lift < 6, (trigger,stop,lift)
    poses = np.linspace(-lift+.025,stop-.035,19)
    half = h.m.CHEEK_X[1] + .25
    line=(h.AXIS,h.KEEPER_Z)
    common = h.previous.go([h.previous.shadow(carrier,-34.,34.,line),h.previous.shadow(paddle,-half,half,line)],line)
    limits = {}
    zone=b.box(-12.,12.,h.AXIS-4.65,h.REAR+.5,h.KEEPER_Z-4.2,h.KEEPER_Z+4.2)
    barrel = paddle ^ zone
    bearings = carrier ^ zone
    for shift in (0., .20, .40):
        raised = barrel.translate((0,0,shift))
        limits[f'z_{shift:.2f}'] = {axis:directional_clearance(raised,bearings,v) for axis,v in
                                    (('forward',(0,-1,0)),('rearward',(0,1,0)),('left',(-1,0,0)),('right',(1,0,0)))}
    gaps = dict(seated_bundle_to_cheeks=round(wires.min_gap(carrier,4.),3),
                seated_bundle_to_paddle=round(wires.min_gap(paddle,4.),3),
                seated_bundle_to_clip=round(wires.min_gap(clip,4.),3),
                bundle_to_holder_during_press=round(min(h.rotate(wires,a).min_gap(carrier,4.) for a in poses),3))
    overlap = dict(wired_board_drop_over_posts=max_volume(plugged,paddle+bar,[(0,0,z) for z in np.arange(0,13.1,.4)]),
                   cable_post_bar_to_paddle=round(vol(wires+r61.plug(),bar+paddle),5),
                   prewired_paddle_lowered_into_bearings=max_volume(paddle+plugged+fasteners,carrier,[(0,0,z) for z in np.arange(0,19.1,.4)]),
                   clip_from_rear=max_volume(clip,carrier+paddle+plugged+fasteners,[(0,y,0) for y in np.arange(0,22.1,.35)]),
                   wired_click_sweep_to_carrier_and_op1=round(max(vol(h.rotate(moving,a),fixed) for a in poses),5),
                   side_press_to_retainer=round(max(vol(h.rotate(paddle,a).translate((x,0,0)),lid)
                                                    for x in (-.16,0,.16) for a in np.linspace(0,stop,9)),5))
    spaces = k.h.d.geometry()[1]
    key_names = [f'key_{i}_{part}' for i in (0,2,3,4) for part in ('switch','maximum_socket','cap_travel')]
    keys = b.union(h.previous.placed(spaces[n],n) for n in key_names)
    overlap.update(socket_below_sensor_to_paddle=round(vol(r61.housing(),paddle),5),
                   fixed_socket_to_post_bar=round(vol(r61.housing(),fasteners),5),
                   plug_mates_with_board_off_paddle=max_volume(r61.plug(),board,[(0,y,0) for y in np.arange(0,9.1,.5)]),
                   all_outer_switches_caps_and_sockets_to_wired_paddle=round(max(vol(h.rotate(moving,a),keys) for a in poses),5),
                   clip_to_paddle=round(vol(clip,paddle),5))
    # Apply the switch maker's operating and case-stop datum at the actual
    # plunger station. Rotation is about this revision's shortened hinge.
    def drop(y, z, angle):
        a=np.radians(angle)
        return (h.AXIS-y)*np.sin(a)+(z-h.KEEPER_Z)*(1-np.cos(a))
    target=b.FREE_TOP-(b.OPERATE[0]-.1)
    travel=drop(b.STATION[1],b.FREE_TOP,stop)-drop(b.STATION[1],b.FREE_TOP,trigger)
    face_points={'centre':(0,(board.bounding_box()[1]+board.bounding_box()[4])/2),
                 'left_front':(-9,board.bounding_box()[1]+1), 'right_front':(9,board.bounding_box()[1]+1)}
    touch_travel={name:round(drop(y,board.bounding_box()[5],stop),3) for name,(x,y) in face_points.items()}
    # The convex click pad still reaches a switch plugged in the opposite way.
    mirrored=np.asarray(b.board_point(0,b.MIRROR_STATION))-np.asarray(b.STATION)
    reversed_plunger=purchased['plunger'].translate((*mirrored,0))
    reversed_trigger=k.onset(lambda a:vol(h.rotate(paddle,a),reversed_plunger)>.001,-lift,stop,24)
    y_reversed=b.board_point(0,b.MIRROR_STATION)[1]
    reversed_travel=drop(y_reversed,b.FREE_TOP,stop)-drop(y_reversed,b.FREE_TOP,reversed_trigger)
    assert travel>target and reversed_travel>target,(travel,reversed_travel,target)
    for name in ('Hinge_Pin','Hinge_Pin_Snug'):
        shaft = h.pin(name)
        overlap[name+'_insertion_both_sides']=max_volume(shaft,carrier+paddle+plugged+fasteners,
                                                         [(x,0,0) for x in np.linspace(-27,27,109)])
        overlap[name+'_clip_seated']=round(vol(shaft,clip),5)
    # An off-centre press can roll the paddle until its outside journal seats.
    # Check both directions with a small lateral translation towards the loaded
    # edge. Record travel at the switch before the case stop in each pose.
    edge_press = {}
    for sign,name in ((-1,'left'),(1,'right')):
        def leaned(shape):
            return shape.translate(-h.PIVOT).rotate((0,sign*.45,0)).translate(
                h.PIVOT+np.array([sign*.10,0,.055]))
        tilted = leaned(paddle)
        end=k.onset(lambda a:vol(h.rotate(tilted,a),purchased['switch'])>.001,0,4,24)
        start=k.onset(lambda a:vol(h.rotate(tilted,a),purchased['plunger'])>.001,-lift,end,24)
        # The clip stays in the pin groove while the paddle shifts around it.
        obstacles=carrier+lid+h.pin()+clip+keys
        ride=leaned(paddle+plugged+fasteners)
        used=np.linspace(0,end-.025,9)
        hit=max(vol(h.rotate(ride,a),obstacles) for a in used)
        overlap[f'{name}_edge_press_to_fixed_parts']=round(hit,5)
        measured=drop(b.STATION[1],b.FREE_TOP,end)-drop(b.STATION[1],b.FREE_TOP,start)
        edge_press[name]=dict(roll_deg=sign*.45,lateral_offset_mm=sign*.10,
                              button_contact_deg=round(start,5),case_stop_deg=round(end,5),
                              plunger_travel_at_case_mm=round(measured,4))
        assert measured>target,edge_press
    paddle_layers = paddle_layer_backing(paddle)
    assert not paddle_layers['unsupported_new_sections'],paddle_layers
    sources = {path.name:sha256(path.read_bytes()).hexdigest() for path in (carrier_path,paddle_path,wires_path,lid_path)}
    report = dict(assembled_sha256=sources, carrier_sha256=sources[carrier_path.name], physical_fit_verified=False,
                  button_contact_deg=trigger, case_stop_deg=stop, lift_stop_deg=lift,
                  plunger_travel_at_case_mm=round(travel,4), reversed_plunger_travel_mm=round(reversed_travel,4),
                  reversed_button_first_contact_deg=reversed_trigger,
                  lowest_operating_point_travel_mm=target, face_travel_to_stop_mm=touch_travel,
                  board_rear_y_mm=round(board.bounding_box()[4],3),outer_paddle_y_mm=round(paddle.bounding_box()[4],3),
                  pcb_rear_to_paddle_end_mm=round(paddle.bounding_box()[4]-board.bounding_box()[4],3),
                  wire_rear_y_mm=round(wires.bounding_box()[4],3),
                  full_height_cheek_rear_y_mm=round(h.REAR-.45,2),rear_rod_and_battery_bed_y_mm=h.previous.BED,
                  centreline_yz_mm=list(line),common_round_straight_line_diameter_mm=2*common[0],
                  common_round_straight_line_yz_mm=common[1],journal_travel_each_direction_mm=limits,
                  bought_harness_clearances_mm=gaps, paddle_layer_backing=paddle_layers,
                  nominal_wire_centreline_lengths_to_open_side_mm=[round(float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum()),2) for path in h.wire_paths()],
                  edge_press=edge_press,
                  overlap_mm3=overlap,
                  assumptions='PCB below-face housing, plug dimensions, 1.3 mm insulated wires and bend are nominal. Physical printed bearing friction, click force and cable flexibility remain unmeasured.')
    assert max(overlap.values())<.012 and min(gaps.values())>.12,report
    assert common[0] >= 1.76 and len(wires.decompose()) == 3,report
    assert max(max(v.values()) for v in limits.values())<.19,limits
    return report


if __name__ == '__main__':
    result = run(h.OUT/h.previous.HOLDER,h.OUT/h.previous.PADDLE,h.OUT/'Gravity_Wires-assembly.stl',
                 r61.prior.PREVIOUS/'exports/OP1_Lid_Stop-assembly.stl')
    (h.OUT/'click-fit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
