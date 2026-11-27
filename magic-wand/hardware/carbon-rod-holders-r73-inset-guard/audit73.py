"""Measure the saved R73 slice with the R72 interface gauges and its unchanged base design."""
import json
from pathlib import Path
import sys
import design73
import kit73
import audit72

def audit(folder):
    a=audit72.a
    baseline=design73.prior.prev.OUT/'print-mechanisms'/'r70-base-reference.json'
    reference=json.loads(baseline.read_text())
    a.a61.audit(folder,kit73.parts,design73.OUT,expected_names=kit73.previous.previous.COMPLETE,
                route_builder=audit72.routes,spring_probe=audit72.spring_opening,
                base_minima=dict(a.a61.MINIMA),expected_fin_count=5,seam_layers=25,
                seam_reference_area_mm2=reference['reference_area_mm2'])
    # The correction is under the lower-left key. None of the five existing
    # breakaway fins touches this fork; keep the recorded removal order accurate.
    path=folder/'fin-design.json'
    fins=json.loads(path.read_text())
    fins['removal']=json.loads((design73.prior.OUT/'print-mechanisms'/path.name).read_text())['removal']
    path.write_text(json.dumps(fins,indent=2)+'\n')

if __name__=='__main__':
    audit(Path(sys.argv[1]))
