#!/usr/bin/env python3
"""Account actual model, support and brim extrusion separately."""
import argparse
import json
import cad
if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--option',choices=list(cad.OPTIONS),default='modular'); a=p.parse_args()
    m=cad.load('compare_mass',cad.HERE.parent/'printed-loop-wand/v20')
    r=m.inspect(cad.HERE/'exports'/('Holder-'+a.option+'-sliced.3mf'))
    assert r['build_instances']==4
    r['scope']='One thumb-clearance key module, battery cage and end gate, and USB-up XIAO holder. Model/support/brim separate. Bought parts, tube, tape, glue and wires excluded; slicer estimate, not weighed.'
    (cad.HERE/'exports'/('mass-'+a.option+'.json')).write_text(json.dumps(r,indent=2)+'\n')
    print({k:r[k] for k in ['object_printed_parts_g','printed_parts_g','supports_and_brim_g','total_slicer_g']})
