#!/usr/bin/env python3
"""Repeat inherited interface/motion checks against actual R13 exports."""
import json
import cad

check=cad.load('verify_geometry',cad.base.HERE)
check.cad=cad;check.OUT=cad.HERE/'exports'
if __name__=='__main__':
    check.check()
    report=json.loads((check.OUT/'geometry-checks.json').read_text())
    actual=check.read('XIAO_Rod_Holder');previous=cad.base.sensor_holder()
    # Free spring arms live only within each ring's axial width. The fixed
    # longitudinal beam between rings is deliberately reinforced in R13.
    width=cad.P['rod']['sensor_clip_width']
    lower=cad.union([cad.box(-7,7,y-width/2,y+width/2,-6,0)for y in [-3.8,22.2]])
    difference=check.overlap(actual-previous,lower)+check.overlap(previous-actual,lower)
    assert difference<.002,difference
    report['sensor_lower_spring_arm_change_mm3']=difference
    report['sensor_fixed_axial_rail_added_lower_volume_mm3']=check.overlap(actual-previous,cad.box(-7,7,-2.6,21,-6,0))
    report['inherited_checker_sha256']=cad.sha(cad.base.HERE/'verify_geometry.py')
    (check.OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
