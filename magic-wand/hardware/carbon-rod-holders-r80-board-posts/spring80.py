"""Measure the printable spring gaps and contact width directly on the two-post bar."""
import numpy as np
from shapely.geometry import Point
from shapely.ops import unary_union

from audit80 import b, retention71


def sections(points, machine):
    import design80 as design
    result = {}
    for sign, side in [(-1,'left'),(1,'right')]:
        x, y = sign*b.HOLE_X, b.HOLE_Y
        beads = retention71.local_beads(points, machine, x, y)
        beads = beads[np.linalg.norm(beads[:,:2] - [x,y],axis=1)<2.0]
        layers = []
        # Restrict to layers with a parallel locating land and full spring face.
        for z in np.arange(b.PLATE_Z+.1, design.FINGER_TOP-design.FINGER_LEAD-.001,.2):
            row = beads[(beads[:,2]<z) & (beads[:,3]>=z)]
            cloud = [Point(px-x,py-y).buffer(r,resolution=16) for px,py,_,_,r in row]
            section = unary_union(cloud)
            members = sorted([g for g in getattr(section,'geoms',[section]) if g.area>.04],key=lambda g:g.centroid.y)
            assert len(members)==2,(side,z,[g.area for g in members])
            finger, core = members
            assert finger.centroid.y < -.4 and core.centroid.y > -.35
            gap = finger.distance(core)
            finger_xy = finger.bounds
            assert gap>.15 and finger_xy[2]-finger_xy[0]>1.4 and finger_xy[3]-finger_xy[1]>.40,(side,z,gap,finger_xy)
            layers.append(dict(above_paddle_bottom_mm=round(z-b.PLATE_Z,3),spring_gap_mm=round(gap,4),
                               finger_area_mm2=round(finger.area,4),core_area_mm2=round(core.area,4)))
        assert len(layers) >= 12
        result[side] = layers
    return result
