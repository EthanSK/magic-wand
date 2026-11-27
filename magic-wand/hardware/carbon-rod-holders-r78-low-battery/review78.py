"""Compare actual extrusions with R77; inspect changed rail runs against laid beads."""
from zipfile import ZipFile

import numpy as np
import guard_layers76 as beads
import plate77
import release61


def inspect(folder, *, baseline=None, part_baselines=None):
    baseline = baseline or plate77.OUT / 'print-mechanisms'
    before = release61.read(baseline / 'layers.json')['parts']
    after = release61.read(folder / 'layers.json')
    if after['native_support_moves']:
        raise ValueError('Unexpected generated supports on the fit plate')
    reference_frames = release61.read(baseline / 'layout.frame.json')['parts']
    for name, directory in (part_baselines or {}).items():
        before[name] = release61.read(directory / 'layers.json')['parts'][name]
        reference_frames[name] = release61.read(directory / 'layout.frame.json')['parts'][name]
    frames = release61.read(folder / 'layout.frame.json')['parts']
    with ZipFile(folder / release61.ARCHIVE) as archive:
        lines = archive.read('Metadata/plate_1.gcode').decode().splitlines()
    marks = {round(float(line.split(':')[1]) * 5): i for i, line in enumerate(lines)
             if line.startswith('; Z_HEIGHT:')}
    reviewed = []
    for name, part in after['parts'].items():
        if part['completely_unsupported_starts']:
            raise ValueError(f'{name} has an unsupported start')
        frame = np.asarray(frames[name]['assembly_to_machine'])
        ref_frame = np.asarray(reference_frames[name]['assembly_to_machine'])
        if not np.allclose(frame[:3,:3], ref_frame[:3,:3]):
            raise ValueError(f'Orientation changed for {name}')
        dx, dy, dz = (frame-ref_frame)[:3,3]
        if abs(dz) > .005:
            raise ValueError(f'Changed first layer reference for {name}')
        prior = []
        for row in before[name]['runs_requiring_review']:
            updated = dict(row)
            updated['extent_machine_xy'] = np.asarray(row['extent_machine_xy']) + [dx, dy, dx, dy]
            prior.append(updated)
        paths = {}
        for span in part['runs_requiring_review']:
            if any(beads.previous.nearby(span, ref) for ref in prior):
                continue
            layer = span['layer']
            local = np.linalg.solve(frame, [*span['midpoint_machine_xy'], layer * .2 - .1, 1])[:3]
            if layer not in paths:
                paths[layer] = beads.paths_at_layer(lines, marks, layer)
            contact = beads.bead_contacts(paths[layer], span)
            # Short two-ended returns can bridge between adjacent printed lines.
            # Anything longer or one-sided requires its own local evidence.
            if not span['two_anchors'] or contact['longest_free_mm'] > 1.5:
                raise ValueError(f'{name} needs review at {local} on layer {layer}: {span} {contact}')
            reviewed.append(dict(part=name, local_xyz_mm=local.round(3).tolist(), span=span, bead=contact))
    return reviewed
