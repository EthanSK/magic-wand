#!/usr/bin/env python3
"""Render R19's exported meshes and the unchanged key carrier for physical review.

Run through the repository geometry runner. This only composes exported geometry and
reference envelopes; it never changes the printable models or their placement.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import holder19 as h

OUT = h.HERE / 'exports'
spec = importlib.util.spec_from_file_location('r16_render_helpers', h.R16 / 'views16.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def load(name: str) -> trimesh.Trimesh:
    return trimesh.load_mesh(OUT / f'{name}-assembly.stl')


def render() -> None:
    manifest = json.loads((OUT / 'manifest.json').read_text())
    names = manifest['plate_parts']
    figures: dict[str, str] = {}
    for name in names:
        part = load(name)
        fig = plt.figure(figsize=(13, 5))
        for index, (elev, azim, label) in enumerate([(27, -62, 'Assembly view'), (-24, 118, 'Opposite / underside')], 1):
            ax = fig.add_subplot(1, 2, index, projection='3d')
            helpers.add(ax, part, '#29a5b7')
            bounds = [part.bounds]
            if name == 'Battery_Holder':
                helpers.add(ax, h.mesh(h.base.cell_shape()), '#f1c40f', .3)
                helpers.add(ax, load('Battery_End_Door'), '#e67e22', .8)
            elif name == 'XIAO_Rod_Holder':
                retainer = load('XIAO_Near_Keeper')
                helpers.add(ax, retainer, '#e67e22', .85)
                bounds.append(retainer.bounds)
                board = trimesh.creation.box(extents=[17.78, 20.955, h.BT])
                board.apply_translation([0, h.S['board_near_end_y_mm'] + 20.955 / 2, h.BZ + h.BT / 2])
                helpers.add(ax, board, '#2ecc71', .3)
                for component in h.XO['components']:
                    helpers.add(ax, h.mesh(h.component_box(component)), '#7f8c8d', .35)
            combined = np.array(bounds)
            helpers.frame(ax, combined[:, 0].min(axis=0), combined[:, 1].max(axis=0))
            ax.view_init(elev, azim)
            ax.set_title(label)
        fig.suptitle(name.replace('_', ' ') + ' — exported mesh; reference hardware translucent')
        fig.tight_layout()
        target = OUT / f'{name}-overview.png'
        fig.savefig(target, dpi=125)
        plt.close(fig)
        figures[target.name] = h.sha(target)

    # The assembly includes the existing key carrier even though this repair plate omits it.
    fig = plt.figure(figsize=(16, 6))
    ax = fig.add_subplot(111, projection='3d')
    key = trimesh.load_mesh(h.R16 / 'exports/Key_Carrier-assembly.stl')
    helpers.add(ax, key, '#536f9b')
    meshes = [key]
    rotation = trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])
    for name in ('Battery_Holder', 'Battery_End_Door'):
        part = load(name)
        part.apply_transform(rotation)
        part.apply_translation([0, h.battery_position(), 0])
        helpers.add(ax, part, '#1abc9c' if name == 'Battery_Holder' else '#e67e22')
        meshes.append(part)
    for name in ('XIAO_Rod_Holder', 'XIAO_Near_Keeper'):
        part = load(name)
        part.apply_translation([0, h.xiao_position(), 0])
        helpers.add(ax, part, '#3498db' if name == 'XIAO_Rod_Holder' else '#e67e22')
        meshes.append(part)
    bounds = np.array([m.bounds for m in meshes])
    lo, hi = bounds[:, 0].min(axis=0), bounds[:, 1].max(axis=0)
    centre = (lo + hi) / 2
    dimensions = (hi - lo) + [15, 15, 15]
    ax.set(xlim=(lo[0]-7.5, hi[0]+7.5), ylim=(lo[1]-7.5, hi[1]+7.5), zlim=(lo[2]-7.5, hi[2]+7.5))
    ax.set_box_aspect(dimensions)
    ax.view_init(27, -60)
    ax.set_axis_off()
    fig.suptitle('R19 assembled reference — existing key carrier, lightweight battery holder, XIAO tray, hoop and near keeper')
    fig.tight_layout()
    target = OUT / 'assembled-view.png'
    fig.savefig(target, dpi=125)
    plt.close(fig)
    figures[target.name] = h.sha(target)
    # What was removed: looking straight down through each holder. White is open all the way through.
    fig, axes = plt.subplots(2, 2, figsize=(11, 10)); r18 = h.h18.HERE / 'exports'
    area = lambda loop: float((loop[:, 0] * np.roll(loop[:, 1], -1) - np.roll(loop[:, 0], -1) * loop[:, 1]).sum()) / 2
    for row, name in zip(axes, h.NEW_PARTS):
        for ax, (rev, folder) in zip(row, (('R18', r18), ('R19', OUT))):
            m = trimesh.load_mesh(folder / f'{name}-assembly.stl'); shadow = h.mf.Manifold(h.mf.Mesh(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32))).project()
            loops = [np.asarray(loop) for loop in shadow.to_polygons()]
            for loop in sorted(loops, key=lambda p: -abs(area(p))): ax.fill(loop[:, 0], loop[:, 1], color='#29a5b7' if area(loop) > 0 else 'white')
            ax.set_aspect('equal'); ax.set_title(f"{rev} {name.replace('_', ' ')}: {float(m.volume):.0f} mm3", fontsize=11); ax.set_xlabel('X mm'); ax.set_ylabel('rod Y mm')
    fig.suptitle('Top-down view through each holder; white is open all the way through'); fig.tight_layout(); target = OUT / 'open-floor-plan.png'; fig.savefig(target, dpi=110); plt.close(fig); figures[target.name] = h.sha(target)
    receipt = {'generator_sha256': h.sha(Path(__file__)), 'manifest_sha256': h.sha(OUT/'manifest.json'),
               'assembly_stl_sha256': {name: h.sha(OUT/f'{name}-assembly.stl') for name in names},
               'unchanged_key_stl_sha256': h.sha(h.R16/'exports/Key_Carrier-assembly.stl'),
               'images_sha256': figures, 'physical_acceptance_verified': False}
    (OUT/'view-checks.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(figures), flush=True)


if __name__ == '__main__':
    render()
