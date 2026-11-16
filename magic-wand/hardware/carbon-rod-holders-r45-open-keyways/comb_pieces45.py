"""Check the order for releasing each disconnected finger-side print aid."""
from pathlib import Path
import numpy as np
import manifold3d as mf
import trimesh
from shelf45 import span,band
from plate45 import digest

def cad_conflicts(moving,fixed):
    heights=np.unique(np.round(np.asarray(moving.to_mesh().vert_properties)[:,2],5))
    collisions=[]
    for lo,hi in zip(heights[:-1],heights[1:]):
        if hi-lo<.00005:continue
        section=moving.slice(float((lo+hi)/2))
        swept=span(section,0,-72.)
        area=(swept^band(fixed,float(lo)-.00001,float(hi)+.00001)).area()
        if area>.0001:collisions.append([float(lo),float(hi),area])
    return collisions

def record(out,shape,report):
    solids=sorted(shape.decompose(),key=lambda s:-s.volume())
    assert 1<=len(solids)<=2
    names=['Finger-side comb','Left guard web prop'];files=['R45-finger-side-comb.stl','R45-left-guard-web-prop.stl']
    records=[]
    for name,file,piece in zip(names,files,solids):
        mesh=piece.to_mesh();trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False).export(out/file)
        records.append(dict(name=name,file=file,sha256=digest(out/file),direction_print=[0,-1,0],translation_mm=72.,
            bounds=piece.bounding_box(),volume_mm3=piece.volume(),bed_face_area_mm2=piece.slice(.1).area(),
            has_1p2mm_grip_land=not piece.slice(.1).offset(-.6).is_empty()))
    order=list(range(len(solids)))
    if len(solids)==2 and cad_conflicts(solids[0],solids[1]):
        assert not cad_conflicts(solids[1],solids[0]),'Neither front helper can withdraw with its neighbour present'
        order.reverse()
    for rank,index in enumerate(order):
        records[index].update(removal_order=rank+1,other_front_pieces_remaining=[names[i] for i in order[rank+1:]],
                              whole_cad_conflicts_with_remaining_front_pieces=[])
    report['removable_pieces']=[records[i] for i in order]
    report['piece_checker_sha256']=digest(Path(__file__))

def actual(out,checker,d,xyz,helper,other,report):
    from lateral45 import inspect
    records=report['removable_pieces'];parts=[]
    assert report['piece_checker_sha256']==digest(Path(__file__))
    for item in records:
        assert digest(out/item['file'])==item['sha256']
        mesh=trimesh.load_mesh(out/item['file']);parts.append(checker.q.solid(mesh.vertices,mesh.faces))
    which=np.full(len(d),-1,int)
    for z in np.unique(d[helper,7]):
        indices=np.flatnonzero(helper&(abs(d[:,7]-z)<.001))
        sections=[p.slice(z-float(d[indices[0],4])/2) for p in parts]
        for radius in (0.,.04,.10,.20,.34,.50):
            if not len(indices):break
            inside=np.array([checker.q._inside(p.offset(radius) if radius else p,xyz[indices,:2]) for p in sections])
            unique=inside.sum(axis=0)==1
            which[indices[unique]]=inside[:,unique].argmax(axis=0)
            # Ambiguous and unassigned samples remain explicitly unresolved.
            indices=indices[~unique]
    unknown=int((helper&(which<0)).sum())
    rows=[]
    for i,record in enumerate(records):
        selected=helper&(which==i)
        release=inspect(checker,d,xyz,other|(helper&(which>i)),selected,'-y')
        foot=selected&(abs(d[:,7]-.2)<.001)
        base=checker.start_audit.bead_footprints(checker.q,xyz[foot,:2],d[foot,3])
        rows.append(dict(name=record['name'],file=record['file'],sample_points=int(selected.sum()),
            actual_first_layer_area_mm2=base.area(),actual_1p2mm_land=not base.offset(-.6).is_empty(),
            actual_bead_withdrawal=release))
    return dict(clear=not unknown and all(r['actual_bead_withdrawal']['clear'] for r in rows),
                unassigned_or_ambiguous_samples=unknown,pieces=rows)

def flare(shape,body,tabs,cradle):
    """Flare the tall web prop at the bed, reusing disposable tab space."""
    solids=sorted(shape.decompose(),key=lambda p:-p.volume())
    if len(solids)==1:
        return shape,tabs,{'separate_web_prop_required':False}
    front,web=solids
    foot=web.slice(.1)
    # The large comb exits first. Keep its complete -Y sweep open.
    # The standing web prop then exits -Y past the permanent carrier.
    fixed=span(band(body,-.001,.81).offset(.44),0,72.)
    fixed+=cradle.project().offset(.70)
    fixed+=span(band(front,-.001,.81).offset(.70),0,-72.)
    free=foot.offset(4.25)-fixed
    pad=mf.CrossSection.batch_boolean([v for v in free.decompose() if (v^foot).area()>.015],mf.OpType.Add)
    assert pad.area()>14.,pad.area()
    release=span(pad.offset(.70),0,-72.).extrude(.41)
    retained=tabs-release
    motion=span(pad,0,-72.)
    collisions=(motion^band(body+retained,-.00001,.40001)).area()
    assert collisions<.0001,collisions
    result=front+web+pad.extrude(.40)
    return result,retained,dict(original_prop_cad_foot_mm2=foot.area(),flared_cad_foot_mm2=(pad+foot).area(),
        removed_tab_mm3=(tabs-retained).volume(),full_pad_sweep_intersection_mm2=collisions,base_layers=2)
