"""Check the finished guard against the other three and keep the handset assembly routes open."""
from hashlib import sha256
from pathlib import Path
import json
import numpy as np

import design73 as model
import checks71
import audit71

b, d = model.b, model.design


def deck_profile(body):
    # Compare the full diameter of the battery-side root with the opposite
    # outside rim at the same height. Farther inboard the sockets leave
    # open pockets; their inner walls do not describe the outside edge.
    root_x = abs(model.centres()[0][0])
    xs = np.linspace(root_x - model.RADIUS, root_x + model.RADIUS, 37)
    heights = np.linspace(7.28, 9.28, 51)
    differences = []
    for x in xs:
        for height in heights:
            left = model.fit.front_y(body, -x, height)
            right = model.fit.front_y(body, x, height)
            if left is not None and right is not None:
                differences.append(right - left)
    return {'protrusion_mm': max([0., *differences]), 'rays': len(differences)}


def verify():
    path=model.OUT/model.HOLDER
    body=b.load(path)
    rejected=b.load(model.prior.OUT/model.HOLDER)
    new_profile=deck_profile(body)
    old_profile=deck_profile(rejected)
    # Slice the exposed finger-contact arc sideways through each height. A
    # lateral detour for the black socket is allowed; a forward lip is not.
    reference=d.r61.curve(model.fit.smooth_return(28.3),model.RADIUS)
    rail=model.branch()
    outline=[]
    for z in np.arange(.1,7.26,.08):
        ref=reference.slice(z)
        current=rail.slice(z)
        if not ref.is_empty() and not current.is_empty():
            outline.append(ref.bounds()[1]-current.bounds()[1])
    sections=[]
    points=np.array(model.centres())
    disk=model.mf.Manifold.cylinder(.06,model.RADIUS,model.RADIUS,40,center=True)
    for i,point in enumerate(points):
        tangent=points[min(i+1,len(points)-1)]-points[max(0,i-1)]
        tangent/=np.linalg.norm(tangent)
        left=np.cross(tangent,[1.,0.,0.]);left/=np.linalg.norm(left)
        disk_at=disk.transform(np.column_stack([left,np.cross(tangent,left),tangent,point]))
        sections.append(float((body^disk_at).volume()/.06))
    # The fit checks use the soldered socket, its entry, the OP1 plug from
    # below and the retained cell; checking only the final position missed
    # interference in earlier revisions.
    checked,hits=checks71.c70.routes(body,checks71.c70.placed_spaces())
    op1={name:max((body^p).volume() for p in poses) for name,poses in audit71.op1_routes().items()}
    pack=d.pack().translate((model.prior.INBOARD,0,0))
    shoe=d.shoe().translate((model.prior.INBOARD,0,0))
    slide=b.box(d.PACK_X[0]+model.prior.INBOARD,d.PACK_X[1]+model.prior.INBOARD,d.PACK_Y0,d.BED+30,*d.PACK_Z)
    report=dict(revision='R73',carrier_sha256=sha256(path.read_bytes()).hexdigest(),physical_fit_verified=False,
        pieces=len(body.decompose()), r72_edge=old_profile, r73_edge=new_profile,
        maximum_branch_forward_of_reference_mm=float(max([0.,*outline])),
        compared_side_sections=len(outline),minimum_exported_rail_section_mm2=min(sections),
        root_centres_mm=14., key_poses=checked,key_hits=hits,op1_routes_mm3=op1,
        battery_route_rigid_overlap_mm3=(slide^(body-shoe)).volume(),battery_contact_mm3=(body^pack^shoe).volume())
    report['passes']=bool(report['pieces']==1 and old_profile['protrusion_mm']>.75 and
        new_profile['rays']>1000 and new_profile['protrusion_mm']<.05 and len(outline)>75 and
        report['maximum_branch_forward_of_reference_mm']<.10 and min(sections)>3.9 and
        checked==336 and not hits and max(op1.values())<.01 and report['battery_route_rigid_overlap_mm3']<.01 and
        .1<report['battery_contact_mm3']<4.)
    (model.OUT/'fit73.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if not report['passes']:
        raise ValueError('Finished R73 guard, perimeter or assembly route failed')


if __name__=='__main__':
    verify()
