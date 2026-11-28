"""Measure the printed spring travel needed to pass through the existing paddle."""
from pathlib import Path
import sys
import numpy as np
from shapely.affinity import translate
from shapely.geometry import Point
from shapely.ops import unary_union

from plate80 import previous
from audit80 import v, b, retention71


def nearby(points, matrix, x, radius):
    beads = retention71.local_beads(points, matrix, x, b.HOLE_Y)
    beads[:,:2] -= [x,b.HOLE_Y]
    return beads[(abs(beads[:,0]) < radius) & (abs(beads[:,1]) < radius)]


def outline(beads):
    circles = np.unique(beads[:,[0,1,4]].round(5), axis=0)
    assert len(circles) > 20
    return unary_union([Point(px,py).buffer(r,resolution=16) for px,py,r in circles])


def post_layers(beads):
    import design80
    rigid, flexible, board_cores = [], [], []
    for z in np.arange(b.PLATE_Z+.1, b.BOARD_TOP+3.01, .2):
        part = outline(beads[(beads[:,3]>z)&(beads[:,2]<z)])
        pieces = [g for g in getattr(part,'geoms',[part]) if g.area > .03]
        assert 1 <= len(pieces) <= 2
        if len(pieces)==2 and z < design80.FINGER_TOP:
            finger, core = sorted(pieces,key=lambda g:g.centroid.y)
            assert finger.centroid.y < -.4
            flexible.append((z,finger,core))
        else:
            # Above the spring tip, the separate little island is the fixed
            # corbel under the clip neck. It travels with the rigid core.
            core = unary_union(pieces)
        rigid.append(core)
        if b.SEAT_Z < z < b.BOARD_TOP:
            board_cores.append(core)
    return unary_union(rigid), flexible, board_cores


def report(folder):
    original = previous.old.OUT/'print-mechanisms'
    inputs = {}
    for part, root in [('Touch_Paddle',original),('DFR_Post_Bar',folder)]:
        points,_ = v.read_native(root/v.ARCHIVE)
        frame = v.read(root/'layout.frame.json')['parts'][part]
        inputs[part] = points, np.asarray(frame['assembly_to_machine']), frame['source_sha256']
    guide = v.read(previous.OUT/'assembly-guide.json')['modules']['pin_hinge']['actors']
    assert inputs['Touch_Paddle'][2] == v.digest(previous.OUT/guide['cap']['file'])
    sides = {}
    for label, x in [('left',-b.HOLE_X),('right',b.HOLE_X)]:
        p = nearby(*inputs['Touch_Paddle'][:2],x,2.45)
        paddle = outline(p[(p[:,3]>b.PLATE_Z+.002)&(p[:,2]<b.SEAT_Z-.002)])
        rigid, layers, board_cores = post_layers(nearby(*inputs['DFR_Post_Bar'][:2],x,2.1))
        finger = unary_union([g for _,g,_ in layers])
        assert len(layers) >= 12 and rigid.area>3 and paddle.area>2
        # With both upper heads inside the old paddle opening, find the least
        # travel leaving 0.02 mm of nominal bead clearance at the entry walls.
        shift = next((float(d) for d in np.arange(0., .55, .005)
                      if translate(finger,yoff=d).distance(paddle) >= .02), None)
        assert shift is not None and rigid.distance(paddle)>.015,(label,shift,rigid.distance(paddle))
        free_after = min(translate(g,yoff=shift).distance(core) for _,g,core in layers)
        assert free_after > .02,(label,shift,free_after)
        # Full post in the nominal 3 mm PCB: seat the rear lands once across
        # all board layers, then find the inward yield of the same front finger.
        import design80
        board = [(z,g,c) for z,g,c in layers if b.SEAT_Z < z < b.BOARD_TOP]
        core_pts = np.vstack([np.asarray(c.convex_hull.exterior.coords) for c in board_cores])
        spring_pts = np.vstack([np.asarray(g.exterior.coords) for _,g,_ in board])
        centre = design80._seat(core_pts,1.50,0.)
        assert centre is not None, (label,'rigid bearing is oversized for the nominal hole')
        board_shift = design80._push(spring_pts,1.50,(0.,centre))
        assert 0 < board_shift and min(translate(g,yoff=board_shift).distance(c) for _,g,c in layers)>.02
        sides[label] = dict(rigid_post_to_reused_paddle_mm=round(rigid.distance(paddle),4),
                            spring_travel_through_paddle_mm=round(shift,4), remaining_spring_gap_mm=round(free_after,4),
                            spring_travel_in_nominal_3mm_board_hole_mm=round(board_shift,4))
    v.write(folder/'paddle-passage.json',dict(parts_sha256={k:r[2] for k,r in inputs.items()}, sides=sides,
            native_archive_sha256=v.digest(folder/v.ARCHIVE),reference_archive_sha256=v.digest(original/v.ARCHIVE)))


if __name__=='__main__':
    report(Path(sys.argv[1]))
