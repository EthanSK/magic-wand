"""R39 fit-trial repairs: stronger hinge roots and a lower positive battery catch.

Composes R38 without changing bought-part locations. Export with assembly39.py.
The battery door still slides down the same two slots; its raised finger tab
retracts the hook away from the cell before removal.
"""
from functools import lru_cache
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r38-centred-op1'))
import holder38 as previous

h, r, box, union, mf = previous.h, previous.r, previous.box, previous.union, previous.mf
R38 = previous.HERE
BASE_GEOMETRY, BASE_BRACKET = previous.geometry, previous.bracket
ARM_Z = (17.0, 19.0)
SUPPORT_TOP = 20.8
BATTERY = previous.r22
DOOR = {**BATTERY.h19.D, 'y_mm': [-15.85, -13.95], 'z_mm': [6.35, 13.4],
        'tongue_z_mm': [10.35, 11.7], 'window_top_z_mm': 12.6, 'tab_top_z_mm': 12.15,
        'tooth_yz_mm': [[-14.15,10.8],[-14.15,11.5],[-13.25,11.5],[-13.25,10.85]]}
RELEASE_MM = 1.65


def door_displacement(points, amount=1.):
    p = np.asarray(points, float)
    x,y,z = p.T
    root, end = DOOR['tongue_root_x_mm'], DOOR['tongue_tip_x_mm']
    t = np.clip((x-root)/(end-root),0.,1.)
    beam = (z >= DOOR['tongue_z_mm'][0]-.001) & (z <= DOOR['tongue_z_mm'][1]+.001)
    tab = (x >= DOOR['tab_x_mm'][0]-.001) & (x <= DOOR['tab_x_mm'][1]+.001) & (z <= DOOR['tab_top_z_mm']+.001) & (z >= DOOR['tongue_z_mm'][1]-.051)
    selected = (x>=root-.001)&(x<=end+.001)&(beam|tab)
    shift = -RELEASE_MM*t*t*(3-t)/2*selected*amount
    return np.column_stack((np.zeros_like(x),shift,np.zeros_like(x)))


@lru_cache(maxsize=1)
def battery_door():
    old = BATTERY.h18.D
    try:
        BATTERY.h18.D = DOOR
        return BATTERY.h18.battery_door()
    finally:
        BATTERY.h18.D = old


@lru_cache(maxsize=1)
def bracket():
    base = BASE_BRACKET()
    # Add height, not bending thickness, to increase layer-bond area without
    # increasing the strain required to squeeze the tabs into their holes.
    extension = r.mirrored(box(*r.h29.ARM_X, r.ARM_ROOT_Y-.6, 28.4, *ARM_Z))
    roots = r.mirrored(mf.Manifold.batch_hull([
        box(1.85,3.05,r.ARM_ROOT_Y-.6,r.ARM_ROOT_Y,*ARM_Z),
        box(3.05,8.65,r.ARM_ROOT_Y-3.0,r.ARM_ROOT_Y,17.0,19.0),
    ]))
    # The triangular root fan ends at the nominal root. The 1.5 mm fillet
    # stiffens the start of the arm and is included in the strain estimate. Free
    # arms retain their outward tabs, current axis and bought-board clearances.
    # A centre spine meets the inside of the arms only beyond their required
    # 0.98 mm squeeze. It prevents crushing both arms together during fitting.
    stop = box(-.65,.65,r.ARM_ROOT_Y-.15,27.6,17.0,18.3)
    bridge = box(-2.5,2.5,r.ARM_ROOT_Y-.6,r.ARM_ROOT_Y,17.0,18.3)
    # Concave 1.5 mm root fillets spread the bending load into the fan.
    radius = 1.5
    y = r.ARM_ROOT_Y
    fillet = (box(3.05,3.05+radius,y,y+radius,*ARM_Z)
              - mf.Manifold.cylinder(2.1,radius,radius,64).translate((3.05+radius,y+radius,16.95)))
    return previous.H.base.clean(base + extension + roots + stop + bridge + r.mirrored(fillet), previous.BRACKET)


@lru_cache(maxsize=1)
def geometry():
    key, working, fixed, ribs = BASE_GEOMETRY()
    world_y = r.AXIS_Y+r.CLICK_SHIFT
    caps=r.mirrored(box(*r.h29.SUPPORT_X,world_y-1.5,world_y+1.5,19.9,SUPPORT_TOP))
    # Round the exposed front deck where the index finger curls beneath the
    # three-key edge. This is a true circular relief, not a sharp chamfer.
    bottom_y=previous.h28.BOTTOM_EDGE
    round_r=.5
    z_top=previous.DECK_TOP
    corner=box(-30.1,30.1,bottom_y,bottom_y+round_r,z_top-round_r,z_top+.01)
    arc=mf.Manifold.cylinder(60.4,round_r,round_r,96).rotate((0,90,0)).translate((-30.2,bottom_y+round_r,z_top-round_r))
    relief=corner-arc
    key=(key+caps)-relief
    return key, working, (fixed+caps)-relief, ribs


def carrier(): return geometry()[0]


def arm_bend(points,amount=1.):
    """Draw the free arm bending beyond the stiffened 1.5 mm root fillet."""
    p=np.asarray(points,float);x,y,z=p.T
    root=r.ARM_ROOT_Y+1.5
    length=r.AXIS_Y-root
    t=np.clip((y-root)/length,0.,None)
    shape=np.where(t<=1.,t*t*(3.-t)/2.,1.+1.5*(t-1.))
    arm=(abs(x)>=r.h29.ARM_X[0]-.01)&(abs(x)<=r.h29.ARM_X[1]+.01)
    tab=(abs(x)>r.h29.ARM_X[1])&(abs(x)<=r.h29.TAB_TIP+.01)&(abs(y-r.AXIS_Y)<=r.h29.TAB_R+.01)&(abs(z-r.AXIS_Z)<=r.h29.TAB_R+.01)
    selected=(arm|tab)&(y>=root-.01)&(z>=ARM_Z[0]-.01)&(z<=20.01)
    return np.column_stack((-np.sign(x)*r.h29.SQUEEZE*amount*shape*selected,0*y,0*z))


def install_checks():
    # Reuse the actual R38 clearance/stroke checks with only the repaired solids.
    previous.geometry = geometry
    previous.bracket = bracket
    r.h29.ARM_Z = ARM_Z
    r.arm_bend = arm_bend


def checks():
    install_checks()
    report=previous.checks()
    arm=report['hinge']['arm_bending_estimate']
    free_length=arm['root_to_tab_mm']-1.5
    arm['nominal_unfilleted_strain_percent_estimate']=arm['root_strain_percent_estimate']
    arm['conservative_free_length_mm']=round(free_length,3)
    arm['root_strain_percent_estimate']=round(arm['root_strain_percent_estimate']*(arm['root_to_tab_mm']/free_length)**2,2)
    arm['physical_strength_verified']=False
    arm['warning']='Stiffened-root estimate only; layer bonding, force and fatigue require a physical trial.'
    return report


def __getattr__(name):
    # Unchanged R38 probes resolve through their canonical implementation.
    return getattr(previous, name)
