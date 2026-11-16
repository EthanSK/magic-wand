"""Fast native preflight using the same actual-bead starts audit as audit45."""
import argparse,json
from pathlib import Path
import numpy as np
from holder45 import inherited
from plate45 import digest
import single44

def check(archive):
    info=json.loads((archive.parent/'frame.json').read_text())
    owner=single44.previous.owners(archive)
    checker=inherited.common.load_checker().audit
    data,features,_,_,offset,objects,_,_=checker.read_project(archive)
    obj=objects['Key_Carrier']
    solid=checker.q.solid(obj['vertices']-info['bed_translation'],obj['faces'])
    xyz=data[:,:3]+offset-info['bed_translation']
    kinds=data[:,5].astype(int);labels=np.array(features)[kinds]
    helper=np.isin(data[:,6],[owner[n] for n in ('External_cradle','Front_pull_shelf','Rear_pull_shelf') if n in owner])&inherited.common.model_mask(labels)
    kinds[helper]=len(features)
    include=(labels!='Prime tower')&(data[:,6]!=owner['Release_tabs'])
    result=checker.start_audit.inspect(checker.q,solid,xyz[include],data[include,4],kinds[include],
        list(features)+['Support: external cradle'],data[include,7],np.array(info['print_to_assembly']),data[include,3],gap=.2)
    report={'archive_sha256':digest(archive),'layer_starts':result}
    (archive.parent/'starts-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
    print('floating actual components:',result['floating_components'],'missing:',result['missing_printed_components'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);check(p.parse_args().archive)
