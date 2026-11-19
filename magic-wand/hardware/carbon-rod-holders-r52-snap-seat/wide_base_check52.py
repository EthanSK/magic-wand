"""Measure actual first-layer coverage and attachment to every bed-starting mechanism foot."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
from plate52 import HERE
from orient51 import load_solid, digest
from removal51 import unpack
from support51 import footprint, GRID
from wide_bases52 import panels


def check(out):
    archive=out/'Mechanisms.gcode.3mf'
    data,features,owners,normal=unpack(archive)
    records=json.loads((out/'layout.frame.json').read_text())['parts']
    report={'archive_sha256':digest(archive),'grid_mm':GRID,'parts':{}}
    fig,axes=plt.subplots(1,2,figsize=(11,6),layout='constrained')
    for ax,(name,row) in zip(axes,records.items()):
        body=load_solid(HERE/'exports'/row['assembly_stl']).transform(np.array(row['assembly_to_machine'])[:3])
        footprint_body=body.slice(.10)
        top=data[(data[:,6]==owners[name])&(data[:,7]<.201)&np.isin(data[:,5],normal)]
        start=np.floor(top[:,:2].min(0))-2
        shape=np.ceil((top[:,:2].max(0)-start+2)[::-1]/GRID).astype(int)
        mask=footprint(top,start,shape)
        raster=Image.fromarray(mask.astype(np.uint8)).copy()
        component_ids=[]
        def root(x,y):
            xy=(np.rint((np.array([x,y])-start)/GRID)).astype(int)
            point=tuple(map(int,xy)); ident=raster.getpixel(point)
            if ident==1:
                ident=2+len(component_ids);component_ids.append(ident)
                ImageDraw.floodfill(raster,point,ident)
            return ident
        if name=='Key_Carrier':
            from plate52 import PREVIOUS
            from props51 import route_parts
            rows=json.loads((PREVIOUS/'exports/print-trial/external-prop-paths.json').read_text())
            locations={f"Outside prop {i+1}":r['foot_xy'] for i,r in enumerate(r for r in rows if r['found'] and r['layer']!=199)}
            locations.update({'Spring frame left':[53,104.5],'Spring frame right':[65,104.5],
                              'Front base':[50,55],'Rear base':[50,125]})
        else:
            locations={'Left base':[103,100],'Right base':[150,100]}
        # Test model material well inside the native body, independently of CAD boundary pixels.
        from support51 import q
        interior=q._inside(footprint_body.offset(-.25),top[:,:2])
        if not interior.any():raise ValueError(name)
        valid=np.flatnonzero(interior)
        locations['Body']=top[valid[len(valid)//2],:2].tolist()
        joints={key:root(*xy) for key,xy in locations.items()}
        iy,ix=np.nonzero(mask)
        bed_xy=np.stack((ix,iy),axis=1)*GRID+start
        panel_masks=[q._inside(panel,bed_xy) for panel in panels(name)]
        plate_area=float(np.logical_or.reduce(panel_masks).sum()*GRID**2)
        area=float(mask.sum()*GRID**2)
        report['parts'][name]=dict(native_positive_bed_area_mm2=round(area,2),native_area_inside_removable_plate_outlines_mm2=round(plate_area,2),same_component_area_mm2=round(float((np.asarray(raster)==joints['Body']).sum())*GRID**2,2),
            root_component_ids=joints,root_machine_xy_mm=locations,
            all_roots_connected=bool(joints['Body'] and len(set(joints.values()))==1))
        ax.imshow(mask,origin='lower',extent=[start[0],start[0]+shape[1]*GRID,start[1],start[1]+shape[0]*GRID],cmap='Greys')
        for k,(x,y) in locations.items(): ax.plot(x,y,'o',ms=3,color='#0a9295')
        ax.set_title(name.replace('_',' '));ax.set_xlabel('Bed X (mm)');ax.set_ylabel('Bed Y (mm)')
    fig.suptitle('Removable base plates and attached feet on the first printed layer')
    fig.savefig(out/'wide-bases.png',dpi=175)
    (out/'wide-bases.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report,flush=True)


if __name__=='__main__':
    check(Path(sys.argv[1]))
