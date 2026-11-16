"""Compose the assembly and ordered support-removal views from the selected R46 meshes."""
import argparse
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from holder46 import HERE, R45
import guide45

def build(parts):
    # Reuse the existing guide's poses and complete removal inventory.
    # Its legacy filename aliases resolve to canonical R46 files before
    # guide45 records relative URLs or calculates the visible asset hashes.
    with tempfile.TemporaryDirectory() as tmp:
        view=Path(tmp)
        for source in parts.iterdir():
            if source.suffix in ('.json','.stl'):
                (view/source.name).symlink_to(source.resolve())
                if source.name.startswith('R46-'):
                    (view/source.name.replace('R46-','R45-',1)).symlink_to(source.resolve())
        with patch.object(guide45,'HERE',HERE):target=guide45.build(view)
    data=json.loads(target.read_text())
    finger=data['modules']['finger_rest']
    finger['note']='The cyan holder has a rounded brace from the middle of each finger rest to its outer edge. Both sides also return to the deck; the left return lands farther inward to clear the soldered socket.'
    finger['steps'][0]['title']='Inspect the permanent finger rests'
    finger['steps'][0]['caption']='Follow each diagonal from the middle spine, across the next guard row, to the outside edge. The sloping returns join both rests to the solid frame.'
    for key in ('key','dfr','whole'):
        module=data['modules'][key]
        module['note']=module['note'].replace('R45','R46')
    cleanup=data['modules']['print_cleanup']
    cleanup['note']='The upright orange pieces support the carrier while it prints. Remove them after cooling. The cyan centre-to-edge braces stay on the holder.'
    cleanup['steps'][0]['caption']='The orange uprights and crossbars come off with the print cradle. The rounded cyan braces underneath the finished carrier stay in place.'
    data['sources']['generator_sha256']=guide45.sha(Path(__file__))
    data['sources']['inherited_guide_generator_sha256']=guide45.sha(R45/'guide45.py')
    data['sources']['brace_receipt_sha256']=guide45.sha(parts/'r46-braces.json')
    target.write_text(json.dumps(data,indent=2)+'\n')
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('parts',type=Path)
    build(parser.parse_args().parts.resolve())
