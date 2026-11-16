"""Conservative swept collision screen of the *actual* removable bead envelope."""
import numpy as np

def whole_bead_release(checker,data,xyz,carrier,helper):
    q=checker.q
    # Maximum centre sampling step is 0.15 mm along each line or arc.
    # Expand by half that step and circumscribe the true circular bead.
    radii=(data[:,3]+checker.STEP)/(2*np.cos(np.pi/12))
    def envelope(mask):
        return checker.start_audit.bead_footprints(q,xyz[mask,:2],2*radii[mask])
    # Fast rejection only: every whole swept disc is contained in its
    # outward-rounded square cells. Confirm any potentially intersecting
    # cell tiles with the original continuous polygon operation.
    step=.05; xy=xyz[:,:2]; obj=carrier|helper
    origin=np.floor((xy[obj].min(0)-2)/step)*step
    extent=np.ceil((xy[obj].max(0)+2-origin)/step).astype(int)+2
    nx,ny=extent
    lo=np.floor((xy-radii[:,None]-origin)/step).astype(int)
    hi=np.floor((xy+radii[:,None]-origin)/step).astype(int)+1
    def cover(mask):
        grid=np.zeros((ny+1,nx+1),dtype=np.int32)
        a,b=lo[mask].T;c,d=hi[mask].T
        for ys,xs,val in ((b,a,1),(d,c,1),(d,a,-1),(b,c,-1)):
            np.add.at(grid,(ys,xs),val)
        return grid.cumsum(0,dtype=np.int32).cumsum(1,dtype=np.int32)[:-1,:-1]>0
    prefix=np.zeros((ny,nx),bool); collisions=[];sections=[]
    for z in np.unique(data[obj,7]):
        layer=np.abs(data[:,7]-z)<.001;part=layer&carrier;rib=layer&helper
        if part.any():prefix|=cover(part)
        if not rib.any():continue
        yy,xx=np.nonzero(prefix&cover(rib))
        if len(xx):
            # Fixed 1-mm tiles cover the union of every possible collision;
            # all beads that can reach a tile are retained, regardless of
            # their object/order. Avoid repeated union of an entire plate.
            quant=20;tiles=np.unique(np.c_[xx//quant,yy//quant],axis=0);pieces=[]
            lower=carrier&(data[:,7]<=z+.001)
            for tx,ty in tiles:
                x0,y0=origin+np.array([tx,ty])*step*quant
                x1,y1=x0+step*quant,y0+step*quant
                near=(xy[:,0]>=x0-radii)&(xy[:,0]<=x1+radii)&(xy[:,1]>=y0-radii)&(xy[:,1]<=y1+radii)
                m=near&lower;h=near&rib
                if not (m.any() and h.any()):continue
                tile=q.CrossSection.square((step*quant,step*quant)).translate((x0,y0))
                overlap=(envelope(m)^envelope(h))^tile
                if not overlap.is_empty():pieces.append(overlap)
            area=sum(p.area() for p in pieces)
            if area>.0001:
                bounds=np.array([p.bounds() for p in pieces])
                collisions.append({'layer_top_mm':round(float(z),3),'conservative_overlap_mm2':area,
                    'print_xy_bounds_mm':[*bounds[:,:2].min(0),*bounds[:,2:].max(0)]})
        if z<.201:
            for patch in envelope(rib).decompose():
                bounds=patch.bounds()
                sections.append(dict(foot_area_mm2=patch.area(),width_mm=bounds[2]-bounds[0],
                    length_mm=bounds[3]-bounds[1],has_1p2mm_grip_land=not patch.offset(-.6).is_empty()))
    return dict(clear=not collisions,collisions=collisions,first_layer_accessible_faces=sections,
        direction='whole cradle straight down in print frame after lifting from bed',
        method='Every actual cradle bead swept past the cumulative XY envelope of every carrier bead in the same or any lower layer. Conservative outward-rounded AABB rejection; exact clipped polygon intersection on every possible conflict tile, 0.15 mm centre-step guard, circumscribed bead widths. No thermal or force inference.')
