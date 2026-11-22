"""One complete standalone kit. The bought board, connector, lead and cell are guide-only."""
import argparse
from pathlib import Path
from design61 import OUT, lead
import plate60

LABELS=dict(plate60.LABELS,Touch_Paddle='Connector-down touch paddle',Key_Carrier='Key holder with upper battery extension')
MINIMA=plate60.MINIMA
printer=plate60.prior.p57

def parts():
    altered={'Key_Carrier':(-90,0),'Touch_Paddle':(180,90),'Hinge_Pin':(0,0),'Hinge_Pin_Snug':(0,0)}
    rows=[]
    for row in plate60.parts():
        name=row['name']
        if name in altered or name in ('Pin_Clip','Pin_Clip_Spare'):
            src=OUT/row['source'].name
            pose=printer.pose_for(src,*altered[name]) if name in altered else printer.side_pose(src)
            row=dict(row,source=src,assembly_to_print=pose)
        if name=='Touch_Paddle':
            row=dict(row,bed_center=(139.6,146),panel=dict(row['panel'],size=(75,60),wire_exit=True))
        if name=='DFR_Clip_Right':
            row=dict(row,bed_center=(100,101.6))
        if name=='Key_Carrier':
            stations=[18.7,-21.5,14.2,-22.45,20.2,-24.0]
            row['panel']=dict(row['panel'],fin_thickness=1.45,ties=[dict(t,at=x) for t,x in zip(row['panel']['ties'],stations)])
        rows.append(row)
    return rows

def panel_builder(body, panel):
    backed=printer.panel_builder(body,panel)
    if panel.get('wire_exit'):
        pose=printer.pose_for(OUT/'Touch_Paddle-assembly.stl',180,90)
        channel=lead().transform(pose[:3]).project().offset(.65).extrude(1).translate((0,0,-.2))
        return backed-(channel-body)
    return backed

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('layout',type=Path)
    printer.write_layout(parts(),parser.parse_args().layout,plate60.prior.p58.TOWER,'R61 connector-down key kit',panel_builder=panel_builder)
