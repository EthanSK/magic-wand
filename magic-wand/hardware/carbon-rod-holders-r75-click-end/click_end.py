"""Rounded beams on the click end. Coordinates and local section radii are in mm."""
import numpy as np
import manifold3d as mf
import design74 as prior


def rounded_beam(stations):
    # Follow the reference flare without a kink. The narrowed section beside
    # the pouch joins the finger surface tangentially instead of ending in a post.
    stations = np.asarray(stations, float)
    lengths = np.linalg.norm(np.diff(stations[:, :3], axis=0), axis=1)
    tangents = np.gradient(stations, np.r_[0., np.cumsum(lengths)], axis=0)
    rings = []
    sphere = mf.Manifold.sphere(1., 32)

    def ring(station):
        return sphere.scale(tuple(station[3:])).translate(tuple(station[:3]))

    for i, length in enumerate(lengths):
        for t in np.linspace(0., 1., max(3, int(length / .23)), endpoint=False):
            t2, t3 = t*t, t*t*t
            point = ((2*t3 - 3*t2 + 1)*stations[i] + (t3 - 2*t2 + t)*length*tangents[i]
                     + (-2*t3 + 3*t2)*stations[i+1] + (t3 - t2)*length*tangents[i+1])
            rings.append(ring(point))
    rings.append(ring(stations[-1]))
    beam = prior.b.union([mf.Manifold.batch_hull([a,b]) for a,b in zip(rings, rings[1:])])
    # Leave a bonded root inside the deck, below the switch-clip recess.
    return beam ^ prior.b.box(-32., -9., -9.5, 15., -4., prior.DECK + .44)


def inner():
    """The branch toward the rod starts at the rim, arcs above the battery exit,
    and blends back down beside the socket. Its projected tips match the good fork."""
    return rounded_beam([
        # x, y, z, and the section radii along those axes
        (-14.2, -6.6, 8.12, 1.35, 1.35, 1.35),
        (-14.22, -5.7, 7.9, 1.35, 1.35, 1.35),
        (-14.36, -4.1, 7.28, 1.35, 1.35, 1.35),
        (-14.65, -2.7, 6.61, 1.35, 1.35, 1.3),
        (-15.27, -1.42, 6.1, 1.35, 1.35, 1.26),
        (-16.0, -0.55, 5.9, 1.35, 1.35, 1.24),
        (-17.25, 0.8, 5.83, 1.35, 1.35, 1.24),
        (-18.7, 2.2, 5.82, 1.32, 1.3, 1.21),
        (-19.9, 3.15, 5.72, 1.12, 1.18, 1.13),
        (-20.78, 3.68, 5.05, 0.92, 1.08, 1.04),
        (-21.03, 3.96, 3.68, 0.9, 1.08, 1.05),
        (-21.07, 4.25, 2.55, 0.92, 1.1, 1.06),
        (-21.44, 4.72, 1.49, 1.1, 1.18, 1.17),
        (-22.1, 5.2, 0.88, 1.35, 1.35, 1.35),
    ])


def outer():
    """Use the previously supported rim turn below the sideways socket opening.
    Continue along the reference arm to its real fork junction at the click end."""
    old_turn = prior.outer_leg() ^ prior.b.box(-31.,-9.,-10.,0.,-4.,prior.DECK+.44)
    t = np.linspace(0., 1., 201)
    path = prior.mirrored_leg(t)
    path = path[path[:, 1] >= -1.6]
    path[:, 2] = prior.CROWN_Z
    return old_turn + prior.rod(path, prior.RADIUS)


def rear():
    """Join the fork from the rear, so the layers at the fork grow from solid
    material. Stay slim where the soldered socket passes beside the battery."""
    return rounded_beam([
        (-20.80, 9.95, 7.82, .88, 1.32, 1.28),
        (-20.80, 9.15, 6.62, .88, 1.30, 1.26),
        (-20.80, 8.44, 5.32, .88, 1.28, 1.25),
        (-20.82, 7.92, 4.20, .88, 1.25, 1.22),
        (-20.90, 7.45, 3.15, .88, 1.23, 1.18),
        (-21.19, 7.04, 2.20, .95, 1.25, 1.20),
        (-21.72, 6.42, 1.44, 1.18, 1.30, 1.28),
        (-22.08, 5.49, .93, 1.35, 1.35, 1.35),
        (-22.10, 5.20, .88, 1.35, 1.35, 1.35),
    ])
