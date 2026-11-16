"""Audit all actual R45 extrusion and the ordered withdrawal of its helpers."""
import argparse,json
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import trimesh
from holder45 import inherited as prior, R44
from plate45 import digest
import single44
common=prior.common
def supplemental_coverage(checker,target,xyz,widths,heights,tops):
    """Measure every new-member slab's material volume, including tiny bonds."""
    x,y,z,X,Y,Z=target.bounding_box()
    near=(xyz[:,0]>=x-.7)&(xyz[:,0]<=X+.7)&(xyz[:,1]>=y-.7)&(xyz[:,1]<=Y+.7)
    rows=[]
    for layer in np.unique(tops):
        if layer<z-.0001 or layer-.25>Z:continue
        all_layer=abs(tops-layer)<.001;h=float(heights[all_layer][0]);lo=float(layer)-h
        slab=target.trim_by_plane((0,0,1),lo).trim_by_plane((0,0,-1),-float(layer))
        volume=slab.volume()
        if volume<1e-7:continue
        m=near&all_layer
        beads=checker.start_audit.bead_footprints(checker.q,xyz[m,:2],widths[m])
        covered=(slab^beads.extrude(h).translate((0,0,lo))).volume()
        rows.append(dict(top_mm=round(float(layer),3),target_mm3=volume,covered_mm3=covered,fraction=max(0.,min(1.,covered/volume))))
    assert rows,('new witness has no measurable native slab',target.bounding_box())
    return dict(layers=len(rows),coverage_fraction=sum(v['covered_mm3'] for v in rows)/sum(v['target_mm3'] for v in rows),
                minimum_layer_fraction=min(v['fraction'] for v in rows),layer_volumes=rows)

def check(archive):
    out=archive.parent; info=json.loads((out/'frame.json').read_text())
    frame=np.array(info['print_to_assembly']); owner=single44.previous.owners(archive)
    has_rear='Rear_pull_shelf' in owner
    from owner45 import layout_owners
    assert set(owner)==layout_owners(out)
    has_front='Front_pull_shelf' in owner
    engine=common.load_checker();checker=engine.audit;q=checker.q
    data,features,stats,config,offset,objects,g,_=checker.read_project(archive)
    features=list(features)
    assert set(objects)==set(owner)
    xyz=data[:,:3]+offset-info['bed_translation']; kinds=data[:,5].astype(int);labels=np.asarray(features)[kinds]
    carrier=(data[:,6]==owner['Key_Carrier'])&common.model_mask(labels)
    cradle_beads=(data[:,6]==owner['External_cradle'])&common.model_mask(labels)
    shelf_beads=(data[:,6]==owner.get('Front_pull_shelf',-999))&common.model_mask(labels)
    rear_beads=(data[:,6]==owner.get('Rear_pull_shelf',-999))&common.model_mask(labels)
    helper=cradle_beads|shelf_beads|rear_beads
    tabs=data[:,6]==owner['Release_tabs']
    brim=np.char.startswith(labels,'Brim')
    tower=labels=='Prime tower';assert (carrier|helper|tabs|brim|tower).all()
    assert tower.any() and carrier.any() and helper.any()
    result={'archive_sha256':digest(archive),'checker_sha256':digest(Path(__file__)),'owners':owner,'physical_success_verified':False}
    def save(): (out/'candidate-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    mesh=trimesh.load_mesh(out/'R45-Key-Carrier-assembly.stl');mesh.apply_transform(np.linalg.inv(frame))
    old_mesh=trimesh.load_mesh(R44/'exports/Key_Carrier-assembly.stl');old_mesh.apply_transform(np.linalg.inv(frame))
    old_body=q.solid(old_mesh.vertices,old_mesh.faces)
    solid=q.solid(mesh.vertices,mesh.faces)
    native={n:q.solid(o['vertices']-info['bed_translation'],o['faces']) for n,o in objects.items()}
    native_body=native['Key_Carrier']
    # Native 3MF's re-centred meshes and its build/component transforms
    # must reproduce the intended functional geometry in this bed frame.
    difference=(native_body-solid).volume()+(solid-native_body).volume()
    # The STL stores float32 vertices and Studio recentres/re-exports the mesh.
    # Independently bound corresponding surface vertices in both directions.
    from itertools import product
    av=mesh.vertices;bv=objects['Key_Carrier']['vertices']-info['bed_translation']
    # A match in the same or a neighbouring 0.2-micron grid cell
    # bounds 3-D displacement by 0.0004*sqrt(3) mm.
    def cells(a):return set(map(tuple,np.floor(a/.0002).astype(int).tolist()))
    ac,bc=cells(av),cells(bv)
    def misses(a,b):
        offsets=list(product((-1,0,1),repeat=3))
        return sum(not any((x+i,y+j,z+k) in b for i,j,k in offsets) for x,y,z in a-b)
    lost=misses(ac,bc)+misses(bc,ac)
    result['native_vertex_bound_mm']=.0004*3**.5
    assert lost==0 and difference<.2,('carrier assembly/print transform drift',lost,difference)
    result['native_carrier_symmetric_difference_mm3']=difference
    for name,file in [('External_cradle','R45-external-cradle.stl'),
                      ('Front_pull_shelf','R45-front-pull-shelf.stl'),('Release_tabs','R45-release-tabs.stl')]+([('Rear_pull_shelf','R45-rear-pull-shelf.stl')] if has_rear else []):
        if name not in owner:continue
        exported=trimesh.load_mesh(out/file)
        a,b=cells(exported.vertices),cells(objects[name]['vertices']-info['bed_translation'])
        assert misses(a,b)+misses(b,a)==0,('native/helper export drift',name)
    solid=native_body
    first=np.abs(data[:,7]-.2)<.001
    result['first_layer_area_mm2']={}
    for name,mask in [('carrier',carrier),('external_cradle',cradle_beads),('front_pull_shelf',shelf_beads),('rear_pull_shelf',rear_beads),('release_tabs',tabs),('brim',brim)]:
        m=first&mask; result['first_layer_area_mm2'][name]=checker.start_audit.bead_footprints(q,xyz[m,:2],data[m,3]).area()
    # Certify downward withdrawal of the entire cradle (and any individual
    # peel strip) for **all translations**, not just a grid of sampled poses.
    # Project the COMPLETE volume of each slab, including any angled clipping
    # introduced by the side shelf. A midpoint section would miss material
    # between planes. Compare with all remaining plastic below the upper
    # face; that conservative shadow contains every downward collision.
    cradle=native['External_cradle']
    release_obstacles=solid+native['Release_tabs']
    if has_front:release_obstacles+=native['Front_pull_shelf']
    if has_rear:release_obstacles+=native['Rear_pull_shelf']
    zverts=np.asarray(cradle.to_mesh().vert_properties)[:,2]
    interference=[];queries=0;smallest_slab=.2
    queue=[(round(k*.2,6),round((k+1)*.2,6))
           for k in range(int(np.ceil(float(zverts.max())/.2)))]
    # Coarse slabs combine geometry at different heights and can falsely
    # overlap. Bisect only unresolved slabs: every accepted slab still covers
    # its COMPLETE volume. No midpoint section or sampled withdrawal poses.
    while queue:
        lo,hi=queue.pop();queries+=1;smallest_slab=min(smallest_slab,hi-lo)
        section=cradle.trim_by_plane((0,0,1),lo).trim_by_plane((0,0,-1),-hi).project()
        if section.is_empty():continue
        below=release_obstacles.trim_by_plane((0,0,-1),-hi).project()
        area=(section^below).area()
        if area<=.0001:continue
        if hi-lo>.0015:
            mid=(lo+hi)/2;queue.extend([(lo,mid),(mid,hi)])
        else:interference.append({'helper_slab_mm':[lo,hi],'overlap_mm2':area})
    result['whole_rib_downward_release']={'colliding_helper_slices':interference,'mechanical_release_geometry_clear':not interference,
        'full_volume_queries':queries,'smallest_slab_mm':smallest_slab,'overlap_area_tolerance_mm2':.0001,
        'scope':'Straight -Z after lifting from the bed; complete helper slabs against the continuous projection of all carrier below. Physical adhesion, grip and peel force untested.'}
    # Relabel only actual helper-owned samples as support for the strict
    # separate-owner layer audit: no same-layer or adjacent-height credit.
    support_kind=len(features); tagged=kinds.copy();tagged[helper]=support_kind
    near=~tower & ~tabs
    result['layer_starts']=checker.start_audit.inspect(q,solid,xyz[near],data[near,4],tagged[near],
        features+['Support: removable print helpers'],data[near,7],frame,data[near,3],gap=.2)
    # Diagnose a missed start without counting a larger gap as adequate.
    for row in result['layer_starts']['floating_components']:
        top=row['layer_top_mm']; bounds=np.array(row['print_xy_bounds_mm'])
        component=next(c for c in solid.slice(top-.1).decompose() if np.max(np.abs(np.array(c.bounds())-bounds))<.015)
        row['underlying_helper_bead_samples_by_top']={}
        for z in np.arange(.2,top-.09,.2):
            m=helper & (abs(data[:,7]-z)<.001)
            count=int(q._inside(component,xyz[m,:2]).sum())
            if count:row['underlying_helper_bead_samples_by_top'][f'{z:.1f}']=count
    print('floating',[(s['layer_top_mm'],s['assembly_centre_mm']) for s in result['layer_starts']['floating_components']],flush=True);save()
    gaps,material=prior.routes();routes={**gaps[prior.d.CARRIER],**prior.full.precision_support_spaces()}
    from route_audit45 import inspect as inspect_route
    from release45 import whole_bead_release
    result['whole_bead_release']=whole_bead_release(checker,data,xyz,carrier|tabs|shelf_beads|rear_beads,cradle_beads)
    print('actual whole-cradle release',result['whole_bead_release']['clear'],flush=True);save()
    result['removal_order']=['External_cradle: -printZ; carrier and tabs remain','Release_tabs: peel after cooling']
    if has_front:
        shelf_cad=json.loads((out/'shelf-cad.json').read_text())
        assert shelf_cad['owner']=='Front_pull_shelf' and shelf_cad['direction_print']==[0,-1,0]
        assert not shelf_cad['whole_cad_conflicts']
        generator=shelf_cad.get('generator_file','shelf45.py')
        assert generator in ('shelf45.py','standing_comb45.py')
        assert shelf_cad['generator_sha256']==digest(Path(__file__).with_name(generator))
        if generator=='standing_comb45.py':
            assert shelf_cad['generator_dependencies_sha256']=={'shelf45.py':digest(Path(__file__).with_name('shelf45.py'))}
        for file,sha in shelf_cad['stl_sha256'].items():
            assert digest(out/file)==sha,('shelf CAD proof no longer matches export',file)
        from lateral45 import inspect as lateral_release
        result['whole_shelf_cad_release']=shelf_cad
        result['whole_shelf_bead_release']=lateral_release(checker,data,xyz,carrier|tabs|rear_beads,shelf_beads,'-y')
        if shelf_cad.get('removable_pieces'):
            from comb_pieces45 import actual as check_front_pieces
            result['individual_front_piece_release']=check_front_pieces(out,checker,data,xyz,shelf_beads,carrier|tabs|rear_beads,shelf_cad)
        result['removal_order']=['External_cradle: -printZ; shelf and tabs remain',
            'Front_pull_shelf: -printY; carrier and tabs remain','Release_tabs: peel after cooling']
        print('actual whole-shelf release',result['whole_shelf_bead_release']['clear'],flush=True);save()
    if has_rear:
        rear_report=json.loads((out/'rear-shelf-cad.json').read_text())
        assert rear_report['owner']=='Rear_pull_shelf' and rear_report['direction_print']==[0,1,0]
        generator=rear_report.get('generator_file','shelf45.py')
        assert generator in ('shelf45.py','standing_aperture45.py')
        assert not rear_report['whole_cad_conflicts'] and rear_report['generator_sha256']==digest(Path(__file__).with_name(generator))
        if generator=='standing_aperture45.py':
            assert rear_report['whole_front_path_against_rear_cad_conflicts']==[]
            assert rear_report['generator_dependencies_sha256']=={'shelf45.py':digest(Path(__file__).with_name('shelf45.py'))}
        for file,sha in rear_report['stl_sha256'].items():assert digest(out/file)==sha
        result['whole_rear_shelf_cad_release']=rear_report
        result['whole_rear_shelf_bead_release']=lateral_release(checker,data,xyz,carrier|tabs,rear_beads,'+y')
        result['removal_order']=['External_cradle: -printZ; both shelves and tabs remain',
            'Front_pull_shelf: -printY; rear shelf, carrier and tabs remain',
            'Rear_pull_shelf: +printY; carrier and tabs remain','Release_tabs: peel after cooling']
    result['working_spaces']={}
    hard_fails=[];cleanup=[]
    removable=result.get('individual_front_piece_release',{'clear':True})['clear'] and not interference and result['whole_bead_release']['clear'] and (not has_front or result['whole_shelf_bead_release']['clear']) and result.get('whole_rear_shelf_bead_release',{'clear':True})['clear']
    for name,region in routes.items():
        row=inspect_route(checker,region,name,frame,xyz,data,kinds,features,~tower,
            {'External_cradle':cradle_beads,**({'Front_pull_shelf':shelf_beads} if has_front else {}),**({'Rear_pull_shelf':rear_beads} if has_rear else {})},tabs,removable)
        public={prior.full.LEGACY_CONNECTOR:'DFRobot board and connector operating stroke',
                prior.full.LEGACY_LEAD:'DFRobot Gravity lead operating stroke',
                prior.full.BOARD_ROUTE:prior.full.BOARD_LABEL}.get(name,name)
        row['inherited_source_region']=name
        result['working_spaces'][public]=row
        if row['unacceptable_obstruction']:hard_fails.append(public)
        if row['requires_print_helper_removal']:cleanup.append(public)
    result['obstructed_until_print_helpers_removed']=cleanup
    result['unacceptable_route_obstructions']=hard_fails
    save(); print('blocked',{k:v['violations'] for k,v in result['working_spaces'].items() if v['violations']},flush=True)
    evaluate_material(result,out,frame,old_body,solid,material,xyz,carrier,data,engine,checker,hard_fails,interference,removable)
    save()


def evaluate_material(result,out,frame,old_body,solid,material,xyz,carrier,data,engine,checker,hard_fails,interference,removable):
    q=checker.q
    result['critical_material']={}
    result['removed_witness_mm3']={}
    for name,region in material[prior.d.CARRIER].items():
        original=region.transform(np.linalg.inv(frame)[:3])^old_body
        result['removed_witness_mm3'][name]=max(0.,(original-solid).volume())
        result['critical_material'][name]=engine.material_coverage(q,checker.start_audit,
            original,xyz[carrier],data[carrier,3],data[carrier,4],data[carrier,7])
    result['new_material_witnesses']={}
    if (out/'standing-repair.json').is_file():
        repair=json.loads((out/'standing-repair.json').read_text())
        assert max(repair['maximum_added_intersection_mm3_by_route'].values())<1.e-5
        if 'lower_lip_relief' in repair:
            assert abs(repair['removed_mm3']-repair['lower_lip_relief']['original_removed_mm3'])<.001
            assert repair['lower_lip_relief']['maximum_mating_or_witness_intrusion_mm3']<1.e-5
        else:assert repair['removed_mm3']<.001
        assert {'left_lip_root','left_lip_floor_lap'}<=set(repair['pre_union_bonds']) or set(repair['pre_union_bonds'])=={'root','floor_lap'}
        added=solid-old_body
        extra=0.
        if (out/'standing-web.json').is_file():
            web=json.loads((out/'standing-web.json').read_text())
            board=json.loads((out/'standing-board-relief.json').read_text())
            for receipt,module in ((web,'standing_web45.py'),(board,'standing_board45.py')):
                assert receipt['generator_file']==module and receipt['generator_sha256']==digest(Path(__file__).with_name(module))
            assert max(web['actual_added_intersections_by_route'].values())<1.e-5
            assert max(board['original_witness_losses_mm3'].values(),default=0.)<1.e-5
            extra=web['added_mm3']
            from web_qualification45 import inspect as qualify_web, LEGACY_WEB_TARGETS
            qualified=qualify_web(checker,out,web,xyz[carrier],data[carrier,3],data[carrier,4],data[carrier,7])
            qualified['intentionally_replaced_legacy_targets']=sorted(LEGACY_WEB_TARGETS)
            qualified['generator_original_witness_losses_mm3']=web['original_witness_losses_mm3']
            assert LEGACY_WEB_TARGETS<=result['critical_material'].keys()
            qualified['actual_original_witness_losses_agree']=all(
                abs(result['removed_witness_mm3'][name]-web['original_witness_losses_mm3'].get(name,0.))<.02
                for name in result['removed_witness_mm3'])
            qualified['qualified'] &= qualified['actual_original_witness_losses_agree']
            result['shared_left_guard_buttress']=qualified
            result['op1_lower_ledge_relief']=board
        if extra:
            # Part of the buttress restores R44 material previously relieved
            # in this revision. Compare net material in a common R44 frame.
            def precise_mesh(record):
                mesh=trimesh.load_mesh(out/record['file'])
                return mf.Manifold(mf.Mesh64(mesh.vertices,np.asarray(mesh.faces,np.uint64)))
            import manifold3d as mf
            expected=(precise_mesh(repair['complete_added_witness'])+precise_mesh(web['witnesses']['member']))-old_body
            missing=(expected-added).volume()
            unexpected=(added-expected).volume()
            result['net_addition_against_original_r44']=dict(expected_mm3=expected.volume(),native_mm3=added.volume(),
                expected_only_mm3=missing,native_only_mm3=unexpected,
                gross_step_additions_mm3=repair['added_mm3']+extra,
                restored_original_stock_mm3=repair['added_mm3']+extra-expected.volume())
            assert missing+unexpected<.025, result['net_addition_against_original_r44']
        else:assert abs(added.volume()-repair['added_mm3'])<.025
        if 'complete_added_witness' in repair:
            full=repair['complete_added_witness'];assert digest(out/full['file'])==full['sha256']
            intended=trimesh.load_mesh(out/full['file']);full_shape=q.solid(intended.vertices,intended.faces)
        else:full_shape=added
        regions={'complete added chamfer':full_shape}
        for name,record in repair['pre_union_bonds'].items():
            if 'sha256' in record:assert digest(out/record['file'])==record['sha256']
            witness=trimesh.load_mesh(out/record['file'])
            regions['pre-union '+name.replace('_',' ')]=q.solid(witness.vertices,witness.faces)
            assert abs(regions['pre-union '+name.replace('_',' ')].volume()-record['volume_mm3'])<.001
        for name,witness in regions.items():
            summary=supplemental_coverage(checker,witness,xyz[carrier],data[carrier,3],data[carrier,4],data[carrier,7])
            result['new_material_witnesses'][name]=dict(**summary,volume_mm3=witness.volume())
    result['weak_section_layers']={}
    for name,summary in result['critical_material'].items():
        if summary['minimum_layer_fraction']>=.9:continue
        target=material[prior.d.CARRIER][name].transform(np.linalg.inv(frame)[:3])^old_body
        rows=[]
        for z in np.unique(data[carrier,7]):
            sec=target.slice(float(z)-.1)
            if sec.area()<.1:continue
            x0,y0,x1,y1=sec.bounds()
            m=carrier & (abs(data[:,7]-z)<.001) & (xyz[:,0]>=x0-.6)&(xyz[:,0]<=x1+.6)&(xyz[:,1]>=y0-.6)&(xyz[:,1]<=y1+.6)
            actual=checker.start_audit.bead_footprints(q,xyz[m,:2],data[m,3])
            covered=(sec^actual).area()/sec.area()
            if covered<.9:rows.append({'layer_top':float(z),'coverage':covered,'target_bounds':sec.bounds(),'target_area':sec.area(),'missing':(sec-actual).bounds()})
        result['weak_section_layers'][name]=rows
    s=result['layer_starts']
    replaced=set()
    web_qualification=result.get('shared_left_guard_buttress')
    if web_qualification and web_qualification['qualified']:
        replaced=set(web_qualification['intentionally_replaced_legacy_targets'])
    intact={n:v for n,v in result['critical_material'].items() if n not in replaced}
    unexpected_removed=[v for n,v in result['removed_witness_mm3'].items() if n not in replaced]
    result['screen_passed']=not (s['floating_components'] or s['missing_printed_components'] or interference or
        hard_fails or max(unexpected_removed,default=0.)>.02 or not removable or
        (web_qualification is not None and not web_qualification['qualified']) or
        any(x['minimum_layer_fraction']<.9 for group in (intact,result['new_material_witnesses']) for x in group.values()))
    result['print_ready']=False
    print('critical below 0.9',{k:v for k,v in result['critical_material'].items() if v['minimum_layer_fraction']<.9},flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);check(p.parse_args().archive)
