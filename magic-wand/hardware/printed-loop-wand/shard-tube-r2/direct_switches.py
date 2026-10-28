"""Integral Choc V1 mounting seats; all dimensions in millimetres.

This module creates PRINTED stem material and machining voids only. Purchased
switch/socket/keycap reference solids are separate and must never be exported
as printable parts. No detachable plate, guide track or printed spring claw.

Use pad(c, angle, z) in the grip's union, then subtract void(c, angle, z) from
its FINAL union after rails, loop receivers and all neighbouring seats. Do not
combine this with V20's old receiver_voids() or button_claw_relief().
"""
from __future__ import annotations
import math

FACE_W=16.4
FACE_H=17.2
FACE_T=1.3
SWITCH_OPENING=14.0
HOLES=((0.,0.,1.85),(0.,5.5,1.1),(0.,-5.5,1.1),(-5.9,0.,1.6),(-3.8,-5.,1.6))


def seat_data():
    return {
        'type':'integral_choc_v1_mount',
        'separate_printed_carrier':False,
        'printed_spring_claws':False,
        'printed_guide_tracks':False,
        'face_mm':[FACE_W,FACE_H,FACE_T],
        'opening_mm':[SWITCH_OPENING,SWITCH_OPENING],
        'retention':'purchased Choc switch flange and its own retaining clips engage the integral face',
        'factory_hook_reference':'simplified nominal hooks; exact purchased clip throat and PETG fit must be checked with the coupon',
        'bought_cap_reference_mm':[16.6,17.5],
        'local_axes':'X tangent; Y down wand; Z outward from the unchanged 9.8 mm radial datum',
        'post_holes_xy_radius_mm':[list(p)for p in HOLES],
        'socket_body_clearance_mm':[7.4,10.6,2.6],
        'socket_overall_solder_tab_length_mm':13.15,
        'wire_channel_diameter_mm':2.5,
        'socket_installation':'feed flexible wires into bore, centre socket at local offset[1.5,2.5], lower to +2.0mm, slide to[0,0], then lower posts into the floor; snap purchased switch in last',
        'hardware_sources':[
            'https://www.kailhswitch.com/Content/upload/pdf/201915927/CPG135001D01_-_Red_Linear_Choc.pdf',
            'https://www.kailhswitch.com/Content/upload/pdf/202115927/CPG135001S30-data-sheet.pdf'],
        'fit_boundary':'Nominal manufacturer geometry with FDM clearances; actual switch-clip force, purchased socket revision and PETG retention require the fit coupon.'
    }


def local_pad(c):
    # Rounded root narrows smoothly towards the stem interior; no box surround
    # stands outside the bought cap. Ten quintic stations avoid an abrupt ledge.
    sections=[]
    for i in range(11):
        t=i/10.;u=t*t*t*(10.-15.*t+6.*t*t)
        zz=-6.5+6.5*t
        w=14.8+(FACE_W-14.8)*u
        h=15.8+(FACE_H-15.8)*u
        r=2.2+(1.3-2.2)*u
        sections.append(c.rr(w,h,r,zz,zz+.015))
    root=c.union([c.Manifold.batch_hull([a,b])for a,b in zip(sections[:-1],sections[1:])])
    face=c.rr(FACE_W,FACE_H,1.3,-.015,FACE_T)
    # Solid floor backs the bought socket; it is not a removable plate. The
    # main wire bore may trim its inner edge, but the offset socket posts retain
    # backed locating lands. Required bores are subtracted after all unions.
    floor=c.rr(8.1,11.2,.7,-5.8,-4.4).translate((-4.7,-2.7,0.))
    return root+face+floor


def _wire_channel(c,points,r=1.25):
    spheres=[c.Manifold.sphere(r,16).translate(p)for p in points]
    return c.union([c.Manifold.batch_hull([a,b])for a,b in zip(spheres[:-1],spheres[1:])])


def local_void(c):
    # Only the true lower housing is relieved; V20's -5.3 mm-deep generic well
    # would erase the socket floor when applied to the final combined solid.
    face=c.rr(SWITCH_OPENING,SWITCH_OPENING,.25,-.04,3.0)
    body=c.rr(14.7,14.7,.45,-2.35,.015)
    socket=c.box(-8.5,-1.1,-8.,2.6,-4.4,-1.8)
    holes=[c.cyl(r,-8.,3.,x=x,y=y)for x,y,r in HOLES]
    # Socket nylon body length is9.95, but its solder tabs span13.15 mm. Their
    # outward run and the insulated wires get dedicated channels to the bore.
    tab_a=c.box(-7.65,-4.15,2.35,4.3,-4.5,-2.4)
    tab_b=c.box(-5.55,-2.05,-9.3,-7.75,-4.5,-2.4)
    wire_a=_wire_channel(c,[(-5.9,4.1,-3.5),(-4.0,4.7,-5.8),(-1.0,4.7,-6.7)])
    wire_b=_wire_channel(c,[(-3.8,-9.1,-3.5),(-2.8,-9.7,-5.8),(-.5,-9.7,-6.7)])
    # Service corridor lies below the structural 1.3mm lip. It allows the
    # offset socket to enter through the centred opening before its posts seat.
    service=c.box(-8.5,.4,-9.5,6.6,-3.85,.015)
    return c.union([face,body,socket,tab_a,tab_b,wire_a,wire_b,service]+holes)


def pad(c,angle,z):
    """Positive material; root's final union MUST be cut by void()."""
    return c.mount_local(local_pad(c),angle,z)


def void(c,angle,z):
    """All required physical clearances, applied after final structural union."""
    return c.mount_local(local_void(c),angle,z)


def local_hardware(c):
    """Bought parts and approximate factory clip reference, never print parts.

    Factory-clip solids below the lip are nominal fit/capture references, not a
    spring-force model. The actual bought component is the final authority.
    """
    housing=c.rr(13.8,13.8,.2,-2.2,1.3)
    flange=c.rr(15.,15.,.45,1.3,2.1)
    # Nominal factory hooks project below the face. They clear at rest and
    # overlap its underside after lifting; the printed face does not flex.
    clips=c.box(-3.,3.,6.85,7.25,-.55,-.15)+c.box(-3.,3.,-7.25,-6.85,-.55,-.15)
    pins=c.cyl(.9,-4.8,-2.1,x=-5.9)+c.cyl(.9,-4.8,-2.1,x=-3.8,y=-5.)
    socket=c.box(-8.3,-1.3,-7.8,2.4,-4.4,-2.6)
    posts=c.cyl(1.45,-5.6,-4.35,x=-5.9)+c.cyl(1.45,-5.6,-4.35,x=-3.8,y=-5.)
    tabs=c.box(-7.5,-4.3,2.3,4.1,-4.2,-2.8)+c.box(-5.4,-2.2,-9.1,-7.7,-4.2,-2.8)
    return {'switch':housing+flange+clips,'switch_housing':housing,
            'factory_clips':clips,'switch_pins':pins,'socket':socket+posts+tabs,
            'socket_body':socket,'socket_posts':posts,'socket_solder_tabs':tabs}


def hardware(c,angle,z):
    return {name:c.mount_local(m,angle,z)for name,m in local_hardware(c).items()}


def socket_route(c):
    """Continuous swept envelopes of the socket's three linear assembly legs.

    Each constituent is convex (body box, two posts, two solder tabs), so its
    two-pose convex hull is the exact rigid translational sweep of that
    constituent. Do not convex-hull the whole nonconvex socket at once.
    """
    h=local_hardware(c)
    pieces=[h['socket_body']]+h['socket_posts'].decompose()+h['socket_solder_tabs'].decompose()
    poses=[(1.5,2.5,12.),(1.5,2.5,2.),(0.,0.,2.),(0.,0.,0.)]
    return {name:c.union([c.Manifold.batch_hull([p.translate(a),p.translate(b)])for p in pieces])
            for name,a,b in zip(('centred_entry','subface_alignment','post_seating'),poses[:-1],poses[1:])}


def assembled_checks(c,stem,right=False):
    """Check the caller's FINAL grip, including all rails, neighbours and bore."""
    result={}
    for name,a,z in c.HAND_BUTTONS:
        a=-a if right else a
        h=hardware(c,a,z)
        aa=math.radians(a);axis=(math.sin(aa),math.cos(aa),0.)
        move=lambda d:tuple(d*v for v in axis)
        clear={k:abs((stem^v).volume())for k,v in h.items()}
        route={k:abs((stem^c.mount_local(v,a,z)).volume())for k,v in socket_route(c).items()}
        bores={str((x,y)):abs((stem^c.mount_local(c.cyl(r-.1,-7.8,2.8,x=x,y=y),a,z)).volume())for x,y,r in HOLES}
        captures={
            'socket_floor_inward_stop_mm3':abs((stem^h['socket'].translate(move(-.3))).volume()),
            'factory_hook_lift_capture_mm3':abs((stem^h['factory_clips'].translate(move(.4))).volume()),
            'switch_flange_press_stop_mm3':abs((stem^h['switch'].translate(move(-.3))).volume()),
            'socket_outward_stop_against_installed_switch_mm3':abs((h['socket_body'].translate(move(.6))^h['switch_housing']).volume())}
        result[name]={'hardware_clearance_mm3':clear,'continuous_socket_route_mm3':route,
                      'post_bores_mm3':bores,'captures':captures,
                      'factory_hook_reference_is_simplified':True,
                      'physical_fit_verified':False}
        assert max(clear.values())<.001,(name,result[name])
        assert max(route.values())<.001 and max(bores.values())<.001,(name,result[name])
        assert min(captures.values())>.1,(name,result[name])
    return result


def checks(c):
    """Local geometry proof, deliberately separate from print/force acceptance."""
    p=local_pad(c)-local_void(c);h=local_hardware(c)
    clear={k:abs((p^v).volume())for k,v in h.items()}
    own_clips_captured=abs((p^h['factory_clips'].translate((0,0,.4))).volume())
    flange_stop=abs((p^h['switch'].translate((0,0,-.3))).volume())
    probe_holes={str((x,y)):abs((p^c.cyl(r-.1,-5.65,-4.45,x=x,y=y)).volume())for x,y,r in HOLES}
    insertion={str(d):abs((p^h['switch_housing'].translate((0,0,d))).volume())for d in [0.,.5,1.,2.,4.,8.]}
    socket_route={}
    for dz in [12.,8.,6.,4.,3.,2.]:
        socket_route['centred_lower_'+str(dz)]=abs((p^h['socket'].translate((1.5,2.5,dz))).volume())
    for f in [1.,.8,.6,.4,.2,0.]:
        socket_route['subface_align_'+str(f)]=abs((p^h['socket'].translate((1.5*f,2.5*f,2.))).volume())
    for dz in [2.,1.5,1.,.5,0.]:
        socket_route['seat_posts_'+str(dz)]=abs((p^h['socket'].translate((0,0,dz))).volume())
    result={'local_components':len(p.decompose()),'local_hardware_clearance_mm3':clear,
            'purchased_clip_lift_capture_mm3':own_clips_captured,
            'flange_downward_stop_mm3':flange_stop,'post_hole_clearance_mm3':probe_holes,
            'housing_insertion_mm3':insertion,'socket_assembly_route_mm3':socket_route,'printed_plate_count':0,'printed_claw_count':0,
            'physical_fit_verified':False,'clip_force_simulated':False}
    assert len(p.decompose())==1,result
    assert max(clear.values())<.001,result
    assert max(probe_holes.values())<.001 and max(insertion.values())<.001,result
    assert max(socket_route.values())<.001,result
    assert own_clips_captured>.1 and flange_stop>.1,result
    return result
