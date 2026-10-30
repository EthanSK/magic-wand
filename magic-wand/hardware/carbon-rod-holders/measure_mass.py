#!/usr/bin/env python3
"""Reuse the existing extrusion-accounting reader for one holder pair."""
from pathlib import Path
import importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wand_mass_reader',HERE.parent/'printed-loop-wand/v20/compare_mass.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if __name__=='__main__':
    result=m.inspect(HERE/'exports/Holder-pair-sliced.3mf')
    assert result['build_instances']==2,result
    result['scope']='One carrier plus one tip holder. Model plastic and brim separate. Bought parts, rod, tape, glue and wires excluded. Slicer estimate, not weighed.'
    (HERE/'exports/mass.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['object_printed_parts_g','printed_parts_g','supports_and_brim_g','total_slicer_g']},indent=2))
