# Adapted from V20 check_sliced_paths.py: check the unchanged V20 grips and loop in this new plate.
from pathlib import Path
import json,zipfile,re,math,collections,numpy as np,xml.etree.ElementTree as E
import argparse,hashlib,importlib.util
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--project',default='Print-Shard-Tube-complete.3mf');args=ap.parse_args()
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sp=importlib.util.spec_from_file_location('vent_cad',HERE.parent/'v20/wand_cad.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
M=json.loads((HERE.parent/'v20/exports/manifest.json').read_text());P={p['name']:p for p in M['parts']}
entry=json.loads((HERE/'exports/projects.json').read_text())['continuous']['complete'];layout={str(i)+':'+name:pos for i,(name,pos) in enumerate(zip(entry['part_names'],entry['positions']))}
PROJECT=ROOT/'magic-wand-3d-models'/args.project
# Sample each extruding straight line and G2/G3 arc, then map printer XYZ to assembly XYZ.
with zipfile.ZipFile(PROJECT) as z:gcode=z.read('Metadata/plate_1.gcode').decode()
features=collections.Counter();points=[];feat='';pos=np.zeros(3);relativeE=True;lastE=0
for line in gcode.splitlines():
 if line.startswith('; FEATURE:'):feat=line[11:].strip();continue
 if line.startswith('M83'):relativeE=True
 if line.startswith('M82'):relativeE=False
 raw=line.split(';')[0].strip();t=raw.split()
 if not t:continue
 if t[0]=='G92':
  for v in t[1:]:
   if v.startswith('E'):lastE=float(v[1:])
  continue
 if t[0] not in ('G0','G1','G2','G3'):continue
 v={x[0]:float(x[1:]) for x in t[1:] if len(x)>1 and x[0] in 'XYZEIJFR'}
 new=np.array([v.get(k,pos[j]) for j,k in enumerate('XYZ')]);de=v.get('E',0) if relativeE else v.get('E',lastE)-lastE
 if not relativeE:lastE=v.get('E',lastE)
 if de>0 and np.linalg.norm(new-pos)>.001 and feat not in ('Custom',''):
  if t[0] in ('G2','G3') and ('I' in v or 'J' in v):
   cen=pos[:2]+[v.get('I',0),v.get('J',0)];r=np.linalg.norm(pos[:2]-cen);a=math.atan2(pos[1]-cen[1],pos[0]-cen[0]);b=math.atan2(new[1]-cen[1],new[0]-cen[0]);da=(b-a)%(2*math.pi)
   if t[0]=='G2':da=-((a-b)%(2*math.pi))
   n=max(2,int(math.ceil(abs(da)*r/.5)));f=np.linspace(0,1,n);aa=a+da*f;ps=np.c_[cen[0]+r*np.cos(aa),cen[1]+r*np.sin(aa),pos[2]+(new[2]-pos[2])*f]
  else:
   n=max(2,int(math.ceil(np.linalg.norm(new-pos)/.5)));ps=pos+(new-pos)*np.linspace(0,1,n)[:,None]
  if len(ps):points.append((feat,ps));features[feat]+=len(ps)
 pos=new
A=np.concatenate([p for f,p in points]);F=np.concatenate([np.repeat(f,len(p)) for f,p in points]);checks={}
for label,ctr in layout.items():
 name=label.split(':',1)[1]
 if name not in ['Handle_Left','Handle_Right','Removable_Finger_Loop']:continue
 t=np.array(P[name]['print_to_assembly']);printer=A+np.array([0.,2.,0.])-np.array([*ctr,0]);xyz=printer@t[:3,:3].T+t[:3,3];x,y,z=xyz.T
 if name.startswith('Handle_'):z0,z1=61,173.5
 elif name=='Lower_Shaft':z0,z1=160.5,259.5
 elif name=='Upper_Shaft':z0,z1=246.5,365.5
 elif name.startswith('Sense_'):z0,z1=352.5,374.8
 else:z0,z1=0.,0.
 # The sliding head cover starts above the neck: do not test an imaginary
 # neck below its physical extent, where a neighbouring print may sit.
 part_z=np.array(P[name]['assembly_vertices'])[:,2];z0=max(z0,float(part_z.min()));z1=min(z1,float(part_z.max()))
 areas={'main_9mm_clearance':(x*x+y*y<4.5**2)&(z>z0)&(z<z1)}
 if name.startswith('Handle_'):
  areas['battery_clearance']=(abs(x)<9.3)&(abs(y)<3.5)&(z>15)&(z<58)
  for k,base_z in enumerate(c.LOOP_MOUNTS):
   r0=c.loop_mount_radius(base_z)
   for angle in [0.,3.,6.,9.,12.]:
    aa=math.radians(angle);xl=x*math.cos(aa)-y*math.sin(aa);yl=x*math.sin(aa)+y*math.cos(aa);dz=-c.LOOP_CAM_RISE*angle/c.LOOP_TWIST
    areas['loop_mount_'+str(k)+'_cam_'+str(angle)]=(xl*xl+(z-base_z-dz)**2<2.3**2)&(yl>-r0+c.LOOP_HEAD_INNER-c.LOOP_HEAD_DEPTH+.2)&(yl<-r0+c.LOOP_HEAD_INNER-.2)
    areas['loop_mount_'+str(k)+'_broad_shoulder_'+str(angle)]=(abs(xl)<3.5)&(abs(z-base_z-dz)<3.)&(yl>-r0+.25)&(yl<-r0+1.)
   aa=math.radians(c.LOOP_TWIST);xl=x*math.cos(aa)-y*math.sin(aa);yl=x*math.sin(aa)+y*math.cos(aa)
   for down in [1.,2.,3.,4.]:
    zz=base_z-c.LOOP_CAM_RISE-down
    areas['loop_mount_'+str(k)+'_lift_'+str(down)]=(xl*xl+(z-zz)**2<2.3**2)&(yl>-r0+c.LOOP_HEAD_INNER-c.LOOP_HEAD_DEPTH+.2)&(yl<-r0+c.LOOP_HEAD_INNER-.2)
   zz=base_z-c.LOOP_CAM_RISE-c.LOOP_SLIDE
   areas['loop_mount_'+str(k)+'_entry']=(xl*xl+(z-zz)**2<1.8**2)&(yl>-r0-.3)&(yl<-r0+c.LOOP_HEAD_INNER-.2)
  r0=c.loop_mount_radius(c.LOOP_MOUNTS[1]);zz=c.LOOP_MOUNTS[1]
  areas['recessed_release_seat']=(x>4.5)&(x<6.5)&(y>-r0+.8)&(y<-r0+1.3)&(z>zz-12.)&(z<zz-9.)
  for n,a,zz in M['hand_buttons']:
   if name.endswith('Right'):a=-a
   a=math.radians(a);tangent=x*math.cos(a)-y*math.sin(a);radial=x*math.sin(a)+y*math.cos(a)
   areas[n+'_6mm_clearance']=(tangent*tangent+(z-zz)**2<3**2)&(radial>0)&(radial<18)
   areas[n+'_socket_clearance']=(tangent>-8.1)&(tangent<-1.5)&(zz-z>-7.6)&(zz-z<2.2)&(radial>M['button_insert_origin_mm']-4.2)&(radial<M['button_insert_origin_mm']-2.8)
   areas[n+'_claw_release_gap']=(abs(tangent)>7.5)&(abs(tangent)<8.1)&(zz-z>4.5)&(zz-z<7.5)&(radial>M['button_insert_origin_mm']-1.5)&(radial<M['button_insert_origin_mm']-.9)
 if name.startswith('Handle_') or name in ('Lower_Shaft','Upper_Shaft'):
  zone='grip' if name.startswith('Handle_') else 'lower' if name=='Lower_Shaft' else 'upper'
  for k,p in enumerate(c.slot_locations(zone)):
   ang=math.radians(p['angle']);zz=p['z'];rad0=p['outer_radius'];tang=x*math.cos(ang)-y*math.sin(ang);rad=x*math.sin(ang)+y*math.cos(ang)
   # Probe through the actual tube skin, not unrelated removable support
   # standing 2 mm outside its mouth. The raised helix is avoided by design.
   areas['body_slot_'+str(k)]=(tang*tang+(z-zz)**2<.7**2)&(rad>rad0-2.5)&(rad<rad0+.3)
 # Check the interiors of the actual curved outlines, beyond centre probes.
  rgrid=np.arange(float(z.min())-1,float(z.max())+2,1.)
  rrgrid=np.array([c.radius(float(zz)) if zone=='grip' else c.shaft_radius(float(zz)) for zz in rgrid]);rrs=np.interp(z,rgrid,rrgrid);radial=np.sqrt(x*x+y*y)
  skin=(radial>rrs-1.7)&(radial<rrs+.3)
  for k,p in enumerate(c.window_regions(zone)):
   cs=c.CrossSection(p['outline_xz_mm']).offset(-.85,c.mf.JoinType.Round)
   lo,za,hi,zb=cs.bounds();ii=np.where(skin&(z>za)&(z<zb))[0]
   theta=(np.degrees(np.arctan2(x[ii],y[ii]))-p['angle']+180)%360-180;arc=np.radians(theta)*p['ref_radius'];valid=(arc>lo)&(arc<hi);ii=ii[valid];arc=arc[valid];inside=np.zeros(len(ii),bool)
   for poly in cs.to_polygons():
    local=np.zeros(len(ii),bool)
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
     crosses=((a[1]>z[ii])!=(b[1]>z[ii]))
     if abs(b[1]-a[1])>1e-10:local ^= crosses & (arc < (b[0]-a[0])*(z[ii]-a[1])/(b[1]-a[1])+a[0])
    inside ^= local
   mask=np.zeros(len(A),bool);mask[ii[inside]]=True;areas['whole_window_'+str(k)]=mask
 if name=='Removable_Finger_Loop':
  xyz_points=np.c_[x,y,z]
  for i,p in enumerate(c.loop_air_ports()):
   delta=xyz_points-np.array(p['center']);n=np.array(p['inward']);axial=delta@n;cross=delta-axial[:,None]*n
   areas['loop_contact_airflow_'+str(i)]=(np.sum(cross*cross,axis=1)<.8**2)&(abs(axial)<8.)
   tangent=delta@np.array(p['tangent']);xx=delta[:,0]
   areas['loop_broad_face_'+str(i)]=((tangent/6.5)**2+(axial/1.5)**2<1)&(abs(xx)<9.3)
 if name.startswith('Sense_'):
  areas['forward_wire_5_4mm']=(x*x+(y-2.)**2<2.7**2)&(z>375)&(z<387.5)
  areas['pcb_inner_clearance']=(abs(x)<8.6)&(y>M['board_y_mm']+.3)&(y<M['board_y_mm']+M['board_thickness_mm']-.3)&(z>M['board_z0_mm']+.3)&(z<M['board_z0_mm']+20.7)
  areas['central_solder_space']=(abs(x)<5.1)&(y>M['board_y_mm']-5.5)&(y<M['board_y_mm']-.4)&(z>M['board_z0_mm']+3.5)&(z<M['board_z0_mm']+17.5)
  areas['usb_plug_12x6']=(abs(x)<5.7)&(y>M['board_y_mm']-.8)&(y<M['board_y_mm']+4.8)&(z>M['board_z0_mm']+21.3)&(z<411.)
 checks[name]={k:dict(collections.Counter(F[mask])) for k,mask in areas.items()}
report={'extruder_offset_mm':[0,2], 'sample_step_mm':.5,'path_samples':len(A),'features':dict(features),'clearance_extrusion_samples':checks,'project_sha256':hashlib.sha256(PROJECT.read_bytes()).hexdigest(),'note':'Checks extrusion centerlines through both V19 handed handles and detachable loop in conservative interior clearances; excludes custom start/end G-code. Not a physical-print test.'}
print(json.dumps({'path_samples':len(A),'clearances':checks},indent=2))

assert all(not features for parts in checks.values() for features in parts.values()), 'Extrusion in protected clearance'

with args.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
