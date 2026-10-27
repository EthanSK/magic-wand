#!/usr/bin/env python3
"""Print V19 candidate: 410 mm hollow helix wand with a continuous taper, rounded diamond, concealed keyhole cam-lock finger loop and an Art Nouveau leaf shell with smaller handle openings and fuller rounded rails. Millimetres. Mechanical review prototype with a clipped board cradle and clear thumb mount.
Install requirements.txt into a virtual environment; use --check or an unused --out directory.
The old model and reference geometry remain unchanged. Physical fit is unverified.
"""
from __future__ import annotations
import argparse, importlib.util, json, math, struct, sys, hashlib, zipfile
from pathlib import Path
from functools import lru_cache
import numpy as np
import manifold3d as mf
from manifold3d import Manifold, CrossSection
HERE=Path(__file__).resolve().parent
SUPPORT=HERE.parent/'v2'
spec=importlib.util.spec_from_file_location('wand_reference',SUPPORT/'reference/wand_cad.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
box,cyl,union=b.box,b.cyl_z,b.union
BORE=10.4; MID=246.; TOP=352.; END=410.; BOARD0=376.; BOARD_Y=-5.5
BOARD_T=1.6; BOARD_SLOT=1.9; BOARD_SIDE_GAP=.2
# Provisional battery envelope; the actual battery must be measured before printing.
BATTERY={'verified_product':False,'nominal_envelope_mm':[20.0,6.0,40.0],
         'chamber_mm':[20.4,6.4,42.0], 'note':'Provisional cell envelope: measure the actual battery and use removable spacers before printing the handle.'}
PRINCIPLES=json.loads((HERE/'design-principles.json').read_text())
LOOP_MOUNTS=[PRINCIPLES['loop_lower_mount_z'],PRINCIPLES['loop_lower_mount_z']+PRINCIPLES['loop_mount_spacing']]
HAND_BUTTONS=[(name,PRINCIPLES['button_angles'][name],LOOP_MOUNTS[1]+offset)for name,offset in PRINCIPLES['button_offsets_from_upper_loop_mount'].items()]
HANDLE_END=160.; JOINT_R=8.95; TIP_ROUND=1.2
LOOP_SHIFT=0.; LOOP_POINTS=[[LOOP_MOUNTS[0]+z,y]for z,y in [[0.,-16.],[0.,-28.],[8.,-39.],[54.,-49.],[76.,-42.],[90.,-28.],[90.,-16.]]]
LOOP_SLIDE=4.; LOOP_FOOT_LENGTH=6.
GRIP_REDUCTION=4.1; GRIP_WALL=1.0; LOOP_WIDTH=7.; LOOP_RADIUS=2.; LOOP_WALL=0.; SHAFT_WALL=1.0
LOOP_HEAD_INNER=3.2; LOOP_HEAD_DEPTH=.9
LOOP_HEAD_RADIUS=3.6; LOOP_NECK_RADIUS=2.1; LOOP_SEAT_WIDTH=14.4; LOOP_SEAT_HEIGHT=9.6

R_MID=8.3;FLAT_MID=7.5; PEG=16.; GAP=.15

def rounded_rect(w,h,r):
 return CrossSection.square((w-2*r,h-2*r),True).offset(r,mf.JoinType.Round)

def rr(w,h,r,z0,z1):return Manifold.extrude(rounded_rect(w,h,r),z1-z0).translate((0,0,z0))

def bevel_poly(w,h,c):
 x,y=w/2,h/2
 return [(-x+c,-y),(x-c,-y),(x,-y+c),(x,y-c),(x-c,y),(-x+c,y),(-x,y-c),(-x,-y+c)]

def poly_prism(p,z0,z1):return Manifold.extrude(CrossSection([p]),z1-z0).translate((0,0,z0))

def previous_radius(z):
 fade=max(0.,min(1.,(z-14.)/16.))
 return b.taper_radius(z*140./HANDLE_END)-1.6*fade

def radius(z):
 # Skin-facing depth loses 5 mm of diameter from V18. Retain the cap ring;
 # the minimum upper radius also preserves 1.2 mm of material over cam grooves.
 if z>HANDLE_END:return shaft_radius(z,HANDLE_END)
 fade=max(0.,min(1.,(z-14.)/10.))
 return max(9.,previous_radius(z)-2.5*fade)

def grip_xradius(z):
 # A 20 mm wide cell cannot fit inside an 18-20 mm circular tube. Its low
 # housing stays 24.6 mm wide, but is 5 mm shallower; above it, both axes slim.
 cell=max(0.,min(1.,(82.-z)/24.))
 return max(radius(z),12.3*cell+radius(z)*(1.-cell))

def grip_radius(z,angle):
 a=np.radians(angle)
 return 1./np.sqrt((np.sin(a)/grip_xradius(z))**2+(np.cos(a)/radius(z))**2)

def shaft_radius(z,start=HANDLE_END):
 r0=9. if start==HANDLE_END else b.taper_radius(140.)
 if z<=MID:
  t=max(0.,min(1.,(z-start)/(MID-start)))
  return 8.98+(r0-8.98)*(1.-t)**1.35
 t=max(0.,min(1.,(z-MID)/(TOP-MID)))
 return 8.98+(JOINT_R-8.98)*t


def rib_height(z,theta,button_clearance=True):
 # Original two counter-wound ribs, 90/72 mm pitch, unstacked at crossings.
 h=b.rib_height(np.full(len(theta),z),theta,True)
 h*=min(1.,max(0.,(TOP-z)/18.))
 # Keep the purchased caps' travel space clear around their small openings.
 if z<HANDLE_END and button_clearance:
  for _,angle,zz in HAND_BUTTONS:
   dz=abs(z-zz)
   if dz<12.:
    for a in (angle,-angle):
     delta=(theta-a+180.)%360.-180.
     mask=np.abs(delta)<50.
     h[mask]*=max(0.,min(1.,(dz-9.)/3.))
 return h

def body(z0,z1,start=None):
 n=120;zs=np.linspace(z0,z1,max(2,int(math.ceil(z1-z0))+1));theta=np.arange(n)*360/n
 verts=[]
 for z in zs:
  r=(grip_radius(z,theta) if start is None else shaft_radius(z,start))+rib_height(z,theta,start is None)
  verts.extend(zip((r*np.sin(np.radians(theta))).tolist(),(r*np.cos(np.radians(theta))).tolist(),[float(z)]*n))
 c0=len(verts);c1=c0+1;verts.extend([(0,0,z0),(0,0,z1)]);tri=[]
 for i in range(len(zs)-1):
  for k in range(n):
   k1=(k+1)%n;a=i*n;d=(i+1)*n;tri.extend([(a+k,a+k1,d+k1),(a+k,d+k1,d+k)])
 for k in range(n):tri.extend([(c0,(k+1)%n,k),(c1,(len(zs)-1)*n+k,(len(zs)-1)*n+(k+1)%n)])
 return b.closed_mesh(verts,tri,'continuous taper with crossed helix')

# Four meridional rails, broad curved hexagonal windows, and the complete
# existing spiral skin. This is a perforated ribbed shell, not a free helix.
SPINE_WIDTH=3.6; SPINE_DEPTH=1.8; GRIP_RAIL_DEPTH=1.6; WINDOW_HEIGHT=28.; WINDOW_PITCH=32.

def leaf_profile(width,height,bow=.55):
 # Four cubic curves form a rounded leaf; its gentle S bend is contained
 # inside the existing cell width. No separate ornamental pieces are added.
 w,h=width/2,height/2
 anchors=[[(0,-h),(.55*w,-h+min(1.,h*.12)),(w,-.56*h),(w,0)],[(w,0),(w,.56*h),(.55*w,h-min(1.,h*.12)),(0,h)],[(0,h),(-.55*w,h-min(1.,h*.12)),(-w,.56*h),(-w,0)],[(-w,0),(-w,-.56*h),(-.55*w,-h+min(1.,h*.12)),(0,-h)]]
 pts=[]
 for segment in anchors:
  p=np.array(segment,float)
  for u in np.linspace(0,1,17,endpoint=False):
   xy=(1-u)**3*p[0]+3*(1-u)**2*u*p[1]+3*(1-u)*u*u*p[2]+u**3*p[3]
   v=(xy[1]+h)/height;xy[0]+=bow*math.sin(2*math.pi*v)*math.sin(math.pi*v)*(1-abs(xy[0])/w)
   pts.append(xy.tolist())
 return CrossSection([pts])

def roof_45(cs):
 # Lower the upper outline until its inward closing slope is at most 1:1.
 # This adds material BELOW a shallow spiral edge, rather than cutting the
 # preserved spiral or asking the printer to bridge a long cell ceiling.
 contours=cs.to_polygons();xmin,ymin,xmax,ymax=cs.bounds()
 xs=np.linspace(xmin,xmax,max(3,int(math.ceil((xmax-xmin)/.35))+1));tops=[]
 for x in xs:
  yy=[]
  for poly in contours:
   for v,w in zip(poly,np.roll(poly,-1,axis=0)):
    if abs(w[0]-v[0])<1e-7:
     if abs(x-v[0])<1e-5:yy.extend([v[1],w[1]])
    elif min(v[0],w[0])-1e-6<=x<=max(v[0],w[0])+1e-6:
     yy.append(v[1]+(w[1]-v[1])*(x-v[0])/(w[0]-v[0]))
  tops.append(max(yy) if yy else ymin)
 roof=np.min(np.asarray(tops)[None,:]+np.abs(xs[:,None]-xs[None,:]),axis=1)
 clip=CrossSection([[ (float(xmin),float(ymin-1)),(float(xmax),float(ymin-1)) ]+[(float(x),float(y)) for x,y in zip(xs[::-1],roof[::-1])]])
 return cs^clip

@lru_cache(None)
def window_regions(zone,start=HANDLE_END):
 rows=[32.,64.,96.,128.] if zone=='grip' else list(np.arange(start+28.,MID-18.,WINDOW_PITCH)) if zone=='lower' else list(np.arange(MID+26.,TOP-18.,WINDOW_PITCH))
 out=[]
 for z in rows:
  for angle in (45.,135.,225.,315.):
   ref=float(grip_radius(z,angle)) if zone=='grip' else shaft_radius(z,start)
   width=math.pi*ref/2.-SPINE_WIDTH;h=WINDOW_HEIGHT;w=width/2.;rise=w+.4
   cell=leaf_profile(width,h,.55 if zone=='grip' else .75).translate((0,z))
   # Reserve the full original 48-degree-wide spiral strips plus a small land.
   guard=24.+math.degrees(.8/ref);zlo,zhi=z-h/2-2,z+h/2+2
   for k in (0,1):
    aa=float(b.rib_angle(zlo,k));bb=float(b.rib_angle(zhi,k))
    for turns in range(-10,11):
     x0=math.radians(aa+360*turns-angle)*ref;x1=math.radians(bb+360*turns-angle)*ref;g=math.radians(guard)*ref
     if max(x0,x1)+g < -w or min(x0,x1)-g > w:continue
     cell-=CrossSection([[(x0-g,zlo),(x0+g,zlo),(x1+g,zhi),(x1-g,zhi)]])
   if zone=='grip':
    # Purchased controls, both handed arrangements, and detachable loop roots.
    keep=[(aa,zz,60.,15.) for _,a,zz in HAND_BUTTONS for aa in (a,-a)]
    keep += [(180.,zz,40.,12.)for zz in LOOP_MOUNTS]
    for aa,zz,da,dz in keep:
     delta=(aa-angle+180)%360-180;x0=math.radians(delta-da)*ref;x1=math.radians(delta+da)*ref
     cell-=CrossSection([[(x0,zz-dz),(x1,zz-dz),(x1,zz+dz),(x0,zz+dz)]])
   # Round the cell corners and discard tiny slivers: no decorative pinholes.
   for component in cell.decompose():
    if component.is_empty() or component.area()<22.:continue
    component=roof_45(component).offset(-1.15,mf.JoinType.Round).offset(1.15,mf.JoinType.Round).offset(-(.15 if zone=='grip' else .05),mf.JoinType.Round).simplify(.015)
    for shape in component.decompose():
     if shape.area()<22.:continue
     x0,y0,x1,y1=shape.bounds()
     if x1-x0<3.5 or y1-y0<6.:continue
     safe=shape.offset(-.9,mf.JoinType.Round)
     if safe.is_empty():continue
     for inset in np.arange(1.1,4.1,.2):
      deeper=shape.offset(-float(inset),mf.JoinType.Round)
      if deeper.is_empty() or deeper.area()<.5:break
      safe=deeper
     # Pick a genuine interior probe instead of assuming the polygon centroid.
     bx,by,tx,ty=safe.bounds();probe=None
     for yy in np.linspace((by+ty)/2,ty,7):
      for xx in np.linspace(bx,tx,13):
       q=CrossSection.square((.1,.1),True).translate((float(xx),float(yy)))
       if (q^safe).area()>.009:probe=(float(xx),float(yy));break
      if probe:break
     if not probe:continue
     out.append({'angle':angle,'ref_radius':ref,'outline_xz_mm':[np.asarray(poly).tolist() for poly in shape.to_polygons()],'area_mm2':shape.area(),'probe_xz':list(probe),'z':probe[1],'outer_radius':float(grip_radius(probe[1],angle+math.degrees(probe[0]/ref))) if zone=='grip' else shaft_radius(probe[1],start),'width_mm':float(x1-x0),'height_mm':float(y1-y0)})
 return out

def wrapped_window(record,zone,start=HANDLE_END):
 # Native convex radial lofts avoid folding a triangulated cap when a very
 # slender curved profile is warped around the tube. All cap geometry is
 # outside the physical skin; the centre stays inside the existing cavity.
 polys=[np.asarray(p,float) for p in record['outline_xz_mm']]
 assert len(polys)==1,'A leaf aperture must have one boundary'
 poly=polys[0];zmin=float(poly[:,1].min());zmax=float(poly[:,1].max())
 zs=np.linspace(zmin,zmax,max(3,int(math.ceil((zmax-zmin)/.5))+1));sections=[]
 for zz in zs:
  xx=[]
  for v,w in zip(poly,np.roll(poly,-1,axis=0)):
   if abs(w[1]-v[1])<1e-9:
    if abs(zz-v[1])<1e-7:xx.extend([float(v[0]),float(w[0])])
   elif min(v[1],w[1])-1e-7<=zz<=max(v[1],w[1])+1e-7:
    xx.append(float(v[0]+(w[0]-v[0])*(zz-v[1])/(w[1]-v[1])))
  assert xx,'Missing leaf cross-section'
  x0,x1=min(xx),max(xx)
  theta=np.radians(record['angle'])+np.linspace(x0,x1,max(2,int(math.ceil(math.degrees((x1-x0)/record['ref_radius'])/5.))+1))/record['ref_radius']
  outer=(radius(float(zz)) if zone=='grip' else shaft_radius(float(zz),start))+9.
  sections.append([(0.,0.,float(zz))]+[(float(outer*math.sin(a)),float(outer*math.cos(a)),float(zz)) for a in theta])
 return union([Manifold.hull_points(a+b) for a,b in zip(sections[:-1],sections[1:])])

@lru_cache(None)
def body_slots(zone,start=HANDLE_END):
 records=window_regions(zone,start)
 if not records:return Manifold()
 low=math.floor(min(min(q[1] for q in a['outline_xz_mm'][0]) for a in records));high=math.ceil(max(max(q[1] for q in a['outline_xz_mm'][0]) for a in records))
 radial=lambda z:radius(z) if zone=='grip' else shaft_radius(z,start)
 # Keep the original inner radial limit so apertures cannot remove a joint
 # anchor or other core feature merely because a native wedge reaches the axis.
 keep=union([cyl(radial(z)-3.,float(z),float(z+1),radial(z+1)-3.) for z in range(low,high)])
 return union([wrapped_window(a,zone,start) for a in records])-keep

def slot_locations(zone,start=HANDLE_END):
 # Probe coordinates for clearance checking; actual holes use curved outlines.
 return [dict(a,angle=a['angle']+math.degrees(a['probe_xz'][0]/a['ref_radius'])) for a in window_regions(zone,start)]

def rr_section(z,radial,depth):
 return rr(SPINE_WIDTH,depth-.18,.38,z-.015,z+.015).translate((0,radial(z)-(depth+.18)/2,0))

@lru_cache(None)
def axial_rails(zone,start=HANDLE_END):
 z0,z1=(13.,147.) if zone=='grip' else (start+18.,MID-5.) if zone=='lower' else (MID+18.,TOP-5.)
 rr=lambda z:radius(z) if zone=='grip' else shaft_radius(z,start)
 pieces=[]
 for a in np.arange(z0,z1,2.):
  d=min(float(a)+2.01,z1)
  for angle in (0.,90.,180.,270.):
   depth=GRIP_RAIL_DEPTH if zone=='grip' else SPINE_DEPTH
   section=lambda zz:rr_section(zz,(lambda p:float(grip_radius(p,angle))) if zone=='grip' else rr,depth)
   p=Manifold.batch_hull([section(float(a)),section(d)])
   pieces.append(local(p,angle,0.))
 return union(pieces)

def shaft_cavity(z0,z1,start):
 # Thinning happens inside the silhouette. Keep solid annular joint anchors
 # and 10.4 mm minimum route, with self-supporting internal transitions.
 zs=np.linspace(z0,z1,max(2,int(math.ceil(z1-z0))+1));pieces=[]
 def inner(z):
  skin=shaft_radius(z,start)-SHAFT_WALL
  entry=max(0.,min(1.,(z-z0-16.)/8.))
  exit=max(0.,min(1.,(z1-z-3.)/8.))
  return BORE/2+(skin-BORE/2)*min(entry,exit)
 for a,d in zip(zs[:-1],zs[1:]):pieces.append(cyl(inner(a),float(a),float(d),inner(d)))
 return union(pieces)

# Isolated small joint module; never change the frozen handle bayonet dimensions.
sp=importlib.util.spec_from_file_location('slim_joint',SUPPORT/'reference/wand_cad.py')
j=importlib.util.module_from_spec(sp);sp.loader.exec_module(j)
j.J=dict(j.J,spigot_diameter=13.2,spigot_length=14.,pin_height=.9,pin_root=6.,pin_width=3.2,pin_center_depth=7.,pin_lead_chamfer=.3)
j.R_SPIGOT=6.6;j.R_BORE=6.8;j.R_TIP=7.5;j.R_GROOVE=7.75
j.HW_PIN=math.degrees(j.J['pin_width']/2/j.R_SPIGOT)
j.HW_SLOT=j.HW_PIN+math.degrees(j.J['slot_clearance']/j.R_TIP)
j.D_FRONT=j.J['pin_center_depth']-j.J['pin_axial']/2;j.D_BACK=j.D_FRONT+j.J['pin_axial']
j.D_GROOVE=j.D_BACK+j.J['groove_floor_clearance'];j.Z_SPIGOT=j.L-j.J['spigot_length']

def slim_male_at(z):return j.mirror_joint(j.spigot_end()).translate((0,0,z-140.))
def slim_female_at(z):
 voids=[cyl(j.R_BORE,j.Z_SPIGOT,j.L+1.),cyl(j.R_BORE,j.L-.6,j.L+.01,j.R_BORE+.61)]
 for lock in j.J['pin_angles']:
  entry=lock-j.J['twist'];voids += [j.sector(j.R_GROOVE,entry-j.HW_SLOT,entry+j.HW_SLOT,j.L-j.D_GROOVE,j.L+1.),j.swept_groove(j.groove_stations(lock,j.J['cam']['crest_interference']))]
 return j.mirror_joint(union(voids)).translate((0,0,z-140.))

def male_at(z):return slim_male_at(z)
def female_at(z):return slim_female_at(z)
def d_shape(r,flat,z0,z1):return cyl(r,z0,z1)^box(-r-1,r+1,-r-1,flat,z0-1,z1+1)

def local(m,angle,z):
 # Local X is tangential, Y is radially outward; Z is the wand length.
 return b.spin(m,angle).translate((0,0,z))

def branch(angle,z,r=4.0):
 # Teardrop's 45-degree peak is +Z, the upright print direction.
 void=Manifold.extrude(b.teardrop_cs(r),20.).transform(np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],float))
 return local(void,angle,z)

def button_standoff(z):return 2. if abs(z-139.)<.01 else 0.

BUTTON_ORIGIN=9.8

def mount_local(m,angle,z):
 return local(m.transform(np.array([[1,0,0,0],[0,0,1,BUTTON_ORIGIN],[0,-1,0,0]],float)),angle,z)

def rail_profile(clearance=0.):
 p=CrossSection([[(7.4,-1.2),(8.2,-1.2),(8.2,-.8),(7.65,.12),(7.4,.12)]])
 return p.offset(clearance,mf.JoinType.Miter) if clearance else p

def along_button_y(cs,y0,y1):
 return Manifold.extrude(cs,y1-y0).transform(np.array([[1,0,0,0],[0,0,1,y0],[0,1,0,0]],float))

def receiver_voids():
 well=rr(14.6,15.0,.6,-5.3,2.)
 socket=box(-8.5,-1.1,-8.,2.6,-4.4,-1.8)
 tracks=[]
 for side in (-1,1):
  tr=along_button_y(rail_profile(.15),0.,8.25)
  entry=box(7.2,8.55,-14.,.05,-1.45,.18)
  tracks.extend([tr if side>0 else tr.mirror((1,0,0)),entry if side>0 else entry.mirror((1,0,0))])
 # Shallow face recess; radial entry avoids a long slot through the helix.
 face=rr(16.7,17.5,.9,-.15,2.)
 return union([well,socket,face]+tracks)

def button_claw_relief():
 return union([box(7.2,9.65,2.0,8.1,-2.1,.3),box(-9.65,-7.2,2.0,8.1,-2.1,.3)])

def button_side_claws(deflection=0.):
 # Two 0.8 mm thick, 5.7 mm free-length PETG arms, rooted at the lower end.
 # Relief behind each arm prevents the curved stem trapping it rigidly.
 beam=box(8.35,9.15,1.,9.5,-1.65,-.05)
 root=box(8.35,9.15,8.1,9.5,-8.,-.05)
 tooth=box(7.75,8.5,2.5,4.2,-.8,-.15)
 top_stop=box(7.75,8.5,1.,1.85,-1.3,-.8)
 arm=(union([beam,root,tooth])-receiver_voids())+top_stop
 both=union([arm,arm.mirror((1,0,0))])
 if not deflection:return both
 mesh=both.refine_to_length(.4).to_mesh();v=np.array(mesh.vert_properties[:,:3],dtype=np.float32)
 v[:,0]+=np.sign(v[:,0])*deflection*np.clip((8.1-v[:,1])/5.6,0.,1.)**2
 return Manifold(mf.Mesh(v,np.asarray(mesh.tri_verts,dtype=np.uint32)))

def button_receiver_local():
 # Internal socket backing only. button_pad clips this cradle to the original
 # curved stem: no exterior square surround. The thin plate hides under the
 # bought cap; two short integral side claws capture its guide feet.
 outer=rr(17.4,19.0,1.0,-6.5,-.05)
 well=rr(14.6,15.0,.6,-5.3,2.)
 socket=box(-8.5,-1.1,-8.,2.6,-4.4,-1.8)
 tracks=[]
 for side in (-1,1):
  tr=along_button_y(rail_profile(.15),0.,8.25)
  entry=box(7.2,8.55,-14.,.05,-1.45,.18)
  tracks.extend([tr if side>0 else tr.mirror((1,0,0)),entry if side>0 else entry.mirror((1,0,0))])
 body=outer-receiver_voids()
 # Remove the forward square rim except two short side claws and the lower
 # seating ledge. Everything else is internal backing, later skin-clipped.
 forward=box(-10.,10.,-11.,11.,-1.65,2.)
 claws=union([box(-9.,-7.35,2.5,5.,-1.65,-.05),box(7.35,9.,2.5,5.,-1.65,-.05),box(-8.7,-7.35,7.9,9.5,-1.65,-.05),box(7.35,8.7,7.9,9.5,-1.65,-.05)])
 body=body-(forward-claws)
 # The bought socket sits directly inside the wand, retained by two integral
 # short spring catches. No loose printed keeper or decorative cap is needed.
 floor=box(-8.5,-.8,-8.,2.6,-5.5,-4.4)
 clips=[]
 for y in (-6.7,.9):
  root=box(-8.7,-8.3,y-.6,y+.6,-4.4,-2.4)
  tooth=Manifold.batch_hull([box(-8.7,-8.05,y-.6,y+.6,-2.55,-2.25),box(-8.7,-8.3,y-.6,y+.6,-1.8,-1.7)])
  clips.extend([root,tooth])
 holes=[cyl(1.85,-7,3),cyl(1.1,-7,3,y=5.5),cyl(1.1,-7,3,y=-5.5),cyl(1.6,-7,3,x=-5.9),cyl(1.6,-7,3,x=-3.8,y=-5.)]
 return union([(body-button_claw_relief()),floor]+clips+[button_side_claws()])-union(holes)

def button_root_ties():
 lower=box(5.,8.6,8.1,9.5,-3.4,-2.5)
 # Stay beyond the bought socket's 8.3 mm edge and above the loop track.
 # The narrow existing claw gets a deep radial root into the slimmer wall.
 upper=box(8.5,9.15,.2,1.6,-8.,-1.)
 anchor=lower+upper
 return anchor+anchor.mirror((1,0,0))

def button_pad(angle,z):
 receiver=button_receiver_local();claws=button_side_claws()
 internal=mount_local(receiver-claws,angle,z)^body(3.2,HANDLE_END-.2).scale((.996,.996,1.))
 lower=union([box(-8.7,-7.35,8.1,9.5,-3.,-.05),box(7.35,8.7,8.1,9.5,-3.,-.05)])
 # No exterior square perimeter: only tiny flexible side claws/lower stops.
 # Short hidden root ties keep the claws attached when the slimmer curved
 # wall and nearby loop seat no longer reach their outer corner directly.
 return internal+mount_local(claws+(receiver^lower)+button_root_ties(),angle,z)

def button_window(angle,z):
 # Small teardrop wire outlet only; the recessed switch/socket well is in
 # the integral receiver, not a 16.8 mm hole through the hollow grip wall.
 return branch(angle,z,3.2)

def cap_pin(angle):
 return b.spin(box(-1.45,1.45,11.5,13.0,4.6,5.8),angle)

def bottom_socket():
 voids=[cyl(12.25,2.,6.3),cyl(12.25,2.,4.,12.8)]
 # Three short, circumferential grooves with a hard stop and a shallow detent.
 for a in (0,120,240):
  voids.append(b.sector(13.25,a-8,a+8,2.,6.05))
  voids.append(b.sector(13.25,a-8,a+38,4.35,6.05))
 return union(voids)

def bottom_cap():
 base=cyl(13.5,0.,.8,15.)+cyl(15.,.8,3.)
 plug=cyl(12.,2.7,5.2)-cyl(10.4,3.1,6.2)
 cap=union([base,plug]+[cap_pin(a+30) for a in (0,120,240)])
 # Two thumbnail grips on the exterior flange; no point projects into the cell.
 return cap-cyl(10.4,1.2,3.2)-union([box(-1.4,1.4,12.6,17.,.8,2.2),box(-1.4,1.4,-17.,-12.6,.8,2.2)])

def hollow_loop():
 # Compatibility helper: a solid 7 x 4 mm band has no tubular cavity.
 old_t,old_c=b.T,b.C
 try:
  b.T=LOOP_WIDTH;b.C=.85
  outer=b.sweep(b.catmull_rom(LOOP_POINTS),LOOP_RADIUS)
 finally:b.T,b.C=old_t,old_c
 return outer,Manifold()


def flute_profile(r):
 # Rounded teardrop: the upper slopes rise at 45 degrees for upright PETG.
 return b.teardrop_cs(r-.35).offset(.35,mf.JoinType.Round)

def radial_vent(angle,z,r,outer_radius):
 cs=flute_profile(r)
 # One skin only: leave the far side and the long internal cable route alone.
 # A 0.35 mm flared mouth softens the opening into the outside surface.
 y0=outer_radius-3.;y1=outer_radius+3.
 q=Manifold.extrude(cs,y1-y0).transform(np.array([[0,1,0,0],[0,0,1,y0],[1,0,0,0]],float))
 flare=Manifold.extrude(cs.offset(.35,mf.JoinType.Round),2.).transform(np.array([[0,1,0,0],[0,0,1,outer_radius-.2],[1,0,0,0]],float))
 return local(q+flare,angle,z)

def vent_locations(zone,start=HANDLE_END,right=False):
 rows=[64.,80.,96.] if zone=='grip' else ([start+34.,start+54.] if zone=='lower' else [277.,297.,319.])
 r=3. if zone=='grip' else 2.6
 out=[]
 for z in rows:
  rad=radius(z) if zone=='grip' else shaft_radius(z,start)
  candidates=[]
  for angle in range(0,360,5):
   # Leave the actual helix crest and its whole skirt intact, including at
   # the widest upper edge of each hole. Keep 0.6 mm beyond the rib skirt.
   safe=True
   for zz in np.linspace(z-r-.5,z+r*1.414+.5,9):
    for k in (0,1):
     delta=abs((angle-float(b.rib_angle(zz,k))+180.)%360.-180.)
     if delta<24.+math.degrees(math.asin((r+1.0)/rad)):safe=False
   if zone=='grip':
    for _,a,zc in HAND_BUTTONS:
     a=-a if right else a
     if abs(z-zc)<20. and abs((angle-a+180.)%360.-180.)<70.:safe=False
   if safe:candidates.append(angle)
  chosen=[]
  if zone=='grip':
   # Prioritise the rear surface against the fingers. The opposite opening
   # admits outside air; it is not a substitute for the skin-facing outlet.
   contact=[a for a in candidates if abs((a-180.+180.)%360.-180.)<=50.]
   if contact:chosen.append((min(contact,key=lambda a:abs(a-180.)),'hand_contact'))
   other=[a for a in candidates if all(abs((a-q+180.)%360.-180.)>95. for q,_ in chosen)]
   if other:chosen.append((min(other,key=lambda a:abs((a+180.)%360.-180.)),'outside_intake'))
  else:
   for target in (0.,180.):
    available=[a for a in candidates if all(abs((a-q+180.)%360.-180.)>95. for q,_ in chosen)]
    if available:chosen.append((min(available,key=lambda a:abs((a-target+180.)%360.-180.)),'shaft_vent'))
  for a,role in chosen:out.append({'angle':float(a),'z':z,'radius':r,'outer_radius':rad,'role':role})
 return out

def flute_vents(zone,start=HANDLE_END,right=False):
 return union([radial_vent(a['angle'],a['z'],a['radius'],a['outer_radius']) for a in vent_locations(zone,start,right)])

def loop_air_ports():return []
def loop_vents():return Manifold()
def loop_side_windows():return Manifold()

def loop_mount_radius(z):return radius(z)

LOOP_TWIST=12.; LOOP_CAM_RISE=.6; LOOP_TRACK_GAP=.22
LOOP_PRELOAD=.65; LOOP_RELEASE_DEFLECTION=3.2

def loop_pose(part,angle=0.,down=0.):
 return part.rotate((0,0,-angle)).translate((0,0,-LOOP_CAM_RISE*angle/LOOP_TWIST-down))

def loop_stud(z,g=0.):
 r=loop_mount_radius(z)
 # Enlarged teardrop head sits behind the original curved wand surface.
 # Reverse the profile's second axis so its printable 45-degree roof is +Z.
 head=Manifold.extrude(b.teardrop_cs(LOOP_HEAD_RADIUS+g).rotate(90.),LOOP_HEAD_DEPTH+2*g).transform(np.array([[1,0,0,0],[0,0,-1,-r+LOOP_HEAD_INNER+g],[0,1,0,z]],float))
 neck=b.cyl_y(LOOP_NECK_RADIUS+g,-r-1.4-g,-r+LOOP_HEAD_INNER-LOOP_HEAD_DEPTH+.2+g).translate((0,0,z))
 return head+neck

def loop_seat(z,g=0.):
 # Identical broad rounded shoulders at both ends. The inner 1.2 mm sits in
 # the stem; a short cam turn seats the face without a floating pin gap.
 r=loop_mount_radius(z)
 return rr(LOOP_SEAT_WIDTH+2*g,LOOP_SEAT_HEIGHT+2*g,1.4,-1.2-g,2.5+g).rotate((90.,0.,0.)).translate((0,-r,z))

@lru_cache(None)
def loop_motion_void(z,extra=0.):
 r=loop_mount_radius(z);g=LOOP_TRACK_GAP+extra
 head=Manifold.extrude(b.teardrop_cs(LOOP_HEAD_RADIUS+g).rotate(90.),LOOP_HEAD_DEPTH+2*g).transform(np.array([[1,0,0,0],[0,0,-1,-r+LOOP_HEAD_INNER+g],[0,1,0,z]],float))
 neck=b.cyl_y(LOOP_NECK_RADIUS+g,-r-20.,-r+LOOP_HEAD_INNER-LOOP_HEAD_DEPTH+.2+g).translate((0,0,z))
 seat=loop_seat(z,g)
 # Sweep adjacent half-degree poses. Globally hulling a broad rotating
 # pad or head erases retaining lips and can thin the inward pocket floor.
 pieces=[]
 for part in [head,neck,seat]:
  poses=[loop_pose(part,float(a)) for a in np.linspace(0.,LOOP_TWIST,25)]
  pieces += [union([Manifold.batch_hull([a,b])for a,b in zip(poses[:-1],poses[1:])]),Manifold.batch_hull([loop_pose(part,LOOP_TWIST),loop_pose(part,LOOP_TWIST,LOOP_SLIDE)])]
 # The broad entry is recessed; after lifting, only the narrow neck occupies
 # the L-shaped slot. Every projecting stud and release part leaves with the loop.
 entry=Manifold.extrude(b.teardrop_cs(LOOP_HEAD_RADIUS+g).rotate(90.),24.).transform(np.array([[1,0,0,0],[0,0,-1,-r+LOOP_HEAD_INNER+g],[0,1,0,z]],float))
 seat_entry=rr(LOOP_SEAT_WIDTH+2*g,LOOP_SEAT_HEIGHT+2*g,1.4,-1.2-g,22.).rotate((90.,0.,0.)).translate((0,-r,z))
 pieces.append(loop_pose(entry+seat_entry,LOOP_TWIST,LOOP_SLIDE))
 result=union(pieces)
 assert result.status()==mf.Error.NoError and result.volume()>1.
 return result

def loop_slide_clearance(z):
 r=loop_mount_radius(z);void=loop_motion_void(z)
 if z==LOOP_MOUNTS[1]:void+=box(4.2,7.5,-r-20.,-r+1.62,z-12.3,z-8.8)
 return void

@lru_cache(None)
def loop_receiver(z):
 r=loop_mount_radius(z);z0=z-LOOP_SLIDE-8.;z1=z+6.5
 # Clip the entire reinforcement to the pre-existing outside surface. No
 # boss, rail, tab or collar remains outside the normal wand when detached.
 blank=box(-8.,8.,-r-3.,-r+6.0,z0,z1)^body(3.2,HANDLE_END-.2).scale((.998,.998,1.))
 channel=loop_motion_void(z)
 if z==LOOP_MOUNTS[1]:
  channel+=box(4.2,7.5,-r-20.,-r+1.62,z-12.3,z-8.8)
 return blank-channel-body_slots('grip')

@lru_cache(None)
def loop_release_latch():
 z=LOOP_MOUNTS[1];r=loop_mount_radius(z)
 root=box(.8,6.7,-28.,-r-3.,z+1.5,z+3.)
 beam=box(4.8,7.,-r-4.,-r-3.,z-15.,z+2.8)
 tooth=Manifold.extrude(CrossSection([[(4.3,-r-3.4),(7.,-r-3.4),(7.,-r-2.4),(4.3,-r+2.2)]]),2.2).translate((0,0,z-11.8))
 tab=rr(4.2,2.2,.45,z-16.5,z-14.).translate((6.8,-r-4.1,0))
 return union([root,beam,tooth,tab])

@lru_cache(None)
def loop_latch_deflected(amount):
 # Geometric deflection envelope only, not PETG force or fatigue prediction.
 latch=loop_release_latch().refine_to_length(.7);m=latch.to_mesh();v=np.array(m.vert_properties[:,:3],np.float32)
 f=np.clip((LOOP_MOUNTS[1]+1.5-v[:,2])/12.,0.,1.)**2
 v[:,1]-=amount*f
 return Manifold(mf.Mesh(v,np.asarray(m.tri_verts,dtype=np.uint32)))

def loop_arm(z):
 # Same direct inward arm at top and bottom: no U return, bulb or hanging toe.
 r=loop_mount_radius(z)
 root=rr(7.,4.,.85,27.,30.).rotate((90.,0.,0.)).translate((0,0,z))
 return Manifold.batch_hull([root,loop_seat(z)])

@lru_cache(None)
def removable_loop():
 loop,void=hollow_loop()
 loop=loop-void-loop_vents()-loop_side_windows()
 feet=[loop_arm(z)+loop_stud(z) for z in LOOP_MOUNTS]
 return union([loop,loop_release_latch()]+feet)

@lru_cache(None)
def loop_with_latch_deflection(amount):
 return (removable_loop()-loop_release_latch())+loop_latch_deflected(amount)

def handle_left(right=False,with_loop_mounts=True):
 base=body(3.2,HANDLE_END-.2)+male_at(HANDLE_END)
 stops=[]
 for name,a,z in HAND_BUTTONS:
  neighbours=union([mount_local(receiver_voids()+button_claw_relief(),-aa if right else aa,zz)for nn,aa,zz in HAND_BUTTONS if nn!=name])
  stops.append(button_pad(-a if right else a,z)-neighbours)
 # Explicit open shell, not a battery-shaped slot surrounded by infill.
 core=[]
 for a in np.arange(13.,140.,1.):
  core.append(Manifold.batch_hull([cyl(radius(zz)-GRIP_WALL,zz,zz+.015).scale(((grip_xradius(zz)-GRIP_WALL)/(radius(zz)-GRIP_WALL),1.,1.))for zz in [float(a),float(a+1.01)]]))
 core += [Manifold.batch_hull([cyl(radius(147.)-GRIP_WALL,146.9,147.),cyl(BORE/2,154.,154.1)]),cyl(BORE/2,153.,177.)]
 voids=[bottom_socket(),union(core),body_slots('grip')]+[union([button_window(-a if right else a,z),mount_local(receiver_voids()+button_claw_relief(),-a if right else a,z)]) for _,a,z in HAND_BUTTONS]
 hardware=union([union([button_window(-a if right else a,z),mount_local(receiver_voids()+button_claw_relief(),-a if right else a,z)]) for _,a,z in HAND_BUTTONS])
 base=(base-union(voids))+(axial_rails('grip')-hardware)
 # 1.2 mm radial webs connect the loose battery guides to the outer shell.
 webs=[box(10.7,14.8,-.6,.6,16.,52.),box(-14.8,-10.7,-.6,.6,16.,52.)]
 webs=[m^body(15.,53.) for m in webs]
 ribs=[box(10.7,11.5,-2.2,2.2,16.,52.),box(-11.5,-10.7,-2.2,2.2,16.,52.)]
 if not with_loop_mounts:return union([base]+webs+ribs+stops)-union([button_window(-a if right else a,z) for _,a,z in HAND_BUTTONS]+[cyl(BORE/2,61.,177.)])
 result=union([base]+webs+ribs+stops+[loop_receiver(z)-hardware for z in LOOP_MOUNTS])-union([button_window(-a if right else a,z) for _,a,z in HAND_BUTTONS]+[cyl(BORE/2,61.,177.)]+[loop_slide_clearance(z) for z in LOOP_MOUNTS])
 # Slimming clips a 0.0124 mm3 isolated skin sliver off the internal switch
 # backing. It cannot print or retain hardware; remove only such tiny debris.
 result=result-bottom_socket()
 components=result.decompose();major=[p for p in components if p.volume()>.02]
 assert len(major)==1 and sum(abs(p.volume())for p in components if p.volume()<=.02)<.025,[(q.volume(),q.bounding_box())for q in components]
 return major[0]

def lower_shaft(start=HANDLE_END):
 return (union([body(start,MID-.2,start),slim_male_at(MID)])-union([(b.tapered_socket(b.J['cam']['crest_interference']) if start==140. else female_at(start)),shaft_cavity(start,MID,start),cyl(BORE/2,start-1,MID+16.),body_slots('lower',start)]))+axial_rails('lower',start)

def upper_shaft():
 return (union([body(MID,TOP-.2,HANDLE_END),slim_male_at(TOP)])-union([slim_female_at(MID),shaft_cavity(MID,TOP,HANDLE_END),cyl(BORE/2,MID-1,TOP+16.),body_slots('upper')]))+axial_rails('upper')

HEAD_WAIST_Z=390.; HEAD_WIDTH=40.; HEAD_DEPTH=37.

def gem(w,d,corner,z0,waist,z1,tip=.8):
 lower=poly_prism(bevel_poly(tip,tip,tip/4),z0,z0+.08)
 belt=poly_prism(bevel_poly(w,d,corner),waist-.04,waist+.04)
 upper=poly_prism(bevel_poly(tip,tip,tip/4),z1-.08,z1)
 return union([Manifold.batch_hull([lower,belt]),Manifold.batch_hull([belt,upper])])

def head_cavity():
 inner=gem(35.6,33.,9.,353.,HEAD_WAIST_Z,408.,.3)
 return inner^box(-13.2,13.2,-30,30,351,412)

def head_outer():
 core=gem(HEAD_WIDTH-2*TIP_ROUND,HEAD_DEPTH-2*TIP_ROUND,5.3,TOP+TIP_ROUND,HEAD_WAIST_Z,END-TIP_ROUND,1.0)
 diamond=core.minkowski_sum(Manifold.sphere(TIP_ROUND,20))
 neck=cyl(JOINT_R,TOP,TOP+16.)
 shoulder=diamond^box(-30,30,-30,30,372.,372.1)
 blend=Manifold.batch_hull([cyl(JOINT_R,TOP+15.9,TOP+16.),shoulder])
 return union([diamond,neck,blend])

def usb_clearance():
 # Rearward board placement keeps a straight upward plug path behind the diamond tip.
 return box(-7.8,7.8,-7.2,-.35,BOARD0+17.,END+2.)

SLIDE_SLOPE=18.5/38.

def slide_shear(m):
 return m.transform(np.array([[1,0,0,0],[0,1,SLIDE_SLOPE,-SLIDE_SLOPE*390.],[0,0,1,0]],float))

def rail_poly(side,clearance=0.):
 p=CrossSection([[(13.5,2.35),(16.8,2.35),(16.8,3.35),(15.75,4.35),(15.75,5.25),(14.55,5.25),(14.55,4.35),(13.5,3.35)]])
 if clearance:p=p.offset(clearance,mf.JoinType.Miter)
 z0,z1=(384.8,END+1.) if clearance else (385.,391.8)
 m=slide_shear(Manifold.extrude(p,z1-z0).translate((0,0,z0)))
 return m if side>0 else m.mirror((1,0,0))

def latch_nub():
 # A shallow detent on one guide rail; the PETG shell flexes for release.
 return slide_shear(Manifold.sphere(.42,16).translate((16.75,3.15,387.1)))

def latch_pocket():
 return slide_shear(Manifold.sphere(.62,20).translate((16.75,3.15,387.1)))

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
  # Self-supporting upper lips, with narrow 45-degree diagonal webs.
  strut=Manifold.batch_hull([
   box(18.6,20.,BOARD_Y+2.7,BOARD_Y+3.9,BOARD0+7.8,BOARD0+8.),
   box(6.25,7.65,BOARD_Y+2.7,BOARD_Y+3.9,BOARD0+20.4,BOARD0+20.6)])^head_outer()
  pieces.append(sx(upper+lip+strut))
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
 outer=head_outer();opening=slide_shear(box(-50,50,4.8,50,376.,END+1.))
 base=outer-union([opening,head_cavity(),slim_female_at(TOP),cyl(BORE/2,TOP-1,388.),usb_clearance()]+[rail_poly(t,.20)for t in(-1,1)])
 seats=[]
 for x in (-6.3,6.3):
  for z in (BOARD0+1.,BOARD0+16.):
   support=Manifold.batch_hull([box(x-.5,x+.5,-25,-24,z-15,z-.45),box(x-.5,x+.5,BOARD_Y-.8,BOARD_Y,z-.45,z+.45)])^outer
   seats.append(support)
 base=union([base]+seats)-latch_pocket()
 return union([base,board_corner_guides(),board_release_clip()]).simplify(1e-5)

def head_cover():
 shell=head_outer()-head_cavity()
 lid=(shell^slide_shear(box(-50,50,4.95,50,376.25,END+1.)))-usb_clearance()
 return union([lid]+[rail_poly(t,0.)for t in(-1,1)]+[latch_nub()]).simplify(1e-5)

def socket_carrier():
 # One thin, rounded recessed-switch switch plate. Bought switch/socket/keycap are
 # installed after this plate is in its track; no bulky cassette or keeper.
 plate=rr(16.4,17.2,.8,0.,1.3)-box(-7.,7.,-7.,7.,-.1,1.5)
 tongue=along_button_y(rail_profile(),2.,8.)
 return union([plate,tongue,tongue.mirror((1,0,0))])

def cassette_on_handle(m,angle,z):return mount_local(m,angle,z)

def button_coupon():
 # Actual curved thumb pocket cut from the new stem, with a flat test backing.
 z=HAND_BUTTONS[0][2];angle=HAND_BUTTONS[0][1]
 piece=button_pad(angle,z)
 piece=b.spin(piece.translate((0,0,-z)),-angle)
 piece=piece.transform(np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,-BUTTON_ORIGIN]],float))
 back=box(-9.5,9.5,-11.,11.,-6.5,-4.5)
 return (piece+back)-cyl(3.2,-8.,3.)

def battery_sled():
 # Open ladder: two thin rails and three short bridges, not a solid tray slab.
 pieces=[box(-10.3,-9.3,-4.1,-2.9,13.,58.),box(9.3,10.3,-4.1,-2.9,13.,58.)]
 pieces += [box(-10.3,10.3,-4.1,-2.9,z,z+1.2) for z in (13.,34.,56.8)]
 pieces += [box(-10.3,10.3,-4.1,3.5,13.,14.2)]
 # Shave only the outer rear corners to clear the new oval inner wall.
 inner=union([Manifold.batch_hull([cyl(radius(z)-GRIP_WALL-.15,z,z+.015).scale(((grip_xradius(z)-GRIP_WALL-.15)/(radius(z)-GRIP_WALL-.15),1.,1.))for z in [float(a),float(a+1.01)]])for a in np.arange(12.,59.,1.)])
 return union(pieces)^inner

def loop_socket_coupon():
 z=LOOP_MOUNTS[1]
 return loop_receiver(z)

def loop_foot_coupon():
 z=LOOP_MOUNTS[1];r=loop_mount_radius(z)
 return removable_loop()^box(-12.,12.,-30.,-r+5.,z-18.,z+5.)

def existing_handle(right=False):
 sp=importlib.util.spec_from_file_location('frozen_v2',SUPPORT/'wand_cad.py');v2=importlib.util.module_from_spec(sp);sp.loader.exec_module(v2)
 return v2.handle_left(right)

def measure(m):
 tri=b.canonical_triangles(m)
 return b.mesh_checks(tri,len(m.decompose()))

def write_new(p,data):
 with p.open('xb') as f:f.write(data)
 assert p.read_bytes()==data

def build(out):
 if out is not None:out.mkdir(parents=True,exist_ok=False)
 models={'Handle_Left':handle_left(),'Handle_Right':handle_left(True),'Removable_Finger_Loop':removable_loop(),'Loop_Socket_Coupon':loop_socket_coupon(),'Loop_Foot_Coupon':loop_foot_coupon(),'Existing_Handle_Left':existing_handle(),'Existing_Handle_Right':existing_handle(True),'Lower_Shaft_Existing_Handle':lower_shaft(140.), 'Lower_Shaft':lower_shaft(),'Upper_Shaft':upper_shaft(),'Sense_Head_Base':head_base(),'Sense_Sliding_Cover':head_cover(),'Battery_Twist_Cap':bottom_cap(),'Battery_Sled':battery_sled(),'Choc_Recessed_Plate':socket_carrier(),'Button_Mount_Coupon':button_coupon(),'Fit_Test_Male':(cyl(JOINT_R,TOP-12,TOP-.2)+slim_male_at(TOP))-cyl(BORE/2,TOP-13,TOP+18),'Fit_Test_Female':cyl(JOINT_R,TOP,TOP+20)-slim_female_at(TOP)-cyl(BORE/2,TOP-1,TOP+21)}
 records=[]
 for name,m in models.items():
  # Remove coincident Boolean seams before triangle export; surface motion is
  # at most 0.001 mm in the five changed mount parts; other parts retain 0.00001 mm.
  if name in ['Handle_Left','Handle_Right','Removable_Finger_Loop','Loop_Socket_Coupon','Loop_Foot_Coupon','Lower_Shaft_Existing_Handle','Lower_Shaft','Upper_Shaft']:m=m.as_original().simplify(.001 if name in ['Handle_Left','Handle_Right','Removable_Finger_Loop','Loop_Socket_Coupon','Loop_Foot_Coupon'] else 1e-5);models[name]=m
  if m.status()!=mf.Error.NoError:raise RuntimeError((name,str(m.status())))
  rot=(0,0,0)
  # Cover prints outer crown down; tiny plate/carrier prints flat, every hole vertical.
  if name=='Sense_Sliding_Cover':rot=(-math.degrees(math.atan2(37.88,18.1)),0,0)
  if name=='Sense_Head_Base':rot=(0,0,0)
  if name in ['Removable_Finger_Loop','Loop_Foot_Coupon']:rot=(0,-90,0)
  if name=='Battery_Sled':rot=(90,0,0)
  # Plate XY face is already horizontal. Coupon prints on its broad backing.
  if name=='Choc_Recessed_Plate':rot=(180,0,0)
  if name=='Button_Mount_Coupon':rot=(0,0,0)
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
 wire=cyl(4.95,61,TOP+16)
 checks['wire_probe_9_9mm']={n:round((m^wire).volume(),6) for n,m in models.items() if n in ['Handle_Left','Lower_Shaft','Upper_Shaft']}
 checks['same_handle_connector']=round(((models['Handle_Left']^box(-30,30,-30,30,159.0,177.))-(models['Handle_Right']^box(-30,30,-30,30,159.,177.))).volume(),6)
 checks['button_branch_6mm']={name:round((models['Handle_Left']^branch(a,z,2.7)).volume(),6) for name,a,z in HAND_BUTTONS}
 checks['cap_handle_locked']=round((models['Handle_Left']^models['Battery_Twist_Cap']).volume(),6)
 checks['sled_handle_clearance']=round((models['Handle_Left']^models['Battery_Sled']).volume(),6)
 checks['battery_envelope_overlap']=round((models['Handle_Left']^rr(20.4,6.4,1.5,14.5,56.5)).volume(),6)
 board=box(-8.9,8.9,BOARD_Y,BOARD_Y+BOARD_T,BOARD0,BOARD0+21.)
 solder=box(-5.4,5.4,BOARD_Y-6.,BOARD_Y-.25,BOARD0+3,BOARD0+18)
 checks['button_plate_coupon_clearance']=round((models['Choc_Recessed_Plate']^models['Button_Mount_Coupon']).volume(),6)
 checks['board_outline']={n:round((models[n]^board).volume(),6) for n in ['Sense_Head_Base','Sense_Sliding_Cover']}
 checks['underside_solder_cavity']={n:round((models[n]^solder).volume(),6) for n in ['Sense_Head_Base','Sense_Sliding_Cover']}
 report={'version':'Print V19 candidate','design_revision':'S410-R15','head_shape':'rounded-plumbob','head_size_mm':[40.,37.,58.],'board_z0_mm':BOARD0,'board_y_mm':BOARD_Y,'board_thickness_mm':BOARD_T,'board_slot_mm':BOARD_SLOT,'board_side_gap_mm':BOARD_SIDE_GAP,'retention':'fixed upper edge pockets, corner guides and lower bridge spring clip','cover_slide_vector':[0.,SLIDE_SLOPE,1.],'length_mm':END,'handle_length_mm':HANDLE_END,'existing_handle_length_mm':140.,'rounding_mm':TIP_ROUND,'joint_type':'38-degree bayonet at all three shaft joints','wire_bore_mm':BORE,'shaft_wall_mm':SHAFT_WALL,'minimum_wire_route_mm':BORE,'helix':{'directions':[1,-1],'pitch_mm':[90.,72.],'height_mm':1.2},'shaft_core_monotonic':True,'wire_count_full':8,'wire_count_shared_ground':6,'hand_buttons':HAND_BUTTONS,'button_standoffs_mm':{'thumb':0.,'index':0.,'middle':0.},'button_insert_origin_mm':BUTTON_ORIGIN,'button_insert_size_mm':[16.4,17.2,2.5],'button_plate_face_mm':1.3,'button_insertion_direction':'radially inward with side claws spread','button_slide_mm':0.,'button_socket_retention':'recessed internal seat and small integral claws; wires carry no mounting load','button_surround_mm':[0.,0.],'button_recess_increase_mm':3.4,'external_square_surround':False,'button_mount_style':'recessed socket seat with tiny side retaining claws; no projecting collar','keycap_reference_mm':[16.6,17.5,5.2],'lower_handle_join':'matching direct inward arms with broad recessed seats and enlarged captured pegs','loop_seat_mm':[LOOP_SEAT_WIDTH,LOOP_SEAT_HEIGHT,1.2],'loop_neck_diameter_mm':2*LOOP_NECK_RADIUS,'loop_head_width_mm':2*LOOP_HEAD_RADIUS,'loop_shift_mm':LOOP_SHIFT,'removable_loop':{'mounts_z_mm':LOOP_MOUNTS,'release_slide_mm':LOOP_SLIDE,'twist_deg':LOOP_TWIST,'cam_rise_mm':LOOP_CAM_RISE,'entry_clockwise_deg_from_tip':LOOP_TWIST,'preload_deflection_mm':LOOP_PRELOAD,'release_deflection_mm':LOOP_RELEASE_DEFLECTION,'clearance_mm':LOOP_TRACK_GAP,'receiver_outside_original_surface_mm3':0.,'stem_mount_type':'recessed keyhole cam sockets and broad matching shallow seats; all pegs and release hardware on removable loop','plane':'YZ unchanged; no rotation','attach_vector':[0,0,1],'release_vector':[0,0,-1],'unlock_before_lowering':True,'upright_load_stop':'closed upper receiver ends; independent of release tongue','retention':'radial keyhole entry, 4mm upward slide then 12-degree left cam turn; handle-carried release catch; no external stem mounts'},'loop_path_points':LOOP_POINTS,'loop_air_ports':loop_air_ports(),'airflow_direction':'outside loop to inner finger-contact surface','grip_wall_mm':GRIP_WALL,'loop_wall_mm':LOOP_WALL,'grip_diameter_reduction_mm':2*GRIP_REDUCTION,'loop_section_mm':[LOOP_WIDTH,2*LOOP_RADIUS],'loop_vent_count':0,'loop_solid_band':True,'loop_band_section_mm':[7.,4.],'grip_cross_section':'oval around battery, circular above; 5mm shallower through hand area','design_principles':PRINCIPLES,'body_slots':{zone:slot_locations(zone) for zone in ['grip','lower','upper']},'solid_spine_width_mm':SPINE_WIDTH,'solid_spine_depth_mm':SPINE_DEPTH,'grip_rail_depth_mm':GRIP_RAIL_DEPTH,'rail_edge_radius_mm':.38,'solid_spine_angles_deg':[0.,90.,180.,270.],'window_architecture':'curved leaf cells with rounded intersections and printable roofs, four wider/deeper rounded axial rails, full original spiral strips','perforation_policy':'regular broad windows in a ribbed shell; preserve full raised helix, four axial rails, short cell connections and solid hardware zones','head_hollowing':'retained hollow V6 shell and rail reinforcement, with self-supporting pocket struts','cap_floor_mm':1.2,'weight_goal_g':80.,'weight_ceiling_g':100.,'battery':BATTERY,'checks':checks,'parts':records,'physical_fit_verified':False}
 assert all(abs(v)<.01 for v in checks['wire_probe_9_9mm'].values()), 'Main bore blocked'
 assert all(abs(v)<.01 for v in checks['button_branch_6mm'].values()), 'Button outlet blocked'
 assert abs(checks['Sense_Head_Base__Sense_Sliding_Cover'])<.01, 'Cover collision'
 assert abs(checks['button_plate_coupon_clearance'])<.01, 'Plate/receiver collision'
 assert checks['cap_handle_locked']<.001 and checks['battery_envelope_overlap']<.001 and checks['sled_handle_clearance']<.001, ('Cell/cap/sled clearance',checks['cap_handle_locked'],checks['battery_envelope_overlap'],checks['sled_handle_clearance'])
 assert all(abs(v)<.001 for v in checks['board_outline'].values()), 'Board collision'
 assert all(abs(v)<.001 for v in checks['underside_solder_cavity'].values()), 'Solder clearance collision'
 report['source']={__import__('os').path.relpath(p,HERE):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),SUPPORT/'reference/wand_cad.py',SUPPORT/'reference/dimensions.json',SUPPORT/'wand_cad.py',HERE/'design-principles.json']}
 report['window_open_area_mm2']={zone:round(sum(a['area_mm2'] for a in window_regions(zone)),3) for zone in ['grip','lower','upper']}
 report['retention_highlights']={}
 for name,m in [('Corner_guides',board_corner_guides()),('Release_clip',board_release_clip())]:
  mesh=m.to_mesh();report['retention_highlights'][name]={'assembly_vertices':np.asarray(mesh.vert_properties)[:,:3].tolist(),'assembly_faces':np.asarray(mesh.tri_verts).tolist()}
 if out is None:assert json.loads((HERE/'exports/manifest.json').read_text())==json.loads(json.dumps(report)), 'Stale geometry manifest'
 else:write_new(out/'manifest.json',(json.dumps(report,separators=(',',':'))+'\n').encode())
 print(json.dumps({'out':str(out),'checks':checks,'parts':{r['name']:r['checks'] for r in records}},indent=2))
 return models,report

if __name__=='__main__':
 ap=argparse.ArgumentParser();group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--out',type=Path);group.add_argument('--check',action='store_true');args=ap.parse_args();build(None if args.check else args.out)
