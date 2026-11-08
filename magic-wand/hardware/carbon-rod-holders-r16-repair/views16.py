#!/usr/bin/env python3
"""Render the exact exported R16 meshes: per-part overviews, the assembled stack and plan views."""
import json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import holder16 as h

OUT = h.HERE / 'exports'


def add(ax, m, colour, alpha=.95):
    ax.add_collection3d(Poly3DCollection(m.triangles, facecolor=colour, edgecolor='none', alpha=alpha))


def frame(ax, lo, hi):
    centre = (lo + hi) / 2; half = max(hi - lo) * .55
    ax.set(xlim=(centre[0] - half, centre[0] + half), ylim=(centre[1] - half, centre[1] + half), zlim=(centre[2] - half, centre[2] + half))
    ax.set_box_aspect((1, 1, 1)); ax.set_xlabel('X mm'); ax.set_ylabel('rod Y mm'); ax.set_zlabel('Z mm')


def part_overviews(manifest):
    images = {}
    refs = h.references()
    for name in manifest['parts']:
        m = trimesh.load_mesh(OUT / (name + '-assembly.stl'))
        fig = plt.figure(figsize=(15, 5))
        views = [(28, -65, 'Top / tip side'), (-28, -115, 'Underside / handle side'), (12, -90 + 180, 'Rear end on the bed')]
        for i, (elev, azim, title) in enumerate(views, 1):
            ax = fig.add_subplot(1, 3, i, projection='3d')
            add(ax, m, '#29a5b7')
            if name == 'Key_Carrier':
                for k in range(5):
                    add(ax, h.mesh(refs[f'key_{k}_switch']), '#c0392b', .5); add(ax, h.mesh(refs[f'key_{k}_socket']), '#8e44ad', .6)
                    add(ax, h.mesh(refs[f'key_{k}_cap']), '#dfedec', .25)
            if name == 'Battery_Holder':
                add(ax, h.mesh(refs['cell']), '#f1c40f', .35); add(ax, h.mesh(h.battery_gate()), '#e67e22', .8)
            if name == 'XIAO_Rod_Holder':
                add(ax, h.mesh(refs['pcb']), '#2ecc71', .45); add(ax, h.mesh(refs['usb']), '#7f8c8d', .5); add(ax, h.mesh(refs['wire']), '#af4a3c', .4)
            if name != 'Battery_End_Gate':
                add(ax, h.mesh(h.tube_y(3.5, 4, m.bounds[0][1] - 4, m.bounds[1][1] + 4)), '#2c3e91', .25)
            lo, hi = m.bounds; frame(ax, lo, hi); ax.view_init(elev, azim); ax.set_title(title)
        fig.suptitle(name + ' | exact exported assembly mesh (blue); bought references translucent; rod in dark blue')
        fig.tight_layout(); target = OUT / (name + '-overview.png'); fig.savefig(target, dpi=120); plt.close(fig)
        images[target.name] = h.sha(target)
    return images


def plan_views(manifest):
    """Carrier plan and side silhouettes with the inferred caps, plus the cage cross-section with the cell."""
    m = trimesh.load_mesh(OUT / 'Key_Carrier-assembly.stl'); refs = h.references()
    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    ax = axes[0][0]
    ax.add_collection(PolyCollection(m.triangles[:, :, :2], facecolor='#8ba5b5', edgecolor='none', alpha=.25))
    for i, (x, y) in enumerate(h.key_positions()):
        bb = refs[f'key_{i}_cap'].bounding_box()
        ax.add_patch(plt.Rectangle((bb[0], bb[1]), bb[3] - bb[0], bb[4] - bb[1], facecolor='#dfedec', edgecolor='#174e59', lw=1.5))
        sb = refs[f'key_{i}_socket'].bounding_box()
        ax.add_patch(plt.Rectangle((sb[0], sb[1]), sb[3] - sb[0], sb[4] - sb[1], fill=False, edgecolor='#8e44ad', lw=1, ls='--'))
        ax.text(x, y, str(i + 1), ha='center', va='center', color='#174e59')
    ax.axhspan(-4, 4, color='#2c3e91', alpha=.0)
    ax.axvspan(-4.2, 4.2, color='#2c3e91', alpha=.08)
    ax.set(xlim=(-32, 32), ylim=(-12, 30), title='Key carrier plan: inferred caps, sockets dashed, rod band shaded', xlabel='X mm', ylabel='toward tip (+Y) mm'); ax.set_aspect('equal'); ax.grid(alpha=.2)
    ax = axes[0][1]
    ax.add_collection(PolyCollection(m.triangles[:, :, [1, 2]], facecolor='#8ba5b5', edgecolor='none', alpha=.18))
    cap = refs['key_1_cap'].bounding_box()
    ax.add_patch(plt.Rectangle((cap[1], cap[2]), cap[4] - cap[1], cap[5] - cap[2], fill=False, edgecolor='#c0392b', ls='--'))
    ax.axhspan(-4, 4, color='#2c3e91', alpha=.08)
    ax.set(xlim=(-12, 30), ylim=(-8, 20), title='Side silhouette: rounded finger nose at the front, rings at mid and tip', xlabel='Y mm', ylabel='Z mm'); ax.set_aspect('equal'); ax.grid(alpha=.2)
    # Front nose section at the middle key (exact mesh section)
    ax = axes[1][0]
    section = m.section(plane_origin=[0, 0, 0], plane_normal=[1, 0, 0])
    if section is not None:
        for e in section.discrete:
            ax.plot(e[:, 1], e[:, 2], color='#174e59', lw=1)
    ax.axhspan(-4, 4, color='#2c3e91', alpha=.08)
    ax.set(xlim=(-12, 30), ylim=(-8, 14), title='Exact YZ section at X=0: nose rounds, middle socket space, mid ring, rear ring', xlabel='Y mm', ylabel='Z mm'); ax.set_aspect('equal'); ax.grid(alpha=.2)
    # Battery cross-section with the cell max envelope
    ax = axes[1][1]
    b = trimesh.load_mesh(OUT / 'Battery_Holder-assembly.stl')
    section = b.section(plane_origin=[0, 2.0, 0], plane_normal=[0, 1, 0])
    if section is not None:
        for e in section.discrete:
            ax.plot(e[:, 0], e[:, 2], color='#174e59', lw=1)
    cb = refs['cell'].bounding_box(); rb = refs['cell_reserve'].bounding_box()
    ax.add_patch(plt.Rectangle((cb[0], cb[2]), cb[3] - cb[0], cb[5] - cb[2], facecolor='#f1c40f', alpha=.4, edgecolor='#b7950b'))
    ax.add_patch(plt.Rectangle((rb[0], rb[2]), rb[3] - rb[0], rb[5] - rb[2], fill=False, edgecolor='#b7950b', ls='--'))
    ax.add_patch(plt.Circle((0, 0), 4.0, fill=False, edgecolor='#2c3e91'))
    ax.set(xlim=(-16, 16), ylim=(-7, 14), title='Battery cage XZ section at Y=2: LP402025 max pack (yellow) in its reserve (dashed)', xlabel='X mm', ylabel='Z mm'); ax.set_aspect('equal'); ax.grid(alpha=.2)
    fig.suptitle('R16 exact exports. Cap size is inferred, not measured; the cell is the manufacturer maximum envelope.')
    fig.tight_layout(rect=[0, .02, 1, .96]); target = OUT / 'layout-views.png'; fig.savefig(target, dpi=120); plt.close(fig)
    return {target.name: h.sha(target)}


def assembled_view(manifest):
    parts = {n: trimesh.load_mesh(OUT / (n + '-assembly.stl')) for n in manifest['parts']}
    refs = h.references()
    battery_y = h.battery_position()
    xiao_y = h.xiao_position()
    rot = trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])
    fig = plt.figure(figsize=(15, 6))
    for i, (elev, azim, title) in enumerate([(25, -60, 'Assembled stack from the tip side'), (-20, -120, 'Underside')], 1):
        ax = fig.add_subplot(1, 2, i, projection='3d')
        add(ax, parts['Key_Carrier'], '#29a5b7')
        bat = parts['Battery_Holder'].copy(); bat.apply_transform(rot); bat.apply_translation((0, battery_y, 0)); add(ax, bat, '#1abc9c')
        gate = parts['Battery_End_Gate'].copy(); gate.apply_transform(rot); gate.apply_translation((0, battery_y, 0)); add(ax, gate, '#e67e22')
        cell = h.mesh(refs['cell']); cell.apply_transform(rot); cell.apply_translation((0, battery_y, 0)); add(ax, cell, '#f1c40f', .4)
        xiao = parts['XIAO_Rod_Holder'].copy(); xiao.apply_translation((0, xiao_y, 0)); add(ax, xiao, '#3498db')
        pcb = h.mesh(refs['pcb']); pcb.apply_translation((0, xiao_y, 0)); add(ax, pcb, '#2ecc71', .5)
        for k in range(5):
            add(ax, h.mesh(refs[f'key_{k}_cap']), '#dfedec', .3)
        rod = h.mesh(h.tube_y(3.5, 4, -40, xiao_y + 40)); add(ax, rod, '#2c3e91', .3)
        lo = np.array([-30, -12, -8]); hi = np.array([30, xiao_y + 26, 20]); centre = (lo + hi) / 2
        ax.set(xlim=(centre[0] - 60, centre[0] + 60), ylim=(lo[1], hi[1]), zlim=(centre[2] - 60, centre[2] + 60)); ax.set_box_aspect((1, (hi[1] - lo[1]) / 120, 1)); ax.view_init(elev, azim); ax.set_title(title)
    fig.suptitle(f'Assembled reference: carrier, battery cage (gate end toward the tip, y={battery_y:.1f}), XIAO holder (y={xiao_y:.1f}); 8 mm end gaps')
    fig.tight_layout(); target = OUT / 'assembled-view.png'; fig.savefig(target, dpi=110); plt.close(fig)
    return {target.name: h.sha(target)}, battery_y, xiao_y


if __name__ == '__main__':
    manifest = json.loads((OUT / 'manifest.json').read_text())
    images = part_overviews(manifest); images.update(plan_views(manifest))
    assembled, battery_y, xiao_y = assembled_view(manifest); images.update(assembled)
    receipt = {'generator_sha256': h.sha(h.HERE / 'views16.py'), 'manifest_sha256': h.sha(OUT / 'manifest.json'),
               'images_sha256': images, 'assembled_positions_mm': {'battery_module_y': battery_y, 'xiao_holder_y': xiao_y},
               'physical_acceptance_verified': False}
    (OUT / 'view-checks.json').write_text(json.dumps(receipt, indent=2) + '\n'); print(images)
