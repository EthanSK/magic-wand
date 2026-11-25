"""Inspect R69's changed load paths in an actual native slice.

Run `sections69.py SLICE_DIRECTORY` after audit69. It compares the retainer's
deposited sections with R68, the rod contact profile with R58, and renders the
new barrel bridge and keeper lips. These are nominal bead envelopes, not a
measurement of printed strength, bonding, grip force or fatigue. — GPT-6.1 Sol
"""
import argparse
import json
from pathlib import Path

import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

import audit69 as a


def run(folder: Path) -> dict:
    """Compare the actual slice with the earlier working geometry and record its hashes. — GPT-6.1 Sol"""
    archive = folder / a.v.ARCHIVE
    frames = a.v.read(folder / 'layout.frame.json')['parts']
    points, _ = a.v.read_native(archive)
    current_tines = tine_sections(points, np.asarray(frames['OP1_Lid_Stop']['assembly_to_machine']))
    current_rod = rod_profile(points, np.asarray(frames['Key_Carrier']['assembly_to_machine']))
    cheeks = cheek_layers(points, np.asarray(frames['Key_Carrier']['assembly_to_machine']),
                          a.v.read(folder / 'layers.json'))
    image = draw_layers(folder, points, frames)
    del points
    before = a.d.r68.OUT / 'print-mechanisms'
    old_points, _ = a.v.read_native(before / a.v.ARCHIVE)
    old_frames = a.v.read(before / 'layout.frame.json')['parts']
    old_tines = tine_sections(old_points, np.asarray(old_frames['OP1_Lid_Stop']['assembly_to_machine']))
    del old_points
    reference = a.d.HARDWARE / 'carbon-rod-holders-r58-smooth-click' / 'exports' / 'print-mechanisms'
    old_points, _ = a.v.read_native(reference / a.v.ARCHIVE)
    old_frames = a.v.read(reference / 'layout.frame.json')['parts']
    old_rod = rod_profile(old_points, np.asarray(old_frames['Key_Carrier']['assembly_to_machine']))
    del old_points
    shared = sorted(set(current_rod) & set(old_rod))
    assert len(shared) > 50
    compared = [dict(y_mm=y, r58_diameter_mm=old_rod[y], r69_diameter_mm=current_rod[y]) for y in shared]
    report = dict(
        archive_sha256=a.v.digest(archive), checker_sha256=a.v.digest(__file__),
        frame_sha256=a.v.digest(folder / 'layout.frame.json'),
        image_sha256=a.v.digest(image), coverage_complete=True,
        cheek_overlap=cheeks,
        retainer=dict(r68=old_tines, r69=current_tines,
                      minimum_ratio={side: round(current_tines[side]['minimum_area_mm2'] / old_tines[side]['minimum_area_mm2'], 4)
                                     for side in ('left', 'right')}),
        rod=dict(stations=compared, max_station_diameter_difference_mm=round(max(abs(row['r69_diameter_mm'] - row['r58_diameter_mm']) for row in compared), 4),
                 outer_wall=outer_ring_wall()),
        method='All bead types. Retainer sections union actual width/height envelopes at <=0.12 mm path samples, without inflating widths. Rounded physical bead profiles and bonding remain unmeasured.',
        physical_strength_and_grip_verified=False)
    (folder / 'mechanical-sections.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def cheek_layers(points: np.ndarray, frame: np.ndarray, layers: dict) -> dict:
    """Reject the old rear-ramp flake and the earlier missing joint layer. — GPT-6.1 Sol"""
    inverse = np.linalg.inv(frame)
    local = points[:, :3] @ inverse[:3, :3].T + inverse[:3, 3]
    band = (abs(local[:, 0]) > 7.2) & (abs(local[:, 0]) < 11.5)
    rows, flagged = [], []
    for layer in (17, 18):
        hit = band & (abs(points[:, 2] - layer * .2) < .01) & (local[:, 2] > 8.9) & (local[:, 2] < 14)
        assert int(hit.sum()) > 100, (layer, int(hit.sum()))
        y = float(local[hit, 1].mean())
        slice_y = y + layers['layer_mm'] / 2  # bead Z is the layer top; CAD is sampled at its mid-plane
        roof = a.hinge69.BUTTRESS_END_Z + max(0, a.hinge69.cheek_profile()[-1][0] - slice_y)
        top = float(local[hit, 2].max())
        rows.append(dict(layer=layer, samples=int(hit.sum()), assembly_y_layer_top_mm=round(y, 4),
                         assembly_y_slice_mm=round(slice_y, 4),
                         maximum_bead_centre_z_mm=round(top, 4), roof_z_mm=round(roof, 4)))
        assert top <= roof + .35, rows[-1]
    for run in layers['parts']['Key_Carrier']['runs_requiring_review']:
        if run['layer'] not in (17, 18):
            continue
        world = inverse @ [*run['midpoint_machine_xy'], run['layer'] * .2, 1]
        if 7.2 < abs(world[0]) < 11.5 and 39.9 < world[1] < 40.6:
            flagged.append(run)
    assert not flagged, flagged
    return dict(passes=True, layers=rows, bridge_or_flake_runs=flagged,
                interpretation='The rear floor remains joined; neither the former low bridges nor the old upper-ramp loops survive.')


def tine_sections(points: np.ndarray, frame: np.ndarray) -> dict:
    """Measure the complete notched span on both tines using nominal deposited sections. — GPT-6.1 Sol"""
    assert np.allclose(frame[:3, :3], np.eye(3))
    local = points[:, :3] - frame[:3, 3]
    rotation = np.asarray(a.b.board_matrix())[:2, :2]
    uv = (local[:, :2] - np.asarray(a.b.STATION)) @ rotation
    selected = (abs(uv[:, 0]) < 8) & (uv[:, 1] > -5) & (uv[:, 1] < 2.5) & (local[:, 2] > 11) & (local[:, 2] < 17)
    uv, z, q = uv[selected], local[selected, 2], points[selected]
    assert len(q) > 1000
    rows = {'left': [], 'right': []}
    for station in np.arange(-4.5, 2.001, .1):
        half = q[:, 3] / 2
        hit = abs(uv[:, 1] - station) < half
        dx = np.sqrt(np.maximum(0, half[hit] ** 2 - (uv[hit, 1] - station) ** 2))
        envelopes = [box(float(u - w), float(top - h), float(u + w), float(top))
                     for u, w, top, h in zip(uv[hit, 0], dx, z[hit], q[hit, 4]) if w > 1e-6]
        section = unary_union(envelopes)
        for side, bounds in (('left', (-7.21, -3.59)), ('right', (3.59, 7.21))):
            measured = section.intersection(box(bounds[0], 10.8, bounds[1], 17))
            assert measured.area > .4, (station, side)
            rows[side].append(dict(v_mm=round(float(station), 3), area_mm2=round(measured.area, 4)))
    return {side: dict(minimum_area_mm2=min(row['area_mm2'] for row in samples), samples=samples) for side, samples in rows.items()}


def rod_profile(points: np.ndarray, frame: np.ndarray) -> dict:
    """Use the same radial bead-envelope rule for each old/new front-ring station. — GPT-6.1 Sol"""
    assert np.allclose(frame[:3, 1], [0, 0, -1])
    q = points[(abs(points[:, 0] - frame[0, 3]) < 5.5) & (abs(points[:, 1] - frame[1, 3]) < 5.5)]
    radius = np.hypot(q[:, 0] - frame[0, 3], q[:, 1] - frame[1, 3]) - q[:, 3] / 2 - .06
    rows = {}
    for top in np.unique(q[:, 2]):
        y = round(float(frame[2, 3] - top), 2)
        if 8.9 <= y <= 20.0:
            rows[y] = round(2 * float(radius[q[:, 2] == top].min()), 4)
    return rows


def outer_ring_wall() -> dict:
    """Report the sleeve outside the restored bore, independently of the contact radius. — GPT-6.1 Sol"""
    old = a.b.load(a.d.HARDWARE / 'carbon-rod-holders-r58-smooth-click' / 'exports' / a.d.HOLDER)
    current = a.b.load(a.OUT / a.d.HOLDER)
    regions = {}
    for radius in (5.5, 6.5, 8.0):
        outer = a.o.lay(a.d.mf.Manifold.cylinder(10.5, radius, radius, 144), 9.25)
        inner = a.o.lay(a.d.mf.Manifold.cylinder(10.7, a.o.ROD_R + .021, a.o.ROD_R + .021, 144), 9.15)
        shell = outer - inner
        left, right = old ^ shell, current ^ shell
        regions[str(radius)] = dict(r58_mm3=round(left.volume(), 4), r69_mm3=round(right.volume(), 4),
                                    removed_mm3=round((left - right).volume(), 4), added_mm3=round((right - left).volume(), 4))
    return dict(assembly_y_mm=[9.25, 19.75], inner_radius_mm=a.o.ROD_R + .021, outer_radius_regions_mm=regions,
                caveat='This distinguishes restored bore contact from the surrounding wall. It does not measure spring compliance or grip force.')


def draw_layers(folder: Path, points: np.ndarray, frames: dict) -> Path:
    """Show both barrel anchors and the reinforced keeper in actual adjacent layers. — GPT-6.1 Sol"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import EllipseCollection
    fig, axes = plt.subplots(3, 4, figsize=(14, 12), layout='constrained')
    for row, (part, point, span) in enumerate([
        ('Touch_Paddle', [0, a.hinge69.AXIS, a.hinge69.KEEPER_Z + a.hinge69.BARREL_R - a.hinge69.BARREL_FLAT], [5, 10]),
        ('OP1_Lid_Stop', [*a.b.board_point(0, -1), a.hinge69.POST_TOP_Z - a.hinge69.LIP_THICK], [11, 8]),
        ('Key_Carrier', [0, 40.25, 10.7], [13, 4])]):
        frame = np.asarray(frames[part]['assembly_to_machine'])
        centre = frame @ [*point, 1]
        first = np.ceil((centre[2] - .001) / .2) * .2
        xy = points[:, :2] - centre[:2]
        keep = (abs(xy[:, 0]) < span[0]) & (abs(xy[:, 1]) < span[1])
        q, xy = points[keep], xy[keep]
        for col, top in enumerate(first + np.array([-.2, 0, .2, .4])):
            ax = axes[row, col]
            for offset, color in ((-.2, '#666a73'), (0, '#ef766b')):
                take = abs(q[:, 2] - top - offset) < .01
                widths = q[take, 3]
                ax.add_collection(EllipseCollection(widths, widths, np.zeros(len(widths)), units='xy', offsets=xy[take],
                                                   transOffset=ax.transData, facecolors=color, edgecolors='none', alpha=.75))
            ax.set(xlim=(-span[0], span[0]), ylim=(-span[1], span[1]), aspect='equal',
                   title=f'{part}\nlayer top {top:.2f} mm', xlabel='machine X offset (mm)', ylabel='machine Y offset (mm)')
    fig.suptitle('Native bead footprints: current red, previous grey; physical bonding and sag untested')
    path = folder / 'bridge-and-keeper-layers.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    result = run(parser.parse_args().folder)
    print(json.dumps(dict(coverage_complete=result['coverage_complete'],
                          retainer_minimum_area_mm2={rev: {side: row['minimum_area_mm2'] for side, row in result['retainer'][rev].items()}
                                                    for rev in ('r68', 'r69')},
                          rod_stations=len(result['rod']['stations']),
                          rod_max_diameter_difference_mm=result['rod']['max_station_diameter_difference_mm'],
                          rod_outer_wall=result['rod']['outer_wall'])), flush=True)
