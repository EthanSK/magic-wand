#!/usr/bin/env python3
"""Reproducible P1S PETG projects for the thin solid-body experiment."""
from pathlib import Path
import argparse, importlib.util, json, subprocess, sys, zipfile, hashlib
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def build(exports,out,bambu):
    out.mkdir(parents=True,exist_ok=False)
    recipe=load('thin_rod_print_recipe',HERE.parent/'v20/print_projects.py')
    mass=load('thin_rod_mass',HERE.parent/'v20/compare_mass.py')
    manifest=json.loads((exports/'manifest.json').read_text());report={}
    settings=HERE.parent/'shard-tube-r2/print-settings'
    recipe.config=json.loads((settings/'project.json').read_text())
    recipe.config.update({'enable_support':'0','sparse_infill_density':'20%','sparse_infill_pattern':'grid','wall_loops':'4','brim_width':'5','brim_type':'outer_only','enable_prime_tower':'0'})
    recipe.changed={k:recipe.config[k]for k in ['enable_support','sparse_infill_density','sparse_infill_pattern','wall_loops','brim_width','brim_type','enable_prime_tower']}
    diffs=recipe.config.get('different_settings_to_system',['','',''])
    diffs[0]=';'.join(sorted(set(filter(None,diffs[0].split(';')))|set(recipe.changed)))
    recipe.config['different_settings_to_system']=diffs
    recipe.blocker=lambda name:None
    for key,variant in manifest['variants'].items():
        recipe.parts={p['name']:p for p in variant['parts']}
        filename=f'Thin-Rod-{key}-prototype.3mf'
        layout=out/(key+'-layout.3mf')
        recipe.make(['Lower_Body','Upper_Body_With_Sensor_Fork'],[(70,110),(155,110)],layout)
        # These are symmetric bare rods, not a complete handed Shard kit.
        with zipfile.ZipFile(layout)as z:entries={n:z.read(n)for n in z.namelist()}
        entries['Metadata/model_settings.config']=entries['Metadata/model_settings.config'].replace(b'Print V20 candidate - 410 mm helix wand - BOTH handed handles',b'Thin solid rod prototype - external controls and battery')
        cfg=ET.fromstring(entries['Metadata/model_settings.config'])
        for obj in cfg.findall('object'):
            for name,value in [('sparse_infill_density','100%'),('sparse_infill_pattern','rectilinear'),('wall_loops','4')]:
                ET.SubElement(obj,'metadata',key=name,value=value)
        entries['Metadata/model_settings.config']=ET.tostring(cfg,encoding='utf-8',xml_declaration=True)
        with zipfile.ZipFile(layout,'w',zipfile.ZIP_DEFLATED)as z:
            for n,data in entries.items():z.writestr(n,data)
        slice_dir=out/(key+'-slice');slice_dir.mkdir()
        process=json.loads((settings/'process.json').read_text());process.update(recipe.changed)
        process['different_settings_to_system']=[';'.join(sorted(recipe.changed)),'','']
        process_path=out/(key+'-process.json');process_path.write_text(json.dumps(process))
        cmd=[bambu,'--datadir',str(slice_dir/'bambu-data'),'--debug','2','--load-settings',str(settings/'machine.json')+';'+str(process_path),'--load-filaments',str(settings/'filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf',filename,'--outputdir',str(slice_dir),str(layout)]
        with(out/(key+'.log')).open('w')as log:subprocess.run(cmd,cwd=slice_dir,stdout=log,stderr=subprocess.STDOUT,check=True)
        result=json.loads((slice_dir/'result.json').read_text())
        assert result['return_code']==0,result
        path=slice_dir/filename;estimate=mass.inspect(path)
        report[key]={'file':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'slice':result['sliced_plates'][0],'mass':estimate,'physical_print_verified':False}
        print(json.dumps({key:report[key]},indent=2),flush=True)
    (out/'projects.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--exports',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--bambu',default='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio');a=ap.parse_args();build(a.exports.resolve(),a.out.resolve(),a.bambu)
