#!/usr/bin/env python3
"""Reload final meshes, check five purchased interfaces and render exact CAD."""
from pathlib import Path
import json
import numpy as np
import cad

HERE = cad.HERE
OUT = HERE / 'exports'
v = cad.load_previous('verify_and_render', HERE.parent / 'carbon-rod-holders')
v.HERE = HERE
v.OUT = OUT

def checks():
    key, tip, refs, report = v.checks()
    _, solid = v.read('Key_Battery_Carrier')
    _, sensor = v.read('XIAO_Rod_Holder')
    k, s, b = cad.P['keys'], cad.P['sensor'], cad.P['battery']
    extra = {}
    for i, (x, y) in enumerate(cad.key_positions()):
        entry = cad.rr(13.8, 13.8, .2, k['plate_z'] - 2.2, k['plate_z'] + 15).translate((x, y, 0))
        clips = cad.ds.local_hardware(cad.C)['factory_clips'].translate((x, y, k['plate_z'] + .4))
        extra[str(i)] = {'housing_entry_mm3': v.collision(solid, entry),
                         'clip_capture_mm3': v.collision(solid, clips)}
        assert extra[str(i)]['housing_entry_mm3'] < .002
        assert extra[str(i)]['clip_capture_mm3'] > .1
    # Check bought parts against each other, including cap-to-battery space.
    hardware = {n: o for n, o in refs.items() if n == 'battery' or n.endswith('_cap')}
    separation = {a + ':' + b: v.collision(hardware[a], hardware[b])
                  for i, a in enumerate(hardware) for b in list(hardware)[i + 1:]}
    assert max(separation.values()) < .002
    wire = cad.wire_route()
    report['r3'] = {'five_keys': extra, 'bought_part_separation_mm3': separation,
        'wire_vs_sensor_mm3': v.collision(sensor, wire),
        'wire_vs_tube_mm3': v.collision(cad.tube_y(3.5, 4, -25, 23.4), wire),
        'reversed_usb_approach_mm3': v.collision(sensor, cad.box(-5.2, 5.2, -22.7, -.7, s['board_z'] + .9, s['board_z'] + 4.4)),
        'sensor_stl_identical_to_r2': cad.sha(OUT / 'XIAO_Rod_Holder.stl') == cad.sha(cad.R2 / 'exports/XIAO_Rod_Holder.stl'),
        'upper_key_centres_mm': cad.key_positions()[3:], 'bottom_key_centres_mm': cad.key_positions()[:3],
        'purchased_cap_travel_verified': False,
        'cap_reference_limit': 'Caps are illustrative external envelopes; actual underside and travel remain unmeasured, as in R1/R2.'}
    assert report['r3']['sensor_stl_identical_to_r2']
    assert max(report['r3'][n] for n in ['wire_vs_sensor_mm3', 'wire_vs_tube_mm3', 'reversed_usb_approach_mm3']) < .002
    report['r3_checker_sha256'] = cad.sha(Path(__file__))
    (OUT / 'geometry-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    return key, tip, refs, report

def render(key, tip, refs, report) -> None:
    plt = v.plt
    fig = plt.figure(figsize=(14, 11), facecolor='#f5f4ef')
    titles = ['Five-key carrier | open frame', 'Three below, two above | battery between',
              'XIAO holder | unchanged R2 frame', 'XIAO holder | USB and wire route']
    for i, (title, shape, loaded, sensor) in enumerate(zip(titles, [key, key, tip, tip], [False, True, False, True], [False, False, True, True])):
        objects = [(shape, '#db963f' if sensor else '#249da2')]
        for name, obj in refs.items():
            if sensor != (name in ['pcb', 'usb']):
                if name != 'rod':
                    continue
            if not loaded and name != 'rod':
                continue
            if name == 'rod':
                obj = cad.tube_y(3.5, 4, *((-9, 23.4) if sensor else (-20, 65)))
            color = '#303741' if name == 'rod' else '#6e7888' if name == 'battery' else '#387c52' if name == 'pcb' else '#b6bfcc' if name == 'usb' else '#e2e5e9'
            objects.append((cad.mesh(obj), color))
        if sensor and loaded:
            objects.append((cad.mesh(cad.wire_route()), '#af4a3c'))
        bounds = np.array([[-15, -15, -6], [15, 31, 16]]) if sensor else np.array([[-38, -18, -6], [38, 62, 22]])
        ax = fig.add_subplot(2, 2, i + 1)
        v.draw(ax, objects, bounds)
        ax.set_title(title, fontsize=15, color='#162635', loc='left', pad=6)
    fig.suptitle('Five keys, with the battery in the upper middle gap', fontsize=23, fontweight='bold', x=.045, ha='left', y=.98, color='#162635')
    kg = report['parts']['Key_Battery_Carrier']['solid_PETG_g']
    fig.text(.045, .927, f'R3 carrier CAD estimate {kg:.2f} g | 3 keys below, 2 above | existing lightweight XIAO holder', fontsize=12, color='#425365')
    fig.text(.045, .045, 'DIMENSIONAL PROTOTYPE: battery 22 x 30 x 6 mm and wire bundle 3 mm remain provisional.\nPurchased parts are references, excluded from print files. Physical fit and strength untested.', fontsize=11, color='#744722')
    fig.subplots_adjust(left=.015, right=.985, top=.89, bottom=.10, wspace=.02, hspace=.09)
    fig.savefig(OUT / 'Design-preview.png', dpi=160)
    plt.close(fig)

if __name__ == '__main__':
    render(*checks())
