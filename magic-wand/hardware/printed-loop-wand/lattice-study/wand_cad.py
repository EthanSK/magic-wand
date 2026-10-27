#!/usr/bin/env python3
"""Separate lightweight studies composed from frozen V18 mechanisms.

Ethan's new "wireframe net" request explicitly explores open lattice alongside,
not in place of, the earlier continuous-shell design. No hardware fit or load
rating follows from these CAD checks. Edit variations.json and regenerate.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, struct, gc
from functools import lru_cache
from pathlib import Path
import numpy as np
import manifold3d as mf
from manifold3d import Manifold, CrossSection

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'v18'
SPECS = json.loads((HERE/'variations.json').read_text())
CHANGED = ['Handle_Left', 'Handle_Right', 'Lower_Shaft', 'Upper_Shaft', 'Removable_Finger_Loop']
SHARED = ['Sense_Head_Base', 'Sense_Sliding_Cover', 'Battery_Twist_Cap', 'Battery_Sled', 'Choc_Recessed_Plate']
BASE_REPORT = json.loads((BASE/'exports/manifest.json').read_text())

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def load_base(key):
    sp=importlib.util.spec_from_file_location('lightweight_'+key, BASE/'wand_cad.py')
    c=importlib.util.module_from_spec(sp); sp.loader.exec_module(c)
    return c

@lru_cache(None)
def reference_part(c, name):
    # Use canonical full-precision solids for Boolean composition. The viewer's
    # rounded vertex arrays create slivers when joined at a coplanar boundary.
    if not hasattr(c,'_frozen'):
        c._frozen=load_base('frozen_'+str(id(c)))
    q=c._frozen
    return {'Handle_Left':lambda:q.handle_left(), 'Handle_Right':lambda:q.handle_left(True),
            'Lower_Shaft':q.lower_shaft,'Upper_Shaft':q.upper_shaft,
            'Removable_Finger_Loop':q.removable_loop}[name]()

def extent(c, zone, start):
    # Solid collars and all bayonet mating surfaces retain the exact V18 solid.
    return (16.,146.) if zone=='grip' else (start+19.,c.MID-16.) if zone=='lower' else (c.MID+19.,c.TOP-16.)

def hardware_guard(c):
    parts=[]
    # Protect both handed arrangements with the same load-spreading pads.
    for _,a,z in c.HAND_BUTTONS:
        for angle in {a,-a}:
            parts.append(c.local(c.box(-12.,12.,0.,35.,-15.,15.),angle,z))
    for z in c.LOOP_MOUNTS:
        parts.append(c.box(-12.,12.,-35.,0.,z-15.,z+15.))
    # Battery rails and their shell ties survive even in the net study.
    parts += [c.box(9.7,17.,-3.,3.,16.,56.),c.box(-17.,-9.7,-3.,3.,16.,56.)]
    return c.union(parts)

def ribbon(c, zone, start, phase, strand, width):
    """Native short convex lofts, rather than a folded nonlinear mesh warp."""
    z0,z1=extent(c,zone,start); pieces=[]
    for a in np.arange(z0,z1,1.5):
        d=min(float(a)+1.501,z1); verts=[]
        for z in (float(a),d):
            rad=c.radius(z) if zone=='grip' else c.shaft_radius(z,start)
            theta=float(c.b.rib_angle(z,strand))+phase
            half=math.degrees((width(z) if callable(width) else width)/(2*rad))
            verts += [(0.,0.,z)] + [(40*math.sin(math.radians(t)),40*math.cos(math.radians(t)),z)
                                    for t in (theta-half,theta+half)]
        pieces.append(Manifold.hull_points(verts))
    return c.union(pieces)

def configure(key):
    spec=SPECS['variants'][key]; c=load_base(key); c.study_spec=spec
    original_slots=c.body_slots; original_rails=c.axial_rails
    # Keep V18's proven connection rails; lightening removes the spans between
    # them. Do not thin the load path under a recessed lock or socket.
    # The loop's exterior AND skin get thinner. Solid mounting roots are retained.
    c.LOOP_WIDTH=spec['loop_width_mm']; c.LOOP_RADIUS=spec['loop_radius_mm'];c.LOOP_WALL=spec['loop_wall_mm']
    guard=hardware_guard(c)
    def taper(z):
        # Ethan's 'less material towards the tip': wide bands stay full near
        # the hand and taper through the shaft. Original four studies stay exact.
        return 1.-(1.-spec.get('tip_band_scale',1.))*max(0.,min(1.,(z-c.HANDLE_END)/(c.TOP-c.HANDLE_END)))
    if spec['kind']=='net':
        @lru_cache(None)
        def slots(zone,start=c.HANDLE_END):
            z0,z1=extent(c,zone,start)
            keep=[ribbon(c,zone,start,360*k/spec['strands'],strand,
                         (lambda z:spec['main_band_mm']*taper(z)) if k==0 and strand in spec.get('wide_strands',[]) else spec['band_mm'])
                  for k in range(spec['strands']) for strand in (0,1)]
            # Four continuous axial paths connect both collars. Depth is added
            # after cavity subtraction by V18's canonical rail generator.
            for angle in (0.,90.,180.,270.):
                keep.append(c.local(c.box(-c.SPINE_WIDTH/2,c.SPINE_WIDTH/2,0.,40.,z0-.1,z1+.1),angle,0.))
            eligible=c.cyl(40.,z0,z1)-(guard if zone=='grip' else Manifold())
            return (eligible-c.union(keep))+(original_slots(zone,start)-eligible)
        c.body_slots=slots
        if spec.get('main_depth_mm'):
            @lru_cache(None)
            def reinforced_rails(zone,start=c.HANDLE_END):
                z0,z1=extent(c,zone,start)
                radial=lambda z:c.radius(z) if zone=='grip' else c.shaft_radius(z,start)
                # Add backing inside the selected wide strips after hollowing.
                # Keep a 0.15 mm margin beyond the original 10.4 mm wire route.
                depth=lambda z:spec.get('tip_depth_mm',spec['main_depth_mm'])+(spec['main_depth_mm']-spec.get('tip_depth_mm',spec['main_depth_mm']))*max(0.,min(1.,(c.TOP-z)/(c.TOP-c.HANDLE_END)))
                shell=c.cyl(radial(z0)-.8,z0,z1,radial(z1)-.8)-c.cyl(max(5.35,radial(z0)-depth(z0)),z0,z1,max(5.35,radial(z1)-depth(z1)))
                wide=c.union([ribbon(c,zone,start,0.,strand,lambda z:spec['main_band_mm']*taper(z)) for strand in spec['wide_strands']])
                backing=shell^wide
                if zone=='grip':backing-=guard
                return original_rails(zone,start)+backing
            c.axial_rails=reinforced_rails
    else:
        # A supporting-shell option retains V18's full spiral strips, but opens
        # longer curved cells. Hardware-region holes remain exactly V18.
        frozen=load_base('leaf_reference');c.WINDOW_HEIGHT=36.;c.WINDOW_PITCH=38.
        @lru_cache(None)
        def slots(zone,start=c.HANDLE_END):
            z0,z1=extent(c,zone,start)
            eligible=c.cyl(40.,z0,z1)-(guard if zone=='grip' else Manifold())
            return (original_slots(zone,start)^eligible)+(frozen.body_slots(zone,start)-eligible)
        c.body_slots=slots
    c.handle_left=lru_cache(None)(c.handle_left)
    return c

def protected_region(c,name):
    if name.startswith('Handle_'):
        return hardware_guard(c)+c.cyl(40.,0.,16.)+c.cyl(40.,146.,178.)
    if name in ('Lower_Shaft','Upper_Shaft'):
        z0,z1=(c.HANDLE_END,c.MID) if name=='Lower_Shaft' else (c.MID,c.TOP)
        return c.cyl(40.,z0-1,z0+19.)+c.cyl(40.,z1-16.,z1+17.)
    # Preserve each entire direct seating arm. Clipping at a tangent to the
    # slimmer tube can strand a real sliver of the original curved root.
    roots=c.union([c.box(-10,10,-35.,0.,z-8.,z+8.) for z in c.LOOP_MOUNTS])
    return roots+c.loop_release_latch()

def models_for(c):
    models={'Handle_Left':c.handle_left(), 'Handle_Right':c.handle_left(True),
            'Lower_Shaft':c.lower_shaft(), 'Upper_Shaft':c.upper_shaft(),
            'Removable_Finger_Loop':c.removable_loop()}
    # Compose exact frozen mounting solids into each study. Preserve the entire
    # load-spreading root, not just a tiny nominal empty clearance probe.
    # Add the canonical solid roots to the slimmer loop without splicing nearly
    # coincident curved tube skins. Stem/shaft interfaces are protected upstream.
    models['Removable_Finger_Loop'] += reference_part(c,'Removable_Finger_Loop')^protected_region(c,'Removable_Finger_Loop')
    if c.study_spec.get('open_head'):models['Sense_Open_Cradle']=open_head(c)
    return models

def open_head(c):
    # Ethan's 'not so bulky' tip: an open holder, not the decorative diamond
    # shell. The lower bayonet, PCB corner pockets and bridge spring are reused.
    neck=c.head_base()^c.cyl(30.,c.TOP,c.TOP+17.)
    guides=c.board_corner_guides()^c.box(-11.2,11.2,-7.4,-2.1,374.5,399.)
    clip=c.board_release_clip()
    def rod(points,radii):
        spheres=[Manifold.sphere(r,16).translate(p) for p,r in zip(points,radii)]
        return c.union([Manifold.batch_hull([a,b]) for a,b in zip(spheres,spheres[1:])])
    arms=[];seats=[]
    for sign in (-1,1):
        pts=[(sign*8.,-4.8,367.),(sign*13.2,-6.3,374.8),(sign*10.6,-6.3,382.),(sign*10.6,-6.3,395.),(sign*10.,-4.,399.),(sign*9.,0.,403.),(sign*7.4,3.4,409.)]
        arms.append(rod(pts,[1.9,1.65,1.5,1.45,1.3,1.1,1.]))
        # Back supports meet short PCB ends/corners. Leave long solder pads open.
        for z in (c.BOARD0+1.,c.BOARD0+16.):
            seats.append(Manifold.batch_hull([c.box(sign*6.3-.5,sign*6.3+.5,c.BOARD_Y-.8,c.BOARD_Y,z-.45,z+.45),c.box(sign*10.6-.6,sign*10.6+.6,-7.4,-5.5,z-.9,z+.9)]))
        seats.append(c.box(sign*10.4-1.2,sign*10.4+1.2,-7.4,-5.5,375.6,398.4))
        upper=c.box(6.25,11.5,-7.4,-5.5,397.2,398.2)+c.box(6.25,7.65,-7.4,-2.1,397.2,398.2)
        seats.append(upper if sign>0 else upper.mirror((1,0,0)))
    frame=c.union([guides,clip]+arms+seats)^c.box(-30,30,-30,30,369.,411.)
    return (neck+frame).simplify(.0001)

def solid_difference(a,b): return abs((a-b).volume())+abs((b-a).volume())

def checks(c, models, interface_tolerance=.03):
    out={'physical_strength_verified':False,'interfaces':{},'wire_clearance':{},'loops':{},'gauge_check':'Run verify_models.py against exported meshes'}
    guard=hardware_guard(c)
    for hand in ('Left','Right'):
        name='Handle_'+hand;ref=reference_part(c,name);part=models[name]
        # All hardware in these protected regions must be byte-geometry equal,
        # not merely clear of the mechanism at its nominal pose.
        protected=guard+c.cyl(40.,0.,16.)+c.cyl(40.,146.,178.)
        value=solid_difference(ref^protected,part^protected)
        out['interfaces'][name]=value
        assert value<interface_tolerance,(name,'changed protected hardware',value)
        q=c.cyl(4.95,61.,177.)
        out['wire_clearance'][name]=abs((part^q).volume());assert out['wire_clearance'][name]<.001
    for name,z0,z1 in [('Lower_Shaft',c.HANDLE_END,c.MID),('Upper_Shaft',c.MID,c.TOP)]:
        ref=reference_part(c,name);part=models[name]
        protected=c.cyl(40.,z0-1,z0+19.)+c.cyl(40.,z1-16.,z1+17.)
        value=solid_difference(ref^protected,part^protected)
        out['interfaces'][name]=value;assert value<interface_tolerance,(name,'changed bayonet',value)
        out['wire_clearance'][name]=abs((part^c.cyl(4.95,z0-1,z1+16.)).volume())
        assert out['wire_clearance'][name]<.001
    loop=models['Removable_Finger_Loop'];original_loop=reference_part(c,'Removable_Finger_Loop')
    # Keep the exact stud, cam, spring and blended lower root. A slimmer bar is
    # allowed outside these local interface zones.
    protected=protected_region(c,'Removable_Finger_Loop')
    out['interfaces']['loop_roots_lost_mm3']=abs(((original_loop^protected)-loop).volume())
    out['interfaces']['loop_root_extra_reinforcement_mm3']=abs(((loop^protected)-original_loop).volume())
    assert out['interfaces']['loop_roots_lost_mm3']<interface_tolerance,('loop root material lost',out['interfaces'])
    latch=c.loop_release_latch();released=(loop-latch)+c.loop_latch_deflected(c.LOOP_RELEASE_DEFLECTION)
    for hand in ('Left','Right'):
        stem=models['Handle_'+hand]
        # Recheck the full V18 lift/turn route; thinning cannot introduce a snag.
        turn=[abs((stem^c.loop_pose(released,float(a))).volume()) for a in np.arange(0.,c.LOOP_TWIST+.01,1.)]
        slide=[abs((stem^c.loop_pose(released,c.LOOP_TWIST,float(d))).volume()) for d in np.arange(0.,4.01,.5)]
        hard=[(stem^released.translate(p)).volume() for p in [(0,-1,0),(0,0,.6),(0,0,-.6)]]
        out['loops'][hand]={'max_turn_overlap_mm3':max(turn),'max_slide_overlap_mm3':max(slide),'hard_stops_mm3':hard}
        assert max(turn+slide)<.001 and min(hard)>1.,(hand,out['loops'][hand])
    # Detect floating starts at the actual 0.2 mm layer height. Geometric
    # connectivity alone can hide an unprintable diagonal member.
    out['floating_layer_starts']={}
    for name,z0,z1 in [('Lower_Shaft',c.HANDLE_END+19,c.MID-16),('Upper_Shaft',c.MID+19,c.TOP-16)]:
        part=models[name];islands=[]
        for z in np.arange(z0+.2,z1,.2):
            prev=part.slice(float(z-.2)).offset(.24)
            for p in part.slice(float(z)).decompose():
                if p.area()>.01 and (p^prev).area()<.001:islands.append(round(float(z),3))
        out['floating_layer_starts'][name]=islands
        assert not islands,(name,'floating starts',islands[:10])
    if 'Sense_Open_Cradle' in models:
        head=models['Sense_Open_Cradle'];ref=c.head_base()
        probes={'board':c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,c.BOARD0+21.),'solder':c.box(-5.4,5.4,c.BOARD_Y-6.,c.BOARD_Y-.25,c.BOARD0+3.,c.BOARD0+18.),'usb':c.box(-5.7,5.7,c.BOARD_Y-.8,c.BOARD_Y+4.8,c.BOARD0+21.3,411.),'wire':c.cyl(2.7,375.,387.5).translate((0.,2.,0.))}
        out['open_head']={'clearances_mm3':{n:abs((head^q).volume()) for n,q in probes.items()},'neck_difference_mm3':solid_difference(ref^c.cyl(30,c.TOP,c.TOP+16.5),head^c.cyl(30,c.TOP,c.TOP+16.5)),'clip_material_lost_mm3':abs((c.board_release_clip()-head).volume()),'bounds_mm':list(head.bounding_box()),'physical_retention_verified':False}
        pockets=c.union([c.box(-10.5,10.5,-6.3,-2.1,a,b) for a,b in [(375.05,375.8),(376.15,377.35),(395.65,398.2)]])
        out['open_head']['corner_pocket_material_lost_mm3']=abs(((c.board_corner_guides()^pockets)-head).volume())
        assert out['open_head']['corner_pocket_material_lost_mm3']<interface_tolerance,out['open_head']
        assert max(out['open_head']['clearances_mm3'].values())<interface_tolerance,out['open_head']
        assert out['open_head']['neck_difference_mm3']<interface_tolerance and out['open_head']['clip_material_lost_mm3']<interface_tolerance,out['open_head']
    return out

def export_part(c,name,m,dest):
    # Native hull unions can leave zero-volume coincident sheets at a protected
    # boundary. Remove only numerically empty components, never a printable
    # detached member. Any nonzero disconnected part still fails below.
    m=m.as_original()
    empty_volume=0.
    for _ in range(2):
        parts=m.decompose();empty=[p for p in parts if abs(p.volume())<1e-6]
        empty_volume+=sum(abs(p.volume()) for p in empty)
        assert empty_volume<1e-5,(name,'nonempty disconnected pieces')
        m=c.union([p for p in parts if abs(p.volume())>=1e-6]).simplify(.001)
    rot=(0,-90,0) if name=='Removable_Finger_Loop' else (90,0,0) if name=='Sense_Open_Cradle' else (0,0,0)
    p=m.rotate(rot); bb=p.bounding_box(); shift=(-(bb[0]+bb[3])/2,-(bb[1]+bb[4])/2,-bb[2]);p=p.translate(shift)
    tri=c.b.canonical_triangles(p);report=c.b.mesh_checks(tri,len(m.decompose()))
    assert m.status()==mf.Error.NoError and report['watertight'] and report['winding_consistent'] and report['every_edge_shared_twice'] and report['bodies']==1,(name,report)
    assert max(report['print_size_mm'])<245.,(name,'bed fit')
    blob=c.b.stl_bytes(tri,name); path=dest/(name+'.stl');path.write_bytes(blob)
    r=c.b.rotation(rot);t=np.eye(4);t[:3,:3]=r.T;t[:3,3]=-r.T@np.array(shift)
    return {'name':name,'file':name+'.stl','sha256':sha(path),'checks':report,'zero_volume_sheet_cleanup_mm3':empty_volume,'print_to_assembly':t.tolist()}

def opening_fraction(c, models):
    """Sample true empty circumferential skin; not void volume inside the tube."""
    out={}
    for zone,name in [('grip','Handle_Left'),('lower','Lower_Shaft'),('upper','Upper_Shaft')]:
        z0,z1=extent(c,zone,c.HANDLE_END);part=models[name];empty=total=0
        for z in np.arange(z0+2,z1-1,2.):
            r=c.radius(z) if zone=='grip' else c.shaft_radius(z)
            section=part.slice(float(z))
            for a in range(0,360,5):
                x=(r-.3)*math.sin(math.radians(a));y=(r-.3)*math.cos(math.radians(a))
                q=CrossSection.square((.12,.12),True).translate((x,y))
                total+=1;empty+=int((q^section).area()<.0001)
        out[zone]={'sampled_open_fraction':round(empty/total,4),'samples':total}
    return out

def build(out, selected=None):
    out.mkdir(parents=True,exist_ok=False)
    result={'version':'Lattice studies on Print V18','baseline':'Print V18 / S410-R14',
            'physical_fit_verified':False,'physical_strength_verified':False,'variants':{},
            'source':{str(p.relative_to(HERE)):sha(p) for p in [HERE/'wand_cad.py',HERE/'variations.json']},
            'baseline_source':{'../v18/wand_cad.py':sha(BASE/'wand_cad.py'),'../v18/exports/manifest.json':sha(BASE/'exports/manifest.json')}}
    for key,spec in SPECS['variants'].items():
        if selected and selected!=key:continue
        print('Building '+key,flush=True);c=configure(key);models=models_for(c);folder=out/key;folder.mkdir()
        records=[export_part(c,n,m,folder) for n,m in models.items()]
        report=checks(c,models);report['skin_open_samples']=opening_fraction(c,models)
        record=dict(spec,parts=records,checks=report)
        record['omit_shared_parts']=['Sense_Head_Base','Sense_Sliding_Cover'] if spec.get('open_head') else []
        record['loop_section_mm']=[c.LOOP_WIDTH,2*c.LOOP_RADIUS];record['loop_skin_mm']=c.LOOP_WALL
        record['loop_section_reduction_percent']=round(100*(1-(c.LOOP_WIDTH*2*c.LOOP_RADIUS)/(18*12)),2)
        result['variants'][key]=record
        print(json.dumps({'variant':key,'parts':{p['name']:p['checks']['volume_mm3'] for p in records},'checks':report}),flush=True)
        del c,models;gc.collect()
    result['shared_parts']=[dict(name=p['name'],file='../../v18/exports/'+p['file'],sha256=p['sha256'],checks=p['checks'],print_to_assembly=p['print_to_assembly']) for p in BASE_REPORT['parts'] if p['name'] in SHARED]
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--variant',choices=list(SPECS['variants']));a=ap.parse_args();build(a.out,a.variant)
