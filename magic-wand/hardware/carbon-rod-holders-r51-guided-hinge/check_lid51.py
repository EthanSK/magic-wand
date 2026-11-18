"""Find a clear opening through all four sliced layers of each new lid window."""
import hashlib
import json
from pathlib import Path

import build48
import audit45
from lid51 import HERE, openings, np, trimesh


def check(archive, report=None):
    out = HERE / 'exports'
    checker = audit45.common.load_checker().audit
    data, features, _, _, offset, parts, _, _ = checker.read_project(archive)
    centre_frame = np.linalg.inv(json.loads((out/'lid-checks.json').read_text())['print_to_assembly'])
    ref = trimesh.load_mesh(out/'Battery_End_Door-print.stl')
    native = parts['Battery_End_Door']['vertices']
    translation = native.min(0) - ref.bounds[0]
    assert np.allclose(native.max(0),ref.bounds[1]+translation,atol=.002)
    centres = []
    for leaf in openings().decompose():
        lo_x,lo_y,hi_x,hi_y = leaf.bounds()
        local = [(.5*(lo_x+hi_x)),(.5*(lo_y+hi_y)),11.35,1.]
        xy = (centre_frame @ local)[:2] + translation[:2]
        clear = []
        for height in (.2,.4,.6,.8):
            layer = data[np.isclose(data[:,2],height)]
            # The native sampler records centres at <= STEP apart. Bound the
            # worst gap between samples conservatively for all extruding paths.
            dist = np.linalg.norm(layer[:,:2]+offset[:2]-xy,axis=1) - layer[:,3]*.5 - checker.STEP*.5
            clear.append(round(float(dist.min()),3))
        assert min(clear)>.30,(xy,clear)
        centres.append(dict(print_xy=xy.tolist(),clear_radius_by_layer_mm=clear))
    assert len(centres)==12
    result = dict(native_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  opening_count=len(centres), layer_tops_mm=[.2,.4,.6,.8],
                  minimum_clear_radius_mm=min(min(c['clear_radius_by_layer_mm']) for c in centres), windows=centres)
    (report or out/'lid-slice-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['minimum_clear_radius_mm'])


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    check(args.archive,args.report)
