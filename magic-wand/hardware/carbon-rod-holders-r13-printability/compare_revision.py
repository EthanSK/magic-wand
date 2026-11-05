#!/usr/bin/env python3
"""Compare final assembly STLs with the preserved R12 assembly STLs."""
import json
from pathlib import Path
import trimesh
import cad
from verify_slice import q

if __name__=='__main__':
    out=cad.HERE/'exports';previous=cad.base.HERE/'exports';manifest=json.loads((out/'manifest.json').read_text());parts={}
    for name in manifest['parts']:
        new=out/(name+'-assembly.stl');old=previous/(name+'-assembly.stl')
        a=trimesh.load_mesh(new);b=trimesh.load_mesh(old);current=q.solid(a.vertices,a.faces);before=q.solid(b.vertices,b.faces)
        parts[name]={'added_mm3':round(abs((current-before).volume()),5),
                     'removed_mm3':round(abs((before-current).volume()),5),
                     'r13_sha256':cad.sha(new),'r12_sha256':cad.sha(old)}
    report={'generator_sha256':cad.sha(Path(__file__)),'manifest_sha256':cad.sha(out/'manifest.json'),
            'previous_manifest_sha256':cad.sha(previous/'manifest.json'),'parts':parts,
            'method':'Boolean volumes between final exported assembly STLs; numerical surface differences are not physical measurements.'}
    (out/'design-differences.json').write_text(json.dumps(report,indent=2)+'\n');print(parts)
