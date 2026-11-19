"""Give the six separate accessory parts the twin, two-layer base geometry of the R48 retry."""
import json
from pathlib import Path
from tower52 import add_tower_base
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import manifold3d as mf
import numpy as np
from shapely.geometry import LineString, Polygon
from plate52 import MODEL, SETTINGS, PROJECT, decode, resource, tag, value

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE/'exports/print-accessories/Clips-and-holders.3mf'
# Bed centres, outside plate dimensions and axis of the two cut ties.
POSITIONS = {
    'DFR0030_Post_Clip': ((29,38), (50,66), 0),
    'DFR0030_Post_Clip_2': ((151,38), (50,66), 0),
    'Battery_End_Door': ((46,100), (84,48), 1),
    'XIAO_Near_Keeper': ((134,100), (84,48), 0),
    'XIAO_Rod_Holder': ((46,152), (84,48), 0),
    'Cable_Clip_12_Wire': ((134,152), (84,48), 1),
}


def polygon(section):
    result = Polygon()
    for loop in section.to_polygons():
        result = result.symmetric_difference(Polygon(loop))
    return result


def rectangle(lo, hi):
    return mf.CrossSection.square(tuple(np.asarray(hi)-lo)).translate(tuple(lo))


def ties_to_wings(original, anchor, axis, footprint_centre, area, protected):
    other = 1-axis
    available = polygon(anchor.slice(.1) ^ anchor.slice(.3))
    bb = np.array(available.bounds).reshape(2,2)
    # Land both edges of the cut tie in the existing pad at both printed layers.
    half_width = .9
    stations = np.arange(bb[0,other]+half_width+.08, bb[1,other]-half_width, .20)
    ties = []
    measures = []
    for sign in (-1,1):
        best = None
        for station in stations:
            tips = []
            for offset in (-half_width,0,half_width):
                points = np.zeros((2,2))
                points[:,axis] = [-200,200]
                points[:,other] = station+offset
                hit = available.intersection(LineString(points))
                if hit.is_empty: break
                tips.append(hit.bounds[axis + (2 if sign>0 else 0)])
            if len(tips)!=3:continue
            tip = min(tips) if sign>0 else max(tips)
            score = sign*tip - .001*abs(station-footprint_centre[other])
            if best is None or score>best[0]:best = (score,tip,station)
        assert best is not None
        _, tip, station = best
        coords = np.zeros((2,2))
        coords[:,axis] = [tip-sign*.60, original.bounding_box()[axis+(3 if sign>0 else 0)]+sign*2.6]
        coords[:,other] = [station-half_width,station+half_width]
        neck = rectangle(coords.min(0), coords.max(0)).extrude(.4)
        cut_at = [0.,0.]
        cut_at[axis],cut_at[other] = tip+sign*.35,station
        if protected is not None:
            assert (neck ^ protected).volume()<.00001, 'Additional tie crossed the permanent part'
        assert (neck ^ anchor).volume()>.09 and (neck ^ area).volume()>.07
        ties.append(neck)
        measures.append(dict(local_xy=cut_at,axis=axis,sign=sign))
    return mf.Manifold.batch_boolean(ties,mf.OpType.Add),measures


def build(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with ZipFile(ORIGINAL) as z:
        files={k:z.read(k) for k in z.namelist()}
    model=ET.fromstring(files[MODEL]); ET.register_namespace('',model.tag[1:].split('}')[0])
    cfg=ET.fromstring(files[SETTINGS]);res=model.find(tag('resources'));build_items=model.find(tag('build'))
    plate=cfg.find('plate'); ranges=ET.fromstring(files['Metadata/layer_config_ranges.xml'])
    owners={o.get('id'):o for o in cfg.findall('object')}
    input_indices={};items={}
    for old_index,item in enumerate(list(build_items),1):
        oid=item.get('objectid');owner=owners[oid]
        name=owner.find("metadata[@key='name']").get('value')
        compound=res.find(f"{tag('object')}[@id='{oid}']")
        get=lambda ident:res.find(f"{tag('object')}[@id='{ident}']")
        parts=[get(p.get('id')) for p in owner.findall('part')]
        if name=='Battery_Holder':
            build_items.remove(item);cfg.remove(owner);res.remove(compound)
            for p in parts: res.remove(p)
            for inst in plate.findall('model_instance'):
                if inst.find("metadata[@key='object_id']").get('value')==oid:plate.remove(inst)
            continue
        input_indices[old_index]=len(items)+1
        bed,size,axis=POSITIONS[name]; bed=np.array(bed);size=np.array(size)
        solids=[decode(p) for p in parts]
        original=mf.Manifold.batch_boolean(solids,mf.OpType.Add)
        bounds=np.array(original.bounding_box()).reshape(2,3)
        centre=bounds[:,:2].mean(0); tr=bed-centre
        outer=rectangle(centre-size/2,centre+size/2).offset(-1.8).offset(1.8)
        hull=original.project().hull().offset(1.45)
        split_lo,split_hi=centre-size/2-1,centre+size/2+1
        split_lo[axis],split_hi[axis]=centre[axis]-.8,centre[axis]+.8
        wings=(outer-hull-rectangle(split_lo,split_hi)).extrude(.4)
        assert len(wings.decompose())==2
        # On already-footed pieces the new plate joins the old removable feet.
        # The lid and keeper have two short cuts at their outermost lands.
        anchor=solids[-1]
        links,cuts=ties_to_wings(original,anchor,axis,centre,wings,solids[0] if len(solids)>1 else None)
        wide=wings+links
        assert len(wide.decompose())==2 and (wings^original).volume()<1e-6
        new_id=3000+old_index
        resource(res,tag,new_id,'Cut away both wide base plates',wide)
        ET.SubElement(compound.find(tag('components')),tag('component'),objectid=str(new_id))
        value(ET.SubElement(owner,'part',id=str(new_id),subtype='normal_part'),'name','Cut away both wide base plates')
        value(owner,'brim_type','no_brim')
        tf=item.get('transform').split();assert list(map(float,tf[:9]))==[1,0,0,0,1,0,0,0,1]
        previous=list(map(float,tf[9:11]));tf[9:11]=[str(x) for x in tr]
        item.set('transform',' '.join(tf))
        items[name]=dict(permanent_id=int(parts[0].get('id')),old_part_ids=[int(p.get('id')) for p in parts],
                         wing_id=new_id,translation=tr.tolist(),original_translation=previous,cuts=cuts,
                         wing_areas_mm2=[round(piece.slice(.1).area(),2) for piece in wide.decompose()])
    for row in list(ranges):
        old_idx=int(row.get('id'))
        if old_idx in input_indices:row.set('id',str(input_indices[old_idx]))
        else:ranges.remove(row)
    add_tower_base(files, (85, 31))
    value(plate,'plater_name','Six accessories with separate wide bases')
    for key,root in ((MODEL,model),(SETTINGS,cfg),('Metadata/layer_config_ranges.xml',ranges)):
        files[key]=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with ZipFile(directory/'layout.3mf','w',ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)
    (directory/'base-cuts.json').write_text(json.dumps(items,indent=2)+'\n')
    print({name:record['wing_areas_mm2'] for name,record in items.items()},flush=True)


if __name__=='__main__':build(Path(sys.argv[1]))
