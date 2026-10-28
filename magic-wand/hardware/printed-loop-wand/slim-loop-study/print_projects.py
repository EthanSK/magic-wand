#!/usr/bin/env python3
"""Slice each slim loop with the canonical R2 full assembly and settings."""
import argparse,importlib.util,json,os,subprocess,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'shard-tube-r2'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
r=load('slim_print_r2',BASE/'print_projects.py')
def main(source,out):
 out.mkdir(parents=True,exist_ok=False)
 source_data=json.loads((source/'manifest.json').read_text());original=json.loads((BASE/'exports/manifest.json').read_text());result={}
 for key in source_data['variants']:
  m=dict(original);m['parts']=[p for p in original['parts'] if p['name']!='Removable_Finger_Loop']+[source_data['variants'][key]['part']]
  for kind in ('one-left-light','complete-both-hands'):
   names,centers=r.projects()[kind];name='Slim-Loop-'+key+'-'+kind+'.3mf';layout=out/(key+'-'+kind+'-layout.3mf');r.make(names,centers,layout,m)
   job=out/(key+'-'+kind);job.mkdir();(job/'tmp').mkdir();base=BASE/'print-settings';exe='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
   cmd=[exe,'--datadir',str(job/'bambu-data'),'--debug','2','--load-settings',str(base/'machine.json')+';'+str(base/'process.json'),'--load-filaments',str(base/'filament.json'),'--orient','0','--arrange','0','--slice','0','--export-3mf',name,'--outputdir',str(job),str(layout)]
   with (out/(key+'-'+kind+'.log')).open('x') as f:subprocess.run(cmd,cwd=job,stdout=f,stderr=subprocess.STDOUT,check=True,env={**os.environ,'TMPDIR':str(job/'tmp')})
   report=json.loads((job/'result.json').read_text());assert report['return_code']==0 and all(not p.get('warning_message','') for p in report['sliced_plates']),report
   # Preserve the explicit per-project settings when Bambu Studio reopens the
   # sliced file, just as the canonical R2 project exporter does.
   with zipfile.ZipFile(job/name) as z:data={n:z.read(n) for n in z.namelist()}
   config=json.loads(data['Metadata/project_settings.config']);config['different_settings_to_system']=r.settings()['different_settings_to_system'];data['Metadata/project_settings.config']=json.dumps(config,indent=2).encode()
   with zipfile.ZipFile(out/name,'x',zipfile.ZIP_DEFLATED) as z:
    for n,raw in data.items():z.writestr(n,raw)
   with zipfile.ZipFile(out/name) as z:assert z.testzip() is None
   result[key+'-'+kind]={'file':name,'sha256':r.sha(out/name),'slice':report['sliced_plates'][0],'parts':names}
   print(key,kind,'sliced',flush=True)
 (out/'projects.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.source,a.out)
