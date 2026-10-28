#!/usr/bin/env python3
"""Check actual R2 routes and layer starts against each slimmer loop slice."""
import argparse,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'shard-tube-r2'
def module(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sys.modules[name]=m;sp.loader.exec_module(m);return m
checker=module('slim_r2_paths',BASE/'check_sliced_paths.py')
def main(projects,out):
 out.mkdir(parents=True,exist_ok=False);study=json.loads((HERE/'exports/manifest.json').read_text());base=json.loads((BASE/'exports/manifest.json').read_text())
 for name in ('slim','petal','leaf'):
  # Input manifest paths point back to canonical R2 STLs and this study's
  # exported loop. No STL or mating geometry is regenerated here.
  records=[dict(p,file=str((BASE/'exports'/p['file']).resolve())) for p in base['parts'] if p['name']!='Removable_Finger_Loop']
  records.append(dict(study['variants'][name]['part'],file=str((HERE/'exports'/name/'Removable_Finger_Loop.stl').resolve())))
  manifest=out/(name+'-manifest.json');manifest.write_text(json.dumps({'parts':records}))
  report=checker.inspect(projects/('Slim-Loop-'+name+'-one-left-light.3mf'),manifest,.5)
  (out/(name+'-paths.json')).write_text(json.dumps(report,indent=2)+'\n')
  assert report['passed'],name+' R2 clearances or layer starts failed'
  print(name+' paths passed',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--projects',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.projects,a.out)
