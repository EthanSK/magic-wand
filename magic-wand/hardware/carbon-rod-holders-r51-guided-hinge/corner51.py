"""Read the actual 31.2-mm subsection across adjacent layers to classify its small bead."""
import json
import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import numpy as np
from shapely import LineString, Point, union_all

from support51 import q
from orient51 import digest
from roofs51 import map_moves


def find(archive):
    with ZipFile(archive) as z:
        text=z.read('Metadata/plate_1.gcode').decode()
        plate=ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
        carrier=int(plate.find("object[@name='Key_Carrier']").get('identify_id'))
        settings=json.loads(z.read('Metadata/project_settings.config'))
    # On these Bambu jobs layer changes precede fresh fully positioned travels.
    lo=text.index('; Z_HEIGHT: 30.8\n')
    hi=text.index('; Z_HEIGHT: 31.8\n',lo)
    snippet='G90\nM83\n; LINE_WIDTH: 0.34\n; LAYER_HEIGHT: 0.2\n'+text[lo:hi]
    d,features,_=q.extrusion_points(snippet,.025)
    lines,seq,*_=map_moves(q,snippet,len(d),step=.025)
    d[:,:2]+=np.fromstring(settings['extruder_offset'][0],sep='x')
    labels=np.asarray(features)[d[:,5].astype(int)]
    mask=(d[:,6]==carrier)&(np.linalg.norm(d[:,:2]-[39.92,88.59],axis=1)<3.)
    rows={}
    for h in [30.8,31.,31.2,31.4,31.6]:
        paths=[]
        sel=mask & (abs(d[:,7]-h)<.001)
        for s in np.unique(seq[sel]):
            m=sel & (seq==s)
            segments=[]
            # Individually padded native lines retain variable Arachne widths.
            for l in np.unique(lines[m]):
                f=m & (lines==l)
                points=d[f,:2]
                shp=LineString(points) if len(points)>1 else Point(*points[0])
                segments.append(shp.buffer(float(np.median(d[f,3]))/2,quad_segs=24))
            row=dict(seq=int(s),sh=union_all(segments),feature=','.join(np.unique(labels[m])))
            paths.append(row)
        rows[h]=paths
    tiny=[r for r in rows[31.2] if r['sh'].distance(Point(39.92,88.59))<.14]
    assert tiny
    target=min(tiny,key=lambda r:r['sh'].area)
    other=[r['sh'] for r in rows[31.2] if r is not target]
    record=dict(sha256=digest(archive),feature=target['feature'],area_mm2=round(target['sh'].area,4),
        observed_bounds=[round(v,4) for v in target['sh'].bounds],distances_to_other_material_mm={},
        model_overlap_mm2={},distance_on_same_layer_mm=round(target['sh'].distance(union_all(other)),4))
    for h,v in rows.items():
        if h==31.2:continue
        sh=union_all([r['sh'] for r in v])
        record['distances_to_other_material_mm'][str(h)]=round(sh.distance(target['sh']),4)
        record['model_overlap_mm2'][str(h)]=round(sh.intersection(target['sh']).area,4)
    return record


if __name__=='__main__':
    p=Path(sys.argv[1]); obj=find(p)
    (p.parent/'corner.json').write_text(json.dumps(obj,indent=2)+'\n')
    print(obj)
