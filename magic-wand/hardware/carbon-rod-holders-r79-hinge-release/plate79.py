"""Replacement carrier and fresh fittings. Reuse the undamaged R77/R78 touch paddle."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r78-low-battery'))
import plate78 as old
import kit70
import hinge71 as posts
import design79 as design

OUT = HERE / 'exports'
CLIPS = {'DFR_Clip_Left': 'Left', 'DFR_Clip_Right': 'Right'}
LABELS = old.previous.kit.base_plate.COMPLETE - {'Touch_Paddle'}
b = posts.b


def parts():
    # Ethan's easy clips are the flat R59 parts printed through R70. Reuse
    # their files, face-down pose, open mouth and separate pads as one recipe.
    original = {p['name']: p for p in kit70.parts() if p['name'] in CLIPS}
    rows = []
    for row in old.parts():
        name = row['name']
        if name == 'Touch_Paddle':
            continue
        if name in original:
            row = dict(original[name], bed_center=row['bed_center'])
        if name == 'Key_Carrier':
            source = OUT / design.HOLDER
            printer = old.previous.kit.base_plate.printer
            pose = old.previous.kit.base_plate.kit64.PRINT_POSES[name]
            row = dict(row, source=source, panel=design.carrier_panel(row['panel']),
                       assembly_to_print=printer.pose_for(source, *pose))
        row['mesh_reference'] = relpath(row['source'], OUT)
        rows.append(row)
    assert {r['name'] for r in rows} == LABELS and len(rows) == len(LABELS)
    return rows


def flat_clip_check(side, bar, original_bar):
    clip = b.load(posts.R59_CLIPS[side])
    def sweep(stock):
        return np.array([(stock ^ clip.translate((0, -float(t), 0))).volume()
                         for t in np.linspace(0, 8, 81)])
    current, original = sweep(bar), sweep(original_bar)
    # The compliant throat snaps around the post. Compare that engagement
    # to the original pair over the entire slide, including its tight spot.
    extra = (current - original).max()
    neck_lift = posts.NECK - (clip.bounding_box()[5] - clip.bounding_box()[2])
    retained = (bar ^ clip.translate((0, 0, neck_lift + .15))).volume()
    assert abs(current[0]) < .001 and extra < .002 and retained > .1, (current[0], extra, retained)
    return dict(mesh_sha256=sha256(posts.R59_CLIPS[side].read_bytes()).hexdigest(),
                original_and_current_slide_poses=len(current), peak_snap_overlap_mm3=round(current.max(),4),
                maximum_extra_overlap_vs_original_mm3=round(extra,5), seated_overlap_mm3=round(current[0],5),
                available_lift_before_head_mm=round(neck_lift,2), head_capture_probe_mm3=round(retained,4))


def routes():
    groups = old.routes()
    del groups['Touch_Paddle']
    bar = b.load(posts.OUT / posts.POST_BAR)
    profile = posts.m.chain()
    for name, side in CLIPS.items():
        clip = b.load(posts.R59_CLIPS[side])
        x = -b.HOLE_X if side == 'Left' else b.HOLE_X
        y, z = b.HOLE_Y, b.BOARD_TOP
        height = clip.bounding_box()[5] - z
        half = profile.CLIP_SLOT / 2 - .10
        throat = b.box(x-half, x+half, y+.2, y+profile.CLIP_TIP+.15, z-.05, z+height+.05)
        bore = posts.mf.Manifold.cylinder(height+.10, profile.NECK_R-.1, circular_segments=48)
        head = bar ^ b.box(x-2.5, x+2.5, y-2.5, y+2.5, z+posts.NECK-.03, z+posts.NECK+3)
        assert head.volume() > .2
        groups[name] = dict(post_clip_bore_and_mouth=[throat + bore.translate((x,y,z-.05))],
                            post_head_during_slide=[head.translate((0,float(t),0)) for t in np.linspace(0,8,33)])
    clips = b.union([b.load(path) for path in posts.R59_CLIPS.values()])
    values = json.loads((posts.OUT / 'carrier.json').read_text())['hinge']['click_values']['r71']
    for name in ('Key_Carrier', 'OP1_Lid_Stop'):
        groups[name]['new_fasteners_during_lift_and_click'] = [
            posts.rotate(bar + clips.translate((0,0,lift)), float(angle))
            for lift in (0., .8) for angle in np.linspace(-values['lift_stop_deg']+.025, values['case_stop_deg']-.035, 19)]
    return groups


def layout(folder):
    from plate_preview import embed
    folder.mkdir(parents=True, exist_ok=True)
    kit = old.previous.kit.base_plate
    target = folder / 'layout.3mf'
    kit.printer.write_layout(parts(), target, kit.kit64.kit63.plate.plate60.prior.p58.TOWER,
                             'R79 key holder replacement and flat board clips', panel_builder=old.previous.panel_builder)
    embed(target)


def audit(folder):
    base = old.previous.base
    ref = json.loads((old.r77.old.prior.r71.OUT / 'print-mechanisms/r70-base-reference.json').read_text())
    settings = next(row['panel'] for row in parts() if row['name'] == 'Key_Carrier')
    base.audit(folder, parts, OUT, expected_names=LABELS, route_builder=routes, spring_probe=old.spring_opening,
               base_minima=dict(base.MINIMA), expected_fin_count=len(settings['ties']), seam_layers=25,
               seam_reference_area_mm2=ref['reference_area_mm2'])
    fin_path = folder / 'fin-design.json'
    fin = json.loads(fin_path.read_text())
    fin['revision'] = 'R79'
    fin['removal'] = [
        'Support the solid body. Snip each thin rim connection at the marked points.',
        'Peel the sides of the disposable sheet away from the hinge. Leave both pin holes intact.',
    ]
    fin_path.write_text(json.dumps(fin, indent=2) + '\n')
    import release_map79
    release_map79.report(folder, render=False)


def verify():
    source = OUT / design.HOLDER
    carrier = b.load(source)
    prior = b.load(old.OUT / design.HOLDER)
    r = routes()['Key_Carrier']
    # Test each hinge interface against exported surfaces in assembly space.
    # Nominal contact at fitted limits can coincide; it must not worsen.
    names = [k for k in r if 'pin_go_gauge' in k or k in
             ('barrel_between_cheeks_from_above','new_fasteners_during_lift_and_click',
              'wired_connector_lowering','actual_retainer_insertion_and_removal')]
    additions = carrier - prior
    fit = {k: max((additions ^ p).volume() for p in r[k]) for k in names}
    assert len(names) >= 7 and max(fit.values()) < .015, fit
    original_bar = b.load(kit70.OUT / posts.POST_BAR)
    bar = b.load(posts.OUT / posts.POST_BAR)
    clips = {side: flat_clip_check(side,bar,original_bar) for side in CLIPS.values()}
    report = dict(revision='R79', carrier_sha256=sha256(source.read_bytes()).hexdigest(),
                  hinge_interface_additional_overlap_mm3=fit, clips=clips, physical_fit_verified=False, passes=True)
    (OUT / 'fit79.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    action, *args = sys.argv[1:]
    if action == 'verify':
        verify()
    elif action == 'package':
        import package75
        import review79
        folder, reopened = map(Path,args)
        from shutil import copyfile
        import release_map79
        package75.package(folder, reopened, plate=sys.modules[__name__], revision=79, layer_review=review79.inspect,
                          battery_route='battery_rear_insertion_and_removal', kit_name='Replacement-Key-Holder')
        evidence = OUT / 'print-mechanisms'
        for prefix, src in (('', folder), ('reopened-', reopened)):
            copyfile(src / 'release-contacts.json', evidence / (prefix+'release-contacts.json'))
        _, solid, base, stations = release_map79.measure(folder, OUT)
        release_map79.figure(solid,base,stations, OUT/'removing-the-base.png')
    else:
        {'layout': layout, 'audit': audit}[action](Path(args[0]))
