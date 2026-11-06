#!/usr/bin/env python3
"""Compose the current assembly viewer from exact R14 exports."""
import json
import trimesh
import cad
builder=cad.load('build_preview',cad.base.HERE)
builder.cad=cad
if __name__=='__main__':
    # The inherited renderer reads the select control on its first frame.
    # Derive its initial selection from the same parameters as the CAD,
    # rather than relying on an old first-option default.
    page=cad.HERE/'preview/index.html';html=page.read_text()
    start=html.index('<select id="revision">');end=html.index('</select>',start)
    options=html[start:end].replace(' selected','')
    value=cad.P['assembly']['default_key_orientation']
    options=options.replace(f'value="{value}"',f'value="{value}" selected')
    html=html[:start]+options+html[end:]
    trial=cad.HERE/'exports/trial-Key_Carrier'
    if (trial/'overhang-review.json').exists():
        import qualify
        qualify.qualify(trial)
        html=html.replace('<p hidden><a id="project-file"','<p><a id="project-file"')
    page.write_text(html)
    # R14 owns its changed description. Keep frozen interfaces/geometry
    # encoders shared, but bind the effective renderer and initial controls.
    out=cad.HERE/'exports';manifest=json.loads((out/'manifest.json').read_text())
    data=builder.data
    geometry={name:data(trimesh.load_mesh(out/(name+'-assembly.stl')))for name in manifest['parts']}
    geometry.update({name:data(shape)for name,shape in cad.seated_hardware().items()})
    refs=cad.references()
    geometry['cap']=data(refs['key_1_cap'].translate((0,0,-cad.P['keys']['pcb_z'])))
    geometry['cell']=data(cad.battery_shape());geometry['rod']=data(cad.tube_y(3.5,4,-.5,.5))
    for name in ['pcb','usb','wire']:geometry[name]=data(refs[name])
    geometry['sensor_rod']=data(cad.tube_y(3.5,4,-9,23.4))
    scene={'geometry':geometry,'manifest':manifest,'parameters':cad.P,'key_positions':cad.key_positions(),'mass':None,
           'battery_poses':{orientation:{'y':cad.battery_position(flipped),'direction':1}
               for orientation,flipped in [('three-toward-tip',True),('two-toward-tip',False)]},
           'sources':{'cad_sha256':cad.sha(cad.HERE/'cad.py'),'generator_sha256':cad.sha(cad.HERE/'build_preview.py'),
                      'renderer_sha256':cad.sha(cad.HERE/'preview/preview.mjs'),'html_sha256':cad.sha(page),
                      'geometry_encoder_sha256':cad.sha(cad.base.HERE/'build_preview.py'),
                      'manifest_sha256':cad.sha(out/'manifest.json')}}
    (out/'review-scene.json').write_text(json.dumps(scene,separators=(',',':')))
    cad.load('publish',cad.HERE.parent/'carbon-rod-holders/preview').publish(cad.HERE)
