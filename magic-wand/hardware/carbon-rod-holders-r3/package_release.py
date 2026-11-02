#!/usr/bin/env python3
"""Package checked R3 exports with their preserved source/viewer dependencies."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

def package(out: Path) -> None:
    exports = HERE / 'exports'
    manifest = json.loads((exports / 'manifest.json').read_text())
    checks = json.loads((exports / 'slice-clearances.json').read_text())
    geom = json.loads((exports / 'geometry-checks.json').read_text())
    mass = json.loads((exports / 'mass.json').read_text())
    assert checks['passed'] and geom['r3']['sensor_stl_identical_to_r2']
    assert checks['project_sha256'] == mass['archive_sha256'] == sha(exports / 'Holder-pair-sliced.3mf')
    assert checks['manifest_sha256'] == sha(exports / 'manifest.json')
    assert checks['r3_checker_sha256'] == sha(HERE / 'verify_slice.py')
    assert geom['r3_checker_sha256'] == sha(HERE / 'verify_and_render.py')
    for name, digest in manifest['source_sha256'].items():
        assert sha(HERE / name) == digest, name
    files = []
    for folder in [HERE, HERE.parent / 'carbon-rod-holders-r2', HERE.parent / 'carbon-rod-holders']:
        files += list(folder.glob('*.py')) + [folder / name for name in ['parameters.json', 'requirements.txt', 'README.md']]
    # Preserved exports are required for exact R2 comparison and unchanged-tip checks.
    files += list((HERE.parent / 'carbon-rod-holders-r2/exports').glob('*'))
    files += [HERE.parent / 'carbon-rod-holders/exports/Key_Battery_Carrier.stl']
    helpers = HERE.parent / 'printed-loop-wand'
    files += [helpers / 'shard-tube-r2' / name for name in ['direct_switches.py', 'print_projects.py', 'check_sliced_paths.py']]
    files += list((helpers / 'shard-tube-r2/print-settings').glob('*.json'))
    files += [helpers / 'v20/compare_mass.py', helpers / 'preview/view-input.mjs', helpers / 'preview/free-view-input.mjs', helpers / 'preview/free-view-controls.mjs']
    files += list((ROOT / 'docs/lib/three-0.185.1').glob('*'))
    files += list((HERE / 'preview').glob('*')) + list(exports.glob('*'))
    mapping = {'source/' + str(path.relative_to(ROOT)): path for path in files if path.is_file()}
    mapping.update({'exports/' + path.name: path for path in exports.iterdir() if path.is_file()})
    mapping['README.md'] = HERE / 'README.md'
    out.mkdir(parents=True, exist_ok=True)
    for name in ['Design-preview.png', 'Key_Battery_Carrier.stl', 'XIAO_Rod_Holder.stl',
                 'Holder-pair-layout.3mf', 'Holder-pair-sliced.3mf', 'Assembly-reference.glb']:
        shutil.copy2(exports / name, out / name)
    shutil.copy2(HERE / 'README.md', out / 'README.md')
    digests = {name: sha(path) for name, path in mapping.items()}
    target = out / 'Wand-holder-prototypes-R3.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(mapping.items()):
            archive.write(path, name)
        archive.writestr('package-sha256.json', json.dumps(digests, indent=2) + '\n')
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name, digest in digests.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    print(target)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    package(parser.parse_args().out)
