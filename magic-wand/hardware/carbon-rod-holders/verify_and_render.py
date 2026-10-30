#!/usr/bin/env python3
"""Reload final STL geometry; check purchased envelopes and show exact meshes."""
from pathlib import Path
import json
import numpy as np
import manifold3d as mf
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cad

HERE=Path(__file__).resolve().parent;OUT=HERE/'exports';P=cad.P

def read(name):
    m=trimesh.load_mesh(OUT/(name+'-assembly.stl'))
    assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
    return m,mf.Manifold(mf.Mesh(np.array(m.vertices,dtype=np.float32),np.array(m.faces,dtype=np.uint32)))

def collision(a,b):return abs((a^b).volume())

def checks():
    key,ks=read('Key_Battery_Carrier');tip,ts=read('XIAO_Rod_Holder');refs=cad.references()
    report={'reloaded_closed_single_bodies':True,'physical_fit_verified':False,'parts':{},'checker_sha256':cad.sha(Path(__file__)),'manifest_sha256':cad.sha(OUT/'manifest.json')}
    manifest=json.loads((OUT/'manifest.json').read_text())
    for name,digest in manifest['source_sha256'].items():assert cad.sha(HERE/name)==digest,('Stale CAD export',name)
    report['carrier_clearance_mm3']={name:collision(ks,obj)for name,obj in refs.items() if name not in ['pcb','usb']}
    report['tip_clearance_mm3']={name:collision(ts,obj)for name,obj in refs.items() if name in ['pcb','usb','rod']}
    assert max(report['carrier_clearance_mm3'].values())<.002,report['carrier_clearance_mm3']
    assert max(report['tip_clearance_mm3'].values())<.002,report['tip_clearance_mm3']
    # Continuous swept bounding boxes test top-loading / outward removal.
    b=P['battery'];s=P['sensor'];k=P['keys']
    battery=refs['battery'];bb=cad.box(-b['width']/2,b['width']/2,b['start_y']+b['clearance_per_side'],b['start_y']+b['clearance_per_side']+b['length'],b['floor_z'],b['floor_z']+b['thickness']+20)
    pcb=cad.box(-s['board_width']/2,s['board_width']/2,1.3,1.3+s['board_length'],s['board_z']+.01,s['board_z']+18)
    usb=cad.box(-5.2,5.2,23.4,45,s['board_z']+.9,s['board_z']+4.4)
    report['continuous_access_mm3']={'battery_outward':collision(ks,bb),'board_outward':collision(ts,pcb),'usb_plug_approach':collision(ts,usb)}
    # Sleeve slides axially over a free rod end; no snap-through is claimed.
    rod_through=cad.tube_y(0.001,P['rod']['diameter']/2,-60,80)
    report['continuous_access_mm3']['rod_axial_entry']=collision(ts,rod_through)
    assert max(report['continuous_access_mm3'].values())<.002,report
    report['switch_housing_entries_mm3']={}
    report['purchased_clip_capture_mm3']={}
    for x in [-k['pitch'],0,k['pitch']]:
        sweep=cad.rr(13.8,13.8,.2,k['plate_z']-2.2,k['plate_z']+15).translate((x,0,0))
        report['switch_housing_entries_mm3'][str(x)]=collision(ks,sweep)
        hooks=cad.ds.local_hardware(cad.C)['factory_clips'].translate((x,0,k['plate_z']+.4))
        report['purchased_clip_capture_mm3'][str(x)]=collision(ks,hooks)
    assert max(report['switch_housing_entries_mm3'].values())<.002,report
    assert min(report['purchased_clip_capture_mm3'].values())>.1,report
    for name,m in [('Key_Battery_Carrier',key),('XIAO_Rod_Holder',tip)]:
        report['parts'][name]={'solid_PETG_g':m.volume/1000*P['print']['density_g_cm3'],'bounds_mm':m.bounds.tolist(),'faces':len(m.faces)}
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return key,tip,refs,report

def draw(ax,objects,bounds):
    triangles=[];all_colors=[]
    elev,azim=np.radians([48,-67])
    front=np.array([np.cos(elev)*np.cos(azim),np.cos(elev)*np.sin(azim),np.sin(elev)])
    right=np.array([-np.sin(azim),np.cos(azim),0]);up=np.cross(front,right)
    basis=np.array([right,up,front]).T
    for m,color in objects:
        normals=m.face_normals
        shade=.62+.38*np.clip(normals@np.array([.3,-.35,.9]),0,1)
        rgb=np.array(matplotlib.colors.to_rgb(color));colors=np.c_[shade[:,None]*rgb,np.ones(len(shade))]
        triangles.append(m.triangles@basis);all_colors.append(colors)
    # A true per-pixel depth buffer prevents painter-order artefacts between
    # large board/cap faces and the narrow frame. Render the actual STL mesh.
    corners=np.array([[x,y,z]for x in bounds[:,0]for y in bounds[:,1]for z in bounds[:,2]])@basis
    lo=corners[:,:2].min(0);hi=corners[:,:2].max(0);width,height=1000,680
    scale=min((width-40)/(hi[0]-lo[0]),(height-40)/(hi[1]-lo[1]));center=(lo+hi)/2
    xyz=np.concatenate(triangles);xyz[:,:,:2]=(xyz[:,:,:2]-center)*scale+[width/2,height/2]
    xyz[:,:,1]=height-xyz[:,:,1]
    rgb=np.full((height,width,3),[245,244,239],dtype=np.uint8);depth=np.full((height,width),-np.inf)
    for tri,color in zip(xyz,np.concatenate(all_colors)):
        x0,y0=np.maximum(0,np.floor(tri[:,:2].min(0)).astype(int));x1,y1=np.minimum([width-1,height-1],np.ceil(tri[:,:2].max(0)).astype(int))
        if x1<x0 or y1<y0:continue
        a,b,c=tri;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-10:continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
        wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;wc=1-wa-wb
        zz=wa*a[2]+wb*b[2]+wc*c[2];region=depth[y0:y1+1,x0:x1+1]
        mask=(wa>=-1e-6)&(wb>=-1e-6)&(wc>=-1e-6)&(zz>region)
        region[mask]=zz[mask];rgb[y0:y1+1,x0:x1+1][mask]=(color[:3]*255).astype(np.uint8)
    ax.imshow(rgb);ax.set_axis_off()

def pane(ax,title,m,refs,loaded,tip=False):
    objects=[(m,'#db963f' if tip else '#249da2')]
    for name,obj in refs.items():
        if tip and name not in ['pcb','usb','rod']:continue
        if not tip and name in ['pcb','usb']:continue
        if not loaded and name!='rod':continue
        mesh=cad.mesh(obj)
        if name=='rod':
            yy=(-9,30) if tip else (-20,70)
            mesh=cad.mesh(cad.cyl(4,yy[0],yy[1]).rotate((-90,0,0)))
        objects.append((mesh,'#303741' if name=='rod' else '#6e7888' if name=='battery' else '#387c52' if name=='pcb' else '#b6bfcc' if name=='usb' else '#e2e5e9'))
    bounds=np.array([[-15,-12,-6],[15,31,16]])if tip else np.array([[-32,-20,-6],[32,70,21]])
    draw(ax,objects,bounds)
    ax.set_title(title,fontsize=16,color='#162635',loc='left',pad=6)

def render(key,tip,refs,report):
    fig=plt.figure(figsize=(14,11),facecolor='#f5f4ef')
    panes=[('Key + battery carrier | bare frame',key,False,False),('Key + battery carrier | reference parts',key,True,False),('Tip holder | bare frame',tip,False,True),('Tip holder | reference board',tip,True,True)]
    for i,(title,m,loaded,is_tip) in enumerate(panes):
        ax=fig.add_subplot(2,2,i+1,facecolor='#f5f4ef');pane(ax,title,m,refs,loaded,is_tip)
    fig.suptitle('Two lightweight holders for the original 8 mm rod',fontsize=24,fontweight='bold',color='#162635',x=.055,ha='left',y=.98)
    kg=report['parts']['Key_Battery_Carrier']['solid_PETG_g'];tg=report['parts']['XIAO_Rod_Holder']['solid_PETG_g']
    fig.text(.055,.927,f'CAD material estimate: carrier {kg:.2f} g  /  tip {tg:.2f} g     |     PETG, printed parts only',fontsize=12,color='#425365')
    fig.text(.055,.045,'DIMENSIONAL PROTOTYPE: battery envelope 22 x 30 x 6 mm. Fitted cell and solder/wire details need confirmation.\nDark rod, grey battery, white keys and green PCB are references, excluded from print files. Fit and strength untested.',fontsize=11,color='#744722',linespacing=1.6)
    fig.subplots_adjust(left=.015,right=.985,top=.89,bottom=.10,wspace=.02,hspace=.09)
    fig.savefig(OUT/'Design-preview.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)

if __name__=='__main__':render(*checks())
