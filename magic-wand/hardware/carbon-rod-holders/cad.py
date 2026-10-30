#!/usr/bin/env python3
"""Two sparse accessories for the original carbon rod, not a replacement wand.

Ethan's 'three keys horizontal side by side' means X across the rod, with
the battery above the middle key along +Y. Z points out towards the finger.
The 'tip one' is the small XIAO holder. Bought parts are reference geometry,
never part of a printable STL or 3MF. parameters.json is the dimension source.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, sys
from pathlib import Path
import numpy as np
import manifold3d as mf
import trimesh

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / 'parameters.json').read_text())
Manifold = mf.Manifold

def union(items):
    return Manifold.batch_boolean(list(items), mf.OpType.Add)

def box(x0,x1,y0,y1,z0,z1):
    return Manifold.cube((x1-x0,y1-y0,z1-z0)).translate((x0,y0,z0))

def cyl(r,z0,z1,x=0.,y=0.):
    return Manifold.cylinder(z1-z0,r,r,64).translate((x,y,z0))

def rr(w,h,r,z0,z1):
    return Manifold.batch_hull([cyl(r,z0,z1,x,y) for x in [-w/2+r,w/2-r] for y in [-h/2+r,h/2-r]])

def rib(a,b,r=.85):
    return Manifold.batch_hull([Manifold.sphere(r,16).translate(a),Manifold.sphere(r,16).translate(b)])

def tube_y(r0,r1,y0,y1):
    return (cyl(r1,y0,y1)-cyl(r0,y0-.1,y1+.1)).rotate((-90,0,0))

def rod_saddle(y0,y1):
    r=P['rod']['diameter']/2+P['rod']['diametral_clearance']/2
    # A half-round seat lowers onto the existing wired rod without threading
    # through it or relying on an untested printed snap spring. Tape/glue holds.
    return tube_y(r,r+1.5,y0,y1)^box(-10,10,y0-.1,y1+.1,0,10)

def load_seat_module():
    path=HERE.parent/'printed-loop-wand/shard-tube-r2/direct_switches.py'
    spec=importlib.util.spec_from_file_location('carbon_rod_choc_reference',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

ds=load_seat_module()
C=sys.modules[__name__]

def key_seat():
    # Reuse Shard R2's established pattern: real housing/post/socket cuts and
    # bought factory clips. The surrounding sparse frame is new geometry.
    face=rr(ds.FACE_W,ds.FACE_H,1.1,0,ds.FACE_T)
    backing=rr(ds.FACE_W,ds.FACE_H,1.1,-2.35,.05)-rr(ds.SWITCH_OPENING+.7,ds.SWITCH_OPENING+.7,.45,-2.5,.2)
    # Two annular locating pads and short ribs replace a broad socket floor.
    # They back the socket posts while leaving most of its underside open.
    floor=union([cyl(2.5,-5.8,-4.4,-5.9,0),cyl(2.5,-5.8,-4.4,-3.8,-5),
        rib((-8.8,-9.8,-5.1),(-8.8,3.2,-5.1),.7),
        rib((-8.8,0,-5.1),(-5.9,0,-5.1),.7),
        rib((-8.8,-9.8,-5.1),(-3.8,-5,-5.1),.7)])
    supports=[rib((-8.8,y,-5.2),(-8.1,y,-1.2),.9) for y in [-8.4,3.2]]
    # Void last, including after every brace. Solder and clip space stay open.
    return union([face,backing,floor]+supports)-ds.local_void(C)

def carrier():
    k=P['keys']; b=P['battery']; z=k['plate_z']; pitch=k['pitch']
    parts=[key_seat().translate((x,0,z)) for x in [-pitch,0,pitch]]
    # Two continuous rails share finger loads across all three seats.
    for y in [-10.5,10.5]:
        parts.append(rib((-pitch-8.4,y,z-.45),(pitch+8.4,y,z-.45),1.0))
        for x in [-pitch,0,pitch]:
            for sign in [-1,1]:
                parts.append(rib((x+sign*7.7,y,z-.45),(x+sign*7.7,math.copysign(8.1,y),z-.45),1.2))
        parts.append(rod_saddle(y-2,y+2))
        parts.append(rib((0,y,5.35),(7.5,y,z-.5),1.0))
        for sign in [-1,1]:
            parts.append(rib((sign*4.0,y,3.9),(sign*7.5,y,z-.5),1.2))
            parts.append(rib((sign*7.5,y,z-.5),(sign*(pitch+5),y,z-.5),1.0))
    w=b['width']+2*b['clearance_per_side']; L=b['length']+2*b['clearance_per_side']
    y0=b['start_y']; y1=y0+L; bz=b['floor_z']
    # Open ladder, smooth side guards and split end stops; no battery clamp.
    for side in [-1,1]:
        x=side*(w/2+.65)
        parts.append(box(x-.65,x+.65,y0-1.2,y1+1.2,bz-1.2,bz+2.6))
        parts.append(rib((side*7.5,10.5,z-.5),(x,y0+3,bz),1.0))
        for yy in [y0+9,y1-9]:
            ear=rr(5.4,8,1.2,bz-1.2,bz+.2)-rr(2.6,4.8,.7,bz-1.4,bz+.4)
            parts.append(ear.translate((x+side*2.3,yy,0)))
    for yy in [y0-.6,y0+L/3,y0+2*L/3,y1+.6]:
        parts.append(rib((-w/2,yy,bz-.65),(w/2,yy,bz-.65),.7))
    for yy in [y0-.6,y1+.6]:
        for side in [-1,1]:
            parts.append(box(side*w/2-2,side*w/2+2,yy-.65,yy+.65,bz-.6,bz+2.6))
    parts.append(rod_saddle(y1-4,y1))
    parts.append(rib((0,y1-2,5.35),(w/2+.65,y1-2,bz+1.5),.9))
    for side in [-1,1]:
        parts.append(rib((side*4.0,y1-2,3.9),(side*(w/2+.65),y1-2,bz),1.0))
    # All structural unions precede the purchased hardware clearance cuts.
    obj=union(parts)
    obj=obj-union([ds.local_void(C).translate((x,0,z)) for x in [-pitch,0,pitch]])
    obj=obj-box(-b['width']/2,b['width']/2,y0+b['clearance_per_side'],y0+b['clearance_per_side']+b['length'],bz,bz+b['thickness']+.2)
    return obj

def sensor_holder():
    s=P['sensor']; rod=P['rod']; ir=rod['diameter']/2+rod['diametral_clearance']/2
    orad=ir+rod['wall']; half=s['board_width']/2; z=s['board_z']
    parts=[tube_y(ir,orad,-5,-2.6),tube_y(ir,orad,21,23.4)]
    for sign in [-1,1]:
        # Open sleeve between the two short rings, with triangulated outer
        # side struts. No rib crosses the board's central solder space.
        parts.append(rib((sign*(orad-.6),-4,0),(sign*(orad-.6),22.2,0),.65))
        x=sign*(half+.9)
        parts.append(box(x-.6,x+.6,1,23.2,z-1.2,z+1.2))
        parts.append(rib((sign*3.7,-4,3.5),(x,2,z-.65),.8))
        parts.append(rib((sign*3.7,21.8,3.5),(x,21.8,z-.65),.8))
        parts.append(rib((0,-4,5.15),(x,2,z-.65),.8))
        parts.append(rib((0,21.8,5.15),(x,21.8,z-.65),.8))
        parts.append(rib((sign*5.0,7.5,0),(x,17,z-.65),.65))
        # Four corner ledges touch only narrow PCB edges. Soft tape supplies
        # retention; no PETG claws push on the board or soldered connections.
        for yy in [2.0,21.0]:
            parts.append(box(sign*(half+.3)-1.0,sign*(half+.3)+1.0,yy-.8,yy+.8,z-1.0,z))
        # Bottom stops are split to leave the middle and wire route open.
        sx=sign*(half-.3)
        parts.append(box(sx-.7,sx+.7,.3,1.3,z-.8,z+1.0))
    # Keep the final rod passage clear after every structural union.
    return union(parts)-cyl(ir,-30,60).rotate((-90,0,0))

def references():
    b=P['battery'];s=P['sensor'];k=P['keys'];z=k['plate_z']
    refs={'rod':Manifold.cylinder(500,P['rod']['diameter']/2,P['rod']['diameter']/2,64).rotate((-90,0,0)).translate((0,-25,0)),
          'battery':box(-b['width']/2,b['width']/2,b['start_y']+b['clearance_per_side'],b['start_y']+b['clearance_per_side']+b['length'],b['floor_z'],b['floor_z']+b['thickness'])}
    for i,x in enumerate([-k['pitch'],0,k['pitch']]):
        for name,shape in ds.local_hardware(C).items():
            if name in ['switch','socket']:
                refs[f'key_{i}_{name}']=shape.translate((x,0,z))
        refs[f'key_{i}_cap']=rr(16.6,17.5,1.4,z+3.6,z+6.6).translate((x,0,0))
    refs['pcb']=box(-s['board_width']/2,s['board_width']/2,1.3,1.3+s['board_length'],s['board_z'],s['board_z']+s['board_thickness'])
    refs['usb']=box(-4.6,4.6,18,24.3,s['board_z']+1,s['board_z']+4.2)
    return refs

def mesh(shape):
    m=shape.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def export(out):
    out.mkdir(parents=True,exist_ok=True)
    models={'Key_Battery_Carrier':carrier(),'XIAO_Rod_Holder':sensor_holder()}
    records={};scene=trimesh.Scene()
    for name,obj in models.items():
        assert obj.status()==mf.Error.NoError,(name,obj.status())
        m=mesh(obj); assert m.is_watertight and m.is_winding_consistent,name
        assert len(m.split())==1,(name,len(m.split()))
        m.export(out/(name+'-assembly.stl'))
        # The key faces / battery guards and the board side fences lie on the
        # bed. Growing back towards the rod avoids vertical floating rings.
        oriented=m.copy();rot=trimesh.transformations.rotation_matrix(math.pi,[1,0,0]);oriented.apply_transform(rot)
        shift=trimesh.transformations.translation_matrix(-oriented.bounds[0]);oriented.apply_transform(shift);oriented.export(out/(name+'.stl'))
        reloaded=trimesh.load_mesh(out/(name+'.stl'))
        assert reloaded.is_watertight and len(reloaded.split())==1
        records[name]={'bounds_mm':m.bounds.tolist(),'volume_mm3':m.volume,'solid_PETG_g':m.volume/1000*P['print']['density_g_cm3'],
                       'watertight':True,'body_count':1,'stl_sha256':sha(out/(name+'.stl')),
                       'print_to_assembly':np.linalg.inv(shift@rot).tolist()}
        m.visual.vertex_colors=[65,202,204,255] if name.startswith('Key') else [237,166,73,255]
        if name.startswith('XIAO'):m.apply_translation((0,451.6,0))
        scene.add_geometry(m,node_name=name)
    refs=references()
    for name,obj in refs.items():
        m=mesh(obj)
        if name in ['pcb','usb']:m.apply_translation((0,451.6,0))
        color=[34,43,52,255] if name=='rod' else [96,108,127,175] if name=='battery' else [54,110,75,255] if name=='pcb' else [187,192,202,240] if name=='usb' else [227,230,235,255]
        m.visual.vertex_colors=color;scene.add_geometry(m,node_name='REFERENCE_'+name)
    scene.export(out/'Assembly-reference.glb')
    sources=[HERE/'cad.py',HERE/'parameters.json',HERE.parent/'printed-loop-wand/shard-tube-r2/direct_switches.py']
    report={'source_sha256':{str(p.relative_to(HERE))if p.is_relative_to(HERE)else '../printed-loop-wand/shard-tube-r2/'+p.name:sha(p)for p in sources},'physical_fit_verified':False,'scope':'CAD export; print evidence is in print-checks.json and slice-clearances.json','parts':records}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    summary={n:{k:v for k,v in r.items() if k not in ['assembly_vertices','assembly_faces']}for n,r in records.items()}
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=HERE/'exports');args=ap.parse_args();export(args.out)
