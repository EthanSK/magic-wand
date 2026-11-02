#!/usr/bin/env python3
"""Build/slice the separate keys, battery and sensor using the preserved PETG recipe."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import zipfile
import xml.etree.ElementTree as ET
import trimesh
import numpy as np
import cad
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--scratch', type=Path, required=True)
    p.add_argument('--slice', action='store_true')
    p.add_argument('--option', choices=list(cad.OPTIONS), default='modular')
    a = p.parse_args()
    source = cad.HERE.parent / 'printed-loop-wand/shard-tube-r2'
    builder = cad.load('print_projects', source)
    settings = builder.settings()
    settings.update(enable_support='1', support_type='normal(auto)', support_on_build_plate_only='0',
                    layer_height='0.2', wall_loops='3', brim_type='outer_only', brim_width='3')
    builder.settings = lambda: settings
    out = cad.HERE / 'exports'
    manifest = json.loads((out / 'manifest.json').read_text())
    parts = []
    names = ['Key_Carrier', 'Battery_Holder', 'Battery_End_Gate', 'XIAO_Rod_Holder']
    for name in names:
        record = manifest['parts'][name]
        # Prepare exactly the final normal STL, including float32 seam cleanup.
        mesh = trimesh.load_mesh(out / (name + '.stl'))
        mesh.apply_transform(np.array(record['print_to_assembly']))
        parts.append(dict(name=name, **record, assembly_vertices=mesh.vertices.tolist(), assembly_faces=mesh.faces.tolist()))
    layout = out / ('Holder-' + a.option + '-layout.3mf')
    layout.unlink(missing_ok=True)
    # Wider five-key carrier needs a new plate placement, not a scaled model.
    builder.make(names, [(50, 135), (125, 130), (175, 130), (210, 100)], layout, {'parts': parts})
    with zipfile.ZipFile(layout) as archive:
        files = {n: archive.read(n) for n in archive.namelist()}
    config = ET.fromstring(files['Metadata/model_settings.config'])
    for obj in config.findall('object'):
        for item in obj.findall('metadata'):
            if item.get('key') == 'enable_support': item.set('value', '1')
        ET.SubElement(obj, 'metadata', key='support_type', value='normal(auto)')
        if any(m.get('key') == 'name' and m.get('value') == 'Battery_Holder' for m in obj.findall('metadata')):
            # A brim would cross the open battery bay. The ladder rails already
            # have bed contact; keep that assembly space clear in the slice.
            ET.SubElement(obj, 'metadata', key='brim_type', value='no_brim')
        if any(m.get('key') == 'name' and m.get('value') == 'Key_Carrier' for m in obj.findall('metadata')):
            ET.SubElement(obj, 'metadata', key='brim_type', value='no_brim')
            for m in obj.findall('metadata'):
                if m.get('key') == 'enable_support': m.set('value', '1')
            ET.SubElement(obj, 'metadata', key='support_type', value='normal(auto)')
    for plate in config.findall('plate'):
        for item in plate.findall('metadata'):
            if item.get('key') == 'plater_name': item.set('value', 'Magic Wand R10 - separate holders')
    # PRINT SUPPORT ONLY: force contact beneath the small socket-floor rim.
    # Automatic supports miss these separate first-layer islands. The normal
    # carrier mesh stays identical to the checked STL; helpers are labelled.
    ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    tag = lambda v: '{' + ns + '}' + v
    model = ET.fromstring(files['3D/3dmodel.model'])
    resources = model.find(tag('resources'))
    ident = max(int(o.get('id')) for o in resources.findall(tag('object'))) + 1
    name = 'Key_Carrier'
    record = manifest['parts'][name]
    inverse = np.linalg.inv(np.array(record['print_to_assembly']))
    z = cad.P['keys']['pcb_z']
    helpers = cad.union([cad.box(x-5.5,x+10.5,y-.7,y+11.7,z-3.7,z-2.9) for x,y in cad.key_positions()])
    mm = cad.mesh(helpers)
    vv = mm.vertices @ inverse[:3,:3].T + inverse[:3,3]
    helper = ET.SubElement(resources, tag('object'), id=str(ident), type='model', name='PRINT SUPPORT ONLY - socket floors')
    mesh = ET.SubElement(helper,tag('mesh')); vertices = ET.SubElement(mesh,tag('vertices')); faces = ET.SubElement(mesh,tag('triangles'))
    for v in vv: ET.SubElement(vertices,tag('vertex'),**{k:format(float(t),'.9g') for k,t in zip('xyz',v)})
    for f in mm.faces: ET.SubElement(faces,tag('triangle'),v1=str(f[0]),v2=str(f[1]),v3=str(f[2]))
    obj = next(o for o in config.findall('object') if any(m.get('key')=='name' and m.get('value')==name for m in o.findall('metadata')))
    root = next(o for o in resources.findall(tag('object')) if o.get('id')==obj.get('id'))
    ET.SubElement(root.find(tag('components')),tag('component'),objectid=str(ident))
    part = ET.SubElement(obj,'part',id=str(ident),subtype='support_enforcer')
    ET.SubElement(part,'metadata',key='name',value='PRINT SUPPORT ONLY - socket floors; remove before assembly')
    files['3D/3dmodel.model'] = ET.tostring(model,encoding='utf-8',xml_declaration=True)
    files['Metadata/model_settings.config'] = ET.tostring(config)
    with zipfile.ZipFile(layout, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    receipt = {'project': layout.name, 'sha256': cad.sha(layout), 'generator_sha256': cad.sha(Path(__file__)),
               'builder_sha256': cad.sha(source / 'print_projects.py'), 'physical_print_verified': False, 'parts': names}
    if a.slice:
        scratch = a.scratch.resolve()
        (scratch / 'tmp').mkdir(parents=True, exist_ok=True)
        cfg = source / 'print-settings'
        process = json.loads((cfg / 'process.json').read_text())
        process.update(enable_support='1', support_type='normal(auto)', support_on_build_plate_only='0')
        process_path = scratch / 'process.json'
        process_path.write_text(json.dumps(process, indent=2) + '\n')
        cmd = ['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio', '--datadir', str(scratch / 'bambu-data'),
               '--debug', '2', '--load-settings', str(cfg / 'machine.json') + ';' + str(process_path),
               '--load-filaments', str(cfg / 'filament.json'), '--orient', '0', '--arrange', '0', '--slice', '0',
               '--export-3mf', ('Holder-' + a.option + '-sliced.3mf'), '--outputdir', str(scratch), str(layout)]
        with (scratch / 'slice.log').open('w') as log:
            subprocess.run(cmd, cwd=scratch, stdout=log, stderr=subprocess.STDOUT, check=True,
                           env={**os.environ, 'TMPDIR': str(scratch / 'tmp')})
        result = json.loads((scratch / 'result.json').read_text())
        assert result['return_code'] == 0
        receipt['slice'] = result
        receipt['warnings'] = [p['warning_message'] for p in result['sliced_plates'] if p.get('warning_message')]
        target = out / ('Holder-' + a.option + '-sliced.3mf')
        target.write_bytes((scratch / target.name).read_bytes())
        receipt['sliced_project_sha256'] = cad.sha(target)
    (out / ('print-checks-' + a.option + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt.get('warnings', []))
