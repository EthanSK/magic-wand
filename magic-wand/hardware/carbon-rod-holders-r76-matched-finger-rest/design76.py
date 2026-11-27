"""Click-end guard copied from the opposite bank, with a local sideways-socket passage."""
from pathlib import Path
from hashlib import sha256
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r75-click-end'))
import design75 as old
import verify75 as checked

prior = old.prior
b = old.b
HOLDER = old.HOLDER
# Move the complete eye toward the click by 1.05 mm. Its curves, circular
# section and finger-contact height stay exactly the same. The distance gives
# its rear support a continuous printed slope into the deck.
EYE_SHIFT = 1.05
PACK_PROJECTION = 2.5


def mirrored_return(x):
    control = prior.fit.smooth_return(x)
    return prior.r71.r61.curve(control, prior.RADIUS).mirror((1, 0, 0))


def crown():
    # The good guard divides into three round bars under the finger. Use the
    # actual curves, including the eye at their meeting point.
    old_guard = prior.r71.r62
    return b.union([prior.r71.r61.curve([old_guard.CROWN_START, (x, 9.5, .88),
                                         (x, 6.6, .88), old_guard.CROWN_END], 1.26)
                    for x in (15.1, 22.1, 28.1)]).mirror((1, 0, 0)).translate((0,-EYE_SHIFT,0))


def rear():
    # The reference eye has a third root toward the rod. Rise into the strip
    # in front of the seated pouch, then curve over its end onto the solid deck.
    # The upper socket feeds from the side, on the far side of this brace.
    return old.click_end.rounded_beam([
        (-13.60, 16.30, 7.85, 1.30, 1.32, 1.30),
        (-13.60, 14.40, 6.91, 1.25, 1.29, 1.23),
        (-13.72, 12.80, 6.23, 1.21, 1.25, 1.17),
        (-14.01, 11.52, 5.87, 1.17, 1.21, 1.14),
        (-14.70, 10.62, 5.31, 1.16, 1.16, 1.14),
        (-15.65, 10.29, 4.04, 1.17, 1.18, 1.17),
        (-16.87, 10.07, 2.78, 1.20, 1.20, 1.20),
        (-18.16, 9.81, 1.73, 1.23, 1.23, 1.22),
        (-19.36, 9.50, 1.02, 1.26, 1.25, 1.24),
        (-20.40, 10.20-EYE_SHIFT, .88, 1.26, 1.26, 1.26),
    ])


def outside_return():
    # Use the existing bend only alongside the black socket. As soon as the
    # wired socket clears, blend back into the hand-tested curve in all axes.
    turn = prior.outer_leg() ^ b.box(-31.,-9.,-10.,-1.5,-4.,prior.DECK+.44)
    t = np.linspace(0,1,141)
    path = prior.mirrored_leg(t)
    path = path[path[:,1] >= -2.9]
    blend = np.clip((path[:,1] + 2.3) / 3.65, 0, 1)
    blend = blend**2 * (3 - 2*blend)
    path[:,2] = prior.CROWN_Z + blend*(path[:,2]-prior.CROWN_Z)
    return turn + prior.rod(path,prior.RADIUS)


def pack():
    return checked.prior.pouch_design.pack().translate((checked.prior.INBOARD,PACK_PROJECTION,0))


def service_lane():
    x,y,z,xx,yy,zz = pack().bounding_box()
    return b.box(x,xx,y,yy+30,z,zz)


def build():
    old_body = b.load(old.OUT/HOLDER)
    # Replace the portion of the old guard standing proud of the deck. Its
    # embedded root lands remain bonded inside the R75 key-seat perimeter.
    clear = old_body - b.box(-30.8,-10.8,-9.2,16.9,-4.,prior.DECK-.002)
    root = b.box(-31.,-9.,-10.,16.,-4.,prior.DECK+.44)
    inner = mirrored_return(14.2) ^ root
    outer = outside_return()
    eye = crown()
    brace = rear()
    guard = inner + outer + eye + brace
    body = clear + guard
    pieces = sorted(body.decompose(),key=lambda s:-s.volume())
    if any(p.volume() > .0001 for p in pieces[1:]):
        raise ValueError([(p.volume(), p.bounding_box()) for p in pieces[1:] if p.volume()>.0001])
    OUT.mkdir(exist_ok=True)
    shape = old.clean_export(OUT/HOLDER,pieces[0])
    hardware,spaces = prior.key_models()
    mirror = (mirrored_return(28.3) + inner) ^ root
    mirror_socket = (mirror ^ hardware['socket_0']).volume()
    seated = pack()
    rigid = shape - prior.shoe()
    report = dict(revision='R76', carrier_sha256=sha256((OUT/HOLDER).read_bytes()).hexdigest(),
                  pack_projection_mm=PACK_PROJECTION, old_installed_pack_to_mirrored_lower_fork_mm=
                  mirror.min_gap(seated.translate((0,-PACK_PROJECTION,0)),15),
                  mirrored_outer_in_seated_socket_mm3=mirror_socket,
                  mirrored_outer_in_soldered_socket_insertion_mm3=max((mirror^pose).volume() for pose in spaces['key_0_soldered_socket_slide']),
                  inner_curve_missing_from_final_mm3=max(0., (inner-shape).volume()),
                  seated_battery_to_crown_mm=eye.min_gap(seated,15),
                  seated_battery_to_fork_and_brace_mm=guard.min_gap(seated,15),
                  rear_service_rigid_overlap_mm3=max(0.,(rigid^service_lane()).volume()),
                  spring_engagement_mm3=(shape^prior.shoe()^seated).volume(),
                  closed_carrier_solids=len(shape.decompose()),
                  guard_vs_key_paths={k:round(max((guard^pose).volume() for pose in ps),5)
                                      for k,ps in spaces.items() if k.startswith(('key_0','key_3'))},
                  physical_fit_verified=False)
    (OUT/'guard-fit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    assert report['inner_curve_missing_from_final_mm3'] < .005
    assert report['rear_service_rigid_overlap_mm3'] < .001 and report['seated_battery_to_fork_and_brace_mm'] > .12
    assert max(report['guard_vs_key_paths'].values()) < .001 and report['closed_carrier_solids']==1


if __name__=='__main__':
    build()
