"""Replace the abrupt leading corner of the shared left guard web with a standing buttress."""
import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

from holder45 import inherited
from shelf45 import band, box
from standing45 import overlap


def total(parts):
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add) if parts else mf.Manifold()


def export(shape, directory, name):
    from plate45 import digest
    path = directory / ('R45-web-' + name + '.stl')
    mesh = shape.to_mesh()
    trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts, process=False).export(path)
    return dict(file=path.name, sha256=digest(path), volume_mm3=shape.volume())


def prepare(body, frame, directory):
    d = inherited.d
    inverse = np.linalg.inv(frame)[:3]
    assembly = lambda shape: shape.transform(frame[:3])
    print_frame = lambda shape: shape.transform(inverse)
    carrier_routes, originals = inherited.routes()
    routes = {**carrier_routes[d.CARRIER], **inherited.full.precision_support_spaces()}

    # The tail is outside the finger-contact spans. Its unprintable edge starts
    # above the solder envelope at Z17.15. The frame rail on its outer side is
    # already present. Carry this rail into a wider buttress before the guards
    # converge, keeping the bought parts' entire swept clearance.
    envelope = box(-.72, 9.70, 5.12, 5.85)
    zone = envelope.extrude(6.0).translate((0, 0, 14.0))
    asm_zone = assembly(zone)
    bounds = asm_zone.bounding_box()
    poses = {name: [p for p in (region.poses() if hasattr(region, 'poses') else [region])
                    if overlap(bounds, p.bounding_box())] for name, region in routes.items()}
    void = print_frame(total([v ^ asm_zone for items in poses.values() for v in items]))
    local = body ^ zone
    web = print_frame(d.guard_reinforcement()) ^ body
    mask = box(-.04, 11.83, 2.12, 1.09)
    previous = body.slice(13.9) ^ envelope.offset(1.)
    layers = []
    cuts = []
    for k in range(71, 101):
        z = .2*k
        mid = z-.1
        old = body.slice(mid) ^ envelope.offset(1.0)
        # Sweep in a wider outside buttress, then lap the original frame
        # and the shared guard tail. Exact hardware relief comes afterwards.
        outside = box(-.72, 10.0, 2.96, 5.50)
        extended = outside if z < 17.4 else envelope
        available = extended - band(void, z-.20001, z+.00001).offset(.08)
        seed = previous.simplify(.006).offset(-.20).simplify(.006).offset(.20).simplify(.006)
        reachable = seed.offset(.13).simplify(.006)
        design = reachable ^ available
        # The first high-Y edge of the old web and neighbouring frame are
        # coincident. Draw their common outer underside as one growing face.
        if 17.0 < z < 18.61:
            cut = ((old ^ mask) - reachable)
            if not cut.is_empty():
                cuts.append(cut.extrude(.20002).translate((0, 0, z-.20001)))
        else:
            cut = mf.CrossSection()
        if design.area()>1.e-6:
            prism=design.simplify(.0005).extrude(.200002).translate((0,0,z-.200001))
            assert prism.status()==mf.Error.NoError, (k,design.area(),prism.status())
            layers.append(prism)
        previous = ((old-cut)+design).simplify(.006)
    gusset = total(layers) - void
    cut = total(cuts) ^ local
    # R41 returns frame and ribs with its web unioned. Its independent
    # pre-union overlaps reconstruct the actual original attachment faces.
    old = d.previous.prev.carrier_parts()
    refs = {'frame': (old[2]-old[4])+old[5]['left guard web-to-frame bond']}
    refs.update({n: (old[3][n]-old[4])+old[5][n+' guard-to-web bond'] for n in ('L1','L2','L3')})
    references = {n:(print_frame(s)^body)^zone for n,s in refs.items()}
    new_member = (web-cut)+gusset
    components=new_member.decompose()
    carrying=[piece for piece in components if all((piece^ref).volume()>.01 for ref in references.values())]
    assert carrying, ('load-path components', [p.volume() for p in components])
    # Select the continuous candidate with the strongest weakest rib joint.
    # Other islands contribute no claimed material or strength.
    new_member=max(carrying,key=lambda c:min((c^references[n]).volume() for n in ('L1','L2','L3')))
    # Omit added islands which reach the frame separately but cannot also
    # carry guard load. Keep all original carrier material outside the cut.
    added=new_member-local
    removed=cut-new_member
    joined=(body-removed)+added
    connected=sorted(joined.decompose(),key=lambda c:-c.volume())
    local_fragments=[p for p in connected[1:] if overlap(zone.bounding_box(),p.bounding_box()) and p.volume()>1.e-8]
    detached=total(local_fragments)
    assert all((p-zone).volume()<.00001 for p in local_fragments)
    joined=joined-detached;removed+=detached^body
    assert (detached^new_member).volume()<.00001
    from plate45 import digest
    report = dict(generator_file=Path(__file__).name,generator_sha256=digest(Path(__file__)),old_member_mm3=web.volume(),new_member_mm3=new_member.volume(),
        added_mm3=added.volume(),removed_mm3=removed.volume(),disconnected_local_fragments_removed_mm3=detached.volume(),max_lateral_growth_per_layer_mm=.13,
        actual_added_intersections_by_route={name:max([0.]+[(assembly(added)^v).volume() for v in items]) for name,items in poses.items()},
        original_witness_losses_mm3={name:max(0.,(print_frame(s)^removed).volume())
            for name,s in originals[d.CARRIER].items()},
        witnesses={'member':export(new_member,directory,'complete-member')},attachments={})
    assert max(report['actual_added_intersections_by_route'].values()) < 1.e-5
    for n,ref in references.items():
        old_overlap = web ^ ref
        joint = new_member ^ ref
        report['witnesses'][n] = export(joint, directory, n+'-bond')
        report['attachments'][n] = dict(old_volume_mm3=old_overlap.volume(),new_volume_mm3=joint.volume())
    # Common outer-tail load travels across X from the outer guard end into
    # the inner frame rail. Use the same fixed physical planes in both solids.
    def transverse(shape,x):
        section=shape.rotate((0.,-90.,0.)).slice(x)
        return max((piece.area() for piece in section.decompose()),default=0.)
    report['transverse_x_sections']=[dict(x_mm=x,original_mm2=transverse(web,x),replacement_mm2=transverse(new_member,x))
        for x in np.arange(.50,1.61,.10).tolist()]
    (directory/'standing-web.json').write_text(json.dumps(report,indent=2)+'\n')
    return joined,report
