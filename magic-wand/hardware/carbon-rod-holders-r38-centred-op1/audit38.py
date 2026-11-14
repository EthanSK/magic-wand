"""Audit R38's deposited paths, including removable support and actual clearances.

No printer commands are sent. Run through geometry_budget.py after plate38's
command guard is available. CAD clearance and support removal remain separate
from physical fit and a real cleanup trial.
"""
from collections import deque
from functools import lru_cache
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import manifold3d as mf
import numpy as np
import trimesh

import holder38 as design
import plate38 as preparation
from audit_plate32 import inspect, load_checker, read_json, digest, SOURCE_SUFFIX, route_hits
from audit36 import clearance_sections

KEY, BRACKET = design.CARRIER, design.BRACKET
PLOT_DIRECTORY = None
PLOT_DIRECTORY = None


def rectangle(bounds):
    x0, y0, x1, y1 = bounds
    return mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


class Poses:
    def __init__(self, shapes):
        self.shapes = tuple(shapes)
        assert self.shapes and all(not s.is_empty() for s in self.shapes)

    def poses(self):
        return iter(self.shapes)


@lru_cache(maxsize=1)
def routes():
    """Every changed working space comes from R38, not a prior offset mount."""
    key, working, fixed, ribs = design.geometry()
    paddle, parts, r = design.bracket(), design.hardware(), design.r
    geometry_record = read_json(design.HERE / 'exports' / 'manifest.json')
    assert geometry_record['source_sha256']['holder38.py'] == digest(Path(design.__file__))
    backup = read_json(design.HERE / 'exports' / 'geometry-checks.json')['checks']['backup_angle_deg']
    angles = np.linspace(design.EARLY_ANGLE, backup, 19)
    # Stop-screw contact is intentional; its landing is checked as material.
    hinge = r.mirrored(r.d.axis_oval(r.AXIS_Y + r.CLICK_SHIFT, r.AXIS_Z,
                                     r.h29.TAB_R + .03, *r.h29.SUPPORT_X))
    installed = design.union(parts[n] for n in ('board', 'sockets', 'housing', 'plug', 'op1_wire'))
    mouse = design.union(parts[n] for n in ('switch', 'terminals', 'plunger'))
    gap = {
        KEY: {
            **working,
            'snap hinge bores': hinge,
            'OP1 mounting screw pilots': design.op1_reliefs()[3],
            'centred OP1 and complete prewired insertion': Poses(
                installed.translate((0., 0., z)) for z in np.linspace(0., design.h32.BOARD_RISE, 33)),
            'OP1 switch insertion': Poses(mouse.translate((0., 0., z)) for z in np.linspace(0., 8., 17)),
            'shifted Grove plug operating stroke': Poses(r.world(design.housing() + design.plug(), a) for a in angles),
            'shifted Grove lead operating stroke': Poses(r.world(design.lead(1.1), a) for a in angles),
            'shifted Grove prewired insertion': Poses(r.world(
                (design.board() + design.housing() + design.plug() + design.components()).translate((0., 0., z)))
                for z in np.linspace(0., design.SERVICE_LIFT, 17)),
        },
        BRACKET: {
            'Grove PCB seat': design.board(),
            'Grove underside socket and plug': design.housing() + design.plug(),
            'Grove underside components': design.components(),
            'Grove lead insertion': Poses(design.lead(1.1, lift=z) for z in np.linspace(0., design.SERVICE_LIFT, 17)),
            'arm squeeze clearance': Poses((r.bent(paddle, a) - paddle) for a in np.linspace(.25, 1., 4)),
            'adjustable stop pilot': design.stop_pilot(.61) ^ design.box(
                design.STOP_X - 1., design.STOP_X + 1., design.STOP_Y - 1., design.STOP_Y + 1.,
                design.STOP_BOSS_BOTTOM + .12, design.STOP_BOSS_BOTTOM + 4.05),
        },
    }
    for i, y in enumerate(design.HOLES, 1):
        gap[BRACKET][f'shifted Grove screw pilot {i}'] = design.cylinder(
            design.GROVE_X, y, design.BOARD_Z - design.grove.PILOT_DEPTH + .25,
            design.BOARD_Z - .07, .61)
    material = {
        KEY: {
            'fixed hinge supports': key ^ r.supports(),
            'OP1 mounting shoulders': key ^ design.op1_seats(),
            'adjustable stop landing': key ^ design.stop_landing(),
            'saddle cheek beside plug': key ^ design.saddle_cheek(),
        },
        BRACKET: {
            'hinge flex arms': paddle ^ r.arms(),
            'adjustable stop boss': paddle ^ design.stop_stock(),
            'switch contact roof': paddle ^ design.box(-1.1, 1.1, r.d.PUSH_Y - 1., r.d.PUSH_Y + 1.,
                                                       design.PUSH_Z, design.BOARD_Z),
            'left hinge-to-screw rail': paddle ^ design.box(
                *design.LEFT_RAIL, design.old.TOUCH_WEB_FRONT, r.ARM_ROOT_Y,
                design.LEFT_RAIL_BOTTOM, design.BOARD_Z),
        },
    }
    for i, y in enumerate(design.HOLES, 1):
        material[BRACKET][f'shifted Grove screw boss {i}'] = paddle ^ design.boss(y)
    for name, rib in ribs.items():
        material[KEY][f'{name} guard root bond'] = fixed ^ rib
    for name, checks in material.items():
        for label, part in checks.items():
            assert not part.is_empty() and part.volume() > .05, (name, label, 'empty material witness')
    return gap, material


def object_data(archive, exports):
    checker = load_checker().audit
    data, features, _, settings, offset, objects, *_ = checker.read_project(archive)
    labels = np.asarray(features)[data[:, 5].astype(int)]
    records = read_json(exports / 'manifest.json')['parts']
    return checker, data, labels, settings, offset, objects, records


def local_points(data, offset, obj, source_mesh):
    shift = (obj['vertices'].max(0) + obj['vertices'].min(0) - source_mesh.bounds.sum(0)) / 2
    return data[:, :3] + offset - shift


def model_mask(labels):
    return ((labels != 'Prime tower') & ~np.char.startswith(labels, 'Support')
            & ~np.char.startswith(labels, 'Brim') & ~np.char.startswith(labels, 'Skirt'))


def footprint(checker, data, xy, mask):
    return checker.start_audit.bead_footprints(checker.q, xy[mask, :2], data[mask, 3])


def support_removal_grid(solid, checker, data, local, model, support, record, *, outward=False):
    """Fragment access through the empty PCB opening, with electronics absent.

    A 0.5 mm grid treats CAD material and deposited walls as solid, removes
    only sacrificial support, then floods from the PCB-side opening. It checks
    access for roughly 0.8 mm fragments, not removal of one intact tower.
    """
    low, high = np.asarray(solid.bounding_box()).reshape(2, 3)
    pts = local[support]
    step, radius = .5, .4
    xs = np.arange(pts[:, 0].min() - 2., pts[:, 0].max() + 2. + step, step)
    ys = np.arange(low[1] - .5, high[1] + 2. + step, step)
    zs = np.arange(.1, data[support, 7].max() + .4, .2)
    xy = np.stack(np.meshgrid(xs, ys, indexing='ij'), -1).reshape(-1, 2)
    free = np.zeros((len(zs), len(xs), len(ys)), dtype=bool)
    support_core = np.zeros_like(free)
    for i, z in enumerate(zs):
        layer = abs(data[:, 7] - (z + .1)) < .051
        occupied = solid.slice(float(z))
        actual = footprint(checker, data, local, model & layer)
        occupied = (occupied + actual).offset(radius, mf.JoinType.Round)
        free[i] = ~checker.q._inside(occupied, xy).reshape(len(xs), len(ys))
        material = footprint(checker, data, local, support & layer).offset(-.2, mf.JoinType.Round)
        # Count obstructed cells too: masking them with free-space here would
        # silently remove the very cells whose access needs verification.
        support_core[i] = checker.q._inside(material, xy).reshape(len(xs), len(ys))
    inverse = np.linalg.inv(np.asarray(record['print_to_assembly']))[:3, :]
    board_opening = design.op1_reliefs()[0].transform(inverse)
    bb = np.asarray(board_opening.bounding_box()).reshape(2, 3)
    # Access is from above the empty OP1 slot, not by crossing a rod-ring wall.
    if outward:
        seeds = free & (xs[None, :, None] < low[0] - .5)
    else:
        seeds = (free & (xs[None, :, None] > bb[0, 0] + radius)
                 & (xs[None, :, None] < bb[1, 0] - radius)
                 & (ys[None, None, :] > high[1] + .5)
                 & (zs[:, None, None] > bb[0, 2]) & (zs[:, None, None] < bb[1, 2]))
    seen = np.zeros_like(free)
    queue = deque(map(tuple, np.argwhere(seeds)))
    for p in queue:
        seen[p] = True
    while queue:
        z, x, y = queue.popleft()
        for a, b, c in ((z-1,x,y),(z+1,x,y),(z,x-1,y),(z,x+1,y),(z,x,y-1),(z,x,y+1)):
            if (0 <= a < len(zs) and 0 <= b < len(xs) and 0 <= c < len(ys)
                    and free[a,b,c] and not seen[a,b,c]):
                seen[a,b,c] = True
                queue.append((a,b,c))
    count = int(support_core.sum())
    reached = int((support_core & seen).sum())
    return {'grid_xy_mm': step, 'grid_z_mm': .2, 'fragment_clearance_radius_mm': radius,
            'exit_seed_cells': int(seeds.sum()), 'support_core_cells': count,
            'reachable_support_core_cells': reached,
            'reachable_fraction': round(reached / max(count, 1), 5),
            'path': ('Break support into small pieces and remove outwards from the left guard.' if outward else
                     'Break support into small pieces and remove through the empty PCB opening before fitting electronics.'),
            'physical_removal_verified': False,
            'passed': bool(seeds.any() and count >= 20 and reached / count >= .98)}


def make_support_check(record, solid, layout):
    boxes = preparation.support_boxes(record)

    def check(data, positions, labels, objects, q, starts):
        # Match the normalized source coordinates used by support_boxes.
        local = positions - objects[KEY]['vertices'].min(0)
        support = np.char.startswith(labels, 'Support')
        model = model_mask(labels)
        checker = load_checker().audit
        rows = []
        if not support.any():
            return {'part': KEY, 'top_gap_mm': .2, 'passed': False, 'failure': 'No generated support deposition'}
        radius = data[support, 3, None] / 2
        lo = (local[support, :2] - radius).min(0)
        hi = (local[support, :2] + radius).max(0)
        bodylo, bodyhi = np.asarray(solid.bounding_box()).reshape(2, 3)
        # Normal support adds a base outside its selected roof. Check its
        # actual bed coordinates and separation from every other part's
        # complete adhesion bounds, rather than an arbitrary STL margin.
        world_lo = (positions[support,:2] - radius).min(0)
        world_hi = (positions[support,:2] + radius).max(0)
        on_bed = bool((world_lo >= 0.).all() and (world_hi <= 180.).all())
        clearances = {}
        for name, bounds in layout['material_bounds_xy_mm'].items():
            if name == KEY:
                continue
            other_lo, other_hi = np.asarray(bounds)
            gap = np.maximum(np.maximum(world_lo-other_hi, other_lo-world_hi), 0.)
            clearances[name] = round(float(np.linalg.norm(gap)), 4)
        tower = labels == 'Prime tower'
        if tower.any():
            radius_tower = data[tower,3,None] / 2
            tower_lo = (positions[tower,:2]-radius_tower).min(0)
            tower_hi = (positions[tower,:2]+radius_tower).max(0)
            gap = np.maximum(np.maximum(world_lo-tower_hi,tower_lo-world_hi),0.)
            clearances['wipe tower'] = round(float(np.linalg.norm(gap)),4)
        else:
            clearances['wipe tower'] = 0.
        clear_of_others = all(gap > .2 for gap in clearances.values())
        for label, (low, high) in boxes:
            low, high = np.asarray(low), np.asarray(high)
            roi = rectangle((low[0], low[1], high[0], high[1]))
            near = ((local[:, :2] >= low[:2] - .45) & (local[:, :2] <= high[:2] + .45)).all(1)
            candidates = model & near & (data[:, 7] >= low[2] + .05) & (data[:, 7] <= high[2] + .25)
            roofs = np.unique(data[candidates, 7])
            layers = []
            for top_value in roofs:
                top = float(top_value)
                roof = model & near & (abs(data[:,7]-top)<.001)
                height = float(np.median(data[roof,4])); bottom = top-height
                roof_poly = footprint(checker,data,local,roof) ^ roi
                previous = model & (abs(data[:,7]-bottom)<.001)
                target = roof_poly-footprint(checker,data,local,previous).offset(.45,mf.JoinType.Round)
                if target.area() < .1:
                    continue
                interfaces = support & near & np.char.startswith(labels, 'Support interface') & (data[:,7] <= bottom+.01)
                probes = []
                for level in np.unique(data[interfaces,7]):
                    layer = interfaces & (abs(data[:,7]-level)<.001)
                    poly = footprint(checker,data,local,layer)
                    overlap = poly ^ target.offset(-.05,mf.JoinType.Round)
                    probes.append({'top_mm':float(level),'samples':int(layer.sum()),
                                   'gap_mm':round(bottom-float(level),4),
                                   'covered_fraction':round((target ^ poly.offset(.25,mf.JoinType.Round)).area()/target.area(),5),
                                   'direct_overlap_mm2':round(overlap.area(),5),
                                   'direct_overlap_bounds_mm':list(overlap.bounds()) if overlap.area()>.001 else None})
                supported = [q for q in probes if .19 <= q['gap_mm'] <= .26]
                best = max(supported,key=lambda q:q['covered_fraction'],default=None)
                contacts = [q for q in probes if q['gap_mm'] < .19 and q['direct_overlap_mm2'] > .015]
                layer_row={'roof_layer_top_mm':round(top,4),'roof_bottom_mm':round(bottom,4),
                           'roof_bead_samples':int(roof.sum()),'overhang_area_mm2':round(target.area(),4),
                           'interface_at_expected_gap':best,'too_close_interfaces':contacts,
                           'passed':bool(best and best['samples']>10 and best['covered_fraction']>=.90 and not contacts)}
                layers.append(layer_row)
            row={'label':label,'enforcer_print_bounds_mm':[low.tolist(),high.tolist()],
                 'roof_bead_samples':int(candidates.sum()),'roof_layers':layers,
                 'passed':bool(layers and all(q['passed'] for q in layers))}
            rows.append(row)
        if PLOT_DIRECTORY is not None:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.patches import Rectangle
            fig, axes = plt.subplots(1,len(boxes),figsize=(15,5),constrained_layout=True)
            for ax,(label,(low,high)),row in zip(axes,boxes,rows):
                low,high=np.asarray(low),np.asarray(high)
                z=next((q['roof_layer_top_mm'] for q in row['roof_layers']),float(low[2]+.25))
                rm=model & (abs(data[:,7]-z)<.001)
                sm=support & (data[:,7]>=z-.65) & (data[:,7]<=z-.19)
                ax.scatter(local[sm,0],local[sm,1],s=2,c='#169b72',label='Support/interface below roof')
                ax.scatter(local[rm,0],local[rm,1],s=2,c='#242833',label='Model at roof layer')
                ax.add_patch(Rectangle(low[:2],*(high[:2]-low[:2]),fill=False,ec='#d93436',lw=1.5))
                ax.set(xlim=(low[0]-2,high[0]+2),ylim=(low[1]-2,high[1]+2),
                       xlabel='Print X (mm)',ylabel='Print Y (mm)',title=f'{label} · roof top {z:.2f} mm')
                ax.set_aspect('equal');ax.legend(fontsize=7);ax.grid(alpha=.2)
            PLOT_DIRECTORY.mkdir(parents=True,exist_ok=True)
            fig.savefig(PLOT_DIRECTORY/'audit38-support-projection.png',dpi=160)
            plt.close(fig)
        removal = {}
        for label, mask, outward in (
                ('central openings', support & (local[:,0] >= 12.), False),
                ('outer finger guard', support & (local[:,0] < 12.), True)):
            removal[label] = (support_removal_grid(solid,checker,data,local,model,mask,record,outward=outward)
                              if mask.any() else {'passed':False,'failure':'Expected support group absent'})
        return {'part': KEY, 'top_gap_mm': .2, 'support_samples': int(support.sum()),
                'support_print_xy_bounds_mm': [lo.tolist(), hi.tolist()],
                'support_bed_bounds_mm': [world_lo.tolist(), world_hi.tolist()],
                'inside_bed': on_bed, 'other_part_adhesion_gaps_mm': clearances,
                'interfaces': rows, 'removal_access': removal,
                'passed': bool(on_bed and clear_of_others and all(r['passed'] for r in rows)
                               and all(r['passed'] for r in removal.values()))}
    return check


def material_diagnostics(checker, data, xyz, model, target):
    """Expose nominal-edge versus inner-core loss without waiving either failure."""
    rows = []
    for top in np.unique(data[:, 7]):
        layer = model & (abs(data[:, 7] - top) < .001)
        if not layer.any():
            continue
        section = target.slice(float(top) - float(np.median(data[layer, 4])) / 2)
        if section.area() < .1:
            continue
        x0,y0,x1,y1=section.bounds()
        near = layer & ((xyz[:, :2] >= [x0-.6,y0-.6]) & (xyz[:, :2] <= [x1+.6,y1+.6])).all(1)
        printed=footprint(checker,data,xyz,near)
        cores={}
        for inset in (0., .1, .2):
            core=section.offset(-inset,mf.JoinType.Round) if inset else section
            area=core.area()
            if area < .03:
                cores[str(inset)]={'area_mm2':round(area,5),'measurable':False}
                continue
            coverage=(core ^ printed).area()/area
            connected=max(((core ^ p).area()/area for p in printed.decompose()),default=0.)
            cores[str(inset)]={'area_mm2':round(area,5),'measurable':True,
                               'coverage_fraction':round(coverage,5),
                               'single_piece_fraction':round(connected,5)}
        rows.append({'layer_top_mm':round(float(top),4),'print_xy_bounds_mm':list(section.bounds()),
                     'bead_samples':int(near.sum()),'core_insets_mm':cores})
    return {'diagnostic_only':True,'nominal_failure_not_waived':True,
            'inset_purpose':'Show sensitivity to edge underfill; these insets do not change the pass threshold.',
            'worst_nominal_layers':sorted(rows,key=lambda q:q['core_insets_mm']['0.0'].get('coverage_fraction',1.))[:8]}


def extra_checks(archive, exports, base_result):
    checker, data, labels, settings, offset, objects, records = object_data(archive, exports)
    results, failures = {}, []
    all_routes, material = routes()
    for part in (KEY, BRACKET):
        mesh = trimesh.load_mesh(exports / f'{part}{SOURCE_SUFFIX}')
        solid = checker.q.solid(mesh.vertices, mesh.faces)
        xyz = local_points(data, offset, objects[part], mesh)
        inv = np.linalg.inv(np.asarray(records[part]['print_to_assembly']))[:3, :]
        non_support = (labels != 'Prime tower') & ~np.char.startswith(labels,'Support')
        d = data[non_support]; pts = xyz[non_support]
        witness = {}
        for label, region in all_routes[part].items():
            # The generic checker handles the many known Choc/rod volumes;
            # new R38 routes additionally require nearby deposited witnesses.
            if label in design.geometry()[1]:
                continue
            shapes = tuple(region.poses()) if hasattr(region,'poses') else (region,)
            # The generic audit has already checked every operating pose.
            # This second check anchors the empty volume to nearby deposition.
            anchors = shapes if len(shapes)<=3 else (shapes[0],shapes[len(shapes)//2],shapes[-1])
            row = clearance_sections(d, pts, anchors, inv, checker,
                                     witness_width=3.2 if 'lead' in label.lower() else 1.15)
            row['full_intrusion_poses']=len(shapes)
            row['deposition_anchor_poses']=len(anchors)
            if label=='OP1 switch insertion' and not row['layers_with_nearby_deposition']:
                anchor=witness['centred OP1 and complete prewired insertion']
                scan=base_result['parts'][KEY]['working_spaces'][label]
                row['free_air_path']=True
                row['anchored_by']='centred OP1 and complete prewired insertion, including printed mounting shoulders'
                row['passed']=bool(anchor['passed'] and row['layers_checked'] and scan['poses_checked']==len(shapes)
                                   and not scan['violations'] and row['maximum_core_intrusion_mm2']<.015)
            witness[label] = row
            if not row['passed']:
                failures.append([part,label,'empty/misplaced or obstructed clearance witness',row])
        root_rows = []
        normal = model_mask(labels)
        previous = None
        for top in (.2,.4,.6,.8,1.,1.2,1.4,1.6):
            section = solid.slice(top-.1).offset(-.06,mf.JoinType.Round)
            mask = normal & (abs(data[:,7]-top)<.001)
            printed = footprint(checker,data,xyz,mask) ^ section
            # R37 deliberately uses sparse infill above its bottom skin.
            # Audit the structural perimeter rather than requiring solid infill.
            wall = mask & np.isin(labels,('Outer wall','Inner wall'))
            wall_width = float(np.median(data[wall,3])) if wall.any() else 0.
            shell_width = int(settings['wall_loops'])*wall_width
            expected = section-section.offset(-shell_width,mf.JoinType.Round) if shell_width else section
            pieces = printed.decompose()
            coverage = (printed ^ expected).area()/max(expected.area(),1e-8)
            connected = max((p.area() for p in pieces),default=0.)/max(printed.area(),1e-8)
            backing = 1. if previous is None else (printed ^ previous.offset(.45,mf.JoinType.Round)).area()/max(printed.area(),1e-8)
            row={'layer_top_mm':top,'nominal_area_mm2':round(section.area(),4),
                 'expected_perimeter_area_mm2':round(expected.area(),4),'perimeter_width_mm':round(shell_width,4),
                 'model_bead_samples':int(mask.sum()),'coverage':round(coverage,5),
                 'largest_piece_fraction':round(connected,5),'previous_layer_overlap':round(backing,5)}
            row['passed']=bool(expected.area()>.1 and wall.any() and mask.any() and coverage>=.85 and connected>=.90 and backing>=.75)
            root_rows.append(row);previous=printed
        diagnosis={}
        for label, summary in base_result['parts'][part]['critical_material'].items():
            if summary['minimum_layer_fraction'] < .9:
                target=material[part][label].transform(inv) ^ solid
                diagnosis[label]=material_diagnostics(checker,data,xyz,normal,target)
        results[part]={'clearance_witnesses':witness,'early_root_layers':root_rows,
                       'failed_nominal_material_diagnostics':diagnosis}
        if part == KEY:
            supporting = np.char.startswith(labels, 'Support')
            features = checker.read_project(archive)[1]
            occupancy = {}
            for label in ('unloaded_clip_bore', 'centred OP1 and complete prewired insertion',
                          'shifted Grove plug operating stroke', 'shifted Grove lead operating stroke'):
                hit = route_hits(checker.q, all_routes[part][label], xyz, data[:,3], data[:,4],
                                 data[:,5].astype(int), features,
                                 np.asarray(records[part]['print_to_assembly']), supporting)
                occupancy[label] = {'support_bead_hits':hit['violations'],
                                    'examples':hit.get('examples',[]),
                                    'must_remove_before_assembly':bool(hit['violations'])}
            results[part]['temporary_support_in_working_spaces'] = occupancy
            results[part]['clearance_scope'] = 'Permanent model paths only after all audited temporary support is removed; physical cleanup remains unverified.'
        if not all(r['passed'] for r in root_rows):
            failures.append([part,'early roots incomplete or disconnected',root_rows])
    return results, failures


def audit(archive, scratch):
    exports = scratch/'build-source'/'exports'
    checker = load_checker()
    if not callable(getattr(preparation,'command_audit',None)):
        raise RuntimeError('plate38.command_audit is not ready; do not substitute the old temperature checker')
    record = read_json(exports/'manifest.json')['parts'][KEY]
    mesh = trimesh.load_mesh(exports/f'{KEY}{SOURCE_SUFFIX}')
    solid = checker.audit.q.solid(mesh.vertices,mesh.faces)
    layout = read_json(scratch/'print-checks.json')
    with patch.object(checker.project22.studio.p19,'command_audit',side_effect=preparation.command_audit):
        result = inspect(archive,exports,routes,layout,
                         removable_support=make_support_check(record,solid,layout))
    additions, failures = extra_checks(archive,exports,result)
    result['r38_deposition_checks']=additions
    result['failures'].extend(failures)
    result['checker_sha256']=digest(Path(__file__))
    result['geometry_source_sha256']=digest(Path(design.__file__))
    result['support_enforcers']=preparation.support_boxes(record)
    result['clearance_requires_support_removal']=True
    result['physical_fit_verified']=False
    result['physical_support_removal_verified']=False
    result['passed']=not result['failures']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('scratch',type=Path)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    PLOT_DIRECTORY = args.report.resolve().parent
    try:
        result=audit(args.archive.resolve(),args.scratch.resolve())
    except Exception as error:
        args.report.write_text(json.dumps({'passed':False,'incomplete':True,
            'error_type':type(error).__name__,'error':str(error),
            'checker_sha256':digest(Path(__file__))},indent=2)+'\n')
        raise
    args.report.write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']:
        raise SystemExit('R38 deposited-path audit found unresolved failures; see the report.')
