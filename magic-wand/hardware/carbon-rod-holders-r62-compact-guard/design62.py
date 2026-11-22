"""R62 uses the proven switch interfaces with a bottom-first finger ramp and compact hinge tongue."""
from pathlib import Path
from hashlib import sha256
import json
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
PREVIOUS = HERE.parent / 'carbon-rod-holders-r61-top-battery'
sys.path.insert(0, str(PREVIOUS))
import design61 as r61

b, k = r61.b, r61.k
# The finger-side view calls -Y the bottom. Both dimensions are along the
# holder, so a sideways sweep cannot make a steep bottom slope look shallower.
BOTTOM_ROOT = -9.3
BOTTOM_CROWN = 5.2
TOP_CROWN = 10.2
TOP_ROOT = 21.0


CROWN_END = (22.1, BOTTOM_CROWN, .88)
CROWN_START = (20.4, TOP_CROWN, .88)
TOP_PATH = [(11.25, TOP_ROOT, 8.7), (12.0, 18.4, 5.3), (11.7, 11.3, .1), CROWN_START]


def bottom_path(x):
    return [(x, BOTTOM_ROOT, 8.3), (x, -3.6, 6.1), (x, -1.5, .88), CROWN_END]


def finger_guard():
    # Keep a low open basket over the contacts. Take the two long bottom
    # rails outside the backer's path before lifting them into their roots.
    shapes = [r61.curve(TOP_PATH, 1.32)]
    for x in (15.1, 22.1, 28.1):
        shapes.append(r61.curve([CROWN_START, (x, 9.5, .88), (x, 6.6, .88), CROWN_END], 1.26))
    for x in (14.2, 28.3):
        shapes.append(r61.curve(bottom_path(x), 1.35))
    return b.union(shapes)


def compact_tail(deck):
    old = r61.prior.BED
    # Only the central tongue carries the pin cheeks, rod and cable passage.
    # Rounded outside shoulders return to the original carrier within 4.5 mm.
    stations = [(32, -.12), (28.5, 0), (22, 1.2), (17, 4.4),
                (12.25, 10.8), (12.0, r61.REAR+.3)]
    outline = [(width,old+depth) for width,depth in stations]
    outline += [(-width,old+depth) for width,depth in reversed(stations)]
    outline += [(-32,-50),(32,-50)]
    return r61.tail(deck) ^ b.prism_xy(outline,-15,40)


def main():
    OUT.mkdir(exist_ok=True)
    carrier,base,guards,cradle,working,routes = r61.holder(finger_guard, compact_tail)
    # Open the inboard shoulder of the upper-right clip only where the
    # native wall entered the latch route. The cut spans the folded edge.
    # Open the notch through the top edge. A thin roof here would begin
    # as an isolated extrusion in the rear-down print orientation.
    clip_clearance = b.box(12.3,15.2,22,25.15,8.35,13.2)
    carrier -= clip_clearance
    pieces = sorted(carrier.decompose(),key=lambda s: -s.volume())
    assert sum(abs(s.volume()) for s in pieces[1:]) < .05
    mesh = OUT/'Key_Carrier-assembly.stl'
    b.save_closed(mesh,pieces[0].simplify(.001))
    carrier = b.load(mesh)
    interior = b.box(12.4,15.1,22.1,25.05,8.45,10.5)
    if not (carrier ^ interior).is_empty():
        # The inherited socket wall can fold back inside its own boundary.
        # Trim its indexed STL faces too, so no internal skin reaches the slicer.
        b.save_closed(mesh, carrier - clip_clearance)
        carrier = b.load(mesh)
    assert (carrier ^ interior).is_empty(), 'A folded mesh remains inside the switch clip relief'
    previous = b.load(r61.OUT/mesh.name)
    shoulder_zone = b.box(-40,40,r61.prior.BED+.01,r61.BED+.1,7.95,32)
    shoulder_volume = lambda body: (body ^ shoulder_zone).volume()
    report = dict(revision='R62', physical_fit_verified=False,
                  source_sha256=sha256(mesh.read_bytes()).hexdigest(),
                  bottom_run_mm=round(BOTTOM_CROWN-BOTTOM_ROOT,2),
                  top_run_mm=round(TOP_ROOT-TOP_CROWN,2),
                  carrier_volume_mm3=round(carrier.volume(),2),
                  previous_carrier_volume_mm3=round(previous.volume(),2),
                  previous_rear_shoulder_mm3=round(shoulder_volume(previous),2),
                  rear_shoulder_mm3=round(shoulder_volume(carrier),2),
                  guard_root_overlap_mm3=round(k.vol(base,guards),2),
                  cradle_overlap_mm3=round(k.vol(base,cradle),2),
                  key_poses_checked=0,key_obstructions=[],backer_sweep_mm3={})
    for name,gauge in routes.items():
        for i,pose in enumerate(r61.prior.c.poses(gauge)):
            report['key_poses_checked'] += 1
            overlap = k.vol(carrier,pose)
            if overlap>.01: report['key_obstructions'].append([name,i,round(overlap,4)])
    for side,sign in [('Left',-1),('Right',1)]:
        strip=b.load(r61.prior.old.R58/'exports'/f'Socket_Backer_{side}-assembly.stl')
        report['backer_sweep_mm3'][side]=max(k.vol(carrier,strip.translate((sign*t,0,0))) for t in range(27))
    print(json.dumps(report,indent=2),flush=True)
    (OUT/'carrier.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not report['key_obstructions'] and max(report['backer_sweep_mm3'].values())<.01
    assert report['guard_root_overlap_mm3']>15 and report['cradle_overlap_mm3']>15
    assert carrier.volume()<previous.volume() and report['bottom_run_mm']>report['top_run_mm']


if __name__ == '__main__':
    main()
