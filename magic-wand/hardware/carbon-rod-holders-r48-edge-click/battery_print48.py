"""Install the checked Micron tray and slider in the two editable Bambu objects."""
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
import trimesh

import compose47 as c
from native48 import digest, read, write

PARTS = {'Battery_Holder', 'Battery_End_Door'}


def inputs(scratch):
    path = scratch / 'battery48/manifest.json'
    manifest = read(path)
    assert manifest['revision'] == 'r48' and manifest['source_sha256'] == digest(Path(__file__).with_name('battery48.py'))
    checks = path.parent / manifest['checks']
    assert digest(checks) == manifest['checks_sha256'] and read(checks)['passed']
    rows = manifest['parts']
    assert set(rows) == PARTS, 'Both pieces of the Micron battery cassette are needed'
    for name,row in rows.items():
        frame = np.asarray(row['print_to_assembly'])
        assert frame.shape == (4,4) and np.allclose(np.linalg.det(frame[:3,:3]), 1.)
        for kind in ('print', 'pad', 'assembly'):
            file = row.get(kind+'_stl')
            if file is not None:
                assert digest(path.parent / file) == row[kind+'_sha256'], (name,file)
        assert row['print_stl'] and row['assembly_stl']
    return path.parent, rows


def install_mesh(node, path):
    # Keep the fully welded canonical triangles. The native vertex audit
    # subsequently checks every triangle after Bambu's own reorder.
    raw = trimesh.load_mesh(path)
    assert raw.is_volume and np.isfinite(raw.vertices).all()
    tag = lambda name: '{'+c.NAMESPACE+'}'+name
    mesh = ET.Element(tag('mesh'))
    vertices = ET.SubElement(mesh, tag('vertices'))
    triangles = ET.SubElement(mesh, tag('triangles'))
    for point in raw.vertices:
        ET.SubElement(vertices, tag('vertex'), **{k:f'{v:.12g}' for k,v in zip('xyz',point)})
    for face in raw.faces:
        ET.SubElement(triangles, tag('triangle'), **{k:str(int(v)) for k,v in zip(('v1','v2','v3'),face)})
    node.remove(node.find('./{*}mesh'))
    node.append(mesh)


def write_project(project, path):
    for entry, key in ((c.MODEL,'model'),(c.SETTINGS,'settings'),(c.RANGES,'ranges')):
        project['files'][entry] = ET.tostring(project[key],encoding='utf-8',xml_declaration=True)
    temp = path.with_suffix('.writing.3mf')
    with ZipFile(temp,'w',ZIP_DEFLATED) as archive:
        for entry, contents in project['files'].items():
            archive.writestr(entry,contents)
    temp.replace(path)


def prepare(template, scratch, output):
    directory,rows = inputs(scratch)
    project = c.read(template)
    by_name = {n:k for k,n in project['names'].items()}
    assert set(by_name) == PARTS
    for name,record in rows.items():
        obj = project['objects'][by_name[name]]
        if name == 'Battery_End_Door':
            # The larger Micron slider's 6-mm brim cleared the old cell but
            # approached the new rear feet. Move it toward unused front space.
            item = next(i for i in project['build'] if i.get('objectid') == by_name[name])
            pose = list(map(float, item.get('transform').split()))
            pose[10] -= 7.
            item.set('transform', ' '.join(f'{v:.12g}' for v in pose))
        components = project['resources'][by_name[name]].find('./{*}components')
        saw = set()
        for part in obj.findall('part'):
            label = c.fields(part)['name']
            identifier = part.get('id')
            ref = components.find(f"./{{*}}component[@objectid='{identifier}']")
            role = 'print' if label == name else 'pad' if 'REMOVE AFTER PRINT' in label else None
            if role and record.get(role+'_stl'):
                assert ref.get('transform') in (None,'1 0 0 0 1 0 0 0 1 0 0 0')
                install_mesh(project['resources'][identifier], directory / record[role+'_stl'])
                saw.add(role)
            else:
                # Remove only superseded R42 geometry and its old local speed box.
                assert role == 'pad' or part.get('subtype') == 'modifier_part'
                components.remove(ref)
                obj.remove(part)
                project['model'].find('./{*}resources').remove(project['resources'][identifier])
        assert saw == ({'print','pad'} if record.get('pad_stl') else {'print'})
    for obj in project['ranges']:
        for item in list(obj):
            if float(item.get('min_z')) > .001:
                obj.remove(item)
    write_project(project, output)
    return output


def strengthen_small_parts(layout):
    """Strengthen the measured click-clip heels, slider and rear ring crowns."""
    project=c.read(layout)
    fine={'wall_loops':'6','sparse_infill_density':'100%', 'infill_wall_overlap':'27%',
          'outer_wall_line_width':'0.32','inner_wall_line_width':'0.32',
          'internal_solid_infill_line_width':'0.32','top_surface_line_width':'0.32'}
    complete={'DFR0030_Post_Clip','DFR0030_Post_Clip_2','Battery_End_Door'}
    bands={'XIAO_Rod_Holder','Battery_Holder'}
    for obj in project['objects'].values():
        name=c.fields(obj)['name']
        if name in complete|bands:
            c.set_fields(obj,{'wall_generator':'arachne'})
        if name in complete:
            c.set_fields(obj,fine)
    order=[project['names'][item.get('objectid')] for item in project['build']]
    for part in sorted(bands):
        id=str(order.index(part)+1)
        node=project['ranges'].find(f"object[@id='{id}']")
        if node is None:
            node=ET.SubElement(project['ranges'],'object',id=id)
        first=next((r for r in node if float(r.get('min_z'))==0.),None)
        end=float(first.get('max_z')) if first is not None else 0.
        assert 0 <= end < 3.6
        assert all(r is first or float(r.get('min_z')) >= 3.6 for r in node), ('Intersecting layer range',part)
        added=ET.SubElement(node,'range',min_z=str(end),max_z='3.6')
        # Bambu Studio 02.09.01.70 needs an explicit height even for
        # a density/width change (layer_height_profile_from_ranges).
        ET.SubElement(added,'option',opt_key='layer_height').text='0.2'
        for r in [added]+([first] if first is not None else []):
            for key,value in fine.items():
                field=r.find(f"option[@opt_key='{key}']")
                if field is None:field=ET.SubElement(r,'option',opt_key=key)
                field.text=value
    write_project(project,layout)
    note=layout.with_suffix('.composition.json')
    report=read(note)
    report['local_strength_settings']={name:{'wall_generator':'arachne',**fine,
                                              'print_z_mm':[0.,3.6] if name in bands else 'full part'}
                                      for name in sorted(complete|bands)}
    write(note,report)
