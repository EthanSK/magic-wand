"""Fresh deposited-path checks for a genuinely single-carrier R42 trial.

Compose the established carrier support, route and material probes without
pretending the unprinted DFRobot bracket or its clips are present. Geometry
and thresholds are the full-assembly ones; actual single-job paths are new.
"""
from pathlib import Path
from unittest.mock import patch
import numpy as np

import audit42 as full

c=full.common
d=full.d
KEY=d.CARRIER


def support_check(record,solid,layout,owner):
    base=full.BASE_SUPPORT_CHECK(record,solid,layout)
    def inspect(data,positions,labels,objects,q,starts):
        support=np.char.startswith(labels,'Support')
        assert not (support & (data[:,6]!=owner)).any(),'Unowned support in one-carrier job'
        result=base(data,positions,labels,objects,q,starts)
        if 'failure' in result:return result
        local=positions-objects[KEY]['vertices'].min(0)
        checker=c.load_checker().audit
        for row in result['interfaces']:
            if not row['roof_layers']:
                proof=full.deposited_roof_backing(checker,data,local,c.model_mask(labels),
                                                  row['enforcer_print_bounds_mm'])
                row['prior_layer_backing']=proof
                row['passed']=proof['passed']
        result['support_owner_ids']={KEY:owner}
        result['passed']=bool(result['inside_bed']
            and all(gap>.2 for gap in result['other_part_adhesion_gaps_mm'].values())
            and all(row['passed'] for row in result['interfaces'])
            and all(row['passed'] for row in result['removal_access'].values()))
        return result
    return inspect


def additions(archive,exports,result,owner):
    checker,data,labels,settings,offset,objects,records=c.object_data(archive,exports)
    features=checker.read_project(archive)[1]
    gaps,material=full.routes()
    mesh=c.trimesh.load_mesh(exports/f'{KEY}{c.SOURCE_SUFFIX}')
    solid=checker.q.solid(mesh.vertices,mesh.faces)
    xyz=c.local_points(data,offset,objects[KEY],mesh)
    frame=np.asarray(records[KEY]['print_to_assembly'])
    inv=np.linalg.inv(frame)[:3]
    model=c.model_mask(labels) & (data[:,6]==owner)
    supporting=np.char.startswith(labels,'Support') & (data[:,6]==owner)
    occupancy={}
    for label,region in {**gaps[KEY],**full.precision_support_spaces()}.items():
        hit=c.route_hits(checker.q,region,xyz,data[:,3],data[:,4],data[:,5].astype(int),
                         features,frame,supporting)
        occupancy[label]={'support_bead_hits':hit['violations'],'poses_checked':hit['poses_checked'],
            'examples':hit.get('examples',[]),'must_remove_before_assembly':bool(hit['violations']),
            'physical_cleanup_verified':False}
    strict=('unloaded_clip_bore','clip_gap_mid','clip_gap_rear','snap hinge bores',
            'complete hinge bore surfaces')
    failures=[]
    for label in strict:
        if occupancy[label]['support_bead_hits']:
            failures.append([KEY,label,'Native support obstructs a support-free grip or hinge'])

    from audit_plate32 import PAD_SUFFIX
    pad=c.trimesh.load_mesh(exports/f'{KEY}{PAD_SUFFIX}')
    pads=checker.q.solid(pad.vertices,pad.faces)
    low,high=np.asarray((solid+pads).bounding_box()).reshape(2,3)
    keep=(data[:,6]==owner) & ~np.char.startswith(labels,'Support') & (labels!='Prime tower')
    keep &= ((xyz>=low-[.55,.55,.4]) & (xyz<=high+[.55,.55,.4])).all(1)
    early=keep & (data[:,7]<=.401)
    assert early.any(),'No first-layer model/helper paths'
    radius=max(.25,float(data[early,3].max())/2+.001)
    pad_only=pads.slice(.1).offset(radius)-solid.slice(.1).offset(radius)
    pad_centres=(data[:,7]<=.401) & checker.q._inside(pad_only,xyz[:,:2])
    cleanup={}
    for label in ('external_wire_bus',full.PLUG_ROUTE):
        region=gaps[KEY][label]
        args=(checker.q,region,xyz,data[:,3],data[:,4],data[:,5].astype(int),features,frame)
        before=c.route_hits(*args,keep)
        after=c.route_hits(*args,keep & ~pad_centres)
        proof={'before_pad_cleanup':before,'after_pad_cleanup':after,
            'excluded_pad_bead_samples':int((keep & pad_centres).sum()),
            'permanent_model_guard_mm':radius,'physical_cleanup_verified':False,
            'non_pad_model_and_brim_retained':True,
            'passed':bool(after['poses_checked']==len(tuple(region.poses())) and not after['violations'])}
        cleanup[label]=proof
        result['parts'][KEY]['working_spaces'][label]=after
        if not proof['passed']:failures.append([KEY,label,'Obstructed after pad cleanup',after])

    # The generic audit proves every complete operating/loading route and
    # nominal critical section. Anchor the new OP1 routes to actual plastic.
    witnesses={}
    base_working=d.geometry()[1]
    for label,region in gaps[KEY].items():
        if label in base_working or label in (full.PLUG_ROUTE,full.LEGACY_CONNECTOR,full.LEGACY_LEAD):
            continue
        shapes=tuple(region.poses()) if hasattr(region,'poses') else (region,)
        anchors=shapes if len(shapes)<=3 else (shapes[0],shapes[len(shapes)//2],shapes[-1])
        row=c.clearance_sections(data[model],xyz[model],anchors,inv,checker,
                                 witness_width=3.2 if 'lead' in label.lower() else 1.15)
        row.update(full_intrusion_poses=len(shapes),deposition_anchor_poses=len(anchors))
        if label=='OP1 switch insertion' and not row['layers_with_nearby_deposition']:
            anchor=witnesses[full.BOARD_ROUTE]
            scan=result['parts'][KEY]['working_spaces'][label]
            row.update(free_air_path=True,anchored_by=full.BOARD_ROUTE,
                passed=bool(anchor['passed'] and row['layers_checked']
                    and scan['poses_checked']==len(shapes) and not scan['violations']
                    and row['maximum_core_intrusion_mm2']<.015))
        witnesses[label]=row
        if not row['passed']:failures.append([KEY,label,'Unanchored or obstructed clearance witness',row])
    geometry=c.read_json(d.HERE/'exports/geometry-checks.json')['checks']
    poses=tuple(gaps[KEY][full.PLUG_ROUTE].poses())
    expected=tuple((d.hardware()['plug']+d.hardware()['op1_wire']).translate((0.,0.,z))
                   for z in np.linspace(-9.,0.,37))
    error=max(float((a-b).volume()+(b-a).volume()) for a,b in zip(poses,expected))
    scan=cleanup[full.PLUG_ROUTE]['after_pad_cleanup']
    witnesses[full.PLUG_ROUTE]={'free_air_path':True,'full_intrusion_poses':len(poses),
        'anchored_by':full.BOARD_ROUTE,'maximum_route_pose_error_mm3':error,
        'passed':bool(geometry['passed'] and witnesses[full.BOARD_ROUTE]['passed']
                      and len(poses)==37 and scan['poses_checked']==37 and not scan['violations'] and error<.001)}
    if not witnesses[full.PLUG_ROUTE]['passed']:
        failures.append([KEY,full.PLUG_ROUTE,'Unanchored or obstructed plug route'])

    early_roots=[];previous=None
    for top in (.2,.4,.6,.8,1.,1.2,1.4,1.6):
        section=solid.slice(top-.1).offset(-.06,c.mf.JoinType.Round)
        mask=model & (abs(data[:,7]-top)<.001)
        printed=c.footprint(checker,data,xyz,mask)^section
        wall=mask & np.isin(labels,('Outer wall','Inner wall'))
        width=float(np.median(data[wall,3])) if wall.any() else 0.
        shell_width=int(settings['wall_loops'])*width
        target=section-section.offset(-shell_width,c.mf.JoinType.Round) if shell_width else section
        coverage=(printed^target).area()/max(target.area(),1e-8)
        connected=max((p.area() for p in printed.decompose()),default=0.)/max(printed.area(),1e-8)
        backing=1. if previous is None else (printed^previous.offset(.45,c.mf.JoinType.Round)).area()/max(printed.area(),1e-8)
        row={'layer_top_mm':top,'coverage':coverage,'largest_piece_fraction':connected,
             'previous_layer_overlap':backing,'model_bead_samples':int(mask.sum()),
             'passed':bool(target.area()>.1 and wall.any() and mask.any()
                           and coverage>=.85 and connected>=.90 and backing>=.75)}
        early_roots.append(row);previous=printed
    if not all(row['passed'] for row in early_roots):
        failures.append([KEY,'Early root layers are incomplete or disconnected',early_roots])
    return {'temporary_support_in_working_spaces':occupancy,'pad_cleanup':cleanup,
        'clearance_witnesses':witnesses,'early_root_layers':early_roots,
        'absent_bracket_scope':'The generic carrier checks include every DFRobot operating pose against this carrier. The unprinted bracket, pusher, posts and clips retain their separate hash-bound assembly audit; they are not deposited or claimed tested here.',
        'physical_strength_and_cleanup_verified':False},failures


def audit(archive,scratch,owner):
    exports=scratch/'build-source/exports'
    checker=c.load_checker()
    c.design,c.preparation=d,full.plate42
    c.KEY,c.BRACKET=KEY,d.BRACKET
    record=c.read_json(exports/'manifest.json')['parts'][KEY]
    mesh=c.trimesh.load_mesh(exports/f'{KEY}{c.SOURCE_SUFFIX}')
    solid=checker.audit.q.solid(mesh.vertices,mesh.faces)
    gaps,material=full.base_routes()
    key_routes=lambda:({KEY:gaps[KEY]},{KEY:material[KEY]})
    layout=c.read_json(scratch/'print-checks.json')
    with patch.object(c,'support_removal_grid',side_effect=full.support_removal_grid), \
         patch.object(checker.project22.studio.p19,'command_audit',side_effect=full.plate42.command_audit):
        result=c.inspect(archive,exports,key_routes,layout,
            removable_support=support_check(record,solid,layout,owner))
    rows,failures=additions(archive,exports,result,owner)
    result['single_carrier_deposition_checks']=rows
    result['failures'].extend(failures)
    result.update(passed=not result['failures'],checker_sha256=c.digest(Path(__file__)),
        geometry_source_sha256=c.digest(Path(d.__file__)),
        full_assembly_checker_sha256=c.digest(Path(full.__file__)),
        physical_success_verified=False,physical_support_removal_verified=False)
    return result
