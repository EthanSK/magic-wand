"""Check the two compliant OP1 locating fingers against the bought references and their entry range."""
import argparse
from pathlib import Path
import json

import numpy as np

import build53 as b
from carrier53 import locator
from checks53 import old, q, file_hash


def inspect(directory):
    old.configure_new_op1()
    src=directory/'Key_Carrier-assembly.stl'
    carrier=b.load(src)
    hw=q.hardware()
    pieces={key:hw[key] for key in ('sockets','housing','plug')}
    cases=[]
    captures=[]
    for pitch in (17.45,17.90,18.35):
        pieces['board']=q.op1_board(pitch,3.60)
        for offset in (0.,.12,.22,.30,.40):
            worst=(0.,None)
            for dx,dy in ((offset,0.),(-offset,0.),(0,offset),(0,-offset),(offset*.707,offset*.707),(-offset*.707,offset*.707)):
                xy=np.asarray(b.board_point(dx,dy))-np.asarray(b.STATION)
                for height in (0.,.4,1.0):
                    for name,obj in pieces.items():
                        touch=(obj.translate((float(xy[0]),float(xy[1]),height)) ^ carrier).volume()
                        if touch>worst[0]:
                            worst=(touch,(dx,dy,height,name))
            cases.append(dict(pitch_mm=pitch,radial_offset_mm=offset,worst_interference_mm3=round(worst[0],6),where=worst[1]))
    for station,side in ((-6.25,-1),(11.65,1)):
        clearance,positive,root,leaf,tip=locator(station,side)
        fixed=carrier-positive
        free_half=leaf ^ b.ubox(-7,7,station-2,station+4.30,-2,18)
        readings=[]
        for dist in (.35,.70):
            travel=((free_half+tip).translate((0,0,-dist)) ^ fixed).volume()
            readings.append(dict(travel_mm=dist,interference_mm3=round(max(0.,travel),6)))
        nose_inside=(tip^b.ubox(-1.8,1.8,station-1.8,station+1.8,b.PCB_Z,b.PCB_TOP)).volume()
        captures.append(dict(station_mm=station,engaged_plastic_mm3=round(nose_inside,4),downward_deflection=readings))
    report=dict(carrier_sha256=file_hash(src),eyelet_diameter_mm=3.60,fit_cases=cases,fingers=captures)
    (directory/'locator-fit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(cases, captures,flush=True)
    assert all(c['worst_interference_mm3']<.001 for c in cases if c['radial_offset_mm'] <= .12)
    assert all(f['engaged_plastic_mm3']>.4 and max(m['interference_mm3'] for m in f['downward_deflection'])<.002 for f in captures)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('directory',type=Path)
    inspect(p.parse_args().directory)
