"""Qualify a changed carrier witness against the same complete native result."""
from pathlib import Path
import json
import math
import shutil

from native48 import digest, read, write, check_plate_inputs, HERE, R47


JOINT = 'R44 R middle branch-to-inner leg bond'
INPUTS = ('frame.json', 'roof-strokes.json', 'helper-starts.json', 'shelf-contact-areas.json',
          'rear-shelf-contact-areas.json', 'contact-areas.json', 'swing-tab-removal.json')


def snapshot(archive, scratch):
    import audit45, audit46, audit47, web_qualification45

    out = archive.parent
    check_plate_inputs(scratch, out)
    checks = [Path(m.__file__) for m in (audit45, audit46, audit47, web_qualification45)]
    checks.extend([HERE / 'pocket_corner48.py', HERE / 'tab_cleanup48.py'])
    candidate = read(out / 'candidate-audit.json')
    assert candidate['archive_sha256'] == digest(archive)
    assert candidate['r47_geometry_receipt_sha256'] == digest(scratch / 'stage/r47-checks.json')
    assert candidate['r47_export_sha256'] == digest(scratch / 'stage/R47-Key-Carrier-assembly.stl')
    assert candidate['op1_pocket_terminal_corner']['checker_sha256'] == digest(checks[-2])
    assert candidate['folded_landing_checker_sha256'] == {p.name: digest(p) for p in checks[1:3]}
    assert all(read(out / name)['archive_sha256'] == candidate['archive_sha256'] for name in INPUTS[1:])
    raw = out / 'carrier-before-joint-review.json'
    shutil.copyfile(out / 'candidate-audit.json', raw)
    provenance = {'archive_sha256': candidate['archive_sha256'], 'raw_audit_sha256': digest(raw),
                  'geometry_sha256': candidate['r47_geometry_receipt_sha256'],
                  'source_sha256': {p.relative_to(HERE.parent).as_posix(): digest(p) for p in checks},
                  'inputs_sha256': {name:digest(out / name) for name in INPUTS}}
    write(out / 'carrier-before-joint-inputs.json', provenance)


def qualify(archive, scratch):
    import audit47, web_qualification45, screen47
    import guard_bond48

    out = archive.parent
    inputs = read(out / 'carrier-before-joint-inputs.json')
    raw = out / 'carrier-before-joint-review.json'
    assert inputs['archive_sha256'] == digest(archive) and inputs['raw_audit_sha256'] == digest(raw)
    assert inputs['geometry_sha256'] == digest(scratch / 'stage/r47-checks.json')
    assert all(digest(HERE.parent / path) == sha for path,sha in inputs['source_sha256'].items())
    assert all(digest(out / key) == sha for key,sha in inputs['inputs_sha256'].items())
    check_plate_inputs(scratch, out)
    report = read(raw)
    # Recalculate every inherited release/material predicate from the full
    # checked inputs. Only the specifically named R44 bond has a new test.
    material = report['critical_material']
    assert JOINT in material
    replacement = report['qualified_r45_guard_replacement']['qualified']
    obsolete = web_qualification45.LEGACY_WEB_TARGETS if replacement else set()
    checked = out / 'guard-bond.json'
    strength = read(checked) if checked.exists() else {}
    old_dir = R47 / 'exports/complete-plate'
    def matching_frame(row, directory, file):
        return (row.get('archive_sha256') == digest(file)
                and row.get('layout_frame_sha256') == digest(directory/'frame.json')
                and row.get('print_carrier_sha256') == digest(directory/'R45-Key-Carrier.stl'))
    current = (strength.get('checker_sha256') == digest(Path(guard_bond48.__file__))
               and strength.get('geometry_receipt_sha256') == inputs['geometry_sha256']
               and strength.get('selected_raw_audit_sha256') == digest(raw)
               and strength.get('R47_raw_audit_sha256') == digest(old_dir/'candidate-audit.json')
               and matching_frame(strength.get('current_joint',{}), out, archive)
               and matching_frame(strength.get('R47_control',{}), old_dir, old_dir/'R47-Complete-A1-mini-PETG.gcode.3mf')
               and all(digest(HERE.parent/path) == sha for path,sha in strength['source_sha256'].items()))
    if not current:
        strength = guard_bond48.inspect(archive,scratch)
    assert strength['archive_sha256'] == inputs['archive_sha256'] and strength['passed']
    assert read(out / 'guard-bond.json') == json.loads(json.dumps(strength, allow_nan=False))
    braces = report['r46_braces']
    starts = report['layer_starts']
    raw_missing = starts['missing_printed_components']
    corner = report['op1_pocket_terminal_corner']
    assert len(corner['qualified']) + len(corner['unqualified']) == len(raw_missing)
    gates = {
        'unmodified_material_witnesses': all(v['minimum_layer_fraction']>=.9 for k,v in material.items()
                                            if k not in obsolete and k!=JOINT),
        'reassessed_right_guard_joint': strength['passed'],
        'brace_stock': all(row['minimum_layer_fraction']>=.9 for group in braces.values()
                           for name,row in group.items() if name!='cross_sections'),
        'brace_sections': all(row['coverage']>=.9 and row['native_largest_connected_mm2']>=math.pi*.95**2
                              for group in braces.values() for row in group['cross_sections']),
        'front_removal': report['whole_shelf_bead_release']['clear'] and report['individual_front_piece_release']['clear'],
        'rear_removal': report['whole_rear_shelf_bead_release']['clear'],
        'cradle_removal': report['whole_bead_release']['clear'] and not report['whole_rib_downward_release']['colliding_helper_slices'],
        'replaced_web': replacement,
        'chamfers': audit47.chamfer_gate(report['r45_chamfer_and_joints']),
        'landing': all(row['coverage']>=.9 and row['folded_landing']['passed'] for row in report['r47_landing_sections']),
        'routes': not report['unacceptable_route_obstructions'],
        'layer_starts': not starts['floating_components'] and not corner['unqualified'],
    }
    previous_material = material[JOINT]['minimum_layer_fraction'] >= .9
    old = all(v for k,v in gates.items() if k != 'reassessed_right_guard_joint') and previous_material
    assert old == report['screen_passed'], 'Inherited full-screen decision cannot be reproduced from selected evidence'
    assert all(gates.values()), {k:v for k,v in gates.items() if not v}
    report.update(screen_passed=True, raw_screen_passed=old, r48_gate_results=gates,
                  right_guard_joint_report_sha256=digest(out / 'guard-bond.json'),
                  raw_carrier_evidence_sha256=digest(out / 'carrier-before-joint-inputs.json'))
    write(out / 'candidate-audit.json', report)
    screen47.finalize(archive)
