"""R44 native supports/pads with the established actual-command PETG checks."""
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import json
import holder44 as design
import plate42 as upstream

HERE=design.HERE
plate=upstream.plate
previous=upstream.previous
PROJECT,RANGES,MODEL=upstream.PROJECT,upstream.RANGES,upstream.MODEL
command_audit=upstream.command_audit
set_fields=upstream.set_fields
BASE_SUPPORT_BOXES=upstream.support_boxes
LEDGES=tuple((label,(x0,z0+(design.KEY_RAISE_MM if label=='upper left key lip' else 0.),
    x1,z1+(design.KEY_RAISE_MM if label=='upper left key lip' else 0.)),heights)
    for label,(x0,z0,x1,z1),heights in upstream.LEDGES)


def support_boxes(record):
    import numpy as np
    with patch.object(upstream,'LEDGES',LEDGES):
        result=BASE_SUPPORT_BOXES(record)
    inverse=np.linalg.inv(np.asarray(record['print_to_assembly']))[:3]
    for side,members in design.finger_rest_paths().items():
        # The new crosswise rounded row prints as a roof. Select its real
        # geometry, not an assumed height, so Studio can back both spans.
        branch=design.h33.rounded_run(members['middle branch'],radius=design.RIB_RADIUS)
        branch ^= design.finger_rests()[side]['shape']
        bounds=np.asarray(branch.transform(inverse).bounding_box()).reshape(2,3)
        bounds[0]-=(.15,.15,.05);bounds[1]+=(.15,.15,.35)
        result.append((f'{side} middle finger branch',bounds.tolist()))
    return result


def stage_parts(*args,**kwargs):
    with patch.object(upstream,'design',design):return upstream.stage_parts(*args,**kwargs)


def configure_layout(*args,**kwargs):
    with patch.object(upstream,'design',design),patch.object(upstream,'LEDGES',LEDGES),patch.object(upstream,'support_boxes',support_boxes):
        upstream.configure_layout(*args,**kwargs)
    # Solid infill only around actual load-bearing joins, rather than
    # filling every hollow part to compensate for sparse joining layers.
    import project22
    import numpy as np
    from zipfile import ZIP_DEFLATED
    path=args[0]
    with ZipFile(path) as archive:files={n:archive.read(n) for n in archive.namelist()}
    from xml.etree import ElementTree as ET
    config=json.loads(files[PROJECT])
    # A wall generator is a process setting. Use it for the whole carrier
    # job, including the unchanged guard roots affected by the new branches.
    config.update(wall_generator='arachne',min_bead_width='60%',wall_distribution_count='2')
    files[PROJECT]=json.dumps(config,indent=2).encode()
    settings=ET.fromstring(files[plate.MODEL_SETTINGS]);model=ET.fromstring(files[MODEL])
    names=previous.names(settings)
    carrier=next(o for o in settings.findall('object') if names[o.get('id')]==design.CARRIER)
    manifest=plate.read_json(path.parent/'build-source/exports/manifest.json')
    frame=np.linalg.inv(np.asarray(manifest['parts'][design.CARRIER]['print_to_assembly']))[:3]
    identifier=max(int(o.get('id')) for o in model.findall('./{*}resources/{*}object'))+1
    joins={**design.seat_bonds(),**design.guard_web_interfaces()}
    for label,shape in joins.items():
        if label.startswith('R44 ') and 'bond' not in label:
            # Apply variable-width walls to each complete new member. A
            # dilated member-shaped selector avoids filling its large
            # enclosing box (and the neighbouring lightweight frame).
            selected=design.union(shape.translate(v) for v in ((0.,0.,0.),
                (.3,0.,0.),(-.3,0.,0.),(0.,.3,0.),(0.,-.3,0.),(0.,0.,.3),(0.,0.,-.3)))
            mesh=selected.transform(frame).to_mesh()
            modifier=upstream.trimesh.Trimesh(vertices=mesh.vert_properties[:,:3],faces=mesh.tri_verts,process=False)
        else:
            bounds=np.asarray(shape.transform(frame).bounding_box()).reshape(2,3)
            bounds[0]-=.25;bounds[1]+=.25
            modifier=upstream.trimesh.creation.box(bounds=bounds)
        project22.studio.p19.add_mesh_part(model,carrier,modifier,
            identifier,'modifier_part',f'R44 solid join - {label}',
            (('sparse_infill_density','100%'),('wall_loops','4'),
             ('wall_generator','arachne'),('min_bead_width','60%'),('wall_distribution_count','2'),
             ('outer_wall_line_width','0.4'),('inner_wall_line_width','0.4'),
             ('internal_solid_infill_line_width','0.4')))
        identifier+=1
    files[MODEL]=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    files[plate.MODEL_SETTINGS]=ET.tostring(settings,encoding='utf-8',xml_declaration=True)
    with ZipFile(path,'w',ZIP_DEFLATED) as archive:
        for n,value in files.items():archive.writestr(n,value)


def make(output):
    output.mkdir(parents=True,exist_ok=True)
    assert not any(output.iterdir())
    selected={n for g in plate.read_json(HERE/plate.BOM)['groups'].values() for n in g['parts']}
    clips=tuple(sorted(n for n in selected if n.startswith(design.CLIP)))
    assert len(selected)==9 and len(clips)==2 and 'Grove_Touch_Bracket' not in selected
    origins={n:v for n,v in previous.pads.ORIGINS.items() if n in selected}
    origins.update({design.BRACKET:(109.,120.),clips[0]:(18.,24.),clips[1]:(35.,24.)})
    assert set(origins)==selected
    plate.BRACKET,plate.CLIPS=design.BRACKET,clips
    plate.LOCAL_PADS=(plate.KEY,plate.BRACKET,*clips)
    plate.ORIGINS,plate.BRIM_WIDTH=origins,6
    plate.stage_parts,plate.configure_layout=stage_parts,configure_layout
    plate.build(HERE,output,plate.FLASHFORGE_PROFILE,False,True)
    target=output/'R44-Complete-A1-mini-PETG-layout.3mf'
    report=plate.read_json(output/'print-checks.json')
    with ZipFile(target) as archive:config=json.loads(archive.read(PROJECT))
    manifest=plate.read_json(output/'build-source/exports/manifest.json')
    report.update(layout_sha256=plate.digest(target),driver_sha256=plate.digest(Path(__file__)),
        recipe_source_sha256=plate.digest(previous.BASE),
        effective_filament_settings={k:config[k] for k in report['effective_filament_settings']},
        support_enforcers=support_boxes(manifest['parts'][design.CARRIER]),
        bracket_support_enforcers=upstream.bracket_support_boxes(manifest['parts'][design.BRACKET]),
        physical_success_verified=False)
    (output/'print-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    return target
