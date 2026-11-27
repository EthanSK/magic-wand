"""Review deposition over the two relocated key seats and the round finger rest."""
from zipfile import ZipFile
import numpy as np
import design77 as d
import guard_layers76 as beads
import release61


def inspect(folder):
    baseline = release61.read(d.old.OUT / 'print-mechanisms/layers.json')['parts']
    after = release61.read(folder / 'layers.json')
    frames = release61.read(folder / 'layout.frame.json')['parts']
    if after['native_support_moves']:
        raise ValueError('Unexpected generated support')
    before = d.old.OUT / 'print-mechanisms'
    with ZipFile(before / release61.ARCHIVE) as archive:
        ref_lines = archive.read('Metadata/plate_1.gcode').decode().splitlines()
    ref_marks = {
        round(float(s.split(':')[1]) * 5): i
        for i, s in enumerate(ref_lines)
        if s.startswith('; Z_HEIGHT:')
    }
    reference_paths = {}
    with ZipFile(folder / release61.ARCHIVE) as archive:
        lines = archive.read('Metadata/plate_1.gcode').decode().splitlines()
    marks = {
        round(float(s.split(':')[1]) * 5): i
        for i, s in enumerate(lines)
        if s.startswith('; Z_HEIGHT:')
    }
    reviewed = []
    for name, part in after['parts'].items():
        if part['completely_unsupported_starts']:
            raise ValueError(f'{name} has a floating start')
        old = baseline[name]['runs_requiring_review']
        frame = np.asarray(frames[name]['assembly_to_machine'])
        prior_layer, paths = None, None
        for span in part['runs_requiring_review']:
            if any(beads.previous.nearby(span, ref) for ref in old):
                continue
            layer = span['layer']
            x, y, z, _ = np.linalg.solve(
                frame, [*span['midpoint_machine_xy'], layer * 0.2 - 0.1, 1.0]
            )
            seat = -31 < x < -11 and -9 < y < 12 and 8.8 < z < 11.6
            fork = -30 < x < -12 and 0 < y < 17 and -0.6 < z < 8
            if name != 'Key_Carrier' or not (seat or fork):
                raise ValueError(f'Unexpected extrusion at {(x,y,z)} in {name}: {span}')
            if layer != prior_layer:
                paths = beads.paths_at_layer(lines, marks, layer)
                prior_layer = layer
            contact = beads.bead_contacts(paths, span)
            # Moving this entire seat 2 mm along the assembly Y axis shifts
            # its roof exactly ten print layers. Match the same bead endpoints
            # and measured deposition, including the small return on that roof.
            if seat and abs(y - (d.PITCH - 7.15)) < 0.25:
                relocated = next(
                    (
                        r
                        for r in old
                        if r['layer'] == layer - 10
                        and r['two_anchors'] == span['two_anchors']
                        and abs(span['mm'] - r['mm']) < 0.01
                        and abs(span['bend_mm'] - r['bend_mm']) < 0.01
                        and np.allclose(
                            span['extent_machine_xy'], r['extent_machine_xy'], atol=0.012
                        )
                        and np.allclose(
                            span['midpoint_machine_xy'], r['midpoint_machine_xy'], atol=0.012
                        )
                    ),
                    None,
                )
                if relocated:
                    ref_layer = relocated['layer']
                    if ref_layer not in reference_paths:
                        reference_paths[ref_layer] = beads.paths_at_layer(
                            ref_lines, ref_marks, ref_layer
                        )
                    original = beads.bead_contacts(reference_paths[ref_layer], relocated)
                    if (
                        contact['longest_free_mm'] <= original['longest_free_mm'] + 0.06
                        and contact['min_fan_fraction'] >= original['min_fan_fraction'] - 0.01
                        and contact['max_speed_mm_s'] <= original['max_speed_mm_s'] + 0.5
                        and abs(contact['bead_width_mm'] - original['bead_width_mm']) < 0.015
                    ):
                        reviewed.append(
                            dict(
                                part=name,
                                span=span,
                                local_xyz_mm=[round(v, 2) for v in (x, y, z)],
                                bead=contact,
                                same_translated_seat=True,
                                reference=dict(relocated, bead=original),
                            )
                        )
                        continue
            if not span['two_anchors']:
                raise ValueError(f'New one-sided extrusion: {span} {contact}')
            # A straight roof crosses a full Choc opening, the same span as
            # the other three sockets. A curved finger beam must grow from a
            # previous bead or bridge less than its own diameter.
            limit = 2 * d.old.prior.RADIUS if fork else d.base.P['bay']['plate_opening_mm']
            if contact['longest_free_mm'] > limit:
                raise ValueError(f'Unbacked length exceeds local feature: {name} {span} {contact}')
            references = sorted(
                (
                    r
                    for r in old
                    if r['two_anchors']
                    and r['mm'] + 0.06 >= span['mm']
                    and r['bend_mm'] + 0.06 >= span['bend_mm']
                ),
                key=lambda r: r['mm'],
            )
            reference = next(iter(references), None)
            if contact['longest_free_mm'] > 3 and span['bend_mm'] > 0.25:
                # Compare genuinely free lengths in the existing Choc seats.
                # Only a same-layer physical match or the corresponding seat
                # moved down by two millimetres is a relevant reference.
                reference = None
                for candidate in references:
                    l = candidate['layer']
                    if l not in (layer, layer - 10):
                        continue
                    if l not in reference_paths:
                        reference_paths[l] = beads.paths_at_layer(ref_lines, ref_marks, l)
                    proof = beads.bead_contacts(reference_paths[l], candidate)
                    if (
                        proof['longest_free_mm'] + 0.06 >= contact['longest_free_mm']
                        and proof['max_speed_mm_s'] + 0.5 >= contact['max_speed_mm_s']
                        and proof['min_fan_fraction'] <= contact['min_fan_fraction'] + 0.01
                    ):
                        reference = dict(candidate, bead=proof)
                        break
            if reference is None:
                raise ValueError(f'No comparable deposited span in the reference holder: {span}')
            reviewed.append(
                dict(
                    part=name,
                    span=span,
                    local_xyz_mm=[round(v, 2) for v in (x, y, z)],
                    bead=contact,
                    reference=reference,
                )
            )
    return reviewed
