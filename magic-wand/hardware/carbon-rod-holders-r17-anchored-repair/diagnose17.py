#!/usr/bin/env python3
"""Measure why the R16 battery holder left the bed, from the re-sliced retry project.

Input: the offline re-slice of the prepared 8 mm outer-brim R16 project (kept outside the repository;
the exact G-code the printer received was not available). Output: exports/diagnosis-r16-retry.json.
Timing comes from a camera timelapse that is not committed: it is typed in here as text and every
frame-to-layer mapping is an inference. The initiating cause is not proven by any of this.
"""
import argparse, json
from pathlib import Path
import numpy as np, trimesh
import holder17 as h
import slice16 as s16
import travel17

q = s16.q; OUT = h.HERE / 'exports'; R16_OUT = h.R16 / 'exports'

TIMELAPSE = {
    'source': 'Camera timelapse of the failed retry, 185 frames; not committed. The plate had 178 layers, and frames near the end are identical, so frame number is treated as approximately layer number. That mapping is an inference.',
    'observations': [
        {'frames': '0-109', 'observation': 'No visible anomaly on the battery holder.'},
        {'frames': '109-110', 'observation': 'A discrete change between consecutive frames: the top of the open battery lattice appears disturbed, with material missing and two upright bars above the old outline. Layer 110 of 178 prints at Z 22 mm in the retry G-code; 185 frames against 178 layers puts frame 110 at roughly Z 20.6-22 mm.'},
        {'frames': '111-112', 'observation': 'Loose strands appear at the top of the battery holder.'},
        {'frames': '112-147', 'observation': 'A growing nest of misplaced filament on the battery holder. The base stays on the plate through this period.'},
        {'frames': '148', 'observation': 'The whole battery holder has left its position, about 38 layers after the first visible change. The 8 mm outer brim stays on the plate with a clean part-shaped opening. A small earlier tilt cannot be excluded from this camera angle.'},
    ],
    'reading': 'The first visible failure is high up in the part, not at the bed. Loss of the part from the bed came second. What triggered the first change (curl, a travel strike, or the lattice simply breaking under the nozzle) is not visible and is not established.',
}


def poly_stats(cs):
    A = Sx = Sy = Ixx = Iyy = 0.
    for p in cs.to_polygons():
        a = np.array(p); b = np.roll(a, -1, axis=0); cr = a[:, 0] * b[:, 1] - b[:, 0] * a[:, 1]
        A += cr.sum() / 2; Sx += ((a[:, 0] + b[:, 0]) * cr).sum() / 6; Sy += ((a[:, 1] + b[:, 1]) * cr).sum() / 6
        Ixx += ((a[:, 1] ** 2 + a[:, 1] * b[:, 1] + b[:, 1] ** 2) * cr).sum() / 12; Iyy += ((a[:, 0] ** 2 + a[:, 0] * b[:, 0] + b[:, 0] ** 2) * cr).sum() / 12
    cx, cy = Sx / A, Sy / A; bb = cs.bounds(); Icx = Ixx - A * cy * cy; Icy = Iyy - A * cx * cx
    return A, Icx / max(cy - bb[1], bb[3] - cy), Icy / max(cx - bb[0], bb[2] - cx)


def islands(samples, widths, tops, lo, hi, step=2.):
    """Connected printed islands from actual bead footprints, one layer every `step` mm."""
    rows = []
    for top in sorted({round(float(v), 3) for v in tops if lo <= v <= hi}):
        if abs(top / step - round(top / step)) > 1e-3: continue
        sel = abs(tops - top) < 1e-3; beads = s16.start_audit.bead_footprints(q, samples[sel, :2], widths[sel])
        areas = sorted((round(c.area(), 2) for c in beads.decompose()), reverse=True)
        rows.append({'layer_top_mm': top, 'islands': len(areas), 'largest_mm2': areas[0], 'smallest_mm2': areas[-1], 'total_mm2': round(sum(areas), 2)})
    return rows


def part_samples(data, offset, info, expected):
    place = (info['vertices'].min(0) + info['vertices'].max(0) - expected.bounds.sum(0)) / 2
    local = data[:, :3] + offset - place; lo, hi = expected.bounds; mask = np.all(local[:, :2] >= lo[:2] - .4, 1) & np.all(local[:, :2] <= hi[:2] + .4, 1)
    return place, local[mask], data[mask, 3], data[mask, 7]


def seam(data, offset, parts, features, name):
    expected = trimesh.load_mesh(R16_OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); info = parts[name]; place = (info['vertices'].min(0) + info['vertices'].max(0) - expected.bounds.sum(0)) / 2
    local = data[:, :3] + offset - place; lo, hi = expected.bounds; first = abs(data[:, 7] - .2) < 1e-3
    near = first & (local[:, 0] > lo[0] - 14) & (local[:, 0] < hi[0] + 14) & (local[:, 1] > lo[1] - 14) & (local[:, 1] < hi[1] + 14); fid = data[:, 5].astype(int)
    brim = near & (fid == features.index('Brim')); wall = near & (fid == features.index('Outer wall')); A, B = local[wall, :2], local[brim, :2]; WA, WB = data[wall, 3], data[brim, 3]
    gaps = []
    for i in range(0, len(A), 400):
        d = np.linalg.norm(A[i:i + 400, None, :] - B[None, :, :], axis=2); j = d.argmin(1); gaps.append(d[np.arange(len(j)), j] - (WA[i:i + 400] + WB[j]) / 2)
    gaps = np.concatenate(gaps)
    manifest = json.loads((R16_OUT / 'manifest.json').read_text()); axis = q.points(np.array([[0, 0, 0.]]), np.linalg.inv(np.array(manifest['parts'][name]['print_to_assembly'])))[0]; radial = np.linalg.norm(B - axis[:2], axis=1)
    actual = q.solid(expected.vertices, expected.faces); area, zx, zy = poly_stats(actual.slice(.1)); height = float(expected.bounds[1][2])
    return {'first_layer_area_mm2': round(area, 2), 'print_height_mm': round(height, 2),
            'brim_to_outer_wall_bead_edge_gap_mm': {'min': round(float(gaps.min()), 3), 'median': round(float(np.median(gaps)), 3), 'p95': round(float(np.percentile(gaps, 95)), 3)},
            'fraction_of_outer_wall_with_brim_bead_touching': round(float((gaps <= .03).mean()), 3),
            'brim_samples_inside_the_3p9_mm_bore_radius': int((radial < 3.9).sum()), 'closest_brim_sample_to_bore_axis_mm': round(float(radial.min()), 3),
            'elastic_screen_bed_edge_tension_MPa_per_N_applied_at_top': {'load_along_X': round(height / zy, 4), 'load_along_Y': round(height / zx, 4)}}


def bed_box(info, offset, expected):
    """Part plan box in G-code coordinates."""
    place = (info['vertices'].min(0) + info['vertices'].max(0) - expected.bounds.sum(0)) / 2
    return place[:2] + expected.bounds[0][:2] - offset[:2], place[:2] + expected.bounds[1][:2] - offset[:2]


def run(retry):
    data, features, stats, settings, offset, parts, text, _ = s16.read_project(retry)
    name = 'Battery_Holder'; expected = trimesh.load_mesh(R16_OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); _, samples, widths, tops = part_samples(data, offset, parts[name], expected)
    lo, hi = bed_box(parts[name], offset, expected)
    r17 = OUT / 'R17-A1-mini-PETG.gcode.3mf'; d2, f2, st2, set2, off2, parts2, text2, _ = s16.read_project(r17); exp2 = trimesh.load_mesh(OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')); _, s2, w2, t2 = part_samples(d2, off2, parts2[name], exp2); lo2, hi2 = bed_box(parts2[name], off2, exp2)
    keys = ['brim_type', 'brim_width', 'brim_object_gap', 'initial_layer_line_width', 'textured_plate_temp', 'nozzle_temperature', 'z_hop', 'z_hop_types', 'wall_loops', 'enable_support']
    report = {'input': 'Offline Bambu Studio CLI re-slice of the prepared 8 mm outer-brim R16 project; not the file the printer ran', 'input_sha256': h.sha(retry), 'generator_sha256': h.sha(Path(__file__)), 'travel_parser_sha256': h.sha(h.HERE / 'travel17.py'), 'r17_project_sha256': h.sha(r17),
              'settings_read_from_retry_project': {k: settings.get(k) for k in keys}, 'timelapse': TIMELAPSE,
              'which_part_and_what_opening': {'part': name, 'opening': 'The opening left in the brim is the part\'s own first-layer outline: the end plate plus the ring. It is bare plate because no brim is printed under a part. The disc found inside the ring is brim plastic printed inside the 7.9 mm bore through the 30-degree clip gap.', 'uncertainty': 'Identified from plate position and footprint shape against the delivered layout; no physical part was measured.'},
              'first_layer_seam_by_part': {n: seam(data, offset, parts, features, n) for n in parts}}
    report['upper_battery_printed_islands'] = {'r16_retry': islands(samples, widths, tops, 18., 30.), 'r17': islands(s2, w2, t2, 18., 30.)}
    report['travel_over_battery_holder_from_layer_top_18_mm'] = {'r16_retry': travel17.exposure(text, lo, hi, 18.), 'r17': travel17.exposure(text2, lo2, hi2, 18.)}
    report['findings'] = [
        'In this offline re-slice the seam was not mechanically joined: the median bead-edge gap between outer wall and brim was under 0.1 mm and no outer-wall sample had a brim bead touching it.',
        'The brim stayed on the plate after the part left, which suggests the brim-to-plate bond held at the end; it does not establish what happened to the base before frame 148.',
        'The first visible change in the camera frames was at about layer 110, in the top of an open lattice that this slice prints as many separate islands; the part left its position about 38 layers later.',
        'R17 replaces those islands with one connected section, adds fused multi-layer anchors, lifts travel moves fully before crossing walls, and uses a 0.6 mm hop.',
    ]
    report['not_established'] = ['What initiated the first change at layer 110: curl, a travel strike or a lattice break.', 'Adhesion force, peel force or the force on the part at any time.', 'Whether the base had partly released before frame 148.', 'Whether the printer ran exactly this G-code, including the brim seam gap.', 'Whether plate cleanliness contributed.']
    report['physical_print_verified'] = False
    (OUT / 'diagnosis-r16-retry.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['upper_battery_printed_islands', 'travel_over_battery_holder_from_layer_top_18_mm']})[:2600], flush=True); print({n: v['brim_to_outer_wall_bead_edge_gap_mm'] for n, v in report['first_layer_seam_by_part'].items()}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--retry-project', type=Path, required=True); a = p.parse_args(); run(a.retry_project)
