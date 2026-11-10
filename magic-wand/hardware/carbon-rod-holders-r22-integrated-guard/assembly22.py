#!/usr/bin/env python3
"""R22 assembly guide (schema 2) for the shared viewer, from the exported meshes and the checked routes.

Every moving actor follows the same poses that verify22.py checks (socket slides, dog-legs and straight routes from
holder22; the R17 board tilt-and-slide; the R17 keeper route; the R19 door drop and cell entry). Each sample stores a
row-major 3x4 affine matrix for every actor, and each step records the largest rigid CAD overlap of its moving parts
against the exported holder, so a reader can see where a spring or snap is meant to flex. Run after the exports.
Reference geometry (sockets, switches, board, cell, rod, wires) is written to exports/guide/ and labelled illustrative.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import json, math
import numpy as np, manifold3d as mf
import holder22 as h

OUT = h.HERE / 'exports'; GUIDE = OUT / 'guide'; base = h.base; G = h.G; C = h.C
I = [1., 0, 0, 0, 0, 1., 0, 0, 0, 0, 1., 0]


def T(x=0., y=0., z=0.): return [1., 0, 0, float(x), 0, 1., 0, float(y), 0, 0, 1., float(z)]


def M(m):
    m = np.asarray(m, float); return [float(v) for v in m[:3, :4].reshape(-1)]


def compose(a, b):
    A = np.vstack([np.array(a).reshape(3, 4), [0, 0, 0, 1]]); B = np.vstack([np.array(b).reshape(3, 4), [0, 0, 0, 1]]); return M(A @ B)


def key_frame(i, offset=(0., 0., 0.)):
    """Socket/switch local frame -> assembly: rotate about Z by the key rotation, then translate to the key and the offset."""
    (x, y), rot = base.key_positions()[i], base.key_rotations()[i]; c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [c, -s, 0, x + offset[0], s, c, 0, y + offset[1], 0, 0, 1, base.PCB_Z + offset[2]]


def write(name, solid):
    GUIDE.mkdir(parents=True, exist_ok=True); path = GUIDE / (name + '.stl'); h.mesh(solid).export(path); return 'guide/' + path.name


def overlap(a, b): return float((a ^ b).volume())


def step(title, caption, samples, checks=None, duration=None):
    out = {'title': title, 'caption': caption, 'duration': duration or max(1.5, min(6., len(samples) / 12)), 'samples': samples}
    if checks is not None: out['checks'] = checks
    return out


def pad_removal(pose):
    return step('Snip Off the Print Pads',
                'With the part cool, snip across the exposed middle of each narrow tie. Keep the cutter away from the permanent holder and clear the wire openings.',
                [pose], duration=2.5)


def key_module():
    carrier = h.read(OUT / 'Key_Carrier-assembly.stl'); hw = base.seated_hardware(); rod = base.references()['rod']
    files = {'socket': write('choc_hotswap_socket', base.seated_socket()), 'switch': write('choc_switch', hw['switch']), 'rod': write('rod_y', rod)}
    actors = {'carrier': {'label': 'Key holder (R22, built-in guard runners)', 'file': 'Key_Carrier-assembly.stl', 'color': '#29a5b7'},
              'rod': {'label': 'Carbon rod (8 mm, illustrative)', 'file': files['rod'], 'color': '#3b3b3b', 'frame': False}}
    for i in range(5):
        actors[f'socket_{i}'] = {'label': f'Socket {i} (pre-soldered, illustrative)', 'file': files['socket'], 'color': '#c8b04a'}
        actors[f'switch_{i}'] = {'label': f'Switch {i} (illustrative)', 'file': files['switch'], 'color': '#7a6f9b'}
    route = {i: (h.slide_poses(i) if i in G['slide_keys'] else h.dogleg_poses(i) if i in G['dogleg_keys'] else [tuple(p) for p in h.spaces16.socket_route_below()]) for i in range(5)}
    rod_out = T(0, 80, 0); up = (0., 0., 14.)
    state = {'carrier': I, 'rod': rod_out, **{f'socket_{i}': key_frame(i, route[i][0]) for i in range(5)}, **{f'switch_{i}': key_frame(i, up) for i in range(5)}}
    def sample(**changes): return {**state, **changes}
    def checked(i, poses):
        s = h.soldered_socket(i); return {'moving': f'socket_{i} with the stated terminal solder allowance', 'route': 'checked in verify22.py', 'max_overlap_mm3_against_exported_holder': round(max(overlap(carrier, s.translate(tuple(float(v) for v in p))) for p in poses), 4)}
    steps = [pad_removal(sample()), step('Solder the Sockets Off the Holder', 'With the holder off the rod and upside down on the bench, solder each socket\'s two wires outside the holder. Keep solder on the terminal tabs, not above them.', [sample()], duration=2.5)]
    names = {0: 'Lower-Left', 2: 'Lower-Right', 1: 'Middle', 3: 'Upper-Left', 4: 'Upper-Right'}
    for i in G['slide_keys']:
        side = 'left' if base.key_positions()[i][0] < 0 else 'right'
        samples = []
        for p in route[i]: state[f'socket_{i}'] = key_frame(i, p); samples.append(sample())
        steps.append(step(f'Slide In the {names[i]} Socket', f'Hold the socket about 2 mm below its seat and slide it in from the {side} edge, above the thin guard runners, wires trailing outward. Under its seat, lift it straight up so the two bosses enter the backplate.', samples, checked(i, route[i])))
    for group, title, caption in (([1], 'Push Up the Middle Socket', 'Push it straight up from below, beside the rod position. No runner passes under it.'),
                                  (G['dogleg_keys'], 'Push Up the Upper Sockets', 'Bring each socket up about 1 mm away from the rod position, so its inner solder joint passes beside the ring arm. 2 mm below the seat, move it in and press it up.')):
        samples = []
        for j in range(max(len(route[i]) for i in group)):
            for i in group: state[f'socket_{i}'] = key_frame(i, route[i][min(j, len(route[i]) - 1)])
            samples.append(sample())
        steps.append(step(title, caption, samples, {f'socket_{i}': checked(i, route[i]) for i in group}))
    steps.append(step('Tape Every Socket', 'Lay one strip of polyimide tape across each socket and its wires onto the backplate, as on R16. Press the tape ends onto the backplate with a flat tool. Keep pressure off the guard runners. The tape insulates the solder from the rod and holds the socket.', [sample()], duration=3))
    samples = []
    for f in np.linspace(1, 0, 21):
        for i in range(5): state[f'switch_{i}'] = key_frame(i, (0., 0., up[2] * f))
        samples.append(sample())
    sw = [hw['switch'].rotate((0, 0, r)).translate((x, y, base.PCB_Z)) for (x, y), r in zip(base.key_positions(), base.key_rotations())]
    steps.append(step('Press In the Switches', 'Back each socket from below with a finger or flat tool, then press each switch in from above until it clicks into the plate.', samples, {'seated_switch_overlap_mm3': [round(overlap(carrier, s), 4) for s in sw]}))
    samples = []
    for d in np.linspace(80, 0, 33): state['rod'] = T(0, d, 0); samples.append(sample())
    steps.append(step('Slide Onto the Rod', 'Slide the wired holder onto the rod end-first. The rod runs through the two rings behind the lower row; the guard has no ring of its own.', samples))
    steps.append(step('Seated', 'Final position. The index finger rests on the rod between the inner runners; the runners sit under the lower sockets\' outer terminals.', [sample()], duration=2))
    return {'label': 'Key holder and finger guard · R22', 'note': 'Exported R22 key holder with the bought socket and switch models. Socket routes carry R20\'s stated, unmeasured solder-and-wire allowance.', 'actors': actors, 'steps': steps}


def xiao_module():
    body = h.read(OUT / 'XIAO_Rod_Holder-assembly.stl'); keeper = h.read(OUT / 'XIAO_Near_Keeper-assembly.stl'); board = h.h19.board_outline(); rod = base.references()['rod']
    files = {'board': write('xiao_board', board), 'rod': write('rod_y', rod)}
    actors = {'holder': {'label': 'XIAO holder (R20 body, unchanged)', 'file': 'XIAO_Rod_Holder-assembly.stl', 'color': '#29a5b7'},
              'board': {'label': 'XIAO nRF52840 Sense board (official outline, illustrative)', 'file': files['board'], 'color': '#2f7d4f'},
              'keeper': {'label': 'Near keeper (R19, original-compatible)', 'file': 'XIAO_Near_Keeper-assembly.stl', 'color': '#d9822b'},
              'rod': {'label': 'Carbon rod (illustrative)', 'file': files['rod'], 'color': '#3b3b3b', 'frame': False}}
    poses = [np.array(p) for p in h.h18.h17.insertion_poses()]; first = M(poses[0]); route = h.h19.RET['route_travel_mm'] if 'route_travel_mm' in h.h19.RET else 12.
    state = {'holder': I, 'board': compose(T(0, 0, 10), first), 'keeper': T(0, -route, 0), 'rod': T(0, 80, 0)}
    def sample(**c): return {**state, **c}
    prep = pad_removal(sample())
    samples = []
    for f in np.linspace(1, 0, 9): state['board'] = compose(T(0, 0, 10 * f), first); samples.append(sample())
    hits = []
    for p in poses:
        state['board'] = M(p); samples.append(sample()); hits.append(overlap(body, board.transform(np.asarray(p)[:3, :4])))
    steps = [prep, step('Lay In the Board', 'Tilt the near end of the board up about 6 degrees, slide the USB end under the two far fingers, then lower the near end onto its ledges. Side wires stay outside the walls. Underside solder must leave room: see the clearance map in geometry-checks.json.', samples, {'max_board_overlap_mm3': round(max(hits), 4)})]
    samples = []; hits = []
    for d in np.linspace(route, 0, 33):
        state['keeper'] = T(0, -d, 0); samples.append(sample()); hits.append(overlap(body, keeper.translate((0, -float(d), 0))))
    steps.append(step('Slide On the Keeper', 'Check that the board sits flat on its ledges. If solder makes it rock or sit high, stop before fitting the keeper. With the board seated, slide the keeper over the near end until its tongue clicks.', samples, {'max_keeper_overlap_mm3': round(max(hits), 4), 'seated_overlap_mm3': round(hits[-1], 4), 'note': 'Overlap during the slide is the keeper tongue flexing past its tooth (designed); seated overlap is zero.'}))
    samples = []
    for d in np.linspace(80, 0, 33): state['rod'] = T(0, d, 0); samples.append(sample())
    steps.append(step('Slide Onto the Rod', 'Slide the holder onto the rod end-first. USB, camera, antenna and reset stay uncovered.', samples))
    steps.append(step('Seated', 'Board held by the side walls, cheeks and near stops, and kept down by the keeper.', [sample()], duration=2))
    return {'label': 'XIAO holder · R20 body + keeper', 'note': 'Board outline from the official XIAO nRF52840 drawing. Underside solder bumps are not modelled; see the clearance map.', 'actors': actors, 'steps': steps}


def battery_module():
    body = h.read(OUT / 'Battery_Holder-assembly.stl'); door = h.read(OUT / 'Battery_End_Door-assembly.stl'); cell = base.cell_shape(); rod = base.references()['rod']
    spacer = h.read(OUT / 'Battery_Spacer_0p4mm-assembly.stl'); t = spacer.bounding_box()[5] - spacer.bounding_box()[2]; travel = base.P['cell']['manufacturer_max_mm']['length'] + 10
    files = {'cell': write('lp402025_max_envelope', cell), 'rod': write('rod_y', rod)}
    actors = {'holder': {'label': 'Battery holder (R22, slot lead-in)', 'file': 'Battery_Holder-assembly.stl', 'color': '#29a5b7'},
              'spacer': {'label': '0.4 mm cell spacer (optional)', 'file': 'Battery_Spacer_0p4mm-assembly.stl', 'color': '#9aa5ad'},
              'cell': {'label': 'LP402025 cell (manufacturer maximum, illustrative)', 'file': files['cell'], 'color': '#b5523b'},
              'door': {'label': 'End door (R19 standard)', 'file': 'Battery_End_Door-assembly.stl', 'color': '#d9822b'},
              'rod': {'label': 'Carbon rod (illustrative)', 'file': files['rod'], 'color': '#3b3b3b', 'frame': False}}
    state = {'holder': I, 'spacer': T(0, -travel, 0), 'cell': T(0, -travel, t), 'door': T(0, 0, 15), 'rod': T(0, 80, 0)}
    def sample(**c): return {**state, **c}
    prep = pad_removal(sample())
    samples = []; hits = []
    for d in np.linspace(travel, 0, 31): state['spacer'] = T(0, -d, 0); samples.append(sample()); hits.append(overlap(body, spacer.translate((0, -float(d), 0))))
    steps = [prep, step('Optional Spacer', 'If the cell is loose, slide in the thinnest spacer that stops it moving (0.4, 0.6 or 0.8 mm) on the floor first.', samples, {'max_overlap_mm3': round(max(hits), 4)})]
    samples = []; hits = []
    for d in np.linspace(travel, 0, 31): state['cell'] = T(0, -d, t); samples.append(sample()); hits.append(overlap(body, cell.translate((0, -float(d), float(t)))))
    steps.append(step('Insert the Cell', 'Insert the cell through the door end, non-lead end first. The leads trail out through the centre opening. Shown sitting on the 0.4 mm spacer.', samples, {'max_overlap_mm3_rigid_max_envelope': round(max(hits), 4)}))
    samples = []; hits = []
    for dz in np.linspace(15, 0, 61): state['door'] = T(0, 0, dz); samples.append(sample()); hits.append(overlap(body, door.translate((0, 0, float(dz)))))
    steps.append(step('Drop In the Door', 'Push the door straight down into its two slots until the centre tooth clicks under the lip. R22 has a longer lead-in at the slot tops, so the tooth is pushed aside more gradually. If it is still too stiff, use the trial door, which has a shallower tooth.', samples,
                      {'max_overlap_mm3': round(max(hits), 4), 'seated_overlap_mm3': round(hits[-1], 4), 'note': 'Overlap near the bottom is the catch tooth flexing over the lip (designed snap), not a clash.'}))
    samples = []
    for d in np.linspace(80, 0, 33): state['rod'] = T(0, d, 0); samples.append(sample())
    steps.append(step('Slide Onto the Rod', 'Slide the holder onto the rod end-first.', samples))
    steps.append(step('Seated', 'Cell held by the walls and teeth without pressure; door latched.', [sample()], duration=2))
    return {'label': 'Battery holder · R22', 'note': 'The cell is drawn at the manufacturer maximum envelope.', 'actors': actors, 'steps': steps}


def cable_module():
    clip = h.read(OUT / (C['name'] + '-assembly.stl')); w = C['axial_width_mm']; r = C['conductor_od_mm'] / 2; cx = C['centres_mm']; mouth = cx + C['cable_bore_mm'] / 2 + C['cable_wall_mm']
    rod = h.cyl(C['rod_bore_mm'] / 2 + .05, -20, 22)
    files = {'rod': write('rod_z', rod), 'wire': write('wire_1p5', h.cyl(r, -14, 16))}
    actors = {'clip': {'label': '12-wire cable clip (R22)', 'file': C['name'] + '-assembly.stl', 'color': '#29a5b7'},
              'rod': {'label': 'Carbon rod (illustrative)', 'file': files['rod'], 'color': '#3b3b3b', 'frame': False}}
    centres = h.wire_centres()
    for i in range(len(centres)): actors[f'wire_{i}'] = {'label': f'Wire {i + 1} (1.5 mm stated envelope)', 'file': files['wire'], 'color': '#c0392b' if i in (0, 1) else '#222222' if i < 7 else '#e0a030', 'frame': False}
    entry_x = mouth + 4
    waiting = [T(entry_x + 2 * (i // 5), 2 * (i % 5), 0) for i in range(len(centres))]
    offset = T(0, 0, 24)
    state = {'clip': offset, 'rod': I,
             **{f'wire_{i}': compose(offset, pose) for i, pose in enumerate(waiting)}}
    def sample(**c): return {**state, **c}
    prep = pad_removal(sample())
    samples = []
    for d in np.linspace(24, 0, 25):
        offset = T(0, 0, d)
        state['clip'] = offset
        for i, pose in enumerate(waiting): state[f'wire_{i}'] = compose(offset, pose)
        samples.append(sample())
    steps = [prep, step('Slide the Clip Onto the Rod',
                        'Align the rod loop with a free rod end and slide the clip to position. Feed the wires through the slit in the second loop.',
                        samples, duration=2.5)]
    # Demonstrate the last wire with the other eleven already in the packed positions.
    # A rigid animation of all twelve following the same entrance would pass through seated wires.
    for i, (x, y) in enumerate(centres[1:], start=1): state[f'wire_{i}'] = T(x, y, 0)
    seat_x, seat_y = centres[0]
    assert seat_y == 0 and all(x <= seat_x for x, _ in centres[1:])
    wire_gap = min(math.dist(centres[0], point) for point in centres[1:]) - 2 * r
    assert wire_gap >= 0, wire_gap
    samples, slit = [], []
    conductor = mf.Manifold.cylinder(w + 2, r, r, 48)
    for x in np.linspace(entry_x, seat_x, 61):
        state['wire_0'] = T(x, 0, 0)
        samples.append(sample())
        slit.append(overlap(clip, conductor.translate((x, 0, -1))))
    assert max(slit) < .001, max(slit)
    steps.append(step('Feed a Wire Through the Slit', 'Feed the flexible wires one at a time and move them aside to make room. This shows the last 1.5 mm wire entering with the rest already packed in the 7 mm loop.', samples,
                      {'max_wire_overlap_with_clip_mm3': round(max(slit), 4), 'min_gap_to_packed_wires_mm': round(wire_gap, 4)}, duration=4))
    steps.append(step('Seated', 'All twelve wires inside the loop. The clip guides the harness; it is not strain relief.', [sample()], duration=2))
    return {'label': 'Cable clip · 12 wires', 'note': 'Clip frame: rod axis along Z, printed flat. Wire positions follow the stated 12 x 1.5 mm packing in parameters.json.', 'actors': actors, 'steps': steps}


def validate(guide):
    assert guide['schema_version'] == 2 and guide['units'] == 'mm' and guide['modules']
    for name, mod in guide['modules'].items():
        assert mod['label'] and mod['actors'] and mod['steps'], name
        for st in mod['steps']:
            assert st['title'] and st['caption'] and st['duration'] > 0 and st['samples'], (name, st.get('title'))
            for s in st['samples']:
                for a in mod['actors']: assert len(s[a]) == 12 and all(math.isfinite(v) for v in s[a]), (name, a)
        for a, rec in mod['actors'].items():
            assert 'file' in rec and (OUT / rec['file']).exists(), (name, a)


def main(target=None, require_fresh_exports=True):
    target = target or (Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / 'assembly-guide.json')
    man = json.loads((OUT / 'manifest.json').read_text())
    src = h.key_carrier(); exp = h.read(OUT / 'Key_Carrier-assembly.stl'); drift = float((src - exp).volume() + (exp - src).volume())
    assert drift < .05 or not require_fresh_exports, ('Exports are older than the CAD source: regenerate the exports first', drift)
    guide = {'schema_version': 2, 'units': 'mm', 'revision': h.LOCAL['revision'],
             'sources': {'generator_sha256': h.sha(Path(__file__)), 'holder22_sha256': h.sha(h.HERE / 'holder22.py'), 'parameters_sha256': h.sha(h.HERE / 'parameters.json'), 'manifest_sha256': h.sha(OUT / 'manifest.json'),
                         'assembly_mesh_sha256': {n: h.sha(OUT / (n + '-assembly.stl')) for n in man['plate_parts']}, 'key_carrier_export_vs_source_drift_mm3': round(drift, 5)},
             'modules': {'key': key_module(), 'xiao': xiao_module(), 'battery': battery_module(), 'cable': cable_module()},
             'physical_fit_verified': False}
    validate(guide); target.write_text(json.dumps(guide, separators=(',', ':')) + '\n')
    print(json.dumps({n: {s['title']: s.get('checks') for s in m['steps'] if s.get('checks')} for n, m in guide['modules'].items()}, default=str)[:3000], flush=True)


if __name__ == '__main__':
    main()
