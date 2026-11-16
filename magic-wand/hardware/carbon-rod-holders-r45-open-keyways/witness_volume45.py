"""Integrate oriented STL triangles inside a native bead footprint and layer slab."""
import manifold3d as mf
import numpy as np


def clip_above(points, z):
    clipped=[]
    for a,b in zip(points,np.roll(points,-1,axis=0)):
        if a[2]>=z:clipped.append(a)
        if (a[2]<z)!=(b[2]<z):
            clipped.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
    return np.asarray(clipped)


def projection(points, direction, mask):
    if len(points)<3:return mf.CrossSection()
    xy=points[:,:2] if direction>0 else points[::-1,:2]
    area=mf.CrossSection([xy])
    return area if mask is None else area^mask


def plane_integral(region, origin, slope, lo):
    # A linear height field integrates exactly at each polygon's area
    # centroid. The winding also subtracts inner holes.
    value=0.
    for path in region.to_polygons():
        xy=path-origin[:2]
        next_xy=np.roll(xy,-1,axis=0)
        cross=xy[:,0]*next_xy[:,1]-xy[:,1]*next_xy[:,0]
        value+=(origin[2]-lo)*cross.sum()/2.
        value+=np.dot((cross[:,None]*(xy+next_xy)).sum(axis=0),slope)/6.
    return float(value)


def native_triangle_slabs(checker, mesh, xyz, widths, heights, levels):
    """Use the signed closed surface directly, including coincident STL faces.

    For a vertical ray, every face above the slab adds/subtracts the full
    layer height. Faces inside the slab add/subtract their height above
    its lower plane. Integrating these signed ray lengths gives volume.
    """
    tri=mesh.triangles.astype(float)
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    active=np.abs(normals[:,2])>1.e-11
    tri=tri[active];normals=normals[active]
    minimum=tri[:,:,2].min(axis=1);maximum=tri[:,:,2].max(axis=1)
    slopes=-normals[:,:2]/normals[:,2,None]
    signs=np.sign(normals[:,2])
    top_z=mesh.bounds[1,2];bottom_z=mesh.bounds[0,2]
    xmin,ymin,_=mesh.bounds[0];xmax,ymax,_=mesh.bounds[1]
    nearby=(xyz[:,0]>xmin-.7)&(xyz[:,0]<xmax+.7)&(xyz[:,1]>ymin-.7)&(xyz[:,1]<ymax+.7)
    rows=[]
    for l in np.unique(levels):
        top=round(float(l),3)
        if top<bottom_z-.001 or top-.25>top_z:continue
        on=abs(levels-l)<.001;h=round(float(heights[on][0]),3);lo=top-h
        mask=on&nearby
        beads=checker.start_audit.bead_footprints(checker.q,xyz[mask,:2],widths[mask])
        covered=volume=0.
        for i in np.flatnonzero(maximum>lo):
            t=tri[i];sgn=signs[i]
            upper=clip_above(t,top)
            above=projection(upper,sgn,None)
            if not above.is_empty():
                volume+=sgn*h*above.area()
                covered+=sgn*h*(above^beads).area()
            if minimum[i]>=top:continue
            within=clip_above(t,lo)
            if len(within)<3:continue
            within=clip_above(within*np.array((1.,1.,-1.)),-top)
            if len(within)<3:continue
            proj=projection(within,sgn,None)
            if proj.is_empty():continue
            volume+=sgn*plane_integral(proj,t[0],slopes[i],lo)
            covered+=sgn*plane_integral(proj^beads,t[0],slopes[i],lo)
        if volume<1.e-7:continue
        assert -.00001<=covered<=volume+.00001,(top,covered,volume)
        rows.append(dict(top_mm=top,target_mm3=volume,covered_mm3=covered,fraction=max(0.,min(1.,covered/volume))))
    total=sum(r['target_mm3'] for r in rows)
    assert abs(total-mesh.volume)<.0001,(total,mesh.volume)
    return dict(layers=len(rows),coverage_fraction=sum(r['covered_mm3'] for r in rows)/total,
                minimum_layer_fraction=min(r['fraction'] for r in rows),layer_volumes=rows)
