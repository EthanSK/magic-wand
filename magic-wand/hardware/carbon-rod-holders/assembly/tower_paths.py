#!/usr/bin/env python3
"""Show a disposable tower using the source archive's actual extrusion paths.

This read-only viewer export does not alter geometry or printer commands. Run
with a checked sliced archive and a JSON destination beside the assembly page.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import zipfile


def extract(project):
    with zipfile.ZipFile(project) as archive:
        member = next(name for name in archive.namelist() if name.endswith('.gcode'))
        source = archive.read(member)
    x = y = z = e = 0.
    relative_e = False
    absolute_xyz = True
    feature = ''
    segments = []
    for raw in source.decode().splitlines():
        if raw.startswith('; FEATURE: '):
            feature = raw.split(':', 1)[1].strip()
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        command = line.split()[0]
        if command == 'M83': relative_e = True
        elif command == 'M82': relative_e = False
        elif command == 'G90': absolute_xyz = True
        elif command == 'G91': absolute_xyz = False
        elif command in ('G0', 'G1', 'G2', 'G3', 'G92'):
            args = {letter: float(value) for letter, value in re.findall(r'([XYZIJE])\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))', line)}
            if command == 'G92':
                x, y, z, e = (args.get(k, v) for k, v in zip('XYZE', (x, y, z, e)))
                continue
            nx, ny, nz = (args.get(k, v) if absolute_xyz else v + args.get(k, 0) for k, v in zip('XYZ', (x, y, z)))
            extrusion = args.get('E', 0) if relative_e else args.get('E', e) - e
            if feature == 'Prime tower' and extrusion > 0 and (nx != x or ny != y):
                points = [(x, y, z)]
                if command in ('G2', 'G3'):
                    cx, cy = x + args.get('I', 0), y + args.get('J', 0)
                    radius = math.hypot(x - cx, y - cy)
                    start, end = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                    sweep = (end - start) % (2 * math.pi) if command == 'G3' else -((start - end) % (2 * math.pi))
                    count = max(1, math.ceil(abs(sweep) * radius / .5))
                    points.extend((cx + radius * math.cos(start + sweep * n / count), cy + radius * math.sin(start + sweep * n / count), z + (nz - z) * n / count) for n in range(1, count))
                points.append((nx, ny, nz))
                segments.extend([*a, *b] for a, b in zip(points, points[1:]))
            x, y, z = nx, ny, nz
            if 'E' in args: e = e + args['E'] if relative_e else args['E']
    if not segments:
        raise ValueError('No actual tower extrusion found')
    values = [segment[:3] for segment in segments] + [segment[3:] for segment in segments]
    low = [min(p[i] for p in values) for i in range(3)]
    high = [max(p[i] for p in values) for i in range(3)]
    centre = [(low[i] + high[i]) / 2 for i in range(2)] + [0]
    centered = [[round(v - centre[i % 3], 4) for i, v in enumerate(segment)] for segment in segments]
    digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return {'schema_version': 1, 'units': 'mm', 'source_sha256': digest(project), 'generator_sha256': digest(__file__),
            'source_member': member, 'bounds_mm': [low, high], 'segments': centered, 'display': 'Extrusion centre lines, not solid beads. Disposable smooth-timelapse helper.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    data = extract(args.project)
    args.output.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    print(json.dumps({'segments': len(data['segments']), 'bounds_mm': data['bounds_mm']}))
