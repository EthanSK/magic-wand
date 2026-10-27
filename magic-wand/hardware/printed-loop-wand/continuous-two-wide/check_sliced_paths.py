#!/usr/bin/env python3
"""Check real printed paths, including supports, through functional spaces."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main(out):
    model=load('continuous',HERE/'wand_cad.py');c,_,head=model.make()
    check=load('paths',HERE.parent/'lattice-study/check_sliced_paths.py')
    check.HERE=HERE;check.ROOT=ROOT
    check.s=types.SimpleNamespace(configure=lambda _:c,open_head=lambda _:head,sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest())
    manifest=json.loads((HERE/'exports/manifest.json').read_text())
    wrapped={'variants':{'continuous':{'parts':manifest['parts']}},'shared_parts':manifest['shared_parts']}
    project=ROOT/'magic-wand-3d-models/Print-Continuous-Two-Wide-complete.3mf'
    result=check.inspect('continuous',wrapped,project)
    out.write_text(json.dumps(result,indent=2)+'\n');print('Combined shaft and cradle sliced clearances passed')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
