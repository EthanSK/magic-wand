#!/usr/bin/env python3
"""Sharper-tapered hollow tube, retaining the tip-mounted XIAO and V20 grip.

Ethan's "Shard" shape means the tube narrows towards the end. The sensor
holder can be wider than the tube; the detachable finger loop stays at the butt.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math
import numpy as np
from manifold3d import Manifold
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'lattice-study'
spec=importlib.util.spec_from_file_location('lattice_shard',PARENT/'wand_cad.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
s.BASE=HERE.parent/'v20'
TIP_RADIUS=6.2

def make():
    c=s.configure('two-wide'); reference=s.configure('two-wide').lower_shaft()
    start,top=c.HANDLE_END,c.TOP; old_radius=c.shaft_radius; original_extent=s.extent
    def radius(z,start=start):
        fade=max(0.,min(1.,(z-(c.HANDLE_END+19.))/(top-(c.HANDLE_END+19.))))
        return old_radius(z,start)-(old_radius(top,start)-TIP_RADIUS)*fade
    c.shaft_radius=radius
    s.extent=lambda c_,zone,start_: (start_+19.,top-5.) if zone=='combined' else original_extent(c_,zone,start_)
    shaft=c.body(start,top,start)-c.union([c.female_at(start),c.shaft_cavity(start,top,start),c.cyl(c.BORE/2,start-1,top+1),c.body_slots('combined')])
    parts=[]
    for a in np.arange(start+18.,top-5.,2.):
        d=min(float(a)+2.01,top-5.)
        for angle in (0.,90.,180.,270.):
            part=Manifold.batch_hull([c.rr_section(float(a),radius,c.SPINE_DEPTH),c.rr_section(d,radius,c.SPINE_DEPTH)])
            parts.append(c.local(part,angle,0.))
    shaft+=c.union(parts)+c.axial_rails('combined')
    join=start+19.
    shaft=(shaft-c.cyl(40.,start-1.,join-.05))+(reference^c.cyl(40.,start-1.,join))
    shaft-=c.cyl(c.BORE/2,start-1,top+1)
    # The last 9 mm is hidden inside the holder. Round it for a repeatable fit.
    shaft-=c.cyl(40.,343.,353.)-c.cyl(6.35,343.,353.)
    def tabs(z0,z1,angle):
        return c.union([c.local(c.box(-1.,1.,6.05,8.1,z0,z1),angle+a,0.) for a in (0.,180.)])
    shaft=(shaft+tabs(347.,349.,0.)).simplify(.001)
    # The XIAO board remains at the tip. This wider sleeve is part of its holder,
    # not a collar widening the visible tube. Two tabs enter then turn 40 degrees.
    frame=s.open_head(c)-c.cyl(40.,top-.1,top+17.)
    cavity=c.cyl(6.6,342.5,352.25)+c.cyl(5.2,352.2,371.)
    def slots(z0,z1,angle):
        return c.union([c.local(c.box(-1.3,1.3,5.9,8.45,z0,z1),angle+a,0.) for a in (0.,180.)])
    cavity+=slots(342.5,349.3,-40.)
    # One smooth sector avoids overlapping tiny rectangular steps in the channel.
    for side in (0.,180.):
        points=[(0.,0.)]+[(10*math.sin(math.radians(a+side)),10*math.cos(math.radians(a+side))) for a in range(10,-51,-2)]
        wedge=Manifold.extrude(s.CrossSection([points]),2.6).translate((0,0,346.7))
        cavity+=wedge^(c.cyl(8.45,346.7,349.3)-c.cyl(5.9,346.7,349.3))
    sleeve=(c.cyl(9.2,343.,352.4)+c.cyl(9.2,352.4,369.,7.)+c.cyl(7.,369.,370.))-cavity
    bridge=c.box(3.8,11.,-7.4,-5.5,368.8,375.)+c.box(-11.,-3.8,-7.4,-5.5,368.8,375.)
    return c,shaft,(frame+sleeve+bridge).simplify(.001)

def validate(c,shaft,head):
    start,top=c.HANDLE_END,c.TOP;radii=[c.shaft_radius(z) for z in np.arange(start,top+.01,1.)]
    assert all(x>=y-1e-8 for x,y in zip(radii,radii[1:])) and abs(radii[-1]-TIP_RADIUS)<1e-6
    assert len(shaft.decompose())==len(head.decompose())==1
    bores={'shaft':abs((shaft^c.cyl(5.,start-1,top+1)).volume()),'head':abs((head^c.cyl(5.,top,370.)).volume())}
    assert max(bores.values())<.001,bores
    lower=s.reference_part(c,'Lower_Shaft');zone=c.cyl(40.,start-1,start+18.9)
    joint=s.solid_difference(lower^zone,shaft^zone);assert joint<.05,joint
    zone=c.cyl(40.,342.,371.);male=shaft^zone;female=head^zone
    insert={str(d):abs((c.b.spin(male,-40).translate((0,0,-d))^female).volume()) for d in [14,10,8,6,4,2,1,0]}
    turn={str(t):abs((c.b.spin(male,t)^female).volume()) for t in [-40,-30,-20,-10,0,5]}
    pull=abs((male.translate((0,0,-2.))^female).volume())
    assert max(insert.values())<.001 and max(turn[str(t)] for t in [-40,-30,-20,-10,0])<.001 and turn['5']>1 and pull>1,(insert,turn,pull)
    probes={'board':c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,c.BOARD0+21.),'solder':c.box(-5.4,5.4,c.BOARD_Y-6.,c.BOARD_Y-.25,c.BOARD0+3.,c.BOARD0+18.),'usb':c.box(-5.7,5.7,c.BOARD_Y-.8,c.BOARD_Y+4.8,c.BOARD0+21.3,411.),'wire':c.cyl(2.7,375.,387.5).translate((0.,2.,0.))}
    clear={k:abs((head^v).volume()) for k,v in probes.items()};assert max(clear.values())<.001,clear
    sec=shaft.slice(c.MID);r=c.shaft_radius(c.MID);opens=0
    for angle in range(0,360,5):
        q=s.CrossSection.square((.12,.12),True).translate(((r-.3)*math.sin(math.radians(angle)),(r-.3)*math.cos(math.radians(angle))))
        opens+=(sec^q).area()<.0001
    assert opens>=8
    return {'base_radius_mm':radii[0],'tip_radius_mm':radii[-1],'shaft_length_mm':shaft.bounding_box()[5]-shaft.bounding_box()[2], 'radius_monotonic':True,'old_seam_open_samples':int(opens),'seam_samples':72,'grip_joint_difference_mm3':joint,'wire_clearance_mm3':bores,'head_clearance_mm3':clear,'head_insertion_mm3':insert,'head_turn_mm3':turn,'head_pull_stop_mm3':pull,'physical_fit_verified':False,'physical_strength_verified':False}

def main(out):
    out.mkdir(parents=True,exist_ok=False);c,shaft,head=make();checks=validate(c,shaft,head)
    parts=[s.export_part(c,'Continuous_Shaft',shaft,out),s.export_part(c,'Sense_Open_Cradle',head,out)]
    old=json.loads((HERE.parent/'v20/exports/manifest.json').read_text());selected={'Handle_Left','Handle_Right','Removable_Finger_Loop','Battery_Twist_Cap','Battery_Sled','Choc_Recessed_Plate'}
    shared=[dict({k:v for k,v in p.items() if k not in ('assembly_vertices','assembly_faces')},file='../../v20/exports/'+p['file']) for p in old['parts'] if p['name'] in selected]
    files=['wand_cad.py','../lattice-study/wand_cad.py','../lattice-study/variations.json','../v20/wand_cad.py','../v20/design-principles.json']
    result={'version':'Two wide spirals - pointed tube V20','base':'V20','checks':checks,'parts':parts,'shared_parts':shared,'source':{str(p):hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in files}}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
