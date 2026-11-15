"""Export R43's raised key seats and complete guide; never send a print."""
import argparse
import json
import math
from pathlib import Path
from unittest.mock import patch
import numpy as np
import holder43 as d
import assembly42 as upstream

HERE=d.HERE
OUT=HERE/'exports'
A,H=upstream.A,upstream.H
LABEL='R43 raised Choc keys flush with DFRobot touch'


def write_guide(checks,battery,door):
    with patch.object(upstream,'d',d),patch.object(upstream,'HERE',HERE),patch.object(upstream,'OUT',OUT):
        upstream.write_guide(checks,battery,door)
        guide=json.loads((OUT/'assembly-guide.json').read_text())
        # Raise each bought switch along its local assembly Z, including
        # insertion frames and the whole-wand module's placement transform.
        local=np.eye(4);local[2,3]=d.KEY_RAISE_MM
        count=0
        for module in guide['modules'].values():
            keys={n for n,a in module['actors'].items()
                  if Path(a.get('file','')).name in ('choc_switch.stl','choc_hotswap_socket.stl')}
            for step in module['steps']:
                for sample in step['samples']:
                    for name in keys:
                        m=np.eye(4);m[:3]=np.asarray(sample[name]).reshape(3,4)
                        sample[name]=(m@local)[:3].ravel().tolist();count+=1
        assert count>100
        guide['modules']['whole']['note']='Same R43 parts on one rod. Four outer key seats are 1.72 mm higher; the OP1, touch board and rod positions are unchanged. External wiring lengths are not dimensioned.'
        for name in ('key','dfr'):
            guide['modules'][name]['note']=guide['modules'][name]['note'].replace('Choc keys and heights match R39.','Choc XY positions match R39.')
            guide['modules'][name]['note']+=' R43 raises the four Choc seats by 1.72 mm to match the released touch top; key travel remains independent.'
        guide['sources'].update(generator_sha256=H.sha(__file__),
            upstream_generator_sha256=H.sha(upstream.__file__),raised_key_pose_frames=count)
        report=upstream.guide_checks(guide)
        A.write_json(OUT/'assembly-guide.json',guide)
        return report


def export():
    (OUT/'guide').mkdir(parents=True,exist_ok=True)
    A.OUT=H.OUT=OUT
    checks=d.checks()
    assert checks['passed'],'R43 geometry checks failed'
    H.PRINT_ROT[d.BRACKET]=A.trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0])
    H.PRINT_ROT['Battery_End_Door']=H.PRINT_ROT[d.BRACKET]
    H.PRINT_ROT[d.CLIP]=H.PRINT_ROT[upstream.CLIP2]=np.eye(4)
    shapes=((d.CARRIER,d.carrier()),(d.BRACKET,d.bracket()),(d.CLIP,d.clip_part()),
            (upstream.CLIP2,d.clip_part()),('Battery_End_Door',d.battery_door()))
    parts={n:H.export_part(n,s,n) for n,s in shapes}
    parts['Battery_Holder']=d.BATTERY.copy_part('Battery_Holder',d.BATTERY.HERE,OUT,anchored=True)
    A.write_json(OUT/'anchors.json',{'parts':{'Battery_Holder':upstream.previous.old.read(
        d.BATTERY.HERE/'exports/anchors.json')['parts']['Battery_Holder']}})
    battery=d.BATTERY.read(OUT/'Battery_Holder-assembly.stl')
    door=d.BATTERY.read(OUT/'Battery_End_Door-assembly.stl')
    checks['battery_door']=upstream.previous.battery_checks(battery,door)
    A.write_json(OUT/'geometry-checks.json',{'revision':HERE.name,'physical_fit_verified':False,
        'sliced':False,'checks':checks})
    A.write_json(OUT/'manifest.json',{'revision':HERE.name,'units':'mm','parts':parts,
        'physical_fit_verified':False,'print_cleared':False,
        'source_sha256':{p.name:H.sha(p) for p in (HERE/'holder43.py',Path(__file__),HERE/'complete-assembly.json')},
        'upstream_sha256':{p.name:H.sha(p) for p in (d.R42/'holder42.py',Path(upstream.__file__),d.R41/'holder41.py')}})
    print(json.dumps({'geometry_passed':True,'guide':write_guide(checks,battery,door)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--register',action='store_true')
    args=parser.parse_args()
    if args.register:
        A.OUT=H.OUT=OUT
        with patch.object(upstream,'d',d),patch.object(upstream,'HERE',HERE),patch.object(upstream,'OUT',OUT):
            upstream.guide_checks(json.loads((OUT/'assembly-guide.json').read_text()))
        A.register_assembly(OUT/'assembly-guide.json','r43',LABEL,make_current=True,group_keys=True)
    else:export()
