"""Give the complete right finger rest one native perimeter process region."""
from pathlib import Path
from xml.etree import ElementTree as ET

import manifold3d as mf
import numpy as np


def configure(target, proof, frame):
    import compose47
    import plate45
    from battery_print48 import write_project
    from native48 import digest, write

    project = compose47.read(target)
    identifier, = [key for key,name in project['names'].items() if name == 'Key_Carrier']
    owner = project['objects'][identifier]
    resources = project['model'].find('./{*}resources')
    components = project['resources'][identifier].find('./{*}components')
    pieces = []
    records = {}
    label = 'Continuous right finger rest, brace and landing'
    # The separate R2 guard-root box sits at the deck, outside this branch.
    right_regions = {'Solid right middle-to-edge brace', 'Solid right guard-leg landing',
                     'Solid middle finger-rest joint'}
    for part in list(owner.findall('part')):
        name = part.find("metadata[@key='name']").get('value')
        if not (name.startswith('R44 solid join - R44 R ') or name in right_regions):
            continue
        assert part.get('subtype') == 'modifier_part'
        fields = {m.get('key'):m.get('value') for m in part.findall('metadata')}
        assert fields['sparse_infill_density'] == '100%' and fields['wall_loops'] == '4'
        key = part.get('id')
        ref = components.find(f"./{{*}}component[@objectid='{key}']")
        assert ref is not None and not ref.get('transform')
        mesh = project['resources'][key]
        vertices = np.array([[float(v.get(a)) for a in ('x','y','z')]
                             for v in mesh.findall('./{*}mesh/{*}vertices/{*}vertex')])
        lo,hi = vertices.min(axis=0),vertices.max(axis=0)
        faces = [[int(t.get(k)) for k in ('v1','v2','v3')]
                 for t in mesh.findall('./{*}mesh/{*}triangles/{*}triangle')]
        solid = mf.Manifold(mf.Mesh(np.asarray(vertices,dtype=np.float32),np.asarray(faces,dtype=np.uint32)))
        assert solid.status() == mf.Error.NoError and solid.volume() > 0.
        pieces.append(solid)
        records[name] = [lo.tolist(),hi.tolist()]
        owner.remove(part)
        components.remove(ref)
        resources.remove(mesh)
    assert right_regions.issubset(records) and len(pieces)==10
    import build48
    d = build48.h.d
    branch = d.finger_rest_paths()['R']['middle branch']
    # Surround the complete curved shaft, so the process boundary cannot
    # cut across the side of its rounded source mesh between the old boxes.
    inverse = np.linalg.inv(np.asarray(frame['print_to_assembly']))[:3]
    sleeve = d.h33.rounded_run(branch,radius=d.RIB_RADIUS+.60).transform(inverse)
    merged = mf.Manifold.batch_boolean([*pieces,sleeve],mf.OpType.Add)
    components_above_sliver = [p for p in merged.decompose() if p.volume()>.001]
    assert len(components_above_sliver)==1, [p.volume() for p in components_above_sliver]
    # Native boundaries of two R47 selectors fell across a single narrow
    # R48 shaft, splitting off its middle segment. The old R44 region spans
    # both separations. Joining the selectors eliminates the internal seams.
    centre = d.h33.rounded_run(branch,radius=d.RIB_RADIUS+.45).transform(inverse)
    assert (centre-merged).volume()<1.e-5
    number = max(int(r.get('id')) for r in resources)+1
    plate45.mesh_resource(resources,number,label,merged)
    ET.SubElement(components,plate45.tag('component'),objectid=str(number))
    part = ET.SubElement(owner,'part',id=str(number),subtype='modifier_part')
    compose47.set_fields(part,{'name':label,'sparse_infill_density':'100%','wall_loops':'4',
        'wall_generator':'arachne','min_bead_width':'60%','wall_distribution_count':'2',
        'inner_wall_line_width':'0.34','outer_wall_line_width':'0.34','internal_solid_infill_line_width':'0.34'})
    write_project(project,target)
    write(proof,{'generator_sha256':digest(Path(__file__)),'joined_print_regions':records,
                 'native_modifier':label,'branch_interior_volume_mm3':centre.volume(),
                 'sleeve_radial_margin_mm':.60,'sleeve_outside_initial_regions_mm3':(sleeve-mf.Manifold.batch_boolean(pieces,mf.OpType.Add)).volume(),
                 'joined_selector_volume_mm3':merged.volume(),'number_of_connected_selectors':1})
