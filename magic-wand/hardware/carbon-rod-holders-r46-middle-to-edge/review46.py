"""Check an R46 native slice, then independently reopen and check the final native archive."""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
import holder46  # Locate the inherited R45 modules beside this revision.
from plate45 import digest
import audit46
import helper_starts45
import roof_strokes45
import roof_context46
import contact45
import delivery45
import slice45
from owner45 import layout_owners

def inspect(archive,*,reuse_initial_roofs=False):
    parents=archive.parent
    audit46.check(archive)
    if reuse_initial_roofs:
        for name in ('helper-starts.json','roof-strokes.json'):
            assert json.loads((parents/name).read_text())['archive_sha256']==digest(archive)
    else:
        helper_starts45.inspect(archive)
        roof_strokes45.inspect(archive)
    roof_context46.inspect(archive)
    for owner in sorted(layout_owners(parents)-{'Key_Carrier','Release_tabs'}):contact45.inspect(archive,owner)
    delivery=delivery45.inspect(archive)
    core=json.loads((parents/'candidate-audit.json').read_text())
    helpers=json.loads((parents/'helper-starts.json').read_text())
    assert core['screen_passed'], 'See the complete structural, route and withdrawal report'
    assert all(not v['unrooted_actual_components'] for v in helpers['owners'].values())
    return delivery

def reopen(directory):
    initial=directory/'R46-first-slice.gcode.3mf'
    inspect(initial,reuse_initial_roofs=True)
    reports=('candidate-audit.json','helper-starts.json','roof-strokes.json','roof-residual-context.json','contact-areas.json',
             'shelf-contact-areas.json','rear-shelf-contact-areas.json','delivery-checks.json')
    for name in reports:shutil.copyfile(directory/name,directory/('initial-'+name))
    final=directory/'R46-Key-Carrier.gcode.3mf'
    # slice45 uses an isolated profile and native output directory for each run.
    original_scratch=os.environ['AGENT_SCRATCH_DIR']
    with tempfile.TemporaryDirectory(dir=original_scratch) as tmp:
        os.environ['AGENT_SCRATCH_DIR']=tmp
        try:slice45.run(initial,final)
        finally:os.environ['AGENT_SCRATCH_DIR']=original_scratch
    inspect(final)
    from reopen_compare46 import check
    check(directory)
    return final

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);reopen(p.parse_args().directory)
