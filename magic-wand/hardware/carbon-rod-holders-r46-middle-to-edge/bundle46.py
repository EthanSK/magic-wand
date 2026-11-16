"""Seal the selected native paths and derive R46 guide and comparison views."""
import argparse
import json
import shutil
from pathlib import Path
from zipfile import ZipFile
from holder46 import HERE,R45,BASE
from plate45 import digest
from guide46 import build as guide
from compare46 import build as compare
import plate38

def publish(work):
    out=HERE/'exports/key-holder-only';out.mkdir(parents=True,exist_ok=True)
    final=work/'R46-Key-Carrier.gcode.3mf'
    core=json.loads((work/'candidate-audit.json').read_text())
    start=json.loads((work/'helper-starts.json').read_text())
    review=json.loads((work/'trial-review.json').read_text())
    assert core['screen_passed'] and core['archive_sha256']==digest(final)==start['archive_sha256']==review['selected_archive_sha256']
    assert review['digital_checks_passed'] and all(not v['unrooted_actual_components'] for v in start['owners'].values())
    reopen=json.loads((work/'reopen-checks.json').read_text())
    assert reopen['selected_archive_sha256']==digest(final) and reopen['own_final_deposition_audited']
    assert reopen['actual_modifier_placements_equivalent'] and reopen['object_process_settings_identical']
    bound_reports=('candidate-audit','helper-starts','roof-strokes','roof-residual-context',
                   'contact-areas','shelf-contact-areas','rear-shelf-contact-areas','delivery-checks')
    for name in bound_reports:
        report=work/(name+'.json')
        assert json.loads(report.read_text())['archive_sha256']==digest(final)
        assert digest(report)==review['report_sha256'][name]
    # Keep unique revision geometry. Unmodified R45 witness meshes remain
    # owned by their source revision and can be reproduced by plate46.
    for f in work.glob('R46-*'):
        if f.suffix in ('.stl','.3mf','.json'):shutil.copyfile(f,out/f.name)
    for name in ('Key-Carrier','Key-Carrier-assembly','release-tabs','external-cradle','front-pull-shelf','rear-pull-shelf','finger-side-comb','left-guard-web-prop'):
        src=work/('R45-'+name+'.stl')
        if src.exists():shutil.copyfile(src,out/('R46-'+name+'.stl'))
    shutil.copyfile(work/'R45-Key-Carrier-layout.3mf',out/'R46-Key-Carrier-layout.3mf')
    proofs=('frame','candidate-audit','helper-starts','roof-strokes','roof-residual-context','contact-areas',
            'shelf-contact-areas','rear-shelf-contact-areas','delivery-checks','shelf-cad','rear-shelf-cad',
            'r46-braces','trial-review','reopen-checks','cad-starts')
    for n in (*proofs,*['initial-'+n for n in proofs]):
        f=work/(n+'.json')
        if f.exists():shutil.copyfile(f,out/f.name)
    target=out/'R46-Key-Holder-Only-print-only.3mf'
    print_source=out/final.name
    plate38.recipe.make_print_only(print_source,out).replace(target)
    with ZipFile(print_source) as src,ZipFile(target) as sealed:
        assert sealed.read('Metadata/plate_1.gcode')==src.read('Metadata/plate_1.gcode')
    path=out/'print-only.json';receipt=json.loads(path.read_text());receipt.update(file=target.name,sha256=digest(target),generator_sha256=digest(Path(__file__)))
    path.write_text(json.dumps(receipt,indent=2)+'\n')
    guide(out);compare(out,HERE/'exports')
    sources={f.name:digest(f) for f in HERE.glob('*.py')}
    upstream={f.name:digest(f) for f in R45.glob('*.py')}
    archive=out/final.name
    files={f.name:digest(f) for f in out.iterdir() if f.is_file() and f.name!='evidence.json'}
    (out/'evidence.json').write_text(json.dumps(dict(selected_archive_sha256=digest(archive),print_only_sha256=digest(target),
        inherited_work_mesh_aliases={f.name.replace('R46-','R45-',1):f.name for f in out.glob('R46-*.stl') if (work/f.name.replace('R46-','R45-',1)).is_file()},source_sha256=sources,inherited_r45_source_sha256=upstream,files_sha256=files,
        guide_sha256=digest(HERE/'exports/assembly-guide.json'),physical_acceptance_verified=False),indent=2)+'\n')
    return target

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('work',type=Path)
    print(publish(parser.parse_args().work.resolve()))
