"""R51 rigid paddle hinge and fitted OP1 seat. Millimetres, +Y toward the two-key row.

The carrier export uses assembly/world coordinates. The paddle and its existing
board/clip actors use the R48 bracket frame. Purchased axle pieces use world
coordinates at the pivot. Physical switch feel and fatigue need a prototype.
"""
from functools import lru_cache
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

import trimesh

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'carbon-rod-holders-r48-edge-click'
sys.path.insert(0, str(BASE))
import build48 as baseline

h, q, r = baseline.h, baseline.q, baseline.r
box = h.box
union = h.union
EXPORT = HERE / 'exports'
OP1_SHIFT = (0., 3.30, .20)
AXIS_Y = 26.55
AXIS_Z = 18.5
AXIS_WORLD_Y = AXIS_Y + r.CLICK_SHIFT
SLEEVE_LENGTH = 12.00
SLEEVE_RADIUS = 1.50
BEARING_RADIUS = 1.60
BEARING_HALF = 5.80
FORK_INNER = 6.10
FORK_OUTER = 8.35
FORK_BORE = 1.14
PIVOT_YZ = (AXIS_WORLD_Y, AXIS_Z)
INPUT = BASE / 'exports'
EMPTY = mf.Manifold


def cylinder_x(x0, x1, y, z, radius, facets=80):
    return mf.Manifold.cylinder(x1-x0, radius, radius, facets).rotate((0., 90., 0.)).translate((x0,y,z))


def xyz_bounds(s):
    return [round(float(v), 5) for v in s.bounding_box()]


def placement(angle):
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    basis = np.array([[1.,0.,0.], [0.,c,-s], [0.,s,c]])
    pivot = np.array((0., AXIS_Y, AXIS_Z))
    return np.column_stack((basis, pivot - basis @ pivot + (0.,r.CLICK_SHIFT,0.)))


def world(paddle, angle):
    return paddle.transform(placement(angle).tolist())


@lru_cache(maxsize=1)
def pivot_hardware():
    """Plain bearing sleeve takes the clamp load; threads do not run in the paddle."""
    y,z = PIVOT_YZ
    half = SLEEVE_LENGTH / 2
    sleeve = cylinder_x(-half,half,y,z,SLEEVE_RADIUS) - cylinder_x(-half-.1,half+.1,y,z,1.05)
    screw = cylinder_x(-FORK_OUTER,-FORK_OUTER+20.,y,z,1.) + cylinder_x(-FORK_OUTER-2.,-FORK_OUTER,y,z,1.90)
    nut = cylinder_x(FORK_OUTER,FORK_OUTER+2.50,y,z,2./math.cos(math.pi/6),6)
    nut -= cylinder_x(FORK_OUTER-.01,FORK_OUTER+2.51,y,z,1.)
    return {'pivot-screw':screw, 'pivot-sleeve':sleeve, 'pivot-locknut':nut}


@lru_cache(maxsize=1)
def fixed_cheeks():
    y, z = PIVOT_YZ
    cap = cylinder_x(FORK_INNER,FORK_OUTER,y,z,2.55)
    foot = box(FORK_INNER, FORK_OUTER, y-4.10,y+2.54, 10.85,11.65)
    cheek = mf.Manifold.batch_hull([foot,cap])
    # The right-hand groove carries the horizontal OP1 harness below this root.
    cheek -= cylinder_x(FORK_INNER-.02,FORK_OUTER+.02,y,z,FORK_BORE)
    return r.mirrored(cheek)


def root_gusset(sign):
    # Broad solid fans from the long rail into the centre journal; the sides
    # are wide where the old thin corner split during hand cleanup.
    rows = [(9.60,5.25,9.95,17.50,19.20),
            (13.9,4.10,10.0,16.78,19.20),
            (16.5,2.65,8.75,16.40,19.18),
            (21.1,.02,4.85,16.25,19.19),
            (23.9,.02,BEARING_HALF,16.1,19.7)]
    hulls = []
    for y,inner,outer,lo,hi in rows:
        x0,x1=sorted([sign*inner,sign*outer])
        hulls.append(box(x0,x1,y-.10,y+.10,lo,hi))
    return union(mf.Manifold.batch_hull([a,b]) for a,b in zip(hulls,hulls[1:]))


def configure_new_op1():
    """Must run once in a fresh process, before building OP1 or touch hardware."""
    if any(fn.cache_info().currsize for fn in (q.hardware, q.pusher, q.op1_reliefs, baseline.p.bracket)):
        raise RuntimeError('Start a fresh process before configuring the R51 hardware.')
    q.OP1_DZ += OP1_SHIFT[2]
    q.PCB_Z += OP1_SHIFT[2]
    q.PCB_TOP += OP1_SHIFT[2]
    q.FREE_TOP += OP1_SHIFT[2]
    q.PUSH_Z += OP1_SHIFT[2]
    q.LEAD_Z += OP1_SHIFT[2]
    q.PLUNGER_XY = (q.PLUNGER_XY[0], q.PLUNGER_XY[1]+OP1_SHIFT[1])
    q.PUSH_Y += OP1_SHIFT[1]
    q.LEVER = AXIS_Y - q.PUSH_Y
    q.REST = math.degrees(math.asin(q.DEPRESSION/q.LEVER))


@lru_cache(maxsize=1)
def paddle():
    # Regenerate the proved board nest and front pads without the adjustable
    # stop hardware. Its two old integral travel-limit heels remain.
    with patch.object(h.base, 'stop_stock', EMPTY), patch.object(h.base, 'stop_pilot', lambda *args: EMPTY()):
        previous = h.p.bracket()
    # Remove ALL thin guides, crush-stop and flex blades. The previous guide
    # starts as far forward as Y=16; load now goes directly through the fans.
    previous -= box(-11.,11.,14.95,35.,12.,25.)
    fans = root_gusset(-1) + root_gusset(1)
    knuckle = cylinder_x(-BEARING_HALF,BEARING_HALF,AXIS_Y,AXIS_Z,2.78)
    land = box(-BEARING_HALF,BEARING_HALF,23.4,23.8,16.1,19.5)
    body = previous + fans + mf.Manifold.batch_hull([land, knuckle])
    bore = cylinder_x(-BEARING_HALF-.1,BEARING_HALF+.1,AXIS_Y,AXIS_Z,BEARING_RADIUS)
    # The top surface of the rail is the board seat. Relieve the three
    # Gravity pin fillets through the two enlarged root fans.
    return body - bore - h.p.pin_relief() - h.p.board_space() + h.p.posts()


@lru_cache(maxsize=1)
def projecting_chin_stock():
    # The R48 chin got two oblong reinforcing ribs on its finger-facing side.
    # Their carved-away holes are already empty in the inherited mesh. Take
    # the original stock below the new flat-backed seat; keep the guard ribs.
    with patch.object(q, 'op1_reliefs', return_value=[EMPTY()]):
        runners = baseline.chin_runners.__wrapped__(h).translate((0.,-OP1_SHIFT[1],0.))
    original_seats = q.op1_seats().translate(tuple(-v for v in OP1_SHIFT))
    return (original_seats + runners) ^ box(-16.,16.,-22.,24.,4.,7.30)


@lru_cache(maxsize=1)
def carrier():
    old = baseline.b.load(INPUT/'Key_Carrier-assembly.stl')
    old = max(old.decompose(), key=lambda s:s.volume())
    # Keep all four fitted Choc seats, rod clips and finger-rest ribs. This
    # local replacement cuts the old latch ears flush at the deck surface.
    old -= box(-7.15,7.15,28.55,33.,11.35,23.)
    # Remove the raised screw landing; preserve the permanent rim below.
    old -= box(-10.36,-6.24,-5.71,-1.49,11.35,13.)
    # The original two mounting holes and their lower protrusions belong to
    # the old switch position. Trim those seats up to the chin's flat underside
    # and fill the obsolete pilot sections only inside the previous pillars.
    original_seats = q.op1_seats().translate(tuple(-v for v in OP1_SHIFT))
    old -= projecting_chin_stock()
    old += original_seats ^ box(-15.,15.,-22.,20.,7.30,9.21)
    slot,barrels,connector,pilots = q.op1_reliefs()
    # Preserve the fitted eyelet profiles and their 17.9 mm pitch. A 2.1 mm
    # floor joins each hole to the side walls without a hanging chin runner.
    seat_floor = q.board_frame(box(-6.8,6.8,h.h32.PCB_Y[0],h.h32.PCB_Y[1],7.12,9.2))
    stock = (old+seat_floor+fixed_cheeks()) - slot - barrels - connector
    saddles = q.op1_seats() ^ box(-16.,16.,-24.,30.,7.30,10.2)
    stock = (stock+saddles) - pilots - barrels - connector
    # The actual lead and fitted plug must have a through exit while the rod
    # and existing key-socket paths remain clear beneath the new local floor.
    stock -= h.base.rod() - h.base.clip_bands()
    # The trimmed STL and analytic runner occasionally share zero-thickness
    # skins. Reject any real island and drop only sub-micron-volume remnants.
    pieces = sorted(stock.decompose(),key=lambda piece:-piece.volume())
    if any(abs(piece.volume())>.0001 for piece in pieces[1:]):
        raise RuntimeError('The trimmed OP1 floor contains disconnected material')
    return pieces[0]


def shifts():
    return {'op1_world_translation_from_r48_mm':list(OP1_SHIFT),
            'axis_paddle_xyz_mm':[0.,AXIS_Y,AXIS_Z],
            'axis_world_xyz_mm':[0.,AXIS_WORLD_Y,AXIS_Z],
            'paddle_local_to_world_at_zero':placement(0.).tolist(),
            'axle_insertion_unit_vector':[1.,0.,0.],
            'plunger_inset_from_board_free_edge_mm':baseline.EDGE_INSET + OP1_SHIFT[1],
            'plunger_inset_from_copper_free_edge_mm':baseline.EDGE_INSET + OP1_SHIFT[1] - .58,
            'copper_length_mm':13.12, 'op1_pcb_hole_spacing_mm':17.9}


def main(out):
    out.mkdir(parents=True,exist_ok=True)
    configure_new_op1()
    parts = {'Key_Carrier-assembly':carrier(),'DFRobot_Hole_Bracket-assembly':paddle(),**pivot_hardware()}
    result={}
    for name,s in parts.items():
        pieces = sorted(s.decompose(),key=lambda b:-b.volume())
        print(name,xyz_bounds(s),[(round(p.volume(),5),xyz_bounds(p)) for p in pieces[:4]],flush=True)
        if s.status()!=mf.Error.NoError or len(pieces)!=1:
            raise RuntimeError(f'{name} is not one closed solid')
        baseline.b.save(out/(name+'.stl'),s)
        result[name]={'sha256':sha256((out/(name+'.stl')).read_bytes()).hexdigest(),
                      'volume_mm3':round(s.volume(),3),'bounds_mm':xyz_bounds(s)}
    # The OP1 cable exit bends toward the back of the Wand; unlike the rigid
    # connector its far end stays at the original strain-relief station.
    baseline.b.save(out/'op1_wire.stl',q.hardware()['op1_wire'])
    import harness_guide48
    wire = trimesh.load_mesh(out/'op1_wire.stl',process=False)
    hanging = harness_guide48.wire_vertices(baseline, wire.vertices)
    trimesh.Trimesh(hanging,wire.faces,process=False).export(out/'op1-wire-hanging.stl')
    summary = shifts() | {'meshes':result,'rest_angle_deg':-q.REST}
    (out/'dimensions.json').write_text(json.dumps(summary,indent=2)+'\n')

if __name__=='__main__':
    main(Path(sys.argv[1]) if len(sys.argv)>1 else EXPORT)
