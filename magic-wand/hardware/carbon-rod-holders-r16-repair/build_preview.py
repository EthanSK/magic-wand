#!/usr/bin/env python3
"""Compose the R16 viewer from its checked exports and frozen component references.

The geometry encoder and input controls follow the existing revision viewers. A normal
build leaves the permanent pointer alone; --publish requires a current delivery receipt.
"""
import argparse
import json
import re
import zipfile

import trimesh
import holder16 as h


def build(publish=False):
    out = h.HERE / 'exports'
    page = h.HERE / 'preview/index.html'
    if publish:
        # Publishing is a separate step from inspecting the candidate in its own viewer.
        h.r15.load('check16', h.HERE).check()
        page.write_text(page.read_text().replace('<p hidden><a id="project-file"', '<p><a id="project-file"'))
    manifest = json.loads((out / 'manifest.json').read_text())
    encoder = h.r15.load('build_preview', h.r15.base.HERE)
    data = encoder.data
    geometry = {name: data(trimesh.load_mesh(out / (name + '-assembly.stl')))
                for name in manifest['parts']}
    hardware = h.seated_hardware()
    hardware['socket'] = h.seated_socket()
    geometry.update({name: data(shape) for name, shape in hardware.items()})
    refs = h.references()
    x, y = h.key_positions()[0]
    geometry['cap'] = data(refs['key_0_cap'].translate((-x, -y, -h.PCB_Z)))
    geometry['cell'] = data(h.cell_shape())
    geometry['rod'] = data(h.tube_y(3.5, 4, -.5, .5))
    for name in ['pcb', 'usb', 'wire']:
        geometry[name] = data(refs[name])
    key_bounds = manifest['parts']['Key_Carrier']['bounds_mm']
    base_y = h.battery_position()
    poses = {'two-toward-tip': {'y': base_y, 'direction': 1},
             'three-toward-tip': {'y': base_y - key_bounds[0][1] - key_bounds[1][1], 'direction': 1}}
    project = out / 'R16-A1-mini-PETG.gcode.3mf'
    with zipfile.ZipFile(project) as archive:
        gcode = archive.read('Metadata/plate_1.gcode').decode()
    weight = re.search(r'^; total filament weight \[g\]\s*:\s*([\d.]+)', gcode, re.M)
    assert weight, 'Sliced project has no total weight estimate'
    scene = {'geometry': geometry, 'manifest': manifest, 'parameters': h.P,
             'key_positions': h.key_positions(), 'key_rotations_degrees': h.key_rotations(),
             'battery_poses': poses, 'xiao_y': h.xiao_position(),
             'mass': {'total_g': float(weight[1]), 'source': project.name},
             'sources': {'generator_sha256': h.sha(h.HERE / 'build_preview.py'),
                         'renderer_sha256': h.sha(h.HERE / 'preview/preview.mjs'),
                         'html_sha256': h.sha(page),
                         'geometry_encoder_sha256': h.sha(h.r15.base.HERE / 'build_preview.py'),
                         'manifest_sha256': h.sha(out / 'manifest.json'),
                         'project_sha256': h.sha(project),
                         'assembly_mesh_sha256': {name: h.sha(out / (name + '-assembly.stl'))
                                                  for name in manifest['parts']}}}
    (out / 'review-scene.json').write_text(json.dumps(scene, separators=(',', ':')))
    if publish:
        h.r15.load('publish', h.HERE.parent / 'carbon-rod-holders/preview').publish(h.HERE)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true')
    build(parser.parse_args().publish)
