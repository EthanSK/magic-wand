"""Check R42's actual deposition, hardware routes and complete load paths.

Composes the established R38 bead/support checker with DFRobot-specific
regions. Internal legacy anchor names are renamed in the public report;
they do not select Grove hardware. Run through geometry_budget.py.
"""
import argparse
from collections import deque
from functools import lru_cache
import json
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np

import holder42 as d
import plate42
import audit38 as common

BOARD_ROUTE = 'centred OP1 and complete prewired insertion'
BOARD_LABEL = 'diagonal OP1 board insertion with the carrier off the rod'
PLUG_ROUTE = 'OP1 prewired plug insertion from below before fitting the rod'
LEGACY_CONNECTOR = 'shifted Grove plug operating stroke'
LEGACY_LEAD = 'shifted Grove lead operating stroke'


@lru_cache(maxsize=1)
def routes():
    key, working, fixed, ribs = d.geometry()
    paddle, parts, r, base = d.bracket(), d.hardware(), d.r, d.base
    original_floor = d.old.bracket()-d.old_pusher_space()-d.switch_relief()
    record = common.read_json(d.HERE/'exports/manifest.json')
    assert record['source_sha256']['holder42.py'] == common.digest(Path(d.__file__))
    geometry = common.read_json(d.HERE/'exports/geometry-checks.json')['checks']
    angles = np.linspace(d.EARLY_ANGLE, geometry['backup_angle_deg'], 29)
    hinge = r.mirrored(r.d.axis_oval(r.AXIS_Y+r.CLICK_SHIFT, r.AXIS_Z,
                                    r.h29.TAB_R+.03, *r.h29.SUPPORT_X))
    board = d.union(parts[n] for n in ('board', 'sockets', 'housing'))
    mouse = d.union(parts[n] for n in ('switch', 'terminals', 'plunger'))
    harness = parts['plug'] + parts['op1_wire']
    pins = d.union(d.gravity_pins(max(d.PIN_TAILS), dx, dy)
                   for dx in (-d.PIN_X_TOLERANCE, 0., d.PIN_X_TOLERANCE)
                   for dy in (-d.PIN_Y_TOLERANCE, 0., d.PIN_Y_TOLERANCE))
    sensor = r.sensor() + r.connector() + r.electrode() + pins
    old_bus = working['external_wire_bus']
    bus = tuple(old_bus.poses()) if hasattr(old_bus, 'poses') else (old_bus,)
    wire_bus = common.Poses((*bus, *(parts['op1_wire'].translate((0., 0., z))
                                    for z in np.linspace(-9., 0., 37))))
    clip_approach = d.union(r.clips().translate((0., -y, 0.))
                            for y in np.linspace(0., 5., 21))
    post_stock = d.union(r.post().translate((s*r.POST_X, r.hole_y(), 0.)) for s in (-1, 1))
    gaps = {
        d.CARRIER: {
            **working, 'external_wire_bus': wire_bus, 'snap hinge bores': hinge,
            # The printed cutter continues below the bosses. The functional
            # pilot stops 0.15 mm below the actual kit screw tip, and is round;
            # the teardrop apex is print relief, not a fastener's envelope.
            'OP1 mounting screw pilots': d.diagonal(d.h32.screw_pilots(
                parts['fasteners'].bounding_box()[2]-.15)),
            BOARD_ROUTE: common.Poses(board.translate((0., 0., z))
                                      for z in np.linspace(0., d.h32.BOARD_RISE, 33)),
            PLUG_ROUTE: common.Poses(harness.translate((0., 0., z))
                                     for z in np.linspace(-9., 0., 37)),
            'OP1 switch insertion': common.Poses(mouse.translate((0., 0., z))
                                                 for z in np.linspace(0., 8., 17)),
            LEGACY_CONNECTOR: common.Poses(r.world(sensor, a) for a in angles),
            LEGACY_LEAD: common.Poses(r.world(r.gravity_lead(), a) for a in angles),
        },
        d.BRACKET: {
            'DFRobot PCB and connector-pin loading': common.Poses(
                sensor.translate((0., 0., z)) for z in np.linspace(0., 6., 25)),
            'DFRobot Gravity lead': r.gravity_lead(),
            'DFRobot clip approach excluding intended post snap': clip_approach-post_stock,
            'arm squeeze clearance': common.Poses(r.bent(paddle, a)-paddle
                                                  for a in np.linspace(.25, 1., 4)),
            'arm flex gaps': r.mirrored(d.box(.72, 1.77, r.ARM_ROOT_Y+1.7, 27.2, 17.07, 18.24)),
            'adjustable stop pilot': base.stop_pilot(.61) ^ d.box(
                base.STOP_X-1., base.STOP_X+1., base.STOP_Y-1., base.STOP_Y+1.,
                base.STOP_BOSS_BOTTOM+.12, base.STOP_BOSS_BOTTOM+4.05),
        },
    }
    material = {
        d.CARRIER: {
            'fixed hinge supports': key ^ r.supports(),
            'OP1 mounting shoulders': key ^ d.op1_seats(),
            'adjustable stop landing': key ^ base.stop_landing(),
            'raised hinge roofs': key ^ r.mirrored(d.box(3.4, 5.5, 29.65, 32.65, 19.9, 20.8)),
        },
        d.BRACKET: {
            'hinge flex arms': paddle ^ r.arms(),
            'adjustable stop boss': paddle ^ base.stop_stock(),
            'diagonal switch pusher': paddle ^ d.pusher(),
            # The added reinforcement is a parallel path into the floor.
            # Check the complete unshrunk floor interface, the pusher-to-root
            # joint and both full solids. Report the old direct-only subregion
            # below as well; it is no longer the complete load-path section.
            'pusher brace bond': (d.pusher()+d.pusher_root()) ^ original_floor,
            'pusher to root bond': d.pusher() ^ d.pusher_root(),
            'pusher root stock': paddle ^ d.pusher_root(),
            'pusher root-to-floor bond': d.pusher_root() ^ (d.old.bracket()-d.old_pusher_space()-d.switch_relief()),
            'arm root fillets': paddle ^ r.mirrored(d.box(
                1.85, 4.55, r.ARM_ROOT_Y-.6, r.ARM_ROOT_Y+1.5, 17., 19.)),
            # Follow the actual forward fan after the pin relief is cut,
            # including its narrow inner edge beside the pocket.
            'root fans beside Gravity pin pocket': paddle ^ d.hinge_repairs() ^ r.mirrored(d.box(
                1.85, 8.65, r.ARM_ROOT_Y-3., r.ARM_ROOT_Y-.6, 17., 19.)),
            'squeeze stop': paddle ^ d.box(-.65, .65, r.ARM_ROOT_Y, 27.6, 17., 18.3),
        },
    }
    for side in (-1, 1):
        material[d.BRACKET][f'DFRobot post and neck {side}'] = (
            paddle ^ r.post().translate((side*r.POST_X, r.hole_y(), 0.)))
    for name, rib in ribs.items():
        label = f'{name} guard root bond' if name.startswith('R') else f'{name} rod-side guard bond'
        bond = fixed ^ rib
        if name.startswith('L'):
            bond ^= d.box(-9., 0., -12., 35., 0., 13.)
        material[d.CARRIER][label] = bond
    material[d.CARRIER].update(d.guard_web_interfaces())
    bom = common.read_json(d.HERE/'complete-assembly.json')
    clips = sorted(n for g in bom['groups'].values() for n in g['parts'] if n.startswith(d.CLIP))
    assert len(clips) == 2
    for name in clips:
        gaps[name] = {'clip neck opening': d.h32.cylinder_at(
            0., 0., r.NECK[0]-.05, r.NECK[0]+r.CLIP_T+.05, r.NECK_R)}
        material[name] = {'both retaining jaws': d.clip_part()}
    for part, regions in material.items():
        for label, shape in regions.items():
            assert not shape.is_empty() and shape.volume() > .05, (part, label, 'empty witness')
    return gaps, material


def base_routes():
    """The prewired approach has its own complete, pad-cleanup scan below."""
    gaps, material = routes()
    return {**gaps, d.CARRIER: {n: s for n, s in gaps[d.CARRIER].items() if n != PLUG_ROUTE}}, material


def precision_support_spaces():
    working=routes()[0][d.CARRIER]
    r=d.r
    full_bore=r.mirrored(r.d.axis_oval(r.AXIS_Y+r.CLICK_SHIFT,r.AXIS_Z,
                                      r.h29.BORE_R,r.h29.SUPPORT_X[0]-.5,r.h29.SUPPORT_X[1]+.5))
    return {**{n:working[n] for n in ('unloaded_clip_bore','clip_gap_mid','clip_gap_rear','snap hinge bores')},
            'complete hinge bore surfaces':full_bore}


BASE_EXTRA_CHECKS = common.extra_checks
BASE_SUPPORT_CHECK = common.make_support_check


def deposited_roof_backing(checker, data, local, model, bounds):
    """Verify every layer in a sloped roof region against actual lower beads.

    R38's flat-roof report requires at least one new overhang. R42's diagonal
    roofs can instead grow entirely within its existing 0.45 mm backing
    envelope. Credit that only with nonempty, layer-by-layer deposition proof;
    an empty or genuinely unbacked region still fails.
    """
    low, high = np.asarray(bounds)
    roi = common.rectangle((*low[:2], *high[:2]))
    near = ((local[:, :2] >= low[:2]-.45) & (local[:, :2] <= high[:2]+.45)).all(1)
    candidates = model & near & (data[:, 7] >= low[2]+.05) & (data[:, 7] <= high[2]+.25)
    rows = []
    for top in np.unique(data[candidates, 7]):
        current = model & near & (abs(data[:, 7]-top)<.001)
        bottom = float(top)-float(np.median(data[current, 4]))
        roof = common.footprint(checker, data, local, current) ^ roi
        if roof.area() < .001:
            continue
        previous = model & (abs(data[:, 7]-bottom)<.001)
        lower = common.footprint(checker, data, local, previous)
        missing = roof-lower.offset(.45, common.mf.JoinType.Round)
        rows.append({'top_mm': round(float(top), 4), 'samples': int(current.sum()),
                     'deposited_area_mm2': roof.area(), 'unbacked_area_mm2': missing.area(),
                     'backed_fraction': 1.-missing.area()/roof.area()})
    total = sum(row['deposited_area_mm2'] for row in rows)
    covered = 1.-sum(row['unbacked_area_mm2'] for row in rows)/max(total, 1e-8)
    return {'basis': 'Actual model beads on every roof layer and its immediately preceding layer',
            'backing_envelope_mm': .45, 'layers': rows, 'backed_fraction': covered,
            'passed': bool(rows and total>.1 and covered>=.98
                           and all(row['unbacked_area_mm2']<.1 for row in rows))}


def native_support_owners(archive):
    """Use Studio's explicit G-code label mapping, never proximity, for ownership."""
    with ZipFile(archive) as source:
        root = ET.fromstring(source.read('Metadata/slice_info.config'))
    owners = {obj.get('name'): int(obj.get('identify_id')) for obj in root.findall('./plate/object')}
    assert len(set(owners.values())) == len(owners)
    assert d.CARRIER in owners and d.BRACKET in owners
    return owners


def bracket_support_check(checker, data, positions, labels, objects, layout, owners):
    mesh = common.trimesh.load_mesh(d.HERE/'exports'/f'{d.BRACKET}{common.SOURCE_SUFFIX}')
    solid = checker.q.solid(mesh.vertices, mesh.faces)
    local = common.local_points(data, np.zeros(3), objects[d.BRACKET], mesh)
    # positions include the extruder offset; local_points above needs the
    # same physical coordinates, even if a future profile has a nonzero one.
    local += positions-data[:,:3]
    support = np.char.startswith(labels, 'Support') & (data[:,6] == owners[d.BRACKET])
    model = common.model_mask(labels) & (data[:,6] == owners[d.BRACKET])
    assert support.any(), 'Bracket feet have no native support paths'
    record = common.read_json(d.HERE/'exports/manifest.json')['parts'][d.BRACKET]
    rows = []
    for label, (low, high) in plate42.bracket_support_boxes(record):
        low, high = np.asarray(low), np.asarray(high)
        near = ((local[:,:2]>=low[:2]-.45)&(local[:,:2]<=high[:2]+.45)).all(1)
        roi = common.rectangle((*low[:2],*high[:2]))
        roof = model & near & (abs(data[:,7]-.6)<.001)
        assert roof.any(), (label, 'No printed foot anchors the support witness')
        bottom = .6-float(np.median(data[roof,4]))
        previous = model & near & (abs(data[:,7]-bottom)<.001)
        target = (common.footprint(checker,data,local,roof)
                  - common.footprint(checker,data,local,previous).offset(.25,common.mf.JoinType.Round)) ^ roi
        assert target.area()>1., (label, 'Empty or misplaced foot witness')
        interfaces = support & near & np.char.startswith(labels,'Support interface')
        probes = []
        for z in np.unique(data[interfaces,7]):
            poly = common.footprint(checker,data,local,interfaces & (abs(data[:,7]-z)<.001))
            overlap = (target ^ poly).area()
            probes.append({'top_mm':float(z),'gap_mm':round(bottom-float(z),4),
                           'direct_overlap_mm2':round(overlap,5),
                           'covered_fraction':round((target ^ poly.offset(.25,common.mf.JoinType.Round)).area()/target.area(),5)})
        qualified = [p for p in probes if .19<=p['gap_mm']<=.26]
        best = max(qualified,key=lambda p:p['covered_fraction'],default=None)
        close = [p for p in probes if p['gap_mm']<.19 and p['direct_overlap_mm2']>.015]
        rows.append({'label':label,'roof_layer_top_mm':.6,'target_mm2':target.area(),
                     'interface_at_expected_gap':best,'too_close_interfaces':close,
                     'passed':bool(best and best['covered_fraction']>=.9 and not close)})
    radius = data[support,3,None]/2
    lo=(positions[support,:2]-radius).min(0);hi=(positions[support,:2]+radius).max(0)
    gaps={}
    for name,bounds in layout['material_bounds_xy_mm'].items():
        if name==d.BRACKET:continue
        other_lo,other_hi=np.asarray(bounds)
        gaps[name]=round(float(np.linalg.norm(np.maximum(np.maximum(lo-other_hi,other_lo-hi),0.))),4)
    tower = labels=='Prime tower'
    assert tower.any(), 'Smooth timelapse has no wipe tower'
    tower_radius=data[tower,3,None]/2
    tower_lo=(positions[tower,:2]-tower_radius).min(0)
    tower_hi=(positions[tower,:2]+tower_radius).max(0)
    gaps['wipe tower']=round(float(np.linalg.norm(np.maximum(np.maximum(lo-tower_hi,tower_lo-hi),0.))),4)
    removal = support_removal_grid(solid,checker,data,local,common.model_mask(labels),support,record)
    only_first_layer = bool(data[support,7].max()<=.201)
    on_bed=bool((lo>=0.).all() and (hi<=180.).all())
    return {'part':d.BRACKET,'support_samples':int(support.sum()),
            'support_bed_bounds_mm':[lo.tolist(),hi.tolist()], 'top_gap_mm':.2,
            'inside_bed':on_bed,'only_first_layer_support':only_first_layer,
            'other_part_adhesion_gaps_mm':gaps,'interfaces':rows,'removal_access':removal,
            'passed':bool(on_bed and only_first_layer and all(g>.2 for g in gaps.values())
                          and all(r['passed'] for r in rows) and removal['passed'])}


def make_support_check(record, solid, layout, owners):
    original = BASE_SUPPORT_CHECK(record, solid, layout)

    def check(data, positions, labels, objects, q, starts):
        support = np.char.startswith(labels,'Support')
        assigned = np.isin(data[:,6],(owners[d.CARRIER],owners[d.BRACKET]))
        assert not (support & ~assigned).any(), 'Native support has an unaudited owner'
        keep = ~support | (data[:,6]==owners[d.CARRIER])
        kd,kp,kl=data[keep],positions[keep],labels[keep]
        result = original(kd, kp, kl, objects, q, starts)
        if 'failure' in result:
            return result
        local = kp-objects[d.CARRIER]['vertices'].min(0)
        checker = common.load_checker().audit
        for row in result['interfaces']:
            if not row['roof_layers']:
                proof = deposited_roof_backing(checker, kd, local, common.model_mask(kl),
                                               row['enforcer_print_bounds_mm'])
                row['prior_layer_backing'] = proof
                row['passed'] = proof['passed']
        result['passed'] = bool(result['inside_bed']
                                and all(gap>.2 for gap in result['other_part_adhesion_gaps_mm'].values())
                                and all(row['passed'] for row in result['interfaces'])
                                and all(row['passed'] for row in result['removal_access'].values()))
        bracket = bracket_support_check(checker,data,positions,labels,objects,layout,owners)
        result['bracket_feet']=bracket
        alo,ahi=np.asarray(result['support_bed_bounds_mm'])
        blo,bhi=np.asarray(bracket['support_bed_bounds_mm'])
        separation=float(np.linalg.norm(np.maximum(np.maximum(alo-bhi,blo-ahi),0.)))
        result.update(plate_support_samples=int(support.sum()),
                      support_owner_ids={name:owners[name] for name in (d.CARRIER,d.BRACKET)},
                      support_to_support_gap_mm=separation,
                      passed=bool(result['passed'] and bracket['passed'] and separation>.2))
        return result
    return check


def support_removal_grid(solid, checker, data, local, model, support, record, *, outward=False, step=.5):
    """R38's fragment flood, with R42's actual open exterior as the entry.

    The diagonal connector and guard have several removal approaches. Use
    free cells outside the complete carrier bounds, never an arbitrary ROI
    boundary inside a cavity. All nominal and deposited model walls remain
    obstacles, and obstructed support cells remain in the required total.
    Electronics and rod are fitted only after support and brim cleanup.
    """
    low, high = np.asarray(solid.bounding_box()).reshape(2, 3)
    pts = local[support]
    assert 0. < step <= .5
    radius = .4
    xs = np.arange(pts[:, 0].min()-2., pts[:, 0].max()+2.+step, step)
    ys = np.arange(low[1]-.5, high[1]+2.+step, step)
    zs = np.arange(.1, data[support, 7].max()+.4, .2)
    xy = np.stack(np.meshgrid(xs, ys, indexing='ij'), -1).reshape(-1, 2)
    free = np.zeros((len(zs), len(xs), len(ys)), dtype=bool)
    core = np.zeros_like(free)
    for i, z in enumerate(zs):
        layer = abs(data[:, 7]-(z+.1)) < .051
        occupied = solid.slice(float(z)) + common.footprint(checker, data, local, model & layer)
        free[i] = ~checker.q._inside(occupied.offset(radius, common.mf.JoinType.Round), xy).reshape(len(xs), len(ys))
        material = common.footprint(checker, data, local, support & layer).offset(-.2, common.mf.JoinType.Round)
        core[i] = checker.q._inside(material, xy).reshape(len(xs), len(ys))
    exterior = ((xs[:, None] < low[0]-.4) | (xs[:, None] > high[0]+.4)
                | (ys[None, :] < low[1]-.4) | (ys[None, :] > high[1]+.4))
    seeds = free & exterior[None, :, :]
    seen = np.zeros_like(free)
    queue = deque(map(tuple, np.argwhere(seeds)))
    for p in queue:
        seen[p] = True
    while queue:
        z, x, y = queue.popleft()
        for a, b, c in ((z-1, x, y), (z+1, x, y), (z, x-1, y),
                        (z, x+1, y), (z, x, y-1), (z, x, y+1)):
            if (0 <= a < len(zs) and 0 <= b < len(xs) and 0 <= c < len(ys)
                    and free[a, b, c] and not seen[a, b, c]):
                seen[a, b, c] = True
                queue.append((a, b, c))
    count, reached = int(core.sum()), int((core & seen).sum())
    return {'grid_xy_mm': step, 'grid_z_mm': .2, 'fragment_clearance_radius_mm': radius,
            'exit_seed_cells': int(seeds.sum()), 'support_core_cells': count,
            'reachable_support_core_cells': reached, 'reachable_fraction': round(reached/max(count, 1), 5),
            'entry': 'Free exterior beyond the complete carrier bounds; empty key/OP1 openings and open underside',
            'cleanup_order': 'Remove brims and break supports into small pieces before fitting electronics or rod',
            'physical_removal_verified': False,
            'passed': bool(seeds.any() and count >= 20 and reached/count >= .98)}


def connected_section(target, printed):
    """One actual bead component must carry the whole nominal section.

    Do not union CAD into the beads or clip away a real connection outside
    the witness. A large total coverage split between islands still fails.
    """
    area = target.area()
    assert area>.001, 'Empty connectivity witness'
    pieces = [(p ^ target).area() for p in printed.decompose()]
    total = sum(pieces)
    largest = max(pieces, default=0.)
    return {'nominal_area_mm2':area, 'deposited_area_mm2':total,
            'bead_components_meeting_witness':sum(p>.005 for p in pieces),
            'coverage_fraction':total/area, 'single_piece_nominal_fraction':largest/area,
            'single_piece_deposited_fraction':largest/max(total,1e-8),
            'passed':bool(largest/area>=.9 and largest/max(total,1e-8)>=.99)}


def pusher_connectivity(checker, data, xyz, normal, targets):
    layers = {}
    for top in np.unique(data[normal,7]):
        on = normal & (abs(data[:,7]-top)<.001)
        mid = float(top)-float(np.median(data[on,4]))/2
        sections = {label:shape.slice(mid) for label,shape in targets.items()}
        sections = {label:s for label,s in sections.items() if s.area()>.001}
        if not sections:continue
        printed = common.footprint(checker,data,xyz,on)
        for label,section in sections.items():
            row=connected_section(section,printed)
            layers.setdefault(label,[]).append({'layer_top_mm':float(top),**row})
    return {'basis':'Every intersecting layer; a single actual model-bead component carries the complete nominal section',
            'regions':layers, 'physical_strength_verified':False,
            'passed':bool(set(layers)==set(targets) and all(row['passed'] for rows in layers.values() for row in rows))}


def extra_checks(archive, exports, base_result):
    gaps, material = routes()
    anchored, _ = base_routes()
    with patch.object(common, 'routes', return_value=(anchored, material)):
        result, failures = BASE_EXTRA_CHECKS(archive, exports, base_result)
    geometry = common.read_json(d.HERE/'exports/geometry-checks.json')['checks']
    # Retain R40's separate pad-only cleanup guard. The finished wire bus
    # includes all original Choc approaches as well as the full OP1 lead.
    # Exclude only labelled early pad centres outside the permanent model's
    # full bead-radius guard; ordinary model and brim samples remain checked.
    checker, data, labels, _, offset, objects, _ = common.object_data(archive, exports)
    records = common.read_json(exports/'manifest.json')['parts']
    owners = native_support_owners(archive)
    features = checker.read_project(archive)[1]
    # Account for native support in every functional space and operating
    # pose, including socket barrels, pins, connector, pilots and flex gaps.
    # Cleanup-dependent openings are not described as presently clear.
    for part, regions in gaps.items():
        if part not in (d.CARRIER,d.BRACKET):continue
        part_mesh = common.trimesh.load_mesh(exports/f'{part}{common.SOURCE_SUFFIX}')
        local = common.local_points(data,offset,objects[part],part_mesh)
        supporting = np.char.startswith(labels,'Support') & (data[:,6]==owners[part])
        occupancy = {}
        for label,region in regions.items():
            hit = common.route_hits(checker.q,region,local,data[:,3],data[:,4],
                                    data[:,5].astype(int),features,
                                    np.asarray(records[part]['print_to_assembly']),supporting)
            occupancy[label] = {'support_bead_hits':hit['violations'],
                                'poses_checked':hit['poses_checked'],
                                'examples':hit.get('examples',[]),
                                'must_remove_before_assembly':bool(hit['violations']),
                                'physical_cleanup_verified':False}
        result[part]['temporary_support_in_working_spaces'] = occupancy
        result[part]['clearance_scope'] = 'All temporary support must be removed before assembly; physical cleanup remains unverified.'
    rod = {name:row for name,row in result[d.CARRIER]['temporary_support_in_working_spaces'].items()
           if name=='unloaded_clip_bore' or name.startswith('clip_gap_')}
    assert set(rod)=={'unloaded_clip_bore','clip_gap_mid','clip_gap_rear'}
    rod_pass=not any(row['support_bead_hits'] for row in rod.values())
    result[d.CARRIER]['support_free_rod_grip']={'working_spaces':list(rod), 'passed':rod_pass}
    if not rod_pass:failures.append([d.CARRIER,'Native support occupies the rod grip or clip gap',rod])
    part_mesh=common.trimesh.load_mesh(exports/f'{d.CARRIER}{common.SOURCE_SUFFIX}')
    local=common.local_points(data,offset,objects[d.CARRIER],part_mesh)
    supporting=np.char.startswith(labels,'Support') & (data[:,6]==owners[d.CARRIER])
    full_bore=common.route_hits(checker.q,precision_support_spaces()['complete hinge bore surfaces'],
        local,data[:,3],data[:,4],data[:,5].astype(int),features,
        np.asarray(records[d.CARRIER]['print_to_assembly']),supporting)
    hinge={'tab_operating_space':result[d.CARRIER]['temporary_support_in_working_spaces']['snap hinge bores'],
           'complete_bore':full_bore,
           'passed':bool(not full_bore['violations'] and not result[d.CARRIER]['temporary_support_in_working_spaces']['snap hinge bores']['support_bead_hits'])}
    result[d.CARRIER]['support_free_hinge']=hinge
    if not hinge['passed']:failures.append([d.CARRIER,'Native support occupies the hinge bores',hinge])
    from audit_plate32 import PAD_SUFFIX
    mesh = common.trimesh.load_mesh(exports/f'{d.CARRIER}{common.SOURCE_SUFFIX}')
    pad = common.trimesh.load_mesh(exports/f'{d.CARRIER}{PAD_SUFFIX}')
    solid = checker.q.solid(mesh.vertices, mesh.faces)
    pads = checker.q.solid(pad.vertices, pad.faces)
    xyz = common.local_points(data, offset, objects[d.CARRIER], mesh)
    keep = (labels != 'Prime tower') & ~np.char.startswith(labels, 'Support')
    low, high = np.asarray((solid+pads).bounding_box()).reshape(2, 3)
    keep &= ((xyz >= low-[.55, .55, .4]) & (xyz <= high+[.55, .55, .4])).all(1)
    early = keep & (data[:, 7] <= .401)
    assert early.any(), 'No carrier first-layer paths anchor the pad cleanup check'
    radius = max(.25, float(data[early, 3].max())/2+.001)
    pad_only = pads.slice(.1).offset(radius)-solid.slice(.1).offset(radius)
    pad_centres = (data[:, 7] <= .401) & checker.q._inside(pad_only, xyz[:, :2])
    frame = np.asarray(common.read_json(exports/'manifest.json')['parts'][d.CARRIER]['print_to_assembly'])
    cleaned = {}
    for label in ('external_wire_bus', PLUG_ROUTE):
        route = gaps[d.CARRIER][label]
        args = (checker.q, route, xyz, data[:, 3], data[:, 4], data[:, 5].astype(int), features, frame)
        before = common.route_hits(*args, keep)
        after = common.route_hits(*args, keep & ~pad_centres)
        proof = {'before_pad_cleanup': before, 'after_pad_cleanup': after,
                 'only_excluded': 'Bead centres in labelled pad-only areas at layer tops <= 0.4 mm',
                 'excluded_pad_bead_samples': int((keep & pad_centres).sum()),
                 'permanent_model_guard_mm': radius, 'assumes_audited_support_removed': True,
                 'non_pad_model_and_brim_retained': True, 'physical_cleanup_verified': False,
                 'passed': bool(after['poses_checked'] == len(tuple(route.poses())) and not after['violations'])}
        cleaned[label] = after
        result[d.CARRIER][f'{label} pad cleanup'] = proof
        if label == PLUG_ROUTE:
            base_result['parts'][d.CARRIER]['working_spaces'][label] = after
        if not proof['passed']:
            failures.append([d.CARRIER, f'{label} after pad cleanup', after])

    # The plug approach is outside the printed carrier. Anchor its complete
    # cleaned scan to the actual mounted PCB, not a nearby arbitrary solid.
    scan = cleaned[PLUG_ROUTE]
    anchor = result[d.CARRIER]['clearance_witnesses'][BOARD_ROUTE]
    poses = tuple(gaps[d.CARRIER][PLUG_ROUTE].poses())
    expected = tuple((d.hardware()['plug']+d.hardware()['op1_wire']).translate((0., 0., z))
                     for z in np.linspace(-9., 0., 37))
    error = max(float((a-b).volume()+(b-a).volume()) for a, b in zip(poses, expected))
    row = {'free_air_path': True, 'full_intrusion_poses': len(poses),
           'anchored_by': 'Mounted diagonal OP1 PCB and its white connector; carrier off the rod',
           'board_deposition_anchor_passed': anchor['passed'],
           'maximum_route_pose_error_mm3': error,
           'CAD_entry_overlap_mm3': geometry['clearance_overlap_mm3']['op1_plug_and_lead_from_below_off_rod'],
           'passed': bool(geometry['passed'] and anchor['passed'] and len(poses) == 37
                          and scan['poses_checked'] == 37 and not scan['violations'] and error < .001)}
    result[d.CARRIER]['clearance_witnesses'][PLUG_ROUTE] = row
    if not row['passed']:
        failures.append([d.CARRIER, PLUG_ROUTE, 'Unanchored or obstructed plug entry', row])

    # The DFRobot PCB moves in free air above the key carrier. Its printed
    # anchors are the bracket's two checked posts, not the carrier below it.
    scan = base_result['parts'][d.CARRIER]['working_spaces'][LEGACY_CONNECTOR]
    loading = result[d.BRACKET]['clearance_witnesses']['DFRobot PCB and connector-pin loading']
    posts = base_result['parts'][d.BRACKET]['critical_material']
    post_pass = all(posts[f'DFRobot post and neck {side}']['minimum_layer_fraction']>=.9 for side in (-1, 1))
    row = result[d.CARRIER]['clearance_witnesses'][LEGACY_CONNECTOR]
    row.update(free_air_path=True, anchored_by='DFRobot bracket loading route and both deposited retaining posts',
               bracket_loading_anchor_passed=loading['passed'], post_material_passed=post_pass,
               passed=bool(geometry['passed'] and loading['passed'] and post_pass
                           and scan['poses_checked']==29 and not scan['violations']))
    if row['passed']:
        failures = [f for f in failures if not (f[0]==d.CARRIER and f[1]==LEGACY_CONNECTOR
                    and f[2]=='empty/misplaced or obstructed clearance witness')]

    # Preserve the smaller original measurement rather than hiding its edge
    # underfill. The critical checks above cover the whole reinforced path:
    # contact pad -> pusher -> root stock -> original bracket floor.
    mesh = common.trimesh.load_mesh(exports/f'{d.BRACKET}{common.SOURCE_SUFFIX}')
    solid = checker.q.solid(mesh.vertices, mesh.faces)
    xyz = common.local_points(data, offset, objects[d.BRACKET], mesh)
    inv = np.linalg.inv(np.asarray(common.read_json(exports/'manifest.json')['parts'][d.BRACKET]['print_to_assembly']))[:3]
    direct = d.pusher() ^ (d.old.bracket()-d.old_pusher_space()-d.switch_relief())
    normal = common.model_mask(labels)
    diagnostic = common.load_checker().material_coverage(checker.q, checker.start_audit,
        direct.transform(inv)^solid, xyz[normal], data[normal,3], data[normal,4], data[normal,7])
    result[d.BRACKET]['pusher_load_path'] = {
        'critical_regions': ['diagonal switch pusher', 'pusher to root bond', 'pusher root stock',
                             'pusher root-to-floor bond', 'pusher brace bond'],
        'basis': 'Complete nominal solids and interfaces; no inset or lower material threshold',
        'original_direct_subregion': diagnostic,
        'direct_subregion_scope': 'Subset of the larger reinforced floor interface, not the complete load-path section',
        'pusher_to_root_overlap_mm3': geometry['bonds']['pusher_to_root_mm3'],
        'physical_strength_verified': False,
    }
    connected = pusher_connectivity(checker,data,xyz,normal & (data[:,6]==owners[d.BRACKET]),
        {name:material[d.BRACKET][name].transform(inv)^solid for name in
         ('diagonal switch pusher','pusher brace bond','pusher to root bond','pusher root stock','pusher root-to-floor bond')})
    result[d.BRACKET]['pusher_load_path']['all_layer_connectivity'] = connected
    if not connected['passed']:
        failures.append([d.BRACKET,'Pusher load path has a disconnected deposited layer',connected])
    return result, failures


def audit(archive, scratch):
    common.design, common.preparation = d, plate42
    common.KEY, common.BRACKET = d.CARRIER, d.BRACKET
    previous_regions = d.BATTERY.h18.regions
    owners = native_support_owners(archive)
    layer_module = common.load_checker().audit.start_audit
    original_layers = layer_module.inspect

    def native_layers(*args, **kwargs):
        # Both support owners use one empty 0.2 mm layer. The legacy helper
        # defaults to 0.24 mm for non-carrier parts and would miss these feet.
        kwargs['gap'] = .2
        return original_layers(*args, **kwargs)

    def battery_regions(name):
        if name != 'Battery_End_Door':
            return previous_regions(name)
        p = d.DOOR
        return {'tongue_slit': d.box(
            p['tongue_root_x_mm']+.05, p['window_x_mm'][0]-.05,
            p['y_mm'][0]-1., p['y_mm'][1]+1.,
            p['tongue_z_mm'][1]+.05, p['tongue_z_mm'][1]+p['slit_mm']-.05)}

    with patch.object(common, 'routes', side_effect=base_routes), \
         patch.object(common, 'extra_checks', side_effect=extra_checks), \
         patch.object(common, 'make_support_check', side_effect=lambda record,solid,layout:
                      make_support_check(record,solid,layout,owners)), \
         patch.object(layer_module, 'inspect', side_effect=native_layers), \
         patch.object(common, 'support_removal_grid', side_effect=support_removal_grid), \
         patch.object(d.BATTERY.h18, 'regions', side_effect=battery_regions):
        result = common.audit(archive, scratch)
    result['r42_deposition_checks'] = result.pop('r38_deposition_checks')
    result['checker_sha256'] = common.digest(Path(__file__))
    renamed = json.dumps(result).replace(BOARD_ROUTE, BOARD_LABEL)
    renamed = renamed.replace(LEGACY_CONNECTOR, 'DFRobot board and connector operating stroke')
    return json.loads(renamed.replace(LEGACY_LEAD, 'DFRobot Gravity lead operating stroke'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    common.PLOT_DIRECTORY = args.report.resolve().parent
    result = audit(args.archive.resolve(), args.scratch.resolve())
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'passed': result['passed'], 'failures': result['failures']}))
    raise SystemExit(0 if result['passed'] else 1)
