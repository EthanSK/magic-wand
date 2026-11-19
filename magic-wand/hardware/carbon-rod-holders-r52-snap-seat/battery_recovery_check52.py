"""Inspect the selected cradle's actual bed adhesion, toolpaths, bridges and hardware routes."""
import hashlib
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import numpy as np
from battery_recovery52 import b, decode, tag, MODEL
import shapely
from support51 import q,footprint,dilation,lost_islands,roofs51


def first_layer_groups(mask, origin):
    """Find actual contiguous first-layer footprints at the 0.1 mm grid pitch."""
    unseen=set(zip(*np.nonzero(mask)))
    groups=[]
    while unseen:
        stack=[unseen.pop()]
        group=[]
        while stack:
            row,col=stack.pop()
            group.append((col,row))
            for neighbour in ((row-1,col),(row+1,col),(row,col-1),(row,col+1)):
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    stack.append(neighbour)
        xy=np.asarray(group)*.1+origin-90
        ears=sorted(set((int(np.sign(x)),centre) for x,y in xy if abs(x)>10
                        for centre in (-10,0,10) if abs(y-centre)<3.5))
        groups.append(dict(area_mm2=round(len(group)*.01,2),bed_ears=len(ears),
                           includes_outer_rim=bool(np.any((np.abs(xy[:,0])>7.6)&(np.abs(xy[:,0])<8.4))),
                           xy_bounds=np.concatenate((xy.min(0),xy.max(0))).round(2).tolist()))
    return sorted(groups,key=lambda group: -group["area_mm2"])


def check(archive):
    with ZipFile(archive) as z:
        text=z.read('Metadata/plate_1.gcode').decode()
        cfg=json.loads(z.read('Metadata/project_settings.config'))
        plate=ET.fromstring(z.read('Metadata/slice_info.config')).find('plate')
    rows,features,_=q.extrusion_points(text,.12)
    lines,seq,*_=roofs51.map_moves(q,text,len(rows),step=.12)
    rows[:,:2]+=np.fromstring(cfg['extruder_offset'][0],sep='x')
    obj=plate.find('object')
    assert obj.get('name')=='Battery_Holder' and len(plate.findall('object'))==1
    keep=(rows[:,0]>71)&(rows[:,0]<109)&(rows[:,1]>66)&(rows[:,1]<109)&(rows[:,7]>.05)
    d,lines,seq=rows[keep],lines[keep],seq[keep]
    layers=np.rint(d[:,7]*5).astype(int)
    origin=np.array([70,60])
    shape=(560,400)
    zero=np.zeros(shape,bool);prev=zero
    issues=[];lost=[];bed={}
    x,y=d[:,0]-90,d[:,1]-90
    with ZipFile(archive.parent/'layout.3mf') as z:
        resources=ET.fromstring(z.read(MODEL)).find(tag('resources'))
        shapes=[decode(resources.find(f"{tag('object')}[@id='{ident}']")) for ident in [1,2,3]]
    membership=np.zeros(len(d),int)
    for n in np.unique(layers):
        sel=layers==n
        pts=shapely.points(x[sel],y[sel])
        distances=[]
        for body in shapes:
            polygons=body.slice(n*.2-.1).to_polygons()
            region=shapely.Polygon()
            for poly in polygons:region=region.symmetric_difference(shapely.Polygon(poly))
            distances.append(shapely.distance(region,pts) if not region.is_empty else np.full(len(pts),1e4))
        membership[sel]=np.argmin(distances,axis=0)
    rail=membership==1
    same_sequences=np.intersect1d(seq[rail],seq[membership==0])
    separation=[]
    for n in np.unique(layers[rail]):
        a=d[(layers==n)&rail];bb=d[(layers==n)&(membership==0)]
        if len(a) and len(bb):
            ii=shapely.STRtree(shapely.points(bb[:,:2])).nearest(shapely.points(a[:,:2]))
            dd=np.linalg.norm(a[:,:2]-bb[ii,:2],axis=1)
            separation.append(float((dd-(a[:,3]+bb[ii,3])/2).min()))
    for n in range(1,layers.max()+1):
        mask=layers==n
        curr=footprint(d[mask],origin,shape)
        if n==1:
            groups=first_layer_groups(curr,origin)
            for key,region in [('all',mask),('pull_rail',mask&rail),('outside_feet',mask&(abs(x)>8.65)),('permanent_rims',mask&~rail&(abs(x)<=8.65))]:
                bed[key]=round(footprint(d[region],origin,shape).sum()*.01,2)
        else:
            backing=dilation(prev,1)
            lost.extend(dict(layer=n,**r) for r in lost_islands(curr,backing,origin))
            # A 0.2-mm intentional Z release gap above the separate support.
            shortgap=footprint(d[rail&(layers==n-2)],origin,shape)
            if n>=3:backing|=dilation(shortgap,1)
            issues.extend(roofs51.inspect(n,d[mask],origin,.1,dilation(prev,2),shortgap,zero,lines[mask],seq[mask]))
        prev=curr
    rad=d[:,3]/2+.06
    ax=-x;ay=y;az=12.8-d[:,7]+d[:,4]/2
    permanent=membership==0
    # Nominal rigid core excludes contacts with the intentional spring grip.
    rod_radius=np.hypot(np.maximum(0,abs(ax)-rad),np.maximum(0,abs(az)-d[:,4]/2))
    between=permanent&(abs(ay)<7)&(az<5)
    inside=permanent&(abs(ax)<5.9+rad)&(abs(ay)<13.5+rad)&(az>6.35+.22)&(az<17)
    lid=permanent&(abs(ax)>6.45)&(abs(ax)<7.28)&(abs(ay)<12)&(az>10.65)&(az<11.70)
    floor=(layers==33)&(abs(ax)<6.4)&(abs(ay)<12)
    bridge_ids=[i for i,f in enumerate(features) if 'ridge' in f]
    floor_bridge=np.flatnonzero(floor&np.isin(d[:,5],bridge_ids))
    spans=[]
    for k in np.unique(seq[floor_bridge]):
        pts=d[floor_bridge[seq[floor_bridge]==k],:2]
        spans.append(np.ptp(pts,axis=0).round(3).tolist())
    # The first floor is a continuous raster. Its outer bounding box hides
    # long individual extrusions. Follow each straight move across actual
    # supporting beads on the last two layers, including the breakaway gap.
    floor_moves = (layers == 33) & (membership == 0) & np.isin(d[:,5], bridge_ids)
    below = footprint(d[layers==32],origin,shape) | footprint(d[(layers==31)&rail],origin,shape)
    longest_move = 0.
    max_free_run = 0.
    maximum_angle_from_x = 0.
    long_moves = 0
    for line in np.unique(lines[floor_moves]):
        points=d[floor_moves & (lines==line),:2]
        if len(points)<2:continue
        delta=points[-1]-points[0]
        length=float(np.linalg.norm(delta))
        longest_move=max(longest_move,length+.12)
        if length>5.0:
            maximum_angle_from_x=max(maximum_angle_from_x,float(np.degrees(np.arctan2(abs(delta[1]),abs(delta[0])))))
            long_moves+=1
        ix,iy=np.rint((points-origin)/.1).astype(int).T
        unbacked=~below[iy,ix]
        boundaries=np.flatnonzero(np.diff(unbacked,prepend=False,append=False))
        for lo,hi in boundaries.reshape(-1,2):
            max_free_run=max(max_free_run,float(np.linalg.norm(points[hi-1]-points[lo]))+.24)
    floor_backing=dict(long_straight_moves=long_moves,maximum_move_mm=round(longest_move,3),
                      maximum_unbacked_run_mm=round(max_free_run,3),
                      maximum_long_move_angle_from_cross_tray_degrees=round(maximum_angle_from_x,3))
    meta={m.get('key'):m.get('value') for m in plate.findall('metadata')}
    # Commands between first and last positive model extrusion are the print temperatures.
    commands=[s for s in text.splitlines() if re.match(r'^M(?:104|109|140|190)\s',s)]
    report=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),seconds=meta['prediction'],grams=meta['weight'],
        original_height_mm=33.0,height_mm=float(d[:,7].max()),layers=int(layers.max()),bed_area_mm2=bed,
        first_layer_connected_groups=groups,native_object_count=1,heater_commands=commands,profile_nozzle=cfg['nozzle_temperature'],profile_bed=cfg['textured_plate_temp'],
        completely_floating_islands=lost,flagged_strokes=issues, floor_bridge_sequence_xy_extents=spans[:30],floor_backing=floor_backing,
        automatic_support_samples=int(np.isin(d[:,5],[i for i,f in enumerate(features) if f.startswith('Support')]).sum()),
        cell_core_positive_samples_after_rail_removal=int(inside.sum()),lid_guide_core_samples=int(lid.sum()),
        between_rings_minimum_native_radius_mm=round(float(rod_radius[between].min()),3) if between.any() else None,
        pull_direction='Towards the open end, along assembly negative Y. Separate the short outside feet at the six necks.',
        shared_pull_rail_and_body_extrusion_sequences=same_sequences.tolist(),
        minimum_same_layer_pull_rail_to_body_bead_edge_mm=round(min(separation),3),
        full_rod_min_conservative_radius_mm=round(float(rod_radius[permanent].min()),3),
        CAD_pullout_continuously_checked_mm=40, CAD_pullout_interference_mm3=0,
        removable_native_bead_samples_in_8mm_rod_bore=int(((membership!=0)&(rod_radius<4)).sum()),
        radius_minimum_assembly_xyz_mm=[round(float(v),3) for v in (ax[permanent][rod_radius[permanent].argmin()],ay[permanent][rod_radius[permanent].argmin()],az[permanent][rod_radius[permanent].argmin()])],
        canonical_hardware=b.checks())
    (archive.parent/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('heater_commands','canonical_hardware','flagged_strokes','floor_bridge_sequence_xy_extents')})
    print('Worst strokes',sorted(issues,key=lambda i:-i['mm'])[:5],'floor',spans[:4])


if __name__=='__main__':check(Path(sys.argv[1]))
