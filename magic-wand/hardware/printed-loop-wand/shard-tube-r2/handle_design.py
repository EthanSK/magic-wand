"""Straight upward captured hooks and a separate quarter-turn cross key.

All geometry is assembled in V20 coordinates. This module does not patch V20.
A fresh CAD module is supplied by the owning Shard R2 generator. Dimensions
are nominal starting fits; physical printed fit/strength remain unverified.
"""
from functools import lru_cache
import math
import numpy as np
from manifold3d import Manifold, CrossSection

MOUNTS=(14.,104.)
SLIDE=4.
GAP=.4
BAND_WIDTH=9.
HEAD_DEPTH=(1.6,3.)
HEAD_HEIGHT=4.
WING_X=(2.,4.5)
NECK_HALF=2.3
KEY_Z=110.8
KEY_RADIUS=1.5
KEY_GAP=.4
KEY_SEAT_OUT=.65
KEY_INDEX_GAP=.25
KEY_INDEX_AXIAL_GAP=.12

class HandleDesign:
 def __init__(self,c):
  self.c=c
  self.key_y=-c.radius(MOUNTS[1])

 def front(self,x,z):
  c=self.c;r=c.radius(z);rx=c.grip_xradius(z)
  return -r*math.sqrt(max(.001,1.-(x/rx)**2))

 def curved_strip(self,x0,x1,d0,d1,z0,z1,zref):
  # Depth is measured inward from the curved, undecorated stem surface.
  # Lateral hook wings avoid a deep flange across the central wire bore.
  xs=np.linspace(x0,x1,max(3,int(math.ceil((x1-x0)/.2))+1))
  pts=[(float(x),self.front(float(x),zref)+d0) for x in xs]
  pts += [(float(x),self.front(float(x),zref)+d1) for x in xs[::-1]]
  return Manifold.extrude(CrossSection([pts]),z1-z0).translate((0,0,z0))

 def rounded_outline(self,w,h,z,r=1.2):
  # Rounded XZ outline, with deliberately generous radial extent.
  return self.c.rr(w,h,r,-25.,25.).rotate((90.,0.,0.)).translate((0,-self.c.radius(z),z))

 def shoulder(self,z,g=0.):
  return self.curved_strip(-4.5-g,4.5+g,-2.5-g,-.35+g,z-4.-g,z+4.+g,z)^self.rounded_outline(9.+2*g,8.+2*g,z,1.2)

 def neck(self,z,g=0.,travel=0.):
  return self.curved_strip(-NECK_HALF-g,NECK_HALF+g,-2.5-g,1.9+g,z-2.-g-travel,z+2.+g,z)

 def wings(self,z,g=0.,entry=False,travel=0.):
  a,b=WING_X;d0=-20. if entry else HEAD_DEPTH[0]-g;d1=HEAD_DEPTH[1]+g
  negative=self.curved_strip(-b-g,-a+g,d0,d1,z-2.-g-travel,z+2.+g,z)
  if g or entry:
   positive=self.curved_strip(1.6-g,b+g,d0,d1,z-2.-g-travel,z+2.+g,z)
  else:
   # Printer Z is assembly X. Start the far wing within the already-printed
   # neck and grow its inner edge at 0.9 mm per layer-mm: a genuine <=45deg
   # rise in printer coordinates, including the stem's curvature. Retained
   # material outside the neck remains up to the full 1.4 mm head depth.
   xs=np.linspace(1.6,b,31);start=self.front(1.6,z)+1.9
   pts=[(float(x),self.front(float(x),z)+d0)for x in xs]
   pts += [(float(x),min(self.front(float(x),z)+d1,start+.9*(float(x)-1.6)))for x in xs[::-1]]
   positive=Manifold.extrude(CrossSection([pts]),4.).translate((0,0,z-2.))
  return negative+positive

 def upper_key_ear(self,g=0.):
  z=MOUNTS[1]
  # Rounded, thin external continuation of the upper loop end. All of it
  # leaves with the loop; no tab is added to the detached wand.
  ear=self.curved_strip(-4.5-g,4.5+g,-2.5-g,-.35+g,105.5-g,115.+g,z)
  outline=self.c.rr(9.+2*g,9.5+2*g,1.3,-25.,25.).rotate((90.,0.,0.)).translate((0,-self.c.radius(z),110.25))
  return ear^outline

 @lru_cache(None)
 def band(self):
  c=self.c
  points=[list(p) for p in c.LOOP_POINTS]
  for i,z in [(0,MOUNTS[0]),(-1,MOUNTS[1])]:points[i]=[z,-c.radius(z)-2.3]
  path=np.asarray(c.b.catmull_rom(points,spacing=.6),float)
  tangent=np.gradient(path,axis=0);tangent/=np.linalg.norm(tangent,axis=1,keepdims=True)
  tangent[0]=[0.,-1.];tangent[-1]=[0.,1.]
  normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)
  distance=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
  edge=np.minimum(distance,distance[-1]-distance)
  vertices=[]
  for p,n,d in zip(path,normal,edge):
   u=float(np.clip(d/23.,0.,1.));fade=1.-(6*u**5-15*u**4+10*u**3)
   height=4.+4.*fade
   vertices += [(x,p[1]+s*n[1],p[0]+s*n[0])for s,x in c.rounded_band_section(BAND_WIDTH,height)]
  k=len(c.rounded_band_section(9.,4.));tri=[]
  for i in range(len(path)-1):
   a=i*k;b=(i+1)*k
   for j in range(k):j1=(j+1)%k;tri += [(a+j,a+j1,b+j1),(a+j,b+j1,b+j)]
  last=k*(len(path)-1)
  tri += [(0,j+1,j)for j in range(1,k-1)]+[(last,last+j,last+j+1)for j in range(1,k-1)]
  return c.b.closed_mesh(vertices,tri,'constant width solid finger loop')

 def y_cylinder(self,r,d0,d1):
  return self.c.b.cyl_y(r,self.key_y+d0,self.key_y+d1).translate((0,0,KEY_Z))

 def key_entry_hole(self):
  c=self.c
  shaft=self.y_cylinder(KEY_RADIUS+KEY_GAP,-20.,3.2)
  paddle=c.box(-3.2,3.2,self.key_y-20.,self.key_y+3.2,KEY_Z-1.4,KEY_Z+1.4)
  # A real countersink seats the head without forcing its underside onto
  # supports. Only radial clearance is added here; taper stops axial float.
  cone=c.cyl(1.9,1.8,2.8,2.9).rotate((90.,0,0)).translate((0,self.key_y,KEY_Z))
  mouth=self.y_cylinder(2.9,-20.,-2.8)
  return shaft+paddle+cone+mouth

 def key_rotation_pocket(self):
  return self.y_cylinder(3.4,1.,3.2)

 def key_index_notches(self):
  # A broad pair of axial notches seats the vertical paddle in front of
  # the turn chamber. Rotation is physically blocked until the key is
  # deliberately pressed fully inward again; no spring or friction lock.
  return self.c.box(-1.-KEY_INDEX_GAP,1.+KEY_INDEX_GAP,
   self.key_y+1.4-KEY_SEAT_OUT-KEY_INDEX_AXIAL_GAP,self.key_y+1.3,
   KEY_Z-2.8-KEY_INDEX_GAP,KEY_Z+2.8+KEY_INDEX_GAP)

 @lru_cache(None)
 def loop(self):
  c=self.c
  solids=[self.band(),self.upper_key_ear()]
  solids += [self.shoulder(z)+self.neck(z)+self.wings(z)for z in MOUNTS]
  return (c.union(solids)-self.key_entry_hole()).simplify(.001)

 @lru_cache(None)
 def key(self):
  c=self.c
  shaft=self.y_cylinder(KEY_RADIUS,-3.,2.8)
  # A stout radial quarter-turn key. The two wings enter horizontally,
  # turn vertical behind a solid land, and positively retain the key.
  paddle=c.box(-2.8,2.8,self.key_y+1.4,self.key_y+2.8,KEY_Z-1.,KEY_Z+1.)
  # With the inner paddle face on the bed, this 45 degree underside
  # grows from the shaft to a broad head without support on mating faces.
  head=c.cyl(1.5,1.8,2.8,2.5).rotate((90.,0,0)).translate((0,self.key_y,KEY_Z))
  head+=self.y_cylinder(2.5,-5.4,-2.8)
  return (shaft+paddle+head).simplify(.001)

 def key_pose(self,angle=90.,out=None):
  if out is None:out=KEY_SEAT_OUT if abs(angle-90.)<.0001 else 0.
  return self.key().translate((0,-self.key_y,-KEY_Z)).rotate((0,angle,0)).translate((0,self.key_y-out,KEY_Z))

 def loop_pose(self,down=0.,out=0.):
  return self.loop().translate((0,-out,-down))

 @lru_cache(None)
 def receiver_voids(self):
  c=self.c;pieces=[]
  for z in MOUNTS:
   # Extrude the individual XY hook profiles over the exact travel.
   # Never convex-hull the whole T: that would erase its retaining lips.
   pieces += [self.neck(z,GAP,travel=SLIDE),self.wings(z,GAP,travel=SLIDE)]
   pieces.append(self.curved_strip(-4.5-GAP,4.5+GAP,-2.5-GAP,-.35+GAP,z-4.-GAP-SLIDE,z+4.+GAP,z))
   pieces.append(self.wings(z,GAP,entry=True).translate((0,0,-SLIDE)))
  pieces.append(self.curved_strip(-4.5-GAP,4.5+GAP,-2.5-GAP,-.35+GAP,105.5-GAP-SLIDE,115.+GAP,MOUNTS[1]))
  pieces += [self.key_entry_hole(),self.key_rotation_pocket(),self.key_index_notches()]
  return c.union(pieces)

 @lru_cache(None)
 def reinforcement(self):
  c=self.c;pieces=[]
  for z in MOUNTS:
   z1=116. if z==MOUNTS[1]else z+7.
   blank=c.box(-7.2,7.2,-c.radius(z)-3.,-c.radius(z)+6.,z-9.,z1)^c.body(3.2,c.HANDLE_END-.2)
   pieces.append(blank)
  # Owning generator subtracts the new cap, cell and control clearances
  # from this reinforcement along with the grip; the bore is explicit here.
  return (c.union(pieces)-self.receiver_voids()-c.cyl(c.BORE/2,3.,177.)).simplify(.001)

 def check(self,stem,obstacles=None,cap=None):
  c=self.c;obs=stem if obstacles is None else stem+obstacles
  rest=abs((stem^self.loop()).volume())
  slides={str(d):abs((obs^self.loop_pose(float(d))).volume())for d in np.linspace(0.,SLIDE,17)}
  entry={str(d):abs((obs^self.loop_pose(SLIDE,float(d))).volume())for d in np.linspace(0.,18.,37)}
  key_in={str(d):abs(((stem+self.loop())^self.key_pose(0.,float(d))).volume())for d in np.linspace(0.,16.,33)}
  key_turn={str(a):abs(((stem+self.loop())^self.key_pose(float(a),0.)).volume())for a in np.linspace(0.,90.,19)}
  key_seat={str(d):abs(((stem+self.loop())^self.key_pose(90.,float(d))).volume())for d in np.linspace(0.,KEY_SEAT_OUT,14)}
  index_blocks={str(a):abs((stem^self.key_pose(float(a),KEY_SEAT_OUT)).volume())for a in [75.,105.]}
  capture={name:abs((stem^self.loop().translate(delta)).volume())for name,delta in [('out',(0,-1.,0)),('up',(0,0,1.))]}
  locked=self.key_pose()
  keeper_down=abs((locked^self.loop().translate((0,0,-1.))).volume())
  key_out_locked=abs(((stem+self.loop())^locked.translate((0.,-1.,0))).volume())
  key_in_locked=abs(((stem+self.loop())^locked.translate((0.,KEY_SEAT_OUT+1.,0))).volume())
  result={'rest_mm3':rest,'slide_mm3':slides,'radial_entry_mm3':entry,'key_entry_mm3':key_in,'key_quarter_turn_mm3':key_turn,'key_pull_to_index_mm3':key_seat,'key_index_rotation_stops_mm3':index_blocks,'key_press_to_turn_travel_mm':KEY_SEAT_OUT,'rigid_capture_mm3':capture,'keeper_downward_stop_mm3':keeper_down,'key_positive_axial_capture_mm3':{'out_at_1mm':key_out_locked,'in_after_deliberate_press_plus_1mm':key_in_locked},'clearance_per_surface_mm':GAP,'mounts_z_mm':list(MOUNTS),'slide_mm':SLIDE,'loop_print_bed_assembly_x_mm':-4.5,'band_print_bed_gap_mm':0.,'physical_fit_verified':False}
  assert rest<.005 and max(slides.values())<.005 and max(entry.values())<.005,result
  assert max(key_in.values())<.005 and max(key_turn.values())<.005 and max(key_seat.values())<.005,result
  assert min(index_blocks.values())>.1,result
  assert min(capture.values())>1. and keeper_down>.5 and min(key_out_locked,key_in_locked)>.1,result
  if cap is not None:
   result['cap_locked_overlap_mm3']=abs((cap^(self.loop()+locked)).volume())
   result['cap_entry_overlap_mm3']=max(abs((cap^self.loop_pose(float(d))).volume())for d in np.linspace(0.,SLIDE,17))
   result['remove_cap_to_attach']=result['cap_entry_overlap_mm3']>.005
   assert result['cap_locked_overlap_mm3']<.005,result
  return result

 def print_to_assembly(self,name):
  # Loop's entire 9 mm width shares this bed plane; no 14.4 mm pad can
  # lift the band above the bed. Key prints paddle face flat, axis upright.
  if name=='loop':return [[0.,0.,1.,-4.5],[0.,1.,0.,-28.5],[-1.,0.,0.,62.],[0.,0.,0.,1.]]
  if name=='key':return [[1.,0.,0.,0.],[0.,0.,-1.,self.key_y+2.8-KEY_SEAT_OUT],[0.,1.,0.,KEY_Z],[0.,0.,0.,1.]]
  raise ValueError(name)


@lru_cache(None)
def build(c):
 return HandleDesign(c)


def loop(c):return build(c).loop()
def keeper(c):return build(c).key_pose()
def receiver_material(c):return build(c).reinforcement()
def receiver_void(c):return build(c).receiver_voids()
def specs():
 return {'type':'two straight upward captured curved T hooks plus independent radial quarter-turn keeper','mount_centres_z_mm':list(MOUNTS),'upward_slide_mm':SLIDE,'clearance_per_surface_mm':GAP,'band_section_mm':[9.,4.],'loop_width_all_features_mm':9.,'hook_wing_depth_mm':list(HEAD_DEPTH),'hook_wing_thickness_mm':HEAD_DEPTH[1]-HEAD_DEPTH[0],'hook_height_mm':HEAD_HEIGHT,'keeper_shaft_diameter_mm':3.,'keeper_turn_deg':90.,'keeper_centre_z_mm':KEY_Z,'keeper_press_to_turn_travel_mm':KEY_SEAT_OUT,'keeper_index_clearance_mm':KEY_INDEX_GAP,'keeper_retention':'pull outward into positive90degree index notches; press inward before turning to remove','bare_stem_external_mounts':False,'physical_fit_verified':False}

