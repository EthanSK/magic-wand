#!/usr/bin/env python3
"""Print V2: 340 mm mirrored mug wand with a faceted diamond head (CAD revision V17). Millimetres. Mechanical review prototype with a clipped board cradle and clear thumb mount.
Install requirements.txt into a virtual environment; use --check or an unused --out directory.
The old model and reference geometry remain unchanged. Physical fit is unverified.
"""
from __future__ import annotations
import argparse, importlib.util, json, math, struct, sys, hashlib, zipfile
from pathlib import Path
import numpy as np
import manifold3d as mf
from manifold3d import Manifold, CrossSection
HERE=Path(__file__).resolve().parent
SUPPORT=HERE
spec=importlib.util.spec_from_file_location('wand_reference',SUPPORT/'reference/wand_cad.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
box,cyl,union=b.box,b.cyl_z,b.union
BORE=10.4; MID=222.; TOP=282.; END=340.; BOARD0=306.; BOARD_Y=-5.5
BOARD_T=1.6; BOARD_SLOT=1.9; BOARD_SIDE_GAP=.2
# Provisional battery envelope; the actual battery must be measured before printing.
BATTERY={'verified_product':False,'nominal_envelope_mm':[20.0,6.0,40.0],
         'chamber_mm':[22.6,9.0,49.0], 'note':'Provisional cell envelope: measure the actual battery and use removable spacers before printing the handle.'}
HAND_BUTTONS=[('thumb',90.,117.),('index',-35.,91.),('middle',-35.,65.)]
R_MID=8.3;FLAT_MID=7.5; PEG=16.; GAP=.15

def rounded_rect(w,h,r):
 return CrossSection.square((w-2*r,h-2*r),True).offset(r,mf.JoinType.Round)

def rr(w,h,r,z0,z1):return Manifold.extrude(rounded_rect(w,h,r),z1-z0).translate((0,0,z0))

def bevel_poly(w,h,c):
 x,y=w/2,h/2
 return [(-x+c,-y),(x-c,-y),(x,-y+c),(x,y-c),(x-c,y),(-x+c,y),(-x,y-c),(-x,-y+c)]

def poly_prism(p,z0,z1):return Manifold.extrude(CrossSection([p]),z1-z0).translate((0,0,z0))

def radius(z):
 if z<=140:return b.taper_radius(z)
 r0=b.taper_radius(140)
 if z<MID:return r0+(10.8-r0)*(z-140)/(MID-140)
 if z<245:return 10.8
 return 10.8+(10.2-10.8)*(z-245)/(TOP-245)

def body(z0,z1):
 n=120; zs=np.linspace(z0,z1,max(2,int(math.ceil(z1-z0))+1));theta=np.arange(n)*360/n
 verts=[]
 for z in zs:
  rib=b.rib_height(np.full(n,z),theta,True)*min(1.,max(0.,(TOP-z)/18.))
  r=radius(z)+rib
  verts.extend(zip((r*np.sin(np.radians(theta))).tolist(),(r*np.cos(np.radians(theta))).tolist(),[float(z)]*n))
 c0=len(verts);c1=c0+1;verts.extend([(0,0,z0),(0,0,z1)]);tri=[]
 for i in range(len(zs)-1):
  for j in range(n):
   j1=(j+1)%n;a=i*n;d=(i+1)*n
   tri.extend([(a+j,a+j1,d+j1),(a+j,d+j1,d+j)])
 for j in range(n):tri.extend([(c0,(j+1)%n,j),(c1,(len(zs)-1)*n+j,(len(zs)-1)*n+(j+1)%n)])
 return b.closed_mesh(verts,tri,'short tapered body')

def male_at(z):return b.mirror_joint(b.spigot_end()).translate((0,0,z-140.))
def female_at(z):return b.tapered_socket(b.J['cam']['crest_interference']).translate((0,0,z-140.))
def d_shape(r,flat,z0,z1):return cyl(r,z0,z1)^box(-r-1,r+1,-r-1,flat,z0-1,z1+1)

def local(m,angle,z):
 # Local X is tangential, Y is radially outward; Z is the wand length.
 return b.spin(m,angle).translate((0,0,z))

def branch(angle,z,r=4.0):
 # Teardrop's 45-degree peak is +Z, the upright print direction.
 void=Manifold.extrude(b.teardrop_cs(r),20.).transform(np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],float))
 return local(void,angle,z)

def button_standoff(z):return 2. if abs(z-117.)<.01 else 0.

def button_pad(angle,z):
 # 24 mm tangent platform, 20.4 mm cassette locator, open central wire outlet.
 offset=button_standoff(z)
 front=box(-12,12,14.0+offset,16.2+offset,-12,12)
 root=box(-5,5,8.5,12.,-18,9)
 solid=Manifold.batch_hull([front,root])
 recess=box(-10.2,10.2,15.55+offset,17.+offset,-10.2,10.2)
 return local(solid-recess,angle,z)

def cap_pin(angle):
 return b.spin(box(-1.45,1.45,11.5,13.0,7.4,9.4),angle)

def bottom_socket():
 voids=[cyl(12.25,2.,11.8),cyl(12.25,2.,4.,12.8)]
 # Three short, circumferential grooves with a hard stop and a shallow detent.
 for a in (0,120,240):
  voids.append(b.sector(13.25,a-8,a+8,2.,9.65))
  voids.append(b.sector(13.25,a-8,a+38,7.1,9.65))
 return union(voids)

def bottom_cap():
 base=cyl(13.5,0.,.8,15.)+cyl(15.,.8,3.)
 plug=cyl(12.,2.7,10.8)-cyl(10.4,3.1,11.8)
 cap=union([base,plug]+[cap_pin(a+30) for a in (0,120,240)])
 # Two thumbnail grips on the exterior flange; no point projects into the cell.
 return cap-union([box(-1.4,1.4,12.6,17.,.8,2.2),box(-1.4,1.4,-17.,-12.6,.8,2.2)])

def handle_left(right=False):
 base=body(3.2,139.8)+male_at(140.)+b.sweep(b.loop_path('oval'),b.H['loop_radius'])
 base=union([base]+[button_pad(-a if right else a,z) for _,a,z in HAND_BUTTONS])
 chamber=rr(BATTERY['chamber_mm'][0],BATTERY['chamber_mm'][1],2.,11.4,60.4)
 # 45-degree chamber roof feeds the 10.4 mm main bore, never a horizontal sealed ceiling.
 chamber_top=Manifold.batch_hull([rr(22.6,9.,2.,60.3,60.5),cyl(BORE/2,66.,66.2)])
 voids=[bottom_socket(),chamber,chamber_top,cyl(BORE/2,59.,157.)]
 voids += [branch(-a if right else a,z) for _,a,z in HAND_BUTTONS]
 base=base-union(voids)
 # Two gentle locating ribs; generous free space, no cell compression or sharp clamp.
 ribs=[box(10.7,11.5,-2.2,2.2,16.,52.),box(-11.5,-10.7,-2.2,2.2,16.,52.)]
 return union([base]+ribs)

def lower_shaft():
 return union([body(140.,MID),d_shape(R_MID,FLAT_MID,MID-.4,MID+PEG)])-union([female_at(140.),cyl(BORE/2,155.,MID+PEG+1)])

def upper_shaft():
 m=body(MID,TOP-.2)+male_at(TOP)
 return m-union([d_shape(R_MID+GAP,FLAT_MID+GAP,MID-1,MID+PEG+.5),cyl(BORE/2,MID-1,TOP+17)])

HEAD_WAIST_Z=320.; HEAD_WIDTH=40.; HEAD_DEPTH=37.

def gem(w,d,corner,z0,waist,z1,tip=.8):
 lower=poly_prism(bevel_poly(tip,tip,tip/4),z0,z0+.08)
 belt=poly_prism(bevel_poly(w,d,corner),waist-.04,waist+.04)
 upper=poly_prism(bevel_poly(tip,tip,tip/4),z1-.08,z1)
 return union([Manifold.batch_hull([lower,belt]),Manifold.batch_hull([belt,upper])])

def head_cavity():
 inner=gem(35.6,33.,9.,283.,HEAD_WAIST_Z,338.,.3)
 return inner^box(-13.2,13.2,-30,30,281,342)

def head_outer():
 diamond=gem(HEAD_WIDTH,HEAD_DEPTH,6.,TOP,HEAD_WAIST_Z,END)
 neck=cyl(11.6,TOP,TOP+16.)
 shoulder=diamond^box(-30,30,-30,30,302.,302.1)
 blend=Manifold.batch_hull([cyl(11.6,TOP+15.9,TOP+16.),shoulder])
 return union([diamond,neck,blend])

def usb_clearance():
 # Rearward board placement keeps a straight upward plug path behind the diamond tip.
 return box(-7.8,7.8,-7.2,-.35,BOARD0+17.,END+2.)

SLIDE_SLOPE=18.5/38.

def slide_shear(m):
 return m.transform(np.array([[1,0,0,0],[0,1,SLIDE_SLOPE,-SLIDE_SLOPE*320.],[0,0,1,0]],float))

def rail_poly(side,clearance=0.):
 p=CrossSection([[(14.05,2.35),(15.35,2.35),(15.15,5.25),(14.25,5.25)]])
 if clearance:p=p.offset(clearance,mf.JoinType.Miter)
 z0,z1=(314.8,END+1.) if clearance else (315.,323.)
 m=slide_shear(Manifold.extrude(p,z1-z0).translate((0,0,z0)))
 return m if side>0 else m.mirror((1,0,0))

def latch_nub():
 # A shallow detent on one guide rail; the PETG shell flexes for release.
 return slide_shear(Manifold.sphere(.42,16).translate((15.26,3.45,317.1)))

def latch_pocket():
 return slide_shear(Manifold.sphere(.62,20).translate((15.26,3.45,317.1)))

def rear_web(x0,x1,z0,z1,y1):
 # Buttressed back-wall anchor; central battery pads remain untouched.
 return Manifold.batch_hull([box(x0,x1,-25,-24,z0-8,z0-.45),
                            box(x0,x1,BOARD_Y-.8,y1,z0,z1)])^head_outer()

def board_corner_guides():
 # Only the short ends/corners are captured. Leave the seven solder pads along
 # each long side open, with no continuous channel over the castellations.
 pieces=[]
 for side in (-1,1):
  def sx(q):return q if side>0 else q.mirror((1,0,0))
  for z0,z1 in ((BOARD0+.15,BOARD0+1.35),(BOARD0+19.65,BOARD0+21.2)):
   pieces.append(sx(rear_web(9.1,10.4,z0,z1,BOARD_Y+2.9)))
  # Lower end stops and rear seats: no front lip here, so the board pivots in.
  pieces.append(sx(rear_web(6.15,7.75,BOARD0-.95,BOARD0-.2,BOARD_Y+2.9)))
  # Upper short-edge pocket: 0.2 mm end clearance, 1.9 mm PCB slot.
  upper=rear_web(6.25,7.65,BOARD0+21.2,BOARD0+22.2,BOARD_Y)
  upper+=box(6.25,7.65,BOARD_Y-.8,BOARD_Y+3.1,BOARD0+21.2,BOARD0+22.2)
  lip=box(6.25,7.65,BOARD_Y+BOARD_SLOT,BOARD_Y+3.1,BOARD0+20.4,BOARD0+22.2)
  pieces.append(sx(upper+lip))
 return union(pieces)

def board_release_clip():
 # A wide bridge spring with two anchored ends, rather than two tiny unsupported
 # snap fingers. Press its centre towards the handle (down Z) to release.
 # Rear bow sits below the board. The centre tongue passes under its short end;
 # the forward 6 mm wire passage stays clear beside it.
 beam=box(-13.65,13.65,BOARD_Y-1.5,BOARD_Y,BOARD0-1.2,BOARD0-.4)
 tongue=box(-2.4,2.4,BOARD_Y-.5,BOARD_Y+3.7,BOARD0-1.,BOARD0-.2)
 nose=Manifold.batch_hull([
  box(-2.4,2.4,BOARD_Y+BOARD_SLOT,BOARD_Y+2.2,BOARD0-.4,BOARD0+.9),
  box(-2.4,2.4,BOARD_Y+3.6,BOARD_Y+3.7,BOARD0-.4,BOARD0-.1)])
 return union([beam,tongue,nose])^head_outer()

def head_base():
 outer=head_outer();opening=slide_shear(box(-50,50,4.8,50,306.,END+1.))
 base=outer-union([opening,head_cavity(),female_at(TOP),cyl(BORE/2,TOP-1,318.),usb_clearance()]+[rail_poly(t,.20)for t in(-1,1)])
 seats=[]
 for x in (-6.3,6.3):
  for z in (BOARD0+1.,BOARD0+16.):
   support=Manifold.batch_hull([box(x-.5,x+.5,-25,-24,z-15,z-.45),box(x-.5,x+.5,BOARD_Y-.8,BOARD_Y,z-.45,z+.45)])^outer
   seats.append(support)
 base=union([base]+seats)-latch_pocket()
 straps=[box(-22,-13.3,BOARD_Y-2.,BOARD_Y+1.,z,z+3.5)for z in(BOARD0+4.2,BOARD0+13.2)]+[box(13.3,22,BOARD_Y-2.,BOARD_Y+1.,z,z+3.5)for z in(BOARD0+4.2,BOARD0+13.2)]
 return union([base-union(straps),board_corner_guides(),board_release_clip()]).simplify(1e-5)

def head_cover():
 shell=head_outer()-head_cavity()
 lid=(shell^slide_shear(box(-50,50,4.95,50,306.25,END+1.)))-usb_clearance()
 return union([lid]+[rail_poly(t,0.)for t in(-1,1)]+[latch_nub()]).simplify(1e-5)

def socket_carrier():
 # Top switch plate: 14.0 mm aperture and 1.3 mm thickness for Choc V1.
 frame=box(-10,10,-10,10,0.,6.6)-box(-7.15,7.15,-7.15,7.15,.9,7.6)
 # Manufacturer socket bounding envelope, enlarged by 0.2 mm each side.
 pocket=box(-8.5,-1.1,-8.0,2.6,.9,3.08)
 access=box(-8.5,-1.1,-11.,-7.8,.9,3.08)
 keeper_slide=box(-8.95,8.95,-11.,9.25,3.05,4.35)
 switch_cut=box(-7.,7.,-7.,7.,5.25,7.6)
 post_holes=[cyl(1.85,-1,4.5),cyl(1.1,-1,4.5,y=5.5),cyl(1.1,-1,4.5,y=-5.5)]
 wires=[box(-7.6,-4.2,1.9,7.5,-1,2.1),box(-5.4,-2.0,-11.,-7.3,-1,2.1)]
 return frame-union([pocket,access,keeper_slide,switch_cut]+post_holes+wires)

def socket_keeper():
 p=box(-8.7,8.7,-9.,8.9,3.2,4.2)+box(-3,3,-12.,-8.8,3.2,4.2)
 holes=[cyl(1.85,2.9,4.5),cyl(1.1,2.9,4.5,y=5.5),cyl(1.1,2.9,4.5,y=-5.5),cyl(1.6,2.9,4.5,x=-5.9),cyl(1.6,2.9,4.5,x=-3.8,y=-5.)]
 return p-union(holes)

def cassette_on_handle(m,angle,z):
 # Local cassette Z pushes away from the tangent mount.
 return local(m.transform(np.array([[1,0,0,0],[0,0,1,15.6+button_standoff(z)],[0,-1,0,0]],float)),angle,z)

def battery_sled():
 # Removable non-rotating support; existing tape straps the cell onto this tray.
 m=box(-10.3,10.3,-4.1,-2.9,13.,58.)+box(-10.3,10.3,-4.1,3.5,13.,14.2)
 m=union([m,box(-10.3,-9.6,-3.0,-.8,14.,58.),box(9.6,10.3,-3.0,-.8,14.,58.)])
 return m-union([box(-11,-9.5,-5,-2.8,23.,28.),box(9.5,11,-5,-2.8,23.,28.),box(-11,-9.5,-5,-2.8,44.,49.),box(9.5,11,-5,-2.8,44.,49.)])

def measure(m):
 tri=b.canonical_triangles(m)
 return b.mesh_checks(tri,len(m.decompose()))

def write_new(p,data):
 with p.open('xb') as f:f.write(data)
 assert p.read_bytes()==data

def build(out):
 if out is not None:out.mkdir(parents=True,exist_ok=False)
 models={'Handle_Left':handle_left(),'Handle_Right':handle_left(True), 'Lower_Shaft':lower_shaft(),'Upper_Shaft':upper_shaft(),'Sense_Head_Base':head_base(),'Sense_Sliding_Cover':head_cover(),'Battery_Twist_Cap':bottom_cap(),'Battery_Sled':battery_sled(),'Choc_Socket_Carrier':socket_carrier(),'Choc_Socket_Keeper':socket_keeper(),'Fit_Test_Male':(cyl(11.6,TOP-12,TOP-.2)+male_at(TOP))-cyl(BORE/2,TOP-13,TOP+18),'Fit_Test_Female':cyl(11.6,TOP,TOP+30)-female_at(TOP)}
 records=[]
 for name,m in models.items():
  if m.status()!=mf.Error.NoError:raise RuntimeError((name,str(m.status())))
  rot=(0,0,0)
  # Cover prints outer crown down; tiny plate/carrier prints flat, every hole vertical.
  if name=='Sense_Sliding_Cover':rot=(-math.degrees(math.atan2(37.88,18.1)),0,0)
  if name=='Sense_Head_Base':rot=(0,0,0)
  if name=='Battery_Sled':rot=(90,0,0)
  p=m.rotate(rot);bb=p.bounding_box();shift=(-(bb[0]+bb[3])/2,-(bb[1]+bb[4])/2,-bb[2]);p=p.translate(shift)
  tri=b.canonical_triangles(p);report=b.mesh_checks(tri,len(m.decompose()))
  if not(report['watertight'] and report['winding_consistent'] and report['every_edge_shared_twice'] and report['bodies']==1):raise RuntimeError((name,report))
  blob=b.stl_bytes(tri,name)
  if out is None:assert (HERE/'exports'/(name+'.stl')).read_bytes()==blob, 'Stale STL: '+name
  else:write_new(out/(name+'.stl'),blob)
  r=b.rotation(rot);t=np.eye(4);t[:3,:3]=r.T;t[:3,3]=-r.T@np.array(shift)
  mesh=m.to_mesh();records.append({'name':name,'file':name+'.stl','sha256':hashlib.sha256(blob).hexdigest(),'checks':report,'print_to_assembly':t.tolist(),'assembly_vertices':np.asarray(mesh.vert_properties)[:,:3].round(4).tolist(),'assembly_faces':np.asarray(mesh.tri_verts).tolist()})
 # Assembly checks exclude designed cam interference at the two twist-lock joints.
 checks={}
 for a,c in [('Lower_Shaft','Upper_Shaft'),('Sense_Head_Base','Sense_Sliding_Cover')]:checks[a+'__'+c]=round((models[a]^models[c]).volume(),6)
 wire=cyl(4.95,61,TOP+18)
 checks['wire_probe_9_9mm']={n:round((m^wire).volume(),6) for n,m in models.items() if n in ['Handle_Left','Lower_Shaft','Upper_Shaft']}
 checks['same_handle_connector']=round(((models['Handle_Left']^box(-30,30,-30,30,139.0,157.))-(models['Handle_Right']^box(-30,30,-30,30,139.,157.))).volume(),6)
 checks['button_branch_7mm']={name:round((models['Handle_Left']^branch(a,z,3.5)).volume(),6) for name,a,z in HAND_BUTTONS}
 checks['cap_handle_locked']=round((models['Handle_Left']^models['Battery_Twist_Cap']).volume(),6)
 checks['sled_handle_clearance']=round((models['Handle_Left']^models['Battery_Sled']).volume(),6)
 checks['battery_envelope_overlap']=round((models['Handle_Left']^rr(20.,6.,1.5,15.,55.)).volume(),6)
 board=box(-8.9,8.9,BOARD_Y,BOARD_Y+BOARD_T,BOARD0,BOARD0+21.)
 solder=box(-5.4,5.4,BOARD_Y-6.,BOARD_Y-.25,BOARD0+3,BOARD0+18)
 checks['socket_keeper_clearance']=round((models['Choc_Socket_Carrier']^models['Choc_Socket_Keeper']).volume(),6)
 checks['board_outline']={n:round((models[n]^board).volume(),6) for n in ['Sense_Head_Base','Sense_Sliding_Cover']}
 checks['underside_solder_cavity']={n:round((models[n]^solder).volume(),6) for n in ['Sense_Head_Base','Sense_Sliding_Cover']}
 report={'version':'Print V2','design_revision':'V17','head_shape':'faceted-plumbob','head_size_mm':[40.,37.,58.],'board_z0_mm':BOARD0,'board_y_mm':BOARD_Y,'board_thickness_mm':BOARD_T,'board_slot_mm':BOARD_SLOT,'board_side_gap_mm':BOARD_SIDE_GAP,'retention':'fixed upper edge pockets, corner guides and lower bridge spring clip','cover_slide_vector':[0.,SLIDE_SLOPE,1.],'length_mm':END,'wire_bore_mm':BORE,'wire_count_full':8,'wire_count_shared_ground':6,'hand_buttons':HAND_BUTTONS,'button_standoffs_mm':{'thumb':2.,'index':0.,'middle':0.},'battery':BATTERY,'checks':checks,'parts':records,'physical_fit_verified':False}
 assert all(abs(v)<.01 for v in checks['wire_probe_9_9mm'].values()), 'Main bore blocked'
 assert all(abs(v)<.01 for v in checks['button_branch_7mm'].values()), 'Button outlet blocked'
 assert abs(checks['Sense_Head_Base__Sense_Sliding_Cover'])<.01, 'Cover collision'
 assert abs(checks['socket_keeper_clearance'])<.01, 'Keeper collision'
 assert all(abs(v)<.001 for v in checks['board_outline'].values()), 'Board collision'
 assert all(abs(v)<.001 for v in checks['underside_solder_cavity'].values()), 'Solder clearance collision'
 report['source']={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),HERE/'reference/wand_cad.py',HERE/'reference/dimensions.json']}
 report['retention_highlights']={}
 for name,m in [('Corner_guides',board_corner_guides()),('Release_clip',board_release_clip())]:
  mesh=m.to_mesh();report['retention_highlights'][name]={'assembly_vertices':np.asarray(mesh.vert_properties)[:,:3].tolist(),'assembly_faces':np.asarray(mesh.tri_verts).tolist()}
 if out is None:assert json.loads((HERE/'exports/manifest.json').read_text())==json.loads(json.dumps(report)), 'Stale geometry manifest'
 else:write_new(out/'manifest.json',(json.dumps(report,separators=(',',':'))+'\n').encode())
 print(json.dumps({'out':str(out),'checks':checks,'parts':{r['name']:r['checks'] for r in records}},indent=2))
 return models,report

if __name__=='__main__':
 ap=argparse.ArgumentParser();group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--out',type=Path);group.add_argument('--check',action='store_true');args=ap.parse_args();build(None if args.check else args.out)
