"""Draw the actual first-layer accessory geometry and the two large-base cuts per part."""
from pathlib import Path
import json
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from wide_accessories52 import POSITIONS, MODEL, decode, tag

NAMES={'Battery_End_Door':'Sliding battery lid','DFR0030_Post_Clip':'DFRobot clip 1',
       'DFR0030_Post_Clip_2':'DFRobot clip 2','XIAO_Rod_Holder':'XIAO holder',
       'XIAO_Near_Keeper':'XIAO keeper','Cable_Clip_12_Wire':'Cable clip'}


def draw(directory):
    with ZipFile(directory/'layout.3mf') as z: model=ET.fromstring(z.read(MODEL))
    data=json.loads((directory/'base-cuts.json').read_text())
    image=Image.new('RGB',(960,850),'#f7f5ef')
    ink=ImageDraw.Draw(image)
    title=ImageFont.load_default(size=24); label=ImageFont.load_default(size=19)
    ink.text((24,14),'Six separate parts · cut the red marks',font=title,fill='#22262f')
    ink.text((25,47),'Purple = wide plates     Gold = original tear-off feet     Blue = part to keep',font=label,fill='#39404b')
    for index,name in enumerate(POSITIONS):
        row,col=divmod(index,2); rec=data[name]
        x0=col*478+10;y0=(2-row)*257+85
        ink.text((x0+12,y0+3),NAMES[name],font=label,fill='#1c2430')
        def mesh(ident):return decode(model.find(f"{tag('resources')}/{tag('object')}[@id='{ident}']"))
        groups=[(rec['wing_id'],'#9a85ca'),*((i,'#dfae53') for i in rec['old_part_ids'][1:]),(rec['permanent_id'],'#32728b')]
        shapes=[(mesh(ident).slice(.1).to_polygons(),color) for ident,color in groups]
        points=np.concatenate([contour for contours,_ in shapes for contour in contours])
        low,high=points.min(axis=0),points.max(axis=0)
        center=(low+high)/2
        scale=min(438/(high[0]-low[0]),194/(high[1]-low[1]))
        def project(points):
            xy=(np.asarray(points)-center)*scale
            return [(round(x0+230+x),round(y0+140-y)) for x,y in xy]
        for contours,color in shapes:
            for contour in contours:
                area=np.sum(contour[:,0]*np.roll(contour[:,1],-1)-np.roll(contour[:,0],-1)*contour[:,1])
                ink.polygon(project(contour),fill=color if area>0 else '#f7f5ef')
        for cut in rec['cuts']:
            axis=cut['axis'];origin=np.array(cut['local_xy']);delta=np.zeros(2);delta[1-axis]=1.9
            ink.line(project([origin-delta,origin+delta]),fill='#a91738',width=4)
    image.save(directory/'wide-base-cuts.png',optimize=True)


if __name__=='__main__':draw(Path(sys.argv[1]))
