"""R65 wired mouse PCB, removable load-bearing seat and integral carrier receiver.

The original board frame has its origin at the mouse plunger. The separate
seat loads on the loose board before the combined parts enter the carrier.
"""
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "carbon-rod-holders-r64-under-entry"))
import design64 as r64

b = r64.b
OUT = HERE / "exports"
HOLDER = r64.HOLDER
SLED_FILE = "OP1_Seat_Sled-assembly.stl"
SLED = "op1_seat"
ACTORS = (*r64.ACTORS, SLED)
# Come only 1.15 mm above the bearing surfaces and slide straight in from the
# open nose. Keeping that small clearance for the whole near-carrier slide
# preserves the receiver land under the front tab as the rear tab passes it.
ENTRY_OFFSETS = ((17.,-66.,-26.), (17.,-66.,1.15), (0.,-66.,1.15),
                 (0.,0.,1.15), (0.,0.,0.))
FLOOR = 7.35
GUIDE_SIDE_GAP = .44
LOAD_HEIGHT = 8.
INSERT_CAPTION = ("With the black switch off, hold the wired PCB on its sled. "
                  "Raise them beside the rod at the nose, slide them in white connector first, "
                  "then lower the sled into the carrier's stops.")
REMOVE_CAPTION = ("With the upper retainer and black switch off, lift the PCB and sled together, "
                  "slide them towards the nose and lower them beside the rod.")


def actor_pose(name, offset):
    if name != SLED:
        return r64.actor_pose(name, offset)
    return np.column_stack((np.eye(3), offset)).ravel().tolist()


def entry_samples(spacing=1.):
    offsets = [np.asarray(ENTRY_OFFSETS[0])]
    for start, end in zip(ENTRY_OFFSETS, ENTRY_OFFSETS[1:]):
        count = math.ceil(np.linalg.norm(np.subtract(end, start)) / spacing) + 1
        offsets.extend(np.linspace(start, end, count)[1:])
    return [{name: actor_pose(name, offset) for name in ACTORS} for offset in offsets]


def seat_samples(spacing=1.):
    """Seat the loose prewired board while the sled is still outside the nose."""
    start = np.asarray(ENTRY_OFFSETS[0])
    frames = []
    for height in np.linspace(LOAD_HEIGHT, 0, math.ceil(LOAD_HEIGHT / spacing)+1):
        frames.append({name: actor_pose(name, start if name == SLED else start+(0,0,height))
                       for name in ACTORS})
    return frames


@lru_cache(maxsize=1)
def blanks():
    # Clip the four plan corners. The forward tab seats in a short drop-in
    # pocket; the outboard rear ear transfers load across to the other deck wall.
    plate = b.uprism([(-5.6,-9.5),(4.9,-9.5),(5.6,-8.8),(5.6,13.6),
                      (4.9,14.3),(-4.9,14.3),(-5.6,13.6),(-5.6,-8.8)], FLOOR, b.PCB_Z)
    # Two broad tabs span the open connector lane and land on the right
    # wall. Their outboard edges track the nearest fitted Choc switch.
    rear_ear = b.uprism([(4.4,9.2),(9.55,9.2),(9.72,9.8),(6.32,18.8),
                         (5.08,19.0),(4.4,18.32)], FLOOR, b.PCB_Z)
    front_ear = b.uprism([(4.4,-4.3),(14.9,-4.3),(15.22,-3.8),
                          (11.55,4.20),(11.05,4.55),(4.4,4.55)], FLOOR, b.PCB_Z)
    # Both moving tabs also pass the inner guard rail. Keep the full working
    # clearance along its fixed X=12.85 mm tangent during the whole slide.
    guard_limit = b.box(-30,12.38,-40,40,4,15)
    # A wide rim at the accessible front gives the user a place to hold the
    # loose board; the asymmetric stops locate the PCB without squeezing it.
    rim = b.ubox(-5.6, 3.4, -11.4, -9.0, FLOOR, b.PCB_Z)
    stops = [b.ubox(-5.55,3.4,-11.4,-9.40,b.PCB_Z-.15,10.40),
             b.ubox(-6.80,-5.35,6.5,12.0,FLOOR,10.40),
             b.ubox(5.35,6.8,10.2,13.5,FLOOR,10.40)]
    return [plate, front_ear ^ guard_limit, rear_ear ^ guard_limit, rim, *stops]


@lru_cache(maxsize=1)
def sled():
    # The three board sockets project 4.3 mm below its 1.6 mm laminate.
    # Let them pass entirely through the slab. All bearing lands end flush
    # with the underside of the laminate; installed electrical parts bear no load.
    holes = [mf.Manifold.cylinder(b.PCB_Z-FLOOR+.4, b.SOCKET_R+.50,
                                  b.SOCKET_R+.50, 64).translate((0,y,FLOOR-.20))
             for y in b.SOCKET_Y]
    return b.union(blanks()) - b.to_world(b.union(holes))


def swept_blanks(offsets, clearance=False, omit_seated_skin=0.):
    parts = []
    for blank in blanks():
        for i,(a,z) in enumerate(zip(offsets, offsets[1:])):
            p = mf.Manifold.batch_hull([blank.translate(a),blank.translate(z)])
            if clearance:
                gap = GUIDE_SIDE_GAP
                # Tiny export tolerance avoids coincident float32 triangles at
                # the nominal seat, far below one physical print layer.
                low = -.002 if i == len(offsets)-2 else -r64.ENTRY_VERTICAL_GAP
                p = p.minkowski_sum(b.box(-gap,gap,-gap,gap,low,r64.ENTRY_VERTICAL_GAP))
            if omit_seated_skin and i == len(offsets)-2:
                p -= b.box(-50,50,-90,80,FLOOR-.01,FLOOR+omit_seated_skin)
            parts.append(p)
    return b.union(parts)


def entry_check_solid(name, bearing_skin=0.):
    if not 0 <= bearing_skin <= .25:
        raise ValueError("The contact skin must be between 0 and 0.25 mm")
    if name == SLED:
        return swept_blanks(ENTRY_OFFSETS, omit_seated_skin=bearing_skin)
    if name != 'board' or not bearing_skin:
        return r64.sweep(name,offsets=ENTRY_OFFSETS)
    near = r64.sweep(name,offsets=ENTRY_OFFSETS[-2:])
    skin = r64.hardware()['board'].hull().project().extrude(bearing_skin+.001)
    return r64.sweep(name,offsets=ENTRY_OFFSETS[:-1]) + (near-skin.translate((0,0,b.PCB_Z-.001)))


def receiver(old):
    # New stock connects both landing areas to the original keypad deck. Cut
    # the buyable hardware and complete access paths *after* forming the roots.
    left = b.ubox(-9.,-1.,-9.5,14.6,6.3,FLOOR)
    # Keep the remaining withdrawal stop rooted through the unsupported end
    # of the old pocket floor; its last 0.05 mm foil cannot support the stop.
    nose_floor = b.box(-7.40,-2.60,-15.85,-9.82,6.30,FLOOR)
    right = b.ubox(4.2,18.,-4.2,19.3,5.9,FLOOR) ^ b.box(10.60,16.5,-14.8,18.,5.8,FLOOR)
    # Print progression is towards -Y. Grow the rear end of the outboard
    # landing from the solid deck wall rather than starting one bead beside it.
    root = b.box(12.24,13.65,14.0,14.22,7.26,8.15)
    landing = b.box(11.42,13.65,11.34,11.58,5.90,7.75)
    ramp = mf.Manifold.batch_hull([root,landing])
    right -= b.box(11.0,14.0,11.55,13.23,5.8,7.45)-ramp
    stock = r64.trim_keys(left + nose_floor + right + ramp)
    route = b.union(r64.sweep(n,clearance=True,offsets=ENTRY_OFFSETS) for n in r64.ACTORS)
    body = (old + stock) - route - swept_blanks(ENTRY_OFFSETS, clearance=True)
    # The sled replaces the old front-left pocket rim. Its very last curled
    # tip was attached only by a 0.05 mm skin and began in free air in PETG.
    toe = b.box(-10.60,-7.40,-17.3,-11.78,6.1,11.5)
    # A shallow lead-in below the left retainer bearing clears the finite
    # bead width on the first 5 mm of the slide, leaving the upper latch intact.
    lead_in = b.prism_yz([(-10.2,10.70),(-6.15,10.81),(-4.85,11.32),
                          (-4.85,11.48),(-10.2,11.48)],-8.80,-5.65)
    return body - toe - lead_in


def section_areas(section):
    def area(x0,x1,y0,y1):
        region = b.ubox(x0,x1,y0,y1,0,1).slice(.5)
        return round((section ^ region).area(),3)
    return dict(total=round(section.area(),3), left=area(-20,0,-30,30),
                right=area(0,20,-30,30),switch=area(-b.BODY_X,b.BODY_X,*b.BODY_Y),
                plunger=area(-1.45,1.45,-.6,.6))


def load_path(body,tray):
    # Measure both right-hand bearing tabs, their depth in the permanent wall
    # and the footprint enclosing the applied switch force.
    contact = (tray.translate((0,0,-.10)) ^ body).project()
    right = b.ubox(0,21,-21,21,0,1).slice(.5)
    force = np.array(b.STATION)
    hull = contact.hull().to_polygons()[0]
    edges = np.roll(hull,-1,axis=0)-hull
    delta = force-hull
    margins = (edges[:,0]*delta[:,1]-edges[:,1]*delta[:,0])/np.linalg.norm(edges,axis=1)
    # Probe the central portion of the longer front tab, clear of its chamfers.
    return dict(right_front_tab_mm2=round((contact ^ b.ubox(5,20,-4.,2.2,0,1).slice(.5)).area(),3),
                right_rear_tab_mm2=round((contact ^ b.ubox(5,20,9,19.3,0,1).slice(.5)).area(),3),
                right_bearing_backed_1mm_down_mm2=round((contact ^ right ^ body.slice(FLOOR-1.)).area(),3),
                plunger_inside_bearing_hull_margin_mm=round(float(margins.min()),3))


def retention(body, tray, old):
    # The tray cannot lift out of the recessed receiver while the PCB is held
    # down by the retainer. The three sockets pass through the tray, so a bare
    # lateral escape of the tray is also prevented independently of friction.
    board = r64.hardware()['board']
    lid = b.load(r64.old.OUT/r64.GUIDE['actors']['lid']['file'])
    results = []
    for angle in range(0,360,15):
        a = math.radians(angle)
        offset = (math.cos(a),math.sin(a),.25)
        results.append(r64.mm3(body,tray.translate(offset)))
    raised = lid.translate((0,0,.6))
    return dict(sled_stopped_at_1mm_with_0_25mm_lift_min_mm3=min(results),
                tested_in_plane_directions=len(results),
                lifted_sled_to_loaded_board_0_25mm_mm3=r64.mm3(tray.translate((0,0,.25)),board),
                r64_raised_lid_to_original_guide_mm3=r64.mm3(old,raised),
                r65_raised_lid_to_current_guide_mm3=r64.mm3(body,raised))


def loose_loading_gaps(moving_bounds, fixed_bounds):
    # The loose board moves only vertically. Its two endpoint boxes enclose
    # the complete sweep, so even these conservative fixture gaps prove it clear.
    swept = np.asarray(list(moving_bounds)).reshape(-1,2,3) + ENTRY_OFFSETS[0]
    swept[:,1,2] += LOAD_HEIGHT
    gaps = {}
    for name,bounds in fixed_bounds.items():
        lo,hi = np.asarray(bounds).reshape(2,3)
        delta = np.maximum(np.maximum(lo-swept[:,1],swept[:,0]-hi),0)
        gaps[name] = round(float(np.linalg.norm(delta,axis=1).min()),3)
    return gaps


def main():
    OUT.mkdir(exist_ok=True)
    old = b.load(r64.OUT/HOLDER)
    body = r64.old.one_piece(receiver(old),'R65 seat receiver',limit=.001)
    tray = sled()
    b.save_closed(OUT/HOLDER,body)
    b.save_closed(OUT/SLED_FILE,tray)
    body,tray = b.load(OUT/HOLDER),b.load(OUT/SLED_FILE)
    if len(body.decompose()) > 1:
        # Float32 export of coincident R64 skin triangles can expose a
        # zero-volume shell on reimport. Keep only the connected carrier.
        b.save_closed(OUT/HOLDER,r64.old.one_piece(body,'exported R65 carrier',limit=.001))
        body = b.load(OUT/HOLDER)
    hw = r64.hardware()
    board = hw['board']
    rod = r64.old.lay(mf.Manifold.cylinder(500,4,4,144),-250)
    entry = b.union(entry_check_solid(n) for n in ACTORS)
    parts = r64.fitted_key_hardware()
    fixtures = dict(parts,carrier=body,full_rod=rod)
    loose = loose_loading_gaps([s.bounding_box() for s in hw.values()],
                               {n:s.bounding_box() for n,s in fixtures.items()})
    mm3 = r64.mm3
    report = dict(revision='R65', physical_fit_verified=False,entry_offsets_mm=ENTRY_OFFSETS,
        entry_side_gap_mm=r64.ENTRY_SIDE_GAP, entry_vertical_gap_mm=r64.ENTRY_VERTICAL_GAP,
        sled_receiver_side_gap_mm=GUIDE_SIDE_GAP,pcb_socket_to_sled_radial_gap_mm=.50,
        pcb_bearing_mm2=section_areas((board.translate((0,0,-.10)) ^ tray).project()),
        receiver_bearing_mm2=section_areas((tray.translate((0,0,-.10)) ^ body).project()),
        receiver_added_mm3=round((body-old).volume(),3),
        receiver_cut_mm3=round((old-body).volume(),3),
        sled_volume_mm3=round(tray.volume(),3),
        carrier_components=[round(g.volume(),5) for g in body.decompose()],
        sled_components=[round(g.volume(),5) for g in tray.decompose()],
        hardware_to_sled_mm3={k:mm3(v,tray) for k,v in hw.items()},
        sled_and_board_path_to_installed_mm3={k:mm3(entry,v) for k,v in parts.items()},
        path_to_full_rod_gap_mm=round(entry.min_gap(rod,10),3),
        path_to_carrier_mm3={n:mm3(entry_check_solid(n),body) for n in ACTORS},
        seat_board_on_loose_sled_mm3={n:mm3(r64.sweep(n,offsets=[(0,0,LOAD_HEIGHT),(0,0,0)]),tray)
                                     for n in r64.ACTORS},
        loose_board_loading_to_fixture_min_gap_bounds_mm=loose,
        assembled_lid_capture=r64.seating_measurements(tray+body, old),
        receiver_capture=retention(body,tray,old),
        receiver_load_path=load_path(body,tray),
        material_trimmed_by_choc_service_routes_mm3=round((tray-r64.trim_keys(tray)).volume(),5),
        original_guard_rail_removed_mm3=mm3(old-body,r64.guard_returns(True)+r64.guard_returns(False)),
        mesh_sha256={n:sha256((OUT/n).read_bytes()).hexdigest() for n in (HOLDER,SLED_FILE)})
    seat=report['pcb_bearing_mm2']
    load=report['receiver_load_path']
    capture=report['receiver_capture']
    report['passes'] = all([
        len(report['carrier_components']) == len(report['sled_components']) == 1,
        seat['left']>70 and seat['right']>70 and seat['switch']>35 and seat['plunger']>2,
        min(load['right_front_tab_mm2'],load['right_rear_tab_mm2'])>3,
        load['right_bearing_backed_1mm_down_mm2']>12 and load['plunger_inside_bearing_hull_margin_mm']>3,
        capture['sled_stopped_at_1mm_with_0_25mm_lift_min_mm3']>.25,
        capture['r65_raised_lid_to_current_guide_mm3']>=capture['r64_raised_lid_to_original_guide_mm3']-.01,
        report['assembled_lid_capture']['additional_lid_interference_per_pose_mm3']<.01,
        report['assembled_lid_capture']['board_lifted_0_35mm_into_lid_mm3']>1,
        min(report['assembled_lid_capture']['board_shift_1mm_into_stops_at_0_2mm_lift_mm3'].values())>.2,
        max(report['hardware_to_sled_mm3'].values())<.001,
        max(report['sled_and_board_path_to_installed_mm3'].values())<.001,
        max(report['seat_board_on_loose_sled_mm3'].values())<.001,
        min(loose.values())>.5,
        max(report['path_to_carrier_mm3'].values())<.001 and report['path_to_full_rod_gap_mm']>.5,
        report['original_guard_rail_removed_mm3']<.005,
        report['material_trimmed_by_choc_service_routes_mm3']<.001])
    print(json.dumps(report,indent=2),flush=True)
    (OUT/'support.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['passes']:
        raise ValueError("R65 mechanical seat checks failed")


if __name__ == '__main__':
    main()
