"""Prove outward prop withdrawal, printed footing, layer backing, and access to native supports."""
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import numpy as np
import manifold3d as mf
from PIL import Image, ImageDraw

from orient51 import digest,load_solid,oriented
from props51 import route_parts
from support51 import q,footprint,dilation,lost_islands
from printed_props51 import native_mask
from clearance51 import inspect as sensitive

HERE=Path(__file__).resolve().parent


def unpack(archive):
    with ZipFile(archive) as z:
        text=z.read('Metadata/plate_1.gcode').decode()
        p=ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
        ids={x.get('name'):int(x.get('identify_id')) for x in p.findall('object')}
        settings=json.loads(z.read('Metadata/project_settings.config'))
    d,labs,_=q.extrusion_points(text,.12)
    d[:,:2]+=np.fromstring(settings['extruder_offset'][0],sep='x')
    features=np.array(labs)
    normal=np.flatnonzero(~(np.char.startswith(features,'Support')|np.char.startswith(features,'Brim')|np.char.startswith(features,'Skirt')|(features=='Prime tower')))
    return d,features,ids,normal


def exact_pulls(body,props,rows,off):
    # Each contributing element is convex. Hull of its original and
    # translated copy is its exact continuous translation sweep.
    parts=[];directions=[];tips=[]
    for row in rows:
        if not row['found']:continue
        xy=np.array(row['xy'])-off;foot=np.array(row['foot_xy'])-off
        tip=np.r_[xy,row['layer']*.2-.6]
        local=route_parts(foot,tip,row['rise_mm'])
        parts.append(local);directions.append(np.array(row['pull_xy']));tips.append(row['xy'])
    made=[mf.Manifold.batch_boolean(p,mf.OpType.Add) for p in parts]
    baseline=[load_solid(p) for p in sorted(props.glob('prop-*.stl'))]
    assert len(baseline)==len(made) and all(abs(a.volume()-b.volume())<.003 for a,b in zip(baseline,made))
    remaining=list(range(len(made))); steps=[]
    while remaining:
        success=False
        for i in remaining.copy():
            init=np.arctan2(directions[i][1],directions[i][0])
            for angle in (0.,-10.,10.,-25.,25.,-45.,45.,-70.,70.,90.,-90.,180.):
                rad=init+np.deg2rad(angle); direction=np.array([np.cos(rad),np.sin(rad),0.])
                sweep=mf.Manifold.batch_boolean([mf.Manifold.batch_hull([p,p.translate(direction*90.)]) for p in parts[i]],mf.OpType.Add)
                if (sweep^body).volume()>.0001:continue
                if any((sweep^made[j]).volume()>.0001 for j in remaining if j!=i): continue
                steps.append(dict(prop=i,tip_machine_xy=tips[i],pull_xy=direction[:2].round(3).tolist(),sweep_mm=90.,
                                  model_collision_mm3=round((sweep^body).volume(),6)))
                remaining.remove(i);success=True;break
            if success: break
        if not success:break
    return steps, remaining


def openings(body,d,features,owner,mesh,off,grid=.4):
    """Access for a broken-off sub-mm piece in empty CAD; not intact removal."""
    origin=np.array(body.bounding_box()[:3])-3.
    hi=np.array(body.bounding_box()[3:])+3.
    shape=np.ceil((hi-origin)/grid).astype(int)+1
    nx,ny,nz=shape; solid=np.zeros((nz,ny,nx),bool)
    for layer in range(nz):
        section=body.slice(float(origin[2]+grid*layer))
        img=np.zeros((ny,nx),bool)
        for poly in section.to_polygons():
            p=Image.new('1',(nx,ny));dr=ImageDraw.Draw(p)
            pts=np.rint((poly-origin[:2])/grid).astype(int)
            dr.polygon([tuple(v) for v in pts],fill=1)
            img ^= np.asarray(p,dtype=bool)
        solid[layer]=img
    obstacle=solid.copy()
    # Inflate the CAD by a 0.4-mm radius in every grid axis. Reject diagonal
    # moves through a point contact by using six-connected outside flooding.
    radius=round(.4/grid)
    directions=[(dx,dy,dz) for dx in range(-radius,radius+1) for dy in range(-radius,radius+1) for dz in range(-radius,radius+1)
                if 0<dx*dx+dy*dy+dz*dz<=radius*radius]
    for dx,dy,dz in directions:
        obstacle |= np.roll(solid,(dz,dy,dx),axis=(0,1,2))
    access=~obstacle
    reached=np.zeros_like(access)
    for axis in range(3):
        for i in (0,-1):
            key=[slice(None)]*3;key[axis]=i;reached[tuple(key)]=access[tuple(key)]
    for _ in range(sum(shape)):
        old=reached
        reached=reached.copy()
        for k in range(3):reached|=np.roll(old,1,axis=k)|np.roll(old,-1,axis=k)
        reached&=access
        if np.array_equal(reached,old):break
    pts=d[np.isin(d[:,5],np.where(np.char.startswith(features,'Support'))[0])]
    xyz=pts[:,:3].copy();xyz[:,:2]-=off;xyz[:,2]=pts[:,7]-pts[:,4]/2
    close=np.all((xyz>=origin+grid)&(xyz<=hi-grid),axis=1);xyz=xyz[close]
    ij=np.rint((xyz-origin)/grid).astype(int)
    x,y,z=ij.T
    reachable=reached[z,y,x]
    for delta in directions:
        delta=np.asarray(delta);ix=ij+delta
        mid=ij+np.rint(delta*.5).astype(int)
        ix=np.clip(ix,0,shape-1);mid=np.clip(mid,0,shape-1)
        clear=~solid[mid[:,2],mid[:,1],mid[:,0]] if np.max(abs(delta))>1 else True
        reachable|=clear & reached[ix[:,2],ix[:,1],ix[:,0]]
    remaining=pts[close][~reachable]
    regions=[]
    if len(remaining):
        for layer in np.unique(remaining[:,7]):
            rr=remaining[np.abs(remaining[:,7]-layer)<.001]
            regions.append(dict(layer_top_mm=round(float(layer),3),count=len(rr),
                xy_bounds=np.round(np.r_[rr[:,:2].min(0),rr[:,:2].max(0)].astype(float),3).tolist()))
    return dict(unreachable_regions=regions,unreachable_sensitive_zone_samples=sensitive(remaining,mesh,'Key_Carrier'),samples=int(len(ij)),reachable_by_0p8_mm_fragment_after_one_cell_release=int(reachable.sum()),
                unreachable_sample_count=int((~reachable).sum()),grid_mm=grid,
                note='A fragment can move one opening cell away from the peel face; the test then follows a six-connected route outside the empty holder. It does not prove intact support release.')


def check(archive,framefile,props,generation):
    frames=json.loads(framefile.read_text()); row=frames['parts']['Key_Carrier']
    source=HERE/'exports/Key_Carrier-assembly.stl';assert digest(source)==row['source_sha256']
    body,frame=oriented(load_solid(source),row['orientation']);off=np.asarray(row['assembly_to_machine'])[:2,3]-frame[:2,3]
    rows=json.loads(generation.read_text())
    steps,blocked=exact_pulls(body,props,rows,off)
    d,features,owners,normal=unpack(archive)
    mask,_=native_mask(archive,q,d,owners['Key_Carrier'],normal)
    m=d[mask]; low=m[:,:2].min(0)-2; dims=tuple(np.ceil(((m[:,:2].max(0)+2-low)/.1)[::-1]).astype(int)+1)
    all_layers=np.rint(m[:,7]*5).astype(int)
    feet=[]; failures=[]
    for layer in range(1,max(all_layers)+1):
        fp=footprint(m[all_layers==layer],low,dims)
        if layer==1:
            feet=lost_islands(fp,np.zeros_like(fp),low)
        else:
            failures.extend(dict(layer=layer,**v) for v in lost_islands(fp,dilation(previous),low))
        previous=fp
    accessible=openings(body,d,features,owners['Key_Carrier'],row['assembly_to_machine'],off)
    fine=openings(body,d,features,owners['Key_Carrier'],row['assembly_to_machine'],off,grid=.20)
    out=dict(sliced_sha256=digest(archive),individual_prop_footprints_mm2=[r['area_mm2'] for r in feet],
             unrooted_prop_islands=failures,peel_steps_after_the_brim_is_off=steps,
             props_requiring_nipping=blocked,normal_support_fragment_access=accessible,fine_fragment_access=fine,physical_cleanup_tested=False)
    (archive.parent/'prop-release.json').write_text(json.dumps(out,indent=2)+'\n')
    print('feet',out['individual_prop_footprints_mm2'],'unrooted',len(failures),'withdrawals',len(steps),'blocked',blocked,'access',accessible,flush=True)


if __name__=='__main__':
    check(*map(Path,sys.argv[1:5]))
