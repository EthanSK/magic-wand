#!/usr/bin/env python3
"""P1S PETG project for the three solid external-wire rod sections."""
from pathlib import Path
import argparse,importlib.util,json,subprocess,sys,zipfile,hashlib,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent

def load(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m

def build(exports,out,bambu):
    out.mkdir(parents=True,exist_ok=False)
    recipe=load('long_rod_recipe',HERE.parent/'v20/print_projects.py')
    mass=load('long_rod_mass',HERE.parent/'v20/compare_mass.py')
    m=json.loads((exports/'manifest.json').read_text());settings=HERE.parent/'shard-tube-r2/print-settings'
    recipe.config=json.loads((settings/'project.json').read_text())
    changed={'enable_support':'0','sparse_infill_density':'20%','sparse_infill_pattern':'grid','wall_loops':'4','brim_width':'5','brim_type':'outer_only','enable_prime_tower':'0'}
    recipe.config.update(changed);diffs=recipe.config.get('different_settings_to_system',['','','']);diffs[0]=';'.join(sorted(set(filter(None,diffs[0].split(';')))|set(changed)));recipe.config['different_settings_to_system']=diffs
    recipe.blocker=lambda name:None;recipe.parts={p['name']:p for p in m['parts']}
    names=list(recipe.parts);layout=out/'layout.3mf';recipe.make(names,[(65,110),(125,110),(185,110)],layout)
    with zipfile.ZipFile(layout)as z:entries={n:z.read(n)for n in z.namelist()}
    cfg=ET.fromstring(entries['Metadata/model_settings.config'])
    for el in cfg.iter():
        if el.tag=='metadata' and 'Print V20' in el.get('value',''):el.set('value','Long solid rod prototype - external controls and battery')
    for obj in cfg.findall('object'):
        for key,value in [('sparse_infill_density','100%'),('sparse_infill_pattern','rectilinear'),('wall_loops','4')]:ET.SubElement(obj,'metadata',key=key,value=value)
    entries['Metadata/model_settings.config']=ET.tostring(cfg,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(layout,'w',zipfile.ZIP_DEFLATED)as z:
        for n,data in entries.items():z.writestr(n,data)
    process=json.loads((settings/'process.json').read_text());process.update(changed);process['different_settings_to_system']=[';'.join(sorted(changed)),'',''];proc=out/'process.json';proc.write_text(json.dumps(process))
    dest=out/'slice';dest.mkdir();name='Long-Solid-Wand-500mm-8mm.3mf'
    cmd=[bambu,'--datadir',str(dest/'bambu-data'),'--debug','2','--load-settings',str(settings/'machine.json')+';'+str(proc),'--load-filaments',str(settings/'filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf',name,'--outputdir',str(dest),str(layout)]
    with(out/'slice.log').open('w')as log:subprocess.run(cmd,cwd=dest,stdout=log,stderr=subprocess.STDOUT,check=True)
    result=json.loads((dest/'result.json').read_text());assert result['return_code']==0,result
    record={'file':name,'sha256':hashlib.sha256((dest/name).read_bytes()).hexdigest(),'slice':result['sliced_plates'][0],'mass':mass.inspect(dest/name),'physical_print_verified':False}
    (out/'project.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--bambu',default='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio');a=p.parse_args();build(a.exports.resolve(),a.out.resolve(),a.bambu)
