#!/usr/bin/env python3
"""PETG projects with baked physical openings. Only the unchanged cradle uses clearly labelled print-support helpers."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,subprocess,sys,zipfile,xml.etree.ElementTree as E
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'v20'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';E.register_namespace('',NS)
tag=lambda s:'{'+NS+'}'+s

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def projects():
    core=['Continuous_Shaft','Sense_Open_Cradle','Battery_Sled','Removable_Finger_Loop','Loop_Keeper_Key']
    return {
      'complete-both-hands':(['Grip_Left','Grip_Right']+core+['Battery_Screw_Cap_Light','Battery_Screw_Cap_Weighted'],[(35,55),(80,55),(125,55),(175,55),(225,170),(75,185),(160,145),(220,55),(220,100)]),
      'one-left-light':(['Grip_Left']+core+['Battery_Screw_Cap_Light'],[(35,55),(125,55),(175,55),(225,170),(75,185),(160,145),(220,55)]),
      'one-left-weighted':(['Grip_Left']+core+['Battery_Screw_Cap_Weighted'],[(35,55),(125,55),(175,55),(225,170),(75,185),(160,145),(220,55)]),
      'replacement-lower-both-hands':(['Grip_Left','Grip_Right','Battery_Sled','Removable_Finger_Loop','Loop_Keeper_Key','Battery_Screw_Cap_Light','Battery_Screw_Cap_Weighted'],[(35,55),(80,55),(225,170),(75,185),(160,145),(220,55),(220,100)]),
      'fit-tests':(['Switch_Fit_Test','Loop_Upper_Socket_Test','Loop_Upper_Hook_Test','Loop_Keeper_Key','Thread_Gauge','Battery_Screw_Cap_Light'],[(35,45),(80,45),(125,45),(170,45),(70,110),(120,110)]),
      'weighted-cap-only':(['Battery_Screw_Cap_Weighted'],[(128,128)])}

def settings():
    cfg=json.loads((HERE/'print-settings/project.json').read_text())
    cfg.update({'enable_support':'0','brim_type':'outer_only','brim_width':'4','brim_object_gap':'0.2','wall_loops':'3','sparse_infill_density':'20%'})
    keep={'enable_support','brim_type','brim_width','brim_object_gap','wall_loops','sparse_infill_density','layer_height'}
    diff=cfg.get('different_settings_to_system',['','','']);diff[0]=';'.join(sorted(set(filter(None,diff[0].split(';')))|keep));cfg['different_settings_to_system']=diff
    return cfg

def head_helpers():
    spec=importlib.util.spec_from_file_location('r2_print_cad',HERE/'wand_cad.py');w=importlib.util.module_from_spec(spec);sys.modules[spec.name]=w;spec.loader.exec_module(w);c=w.c
    zones=[c.box(-10,10,-9.6,-6.85,352.5,369.),c.box(-14,14,-7.2,-6.85,374.8,375.6)]
    for sign in (-1,1):zones.append(c.box(sign*11.5-3.,sign*11.5+3.,-8.2,-6.85,369.,399.))
    # Retain the already checked main-head recipe. These are PRINT supports,
    # never negative volumes defining the board slot or the physical model.
    blocked=c.union([c.cyl(8.5,342.5,411.),c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,397.),c.box(-5.4,5.4,c.BOARD_Y-6.,c.BOARD_Y-.25,379.,394.),c.box(-5.8,5.8,c.BOARD_Y-.9,c.BOARD_Y+4.9,397.3,411.),c.cyl(2.9,375.,387.5).translate((0.,2.,0.)),c.box(-12.5,12.5,-7.,-4.,373.5,374.7)])
    return [('support_enforcer','PRINT SUPPORT ONLY - low back',c.union(zones)),('support_blocker','KEEP PRINT SUPPORT OUT - board USB wire and lock',blocked)]

def make(names,centers,dest,manifest):
    parts={p['name']:p for p in manifest['parts']};model=E.Element(tag('model'),unit='millimeter',attrib={'xml:lang':'en-US'});E.SubElement(model,tag('metadata'),name='Application').text='BambuStudio-02.08.04.57'
    resources=E.SubElement(model,tag('resources'));build=E.SubElement(model,tag('build'));cfg=E.Element('config');ident=0;rootids=[];bounds=[]
    for name,center in zip(names,centers):
        p=parts[name];tf=np.asarray(p['print_to_assembly']);it=np.linalg.inv(tf);v=np.asarray(p['assembly_vertices']);verts=v@it[:3,:3].T+it[:3,3];faces=p['assembly_faces']
        ident+=1;child=ident;o=E.SubElement(resources,tag('object'),id=str(child),type='model',name=name);mesh=E.SubElement(o,tag('mesh'));vs=E.SubElement(mesh,tag('vertices'));ts=E.SubElement(mesh,tag('triangles'))
        for q in verts:E.SubElement(vs,tag('vertex'),**{k:format(float(x),'.9g')for k,x in zip('xyz',q)})
        for q in faces:E.SubElement(ts,tag('triangle'),v1=str(q[0]),v2=str(q[1]),v3=str(q[2]))
        ident+=1;rootid=ident;rootids.append(rootid);o=E.SubElement(resources,tag('object'),id=str(rootid),type='model',name=name);comps=E.SubElement(o,tag('components'));E.SubElement(comps,tag('component'),objectid=str(child))
        obj=E.SubElement(cfg,'object',id=str(rootid));E.SubElement(obj,'metadata',key='name',value=name);E.SubElement(obj,'metadata',key='extruder',value='1');E.SubElement(obj,'metadata',key='enable_support',value='1'if name=='Sense_Open_Cradle'else'0')
        if name=='Sense_Open_Cradle':
            E.SubElement(obj,'metadata',key='support_type',value='normal(manual)');E.SubElement(obj,'metadata',key='bridge_no_support',value='1')
        if name in ['Switch_Fit_Test','Loop_Upper_Socket_Test']:E.SubElement(obj,'metadata',key='brim_type',value='no_brim')
        if name in ['Removable_Finger_Loop','Loop_Upper_Hook_Test','Loop_Keeper_Key']:E.SubElement(obj,'metadata',key='sparse_infill_density',value='100%')
        if name=='Battery_Screw_Cap_Weighted':
            for k,val in {'sparse_infill_density':'45%','sparse_infill_pattern':'gyroid','wall_loops':'3','top_shell_layers':'5','bottom_shell_layers':'5'}.items():E.SubElement(obj,'metadata',key=k,value=val)
        part=E.SubElement(obj,'part',id=str(child),subtype='normal_part');E.SubElement(part,'metadata',key='name',value=name)
        if name=='Sense_Open_Cradle':
            for role,title,helper in head_helpers():
                mm=helper.to_mesh();hv=np.asarray(mm.vert_properties)[:,:3]@it[:3,:3].T+it[:3,3]
                ident+=1;hid=ident;ho=E.SubElement(resources,tag('object'),id=str(hid),type='model',name=title);hm=E.SubElement(ho,tag('mesh'));hvs=E.SubElement(hm,tag('vertices'));hfs=E.SubElement(hm,tag('triangles'))
                for q in hv:E.SubElement(hvs,tag('vertex'),**{k:format(float(x),'.9g')for k,x in zip('xyz',q)})
                for q in mm.tri_verts:E.SubElement(hfs,tag('triangle'),v1=str(q[0]),v2=str(q[1]),v3=str(q[2]))
                E.SubElement(comps,tag('component'),objectid=str(hid));hp=E.SubElement(obj,'part',id=str(hid),subtype=role);E.SubElement(hp,'metadata',key='name',value=title)
        E.SubElement(build,tag('item'),objectid=str(rootid),transform=f'1 0 0 0 1 0 0 0 1 {center[0]} {center[1]} 0',printable='1')
        lo=verts.min(axis=0)+[center[0],center[1],0];hi=verts.max(axis=0)+[center[0],center[1],0];assert min(lo[:2])>=5 and max(hi[:2])<=250 and hi[2]<=250,(name,lo,hi)
        bounds.append((name,lo,hi))
    for i,(a,al,ah)in enumerate(bounds):
        for b,bl,bh in bounds[i+1:]:assert not all(min(ah[k],bh[k])-max(al[k],bl[k])>0 for k in range(2)),('plate parts overlap',a,b)
    plate=E.SubElement(cfg,'plate');E.SubElement(plate,'metadata',key='plater_id',value='1');E.SubElement(plate,'metadata',key='plater_name',value='Shard Tube R2 - integral seats - open battery - plain meshes')
    for objid in rootids:
        ins=E.SubElement(plate,'model_instance')
        for k,val in [('object_id',str(objid)),('instance_id','0'),('identify_id',str(objid))]:E.SubElement(ins,'metadata',key=k,value=val)
    E.SubElement(cfg,'assemble')
    with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED)as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',E.tostring(model,encoding='utf-8',xml_declaration=True));z.writestr('Metadata/model_settings.config',E.tostring(cfg,encoding='utf-8',xml_declaration=True));z.writestr('Metadata/project_settings.config',json.dumps(settings(),indent=2))

def build(out,do_slice=False,only=None):
    out.mkdir(parents=True,exist_ok=False);m=json.loads((HERE/'exports/manifest.json').read_text());results={}
    for label,(names,centers) in projects().items():
        if only and label!=only:continue
        filename='Print-Shard-R2-'+label+'.3mf';layout=out/(label+'-layout.3mf');make(names,centers,layout,m)
        if not do_slice:results[label]={'file':layout.name,'parts':names,'centers':centers};continue
        scratch=out/(label+'-slice');scratch.mkdir();(scratch/'tmp').mkdir();exe='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio';base=HERE/'print-settings'
        cmd=[exe,'--datadir',str(scratch/'bambu-data'),'--debug','2','--load-settings',str(base/'machine.json')+';'+str(base/'process.json'),'--load-filaments',str(base/'filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf',filename,'--outputdir',str(scratch),str(layout)]
        with (out/(label+'.slice.log')).open('x')as log:subprocess.run(cmd,cwd=scratch,stdout=log,stderr=subprocess.STDOUT,check=True,env={**os.environ,'TMPDIR':str(scratch/'tmp')})
        report=json.loads((scratch/'result.json').read_text());assert report['return_code']==0 and all(not p.get('warning_message','')for p in report['sliced_plates']),report
        with zipfile.ZipFile(scratch/filename)as z:data={n:z.read(n)for n in z.namelist()}
        config=json.loads(data['Metadata/project_settings.config']);config['different_settings_to_system']=settings()['different_settings_to_system'];data['Metadata/project_settings.config']=json.dumps(config,indent=2).encode()
        dest=out/filename
        with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED)as z:
            for n,raw in data.items():z.writestr(n,raw)
        with zipfile.ZipFile(dest)as z:assert z.testzip()is None
        results[label]={'file':filename,'sha256':sha(dest),'parts':names,'centers':centers,'return_code':report['return_code'],'warnings':[],'slice':report['sliced_plates'][0]}
        print(label+' sliced',flush=True)
    with (out/'projects.json').open('x')as f:json.dump(results,f,indent=2);f.write('\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--slice',action='store_true');ap.add_argument('--only');a=ap.parse_args();build(a.out.resolve(),a.slice,a.only)
