#!/usr/bin/env python3
"""Check V2 model topology, analytic clearances and source/export freshness.
Run after ring_cad.py. These checks deliberately do not claim physical fit.
"""
from __future__ import annotations
import hashlib
import json
import zipfile
from xml.etree import ElementTree as ET
from itertools import combinations, product
from pathlib import Path
import numpy as np
import trimesh
from ring_cad import CONFIG, HERE, OUT, build, finger_bore, mesh


def main() -> None:
    manifest=json.loads((OUT/'manifest.json').read_text())
    expected=hashlib.sha256((HERE/'dimensions.json').read_bytes()+(HERE/'ring_cad.py').read_bytes()).hexdigest()
    assert manifest['source_sha256']==expected, 'Regenerate exports after source changes'
    checks=[]
    for family,count in product(('Ring','Handheld'),(3,4)):
        prefix='Handheld_' if family=='Handheld' else ''
        left,right=build('Left',count,family),build('Right',count,family)
        for a,b in zip(left,right,strict=True):
            assert abs(a.solid.volume()-b.solid.volume())<1e-5
            assert (a.solid.mirror((1,0,0))-b.solid).volume()<1e-5
        for hand,parts in [('Left',left),('Right',right)]:
            components={p.name:len(p.solid.decompose()) for p in parts}
            assert all(n==1 for n in components.values()), components
            collisions=[]
            for a,b in combinations(parts,2):
                intersection=(a.solid ^ b.solid).volume()
                if intersection>1e-5: collisions.append([a.name,b.name,intersection])
            assert not collisions, collisions
            if family=='Ring':assert (parts[0].solid ^ finger_bore()).volume()<1e-5
            name=prefix+f'{hand}_{count}Button'
            for part in parts:
                imported=trimesh.load_mesh(OUT/name/(part.name+'.stl'))
                assert imported.is_watertight and imported.volume>0
                assert np.allclose(imported.bounds,mesh(part.solid).bounds,atol=1e-4)
            glb=trimesh.load(OUT/(name+'.glb'),force='scene')
            expected_scene=trimesh.Scene()
            for part in parts:
                m=mesh(part.solid);m.apply_scale(.001)
                m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,(1,0,0)))
                expected_scene.add_geometry(m)
            assert np.allclose(glb.bounds,expected_scene.bounds,atol=1e-7), 'glTF scale or axes changed'
            with zipfile.ZipFile(OUT/(name+'_CONCEPT.3mf')) as archive:
                root=ET.fromstring(archive.read('3D/3dmodel.model'))
                ns={'c':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
                assert root.attrib['unit']=='millimeter'
                objects=root.findall('c:resources/c:object',ns)
                assembly=objects[-1]
                assert len(assembly.findall('c:components/c:component',ns))==len(parts)
                assert root.find('c:build/c:item',ns).attrib['objectid']==assembly.attrib['id']
                for part,obj in zip(parts,objects[:-1],strict=True):
                    imported=np.array([[float(v.attrib[k]) for k in ('x','y','z')] for v in obj.findall('c:mesh/c:vertices/c:vertex',ns)])
                    assert np.allclose(imported,mesh(part.solid).vertices,atol=1e-5)
            plastic_volume=sum(p.solid.volume() for p in parts if p.role in ('concept shell','button position mock-up'))
            entry={'variant':name,'family':family,'concept_plastic_volume_mm3':plastic_volume,'illustrative_plastic_mass_g_at_1_24_to_1_27_g_cm3':[plastic_volume*.00124,plastic_volume*.00127],'single_connected_solids':True,'roundtrip_stl_watertight':True,'glb_metres_and_y_up_verified':True,'3mf_mm_and_assembly_verified':True,'component_envelopes_disjoint':True,'finger_reference_clear':True if family=='Ring' else 'not applicable','exact_anatomical_mirror':True,'part_count':len(parts),'assembly_bounds_mm':trimesh.util.concatenate([mesh(p.solid) for p in parts]).bounds.tolist()}
            checks.append(entry)
    report={'status':'Passed geometry checks only','source_sha256':expected,'checks':checks,'mass_note':'Illustrative solid plastic volume only using assumed 1.24–1.27 g/cm3 density. Electronics, wiring, retention, slicer changes and actual mass unmeasured.', 'checked_fit':'Nominal rectangular envelopes only. Board XY matches manufacturer specification. All other component dimensions, physical fit and printability remain unverified.','unverified':CONFIG['unverified']}
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
