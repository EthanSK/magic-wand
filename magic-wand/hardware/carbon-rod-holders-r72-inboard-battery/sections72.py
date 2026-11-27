"""Measure each release fin and compare the eight reused parts with the qualified R71 slice."""
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile
import json
import sys
import numpy as np

import audit72 as audit
import sections71 as previous

a, m = audit.a, audit.m


def owners(archive):
    with ZipFile(archive) as file:
        plate = ElementTree.fromstring(file.read('Metadata/slice_info.config')).find('plate')
    return {part.get('name'): int(part.get('identify_id')) for part in plate.findall('object')}


def signature(points, owner):
    # Compare the spatial distribution of all bead samples, widths and layer heights.
    # Extrusion order can differ when another object changes how long a layer takes.
    near = np.round(points[points[:,6] == owner, :5], decimals=4)
    assert len(near) > 150
    order = np.lexsort(near.T[::-1])
    return near[order]


def run(folder):
    archive = folder/a.v.ARCHIVE
    old_archive = m.prev.OUT/'print-mechanisms'/a.v.ARCHIVE
    frame = a.v.read(folder/'layout.frame.json')['parts']
    points, _ = a.v.read_native(archive)
    old_points, _ = a.v.read_native(old_archive)
    new_ids, old_ids = owners(archive), owners(old_archive)
    equal = {}
    for part, owner in new_ids.items():
        if part == 'Key_Carrier':
            continue
        current = signature(points, owner)
        earlier = signature(old_points, old_ids[part])
        equal[part] = bool(np.array_equal(current, earlier))
    del old_points
    previous_out = a.OUT
    try:
        a.OUT = m.OUT
        necks = previous.neck_sections(folder, points, frame['Key_Carrier'])
    finally:
        a.OUT = previous_out
    report = dict(archive_sha256=a.v.digest(archive), prior_archive_sha256=a.v.digest(old_archive),
                  frame_sha256=a.v.digest(folder/'layout.frame.json'), reused_bead_samples_equal=equal,
                  unchanged_meshes={r['name']:a.v.digest(r['source']) for r in audit.kit72.parts() if r['name']!='Key_Carrier'},
                  base_necks=necks, passes=len(necks)==5 and all(n['passes'] for n in necks))
    a.v.write(folder/'release-fins-and-reused-parts.json', report)
    print('Base fins', report['passes'], 'unchanged sliced parts', equal, flush=True)
    if not report['passes']:
        raise ValueError('Release fins lack a smaller, connected holder-side section')


if __name__ == '__main__':
    run(Path(sys.argv[1]))
