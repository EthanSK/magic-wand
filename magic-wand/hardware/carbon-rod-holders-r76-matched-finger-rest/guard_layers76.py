"""Review the newly sliced loop and its rear support against actual extrusion paths."""
from zipfile import ZipFile

import numpy as np

import design76
import guard_layers74 as previous
from layers53 import q, roofs51
import release61


def paths_at_layer(lines, marks, layer):
    # Include the layer below so a laid bead can be distinguished from empty space.
    first = marks[layer - 2]
    block = '\n'.join(lines[first:marks[layer + 1]])
    points, _, _ = q.extrusion_points(block, .06)
    numbers, sequences, speed, fan = roofs51.map_moves(q, block, len(points), step=.06)
    return points, numbers + first, sequences, speed, fan


def bead_contacts(data, span):
    pts, numbers, seq, speed, fan = data
    start, stop = span['gcode_lines']
    ids = np.flatnonzero((numbers >= start) & (numbers <= stop))
    assert len(ids) > 1 and np.all(seq[ids] == seq[ids[0]])
    bead = pts[ids]
    layer = span['layer']
    nearby = np.all((pts[:, :2] >= bead[:, :2].min(axis=0)-1.5)
                    & (pts[:, :2] <= bead[:, :2].max(axis=0)+1.5), axis=1)
    heights = np.rint(pts[:,7]*5)
    laid = pts[nearby & ((heights == layer-1) | ((heights == layer) & (seq < seq[ids[0]])))]
    def bonded(samples):
        result = []
        for point in samples:
            distance = np.linalg.norm(laid[:,:2] - point[:2], axis=1)
            result.append(np.any((laid[:,3] + point[3])/2 - distance >= .03))
        return np.asarray(result)

    # The reported G-code lines include the short tails before/after the
    # unbacked part. Measure the longest genuinely free length at bead resolution.
    backed = bonded(bead)
    length = np.r_[0.,np.cumsum(np.linalg.norm(np.diff(bead[:,:2], axis=0), axis=1))]
    yes = np.flatnonzero(backed)
    boundaries = np.r_[0,yes,len(bead)-1]
    longest = float(max(np.diff(length[boundaries]), default=0.))
    return dict(bead_width_mm=round(float(bead[:,3].min()),3), longest_free_mm=round(longest,3),
                max_speed_mm_s=round(float(speed[ids].max()),2), min_fan_fraction=round(float(fan[ids].min()),3))


def inspect(folder):
    old = design76.old.OUT/'print-mechanisms'
    before = release61.read(old/'layers.json')['parts']
    after = release61.read(folder/'layers.json')
    frame = np.asarray(release61.read(folder/'layout.frame.json')['parts']['Key_Carrier']['assembly_to_machine'])
    assert not after['native_support_moves']
    with ZipFile(folder/release61.ARCHIVE) as archive:
        lines = archive.read('Metadata/plate_1.gcode').decode().splitlines()
    marks = {round(float(s.split(':')[1])*5): i for i,s in enumerate(lines) if s.startswith('; Z_HEIGHT:')}
    reviewed = []
    for name, part in after['parts'].items():
        if part['completely_unsupported_starts']:
            raise ValueError(f'A toolpath in {name} starts in midair')
        baseline = before[name]['runs_requiring_review']
        last_layer, data = None, None
        for span in part['runs_requiring_review']:
            if any(previous.nearby(span, ref) for ref in baseline):
                continue
            layer = span['layer']
            x,y,z,_ = np.linalg.solve(frame,[*span['midpoint_machine_xy'],layer*.2-.1,1.])
            if (name != 'Key_Carrier' or not span['two_anchors']
                    or not (-25.5 < x < -12 and 9 < y < 16 and -.6 < z < 8)):
                raise ValueError(f'Unexpected new unsupported extrusion: {name} {span}')
            if layer != last_layer:
                last_layer, data = layer, paths_at_layer(lines, marks, layer)
            contact = bead_contacts(data, span)
            # Compare with a two-ended turn from the preceding holder. On
            # partly supported walls also record the actual free bead length.
            ref = min((r for r in baseline if r['two_anchors'] and r['mm'] >= span['mm']
                       and r['bend_mm'] >= span['bend_mm']), key=lambda r:r['mm'], default=None)
            reviewed.append(dict(span=span, local_xyz_mm=[round(n,2) for n in (x,y,z)], bead=contact, reference=ref))
            # Keep any truly free length shorter than this round bar is thick.
            if not ref or contact['longest_free_mm'] >= 2*design76.prior.RADIUS:
                raise ValueError(f'The new guard extends beyond the reviewed bridge geometry: {span}')
    return reviewed
