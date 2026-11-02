#!/usr/bin/env python3
"""Render technical concept views directly from the generated CAD manifest.
Run after ring_cad.py; illustrations show actual meshes, never AI-invented fit.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent
DATA=json.loads((HERE/'exports/manifest.json').read_text())
BG='#f5f3ee'; INK='#193b46'


def draw(ax, variant: str, elev: float, azim: float, exploded: bool=False, scale_override: float | None=None) -> None:
    # A small depth buffer gives reliable occlusion for the hollow band and
    # recessed pads; a painter's triangle sort incorrectly exposes rear faces.
    from PIL import Image
    model=next(v for v in DATA['variants'] if v['name']==variant)
    width,height=1000,760
    pixels=np.full((height,width,3),matplotlib.colors.to_rgb(BG))
    depth=np.full((height,width),-np.inf)
    e,a=np.radians([elev,azim])
    eye=np.array([np.cos(a)*np.cos(e),np.sin(a)*np.cos(e),np.sin(e)])
    right=np.array([-np.sin(a),np.cos(a),0]); up=np.cross(eye,right)
    handheld=model['family']=='Handheld'
    center=np.array([0,0,(18 if exploded else 5) if handheld else (18 if exploded else 4)])
    scale=scale_override if scale_override is not None else (10 if exploded else (19 if handheld else 14))
    light=np.array([.3,-.5,1]);light/=np.linalg.norm(light)
    for part in model['parts']:
        if not exploded and ('Envelope' in part['name'] or 'Switch_Assumed' in part['name']): continue
        vertices=np.array(part['vertices']);faces=np.array(part['faces'])
        if exploded:
            dz={'Lift_Off_Lid':28,'Board_Envelope':20,'Battery_Envelope':14}.get(part['name'],0)
            vertices[:,2]+=dz
        rel=vertices-center
        projected=np.column_stack([width/2+rel@right*scale,height/2-rel@up*scale,rel@eye])
        color=np.array(matplotlib.colors.to_rgb(part['color']))
        if exploded and part['name'] in ('Band_Pod','Handheld_Shell'):color=.65*color+.35*np.array(matplotlib.colors.to_rgb(BG))
        for face in faces:
            v=projected[face]; world=vertices[face]
            normal=np.cross(world[1]-world[0],world[2]-world[0]); norm=np.linalg.norm(normal)
            if norm<1e-10:continue
            normal/=norm
            if normal@eye<0:continue
            xmin=max(0,int(np.floor(v[:,0].min())));xmax=min(width-1,int(np.ceil(v[:,0].max())))
            ymin=max(0,int(np.floor(v[:,1].min())));ymax=min(height-1,int(np.ceil(v[:,1].max())))
            if xmax<xmin or ymax<ymin:continue
            x,y=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
            denom=(v[1,1]-v[2,1])*(v[0,0]-v[2,0])+(v[2,0]-v[1,0])*(v[0,1]-v[2,1])
            if abs(denom)<1e-10:continue
            u=((v[1,1]-v[2,1])*(x-v[2,0])+(v[2,0]-v[1,0])*(y-v[2,1]))/denom
            w=((v[2,1]-v[0,1])*(x-v[2,0])+(v[0,0]-v[2,0])*(y-v[2,1]))/denom
            t=1-u-w;z=u*v[0,2]+w*v[1,2]+t*v[2,2]
            tile=depth[ymin:ymax+1,xmin:xmax+1]
            mask=(u>=-1e-8)&(w>=-1e-8)&(t>=-1e-8)&(z>tile)
            tile[mask]=z[mask]
            shade=.42+.58*max(0,float(normal@light))
            pixels[ymin:ymax+1,xmin:xmax+1][mask]=np.clip(color*shade,0,1)
    ax.imshow(Image.fromarray(np.uint8(pixels*255)).resize((width//2,height//2),Image.Resampling.LANCZOS))
    ax.set_axis_off()


def main() -> None:
    fig=plt.figure(figsize=(16,11),facecolor=BG)
    fig.text(.045,.955,'CONTROL STONES V2',fontweight='bold',fontsize=26,color=INK)
    fig.text(.045,.919,'One sensor ring · left and right hands · three-button baseline',fontsize=14,color='#53727b')
    fig.text(.955,.954,'MECHANICAL CONCEPT',ha='right',fontsize=10,fontweight='bold',color='#94612e')
    panels=[('Left_3Button','LEFT HAND · THREE BUTTONS',18,-58,False),('Right_3Button','RIGHT HAND · THREE BUTTONS',18,-122,False),('Left_4Button','OPTIONAL FOURTH · UNDERSIDE',-33,-58,False),('Left_3Button','ELECTRONICS · EXPLODED',12,-60,True)]
    for i,(variant,title,elev,azim,exploded) in enumerate(panels):
        x=.025+(i%2)*.495; y=.49 if i<2 else .095
        ax=fig.add_axes((x,y,.48,.37),facecolor=BG); draw(ax,variant,elev,azim,exploded)
        fig.text(x+.03,y+.355,title,fontsize=11,fontweight='bold',color=INK)
        captions=['Gold = thumb-facing normal click. Purple = far-side button.','Anatomical mirror: normal click stays beside the thumb.','Two separate underside pads; rear pad has a tactile ridge.','Green: board envelope. Silver: assumed battery. Lift-off lid.']
        fig.text(x+.03,y-.004,captions[i],fontsize=10,color='#53727b')
    dims=DATA['assumptions']; board=dims['board']['size']; finger=dims['finger']
    points=np.concatenate([np.array(p['vertices']) for p in DATA['variants'][0]['parts']])
    extents=np.ptp(points,axis=0)
    summary=f"Footprint checked: XIAO {board[1]:g} × {board[0]:g} mm. Ring bore: assumed {finger['bore_width']:g} × {finger['bore_height']:g} mm. Overall: {extents[0]:.1f} × {extents[1]:.1f} × {extents[2]:.1f} mm."
    fig.text(.055,.066,summary,fontsize=11,color=INK)
    fig.text(.055,.035,'Battery, switches, finger fit, comfort, retention and printability are unverified. Coloured pads show positions, not working mechanisms.',fontsize=10,color='#94612e')
    fig.savefig(HERE/'exports/overview.png',dpi=135,facecolor=BG)
    plt.close(fig)
    fig=plt.figure(figsize=(12,6),facecolor=BG)
    fig.text(.04,.94,'THREE OR FOUR BUTTONS · UNDERSIDE',fontsize=20,fontweight='bold',color=INK)
    for i,count in enumerate((3,4)):
        ax=fig.add_axes((i*.5,.12,.5,.72),facecolor=BG)
        draw(ax,f'Left_{count}Button',-48,-58)
        fig.text(.04+i*.5,.09,'One underside pad' if count==3 else 'Two underside pads · one raised ridge',fontsize=12,color=INK)
    fig.text(.04,.035,'Optional fourth button requires a comfortable, eyes-free reach test. No working switch mechanism is implied.',fontsize=10,color='#94612e')
    fig.savefig(HERE/'exports/underside-comparison.png',dpi=135,facecolor=BG)
    plt.close(fig)


def handheld_views() -> None:
    fig=plt.figure(figsize=(16,11),facecolor=BG)
    fig.text(.045,.955,'CONTROL STONES V2 · COMPACT HANDHELD',fontweight='bold',fontsize=24,color=INK)
    fig.text(.045,.919,'Very short · hollow body · no extra shaft · pick up and put down',fontsize=14,color='#53727b')
    panels=[('Handheld_Left_3Button','LEFT HAND · THREE BUTTONS',28,-58,False),('Handheld_Right_3Button','RIGHT HAND · THREE BUTTONS',28,-122,False),('Handheld_Left_4Button','OPTIONAL FOURTH · UNDERSIDE',-38,-58,False),('Handheld_Left_3Button','ELECTRONICS · EXPLODED',18,-60,True)]
    for i,(variant,title,elev,azim,exploded) in enumerate(panels):
        x=.025+(i%2)*.495;y=.49 if i<2 else .095
        ax=fig.add_axes((x,y,.48,.37),facecolor=BG);draw(ax,variant,elev,azim,exploded)
        fig.text(x+.03,y+.355,title,fontsize=11,fontweight='bold',color=INK)
        captions=['Gold: thumb-facing normal click. Purple: opposite side.','Anatomical mirror; actual grip and reach need a mock-up.','Two separate pads below the body; one tactile ridge.','One board, one battery. Wire-tie bridge in the rear gutter.']
        fig.text(x+.03,y-.004,captions[i],fontsize=10,color='#53727b')
    model=next(v for v in DATA['variants'] if v['name']=='Handheld_Left_3Button')
    points=np.concatenate([np.array(p['vertices']) for p in model['parts']]);size=np.ptp(points,axis=0)
    fig.text(.055,.066,f'Current envelope: {size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} mm. Board XY checked; battery, switches and assembled board height are assumptions.',fontsize=11,color=INK)
    fig.text(.055,.035,'Concept only. No verified minimum weight, complete switch mechanism, retention, comfort, strength or printability.',fontsize=10,color='#94612e')
    fig.savefig(HERE/'exports/handheld-overview.png',dpi=135,facecolor=BG);plt.close(fig)
    fig=plt.figure(figsize=(12,7),facecolor=BG)
    fig.text(.04,.94,'LEADING HANDHELD · ORIGINAL RING',fontsize=22,fontweight='bold',color=INK)
    for i,(variant,label) in enumerate([('Handheld_Left_3Button','Compact pickup-and-put-down body'),('Left_3Button','Earlier finger-worn ring · preserved')]):
        ax=fig.add_axes((i*.5,.13,.5,.72),facecolor=BG);draw(ax,variant,20,-58,scale_override=14)
        fig.text(.04+i*.5,.11,label,fontsize=12,color=INK)
    fig.text(.04,.055,'Same viewing scale. Both use the same component envelopes; no extra shaft in the handheld design.',fontsize=11,color=INK)
    fig.text(.04,.023,'Same rotation gives the same gyro reading; balance, inertia, grip and click feel still need physical testing.',fontsize=10,color='#94612e')
    fig.savefig(HERE/'exports/handheld-v-ring.png',dpi=135,facecolor=BG);plt.close(fig)

if __name__=='__main__':
    main()
    handheld_views()
