"""Seal the checked native slice for Studio without editable model resources.

This reuses R37/R44's established print-only package. Opening the delivered
file must not regenerate toolpaths or relocate the timelapse wipe tower.
"""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from holder45 import inherited  # establishes the archived project imports
import plate38


def package(source, output):
    source = source.resolve()
    checks = json.loads((source.parent / 'delivery-checks.json').read_text())
    assert checks['archive_sha256'] == sha256(source.read_bytes()).hexdigest()
    review = json.loads((source.parent / 'trial-review.json').read_text())
    assert review['selected_archive_sha256'] == checks['archive_sha256']
    assert review['digital_checks_passed'] is True, 'Unresolved trial-file checks'
    result = plate38.recipe.make_print_only(source, output)
    target = output / 'R45-Key-Holder-Only-print-only.3mf'
    result.rename(target)
    with ZipFile(source) as before, ZipFile(target) as after:
        assert before.read('Metadata/plate_1.gcode') == after.read('Metadata/plate_1.gcode')
    receipt_path = output / 'print-only.json'
    receipt = json.loads(receipt_path.read_text())
    receipt.update(file=target.name, sha256=sha256(target.read_bytes()).hexdigest(),
                   generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                   physical_trial_verified=False)
    assert receipt['gcode_sha256'] == checks['gcode_sha256']
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    # Delivery owns the generated viewer too: compose it from this exact
    # audited part inventory every time a checked native file is sealed.
    from guide45 import build as compose_guide
    from evidence45 import inventory
    compose_guide(source.parent)
    inventory(source.parent, source)
    print('Sealed unchanged G-code', target.name, receipt['sha256'], flush=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    package(args.archive, args.output)
