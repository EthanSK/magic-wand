"""Show which independently printed parts to keep and which bed material peels away."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'carbon-rod-holders-r52-snap-seat'))
from native_layout53 import load_solid, mesh_path
from support51 import footprint, q, GRID

PAPER = '#faf8f4'
INK = '#15272d'
PLASTIC = '#a83d32'
BRIM = '#e8c2b1'
TOWER = '#77888b'


def font(size):
    try:
        return ImageFont.truetype('Arial.ttf',size)
    except OSError:
        return ImageFont.load_default(size=size)


def generate(archive, frame_file, mesh_dir, titles, out):
    with ZipFile(archive) as z:
        settings=json.loads(z.read('Metadata/project_settings.config'))
        info=ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
        owners={row.get('name'):int(row.get('identify_id')) for row in info.findall('object')}
        gcode=z.read('Metadata/plate_1.gcode').decode()
    frames=json.loads(frame_file.read_text())['parts']
    assert set(owners)==set(frames)
    pts,names,_=q.extrusion_points('; CHANGE_LAYER'.join(gcode.split('; CHANGE_LAYER',2)[:2]),GRID)
    pts[:,:2]+=np.fromstring(settings['extruder_offset'][0],sep='x')
    img=Image.new('RGB',(1224,850),PAPER)
    draw=ImageDraw.Draw(img)
    draw.text((32,18),'OP1 holder and hinge',font=font(32),fill=INK)
    draw.rectangle((32,85,752,805),fill='#f3f0ea',outline='#9da8a7',width=2)
    scale=4
    def xy(p):
        return (32+p[0]*scale,805-p[1]*scale)
    for i,(name,owner) in enumerate([*owners.items(),('wipe_tower',None)],1):
        if owner is None:
            data=pts[pts[:,5]==names.index('Prime tower')]
        else:
            is_part=pts[:,5]!=names.index('Prime tower')
            data=pts[is_part] if len(owners)==1 else pts[is_part & (pts[:,6]==owner)]
        shape=(1804,1804)
        mask=footprint(data,[-.2,-.2],shape)[2:-2,2:-2]
        mask=Image.fromarray((mask[::-1]*255).astype(np.uint8)).resize((720,720),Image.Resampling.BOX)
        img.paste(TOWER if owner is None else BRIM,(32,85,752,805),mask)
        if owner is None:
            pos=(data[:,:2].min(0)+data[:,:2].max(0))/2
            title='Timelapse tower'
        else:
            entry=frames[name]
            body=load_solid(mesh_path(entry['source'],mesh_dir)).transform(np.array(entry['assembly_to_machine'])[:3])
            pos=(np.array(body.bounding_box())[:2]+np.array(body.bounding_box())[3:5])/2
            silhouette=Image.new('L',img.size)
            pen=ImageDraw.Draw(silhouette)
            polys=body.project().to_polygons()
            def signed(p):
                return float((p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)).sum())
            for p in sorted(polys,key=lambda p:-abs(signed(p))):
                pen.polygon([xy(pt) for pt in p],fill=255 if signed(p)>0 else 0)
            img.paste(PLASTIC,(0,0,img.width,img.height),silhouette)
            title=titles.get(name,name.replace('_',' '))
        cx,cy=xy(pos)
        if owner is not None and body.project().area() < 170:
            # Leave the silhouette visible even when the actual clip is shorter
            # than its label. Put the number on its own wide, disposable brim.
            right = pos[0] < 150
            end_x = 32 + (body.bounding_box()[3 if right else 0])*scale
            label_x = end_x + (21 if right else -21)
            draw.line((end_x,cy,label_x,cy),fill=INK,width=2)
            cx=label_x
        draw.ellipse((cx-12,cy-12,cx+12,cy+12),fill=INK)
        draw.text((cx,cy),str(i),anchor='mm',font=font(16),fill='white')
        y=112+(i-1)*62
        draw.text((785,y),str(i),font=font(23),fill=INK)
        draw.text((826,y),title,font=font(22),fill=INK)
        if owner is None:draw.text((827,y+25),'Discard after printing',font=font(17),fill='#405253')
    draw.text((32,813),'Front edge of the tray',fill=INK,font=font(19))
    draw.rectangle((785,741,810,761),fill=PLASTIC)
    draw.text((827,740),'Keep these parts',fill=INK,font=font(19))
    draw.rectangle((785,779,810,799),fill=BRIM)
    draw.text((827,777),'Peel away the thin outer base',fill=INK,font=font(19))
    img.save(out)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('archive','frames','meshes','names','out'):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    generate(a.archive,a.frames,a.meshes,json.loads(a.names.read_text()),a.out)
