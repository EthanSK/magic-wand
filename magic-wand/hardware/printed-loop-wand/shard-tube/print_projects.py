#!/usr/bin/env python3
"""Make P1S PETG layouts for the continuous Two wide spirals study."""
import argparse,importlib.util,json,hashlib,shutil,subprocess,zipfile
import xml.etree.ElementTree as E
from pathlib import Path
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE.parent/'v20';STUDY=HERE.parent/'lattice-study'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def names(both):return ['Handle_Left']+(['Handle_Right'] if both else [])+['Continuous_Shaft','Sense_Open_Cradle','Battery_Twist_Cap','Battery_Sled']+['Choc_Recessed_Plate']*3+['Removable_Finger_Loop']
def centers(both):return [(35,55)]+([(80,55)] if both else [])+[(125,55),(215,55),(156,100),(231,160),(25,100),(55,100),(85,100),(75,190)]
def shaft_support(path):
    with zipfile.ZipFile(path) as z:files={i.filename:z.read(i.filename) for i in z.infolist()}
    cfg=E.fromstring(files['Metadata/model_settings.config'])
    obj=next(o for o in cfg.findall('object') if any(m.get('key')=='name' and m.get('value')=='Continuous_Shaft' for m in o.findall('metadata')))
    for key,value in [('enable_support','1'),('support_type','normal(auto)')]:
        item=next((m for m in obj.findall('metadata') if m.get('key')==key),None)
        if item is None:item=E.SubElement(obj,'metadata',key=key)
        item.set('value',value)
    files['Metadata/model_settings.config']=E.tostring(cfg,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in files.items():z.writestr(n,b)
def build(out,bambu):
    out.mkdir(parents=True,exist_ok=False)
    model=module('continuous_model',HERE/'wand_cad.py');c,_,_=model.make()
    helper=module('study_print',STUDY/'print_projects.py');recipe=module('recipe',BASE/'print_projects.py');recipe.c=c
    m=json.loads((HERE/'exports/manifest.json').read_text());records=m['parts']+m['shared_parts'];recipe.parts={}
    for p in records:
        path=HERE/'exports'/p['file'];assert sha(path)==p['sha256']
        mesh=trimesh.load_mesh(path,process=True);mesh.apply_transform(np.asarray(p['print_to_assembly']))
        recipe.parts[p['name']]=dict(p,assembly_vertices=mesh.vertices.tolist(),assembly_faces=mesh.faces.tolist())
    original=recipe.blocker
    def blocker(name):
        if name=='Continuous_Shaft':
            return c.female_at(c.HANDLE_END)+c.cyl(c.shaft_radius(c.HANDLE_END)-.3,c.HANDLE_END-1,c.TOP+15,c.shaft_radius(c.TOP)-.3)
        if name=='Sense_Open_Cradle':
            return c.union([c.cyl(8.5,342.5,411.),c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,397.),c.box(-5.4,5.4,c.BOARD_Y-6.,c.BOARD_Y-.25,379.,394.),c.box(-5.8,5.8,c.BOARD_Y-.9,c.BOARD_Y+4.9,397.3,411.),c.cyl(2.9,375.,387.5).translate((0.,2.,0.)),c.box(-12.5,12.5,-7.,-4.,373.5,374.7)])
        return original(name)
    recipe.blocker=blocker
    p={};comparison={};mass=module('mass',BASE/'compare_mass.py')
    for label,both in [('complete',True),('one-left',False)]:
        filename=f'Print-Shard-Tube-{label}.3mf';layout=out/(label+'-layout.3mf')
        recipe.make(names(both),centers(both),layout)
        helper.prepare_layout(layout,'sharper tube',both,c,{'open_head':True,'parts':m['parts']},support_start=352.5,plate_version='V20')
        shaft_support(layout)
        scratch=out/(label+'-slice');scratch.mkdir();settings=BASE/'print-settings'
        cmd=[bambu,'--datadir',str(scratch/'bambu-data'),'--debug','2','--load-settings',str(settings/'machine.json')+';'+str(settings/'process.json'),'--load-filaments',str(settings/'filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf',filename,'--outputdir',str(scratch),str(layout)]
        with (out/(label+'.log')).open('w') as log:subprocess.run(cmd,cwd=scratch,stdout=log,stderr=subprocess.STDOUT,check=True)
        result=json.loads((scratch/'result.json').read_text());assert result['return_code']==0 and all(not q.get('warning_message','') for q in result['sliced_plates']),result
        with zipfile.ZipFile(scratch/filename) as z:files={i.filename:z.read(i.filename) for i in z.infolist()}
        cfg=json.loads(files['Metadata/project_settings.config']);diff=cfg.get('different_settings_to_system',['','','']);diff[0]=';'.join(sorted(set(filter(None,diff[0].split(';')))|set(recipe.changed)));cfg['different_settings_to_system']=diff;files['Metadata/project_settings.config']=json.dumps(cfg,indent=2).encode()
        dest=out/filename
        with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
            for n,b in files.items():z.writestr(n,b)
        p[label]={'file':filename,'sha256':sha(dest),'part_names':names(both),'positions':centers(both),'slice':result['sliced_plates'][0]}
        if not both:
            comparison=mass.inspect(dest);assert comparison['build_instances']==9
        print(filename+' sliced',flush=True)
    prior=json.loads((STUDY/'exports/mass-comparison.json').read_text())
    assert comparison['settings']['layer_height'] == prior['variants']['two-wide']['settings']['layer_height']
    (out/'projects.json').write_text(json.dumps({'continuous':p},indent=2)+'\n')
    (out/'mass.json').write_text(json.dumps({'continuous':comparison,'previous_two_wide':prior['variants']['two-wide'],'physical_mass_measured':False},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--bambu',default='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio');a=p.parse_args();build(a.out.resolve(),a.bambu)
