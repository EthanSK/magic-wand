#!/usr/bin/env python3
"""Verify source, mesh and packaged 3MF receipts without the CAD runtime."""
from collections import Counter
from pathlib import Path
import argparse,hashlib,json,zipfile,xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];RECEIPT=HERE/'exports/release.json'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files():
 return sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=RECEIPT)+sorted((ROOT/'magic-wand-3d-models').glob('Slim-Loop-*.3mf'))
def dependencies():
 base=HERE.parent/'shard-tube-r2'
 return [base/p for p in ('wand_cad.py','handle_design.py','direct_switches.py','cap_design.py','print_projects.py','check_sliced_paths.py','exports/manifest.json','print-settings/machine.json','print-settings/process.json','print-settings/filament.json','print-settings/project.json')]
def record():
 assert not RECEIPT.exists()
 RECEIPT.write_text(json.dumps({'files':{str(p.relative_to(ROOT)):sha(p) for p in files()},'r2_dependencies':{str(p.relative_to(ROOT)):sha(p) for p in dependencies()}},indent=2)+'\n')
def check():
 receipt=json.loads(RECEIPT.read_text());assert receipt['files']=={str(p.relative_to(ROOT)):sha(p) for p in files()},'Study files changed after verification'
 assert receipt['r2_dependencies']=={str(p.relative_to(ROOT)):sha(p) for p in dependencies()},'R2 source or print settings changed; regenerate the study'
 m=json.loads((HERE/'exports/manifest.json').read_text());projects=json.loads((HERE/'exports/projects.json').read_text());scans=json.loads((HERE/'exports/sliced-checks.json').read_text())
 assert set(m['variants'])=={'slim','petal','leaf'} and len(projects)==6
 for variant,entry in m['variants'].items():
  part=entry['part'];assert sha(HERE/'exports'/variant/part['file'])==part['sha256']
  assert all(part['checks'][key] for key in ('watertight','winding_consistent','every_edge_shared_twice')) and part['checks']['bodies']==1
  assert not entry['checks']['physical_fit_verified'] and not entry['checks']['physical_strength_verified']
  assert scans['checked_projects'][variant]['passed']
 for variant in ('petal','leaf'):
  assert scans['opening_cores'][variant]['checked']==m['variants'][variant]['checks']['openings'] and scans['opening_cores'][variant]['violations']==0
  assert all(n>10 for n in scans['opening_cores'][variant]['nearby_samples'])
 for key,entry in projects.items():
  p=ROOT/'magic-wand-3d-models'/entry['file'];assert sha(p)==entry['sha256'] and not entry['warnings']
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None and hashlib.sha256(z.read('Metadata/plate_1.gcode')).hexdigest()==entry['gcode_sha256']
   model=E.fromstring(z.read('3D/3dmodel.model'));config=E.fromstring(z.read('Metadata/model_settings.config'))
   names={o.get('id'):next(v.get('value') for v in o.findall('metadata') if v.get('key')=='name') for o in config.findall('object')}
   assert Counter(names[o.get('objectid')] for o in model.findall('m:build/m:item',NS))==Counter(entry['parts'])
   settings=json.loads(z.read('Metadata/project_settings.config'));assert 'wall_loops' in settings['different_settings_to_system'][0]
  if key.endswith('one-left-light'):assert scans['checked_projects'][key.split('-')[0]]['gcode_sha256']==entry['gcode_sha256']
 print('Slim loop source, meshes, six print projects and checked G-code receipts match')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--record',action='store_true');a=p.parse_args();record() if a.record else check()
