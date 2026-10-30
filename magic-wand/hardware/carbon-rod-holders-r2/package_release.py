#!/usr/bin/env python3
"""Derive a checked R2 package including its preserved source dependencies."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def package(out):
    exports=HERE/'exports';checks=json.loads((exports/'slice-clearances.json').read_text())
    assert checks['passed'] and checks['project_sha256']==sha(exports/'Holder-pair-sliced.3mf')
    assert checks['manifest_sha256']==sha(exports/'manifest.json')
    assert checks['r2_checker_sha256']==sha(HERE/'verify_slice.py')
    geom=json.loads((exports/'geometry-checks.json').read_text())
    assert geom['r2_checker_sha256']==sha(HERE/'verify_and_render.py')
    manifest=json.loads((exports/'manifest.json').read_text())
    for name,digest in manifest['source_sha256'].items():assert sha(HERE/name)==digest,name
    out.mkdir(parents=True,exist_ok=True)
    for name in ['Design-preview.png','Key_Battery_Carrier.stl','XIAO_Rod_Holder.stl','Holder-pair-layout.3mf','Holder-pair-sliced.3mf','Assembly-reference.glb']:
        shutil.copy2(exports/name,out/name)
    (out/'README.md').write_text((HERE/'README.md').read_text().replace('](exports/Design-preview.png)','](Design-preview.png)'))
    files=[]
    for d in [HERE,HERE.parent/'carbon-rod-holders']:
        files+=list(d.glob('*.py'))+[d/'parameters.json',d/'requirements.txt',d/'README.md']
    files.append(HERE.parent/'carbon-rod-holders/exports/Key_Battery_Carrier.stl')
    helpers=HERE.parent/'printed-loop-wand'
    files += [helpers/'shard-tube-r2'/n for n in ['direct_switches.py','print_projects.py','check_sliced_paths.py']]
    files += list((helpers/'shard-tube-r2/print-settings').glob('*.json'))+[helpers/'v20/compare_mass.py']
    mapping={'source/hardware/'+str(p.relative_to(HERE.parent)):p for p in files}
    mapping.update({'exports/'+p.name:p for p in exports.iterdir()if p.is_file()});mapping['README.md']=HERE/'README.md'
    digests={n:sha(p)for n,p in mapping.items()};target=out/'Wand-holder-prototypes-R2.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED)as z:
        for n,p in sorted(mapping.items()):z.write(p,n)
        z.writestr('package-sha256.json',json.dumps(digests,indent=2)+'\n')
    with zipfile.ZipFile(target)as z:
        assert z.testzip()is None
        for n,d in digests.items():assert hashlib.sha256(z.read(n)).hexdigest()==d
    print(target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();package(a.out)
