"""Reuse the R61 animation and bought parts with the current printed carrier in every view."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from design62 import OUT, HERE, r61


def write_guide(register=False):
    original = r61.OUT/'assembly-guide.json'
    guide = json.loads(original.read_text())
    hashes = {}
    for module in guide['modules'].values():
        for actor in module['actors'].values():
            for field in ('file','morphFile'):
                if field not in actor:
                    continue
                name = actor[field]
                mesh = (OUT if name=='Key_Carrier-assembly.stl' else r61.OUT)/name
                relative = os.path.relpath(mesh.resolve(strict=True),OUT)
                actor[field] = relative
                if relative not in hashes:
                    hashes[relative] = sha256(mesh.read_bytes()).hexdigest()
    guide['modules']['finger_rest']['note'] = 'The rounded bottom supports run farther along the holder, giving your finger a gentler approach. Insert the sockets and backing strips from the outside.'
    guide.update(revision='R62',sources=dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                 upstream_guide_sha256=sha256(original.read_bytes()).hexdigest(),meshes_sha256=hashes))
    out = OUT/'assembly-guide.json'
    out.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    if register:
        sys.path.insert(0,str(HERE.parent/'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(out,'r62','R62 trial · Gentle bottom guards and compact hinge',group_keys=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--register',action='store_true')
    write_guide(parser.parse_args().register)
