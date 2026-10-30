#!/usr/bin/env python3
"""Reuse the existing extrusion accounting without duplicating its rules."""
import json
import cad
if __name__=='__main__':
    m=cad.load('measure_mass').m
    result=m.inspect(cad.HERE/'exports/Holder-pair-sliced.3mf')
    assert result['build_instances']==2,result
    result['scope']='One carrier plus one R2 tip. Model plastic and brim separate; bought parts, tube, wires and retention excluded. Slicer estimate, not weighed.'
    (cad.HERE/'exports/mass.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['object_printed_parts_g','printed_parts_g','supports_and_brim_g','total_slicer_g']},indent=2))
