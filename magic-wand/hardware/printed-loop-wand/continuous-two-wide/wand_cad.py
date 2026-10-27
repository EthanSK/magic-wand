#!/usr/bin/env python3
"""One-piece upper shaft based on the checked Two wide spirals study.

Ethan's "top two segments" are Lower_Shaft and Upper_Shaft, not the
removable finger loop or the sensor cradle. The old studies stay unchanged.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math
import numpy as np
from manifold3d import Manifold

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'lattice-study'
spec=importlib.util.spec_from_file_location('lattice',PARENT/'wand_cad.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
SCALE=.95

def make():
    c=s.configure('two-wide')
    # Preserve the original complete grip-side socket and its collar exactly.
    original_lower=s.configure('two-wide').lower_shaft()
    # Retain the exact V18 grip bayonet and loop; the last joint is scaled on
    # BOTH sides so the thinner shaft meets its matching removable sensor holder.
    old_radius=c.shaft_radius
    def radius(z,start=c.HANDLE_END):
        fade=max(0.,min(1.,(z-(c.HANDLE_END+19.))/(c.TOP-(c.HANDLE_END+19.))))
        return old_radius(z,start)-(1.-SCALE)*c.JOINT_R*fade
    old_extent=s.extent
    def extent(c_,zone,start):
        return (start+19.,c_.TOP-16.) if zone=='combined' else old_extent(c_,zone,start)
    s.extent=extent
    old_male=c.slim_male_at
    c.shaft_radius=radius
    shrink=np.diag([SCALE,SCALE,1.])
    def scale_xy(part):
        return part.transform(np.column_stack((shrink,np.zeros(3))))
    # The board, pockets, spring, solder and USB geometry above the neck are
    # unchanged. A narrow solid transition reconnects the scaled bayonet.
    head=s.open_head(c)
    neck=head^c.cyl(40.,c.TOP,c.TOP+17.)
    frame=head-c.cyl(40.,c.TOP-.1,c.TOP+17.)
    narrow=scale_xy(neck)-c.cyl(c.BORE/2,c.TOP-1,c.TOP+19.)
    bridge=(c.cyl(c.JOINT_R*SCALE,c.TOP+15.,c.TOP+18.,c.JOINT_R*SCALE+1.)-c.cyl(c.BORE/2,c.TOP+14.,c.TOP+19.))
    head=c.union([narrow,frame,bridge]).simplify(.0001)
    # One continuous shell and criss-cross lattice: no middle bayonet or collar.
    shaft=(c.union([c.body(c.HANDLE_END,c.TOP-.2,c.HANDLE_END),scale_xy(old_male(c.TOP))])
           -c.union([c.female_at(c.HANDLE_END),c.shaft_cavity(c.HANDLE_END,c.TOP,c.HANDLE_END),
                     c.cyl(c.BORE/2,c.HANDLE_END-1,c.TOP+16.),c.body_slots('combined')]))
    z0,z1=c.HANDLE_END+18.,c.TOP-5.;parts=[]
    for a in np.arange(z0,z1,2.):
        d=min(float(a)+2.01,z1)
        for angle in (0.,90.,180.,270.):
            part=Manifold.batch_hull([c.rr_section(float(a),radius,c.SPINE_DEPTH),c.rr_section(d,radius,c.SPINE_DEPTH)])
            parts.append(c.local(part,angle,0.))
    # The configured two-wide backing spans the entire combined lattice.
    shaft+=c.union(parts)+c.axial_rails('combined')
    join=c.HANDLE_END+19.
    shaft=(shaft-c.cyl(40.,c.HANDLE_END-1.,join-.05))+(original_lower^c.cyl(40.,c.HANDLE_END-1.,join))
    return c,shaft,head

def validate(c,shaft,head):
    a=c.HANDLE_END;top=c.TOP;mid=c.MID
    radii=[c.shaft_radius(z) for z in np.arange(a,top+.01,1.)]
    assert all(x>=y-1e-8 for x,y in zip(radii,radii[1:])), 'Shaft widens towards the tip'
    assert radii[-1]<s.load_base('baseline').shaft_radius(top)-.4
    assert len(shaft.decompose())==len(head.decompose())==1
    bore=c.cyl(4.95,a-1,top+16.)
    wire={'shaft':abs((shaft^bore).volume()),'head':abs((head^c.cyl(4.95,top-1,top+16.)).volume())}
    assert max(wire.values())<.001,wire
    # Both old handed grip connectors and their detachable loop stay byte-identical.
    lower=s.reference_part(c,'Lower_Shaft');region=c.cyl(40.,a-1,a+18.9)
    joint=s.solid_difference(lower^region,shaft^region);assert joint<.03,('grip joint',joint)
    region=c.box(-20,20,-20,20,top-1,top+16.);male=shaft^region;female=head^region
    insertion={str(d):abs((c.b.spin(male,-38).translate((0,0,-d))^female).volume()) for d in [14,10,5,1,0]}
    rotation={str(t):abs((c.b.spin(male,t)^female).volume()) for t in [-38,-30,-20,-10,0,5]}
    pull=abs((male.translate((0,0,-2.))^female).volume())
    assert max(insertion.values())<.001,(insertion,rotation,pull)
    assert all(rotation[str(t)]<1.5 for t in [-38,-30,-20,-10,0]) and rotation['5']>rotation['0']+1 and pull>1.,(rotation,pull)
    probes={'board':c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,c.BOARD0+21.),'solder':c.box(-5.4,5.4,c.BOARD_Y-6.,c.BOARD_Y-.25,c.BOARD0+3.,c.BOARD0+18.),'usb':c.box(-5.7,5.7,c.BOARD_Y-.8,c.BOARD_Y+4.8,c.BOARD0+21.3,411.),'wire':c.cyl(2.7,375.,387.5).translate((0.,2.,0.))}
    clear={k:abs((head^v).volume()) for k,v in probes.items()};assert max(clear.values())<.001,clear
    # A real opening at the former middle seam, sampled on the outside skin.
    sec=shaft.slice(mid);r=c.shaft_radius(mid);opens=0
    for angle in range(0,360,5):
        q=s.CrossSection.square((.12,.12),True).translate(((r-.3)*math.sin(math.radians(angle)),(r-.3)*math.cos(math.radians(angle))))
        opens+=(sec^q).area()<.0001
    assert opens>=8,('Former seam is not visibly open',opens)
    return {'tip_radius_mm':radii[-1],'original_tip_radius_mm':s.load_base('reference').shaft_radius(top),'shaft_length_with_connector_mm':shaft.bounding_box()[5]-shaft.bounding_box()[2],
            'radius_monotonic':True,'old_seam_open_samples':int(opens),'seam_samples':72,'grip_joint_difference_mm3':joint,'wire_clearance_mm3':wire,'head_clearance_mm3':clear,'head_insertion_mm3':insertion,'head_turn_mm3':rotation,'head_pull_stop_mm3':pull,'physical_fit_verified':False,'physical_strength_verified':False}

def main(out):
    out.mkdir(parents=True,exist_ok=False);c,shaft,head=make()
    checks=validate(c,shaft,head)
    pieces=[s.export_part(c,'Continuous_Shaft',shaft,out),s.export_part(c,'Sense_Open_Cradle',head,out)]
    # Reference, do not duplicate or alter, the established two-wide grip/loop.
    old=json.loads((PARENT/'exports/manifest.json').read_text());v=old['variants']['two-wide']
    shared=[p for p in v['parts'] if p['name'] in ('Handle_Left','Handle_Right','Removable_Finger_Loop')]
    shared += [p for p in old['shared_parts'] if p['name'] in ('Battery_Twist_Cap','Battery_Sled','Choc_Recessed_Plate')]
    for p in shared:
        p['file']=('../../lattice-study/exports/two-wide/'+p['file']) if p in v['parts'] else p['file']
    result={'version':'Two wide spirals - continuous shaft','base':'Two wide spirals','head_joint_scale':SCALE,'checks':checks,'parts':pieces,'shared_parts':shared,
            'source':{str(p):hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in ['wand_cad.py','../lattice-study/wand_cad.py','../lattice-study/variations.json','../v18/wand_cad.py']}}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
