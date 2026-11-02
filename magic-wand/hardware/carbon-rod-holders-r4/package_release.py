#!/usr/bin/env python3
"""Package only fresh checked meshes, source references and viewer dependencies."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def package(out):
    exports=HERE/'exports'
    manifest=json.loads((exports/'manifest.json').read_text())
    geom=json.loads((exports/'geometry-checks.json').read_text())
    assert geom['passed'] and geom['sensor_stl_identical_to_r2']
    assert geom['manifest_sha256']==sha(exports/'manifest.json')
    assert geom['checker_sha256']==sha(HERE/'verify_geometry.py')
    for path,digest in manifest['source_sha256'].items(): assert sha(HERE/path)==digest,path
    for option in ['front','rear','lower']:
        project=exports/f'Holder-{option}-sliced.3mf'
        check=json.loads((exports/f'slice-clearances-{option}.json').read_text())
        mass=json.loads((exports/f'mass-{option}.json').read_text())
        receipt=json.loads((exports/f'print-checks-{option}.json').read_text())
        assert check['passed'] and check['checker_sha256']==sha(HERE/'verify_slice.py')
        assert check['manifest_sha256']==sha(exports/'manifest.json')
        assert check['project_sha256']==mass['archive_sha256']==receipt['sliced_project_sha256']==sha(project)
        assert receipt['generator_sha256']==sha(HERE/'print_project.py')
        assert not receipt['warnings'], (option,receipt['warnings'])
        assert geom['options'][option]['final_stl_sha256']==sha(exports/f'Carrier_{option}.stl')
    review=json.loads((exports/'mechanical-review.json').read_text())
    assert review['final_manifest_sha256']==sha(exports/'manifest.json')
    assert review['final_cad_sha256']==manifest['source_sha256']['cad.py']
    assert review['final_geometry_checker_sha256']==sha(HERE/'verify_geometry.py')
    coupon=json.loads((exports/'fit-coupons/manifest.json').read_text())
    assert coupon['generator_sha256']==sha(HERE/'fit_coupons.py') and coupon['cad_sha256']==sha(HERE/'cad.py')
    for name,r in coupon['parts'].items(): assert r['sha256']==sha(exports/'fit-coupons'/(name+'.stl'))
    scene=json.loads((exports/'review-scene.json').read_text())
    assert scene['sources']['manifest_sha256']==sha(exports/'manifest.json')
    assert scene['sources']['cad_sha256']==sha(HERE/'cad.py')
    assert scene['sources']['generator_sha256']==sha(HERE/'build_preview.py')
    render=json.loads((exports/'render-receipt.json').read_text())
    assert render['manifest_sha256']==sha(exports/'manifest.json')
    assert render['generator_sha256']==sha(HERE/'render_options.py')
    assert render['image_sha256']==sha(exports/'Battery-options.png')
    files=[]
    for folder in [HERE,HERE.parent/'carbon-rod-holders-r3',HERE.parent/'carbon-rod-holders-r2',HERE.parent/'carbon-rod-holders']:
        files += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.json','.md','.txt','.stl','.3mf','.glb','.stp','.png','.mjs','.html'}]
    helpers=HERE.parent/'printed-loop-wand'
    files += [helpers/'shard-tube-r2'/n for n in ['direct_switches.py','print_projects.py','check_sliced_paths.py']]
    files += list((helpers/'shard-tube-r2/print-settings').glob('*.json'))
    files += [helpers/'v20/compare_mass.py',helpers/'preview/view-input.mjs',helpers/'preview/free-view-input.mjs',helpers/'preview/free-view-controls.mjs',ROOT/'LICENSE']
    files += list((ROOT/'docs/lib/three-0.185.1').glob('*'))
    mapping={'source/'+str(p.relative_to(ROOT)):p for p in files if p.is_file()}
    mapping.update({'exports/'+str(p.relative_to(exports)):p for p in exports.rglob('*') if p.is_file()})
    mapping['README.md']=HERE/'README.md'
    out.mkdir(parents=True,exist_ok=True)
    for p in exports.iterdir():
        if p.is_file() and (p.suffix in {'.stl','.3mf','.glb','.png'}): shutil.copy2(p,out/p.name)
    shutil.copytree(exports/'fit-coupons',out/'fit-coupons',dirs_exist_ok=True)
    shutil.copy2(HERE/'README.md',out/'README.md')
    digests={n:sha(p) for n,p in mapping.items()}
    target=out/'Wand-holder-prototypes-R4.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(mapping.items()): archive.write(path,name)
        archive.writestr('package-sha256.json',json.dumps(digests,indent=2)+'\n')
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name,digest in digests.items(): assert hashlib.sha256(archive.read(name)).hexdigest()==digest
    print(target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);package(p.parse_args().out)
