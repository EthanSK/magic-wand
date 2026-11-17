"""Screen an R47 native slice with R45's inherited tools, and compare its helpers with R46.

Usage (through geometry_budget.py): review47.py ARCHIVE
ARCHIVE sits in plate47's BUILD directory, beside frame.json. Writes
helper-starts.json, roof-strokes.json, the three contact-area receipts,
material.json and helper-comparison.json there.

- helper_starts45: every disposable helper bead island must trace down to
  a grounded lower layer.
- roof_strokes45: every carrier move with incomplete backing below, with
  one- and two-ended unsupported sequences.
- contact45: each helper's actually deposited roof contact under the carrier
  (projected area at the one-empty-layer gap, patch count, bed feet).
- material47: commanded filament per native object, beside R46's selected
  archive measured the same way.

These are the R46 screens. R45's whole-bead route, withdrawal and material
audit (audit45/audit46) and the independent reopen are not run here.
Projected contact areas are not peel or release forces.
"""
import json
from pathlib import Path
import sys

import holder47 as h  # configure R47 before any inherited module builds geometry

R45 = h.HERE.parent / 'carbon-rod-holders-r45-open-keyways'
sys.path.insert(0, str(R45))
import contact45  # noqa: E402
import helper_starts45  # noqa: E402
import material47  # noqa: E402
import roof_strokes45  # noqa: E402
from owner45 import layout_owners  # noqa: E402

R46_SELECTED = h.R46 / 'exports/key-holder-only'
R46_ARCHIVE = R46_SELECTED / 'R46-Key-Carrier.gcode.3mf'
CONTACTS = {'External_cradle': 'contact-areas.json', 'Front_pull_shelf': 'shelf-contact-areas.json',
            'Rear_pull_shelf': 'rear-shelf-contact-areas.json'}


def contact_summary(path):
    d = json.loads(path.read_text())
    rows, feet = d['peel_pieces'], d['actual_first_layer_cradle_islands']
    layers = [layer for row in rows for layer in row['contact_layers']]
    return {'pieces': len(rows), 'projected_contact_mm2': round(sum(r['projected_contact_area_sum_mm2'] for r in rows), 3),
            'largest_continuous_patch_mm2': round(max((r['largest_continuous_contact_patch_mm2'] for r in rows), default=0.), 3),
            'contact_patches': sum(layer['number_of_separate_contact_patches'] for layer in layers),
            'finger_guard_contact_mm2': round(sum(r['finger_guard_contact_sum_mm2'] for r in rows), 3),
            'contact_layers': len(layers),
            'bed_feet': len(feet),
            'bed_feet_without_1.2mm_grip_land': sum(not f['contains_1p2mm_diameter_grip_land'] for f in feet)}


def review(archive):
    helper_starts45.inspect(archive)
    roof_strokes45.inspect(archive)
    owners = sorted(layout_owners(archive.parent) - {'Key_Carrier', 'Release_tabs'})
    for owner in owners:
        contact45.inspect(archive, owner)
    contacts = {owner: {'r47': contact_summary(archive.parent / CONTACTS[owner]),
                        'r46_selected': contact_summary(R46_SELECTED / CONTACTS[owner])} for owner in owners}
    material = {'r47': material47.per_object(archive), 'r46_selected': material47.per_object(R46_ARCHIVE)}
    r46, r47 = material['r46_selected']['objects'], material['r47']['objects']
    material['difference_g'] = {n: round(r47.get(n, {}).get('estimated_g', 0.) - r46.get(n, {}).get('estimated_g', 0.), 3)
                                for n in sorted(set(r46) | set(r47))}
    material['helper_difference_g'] = round(material['r47']['helper_estimated_g']
                                            - material['r46_selected']['helper_estimated_g'], 3)
    (archive.parent / 'material.json').write_text(json.dumps(material, indent=1) + '\n')
    starts = json.loads((archive.parent / 'helper-starts.json').read_text())
    roofs = json.loads((archive.parent / 'roof-strokes.json').read_text())
    cad = json.loads((archive.parent / 'cad-starts.json').read_text())
    summary = {
        'archive': archive.name,
        'cad_unsupported_starts': len(cad),
        'unrooted_helper_islands': {n: len(v['unrooted_actual_components']) for n, v in starts['owners'].items()},
        'roof_sequence_classifications': roofs['sequence_classifications'],
        'unresolved_continuous_intervals': roofs['unresolved_continuous_intervals'],
        'longest_unanchored_or_one_ended_sequence': roofs['longest_unanchored_or_one_ended_sequence'],
        'longest_two_ended_sequence': roofs['longest_two_ended_sequence'],
        'helper_contacts': contacts,
        'material_estimated_g': {n: v['estimated_g'] for n, v in r47.items()},
        'material_difference_from_r46_g': material['difference_g'],
        'helper_difference_from_r46_g': material['helper_difference_g'],
        'release_force_or_strength_measured': False,
    }
    (archive.parent / 'helper-comparison.json').write_text(json.dumps(summary, indent=1, default=str) + '\n')
    print(json.dumps(summary, indent=1, default=str))


if __name__ == '__main__':
    review(Path(sys.argv[1]).resolve())
