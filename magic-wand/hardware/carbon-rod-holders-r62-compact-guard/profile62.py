"""Check the actual shoulder projections and the remaining core along both finger guards."""
from hashlib import sha256
from math import atan2, degrees
import json

from design62 import OUT, TOP_PATH, b, bottom_path, r61


def root_angle(points):
    (_, y, z), (_, y1, z1) = points[:2]
    return round(degrees(atan2(abs(z1-z),abs(y1-y))),1)


def main():
    mesh=OUT/'Key_Carrier-assembly.stl'
    carrier=b.load(mesh)
    behind_keys={}
    for x in (-21,21):
        band=carrier ^ b.box(x-.01,x+.01,r61.prior.BED,50,7.95,32)
        assert not band.is_empty()
        behind_keys[str(x)]=round(band.bounding_box()[4]-r61.prior.BED,2)
    # Each continuous 2.1 mm centre core must survive the switch cut-outs.
    # Check the exported mesh on each side independently, including both feet.
    remaining={}
    for name,points in [('top',TOP_PATH),('inner_bottom',bottom_path(14.2)),('outer_bottom',bottom_path(28.3))]:
        right=r61.curve(points,1.05)
        for side,core in [('right',right),('left',right.mirror((1,0,0)))]:
            remaining[side+'_'+name]=round((core-carrier).volume(),4)
    result=dict(carrier_sha256=sha256(mesh.read_bytes()).hexdigest(),
                bottom_root_angle_deg=root_angle(bottom_path(14.2)),top_root_angle_deg=root_angle(TOP_PATH),
                rear_extension_at_key_centres_mm=behind_keys,missing_guard_core_mm3=remaining,
                nominal_wire_to_hinge_fore_aft_gap_mm=round(r61.m.BARREL_Y[0]+r61.REAR-r61.lead().bounding_box()[4],2))
    print(json.dumps(result,indent=2),flush=True)
    assert result['bottom_root_angle_deg']<result['top_root_angle_deg'] and max(behind_keys.values())<5
    assert max(remaining.values())<.01,remaining
    (OUT/'profile.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
