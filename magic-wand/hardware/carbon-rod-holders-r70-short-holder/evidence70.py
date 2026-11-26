"""Rebuild every R70 mesh from source and compare it with the export, byte for byte.

`--slice` adds R69's deposited-bead evidence (the published plug motion and the three
socket bores) on a native slice. Reports retain the archive and guide hashes.
 — Claude Fable 5.2"""
from hashlib import sha256
import argparse
import json
from pathlib import Path
import tempfile

import design70 as d
import hinge70

MESHES = (d.HOLDER, hinge70.PADDLE, hinge70.POST_BAR, hinge70.WIRES, hinge70.LID)


def source():
    rows = {}
    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        d.export(scratch / d.HOLDER)
        hinge70.save_parts(scratch)
        for name in MESHES:
            rows[name] = dict(export_sha256=digest(d.OUT / name), reproduced_sha256=digest(scratch / name))
    report = dict(revision='R70', generator_sha256={Path(m.__file__).name: digest(m.__file__) for m in (d, hinge70)}, meshes=rows,
                  inputs_sha256=dict(r69_carrier=d.R69_SHA256, r69_retainer=hinge70.R69_LID_SHA256),
                  carrier_sha256=rows[d.HOLDER]['export_sha256'], reproduced_sha256=rows[d.HOLDER]['reproduced_sha256'])
    report['passes'] = all(r['export_sha256'] == r['reproduced_sha256'] for r in rows.values())
    assert report['passes'], report
    return report


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def slice_evidence(folder):
    """R69's supplemental evidence on an R70 slice. — Claude Fable 5.2"""
    import audit70
    import evidence69
    audit70.bind()
    evidence69.d, evidence69.audit = d, audit70.a69
    return evidence69.slice_evidence(Path(folder))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slice', type=Path, action='append', default=[], help='a native slice directory')
    parser.add_argument('--slice-only', action='store_true')
    args = parser.parse_args()
    if not args.slice_only:
        result = source()
        (d.OUT / 'source-reproduction.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=1), flush=True)
    for folder in args.slice:
        print(json.dumps(slice_evidence(folder)), flush=True)
