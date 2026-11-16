"""Whole horizontal withdrawal of the actual deposited shelf, before assembly.

Native Z intervals stay unchanged during this movement. Each footprint is
expanded to contain the complete bead and every inter-sample path segment.
The obstacle shadow extends to infinity, so this is not a sampled motion.
"""
import numpy as np
import manifold3d as mf


def inspect(checker, data, xyz, obstacle, shelf, axis='-y'):
    q = checker.q
    assert axis in ('-x', '+x', '-y', '+y') and shelf.any()
    # Represent the selected direction as -U; V is the other horizontal axis.
    u, v = (0, 1) if axis.endswith('x') else (1, 0)
    xy = xyz[:, [u, v]].copy()
    if axis.startswith('+'):
        xy[:, 0] *= -1
    radii = (data[:, 3] + checker.STEP) / (2 * np.cos(np.pi/12))
    top = xyz[:, 2]
    bottom = top - data[:, 4]
    relevant = obstacle | shelf
    step = .05
    origin = np.floor((xy[relevant].min(0)-radii[relevant].max()-2)/step)*step
    extent = np.ceil((xy[relevant].max(0)+radii[relevant].max()+2-origin)/step).astype(int)+2
    nx, ny = map(int, extent)
    lo = np.floor((xy-radii[:, None]-origin)/step).astype(int)
    hi = np.floor((xy+radii[:, None]-origin)/step).astype(int)+1

    def cover(mask, shadow=False):
        grid = np.zeros((ny+1, nx+1), dtype=np.int32)
        a, b = lo[mask].T
        c, d = hi[mask].T
        if shadow:
            c = np.full_like(c, nx)
        for ys, xs, value in ((b, a, 1), (d, c, 1), (d, a, -1), (b, c, -1)):
            np.add.at(grid, (ys, xs), value)
        return grid.cumsum(0, dtype=np.int32).cumsum(1, dtype=np.int32)[:-1, :-1] > 0

    angle = np.arange(12)*np.pi/6
    circle = np.c_[np.cos(angle), np.sin(angle)]
    far = float((xy[relevant, 0].max()-xy[relevant, 0].min())+2*radii[relevant].max()+4)
    collisions = []
    checked = 0
    for z in np.unique(top[shelf]):
        current = shelf & (np.abs(top-z) < .001)
        # Include every bead whose height overlaps any shelf bead on this layer.
        low = bottom[current].min()
        high = top[current].max()
        # Include touching height faces too: a zero-gap PETG interface is
        # not a demonstrated release seam, even without volume overlap.
        model = obstacle & (bottom <= high+q.Z_GUARD) & (top >= low-q.Z_GUARD)
        checked += 1
        if not model.any():
            continue
        yy, xx = np.nonzero(cover(model, True) & cover(current))
        if not len(xx):
            continue
        tiles = np.unique(np.c_[xx//20, yy//20], axis=0)
        hits = []
        for tx, ty in tiles:
            x0, y0 = origin+np.array([tx, ty])
            x1, y1 = x0+1, y0+1
            near_y = (xy[:, 1] >= y0-radii) & (xy[:, 1] <= y1+radii)
            m = model & near_y & (xy[:, 0]-radii <= x1)
            h = current & near_y & (xy[:, 0] >= x0-radii) & (xy[:, 0] <= x1+radii)
            if not (m.any() and h.any()):
                continue
            swept = []
            for index in np.flatnonzero(m):
                polygon = xy[index]+radii[index]*circle
                swept.append(q.CrossSection.hull_points(np.r_[polygon, polygon+[far, 0.]]))
            shadow = q.CrossSection.batch_boolean(swept, mf.OpType.Add)
            envelope = checker.start_audit.bead_footprints(q, xy[h], 2*radii[h])
            tile = q.CrossSection.square((1., 1.)).translate((x0, y0))
            overlap = (shadow ^ envelope) ^ tile
            if overlap.area() > .0001:
                hits.append({'tile_uv_mm': [x0, y0], 'conservative_overlap_mm2': overlap.area()})
        if hits:
            collisions.append({'layer_top_mm': round(float(z), 3), 'tiles': hits})
    return {'clear': not collisions, 'axis_in_print_frame': axis, 'checked_shelf_layers': checked,
            'collisions': collisions,
            'method': 'Every shelf bead against complete infinite horizontal obstacle shadows on all overlapping native height intervals. Circumscribed footprints include the 0.15-mm sample-step guard; outward-rounded AABBs reject only impossible conflicts, exact clipped convex sweeps confirm all candidate tiles.',
            'physical_release_force_verified': False}
