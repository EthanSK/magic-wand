#!/usr/bin/env python3
"""Strict adaptation of the shared layer audit: backing must be underneath.

Keep the archived Shard auditor unchanged. This revision separately records
partial overhangs, and measures one-empty-layer gaps in actual lower beads.
"""
import numpy as np

def bead_footprints(q,xy,width):
    """Conservative actual plastic, shared by start and load-path checks."""
    angle=np.arange(12)*np.pi/6;unit=np.c_[np.cos(angle),np.sin(angle)]
    return q.CrossSection((xy[:,None,:]+unit[None,:,:]*width[:,None,None]/2).tolist())

def inspect(q,mesh,xyz,height,feature,features,layer_top,assembly_tf,width,gap=.2):
    model=np.array([not features[int(v)].startswith(('Brim','Skirt','Support'))for v in feature])
    support=np.array([features[int(v)].startswith('Support')for v in feature])
    ids=np.flatnonzero(model);keys=np.rint(layer_top[ids]*10000).astype(np.int32)
    order=np.argsort(keys);ids=ids[order];keys=keys[order]
    groups=np.r_[0,np.flatnonzero(np.diff(keys))+1,len(ids)]
    floating=[];missing=[];backed_starts=[];partial=[];previous_top=None;previous_section=q.CrossSection();checked=0
    def printed_section(group,section):
        # Inscribed 12-gon bead footprints are conservative. Mesh sections
        # can locate the part, but unprinted CAD must never back a new path.
        return bead_footprints(q,xyz[group,:2],width[group])^section
    def has_bead(component,group):
        for bead_width in np.unique(np.round(width[group],3)):
            candidates=group[abs(width[group]-bead_width)<.0006]
            if q._inside(component.offset(float(bead_width)/2+.075),xyz[candidates,:2]).any():return True
        return False
    def distributed_beads(component,group):
        # A bead at one corner must not bring an entire unprinted guide
        # face into the boundary envelope or falsely back its next layer.
        x0,y0,x1,y1=component.bounds();occupied=0
        for ix in range(3):
            for iy in range(3):
                a=x0+(x1-x0)*ix/3;b=x0+(x1-x0)*(ix+1)/3
                c=y0+(y1-y0)*iy/3;d=y0+(y1-y0)*(iy+1)/3
                cell=component^q.CrossSection([[[a,c],[b,c],[b,d],[a,d]]])
                if cell.area()<max(.05,component.area()*.02):continue
                occupied+=1
                if not has_bead(cell,group):return False
        return occupied>0
    for a,b in zip(groups[:-1],groups[1:]):
        group=ids[a:b];top=float(keys[a])/10000;h=float(np.min(height[group]));mid=top-h/2
        current=mesh.slice(mid)
        # At a float32 face exactly on the sampling plane, accept extra
        # geometry from a 1-micron envelope ONLY when this actual layer has
        # a bead footprint there. Never invent an early unprinted floor.
        boundary=(mesh.slice(mid-.001)+mesh.slice(mid+.001))-current
        for component in boundary.decompose():
            if component.area()>.15 and distributed_beads(component,group):current+=component
        if current.is_empty():continue
        checked+=1
        printed=printed_section(group,current)
        if previous_top is None and top<=h+.06:
            previous_top=top;previous_section=printed;continue
        previous=previous_section if previous_top is not None and abs(top-previous_top-h)<.06 else q.CrossSection()
        natural=previous.offset(.25,q.JoinType.Round);unbacked=printed-natural
        bottom=top-h
        # Only the real layer immediately below one empty layer can qualify.
        support_ids=np.flatnonzero(support&(abs(layer_top-(bottom-gap))<.016))
        def backing(component):
            interior=component.offset(-.03)
            if interior.is_empty():interior=component
            if not len(support_ids):return None,0
            hits=q._inside(interior,xyz[support_ids,:2])
            if not hits.any():return None,0
            real_top=float(layer_top[support_ids[hits]].max())
            return round(bottom-real_top,4),int(hits.sum())
        for component in unbacked.decompose():
            if component.area()<2.:continue
            bounds=component.bounds();real_gap,count=backing(component)
            partial.append({'layer_top_mm':round(top,4),'unbacked_mesh_area_mm2':round(component.area(),4),
                            'print_xy_bounds_mm':[round(float(v),4)for v in bounds],
                            'direct_lower_bead_samples':count,'actual_vertical_gap_mm':real_gap,
                            'note':'Requires an explicit bridge/backing decision; a nearby sideways bead is not backing.'})
        for component in current.decompose():
            if component.area()<.15:continue
            # A line centre may lie outside a narrow rounded edge while
            # its real bead still covers it. Use actual half-widths here;
            # backing above remains strictly centre-under-component.
            if not has_bead(component,group):
                missing.append({'layer_top_mm':round(top,4),'area_mm2':round(component.area(),4),'print_xy_bounds_mm':[round(float(v),4)for v in component.bounds()]})
                continue
            if(component^natural).area()>.01:continue
            bounds=component.bounds();centre=np.array([[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2,mid]])
            item={'layer_top_mm':round(top,4),'area_mm2':round(component.area(),4),
                  'print_xy_bounds_mm':[round(float(v),4)for v in bounds],
                  'assembly_centre_mm':np.round(q.points(centre,assembly_tf)[0],4).tolist()}
            real_gap,count=backing(component)
            if real_gap is None:floating.append(item)
            else:
                item.update(actual_vertical_gap_mm=real_gap,direct_lower_bead_samples=count)
                backed_starts.append(item)
        previous_top=top;previous_section=printed
    return {'checked_layers':checked,'floating_components':floating,'missing_printed_components':missing,'support_backed_islands':backed_starts,
            'partial_overhangs':partial,'largest_unbacked_layers':sorted(partial,key=lambda r:r['unbacked_mesh_area_mm2'],reverse=True)[:16],
            'required_empty_layer_gap_mm':gap,'section_plane_guard_mm':.001,'boundary_witness_grid':3,'sideways_backing_credit_mm':0,
            'backing_source':'Actual previous-layer bead footprints clipped to the final mesh; inscribed 12-gons, no credit for unprinted mesh.',
            'limitation':'Bead-backed geometry audit, not a thermal, bridge-sag, strength or fatigue simulation.'}
