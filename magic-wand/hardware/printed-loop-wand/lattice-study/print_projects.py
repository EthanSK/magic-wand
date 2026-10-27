#!/usr/bin/env python3
"""Reuse V18 plate/settings/support recipes for each lightweight study."""
from pathlib import Path
import argparse, importlib.util, json, hashlib, zipfile, subprocess, shutil
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=HERE.parent/'v18'

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def names(both=True,open_head=False):
    return ['Handle_Left']+(['Handle_Right'] if both else [])+['Lower_Shaft','Upper_Shaft']+(['Sense_Open_Cradle'] if open_head else ['Sense_Head_Base','Sense_Sliding_Cover'])+['Battery_Twist_Cap','Battery_Sled']+['Choc_Recessed_Plate']*3+['Removable_Finger_Loop']

def centers(both=True,open_head=False):
    return [(35,55)]+([(80,55)] if both else [])+[(125,55),(160,55),(215,55)]+([] if open_head else [(207,100)])+[(156,100),(231,160),(25,100),(55,100),(85,100),(75,190)]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare_layout(path,key,both,c,record):
    """The open studies need supports where V18's closed shaft did not."""
    with zipfile.ZipFile(path) as z:files={i.filename:z.read(i.filename) for i in z.infolist()}
    cfg=ET.fromstring(files['Metadata/model_settings.config'])
    for obj in cfg.findall('object'):
        name=next((m.get('value') for m in obj.findall('metadata') if m.get('key')=='name'),'')
        if name not in ('Lower_Shaft','Upper_Shaft','Sense_Open_Cradle'):continue
        for key_,value in [('enable_support','1'),('support_type','normal(manual)' if name=='Sense_Open_Cradle' else 'normal(auto)')]+([('bridge_no_support','1')] if name=='Sense_Open_Cradle' else []):
            entry=next((m for m in obj.findall('metadata') if m.get('key')==key_),None)
            if entry is None:entry=ET.SubElement(obj,'metadata',key=key_)
            entry.set('value',value)
    if record.get('open_head'):
        # Only the low back of the flat cradle needs removable supports. Auto
        # support filled the board slot despite blockers; limit landing sources
        # to these explicit back-facing patches, away from all functional gaps.
        zones=[c.box(-10,10,-9.6,-6.85,352.,369.),c.box(-14,14,-7.2,-6.85,374.8,375.6)]
        for sign in (-1,1):zones.append(c.box(sign*11.5-3.,sign*11.5+3.,-8.2,-6.85,369.,399.))
        support=c.union(zones).to_mesh()
        t=np.linalg.inv(np.asarray(next(p for p in record['parts'] if p['name']=='Sense_Open_Cradle')['print_to_assembly']))
        vertices=np.asarray(support.vert_properties)[:,:3]@t[:3,:3].T+t[:3,3]
        model=ET.fromstring(files['3D/3dmodel.model']);ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';tag=lambda name:'{'+ns+'}'+name
        resources=model.find(tag('resources'));newid=max(int(o.get('id')) for o in resources)+1
        obj=ET.SubElement(resources,tag('object'),id=str(newid),type='model');mesh=ET.SubElement(obj,tag('mesh'));vs=ET.SubElement(mesh,tag('vertices'));fs=ET.SubElement(mesh,tag('triangles'))
        for v in vertices:ET.SubElement(vs,tag('vertex'),**{a:format(float(b),'.7g') for a,b in zip('xyz',v)})
        for f in support.tri_verts:ET.SubElement(fs,tag('triangle'),**{a:str(int(b)) for a,b in zip(['v1','v2','v3'],f)})
        target=next(o for o in cfg.findall('object') if any(m.get('key')=='name' and m.get('value')=='Sense_Open_Cradle' for m in o.findall('metadata')))
        parent=resources.find(tag('object')+"[@id='"+target.get('id')+"']")
        ET.SubElement(parent.find(tag('components')),tag('component'),objectid=str(newid))
        part=ET.SubElement(target,'part',id=str(newid),subtype='support_enforcer');ET.SubElement(part,'metadata',key='name',value='Support low back only')
        files['3D/3dmodel.model']=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    for m in cfg.findall('./plate/metadata'):
        if m.get('key')=='plater_name':m.set('value',f'Print V18 {key} - '+('both handed stems' if both else 'one left wand'))
    files['Metadata/model_settings.config']=ET.tostring(cfg,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)

def build(exports,out,bambu,selected=None):
    out.mkdir(parents=True,exist_ok=False)
    study=module('lightweight_cad',HERE/'wand_cad.py')
    manifest=json.loads((exports/'manifest.json').read_text())
    projects={}
    mass_parser=module('wand_mass',BASE/'compare_mass.py')
    baseline=ROOT/'magic-wand-3d-models/Print-18-one-left-wand-410mm.3mf'
    comparison={'baseline':mass_parser.inspect(baseline),'variants':{},'physical_mass_measured':False,
                'scope':'One complete LEFT wand per mass row, including detachable loop and three printed switch plates. PETG only; electronics, cell, wires, bought switches, sockets and caps are unweighed.'}
    if selected:assert set(selected).issubset(manifest['variants']),selected
    for key,record in manifest['variants'].items():
        if selected and key not in selected:continue
        print('Preparing '+key,flush=True)
        recipe=module('recipe_'+key,BASE/'print_projects.py');recipe.c=study.configure(key)
        original_blocker=recipe.blocker
        def blocker(name):
            if name=='Sense_Open_Cradle':
                c=recipe.c
                return c.union([c.slim_female_at(c.TOP),c.cyl(8.5,c.TOP-1,411.),c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,397.),c.box(-5.4,5.4,c.BOARD_Y-6.,c.BOARD_Y-.25,379.,394.),c.box(-5.8,5.8,c.BOARD_Y-.9,c.BOARD_Y+4.9,397.3,411.),c.cyl(2.9,375.,387.5).translate((0.,2.,0.)),c.box(-12.5,12.5,-7.,-4.,373.5,374.7)])
            original=original_blocker(name)
            if name not in ('Lower_Shaft','Upper_Shaft'):return original
            c=recipe.c
            z0,z1=(c.HANDLE_END-1,c.MID+15.) if name=='Lower_Shaft' else (c.MID-1,c.TOP+15.)
            # Stop support landing sources over the complete hollow interior.
            # A small bore-only blocker did not stop descending support columns.
            landing=c.cyl(c.shaft_radius(z0)-.3,z0,z1,c.shaft_radius(z1)-.3)
            return original+landing
        recipe.blocker=blocker
        records=record['parts']+[p for p in manifest['shared_parts'] if p['name'] not in record.get('omit_shared_parts',[])];parts={}
        for r in records:
            path=(exports/key/r['file']) if r in record['parts'] else (exports/r['file']).resolve()
            mesh=trimesh.load_mesh(path,process=True)
            mesh.apply_transform(np.asarray(r['print_to_assembly']))
            parts[r['name']]=dict(r,assembly_vertices=mesh.vertices.tolist(),assembly_faces=mesh.faces.tolist())
        recipe.parts=parts
        projects[key]={}
        for label,both in [('complete',True),('one-left',False)]:
            filename=f'Print-Lattice-{key}-{label}.3mf';layout=out/(key+'-'+label+'-layout.3mf')
            recipe.make(names(both,record.get('open_head',False)),centers(both,record.get('open_head',False)),layout)
            prepare_layout(layout,key,both,recipe.c,record)
            scratch=out/(key+'-'+label+'-slice');scratch.mkdir()
            settings=BASE/'print-settings'
            cmd=[bambu,'--datadir',str(scratch/'bambu-data'),'--debug','2','--load-settings',str(settings/'machine.json')+';'+str(settings/'process.json'),'--load-filaments',str(settings/'filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf',filename,'--outputdir',str(scratch),str(layout)]
            with (out/(key+'-'+label+'.log')).open('w') as log:
                subprocess.run(cmd,cwd=scratch,stdout=log,stderr=subprocess.STDOUT,check=True)
            result=json.loads((scratch/'result.json').read_text())
            assert result['return_code']==0 and all(not p.get('warning_message','') for p in result['sliced_plates']),result
            with zipfile.ZipFile(scratch/filename) as z:files={i.filename:z.read(i.filename) for i in z.infolist()}
            cfg=json.loads(files['Metadata/project_settings.config']);diff=cfg.get('different_settings_to_system',['','',''])
            diff[0]=';'.join(sorted(set(filter(None,diff[0].split(';')))|set(recipe.changed)));cfg['different_settings_to_system']=diff
            files['Metadata/project_settings.config']=json.dumps(cfg,indent=2).encode()
            dest=out/filename
            with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
                for name,data in files.items():z.writestr(name,data)
            plate=result['sliced_plates'][0]
            projects[key][label]={'file':filename,'sha256':sha(dest),'part_names':names(both,record.get('open_head',False)),'positions':centers(both,record.get('open_head',False)),'slice':plate}
            if not both:
                row=mass_parser.inspect(dest);assert row['build_instances']==len(names(False,record.get('open_head',False)))
                assert row['settings']==comparison['baseline']['settings'],('Unmatched settings',row['settings'])
                row['printed_parts_reduction_percent']=round(100*(1-row['printed_parts_g']/comparison['baseline']['printed_parts_g']),2)
                comparison['variants'][key]=row
            print(filename+' sliced',flush=True)
    (out/'projects.json').write_text(json.dumps(projects,indent=2)+'\n')
    (out/'mass-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,default=HERE/'exports');p.add_argument('--out',type=Path,required=True);p.add_argument('--variant',nargs='+',help='Regenerate selected options in a new output directory');p.add_argument('--bambu',default='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio');a=p.parse_args();build(a.exports.resolve(),a.out.resolve(),a.bambu,a.variant)
