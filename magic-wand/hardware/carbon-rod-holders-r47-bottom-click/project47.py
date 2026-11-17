"""Compose all nine functional parts and preserve the checked key/helper frame."""
import argparse
from pathlib import Path
import hashlib
import json
import shutil
import bracket47
import compose47

HERE=Path(__file__).resolve().parent
R42=HERE.parent/'carbon-rod-holders-r42-lower-diagonal/exports'


def prepare(scratch,output,key=None):
    stage=scratch/'stage';key=key or scratch/'final-key-layout'
    checks=stage/'r47-checks.json'
    assert json.loads(checks.read_text())['r47']['passed']
    output.mkdir(parents=True,exist_ok=True)
    bracket=output/'R47-Bracket-and-Clips-layout.3mf'
    bracket47.prepare(R42/'print-trial/R42-Complete-A1-mini-PETG-layout.3mf',
        stage/'R47-DFRobot_Hole_Bracket-cap.stl',checks,bracket)
    target=output/'R47-Complete-A1-mini-PETG-layout.3mf'
    compose47.compose(R42/'print-trial/R42-Complete-A1-mini-PETG-layout.3mf',
        key/'R45-Key-Carrier-layout.3mf',bracket,target,
        R42/'print-jobs/battery/R42-battery-A1-mini-PETG-layout.3mf')
    for path in key.iterdir():
        if path.is_file() and path.suffix in ('.stl','.json'):
            shutil.copyfile(path,output/path.name)
    # The inherited audit reads this key-only recipe to identify its five
    # owners. It is a reference subproject, never the complete send file.
    shutil.copyfile(key/'R45-Key-Carrier-layout.3mf',output/'R45-Key-Carrier-layout.3mf')
    path=output/'frame.json';frame=json.loads(path.read_text())
    frame['key_subproject_bed_translation']=frame['bed_translation']
    frame['bed_translation']=[18.,113.,0.]
    frame['combined_layout_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    frame['scope']='Key/helper assembly frame within the complete nine-part plate; reference layout remains key-only.'
    path.write_text(json.dumps(frame,indent=2)+'\n')
    return target


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scratch',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--key-layout',type=Path)
    a=p.parse_args();print(prepare(a.scratch.resolve(),a.output.resolve(),
                                 a.key_layout.resolve() if a.key_layout else None))
