#!/usr/bin/env python3
"""Render the exported meshes, rather than a separate illustrative design."""
import json
import numpy as np
import trimesh
import cad

def render():
    out = cad.HERE / 'exports'
    v = cad.load('verify_and_render', cad.HERE.parent / 'carbon-rod-holders')
    fig = v.plt.figure(figsize=(16, 10), facecolor='#f5f4ef')
    for col, (option, label) in enumerate(cad.OPTIONS.items()):
        carrier = trimesh.load_mesh(out / ('Carrier_' + option + '-assembly.stl'))
        refs = cad.references(option)
        for row, loaded in enumerate([True, False]):
            objects = [(carrier, '#249da2')]
            for name, shape in refs.items():
                if name in ['pcb','usb','wire'] or (not loaded and name != 'rod'): continue
                color = '#303741' if name == 'rod' else '#718096' if name == 'battery' else '#404955' if name.endswith('_socket') else '#e2e5e9'
                objects.append((cad.mesh(shape), color))
            ax = fig.add_subplot(2, 3, row * 3 + col + 1)
            y0 = -67 if option == 'lower' else -23
            v.draw(ax, objects, np.array([[-38,y0,-13],[38,62,21]]))
            ax.set_title(label if loaded else 'Printed frame · ' + option, fontsize=14, color='#162635', loc='left')
    fig.suptitle('Five keys, close to the original carbon tube', fontsize=23, fontweight='bold', color='#162635', x=.035, ha='left', y=.985)
    fig.text(.035,.935,'R4 · Complete slide-on rings · Flat socket seats · Three battery positions · Unchanged separate XIAO holder',fontsize=12,color='#425365')
    fig.text(.035,.035,'DIMENSIONAL PRINT PROTOTYPES. Community switch/socket CAD checked against Kailh drawings; keycaps are illustrative.\nRemove print supports before assembly. Physical fit, key travel, comfort and strength remain untested.',fontsize=11,color='#744722')
    fig.subplots_adjust(left=.01,right=.99,top=.90,bottom=.10,wspace=.025,hspace=.1)
    fig.savefig(out/'Battery-options.png',dpi=150); v.plt.close(fig)
    scene = trimesh.Scene()
    for option in cad.OPTIONS:
        m = trimesh.load_mesh(out / ('Carrier_' + option + '-assembly.stl'))
        m.apply_translation(([0,90,180][list(cad.OPTIONS).index(option)],0,0))
        scene.add_geometry(m,node_name='Carrier_'+option)
    tip=trimesh.load_mesh(out/'XIAO_Rod_Holder-assembly.stl');tip.apply_translation((235,0,0));scene.add_geometry(tip,node_name='XIAO_Rod_Holder')
    scene.export(out/'Printed-parts-reference.glb')
    (out/'render-receipt.json').write_text(json.dumps({'generator_sha256':cad.sha(cad.HERE/'render_options.py'),'manifest_sha256':cad.sha(out/'manifest.json'),'image_sha256':cad.sha(out/'Battery-options.png')},indent=2)+'\n')

if __name__ == '__main__': render()
