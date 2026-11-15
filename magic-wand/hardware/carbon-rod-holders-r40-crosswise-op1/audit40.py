"""Audit actual R40 deposition with revision-specific routes and load paths.

The R38 checker owns bead sampling, anchoring, support access and material
coverage. This file supplies the changed board, plug, pusher and root spaces.
Run through geometry_budget.py; no printer connection is made.
"""
import argparse
from functools import lru_cache
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

import holder40 as d
import plate40
import audit38 as common

BOARD_ROUTE = 'centred OP1 and complete prewired insertion'
BOARD_LABEL = 'crosswise OP1 board insertion'


@lru_cache(maxsize=1)
def routes():
    key, working, fixed, ribs = d.geometry()
    paddle, parts, r = d.bracket(), d.hardware(), d.r
    receipt = common.read_json(d.HERE/'exports/manifest.json')
    assert receipt['source_sha256']['holder40.py'] == common.digest(Path(d.__file__))
    backup = common.read_json(d.HERE/'exports/geometry-checks.json')['checks']['backup_angle_deg']
    angles = np.linspace(d.EARLY_ANGLE, backup, 29)
    hinge = r.mirrored(r.d.axis_oval(r.AXIS_Y+r.CLICK_SHIFT, r.AXIS_Z, r.h29.TAB_R+.03, *r.h29.SUPPORT_X))
    board = d.union(parts[n] for n in ('board','sockets','housing'))
    mouse = d.union(parts[n] for n in ('switch','terminals','plunger'))
    # Feed the complete flexible lead through the existing external wire bus.
    # That canonical route checks permanent plastic after the separately
    # audited, labelled breakaway pads are removed. The OP1 lead's -9 mm
    # approach crosses one such pad at the rear bed face; it is not permanent
    # holder material. Keep all the original Choc wire-bus poses as well.
    old_bus=working['external_wire_bus']
    bus_poses=tuple(old_bus.poses()) if hasattr(old_bus,'poses') else (old_bus,)
    wire_bus=common.Poses((*bus_poses,*(parts['op1_wire'].translate((0.,0.,z)) for z in np.linspace(-9.,0.,37))))
    gaps = {
        d.CARRIER: {
            **working, 'external_wire_bus':wire_bus, 'snap hinge bores':hinge, 'OP1 mounting screw pilots':d.op1_reliefs()[3],
            # Retain the inherited checker's internal anchor key only here.
            # The public report renames it to BOARD_LABEL; the harness has its
            # own different, below-board path rather than the old wired drop.
            BOARD_ROUTE:common.Poses(board.translate((0.,0.,z)) for z in np.linspace(0.,d.h32.BOARD_RISE,33)),
            'OP1 plug insertion from below':common.Poses(parts['plug'].translate((0.,0.,z)) for z in np.linspace(-9.,0.,37)),
            'OP1 switch insertion':common.Poses(mouse.translate((0.,0.,z)) for z in np.linspace(0.,8.,17)),
            'shifted Grove plug operating stroke':common.Poses(r.world(d.housing()+d.plug(),a) for a in angles),
            'shifted Grove lead operating stroke':common.Poses(r.world(d.lead(1.1),a) for a in angles),
            'shifted Grove prewired insertion':common.Poses(r.world((d.board()+d.housing()+d.plug()+d.components()).translate((0.,0.,z))) for z in np.linspace(0.,d.SERVICE_LIFT,17)),
        },
        d.BRACKET: {
            'Grove PCB seat':d.board(), 'Grove underside socket and plug':d.housing()+d.plug(),
            'Grove underside components':d.components(),
            'Grove lead insertion':common.Poses(d.lead(1.1,lift=z) for z in np.linspace(0.,d.SERVICE_LIFT,17)),
            'arm squeeze clearance':common.Poses(r.bent(paddle,a)-paddle for a in np.linspace(.25,1.,4)),
            'arm flex gaps':r.mirrored(d.box(.72,1.77,r.ARM_ROOT_Y+1.7,27.2,17.07,18.24)),
            'adjustable stop pilot':d.stop_pilot(.61)^d.box(d.STOP_X-1.,d.STOP_X+1.,d.STOP_Y-1.,d.STOP_Y+1.,d.STOP_BOSS_BOTTOM+.12,d.STOP_BOSS_BOTTOM+4.05),
        },
    }
    for i,y in enumerate(d.HOLES,1):
        gaps[d.BRACKET][f'shifted Grove screw pilot {i}']=d.cylinder(d.GROVE_X,y,d.BOARD_Z-d.grove.PILOT_DEPTH+.25,d.BOARD_Z-.07,.61)
    material={
        d.CARRIER:{'fixed hinge supports':key^r.supports(), 'OP1 mounting shoulders':key^d.op1_seats(),
            'adjustable stop landing':key^d.stop_landing(), 'saddle cheek beside plug':key^d.saddle_cheek(),
            'raised hinge roofs':key^r.mirrored(d.box(3.4,5.5,29.65,32.65,19.9,20.8))},
        d.BRACKET:{'hinge flex arms':paddle^r.arms(), 'adjustable stop boss':paddle^d.stop_stock(),
            'crosswise switch pusher':paddle^d.pusher(),
            'pusher brace bond':d.pusher()^(d.r39.bracket()-d.old_pusher_space()-d.switch_relief()),
            'arm root fillets':paddle^r.mirrored(d.box(1.85,4.55,r.ARM_ROOT_Y-.6,r.ARM_ROOT_Y+1.5,17.,19.)),
            'squeeze stop':paddle^d.box(-.65,.65,r.ARM_ROOT_Y,27.6,17.,18.3),
            'left hinge-to-screw rail':paddle^d.box(*d.LEFT_RAIL,d.old.TOUCH_WEB_FRONT,r.ARM_ROOT_Y,d.LEFT_RAIL_BOTTOM,d.BOARD_Z)},
    }
    for i,y in enumerate(d.HOLES,1):
        material[d.BRACKET][f'shifted Grove screw boss {i}']=paddle^d.boss(y)
    for name,rib in ribs.items():
        if name.startswith('R'):
            material[d.CARRIER][f'{name} guard root bond']=fixed^rib
        else:
            # The new web changes only the outer attachment. Keep the
            # unchanged rod-side joint in the actual deposition audit too.
            material[d.CARRIER][f'{name} rod-side guard bond']=fixed^rib^d.box(-9.,0.,-12.,35.,0.,13.)
    material[d.CARRIER].update(d.guard_web_interfaces())
    for part,regions in material.items():
        for label,shape in regions.items():
            assert not shape.is_empty() and shape.volume()>.05,(part,label,'empty witness')
    return gaps,material


BASE_EXTRA_CHECKS = common.extra_checks
PLUG_ROUTE = 'OP1 plug insertion from below'


def extra_checks(archive, exports, base_result):
    gaps, material = routes()
    # The plug is outside the printed carrier, so its below-board route has
    # no nearby holder beads. Anchor that free-air path to the actual mounted
    # PCB/connector instead, as the inherited checker does for the switch.
    # The generic audit has already scanned every plug pose for collisions.
    anchored_gaps = {**gaps, d.CARRIER:{k:v for k,v in gaps[d.CARRIER].items() if k != PLUG_ROUTE}}
    with patch.object(common, 'routes', return_value=(anchored_gaps,material)):
        result, failures = BASE_EXTRA_CHECKS(archive,exports,base_result)
    scan = base_result['parts'][d.CARRIER]['working_spaces'][PLUG_ROUTE]
    anchor = result[d.CARRIER]['clearance_witnesses'][BOARD_ROUTE]
    geometry = common.read_json(d.HERE/'exports/geometry-checks.json')['checks']
    poses = tuple(gaps[d.CARRIER][PLUG_ROUTE].poses())
    expected = tuple(d.hardware()['plug'].translate((0.,0.,z)) for z in np.linspace(-9.,0.,37))
    pose_error = max(float((a-b).volume()+(b-a).volume()) for a,b in zip(poses,expected))
    row = {'free_air_path':True, 'full_intrusion_poses':37,
        'anchored_by':'Mounted OP1 PCB and its rigidly transformed white connector',
        'board_deposition_anchor_passed':anchor['passed'],
        'rigid_hardware_transform_error_mm3':geometry['op1_group_rigid_turn_error_mm3'],
        'CAD_entry_overlap_mm3':geometry['clearance_overlap_mm3']['op1_plug_from_below'],
        'maximum_route_pose_error_mm3':pose_error,
        'passed':bool(geometry['passed'] and anchor['passed'] and scan['poses_checked']==len(poses)==37 and not scan['violations']
            and pose_error<.001
            and geometry['op1_group_rigid_turn_error_mm3']<.001
            and geometry['clearance_overlap_mm3']['op1_plug_from_below']<.035)}
    result[d.CARRIER]['clearance_witnesses'][PLUG_ROUTE] = row
    if not row['passed']:failures.append([d.CARRIER,PLUG_ROUTE,'Unanchored or obstructed plug entry',row])

    # Retain direct evidence that the new lead's cleanup dependency really
    # is the labelled first-two-layer pad, not a hole in permanent plastic.
    checker,data,labels,_,offset,objects,records = common.object_data(archive,exports)
    from audit_plate32 import PAD_SUFFIX
    mesh = common.trimesh.load_mesh(exports/f'{d.CARRIER}{common.SOURCE_SUFFIX}')
    pad = common.trimesh.load_mesh(exports/f'{d.CARRIER}{PAD_SUFFIX}')
    solid = checker.q.solid(mesh.vertices,mesh.faces)
    pads = checker.q.solid(pad.vertices,pad.faces)
    xyz = common.local_points(data,offset,objects[d.CARRIER],mesh)
    keep = (labels!='Prime tower') & ~np.char.startswith(labels,'Support')
    low,high = np.asarray((solid+pads).bounding_box()).reshape(2,3)
    keep &= ((xyz>=low-[.55,.55,.4]) & (xyz<=high+[.55,.55,.4])).all(1)
    early = keep & (data[:,7]<=.401)
    assert early.any(), 'No carrier first-layer deposition anchors the pad check'
    radius = max(.25,float(data[early,3].max())/2+.001)
    pad_only = pads.slice(.1).offset(radius)-solid.slice(.1).offset(radius)
    pad_centres = (data[:,7]<=.401) & checker.q._inside(pad_only,xyz[:,:2])
    lead = gaps[d.CARRIER]['external_wire_bus']
    pose_count = len(tuple(lead.poses()))
    features = checker.read_project(archive)[1]
    frame = np.asarray(records[d.CARRIER]['print_to_assembly'])
    args = (checker.q,lead,xyz,data[:,3],data[:,4],data[:,5].astype(int),features,frame)
    before = common.route_hits(*args,keep)
    after = common.route_hits(*args,keep & ~pad_centres)
    proof = {'before_pad_cleanup':before, 'after_pad_cleanup':after,
        'only_excluded':'Bead centres in labelled pad-only areas at layer tops <= 0.4 mm',
        'includes':'Original Choc bus and every OP1 lead approach pose',
        'permanent_model_guard_mm':radius, 'assumes_audited_support_removed':True,
        'non_pad_model_and_brim_retained':True, 'physical_cleanup_verified':False,
        'passed':bool(after['poses_checked']==pose_count and not after['violations'])}
    result[d.CARRIER]['OP1_lead_pad_cleanup'] = proof
    if not proof['passed']:failures.append([d.CARRIER,'OP1 lead after pad cleanup',after])
    return result,failures


def audit(archive: Path, scratch: Path) -> dict:
    common.design=d
    common.preparation=plate40
    regions_before=d.BATTERY.h18.regions
    def battery_regions(name):
        if name!='Battery_End_Door':return regions_before(name)
        p=d.DOOR
        return {'tongue_slit':d.box(p['tongue_root_x_mm']+.05,p['window_x_mm'][0]-.05,
            p['y_mm'][0]-1,p['y_mm'][1]+1,p['tongue_z_mm'][1]+.05,p['tongue_z_mm'][1]+p['slit_mm']-.05)}
    with patch.object(common,'routes',side_effect=routes),patch.object(common,'extra_checks',side_effect=extra_checks),patch.object(d.BATTERY.h18,'regions',side_effect=battery_regions):
        result=common.audit(archive,scratch)
    result['r40_deposition_checks']=result.pop('r38_deposition_checks')
    result['checker_sha256']=common.digest(Path(__file__))
    # Rename the compatibility-only anchor throughout keys and explanations.
    return json.loads(json.dumps(result).replace(BOARD_ROUTE,BOARD_LABEL))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('scratch',type=Path);parser.add_argument('report',type=Path)
    args=parser.parse_args();common.PLOT_DIRECTORY=args.report.resolve().parent
    result=audit(args.archive,args.scratch)
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'failures':result['failures']}))
    raise SystemExit(0 if result['passed'] else 1)
