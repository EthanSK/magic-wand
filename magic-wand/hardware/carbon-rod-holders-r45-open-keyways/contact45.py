"""Measure actual one-empty-layer roof contact from each accessible peel piece."""
import argparse,json
from pathlib import Path
import numpy as np
from holder45 import inherited as prior
from plate45 import digest
import single44
def inspect(path,helper_name='External_cradle'):
    c=prior.common.load_checker().audit;q=c.q
    d,features,stats,config,offset,objects,_,_=c.read_project(path)
    names=np.asarray(features)[d[:,5].astype(int)];owners=single44.previous.owners(path)
    shift=np.array([50.,70.,0.]);xyz=d[:,:3]+offset-shift
    part=(d[:,6]==owners['Key_Carrier'])&prior.common.model_mask(names)
    rib=(d[:,6]==owners[helper_name])&prior.common.model_mask(names)
    def solid(n):
        obj=objects[n];return q.solid(obj['vertices']-shift,obj['faces'])
    body,cradle=solid('Key_Carrier'),solid(helper_name)
    frame=json.loads((path.parent/'frame.json').read_text())['print_to_assembly']
    inverse=np.linalg.inv(frame)[:3]
    guards=prior.d.union(prior.d.geometry()[3].values()).transform(inverse)
    feet=cradle.slice(.1).decompose(); records=[]
    # Side teeth reach beyond their bed feet. Attribute their entire roof
    # to the single connected shelf, including all cantilevered contacts.
    actor_feet=feet if helper_name=='External_cradle' else [cradle.slice(.1)]
    regions=feet if helper_name=='External_cradle' else [cradle.project()]
    piece_shapes=[];piece_names=[]
    if helper_name=='Front_pull_shelf':
        cad=json.loads((path.parent/'shelf-cad.json').read_text())
        if cad.get('removable_pieces'):
            import trimesh
            for item in cad['removable_pieces']:
                file=path.parent/item['file'];assert digest(file)==item['sha256']
                mesh=trimesh.load_mesh(file)
                piece_shapes.append(q.solid(mesh.vertices,mesh.faces));piece_names.append(item['name'])
            actor_feet=[s.slice(.1) for s in piece_shapes]
    for f in actor_feet:
        records.append({'bed_face_area_mm2':f.area(),'bed_xy_bounds_mm':f.bounds(),
            'contains_1p2mm_diameter_grip_land':not f.offset(-.6).is_empty(),
            'projected_contact_area_sum_mm2':0.,'largest_continuous_contact_patch_mm2':0.,
            'finger_guard_contact_sum_mm2':0.,'contact_layers':[]})
    for row,name in zip(records,piece_names):row['removable_piece']=name
    def footprints(mask):
        return c.start_audit.bead_footprints(q,xyz[mask,:2],d[mask,3])
    grounded=footprints(rib&(np.abs(d[:,7]-.2)<.001)).decompose()
    next_layer=footprints(rib&(np.abs(d[:,7]-.4)<.001)).decompose()
    actual_feet=[]
    for index,patch in enumerate(grounded):
        linked=[up for up in next_layer if (up^patch).area()>.02]
        substantial=[j+1 for j,other in enumerate(grounded) if j!=index and other.area()>=3
            and any((other^up).area()>.2 for up in linked)]
        actual_feet.append(dict(index=index+1,actual_bead_area_mm2=patch.area(),
            contains_1p2mm_diameter_grip_land=not patch.offset(-.6).is_empty(),bed_xy_bounds_mm=patch.bounds(),
            cad_foot_indices=[i+1 for i,f in enumerate(feet) if (patch^f).area()>.01],
            continues_on_layer_two=bool(linked),joins_substantial_feet_on_layer_two=substantial))
    # Follow any unusually slender real bed track (not its ideal CAD
    # footprint) through successive physical layers until merger or end.
    suspects={a['index'] for a in actual_feet if not a['contains_1p2mm_diameter_grip_land'] or a['actual_bead_area_mm2']<3}
    if suspects:
        lineage=[(patch,{i+1}) for i,patch in enumerate(grounded)]
        for top in np.unique(d[rib,7]):
            if top<.3 or not suspects:continue
            upper=footprints(rib&(abs(d[:,7]-top)<.001)).decompose()
            next_line=[]
            for patch in upper:
                x0,y0,x1,y1=patch.bounds();anc=set()
                for low,ids in lineage:
                    a,b,c0,e=low.bounds()
                    if x1<a or y1<b or c0<x0 or e<y0:continue
                    if (patch^low).area()>.02:anc.update(ids)
                if anc:next_line.append((patch,anc))
            for n in tuple(suspects):
                alive=[anc for patch,anc in next_line if n in anc]
                joined=set.union(*alive)-{n} if alive else set()
                row=actual_feet[n-1]
                if joined:
                    row.update(first_actual_merge_layer_top_mm=round(float(top),3),merged_with_bed_foot_indices=sorted(joined))
                    suspects.remove(n)
                elif not alive:
                    row['last_continuous_layer_top_mm']=round(float(top)-.2,3);suspects.remove(n)
                else:row['last_continuous_layer_top_mm']=round(float(top),3)
            lineage=next_line
    for top in np.unique(d[rib,7]):
        t=float(top)
        # Only exposed cradle roofs count: do not mistake an inner layer
        # of a tall cradle for a face touching the carrier two layers up.
        roof=cradle.slice(t-.1)-cradle.slice(t+.1)
        target=roof^body.slice(t+.3)
        if target.area()<.0001:continue
        a=rib&(abs(d[:,7]-top)<.001);b=part&(abs(d[:,7]-(top+.4))<.001)
        if not(a.any() and b.any()):continue
        contact=(footprints(a)^footprints(b))^target
        if contact.is_empty():continue
        g=guards.slice(t+.3)
        at_level=[piece.slice(t-.1) for piece in piece_shapes] if piece_shapes else regions
        for f,row in zip(at_level,records):
            joint=f^contact;area=joint.area()
            if area<.0001:continue
            pieces=joint.decompose();mx=max(p.area() for p in pieces)
            row['projected_contact_area_sum_mm2']+=area
            row['largest_continuous_contact_patch_mm2']=max(row['largest_continuous_contact_patch_mm2'],mx)
            contact_on_guard=joint^g
            finger=contact_on_guard.area()
            guard_patch=max((p.area() for p in contact_on_guard.decompose()),default=0.)
            row['finger_guard_contact_sum_mm2']+=finger
            row['contact_layers'].append({'actual_helper_top_mm':round(t,3),'actual_carrier_bottom_mm':round(t+.2,3),
                'vertical_gap_mm':.2,'projected_guard_area_mm2':finger,'largest_projected_guard_patch_mm2':guard_patch,
                'number_of_separate_contact_patches':len(pieces),'area_mm2':area,'largest_patch_mm2':mx})
    result={'helper_owner':helper_name,'archive_sha256':digest(path),'peel_pieces':records,'actual_first_layer_cradle_islands':actual_feet,'physical_release_force_measured':False,
        'measurement':'Conservative inscribed footprints of actually extruded roof and carrier beads, at the intended 0.2-mm vertical gap, clipped to native exposed roof and carrier material. Projected areas are not fused-contact or peel-force measurements.'}
    report='contact-areas.json' if helper_name=='External_cradle' else ('rear-shelf-contact-areas.json' if helper_name=='Rear_pull_shelf' else 'shelf-contact-areas.json')
    (path.parent/report).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);inspect(p.parse_args().archive)
