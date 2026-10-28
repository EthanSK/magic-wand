#!/usr/bin/env python3
"""Shard Tube R2: repaired lower assembly generated as actual closed CAD meshes.

Old revisions remain immutable. Units mm; canonical butt Z0, tip+Z.
Boolean switch/receiver/cell/thread cuts are baked into each grip, never sent
as slicer negative volumes. The unchanged Shard upper assembly is reused.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,sys
from functools import lru_cache
from pathlib import Path
import numpy as np
import manifold3d as mf
import trimesh
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'v20'
UPPER=HERE.parent/'shard-tube'

def module(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sys.modules[name]=m;sp.loader.exec_module(m);return m
c=module('shard_r2_v20_library',BASE/'wand_cad.py')
ds=module('shard_r2_switches',HERE/'direct_switches.py')
cp=module('shard_r2_caps',HERE/'cap_design.py')

@lru_cache(None)
def handle_module():return module('shard_r2_handle',HERE/'handle_design.py')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

@lru_cache(None)
def cell_loading_void():
    # FULL insertion sweep, including the sled's 20.6 mm width and lower feet.
    # This opens the old Z6.3..13 diaphragm and remains open after ALL unions.
    rectangle=c.rr(21.2,9.2,.8,-65.,59.5).translate((0.,-.3,0.))
    # Join the threaded mouth to the hollow chamber with 0.1mm overlap.
    # Without this, Z11.4..12.0 leaves long unsupported crescent roofs.
    return rectangle+c.cyl(cp.CORE_RADIUS,11.3,12.1)

@lru_cache(None)
def hollow_core():
    core=[]
    for a in np.arange(12.,147.,1.):
        core.append(c.Manifold.batch_hull([c.cyl(c.radius(z)-c.GRIP_WALL,z,z+.015).scale(((c.grip_xradius(z)-c.GRIP_WALL)/(c.radius(z)-c.GRIP_WALL),1.,1.)) for z in [float(a),float(a+1.01)]]))
    core += [c.Manifold.batch_hull([c.cyl(c.radius(147.)-c.GRIP_WALL,146.9,147.),c.cyl(c.BORE/2,154.,154.1)]),c.cyl(c.BORE/2,153.,177.)]
    return c.union(core)

def hand_buttons(right=False):return [(name,-a if right else a,z)for name,a,z in c.HAND_BUTTONS]

@lru_cache(None)
def grip_shell():
    outer=c.body(3.2,c.HANDLE_END-.2)+c.male_at(c.HANDLE_END)
    shell=outer-hollow_core()-c.body_slots('grip')
    webs=[c.box(10.7,14.8,-.6,.6,16.,52.),c.box(-14.8,-10.7,-.6,.6,16.,52.)]
    webs=[m^c.body(15.,53.)for m in webs]
    rails=[c.box(10.7,11.5,-2.2,2.2,16.,52.),c.box(-11.5,-10.7,-2.2,2.2,16.,52.)]
    return c.union([shell,c.axial_rails('grip')]+webs+rails)

@lru_cache(None)
def grip(right=False):
    hd=handle_module()
    pads=[ds.pad(c,a,z)for _,a,z in hand_buttons(right)]
    # Receiver API includes only permanent recessed material. All projecting
    # hooks/keeper belong to the removable loop and are exported separately.
    positive=c.union([grip_shell(),hd.receiver_material(c)]+pads)
    cuts=c.union([cell_loading_void(),cp.female_socket_void(c),c.cyl(c.BORE/2,61.,177.),hd.receiver_void(c)]+[ds.void(c,a,z)for _,a,z in hand_buttons(right)])
    result=(positive-cuts).as_original().simplify(.0006)
    components=result.decompose();major=[p for p in components if p.volume()>.02];debris=sum(abs(p.volume())for p in components if p.volume()<=.02)
    assert len(major)==1 and debris<.02,[(p.volume(),p.bounding_box())for p in components]
    return major[0]

@lru_cache(None)
def battery_sled():
    old=c.battery_sled()
    # Two small feet and a crossbar rest above the closed cap floor; the cell
    # sits on the original open ladder. No solid battery-shaped infill block.
    feet=[c.box(8.3,9.2,-4.1,-2.9,3.4,13.2),c.box(-9.2,-8.3,-4.1,-2.9,3.4,13.2),c.box(-9.2,9.2,-4.1,-2.9,3.4,4.6)]
    # Rectangular cell clearance: do not rely on a rounded-cell assumption.
    return c.union([old]+feet)-c.box(-11.,11.,-3.2,5.,14.4,56.6)

@lru_cache(None)
def reused_upper(name):
    manifest=json.loads((UPPER/'exports/manifest.json').read_text());p=next(p for p in manifest['parts']if p['name']==name);path=UPPER/'exports'/p['file'];assert sha(path)==p['sha256']
    mesh=trimesh.load_mesh(path,process=True);mesh.apply_transform(np.asarray(p['print_to_assembly']))
    return c.b.closed_mesh(mesh.vertices.tolist(),mesh.faces.tolist(),'unchanged Shard '+name)

@lru_cache(None)
def models():
    hd=handle_module()
    parts={'Grip_Left':grip(False),'Grip_Right':grip(True),'Removable_Finger_Loop':hd.loop(c),'Loop_Keeper_Key':hd.keeper(c),'Battery_Screw_Cap_Light':cp.light_cap(c),'Battery_Screw_Cap_Weighted':cp.weighted_cap(c),'Battery_Sled':battery_sled(),'Continuous_Shaft':reused_upper('Continuous_Shaft'),'Sense_Open_Cradle':reused_upper('Sense_Open_Cradle'),'Thread_Gauge':cp.socket_coupon(c)}
    # Actual functional geometry cropped into small fit samples, not guessed
    # stand-ins. Tests must validate the same interfaces as the full assembly.
    # A short ACTUAL grip section preserves the socket's real backing and
    # printing orientation. An isolated lip coupon otherwise cantilevers.
    parts['Switch_Fit_Test']=grip()^c.box(-30.,30.,-20.,20.,100.,122.)
    parts['Loop_Upper_Socket_Test']=grip()^c.box(-14.,14.,-15.,6.,93.,118.)
    parts['Loop_Upper_Hook_Test']=hd.loop(c)^c.box(-12.,12.,-31.,1.,93.,115.)
    return parts


def export_part(name,solid,out):
    # Resolve sub-print-resolution coincident Boolean seams before STL.
    tolerance=.01 if name in ['Grip_Left','Grip_Right','Loop_Upper_Socket_Test','Switch_Fit_Test'] else .0006
    solid=solid.as_original().simplify(tolerance)
    assert solid.status()==mf.Error.NoError and len(solid.decompose())==1,(name,solid.status(),[(p.volume(),p.bounding_box())for p in solid.decompose()])
    rot=(0.,0.,0.)
    if name in ['Removable_Finger_Loop','Loop_Upper_Hook_Test']:rot=(0.,-90.,0.)
    if name=='Battery_Sled':rot=(90.,0.,0.)
    if name=='Loop_Keeper_Key':rot=(-90.,0.,0.)
    if name=='Sense_Open_Cradle':rot=(90.,0.,0.)
    # The unchanged sensor cradle retains main's checked back-flat orientation
    # and carefully limited low-back print supports; its holes are real cuts.
    # All caps print closed face down; their open necks face upwards.
    mesh=solid.rotate(rot);bb=mesh.bounding_box();shift=(-(bb[0]+bb[3])/2,-(bb[1]+bb[4])/2,-bb[2]);mesh=mesh.translate(shift)
    triangles=c.b.canonical_triangles(mesh);checks=c.b.mesh_checks(triangles,len(solid.decompose()))
    assert checks['watertight']and checks['winding_consistent']and checks['every_edge_shared_twice']and checks['bodies']==1,(name,checks)
    blob=c.b.stl_bytes(triangles,name)
    with (out/(name+'.stl')).open('xb') as f:f.write(blob)
    r=c.b.rotation(rot);t=np.eye(4);t[:3,:3]=r.T;t[:3,3]=-r.T@np.asarray(shift)
    # Viewer/3MF geometry comes from the very same checked STL triangles.
    pv,idx=np.unique(triangles.reshape(-1,3),axis=0,return_inverse=True)
    av=pv.astype(float)@t[:3,:3].T+t[:3,3]
    return {'name':name,'file':name+'.stl','sha256':hashlib.sha256(blob).hexdigest(),'checks':checks,'print_to_assembly':t.tolist(),'export_surface_tolerance_mm':tolerance,'assembly_vertices':av.tolist(),'assembly_faces':idx.reshape(-1,3).tolist()}


def build(out):
    out.mkdir(parents=True,exist_ok=False)
    records=[export_part(n,p,out)for n,p in models().items()]
    source_files=[HERE/'wand_cad.py',HERE/'direct_switches.py',HERE/'handle_design.py',HERE/'cap_design.py',BASE/'wand_cad.py',BASE/'design-principles.json',BASE.parent/'v2/reference/wand_cad.py',BASE.parent/'v2/reference/dimensions.json',BASE.parent/'v2/wand_cad.py',UPPER/'exports/manifest.json',UPPER/'exports/Continuous_Shaft.stl',UPPER/'exports/Sense_Open_Cradle.stl']
    hd=handle_module();report={'version':'Shard Tube R2 mechanical repair','length_light_mm':410.,'weighted_extension_below_butt_mm':18.,'button_mounts':hand_buttons(),'switches':ds.seat_data(),'caps':cp.specs(),'handle':hd.specs(),'battery':{'nominal_cell_mm':[20.,6.,40.],'provisional':True,'bottom_loading':True,'minimum_thread_mouth_mm':24.4,'full_sled_insertion_checked':False},'slicer_modifiers':True,'functional_negative_modifiers':False,'support_helpers':{'Sense_Open_Cradle':'manual low-back enforcer and functional-space protection only'},'separate_switch_plate_count':0,'physical_fit_verified':False,'parts':records,'source':{__import__('os').path.relpath(p,HERE):sha(p)for p in source_files}}
    with (out/'manifest.json').open('x') as f:json.dump(report,f,separators=(',',':'));f.write('\n')
    print(json.dumps({'parts':{p['name']:p['checks']for p in records}},indent=2),flush=True)
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();build(args.out.resolve())
