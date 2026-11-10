#!/usr/bin/env python3
"""Render the R20 exports for review: guard on the key holder, guard sections, and each revised part beside its predecessor.

Only composes exported meshes and reference envelopes; it changes no model. Translucent hardware is illustrative.
"""
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path
import numpy as np, trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import holder20 as h

OUT = h.HERE / 'exports'; h19 = h.h19; base = h.base
load = lambda folder, name: trimesh.load_mesh(folder / f'{name}-assembly.stl')


def add(ax, m, color, alpha=1.):
    ax.plot_trisurf(m.vertices[:, 0], m.vertices[:, 1], m.vertices[:, 2], triangles=m.faces, color=color, alpha=alpha, linewidth=0, antialiased=False, shade=True)


def scene(ax, lo, hi, elev, azim, title=''):
    ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]), zlim=(lo[2], hi[2])); ax.set_box_aspect(np.array(hi) - np.array(lo)); ax.view_init(elev, azim); ax.set_axis_off(); ax.set_title(title, fontsize=11)


def outline(ax, section, style, lw=1., fill=None, flip=False):
    for loop in section.to_polygons():
        q = np.vstack([loop, loop[:1]]); y = -q[:, 1] if flip else q[:, 1]
        if fill: ax.fill(q[:, 0], y, color=fill, alpha=.55, lw=0)
        ax.plot(q[:, 0], y, style, lw=lw)


def shadow(ax, mesh_, title):
    """Looking straight through a part: white is open all the way through."""
    area = lambda p: float((p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]).sum()) / 2
    loops = [np.asarray(p) for p in h.mf.Manifold(h.mf.Mesh(np.asarray(mesh_.vertices, np.float32), np.asarray(mesh_.faces, np.uint32))).project().to_polygons()]
    for loop in sorted(loops, key=lambda p: -abs(area(p))): ax.fill(loop[:, 0], loop[:, 1], color='#29a5b7' if area(loop) > 0 else 'white')
    ax.set_aspect('equal'); ax.set_title(title, fontsize=11); ax.set_xlabel('X mm'); ax.set_ylabel('rod Y mm')


def render():
    figures = {}; guard, key, bat, xiao = (load(OUT, n) for n in ('Finger_Guard', 'Key_Carrier', 'Battery_Holder', 'XIAO_Rod_Holder'))
    def save(fig, name, dpi=110):
        fig.tight_layout(); target = OUT / name; fig.savefig(target, dpi=dpi); plt.close(fig); figures[name] = h.sha(target)
    # Guard on the key holder.
    fig = plt.figure(figsize=(18, 6.5))
    for i, (el, az, title) in enumerate([(-30, -62, 'From below, hand side'), (-62, -90, 'Underside'), (8, -90, 'From the hand, along the rod'), (22, -58, 'From above')], 1):
        ax = fig.add_subplot(1, 4, i, projection='3d'); add(ax, key, '#8fa3c4', .5); add(ax, guard, '#e67e22'); scene(ax, (-31, -12, -12), (31, 30, 14), el, az, title)
    fig.suptitle('R20 Finger_Guard (orange) on the R20 key holder: exported meshes'); save(fig, 'Finger_Guard-overview.png')
    # Guard sections with bought parts and stated allowances.
    G, C = (h.read(OUT / f'{n}-assembly.stl').rotate((90, 0, 0)) for n in ('Finger_Guard', 'Key_Carrier')); B = {k: v.rotate((90, 0, 0)) for k, v in h.bought_parts().items()}; E = {k: v.rotate((90, 0, 0)) for k, v in h.contact_envelopes().items()}
    fig, axes = plt.subplots(3, 3, figsize=(21, 13)); t = np.linspace(0, 2 * np.pi, 100)
    for ax, y in zip(axes.ravel(), [8.3, 7.0, 4.0, 0.0, -2.0, -4.0, -6.0, -7.3, -8.2]):
        outline(ax, C.slice(y), 'b-', .8, '#9ab', True); outline(ax, G.slice(y), 'k-', 1.2, '#e67e22', True)
        for k, v in B.items():
            if k.endswith(('_switch', '_socket')): outline(ax, v.slice(y), 'g-' if 'switch' in k else 'r-', .6, None, True)
        for v in E.values(): outline(ax, v.slice(y), 'm--', .6, None, True)
        ax.plot(4 * np.cos(t), 4 * np.sin(t), 'k:', lw=.8); ax.set_title(f'rod Y = {y} mm'); ax.set_aspect('equal'); ax.set_xlim(-32, 32); ax.set_ylim(-9, 13); ax.grid(alpha=.3)
    fig.suptitle('Sections across the rod. Orange guard, blue-grey key holder, green switches, red sockets, dashed magenta stated solder and wire allowance, dotted 8 mm rod'); save(fig, 'Finger_Guard-sections.png', 70)
    # Key holder: what the windows removed.
    window_counts = json.loads((OUT / 'geometry-checks.json').read_text())['Key_Carrier']['windows_added']
    added = window_counts['under_upper_switch_fronts'] + window_counts['shoulders']
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5)); shadow(axes[0], load(h.R16 / 'exports', 'Key_Carrier'), 'R16 key holder'); shadow(axes[1], key, f'R20 key holder: {added} more arrow windows, {h.K20["ring_bore_mm"]:g} mm rings')
    fig.suptitle('Looking straight through the key holder; white is open all the way through'); save(fig, 'Key_Carrier-windows.png')
    # Battery holder: side view old and new.
    fig = plt.figure(figsize=(15, 6))
    for i, (m, title) in enumerate([(load(h.R19 / 'exports', 'Battery_Holder'), 'R19: 35.6 mm, gap behind the cell stop'), (bat, 'R20: 33.0 mm, end frame is the stop')], 1):
        ax = fig.add_subplot(1, 2, i, projection='3d'); add(ax, m, '#1abc9c'); add(ax, h.mesh(base.cell_shape()), '#f1c40f', .35); scene(ax, (-15, -19, -6), (15, 19, 13), 28, -20, title)
    fig.suptitle('Battery holder, closed end at the right; translucent block is the catalogue-maximum cell'); save(fig, 'Battery_Holder-comparison.png')
    # XIAO holder with board, keeper and components.
    fig = plt.figure(figsize=(15, 6.5)); keeper = load(h.R19 / 'exports', 'XIAO_Near_Keeper'); board = h.mesh(h19.board_outline())
    for i, (m, title) in enumerate([(load(h.R19 / 'exports', 'XIAO_Rod_Holder'), 'R19'), (xiao, 'R20: side walls, far corner cheeks, 3.6 mm far ring')], 1):
        ax = fig.add_subplot(1, 2, i, projection='3d'); add(ax, m, '#29a5b7'); add(ax, keeper, '#e67e22', .85); add(ax, board, '#2ecc71', .45)
        for c in h19.XO['components']: add(ax, h.mesh(h19.component_box(c)), '#7f8c8d', .35)
        scene(ax, (-16, -6, -6), (16, 25, 17), 30, -58, title)
    fig.suptitle('XIAO holder; green board, grey components and orange keeper are references'); save(fig, 'XIAO_Rod_Holder-overview.png')
    receipt = {'generator_sha256': h.sha(Path(__file__)), 'manifest_sha256': h.sha(OUT / 'manifest.json'), 'geometry_sha256': h.sha(OUT / 'geometry-checks.json'), 'images_sha256': figures, 'physical_acceptance_verified': False}
    (OUT / 'view-checks.json').write_text(json.dumps(receipt, indent=2) + '\n'); print(json.dumps(figures), flush=True)


if __name__ == '__main__':
    render()
