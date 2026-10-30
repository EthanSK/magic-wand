#!/usr/bin/env python3
"""Check final prepared meshes and actual model/support extrusion in openings.

Compose the Shard R2 parser, bead-footprint checker and layer-start audit.
Clearance guards are numerical allowances, not manufacturing tolerances.
"""
import argparse,importlib.util,json,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
import trimesh
import cad
HERE=Path(__file__).resolve().parent;OUT=HERE/'exports'
spec=importlib.util.spec_from_file_location('existing_path_auditor',HERE.parent/'printed-loop-wand/shard-tube-r2/check_sliced_paths.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
N={'m':q.NS};tag=lambda s:'{'+q.NS+'}'+s

def inspect(project=None):
    manifest=json.loads((OUT/'manifest.json').read_text())
    project=project or OUT/'Holder-pair-sliced.3mf'
    with zipfile.ZipFile(project)as z:
        assert z.testzip()is None
        cfg=E.fromstring(z.read('Metadata/model_settings.config'))
        model=E.fromstring(z.read('3D/3dmodel.model'));cache={'3D/3dmodel.model':model}
        roots={o.get('id'):o for o in model.findall('m:resources/m:object',N)}
        builds={i.get('objectid'):q.transform(i.get('transform'))for i in model.findall('m:build/m:item',N)}
        config=json.loads(z.read('Metadata/project_settings.config'))
        data,features,stats=q.extrusion_points(z.read('Metadata/plate_1.gcode').decode(),.3)
        off=np.array([float(x)for x in config.get('extruder_offset',['0x0'])[0].split('x')]+[0])
        report={'project_sha256':cad.sha(project),'checker_sha256':cad.sha(Path(__file__)),'parser_sha256':cad.sha(Path(q.__file__)),'manifest_sha256':cad.sha(OUT/'manifest.json'),'parts':{},'path_samples':len(data),'parser_stats':stats,'physical_fit_verified':False,'xy_guard_mm':q.XY_GUARD,'z_guard_mm':q.Z_GUARD}
        refs=cad.references()
        for obj in cfg.findall('object'):
            name=q.metadata(obj)['name'];record=manifest['parts'][name]
            normal=next(p for p in obj.findall('part')if p.get('subtype')=='normal_part')
            component=next(c for c in roots[obj.get('id')].findall('m:components/m:component',N)if c.get('objectid')==normal.get('id'))
            path=next((v.lstrip('/')for k,v in component.attrib.items()if k.endswith('}path')),'3D/3dmodel.model')
            if path not in cache:cache[path]=E.fromstring(z.read(path))
            child=next(o for o in cache[path].findall('m:resources/m:object',N)if o.get('id')==normal.get('id'))
            vv=np.array([[float(v.get(k))for k in 'xyz']for v in child.findall('m:mesh/m:vertices/m:vertex',N)])
            ff=np.array([[int(v.get(k))for k in ['v1','v2','v3']]for v in child.findall('m:mesh/m:triangles/m:triangle',N)])
            vv=q.points(q.points(vv,q.transform(component.get('transform'))),builds[obj.get('id')])
            expected=trimesh.load_mesh(OUT/(name+'.stl'))
            placement=(vv.min(0)+vv.max(0)-expected.bounds.sum(axis=0))/2
            local=vv-placement
            actual=q.solid(local,ff);solid=q.solid(expected.vertices,expected.faces)
            difference=abs((actual-solid).volume())+abs((solid-actual).volume())
            assert difference<.08,(name,difference)
            xyz=data[:,:3]+off-placement
            bb=expected.bounds;mask=np.all(xyz>=bb[0]-[8,8,.4],axis=1)&np.all(xyz<=bb[1]+[8,8,.4],axis=1)
            samples=xyz[mask];w=data[mask,3];h=data[mask,4];f=data[mask,5].astype(int)
            rod=cad.cyl(cad.P['rod']['diameter']/2,-40,100).rotate((-90,0,0))
            regions={'rod':rod}
            if name=='Key_Battery_Carrier':
                regions['battery']=refs['battery']
                for x in [-cad.P['keys']['pitch'],0,cad.P['keys']['pitch']]:
                    for label,part in cad.ds.local_hardware(cad.C).items():
                        if label in ['switch_housing','socket','switch_pins']:
                            regions[f'{x}_{label}']=part.translate((x,0,cad.P['keys']['plate_z']))
            else:
                regions.update({'board':refs['pcb'],'usb':refs['usb'],'central_solder_space':cad.box(-7.2,7.2,4,19,5.3,cad.P['sensor']['board_z'])})
            pa=np.array(record['print_to_assembly']);pr=np.linalg.inv(pa)
            checks={n:q.inspect_region(region.transform(pr[:3,:]),samples,w,h,f,features,pa)for n,region in regions.items()}
            starts=q.inspect_layer_starts(actual,samples,h,f,features,data[mask,7],pa,w,float(config.get('support_top_z_distance','.2')))
            report['parts'][name]={'normal_mesh_difference_mm3':difference,'checks':checks,'layer_starts':starts}
            print(name,{n:c['violations']for n,c in checks.items()if c['violations']},flush=True)
            print('floating layer starts:',starts['floating_components'][:5],flush=True)
        report['passed']=all(not c['violations']for p in report['parts'].values()for c in p['checks'].values()) and all(not p['layer_starts']['floating_components'] for p in report['parts'].values())
        (OUT/'slice-clearances.json').write_text(json.dumps(report,indent=2)+'\n')
        assert report['passed'],'Actual model/support extrusion entered a protected space; inspect slice-clearances.json'
        print('All prepared meshes and sampled model/support bead clearances passed.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path);a=ap.parse_args();inspect(a.project)
