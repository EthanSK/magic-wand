"""Check native material across the retainer arms and the two loaded spring roots."""
import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

from audit80 import b, v
from plate80 import previous
import sections69
import design80


def sections(points, frame):
    # Compare like with like: the 95% R59 rule is for solid CAD sections and
    # is enforced in design80. The R79 print gives the actual bead baseline.
    # Both scans sample toolpaths at 0.12 mm. Allow 0.01 mm² when comparing
    # minimum cross-sections, which can occur at different stations.
    fitted = previous.OUT / 'print-mechanisms'
    fitted_points, _ = v.read_native(fitted / v.ARCHIVE)
    fitted_frame = v.read(fitted / 'layout.frame.json')['parts']['OP1_Lid_Stop']
    reference = sections69.tine_sections(fitted_points, np.asarray(fitted_frame['assembly_to_machine']))
    del fitted_points
    tines = sections69.tine_sections(points, np.asarray(frame['OP1_Lid_Stop']['assembly_to_machine']))
    for side, row in tines.items():
        row['r79_native_minimum_mm2'] = reference[side]['minimum_area_mm2']
        assert row['minimum_area_mm2'] >= row['r79_native_minimum_mm2'] - .01, (side, row['minimum_area_mm2'])

    inv = np.linalg.inv(np.asarray(frame['DFR_Post_Bar']['assembly_to_machine']))
    assert np.isclose(inv[2,2],1)
    xyz = points[:,:3] @ inv[:3,:3].T + inv[:3,3]
    low, high = b.HOLE_Y+design80.ARM_OUT, b.HOLE_Y+design80.ARM_IN
    floor, roof = design80.BASE0, design80.ARM_TOP
    near = (xyz[:,1]>=low-.5)&(xyz[:,1]<=high+.5)&(xyz[:,2]>floor)&(xyz[:,2]<roof+.3)
    xyz, beads = xyz[near], points[near]
    window = box(low,floor,high,roof)
    roots = {}
    for label, sign in [('left',-1),('right',1)]:
        values = []
        for distance in (1.15,1.55,2.05,3.05,4.05,5.05):
            station = sign*distance
            dx = xyz[:,0]-station
            at = abs(dx) < beads[:,3]/2
            half = np.sqrt(np.maximum(0., (beads[at,3]/2)**2 - dx[at]**2))
            rects = [box(y-r,z-h,y+r,z) for (_,y,z),r,h in zip(xyz[at],half,beads[at,4]) if r>1e-5]
            area = unary_union(rects).intersection(window).area
            assert area>1.05,(label,station,area)
            values.append(dict(station_mm=round(station,3),area_mm2=round(area,4)))
        roots[label] = values
    return dict(retainer_tines=tines, post_spring_roots=roots)
