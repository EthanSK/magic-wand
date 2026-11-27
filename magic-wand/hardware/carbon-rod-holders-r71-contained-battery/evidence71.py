"""Rebuild every R71 mesh from source and compare it with the export, byte for byte.

The rebuild goes to a scratch folder (AGENT_SCRATCH_DIR when set) that is removed again.
The report keeps the generator and input hashes. Nothing here is a slice.
 — Claude Fable 5.2"""
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import tempfile

import design71 as d
import hinge71

MESHES = (d.HOLDER, hinge71.PADDLE, *hinge71.CLIPS.values(), hinge71.POST_BAR, hinge71.WIRES, hinge71.LID)


def source():
    rows = {}
    with tempfile.TemporaryDirectory(dir=os.environ.get('AGENT_SCRATCH_DIR')) as scratch:
        scratch = Path(scratch)
        d.export(scratch / d.HOLDER)
        hinge71.save_parts(scratch)
        for name in MESHES:
            rows[name] = dict(export_sha256=digest(d.OUT / name), reproduced_sha256=digest(scratch / name))
    r70, h70 = d.r70, hinge71.h70
    report = dict(revision='R71', generator_sha256={Path(m.__file__).name: digest(m.__file__) for m in (d, hinge71, r70, h70)}, meshes=rows,
                  inputs_sha256=dict(r70_carrier=digest(r70.OUT / d.HOLDER), r70_paddle=digest(r70.OUT / hinge71.PADDLE), r70_post_bar=digest(r70.OUT / hinge71.POST_BAR), r69_retainer=h70.R69_LID_SHA256,
                                     r59_clips={side: digest(path) for side, path in hinge71.R59_CLIPS.items()}),
                  copied_from_r70={name: digest(d.OUT / name) == digest(r70.OUT / name) for name in (hinge71.WIRES, hinge71.LID)},
                  carrier_sha256=rows[d.HOLDER]['export_sha256'], reproduced_sha256=rows[d.HOLDER]['reproduced_sha256'])
    report['passes'] = all(r['export_sha256'] == r['reproduced_sha256'] for r in rows.values()) and all(report['copied_from_r70'].values())
    assert report['passes'], report
    return report


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def slice_evidence(folder):
    """Reuse the established native plug/three-bore checks with R71's guide.

    The R69 method already scans every bead type and includes an occupied-deck
    positive control. Its inputs and outputs are rebound, not its geometry.
    — GPT-6.1 Sol
    """
    import audit71
    import evidence69
    audit71.bind()
    evidence69.d, evidence69.audit = d, audit71.a69
    report = evidence69.slice_evidence(Path(folder))
    report['adapter_sha256'] = digest(__file__)
    (Path(folder) / 'supplemental-evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slice-only', action='store_true')
    parser.add_argument('--slice', type=Path, action='append', default=[])
    args = parser.parse_args()
    if not args.slice_only:
        result = source()
        (d.OUT / 'source-reproduction.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=1), flush=True)
    for folder in args.slice:
        print(json.dumps(slice_evidence(folder)), flush=True)
