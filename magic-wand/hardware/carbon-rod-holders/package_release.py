#!/usr/bin/env python3
"""Derive a portable review package from checked canonical sources/exports."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
HERE=Path(__file__).resolve().parent

def package(out):
    exports=HERE/'exports';checks=json.loads((exports/'slice-clearances.json').read_text())
    assert checks['passed'],'Do not package a failed extrusion audit'
    assert checks['project_sha256']==hashlib.sha256((exports/'Holder-pair-sliced.3mf').read_bytes()).hexdigest()
    assert checks['manifest_sha256']==hashlib.sha256((exports/'manifest.json').read_bytes()).hexdigest()
    out.mkdir(parents=True,exist_ok=True)
    deliver=['Design-preview.png','Key_Battery_Carrier.stl','XIAO_Rod_Holder.stl','Holder-pair-layout.3mf','Holder-pair-sliced.3mf','Assembly-reference.glb']
    for name in deliver:shutil.copy2(exports/name,out/name)
    (out/'README.md').write_text((HERE/'README.md').read_text().replace('](exports/Design-preview.png)','](Design-preview.png)'))
    # Distribution copies are generated, never another editable authority.
    sources=list(HERE.glob('*.py'))+[HERE/'parameters.json',HERE/'requirements.txt',HERE/'README.md']
    helpers=HERE.parent/'printed-loop-wand'
    deps=[helpers/'shard-tube-r2'/n for n in ['direct_switches.py','print_projects.py','check_sliced_paths.py']]
    deps += list((helpers/'shard-tube-r2/print-settings').glob('*.json'))
    deps += [helpers/'v20/compare_mass.py']
    mapping={}
    for p in sources+deps:mapping['source/hardware/'+str(p.relative_to(HERE.parent))]=p
    for p in exports.iterdir():
        if p.is_file():mapping['exports/'+p.name]=p
    mapping['README.md']=HERE/'README.md'
    digests={name:hashlib.sha256(path.read_bytes()).hexdigest()for name,path in mapping.items()}
    target=out/'Wand-holder-prototypes.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED)as z:
        for name,path in sorted(mapping.items()):z.write(path,name)
        z.writestr('package-sha256.json',json.dumps(digests,indent=2)+'\n')
    with zipfile.ZipFile(target)as z:
        assert z.testzip()is None
        for name,digest in digests.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    print(target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();package(a.out)
