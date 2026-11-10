#!/usr/bin/env python3
"""Check every real R21 layer for clear loops, connecting material and pad removal.

Uses the existing R16 bead parser and R15 layer-start auditor. The screens bind
to the exact archive and source; none measures real PETG force or cable fit.
"""
from pathlib import Path
import argparse
import json
import math
import sys
import numpy as np
import trimesh
import manifold3d as mf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import clip21 as h
import project21 as project

sys.path.insert(0, str(h.h19.R16))
import slice16 as s16  # noqa: E402
import slice19  # noqa: E402

OUT = h.HERE / 'exports'


def check(archive: Path, report_name: str) -> None:
    manifest = json.loads((OUT / 'manifest.json').read_text())
    for file, digest in manifest['sources'].items():
        assert h.sha(h.HERE / file) == digest, file
    data, features, stats, cfg, offset, parts, _, _ = s16.read_project(archive)
    assert list(parts) == [h.NAME]
    assert not any(f.startswith(('Support', 'Brim', 'Skirt')) for f in features)
    assert cfg['timelapse_type'] == '1' and cfg['enable_prime_tower'] == '1'
    assert not project.p19.slice_info_warnings(archive)
    commands = project.command_audit(archive)
    expected = trimesh.load_mesh(OUT / (h.NAME + '-SOURCE-REQUIRES-PREPARATION.stl'))
    actual = parts[h.NAME]
    place = (actual['vertices'].min(0) + actual['vertices'].max(0) - expected.bounds.sum(0)) / 2
    assert np.array_equal(expected.faces, actual['faces'])
    assert np.abs(actual['vertices'] - place - expected.vertices).max() < 1e-4
    transform = np.asarray(manifest['parts'][h.NAME]['print_to_assembly'])
    shift = -transform[:3, 3]
    rebuilt = s16.q.solid(expected.vertices - shift, expected.faces)
    drift = (rebuilt - h.clip()).volume() + (h.clip() - rebuilt).volume()
    assert drift < .02, ('Source/STL drift', drift)
    pad_mesh = trimesh.load_mesh(OUT / (h.NAME + '-ANCHOR-REMOVE-AFTER-PRINT.stl'))
    pad_project, _ = slice19.anchor_in_project(archive, h.NAME, place)
    pad_source = s16.q.solid(pad_mesh.vertices, pad_mesh.faces)
    pad_drift = (pad_source - pad_project).volume() + (pad_project - pad_source).volume()
    assert pad_drift < .02
    for sign in (-1, 1):
        y0, y1 = sorted((sign * 3.5, sign * 3.9))
        corridor = h.h19.box(4.2, 5.6, y0, y1, -.1, 1)
        assert (h.clip() ^ corridor).volume() < .001, 'Scissors would cut permanent plastic'
    lo, hi = np.asarray(h.anchors().bounding_box())[:3] + shift, np.asarray(h.anchors().bounding_box())[3:] + shift
    bounds = np.vstack((np.minimum(lo, expected.bounds[0]), np.maximum(hi, expected.bounds[1])))
    xyz = data[:, :3] + offset - place
    selected = np.all(xyz >= bounds[0] - .45, 1) & np.all(xyz <= bounds[1] + .45, 1)
    local, widths, heights = xyz[selected], data[selected, 3], data[selected, 4]
    tops, types = data[selected, 7], data[selected, 5].astype(int)
    assert selected.sum() > 500
    combined = (h.clip() + h.anchors()).translate(tuple(shift))
    starts = s16.start_audit.inspect(s16.q, combined, local, heights, types, features, tops, np.eye(4), widths)
    assert not starts['floating_components'] and not starts['missing_printed_components']
    clear = {
        'rod_bore_7p7mm': mf.CrossSection.circle(3.85, 128),
        'cable_bore_3p7mm': mf.CrossSection.circle(1.85, 128).translate((h.P['centres_mm'], 0)),
        'rod_entry': mf.CrossSection.square((6, .7)).translate((-6, -.35)),
        'cable_entry': mf.CrossSection.square((3.0, .6)).translate((h.P['centres_mm'] + 1.6, -.3)),
    }
    layers = []
    pad_gaps = []
    tie_regions = mf.CrossSection()
    pad_regions = mf.CrossSection()
    for sign in (-1, 1):
        y0, y1 = sorted((sign * .8, sign * 4.7))
        tie_regions += mf.CrossSection.square((.7, y1 - y0)).translate((4.55, y0))
        y0, y1 = sorted((sign * 4.5, sign * 7.0))
        pad_regions += mf.CrossSection.square((3., y1 - y0)).translate((3.5, y0))
    centre = np.array([4.9, 0.])
    for top in sorted(set(np.round(tops, 4))):
        ids = abs(tops - top) < 1e-3
        beads = s16.start_audit.bead_footprints(s16.q, local[ids, :2] - shift[:2], widths[ids])
        for name, region in clear.items():
            assert (beads ^ region).area() < .005, (top, name, (beads ^ region).area())
        pieces = beads.decompose()
        assert len(pieces) == 1, (top, 'disconnected layer', len(pieces))
        section = h.clip().slice(float(top) - .1)
        coverage = (beads ^ section).area() / section.area()
        assert coverage > .8, (top, coverage)
        # The waist must be printed, not merely a union in the source mesh.
        waist = mf.CrossSection.square((.5, 1.6), center=True).translate(tuple(centre))
        assert (beads ^ waist).area() / waist.area() > .85, (top, 'missing waist')
        ties = []
        tracks = {}
        rows = local[ids, :2] - shift[:2]
        for label, x, angles, low, high in [('rod', 0., (-90, 90), 3.8, 5.6),
                                           ('cable', h.P['centres_mm'], (-90, 90), 1.8, 3.2)]:
            relative = rows - [x, 0.]
            theta = np.degrees(np.arctan2(relative[:, 1], relative[:, 0]))
            radii = np.linalg.norm(relative, axis=1)
            for angle in angles:
                selected_radii = np.sort(radii[(abs((theta - angle + 180) % 360 - 180) < 3) & (radii > low) & (radii < high)])
                clusters = []
                for radius in selected_radii:
                    if not clusters or radius - clusters[-1][-1] > .17: clusters.append([float(radius)])
                    else: clusters[-1].append(float(radius))
                tracks[f'{label}:{angle}'] = [float(np.median(c)) for c in clusters]
                assert len(clusters) >= 2, (top, label, angle, tracks)
        if top <= .401:
            for sign in (-1, 1):
                points = np.c_[np.full(50, 4.9), np.linspace(sign * 2.7, sign * 4.8, 50)]
                covered = float(s16.q._inside(beads, points).mean())
                assert covered > .95, (top, 'broken pad tie', sign, covered)
                ties.append(covered)
            # Reuse R19/R20's actual-bead separation screen away from the ties.
            # Connected layers alone cannot distinguish a tie from an extra weld.
            away = beads - tie_regions.offset(.35, mf.JoinType.Round)
            part_beads = away ^ section.offset(.3, mf.JoinType.Round)
            pad_beads = away ^ pad_regions.offset(.3, mf.JoinType.Round)
            assert part_beads.area() > 10 and pad_beads.area() > 5
            assert (part_beads.offset(.01, mf.JoinType.Round) ^ pad_beads).is_empty(), 'Pad welded to spring arm'
            low, high = 0., 1.2
            for _ in range(9):
                middle = (low + high) / 2
                low, high = (middle, high) if (part_beads.offset(middle, mf.JoinType.Round) ^ pad_beads).is_empty() else (low, middle)
            assert low >= .35, (top, 'pad-to-arm clearance', low)
            pad_gaps.append({'layer_top_mm': float(top), 'minimum_bead_gap_away_from_ties_mm': float(low)})
        layers.append({'top_mm': float(top), 'connected_pieces': len(pieces), 'source_area_printed_fraction': float(coverage), 'tie_coverage': ties, 'ring_track_centres_mm': tracks})
    assert len(layers) == 12
    tower = data[:, 5].astype(int) == features.index('Prime tower')
    assert tower.sum() > 0
    assert np.all(selected | tower), 'Unexpected extrusion outside the clip, pads or tower'
    world = data[tower, :2] + offset[:2]
    half = data[tower, 3, None] / 2
    tower_lo, tower_hi = (world - half).min(0), (world + half).max(0)
    assert np.all(tower_lo >= 0) and np.all(tower_hi <= 180)
    object_lo, object_hi = bounds[:, :2] + place[:2]
    gap = np.maximum(np.maximum(object_lo - tower_hi, tower_lo - object_hi), 0)
    assert np.linalg.norm(gap) > 5
    # A deliberate filled cable bore must trip the same opening test.
    assert ((h.clip().slice(1.2) + clear['cable_bore_3p7mm']) ^ clear['cable_bore_3p7mm']).area() > 5
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, shape, title in [(axes[0], h.clip().slice(1.2), 'Actual exported clip: 0.13 g CAD solid'),
                             (axes[1], beads, 'Final layer: actual extrusion footprints')]:
        for polygon in shape.to_polygons():
            ax.fill(polygon[:, 0], polygon[:, 1], color='#0d8c8f', alpha=.8)
        for x, radius, label in [(0, 4., '8 mm rod'), (h.P['centres_mm'], 2., '4 mm cable guide')]:
            ax.add_patch(plt.Circle((x, 0), radius, fill=False, linestyle='--', color='#555'))
            ax.text(x, 0, label, ha='center', va='center', fontsize=8)
        ax.set_aspect('equal'); ax.set_xlim(-6.5, 12); ax.set_ylim(-7.5, 7.5)
        ax.set_title(title); ax.set_xlabel('mm'); ax.set_ylabel('mm')
    fig.tight_layout()
    image = OUT / ('clip-and-paths.png' if report_name == 'slice-checks.json' else 'clip-and-paths-roundtrip.png')
    fig.savefig(image, dpi=160); plt.close(fig)
    report = {'project_sha256': h.sha(archive), 'manifest_sha256': h.sha(OUT / 'manifest.json'),
              'checker_sha256': h.sha(Path(__file__)), 'project_generator_sha256': h.sha(h.HERE / 'project21.py'),
              'actual_commands': commands, 'features': features, 'parser_stats': stats,
              'path_samples': int(selected.sum()), 'all_layers': layers,
              'working_openings': list(clear), 'source_mesh_matches': True,
              'source_stl_difference_mm3': float(drift), 'anchor_mesh_difference_mm3': float(pad_drift),
              'pad_bead_gaps': pad_gaps,
              'layer_starts': {k: v for k, v in starts.items() if k != 'partial_overhangs'},
              'partly_backed_regions': starts['partial_overhangs'],
              'tower_clearance_mm': float(np.linalg.norm(gap)), 'image': image.name, 'image_sha256': h.sha(image),
              'physical_print_verified': False, 'passed': True}
    (OUT / report_name).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'layers': len(layers), 'smallest_coverage': min(r['source_area_printed_fraction'] for r in layers), 'tower_gap_mm': report['tower_clearance_mm']}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--project', type=Path, default=OUT / 'R21-A1-mini-PETG.gcode.3mf')
    p.add_argument('--report', default='slice-checks.json')
    args = p.parse_args()
    check(args.project, args.report)
