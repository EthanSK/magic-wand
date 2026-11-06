#!/usr/bin/env python3
"""Render every audited broad-overhang layer using actual project placement."""
import argparse,json,zipfile,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np,trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cad
import deliverables
from verify_slice import q,N


def render(out):
    project=out/deliverables.project_name(out);manifest=json.loads((out/'manifest.json').read_text())
    audit=json.loads((out/'slice-clearances.json').read_text())
    assert audit['project_sha256']==cad.sha(project)
    images={}
    with zipfile.ZipFile(project)as z:
        data,features,_=q.extrusion_points(z.read('Metadata/plate_1.gcode').decode(),.15)
        cfg=E.fromstring(z.read('Metadata/model_settings.config'));model=E.fromstring(z.read('3D/3dmodel.model'))
        cache={'3D/3dmodel.model':model};roots={o.get('id'):o for o in model.findall('m:resources/m:object',N)}
        builds={i.get('objectid'):q.transform(i.get('transform'))for i in model.findall('m:build/m:item',N)}
        settings=json.loads(z.read('Metadata/project_settings.config'))
        offset=np.array([float(x)for x in settings['extruder_offset'][0].split('x')]+[0])
        for obj in cfg.findall('object'):
            name=q.metadata(obj)['name'];record=manifest['parts'][name]
            part=next(p for p in obj.findall('part')if q.metadata(p).get('name')==name)
            comp=next(c for c in roots[obj.get('id')].findall('m:components/m:component',N)if c.get('objectid')==part.get('id'))
            source=next((v.lstrip('/')for k,v in comp.attrib.items()if k.endswith('}path')),'3D/3dmodel.model')
            if source not in cache:cache[source]=E.fromstring(z.read(source))
            child=next(o for o in cache[source].findall('m:resources/m:object',N)if o.get('id')==part.get('id'))
            vv=np.array([[float(v.get(k))for k in 'xyz']for v in child.findall('m:mesh/m:vertices/m:vertex',N)])
            vv=q.points(q.points(vv,q.transform(comp.get('transform'))),builds[obj.get('id')])
            mm=trimesh.load_mesh(out/deliverables.normal_name(name));place=(vv.min(0)+vv.max(0)-mm.bounds.sum(0))/2
            assert np.max(abs(np.array([vv.min(0),vv.max(0)])-place-mm.bounds))<.025
            xyz=data[:,:3]+offset-place;normal=q.solid(mm.vertices,mm.faces)
            helper_path=out/(name+'-PRINT-HELPER-assembly.stl');hs=None
            if helper_path.exists():
                hm=trimesh.load_mesh(helper_path);hm.apply_transform(np.linalg.inv(np.array(record['print_to_assembly'])))
                hs=q.solid(hm.vertices,hm.faces)
            rows=audit['parts'][name]
            levels=sorted({r['layer_top_mm']for scope in ['layer_starts','whole_print_layer_starts']for r in rows[scope]['partial_overhangs']})
            levels=sorted(set([.2]+levels))
            if len(levels)==1:levels += [.6,1.6]
            count=int(np.ceil(len(levels)/3));fig,axes=plt.subplots(count,3,figsize=(15,3.4*count),squeeze=False)
            fig.suptitle(name+' | every broad-overhang layer; actual project coordinates')
            for ax,top in zip(axes.flat,levels):
                prior=abs(data[:,7]-(top-.2))<.001
                ax.scatter(xyz[prior,0],xyz[prior,1],s=.8,c='#8a5cb7')
                ids=abs(data[:,7]-top)<.001;ax.scatter(xyz[ids,0],xyz[ids,1],s=.7,c='#007aa5')
                solids=[(normal,top-.1,'black'),(normal,top-.3,'#999999')]
                if hs is not None:solids.append((hs,top-.5,'#f28b25'))
                for solid,level,colour in solids:
                    for poly in solid.slice(level).to_polygons():
                        pp=np.array(poly);pp=np.vstack([pp,pp[:1]]);ax.plot(pp[:,0],pp[:,1],c=colour,lw=.65,ls='--'if colour=='#999999'else'-')
                lo,hi=mm.bounds;ax.set(xlim=(lo[0]-1,hi[0]+1),ylim=(lo[1]-3,hi[1]+2))
                ax.set_aspect('equal');ax.set_title(f'Layer top {top:g} mm');ax.grid(alpha=.2)
            for ax in list(axes.flat)[len(levels):]:ax.set_visible(False)
            fig.text(.5,.005,'Blue: current paths. Purple: previous actual paths. Black: current mesh. Gray dashed: previous mesh, not backing. Orange: helper one empty layer below. Physical result unverified.',ha='center',fontsize=9)
            fig.tight_layout(rect=[0,.015,1,.97]);target=out/(name+'-overhang-views.png');fig.savefig(target,dpi=130);plt.close(fig)
            images[target.name]=cad.sha(target)
    report={'generator_sha256':cad.sha(Path(__file__)),'project_sha256':cad.sha(project),
            'slice_audit_sha256':cad.sha(out/'slice-clearances.json'),'images_sha256':images,
            'physical_print_verified':False}
    (out/'view-checks.json').write_text(json.dumps(report,indent=2)+'\n');print('Every reported broad-overhang layer rendered from the actual prepared project.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--exports',type=Path,default=cad.HERE/'exports');a=p.parse_args();render(a.exports.resolve())
