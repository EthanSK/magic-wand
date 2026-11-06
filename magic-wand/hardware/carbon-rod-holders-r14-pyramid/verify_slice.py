#!/usr/bin/env python3
"""Check final prepared meshes and actual model/support extrusion in openings.

Compose the Shard R2 parser, bead-footprint checker and layer-start audit. Fail
on support, interfaces and brim in functional spaces, not only model material.
Clearance guards are numerical allowances, not manufacturing tolerances.
"""
import argparse,importlib.util,json,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import trimesh
import cad
import deliverables
import start_audit
import side_gap
import working_spaces
HERE=Path(__file__).resolve().parent;OUT=HERE/'exports'
spec=importlib.util.spec_from_file_location('existing_path_auditor',HERE.parent/'printed-loop-wand/shard-tube-r2/check_sliced_paths.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
N={'m':q.NS};tag=lambda s:'{'+q.NS+'}'+s

def views(name, actual, helper_solid, samples, layers):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    tops=np.unique(np.round(layers,4))
    critical={'Key_Carrier':[.2,4.,13.6,34.], 'Battery_Holder':[.2,18.,32.,33.2],
              'XIAO_Rod_Holder':[.2,5.6,6.2,26.2], 'Battery_End_Gate':[.2,.6,1.2,1.6]}[name]
    fig,axes=plt.subplots(2,2,figsize=(10,8));fig.suptitle(name+' | actual sliced beads and STL sections')
    for ax,level in zip(axes.flat,critical):
        top=tops[np.argmin(abs(tops-level))];ids=abs(layers-top)<.001
        ax.scatter(samples[ids,0],samples[ids,1],s=2,color='#007aa5',label='actual extrusion')
        for solid,col,label in [(actual,'black','normal STL'),(helper_solid,'#f28b25','CAD helper')]:
            if solid is None:continue
            for poly in solid.slice(float(top)-.1).to_polygons():
                pp=np.asarray(poly);pp=np.vstack([pp,pp[:1]]);ax.plot(pp[:,0],pp[:,1],color=col,lw=.65,label=label)
        ax.set_aspect('equal');ax.set_title(f'Layer top {top:g} mm');ax.set_xlabel('print X mm');ax.set_ylabel('print Y mm');ax.grid(alpha=.2)
    fig.text(.5,.01,'Numerical audit scans all layers. Physical sag, cleanup and strength remain unverified.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.025,1,.95]);fig.savefig(OUT/(name+'-slice-views.png'),dpi=145);plt.close(fig)

def inspect(option, project=None, exports=None, report_path=None):
    global OUT
    OUT=exports or OUT
    manifest=json.loads((OUT/'manifest.json').read_text())
    project=project or OUT/deliverables.project_name(OUT)
    with zipfile.ZipFile(project)as z:
        assert z.testzip()is None
        cfg=E.fromstring(z.read('Metadata/model_settings.config'))
        model=E.fromstring(z.read('3D/3dmodel.model'));cache={'3D/3dmodel.model':model}
        roots={o.get('id'):o for o in model.findall('m:resources/m:object',N)}
        builds={i.get('objectid'):q.transform(i.get('transform'))for i in model.findall('m:build/m:item',N)}
        config=json.loads(z.read('Metadata/project_settings.config'))
        data,features,stats=q.extrusion_points(z.read('Metadata/plate_1.gcode').decode(),.15)
        off=np.array([float(x)for x in config.get('extruder_offset',['0x0'])[0].split('x')]+[0])
        report={'project_sha256':cad.sha(project),'checker_sha256':cad.sha(Path(__file__)),'parser_sha256':cad.sha(Path(q.__file__)),'start_auditor_sha256':cad.sha(Path(start_audit.__file__)),'side_gap_checker_sha256':cad.sha(Path(side_gap.__file__)),'working_spaces_sha256':cad.sha(Path(working_spaces.__file__)),'manifest_sha256':cad.sha(OUT/'manifest.json'),'parts':{},'path_samples':len(data),'parser_stats':stats,'path_sample_step_mm':.15,'unknowns':['Populated PCB underside and actual wire/solder bends are unmeasured.','PETG helper removal, print stability, fit, strength and fatigue require a physical coupon.'],'physical_fit_verified':False,'support_removal_physically_verified':False,'support_policy':'Model, support, interface, transition and brim beads must clear every functional region. No removable-support exception.','xy_guard_mm':q.XY_GUARD,'z_guard_mm':q.Z_GUARD}
        assert len(builds)==len(manifest['parts'])==len(cfg.findall('object'))
        assert {q.metadata(o)['name']for o in cfg.findall('object')}==set(manifest['parts'])
        refs=cad.references(option)
        for obj in cfg.findall('object'):
            name=q.metadata(obj)['name'];record=manifest['parts'][name]
            normal=next(p for p in obj.findall('part')if p.get('subtype')=='normal_part' and q.metadata(p).get('name')==name)
            component=next(c for c in roots[obj.get('id')].findall('m:components/m:component',N)if c.get('objectid')==normal.get('id'))
            path=next((v.lstrip('/')for k,v in component.attrib.items()if k.endswith('}path')),'3D/3dmodel.model')
            if path not in cache:cache[path]=E.fromstring(z.read(path))
            child=next(o for o in cache[path].findall('m:resources/m:object',N)if o.get('id')==normal.get('id'))
            vv=np.array([[float(v.get(k))for k in 'xyz']for v in child.findall('m:mesh/m:vertices/m:vertex',N)])
            ff=np.array([[int(v.get(k))for k in ['v1','v2','v3']]for v in child.findall('m:mesh/m:triangles/m:triangle',N)])
            vv=q.points(q.points(vv,q.transform(component.get('transform'))),builds[obj.get('id')])
            expected=trimesh.load_mesh(OUT/deliverables.normal_name(name))
            placement=(vv.min(0)+vv.max(0)-expected.bounds.sum(axis=0))/2
            local=vv-placement
            actual=q.solid(local,ff);solid=q.solid(expected.vertices,expected.faces)
            difference=abs((actual-solid).volume())+abs((solid-actual).volume())
            assert difference<.08,(name,difference)
            xyz=data[:,:3]+off-placement
            bb=expected.bounds;mask=np.all(xyz>=bb[0]-[8,8,.4],axis=1)&np.all(xyz<=bb[1]+[8,8,.4],axis=1)
            samples=xyz[mask];w=data[mask,3];h=data[mask,4];f=data[mask,5].astype(int)
            regions=working_spaces.regions(name,manifest.get('clip_diameter_mm'),tuple(manifest['key_indices'])if manifest.get('coupon')else None)
            pa=np.array(record['print_to_assembly']);pr=np.linalg.inv(pa)
            # Every bead type, including labelled CAD print helpers, must
            # clear working spaces. Separate feature counts are diagnostic.
            support=np.array([features[int(i)].startswith('Support') for i in f])
            checks={n:q.inspect_region(region.transform(pr[:3,:]),samples[~support],w[~support],h[~support],f[~support],features,pa)for n,region in regions.items()}
            support_checks={n:q.inspect_region(region.transform(pr[:3,:]),samples[support],w[support],h[support],f[support],features,pa)for n,region in regions.items()}
            # With no slicer-support rows, the preceding non-support scan
            # already includes every bead, including CAD aids and brim.
            # R12's support-bearing negative control takes the full branch.
            all_checks=checks if not support.any()else {n:q.inspect_region(region.transform(pr[:3,:]),samples,w,h,f,features,pa)for n,region in regions.items()}
            model_rows=np.array([not features[int(v)].startswith(('Support','Brim','Skirt'))for v in f])
            assert model_rows.sum()>100,(name,'Missing neighbouring model paths')
            assert abs(float(samples[model_rows,2].max())-bb[1,2])<.4,(name,'Missing top paths')
            # Recover explicit CAD-wall paths from their exact exported mesh,
            # excluding any points in the normal part. All-bead checks above
            # already include these walls, so this only credits real backing.
            starts_f=f.copy();starts_features=list(features)
            hs=None;helper_difference=0.
            helper_path=OUT/(name+'-PRINT-HELPER-assembly.stl')
            if helper_path.exists():
                hm=trimesh.load_mesh(helper_path);hm.apply_transform(pr)
                hs=q.solid(hm.vertices,hm.faces)
                hp=[p for p in obj.findall('part')if p.get('subtype')=='normal_part'and p.get('id')!=normal.get('id')]
                assert len(hp)==1,(name,'Missing or unexpected print helper')
                hc=next(c for c in roots[obj.get('id')].findall('m:components/m:component',N)if c.get('objectid')==hp[0].get('id'))
                hf=next((v.lstrip('/')for k,v in hc.attrib.items()if k.endswith('}path')),'3D/3dmodel.model')
                if hf not in cache:cache[hf]=E.fromstring(z.read(hf))
                ho=next(o for o in cache[hf].findall('m:resources/m:object',N)if o.get('id')==hp[0].get('id'))
                hv=np.array([[float(v.get(k))for k in 'xyz']for v in ho.findall('m:mesh/m:vertices/m:vertex',N)])
                ht=np.array([[int(v.get(k))for k in ['v1','v2','v3']]for v in ho.findall('m:mesh/m:triangles/m:triangle',N)])
                hv=q.points(q.points(hv,q.transform(hc.get('transform'))),builds[obj.get('id')])-placement
                actual_helper=q.solid(hv,ht)
                helper_difference=abs((hs-actual_helper).volume())+abs((actual_helper-hs).volume())
                assert helper_difference<.08,(name,'Actual helper mesh changed',helper_difference)
                hs=actual_helper
                sid=len(starts_features);starts_features.append('Support - explicit exterior CAD wall')
                for top in np.unique(np.round(data[mask,7],4)):
                    ii=np.flatnonzero(abs(data[mask,7]-top)<.001);mid=float(top)-float(h[ii].min())/2
                    sec=hs.slice(mid);normal_sec=actual.slice(mid)
                    if sec.is_empty():continue
                    hit=q._inside(sec.offset(.15),samples[ii,:2]) & ~q._inside(normal_sec.offset(.06),samples[ii,:2])
                    starts_f[ii[hit]]=sid
            helper_rows=starts_f==len(features)if hs is not None else np.zeros(len(samples),bool)
            if hs is not None:
                assert helper_rows.sum()>100,(name,'No actual print-helper extrusion')
                assert abs(float(samples[helper_rows,2].max())-hs.bounding_box()[5])<.3,(name,'Missing print-helper top')
            assembly_samples=q.points(samples,pa);bonded=np.zeros(len(samples),bool)
            helpers_module=cad.load('print_project',HERE)
            for tab in helpers_module.bonded_tabs(name):
                tb=np.array(tab.bounding_box()).reshape(2,3)
                bonded|=np.all(assembly_samples>=tb[0]-.5,axis=1)&np.all(assembly_samples<=tb[1]+.5,axis=1)
            gap_check=side_gap.inspect(samples,w,data[mask,7],helper_rows,bonded)
            starts=start_audit.inspect(q,actual,samples,h,starts_f,starts_features,data[mask,7],pa,w)
            # Also check print helpers themselves. Duplicate actual lower paths
            # as backing candidates so a real normal-part surface may support
            # a helper across its deliberate gap; never invent support paths.
            combined=actual if hs is None else actual+hs
            all_features=list(features)+['Support - actual lower bead backing']
            fs=np.concatenate([f,np.full(len(f),len(features))])
            whole_starts=start_audit.inspect(q,combined,np.vstack([samples,samples]),np.r_[h,h],fs,all_features,np.r_[data[mask,7],data[mask,7]],pa,np.r_[w,w])
            if report_path is None and (OUT==HERE/'exports' or manifest.get('coupon')or manifest.get('subset_test')):
                views(name,actual,hs,samples,data[mask,7])
                report.setdefault('slice_images_sha256',{})[name+'-slice-views.png']=cad.sha(OUT/(name+'-slice-views.png'))
            report['parts'][name]={'normal_mesh_difference_mm3':difference,'helper_mesh_difference_mm3':helper_difference,'checks':all_checks,'model_only_checks':checks,'support_only_checks':support_checks,'layer_starts':starts,'whole_print_layer_starts':whole_starts,'helper_side_gap':gap_check}
            print(name,{n:c['violations']for n,c in all_checks.items()if c['violations']},flush=True)
            print('floating layer starts:',starts['floating_components'][:5],flush=True)
        report['passed']=all(not c['violations']for p in report['parts'].values()for c in p['checks'].values()) and all(not p['whole_print_layer_starts']['floating_components']and not p['whole_print_layer_starts']['missing_printed_components'] for p in report['parts'].values()) and all(not p['helper_side_gap']['violating_samples']for p in report['parts'].values())
        (report_path or OUT/'slice-clearances.json').write_text(json.dumps(report,indent=2)+'\n')
        assert report['passed'],'Actual model/support extrusion entered a protected space; inspect slice-clearances.json'
        print('All actual bead types, prepared normal meshes and supported starts passed.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path);ap.add_argument('--exports',type=Path);ap.add_argument('--report',type=Path);ap.add_argument('--option', choices=list(cad.OPTIONS), default='modular');a=ap.parse_args();inspect(a.option,a.project,a.exports,a.report)
