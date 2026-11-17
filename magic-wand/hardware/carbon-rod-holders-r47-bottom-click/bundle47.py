"""Publish the checked complete plate and seal its original native G-code."""
import argparse
import json
from pathlib import Path
import shutil
from zipfile import ZipFile
import holder47 as h
import plate38
from compose47 import FUNCTIONAL
from plate45 import digest


def trial_review(work):
    """Apply the reviewed R46 trial envelope; retain all roof residuals."""
    archive = work / 'R47-Complete-A1-mini-PETG.gcode.3mf'
    sha = digest(archive)
    files = ('candidate-audit.json', 'helper-starts.json', 'roof-strokes.json',
             'roof-residual-context.json', 'contact-areas.json', 'shelf-contact-areas.json',
             'rear-shelf-contact-areas.json', 'delivery-checks.json', 'empty-space-checks.json',
             'other-audit/other-parts-audit.json')
    reports = {name: json.loads((work / name).read_text()) for name in files}
    assert all(row['archive_sha256'] == sha for row in reports.values())
    assert reports['candidate-audit.json']['screen_passed']
    assert reports['other-audit/other-parts-audit.json']['passed']
    assert reports['empty-space-checks.json']['maximum_interior_overlap_mm3'] < .0001
    roof = reports['roof-strokes.json']
    gaps = roof['sequence_gaps']
    unanchored = [r for r in gaps if not (r['before'] or r['after'])]
    expected = [(9., .62), (18., .407), (30., .464), (30.4, .57), (30.8, .523)]
    assert sorted((r['z'], r['mm']) for r in unanchored) == expected
    long = [r for r in gaps if r['classification'] == 'beyond screened anchored span']
    assert all(r['before'] and r['after'] and r['deviation_from_chord_mm'] < .1
               and r['mm'] <= 13.565 for r in long)
    bent = [r for r in gaps if r['classification'] == 'unsupported bend outside bead corridor']
    assert all(r['before'] and r['after'] and r['mm'] <= 2.732 for r in bent)
    one_ended = [r for r in gaps if bool(r['before']) != bool(r['after'])]
    # The longest R47 edge overhang is 0.018 mm longer than R46's 1.037 mm.
    # Accept this bounded first-fit trial, not a claim of direct backing.
    assert max(r['mm'] for r in one_ended) <= 1.057
    report = {
        'selected_archive_sha256': sha, 'digital_checks_passed': True,
        'designation': 'Digitally checked complete first-fit trial; not physically accepted',
        'functional_parts': sorted(FUNCTIONAL),
        'report_sha256': {name: digest(work / name) for name in files},
        'unbacked_short_strokes': unanchored,
        'longer_two_ended_bridge_count': len(long),
        'maximum_straight_trial_bridge_mm': max(r['mm'] for r in long),
        'maximum_two_ended_bent_run_mm': max(r['mm'] for r in bent),
        'maximum_one_ended_mm': max(r['mm'] for r in one_ended),
        'residual_disposition': (
            'Five short unanchored strokes retain R46 layer/length signatures. '
            'The longer straight bridges retain two rooted ends and the R46 span limit; '
            'bent runs retain the R46 maximum. The longest one-ended edge differs by 0.018 mm. '
            'Actual contexts are retained; following-layer capture is not prior backing. '
            'R46 printed successfully but left wisps and support nubs. Sag, wisps, release effort, '
            'bought-part fit, click force and strength remain physical-trial limits.'),
        'independent_review_disposition': (
            'Opus reviewed the preceding same-geometry archive and required explicit left-joint solid fill. '
            'The selected re-slice has the recommended selectors and passed fresh full-path audits. '
            'Missing eight-part and roof coverage was completed. The construction-overlap fringe stays '
            'reported, with all designed chamfer slabs tested. Nominal mounting end contacts are '
            'reported separately from strictly clear interiors. Physical switch-stop margins remain unverified.'),
        'physical_acceptance_verified': False, 'gui_send_ready_verified': False,
    }
    (work / 'trial-review.json').write_text(json.dumps(report, indent=2) + '\n')
    reopen_path = work / 'reopen-checks.json'
    reopen = json.loads(reopen_path.read_text())
    assert reopen['selected_archive_sha256'] == sha
    reopen.update(own_final_deposition_audited=True, trial_review_sha256=digest(work / 'trial-review.json'))
    reopen_path.write_text(json.dumps(reopen, indent=2) + '\n')
    return report


def publish(scratch, work):
    trial_review(work)
    output = h.HERE / 'exports/complete-plate'
    output.mkdir(parents=True, exist_ok=True)
    for path in work.iterdir():
        if path.is_file() and (path.suffix in ('.json', '.stl') or path.name in (
                'R47-Complete-A1-mini-PETG.gcode.3mf', 'R47-Complete-A1-mini-PETG-layout.3mf',
                'R45-Key-Carrier-layout.3mf')):
            shutil.copyfile(path, output / path.name)
    for folder, target in ((work / 'other-audit', output / 'other-audit'),
                           (scratch / 'parent-audit-targets/r45-standing', output / 'r45-standing')):
        shutil.copytree(folder, target, dirs_exist_ok=True)
    archive = output / 'R47-Complete-A1-mini-PETG.gcode.3mf'
    sealed = plate38.recipe.make_print_only(archive, output)
    target = output / 'R47-All-Components-print-only.3mf'
    if sealed != target:
        sealed.replace(target)
    with ZipFile(archive) as original, ZipFile(target) as final:
        assert original.read('Metadata/plate_1.gcode') == final.read('Metadata/plate_1.gcode')
        (output / 'plate-preview.png').write_bytes(original.read('Metadata/plate_1.png'))
    receipt_path = output / 'print-only.json'
    receipt = json.loads(receipt_path.read_text())
    receipt.update(file=target.name, sha256=digest(target), generator_sha256=digest(Path(__file__)))
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    manifest_path = h.HERE / 'exports/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['source_sha256'] = {p.name: digest(p) for p in sorted(h.HERE.glob('*.py'))
                               + [h.HERE / 'complete-assembly.json']}
    manifest.update(digital_complete_plate_checks_passed=True, selected_archive_sha256=digest(archive))
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    geometry_path = h.HERE / 'exports/geometry-checks.json'
    geometry = json.loads(geometry_path.read_text())
    geometry.update(sliced=True, selected_native_archive_sha256=digest(archive),
                    native_trial_review='complete-plate/trial-review.json')
    geometry_path.write_text(json.dumps(geometry, indent=2) + '\n')
    evidence = {
        'selected_archive_sha256': digest(archive), 'print_only_sha256': digest(target),
        'source_sha256': manifest['source_sha256'],
        'files_sha256': {p.relative_to(output).as_posix(): digest(p) for p in sorted(output.rglob('*'))
                         if p.is_file() and p.name != 'evidence.json'},
        'guide_sha256': digest(h.HERE / 'exports/assembly-guide.json'),
        'physical_acceptance_verified': False,
    }
    (output / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print('Published checked complete trial', target, flush=True)
    return target


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('scratch', type=Path); p.add_argument('work', type=Path)
    a = p.parse_args(); publish(a.scratch.resolve(), a.work.resolve())
