#!/usr/bin/env python3
"""Draw comparison images directly from the delivered CAD triangles.

Orthographic shaded CAD drawings, not photographs or strength simulations.
Requires numpy and Pillow; source meshes remain the sole model definition.
"""
from pathlib import Path
import argparse,json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent

def font(size):
    for path in ['/System/Library/Fonts/Supplemental/Arial.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(path).exists():return ImageFont.truetype(path,size)
    return ImageFont.load_default()

def draw_model(image,parts,center,scale,zcenter,color,clip=None):
    d=ImageDraw.Draw(image);yaw=.38
    horizontal=np.array([math.cos(yaw),math.sin(yaw),0.]);depth=np.array([-math.sin(yaw),math.cos(yaw),0.])
    polygons=[];light=np.array([-.3,-.6,.74]);light/=np.linalg.norm(light)
    for p in parts:
        verts=np.asarray(p['assembly_vertices']);faces=np.asarray(p['assembly_faces']);tri=verts[faces]
        if clip is not None:tri=tri[(tri[:,:,2].max(axis=1)>=clip[0])&(tri[:,:,2].min(axis=1)<=clip[1])]
        normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
        strength=.5+.5*np.maximum(0.,normals@light)
        screen=np.stack([center[0]+(tri@horizontal)*scale,center[1]-(tri[:,:,2]-zcenter)*scale],axis=2)
        for z,q,b in zip((tri@depth).mean(axis=1),screen,strength):polygons.append((z,q,tuple(int(c*b)for c in color)))
    for _,q,c in sorted(polygons,key=lambda x:x[0],reverse=True):d.polygon([tuple(p)for p in q],fill=c)

def build(exports,out):
    out.mkdir(parents=True,exist_ok=True)
    m=json.loads((exports/'manifest.json').read_text());old=json.loads((HERE.parent/'shard-tube-r2/exports/manifest.json').read_text())
    baseline=[p for p in old['parts']if p['name']in ['Grip_Left','Battery_Screw_Cap_Light','Continuous_Shaft','Sense_Open_Cradle']]
    variants=[(key,[p for p in value['parts']if p['name']in ['Lower_Body','Upper_Body_With_Sensor_Fork']])for key,value in m['variants'].items()]
    options=[('Previous Shard R2',baseline,(145,162,171),'Battery and switch fittings inside'),('8 mm → 5.8 mm',variants[0][1],(38,158,185),'Matches first tube width at the base'),('10 mm → 7.8 mm',variants[1][1],(38,161,126),'Slightly thicker comparison')]
    im=Image.new('RGB',(1600,1440),(242,246,248));d=ImageDraw.Draw(im)
    d.text((65,35),'Thinner tapered wand prototypes',font=font(42),fill=(27,45,56))
    d.text((65,94),'410 mm overall · Actual exported CAD · Same XIAO board position',font=font(24),fill=(69,88,99))
    for i,(name,parts,color,note)in enumerate(options):
        x=290+i*510
        draw_model(im,parts,(x,738),2.55,205.,color)
        d.text((x-185,130),name,font=font(31),fill=(27,45,56))
        d.text((x-225,1310),note,font=font(20),fill=(62,84,96))
        if i:d.text((x-225,1342),'External buttons, battery and wires',font=font(20),fill=(62,84,96))
    d.line((57,215,57,1260),fill=(78,98,108),width=2);d.line((48,215,66,215),fill=(78,98,108),width=2);d.line((48,1260,66,1260),fill=(78,98,108),width=2)
    d.text((75,710),'410 mm',font=font(21),fill=(54,73,85))
    d.text((65,1395),'Unprinted experiments. Thin printed PETG is not proven equivalent to the original carbon-fibre tube.',font=font(21),fill=(124,78,39))
    im.save(out/'comparison.png')
    im=Image.new('RGB',(1500,1120),(242,246,248));d=ImageDraw.Draw(im)
    d.text((55,35),'Sensor holder: old joint versus integral fork',font=font(36),fill=(27,45,56))
    oldtop=[p for p in baseline if p['name']in ['Continuous_Shaft','Sense_Open_Cradle']]
    for x,name,parts,color in [(400,'Previous removable tip',oldtop,(145,162,171)),(1080,'New one-piece upper rod + holder',variants[0][1],(38,158,185))]:
        draw_model(im,parts,(x,590),12.,376.,color,clip=(341.,411.))
        d.text((x-275,113),name,font=font(26),fill=(27,45,56))
    d.rectangle((0,1060,1500,1120),fill=(242,246,248))
    d.text((55,1075),'Broader fork rails; no tip bayonet. Board, solder space and USB remain clear in CAD. Strength needs a print test.',font=font(22),fill=(62,84,96))
    im.save(out/'sensor-closeup.png')
    print(out/'comparison.png');print(out/'sensor-closeup.png')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--exports',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();build(a.exports.resolve(),a.out.resolve())
