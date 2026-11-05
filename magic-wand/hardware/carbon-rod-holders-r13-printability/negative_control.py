#!/usr/bin/env python3
"""Require the preserved R12 delivery to fail the current all-bead audit.

Adapt source references and normal-mesh names in memory only. Never rewrite
the old delivery, its manifests or reports. A failure before a fresh report
exists is an error in this control, not evidence of blocked openings.
"""
import json,tempfile
from pathlib import Path
import cad,deliverables,verify_slice,working_spaces

def run():
    old=cad.base;project=old.HERE/'exports/Holder-modular-sliced.3mf'
    saved=(verify_slice.cad,working_spaces.cad,deliverables.normal_name)
    verify_slice.cad=old;working_spaces.cad=old
    deliverables.normal_name=lambda name:name+'.stl'
    working_spaces.regions.cache_clear();working_spaces.maximum_socket.cache_clear()
    try:
        with tempfile.TemporaryDirectory(prefix='r13-negative-control-')as folder:
            path=Path(folder)/'report.json'
            try:verify_slice.inspect('modular',project,old.HERE/'exports',path)
            except AssertionError:
                assert path.exists(),'Audit failed before producing negative-control evidence'
            report=json.loads(path.read_text())
    finally:
        verify_slice.cad,working_spaces.cad,deliverables.normal_name=saved
        working_spaces.regions.cache_clear();working_spaces.maximum_socket.cache_clear()
    assert report['project_sha256']==cad.sha(project) and not report['passed']
    blocked=sum(bool(row['violations'])for part in report['parts'].values()for row in part['checks'].values())
    count=sum(len(part['checks'])for part in report['parts'].values())
    assert blocked and any(kind.startswith('Support')for part in report['parts'].values()
        for row in part['checks'].values()for kind in row['violations'])
    report['negative_control']={'generator_sha256':cad.sha(Path(__file__)),
        'preserved_project_sha256':cad.sha(project),'blocked_regions':blocked,'checked_regions':count,
        'adaptation':'Current working regions with R12 positions/interfaces and original normal meshes. This rejects the old delivery; it does not requalify R12.'}
    (cad.HERE/'exports/r12-negative-control.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Expected rejection verified: {blocked}/{count} R12 regions contain extrusions.')

if __name__=='__main__':run()
