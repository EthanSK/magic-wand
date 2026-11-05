#!/usr/bin/env python3
"""Re-slice the portable project using embedded settings only, then audit it."""
import argparse,hashlib,json,os,subprocess,zipfile,xml.etree.ElementTree as E
from pathlib import Path
import cad
import deliverables
import verify_slice
import print_project

KEYS=['enable_support','support_type','brim_type','layer_height','wall_loops',
      'sparse_infill_density','printer_settings_id','filament_settings_id','bridge_no_support','max_bridge_length']

def settings(path):
    with zipfile.ZipFile(path)as z:
        config=json.loads(z.read('Metadata/project_settings.config'))
        model=E.fromstring(z.read('Metadata/model_settings.config'))
    objects={}
    for obj in model.findall('object'):
        meta={m.get('key'):m.get('value')for m in obj.findall('metadata')}
        objects[meta['name']]={k:meta.get(k,config.get(k))for k in KEYS}
    return {'global':{k:config.get(k)for k in KEYS},'objects':objects,
            'all_embedded_global_keys':len(config),
            'all_embedded_global_values_sha256':hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()}

def run(scratch,exports):
    source=exports/deliverables.project_name(exports);scratch=scratch.resolve();scratch.mkdir();(scratch/'tmp').mkdir()
    target=scratch/'Reopened.3mf'
    cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--datadir',str(scratch/'bambu-data'),
         '--debug','2','--orient','0','--arrange','0','--slice','0','--export-3mf',target.name,
         '--outputdir',str(scratch),str(source)]
    with (scratch/'slice.log').open('w')as log:
        subprocess.run(cmd,cwd=scratch,env={**os.environ,'TMPDIR':str(scratch/'tmp')},stdout=log,stderr=subprocess.STDOUT,check=True)
    result=json.loads((scratch/'result.json').read_text());assert result['return_code']==0
    with zipfile.ZipFile(source)as z:expected=json.loads(z.read('Metadata/project_settings.config'))
    registration=print_project.restore_registration(target,expected)
    before=settings(source);after=settings(target);assert before==after,('Embedded recipe changed',before,after)
    verify_slice.inspect('modular',target,exports,exports/'reopened-clearances.json')
    report={'input_project_sha256':cad.sha(source),'reopened_project_sha256':cad.sha(target),
            'generator_sha256':cad.sha(Path(__file__)),'effective_settings_equal':True,'effective_settings':after,
            'actual_paths_passed':True,'actual_paths_report_sha256':cad.sha(exports/'reopened-clearances.json'),
            'warnings':[p['warning_message']for p in result['sliced_plates']if p.get('warning_message')],
            'cli_return_code':0,'gui_test_performed':False,'physical_print_verified':False}
    report['delivered_settings_registration']=registration
    (exports/'reopen-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Embedded recipe retained and reopened actual paths passed; GUI and physical printing remain unverified.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);p.add_argument('--exports',type=Path,default=cad.HERE/'exports');a=p.parse_args();run(a.scratch,a.exports.resolve())
