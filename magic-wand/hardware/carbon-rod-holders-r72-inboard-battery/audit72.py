"""Audit actual R72 native extrusion against all R71 routes, with the battery lane moved inward."""
from pathlib import Path
import json
import sys
import numpy as np
import design72 as m
import kit72
import audit71 as a


def routes():
    groups = a.routes()
    holder = groups['Key_Carrier']
    for name in a.battery_gauges():
        holder[name] = [solid.translate((m.INBOARD,0,0)) for solid in holder[name]]
    return groups


def spring_opening(points, pose):
    shifted = pose.copy()
    shifted[:3,3] += shifted[:3,:3] @ np.array([m.INBOARD,0.,0.])
    return a.spring_opening(points,shifted)


def audit(folder):
    base = m.prev.OUT / 'print-mechanisms'
    reference = json.loads((base/'r70-base-reference.json').read_text())
    a.a61.audit(folder,kit72.parts,m.OUT,expected_names=kit72.previous.COMPLETE,
                route_builder=routes,spring_probe=spring_opening,base_minima=dict(a.a61.MINIMA),
                expected_fin_count=5,seam_layers=25,seam_reference_area_mm2=reference['reference_area_mm2'])
    fins_path = folder / 'fin-design.json'
    fins = json.loads(fins_path.read_text())
    ties = next(row for row in kit72.parts() if row['name'] == 'Key_Carrier')['panel']['ties']
    below = sum(tie['face'] == '-y' for tie in ties)
    above = sum(tie['face'] == '+y' for tie in ties)
    fins['removal'][0] = f'Cut the {below} underside fins and {above} top fin at their narrow necks.'
    fins_path.write_text(json.dumps(fins, indent=2)+'\n')
    seat = a.a69.printed_seat_report(folder,render=False)
    seat['versions']['R72'] = seat['versions'].pop('R69')
    seat['r72_fraction_of_r63'] = seat.pop('r69_fraction_of_r63')
    (folder/'printed-seat.json').write_text(json.dumps(seat,indent=2)+'\n')
    if not seat['passes']:
        raise ValueError('OP1 printed bearing seat failed comparison to the working R63 print')


if __name__=='__main__':
    audit(Path(sys.argv[1]))
