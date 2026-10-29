#!/usr/bin/env python3
"""Ethan's long, thin, solid rod: no internal wire bore; wires run outside.

Composes the thin-rod study's checked helix and integral sensor fork. It
preserves that study and all previous handed grips; this bare-rod prototype
uses externally attached controls/battery rather than claiming their fit.
"""
from pathlib import Path
import argparse, importlib.util, json, hashlib, sys
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('long_rod_base',HERE.parent/'thin-rod-study/wand_cad.py')
b=importlib.util.module_from_spec(spec);sys.modules[spec.name]=b;spec.loader.exec_module(b)
v=b.v; mf=b.mf
LENGTH=500.; SHAFT_END=460.; HEAD_SHIFT=90.; BASE=8.; TIP=5.8
JOINTS=[(154.,182.),(308.,336.)]
b.SHAFT_END=SHAFT_END

def geometry():
    solid=b.body(BASE,TIP)
    # The long rod is three printable sections. Long half-laps keep the joint
    # inside the taper; adhesive/tape retain them, without an oversized collar.
    lower=solid^v.box(-30,30,-30,30,-1,JOINTS[0][1])
    middle=solid^v.box(-30,30,-30,30,JOINTS[0][0],JOINTS[1][1])
    upper=solid^v.box(-30,30,-30,30,JOINTS[1][0],SHAFT_END+.1)
    for lo,hi,left,right in [(154.,182.,'lower','middle'),(308.,336.,'middle','upper')]:
        cut_a=v.box(-30,30,-.1,30,lo,hi+.05)
        cut_b=v.box(-30,30,-30,.1,lo-.05,hi)
        if left=='lower':lower-=cut_a
        else:middle-=cut_a
        if right=='middle':middle-=cut_b
        else:upper-=cut_b
    # Wider integrated fork supports replace the old small detachable tip.
    upper+=b.sensor_fork().translate((0,0,HEAD_SHIFT))
    return {'Lower_Rod':lower,'Middle_Rod':middle,'Upper_Rod_Integral_Gyro_Mount':upper}

def check(parts):
    for n,s in parts.items():
        assert s.status()==mf.Error.NoError and len(s.decompose())==1,(n,s.status(),len(s.decompose()))
    names=list(parts);intersections={}
    for i,n in enumerate(names):
        for other in names[i+1:]:
            vol=abs((parts[n]^parts[other]).volume());assert vol<.003,(n,other,vol)
            intersections[n+'/'+other]=vol
    upper=parts[names[-1]];probes={n:p.translate((0,0,HEAD_SHIFT))for n,p in b.probes().items()}
    clear={n:abs((upper^p).volume())for n,p in probes.items()};assert max(clear.values())<.003,clear
    body=parts[names[0]]+parts[names[1]]+upper
    profile=[]
    for z in [12.,72.,125.,220.,270.,370.,420.]:
        section=body.slice(z);loops=section.to_polygons()
        # Each section away from laps is one simply connected solid: no bore.
        assert len(loops)==1,(z,len(loops))
        points=np.asarray(loops[0]);r=np.linalg.norm(points,axis=1)
        assert max(r)<=b.envelope(z,BASE,TIP)+.004
        profile.append({'z_mm':z,'max_diameter_mm':float(max(r)*2),'core_diameter_mm':float(min(r)*2),'holes':0})
    assert all(a['max_diameter_mm']>c['max_diameter_mm']for a,c in zip(profile,profile[1:]))
    # Retain the actual board-removal pivot at the new head position.
    board=probes['board'];pivot=(0.,v.BOARD_Y+v.BOARD_T/2,v.BOARD0+21.+HEAD_SHIFT)
    rigid=upper-v.board_release_clip().translate((0,0,HEAD_SHIFT))
    hits=[abs((rigid^board.translate(tuple(-x for x in pivot)).rotate((a,0,0)).translate(pivot)).volume())for a in np.arange(0,10.01,.5)]
    assert max(hits)<.003,max(hits)
    return {'overall_length_mm':LENGTH,'body_maximum_diameter_mm':BASE,'body_tip_maximum_diameter_mm':TIP,
        'solid_cross_sections':profile,'lap_overlap_mm':28.,'lap_face_gap_mm':.2,
        'assembly_overlap_mm3':intersections,'board_solder_usb_wire_clearance_mm3':clear,
        'board_removal_overlap_mm3':max(hits),'integral_gyro_mount':True,'external_wires':True,
        'physical_fit_verified':False,'physical_strength_verified':False}

def build(out):
    out.mkdir(parents=True,exist_ok=False);parts=geometry();report=check(parts)
    records=[b.export(n,s,out)for n,s in parts.items()]
    # Recheck delivered STLs, rather than only the in-memory solids.
    loaded={}
    for p in records:
        mesh=trimesh.load_mesh(out/p['file'],process=True);mesh.apply_transform(p['print_to_assembly'])
        loaded[p['name']]=v.b.closed_mesh(mesh.vertices,mesh.faces,p['name'])
    check(loaded)
    result={'version':'Long solid rod 1','length_mm':LENGTH,'source_tube':b.SOURCE_TUBE,
        'checks':report,'parts':records,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'dependency_sha256':{str(f.relative_to(HERE.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [HERE.parent/'thin-rod-study/wand_cad.py',Path(v.__file__)]}}
    (out/'manifest.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'checks':report,'parts':[{k:p[k]for k in ['name','file','sha256','checks']}for p in records]},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out.resolve())
