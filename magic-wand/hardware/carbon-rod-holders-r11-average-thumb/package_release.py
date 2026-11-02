#!/usr/bin/env python3
"""Package R11 only after source, geometry, slice and scene freshness checks pass."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def checked_files() -> set[Path]:
    out=HERE/'exports';manifest=json.loads((out/'manifest.json').read_text())
    geometry=json.loads((out/'geometry-checks.json').read_text())
    sliced=json.loads((out/'slice-clearances-modular.json').read_text())
    printed=json.loads((out/'print-checks-modular.json').read_text())
    mass=json.loads((out/'mass-modular.json').read_text())
    scene=json.loads((out/'review-scene.json').read_text())
    assert geometry['passed'] and sliced['passed'] and not printed['warnings']
    for record in [geometry,sliced]:assert record['manifest_sha256']==sha(out/'manifest.json')
    assert geometry['checker_sha256']==sha(HERE/'verify_geometry.py')
    assert sliced['checker_sha256']==sha(HERE/'verify_slice.py')
    assert printed['generator_sha256']==sha(HERE/'print_project.py')
    assert printed['sliced_project_sha256']==sliced['project_sha256']==mass['archive_sha256']==sha(out/'Holder-modular-sliced.3mf')
    for path,digest in manifest['source_sha256'].items():assert sha(HERE/path)==digest,path
    for path,digest in manifest.get('fit_coupons',{}).items():assert sha(out/path)==digest
    for name,part in manifest['parts'].items():assert part['stl_sha256']==sha(out/(name+'.stl')),name
    assert scene['sources']['cad_sha256']==sha(HERE/'cad.py')
    assert scene['sources']['generator_sha256']==sha(HERE/'build_preview.py')
    assert scene['sources']['manifest_sha256']==sha(out/'manifest.json')
    assert scene['mass']==mass
    # Only the frozen dependency inputs are copied, with their real relative
    # tree. Older 3D revisions remain in Git; they are not alternate R11 sources.
    r7=HERE.parent/'carbon-rod-holders-r7-spring-clips'
    files={HERE/path for path in manifest['source_sha256']}
    files.update(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.update([r7/'exports/manifest.json',r7/'exports/XIAO_Rod_Holder.stl',r7/'README.md',r7/'references/LICENSE-CC-BY-SA.txt',r7/'preview/wheel-input.mjs'])
    files.update(p for p in (r7/'exports/fit-coupons').glob('*') if p.is_file())
    shared=HERE.parent/'printed-loop-wand'
    files.update(shared/'preview'/p for p in ['view-input.mjs','free-view-input.mjs','free-view-controls.mjs'])
    files.update(shared/'shard-tube-r2'/p for p in ['direct_switches.py','print_projects.py','check_sliced_paths.py'])
    files.update((shared/'shard-tube-r2/print-settings').glob('*.json'))
    files.add(shared/'v20/compare_mass.py');files.add(ROOT/'LICENSE')
    files.update((ROOT/'docs/lib/three-0.185.1').glob('*'))
    files.update((HERE.parent/'carbon-rod-holders/preview').glob('*'))
    return {p.resolve() for p in files if p.is_file()}

def package(destination: Path) -> None:
    files=checked_files();out=HERE/'exports'
    destination.mkdir(parents=True,exist_ok=True)
    for p in out.iterdir():
        if p.suffix in {'.stl','.3mf'}:shutil.copy2(p,destination/p.name)
    shutil.copy2(HERE/'README.md',destination/'README.md')
    r7=HERE.parent/'carbon-rod-holders-r7-spring-clips'
    shutil.copytree(r7/'exports/fit-coupons',destination/'fit-coupons',dirs_exist_ok=True)
    shutil.copytree(out/'fit-coupons',destination/'fit-coupons',dirs_exist_ok=True)
    mapping={'source/'+str(p.relative_to(ROOT)):p for p in files}
    mapping.update({'exports/'+str(p.relative_to(out)):p for p in out.rglob('*') if p.is_file()})
    mapping['README.md']=HERE/'README.md'
    hashes={name:sha(p) for name,p in mapping.items()}
    target=destination/'Wand-holder-prototypes-R11.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,p in sorted(mapping.items()):archive.write(p,name)
        archive.writestr('package-sha256.json',json.dumps(hashes,indent=2)+'\n')
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,digest in hashes.items():assert hashlib.sha256(archive.read(name)).hexdigest()==digest,name
    print(target,len(hashes),'verified members')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);package(p.parse_args().out)
