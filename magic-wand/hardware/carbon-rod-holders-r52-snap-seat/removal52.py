"""Check external support release on the final holder and draw its cleanup map."""
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
import manifold3d as mf
import trimesh
from plate52 import HERE, PREVIOUS, shoulder_tab, adhesion_ears
from removal51 import unpack, exact_pulls, openings
from props51 import route_parts
from orient51 import digest,load_solid
import build52 as cad
from clearance51 import patches


def check(out, models=None):
    models=Path(models) if models else HERE/'exports'
    patches()
    archive=out/'Mechanisms.gcode.3mf'
    record=json.loads((out/'layout.frame.json').read_text())['parts']
    rows=json.loads((PREVIOUS/'exports/print-trial/external-prop-paths.json').read_text())
    frame=np.array(record['Key_Carrier']['assembly_to_machine'])
    for part in record.values():
        assert digest(models/part['assembly_stl'])==part['source_sha256']
    body=load_solid(models/'Key_Carrier-assembly.stl').transform(frame[:3])
    rows=[r for r in rows if not r['found'] or r['layer']!=199]
    props=[]
    with tempfile.TemporaryDirectory() as tmp:
        for row in rows:
            if not row['found']:continue
            top=np.r_[row['xy'],row['layer']*.2-.6]
            blocks=route_parts(np.array(row['foot_xy']),top,row['rise_mm'])
            shape=mf.Manifold.batch_boolean(blocks,mf.OpType.Add)
            mesh=shape.to_mesh()
            trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False).export(Path(tmp)/f'prop-{len(props)}.stl')
            props.append(shape)
        steps,blocked=exact_pulls(body,Path(tmp),rows,np.zeros(2))
    small=shoulder_tab()
    direction=np.array([-1.,1.,0])/np.sqrt(2)
    swept=mf.Manifold.batch_hull([small,small.translate(90*direction)])
    tab_contact=(small^body).volume()
    tab_pull=(swept^body).volume()
    props_contact=[(swept^p).volume() for p in props]
    data,features,ids,_=unpack(archive)
    holes={}
    for n,row in record.items():
        actual=load_solid(models/row['assembly_stl']).transform(np.array(row['assembly_to_machine'])[:3])
        coarse=openings(actual,data,features,ids[n],row['assembly_to_machine'],np.zeros(2),grid=.4)
        fine=openings(actual,data,features,ids[n],row['assembly_to_machine'],np.zeros(2),grid=.2)
        holes[n]={'coarse':coarse,'fine':fine}
        if n == 'DFRobot_Hole_Bracket' and fine['unreachable_sample_count']:
            # Resolve the tight exterior curve at the paddle post. Keep both
            # earlier grids; the physical fragment still has a 0.4 mm radius.
            holes[n]['intermediate'] = fine
            holes[n]['fine'] = openings(actual,data,features,ids[n],row['assembly_to_machine'],np.zeros(2),grid=.1)
    ears=adhesion_ears(body,frame[:2,3])
    foot=body.slice(.10)
    ear_section=ears.slice(.10)
    ear_native=data[(data[:,6]==ids['Key_Carrier'])&(data[:,7]<.201)&np.isin(data[:,5],_)]
    from support51 import q
    accepted=q._inside(ear_section,ear_native[:,:2])
    adhesion=dict(external_ear_area_mm2=ear_section.area(),first_layer_samples_on_ear=int(accepted.sum()),carrier_CAD_footprint_mm2=foot.area(),native_ear_min_radius_to_rod_mm=float(np.min(np.linalg.norm(ear_native[accepted,:2]-frame[:2,3],axis=1)-ear_native[accepted,3]/2)))
    result=dict(adhesion=adhesion,archive_sha256=digest(archive),long_props=len(props),pull_order=steps,blocked=blocked,
                fixed_shoulder_tab={'root_tie_mm3':tab_contact,'pull_sweep_total_mm3':tab_pull,'pull_xy':direction[:2].tolist(),
                                    'collision_with_other_props_mm3':max(props_contact)},native_support_openings=holes,
                physical_cleanup_tested=False)
    from arm_fixture52 import carrier_fixture
    fixture,ties,fixture_pull=carrier_fixture(frame,with_sweep=True)
    result['spring_fixture']=dict(snip_locations=10,
        withdrawal_machine_xyz_mm=[0,60,0],carrier_overlap_after_cut_mm3=round((fixture_pull^body).volume(),7),
        other_prop_overlap_during_pull_mm3=round(max((fixture_pull^p).volume() for p in [*props,small]),7))
    (out/'removal.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Long props',len(steps),blocked,'Root starter',tab_contact,tab_pull,'openings',[(n,r['fine']['unreachable_sample_count'],r['fine']['samples']) for n,r in holes.items()],flush=True)
    draw(out,body,props+[ears],small,data,features,frame,steps,rows,fixture,ties)
    draw_paddle(out,record['DFRobot_Hole_Bracket'],data,features,models)


def draw(out,body,props,small,data,features,frame,steps,rows,fixture,ties):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
    leaves=[]
    for y,side in zip(cad.h.h32.EYELETS,(1,-1)):
        _,spine,nose=cad.arm_features(y,side)
        leaves.append(cad.q.board_frame(spine+nose).transform(frame[:3]))
    for ax,(i,j),title in zip(axes,[(0,2),(0,1)],['Looking at the front of the plate','Looking down at the plate']):
        def meshplot(s,color,alpha=1):
            m=s.to_mesh();v=m.vert_properties[:,:3]
            ax.triplot(v[:,i],v[:,j],m.tri_verts,color=color,lw=.09,alpha=alpha,rasterized=True)
        meshplot(body,'#a1a1a1',.27)
        support=data[np.isin(data[:,5],np.flatnonzero(np.char.startswith(features,'Support')))]
        support=support[(support[:,0]<88)&(support[:,0]>15)]
        ax.scatter(support[::9,i],support[::9,j],s=.13,color='#cd8b12',alpha=.4,rasterized=True)
        for p in props:meshplot(p,'#dc6416',.7)
        meshplot(small,'#af2c0c')
        meshplot(fixture,'#873fb1',.65)
        for contact in ties.decompose():
            bounds=np.array(contact.bounding_box())
            centre=(bounds[:3]+bounds[3:])/2
            ax.plot(centre[i],centre[j],marker='x',ms=3,ls='none',color='#442353')
        if j==1:
            ax.annotate('Snip ties, then pull',xy=(59,106),xytext=(40,112),fontsize=7,
                arrowprops=dict(arrowstyle='->',color='#873fb1'),color='#582174')
        for leaf in leaves:meshplot(leaf,'#086b85')
        ax.annotate('Short tab',xy=(62.4,29.2 if j==2 else 92.49),xytext=(66,36 if j==2 else 98),fontsize=8,
                    arrowprops=dict(arrowstyle='->',color='#af2c0c'),color='#842000')
        if j==1:
            feet=[r['foot_xy'] for r in rows if r['found']]
            for step in steps:
                x,y=feet[step['prop']];dx,dy=np.array(step['pull_xy'])*4
                ax.annotate('',xy=(x+dx,y+dy),xytext=(x,y),arrowprops=dict(arrowstyle='->',color='#a74409',lw=.9))
        ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('Machine X (mm)');ax.set_ylabel(('Machine Z' if j==2 else 'Machine Y')+' (mm)')
    handles=[Line2D([],[],color=c,lw=4,label=n) for c,n in [('#086b85','Keep both OP1 spring arms'),('#dc6416','Remove outside props and short tab'),('#cd8b12','Peel slicer supports'),('#873fb1','Snip ten ties, remove spring fixture')]]
    fig.legend(handles=handles,loc='outside lower center',ncol=2,fontsize=8)
    fig.savefig(out/'carrier-cleanup.png',dpi=185)
    plt.close(fig)


def draw_paddle(out,row,data,features,models):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    frame=np.array(row['assembly_to_machine'])
    body=load_solid(models/row['assembly_stl']).transform(frame[:3])
    mesh=body.to_mesh();v=mesh.vert_properties[:,:3]
    support=data[np.isin(data[:,5],np.flatnonzero(np.char.startswith(features,'Support')))]
    b=np.array(body.bounding_box())
    support=support[((support[:,:3]>=b[:3]-6)&(support[:,:3]<=b[3:]+6)).all(1)]
    fig,axes=plt.subplots(1,2,figsize=(8,4.5),layout='constrained')
    for ax,(i,j),title in zip(axes,[(0,1),(1,2)],['Looking down the axle','Side of the paddle']):
        ax.triplot(v[:,i],v[:,j],mesh.tri_verts,color='#506d78',lw=.12,alpha=.34,rasterized=True)
        ax.scatter(support[::6,i],support[::6,j],s=.25,color='#dc6416',alpha=.6,rasterized=True)
        ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('Machine '+('X' if i==0 else 'Y')+' (mm)');ax.set_ylabel('Machine '+('Y' if j==1 else 'Z')+' (mm)')
    fig.legend(handles=[Line2D([],[],color='#506d78',lw=4,label='Keep the paddle, posts and rounded dome'),
                        Line2D([],[],color='#dc6416',lw=4,label='Peel the outside support in sections')],loc='outside lower center',ncol=2,fontsize=8)
    fig.savefig(out/'paddle-cleanup.png',dpi=175);plt.close(fig)

if __name__=='__main__':
    check(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else None)
