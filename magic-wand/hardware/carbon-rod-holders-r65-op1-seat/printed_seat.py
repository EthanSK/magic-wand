"""Measure where actual carrier extrusions support the board, on both sides of the click."""
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import numpy as np
from shapely.affinity import affine_transform
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

import kit65
import design65
import design64 as reference
from openings53 import read_native


def local_board_frame():
    transform = np.asarray(reference.b.board_matrix())
    inverse = np.linalg.inv(transform[:2, :2])
    return [*inverse.ravel(), *(-inverse @ transform[:2, 3])]


def board_outline():
    outline = Polygon()
    for boundary in reference.hardware()['board'].project().to_polygons():
        outline = outline.symmetric_difference(Polygon(boundary))
    return affine_transform(outline, local_board_frame())


def object_id(archive, name):
    with ZipFile(archive) as package:
        settings = ElementTree.fromstring(package.read('Metadata/model_settings.config'))
    def fields(node):
        return {m.get('key'): m.get('value') for m in node.findall('metadata')}
    carrier, = [obj.get('id') for obj in settings.findall('object') if fields(obj).get('name') == name]
    item, = [attrs for node in settings.find('plate').findall('model_instance')
             if (attrs := fields(node)).get('object_id') == carrier]
    return int(item['identify_id'])


def body_beads(archive, native, part):
    points, names = native
    features = [i for i, name in enumerate(names) if name in {
        'Outer wall', 'Inner wall', 'Bottom surface', 'Top surface', 'Internal solid infill',
        'Sparse infill', 'Bridge', 'Internal Bridge', 'Internal bridge', 'Overhang wall', 'Gap infill'}]
    return points[(points[:, 6] == object_id(archive, part)) & np.isin(points[:, 5], features)]


def printed_contact(folder, archive, native, height):
    """Section real bead widths and heights 0.10 mm below the nominal PCB underside.

    Each sampled bead contributes its inscribed cross-section at the witness plane.
    The sampling step is 0.12 mm or less. Exclude every other object and all support
    and adhesion features, so neither a brim nor a trapped support counts as a seat.
    """
    frame = json.loads((folder / 'layout.frame.json').read_text())['parts']['Key_Carrier']
    pose = np.asarray(frame['assembly_to_machine'])
    assert np.allclose(pose[:3, :3], [[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    tx, ty, tz = pose[:3, 3]
    points = body_beads(archive, native, 'Key_Carrier')
    mask = ((abs(points[:, 1] - ty - height) < points[:, 3]/2)
            & (abs(points[:, 0] - tx) < 24) & (abs(points[:, 2] - tz) < 25))
    rows = points[mask].astype(float)
    assert len(rows) > 100
    strips = []
    for level in np.unique(rows[:, 2]):
        layer = rows[rows[:, 2] == level]
        assert np.ptp(layer[:, 4]) < 1e-5
        dx = np.sqrt(np.maximum(0., (layer[:, 3]/2)**2 - (layer[:, 1] - ty - height)**2))
        ranges = sorted(zip(layer[:, 0] - tx - dx, layer[:, 0] - tx + dx))
        merged = []
        for lo, hi in ranges:
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        strips.extend(box(lo, tz-level, hi, tz-level+layer[0, 4]) for lo, hi in merged if hi > lo)
    return affine_transform(unary_union(strips), local_board_frame())


def sled_deposits(folder, archive, native, height):
    frame = json.loads((folder/'layout.frame.json').read_text())['parts']['OP1_Seat_Sled']
    pose = np.asarray(frame['assembly_to_machine'])
    assert np.allclose(pose[2,:3], [0, 0, 1])
    points = body_beads(archive, native, 'OP1_Seat_Sled')
    plane = height + pose[2,3]
    rows = points[(points[:,2] >= plane) & (points[:,2]-points[:,4] < plane)]
    assert len(rows) > 50
    # Grid centres in board-local coordinates. Query within each true bead width,
    # allowing for the smallest inscribed disc between successive G-code samples.
    resolution = .10
    xs = np.arange(-12, 18, resolution) + resolution/2
    ys = np.arange(-15, 25, resolution) + resolution/2
    board = np.asarray(reference.b.board_matrix())
    world = (rows[:,:2] - pose[:2,3]) @ pose[:2,:2]
    xy = (world-board[:2,3]) @ board[:2,:2]
    radii = rows[:,3]/2
    ix = np.rint((xy[:,0]-xs[0])/resolution).astype(int)
    iy = np.rint((xy[:,1]-ys[0])/resolution).astype(int)
    occupied = np.zeros((len(ys),len(xs)),dtype=bool)
    reach = int(np.ceil(radii.max()/resolution+.5))
    for ox in range(-reach,reach+1):
        for oy in range(-reach,reach+1):
            x, y = ix+ox, iy+oy
            inside = (x>=0)&(x<len(xs))&(y>=0)&(y<len(ys))
            x, y = x[inside], y[inside]
            hit = (xs[x]-xy[inside,0])**2 + (ys[y]-xy[inside,1])**2 <= radii[inside]**2
            occupied[y[hit],x[hit]] = True
    bands = []
    for y, cells in zip(ys, occupied):
        ends = np.flatnonzero(np.diff(np.pad(cells.astype(int),(1,1))))
        bands.extend(box(xs[lo]-.05,y-.05,xs[hi-1]+.05,y+.05) for lo,hi in ends.reshape(-1,2))
    # The detachable bed ties and the solder-socket holes must never contribute
    # to structural coverage. Clip to the section of the actual exported sled.
    mesh = reference.b.load(kit65.OUT/design65.SLED_FILE)
    section = Polygon()
    for ring in mesh.slice(height).to_polygons():
        section = section.symmetric_difference(Polygon(ring))
    return unary_union(bands).intersection(affine_transform(section, local_board_frame()))


def metrics(seat):
    zones = {'whole': board_outline(), 'left': box(-5,-10,0,22), 'right': box(0,-10,5,22),
             'switch_left': box(-2.9,-4.45,0,8.35), 'switch_right': box(0,-4.45,2.9,8.35)}
    areas = {key: round(seat.intersection(region).area, 2) for key, region in zones.items()}
    return dict(area_mm2=areas, plunger_inside_support_polygon=seat.convex_hull.contains(Point(0, 0)),
                nearest_support_to_plunger_mm=round(seat.distance(Point(0, 0)), 3))


def compare(folder, render=False):
    previous = kit65.kit64
    dirs = {'R63': previous.kit63.OUT/'print-mechanisms', 'R64': previous.OUT/'print-mechanisms', 'R65': folder}
    shapes = {}
    for label, path in dirs.items():
        archive = path / 'OP1-hinge.gcode.3mf'
        native = read_native(archive)
        top = reference.b.PCB_Z - .10
        if label == 'R65':
            shape = sled_deposits(path, archive, native, top)
            receiver = printed_contact(path, archive, native, design65.FLOOR-.10)
            underside = sled_deposits(path, archive, native, design65.FLOOR+.10)
            bearing = receiver.intersection(underside)
        else:
            shape = printed_contact(path, archive, native, top)
        shapes[label] = shape.intersection(board_outline())
        del native
    results = {label: metrics(shape) for label, shape in shapes.items()}
    report = dict(archive_sha256=sha256((folder/'OP1-hinge.gcode.3mf').read_bytes()).hexdigest(),
                  plane_below_board_mm=.10, sampled_bead_spacing_mm=.12, versions=results)
    # A broad, two-sided bearing should approach the previous R63 support in each
    # load region. Run the identical checks against the known bad R64 slice.
    baseline = results['R63']['area_mm2']
    def passes(result):
        return result['plunger_inside_support_polygon'] and all(
            result['area_mm2'][key] >= baseline[key]*.80 for key in baseline)
    report['known_bad_r64_rejected'] = not passes(results['R64'])
    report['receiver_bearing_mm2'] = {'left':round(bearing.intersection(box(-20,-30,0,30)).area,2),
                                      'right':round(bearing.intersection(box(0,-30,20,30)).area,2)}
    report['direct_plunger_contact_mm2'] = round(shapes['R65'].intersection(box(-1.45,-.6,1.45,.6)).area,2)
    report['passes'] = (report['known_bad_r64_rejected'] and passes(results['R65'])
                        and min(report['receiver_bearing_mm2'].values()) >= 10
                        and report['direct_plunger_contact_mm2'] >= 1.5)
    if render:
        draw(folder/'op1-seat-comparison.png', shapes, results)
    (folder/'printed-seat.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def draw(destination, shapes, results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(1, 3, figsize=(8, 5), layout='constrained', sharex=True, sharey=True)
    for ax, (label, surface) in zip(axes, shapes.items()):
        for contour in getattr(surface, 'geoms', [surface]):
            if contour.geom_type != 'Polygon':
                continue
            ax.fill(*contour.exterior.xy, color='#35866d')
            for hole in contour.interiors:
                ax.fill(*hole.xy, color='white')
        board = board_outline()
        for ring in [board.exterior, *board.interiors]:
            ax.plot(*ring.xy, color='#34414c', linewidth=1)
        ax.add_patch(Rectangle((-2.9,-4.45),5.8,12.8,fill=False,linestyle='--',color='#725499'))
        ax.plot(0, 0, '+', color='#5c267c', markersize=10)
        ax.set(aspect='equal', title=f"{label} · {results[label]['area_mm2']['whole']:.0f} mm²",
               xlabel='Board width (mm)', xlim=(-6,6), ylim=(-10,22))
    axes[0].set_ylabel('Along the OP1 board (mm)')
    fig.suptitle('Printed support beneath the OP1 board\nGreen = plastic at the seat · dashed = switch · + = press point')
    fig.savefig(destination, dpi=165)
    plt.close(fig)
