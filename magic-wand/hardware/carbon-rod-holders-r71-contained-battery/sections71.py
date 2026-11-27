"""R71 deposited load paths and selected actual native layers.

R70's section and post method is reused for unchanged geometry. R71 adds the
holder-side neck and full-width plate end on every base fin, with visual witnesses at the new guard/battery/clip
locations. Nominal deposited envelopes do not predict break force or friction.
— GPT-6.1 Sol
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from shapely.geometry import box, LineString
from shapely.ops import unary_union

import audit71 as a
import sections70 as previous


class DesignContract:
    def __getattr__(self, name):
        return getattr(a.d, name) if hasattr(a.d, name) else getattr(a.d.r70, name)


def configure():
    previous.a = SimpleNamespace(d=DesignContract(), v=a.v, b=a.b, hinge70=a.hinge, kit70=a.k)


def neck_sections(folder, points, frame):
    """Measure the deliberate holder break and stronger plate end at full height."""
    body = a.b.load(a.OUT / frame['source'])
    pose = np.asarray(frame['assembly_to_machine'])
    orient = pose[:3].copy(); orient[:2, 3] = 0
    lay = a.k.p54.layout54(body.transform(orient), a.k.panel55.settings(frame['adhesion_panel']))
    result = []
    for root, tie in zip(lay['roots'], frame['adhesion_panel']['ties']):
        assert np.allclose(root['out'], a.k.p54._frame(tie['face'])[0])
        out, tangent = root['out'], np.abs(root['tangent'])
        station = root['station'] + pose[:2, 3]
        local = points[:, :2] - station
        normal, along = local @ out, local @ tangent
        chosen = (abs(along) < 1.3) & (points[:, 2] - points[:, 4] < root['height'] + .01)
        q, normal, along = points[chosen], normal[chosen], along[chosen]
        ends = []
        spans = list(a.k.neck_spans(root))
        if not any(row[3] == 'plate' for row in spans):
            # The repaired kit leaves this end full width, making the holder
            # neck the deliberate break. Still measure both actual endpoints.
            spans.append((root['start'] - sum(a.k.PLATE_NECK),
                          root['start'] - a.k.PLATE_NECK[0], a.k.FIN, 'plate'))
        for lo, hi, width, name in spans:
            rows = []
            for depth in np.linspace(lo + .08, hi - .08, 3):
                within = abs(normal - depth) < q[:, 3] / 2
                at, x, delta = q[within], along[within], normal[within] - depth
                half = np.sqrt(np.maximum(0, (at[:, 3] / 2) ** 2 - delta ** 2))
                section = unary_union([box(float(px - w), float(top - height), float(px + w), float(top))
                                       for px, w, top, height in zip(x, half, at[:, 2], at[:, 4]) if w > 1e-6])
                section = section.intersection(box(-a.k.FIN / 2 - .10, 0, a.k.FIN / 2 + .10, root['height']))
                widths = [section.intersection(LineString([(-2, float(z)), (2, float(z))])).length
                          for z in np.arange(.50, root['height'] - .09, .2)]
                assert widths, (tie, root['height'])
                rows.append(dict(outward_station_mm=round(float(depth), 4), area_mm2=round(section.area, 4),
                                 minimum_width_above_panel_mm=round(min(widths), 4)))
            expected = width * root['height']
            ends.append(dict(end=name, nominal_width_mm=width, nominal_section_mm2=round(expected, 4), rows=rows,
                             passes=bool(all(.75 * expected <= row['area_mm2'] <= 1.25 * expected
                                             and .70 * width <= row['minimum_width_above_panel_mm'] <= 1.25 * width for row in rows))))
        assert {row['end'] for row in ends} == {'holder', 'plate'}
        areas = {end['end']: [row['area_mm2'] for row in end['rows']] for end in ends}
        bias = min(areas['plate']) / max(areas['holder'])
        result.append(dict(face=tie['face'], station=tie['at'], height_mm=root['height'], ends=ends,
                           minimum_plate_to_maximum_holder_section_ratio=round(bias, 4),
                           passes=all(row['passes'] for row in ends) and bias > 1.12))
    return result


def draw(folder, points, frames):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import EllipseCollection
    d, h, b = a.d, a.hinge, a.b
    probes = [
        ('new guard arm', 'Key_Carrier', [-13.78, 14.0, 3.5], [6, 7]),
        ('battery rail and tongue', 'Key_Carrier', [sum(d.PACK_X) / 2, d.TONGUE_Y[1] - d.LEVER, d.PACK_MID], [9, 6]),
        ('guard and pouch nose', 'Key_Carrier', [-18., d.PACK_Y0 - .8, d.PACK_MID], [9, 6]),
        ('roof base neck', 'Key_Carrier', [-26.45, d.BED - 1., d.DECK + 1.2], [6, 5]),
        ('heel base neck', 'Key_Carrier', [-27., d.BED - 1., d.LOW - .8], [6, 4]),
        ('OP1 seat', 'Key_Carrier', [0, 0, b.PCB_Z - .1], [8, 9]),
        ('left new board clip', 'DFR_Clip_Left', [-b.HOLE_X, b.HOLE_Y, b.BOARD_TOP + a.h.CLIP_T - .2], [5, 5]),
        ('right new board clip', 'DFR_Clip_Right', [b.HOLE_X, b.HOLE_Y, b.BOARD_TOP + a.h.CLIP_T - .2], [5, 5]),
        ('eased journal', 'Touch_Paddle', [-h.JOURNAL_OUT + .5, h.AXIS, h.KEEPER_Z], [5, 6]),
        ('new post nose', 'DFR_Post_Bar', [b.HOLE_X, b.HOLE_Y - .98, b.BOARD_TOP + a.h.NECK + .1], [3, 3]),
        ('spring arm root', 'DFR_Clip_Left', [-b.HOLE_X + sum(a.h.ARM_X) / 2, b.HOLE_Y - a.h.ARM_ROOT + .3, b.BOARD_TOP + a.h.LIFT + a.h.CLIP_T - .4], [4, 4]),
        ('spring root underside', 'DFR_Clip_Left', [-b.HOLE_X + sum(a.h.ARM_X) / 2, b.HOLE_Y - a.h.ARM_ROOT + .08, b.BOARD_TOP + a.h.LIFT + a.h.CLIP_T - a.h.arm_thickness(-a.h.ARM_ROOT + .08) + .1], [4, 4]),
    ]
    fig, axes = plt.subplots(4, 3, figsize=(15, 17), layout='constrained')
    for ax, (title, part, point, span) in zip(axes.flat, probes):
        frame = np.asarray(frames[part]['assembly_to_machine']); centre = frame @ [*point, 1]
        nearest = np.unique(points[(abs(points[:, 0] - centre[0]) < span[0]) & (abs(points[:, 1] - centre[1]) < span[1]), 2])
        assert len(nearest), title
        top = float(nearest[np.argmin(abs(nearest - centre[2]))])
        for layer, color in ((top - .2, '#8d939d'), (top, '#dc7864')):
            mask = (abs(points[:, 2] - layer) < .015) & (abs(points[:, 0] - centre[0]) < span[0]) & (abs(points[:, 1] - centre[1]) < span[1])
            q = points[mask]
            ax.add_collection(EllipseCollection(q[:, 3], q[:, 3], np.zeros(len(q)), units='xy', offsets=q[:, :2],
                                                transOffset=ax.transData, facecolors=color, edgecolors='none', alpha=.8))
        ax.set(xlim=(centre[0] - span[0], centre[0] + span[0]), ylim=(centre[1] - span[1], centre[1] + span[1]),
               title=f'{title} — actual layer {top:.2f} mm', aspect='equal')
        ax.grid(alpha=.15)
    for ax in axes.flat[len(probes):]:
        ax.set_axis_off()
    path = folder / 'r71-critical-native-layers.png'
    fig.savefig(path, dpi=125); plt.close(fig)
    return path


def run(folder):
    configure()
    current = previous.measure(folder)
    reference = previous.measure(a.d.r70.OUT / 'print-mechanisms')
    points, _ = a.v.read_native(folder / a.v.ARCHIVE)
    frames = a.v.read(folder / 'layout.frame.json')['parts']
    necks = neck_sections(folder, points, frames['Key_Carrier'])
    image = draw(folder, points, frames)
    report = dict(archive_sha256=a.v.digest(folder / a.v.ARCHIVE), frame_sha256=a.v.digest(folder / 'layout.frame.json'),
                  checker_sha256=a.v.digest(__file__), parts=current['parts'],
                  sections={name: dict(r70=reference['sections'][name], r71=row) for name, row in current['sections'].items()},
                  post_fit=dict(r70=reference['post_fit'], r71=current['post_fit']),
                  post_neck_root=dict(r70=reference['post_neck_root'], r71=current['post_neck_root']),
                  base_necks=necks, images={image.name: a.v.digest(image)}, physical_strength_and_fit_verified=False,
                  method='Nominal native deposited envelopes; full fin heights and three planes at both fin endpoints. Width and continuity are measured, not break force.')
    report['passes'] = bool(set(current['parts']) == a.k.COMPLETE and all(row['passes'] for row in necks)
                            and all(3.04 < rows[0]['smallest_enclosing_diameter_mm'] < 3.3 and rows[-1]['smallest_enclosing_diameter_mm'] < 3.05
                                    for rows in current['post_fit'].values()))
    a.v.write(folder / 'mechanical-sections.json', report)
    assert report['passes'], report
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('folder', type=Path)
    print(json.dumps(run(p.parse_args().folder)))
