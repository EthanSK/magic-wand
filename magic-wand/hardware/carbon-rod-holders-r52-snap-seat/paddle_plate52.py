"""Lay the DFRobot paddle on its side so its sleeve axis prints vertically."""
import numpy as np
import manifold3d as mf

from clearance51 import blockers
from orient51 import oriented
from plate51 import resource, value


def lay_on_side(model, config, frame, source_body):
    from plate52 import add_modifiers, tag

    owner_id = str(frame['owner'])
    resources = model.find(tag('resources'))
    owner = config.find(f"object[@id='{owner_id}']")
    compound = resources.find(tag('object') + f"[@id='{owner_id}']")
    components = compound.find(tag('components'))
    item = model.find(tag('build') + '/' + tag('item') + f"[@objectid='{owner_id}']")
    translation = np.array([float(x) for x in item.get('transform').split()[-3:]])
    normal = owner.find("part[@subtype='normal_part']").get('id')
    for part in list(owner.findall('part')):
        index = part.get('id')
        resources.remove(resources.find(tag('object') + f"[@id='{index}']"))
        if index != normal:
            owner.remove(part)
            components.remove(components.find(tag('component') + f"[@objectid='{index}']"))
    body, transform = oriented(source_body, 'left_down')
    resource(resources, tag, normal, 'DFRobot_Hole_Bracket', body)
    bearing = blockers('DFRobot_Hole_Bracket')['bearing through hole']
    bore = bearing.transform(transform[:3]).project().offset(0.6)

    bounds = body.bounding_box()
    envelope = mf.Manifold.cube(tuple(v+1 for v in bounds[3:])).translate((-.5,-.5,-.5))
    # Manual contacts exclude the journal's full projection. Automatic support
    # can put a column up its middle to reach the far end of the bearing.
    marks = {'Outside the journal':envelope - bore.offset(1.55).extrude(bounds[5]+2).translate((0,0,-1))}
    # Back the first annular thrust face only. A column growing through
    # the journal to its upper end would obstruct the slide-in sleeve.
    axis = bore.bounds()
    centre = ((axis[0]+axis[2])/2, (axis[1]+axis[3])/2)
    ring = mf.CrossSection.circle(5.2,80) - mf.CrossSection.circle(1.95,80)
    marks['Bearing underside'] = ring.translate(centre).extrude(0.65).translate((0,0,4.46))
    # The far board post and upper guide start above the near side.
    for i,(x,y,z) in enumerate(((127.67,112.10,13.8),(123.22,110.05,17.4))):
        marks[f'Backing for upper ledge {i+1}'] = mf.Manifold.cube((2.8,2.9,1.5),True).translate((x,y,z)).translate(-translation)
    add_modifiers(resources, compound, owner, marks, 460, 'support_enforcer')
    for key, setting in {
        'support_type':'normal(manual)', 'support_style':'snug', 'support_on_build_plate_only':0,
        'support_threshold_angle':40, 'support_object_xy_distance':0.35,
        'outer_wall_acceleration':600, 'inner_wall_acceleration':900,
    }.items():
        value(owner, key, setting)
    transform[:3, 3] += translation
    frame.update(orientation='left_down', assembly_to_machine=transform.tolist(), height_mm=round(body.bounding_box()[5],4))
