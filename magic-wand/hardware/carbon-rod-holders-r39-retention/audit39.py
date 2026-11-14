"""Run canonical deposited-path checks against R39 sources and its new slice."""
from pathlib import Path
import argparse,json
from unittest.mock import patch
import holder39 as d
import plate39
import audit38


def audit(archive,scratch):
    d.install_checks()
    audit38.design=d
    audit38.preparation=plate39
    old_regions=d.BATTERY.h18.regions
    def regions(name):
        if name!='Battery_End_Door':return old_regions(name)
        params=d.DOOR
        return {'tongue_slit':d.box(params['tongue_root_x_mm']+.05,params['window_x_mm'][0]-.05,
            params['y_mm'][0]-1,params['y_mm'][1]+1,params['tongue_z_mm'][1]+.05,
            params['tongue_z_mm'][1]+params['slit_mm']-.05)}
    original_read=audit38.read_json
    def read_bound(path):
        result=original_read(path)
        if Path(path).resolve()==(d.HERE/'exports/manifest.json').resolve():
            # Supply the inherited check's old key from this revision's real
            # hash without modifying either stored manifest or archived code.
            result['source_sha256']['holder38.py']=result['source_sha256']['holder39.py']
        return result
    with patch.object(audit38,'read_json',side_effect=read_bound), patch.object(d.BATTERY.h18,'regions',side_effect=regions):
        result=audit38.audit(archive,scratch)
    result['r39_deposition_checks']=result.pop('r38_deposition_checks')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('scratch',type=Path);p.add_argument('report',type=Path)
    args=p.parse_args();result=audit(args.archive,args.scratch)
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'failures':result['failures']}))
    raise SystemExit(0 if result['passed'] else 1)
