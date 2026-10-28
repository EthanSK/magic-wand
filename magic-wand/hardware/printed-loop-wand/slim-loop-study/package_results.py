#!/usr/bin/env python3
"""Package checked Bambu slices and compare with a freshly sliced R2 baseline."""
import argparse, hashlib, importlib.util, json, sys, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=HERE.parent/'shard-tube-r2'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
mass=load('slim_mass',HERE.parent/'v20/compare_mass.py')
printer=load('slim_r2_project_settings',BASE/'print_projects.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(slices,baseline,path_checks,opening_checks):
 projects=json.loads((slices/'projects.json').read_text())
 dest=ROOT/'magic-wand-3d-models';dest.mkdir(exist_ok=True)
 verified={};weights={};openings=json.loads(opening_checks.read_text())
 assert all(c.get('nearby_samples',0)>10 and not c['violations'] for v in openings.values() for c in v['slot_core_checks'])
 for key,entry in projects.items():
  variant=key.split('-')[0]
  assert not entry['slice'].get('warning_message')
  src=slices/entry['file'];target=dest/entry['file'];assert not target.exists(),target
  with zipfile.ZipFile(src) as z: data={n:z.read(n) for n in z.namelist()}
  cfg=json.loads(data['Metadata/project_settings.config']);cfg['different_settings_to_system']=printer.settings()['different_settings_to_system'];data['Metadata/project_settings.config']=json.dumps(cfg,indent=2).encode()
  with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
   for n,raw in data.items():z.writestr(n,raw)
  with zipfile.ZipFile(target) as z:assert z.testzip() is None
  scan=json.loads((path_checks/(variant+'-paths.json')).read_text())
  assert scan['passed'],variant
  verified[key]={'file':entry['file'],'sha256':sha(target),'gcode_sha256':hashlib.sha256(data['Metadata/plate_1.gcode']).hexdigest(),'parts':entry['parts'],'warnings':[], 'estimated_seconds':round(entry['slice']['main_predication'])}
  if key.endswith('one-left-light'):
   w=mass.inspect(target);weights[variant]={k:w[k] for k in ('printed_parts_g','supports_and_brim_g','total_slicer_g','object_printed_parts_g')}
 reference=mass.inspect(baseline);assert reference['build_instances']==7
 weights['r2_baseline']={k:reference[k] for k in ('printed_parts_g','supports_and_brim_g','total_slicer_g','object_printed_parts_g')}
 out=HERE/'exports'
 (out/'projects.json').write_text(json.dumps(verified,indent=2)+'\n')
 (out/'mass.json').write_text(json.dumps({'scope':'Same P1S PETG settings, one complete left-handed wand, excluding electronics and battery. Slicer estimates; no physical weighing.','physical_mass_verified':False,'versions':weights},indent=2)+'\n')
 (out/'sliced-checks.json').write_text(json.dumps({'source':'R2 clearance and layer-start checker on each one-left project before metadata-only repackaging','checked_projects':{n:{'passed':True,'slice_sha256':sha(slices/('Slim-Loop-'+n+'-one-left-light.3mf')),'gcode_sha256':verified[n+'-one-left-light']['gcode_sha256']} for n in ('slim','petal','leaf')},'opening_cores':{n:{'checked':len(openings[n]['slot_core_checks']),'nearby_samples':[c['nearby_samples'] for c in openings[n]['slot_core_checks']],'violations':sum(bool(c['violations']) for c in openings[n]['slot_core_checks'])} for n in ('petal','leaf')},'physical_fit_verified':False},indent=2)+'\n')
 print(json.dumps({n:{'printed_parts_g':v['printed_parts_g'],'loop_g':v['object_printed_parts_g'].get('Removable_Finger_Loop')} for n,v in weights.items()},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--slices',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--path-checks',type=Path,required=True);p.add_argument('--opening-checks',type=Path,required=True);a=p.parse_args();main(a.slices,a.baseline,a.path_checks,a.opening_checks)
