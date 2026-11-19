"""Check all four bought Choc keys against deposited plastic before removing supports."""
import argparse
import json
from functools import lru_cache
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import manifold3d as mf
import numpy as np

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'carbon-rod-holders-r51-guided-hinge'
sys.path.insert(0, str(PREVIOUS))
import build51
from orient51 import digest
from support51 import q as paths

KEYS = (0, 2, 3, 4)


@lru_cache(maxsize=1)
def key_spaces():
    # R44 lowered the R43 raised seats by 0.3 mm. Preserve the exact bought
    # Choc case, plate aperture, under-seat PCB/socket, and soldered loading routes.
    import holder44
    import holder41
    holder41.base.set_key_layout()
    old = holder41.r22.carrier_regions()
    spaces = {}
    for name, region in old.items():
        if not name.startswith(tuple(f'key_{key}_' for key in KEYS)):
            continue
        region = region.translate((0, 0, holder44.KEY_RAISE_MM))
        poses = list(region.poses()) if hasattr(region, 'poses') else [region]
        spaces[name] = poses
    for key in KEYS:
        assert all(f'key_{key}_{part}' in spaces for part in ('mount_opening', 'switch', 'socket', 'cap_travel'))
    return spaces


def socket_blocks():
    # Only this non-printing modifier uses conservative route boxes. Final
    # acceptance runs on the individual purchased-part shapes at each pose.
    blocks = {}
    for key in KEYS:
        bounds = np.asarray([pose.bounding_box() for name, poses in key_spaces().items()
                             if name.startswith(f'key_{key}_') for pose in poses])
        low, high = bounds[:, :3].min(axis=0), bounds[:, 3:].max(axis=0)
        blocks[f'Choc {key} insertion and removal'] = mf.Manifold.cube(high-low+0.8).translate(low-.4)
    return blocks


def inspect(archive, frame_file, output, seated_only=False):
    frame = np.asarray(json.loads(frame_file.read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    to_local = np.linalg.inv(frame)
    with ZipFile(archive) as src:
        gcode = src.read('Metadata/plate_1.gcode').decode()
        cfg = json.loads(src.read('Metadata/project_settings.config'))
        plate = ET.fromstring(src.read('Metadata/slice_info.config')).find('plate')
        owner = next(int(o.get('identify_id')) for o in plate.findall('object') if o.get('name')=='Key_Carrier')
    data, labels, _ = paths.extrusion_points(gcode, .12)
    data[:, :2] += np.fromstring(cfg['extruder_offset'][0], sep='x')
    import printed_props51
    ids=[i for i,n in enumerate(labels) if not n.startswith(('Support','Prime tower','Skirt','Brim'))]
    prop,_ = printed_props51.native_mask(archive,paths,data,owner,ids)
    data[prop,5] += len(labels)
    labels = list(labels)+['Exterior cradle / '+n for n in labels]
    result = {'archive_sha256': digest(archive), 'frame_sha256': digest(frame_file),
              'mode': 'seated diagnostic' if seated_only else 'complete insertion and removal', 'routes': {}}
    for name, poses in key_spaces().items():
        if seated_only and len(poses) > 1:
            continue
        tested = [p.transform(frame[:3]) for p in poses]
        bounds = np.asarray([p.bounding_box() for p in tested])
        lo, hi = bounds[:, :3].min(axis=0)-1., bounds[:, 3:].max(axis=0)+1.
        # Keep every extrusion type and owner, including helpers, brims and interfaces.
        local = data[np.all((data[:, :3]>=lo) & (data[:, :3]<=hi), axis=1)]
        seen, worst, conflicts = 0, {}, []
        for i, shape in enumerate(tested):
            r = paths.inspect_region(shape, local[:,:3], local[:,3], local[:,4],
                                     local[:,5].astype(int), labels, to_local, limit=1)
            seen = max(seen, r['checked_samples'])
            if r['violations']:
                conflicts.append(i)
                for feature,count in r['violations'].items():
                    worst[feature] = max(worst.get(feature,0), count)
        result['routes'][name] = dict(poses=len(tested), nearby_samples=len(local), checked=seen,
                                      worst_per_feature=worst, obstructed_poses=conflicts)
    for key in KEYS:
        assert result['routes'][f'key_{key}_mount_opening']['nearby_samples'] > 25
    result['clear'] = all(not row['obstructed_poses'] for row in result['routes'].values())
    output.write_text(json.dumps(result, indent=2)+'\n')
    for key in KEYS:
        for n in ('mount_opening', 'switch', 'socket'):
            print(key,n,result['routes'][f'key_{key}_{n}']['worst_per_feature'],flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('archive',type=Path)
    p.add_argument('frame',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--seated-only',action='store_true')
    args = p.parse_args()
    inspect(args.archive,args.frame,args.output,args.seated_only)
