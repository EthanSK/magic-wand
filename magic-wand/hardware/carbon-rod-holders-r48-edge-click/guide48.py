"""Export the measured R48 assembly and its removal animation from the selected print.

Under the geometry lease: guide48.py SCRATCH COMPLETE_PLATE. After the complete
delivery has passed, guide48.py --register makes it selectable and current.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
PREVIOUS = HERE.parent / 'carbon-rod-holders-r47-bottom-click'
ASSEMBLY = HERE.parent / 'carbon-rod-holders/assembly'
LABEL = 'R48 lower-edge click — fit trial'
sys.path.insert(0, str(ASSEMBLY))


def read(path):
    return json.loads(path.read_text())


def publish_cleanup_inputs(source):
    """The viewer reads the helper meshes from the actual complete plate."""
    target = OUT / 'complete-plate'
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.suffix == '.stl' or path.name in (
                'frame.json', 'shelf-cad.json', 'rear-shelf-cad.json', 'candidate-audit.json',
                'recess-support-removal.json'):
            dest = target / path.name
            if dest.resolve() != path.resolve():
                shutil.copyfile(path, dest)
    return target


def update_steps(guide, checks, g, where, yaw):
    """Keep both click demonstrations consistent with the illustrated screw setting."""
    import numpy as np
    import hinge48
    modules = guide['modules']
    dfr = modules['dfr']
    steps = {step['title']: step for step in dfr['steps']}
    h = g.h
    for module, prefix in ((dfr, ''), (modules['whole'], 'keys_')):
        for name, label in (
                ('board', f'OP1 PCB at {yaw} with two mounting holes'),
                ('plug', 'Harness plug fitted before lowering the board'),
                ('plunger', "OP1 plunger near the touch board's lower edge")):
            module['actors'][prefix + name]['label'] = label
    dfr['note'] = (f'The OP1 plunger sits {where}, {h.q.LEVER:.2f} mm from the hinge. '
                   'Press near the three-key end. Check that the switch clicks, stops and springs back '
                   'once the bought board is fitted.')
    modules['key']['note'] = ('Fit the outer Choc switches and caps. In the DFRobot view, fit the centre '
                              'board, its two clips and the OP1 click switch.')
    modules['finger_rest']['note'] = ('The rounded beams support your finger beneath the keys. Check for '
                                      'support remnants where your finger rests.')
    modules['snap_hinge']['note'] = (
        'Pinch the two outer orange arms until their tabs clear the hinge holes. '
        'The short prong between the arms limits how far you can pinch them.')
    modules['whole']['note'] = ('The DFRobot click assembly, XIAO, battery and 12-wire clip share the rod. '
                                'Wire lengths between holders are illustrative.')
    steps['Lower the OP1 Board']['caption'] = (
        'With the holder off the rod, plug the three-wire harness into the white socket on the OP1. '
        'Feed the free wire ends down through the oblong slot in line with the plug. '
        f'Lower the plugged-in board onto its two seats at {yaw}. The outer keys can stay fitted.')
    steps['Touch, Click and Release']['caption'] = (
        f"Press near the lower edge of the gold pad. The bracket meets the OP1 plunger {where}. "
        'Check that the underside pusher lands on the centre of the switch, clicks before the stops touch and springs back freely when you lift your finger.')
    for mark in dfr['annotations']:
        if mark['actor'] == 'electrode':
            mark.update(title='Click position under the touch board',
                        point=[h.q.PLUNGER_XY[0], h.q.PUSH_Y, h.r.electrode().bounding_box()[5]])
    for mark in modules['snap_hinge']['annotations']:
        if mark['actor'] == 'cap':
            mark['point'][0] = -(hinge48.SEATED_SHOULDER + hinge48.PIN_LENGTH)
            mark['point'][1] = h.r.AXIS_Y
        elif mark['actor'] == 'carrier':
            mark['point'][1] = h.r.AXIS_Y + h.r.CLICK_SHIFT

    # assembly42 animates adjustment but resets to the original screw pose on
    # its second click. Use two measured stop rows, including the second limit.
    settings = checks['stop_settings']
    initial = settings[len(settings) // 2]
    adjusted = min((row for row in settings if row['turns_out'] < initial['turns_out']),
                   key=lambda row: abs(row['turns_out'] - (initial['turns_out'] - .25)))
    difference = initial['turns_out'] - adjusted['turns_out']
    steps['Set the OP1 Stop Screw']['caption'] = (
        'Fit the M2 × 4 stop screw head-down. Turn it fully in, then back it out '
        f"{initial['turns_out']:.2f} turns for the setting shown.")
    steps['Adjust the Stop Screw']['caption'] = (
        f"For more travel, turn the screw in slightly. The animation shows {difference:.2f} turns. "
        'Turn it out if the switch presses too far after the click.')

    def screw(angle, turns, lift):
        return g.up.at((0., 0., -turns * g.d.PITCH), angle=angle, lift=lift)

    start = dfr['steps'].index(steps['Adjust the Stop Screw'])
    for step in dfr['steps'][start:-1]:
        samples = step['samples']
        for i, sample in enumerate(samples):
            t = i / max(1, len(samples) - 1)
            turns = adjusted['turns_out']
            lift = 0.
            if step is steps['Adjust the Stop Screw']:
                turns = initial['turns_out'] - t * difference
                lift = 8.
            elif step is steps['Pinch and Lower It Back']:
                lift = (1. - t) * 8.
            sample['adjustment_screw'] = screw(-h.q.REST, turns, lift)
    last = steps['Check the Click Again']['samples']
    angles = np.linspace(-h.q.REST, adjusted['angle_deg'], len(last) // 2)
    for sample, angle in zip(last, [*angles, *angles[::-1]], strict=True):
        for name in g.up.MOVING:
            sample[name] = g.up.at(angle=float(angle))
        sample['adjustment_screw'] = screw(float(angle), adjusted['turns_out'], 0.)
        sample['plunger'] = g.up.lifted(g.I, -h.base.actuator_travel(float(angle)))
    join = steps['Refit the Clips']['samples'][-1]
    for name in (*g.up.MOVING, 'plunger'):
        assert np.allclose(join[name], last[0][name], atol=1e-6)
        assert np.allclose(last[0][name], last[-1][name], atol=1e-6)
    return {'initial_turns_out': initial['turns_out'], 'adjusted_turns_out': adjusted['turns_out']}


def render_views(guide):
    """Two views of the actual assembled actors, with the touch bracket lifted out of the second view."""
    import numpy as np
    from compare46 import render, triangles
    from register_assembly import write_json
    from native48 import digest
    module = guide['modules']['dfr']
    rest = module['steps'][-1]['samples'][-1]
    visible = []
    underneath = []
    board_group = {'cap', 'sensor', 'electrode', 'connector', 'gravity_pins', 'sensor_lead',
                   'clip_left', 'clip_right', 'adjustment_screw'}
    for name, actor in module['actors'].items():
        if 'file' not in actor:
            continue
        matrix = np.eye(4)
        matrix[:3] = np.asarray(rest[name]).reshape(3, 4)
        color = actor.get('color', '#bbbbbb')
        rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        path = guide['modules']['whole']['actors']['keys_cap']['file'] if name == 'cap' else actor['file']
        item = (triangles(OUT / path, matrix), rgb)
        visible.append(item)
        if name not in board_group:
            underneath.append(item)
    # Keycaps are reference geometry supplied by the shared viewer. Ask that
    # exact component composer for its four displayed shapes and seated poses.
    import subprocess
    js = """
        import fs from 'node:fs';
        const {groupKeys}=await import(process.argv[1]);
        const {modules}=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
        const view=groupKeys(modules).views.dfr;
        const end=view.steps.at(-1).samples.at(-1);
        console.log(JSON.stringify(Object.entries(view.actors).filter(([id])=>id.startsWith('keycap_'))
          .map(([id,actor])=>[actor.geometry,actor.color,end[id]])));
    """
    caps=json.loads(subprocess.check_output(['node','--input-type=module','-e',js,
            (ASSEMBLY/'assembly-data.mjs').as_uri(),str(OUT/'assembly-guide.json')],text=True))
    assert len(caps)==4
    for shape,color,pose in caps:
        matrix=np.asarray(pose).reshape(3,4)
        points=np.asarray(shape['vertices'])@matrix[:,:3].T+matrix[:,3]
        item=(points[np.asarray(shape['faces'])],list(bytes.fromhex(color.strip('#'))))
        visible.append(item)
        underneath.append(item)
    for name, items, direction, centre in (
            ('assembled', visible, (.12, -.35, 1.), (0., 11., 11.)),
            ('op1-seat', underneath, (.12, -.35, 1.), (0., 11., 9.))):
        render(items, direction, 9., (900, 640), np.array(centre)).save(OUT / f'R48-{name}.png')
    from hinge_guide48 import render_fit_states
    render_fit_states(guide['modules']['snap_hinge'], OUT)
    write_json(OUT / 'visual-inputs.json', {
        'guide_sha256': digest(OUT / 'assembly-guide.json'), 'views': ['R48-assembled.png', 'R48-op1-seat.png','R48-hinge-fit.png'],
        'physical_fit_verified': False})


def verify_displayed_parts(guide, cap_file, g, inset):
    """Verify that the exported actors put the click, screw and hinge where the CAD did."""
    import numpy as np
    module = guide['modules']['dfr']

    def bounds(name):
        return g.A.trimesh.load_mesh(OUT / module['actors'][name]['file'], process=False).bounds

    plunger_xy = bounds('plunger').mean(axis=0)[:2]
    board_front = bounds('sensor')[0, 1] + g.r.placement(angle=0.)[1, 3]
    displayed_inset = float(plunger_xy[1] - board_front)
    assert abs(displayed_inset - inset) < .001, (displayed_inset, inset)
    assert np.allclose(plunger_xy, g.q.PLUNGER_XY, atol=.001)
    assert np.allclose(bounds('adjustment_screw').mean(axis=0)[:2],
                       (g.base.STOP_X, g.base.STOP_Y), atol=.001)
    actual = g.b.load(OUT / module['actors']['cap']['file'])
    selected = g.b.load(cap_file)
    drift = (actual - selected).volume() + (selected - actual).volume()
    assert abs(drift) < .005, ('Displayed bracket against the native slice input', drift)
    return {'displayed_click_inset_mm': round(displayed_inset, 4),
            'displayed_bracket_vs_layout_input_mm3': round(float(drift), 6)}


def build(scratch, parts, *, preview=False):
    # build48 configures all upstream hardware before any actor is generated.
    import build48
    import guide47 as g
    import hinge_guide48
    import battery_guide48
    import native48
    from register_assembly import write_json
    stage = scratch / 'stage'
    if preview:
        # This independent assembly preview displays checked CAD while a follow-up
        # carrier relief or a native release is still running. Bind every staged
        # solid to its own receipt; the final print has its stronger release gate.
        full = read(stage/'r47-checks.json')
        assert full['r48']['passed']
        for path, sha in full['r48']['source_sha256'].items():
            if path.endswith('.stl'):
                assert native48.digest(stage/path)==sha
    else:
        full = native48.stage_checks(scratch)
        native48.check_plate_inputs(scratch, parts)
        audit = read(parts / 'candidate-audit.json')
        selected = native48.digest(parts / native48.SELECTED)
        guard = read(parts/'guard-bond.json')
        assert guard['passed'] and guard['archive_sha256']==selected, 'The right finger-rest joint must pass on this slice'
        assert audit['screen_passed'] and audit['archive_sha256'] == selected
    current = full['r48']
    frame=read(parts/'frame.json')
    assert frame['geometry_receipt_sha256']==native48.digest(stage/'r47-checks.json'), 'Layout and staged geometry differ'
    inset = current['plunger_inset_from_free_edge_mm']
    assert abs(inset - build48.h.PUSH_FROM_FRONT) < .0001
    where = f"{inset:g} mm in from the touch board's lower edge"
    yaw = f"{abs(current['op1_board_yaw_deg']):g}°"
    groups = read(PREVIOUS / 'complete-assembly.json')['groups']
    write_json(HERE / 'complete-assembly.json', {'revision': 'r48', 'groups': groups})
    checks = dict(full, passed=True, inherited_r44_gates_passed=full['passed'])
    carrier = g.b.load(stage / 'R47-Key-Carrier-assembly.stl')
    with patch.object(g.h, 'HERE', HERE), patch.object(g, 'OUT', OUT), \
            patch.object(g.d, 'carrier', lambda: carrier), patch.object(g.d, 'checks', lambda: checks):
        battery, door = g.export_parts(carrier, checks, parts)
        g.base_guide(checks, battery, door)
    manifest_path = OUT / 'manifest.json'
    manifest = read(manifest_path)
    cassette = battery_guide48.export(OUT, scratch, manifest, g)
    spring = hinge_guide48.export_printed(g, stage, scratch, OUT, manifest)
    manifest['parts'][g.d.CARRIER]['source'] = 'Exact carrier mesh from the checked R48 layout.'
    write_json(manifest_path, manifest)
    target = OUT / 'assembly-guide.json'
    guide = read(target)
    battery_guide48.compose(guide, cassette)
    import contact_guide48
    guide['sources']['pusher_contact_at_guide_limits'] = contact_guide48.overlap(g.h, g.b.load(stage / 'R48-DFRobot_Hole_Bracket-seated.stl'))
    if preview:
        guide['modules'].pop('print_cleanup',None)
        for name in ('key','dfr'):
            guide['modules'][name]['steps'][0].update(title='Remove Print Supports',
                caption='This assembly view shows how the fitted pieces work. The final plate supplies the support-removal steps.')
        guide['sources']['scope']='Assembly preview of the checked hardware. The final plate and its support paths are reviewed separately.'
    else:
        import cleanup48
        guide['sources'].update(cleanup48.compose(guide, publish_cleanup_inputs(parts), OUT))
        guide['sources']['finger_rest_joint_validation_sha256']=native48.digest(parts/'guard-bond.json')
    with patch.object(g, 'WHERE', where), patch.object(g, 'YAW', yaw):
        g.r47_harness(guide)
    settings = update_steps(guide, full, g, where, yaw)
    for name in ('key', 'dfr'):
        guide['modules'][name]['steps'][0]['title'] = 'Remove Print Supports'
    guide['revision'] = HERE.name
    # Sealing updates the final manifest with the selected print. Its digest
    # and this guide's digest belong together in the final evidence file.
    guide['sources'].pop('manifest_sha256', None)
    guide['sources'].update(
        generator_sha256=g.H.sha(Path(__file__)), geometry_receipt_sha256=g.H.sha(stage / 'r47-checks.json'),
        click_inset_mm=inset, hinge_to_plunger_mm=current['hinge_to_plunger_mm'], screw_demo=settings,
        visible_mechanism=verify_displayed_parts(guide, stage / 'R48-DFRobot_Hole_Bracket-seated.stl', g, inset))
    with patch.object(g.up, 'OUT', OUT):
        report = g.up.guide_checks(guide)
    import harness_guide48
    guide['sources']['op1_harness'] = harness_guide48.prepare(guide, g, OUT, carrier)
    spring['installed_morph_weight'] = hinge_guide48.animate(guide, g, spring['free_file'])
    hinge_guide48.show_independent_arms(guide, g, OUT, spring['installed_morph_weight'])
    guide['sources']['hinge_poses'] = spring
    paths = {actor[key] for module in guide['modules'].values() for actor in module['actors'].values()
             for key in ('file', 'morphFile') if key in actor}
    assert all((OUT / name).resolve().is_relative_to(HERE.parents[2]) for name in paths)
    guide['sources']['meshes_sha256'] = {name:g.H.sha(OUT/name) for name in sorted(paths)}
    for module in guide['modules'].values():
        titles = {s['title'] for s in module['steps']}
        assert all(a['step'] in titles for a in module.get('annotations', []) if 'step' in a)
    write_json(target, guide)
    render_views(guide)
    print(json.dumps(report))
    return target


def register():
    import hashlib
    from register_assembly import register_assembly
    guide = OUT / 'assembly-guide.json'
    evidence = read(OUT / 'complete-plate/evidence.json')
    assert hashlib.sha256(guide.read_bytes()).hexdigest() == evidence['guide_sha256']
    assert read(guide)['sources']['selected_native_archive_sha256'] == evidence['selected_archive_sha256']
    register_assembly(guide, 'r48', LABEL, make_current=True, group_keys=True)
    catalog_file=ASSEMBLY/'catalog.json'
    catalog=read(catalog_file)
    if any(v['id']=='r48-review' for v in catalog['versions']):
        from register_assembly import write_json
        catalog['versions']=[v for v in catalog['versions'] if v['id']!='r48-review']
        write_json(catalog_file,catalog)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scratch', type=Path, nargs='?')
    parser.add_argument('parts', type=Path, nargs='?')
    parser.add_argument('--register', action='store_true')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    if args.register:
        register()
    elif args.scratch and args.parts:
        if args.preview:
            import hashlib
            revision=hashlib.sha256((args.scratch/'stage/r47-checks.json').read_bytes()).hexdigest()[:12]
            OUT=HERE/'review'/revision
            target=build(args.scratch.resolve(),args.parts.resolve(),preview=True)
            from register_assembly import register_assembly
            register_assembly(target,'r48-review','R48 assembly preview',group_keys=True)
        else:
            build(args.scratch.resolve(), args.parts.resolve())
    else:
        parser.error('Supply SCRATCH and COMPLETE_PLATE, or --register')
