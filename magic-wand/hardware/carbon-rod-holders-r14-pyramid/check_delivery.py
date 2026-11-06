#!/usr/bin/env python3
"""Check the complete R14 source/project/image/default-control receipt chain."""
import json
from html.parser import HTMLParser
from pathlib import Path
import cad
import deliverables
import qualify

OUT=cad.HERE/'exports'
def read(path):return json.loads(path.read_text())

class SelectedOrientation(HTMLParser):
    def __init__(self):super().__init__();self.inside=False;self.selected=[]
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if tag=='select':self.inside=a.get('id')=='revision'
        if self.inside and tag=='option' and 'selected'in a:self.selected.append(a['value'])
    def handle_endtag(self,tag):
        if tag=='select':self.inside=False

def check():
    geometry=read(OUT/'geometry-checks.json')
    assert geometry['passed'] and geometry['checker_sha256']==cad.sha(cad.HERE/'verify_geometry.py')
    assert geometry['manifest_sha256']==cad.sha(OUT/'manifest.json')
    receipts={}
    for out in [OUT,OUT/'trial-Key_Carrier']:
        qualify.qualify(out)
        project=out/deliverables.project_name(out);digest=cad.sha(project)
        audit=read(out/'slice-clearances.json');views=read(out/'view-checks.json')
        assert views['project_sha256']==digest and views['slice_audit_sha256']==cad.sha(out/'slice-clearances.json')
        assert views['generator_sha256']==cad.sha(cad.HERE/'review_views.py')
        for filename,sha in {**views['images_sha256'],**audit['slice_images_sha256']}.items():assert cad.sha(out/filename)==sha,filename
        reopen=read(out/'reopen-checks.json')
        assert reopen['input_project_sha256']==digest and reopen['effective_settings_equal'] and reopen['actual_paths_passed']
        assert reopen['generator_sha256']==cad.sha(cad.HERE/'reopen_project.py')
        assert reopen['actual_paths_report_sha256']==cad.sha(out/'reopened-clearances.json')
        reopened=read(out/'reopened-clearances.json')
        assert reopened['passed']
        for key in ['checker_sha256','parser_sha256','start_auditor_sha256','side_gap_checker_sha256','working_spaces_sha256']:
            assert reopened[key]==audit[key],key
        receipts[out.relative_to(cad.HERE).as_posix()]={'project_sha256':digest,'view_receipt_sha256':cad.sha(out/'view-checks.json'),
                                                     'reopen_receipt_sha256':cad.sha(out/'reopen-checks.json')}
    overview=read(OUT/'overview-checks.json')
    assert overview['manifest_sha256']==cad.sha(OUT/'manifest.json')
    assert overview['project_sha256']==cad.sha(OUT/deliverables.project_name(OUT))
    assert overview['generator_sha256']==cad.sha(cad.HERE/'audit_views.py')
    for filename,digest in {**overview['source_meshes_sha256'],**overview['images_sha256']}.items():
        assert digest==cad.sha(OUT/filename),filename
    layout=read(OUT/'layout-comparison.json')
    assert layout['generator_sha256']==cad.sha(cad.HERE/'layout_views.py') and layout['image_sha256']==cad.sha(OUT/'layout-comparison.png')
    assert layout['r14_manifest_sha256']==cad.sha(OUT/'manifest.json')
    previous=cad.HERE.parent/'carbon-rod-holders-r13-printability/exports'
    assert layout['r13_manifest_sha256']==cad.sha(previous/'manifest.json')
    differences=read(OUT/'design-differences.json')
    assert differences['manifest_sha256']==cad.sha(OUT/'manifest.json')
    assert differences['generator_sha256']==cad.sha(cad.HERE/'compare_revision.py')
    for name,record in differences['parts'].items():
        assert record['r14_sha256']==cad.sha(OUT/(name+'-assembly.stl'))
        assert record['r13_sha256']==cad.sha(previous/(name+'-assembly.stl'))
        if name!='Key_Carrier':assert record['r14_sha256']==record['r13_sha256']
    scene=read(OUT/'review-scene.json')
    assert scene['sources']['manifest_sha256']==cad.sha(OUT/'manifest.json')
    assert scene['sources']['cad_sha256']==cad.sha(cad.HERE/'cad.py')
    assert scene['sources']['generator_sha256']==cad.sha(cad.HERE/'build_preview.py')
    assert scene['sources']['renderer_sha256']==cad.sha(cad.HERE/'preview/preview.mjs')
    assert scene['sources']['html_sha256']==cad.sha(cad.HERE/'preview/index.html')
    assert scene['sources']['geometry_encoder_sha256']==cad.sha(cad.base.HERE/'build_preview.py')
    page=SelectedOrientation();page.feed((cad.HERE/'preview/index.html').read_text())
    assert page.selected==[scene['parameters']['assembly']['default_key_orientation']]==['two-toward-tip']
    assert scene['key_positions']==[list(p)for p in cad.key_positions()]
    pointer=read(cad.HERE.parent/'carbon-rod-holders/preview/current.json')
    assert pointer=={'revision':cad.P['revision'],'scene_sha256':cad.sha(OUT/'review-scene.json')}
    result={'checker_sha256':cad.sha(Path(__file__)),'projects':receipts,'geometry_sha256':cad.sha(OUT/'geometry-checks.json'),
            'overview_sha256':cad.sha(OUT/'overview-checks.json'),'scene_sha256':pointer['scene_sha256'],
            'default_orientation':page.selected[0],'passed':True,'physical_acceptance_verified':False}
    (OUT/'delivery-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Consistent source, project, image, reopen and initial viewer-control receipts passed.')

if __name__=='__main__':check()
