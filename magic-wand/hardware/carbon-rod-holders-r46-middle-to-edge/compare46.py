"""Render the two finished carriers from their generated STL triangles."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh
from holder46 import BASE

def triangles(path,transform=None):
    obj=trimesh.load_mesh(path,process=False)
    if transform is not None:obj.apply_transform(transform)
    return obj.triangles

def render(items,direction,scale,size,centre):
    forward=np.array(direction,dtype=float);forward/=np.linalg.norm(forward)
    right=np.cross(np.array([0.,1.,0.]),forward);right/=np.linalg.norm(right)
    up=np.cross(forward,right);basis=np.stack((right,up,forward))
    pts=np.concatenate([t for t,colour in items])
    colours=np.concatenate([np.broadcast_to(c,(len(t),3)) for t,c in items])
    normals=np.cross(pts[:,1]-pts[:,0],pts[:,2]-pts[:,0])
    view=normals@forward>1.e-9;pts=pts[view];normals=normals[view];colours=colours[view]
    normals/=np.maximum(1e-10,np.linalg.norm(normals,axis=1))[:,None]
    light=(.80*forward-.34*right+.45*up);light/=np.linalg.norm(light)
    rgb=np.clip(colours*(.53+.47*np.maximum(0,normals@light))[:,None],0,255).astype('uint8')
    vs=(pts-centre)@basis.T
    width,height=size
    xy=vs[:,:,:2]*[scale,-scale]+np.array(size)/2
    vertices=np.concatenate((xy,vs[:,:,2:3]),axis=2)
    pixels=np.full((height,width,3),[24,31,37],dtype=np.uint8)
    zbuf=np.full((height,width),-np.inf)
    # Interpolate actual triangle depth at pixel centres. Faces on the
    # broad deck and the rounded braces overlap in projection.
    lo=np.maximum(np.ceil(xy.min(axis=1)-.5).astype(int),0)
    hi=np.minimum(np.floor(xy.max(axis=1)-.5).astype(int),[width-1,height-1])
    for i in np.flatnonzero(np.all(hi>=lo,axis=1)):
        x,y=lo[i];X,Y=hi[i];a,b,c=vertices[i]
        u,v=b-a,c-a;det=u[0]*v[1]-u[1]*v[0]
        if abs(det)<1.e-10:continue
        dx=np.arange(x,X+1)+.5-a[0];dy=np.arange(y,Y+1)[:,None]+.5-a[1]
        s=(dx*v[1]-dy*v[0])/det;t=(u[0]*dy-u[1]*dx)/det
        z=a[2]+s*u[2]+t*v[2]
        window=zbuf[y:Y+1,x:X+1]
        covered=(s>=-1e-9)&(t>=-1e-9)&(s+t<=1.+1e-9)&(z>window)
        window[covered]=z[covered]
        pixels[y:Y+1,x:X+1][covered]=rgb[i]
    return Image.fromarray(pixels)

def build(parts,out):
    out.mkdir(parents=True,exist_ok=True)
    frame=np.array(json.loads((parts/'frame.json').read_text())['print_to_assembly'])
    old=triangles(BASE/'R45-Key-Carrier-assembly.stl')
    braces=triangles(parts/'R46-added-braces.stl',frame)
    for name,direction,centre,scale in [('underside',(0.,-.12,-1.),(0.,12.,3.),11.),
            ('left-return',(-.5,-.6,-1.),(-13.5,13.,5.),21.)]:
        sizes=(760,510);overall=Image.new('RGB',(1532,564),(24,31,37))
        for x,items in [(0,[(old,[71,171,183])]),(772,[(old,[71,171,183]),(braces,[204,244,232])])]:
            overall.paste(render(items,direction,scale,sizes,centre),(x,54))
        draw=ImageDraw.Draw(overall)
        try:font=ImageFont.truetype('Arial.ttf',22)
        except OSError:font=ImageFont.load_default(size=22)
        draw.text((20,14),'R45  •  finished carrier',font=font,fill='white')
        draw.text((792,14),'R46  •  new permanent braces in pale green',font=font,fill='white')
        overall.save(out/('R45-R46-'+name+'.png'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parts',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();build(a.parts,a.output)
