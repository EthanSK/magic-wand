"""Audit the changed carrier and every actual normal-object extrusion in its native plate."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
import trimesh
from holder46 import BASE,mesh,union
import audit45
from plate45 import digest
from audit45 import supplemental_coverage
import manifold3d as mf

parent_material=audit45.evaluate_material

def transverse_sections(shape,stations,frame,xyz,width,height,top,checker):
    matrix=np.linalg.inv(frame)
    line=trimesh.transform_points(np.asarray(stations),matrix)
    length=np.linalg.norm(np.diff(line,axis=0),axis=1)
    cumulative=np.r_[0.,np.cumsum(length)]
    queries=[]
    for fraction in (.25,.5,.75):
        d=fraction*cumulative[-1];i=np.searchsorted(cumulative[1:],d)
        direction=(line[i+1]-line[i])/length[i]
        point=line[i]+(d-cumulative[i])*direction
        pose=trimesh.geometry.align_vectors(direction,[0.,0.,1.]);pose[:3,3]=-pose[:3,:3]@point
        target=shape.transform(pose[:3]).slice(0.)
        queries.append((fraction,pose,target,[]))
    x,y,z,X,Y,Z=shape.bounding_box()
    near=(xyz[:,0]>x-.7)&(xyz[:,0]<X+.7)&(xyz[:,1]>y-.7)&(xyz[:,1]<Y+.7)
    for level in np.unique(top[near]):
        if level<=z or level-.22>=Z:continue
        m=near&(abs(top-level)<.001)
        h=round(float(height[m][0]),3);upper=round(float(level),3)
        assert h==.2 and abs(upper/.2-round(upper/.2))<1e-6
        film=checker.start_audit.bead_footprints(checker.q,xyz[m,:2],width[m])
        deposited=film.extrude(h).translate((0,0,upper-h))^shape
        for _,pose,_,pieces in queries:pieces.append(deposited.transform(pose[:3]).slice(0.))
    rows=[]
    for fraction,pose,target,parts in queries:
        deposited=mf.CrossSection.batch_boolean(parts,mf.OpType.Add)
        largest=max((v.area() for v in deposited.decompose()),default=0.)
        rows.append({'fraction_of_path':fraction,'cad_area_mm2':target.area(),'native_largest_connected_mm2':largest,
                     'native_total_mm2':deposited.area(),'coverage':deposited.area()/target.area()})
    return rows

def evaluate(result,out,frame,old44,actual,legacy_targets,xyz,carrier,data,engine,checker,hard,interference,removable):
    fields=(xyz[carrier],data[carrier,3],data[carrier,4],data[carrier,7])
    recipe=json.loads((out/'r46-braces.json').read_text())
    old45=mesh(BASE/'R45-Key-Carrier-assembly.stl').transform(np.linalg.inv(frame)[:3])
    additions=mesh(out/'R46-added-braces.stl')
    expected=old45+additions
    difference={'expected_missing_mm3':max(0.,(expected-actual).volume()),
                'unexpected_material_mm3':max(0.,(actual-expected).volume()),
                'lost_original_carrier_mm3':max(0.,(old45-actual).volume())}
    print('R46 native CAD difference',difference,flush=True)
    assert sum((difference['expected_missing_mm3'],difference['unexpected_material_mm3']))<.025,difference
    # Keep the R45 base construction comparison in its own R44 reference
    # frame. ALL inherited material coverage uses actual R46 carrier beads.
    parent_material(result,out,frame,old44,old45,legacy_targets,xyz,carrier,data,engine,checker,hard,interference,removable)
    results={}
    for name,row in recipe['records'].items():
        targets={'whole member':row['witness'],**row['joint_witnesses']}
        report={}
        for k,t in targets.items():
            assert digest(out/t['file'])==t['sha256']
            shape=mesh(out/t['file'])
            report[k]=engine.material_coverage(checker.q,checker.start_audit,shape,*fields)
            report[k]['cad_volume_mm3']=t['volume_mm3']
            if k=='whole member':report['cross_sections']=transverse_sections(shape,row['stations'],frame,*fields,checker)
        results[name]=report
    result['r46_braces']={'native_geometry':difference,'members':results,'net_added_volume_mm3':recipe['added_mm3'],
        'after_cleanup_cad_intrusions_mm3':recipe['route_max_added_intrusion_mm3']}
    member_gate=all(r['minimum_layer_fraction']>=.9 for v in results.values() for k,r in v.items() if k!='cross_sections')
    section_gate=all(s['coverage']>=.9 and s['native_largest_connected_mm2']>=np.pi*.95**2 for v in results.values() for s in v['cross_sections'])
    result['r46_braces']['individual_member_and_joint_gate']=member_gate
    result['r46_braces']['transverse_section_gate']=section_gate
    result['screen_passed']=bool(result['screen_passed'] and member_gate and section_gate)

def check(archive):
    with patch.object(audit45,'evaluate_material',evaluate):audit45.check(archive)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);check(p.parse_args().archive)
