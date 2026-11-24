"""Measure the worst deposited bead along the carbon rod and the *same* pin line in both parts."""
import argparse
from pathlib import Path
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r62-compact-guard'))
from design62 import r61
from openings53 import read_native
from verify59 import ARCHIVE, digest

# The native path reader samples every 0.12 mm or closer (including arc endpoints).
# Expand the bead envelope by half that spacing, also at longitudinal boundaries.
MARGIN = .06


def pin_cross_section(paths, frame, axis_y, name, axis_z=None):
    # The part's hinge runs along assembly X. Each print pose maps it onto bed X or Y.
    along = int(np.argmax(abs(frame[:2, 0])))
    cross = 1 - along
    assert abs(frame[along, 0]) > .9999
    anchor = frame @ [0, axis_y, r61.m.CHEEK_HOLE_Z if axis_z is None else axis_z, 1]
    # Check the pin while it approaches both external cheek faces, including
    # its far end when its leading end first enters the stationary assembly.
    reach = r61.m.CHEEK_X[1] + 2*r61.m.PIN_HALF
    local = paths[(abs(paths[:, along] - anchor[along]) < reach + paths[:, 3]/2 + MARGIN)
                  & (abs(paths[:, cross] - anchor[cross]) < 5)
                  & (abs(paths[:, 2] - anchor[2]) < 5)]
    assert len(local)>250
    def clearance(y, z, *, witness=False):
        centre = frame @ [0, y, z, 1]
        across = np.maximum(abs(local[:, cross] - centre[cross]) - local[:, 3]/2 - MARGIN, 0)
        # Z is the commanded layer top. Include the entire slab and all beads.
        vertical = np.maximum.reduce([centre[2] - local[:,2], local[:,2] - local[:,4] - centre[2],
                                      np.zeros(len(local))])
        radii = np.hypot(across, vertical)
        if witness:
            row = local[np.argmin(radii)]
            point = np.linalg.solve(frame, [*row[:3], 1])
            return dict(part=name, layer_top_mm=round(float(row[2]),3),
                        layer_height_mm=round(float(row[4]),3), bead_width_mm=round(float(row[3]),3),
                        feature_index=int(row[5]), assembly_bead_centre_at_layer_top_mm=point[:3].round(3).tolist())
        return float(radii.min())
    return clearance


def shaft_envelopes(folder):
    """Upper bounds for the straight bearing portions of the two already printed R62 pins."""
    paths, _ = read_native(folder / ARCHIVE)
    layout = json.loads((folder / 'layout.frame.json').read_text())['parts']
    measured = {}
    for name in ('Hinge_Pin', 'Hinge_Pin_Snug'):
        pose = np.asarray(layout[name]['assembly_to_machine'])
        assert np.allclose(pose[:3,:3], np.eye(3))
        x, y, z, _ = pose @ [0, r61.AXIS, r61.m.PIN_Z, 1]
        # Both base ties are at the axial ends. At the bearing stations the
        # panel lies across the open moat, outside this 2 mm search radius.
        # Exclude the centre groove and the transition at the tapered ends.
        shaft = paths[(abs(paths[:,0]-x)>4) & (abs(paths[:,0]-x)<9) & (abs(paths[:,1]-y)<2)]
        assert len(shaft) > 100 and np.ptp(shaft[:,2]) > 2
        side = abs(shaft[:,1] - y) + shaft[:,3]/2
        vertical = np.maximum(abs(shaft[:,2] - z), abs(shaft[:,2] - shaft[:,4] - z))
        measured[name] = round(2*float(np.hypot(side,vertical).max()),3)
    return dict(archive_sha256=digest(folder / ARCHIVE), straight_shaft_envelope_diameter_mm=measured)


def collet_profile(paths, pose):
    """Measure the separate split grip from flange to tip at each deposited layer."""
    assert np.allclose(pose[:3,1], [0,0,-1])
    xy = paths[:,:2] - pose[:2,3]
    radius = np.linalg.norm(xy, axis=1)
    # The release tab and base are outside the working cone. Restrict the
    # angular sector to the backed wall opposite the mouth and omit the flange.
    accepted = (radius<6) & (abs(np.arctan2(xy[:,1],xy[:,0])) < np.deg2rad(105)) & (paths[:,2]>1.41)
    band = paths[accepted]
    radii = radius[accepted]
    assert len(band)>1000
    layers = []
    for top in np.unique(band[:,2]):
        mask=band[:,2]==top
        widths=band[mask,3]
        inside=radii[mask]-widths/2
        outside=radii[mask]+widths/2
        layers.append(dict(z=round(float(top),2), inside_diameter=round(2*float(inside.min()),3),
                           outside_diameter=round(2*float(outside.max()),3)))
    assert len(layers)>=20 and layers[-1]['outside_diameter'] > 8
    return dict(layers=layers, grip_is_split=True, physical_grip_unmeasured=True)


def inspect(folder, axis_y, reused_paddle=None, *, axis_z=None):
    archive = folder / ARCHIVE
    paths, names = read_native(archive)
    layout = json.loads((folder/'layout.frame.json').read_text())['parts']
    frame = np.asarray(layout['Key_Carrier']['assembly_to_machine'])
    assert np.allclose(frame[:3,1], [0,0,-1])
    scan = paths[(abs(paths[:,0]-frame[0,3])<5.5) & (abs(paths[:,1]-frame[1,3])<5.5)]
    min_r = np.hypot(scan[:,0]-frame[0,3], scan[:,1]-frame[1,3])-scan[:,3]/2-MARGIN
    assert len(scan)>1000
    idx = int(np.argmin(min_r))
    rings = {}
    for top in sorted(set(scan[:,2])):
        ring = min_r[scan[:,2]==top]
        rings[float(top)] = float(ring.min())
    cheek = pin_cross_section(paths, frame, axis_y, 'Key_Carrier', axis_z)
    if 'Touch_Paddle' in layout:
        barrel=pin_cross_section(paths, np.asarray(layout['Touch_Paddle']['assembly_to_machine']), axis_y, 'Touch_Paddle', axis_z)
        paddle_sha=digest(archive)
    else:
        assert reused_paddle is not None
        other, paddle_names=read_native(reused_paddle/ARCHIVE)
        pose=json.loads((reused_paddle/'layout.frame.json').read_text())['parts']['Touch_Paddle']
        barrel=pin_cross_section(other, np.asarray(pose['assembly_to_machine']), axis_y, 'Touch_Paddle', axis_z)
        paddle_sha=digest(reused_paddle/ARCHIVE)
    height = (r61.m.BARREL_HOLE_Z + r61.m.CHEEK_HOLE_Z)/2 if axis_z is None else axis_z
    candidates = []
    # Seek one unloaded insertion line usable by the carrier AND the resting paddle.
    # Check each individual throat too, so one component cannot mask the other's problem.
    for y in axis_y + np.arange(-.28,.281,.04):
        for z in height + np.arange(-.38,.381,.02):
            a, b = cheek(y,z), barrel(y,z)
            candidates.append((min(a,b),a,b,y,z))
    best = max(candidates)
    evidence=[]
    for profile, features in ((cheek,names), (barrel,names if 'Touch_Paddle' in layout else paddle_names)):
        witness=profile(*best[3:],witness=True)
        witness['feature']=features[witness.pop('feature_index')]
        evidence.append(witness)
    grip = collet_profile(paths,np.asarray(layout['Rod_Collet']['assembly_to_machine'])) if 'Rod_Collet' in layout else None
    return dict(archive_sha256=digest(archive), paddle_archive_sha256=paddle_sha, collet=grip,
                rod_min_clear_diameter_mm=round(2*float(min_r.min()),3),
                rod_limiting_feature=names[int(scan[idx,5])],rod_limiting_layer_top_mm=round(float(scan[idx,2]),3),
                rod_layers_under_8mm=sum(r<4 for r in rings.values()), rod_layers_sampled=len(rings),
                cheek_unloaded_max_diameter_mm=round(2*max(c[1] for c in candidates),3),
                paddle_unloaded_max_diameter_mm=round(2*max(c[2] for c in candidates),3),
                assembled_clear_diameter_mm=round(2*best[0],3),cheek_at_shared_line_mm=round(2*best[1],3),
                paddle_at_shared_line_mm=round(2*best[2],3),shared_insertion_yz_mm=[round(i,3) for i in best[3:]],
                limiting_beads=evidence,standard_pin_mm=3.,optional_snug_pin_mm=3.2,
                method='Finite sampled common insertion axes, all toolpath bead types, full layer heights and 0.06 mm XY sampling allowance. Sag and print variation unmeasured.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('plate',type=Path)
    parser.add_argument('axis_y',type=float)
    parser.add_argument('--reused-paddle',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=inspect(args.plate,args.axis_y,args.reused_paddle)
    print(json.dumps(report,indent=2))
    if args.output:
        args.output.write_text(json.dumps(report,indent=2)+'\n')
