#!/usr/bin/env python3
"""Reuse R1 checks/depth renderer; add reversed USB and hollow-tube wire checks."""
import json
from pathlib import Path
import numpy as np
import cad
HERE=Path(__file__).resolve().parent;OUT=HERE/'exports'
v=cad.load('verify_and_render');v.HERE=HERE;v.OUT=OUT

def checks():
    key,tip,refs,report=v.checks();_,solid=v.read('XIAO_Rod_Holder')
    s=cad.P['sensor'];w=cad.wire_route();tube=cad.tube_y(3.5,4,-25,23.4)
    report['r2_clearances_mm3']={
      'usb_negative_y_plug_approach':v.collision(solid,cad.box(-5.2,5.2,-22.7,-.7,s['board_z']+.9,s['board_z']+4.4)),
      'nominal_wire_vs_holder':v.collision(solid,w),
      'nominal_wire_vs_tube_wall':v.collision(tube,w),
      'nominal_wire_vs_board':v.collision(refs['pcb'],w)}
    assert max(report['r2_clearances_mm3'].values())<.002,report
    assert cad.mesh(refs['usb']).bounds[0,1]<0
    assert np.allclose(tip.bounds,[[-10.6,-5.,-5.4],[10.6,23.4,10.]],atol=.01)
    assert cad.sha(OUT/'Key_Battery_Carrier.stl')==cad.sha(cad.BASE/'exports/Key_Battery_Carrier.stl')
    report['carrier_identical_to_r1']=True
    report['r2_checker_sha256']=cad.sha(Path(__file__))
    report['wire_bundle_diameter_mm']=s['wire_bundle_diameter']
    report['wire_envelope_measured']=False
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    return key,tip,refs,report

def pane(ax,title,m,refs,loaded,tip=False):
    objects=[(m,'#db963f' if tip else '#249da2')]
    for name,obj in refs.items():
        if tip and name not in ['pcb','usb','rod']:continue
        if not tip and name in ['pcb','usb']:continue
        if not loaded and name!='rod':continue
        if name=='rod':obj=cad.tube_y(3.5,4,*((-9,23.4)if tip else(-20,70)))
        objects.append((cad.mesh(obj),'#303741'if name=='rod'else '#6e7888'if name=='battery'else '#387c52'if name=='pcb'else '#b6bfcc'if name=='usb'else '#e2e5e9'))
    if tip and loaded:objects.append((cad.mesh(cad.wire_route()),'#af4a3c'))
    bounds=np.array([[-15,-24,-6],[15,31,16]])if tip else np.array([[-32,-20,-6],[32,70,21]])
    v.draw(ax,objects,bounds);ax.set_title(title,fontsize=15,color='#162635',loc='left',pad=6)

if __name__=='__main__':
    v.pane=pane
    v.render(*checks())
