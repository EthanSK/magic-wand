"""Compare the realised standing buttress with the original guard load path."""
import manifold3d as mf
import numpy as np
import trimesh
from plate45 import digest

LEGACY_WEB_TARGETS = {
    'left guard reinforcement web','left guard web-to-frame bond',
    'L1 guard-to-web bond','L2 guard-to-web bond','L3 guard-to-web bond',
    'R43 complete thicker guard web',
}


def inspect(checker, directory, receipt, xyz, widths, heights, tops):
    from audit45 import supplemental_coverage
    q=checker.q
    results={}
    precision={}
    body=None
    from witness_volume45 import native_triangle_slabs
    for name,record in receipt['witnesses'].items():
        path=directory/record['file']
        assert digest(path)==record['sha256']
        mesh=trimesh.load_mesh(path)
        # STL coordinates are float32. Keep their exact values in a
        # double-precision constructor, then independently compare volumes.
        shape=mf.Manifold(mf.Mesh64(mesh.vertices,np.asarray(mesh.faces,np.uint64)))
        raw_volume=float(mesh.volume)
        assert abs(raw_volume-record['volume_mm3'])<.001
        precision[name]=dict(cad_mm3=record['volume_mm3'],signed_stl_mm3=raw_volume,
                             reconstructed_mesh64_mm3=shape.volume())
        if abs(shape.volume()-raw_volume)<.0001:
            results[name]=supplemental_coverage(checker,shape,xyz,widths,heights,tops)
            precision[name]['measurement']='double-precision solid'
        else:
            # Some coincident source facets collapse in STL's float32
            # format. Integrate the complete raw oriented triangle surface
            # instead of accepting any material added by manifold repair.
            results[name]=native_triangle_slabs(checker,mesh,xyz,widths,heights,tops)
            precision[name]['measurement']='signed raw triangles clipped to each actual bead slab'
        if name=='member':
            assert abs(shape.volume()-raw_volume)<.0001
            body=shape
    results['witness_precision']=precision
    x,y,z,X,Y,Z=body.bounding_box()
    near=(xyz[:,0]>x-.7)&(xyz[:,0]<X+.7)&(xyz[:,1]>y-.7)&(xyz[:,1]<Y+.7)
    planes=receipt['transverse_x_sections']
    sections=[[] for _ in planes]
    for level in np.unique(tops[near]):
        if level<=z or level-.25>=Z:continue
        mask=near & (abs(tops-level)<.001)
        height=float(heights[mask][0])
        # The inherited parser stores the machine's decimal layer heights as
        # float32. Restore their values before joining touching slab faces.
        # Otherwise nanometre-scale rounding gaps split connected sections.
        top=round(float(level),3)
        h=round(height,3)
        assert abs(top-float(level))<.000003 and abs(h-height)<.000003
        assert abs(top/.2-round(top/.2))<1.e-7 and h==.2, 'Unexpected physical layer interval'
        beads=checker.start_audit.bead_footprints(q,xyz[mask,:2],widths[mask])
        deposited=(beads.extrude(h).translate((0,0,top-h))^body).rotate((0,-90,0))
        for slices,station in zip(sections,planes):
            slices.append(deposited.slice(station['x_mm']))
    for station,slices in zip(planes,sections):
        section=q.CrossSection.batch_boolean(slices,mf.OpType.Add)
        station['native_replacement_mm2']=max((c.area() for c in section.decompose()),default=0.)
    for name,old in receipt['attachments'].items():
        target=results[name]
        target['original_overlap_mm3']=old['old_volume_mm3']
        target['realised_overlap_mm3']=sum(r['covered_mm3'] for r in target['layer_volumes'])
    # Preserve every below-threshold slab. The replacement comparison uses
    # the original physical cross section and independently measured joint
    # overlap, in addition to complete new member and attachment coverage.
    results['transverse_x_sections']=planes
    results['minimum_original_section_mm2']=min(r['original_mm2'] for r in planes)
    results['minimum_native_section_mm2']=min(r['native_replacement_mm2'] for r in planes)
    results['every_section_exceeds_original']=all(r['native_replacement_mm2']>=r['original_mm2'] for r in planes)
    results['every_joint_exceeds_original']=all(results[n]['realised_overlap_mm3']>=old['old_volume_mm3'] for n,old in receipt['attachments'].items())
    results['all_new_member_slabs_at_least_0p90']=results['member']['minimum_layer_fraction']>=.90
    # standing_web45 ends its last designed layer at Z20, adding one
    # nanometre past the top plane to join the construction slabs. Keep the raw terminal fringe
    # measurement. A layer above Z20 contains only that construction overlap.
    design_top=20.
    assert abs(body.bounding_box()[5]-design_top)<.000003
    rows=results['member']['layer_volumes']
    fringe=[r for r in rows if r['top_mm']>design_top]
    assert all(r['top_mm']==20.2 and r['target_mm3']<.0001 for r in fringe)
    results['terminal_overlap_slabs']=fringe
    results['designed_member_slabs_at_least_0p90']=all(r['fraction']>=.9 for r in rows if r['top_mm']<=design_top)
    results['all_complete_joints_at_least_0p90']=all(results[n]['coverage_fraction']>=.90 for n in receipt['attachments'])
    results['joint_slabs_below_0p90']={n:[r for r in results[n]['layer_volumes'] if r['fraction']<.90] for n in receipt['attachments']}
    results['qualified']=all(results[n] for n in ('every_section_exceeds_original','every_joint_exceeds_original',
        'designed_member_slabs_at_least_0p90','all_complete_joints_at_least_0p90'))
    return results
