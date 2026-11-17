"""Measure the last sub-bead corner between the OP1 plug pocket and wire slot."""
import numpy as np


def inspect(missing, frame, solid, checker, fields):
    from build48 import q
    from manifold3d import CrossSection

    xyz, widths, _, tops = fields
    result = {'qualified': [], 'unqualified': []}
    for row in missing:
        top = row['layer_top_mm']
        bounds = np.asarray(row['print_xy_bounds_mm'])
        mid = top - .1
        # Locate in the board's own frame. One face is across the plug and
        # the other is the side of the harness mouth; neither locates the PCB.
        probes = np.array([[x, bounds[1], mid, 1.] for x in bounds[[0, 2]]]) @ frame.T
        origin = np.asarray(q.board_point(0., 0.))
        axes = np.array([q.board_point(1., 0.), q.board_point(0., 1.)]) - origin
        board_xy = (probes[:, :2] - origin) @ axes.T
        width = bounds[2] - bounds[0]
        if not (abs(board_xy[0, 1] - 21.70) < .005 and abs(board_xy[1, 0] + 2.08) < .005
                and .0 < width < .06 and 0 < row['area_mm2'] < .24):
            result['unqualified'].append(row)
            continue
        patch = CrossSection.square(tuple(bounds[2:] - bounds[:2])).translate(tuple(bounds[:2]))
        window = patch.offset(.60)
        preceding = solid.slice(mid - .2) ^ window
        lower = (np.abs(tops - (top - .2)) < .001) & np.all(
            (xyz[:, :2] >= bounds[:2] - 1.5) & (xyz[:, :2] <= bounds[2:] + 1.5), axis=1)
        film = checker.start_audit.bead_footprints(checker.q, xyz[lower, :2], widths[lower])
        bond = (film ^ preceding).area()
        # Inspect the WHOLE next slab in the vicinity, not just its midpoint.
        part_over = solid ^ window.extrude(.20).translate((0., 0., top))
        cap = solid ^ window.extrude(.20).translate((0., 0., top - .20))
        upper = abs(tops - (top + .2)) < .001
        nearby = upper & np.all((xyz[:,:2] >= bounds[:2] - 1.5) & (xyz[:,:2] <= bounds[2:] + 1.5), axis=1)
        layers_above = checker.start_audit.bead_footprints(checker.q, xyz[nearby,:2], widths[nearby]) if nearby.any() else CrossSection()
        overprinted_area = (layers_above ^ patch.offset(.2)).area()
        record = {'raw': row, 'corner_in_op1_xy_mm': board_xy.round(4).tolist(), 'width_mm': width,
                  'preceding_section_mm2': preceding.area(), 'preceding_actual_plastic_mm2': bond,
                  'upper_bound_omitted_tip_volume_mm3': cap.volume(), 'cad_in_next_slab_mm3': part_over.volume(),
                  'next_layer_plastic_above_tip_mm2': overprinted_area,
                  'basis': 'Terminal corner of two intersecting clearance cuts. The wider section below prints and no plate feature rests on the omitted tip.'}
        ok = (bond > .9 and cap.volume() < .14 and part_over.volume() < .00001 and overprinted_area < .00001)
        result['qualified' if ok else 'unqualified'].append(record)
    return result
