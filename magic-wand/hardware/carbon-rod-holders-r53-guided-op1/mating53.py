"""Test unobstructed entrances on the final native print, including first-layer ties."""
import argparse
import json
from pathlib import Path
import numpy as np
import build53 as b
from openings53 import check_routes, read_native, digest
from checks53 import old, q

def gauges():
    old.configure_new_op1()
    hw = q.hardware()
    # The entire Ø4 pivot must lower into both open seats. A short length at each
    # end remains inside the same bearing from the entrance down to seated contact.
    journal = b.axle() ^ b.mirrored(b.box(7.53,9.45,26,33,15,20))
    def sweep(solid, delta, distance, step=.5):
        return [solid.translate(tuple(np.array(delta)*d)) for d in np.linspace(0,distance,1+int(distance/step))]
    carrier = dict(journals_from_above=sweep(journal,(0,0,1),11))
    for k in ('board','sockets','housing','plug','switch'):
        carrier[k+'_from_above']=sweep(hw[k],(0,0,1),8,1)
    carrier['seated_wire_outlet'] = [hw['op1_wire']]
    # Rigid region of each slider. Exclude only the intentional sprung latch.
    carrier['hinge_cap_from_rear']=sweep(b.hinge_cap()-b.box(-3.5,3.5,26,34,18,21.1),(0,1,0),8,1)
    not_bump = b.ubox(-9,-b.LID_HALF+.02,7,11,10.9,13)
    carrier['lid_from_front']=sweep(b.op1_lid()-not_bump,-b.board_axis(),32,1)
    # Test the case in the sleeve, including its complete opening before assembly.
    paddle=dict(switch_case_into_sleeve=sweep(hw['switch'],(0,0,-1),7,1))
    for sign in (-1,1):
        # Gauging just the shaft avoids counting the permanent transverse bottom bar.
        gauge=b.box(sign*b.HOLE_X-1.05,sign*b.HOLE_X+1.05,b.HOLE_Y-1.10,b.HOLE_Y+1.10,b.PLATE_Z-4,b.SEAT_Z+3)
        paddle['post_'+str(sign)]=[gauge]
    return {'Key_Carrier':carrier,'Touch_Paddle':paddle}

def check(archive,framefile,output):
    frame=json.loads(framefile.read_text())['parts']
    points,labels=read_native(archive)
    records={}
    for part,paths in gauges().items():
        records[part]=check_routes(paths,np.array(frame[part]['assembly_to_machine']),points,labels)
    data=dict(archive_sha256=digest(archive),frame_sha256=digest(framefile),parts=records)
    output.write_text(json.dumps(data,indent=2)+'\n')
    bad=[(part,n) for part,rs in records.items() for n,r in rs.items() if r['obstructed_poses']]
    if bad:raise ValueError(bad)
if __name__=='__main__':
    cli=argparse.ArgumentParser()
    for name in ('archive','frame','output'):cli.add_argument(name,type=Path)
    args=cli.parse_args()
    check(args.archive,args.frame,args.output)
