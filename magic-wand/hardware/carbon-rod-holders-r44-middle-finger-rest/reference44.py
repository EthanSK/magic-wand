"""Derive the rod/OP1 scale check and end-on diagram from the current CAD.

Ethan's 'metal poky bits' in this view are the three OP1 socket barrels.
Model consistency is distinct from measuring the bought connector/PCB.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh


def hull2d(points):
    points=sorted(set(map(tuple,points)))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return np.asarray(lower[:-1]+upper[:-1])


def nearest_radial(part,radius):
    points=hull2d(np.asarray(part.to_mesh().vert_properties)[:,[0,2]])
    candidates=[]
    for a,b in zip(points,np.roll(points,-1,axis=0)):
        v=b-a;t=np.clip(-np.dot(a,v)/np.dot(v,v),0.,1.)
        p=a+t*v;candidates.append((float(np.linalg.norm(p)),p))
    distance,p=min(candidates,key=lambda row:row[0])
    return {'end_on_gap_mm':distance-radius,'nearest_part_xz_mm':p.tolist(),
            'nearest_rod_xz_mm':(p*radius/distance).tolist()}


def generate(design,output):
    rod=design.base.rod();bounds=np.asarray(rod.bounding_box());radius=(bounds[3]-bounds[0])/2
    assert abs(radius-4.)<1e-6 and abs(bounds[5]-bounds[2]-8.)<1e-6
    parts=design.hardware();guide=json.loads((output/'assembly-guide.json').read_text())
    module=guide['modules']['dfr'];pose=module['steps'][-1]['samples'][-1]
    checks={}
    for name in ('rod','sockets','plug','housing'):
        actor=module['actors'][name];path=(output/actor['file']).resolve()
        mesh=trimesh.load_mesh(path);matrix=np.eye(4);matrix[:3]=np.asarray(pose[name]).reshape(3,4)
        scale=np.linalg.svd(matrix[:3,:3])[1]
        assert np.allclose(scale,1.,atol=1e-7)
        points=trimesh.transform_points(mesh.vertices,matrix)
        actual=np.concatenate((points.min(0),points.max(0)))
        row={'file':actor['file'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
             'actor_scale':scale.tolist(),'assembled_bounds_mm':actual.tolist()}
        if name=='rod':
            assert np.allclose(actual[[0,2,3,5]],[-4.,-4.,4.,4.],atol=1e-5)
        else:
            shape=parts[name];expected=np.asarray(shape.bounding_box())
            assert np.allclose(actual,expected,atol=2e-5)
            row.update(source_bounds_mm=expected.tolist(),minimum_3d_gap_mm=float(shape.min_gap(rod,10.)),
                components=[{'bounds_mm':list(p.bounding_box()),'minimum_3d_gap_mm':float(p.min_gap(rod,10.)),
                             **nearest_radial(p,radius)} for p in shape.decompose()])
        checks[name]=row
    result={'units':'mm','viewer_scale_matches_source':True,'rod_diameter_mm':2*radius,
        'op1_yaw_degrees':design.OP1_YAW,'hardware_dimensions_measured':False,
        'dimension_provenance':'OP1 PCB and connector are photo-derived envelopes from the bought kit, not a dimensioned manufacturer drawing.',
        'parts':checks,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output/'reference-check.json').write_text(json.dumps(result,indent=2)+'\n')
    diagram(result,output/'reference-clearance.png')
    return result


def diagram(result,target):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Rectangle
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(10,4.3),layout='constrained')
    tube=min(result['parts']['sockets']['components'],key=lambda p:p['minimum_3d_gap_mm'])
    plug=result['parts']['plug']['components'][0]
    for ax,part,color,label in zip(axes,(tube,plug),('#c6a956','#bdd9de'),('Closest metal tube','Plug below the white socket')):
        ax.add_patch(Circle((0,0),4,color='#505966'))
        if part is plug:
            h=result['parts']['housing']['components'][0]['bounds_mm']
            ax.add_patch(Rectangle((h[0],h[2]),h[3]-h[0],h[5]-h[2],facecolor='#f0eee6',edgecolor='#788087'))
            ax.text(6.1,7.7,'Fixed white socket',ha='center',fontsize=8)
        b=part['bounds_mm'];ax.add_patch(Rectangle((b[0],b[2]),b[3]-b[0],b[5]-b[2],facecolor=color,edgecolor='#263743'))
        p=np.asarray(part['nearest_part_xz_mm']);q=np.asarray(part['nearest_rod_xz_mm'])
        ax.plot([q[0],p[0]],[q[1],p[1]],color='#d65128',linewidth=2)
        ax.scatter(*p,s=16,color='#d65128')
        ax.annotate(f"{part['minimum_3d_gap_mm']:.2f} mm gap",xy=(p+q)/2,xytext=(-4.5,7.8),
                    arrowprops={'arrowstyle':'->','color':'#d65128'},color='#ad3e1d')
        ax.text(0,-.2,'8 mm rod',color='white',ha='center')
        ax.set(title=label,xlabel='Across the rod (mm)',ylabel='Above rod centre (mm)',xlim=(-5,11),ylim=(-5,10))
        ax.set_aspect('equal');ax.grid(alpha=.12)
    fig.suptitle('Looking along the rod: model dimensions, not measured hardware',fontsize=12)
    fig.savefig(target,dpi=150,metadata={'Software':'Magic Wand reference44.py'});plt.close(fig)
