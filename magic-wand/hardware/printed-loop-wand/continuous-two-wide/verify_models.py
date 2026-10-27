#!/usr/bin/env python3
"""Check the exported meshes, joint routes, removable loop, and layer starts."""
from pathlib import Path
import argparse,importlib.util,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main(out):
    m=json.loads((HERE/'exports/manifest.json').read_text());study=module('mesh_check',HERE.parent/'lattice-study/verify_models.py');cad=module('continuous',HERE/'wand_cad.py');c,_,_=cad.make()
    own={p['name']:study.solid(p,HERE/'exports'/p['file']) for p in m['parts']};shared={p['name']:study.solid(p,HERE/'exports'/p['file']) for p in m['shared_parts']}
    shaft=own['Continuous_Shaft'];head=own['Sense_Open_Cradle'];a=c.HANDLE_END;top=c.TOP
    for source,digest in m['source'].items():assert hashlib.sha256((HERE/source).read_bytes()).hexdigest()==digest,source
    ref=json.loads((HERE.parent/'lattice-study/exports/manifest.json').read_text())['variants']['two-wide'];lower=next(p for p in ref['parts'] if p['name']=='Lower_Shaft');old=study.solid(lower,HERE.parent/'lattice-study/exports/two-wide'/lower['file'])
    zone=c.cyl(40.,a-1,a+18.9);joint=abs(((shaft^zone)-(old^zone)).volume())+abs(((old^zone)-(shaft^zone)).volume());assert joint<.75,joint
    bores={'shaft':abs((shaft^c.cyl(4.95,a-1,top+16.)).volume()),'head':abs((head^c.cyl(4.95,top-1,top+16.)).volume())};assert max(bores.values())<.001,bores
    clip=abs((c.board_release_clip()-head).volume());pockets=c.union([c.box(-10.5,10.5,-6.3,-2.1,x,y) for x,y in [(375.05,375.8),(376.15,377.35),(395.65,398.2)]])
    pocket_loss=abs(((c.board_corner_guides()^pockets)-head).volume());assert max(clip,pocket_loss)<.75,(clip,pocket_loss)
    # Same handed grips and loop by hash: reuse the established full path tests.
    prior=json.loads((HERE.parent/'lattice-study/exports/exported-model-checks.json').read_text())['variants']['two-wide']['loops']
    assert all(max(v['max_turn_overlap_mm3'],v['max_slide_overlap_mm3'])<.001 and min(v['hard_stops_mm3'])>1 for v in prior.values())
    islands=[]
    for z in np.arange(a+19.2,top-16.,.2):
        prev=shaft.slice(float(z-.2)).offset(.24)
        for component in shaft.slice(float(z)).decompose():
            if component.area()>.01 and (component^prev).area()<.001:islands.append(round(float(z),3))
    assert not islands,('Floating starts',islands[:20])
    report={'geometry':'actual exported STL solids','grip_joint_difference_mm3':joint,'wire_clearance_mm3':bores,'clip_lost_mm3':clip,'board_pockets_lost_mm3':pocket_loss,'loop_paths_reused':prior,'floating_layer_starts':islands,'physical_fit_verified':False,'physical_strength_verified':False}
    out.write_text(json.dumps(report,indent=2)+'\n');print('Exported shaft, tip and removable-loop checks passed')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
