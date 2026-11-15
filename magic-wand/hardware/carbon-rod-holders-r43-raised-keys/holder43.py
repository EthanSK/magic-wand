"""R43: raise only the four outer Choc seats to the released touch height.

Ethan's 'metal poky bits' are the OP1 socket barrels: their closest rod gap
is 0.9 mm, whereas the white harness plug has only 0.31 mm. Keep that bought
assembly, rod, DFRobot bracket and hinge fixed. Add connected raised key
platforms, then cut the complete translated bought-key and wiring routes.
Run assembly43.py through geometry_budget.py; this module writes nothing.
"""
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch
import json
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
R42=HERE.parent/'carbon-rod-holders-r42-lower-diagonal'
sys.path.insert(0,str(R42))
import holder42 as previous

KEY_RAISE_MM=1.72
OUTER_KEYS=(0,2,3,4)
OUTER_BANK_START=12.7
SOCKET_PRINT_CLEARANCE_MM=.12
SOCKET_BODY_EDGE_CLEARANCE_MM=.25
H,r22,h28=previous.H,previous.r22,previous.h28
box,union=previous.box,previous.union
CARRIER,BRACKET,CLIP=previous.CARRIER,previous.BRACKET,previous.CLIP


def __getattr__(name):
    if hasattr(previous,name):return getattr(previous,name)
    return getattr(previous.prev,name)


@lru_cache(maxsize=1)
def seat_platforms():
    """Preserve the old guard/frame bonds; add only the two outer key banks.

    Moving the entire legacy slab also moves its guard-growth backing and
    can detach the existing guard roots. The new platforms overlap the old
    frame instead. The centre mechanism and rod attachments remain intact.
    """
    previous.geometry()  # Establish the inherited XY key layout once.
    base=r22.base
    platform=r22.rounded_slab(r22.slab_outline(),base.slab_bottom()+KEY_RAISE_MM,
                              base.plate_top()+KEY_RAISE_MM)
    platform-=r22.slab_cutters().translate((0.,0.,KEY_RAISE_MM))
    platform-=base.thinning(base.key_positions(),base.key_rotations()).translate((0.,0.,KEY_RAISE_MM))
    banks=box(OUTER_BANK_START,40.,-30.,60.,-10.,30.)+box(-40.,-OUTER_BANK_START,-30.,60.,-10.,30.)
    return platform^banks


@lru_cache(maxsize=1)
def geometry():
    _,old_working,old_fixed,old_ribs=previous.geometry()
    up=(0.,0.,KEY_RAISE_MM)
    working={name:shape.translate(up) if name.startswith('key_') else shape
             for name,shape in old_working.items()}
    cutters=socket_print_cutters(working)
    web=guard_reinforcement()
    fixed=r22.spaces16.carve(old_fixed+seat_platforms()+web,cutters,'R43 raised outer key seats')
    ribs={name:r22.spaces16.carve(shape,cutters,'R43 guard '+name)
          for name,shape in old_ribs.items()}
    # The raised lower socket route left a 0.33 mm-wide legacy shelf at
    # assembly (-16.165,14.75,8.345). Its native support covered only 77%
    # in the actual slice. Remove this non-interface nub instead of leaving
    # an unsupported start or welding a helper into the socket route.
    relief=socket_approach_relief()
    fixed-=relief
    ribs={name:shape-relief for name,shape in ribs.items()}
    carrier=H.base.clean(fixed+union(ribs.values()),CARRIER)
    return carrier,working,fixed,ribs


def carrier():return geometry()[0]


def socket_approach_relief():
    # The actual key_2 slice also grew an outer wall from a 0.055 mm fin
    # left by intersecting socket cutters. Flatten just this lower corner;
    # keep the mounting collar (Z >= 11.64) and platform bond intact.
    return box(-16.6,-15.6,14.4,15.2,7.4,9.3)+box(27.7,30.1,2.5,4.9,7.4,9.6)


@lru_cache(maxsize=1)
def guard_reinforcement():
    """Thicken the existing left web, including its narrow taper, by 0.6 mm.

    The old complete web/bond witnesses remain required. This additional
    stock puts printed plastic around those former underfilled edges.
    """
    old=previous.prev.guard_web_interfaces()['left guard reinforcement web']
    return old+old.translate((0.,0.,.3))+old.translate((0.,0.,-.3))


def guard_web_interfaces():
    return {**previous.prev.guard_web_interfaces(),
            'R43 complete thicker guard web':guard_reinforcement()}


def socket_print_cutters(working):
    return _socket_print_cutters(tuple(working.items()))


@lru_cache(maxsize=1)
def _socket_print_cutters(items):
    """Extra printed fit clearance; functional envelopes stay unmodified.

    The first actual slice deposited walls into nominal socket/load/tape
    envelopes. Add a copy enlarged by the stated per-side allowance, keeping
    the original whole envelope too. This is a manufacturing cutter, not
    a change to the nominal fit-check spaces. The exact
    Choc mounting window, cap travel, rod grip and central mechanism retain
    their existing definitions, and all nominal route checks remain strict.
    """
    e=SOCKET_PRINT_CLEARANCE_MM
    working=dict(items)
    result=dict(working)
    for name,shape in working.items():
        if not name.startswith('key_') or not any(term in name for term in ('socket','tape_zone')):
            continue
        swept=isinstance(shape,r22.spaces16.Swept)
        solid=shape.solid if swept else shape
        bounds=np.asarray(solid.bounding_box()).reshape(2,3)
        centre=bounds.mean(0);span=bounds[1]-bounds[0]
        assert (span>0).all()
        enlarged=solid.translate(tuple(-centre)).scale(tuple((span+2*e)/span)).translate(tuple(centre))
        enlarged=solid+enlarged
        if not swept and name.endswith(('_socket','_maximum_socket')):
            # The remaining actual bead intrusions were on the body edges
            # at assembly Z 8.75--9.15, not on the lower terminal routes.
            # Give those edges a real translated clearance without widening
            # the low solder routes through the finger-guard connections.
            pcb=working['key_0_mount_opening'].bounding_box()[2]-r22.P['bay']['plate_bottom_mm']
            e2=SOCKET_BODY_EDGE_CLEARANCE_MM
            moved=union(solid.translate(v) for v in ((e2,0.,0.),(-e2,0.,0.),
                (0.,.12,0.),(0.,-.12,0.),(0.,0.,e2),(0.,0.,-e2)))
            enlarged+=moved^box(-100.,100.,-100.,100.,pcb-2.3,pcb+1.)
        result[name]=r22.spaces16.Swept(enlarged,shape.offsets) if swept else enlarged
    return result


def key_apertures(key):
    """The raised seating collars retain the bought Choc interface.

    R41 compared its whole unchanged lower bay with R39. That stock now
    deliberately grows upward; compare the new top collars with R39 moved
    by the same amount instead. Full socket and insertion routes remain
    separate collision checks, including the lower retained frame.
    """
    baseline=previous.prev.r39_carrier().translate((0.,0.,KEY_RAISE_MM))
    rows={}
    for i in OUTER_KEYS:
        x,y=r22.base.key_positions()[i]
        z0=r22.base.PCB_Z+KEY_RAISE_MM+r22.P['bay']['plate_bottom_mm']
        z1=r22.base.plate_top()+KEY_RAISE_MM
        region=box(x-7.7,x+7.7,y-7.7,y+7.7,z0,z1)
        new,was=key^region,baseline^region
        rows[f'key_{i}']={'centre_mm':[x,y],
            'difference_mm3':float((new-was).volume()+(was-new).volume()),
            'seat_volume_mm3':float(new.volume()),'baseline_translated_mm':KEY_RAISE_MM,
            'checked_z_mm':[z0,z1]}
    return rows


def seat_bonds():
    """Whole surviving interfaces, measured before union, one per key."""
    old_fixed=previous.geometry()[2]
    working=geometry()[1]
    contact=r22.spaces16.carve(old_fixed^seat_platforms(),socket_print_cutters(working),'R43 seat bond witnesses')
    positions=r22.base.key_positions()
    return {f'raised key {i} platform-to-frame bond':contact^box(
                positions[i][0]-9.4,positions[i][0]+9.4,
                positions[i][1]-8.8,positions[i][1]+8.8,-10.,30.) for i in OUTER_KEYS}


@lru_cache(maxsize=1)
def checks():
    actual=geometry()
    old_references=r22.base.references
    contacts=previous.h33.old.h20.contact_envelopes
    def raised_references():
        return {name:shape.translate((0.,0.,KEY_RAISE_MM)) if name.startswith('key_') else shape
                for name,shape in old_references().items()}
    def raised_contacts():
        return {name:shape.translate((0.,0.,KEY_RAISE_MM)) if name.startswith('key_') else shape
                for name,shape in contacts().items()}
    # Re-run the established full CAD checks with the actual new carrier,
    # complete translated key routes and bought key references. No old pass
    # flag is accepted in place of these changed-geometry queries.
    previous.checks.cache_clear();previous.prev.checks.cache_clear()
    with patch.object(previous.prev,'geometry',return_value=actual), \
         patch.object(h28,'CHOC_TOP',19.92+KEY_RAISE_MM), \
         patch.object(previous.prev,'key_apertures',side_effect=key_apertures), \
         patch.object(previous.h33.old.h20,'contact_envelopes',side_effect=raised_contacts), \
         patch.object(r22.base,'references',side_effect=raised_references):
        result=json.loads(json.dumps(previous.checks()))
    old=previous.geometry()[0]
    protected=previous.op1_seats()+previous.r.supports()+previous.base.stop_landing()+previous.base.clip_bands()
    centre_change=float(((actual[0]-old)^protected).volume()+((old-actual[0])^protected).volume())
    bonds={name:float(shape.volume()) for name,shape in seat_bonds().items()}
    top=19.92+KEY_RAISE_MM
    touch=result['lowering']['touch_top_released_mm']
    result['raised_keys']={'raise_mm':KEY_RAISE_MM,'keys':list(OUTER_KEYS),
        'underside_socket_print_clearance_mm':SOCKET_PRINT_CLEARANCE_MM,
        'socket_body_edge_clearance_mm':SOCKET_BODY_EDGE_CLEARANCE_MM,
        'keycap_top_mm':top,'released_touch_top_mm':touch,'top_difference_mm':round(touch-top,6),
        'fixed_mount_hinge_stop_and_rod_clip_geometry_change_mm3':centre_change,'platform_bond_volumes_mm3':bonds,
        'rod_op1_touch_hinge_and_stop_positions_changed':False,
        'physical_fit_strength_and_comfort_verified':False}
    result['layout'].pop('choc_seat_and_rod_clip_height_change_mm',None)
    result['layout'].update(choc_seat_height_change_mm=KEY_RAISE_MM,rod_clip_height_change_mm=0.)
    result['lowering']['carrier_changed_from_r41']=True
    result['passed']=bool(result['passed'] and centre_change<1e-5
        and abs(touch-top)<.025 and min(bonds.values())>1.
        and min(row['seat_volume_mm3'] for row in result['key_apertures_vs_r39'].values())>1.)
    result['cad_checks_passed']=result['passed']
    result['basis']+=' R43 raises only the four outer key platforms by 1.72 mm; complete CAD checks rerun against translated bought-key envelopes and loading routes.'
    return result
