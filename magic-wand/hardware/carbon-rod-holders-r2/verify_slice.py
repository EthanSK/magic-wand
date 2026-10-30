#!/usr/bin/env python3
"""R1 prepared-mesh/bead audit plus the entire nominal wire sweep."""
import json,zipfile
from pathlib import Path
import numpy as np
import cad
HERE=cad.HERE;OUT=HERE/'exports'
if __name__=='__main__':
    m=cad.load('verify_slice');m.HERE=HERE;m.OUT=OUT;m.inspect()
    q=m.q;project=OUT/'Holder-pair-sliced.3mf'
    manifest=json.loads((OUT/'manifest.json').read_text())
    # Existing parser resolves prepared normal objects and their plate placement.
    entries=[dict(name=n,file=n+'.stl',sha256=r['stl_sha256'],**r)for n,r in manifest['parts'].items()]
    with zipfile.ZipFile(project)as z:
        objects,offset,config=q.objects(z,{'parts':entries},OUT/'manifest.json')
        data,features,stats=q.extrusion_points(z.read('Metadata/plate_1.gcode').decode(),.3)
    result={}
    for obj in objects:
        if obj['name']!='XIAO_Rod_Holder':continue
        xyz=data[:,:3]+offset-obj['build'][:3,3]
        bb=obj['print_bbox'];mask=np.all(xyz>=bb[0]-[8,8,.4],axis=1)&np.all(xyz<=bb[1]+[8,8,.4],axis=1)
        pa=obj['print_to_assembly'];pr=np.linalg.inv(pa);s=cad.P['sensor']
        regions={'entire_nominal_wire_route':cad.wire_route(),'reversed_usb_plug_approach':cad.box(-5.2,5.2,-22.7,-.7,s['board_z']+.9,s['board_z']+4.4)}
        result={n:q.inspect_region(region.transform(pr[:3,:]),xyz[mask],data[mask,3],data[mask,4],data[mask,5].astype(int),features,pa)for n,region in regions.items()}
    assert result,'Missing tip in prepared print project'
    report=json.loads((OUT/'slice-clearances.json').read_text())
    report['r2_checker_sha256']=cad.sha(Path(__file__))
    report['r2_extra_regions']=result
    report['passed']=report['passed'] and all(not c['violations']for c in result.values())
    (OUT/'slice-clearances.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['passed'],result
    print('Reversed USB approach and entire nominal wire route:',{n:c['violations']for n,c in result.items()})
