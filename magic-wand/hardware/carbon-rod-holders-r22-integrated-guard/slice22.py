#!/usr/bin/env python3
"""Check the exact R22 meshes and deposited layers before trying the print."""
import argparse
import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

import holder22 as holder
import project22
import slice20 as previous


OUT = holder.HERE / 'exports'
Q = previous.q
START = previous.start_audit
PROJECT = OUT / (project22.LABEL + '.gcode.3mf')
GUARD_FREE_SPAN_MM = (22., 26.)


def inspect_regions(name, transform, samples, widths, heights, kinds, features, removable):
    if name == 'Key_Carrier':
        regions = holder.carrier_regions()
    elif name in ('Battery_Holder', 'XIAO_Rod_Holder'):
        regions = holder.h20.part_regions(name)
    else:
        return {}
    to_print = np.linalg.inv(transform)[:3, :]
    result = {}
    for label, region in regions.items():
        swept = isinstance(region, holder.spaces16.Swept)
        poses = region.poses() if swept else [region]
        pose_count = len(region) if swept else 1
        worst, count, worst_examples = 0, 0, []
        for pose in poses:
            check = Q.inspect_region(pose.transform(to_print), samples, widths, heights, kinds, features, transform, limit=3)
            count = max(count, check['checked_samples'])
            hits = sum(check['violations'].values())
            if hits > worst:
                worst, worst_examples = hits, check['examples']
        result[label] = {'poses': pose_count, 'nearby_samples': count, 'worst_violations': worst}
        if worst:
            result[label]['examples'] = worst_examples
            if label in ('external_wire_bus', 'reverse_wire_bus'):
                keep = ~removable
                permanent = Q.inspect_region(region.transform(to_print), samples[keep], widths[keep],
                                             heights[keep], kinds[keep], features, transform, limit=3)
                result[label]['violations_after_pad_removal'] = sum(permanent['violations'].values())
    return result


def cable_check(samples, widths, tops, transform):
    cfg = holder.C
    radius = cfg['conductor_od_mm'] / 2
    centre = cfg['centres_mm']
    clearance = {'rod_bore': mf.CrossSection.circle(3.85, 128),
                 'rod_slit': holder.rect(-6, -3.6, -.35, .35),
                 'cable_slit': holder.rect(centre, centre + 5.5, -radius, radius)}
    clearance.update({f'wire_{i + 1}': mf.CrossSection.circle(radius, 48).translate(point)
                      for i, point in enumerate(holder.wire_centres())})
    rows = []
    assembly_xy = Q.points(samples, transform)[:, :2]
    clip = holder.cable_clip()
    pad_shapes = [part.slice(.1) for part in holder.cable_clip_pads().decompose()]
    tie_half_width = cfg['tie_width_mm'] / 2 + .3
    tie_area = holder.rect(4.7 - tie_half_width, 4.7 + tie_half_width, -6., 6.)
    for top in sorted(set(np.round(tops, 4))):
        use = abs(tops - top) < 1e-3
        beads = START.bead_footprints(Q, assembly_xy[use], widths[use])
        overlap = {name: round((beads ^ shape).area(), 6) for name, shape in clearance.items()}
        layer = clip.slice(float(top) - .1)
        coverage = (beads ^ layer).area() / layer.area()
        # A waist check traverses the joined material where the loops meet.
        waist = holder.rect(4.55, 5.15, -.6, .6)
        waist_spans = [(beads ^ holder.rect(x - .015, x + .015, -1.5, 1.5)).area() / .03
                       for x in (4.55, 4.7, 4.85, 5., 5.15)]
        waist_coverage = (beads ^ waist).area() / waist.area()
        pads_joined = None
        pad_gap = None
        if top <= cfg['pad_thickness_mm'] + .001:
            pads_joined = all(any((part ^ layer).area() > 1. and (part ^ pad).area() > 1.
                                  for part in beads.decompose()) for pad in pad_shapes)
            xy, w = assembly_xy[use], widths[use]
            on_clip = Q._inside(layer.offset(.05), xy)
            pad_outline = mf.CrossSection.batch_boolean(pad_shapes, mf.OpType.Add)
            on_pad = Q._inside(pad_outline.offset(.05), xy) & ~on_clip
            clip_beads = START.bead_footprints(Q, xy[on_clip], w[on_clip])
            pad_beads = START.bead_footprints(Q, xy[on_pad], w[on_pad]) - tie_area
            assert not clip_beads.is_empty() and not pad_beads.is_empty()
            low, high = 0., 2.
            for _ in range(14):
                mid = (low + high) / 2
                if (clip_beads.offset(mid, Q.JoinType.Round) ^ pad_beads).is_empty():
                    low = mid
                else:
                    high = mid
            pad_gap = round(low, 4)
        rows.append({'top_mm': float(top), 'opening_intrusion_mm2': overlap,
                     'clip_coverage': round(coverage, 4), 'waist_coverage': round(waist_coverage, 4),
                     'min_waist_span_mm': round(min(waist_spans), 4),
                     'components': len(beads.decompose()), 'pads_joined': pads_joined,
                     'pad_gap_away_from_ties_mm': pad_gap})
    return rows


def guard_check(samples, widths, tops, transform):
    guard = holder.guard().transform(np.linalg.inv(transform)[:3, :])
    rows = []
    for top in sorted(set(np.round(tops, 4))):
        section = guard.slice(float(top) - .1)
        relevant = [piece for piece in section.decompose() if piece.area() >= .1]
        if not relevant:
            continue
        use = abs(tops - top) < 1e-3
        beads = START.bead_footprints(Q, samples[use, :2], widths[use])
        fractions = [(piece ^ beads).area() / piece.area() for piece in relevant]
        row = {'top_mm': float(top), 'pieces': len(relevant), 'min_section_coverage': round(min(fractions), 4)}
        if GUARD_FREE_SPAN_MM[0] <= top <= GUARD_FREE_SPAN_MM[1]:
            spans = [piece for piece in relevant if piece.area() >= 1.]
            cores = [piece.offset(-.30) for piece in spans]
            assert len(cores) == len(holder.G['beams']) and all(not core.is_empty() for core in cores), top
            row['min_free_section_coverage'] = round(min((piece ^ beads).area() / piece.area() for piece in spans), 4)
            row['min_free_core_coverage'] = round(min((core ^ beads).area() / core.area() for core in cores), 4)
        rows.append(row)
    return rows


def ring_backing_check(samples, widths, tops, overhangs):
    # Arachne originally started two internal loops above sparse infill gaps.
    # Check deposited plastic under those same windows, not the solid CAD section.
    window = holder.rect(25.9, 29.5, 10.2, 12.4)
    x0, y0, x1, y1 = window.bounds()
    nearby = np.all(samples[:, :2] >= [x0 - .5, y0 - .5], axis=1) & np.all(
        samples[:, :2] <= [x1 + .5, y1 + .5], axis=1)
    rows = []
    for top in (1.4, 17.2):
        use = nearby & (abs(tops - (top - .2)) < .001)
        prior = START.bead_footprints(Q, samples[use, :2], widths[use])
        unsupported = []
        for row in overhangs:
            if abs(row['layer_top_mm'] - top) < .001:
                xa, ya, xb, yb = row['print_xy_bounds_mm']
                if not (window ^ holder.rect(xa, xb, ya, yb)).is_empty():
                    unsupported.append(row)
        rows.append({'shell_layer_top_mm': top, 'prior_bead_coverage': round((window ^ prior).area() / window.area(), 4),
                     'partial_overhangs_in_window': unsupported})
    return rows


def inspect(project=PROJECT, target=OUT / 'slice-clearances.json'):
    manifest = json.loads((OUT / 'manifest.json').read_text())
    anchor_manifest = json.loads((OUT / 'anchors.json').read_text())
    layout = json.loads((OUT / (project22.LABEL + '-print-checks.json')).read_text())
    data, features, _, settings, offset, parts, _, _ = previous.s16.read_project(project)
    assert set(parts) == set(holder.PLATE)
    assert not any(name.startswith(('Support', 'Brim', 'Skirt', 'Raft')) for name in features)
    assert settings['timelapse_type'] == '1' and settings['enable_prime_tower'] == '1'
    assert not project22.studio.p19.slice_info_warnings(project)
    tower = data[:, 5].astype(int) == features.index('Prime tower')
    points = data[:, :3] + offset
    radius = data[tower, 3, None] / 2
    tower_lo = (points[tower, :2] - radius).min(0)
    tower_hi = (points[tower, :2] + radius).max(0)
    gaps = {name: round(float(np.linalg.norm(np.maximum(np.maximum(np.array(lo[:2]) - tower_hi,
                                                                  tower_lo - np.array(hi[:2])), 0))), 3)
            for name, (lo, hi) in layout['plate_extents_mm'].items()}
    assert (tower_lo >= 0).all() and (tower_hi <= 180).all() and min(gaps.values()) > 5
    rows, failures = {}, []
    previous.anchors20.OUT = OUT
    for name in holder.PLATE:
        part = parts[name]
        record = manifest['parts'][name]
        path = OUT / (name + '-SOURCE-REQUIRES-PREPARATION.stl')
        assert holder.sha(path) == record['stl_sha256']
        expected = trimesh.load_mesh(path)
        place = (part['vertices'].min(0) + part['vertices'].max(0) - expected.bounds.sum(0)) / 2
        assert np.array_equal(part['faces'], expected.faces), (name, 'sliced topology differs')
        assert np.abs(part['vertices'] - place - expected.vertices).max() < .0002, (name, 'sliced position differs')
        actual = Q.solid(expected.vertices, expected.faces)
        combined = actual
        pads = None
        if name in holder.ANCHORED:
            pad_path = OUT / (name + '-ANCHOR-REMOVE-AFTER-PRINT.stl')
            assert holder.sha(pad_path) == anchor_manifest['parts'][name]['stl_sha256']
            pads = holder.read(pad_path)
            read_pads, label = previous.slice19.anchor_in_project(project, name, place)
            drift = (pads - read_pads).volume() + (read_pads - pads).volume()
            assert drift < .05 and 'REMOVE AFTER PRINT' in label, (name, drift, label)
            combined += pads
        lo, hi = np.asarray(combined.bounding_box()).reshape(2, 3)
        local = points - place
        use = np.all(local >= lo - .45, axis=1) & np.all(local <= hi + .45, axis=1)
        assert use.sum() > 100
        samples, widths, heights = local[use], data[use, 3], data[use, 4]
        kinds, tops = data[use, 5].astype(int), data[use, 7]
        transform = np.asarray(record['print_to_assembly'])
        starts = START.inspect(Q, combined, samples, heights, kinds, features, tops, transform, widths)
        removable = np.zeros(len(samples), dtype=bool)
        if pads is not None:
            for top in np.unique(tops[tops <= .401]):
                in_layer = abs(tops - top) < .001
                at = float(top) - .1
                at_pad = Q._inside(pads.slice(at).offset(.26), samples[in_layer, :2])
                at_main = Q._inside(actual.slice(at).offset(.26), samples[in_layer, :2])
                removable[in_layer] = at_pad & ~at_main
        openings = inspect_regions(name, transform, samples, widths, heights, kinds, features, removable)
        bad_openings = [label for label, check in openings.items()
                        if check.get('violations_after_pad_removal', check['worst_violations'])]
        row = {'samples': int(use.sum()), 'working_spaces': openings, 'layer_starts': starts}
        if starts['floating_components'] or starts['missing_printed_components'] or bad_openings:
            failures.append({'part': name, 'openings': bad_openings,
                             'floating': len(starts['floating_components']), 'missing': len(starts['missing_printed_components'])})
        if name in ('Key_Carrier', 'Battery_Holder', 'XIAO_Rod_Holder'):
            row['ties'] = previous.neck_audit(name, samples, widths, tops)
        if name == 'Key_Carrier':
            row['guard_layers'] = guard_check(samples, widths, tops, transform)
            if not row['guard_layers'] or min(layer['min_section_coverage'] for layer in row['guard_layers']) < .65:
                failures.append({'part': name, 'reason': 'guard layer underfilled'})
            free_span = [layer for layer in row['guard_layers'] if 'min_free_core_coverage' in layer]
            if len(free_span) != 21 or any(layer['min_free_section_coverage'] < .90 or
                                           layer['min_free_core_coverage'] < .95 for layer in free_span):
                failures.append({'part': name, 'reason': 'free guard span underfilled', 'layers': free_span})
            row['ring_backing'] = ring_backing_check(samples, widths, tops, starts['partial_overhangs'])
            if any(layer['prior_bead_coverage'] < .8 or layer['partial_overhangs_in_window'] for layer in row['ring_backing']):
                failures.append({'part': name, 'reason': 'missing bead backing below ring shell', 'layers': row['ring_backing']})
        if name == holder.C['name']:
            row['cable_layers'] = cable_check(samples, widths, tops, transform)
            for layer in row['cable_layers']:
                top = layer['top_mm']
                # Two bead widths through the full-height core. At the entry
                # chamfers the remaining material must still connect the loops.
                chamfer = holder.C['cable_chamfer_mm']
                core = chamfer < top - .1 < holder.C['axial_width_mm'] - chamfer
                span_floor = .84 if core else .42
                gap = layer['pad_gap_away_from_ties_mm']
                if (max(layer['opening_intrusion_mm2'].values()) > .01 or layer['min_waist_span_mm'] < span_floor
                        or (gap is not None and gap < .35)
                        or layer['components'] != 1 or layer['pads_joined'] is False):
                    failures.append({'part': name, 'cable_layer': layer})
        rows[name] = row
        print(name, int(use.sum()), 'opening violations', bad_openings, 'floating', len(starts['floating_components']), flush=True)
    report = {'project_sha256': holder.sha(project), 'manifest_sha256': holder.sha(OUT / 'manifest.json'),
              'anchors_sha256': holder.sha(OUT / 'anchors.json'), 'checker_sha256': holder.sha(Path(__file__)),
              'features': features, 'tower_gaps_mm': gaps, 'parts': rows, 'failures': failures,
              'passed': not failures, 'physical_print_verified': False}
    target.write_text(json.dumps(report, indent=2) + '\n')
    assert not failures, failures[:4]
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=PROJECT)
    parser.add_argument('--report', type=Path, default=OUT / 'slice-clearances.json')
    args = parser.parse_args()
    inspect(args.project, args.report)
