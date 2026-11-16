"""Run a single isolated, headless A1 mini slice; never send or start."""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
def run(layout,output):
    scratch=Path(os.environ['AGENT_SCRATCH_DIR'])/'native';scratch.mkdir()
    for n in ('tmp','data','profile-home/Library/Preferences'):(scratch/n).mkdir(parents=True)
    env={**os.environ,'TMPDIR':str(scratch/'tmp'),'CFFIXED_USER_HOME':str(scratch/'profile-home')}
    binary='/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
    args=[binary,'--datadir',str(scratch/'data'),'--debug','2','--orient','0','--arrange','0','--slice','0','--export-3mf','sliced.3mf','--outputdir',str(scratch),str(layout.resolve())]
    with (scratch/'slice.log').open('w') as out:
        run=subprocess.run(args,cwd=scratch,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=320)
    if run.returncode:raise RuntimeError((scratch/'slice.log').read_text()[-5000:])
    result=json.loads((scratch/'result.json').read_text())
    receipt={k:result.get(k) for k in ('error_string','return_code','layer_height')}
    receipt['plates']=[{k:p.get(k) for k in ('warning_message','total_predication','total_filament','triangle_count')} for p in result['sliced_plates']]
    shutil.copyfile(scratch/'sliced.3mf',output)
    receipt['archive_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.native.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('layout',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.layout,a.output)
