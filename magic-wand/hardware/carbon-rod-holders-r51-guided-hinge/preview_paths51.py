"""Render two views of the actual selected carrier and support G-code beads."""
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from support51 import q
from printed_props51 import native_mask


def font(size):
    try:
        return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',size)
    except OSError:
        return ImageFont.load_default(size=size)


def projection(points, features, azimuth, elevation, width, height):
    th,ph=np.radians([azimuth,elevation])
    right=np.array([np.cos(th),np.sin(th),0.])
    up=np.array([-np.sin(th)*np.sin(ph),np.cos(th)*np.sin(ph),np.cos(ph)])
    eye=np.cross(right,up)
    flat=np.column_stack([points@right,points@up])
    scale=min((width-45)/max(np.ptp(flat[:,0]),.1),(height-45)/max(np.ptp(flat[:,1]),.1))
    bounds=(flat.max(0)+flat.min(0))/2
    flat=(flat-bounds)*np.array([scale,-scale])+[width/2,height/2]
    x,y=np.rint(flat).astype(np.int32).T
    depth=points@eye
    zbuf=np.full((height,width),-np.inf,dtype='float32')
    colors=np.array([[191,68,66],[80,168,180],[194,173,135]],dtype='uint8')
    tint=np.clip(.8+.28*(depth-depth.min())/max(np.ptp(depth),1),0,1.2)
    rgb=(colors[features]*tint[:,None]).astype('uint8')
    idx=np.argsort(depth)
    canvas=np.full((height,width,3),250,dtype='uint8')
    # Actual paths sampled at 0.15. A short screen-space expansion closes
    # sample spacing only; the numerical measurements use the true widths.
    radius=max(1,round(.16*scale))
    for dx in range(-radius,radius+1):
        for dy in range(-radius,radius+1):
            if dx*dx+dy*dy>radius*radius:continue
            yy=y[idx]+dy;xx=x[idx]+dx
            front=depth[idx]>=zbuf[yy,xx]
            yy=yy[front];xx=xx[front];ii=idx[front]
            zbuf[yy,xx]=depth[ii]
            canvas[yy,xx]=rgb[ii]
    return Image.fromarray(canvas)


def make(archive,output,trial=False):
    with ZipFile(archive) as z:
        text=z.read('Metadata/plate_1.gcode').decode()
        plate=ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
        owner=int(plate.find("object[@name='Key_Carrier']").get('identify_id'))
        extra=plate.find("object[@name='External_peel_support']")
        prop_owner=int(extra.get('identify_id')) if extra is not None else None
    data,labels,_=q.extrusion_points(text,.15)
    feature=np.array(labels)[data[:,5].astype(int)]
    keep=(data[:,6]==owner)&~np.char.startswith(feature,'Support')&~np.char.startswith(feature,'Brim')&~np.char.startswith(feature,'Skirt')&(feature!='Prime tower')
    lo,hi=data[keep,:2].min(0)-9,data[keep,:2].max(0)+9
    nearby=np.all((data[:,:2]>lo)&(data[:,:2]<hi),axis=1)
    supp=np.char.startswith(feature,'Support')&nearby
    if prop_owner is not None:supp|=(data[:,6]==prop_owner)&~np.char.startswith(feature,'Brim')&~np.char.startswith(feature,'Skirt')
    brim=np.char.startswith(feature,'Brim')&nearby
    permanent_ids=np.flatnonzero(~(np.char.startswith(np.array(labels),'Support')|np.char.startswith(np.array(labels),'Skirt')|np.char.startswith(np.array(labels),'Brim')|(np.array(labels)=='Prime tower')))
    peels,_=native_mask(archive,q,data,owner,permanent_ids)
    keep&=~peels;supp|=peels
    sel=keep|supp|brim
    xyz=data[sel,:3].astype(float);xyz[:,2]=data[sel,7]-.5*data[sel,4]
    cat=np.select([supp[sel],brim[sel]],[1,2],default=0)
    W,H=1380,740
    img=Image.new('RGB',(W,H),(250,250,250))
    for i,azimuth in enumerate((18,180+30)):
        img.paste(projection(xyz,cat,azimuth,13,680,546),(i*690,92))
    dr=ImageDraw.Draw(img)
    dr.text((30,22),'R51 key holder • sliced at 0.20 mm',font=font(33),fill=(32,35,38))
    dr.text((30,65),'Native Bambu Studio paths',font=font(17),fill=(73,81,84))
    for i,title in enumerate(('Front of the print','Opposite face')):
        dr.text((30+i*690,635),title,font=font(21),fill=(45,49,53))
    for x,color,name in ((30,(191,68,66),'Key holder'),(216,(80,168,180),'Removable support'),(535,(194,173,135),'Bed brim')):
        dr.ellipse((x,696,x+16,712),fill=color)
        dr.text((x+24,693),name,font=font(18),fill=(54,58,60))
    if trial:dr.text((980,695),'Comparison slice',font=font(17),fill=(73,81,84))
    img.save(output,optimize=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('output',type=Path);p.add_argument('--trial',action='store_true')
    a=p.parse_args();make(a.archive,a.output,a.trial)
