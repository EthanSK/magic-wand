"""Run the shared contact checker on the original key-only and complete fixtures.

Use a fresh CAD Python process for each revision. Scratch is required because
contact45 writes its output alongside its input; archived evidence stays intact.
"""
from pathlib import Path
import sys
from unittest.mock import patch

from native48 import digest, read, write, HERE


def run(number, scratch):
    if number == 'r46':
        source = HERE.parent / 'carbon-rod-holders-r46-middle-to-edge'
        sys.path.insert(0, str(source))
        import holder46
        exports, name = source / 'exports/key-holder-only', 'R46-Key-Carrier.gcode.3mf'
    elif number == 'r47':
        source = HERE.parent / 'carbon-rod-holders-r47-bottom-click'
        sys.path.insert(0, str(source))
        import holder47
        exports, name = source / 'exports/complete-plate', 'R47-Complete-A1-mini-PETG.gcode.3mf'
    else:
        raise ValueError(number)

    import contact45
    stage = scratch / 'contact-regression' / number
    stage.mkdir(parents=True, exist_ok=True)
    fixture = exports / name
    parts = read(exports / 'shelf-cad.json')['removable_pieces']
    inputs = {f.name: f for f in (fixture, exports / 'frame.json', exports / 'shelf-cad.json', exports / 'rear-shelf-cad.json')}
    for part in parts:
        key = part['file']
        # The R46 publisher renamed the public meshes to R46; the project
        # shelf still refers to its generator's internal R45 filenames.
        file = exports / key
        if not file.is_file() and number == 'r46':
            file = exports / key.replace('R45-', 'R46-', 1)
        assert digest(file) == part['sha256']
        inputs[key] = file
    for name_in_fixture, file in inputs.items():
        link = stage / name_in_fixture
        if link.is_symlink() and not link.exists():
            link.unlink()
        if not link.exists():
            link.symlink_to(file)
        assert file.is_file() and link.resolve() == file.resolve()
    # Cache parsing for this identical archive while keeping the original
    # native deposition, setup, frame and existing fixtures intact.
    checker = contact45.prior.common.load_checker()
    actual = checker.audit.read_project(fixture)
    with patch.object(contact45.prior.common, 'load_checker', return_value=checker), \
         patch.object(checker.audit, 'read_project', return_value=actual):
        for owner in ('Front_pull_shelf', 'Rear_pull_shelf', 'External_cradle'):
            contact45.inspect(stage / name, owner)
    filename = 'shelf-contact-areas.json'
    before, after = read(exports / filename), read(stage / filename)
    assert after['archive_sha256'] == before['archive_sha256'] == digest(fixture)
    if number == 'r46':
        assert before == after, 'Original key-only contact witness changed'
    else:
        assert all(piece['projected_contact_area_sum_mm2'] == 0 for piece in before['peel_pieces'])
        assert all(piece['projected_contact_area_sum_mm2'] > 0 for piece in after['peel_pieces'])
    rows = [{'piece': old['removable_piece'], 'recorded_mm2': old['projected_contact_area_sum_mm2'],
             'corrected_mm2': new['projected_contact_area_sum_mm2']}
            for old, new in zip(before['peel_pieces'], after['peel_pieces'], strict=True)]
    result = {'revision': number, 'archive_sha256': digest(fixture),
              'recorded_report_sha256': digest(exports / filename),
              'rechecked_report_sha256': digest(stage / filename),
              'checker_sha256': digest(Path(contact45.__file__)),
              'bed_translation_mm': read(exports / 'frame.json')['bed_translation'],
              'front_pieces': rows, 'passed': True}
    result['all_peel_pieces'] = {}
    for owner, filename in [('Front_pull_shelf', 'shelf-contact-areas.json'),
                            ('Rear_pull_shelf', 'rear-shelf-contact-areas.json'),
                            ('External_cradle', 'contact-areas.json')]:
        pieces = read(stage / filename)['peel_pieces']
        result['all_peel_pieces'][owner] = [
            {k: row.get(k) for k in ('removable_piece', 'bed_xy_bounds_mm',
             'projected_contact_area_sum_mm2', 'largest_continuous_contact_patch_mm2', 'finger_guard_contact_sum_mm2')}
            for row in pieces]
    write(stage / 'result.json', result)
    print(rows, flush=True)


if __name__ == '__main__':
    run(sys.argv[1], Path(sys.argv[2]))
