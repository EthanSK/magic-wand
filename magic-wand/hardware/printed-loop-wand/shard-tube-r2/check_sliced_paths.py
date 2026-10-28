#!/usr/bin/env python3
"""Independent prepared-path checks for Shard R2 functional clearances.

Reads actual 3MF normal meshes, transforms, extrusion widths, straight moves
and circular arcs. Source negatives define the intended empty spaces; actual
extrusions, not slicer modifier presence, establish the slice result. No
physical fit/force/strength claim is made. Outputs are exclusively created.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,math,re,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import trimesh
from manifold3d import Manifold,Mesh,CrossSection,JoinType
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
N={'m':NS}
XY_GUARD=.12
Z_GUARD=.10
Z_GRID=.05
WIDTH_GRID=.025


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def metadata(node):return {m.get('key'):m.get('value',m.text)for m in node.findall('metadata')}


def transform(text=None):
    t=np.eye(4)
    if text:
        q=np.asarray([float(v)for v in text.split()]).reshape(4,3)
        t[:3,:3]=q[:3].T;t[:3,3]=q[3]
    return t


def points(v,t):return np.asarray(v)@t[:3,:3].T+t[:3,3]


def solid(v,f):
    m=Manifold(Mesh(np.asarray(v,np.float32),np.asarray(f,np.uint32)))
    assert m.status().name=='NoError',('Invalid actual prepared normal mesh',str(m.status()))
    return m


def _truth(v):return str(v).lower()in('1','true','yes')


def objects(z,manifest,manifest_path):
    config=json.loads(z.read('Metadata/project_settings.config'))
    # Raw CLI projects may retain the process global1 while every object
    # explicitly disables support. Check effective object state and actual
    # extrusion; report global setting for final portable packaging.
    cfg=E.fromstring(z.read('Metadata/model_settings.config'))
    model=E.fromstring(z.read('3D/3dmodel.model'))
    assert model.get('unit','millimeter')=='millimeter'
    model_cache={'3D/3dmodel.model':model}
    pmap={p['name']:p for p in manifest['parts']}
    root_objects={o.get('id'):o for o in model.findall('m:resources/m:object',N)}
    settings={o.get('id'):o for o in cfg.findall('object')}
    labels={}
    for plate in cfg.findall('plate'):
        for inst in plate.findall('model_instance'):
            m=metadata(inst);labels[m['object_id']]=int(m.get('identify_id',m['object_id']))
    result=[]
    for item in model.findall('m:build/m:item',N):
        if item.get('printable','1')=='0':continue
        rid=item.get('objectid');o=settings[rid];meta=metadata(o);name=meta['name']
        assert name in pmap,('Prepared part absent from manifest',name)
        support_enabled=_truth(meta.get('enable_support',config.get('enable_support','0')))
        if support_enabled:
            assert name=='Sense_Open_Cradle' and 'manual' in str(meta.get('support_type','')),('Only manual head support is allowed',name,meta)
        sub=o.findall('part');normal=[a for a in sub if a.get('subtype')=='normal_part'];helpers=[a for a in sub if a.get('subtype')!='normal_part']
        assert len(normal)==1,('Expected one actual normal mesh',name,[a.attrib for a in sub])
        assert not helpers or(name=='Sense_Open_Cradle' and all(a.get('subtype')in('support_blocker','support_enforcer')for a in helpers)),('Only clearly typed head printing helpers allowed',name,[a.attrib for a in helpers])
        comps=root_objects[rid].findall('m:components/m:component',N)
        comp=next(a for a in comps if a.get('objectid')==normal[0].get('id'));cid=comp.get('objectid')
        path=next((v for k,v in comp.attrib.items()if k.endswith('}path')or k=='path'),'3D/3dmodel.model').lstrip('/')
        if path not in model_cache:model_cache[path]=E.fromstring(z.read(path))
        child=next(v for v in model_cache[path].findall('m:resources/m:object',N)if v.get('id')==cid)
        verts=np.array([[float(v.get(k))for k in 'xyz']for v in child.findall('m:mesh/m:vertices/m:vertex',N)])
        faces=np.array([[int(v.get(k))for k in('v1','v2','v3')]for v in child.findall('m:mesh/m:triangles/m:triangle',N)])
        component_local=points(verts,transform(comp.get('transform')))
        archive_build=transform(item.get('transform'))
        plate_vertices=points(component_local,archive_build)
        p=pmap[name];ta=np.asarray(p['print_to_assembly']);source_path=manifest_path.parent/p['file']
        assert sha(source_path)==p['sha256'],('Export SHA mismatch',name)
        mesh=trimesh.load_mesh(source_path,process=True)
        # Bambu can place its centering translation in either child/component
        # OR build transform. Recover actual placement from full composed
        # mesh, then independently verify the entire translated solid.
        placement=(plate_vertices.min(0)+plate_vertices.max(0)-mesh.vertices.min(0)-mesh.vertices.max(0))/2
        local=plate_vertices-placement
        bbox_error=float(np.max(np.abs(np.r_[local.min(0),local.max(0)]-np.r_[mesh.vertices.min(0),mesh.vertices.max(0)])))
        assert bbox_error<.025,('Prepared coordinates changed unexpectedly',name,bbox_error)
        actual=solid(local,faces);expected=solid(mesh.vertices,mesh.faces)
        difference=abs((actual-expected).volume())+abs((expected-actual).volume())
        assert difference<.08,('Actual prepared mesh differs from exported STL',name,difference)
        tb=np.eye(4);tb[:3,3]=placement;tf=ta@np.linalg.inv(tb)
        result.append({'name':name,'root_id':rid,'identify_id':labels.get(rid,int(rid)),
                       'print_to_assembly':ta,'plate_to_assembly':tf,'build':tb,
                       'print_bbox':np.array([local.min(0),local.max(0)]),
                       'mesh_difference_mm3':difference,'bbox_error_mm':bbox_error,'actual_normal_solid':actual,
                       'support_enabled':support_enabled,'printing_helpers':[{'type':a.get('subtype'),'name':metadata(a).get('name','')}for a in helpers]})
    off=config.get('extruder_offset',['0x0'])[0]
    offset=np.array([float(a)for a in off.split('x')]+[0.])
    assert len(offset)==3,('Unknown extruder offset',off)
    return result,offset,config


def _arc(start,end,d,clockwise):
    if 'I'in d or 'J'in d:
        centre=start[:2]+[d.get('I',0.),d.get('J',0.)]
    elif 'R'in d:
        radius=abs(d['R']);chord=end[:2]-start[:2];length=np.linalg.norm(chord)
        assert length>1e-8 and length<=2*radius+1e-5,('Invalid R arc',d)
        normal=np.array([-chord[1],chord[0]])/length;mid=(start[:2]+end[:2])/2
        height=math.sqrt(max(0.,radius*radius-length*length/4))
        candidates=[mid+height*normal,mid-height*normal];centre=None
        for candidate in candidates:
            aa=math.atan2(start[1]-candidate[1],start[0]-candidate[0]);bb=math.atan2(end[1]-candidate[1],end[0]-candidate[0])
            sweep=-((aa-bb)%(2*math.pi))if clockwise else(bb-aa)%(2*math.pi)
            if (abs(sweep)>math.pi)==(d['R']<0):centre=candidate;break
        assert centre is not None,('Ambiguous R arc',d)
    else:raise AssertionError(('Extruding arc has no centre or radius',d))
    radius=float(np.linalg.norm(start[:2]-centre));aa=math.atan2(start[1]-centre[1],start[0]-centre[0]);bb=math.atan2(end[1]-centre[1],end[0]-centre[0])
    sweep=-((aa-bb)%(2*math.pi))if clockwise else(bb-aa)%(2*math.pi)
    if abs(sweep)<1e-10 and np.linalg.norm(end[:2]-start[:2])<1e-7:sweep=-2*math.pi if clockwise else 2*math.pi
    return centre,radius,aa,sweep


def extrusion_points(text,step,default_width=.42,default_height=.2):
    pos=np.zeros(3);relative_e=True;relative_xyz=False;last_e=0.;feature='';width=default_width;height=default_height;object_id=-1
    features=[];feature_ids={};rows=[];counts=collections.Counter();line_count=0;arc_count=0;support_moves=0;layer_top=None
    for line in text.splitlines():
        if line.startswith('; FEATURE:'):feature=line[11:].strip();continue
        if line.startswith('; LINE_WIDTH:'):width=float(line.split(':',1)[1]);continue
        if line.startswith('; LAYER_HEIGHT:'):height=float(line.split(':',1)[1]);continue
        if line.startswith('; Z_HEIGHT:'):layer_top=float(line.split(':',1)[1]);continue
        if line.startswith('; start printing object, unique label id:'):object_id=int(line.rsplit(':',1)[1]);continue
        if line.startswith('; stop printing object, unique label id:'):object_id=-1;continue
        raw=line.split(';')[0].strip().split()
        if not raw:continue
        cmd=raw[0]
        if cmd=='M83':relative_e=True
        if cmd=='M82':relative_e=False
        if cmd=='G90':relative_xyz=False
        if cmd=='G91':relative_xyz=True
        if cmd not in ('G0','G1','G2','G3','G92'):continue
        d={s[0]:float(s[1:])for s in raw[1:]if len(s)>1 and s[0]in'XYZEIJR'}
        if cmd=='G92':
            last_e=d.get('E',last_e)
            for i,k in enumerate('XYZ'):
                if k in d:assert object_id<0,('G92 XYZ inside model paths',line);pos[i]=d[k]
            continue
        end=pos+np.array([d.get(k,0.)for k in'XYZ'])if relative_xyz else np.array([d.get(k,pos[i])for i,k in enumerate('XYZ')])
        delta_e=d.get('E',0.)if relative_e else d.get('E',last_e)-last_e
        if not relative_e:last_e=d.get('E',last_e)
        if delta_e>0 and feature not in ('','Custom','Flush'):
            if feature.startswith('Support'):support_moves+=1
            if cmd in('G2','G3'):
                centre,r,aa,sweep=_arc(pos,end,d,cmd=='G2');length=math.hypot(abs(sweep)*r,end[2]-pos[2]);n=max(2,int(math.ceil(length/step))+1);f=np.linspace(0,1,n);angles=aa+sweep*f
                xyz=np.c_[centre[0]+r*np.cos(angles),centre[1]+r*np.sin(angles),pos[2]+(end[2]-pos[2])*f];arc_count+=1
            else:
                length=float(np.linalg.norm(end-pos))
                if length<1e-7:pos=end;continue
                n=max(2,int(math.ceil(length/step))+1);xyz=pos+(end-pos)*np.linspace(0,1,n)[:,None];line_count+=1
            assert 0.<width<2. and 0.<height<1.,('Unknown extrusion dimensions',width,height)
            if feature not in feature_ids:feature_ids[feature]=len(features);features.append(feature)
            rows.append(np.c_[xyz,np.full(n,width),np.full(n,height),np.full(n,feature_ids[feature]),np.full(n,object_id),np.full(n,layer_top if layer_top is not None else end[2])].astype(np.float32));counts[feature]+=n
        pos=end
    assert rows,'No positive extrusion paths in archive'
    return np.concatenate(rows),features,{'straight_extruding_moves':line_count,'arc_extruding_moves':arc_count,'support_extruding_moves':support_moves,'feature_samples':dict(counts)}


def clearance_regions(model,name,record=None):
    c=model.c;ds=model.ds;cp=model.cp
    if name=='Switch_Fit_Test' and record is not None and np.min(np.asarray(record.get('assembly_vertices',[[0,0,0]]))[:,2])>90.:
        return clearance_regions(model,'Grip_Left')
    if name in('Grip_Left','Grip_Right','Loop_Upper_Socket_Test'):
        right=name=='Grip_Right';hd=model.handle_module();parts={
            'full_bottom_cell_sled_loading':model.cell_loading_void(),
            'main_10_4mm_wire_bore':c.cyl(c.BORE/2,59.5,177.),
            'female_screw_mouth_and_groove':cp.female_socket_void(c),
            'handle_hooks_and_keeper':hd.receiver_void(c)}
        for button,a,z in model.hand_buttons(right):
            parts[button+'_all_baked_switch_clearances']=ds.void(c,a,z)
            # The true continuous service route includes the offset solder tabs.
            parts[button+'_socket_installation_sweep']=c.union([c.mount_local(v,a,z)for v in ds.socket_route(c).values()])
            parts[button+'_purchased_hardware']=c.union(list(ds.hardware(c,a,z).values()))
        return parts
    if name=='Switch_Fit_Test':return {'baked_switch_voids':ds.local_void(c),'socket_installation_sweep':c.union(list(ds.socket_route(c).values())),'purchased_switch_socket':c.union(list(ds.local_hardware(c).values()))}
    if name in('Removable_Finger_Loop','Loop_Upper_Hook_Test'):
        return {'quarter_turn_key_hole':model.handle_module().build(c).key_entry_hole()}
    if name=='Thread_Gauge':return {'female_thread_core_and_groove':cp.female_socket_void(c)}
    if name.startswith('Battery_Screw_Cap_'):
        # The lower cap floor and weighted extension are intentionally closed.
        return {'open_neck_above_closed_floor':c.cyl(10.4,3.0,10.)}
    if name=='Continuous_Shaft':return {'wire_bore':c.cyl(c.BORE/2,159.,353.),'lower_bayonet_socket':c.female_at(c.HANDLE_END)}
    if name=='Sense_Open_Cradle':
        cavities={'sleeve_and_wire_route':c.cyl(6.6,342.5,352.25)+c.cyl(5.2,352.2,371.),
                  'board':c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,376.,397.),
                  'solder':c.box(-5.4,5.4,c.BOARD_Y-6.,c.BOARD_Y-.25,379.,394.),
                  'usb':c.box(-5.7,5.7,c.BOARD_Y-.8,c.BOARD_Y+4.8,397.3,411.),
                  'forward_wires':c.cyl(2.7,375.,387.5).translate((0,2.,0))}
        entry=c.union([c.local(c.box(-1.3,1.3,5.9,8.45,342.5,349.3),-40.+a,0.)for a in(0.,180.)])
        turns=[]
        for side in(0.,180.):
            p=[(0.,0.)]+[(10*math.sin(math.radians(a+side)),10*math.cos(math.radians(a+side)))for a in range(10,-51,-2)]
            wedge=Manifold.extrude(CrossSection([p]),2.6).translate((0,0,346.7));turns.append(wedge^(c.cyl(8.45,346.7,349.3)-c.cyl(5.9,346.7,349.3)))
        cavities['sleeve_tabs_entry_and_turn']=entry+c.union(turns)
        return cavities
    return {}


def _inside(cs,xy):
    inside=np.zeros(len(xy),bool)
    if not len(xy)or cs.is_empty():return inside
    lo,bot,hi,top=cs.bounds();eligible=(xy[:,0]>=lo)&(xy[:,0]<=hi)&(xy[:,1]>=bot)&(xy[:,1]<=top);ids=np.flatnonzero(eligible)
    if not len(ids):return inside
    x,y=xy[ids].T;hit=np.zeros(len(ids),bool)
    for poly in cs.to_polygons():
        q=np.zeros(len(ids),bool)
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            if abs(b[1]-a[1])<1e-12:continue
            q^=((a[1]>y)!=(b[1]>y))&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
        hit^=q
    inside[ids]=hit
    return inside


def inspect_region(region,xyz,width,height,feature,features,assembly_tf,limit=8,allow_external_solder_support=False):
    box=np.asarray(region.bounding_box());lo=box[:3];hi=box[3:]
    # Full bead discs are evaluated at the layer middle. Layer rounding error
    # is <=0.025mm, smaller than the independent 0.10mm vertical boundary guard.
    mid=xyz[:,2]-height/2
    cand=np.all(xyz[:,:2]>=lo[:2]-width[:,None]/2,axis=1)&np.all(xyz[:,:2]<=hi[:2]+width[:,None]/2,axis=1)&(mid>lo[2]+Z_GUARD)&(mid<hi[2]-Z_GUARD)
    ids=np.flatnonzero(cand);bad=[]
    if not len(ids):return {'checked_samples':0,'violations':{},'removable_external_support_samples':0,'examples':[]}
    zkey=np.rint(mid[ids]/Z_GRID).astype(np.int32);order=np.argsort(zkey);ids=ids[order];zkey=zkey[order]
    bounds=np.r_[0,np.flatnonzero(np.diff(zkey))+1,len(ids)]
    for a,b in zip(bounds[:-1],bounds[1:]):
        group=ids[a:b];zz=float(zkey[a])*Z_GRID
        # A robust interior excludes numerical contacts and intentional roofs.
        section=region.slice(zz-Z_GUARD)^region.slice(zz)^region.slice(zz+Z_GUARD)
        if section.is_empty():continue
        radii=np.ceil(width[group]/2/WIDTH_GRID)*WIDTH_GRID
        for rr in np.unique(radii):
            subset=group[radii==rr]
            # Minkowski expansion tests the ENTIRE bead disc, not just eight
            # sampled directions. Width is rounded outward by <=0.05mm total.
            protected=section.offset(float(rr)-XY_GUARD,JoinType.Round)
            hit=_inside(protected,xyz[subset,:2]);bad.extend(subset[hit].tolist())
    bad=np.asarray(sorted(set(bad)),np.int64)
    external_count=0
    if allow_external_solder_support and len(bad):
        assembly=points(xyz[bad],assembly_tf)
        disc_y=math.hypot(float(assembly_tf[1,0]),float(assembly_tf[1,1]))
        front_y=assembly[:,1]+width[bad]/2*disc_y+np.maximum(0.,-height[bad]*float(assembly_tf[1,2]))
        external=np.array([features[int(i)].startswith('Support')for i in feature[bad]])&(front_y<=-7.8)
        external_count=int(external.sum());bad=bad[~external]
    counts=collections.Counter(features[int(i)]for i in feature[bad])
    examples=[]
    for i in bad[:limit]:
        q=points(xyz[i:i+1],assembly_tf)[0]
        examples.append({'assembly_xyz_mm':np.round(q,4).tolist(),'feature':features[int(feature[i])],'line_width_mm':round(float(width[i]),4),'layer_height_mm':round(float(height[i]),4)})
    return {'checked_samples':len(ids),'violations':dict(counts),'removable_external_support_samples':external_count,'external_support_exception':'Support-only bead entirely behind assemblyY=-7.8, accessible and removed before electronics; no printed material exception'if allow_external_solder_support else None,'examples':examples}


def inspect_layer_starts(mesh,xyz,height,feature,features,layer_top,assembly_tf,width=None,support_gap=.2):
    """Detect actual printed islands with no previous-layer support.

    Uses actual prepared mesh sections at real G-code layer heights, and only
    counts islands receiving real model extrusion. A 0.25mm overlap allowance
    avoids treating normal 45-degree growth as an unsupported start. Broad
    partially unsupported areas are reported for review, not confused with
    floating islands or declared impossible bridges.
    """
    real=np.array([not features[int(f)].startswith(('Brim','Skirt','Support'))for f in feature])
    support=np.array([features[int(f)].startswith('Support')for f in feature])
    if width is None:width=np.full(len(xyz),.42)
    ids=np.flatnonzero(real)
    if not len(ids):return {'checked_layers':0,'floating_components':[],'support_backed_islands':[],'largest_unbacked_layers':[]}
    keys=np.rint(layer_top[ids]*10000).astype(np.int32);order=np.argsort(keys);ids=ids[order];keys=keys[order]
    groups=np.r_[0,np.flatnonzero(np.diff(keys))+1,len(ids)];floating=[];supported=[];overhang=[];previous_top=None;checked=0
    for a,b in zip(groups[:-1],groups[1:]):
        group=ids[a:b];top=float(keys[a])/10000;hh=float(np.min(height[group]))
        if previous_top is not None and top>previous_top:hh=min(hh,top-previous_top)
        mid=top-hh/2
        current=mesh.slice(mid)
        if current.is_empty():continue
        checked+=1
        if previous_top is None and top<=hh+.06:
            previous_top=top;continue  # Actual build-plate-supported first layer.
        previous=mesh.slice(mid-hh)if previous_top is not None and abs(top-previous_top-hh)<.06 else CrossSection()
        backed=previous.offset(.25,JoinType.Round)
        unsupported=current-backed
        area=unsupported.area()
        if area>2.:
            overhang.append({'layer_top_mm':round(top,4),'unbacked_mesh_area_mm2':round(area,4),'note':'partial overhang/bridge review; not alone a floating start'})
        for component in current.decompose():
            if component.area()<.15 or(component^backed).area()>.01:continue
            if not _inside(component.offset(.3,JoinType.Round),xyz[group,:2]).any():continue
            bx=component.bounds();centre=np.array([[(bx[0]+bx[2])/2,(bx[1]+bx[3])/2,mid]])
            item={'layer_top_mm':round(top,4),'area_mm2':round(component.area(),4),'print_xy_bounds_mm':[round(float(v),4)for v in bx],'assembly_centre_mm':np.round(points(centre,assembly_tf)[0],4).tolist()}
            support_ids=np.flatnonzero(support&(xyz[:,2]>=top-hh-support_gap-.6*hh)&(xyz[:,2]<=top-hh+.06))
            backed_by_support=False
            if len(support_ids):
                possible=component.offset(float(width[support_ids].max())/2+.10,JoinType.Round)
                hits=_inside(possible,xyz[support_ids,:2])
                if hits.any():
                    item['actual_support_top_z_mm']=round(float(xyz[support_ids[hits],2].max()),4);supported.append(item);backed_by_support=True
            if not backed_by_support:floating.append(item)
        previous_top=top
    return {'checked_layers':checked,'overlap_allowance_mm':.25,'minimum_island_area_mm2':.15,
            'floating_components':floating,'support_backed_islands':supported,'largest_unbacked_layers':sorted(overhang,key=lambda q:q['unbacked_mesh_area_mm2'],reverse=True)[:12],
            'limitation':'Mesh-supported layer-island audit correlated with actual extrusion, not thermal/bridge/strength simulation. Review broad overhangs separately.'}


def inspect(project,manifest_path,step):
    manifest_bytes=manifest_path.read_bytes();manifest=json.loads(manifest_bytes);part_records={p['name']:p for p in manifest['parts']};model=load('shard_r2_path_model',HERE/'wand_cad.py')
    with zipfile.ZipFile(project)as z:
        assert z.testzip()is None,'Invalid 3MF ZIP'
        objs,offset,config=objects(z,manifest,manifest_path)
        files=[n for n in z.namelist()if re.fullmatch(r'Metadata/plate_\d+\.gcode',n)];assert len(files)==1,('Expected one sliced plate',files)
        data,features,stats=extrusion_points(z.read(files[0]).decode(),step,float(config.get('line_width','.42')),float(config.get('layer_height','.2')))
    report={'project':project.name,'sha256':sha(project),'manifest_sha256':hashlib.sha256(manifest_bytes).hexdigest(),'used_part_stl_sha256':{o['name']:part_records[o['name']]['sha256']for o in objs},'checker_sha256':sha(Path(__file__)),'region_source_hashes':{p.name:sha(p)for p in[HERE/'wand_cad.py',HERE/'direct_switches.py',HERE/'handle_design.py',HERE/'cap_design.py']},
            'path_sample_step_mm':step,'extruder_offset_mm':offset[:2].tolist(),
            'bead_check':{'line_width':'actual per-move LINE_WIDTH, full circular XY footprint','height':'actual LAYER_HEIGHT; layer-middle discs','xy_boundary_tolerance_mm':XY_GUARD,'z_boundary_tolerance_mm':Z_GUARD,'z_quantisation_mm':Z_GRID,'maximum_full_width_rounding_mm':2*WIDTH_GRID},
            'path_samples':len(data),'stats':stats,'global_enable_support':str(config.get('enable_support','0')),'manual_head_supports_only':True,'parts':{},'physical_fit_verified':False}
    support_rows=np.array([features[int(v)].startswith('Support')for v in data[:,5]])
    if support_rows.any():
        allowed=np.zeros(int(support_rows.sum()),bool);support_xyz=data[support_rows,:3]+offset
        for head in [o for o in objs if o['name']=='Sense_Open_Cradle' and o['support_enabled']]:
            q=points(support_xyz,np.linalg.inv(head['build']));bb=head['print_bbox']
            allowed|=np.all(q[:,:2]>=bb[0,:2]-8.,axis=1)&np.all(q[:,:2]<=bb[1,:2]+8.,axis=1)&(q[:,2]>=-.05)&(q[:,2]<=bb[1,2]+.3)
        assert allowed.all(),('Support extrusion outside the one permitted head region',int((~allowed).sum()))
    for obj in objs:
        name=obj['name'];it=np.linalg.inv(obj['build']);xyz=points(data[:,:3]+offset,it)
        bb=obj['print_bbox'];r=data[:,3]/2
        if name=='Sense_Open_Cradle':r=np.maximum(r,8.)
        mask=np.all(xyz>=bb[0]-np.c_[r,r,data[:,4]],axis=1)&np.all(xyz<=bb[1]+np.c_[r,r,data[:,4]],axis=1)
        ii=np.flatnonzero(mask);sample=xyz[ii];w=data[ii,3];h=data[ii,4];f=data[ii,5].astype(np.int16)
        assert len(ii)>0,('Prepared object has no actual model paths',name)
        model_rows=np.array([not features[int(v)].startswith(('Brim','Skirt','Support'))for v in f])
        assert model_rows.any(),('Prepared object has only brim/skirt',name)
        top_error=abs(float(sample[model_rows,2].max())-float(bb[1,2]))
        assert top_error<max(.32,float(h.max())*1.5),('Sliced paths do not reach object top',name,top_error)
        regions=clearance_regions(model,name,part_records[name]);pr=np.linalg.inv(obj['print_to_assembly'])
        checks={}
        for key,m in regions.items():
            # Clip to the physical part extent so an imaginary continuation of
            # a clearance cannot attribute neighbouring print paths to a part.
            m=m.transform(pr[:3,:])
            checks[key]=inspect_region(m,sample,w,h,f,features,obj['print_to_assembly'],allow_external_solder_support=(name=='Sense_Open_Cradle'and key=='solder'))
        assert np.max(np.abs(obj['build'][2,:3]-[0.,0.,1.]))<1e-8,'Unexpected tilted build axis'
        starts=inspect_layer_starts(obj['actual_normal_solid'],sample,h,f,features,data[ii,7]-obj['build'][2,3],obj['print_to_assembly'],w,float(config.get('support_top_z_distance','.2')))
        report['parts'][str(obj['identify_id'])+':'+name]={'layer_start_audit':starts,'support_enabled':obj['support_enabled'],'printing_helpers':obj['printing_helpers'],'normal_mesh_difference_mm3':round(obj['mesh_difference_mm3'],6),'prepared_bbox_error_mm':round(obj['bbox_error_mm'],6),'candidate_samples':len(ii),'sliced_top_error_mm':round(top_error,5),'checks':checks}
        print(name+': '+str(len(checks))+' protected regions; '+str(sum(bool(q['violations'])for q in checks.values()))+' intrusion regions; '+str(len(starts['floating_components']))+' unsupported starts',flush=True)
    report['passed']=all(not c['violations']for p in report['parts'].values()for c in p['checks'].values()) and all(not p['layer_start_audit']['floating_components']for p in report['parts'].values())
    return report


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,action='append',required=True);ap.add_argument('--manifest',type=Path,default=HERE/'exports/manifest.json');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--step',type=float,default=.35);args=ap.parse_args()
    assert 0.<args.step<=.5
    assert not args.out.exists(),('Preserve previous report',args.out)
    reports=[]
    for p in args.project:
        if not p.exists():p=ROOT/'magic-wand-3d-models'/p
        reports.append(inspect(p,args.manifest,args.step))
    result={'projects':reports,'passed':all(r['passed']for r in reports),'limitations':'Sampled extrusion paths with actual XY bead-width envelopes and explicit boundary guards. Does not certify printed fit, strength, full bead cross-section or thermal sag.'}
    with args.out.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
    assert result['passed'],'Actual extrusions enter protected clearances; inspect saved report'
    print('All prepared-path checks passed',flush=True)

if __name__=='__main__':main()
