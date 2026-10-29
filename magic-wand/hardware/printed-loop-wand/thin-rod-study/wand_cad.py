#!/usr/bin/env python3
"""Thin solid-body experiment; previous Shard models remain unchanged.

Ethan's 'first tube' is the 8 mm OD / 7 mm ID carbon tube. Here 8 mm
includes the raised counter-wound decoration, not just its underlying core.
External buttons, battery and wiring are deliberately not packaged in this
experimental rod. Its integral sensor fork replaces the old tip bayonet.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, sys
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

v=module('thin_rod_v20',HERE.parent/'v20/wand_cad.py')
s=module('thin_rod_lattice',HERE.parent/'lattice-study/wand_cad.py')
VARIANTS={'tube8':(8.,5.8),'rod10':(10.,7.8)}
SHAFT_END=370.;JOINT0=180.;JOINT1=210.;RIDGE=.45
SOURCE_TUBE={'outside_mm':8.,'inside_mm':7.,'length_mm':500.,
    'source':'https://www.align-trex.co.uk/carbon-fibre-tube-8mm-x-0-5metre-7mm-id.html'}

def envelope(z,base,tip):return (base+(tip-base)*max(0.,min(1.,z/SHAFT_END)))/2

def body(base,tip):
    n=120;zs=np.linspace(0.,SHAFT_END,741);angles=np.arange(n)*2*math.pi/n
    vertices=[]
    for z in zs:
        # Preserve the established 90/72 mm opposite winding directions.
        # Unstacked crossings never exceed the requested outside diameter.
        ridge=np.zeros(n)
        for pitch,sign in [(90.,1.),(72.,-1.)]:
            d=np.arctan2(np.sin(angles-sign*2*math.pi*z/pitch),np.cos(angles-sign*2*math.pi*z/pitch))
            ridge=np.maximum(ridge,RIDGE*np.maximum(0.,np.cos(np.minimum(abs(d)/.27,1.)*math.pi/2))**2)
        fade=min(1.,z/3.,(SHAFT_END-z)/3.)
        rr=envelope(z,base,tip)-RIDGE+ridge*max(0.,fade)
        vertices.extend(zip((rr*np.sin(angles)).tolist(),(rr*np.cos(angles)).tolist(),[float(z)]*n))
    bottom=len(vertices);vertices.extend([(0.,0.,0.),(0.,0.,SHAFT_END)]);faces=[]
    for i in range(len(zs)-1):
        for k in range(n):
            j=(k+1)%n;a=i*n;b=(i+1)*n
            faces.extend([(a+k,a+j,b+j),(a+k,b+j,b+k)])
    for k in range(n):
        j=(k+1)%n;faces.extend([(bottom,j,k),(bottom+1,(len(zs)-1)*n+k,(len(zs)-1)*n+j)])
    return v.b.closed_mesh(vertices,faces,'thin continuous counter-wound body')

def rod(points,radius):
    balls=[mf.Manifold.sphere(radius,24).translate(p)for p in points]
    return v.union([mf.Manifold.batch_hull([a,b])for a,b in zip(balls,balls[1:])])

def sensor_fork():
    # Compose the original checked board guides and release clip. Keep PCB,
    # solder and USB coordinates unchanged; strengthen their supports, not
    # the board slot. No flexible neck, tabs or detachable tip connector.
    old=s.open_head(v)
    guides=v.board_corner_guides()^v.box(-11.2,11.2,-7.4,-2.1,374.5,399.)
    crown=old^v.box(-30.,30.,-30.,30.,398.,411.)
    rails=[]
    for side in (-1.,1.):
        rails += [rod([(0.,0.,355.),(side*12.4,-6.3,374.8),(side*10.5,-6.8,380.)],2.15),
                  v.box(side*10.5-2.,side*10.5+2.,-8.6,-5.4,379.,398.4)]
        # Grow the upper pocket's forward lip from an already printed side
        # rail rather than starting that lip in mid-air. Stay in front of
        # the board, or outside its side edge, throughout the sloped web.
        anchor=v.box(9.15,11.6,-6.,-2.4,387.,390.2)
        lip_web=mf.Manifold.batch_hull([v.box(9.15,11.6,-3.7,-2.4,390.,390.2),v.box(6.25,7.65,-3.7,-2.4,396.4,396.6)])
        back_web=mf.Manifold.batch_hull([v.box(9.15,11.6,-8.6,-5.4,390.,390.2),v.box(6.25,7.65,-7.4,-5.4,396.2,396.4)])
        lower_web=mf.Manifold.batch_hull([v.cyl(2.,358.4,358.6),v.box(6.1,7.8,-7.4,-3.7,374.3,374.6)])
        rails += [q if side>0 else q.mirror((1,0,0))for q in [anchor,lip_web,back_web,lower_web]]
    frame=v.union([guides,crown,v.board_release_clip()]+rails)
    # Original short end seats support the board without covering its long
    # solder edges. Reuse actual positive material, then recheck all voids.
    end_seats=old^v.union([v.box(-13.,13.,-9.,-2.,375.6,378.),v.box(-13.,13.,-9.,-2.,391.1,393.)])
    board_space=v.box(-9.1,9.1,v.BOARD_Y-.05,v.BOARD_Y+v.BOARD_T+.2,v.BOARD0-.1,v.BOARD0+21.1)
    board=v.box(-8.9,8.9,v.BOARD_Y,v.BOARD_Y+v.BOARD_T,v.BOARD0,v.BOARD0+21.)
    pivot=(0.,v.BOARD_Y+v.BOARD_T/2,v.BOARD0+21.)
    poses=[board.translate(tuple(-x for x in pivot)).rotate((a,0,0)).translate(pivot)for a in np.arange(0.,10.01,.5)]
    board_sweep=v.union([mf.Manifold.batch_hull([a,b])for a,b in zip(poses,poses[1:])])
    clip=v.board_release_clip();raw=clip.refine_to_length(.7).to_mesh()
    flex=[]
    for depth in np.linspace(0.,1.3,8):
        vertices=np.array(raw.vert_properties[:,:3],dtype=np.float32)
        vertices[:,2]-=depth*np.maximum(0,1-(vertices[:,0]/10.)**2)**2
        flex.append(mf.Manifold(mf.Mesh(vertices,np.asarray(raw.tri_verts,dtype=np.uint32))))
    # Reinforcement must preserve the board's complete removal pivot and
    # the existing clip's release envelope, not only a seated-board void.
    moving=v.union(flex)^v.box(-10.,10.,-20.,20.,370.,380.)
    release_space=moving.minkowski_sum(mf.Manifold.sphere(.06,8))
    return ((frame+end_seats-board_space-board_sweep-release_space)+clip).as_original().simplify(.001)

def models(base,tip):
    full=body(base,tip)
    # A long half-lap preserves more section than a tiny hollow bayonet.
    # This exploratory joint needs tape or adhesive for retention; it is
    # not presented as the earlier detachable handle/quarter-turn mechanism.
    lower=full^v.box(-20,20,-20,20,-1.,JOINT1)
    lower-=v.box(-20,20,-.10,20,JOINT0,JOINT1+.1)
    upper=full^v.box(-20,20,-20,20,JOINT0,371.)
    upper-=v.box(-20,20,-20,.10,JOINT0-.1,JOINT1)
    upper+=sensor_fork()
    # Small coupons reproduce both actual lap surfaces at their actual size.
    coupons={'Lap_Lower_Test':lower^v.box(-20,20,-20,20,JOINT0-5.,JOINT1+1.),
             'Lap_Upper_Test':upper^v.box(-20,20,-20,20,JOINT0-1.,JOINT1+5.)}
    return {'Lower_Body':lower,'Upper_Body_With_Sensor_Fork':upper,**coupons}

def probes():
    return {'board':v.box(-8.9,8.9,v.BOARD_Y,v.BOARD_Y+v.BOARD_T,v.BOARD0,v.BOARD0+21.),
        'solder':v.box(-5.4,5.4,v.BOARD_Y-6.,v.BOARD_Y-.25,v.BOARD0+3.,v.BOARD0+18.),
        'usb':v.box(-5.7,5.7,v.BOARD_Y-.8,v.BOARD_Y+4.8,v.BOARD0+21.3,411.),
        'wire_exit':v.cyl(2.7,375.,387.5).translate((0.,2.,0.))}

def checks(parts,base,tip):
    lo,up=parts['Lower_Body'],parts['Upper_Body_With_Sensor_Fork']
    clear={k:abs((up^p).volume())for k,p in probes().items()}
    assert max(clear.values())<.002,clear
    board=probes()['board'];clip=v.board_release_clip();rigid=up-clip
    pivot=(0.,v.BOARD_Y+v.BOARD_T/2,v.BOARD0+21.)
    pivot_hits=[abs((rigid^board.translate(tuple(-x for x in pivot)).rotate((a,0,0)).translate(pivot)).volume())for a in np.arange(0.,10.01,.5)]
    assert max(pivot_hits)<.002,max(pivot_hits)
    stops={name:abs((up^board.translate(delta)).volume())for name,delta in {'left':(-.4,0,0),'right':(.4,0,0),'up':(0,0,.4),'down':(0,0,-.4),'forward':(0,.5,0)}.items()}
    assert min(stops.values())>.05,stops
    assert abs((lo^up).volume())<.002
    # Remove laterally, with external wiring not installed, before taping.
    route=[abs((up^lo.translate((0,-d,0))).volume())for d in np.arange(0,16.01,.25)]
    assert max(route)<.002,max(route)
    profiles=[]
    for z in [10.,60.,110.,150.,215.,270.,330.,350.]:
        sec=(lo+up).slice(z);points=np.concatenate([np.asarray(p)for p in sec.to_polygons()]);r=np.linalg.norm(points,axis=1)
        expected=envelope(z,base,tip)
        assert max(r)<=expected+.003 and max(r)-min(r)>.35,(z,min(r),max(r),expected)
        profiles.append({'z_mm':z,'maximum_diameter_mm':float(max(r)*2),'core_diameter_mm':float(min(r)*2)})
    assert all(a['maximum_diameter_mm']>b['maximum_diameter_mm']for a,b in zip(profiles,profiles[1:]))
    # Added fork rails are 4 x 3.2 mm; the older long side strut was about
    # 2.9 mm across. Report geometry only, never a calculated load rating.
    return {'base_maximum_diameter_mm':base,'tip_maximum_diameter_mm':tip,
        'lap_overlap_mm':30.,'lap_gap_mm':.2,'lap_insertion_max_overlap_mm3':max(route),
        'sensor_clearance_mm3':clear,'radius_profile':profiles,
        'board_released_pivot_max_overlap_mm3':max(pivot_hits),'board_stop_interference_mm3':stops,
        'fork_rail_section_mm':[4.,3.2],'sensor_tip_integral':True,
        'external_buttons_battery_wires_required':True,'existing_grip_loop_compatible':False,
        'physical_fit_verified':False,'physical_strength_verified':False}

def export(name,solid,out):
    solid=solid.as_original().simplify(.003)
    assert solid.status()==mf.Error.NoError and len(solid.decompose())==1,(name,solid.status(),[p.volume()for p in solid.decompose()])
    bb=solid.bounding_box();shift=(-(bb[0]+bb[3])/2,-(bb[1]+bb[4])/2,-bb[2])
    printed=solid.translate(shift);tri=v.b.canonical_triangles(printed)
    report=v.b.mesh_checks(tri,1)
    assert report['watertight']and report['winding_consistent']and report['every_edge_shared_twice'],(name,report)
    assert max(report['print_size_mm'])<245.,(name,report['print_size_mm'])
    blob=v.b.stl_bytes(tri,name);path=out/(name+'.stl');path.write_bytes(blob)
    t=np.eye(4);t[:3,3]=-np.asarray(shift)
    vertices,indices=np.unique(tri.reshape(-1,3),axis=0,return_inverse=True)
    return {'name':name,'file':path.name,'sha256':hashlib.sha256(blob).hexdigest(),'checks':report,
        'print_to_assembly':t.tolist(),'assembly_vertices':(vertices-np.asarray(shift)).tolist(),
        'assembly_faces':indices.reshape(-1,3).tolist()}

def build(out):
    out.mkdir(parents=True,exist_ok=False);result={'version':'Thin rod study 1','source_tube':SOURCE_TUBE,'length_mm':410.,'variants':{}}
    for key,(base,tip)in VARIANTS.items():
        dest=out/key;dest.mkdir();parts=models(base,tip);report=checks(parts,base,tip)
        records=[export(n,p,dest)for n,p in parts.items()]
        # Reload exported mesh triangles before declaring final fit checks.
        reloaded={}
        for p in records:
            m=trimesh.load_mesh(dest/p['file'],process=True);m.apply_transform(p['print_to_assembly'])
            reloaded[p['name']]=v.b.closed_mesh(m.vertices,m.faces,p['name'])
        checks(reloaded,base,tip)
        result['variants'][key]={'checks':report,'parts':records}
        print(key+' checked and exported',flush=True)
    result['source']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [HERE/'wand_cad.py',HERE.parent/'v20/wand_cad.py',HERE.parent/'lattice-study/wand_cad.py']}
    (out/'manifest.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({k:x['checks']for k,x in result['variants'].items()},indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);build(ap.parse_args().out.resolve())
