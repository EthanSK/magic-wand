"""Find unsupported starts and long unbacked runs in the support-free production slice."""
import argparse
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'carbon-rod-holders-r52-snap-seat'))
from parts52 import digest
from support51 import q, GRID, footprint, dilation, lost_islands, roofs51


def inspect(archive):
    with ZipFile(archive) as z:
        text = z.read('Metadata/plate_1.gcode').decode()
        plate = ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
        config = json.loads(z.read('Metadata/project_settings.config'))
    owners = {row.get('name'):int(row.get('identify_id')) for row in plate.findall('object')}
    assert not re.search(r'^; FEATURE: Support', text, flags=re.MULTILINE)
    # Remove only feature tags, retaining every motion instruction and the original
    # line numbers for the path ordering. The tower has a separate root audit.
    model_only = re.sub(r'^; FEATURE: (Prime tower|Skirt|Brim)$','; FEATURE: Custom',text,flags=re.MULTILINE)
    pts, names, count = q.extrusion_points(model_only,.12)
    lines, sequences, *_ = roofs51.map_moves(q, model_only,len(pts),step=.12)
    pts[:, :2] += np.fromstring(config['extruder_offset'][0], sep='x')
    reports = {}
    for name,owner in owners.items():
        ids = np.arange(len(pts)) if len(owners)==1 else np.flatnonzero(pts[:,6]==owner)
        own = pts[ids]
        origin = np.floor(own[:, :2].min(axis=0))-1
        shape = tuple(np.ceil((own[:, :2].max(axis=0)-origin+1) / GRID).astype(int)[::-1])
        upper = np.rint(own[:,7]*5).astype(int)
        assert np.allclose(upper,own[:,7]*5,atol=.001), 'Unexpected layer height'
        assert np.all(upper[:-1]<=upper[1:]) and upper[0]==1
        ungrounded, spans = [], []
        boundaries = np.r_[0,np.flatnonzero(upper[1:]!=upper[:-1])+1,len(upper)]
        empty = np.zeros(shape,bool)
        previous = empty
        for a,b in zip(boundaries,boundaries[1:]):
            z = int(upper[a])
            material = footprint(own[a:b],origin,shape)
            if z>1:
                for item in lost_islands(material, dilation(previous), origin):
                    ungrounded.append(dict(layer=z, **item))
                spans.extend(roofs51.inspect(z,own[a:b],origin,GRID,dilation(previous,2),
                                             empty,empty,lines[ids[a:b]],sequences[ids[a:b]]))
            previous = material
        reports[name] = dict(layers=int(upper[-1]), samples=len(own),
                             completely_unsupported_starts=ungrounded,
                             runs_requiring_review=spans)
    return dict(archive_sha256=digest(archive), layer_mm=.2, grid_mm=GRID,
                native_support_moves=count['support_extruding_moves'], parts=reports)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive',type=Path)
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    result = inspect(args.archive)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    for name,row in result['parts'].items():
        print(name,row['layers'],len(row['completely_unsupported_starts']),len(row['runs_requiring_review']))
