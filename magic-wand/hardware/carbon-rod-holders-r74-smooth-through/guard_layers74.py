"""Find new unsupported toolpaths compared with the previously checked R73 plate."""
from pathlib import Path
import json
import sys
from zipfile import ZipFile

import numpy as np
import kit74
import release61
from layers53 import q, roofs51


def nearby(run, candidate):
    # Line numbers change when a plate is re-sliced. Match physical locations,
    # previous-layer bond and the shape of the span in the same part instead.
    return (run['layer'] == candidate['layer'] and run['two_anchors'] == candidate['two_anchors']
            and abs(run['mm'] - candidate['mm']) < .6
            and abs(run['bend_mm'] - candidate['bend_mm']) < .15
            and np.max(np.abs(np.asarray(run['extent_machine_xy']) - candidate['extent_machine_xy'])) < .4)


def inner_guard_bridge(folder, row, frame, baseline):
    # The inner leg meets the underside of the deck. Its first long perimeter
    # runs almost straight between two anchors. Check the actual deposited
    # widths, fan, feed and plastic immediately beyond both ends of that pass.
    x, y = row['midpoint_machine_xy']
    local = np.linalg.solve(frame, [x, y, row['layer'] * .2 - .1, 1.])
    if (row['part'] != 'Key_Carrier' or not row['two_anchors']
            or not np.allclose(local[:3], [-20.93, -2.25, 5.51], atol=.25)):
        return None
    with ZipFile(folder / release61.ARCHIVE) as archive:
        lines = archive.read('Metadata/plate_1.gcode').decode().splitlines()
    layer = row['layer']
    marks = {round(float(line.split(':')[1]) * 5): i for i, line in enumerate(lines) if line.startswith('; Z_HEIGHT:')}
    start = marks[layer - 2]
    window = '\n'.join(lines[start:marks[layer + 1]])
    pts, _, _ = q.extrusion_points(window, .06)
    numbers, seq, speed, fan = roofs51.map_moves(q, window, len(pts), step=.06)
    first, last = np.asarray(row['gcode_lines']) - start
    ids = np.flatnonzero((numbers >= first) & (numbers <= last))
    assert len(ids) > 10 and np.all(seq[ids] == seq[ids[0]])
    current = pts[ids]
    near = np.all((pts[:, :2] >= current[:, :2].min(axis=0) - 2) & (pts[:, :2] <= current[:, :2].max(axis=0) + 2), axis=1)
    layers = np.rint(pts[:, 7] * 5)
    prior = pts[near & ((layers == layer - 1) | ((layers == layer) & (seq < seq[ids[0]])))]

    def anchor(end, direction):
        travel = 0.
        for index in range(end, end + direction * 200, direction):
            if index < 0 or index >= len(pts) or seq[index] != seq[end] or travel > 1.:
                break
            point = pts[index]
            overlap = (prior[:, 3] + point[3]) / 2 - np.linalg.norm(prior[:, :2] - point[:2], axis=1)
            if np.any(overlap >= .03):
                return round(float(travel), 3)
            travel += np.linalg.norm(pts[index + direction, :2] - point[:2])
        return None

    ends = [anchor(ids[0], -1), anchor(ids[-1], 1)]
    width = float(current[:, 3].min())
    established = min((r for r in baseline if r['two_anchors'] and r['mm'] >= row['mm']
                       and r['bend_mm'] >= row['bend_mm']), key=lambda r: r['mm'], default=None)
    return dict(run=row, overlap_at_ends_within_mm=ends, min_line_width_mm=round(width, 3),
                min_fan_fraction=round(float(fan[ids].min()), 2), max_speed_mm_s=round(float(speed[ids].max()), 2),
                earlier_anchored_bridge=established,
                passes=bool(established and all(d is not None and d <= width for d in ends)
                            and row['bend_mm'] < width and row['mm'] < 6 and fan[ids].min() >= .69 and speed[ids].max() <= 16))


def inspect(folder):
    old = kit74.kit73.model.OUT / 'print-mechanisms'
    current = release61.read(folder / 'layers.json')
    previous = release61.read(old / 'layers.json')
    report = dict(archive_sha256=current['archive_sha256'], previous_archive_sha256=previous['archive_sha256'],
                  parts={}, reviewed_bridges=[], new_runs_for_inspection=[])
    frame = np.asarray(release61.read(folder / 'layout.frame.json')['parts']['Key_Carrier']['assembly_to_machine'])
    for name, part in current['parts'].items():
        before = previous['parts'][name]['runs_requiring_review']
        after = part['runs_requiring_review']
        extra = [row for row in after if not any(nearby(row, old_row) for old_row in before)]
        report['parts'][name] = dict(floating_starts=part['completely_unsupported_starts'],
                                     runs_in_reference=len(before), runs_in_slice=len(after), new_runs=len(extra))
        for row in extra:
            identified = dict(part=name, **row)
            review = inner_guard_bridge(folder, identified, frame, before)
            if review:
                report['reviewed_bridges'].append(review)
            if not review or not review['passes']:
                report['new_runs_for_inspection'].append(identified)
    report['passes'] = (not report['new_runs_for_inspection']
                        and all(not p['floating_starts'] for p in report['parts'].values()))
    (folder / 'guard-review.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    result = inspect(Path(sys.argv[1]))
    print(json.dumps(result['new_runs_for_inspection'], indent=2))
