"""A rounded harness mouth starts on the mating plug axis, with no reverse jog."""
from functools import lru_cache
import math


def centres(h):
    tip = h.h32.MATE_Y[1]
    return tuple(h.q.board_point(0., tip + run) for run in (.40, 2.45))


@lru_cache(maxsize=1)
def outlet(h):
    # A true through-slot allows a prewired board to drop from above. The existing
    # open-bottom guide takes the lead from the end of this mouth towards the bus.
    ends = [h.mf.Manifold.cylinder(28., 2.08, 2.08, 96).translate((*xy, -6.))
            for xy in centres(h)]
    return h.mf.Manifold.batch_hull(ends)


def check(h, carrier):
    q = h.q
    a, b = centres(h)
    # Circumscribing circle for 3 equal round wires in a triangular bundle.
    bundle_r = .75 * (1. + 2. / math.sqrt(3.))
    path = []
    for i in range(18):
        t = max(0, i-1) / 16.
        xy = q.board_point(0., h.h32.MATE_Y[1]) if i == 0 else tuple(x + t * (y-x) for x, y in zip(a,b))
        probe = h.mf.Manifold.cylinder(28., bundle_r, bundle_r, 96).translate((*xy, -6.))
        path.append(float((probe ^ carrier).volume()))
    pts = q.lead_points()
    alignment = abs((b[0]-a[0])*(pts[1][1]-pts[0][1])-(b[1]-a[1])*(pts[1][0]-pts[0][0]))
    return {'centreline_mm': [list(a), list(b)], 'width_mm': 4.16,
            'usable_straight_travel_mm': math.dist(a,b), 'wire_bundle_mm': 2*bundle_r,
            'max_bundle_intersection_mm3': max(path),
            'passes': max(path) < .0001 and alignment < .0001 and math.dist(q.board_point(0., h.h32.MATE_Y[1]), a) < .401}
