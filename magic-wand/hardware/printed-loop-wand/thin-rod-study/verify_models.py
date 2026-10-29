#!/usr/bin/env python3
"""Verify final exported solids and actual sliced paths, not physical strength."""
import argparse,hashlib,importlib.util,json,sys,zipfile
from pathlib import Path
import numpy as np
import trimesh
HERE=Path(__file__).resolve().parent
def load(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sys.modules[name]=m;sp.loader.exec_module(m);return m
cad=load('thin_rod_geometry_check',HERE/'wand_cad.py')
paths=load('thin_rod_gcode_samples',HERE.parent/'continuous-two-wide-v19/inspect_sliced_paths.py')

def verify(exports,slices,out):
    manifest=json.loads((exports/'manifest.json').read_text());projects=json.loads((slices/'projects.json').read_text());report={}
    for key,variant in manifest['variants'].items():
        solids={}
        for p in variant['parts']:
            path=exports/key/p['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256']
            mesh=trimesh.load_mesh(path,process=True);assert mesh.is_watertight and mesh.is_winding_consistent
            mesh.apply_transform(p['print_to_assembly']);solids[p['name']]=cad.v.b.closed_mesh(mesh.vertices,mesh.faces,p['name'])
        geometry=cad.checks(solids,*cad.VARIANTS[key])
        clip=cad.v.board_release_clip();raw=clip.refine_to_length(.7).to_mesh();rigid=solids['Upper_Body_With_Sensor_Fork']-clip
        release=[]
        for depth in np.linspace(0.,1.3,8):
            vertices=np.array(raw.vert_properties[:,:3],dtype=np.float32);vertices[:,2]-=depth*np.maximum(0,1-(vertices[:,0]/10.)**2)**2
            flex=cad.mf.Manifold(cad.mf.Mesh(vertices,np.asarray(raw.tri_verts,dtype=np.uint32)))
            release.append(abs((rigid^flex).volume()))
        assert max(release)<.004,('clip blocked',release)
        islands=[]
        for z in np.arange(350.2,410.,.2):
            up=solids['Upper_Body_With_Sensor_Fork'];previous=up.slice(float(z-.2)).offset(.25)
            for c in up.slice(float(z)).decompose():
                if c.area()>.015 and (c^previous).area()<.002:islands.append(round(float(z),3))
        assert not islands,('unbacked sensor starts',islands)
        record=projects[key];archive=slices/(key+'-slice')/record['file']
        assert not record['slice'].get('warning_message'),record['slice'].get('warning_message')
        points,features=paths.samples(archive);p=next(p for p in variant['parts']if p['name']=='Upper_Body_With_Sensor_Fork')
        t=np.asarray(p['print_to_assembly']);xyz=(points+[0.,2.,0.]-[155.,110.,0.])@t[:3,:3].T+t[:3,3];x,y,z=xyz.T
        # Conservative inner functional spaces; account for extrusion width
        # by probing 0.3 mm inside each wall, as in existing Shard checks.
        areas={'board':(abs(x)<8.6)&(y>-5.2)&(y<-4.2)&(z>376.3)&(z<396.7),
            'solder':(abs(x)<5.1)&(y>-11.)&(y<-5.9)&(z>379.5)&(z<393.5),
            'usb':(abs(x)<5.4)&(y>-6.)&(y<-1.)&(z>397.6)&(z<410.7),
            'wire_exit':(x*x+(y-2.)**2<2.4**2)&(z>375.3)&(z<387.2)}
        counts={name:int(mask.sum())for name,mask in areas.items()};assert not any(counts.values()),counts
        nearby=int(((abs(abs(x)-10.5)<2.)&(y>-9.)&(y<-5.)&(z>381.)&(z<393.)).sum())
        assert nearby>100,('vacuous clearance check',nearby)
        with zipfile.ZipFile(archive)as zf:
            assert zf.testzip() is None
            for name in zf.namelist():
                if name.endswith(('.json','.config','.model','.gcode')):
                    data=zf.read(name);assert b'/Users/'not in data and b'/Volumes/'not in data,('private path',name)
        report[key]={'exported_mesh_checks':geometry,'clip_release_max_overlap_mm3':max(release),
            'floating_sensor_layer_starts':islands,'sliced_clearance_samples':counts,'nearby_rail_path_samples':nearby,
            'gcode_sample_step_mm':.5,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'physical_fit_verified':False,'physical_strength_verified':False}
        print(key+' exported solids and actual sliced clearances passed',flush=True)
    out.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--exports',type=Path,required=True);ap.add_argument('--slices',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();verify(a.exports,a.slices,a.out)
