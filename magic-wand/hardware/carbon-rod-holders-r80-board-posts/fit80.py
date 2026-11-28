"""Measure the exported fit at the centre and at either rolled corner of the actual paddle."""
import math
import numpy as np

from plate80 import OUT, previous
from routes80 import b, transform
from audit80 import v

h = previous.posts


def first_contact(hit, high):
    assert not hit(0.), 'The starting pose already overlaps'
    low = 0.
    for probe in np.linspace(.05, high, int(high/.05)):
        if hit(float(probe)):
            high = float(probe)
            break
        low = float(probe)
    else:
        raise ValueError(f'No contact in the first {high} mm or degrees')
    for _ in range(23):
        middle = (low+high)/2
        if hit(middle):
            high = middle
        else:
            low = middle
    return high


def measure(folder):
    guide = v.read(folder / 'assembly-guide.json')['modules']['pin_hinge']
    rest = next(s for s in guide['steps'] if s['title']=='Press the lower half of the pad')['samples'][0]
    def fitted(actor):
        return b.load(folder / guide['actors'][actor]['file']).transform(transform(rest,actor)[:3])
    paddle, keeper = map(fitted, ('cap','lid'))
    switch = fitted('switch')
    # With an open pocket floor, the bought OP1 board becomes the next lower surface.
    fixed_below = b.union([keeper, *(fitted(n) for n in ('board','sockets','housing','plug','carrier'))])
    stop = first_contact(lambda a: (h.rotate(paddle,a) ^ switch).volume() > .001, 4.)
    lift = first_contact(lambda a: (h.rotate(paddle,-a) ^ keeper).volume() > .001, 4.)
    zone = b.to_world(b.box(-6.5,6.5,-4.0,1.5,10.5,15.36))
    lower = paddle ^ zone
    assert lower.volume() > 5
    station = np.array([0.,b.STATION[1],b.FREE_TOP-.8])
    poses = {'square': h.rotate(lower,stop)}
    heel = math.degrees(.35/(h.AXIS-station[1]))
    for roll in (-.8,.8):
        for dx in (-.2,.2):
            poses[f'roll_{roll}_offset_{dx}'] = h.rotate(lower,stop+.25).translate(-station).rotate(
                (heel,roll,0)).translate(station+[dx,0,0])
    def clearance(part):
        return dict(nearest_retainer_mm=round(part.min_gap(keeper,4),4),
                    pure_down_to_next_fixed_surface_mm=round(first_contact(lambda dz:(part.translate((0,0,-dz)) ^ fixed_below).volume()>.0005,3.),4))
    corners = {name:clearance(part) for name,part in poses.items()}
    # The moving upper face is meant to catch the keeper only once lifted.
    # The pin and the switch actuator need their present short, useful stroke.
    forward = [h.rotate(lower,float(a)) for a in np.linspace(0.,stop,22)]
    overlap = max((p ^ keeper).volume() for p in forward)
    upward = [h.rotate(lower,-float(a)) for a in np.linspace(0.,lift*.9,21)]
    free_return = max((p ^ keeper).volume() for p in upward)
    assert overlap < .002 and free_return < .002 and lift > .5
    return dict(centre_case_stop_deg=round(stop,4), designed_upper_catch_deg=round(lift,4),
                rest=clearance(lower), centre_and_corner_press=corners,
                press_overlap_mm3=round(overlap,6), free_return_overlap_mm3=round(free_return,6))


def retainer_insertion():
    # The new ends of the catch also have to slide past the fitted board,
    # switch and fixed R79 rails. The existing latch has deliberate contact.
    guide = v.read(OUT/'assembly-guide.json')['modules']['pin_hinge']
    old = v.read(previous.OUT/'assembly-guide.json')['modules']['pin_hinge']
    actors = guide['actors']
    new_retainer = b.load(OUT / actors['lid']['file'])
    additions = new_retainer - b.load(previous.OUT / old['actors']['lid']['file'])
    assert additions.volume() > .5
    participants = ('carrier','board','sockets','housing','plug','terminals','switch','cap')
    meshes = {n:b.load(OUT / actors[n]['file']) for n in participants}
    worst = {n:0. for n in participants}
    samples = []
    for step in guide['steps']:
        if step['title'] in ('Fit the OP1 retainer','Remove the OP1 retainer'):
            samples.extend(step['samples'])
    assert len(samples) >= 40
    for sample in samples:
        lid_pose = transform(sample,'lid')
        for name, fixed in meshes.items():
            local = (np.linalg.inv(transform(sample,name)) @ lid_pose)[:3]
            worst[name] = max(worst[name], (additions.transform(local) ^ fixed).volume())
    assert max(worst.values()) < .01, worst
    return dict(poses=len(samples), new_material_overlap_mm3={k:round(v,6) for k,v in worst.items()})


def run():
    old, new = measure(previous.OUT), measure(OUT)
    assert abs(new['centre_case_stop_deg']-old['centre_case_stop_deg'])<.05
    assert all(value['nearest_retainer_mm'] > 0 for value in new['centre_and_corner_press'].values())
    v.write(OUT/'click-comparison.json',dict(r79=old,r80=new,new_retainer_insertion=retainer_insertion(),physical_fit_verified=False))


if __name__ == '__main__':
    run()
