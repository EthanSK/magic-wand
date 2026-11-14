"""Static packing/lead-route evidence. Run with the project CAD runtime on PYTHONPATH."""
import sys,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import holder38 as d
key,working,_,_=d.geometry()
hw=d.hardware(); ay=d.h32.ACTUATOR_Y
rigid_names=('board','sockets','housing','plug','switch','terminals','plunger','fasteners')
def bb(s): return [round(float(x),5) for x in s.bounding_box()]
def vol(s): return round(float(s.volume()),6)
def rotate(s,deg):return s.translate((0.,-ay,0.)).rotate((0.,0.,deg)).translate((0.,ay,0.))
def keys(extra=0.):
 solids=[]
 for i,sign in ((0,-1),(2,1),(3,-1),(4,1)):
  # Restore exact R37 lateral spacing, independent of the new narrower choice.
  shift=sign*(d.R37_KEY_X-d.KEY_X+extra)
  solids.extend(working[f'key_{i}_{p}'].translate((shift,0.,0.)) for p in ('switch','maximum_socket','cap_travel'))
 return d.union(solids)
chocs=keys(); rod=d.rod()
grove={name:d.r.world(f(),0.) for name,f in {'board':d.grove.board,'housing':d.grove.housing,'plug':d.grove.plug,'components':d.grove.components,'lead':d.grove.lead}.items()}
res={'status':'static packing probe only; no model changes or print approval','source_sha256':hashlib.sha256((ROOT/'holder38.py').read_bytes()).hexdigest(),'rod_aabb_mm':bb(rod),'grove_original_aabbs_mm':{n:bb(v) for n,v in grove.items()},'r37_choc_spacing_x_mm':d.R37_KEY_X,'results':[]}
for zlift in (0.,d.OP1_LIFT):
 for yaw in (-90.,90.):
  p={n:rotate(hw[n].translate((0.,0.,zlift-d.OP1_LIFT)),yaw) for n in rigid_names}
  group=d.union(p.values())
  overlaps={n:{'choc_hardware_and_cap_travel':vol(s^chocs),'rod':vol(s^rod),'grove_original':vol(s^d.union(grove.values()))} for n,s in p.items()}
  lo,hi=0.,20.
  for _ in range(15):
   mid=(lo+hi)/2
   if (group^keys(mid)).volume()>1e-4:lo=mid
   else:hi=mid
  res['results'].append({'yaw_deg':yaw,'op1_seat_lift_mm':zlift,'op1_rigid_aabb_mm':bb(group),'overlap_mm3':overlaps,'minimum_extra_symmetrical_key_shift_mm_for_zero_rigid_overlap':round(hi,3),'width_increase_for_that_shift_mm':round(2*hi,3),'current_fit':all(max(v.values())<1e-4 for v in overlaps.values()),'wire_route_verified':False})
# Independently model a two-wire bundle emerging from the actual longitudinal end face.
# Photo supports this outlet region; exact crimp exit height/bend stiffness remain unmeasured.
import manifold3d as mf
parts=d.hardware(); plugbb=parts["plug"].bounding_box(); exit_y=plugbb[4]; exit_z=(plugbb[2]+plugbb[5])/2
points=[(0.,exit_y-.2,exit_z),(0.,exit_y+.8,exit_z),(.5,exit_y+1.4,exit_z),
        (1.4,exit_y+1.7,exit_z),(3.5,exit_y+1.7,exit_z),(5.8,exit_y+1.7,exit_z),
        (7.3,exit_y+1.7,exit_z-1.2),(8.1,exit_y+1.7,exit_z-3.2),(8.1,exit_y+1.7,exit_z-6.8)]
balls=[mf.Manifold.sphere(1.3,24).translate(x) for x in points]
wire=d.union(mf.Manifold.batch_hull([a,b]) for a,b in zip(balls,balls[1:]))
fixed=key+chocs
path_overlaps=[]
for i in range(33):
 z=i*.5
 o=wire.translate((0.,0.,z))^fixed
 path_overlaps.append({"lift_mm":z,"overlap_mm3":vol(o),"bounds_mm":bb(o) if o.volume()>1e-6 else None})
res["longitudinal_wire_probe"]={"radius_mm":1.3,"plug_aabb_mm":bb(parts["plug"]),"path_points_mm":points,
 "wire_aabb_mm":bb(wire),"rod_overlap_mm3":vol(wire^rod),"seated_carrier_overlap_mm3":vol(wire^key),
 "seated_choc_overlap_mm3":vol(wire^chocs),"insertion_path":path_overlaps,
 "physical_route_verified":False,"direction_basis":"manufacturer kit photo; exact outlet depth and bend stiffness remain unmeasured"}
path=ROOT/'evidence'/'packing-probe.json'
path.write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res,indent=2))
