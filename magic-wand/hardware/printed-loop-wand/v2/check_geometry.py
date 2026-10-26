"""Geometric fit checks; this does not simulate PETG force or establish physical fit."""
from pathlib import Path
import importlib.util,json,math,hashlib,numpy as np
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('print_v2_cad',HERE/'wand_cad.py');c=importlib.util.module_from_spec(sp);sp.loader.exec_module(c)
base,cover=c.head_base(),c.head_cover();clip=c.board_release_clip();guides=c.board_corner_guides()
board=c.box(-8.9,8.9,c.BOARD_Y,c.BOARD_Y+c.BOARD_T,c.BOARD0,c.BOARD0+21.)
# A static solid test: clear at rest; stops reached after designed small clearances.
checks={'resting_board_overlap_mm3':(base^board).volume(),'body_cover_overlap_mm3':(base^cover).volume()}
checks['rigid_board_stop_overlap_mm3']={}
for name,delta in {'left':(-.4,0,0),'right':(.4,0,0),'up':(0,0,.4),'down':(0,0,-.4),'out_of_seats':(0,.5,0)}.items():
 checks['rigid_board_stop_overlap_mm3'][name]=(base^board.translate(delta)).volume()
# Board removal is a pivot around the USB end after the lower spring is deflected.
# Flex is NOT simulated: explicitly subtract the spring envelope for this clearance test.
rigid=base-clip;pivot=(0,c.BOARD_Y+c.BOARD_T/2,c.BOARD0+21.)
checks['released_board_pivot_overlap_mm3']={}
for a in [0,1,2,3,5,8,10]:
 moved=board.translate(tuple(-v for v in pivot)).rotate((a,0,0)).translate(pivot)
 checks['released_board_pivot_overlap_mm3'][str(a)]=(rigid^moved).volume()
checks['cover_released_slide_overlap_mm3']={str(d):(base^(cover-c.latch_nub()).translate((0,d*c.SLIDE_SLOPE,d))).volume() for d in [.25,.5,1,2,5,10,20,35]}
plug=c.box(-6,6,c.BOARD_Y-1,c.BOARD_Y+5,c.BOARD0+21.2,342.)
solder=c.box(-5.4,5.4,c.BOARD_Y-6,c.BOARD_Y-.25,c.BOARD0+3,c.BOARD0+18)
checks['usb_12x6_plug_overlap_mm3']={'base':(base^plug).volume(),'cover':(cover^plug).volume()}
checks['rear_solder_space_overlap_mm3']={'base':(base^solder).volume(),'cover':(cover^solder).volume()}
checks['head_9mm_wire_probe_overlap_mm3']=(base^c.cyl(4.5,282.5,304.8)).volume()
checks['head_forward_6mm_wire_probe_overlap_mm3']=(base^c.cyl(3.,304.7,318.,y=2.)).volume()
loop=c.b.sweep(c.b.loop_path('oval'),c.b.H['loop_radius'])
checks['thumb_mount']={}
for hand,angle in [('left',90),('right',-90)]:
 front=c.local(c.box(-12,12,16,18.2,-12,12),angle,117.)
 carrier=c.cassette_on_handle(c.socket_carrier()+c.socket_keeper(),angle,117.)
 keycap=c.local(c.box(-10,10,24,34,-10,10),angle,117.)
 envelope=c.union([front,carrier,keycap])
 checks['thumb_mount'][hand]={'loop_overlap_mm3':(envelope^loop).volume(),'minimum_loop_gap_mm':envelope.min_gap(loop,15),'includes':'24mm pad face, actual socket carrier/keeper, conservative 20x20x10mm keycap envelope'}
# Geometric deflection envelope only: no force, strength, or print tolerance simulation.
mesh=clip.refine_to_length(.7).to_mesh();v=np.array(mesh.vert_properties[:,:3],dtype=np.float32)
v[:,2]-=1.3*np.maximum(0,1-(v[:,0]/10.)**2)**2
flexed=c.Manifold(c.mf.Mesh(v,np.asarray(mesh.tri_verts,dtype=np.uint32)))
checks['flexed_clip_status']=str(flexed.status())
checks['board_pivot_with_1_3mm_clip_deflection_mm3']={}
for a in [0,1,2,3,5,8,10]:
 moved=board.translate(tuple(-v for v in pivot)).rotate((a,0,0)).translate(pivot)
 checks['board_pivot_with_1_3mm_clip_deflection_mm3'][str(a)]=(flexed^moved).volume()
checks['physical_fit_verified']=False
print(json.dumps(checks,indent=2))
assert abs(checks['resting_board_overlap_mm3'])<.0001
assert all(v>0 for v in checks['rigid_board_stop_overlap_mm3'].values())
assert all(abs(v)<.001 for v in checks['released_board_pivot_overlap_mm3'].values())
assert all(abs(v)<.001 for v in checks['cover_released_slide_overlap_mm3'].values())
assert all(abs(v)<.001 for v in checks['usb_12x6_plug_overlap_mm3'].values())
assert all(p['minimum_loop_gap_mm']>=4.9 and abs(p['loop_overlap_mm3'])<.001 for p in checks['thumb_mount'].values())

assert all(abs(v)<.001 for v in checks['board_pivot_with_1_3mm_clip_deflection_mm3'].values())
assert abs(checks['head_forward_6mm_wire_probe_overlap_mm3'])<.001
