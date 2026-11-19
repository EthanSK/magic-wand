"""Verify both layers of every accessory base on the selected Bambu machine paths."""
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
import shapely
from parts52 import audit
from plate52 import MODEL, PROJECT, decode, tag
from orient51 import digest
from support51 import q, footprint, lost_islands
from wide_accessories52 import HERE, ORIGINAL, POSITIONS, polygon


def check(directory):
    layout=directory/'layout.3mf'; native=directory/'Wide-accessories.gcode.3mf'
    receipts=json.loads((directory/'base-cuts.json').read_text())
    with ZipFile(native) as z:
        text=z.read('Metadata/plate_1.gcode').decode()
        info=ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
        boxes=json.loads(z.read('Metadata/plate_1.json'))['bbox_objects']
        cfg=json.loads(z.read(PROJECT))
    owners={x.get('name'):int(x.get('identify_id')) for x in info.findall('object')}
    assert set(owners)==set(receipts)==set(POSITIONS)
    points,labels,_=q.extrusion_points(text,.12)
    points[:,:2]+=np.fromstring(cfg['extruder_offset'][0],sep='x')
    with ZipFile(layout) as z, ZipFile(ORIGINAL) as old:
        model=ET.fromstring(z.read(MODEL)); previous=ET.fromstring(old.read(MODEL))
    resources=model.find(tag('resources'))
    report={}
    minimum_edge=180
    tower=np.array(next(row['bbox'] for row in boxes if row['name']=='wipe_tower')).reshape(2,2)
    minimum_tower=180
    for name,owner in owners.items():
        rec=receipts[name]; tr=np.array(rec['translation'])
        for ident in rec['old_part_ids']:
            path=f"{tag('resources')}/{tag('object')}[@id='{ident}']/{tag('mesh')}"
            assert ET.tostring(model.find(path))==ET.tostring(previous.find(path)),name
        permanent=decode(resources.find(f"{tag('object')}[@id='{rec['permanent_id']}']"))
        layers=[]
        for layer in (1,2):
            z=layer*.2
            p=points[(points[:,6]==owner)&np.isclose(points[:,7],z)]
            assert len(p)>0,name
            lo,hi=p[:,:2].min(0)-.5,p[:,:2].max(0)+.5
            minimum_edge=min(minimum_edge,float(np.min(np.minimum(lo,180-hi))))
            origin=np.floor(lo)-1;shape=tuple((np.ceil((hi-origin+1)/.1)[::-1]).astype(int))
            mask=footprint(p,origin,shape)
            region=polygon(permanent.slice(z-.1)).buffer(-.06)
            core=shapely.contains_xy(region,p[:,0]-tr[0],p[:,1]-tr[1])
            seed=footprint(p[core],origin,shape)
            unrooted=lost_islands(mask,seed,origin)
            assert not unrooted,(name,layer,'disconnected base',unrooted)
            widths=[];cuts=mask.copy()
            for cut in rec['cuts']:
                xy=np.rint((np.asarray(cut['local_xy'])+tr-origin)/.1).astype(int)
                axis=cut['axis'];x,y=xy
                window=mask[y-16:y+17,x] if axis==0 else mask[y,x-16:x+17]
                widths.append(round(float(window.sum())*.1,2))
                if axis==0:cuts[y-16:y+17,x-1:x+2]=False
                else:cuts[y-1:y+2,x-16:x+17]=False
            separated=sorted((k['area_mm2'] for k in lost_islands(cuts,seed,origin)),reverse=True)
            assert min(widths)>=1.2 and len(separated)>=2 and min(separated[:2])>1100,(name,widths,separated)
            area=round(float(mask.sum())*.01,2)
            assert area>=2800,(name,area)
            # Test actual deposited bead distance to the tower rectangle, also across the front notches.
            delta=np.maximum(0,np.maximum(tower[0]-p[:,:2],p[:,:2]-tower[1]))
            gap=float((np.linalg.norm(delta,axis=1)-p[:,3]*.5-.07).min())
            minimum_tower=min(minimum_tower,gap)
            layers.append(dict(layer=layer,connected_material_mm2=area,unconnected_material=unrooted,
                tie_widths_mm=widths,detachable_wing_areas_after_two_cuts_mm2=separated[:2]))
        report[name]=layers
    assert minimum_edge>=3 and minimum_tower>=3,(minimum_edge,minimum_tower)
    # Translate the twelve windows measured on the preceding native slice.
    old_lid=json.loads((ORIGINAL.parent/'lid-openings.json').read_text())
    lid=receipts['Battery_End_Door']; shift=np.subtract(lid['translation'],lid['original_translation'])
    clear=[]
    for opening in old_lid['windows']:
        centre=np.array(opening['print_xy'])+shift
        by_layer=[]
        for z in old_lid['layer_tops_mm']:
            p=points[np.isclose(points[:,7],z)]
            by_layer.append(float((np.linalg.norm(p[:,:2]-centre,axis=1)-p[:,3]/2-.07).min()))
        clear.append(round(min(by_layer),3))
    assert len(clear)==12 and min(clear)>.30,clear
    result=dict(native_sha256=digest(native),layout_sha256=digest(layout),parts=report,
                minimum_bed_edge_mm=round(minimum_edge,2),minimum_tower_gap_mm=round(minimum_tower,2),
                lid_window_minimum_clear_radii_mm=clear,
                permanent_meshes_and_original_pad_meshes_unchanged=True,
                native_seconds=int(info.find("metadata[@key='prediction']").get('value')),
                grams=float(info.find("metadata[@key='weight']").get('value')))
    (directory/'wide-bases.json').write_text(json.dumps(result,indent=2)+'\n')
    audit(native,layout,directory/'separation-and-machine.json',set(owners))
    print({name:layers[0]['connected_material_mm2'] for name,layers in report.items()},flush=True)


if __name__=='__main__':check(Path(sys.argv[1]))
