"""Render the actual hinge and battery lid meshes at their assembly poses."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build51
from guide51 import OUT, matrix

sys.path.insert(0,str(next(OUT.parent.parent.glob('carbon-rod-holders-r46-*'))))
from compare46 import render, triangles


def scene(module, pose, names):
    items=[]
    for name in names:
        actor=module['actors'][name]
        color=tuple(bytes.fromhex(actor['color'][1:]))
        items.append((triangles(OUT/actor['file'],matrix(pose[name])),color))
    return items


def main():
    guide=json.loads((OUT/'assembly-guide.json').read_text())['modules']
    hinge=guide['pin_hinge']
    pivot=json.loads((OUT/'dimensions.json').read_text())['axis_world_xyz_mm']
    lid=guide['battery_latch']
    size=(530,380)
    checks=[('Touchpad hinge',hinge,hinge['steps'][3]['samples'][-1],hinge['actors'],(.55,.58,1.),17.,pivot),
            ('Sliding battery lid',lid,lid['steps'][0]['samples'][-1],['door'],(.20,-.15,1.),11.,(0.,0.,11.))]
    output=Image.new('RGB',(2*size[0],size[1]+44),'#202327')
    drawing=ImageDraw.Draw(output)
    font=ImageFont.load_default(size=23)
    for i,(label,module,pose,keys,direction,scale,centre) in enumerate(checks):
        output.paste(render(scene(module,pose,keys),direction,scale,size,centre),(i*size[0],44))
        drawing.text((i*size[0]+18,8),label,font=font,fill='white')
    output.save(OUT/'R51-hinge-and-lid.png')


if __name__=='__main__':
    main()
