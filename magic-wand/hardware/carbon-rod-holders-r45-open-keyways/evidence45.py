"""Assemble the file inventory for review (no readiness or physical claims)."""
import argparse,json,sys
from pathlib import Path
from hashlib import sha256
def digest(f):return sha256(f.read_bytes()).hexdigest()
def inventory(out,archive=None):
    here=Path(__file__).resolve().parent
    files={f.name:digest(f) for f in sorted(out.iterdir()) if f.is_file() and f.name!='evidence.json'}
    sources={f.name:digest(f) for f in sorted(here.glob('*.py'))}
    r=json.loads((out/'candidate-audit.json').read_text())
    archive=archive or out/'R45-candidate.gcode.3mf'
    assert r['archive_sha256']==files[archive.name]
    shape=json.loads((out/'frame.json').read_text())
    assert shape['layout_sha256']==files['R45-Key-Carrier-layout.3mf']
    # roof-strokes45 covers every native carrier layer and stroke. The old
    # flat-Z saddle and earlier-only bridge probes remain diagnostics; they
    # are not duplicate gates or evidence for a different print frame.
    required=('contact-areas.json','helper-starts.json','roof-strokes.json','delivery-checks.json')
    if 'Front_pull_shelf' in r['owners']:required+=('shelf-contact-areas.json',)
    if 'Rear_pull_shelf' in r['owners']:required+=('rear-shelf-contact-areas.json',)
    missing=[f for f in required if not (out/f).is_file()]
    for f in required:
        if f not in missing:assert json.loads((out/f).read_text())['archive_sha256']==r['archive_sha256']
    guide_path=here/'exports/assembly-guide.json'
    matching_guide=None
    if guide_path.is_file():
        guide=json.loads(guide_path.read_text())
        if guide.get('sources',{}).get('selected_native_archive_sha256')==r['archive_sha256']:
            matching_guide={'file':'../assembly-guide.json','sha256':digest(guide_path)}
    root=here.parents[2]
    upstream={}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if not name:continue
        path=Path(name).resolve()
        if path.suffix=='.py' and path.is_relative_to(root) and not path.is_relative_to(here):
            upstream[path.relative_to(root).as_posix()]=digest(path)
    (out/'evidence.json').write_text(json.dumps({
        'revision':'R45','designation':'test-first native project; not physical acceptance or a print authorisation',
        'selected_file':archive.name,
        'functional_components':['Key_Carrier'],'disposable_components':[n for n in ('External_cradle','Front_pull_shelf','Rear_pull_shelf','Release_tabs') if n in r['owners']],
        'print_to_assembly':shape['print_to_assembly'],'core_screen_passed':r['screen_passed'],
        'complete_evidence_set':not missing,'missing_reports':missing,
        'matching_assembly_guide':matching_guide,
        'physical_fit_strength_and_support_release_verified':False,
        'sources_sha256':sources,'upstream_sources_sha256':upstream,'candidate_files_sha256':files},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--archive',type=Path);a=p.parse_args();inventory(a.directory,a.archive)
