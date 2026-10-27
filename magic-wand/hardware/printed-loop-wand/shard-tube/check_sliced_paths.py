#!/usr/bin/env python3
"""Check real printed paths, including supports, through functional spaces."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main(out):
    model=load('continuous',HERE/'wand_cad.py');c,_,head=model.make()
    check=load('paths',HERE.parent/'continuous-two-wide-v19/inspect_sliced_paths.py')
    check.HERE=HERE;check.ROOT=ROOT
    check.s=types.SimpleNamespace(configure=lambda _:c,open_head=lambda _:head,sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest())
    manifest=json.loads((HERE/'exports/manifest.json').read_text())
    wrapped={'variants':{'continuous':{'parts':manifest['parts']}},'shared_parts':manifest['shared_parts']}
    project=ROOT/'magic-wand-3d-models/Print-Shard-Tube-complete.3mf'
    def holder_areas(name,x,y,z):
        if name!='Sense_Open_Cradle':return {}
        areas={'holder_socket':(x*x+y*y<6.3**2)&(z>343.3)&(z<351.9)}
        for angle in [-40.,-30.,-20.,-10.,0.]:
            for side in [0.,180.]:
                a=math.radians(angle+side);xl=x*math.cos(a)-y*math.sin(a);yl=x*math.sin(a)+y*math.cos(a)
                areas[f'holder_turn_{angle}_{side}']=(abs(xl)<.65)&(yl>6.7)&(yl<7.85)&(z>347.2)&(z<348.8)
                if angle==-40.:
                    areas[f'holder_entry_{side}']=(abs(xl)<.65)&(yl>6.7)&(yl<7.85)&(z>343.3)&(z<348.8)
        return areas
    result=check.inspect('continuous',wrapped,project,shaft_end=351.5,extra_areas=holder_areas)
    out.write_text(json.dumps(result,indent=2)+'\n');print('Combined shaft and cradle sliced clearances passed')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
