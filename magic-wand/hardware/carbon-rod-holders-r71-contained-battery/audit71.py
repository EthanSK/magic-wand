"""R71 native-path adapter; parent verification, not a physical fit claim.

The R70/R69 audit engines remain immutable. R71 rebuilds the changed battery
gauges, spring measurement and rear-face seam windows at their actual locations.
The pin, key, OP1 and retainer route construction below was extracted from
audit69.routes/audit70.routes because their archived report contracts differ.
— GPT-6.1 Sol
"""
import argparse
import json
from pathlib import Path

import numpy as np

import audit70 as a
import checks71 as c
import design71 as d
import hinge71 as h
import kit71 as k

v, b, a69, a61, a64 = a.v, d.b, a.a69, a.a61, a.a64
OUT = d.OUT


class CurrentHinge:
    """R71 overrides with the unchanged R70 coordinate/fit helper contract."""
    def __getattr__(self, name):
        return getattr(h, name) if hasattr(h, name) else getattr(h.h70, name)


hinge = CurrentHinge()


def bind():
    a69.d, a69.hinge69, a69.kit69, a69.OUT = d, hinge, k, OUT
    a69.RING_PRINT_HEIGHTS = a.RING_PRINT_HEIGHTS
    a69.CAD_REPORTS = c.REPORTS
    a69.op1_routes, a69.routes = op1_routes, routes
    a69.bind()


def op1_routes():
    # This centre is unchanged R70 geometry; all new native beads are scanned.
    best = v.read(d.r70.OUT / 'keys.json')['kept_in_place']['plug_margin_on_the_r69_route_mm']['route']
    x, y = best['centre_world_xy_mm']
    found = {'op1_plug_rises_through_window': [a69.checks69.plug_box(a.PLUG_ROUTE_MARGIN, best['wide_side_yaw_deg']).translate((x, y, float(z))) for z in np.arange(-14., 13.01, .5)],
             'op1_lead_in_channel': [d.r66.lead_solid('route')]}
    for name in ('board', 'sockets', 'housing', 'plug', 'lead'):
        found[f'op1_{name}_lowered_onto_seat'] = [d.r66.drop_route(name, bearing_skin=.20 if name == 'board' else 0.)]
    return found


def spring_gauges():
    x0, x1 = d.INNER_X
    y0, y1 = d.TONGUE_Y
    z0, z1 = d.TONGUE_Z
    return {
        'side_leaf_can_flex': [b.box(x1 + .10, x1 + .40, y0 + .25, y1 - .25, z0 + .20, z1 - .20)],
        'leaf_is_free_of_floor': [b.box(x0 + .15, x1 - .15, y0 + .25, y1 - .25, z0 - d.SLOT + .15, z0 - .15)],
        'leaf_upper_window': [b.box(x0 + .15, x1 - .15, y0 + .25, y1 - .25, z1 + .15, z1 + d.SLOT - .15)],
        'leaf_free_tip': [b.box(x0 + .15, x1 - .15, y0 - d.SLOT + .15, y0 - .15, z0 + .15, z1 - .15)],
    }


def battery_gauges():
    # The spring shoe deliberately interferes with the compliant pouch. Exclude
    # only its stated .21 mm contact strip, not the rigid walls, lips or floor.
    p = b.box(d.PACK_X[0] + .04, d.PACK_X[1] - d.SHOE - .08,
              d.PACK_Y0 + .10, d.BED - .10, d.PACK_Z[0] + .08, d.PACK_Z[1] - .08)
    return {'battery_seated': [p],
            'battery_rear_insertion_and_removal': [p.translate((0, float(y), 0)) for y in np.arange(0, 30.01, .5)],
            **spring_gauges()}


def clip_gauges():
    """R59's bore/mouth test through the full new 2.0 mm height, not 1.4 mm."""
    profile = h.m.chain()
    half = profile.CLIP_SLOT / 2 - .10
    post_bar = b.load(OUT / h.POST_BAR)
    found = {}
    for side, x in (('Left', -b.HOLE_X), ('Right', b.HOLE_X)):
        y, bottom = b.HOLE_Y, b.BOARD_TOP + h.LIFT
        bore = d.mf.Manifold.cylinder(h.CLIP_T + .1, profile.NECK_R - .10, circular_segments=48)
        mouth = b.box(x - half, x + half, y + .2, y + profile.CLIP_TIP + .15,
                      bottom - .05, bottom + h.CLIP_T + .05)
        head = post_bar ^ b.box(x - 2.5, x + 2.5, y - 2.5, y + 2.5,
                                b.BOARD_TOP + h.NECK - .03, b.BOARD_TOP + h.NECK + 3.)
        assert head.volume() > .2
        found['DFR_Clip_' + side] = {
            'post_clip_bore_and_mouth': [bore.translate((x, y, bottom - .05)) + mouth],
            # The frame is pressed down while sliding on. Its free export is
            # LIFT higher, so raise the relative head by that same amount.
            # The guide moves the clip from -8 mm in Y to home. In the
            # clip's frame the head therefore moves from +8 mm to zero.
            'post_head_space_during_clip_insertion': [head.translate((0, float(t), h.LIFT)) for t in np.arange(0, 8.01, .5)],
            **h.clip_voids(side),
        }
    return found


def routes():
    bind()
    groups = a61.gauges()
    a64.audit63.key_routes(groups)
    holder, paddle = groups['Key_Carrier'], groups['Touch_Paddle']
    holder.update(a64.deposited_routes())
    for name in ('board', 'sockets', 'housing', 'plug'):
        holder.pop(name + '_from_above', None)
    holder['seated_wire_outlet'] = [d.r66.hardware()['op1_wire']]
    holder.update(op1_routes())
    for name in ('both_cheeks', 'left_cheek', 'right_cheek'):
        key = 'pin_go_gauge_through_' + name
        holder[key] = [solid.translate(hinge.MOVE) for solid in holder[key]]
    moving = b.load(OUT / h.PADDLE)
    bearing = moving ^ b.box(-hinge.JOURNAL_OUT - .01, hinge.JOURNAL_OUT + .01, h.AXIS - 3.4, hinge.REAR + .01,
                             h.KEEPER_Z - 3.4, h.KEEPER_Z + 3.4)
    holder['barrel_between_cheeks_from_above'] = [bearing.translate((0, 0, float(z))) for z in np.arange(0, 12.1, 1)]
    cable = h.r61.housing() + h.r61.plug() + h.wired_lead()
    rear_clip = h.clip()
    for group in (holder, paddle):
        group['wired_connector_lowering'] = [cable.translate((0, 0, float(z))) for z in np.arange(0, 12.1, .5)]
        group['rear_clip_from_behind'] = [rear_clip.translate((0, float(y), 0)) for y in np.arange(0, 11.1, .5)]
    paddle['pin_go_gauge_through_barrel'] = [hinge.disc(1.60, -hinge.JOURNAL_OUT - .6, hinge.JOURNAL_OUT + .6)]
    paddle.pop('pin_clip_well', None)
    stop = v.read(OUT / 'carrier.json')['hinge']['click_values']['r71']['case_stop_deg']
    legs = moving ^ b.box(-12, 12, -12, 6, 11.5, 17.6)
    groups.setdefault('OP1_Lid_Stop', {})['paddle_far_end_press'] = a69.far_end_poses(legs, stop)
    guide = v.read(OUT / 'assembly-guide.json')
    for name in (d.HOLDER, h.PADDLE, h.LID):
        assert guide['sources']['meshes_sha256'][name] == v.digest(OUT / name)
    retainer = b.load(OUT / h.LID)
    insertion, through_paddle = [], []
    for step in guide['modules']['pin_hinge']['steps']:
        if step['title'] not in ('Fit the OP1 retainer', 'Remove the OP1 retainer'):
            continue
        for sample in step['samples']:
            lid_pose, paddle_pose = np.eye(4), np.eye(4)
            lid_pose[:3] = np.asarray(sample['lid']).reshape(3, 4)
            paddle_pose[:3] = np.asarray(sample['cap']).reshape(3, 4)
            insertion.append(retainer.transform(lid_pose[:3]))
            through_paddle.append(retainer.transform((np.linalg.inv(paddle_pose) @ lid_pose)[:3]))
    assert len(insertion) >= 40
    holder['actual_retainer_insertion_and_removal'] = insertion
    paddle['actual_retainer_insertion_and_removal'] = through_paddle
    for group in groups.values():
        for name in list(group):
            if name.startswith('key_4_'):
                group[name] = [solid.translate(a.SHIFT) for solid in group[name]]
            if name.startswith(('battery_', 'side_leaf_', 'leaf_is_')):
                del group[name]
    holder.update(battery_gauges())
    groups.update(clip_gauges())
    values = v.read(OUT / 'carrier.json')['hinge']['click_values']['r71']
    clips = [h.spring_clip(side, lift, bend) for side in h.CLIPS
             for lift, bend in ((h.LIFT, 0.), (h.LIFT, h.PRESS), (0., h.FOOT))]
    riding = b.load(OUT / h.POST_BAR) + b.union(clips)
    poses = [h.rotate(riding, float(angle)) for angle in np.linspace(
        -values['lift_stop_deg'] + .025, values['case_stop_deg'] - .035, 19)]
    # Include free, fitted and pressed-flat arms. Fitted tips can rise above
    # the free export; the free mesh alone is not their complete envelope.
    for name in ('Key_Carrier', 'OP1_Lid_Stop'):
        groups[name]['new_fasteners_during_lift_and_click'] = poses
    return groups


def spring_opening(points, position):
    assert np.allclose(position[:3, :3], [[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    x0, y0, z0 = position[:3, 3]
    probe = y0 + d.PACK_MID
    chosen = points[(points[:, 0] > x0 + d.PACK_X[0] - 3) & (points[:, 0] < x0 + d.PACK_X[1] + 3)
                    & (abs(points[:, 1] - probe) < points[:, 3] / 2)]
    rows = []
    centre = d.TONGUE_Y[1] - d.LEVER
    for depth in (centre - .8, centre, centre + .8):
        q = chosen[abs(z0 - chosen[:, 2] - depth) < .11]
        dx = np.sqrt(np.maximum(0, (q[:, 3] / 2) ** 2 - (q[:, 1] - probe) ** 2))
        spring = q[:, 0] > x0 + sum(d.PACK_X) / 2
        assert spring.any() and (~spring).any()
        opening = float((q[spring, 0] - dx[spring]).min() - (q[~spring, 0] + dx[~spring]).max())
        rows.append(dict(depth_mm=round(depth, 3), opening_mm=round(opening, 3), nominal_pack_interference_mm=round(d.PACK[0] - opening, 3)))
    assert all(0 < row['nominal_pack_interference_mm'] < .35 for row in rows), rows
    return rows


def battery_regions():
    ox0, ox1 = d.outer_wall_x()
    return {
        'open_pouch_mouth': [d.PACK_X[0] + .3, d.LIP_TOP + .3, d.PACK_X[1] - .3, d.PAD_Z - .3],
        'outer_lip_free_edge': [ox1 + .45, d.LOW - .1, d.PACK_X[0] + d.LIP_W - .1, d.LIP_TOP + .1],
        'inner_lip_free_edge': [d.PACK_X[1] - d.LIP_W + .1, d.LOW - .1, d.INNER_X[0] - .45, d.LIP_TOP + .1],
        'backed_roof_root': [-27.15, d.DECK - .6, -25.7, d.DECK + 1.5],
        'backed_heel_root': [-27.7, d.LOW - 1., -26.4, d.LOW + .7],
    }


def verify_base(folder):
    frame = v.read(folder / 'layout.frame.json')
    row = frame['parts']['Key_Carrier']
    body = b.load(OUT / row['source'])
    pose = np.asarray(row['assembly_to_machine'])
    oriented = pose[:3].copy(); oriented[:2, 3] = 0
    posed = body.transform(oriented)
    panel = row['adhesion_panel']
    # panel_builder returns the holder too. The seam witness must contain only
    # disposable base plastic, or a folded permanent wall counts as attachment.
    base, _, _ = v.base54(posed, v.settings(panel))
    for cut in k.neck_cuts(posed, panel):
        base -= cut
    regions = battery_regions()
    result = v.seam(folder / v.ARCHIVE, frame, body, regions=regions,
                    regional_base=base.translate((*pose[:2, 3], 0)), max_layers=25)
    areas = result['regional_joint_area_mm2']
    free = ('open_pouch_mouth', 'outer_lip_free_edge', 'inner_lip_free_edge')
    roots = ('backed_roof_root', 'backed_heel_root')
    report = dict(archive_sha256=v.digest(folder / v.ARCHIVE), regions=regions, contacts_mm2=areas,
                  passes=bool(all(areas[n] < .05 for n in free) and all(areas[n] > .4 for n in roots)))
    v.write(folder / 'battery-base.json', report)
    assert report['passes'], report


def audit(folder):
    bind()
    for name in c.REPORTS:
        report = v.read(OUT / name)
        assert report['passes'] and report['carrier_sha256'] == v.digest(OUT / d.HOLDER), name
    a69.mounts(folder)
    verify_base(folder)
    prior = d.r70.OUT / 'print-mechanisms'
    ref = v.read(prior / 'joint.json')
    assert ref['archive_sha256'] == v.digest(prior / v.ARCHIVE)
    area = ref['current']['regional_joint_area_mm2']['all_base_contacts']
    # Keep R70's accepted full-height reference and bounds. R71 moves two fin
    # roots, so summed contact at the holder face is not the neck's section.
    # sections71 separately measures BOTH actual necks of each changed fin.
    accepted = v.read(prior / 'r69-base-reference.json')
    old = d.r69.OUT / 'print-mechanisms'
    assert accepted['archive_sha256'] == v.digest(old / v.ARCHIVE)
    assert accepted['frame_sha256'] == v.digest(old / 'layout.frame.json')
    assert accepted['seam_layers'] == 25
    bound = accepted['regional_joint_area_mm2']['all_base_contacts']
    assert bound == ref['reference_area_mm2']
    v.write(folder / 'r70-base-reference.json', dict(archive_sha256=ref['archive_sha256'], r70_holder_face_area_mm2=area,
                reference_area_mm2=bound, report_sha256=v.digest(prior / 'joint.json'),
                accepted_reference_sha256=v.digest(prior / 'r69-base-reference.json'),
                method='Unchanged full-height acceptance band from the fitted R70 audit; actual new break sections measured separately in mechanical-sections.json.',
                physical_strength_verified=False))
    a61.audit(folder, k.parts, OUT, expected_names=k.COMPLETE, route_builder=routes, spring_probe=spring_opening,
              base_minima=dict(a61.MINIMA), expected_fin_count=len(k.CARRIER_TIES), seam_layers=25,
              seam_reference_area_mm2=bound)
    fit = v.read(folder / 'fit.json'); fit['guide_sha256'] = v.digest(OUT / 'assembly-guide.json')
    fit['adapter_sha256'] = v.digest(__file__)
    v.write(folder / 'fit.json', fit)
    fin = v.read(folder / 'fin-design.json'); fin['removal'] = v.read(OUT / 'base.json')['release']
    fin['revision'] = 'R71'
    v.write(folder / 'fin-design.json', fin)
    seat = a69.printed_seat_report(folder, render=True)
    assert seat['passes'], seat
    seat['audited_revision'] = 'R71'
    seat['plot_label_aliases'] = {'R69': 'R71 current audited archive'}
    v.write(folder / 'printed-seat.json', seat)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    audit(parser.parse_args().folder)
