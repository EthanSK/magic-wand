"""Check release of both upper leaves against permanent paths nearby."""
import json
from pathlib import Path
import sys
import numpy as np
import manifold3d as mf
from plate52 import HERE
from sockets52 import paths
from printed_props51 import native_mask
from removal51 import unpack
from orient51 import digest
from clearance51 import patches
import build52 as cad


def check(out):
    patches()
    archive=out/'Mechanisms.gcode.3mf'
    data,features,ids,normal=unpack(archive)
    prop,_=native_mask(archive,paths,data,ids['Key_Carrier'],normal)
    frame=np.array(json.loads((out/'layout.frame.json').read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    rows=[]
    for y,side in zip(cad.h.h32.EYELETS,(1,-1)):
        root,spine,nose=cad.arm_features(y,side)
        base=cad.q.board_frame(spine+nose).transform(frame[:3])
        anchor=cad.q.board_frame(root).transform(frame[:3])
        poses=[]
        for lift in np.linspace(0,cad.RELEASE,13):
            _,spine,nose=cad.arm_features(y,side,lift)
            poses.append(cad.q.board_frame(spine+nose).transform(frame[:3]))
        span=cad.union(poses)
        b=np.array(span.bounding_box())
        selected=(((data[:,:3]>b[:3]-1)&(data[:,:3]<b[3:]+1)).all(1))
        d=data[selected];other=~prop[selected]&np.isin(d[:,5],normal)&(d[:,6]==ids['Key_Carrier'])
        # Rest-leaf bead paths belong to the moving leaf. The first 0.30 mm
        # of its root is part of the flexible bend, not a fixed obstruction.
        own=np.zeros(len(d),bool)
        for z in np.unique(d[:,7]):
            i=np.flatnonzero(d[:,7]==z)
            s=(base+anchor).slice(float(z-.10)).offset(.24)
            own[i]=paths._inside(s,d[i,:2])
        fixed=d[other&~own]
        result=paths.inspect_region(span,fixed[:,:3],fixed[:,3],fixed[:,4],fixed[:,5].astype(int),features,np.linalg.inv(frame))
        rows.append(dict(eyelet_board_y_mm=float(y),travel_mm=cad.RELEASE,poses=len(poses),classified_moving_and_root_samples=int((own&other).sum()),
                         fixed_material_in_lift=result))
    report=dict(archive_sha256=digest(archive),leaves=rows,physical_release_tested=False)
    (out/'spring-paths.json').write_text(json.dumps(report,indent=2)+'\n')
    print([(r['eyelet_board_y_mm'],r['fixed_material_in_lift']['violations']) for r in rows],flush=True)


if __name__=='__main__':check(Path(sys.argv[1]))
