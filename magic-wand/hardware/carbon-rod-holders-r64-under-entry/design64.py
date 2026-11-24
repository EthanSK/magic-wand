"""R64 OP1 entry from underneath the nose of the key holder, and rounded guard returns.

Assembly coordinates and bought-hardware meshes are the same ones used by the click
guide. The rod runs along Y. The removable mouse switch is fitted after the PCB.
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
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r63-open-hinge'))
import design63 as old
import hinge64

b = old.b
OUT = HERE / 'exports'
HOLDER, COLLET_FILE = old.HOLDER, old.COLLET_FILE
COLLET_ID = 7.96
ACTORS = ('board', 'sockets', 'housing', 'plug', 'op1_wire')
GUIDE = json.loads((old.OUT / 'assembly-guide.json').read_text())['modules']['pin_hinge']
SEATED = GUIDE['steps'][0]['samples'][-1]
# A wide free-space approach locates the PCB beside the tube first. The connector
# then enters the lower front opening before the PCB reaches its seated height.
# The brief final drop engages the low perimeter stops under the existing lid.
ENTRY_OFFSETS = ((17., -66., -26.), (17., -66., -.15), (-.30, -66., -.15),
                 (-.30, -22., -.15), (0., -9., 1.15), (0., 0., 1.15), (0., 0., 0.))
ENTRY_SIDE_GAP = .57
ENTRY_VERTICAL_GAP = .38
CONNECTOR_SIDE_GAP = .90


def actor_pose(actor, offset):
    """3×4 row-major guide transform for a bought actor; wire STL is already in world coordinates."""
    frame = np.asarray(SEATED[actor], float).reshape(3, 4).copy()
    frame[:, 3] += offset
    return frame.ravel().tolist()


def entry_samples(spacing=1.0):
    """Linearly spaced, ordered samples for the viewer and the native-path check."""
    offsets = [np.asarray(ENTRY_OFFSETS[0])]
    for start, end in zip(ENTRY_OFFSETS, ENTRY_OFFSETS[1:]):
        length = np.linalg.norm(np.subtract(end, start))
        offsets.extend(np.linspace(start, end, math.ceil(length / spacing) + 1)[1:])
    return [{name:actor_pose(name, offset) for name in ACTORS} for offset in offsets]


@lru_cache(maxsize=1)
def hardware():
    return {n: b.load(old.OUT / GUIDE['actors'][n]['file']).transform(
        np.asarray(actor_pose(n, (0, 0, 0))).reshape(3, 4)) for n in ACTORS}


def convex_components(name):
    solid = hardware()[name]
    if name == 'op1_wire':
        # Bound the curved cable closely without assuming just its two endpoints
        # define its collision volume. Convex pieces overlap across each station.
        lo, hi = solid.bounding_box()[1::3]
        pieces = [solid ^ b.box(0, 20, y-.001, y+2.001, -3, 12)
                  for y in range(math.floor(lo), math.ceil(hi), 2)]
    else:
        pieces = solid.decompose()
    return [part.hull() for part in pieces if not part.is_empty()]


def sweep(name, clearance=False, offsets=ENTRY_OFFSETS):
    # On a translation segment the convex hull of each component's endpoints
    # contains every intermediate point. The actual rod is checked independently.
    swept = []
    for p in convex_components(name):
        for index, (start, end) in enumerate(zip(offsets, offsets[1:])):
            piece = mf.Manifold.batch_hull([p.translate(start), p.translate(end)])
            if clearance:
                g = CONNECTOR_SIDE_GAP if name in ('housing', 'plug') else ENTRY_SIDE_GAP
                v = ENTRY_VERTICAL_GAP
                # Preserve the seated PCB bearing plane. The other four actors
                # retain clearance all around them throughout the movement.
                floor = 0 if name == 'board' and index == len(offsets)-2 else -v
                piece = piece.minkowski_sum(b.box(-g, g, -g, g, floor, v))
            swept.append(piece)
    return b.union(swept)


def entry_check_solid(name, bearing_skin=0.0):
    """Solid checked against deposited paths. All earlier entry positions stay intact.

    A slice checks its finite-height beads against the seated board. The caller
    can exempt a thin skin directly on the final bearing plane. No other actor,
    off-seat board position, lateral clearance or underside component is exempt.
    """
    if name != 'board' or bearing_skin == 0:
        return sweep(name)
    if not 0 <= bearing_skin <= .25:
        raise ValueError('The board bearing skin must be between 0 and 0.25 mm')
    last = sweep(name, offsets=ENTRY_OFFSETS[-2:])
    footprint = hardware()['board'].hull().project()
    contact = footprint.extrude(bearing_skin+.001).translate((0,0,b.PCB_Z-.001))
    return sweep(name, offsets=ENTRY_OFFSETS[:-1]) + (last-contact)


def pcb_stock():
    # A shallow integral floor carries the board rather than its solder joints.
    # The four short corner stops locate its outside edges when the lid is closed.
    stock = [b.ubox(-5.90, 5.90, -10.0, 21.95, 7.30, b.PCB_Z)]
    for edge in (b.PCB_Y[0], b.PCB_Y[1]):
        for x in (-4.25, 4.25):
            stock.append(b.ubox(x-1.25, x+1.25, edge-1.75, edge+1.75, 7.35, 10.0))
    return b.union(stock)


GUARD_ROOT_Y = -6.60


@lru_cache(maxsize=1)
def unguarded_deck():
    # Use the original keypad perimeter, including its radius at the outer corners.
    return old.prior.geometry()[1]


def smooth_return(x):
    # Bottom is -Y in the finger-side view. The rail now enters the underside
    # almost tangent to the deck, with the full 2.7 mm diameter inside its outline.
    return np.array([(x, GUARD_ROOT_Y, 8.12), (x, GUARD_ROOT_Y+3.2, 8.04),
                     (x, -1.0, .88), old.r62.CROWN_END])


def bezier(nodes, t):
    a, b1, c, d = nodes
    return (1-t)**3*a + 3*(1-t)**2*t*b1 + 3*(1-t)*t*t*c + t**3*d


def guard_returns(left):
    rails = [smooth_return(x) for x in (14.2, old.LEFT_RAIL_X if left else 28.3)]
    shapes = [old.r61.curve(curve, 1.35) for curve in rails]
    if left:
        # Close the old dangling tip into the second bottom rail, below the
        # backing strip. Both tangents at the turn point have the same direction.
        end = bezier(rails[1], .50)
        turn = np.array([25.5, -2.65, .85])
        prev = np.array([27.15, -1.95, .68])
        shapes.extend([old.r61.curve([old.r62.CROWN_END, (26.6, 1.5, .75), prev, turn], 1.26),
                       old.r61.curve([turn, 2*turn-prev, (20.1, -2.55, 2.55), end], 1.26)])
    shape = b.union(shapes)
    return shape.mirror((1,0,0)) if left else shape


def revised_guards(source):
    # Replace the old rounded ends above AND below the keypad underside. Keep
    # the actual deck intact, including its original radiused front edge.
    old_runs = []
    for side, rails in [(1, (14.2, 28.3)), (-1, (14.2, old.LEFT_RAIL_X))]:
        pieces = [old.r61.curve(old.r62.bottom_path(x), 1.36) for x in rails]
        if side < 0:
            pieces.append(old.r61.run([old.r62.CROWN_END, *old.LEFT_ARM], 1.27))
        shape = b.union(pieces)
        old_runs.append(shape if side > 0 else shape.mirror((1,0,0)))
    below = b.box(-33,33,-14,5.25,-5,7.27)
    rails = b.union(old_runs)
    core = source - (rails ^ below) - ((rails ^ b.box(-32,32,-12,-5.4,old.DECK-.01,9.75)) - unguarded_deck())
    # The old left gusset ended as a rectangular nub below the rounded deck.
    # Keep its supported middle and retire the projecting front with the old rail.
    (gx0,gx1),(gy0,gy1),depth = old.ROOT_GUSSET
    gusset = b.prism_yz([(gy0,old.DECK+.03),(gy1,old.DECK+.03),(gy1,old.DECK-depth)],gx0,gx1)
    core -= (gusset ^ b.box(gx0-.01,gx1+.01,-12,-8.,old.DECK-depth-.01,old.DECK+.04)) - unguarded_deck()
    # Respect the actually machined reliefs around the two corner switches.
    added = trim_keys(guard_returns(True)+guard_returns(False))
    strips = [b.load(old.OUT / old.BACKER), b.load(old.prior.old.R58 / 'exports/Socket_Backer_Right-assembly.stl')]
    for strip, sign in zip(strips, (-1, 1)):
        added -= mf.Manifold.batch_hull([strip, strip.translate((26*sign,0,0))])
    return core, added


@lru_cache(maxsize=1)
def key_clearance_cutters():
    d44 = old.k.h.d
    spaces = old.prior.geometry()[3]
    return {n:old.placed(v,n) for n,v in d44.socket_print_cutters(spaces).items()
            if n.startswith('key_')}


def trim_keys(stock):
    return old.k.h.d.r22.spaces16.carve(stock, key_clearance_cutters(), 'R64 lower banks')


def lid_rail_backing():
    # The new channel passes below the right retainer rail. Anchor the roof
    # on its outer edge so both guides remain attached. A rear-in-print ramp
    # grows the roof from the backed deck instead of bridging the rail length.
    post = b.ubox(8.26, 16.0, 1.65, 9.9, 8.62, 13.25)
    ramp = b.to_world(b.prism_yz([(9.88,8.62),(14.4,8.62),(14.4,9.0),(9.88,13.25)],8.26,16))
    return trim_keys((post+ramp) ^ b.box(-13.4,13.40,-18,22,8,15))


@lru_cache(maxsize=1)
def entry_clearance():
    return b.union(sweep(name, clearance=True) for name in ACTORS)


def bearing_and_entry(body):
    # Replacing the floor also replaces the old compliant eyelet fingers. There
    # are no narrow posts to thread or depress while the PCB is being raised.
    old_tips = b.ubox(-5.38, 5.38, -9.45, 20.3, b.PCB_Z-.003, 10.9)
    bearing = (body - old_tips) + trim_keys(pcb_stock()) + lid_rail_backing()
    # The old right-side wiring rib ends in a detached, sub-bead feather
    # after the lead passes through. Open this last corner into the channel.
    feather = b.box(10.40,10.86,3.22,5.29,3.36,3.83)
    return bearing - entry_clearance() - feather


def printable_entry_edges(body):
    # The first native slice left five single-bead fragments at the bottom
    # of the PCB floor. These were 0.1 mm shelves projecting out beyond the
    # two vertical walls alongside the connector lane. Remove their unsupported
    # undersides up to the plan of the substantial wall immediately above.
    z0, z1 = 7.05, 7.56
    windows = b.box(.6,3.65,1.2,13.2,z0,z1) + b.box(10.2,13.2,5.2,14.0,z0,z1)
    wall = body.slice(z1+.03).extrude(z1-z0+.04).translate((0,0,z0-.02))
    body -= windows - wall
    # The old inner tip behind the sliding lid's right end stop grew in the
    # air after the bottom entry opened under it. Grow the lip at 45 degrees
    # from the supported outboard wall as the print advances toward -Y.
    bevel = [(6.4,1.40),(8.20,1.40),(13.15,6.35),(13.15,8.1),(6.4,8.1)]
    body -= b.prism_xy(bevel,12.35,13.55)
    # A bevel alone still started as an isolated dot at Y=3.5: the right
    # Choc opening leaves no outboard wall above Z=12.5 at that station.
    # A continuous beam instead grows from the deck BEHIND the OP1 connector.
    # The back end ramps up in the build direction, then carries the guide lip
    # across the full channel, above the PCB and the sliding lid.
    rib = b.prism_yz([(1.35,12.57), (1.35,13.53), (14.25,13.53), (20.0,8.35),
                      (20.0,7.55), (17.7,7.55), (12.65,12.57)], 10.50,11.78)
    return body + (trim_keys(rib) - entry_clearance())


def carrier_transform(body):
    core, guards = revised_guards(body)
    return printable_entry_edges(bearing_and_entry(core + guards))


def collet():
    # Only indexed vertices on the bore move. Flange, taper, slot faces and
    # insertion depth retain the original dimensions and the split stays open.
    ring = b.load(old.OUT / old.COLLET_FILE)
    def shrink(points):
        pts = points.copy()
        radii = np.hypot(pts[:,0], pts[:,2])
        inside = abs(radii-old.COLLET_BORE_R) < .005
        factor = (COLLET_ID / 2) / old.COLLET_BORE_R
        pts[inside,0] *= factor
        pts[inside,2] *= factor
        return pts
    return ring.warp_batch(shrink)


def mm3(a,b1):
    return round(max(0., float((a ^ b1).volume())), 5)


def fitted_key_hardware():
    module = json.loads((old.OUT/'assembly-guide.json').read_text())['modules']['key']
    frame = module['steps'][-1]['samples'][-1]
    names = ['rod', *(f'{kind}_{i}' for i in (0, 2, 3, 4) for kind in ('switch', 'socket'))]
    return {n: b.load(old.OUT/module['actors'][n]['file']).transform(np.asarray(frame[n]).reshape(3,4))
            for n in names}


def front_y(solid, x, z):
    # Follow a ray through the actual finished STL at precisely this X and Z.
    hits = solid.ray_cast((x,-17.,z),(x,-2.,z))
    return min((hit.position[1] for hit in hits), default=None)


def guard_measurements(body, original, core, guards):
    roots = {}
    for sign, xs in [(1, (14.2,28.3)), (-1,(14.2,old.LEFT_RAIL_X))]:
        for x in xs:
            curve = smooth_return(x) * (sign, 1, 1)
            names = ('left' if sign < 0 else 'right') + (' inner' if x==14.2 else ' outer')
            # Cut transverse disks through the actual root and its first bend.
            # The circular mask limits the result to the specified rail diameter.
            areas = []
            for t in np.linspace(0,.52,15):
                centre = bezier(curve,t)
                tangent = bezier(curve,t+.001) - bezier(curve,t-.001)
                tangent /= np.linalg.norm(tangent)
                u = np.cross(tangent, (1,0,0))
                u /= np.linalg.norm(u)
                basis = np.array([u, np.cross(tangent,u), tangent])
                frame = np.column_stack((basis, -basis @ centre))
                section = body.transform(frame).slice(0) ^ mf.CrossSection.circle(1.34,48)
                areas.append(section.area())
            probe = old.r61.curve(curve,1.35)
            profile = []
            for z in [3., 5., 6.75]:
                station = b.box(x*sign-2.,x*sign+2.,-13.,1.0,z,z+.10)
                old_edge = (original ^ station).bounding_box()[1]
                new_edge = (body ^ station).bounding_box()[1]
                if math.isfinite(old_edge) and math.isfinite(new_edge):
                    profile.append(dict(z_mm=z, old_lowest_y_mm=round(old_edge,2),
                                        new_lowest_y_mm=round(new_edge,2), inset_mm=round(new_edge-old_edge,2)))
            margins,legacy,projections = [], [], []
            for z in np.arange(old.DECK+.002,9.32,.12):
                for xx in np.arange(sign*x-1.35,sign*x+1.36,.12):
                    edge = front_y(unguarded_deck(),xx,z)
                    rail = front_y(guards,xx,z)
                    actual = front_y(body,xx,z)
                    prior_edge = front_y(original,xx,z)
                    if None not in (edge,actual,prior_edge):
                        legacy.append(max(0.,edge-prior_edge))
                        projections.append(max(0.,edge-actual))
                    if edge is not None and rail is not None:
                        margins.append(rail-edge)
            roots[names] = dict(actual_bottom_outline=profile,minimum_across_core_mm2=round(min(areas),2),
                                near_deck_probe_z_mm=[7.272,9.312], root_setback_min_mm=round(min(margins),3),
                                original_front_projection_max_mm=round(max(legacy),3),
                                remaining_front_projection_max_mm=round(max(projections),3),
                                connected_root_overlap_mm3=mm3(probe,core ^ guards))
    return dict(old_root_y_mm=old.r62.BOTTOM_ROOT,new_root_y_mm=GUARD_ROOT_Y,
                old_root_tangent_angle_deg=round(math.degrees(math.atan2(2.2,5.7)),1),
                new_root_tangent_angle_deg=round(math.degrees(math.atan2(.08,3.2)),1),
                new_bottom_run_mm=round(old.r62.BOTTOM_CROWN-GUARD_ROOT_Y,2),top_run_mm=old.r62.TOP_ROOT-old.r62.TOP_CROWN,
                root_details=roots,
                left_outer_arm='Continuous curved return to the second left rail; old free prong removed.')


def seating_measurements(body, original):
    board = hardware()['board']
    captured = {}
    for axis,offset in [('left',(-1,0)),('right',(1,0)),('front',(0,-1)),('back',(0,1))]:
        delta = np.asarray(b.board_point(*offset))-b.STATION
        captured[axis]=mm3(body,board.translate((*delta,.2)))
    lid = b.load(old.OUT/GUIDE['actors']['lid']['file'])
    fit = next(s for s in GUIDE['steps'] if s['title']=='Fit the OP1 retainer')
    poses = [lid.transform(np.asarray(s['lid']).reshape(3,4)) for s in fit['samples']]
    lid_to_carrier = max(mm3(body,p) for p in poses)
    added_to_lid_path = max(max(0, mm3(body,p)-mm3(original,p)) for p in poses)
    # The tiny contact at the original left-hand spring catch provides the
    # detent. Compare each position against the R63 slide, including its latch.
    baseline = max(mm3(original,p) for p in poses)
    return dict(board_shift_1mm_into_stops_at_0_2mm_lift_mm3=captured,
                board_lifted_0_35mm_into_lid_mm3=mm3(lid,board.translate((0,0,.35))),
                lid_guide_complete_insertion_overlap_mm3=lid_to_carrier,
                inherited_lid_guide_complete_insertion_overlap_mm3=baseline,
                additional_lid_interference_per_pose_mm3=round(added_to_lid_path,5))


def main():
    OUT.mkdir(exist_ok=True)
    original = b.load(old.OUT / HOLDER)
    core, guards = revised_guards(original)
    made = hinge64.carrier(printable_entry_edges(bearing_and_entry(core + guards)))
    pieces = sorted(made.decompose(), key=lambda p:-p.volume())
    print('entry carrier pieces:', [(round(p.volume(), 3), p.bounding_box()) for p in pieces[:12]], flush=True)
    body = pieces[0]
    b.save_closed(OUT / HOLDER, body)
    b.save_closed(OUT / COLLET_FILE, collet())
    body = b.load(OUT / HOLDER)
    rod = old.lay(mf.Manifold.cylinder(500,4,4,144), -250)
    gauges = {name:sweep(name) for name in ACTORS}
    board = hardware()['board']
    floor = board.translate((0,0,-.10)) ^ body
    projection = floor.project()
    support = round(projection.area(), 2)
    bought = fitted_key_hardware()
    entry = b.union(gauges.values())
    seated = seating_measurements(body, original)
    guard = guard_measurements(body, original, core, guards)
    o, grip = b.load(old.OUT / old.COLLET_FILE), b.load(OUT / COLLET_FILE)
    outer = old.lay(mf.Manifold.cylinder(100,4.15,4.15,144),old.BED - 20)
    report = dict(seating=seated, entry_to_key_hardware_mm3={n:mm3(entry,solid) for n,solid in bought.items()},
                  bought_rod_bounds_mm=bought['rod'].bounding_box(),
                  swept_entry_min_gap_to_full_rod_mm=round(entry.min_gap(rod,10),3),
                  clearance_cut_to_guard_roots_mm3=mm3(b.union(sweep(n,True) for n in ACTORS),guards),
                  taper_outside_8_30_diameter_volume_change_mm3=round((grip-outer).volume()-(o-outer).volume(),6),
                  carrier_sha256=sha256((OUT/HOLDER).read_bytes()).hexdigest(),
                  revision='R64', physical_fit_verified=False, entry_offsets_mm=ENTRY_OFFSETS,
                  hardware_sweep_vs_carrier_mm3={n:mm3(g, body) for n,g in gauges.items()},
                  hardware_sweep_vs_installed_rod_mm3={n:mm3(g, rod) for n,g in gauges.items()},
                  hardware_sweep_vs_original_carrier_mm3={n:mm3(g, original) for n,g in gauges.items()},
                  straight_up_sweep_vs_rod_mm3={n:mm3(sweep(n,offsets=[(0,0,-30),(0,0,0)]),rod) for n in ACTORS},
                  floor_contact_area_within_0_10_mm2=support,
                  floor_contact_bounds_mm=projection.bounds(),
                  collet_free_id_mm=dict(r63=2*old.COLLET_BORE_R,r64=COLLET_ID),
                  entry_side_gap_mm=ENTRY_SIDE_GAP, entry_vertical_gap_mm=ENTRY_VERTICAL_GAP,
                  fixed_and_mated_connector_side_gap_mm=CONNECTOR_SIDE_GAP,
                  guard_return=guard,
                  discarded_volumes_mm3=[p.volume() for p in pieces[1:] if p.volume()>.001])
    report['passes'] = all([
        max(report['hardware_sweep_vs_carrier_mm3'].values()) < .002,
        max(report['hardware_sweep_vs_installed_rod_mm3'].values()) < .002,
        max(report['entry_to_key_hardware_mm3'].values()) < .002,
        max(report['discarded_volumes_mm3'],default=0) < .05,
        min(seated['board_shift_1mm_into_stops_at_0_2mm_lift_mm3'].values()) > .05,
        seated['board_lifted_0_35mm_into_lid_mm3'] > .2,
        seated['additional_lid_interference_per_pose_mm3'] < .001, support > 30,
        report['clearance_cut_to_guard_roots_mm3'] < .002,
        min(item['root_setback_min_mm'] for item in guard['root_details'].values()) > .20,
        max(item['remaining_front_projection_max_mm'] for item in guard['root_details'].values()) < .03,
        min(item['minimum_across_core_mm2'] for item in guard['root_details'].values()) > 2.0,
    ])
    (OUT/'under-entry.json').write_text(json.dumps(report,indent=2)+'\n')
    working = old.k.h.d.geometry()[1]
    checked, obstructions = 0, []
    for name, space in working.items():
        if not name.startswith('key_'):
            continue
        for idx, pose in enumerate(old.c.poses(old.placed(space,name))):
            checked += 1
            overlap = mm3(body,pose)
            if overlap > .01:
                obstructions.append(dict(route=name, pose_index=idx, overlap_mm3=overlap))
    strips = [b.load(old.OUT/old.BACKER), b.load(old.prior.old.R58/'exports/Socket_Backer_Right-assembly.stl')]
    strip_check = {side:mm3(body,mf.Manifold.batch_hull([s,s.translate((26*sign,0,0))]))
                   for s,side,sign in zip(strips,['left','right'],[-1,1])}
    # The floor and lid deliberately support the board. Distinguish these
    # interfaces from the four independent Choc socket loading paths.
    summary = dict(revision='R64',physical_fit_verified=False,source_sha256=report['carrier_sha256'],
                   carrier_sha256=report['carrier_sha256'], generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                   key_poses_checked=checked,key_obstructions=obstructions,socket_backer_sweeps_mm3=strip_check,
                   passes=bool(report['passes'] and not obstructions and max(strip_check.values())<.01))
    (OUT/'carrier.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(summary,flush=True)
    assert summary['passes'], summary
    print(json.dumps(report,indent=1),flush=True)
    assert report['passes'],report

if __name__=='__main__':
    main()
