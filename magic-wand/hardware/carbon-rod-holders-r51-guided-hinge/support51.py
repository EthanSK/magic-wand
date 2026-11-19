"""Compare real native extrusion on the changed bodies at 0.10 mm, including support under new islands."""
import argparse
from collections import deque
import importlib.util
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np


from orient51 import digest
from clearance51 import inspect as inspect_sensitive, bearing_space
import roofs51
import printed_props51

HERE = Path(__file__).resolve().parent
QFILE = HERE.parent / 'printed-loop-wand/shard-tube-r2/check_sliced_paths.py'
spec = importlib.util.spec_from_file_location('support51_native', QFILE)
q = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = q
spec.loader.exec_module(q)
GRID = .10


def footprint(points, origin, shape):
    """Stamp actual bead widths around the sampled straight and arc centre lines."""
    mask = np.zeros(shape, dtype=bool)
    if not len(points):
        return mask
    ij = np.rint((points[:,:2]-origin) / GRID).astype('int32')
    width = np.rint(points[:,3]*20).astype('int32')
    for w in np.unique(width):
        x, y = ij[width==w].T
        r = w / 40 / GRID
        for dy in range(-int(r),int(r)+1):
            dxs = int((r*r-dy*dy)**.5)
            for dx in range(-dxs,dxs+1):
                mask[y+dy,x+dx] = True
    return mask


def dilation(mask, n=1):
    padded=np.pad(mask,n)
    y,x=mask.shape
    return np.logical_or.reduce([padded[n+dy:n+dy+y,n+dx:n+dx+x]
        for dy in range(-n,n+1) for dx in range(-n,n+1) if dy*dy+dx*dx<=n*n])


def lost_islands(model, backed, origin):
    """Flood only model material which is both present AND ungrounded at this layer."""
    # Four-neighbour raster excludes diagonal point contacts from load-bearing evidence.
    # Run-length components. A row-run joins every overlapped run on the
    # preceding row; diagonal point-only contacts remain separate.
    occupied_rows = np.flatnonzero(model.any(axis=1))
    runs=[]; parent=[]; previous=[]; last_y=-2
    def root(i):
        while i!=parent[i]:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    for y in occupied_rows:
        bounds=np.flatnonzero(np.diff(model[y],prepend=False,append=False)).reshape(-1,2)
        if y!=last_y+1: previous=[]
        current=[]; first=0
        for xa,xb in bounds:
            xa=int(xa);xb=int(xb)
            i=len(parent);parent.append(i)
            runs.append((int(y),xa,xb))
            while first<len(previous) and previous[first][1]<=xa: first+=1
            j=first
            while j<len(previous) and previous[j][0]<xb:
                parent[root(i)]=root(previous[j][2])
                j+=1
            current.append((xa,xb,i))
        previous=current;last_y=y
    grounded=set(); grouped={}
    for i,(y,xa,xb) in enumerate(runs):
        k=root(i)
        if k in grounded:continue
        if backed[y,xa:xb].any():
            grounded.add(k);grouped.pop(k,None);continue
        if k not in grouped:grouped[k]=[0,xa,y,xb-1,y]
        part=grouped[k];part[0]+=xb-xa
        part[1]=min(part[1],xa);part[2]=min(part[2],y)
        part[3]=max(part[3],xb-1);part[4]=max(part[4],y)
    result=[]
    for count,xa,ya,xb,yb in grouped.values():
        if count>=10:
            bounds=[origin[0]+xa*GRID,origin[1]+ya*GRID,origin[0]+xb*GRID,origin[1]+yb*GRID]
            result.append(dict(area_mm2=round(count*GRID**2,3),machine_xy_bounds=[round(float(v),2) for v in bounds]))
    return result



def support_mass(text, settings, centres):
    """Positive filament for actual support moves, attributed by the separated XY footprints."""
    relative=True
    tag=False
    last_e=0.
    pos=np.zeros(2)
    length={n:0. for n in centres}
    for raw in text.splitlines():
        if raw.startswith('; FEATURE:'):
            tag=raw[11:].strip().startswith('Support')
            continue
        parts=raw.split(';',1)[0].split()
        if not parts:continue
        cmd=parts[0]
        if cmd in ('M82','M83'):
            relative=cmd=='M83';continue
        if cmd=='G92':
            for field in parts[1:]:
                if field.startswith('E'):last_e=float(field[1:])
            continue
        if cmd not in ('G0','G1','G2','G3'):continue
        axes={v[0]:float(v[1:]) for v in parts[1:] if len(v)>1 and v[0] in 'XYE'}
        dest=np.array([axes.get('X',pos[0]),axes.get('Y',pos[1])])
        de=axes.get('E',0.) if relative else axes.get('E',last_e)-last_e
        if not relative:last_e=axes.get('E',last_e)
        if tag and de>0 and (not np.array_equal(pos,dest) or cmd in ('G2','G3')):
            nearest=min(centres,key=lambda n:np.sum(((pos+dest)/2-centres[n])**2))
            length[nearest]+=de
        pos=dest
    diameter=float(settings['filament_diameter'][0])
    density=float(settings['filament_density'][0])
    return {k:round(v*np.pi*(diameter/2)**2*density/1000,4) for k,v in length.items()}


def inspect(archive, frame, output, trace_roofs=False, *, other_objects=()):
    with ZipFile(archive) as z:
        assert not z.testzip()
        gcode=z.read('Metadata/plate_1.gcode').decode()
        plate=ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
        settings=json.loads(z.read('Metadata/project_settings.config'))
    data,features,_=q.extrusion_points(gcode,.12)
    if trace_roofs:
        lines,sequences,*_=roofs51.map_moves(q,gcode,len(data),step=.12)
    offset=np.fromstring(settings['extruder_offset'][0],sep='x')
    data[:,:2]+=offset
    labels=np.asarray(features)
    model_ids=np.where(~(np.char.startswith(labels,'Support') | np.char.startswith(labels,'Brim') | np.char.startswith(labels,'Skirt') | (labels=='Prime tower')))[0]
    support_ids=np.where(np.char.startswith(labels,'Support'))[0]
    fm=json.loads(frame.read_text())
    owners={x.get('name'):int(x.get('identify_id')) for x in plate.findall('object')}
    assert set(owners)==set(fm['parts']) | set(other_objects)
    results={}
    for name, owner in owners.items():
        if name in other_objects or name in ('Battery_End_Door','External_peel_support'):continue  # The lid has its own four-layer through-window test.
        model=(data[:,6]==owner) & np.isin(data[:,5],model_ids)
        peels=np.zeros(len(data),bool);prop_evidence={}
        if name=='Key_Carrier':
            peels,prop_evidence=printed_props51.native_mask(archive,q,data,owner,model_ids,sequences if trace_roofs else None)
            model&=~peels
        model_points=data[model]
        low=model_points[:,:2].min(0)-14
        high=model_points[:,:2].max(0)+14
        nearby=np.all((data[:,:2]>low+.6)&(data[:,:2]<high-.6),axis=1)
        support=(np.isin(data[:,5],support_ids) & nearby) | peels
        if name=='Key_Carrier' and 'External_peel_support' in owners:
            support |= (data[:,6]==owners['External_peel_support']) & np.isin(data[:,5],model_ids)
        shape=tuple(np.ceil((high-low)[::-1]/GRID).astype(int)+1)
        prev=np.zeros(shape,bool)
        support_below=deque(maxlen=3)
        lost=[];spans=[];bed=None;interface_area=0.;supported_layers=[];total_support=0.
        layer_numbers=np.rint(data[:,7]*5).astype(int)
        for layer in range(1,max(layer_numbers[model])+1):
            ids=np.flatnonzero(model & (layer_numbers==layer))
            layer_points=data[ids]
            m=footprint(layer_points,low,shape)
            s=footprint(data[support & (layer_numbers==layer)],low,shape)
            if layer==1:
                bed=round(m.sum()*GRID**2,2)
            else:
                below=dilation(prev,1)
                # Nominal top support gap can be rounded up to 0.4 mm with 0.2-mm layers.
                available=np.logical_or.reduce(list(support_below))
                if trace_roofs and len(ids):
                    support_underneath=dilation(available,1)
                    spans.extend(roofs51.inspect(layer,layer_points,low,GRID,dilation(prev,2),support_underneath,support_underneath,lines[ids],sequences[ids]))
                support_under=m & ~below & available
                if support_under.any():
                    area=support_under.sum()*GRID**2
                    interface_area+=area
                    supported_layers.append([layer,round(float(area),2)])
                # Flood just the portions which could be disconnected.
                substantial=m & ~dilation(below|available,3)
                if substantial.any():
                    # Classify only a component with zero model or support contact even under
                    # the tighter true one-cell registration allowance.
                    for item in lost_islands(m,below|available,low):
                        lost.append(dict(layer=layer,z_mm=round(layer*.2,2),**item))
            total_support+=s.sum()*GRID**2*.2
            support_below.append(s)
            prev=m
        results[name]=dict(owner=owner,source_sha256=fm['parts'][name]['source_sha256'],orientation=fm['parts'][name]['orientation'],
            model_bed_area_mm2=bed,support_occupancy_volume_mm3=round(float(total_support),2),
            support_occupancy_mass_estimate_g=round(float(total_support)*.00127,3),
            supported_area_summed_across_layers_mm2=round(float(interface_area),2),supported_layers=supported_layers,
            completely_unrooted_model_islands=lost,
            longer_unsupported_strokes=spans if trace_roofs else None,
            external_props=prop_evidence,
            bearing_space=bearing_space(data[model],fm['parts'][name]['assembly_to_machine'],name),
            protected_support=inspect_sensitive(data[support],fm['parts'][name]['assembly_to_machine'],name))
        print(name,bed,len(lost),round(float(total_support),1),flush=True)
    pvals={e.get('key'):e.get('value') for e in plate.findall('metadata')}
    native=json.loads(archive.with_suffix('.native.json').read_text())
    assert native['archive_sha256']==digest(archive)
    centres={name:data[(data[:,6]==owner)&np.isin(data[:,5],model_ids),:2].mean(0) for name,owner in owners.items() if name!="External_peel_support"}
    exact_mass=support_mass(gcode,settings,centres)
    for name,r in results.items():r['commanded_support_mass_g']=exact_mass[name]
    result=dict(archive_sha256=digest(archive),frame_sha256=digest(frame),parts=results,
        total_native_filament_g=float(pvals['weight']),native_seconds=int(pvals['prediction']),
        native_support_used=pvals['support_used'],warning=native['plates'][0].get('warning_message'),
        method='Positive native extrusion with 0.12 mm line/arc sampling, a 0.10 mm radial-width footprint raster and prior true layer/contact check. Model area calculated without brim. Support mass is a deposited occupancy estimate; native full-plate weight includes brim and tower. A connected overhang may still need backing.')
    output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('frame',type=Path);p.add_argument('output',type=Path);p.add_argument('--roofs',action='store_true')
    a=p.parse_args();inspect(a.archive,a.frame,a.output,a.roofs)
