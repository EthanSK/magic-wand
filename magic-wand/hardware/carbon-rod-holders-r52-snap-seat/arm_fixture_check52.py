"""Measure native functional slits and verify the positive breakaway spring fixture."""
import json
from pathlib import Path
import sys
import numpy as np
import shapely
from arm_fixture52 import carrier_fixture
import build52 as d
from removal51 import unpack
from support51 import GRID,footprint,lost_islands,dilation
from printed_props51 import native_mask
from sockets52 import paths
from orient51 import digest,load_solid


def check(out,carrier_path):
    d.old.configure_new_op1()
    archive=out/'Mechanisms.gcode.3mf'
    fr=np.array(json.loads((out/'layout.frame.json').read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    cad=load_solid(carrier_path).transform(fr[:3])
    fixture,ties,sweep=carrier_fixture(fr,with_sweep=True)
    rows,labels,owners,normal=unpack(archive)
    prop,_=native_mask(archive,paths,rows,owners['Key_Carrier'],normal)
    window=(rows[:,0]>47)&(rows[:,0]<71)&(rows[:,1]>87)&(rows[:,1]<111)
    keep=window&(rows[:,6]==owners['Key_Carrier'])&np.isin(rows[:,5],normal)
    positives=rows[keep]
    fixedrows=rows[keep&~prop]; removable=rows[keep&prop]
    measures=[]
    for y,side in zip(d.h.h32.EYELETS,(1,-1)):
        root,beam,tip=d.arm_features(y,side)
        own=d.q.board_frame(beam+tip+root).transform(fr[:3])
        ry=y+side*d.SPRING_LENGTH
        lo,hi=sorted([ry-side*2.4,y-side*2.2])
        free=d.q.board_frame((beam+tip)^d.box(-25,25,lo,hi,5,19)).transform(fr[:3])
        gaps=[]
        for z in np.unique(fixedrows[:,7]):
            layer=fixedrows[fixedrows[:,7]==z]
            s=free.slice(float(z-.1))
            if s.is_empty():continue
            active=paths._inside(s.offset(.12),layer[:,:2])
            fixed=~paths._inside(own.slice(float(z-.1)).offset(.18),layer[:,:2])
            aa,bb=layer[active],layer[fixed]
            if not (len(aa) and len(bb)):continue
            idx=shapely.STRtree(shapely.points(bb[:,:2])).nearest(shapely.points(aa[:,:2]))
            dist=np.linalg.norm(aa[:,:2]-bb[idx,:2],axis=1)-(aa[:,3]+bb[idx,3])/2
            k=int(dist.argmin())
            gaps.append([round(float(dist[k]),4),round(float(z),3),*[round(float(v),3) for v in [*aa[k,:2],*bb[idx[k],:2]]]])
        measures.append(dict(eyelet_y_mm=y,min_gap_mm_z=min(gaps),root_excluded_mm=2.4))
    # Around each intended contact find actual print material of both kinds.
    contacts=[]
    for tip in ties.decompose():
        b=np.array(tip.bounding_box())
        def nearby(data):
            return data[np.all((data[:,:3]>b[:3]-.42)&(data[:,:3]<b[3:]+.42),axis=1)]
        aa=nearby(fixedrows);bb=nearby(removable)
        contact=[]
        for a in aa:
            same=bb[abs(bb[:,7]-a[7])<.21]
            if len(same):contact.append(float((np.linalg.norm(same[:,:2]-a[:2],axis=1)-(same[:,3]+a[3])/2).min()))
        contacts.append(dict(center_mm=np.round((b[:3]+b[3:])/2,2).tolist(),positive_neck_samples=len(bb),
                             leaf_samples=len(aa),minimum_xy_bead_gap_same_or_adjacent_layer_mm=round(min(contact),3) if contact else None))
    # Positive material alone must root the two nose starts.
    origin=np.array([46.,85.]);shape=(270,270);prev=np.zeros(shape,bool);unbacked=[]
    for n in range(1,226):
        layer=positives[np.abs(positives[:,7]-n*.2)<.001]
        mask=footprint(layer,origin,shape)
        if n>1:
            for island in lost_islands(mask,dilation(prev,1),origin):
                a,b,c,e=island['machine_xy_bounds']
                if a>49 and c<68.5 and b>90.8 and e<108:
                    unbacked.append(dict(layer=n,**island))
        prev=mask
    report=dict(archive_sha256=digest(archive),carrier_sha256=digest(carrier_path),working_arm_slits=measures,
                positive_fixture_contacts=contacts,fixture_contact_volume_mm3=(fixture^cad).volume(),fixture_pull_volume_mm3=(sweep^cad).volume(),fixture_pull_extra_interference_mm3=((sweep-fixture)^cad).volume(),fixture_pull_machine_mm=[0,60,0],bay_islands_without_positive_material_below=unbacked)
    (out/'op1-spring-fixture.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)


if __name__=='__main__':check(Path(sys.argv[1]),Path(sys.argv[2]))
