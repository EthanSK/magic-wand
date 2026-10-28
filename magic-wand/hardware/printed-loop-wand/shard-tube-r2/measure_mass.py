#!/usr/bin/env python3
"""Compare one complete left wand per row using actual sliced extrusion."""
from pathlib import Path
import argparse,importlib.util,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def measure():
 spec=importlib.util.spec_from_file_location('r2_mass_reader',HERE.parent/'v20/compare_mass.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
 versions={}
 for key,file in [('main_before','Print-Shard-Tube-one-left.3mf'),('R2_left_light','Print-Shard-R2-one-left-light.3mf'),('R2_left_weighted','Print-Shard-R2-one-left-weighted.3mf')]:versions[key]=reader.inspect(ROOT/'magic-wand-3d-models'/file)
 light=versions['R2_left_light'];heavy=versions['R2_left_weighted'];assert light['build_instances']==heavy['build_instances']==7
 delta=heavy['object_printed_parts_g']['Battery_Screw_Cap_Weighted']-light['object_printed_parts_g']['Battery_Screw_Cap_Light']
 return {'scope':'Exactly one complete left wand per row; printed plastic only. Actual electronics, cell, purchased switches, sockets, keycaps and wiring are unweighed and excluded. Supports/brim counted separately. Slicer estimates, not measured mass.',
 'versions':versions,'weighted_cap_extra_printed_g':round(delta,3),'weighted_extension_mm':18.,
 'infill':{'ordinary_parts_percent':20,'loop_and_keeper_percent':100,'weighted_cap_percent':45,'weighted_cap_pattern':'gyroid','weighted_cap_walls':3,'weighted_cap_top_bottom_layers':5},
 'light_hardware_allowance_to_80g':round(80.-light['printed_parts_g'],3),'light_hardware_allowance_to_100g':round(100.-light['printed_parts_g'],3),'physical_mass_measured':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=measure()
 with a.out.open('x')as f:json.dump(r,f,indent=2);f.write('\n')
 print(json.dumps({'printed_parts_g':{k:v['printed_parts_g']for k,v in r['versions'].items()},'weighted_cap_extra_g':r['weighted_cap_extra_printed_g']},indent=2))
