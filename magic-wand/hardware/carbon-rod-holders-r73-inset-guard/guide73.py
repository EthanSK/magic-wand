"""Register the corrected carrier with the exact R72 battery placement and assembly motions."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

import design73 as model


def write(register=False):
    previous=model.prior.OUT/'assembly-guide.json'
    guide=json.loads(previous.read_text())
    guide['revision']='R73'
    hashes={}
    for module in guide['modules'].values():
        if 'status' in module:
            module['status']='R73 design · physical fit untested'
        for actor in module['actors'].values():
            for field in ('file','morphFile'):
                if field not in actor:
                    continue
                mesh=(previous.parent/actor[field]).resolve(strict=True)
                # Only this integral branch has changed. The battery still sits
                # next to the rod, and every bought part follows its fitted route.
                if mesh==model.prior.OUT/model.HOLDER:
                    mesh=model.OUT/model.HOLDER
                name=relpath(mesh,model.OUT)
                actor[field]=name
                if name not in hashes:
                    hashes[name]=sha256(mesh.read_bytes()).hexdigest()
    guide['r73_changes']={'lower_guard':'All four tips turn inward into the rounded body'}
    guide['optional_components']['note']=guide['optional_components']['note'].replace('R72 plate','R73 plate')
    guide['sources']=dict(generator_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        upstream_guide_sha256=sha256(previous.read_bytes()).hexdigest(), meshes_sha256=hashes)
    if model.HOLDER not in hashes:
        raise ValueError('Missing revised carrier in guide')
    out=model.OUT/'assembly-guide.json'
    out.write_text(json.dumps(guide,separators=(',',':'),allow_nan=False)+'\n')
    if register:
        sys.path.insert(0,str(model.HERE.parent/'carbon-rod-holders/assembly'))
        from register_assembly import register_assembly
        register_assembly(out,'r73','R73 · Finger guard turns into the rounded edge',group_keys=True,make_current=True)
    return out


if __name__=='__main__':
    print(write('--current' in sys.argv))
