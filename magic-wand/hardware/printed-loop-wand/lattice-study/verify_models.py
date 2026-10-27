#!/usr/bin/env python3
"""Check actual exported STL solids, including sampled material gauges.

The radial gauges sample the centres of retained bands and rails, not every
edge or a minimum breaking strength. This is separate from slicer evidence.
"""
import argparse, importlib.util, json, math
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf

HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('study',HERE/'wand_cad.py')
s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)

def solid(record,path):
    assert s.sha(path)==record['sha256'],str(path)
    mesh=trimesh.load_mesh(path,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent,str(path)
    mesh.apply_transform(record['print_to_assembly'])
    result=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
    assert result.status()==mf.Error.NoError and len(result.decompose())==1,str(path)
    return result

def gauges(c,models,spec):
    result={}
    for zone,name,zs in [('grip','Handle_Left',[62.,75.,88.]),('lower','Lower_Shaft',[190.,211.,228.]),('upper','Upper_Shaft',[275.,299.,323.])]:
        values=[]
        for z in zs:
            r=c.radius(z) if zone=='grip' else c.shaft_radius(z)
            section=models[name].slice(z)
            angles=[0.,90.,180.,270.]
            if spec['kind']=='net':angles += [float(c.b.rib_angle(z,k))+360*i/spec['strands'] for k in (0,1) for i in range(spec['strands'])]
            for angle in angles:
                ray=mf.CrossSection.square((.04,7.)).translate((-.02,r-4.)).rotate(-angle)
                thickness=(section^ray).area()/.04
                values.append(round(thickness,4))
        assert min(values)>.8,(name,'thin retained member centre',min(values))
        result[zone]={'sampled_min_radial_material_mm':min(values),'probes':len(values)}
    # Sample the loop's two broad faces away from the deliberately open vents.
    loop=models['Removable_Finger_Loop'];samples=[]
    path=np.asarray([(z+c.LOOP_SHIFT,y) for z,y in c.b.catmull_rom(c.LOOP_POINTS)])
    for z in [50.,70.,90.,110.]:
        candidates=path[path[:,1]<-32.];i=np.argmin(abs(candidates[:,0]-z));zz,y=candidates[i]
        section=loop.slice(float(zz));ray=mf.CrossSection.square((c.LOOP_WIDTH+2.,.04)).translate((-(c.LOOP_WIDTH+2)/2,y-.02))
        # Sum the two skins; the hollow gap is excluded by the solid.
        combined=(section^ray).area()/.04
        if combined<1.8:continue
        samples.append(round(combined/2,4))
    assert len(samples)>=2,('Too few intact loop skin samples',samples)
    result['loop']={'sampled_mean_of_two_broad_skins_min_mm':min(samples),'probes':len(samples)}
    return result

def main(out):
    manifest=json.loads((HERE/'exports/manifest.json').read_text())
    ref=json.loads((s.BASE/'exports/manifest.json').read_text())
    refs={p['name']:solid(p,s.BASE/'exports'/p['file']) for p in ref['parts'] if p['name'] in s.CHANGED}
    s.reference_part=lambda c,name:refs[name]
    report={'kind':'Checks on actual exported STL solids','physical_strength_verified':False,'variants':{}}
    diamond={p['name']:solid(p,HERE/'exports/diamond'/p['file']) for p in manifest['variants']['diamond']['parts']}
    for key,spec in manifest['variants'].items():
        c=s.configure(key);models={p['name']:solid(p,HERE/'exports'/key/p['file']) for p in spec['parts']}
        # Exported references have different triangulation after 0.001 mm
        # simplification and 0.0001 mm vertex rounding. Exact source solids
        # are checked separately at 0.03 mm3; bound this STL volume residual.
        checks=s.checks(c,models,interface_tolerance=.75)
        checks['exported_interface_volume_tolerance_mm3']=.75;checks['minimum_members']=gauges(c,models,spec)
        if spec.get('wide_strands'):
            # Ethan asked for wide strands so the open sections have more
            # support. Verify this adds body material instead of removing any
            # of the original Diamond net's paths. This is not a load rating.
            # The wider main paths taper towards the tip but remain wider than
            # the Diamond reference. Check retained shell paths, not old backing.
            lost={n:abs((diamond[n]-models[n]).volume()) for n in ['Handle_Left','Handle_Right','Lower_Shaft','Upper_Shaft']}
            assert max(lost.values())<.75,('Lost original net material',key,lost)
            areas={}
            for name,z in [('Handle_Left',75.),('Lower_Shaft',211.),('Upper_Shaft',299.)]:
                before=diamond[name].slice(z).area();after=models[name].slice(z).area();assert after>before*1.05,(key,name,'no meaningful reinforcement')
                areas[name]={'z_mm':z,'diamond_net_mm2':round(before,3),'reinforced_mm2':round(after,3),'increase_percent':round(100*(after/before-1),2)}
            checks['reinforcement']={'lost_original_net_material_mm3':lost,'section_material_area':areas,'physical_strength_verified':False}
        report['variants'][key]=checks
        print(key+' exported STL checks passed',flush=True)
    out.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
