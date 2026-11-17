"""Audit the complete plate's carrier and disposable helpers once, from native paths."""
import argparse
import json
from pathlib import Path
import holder47
import audit47
import review47
from scope47 import key_group
from plate45 import digest


def run(archive,scratch,resume_material=False):
    with key_group(archive):
        audit47.check(archive,scratch,resume_material)
        review47.review(archive)
    p=archive.parent
    core=json.loads((p/'candidate-audit.json').read_text())
    helpers=json.loads((p/'helper-starts.json').read_text())
    assert core['screen_passed'], 'Native route/material/removal gate failed'
    assert not json.loads((p/'cad-starts.json').read_text()), 'Unresolved CAD start'
    assert all(not row['unrooted_actual_components'] for row in helpers['owners'].values())
    assert core['archive_sha256']==helpers['archive_sha256']==digest(archive)
    core['scope']='Complete native archive, key/helper owners and actual tower. Neighbours and eight other pieces are covered by audit_parts47.'
    (p/'candidate-audit.json').write_text(json.dumps(core,indent=2)+'\n')
    print('COMPLETE-PLATE KEY PATH GATES PASSED; independent roof/trial review pending',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('scratch',type=Path)
    p.add_argument('--resume-material',action='store_true')
    a=p.parse_args();run(a.archive.resolve(),a.scratch.resolve(),a.resume_material)
