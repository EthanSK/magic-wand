"""R44: joined middle finger rests and outer keys 0.30 mm lower than R43.

Ethan: "can these things connect and have a branch from the middle to the
edge in the middle as well not just on the outer sides. thats where it will
lie on the finger ... redesign that finger rester so theres not big gaps like
that where the finger will actual hold it" and "the keys can be a tiny bit
lower tbh".

Frame: X across the keys, +Y towards the two-key row, +Z up from the rod
centre. The holding finger lies under the carrier, across the rounded guard
rows (underside plane Z 0.3). Behind the third row (Y 6.7) the old guard left
a fingertip-sized pocket up to the slab, 5-6 mm deep, on both sides.

- A rounded middle branch (R38 rib radius 0.95) continues the 3.25 mm row
  pitch at Y 9.95, on the same underside plane. It runs from the third
  guard's inner leg to the existing outer guard path on each side.
- A rounded spine along Y joins the three old rows and the middle branch at
  mid-span (X 15.5 right, -15.3 left). The carrier prints rear-down (print
  z = 32.65 - Y), so the spine is a vertical column and shortens the old
  crosswise bridges.
- On the right, a sloping riser carries the middle branch into the slab
  underside, using a slightly thicker 2.30 mm round section: a direct load path to the frame and an intermediate printed
  support for the branch. The left is not given one: the lower-left key's
  lightening window and dogleg socket column occupy the matching slab.
- No plate, panel or separate part. The additions are cut by the same guard
  keep-outs as the old ribs (old and raised), the OP1 board, barrel,
  connector and pilot reliefs, then carved by every complete raised working
  route and socket print cutter. Only pieces joined to the existing guard or
  frame are kept. Each side joins its third guard rib, so every guard
  remains one piece and keeps its own frame bonds.

The four outer Choc seats are R42 + 1.42 mm, rebuilt here from R43's method
at this height without changing R43's immutable module or its caches. OP1,
touch board, hinge, stop and rod positions are unchanged; the touch top is
now about 0.30 mm above the outer keycaps.

Sizes of bought parts remain photo-derived estimates. Run assembly44.py
through geometry_budget.py; this module writes nothing and claims no physical
fit, comfort, strength or print readiness.
"""
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch
import json
import sys

import manifold3d as mf
import numpy as np

HERE=Path(__file__).resolve().parent
R42=HERE.parent/'carbon-rod-holders-r42-lower-diagonal'
R43=HERE.parent/'carbon-rod-holders-r43-raised-keys'
sys.path.insert(0,str(R42))
sys.path.insert(0,str(R43))
import holder42 as previous  # noqa: E402
import holder43 as r43  # noqa: E402  height-independent helpers only

R41=previous.R41
KEY_RAISE_MM=1.42               # R43 was 1.72: Ethan asked for slightly lower keys
R43_KEY_RAISE_MM=r43.KEY_RAISE_MM
CHOC_TOP_R42=19.92
OUTER_KEYS=r43.OUTER_KEYS
OUTER_BANK_START=r43.OUTER_BANK_START
SOCKET_PRINT_CLEARANCE_MM=r43.SOCKET_PRINT_CLEARANCE_MM
SOCKET_BODY_EDGE_CLEARANCE_MM=r43.SOCKET_BODY_EDGE_CLEARANCE_MM

H,r22,h28,h33=previous.H,previous.r22,previous.h28,previous.h33
box,union=previous.box,previous.union
base=previous.base
CARRIER,BRACKET,CLIP=previous.CARRIER,previous.BRACKET,previous.CLIP
BATTERY,DOOR,battery_door=previous.BATTERY,previous.DOOR,previous.battery_door
hardware,bracket,clip_part=previous.hardware,previous.bracket,previous.clip_part
OP1_YAW=previous.prev.OP1_YAW
RIB_RADIUS=base.RIB_RADIUS

# --- middle finger rest (raw R38 rib coordinates; base.shift_x places them) ---
FINGER_REST_Y=9.95              # next row after 0.2 / 3.45 / 6.7 (3.25 mm pitch)
FINGER_REST_Z=1.25              # same centre height and underside plane as the rows
SPINE_X_RAW={'R':15.6,'L':15.4}  # placed at X 15.5 and -15.3
RISER_TOP=(17.0,8.5)          # Y, Z: joins the central solid land, clear of the outer socket.
RISER_SIDES=('R',)
RISER_END_X_RAW=12.1
RISER_RADIUS=1.15
FINGER_REST_RIB={'R':'R3','L':'L3'}
FINGER_PROBE_RADIUS=5.
FINGER_SINK_MM=1.
PROBE_X={'R':(12.5,19.),'L':(-12.5,-22.)}
PROBE_Y=(-.5,11.5)


def __getattr__(name):
    if hasattr(previous,name):return getattr(previous,name)
    return getattr(previous.prev,name)


# --- outer key seats at this revision's height --------------------------------
@lru_cache(maxsize=1)
def seat_platforms():
    """R43's connected outer key banks at KEY_RAISE_MM, overlapping the old frame."""
    previous.geometry()  # Establish the inherited XY key layout once.
    base22=r22.base
    platform=r22.rounded_slab(r22.slab_outline(),base22.slab_bottom()+KEY_RAISE_MM,
                              base22.plate_top()+KEY_RAISE_MM)
    platform-=r22.slab_cutters().translate((0.,0.,KEY_RAISE_MM))
    platform-=base22.thinning(base22.key_positions(),base22.key_rotations()).translate((0.,0.,KEY_RAISE_MM))
    banks=box(OUTER_BANK_START,40.,-30.,60.,-10.,30.)+box(-40.,-OUTER_BANK_START,-30.,60.,-10.,30.)
    return platform^banks


def socket_print_cutters(working):
    """R43's height-independent printed socket clearance, keyed by these routes."""
    return r43.socket_print_cutters(working)


def socket_approach_relief():
    """R43's two underside reliefs, extended down with the lower socket routes.

    Both boxes stay below the raised mounting collars (Z >= 11.34 here).
    """
    dz=min(0.,KEY_RAISE_MM-R43_KEY_RAISE_MM)
    return (box(-16.6,-15.6,14.4,15.2,7.4+dz,9.3)
            +box(27.7,30.1,2.5,4.9,7.4+dz,9.6)
            +box(-14.3,-12.7,2.5,4.9,7.4+dz,9.6))


@lru_cache(maxsize=1)
def guard_reinforcement():
    """R43's 0.6 mm thicker R41 left web; read directly, never through a patch."""
    old=previous.prev.carrier_parts()[4]
    return old+old.translate((0.,0.,.3))+old.translate((0.,0.,-.3))


@lru_cache(maxsize=1)
def _base_geometry():
    """R43's construction at KEY_RAISE_MM, before the middle finger rests."""
    _,old_working,old_fixed,old_ribs=previous.geometry()
    up=(0.,0.,KEY_RAISE_MM)
    working={name:shape.translate(up) if name.startswith('key_') else shape
             for name,shape in old_working.items()}
    cutters=socket_print_cutters(working)
    fixed=r22.spaces16.carve(old_fixed+seat_platforms()+guard_reinforcement(),cutters,'R44 raised outer key seats')
    ribs={name:r22.spaces16.carve(shape,cutters,'R44 guard '+name) for name,shape in old_ribs.items()}
    relief=socket_approach_relief()
    fixed-=relief
    ribs={name:shape-relief for name,shape in ribs.items()}
    return working,fixed,ribs


# --- middle finger rest ---------------------------------------------------------
def _point_at_y(a,b,y):
    t=(a[1]-y)/(a[1]-b[1])
    assert 0.<=t<=1.,(a,b,y)
    return tuple(float(p+t*(q-p)) for p,q in zip(a,b))


def finger_rest_paths():
    """Placed centre lines of each side's new members, on existing rib centres."""
    rows=h33.RIB_ROWS
    root=14.8+.8*2;span=root-rows[2]
    # The third guard's inner leg (R38 rib_at) and the shared left outer path.
    leg=_point_at_y((8.95,root-.6*span,4.45),(11.05,root-.87*span,1.35),FINGER_REST_Y)
    left_outer=_point_at_y((25.5,9.55,2.65),(27.45,10.65,4.15),FINGER_REST_Y)
    y,z=FINGER_REST_Y,FINGER_REST_Z
    raw={}
    for side in ('R','L'):
        sx=SPINE_X_RAW[side]
        if side=='R':
            branch=[leg,(12.2,y,z),(sx,y,z),(18.35,y,z),(20.7,9.55,1.35)]  # R outer node
        else:
            branch=[leg,(12.2,y,z),(sx,y,z),(21.4,y,z),left_outer]
        members={'middle branch':branch,'spine':[(sx,y,z),(sx,rows[0],z)]}
        if side in RISER_SIDES:
            members['riser']=[(sx,y,z),(RISER_END_X_RAW,*RISER_TOP)]
        raw[side]=members
    placed={}
    for side,members in raw.items():
        s=1. if side=='R' else -1.
        placed[side]={name:[(s*base.shift_x(x),py,pz) for x,py,pz in points]
                      for name,points in members.items()}
    return placed


@lru_cache(maxsize=1)
def finger_rest_keepouts():
    """The old guard keep-outs plus their raised copies and all OP1 reliefs."""
    working=_base_geometry()[0]
    slot,barrels,connector,pilots=previous.prev.op1_reliefs()
    up=(0.,0.,KEY_RAISE_MM)
    guard=r22.guard_keepout();slab=r22.slab_cutters()
    return union((guard,guard.translate(up),slab,slab.translate(up),
                  slot,barrels,connector,pilots,working['key_3_socket_tape_zone']))


@lru_cache(maxsize=1)
def finger_rests():
    """Whole, cut, pre-union additions per side; detached cut pieces recorded."""
    working,fixed,ribs=_base_geometry()
    keep=finger_rest_keepouts()
    cutters=socket_print_cutters(working)
    relief=socket_approach_relief()
    existing=fixed+union(ribs.values())
    result={}
    for side,members in finger_rest_paths().items():
        raw=union(h33.rounded_run(points,radius=RISER_RADIUS if name=='riser' else RIB_RADIUS)
                  for name,points in members.items())
        cut=r22.spaces16.carve(raw-keep,cutters,'R44 middle finger rest '+side)-relief
        pieces=cut.decompose()
        kept=[piece for piece in pieces if (piece^existing).volume()>.1]
        shape=union(kept) if kept else mf.Manifold()
        result[side]={'shape':shape,'raw_volume_mm3':float(raw.volume()),
                      'discarded_mm3':float(sum(piece.volume() for piece in pieces)-shape.volume()),
                      'pieces':len(shape.decompose())}
    return result


def _side_box(sign,x0,x1,y0,y1):
    a,b=sorted((sign*x0,sign*x1))
    return box(a,b,y0,y1,-12.,30.)


@lru_cache(maxsize=1)
def finger_rest_interfaces():
    """Whole members and each attachment, measured before they join the carrier."""
    _,fixed,ribs=_base_geometry()
    rows=h33.RIB_ROWS
    out={}
    for side,rest in finger_rests().items():
        shape=rest['shape'];s=1. if side=='R' else -1.
        own={name:rib for name,rib in ribs.items() if name.startswith(side)}
        spine_x=s*base.shift_x(SPINE_X_RAW[side])
        out[f'R44 {side} middle finger rest']=shape
        out[f'R44 {side} middle branch-to-inner leg bond']=(shape^own[FINGER_REST_RIB[side]]
            ^_side_box(s,8.,11.6,FINGER_REST_Y-1.4,FINGER_REST_Y+1.4))
        out[f'R44 {side} middle branch-to-outer guard bond']=(shape^union(own.values())
            ^_side_box(s,19.,27.5,FINGER_REST_Y-1.4,FINGER_REST_Y+1.4))
        for number,row in enumerate(rows):
            name=f'{side}{number+1}'
            out[f'R44 {side} spine-to-{name} guard bond']=(shape^own[name]
                ^box(spine_x-1.6,spine_x+1.6,row-1.6,row+1.6,-12.,30.))
        if side in RISER_SIDES:
            out[f'R44 {side} riser-to-frame load-path bond']=(shape^fixed
                ^h33.rounded_run(finger_rest_paths()[side]['riser'],radius=RISER_RADIUS))
    return out


@lru_cache(maxsize=1)
def geometry():
    working,fixed,ribs=_base_geometry()
    ribs=dict(ribs)
    for side,rest in finger_rests().items():
        name=FINGER_REST_RIB[side]
        ribs[name]=ribs[name]+rest['shape']
    carrier=H.base.clean(fixed+union(ribs.values()),CARRIER)
    return carrier,working,fixed,ribs


def carrier():return geometry()[0]


def guard_web_interfaces():
    parts=previous.prev.carrier_parts()
    return {'left guard reinforcement web':parts[4],**parts[5],
            'R43 complete thicker guard web':guard_reinforcement(),
            **finger_rest_interfaces()}


def key_apertures(key):
    """The lowered collars still match R39's bought Choc interface, moved up by the raise."""
    baseline=previous.prev.r39_carrier().translate((0.,0.,KEY_RAISE_MM))
    rows={}
    for i in OUTER_KEYS:
        x,y=r22.base.key_positions()[i]
        z0=r22.base.PCB_Z+KEY_RAISE_MM+r22.P['bay']['plate_bottom_mm']
        z1=r22.base.plate_top()+KEY_RAISE_MM
        assert z1>z0+.5,(z0,z1)
        region=box(x-7.7,x+7.7,y-7.7,y+7.7,z0,z1)
        new,was=key^region,baseline^region
        rows[f'key_{i}']={'centre_mm':[x,y],
            'difference_mm3':float((new-was).volume()+(was-new).volume()),
            'seat_volume_mm3':float(new.volume()),'baseline_translated_mm':KEY_RAISE_MM,
            'checked_z_mm':[z0,z1]}
    return rows


def seat_bonds():
    """Whole surviving platform interfaces, after the final underside relief."""
    old_fixed=previous.geometry()[2]
    working=geometry()[1]
    contact=r22.spaces16.carve(old_fixed^seat_platforms(),socket_print_cutters(working),'R44 seat bond witnesses')
    contact-=socket_approach_relief()
    positions=r22.base.key_positions()
    return {f'raised key {i} platform-to-frame bond':contact^box(
                positions[i][0]-9.4,positions[i][0]+9.4,
                positions[i][1]-8.8,positions[i][1]+8.8,-10.,30.) for i in OUTER_KEYS}


def fingertip_sink_probe(carrier):
    """Grid points where a 5 mm-radius fingertip rises 1 mm past the rib underside untouched."""
    finger=mf.Manifold.sphere(FINGER_PROBE_RADIUS,48)
    low=carrier^box(-40.,40.,-20.,40.,-10.,7.6)
    z=FINGER_REST_Z-RIB_RADIUS+FINGER_SINK_MM-FINGER_PROBE_RADIUS
    free=[]
    for side,xs in PROBE_X.items():
        for x in np.linspace(*xs,4):
            for y in np.linspace(*PROBE_Y,7):
                if (finger.translate((float(x),float(y),z))^low).volume()<.035:
                    free.append([side,round(float(x),3),round(float(y),3)])
    return free


def _clear_inherited_checks():
    previous.checks.cache_clear();previous.prev.checks.cache_clear()


@lru_cache(maxsize=1)
def checks():
    actual=geometry()
    webs=guard_web_interfaces()
    old_references=r22.base.references
    contacts=h33.old.h20.contact_envelopes
    def raised_references():
        return {name:shape.translate((0.,0.,KEY_RAISE_MM)) if name.startswith('key_') else shape
                for name,shape in old_references().items()}
    def raised_contacts():
        return {name:shape.translate((0.,0.,KEY_RAISE_MM)) if name.startswith('key_') else shape
                for name,shape in contacts().items()}
    # Re-run the complete inherited CAD checks on the actual R44 carrier,
    # translated key routes/references and every R44 bond witness. Leave no
    # patched result in the inherited caches afterwards.
    _clear_inherited_checks()
    try:
        with patch.object(previous.prev,'geometry',return_value=actual), \
             patch.object(previous.prev,'guard_web_interfaces',return_value=webs), \
             patch.object(h28,'CHOC_TOP',CHOC_TOP_R42+KEY_RAISE_MM), \
             patch.object(previous.prev,'key_apertures',side_effect=key_apertures), \
             patch.object(h33.old.h20,'contact_envelopes',side_effect=raised_contacts), \
             patch.object(r22.base,'references',side_effect=raised_references):
            result=json.loads(json.dumps(previous.checks()))
    finally:
        _clear_inherited_checks()
    old=previous.geometry()[0]
    protected=previous.op1_seats()+previous.r.supports()+previous.base.stop_landing()+previous.base.clip_bands()
    centre_change=float(((actual[0]-old)^protected).volume()+((old-actual[0])^protected).volume())
    bonds={name:float(shape.volume()) for name,shape in seat_bonds().items()}
    top=CHOC_TOP_R42+KEY_RAISE_MM
    r43_top=CHOC_TOP_R42+R43_KEY_RAISE_MM
    r43_touch=21.6416  # R43's unchanged released touch reference, not its keycap top.
    touch=result['lowering']['touch_top_released_mm']
    rests=finger_rests()
    sides={side:{'merged_into_guard':FINGER_REST_RIB[side],
                 'volume_mm3':round(float(rest['shape'].volume()),4),
                 'raw_volume_mm3':round(rest['raw_volume_mm3'],4),
                 'discarded_mm3':round(rest['discarded_mm3'],4),'pieces':rest['pieces'],
                 'bounds_mm':[round(v,3) for v in rest['shape'].bounding_box()]}
           for side,rest in rests.items()}
    interfaces={name:round(float(shape.volume()),4) for name,shape in finger_rest_interfaces().items()}
    probe=fingertip_sink_probe(actual[0])
    before=fingertip_sink_probe(old)
    rest_ok=bool(all(row['pieces']==1 and row['discarded_mm3']<.05 and row['volume_mm3']>20.
                     for row in sides.values())
                 and min(v for k,v in interfaces.items() if 'bond' in k)>1. and not probe)
    result['finger_rest']={
        'centre_lines_mm':{side:{name:[[round(v,3) for v in p] for p in points]
                                 for name,points in members.items()}
                           for side,members in finger_rest_paths().items()},
        'radius_mm':RIB_RADIUS,'sides':sides,'interfaces_mm3':interfaces,
        'fingertip_probe':{'radius_mm':FINGER_PROBE_RADIUS,
                           'rise_past_rib_underside_mm':FINGER_SINK_MM,
                           'grid_x_mm':{k:list(v) for k,v in PROBE_X.items()},'grid_y_mm':list(PROBE_Y),
                           'points_per_side':28,'free_points_r44':probe,'free_points_r42':before},
        'passed':rest_ok,
        'physical_comfort_strength_and_print_verified':False}
    result['raised_keys']={'raise_mm':KEY_RAISE_MM,'lowered_from_r43_mm':round(R43_KEY_RAISE_MM-KEY_RAISE_MM,6),
        'keys':list(OUTER_KEYS),
        'underside_socket_print_clearance_mm':SOCKET_PRINT_CLEARANCE_MM,
        'socket_body_edge_clearance_mm':SOCKET_BODY_EDGE_CLEARANCE_MM,
        'keycap_top_mm':top,'released_touch_top_mm':touch,
        'touch_above_keycap_tops_mm':round(touch-top,6),
        'released_touch_top_change_from_r43_reference_mm':round(touch-r43_touch,6),
        'fixed_mount_hinge_stop_and_rod_clip_geometry_change_mm3':centre_change,'platform_bond_volumes_mm3':bonds,
        'rod_op1_touch_hinge_and_stop_positions_changed':False,
        'physical_fit_strength_and_comfort_verified':False}
    result['layout'].pop('choc_seat_and_rod_clip_height_change_mm',None)
    result['layout'].update(choc_seat_height_change_mm=KEY_RAISE_MM,rod_clip_height_change_mm=0.)
    result['lowering']['carrier_changed_from_r41']=True
    result['passed']=bool(result['passed'] and centre_change<1e-5
        and abs(touch-r43_top)<.025 and min(bonds.values())>1.
        and min(row['seat_volume_mm3'] for row in result['key_apertures_vs_r39'].values())>1.
        and rest_ok)
    result['cad_checks_passed']=result['passed']
    result['basis']+=(f' R44 places the four outer key platforms {KEY_RAISE_MM:.2f} mm above R42 '
                      f'({R43_KEY_RAISE_MM-KEY_RAISE_MM:.2f} mm below R43) and joins rounded middle finger '
                      'rests to the existing guards; complete CAD checks rerun against translated '
                      'bought-key envelopes and loading routes. Finger comfort is a CAD probe only.')
    return result
