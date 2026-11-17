"""Commanded filament per native object in a sliced Bambu archive.

Usage: material47.py ARCHIVE.gcode.3mf [ARCHIVE ...]
Counts positive E on moves with X or Y (G0-G3), grouped by the slicer's
object label comments; E-only retractions and primes are left out. Moves
outside any object (prime tower, purge line, wipes) are 'unowned'. The
estimate uses the archive's own filament diameter and density; it is not
a weighed mass.
"""
import json
import math
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

WORD = re.compile(r'([A-Z])(-?\d*\.?\d+)')
HELPERS = {'External_cradle', 'Front_pull_shelf', 'Rear_pull_shelf', 'Release_tabs'}


def per_object(archive):
    with ZipFile(archive) as z:
        gcode = z.read('Metadata/plate_1.gcode').decode()
        info = ET.fromstring(z.read('Metadata/slice_info.config'))
    names = {o.get('identify_id'): o.get('name') for o in info.iter('object')}
    diameter = float(re.search(r'; filament_diameter: ([\d.]+)', gcode).group(1))
    density = float(re.search(r'; filament_density: ([\d.]+)', gcode).group(1))
    declared = float(re.search(r'; total filament weight \[g\] : ([\d.]+)', gcode).group(1))
    relative, last_e, owner = True, 0., 'unowned_tower_or_machine'
    totals = {}
    for line in gcode.splitlines():
        if line.startswith('; start printing object, unique label id: '):
            owner = names.get(line.rsplit(' ', 1)[1], line.rsplit(' ', 1)[1])
            continue
        if line.startswith('; stop printing object'):
            owner = 'unowned_tower_or_machine'
            continue
        code = line.split(';', 1)[0].strip()
        if not code:
            continue
        if code.startswith('M83'):
            relative = True
        elif code.startswith('M82'):
            relative = False
        elif code.startswith('G92'):
            words = dict(WORD.findall(code[3:]))
            if 'E' in words:
                last_e = float(words['E'])
        elif code[:3] in ('G0 ', 'G1 ', 'G2 ', 'G3 '):
            words = dict(WORD.findall(code[2:]))
            if 'E' not in words:
                continue
            e = float(words['E'])
            step = e if relative else e - last_e
            if not relative:
                last_e = e
            if step > 0 and ('X' in words or 'Y' in words):
                totals[owner] = totals.get(owner, 0.) + step
    area = math.pi * diameter ** 2 / 4.
    objects = {n: {'commanded_xy_filament_mm': round(v, 3), 'estimated_g': round(v * area / 1000. * density, 3)}
               for n, v in sorted(totals.items())}
    helpers = sum(v['estimated_g'] for n, v in objects.items() if n in HELPERS)
    return {'archive': Path(archive).name, 'filament_diameter_mm': diameter, 'density_g_cm3': density,
            'objects': objects, 'helper_estimated_g': round(helpers, 3),
            'total_xy_estimated_g': round(sum(v['estimated_g'] for v in objects.values()), 3),
            'slicer_declared_total_g': declared}


if __name__ == '__main__':
    print(json.dumps([per_object(a) for a in sys.argv[1:]], indent=1))
