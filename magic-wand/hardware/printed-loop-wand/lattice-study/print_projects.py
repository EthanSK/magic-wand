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

def names(both=True):
    return ['Handle_Left']+(['Handle_Right'] if both else [])+['Lower_Shaft','Upper_Shaft','Sense_Head_Base','Sense_Sliding_Cover','Battery_Twist_Cap','Battery_Sled']+['Choc_Recessed_Plate']*3+['Removable_Finger_Loop']

def centers(both=True):
    return [(35,55)]+([(80,55)] if both else [])+[(125,55),(160,55),(215,55),(207,100),(156,100),(231,160),(25,100),(55,100),(85,100),(75,190)]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare_layout(path,key,both):
    """The open studies need supports where V18's closed shaft did not."""
    with zipfile.ZipFile(path) as z:files={i.filename:z.read(i.filename) for i in z.infolist()}
    cfg=ET.fromstring(files['Metadata/model_settings.config'])
    for obj in cfg.findall('object'):
        name=next((m.get('value') for m in obj.findall('metadata') if m.get('key')=='name'),'')
        if name not in ('Lower_Shaft','Upper_Shaft'):continue
        for key_,value in [('enable_support','1'),('support_type','normal(auto)')]:
            entry=next((m for m in obj.findall('metadata') if m.get('key')==key_),None)
            if entry is None:entry=ET.SubElement(obj,'metadata',key=key_)
            entry.set('value',value)
    for m in cfg.findall('./plate/metadata'):
        if m.get('key')=='plater_name':m.set('value',f'Print V18 {key} - '+('both handed stems' if both else 'one left wand'))
    files['Metadata/model_settings.config']=ET.tostring(cfg,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():z.writestr(name,data)

def build(exports,out,bambu):
    out.mkdir(parents=True,exist_ok=False)
    study=module('lightweight_cad',HERE/'wand_cad.py')
    manifest=json.loads((exports/'manifest.json').read_text())
    projects={}
    mass_parser=module('wand_mass',BASE/'compare_mass.py')
    baseline=ROOT/'magic-wand-3d-models/Print-18-one-left-wand-410mm.3mf'
    comparison={'baseline':mass_parser.inspect(baseline),'variants':{},'physical_mass_measured':False,
                'scope':'One complete LEFT wand per mass row, including detachable loop and three printed switch plates. PETG only; electronics, cell, wires, bought switches, sockets and caps are unweighed.'}
    for key,record in manifest['variants'].items():
        print('Preparing '+key,flush=True)
        recipe=module('recipe_'+key,BASE/'print_projects.py');recipe.c=study.configure(key)
        original_blocker=recipe.blocker
        def blocker(name):
            original=original_blocker(name)
            if name not in ('Lower_Shaft','Upper_Shaft'):return original
            c=recipe.c
            z0,z1=(c.HANDLE_END-1,c.MID+15.) if name=='Lower_Shaft' else (c.MID-1,c.TOP+15.)
            # Stop support landing sources over the complete hollow interior.
            # A small bore-only blocker did not stop descending support columns.
            landing=c.cyl(c.shaft_radius(z0)-.3,z0,z1,c.shaft_radius(z1)-.3)
            return original+landing
        recipe.blocker=blocker
        records=record['parts']+manifest['shared_parts'];parts={}
        for r in records:
            path=(exports/key/r['file']) if r in record['parts'] else (exports/r['file']).resolve()
            mesh=trimesh.load_mesh(path,process=True)
            mesh.apply_transform(np.asarray(r['print_to_assembly']))
            parts[r['name']]=dict(r,assembly_vertices=mesh.vertices.tolist(),assembly_faces=mesh.faces.tolist())
        recipe.parts=parts
        projects[key]={}
        for label,both in [('complete',True),('one-left',False)]:
            filename=f'Print-Lattice-{key}-{label}.3mf';layout=out/(key+'-'+label+'-layout.3mf')
            recipe.make(names(both),centers(both),layout)
            prepare_layout(layout,key,both)
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
            projects[key][label]={'file':filename,'sha256':sha(dest),'part_names':names(both),'positions':centers(both),'slice':plate}
            if not both:
                row=mass_parser.inspect(dest);assert row['build_instances']==11
                assert row['settings']==comparison['baseline']['settings'],('Unmatched settings',row['settings'])
                row['printed_parts_reduction_percent']=round(100*(1-row['printed_parts_g']/comparison['baseline']['printed_parts_g']),2)
                comparison['variants'][key]=row
            print(filename+' sliced',flush=True)
    (out/'projects.json').write_text(json.dumps(projects,indent=2)+'\n')
    (out/'mass-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,default=HERE/'exports');p.add_argument('--out',type=Path,required=True);p.add_argument('--bambu',default='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio');a=p.parse_args();build(a.exports.resolve(),a.out.resolve(),a.bambu)
