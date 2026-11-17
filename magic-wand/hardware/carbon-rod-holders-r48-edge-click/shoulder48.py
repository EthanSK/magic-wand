"""Back the fixed shoulder of the forward rod clip beside the OP1 plug."""
from functools import lru_cache


@lru_cache(maxsize=1)
def shoulder(h):
    # The plug needs clearance over the upper-right side of the original
    # 3.6 mm band. Extend its fixed shoulder forward, blending back into the
    # band. The new stock clears the 8 mm rod; the snap jaws keep their bore.
    front, rear = 6.1, 12.6
    def along_rod(radius):
        return h.mf.Manifold.cylinder(rear - front, radius, radius, 128).rotate(
            (-90., 0., 0.)).translate((0., front, 0.))

    band = along_rod(6.55) - along_rod(4.16)
    plan = h.mf.CrossSection([[(.7, 9.4), (2.8, front), (5.45, front),
                              (6.6, 9.2), (6.6, rear), (.7, rear)]]).extrude(8.)
    above_jaw = h.r.d.wedge(0., 6.7, [(front, 3.2), (9.1, 1.65), (rear, 1.65),
                                        (rear, 7.), (front, 7.)])
    return (band ^ plan ^ above_jaw) - h.union(h.q.op1_reliefs())


@lru_cache(maxsize=1)
def connector_buttress(h):
    # The standing print builds towards decreasing assembly Y. By itself the
    # connector relief exposes a tiny isolated strand two layers before it
    # joins the carrier. Round a path back to the stock already printed.
    points = [(3.95, 10.15, 4.9), (4.75, 8.9, 4.75), (5.7, 8.5, 4.7),
              (6.7, 7.85, 4.7), (7.25, 7.25, 4.4)]
    return h.h46.run(points, [.93, .93, 1.02, 1.02, .93]) - h.union(h.q.op1_reliefs())
