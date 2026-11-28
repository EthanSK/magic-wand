"""Check the wrist controller repair using the toolpaths that will actually be printed."""
from pathlib import Path
import sys

import numpy as np
from shapely import minimum_bounding_radius
from shapely.geometry import Point
from shapely.ops import unary_union

from plate80 import OUT, parts, previous
import audit61
import retention71

v = audit61.v
b = previous.b


def post_profile(beads, x, y):
    # All XY bead radii count, including the sectors between the old narrow ribs.
    # Measure every 0.2 mm layer within the board, then the neck above the board.
    planes = np.arange(b.SEAT_Z + .1, b.BOARD_TOP, .2).tolist() + [b.BOARD_TOP + .50, b.BOARD_TOP + 1.1]
    directions = np.column_stack((np.cos(np.deg2rad(np.arange(180.))), np.sin(np.deg2rad(np.arange(180.)))))
    local = beads[np.linalg.norm(beads[:, :2] - [x, y], axis=1) < 2.]
    measured = []
    for z in planes:
        section = local[(local[:, 2] < z) & (local[:, 3] >= z)]
        assert len(section) > 20, (z, len(section))
        centres, radii = section[:, :2] - [x,y], section[:, 4]
        projected = centres @ directions.T
        width = (projected + radii[:, None]).max(0) - (projected - radii[:, None]).min(0)
        rim = unary_union([Point(*xy).buffer(radius, resolution=16) for xy, radius in zip(centres, radii)])
        measured.append(dict(above_board_seat_mm=round(float(z-b.SEAT_Z), 4), width_x_mm=round(width[0],4),
                             width_y_mm=round(width[90],4), minimum_width_mm=round(width.min(),4),
                             enclosing_diameter_mm=round(2*minimum_bounding_radius(rim),4), area_mm2=round(rim.area,4)))
    return measured


def profiles(folder, points=None):
    frame = v.read(folder / 'layout.frame.json')['parts']
    if points is None:
        points, _ = v.read_native(folder / v.ARCHIVE)
    post = np.asarray(frame['DFR_Post_Bar']['assembly_to_machine'])
    return {side: post_profile(retention71.local_beads(points, post, x, b.HOLE_Y), x, b.HOLE_Y)
            for side, x in [('left', -b.HOLE_X), ('right', b.HOLE_X)]}


def audit(folder):
    layout, archive = folder / 'layout.3mf', folder / v.ARCHIVE
    frame = v.read(folder / 'layout.frame.json')
    names = {p['name'] for p in parts()}
    native = v.read(folder / 'OP1-hinge.gcode.native.json')
    assert native['return_code'] == 0 and native['archive_sha256'] == v.digest(archive)
    assert frame['layout_sha256'] == v.digest(layout) and set(frame['parts']) == names
    for row in parts():
        assert frame['parts'][row['name']]['source_sha256'] == v.digest(row['source'])
    v.audit(archive, layout, folder / 'separation-and-machine.json', names)
    bases = v.bases(archive)
    v.verify(bases, minimum_base_mm2={k: a for k, a in audit61.MINIMA.items() if k in names})
    layers = v.inspect(archive)
    assert set(layers['parts']) == names and layers['native_support_moves'] == 0
    assert all(not row['completely_unsupported_starts'] for row in layers['parts'].values())
    v.write(folder / 'layers.json', layers)
    v.write(folder / 'bases.json', bases)
    from routes80 import routes
    points, labels = v.read_native(archive)
    v.write(folder / 'post-sections.json', profiles(folder, points))
    import spring80
    import sections80
    v.write(folder/'load-sections.json', sections80.sections(points,frame['parts']))
    v.write(folder / 'spring-gaps.json', spring80.sections(points, np.asarray(frame['parts']['DFR_Post_Bar']['assembly_to_machine'])))
    fits = {}
    raw_bar = {}
    for name, paths in routes().items():
        pose = np.asarray(frame['parts'][name]['assembly_to_machine'])
        raw = v.check_routes(paths, pose, points, labels)
        if name == 'DFR_Post_Bar':
            # The connector goes on after the sacrificial perimeter is detached.
            # Keep the untrimmed scan. Include every bead near the permanent bar
            # plus an extra half millimetre around its whole bounding box.
            raw_bar = raw
            piece = b.load(OUT / frame['parts'][name]['source']).transform(pose[:3])
            bounds = np.asarray(piece.bounding_box())
            margin = .50 + points[:,3:4]/2
            inside = ((points[:,:3] >= bounds[:3]-margin) & (points[:,:3] <= bounds[3:]+margin)).all(axis=1)
            assert inside.sum()>1000
            raw = v.check_routes(paths, pose, points[inside], labels)
        fits[name] = raw
    v.write(folder / 'before-pad-removal.json', raw_bar)
    v.write(folder / 'routes.json', fits)
    failed = [(part, name, value['obstructed_poses']) for part, paths in fits.items()
              for name, value in paths.items() if value['obstructed_poses']]
    assert not failed, failed


if __name__ == '__main__':
    if sys.argv[1] == 'baseline':
        v.write(Path(sys.argv[2]), profiles(previous.OUT / 'print-mechanisms'))
    else:
        audit(Path(sys.argv[1]))
