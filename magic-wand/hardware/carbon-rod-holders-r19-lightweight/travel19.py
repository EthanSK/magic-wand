#!/usr/bin/env python3
"""Non-printing moves from Bambu G-code, including the spiral Z lifts that G0/G1 parsing misses.

Bambu's Auto Lift can raise the nozzle with `G3 Z.. I.. J.. P1`, a helix with no X or Y word. A
reader that only tracks G0/G1 keeps a stale height after one, so it reports hopped travels as flat.
"""
import math
import re
import numpy as np

WORD = re.compile(r'([XYZEIJ])(-?\d*\.?\d+)')


def walk(text):
    """Yield (layer_top, kind, start_xyz, end_xyz, feature) in file order. kind is 'extrude', 'travel' or 'wipe'."""
    x = y = z = 0.; top = None; feature = ''
    for line in text.splitlines():
        if line.startswith('; Z_HEIGHT:'):
            top = float(line.split(':')[1]); continue
        if line.startswith('; FEATURE:'):
            feature = line.split(':')[1].strip(); continue
        code = line.split(';')[0].strip()
        head = code.split(' ', 1)[0]
        if head not in ('G0', 'G1', 'G2', 'G3'): continue
        w = {k: float(v) for k, v in WORD.findall(code)}
        nx, ny, nz = w.get('X', x), w.get('Y', y), w.get('Z', z); e = w.get('E', 0.)
        kind = 'extrude' if e > 0 else 'wipe' if e < 0 else 'travel'
        if head in ('G2', 'G3') and 'I' in w and ('X' in w or 'Y' in w):
            cx, cy = x + w['I'], y + w.get('J', 0.); a0 = math.atan2(y - cy, x - cx); a1 = math.atan2(ny - cy, nx - cx); r = math.hypot(x - cx, y - cy)
            if head == 'G3' and a1 <= a0: a1 += 2 * math.pi
            if head == 'G2' and a1 >= a0: a1 -= 2 * math.pi
            steps = max(2, int(abs(a1 - a0) * r / .5) + 1); px, py, pz = x, y, z
            for i in range(1, steps + 1):
                f = i / steps; qx, qy, qz = cx + r * math.cos(a0 + (a1 - a0) * f), cy + r * math.sin(a0 + (a1 - a0) * f), z + (nz - z) * f
                yield top, kind, (px, py, pz), (qx, qy, qz), feature
                px, py, pz = qx, qy, qz
        else:
            yield top, kind, (x, y, z), (nx, ny, nz), feature
        x, y, z = nx, ny, nz


def crossing_fractions(a0, a1, segments):
    """Fractions along the move from a0 to a1 at which it strictly crosses a segment."""
    if not len(segments): return np.empty(0)
    p, r = np.asarray(a0, float), np.asarray(a1, float) - np.asarray(a0, float)
    q = segments[:, :2]; s = segments[:, 2:] - q; denom = r[0] * s[:, 1] - r[1] * s[:, 0]; ok = abs(denom) > 1e-9
    d = q[ok] - p; den = denom[ok]; f = (d[:, 0] * s[ok, 1] - d[:, 1] * s[ok, 0]) / den; u = (d[:, 0] * r[1] - d[:, 1] * r[0]) / den
    return f[(f > .001) & (f < .999) & (u > .001) & (u < .999)]


def exposure(text, lo_bed, hi_bed, min_top, max_top=1e9, long_move=2.):
    """Every travel whose middle lies over a part's plan box, from a layer top upward.

    Each crossing of a wall already laid in that layer is credited with the nozzle's height at that
    point along the move, so a ramped travel is not mistaken for a flat one. Moves are reported in
    full and split at long_move (mm), because the slicer only lifts for moves over its minimum.
    Nothing here measures curl or force.
    """
    lo, hi = np.asarray(lo_bed, float), np.asarray(hi_bed, float); walls = []; outer = []; current = None; wipes = 0; travels = 0
    rows = {'any_wall': [], 'outer_wall': []}; per_layer = {}
    for top, kind, a, b, feature in walk(text):
        if top != current:
            walls, outer = [], []; current = top
        if top is None or top < min_top or top > max_top: continue
        a2, b2 = np.array(a[:2]), np.array(b[:2]); inside = np.all((a2 + b2) / 2 >= lo) and np.all((a2 + b2) / 2 <= hi)
        if kind == 'extrude':
            if inside and 'wall' in feature.lower():
                walls.append((*a[:2], *b[:2]))
                if 'outer' in feature.lower() or 'overhang' in feature.lower(): outer.append((*a[:2], *b[:2]))
            continue
        if not inside: continue
        if kind == 'wipe':
            wipes += 1; continue
        moved = float(np.linalg.norm(b2 - a2))
        if moved < .01: continue
        travels += 1
        for label, group in (('any_wall', walls), ('outer_wall', outer)):
            hits = crossing_fractions(a2, b2, np.array(group)) if group else np.empty(0)
            if len(hits):
                height = float((a[2] + (b[2] - a[2]) * hits - top).min()); rows[label].append((moved, round(height, 3)))
                if label == 'outer_wall' and height < .05: per_layer[round(top, 1)] = per_layer.get(round(top, 1), 0) + 1
    summary = {'travels_over_part': travels, 'wipe_moves_excluded': wipes, 'layer_top_range_mm': [min_top, None if max_top > 1e8 else max_top], 'length_split_mm': long_move, 'layers_with_outer_wall_crossed_at_layer_height': len(per_layer)}
    for label, values in rows.items():
        for band, chosen in (('all', values), (f'longer_than_{long_move:g}_mm', [v for v in values if v[0] > long_move]), (f'up_to_{long_move:g}_mm', [v for v in values if v[0] <= long_move])):
            heights = np.array([v[1] for v in chosen]) if chosen else np.empty(0)
            summary[f'{label}_{band}'] = {'travels_crossing': int(len(heights)), 'of_which_at_layer_height': int((heights < .05).sum()), 'lowest_nozzle_height_mm': float(heights.min()) if len(heights) else None,
                                          'median_nozzle_height_mm': float(np.median(heights)) if len(heights) else None, 'longest_flat_move_mm': round(max((v[0] for v in chosen if v[1] < .05), default=0.), 3)}
    summary['method'] = 'G0/G1/G2/G3 including helix lifts and ramped travels; a wipe is a move with negative E; each crossing of an earlier same-layer wall inside the plan box is credited with the interpolated nozzle height there.'
    return summary
