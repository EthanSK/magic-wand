#!/usr/bin/env python3
"""Build/slice exactly the carrier and sensor using the preserved PETG recipe."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import zipfile
import xml.etree.ElementTree as ET
import trimesh
import cad
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--scratch', type=Path, required=True)
    p.add_argument('--slice', action='store_true')
    a = p.parse_args()
    source = cad.HERE.parent / 'printed-loop-wand/shard-tube-r2'
    builder = cad.load_previous('print_projects', source)
    settings = builder.settings()
    settings.update(enable_support='0', support_type='normal(auto)', support_on_build_plate_only='1',
                    layer_height='0.2', wall_loops='3', brim_type='outer_only', brim_width='3')
    builder.settings = lambda: settings
    out = cad.HERE / 'exports'
    manifest = json.loads((out / 'manifest.json').read_text())
    parts = []
    for name, record in manifest['parts'].items():
        mesh = trimesh.load_mesh(out / (name + '-assembly.stl'))
        parts.append(dict(name=name, **record, assembly_vertices=mesh.vertices.tolist(), assembly_faces=mesh.faces.tolist()))
    layout = out / 'Holder-pair-layout.3mf'
    # Wider five-key carrier needs a new plate placement, not a scaled model.
    builder.make(list(manifest['parts']), [(70, 100), (175, 100)], layout, {'parts': parts})
    with zipfile.ZipFile(layout) as archive:
        files = {n: archive.read(n) for n in archive.namelist()}
    config = ET.fromstring(files['Metadata/model_settings.config'])
    for obj in config.findall('object'):
        if any(m.get('key') == 'name' and m.get('value') == 'Key_Battery_Carrier' for m in obj.findall('metadata')):
            ET.SubElement(obj, 'metadata', key='brim_type', value='no_brim')
    files['Metadata/model_settings.config'] = ET.tostring(config)
    with zipfile.ZipFile(layout, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    receipt = {'project': layout.name, 'sha256': cad.sha(layout), 'generator_sha256': cad.sha(Path(__file__)),
               'builder_sha256': cad.sha(source / 'print_projects.py'), 'physical_print_verified': False, 'parts': list(manifest['parts'])}
    if a.slice:
        scratch = a.scratch.resolve()
        (scratch / 'tmp').mkdir(parents=True, exist_ok=True)
        cfg = source / 'print-settings'
        cmd = ['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio', '--datadir', str(scratch / 'bambu-data'),
               '--debug', '2', '--load-settings', str(cfg / 'machine.json') + ';' + str(cfg / 'process.json'),
               '--load-filaments', str(cfg / 'filament.json'), '--orient', '0', '--arrange', '0', '--slice', '0',
               '--export-3mf', 'Holder-pair-sliced.3mf', '--outputdir', str(scratch), str(layout)]
        with (scratch / 'slice.log').open('w') as log:
            subprocess.run(cmd, cwd=scratch, stdout=log, stderr=subprocess.STDOUT, check=True,
                           env={**os.environ, 'TMPDIR': str(scratch / 'tmp')})
        result = json.loads((scratch / 'result.json').read_text())
        assert result['return_code'] == 0
        receipt['slice'] = result
        receipt['warnings'] = [p['warning_message'] for p in result['sliced_plates'] if p.get('warning_message')]
        target = out / 'Holder-pair-sliced.3mf'
        target.write_bytes((scratch / target.name).read_bytes())
        receipt['sliced_project_sha256'] = cad.sha(target)
    (out / 'print-checks.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt.get('warnings', []))
