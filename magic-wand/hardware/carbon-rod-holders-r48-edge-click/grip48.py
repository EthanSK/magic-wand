"""Find an exterior tweezer approach for each support after the part leaves the bed."""
from pathlib import Path
import manifold3d as mf
import numpy as np
from shelf45 import band, span


def grips(out):
    from build48 import b
    from native48 import read
    front, rear = [read(out / f) ['removable_pieces'] for f in ('shelf-cad.json','rear-shelf-cad.json')]
    rows = front + rear
    pieces = [b.load(out / r['file']) for r in rows]
    fixed = b.load(out / 'R45-Key-Carrier.stl') + b.load(out / 'R45-release-tabs.stl')
    result=[]
    # Outer cradle comes off first in the established cleanup order. The
    # lower jaw slides below the off-bed part; the upper jaw follows the
    # same entry line above the exterior pull land, with no printed fulcrum.
    radius = .60
    for i,(r,body) in enumerate(zip(rows,pieces,strict=True)):
        stationary = mf.Manifold.batch_boolean([fixed,*pieces[i+1:]],mf.OpType.Add)
        direction=r['direction_print'][1]
        foot=body.slice(.1).offset(-radius)
        found=None
        for top in (.4,.6,.8,1.,1.2,1.6,2.,2.4,3.,4.,5.,6.):
            # A full 1.2-mm disk on both jaws, with 0.8-mm vertical space
            # for the upper jaw and 72 mm of straight, unimpeded withdrawal.
            land=foot ^ body.slice(top-.08).offset(-radius)
            if land.is_empty():continue
            blockage=band(stationary, top-.08,top+.85) + band(body,top+.025,top+.85)
            free=land - span(blockage.offset(radius+.10),0,-direction*72.)
            options=[p for p in free.decompose() if p.area()>.01]
            if options:
                best=max(options,key=lambda p:p.area())
                # Get an interior witness even for curved polygonal lands.
                from math import ceil
                minx,miny,maxx,maxy=best.bounds()
                xs=np.linspace(minx,maxx,max(3,ceil((maxx-minx)/.09)+1))
                ys=np.linspace(miny,maxy,max(3,ceil((maxy-miny)/.09)+1))
                for x in xs[1:-1]:
                    for y in ys[1:-1]:
                        disk=mf.CrossSection.circle(.04,24).translate((x,y))
                        if (disk-best).area()<1e-7:
                            found={'centre_print_xy_mm':[float(x),float(y)],'top_mm':top,'minimum_land_diameter_mm':2*radius,
                                   'upper_jaw_thickness_mm':.8,'outward_approach_mm':72.,'direction_print':direction,
                                   'minimum_extra_side_margin_mm':.10,'available_position_area_mm2':best.area()}
                            break
                    if found:break
            if found:break
        result.append({'piece':r['name'],'file':r['file'],'grip':found})
    return result


def actual_access(records, out, checker, data, xyz, normal, owners):
    """Check both jaw lands and the entire upper-jaw approach in deposited PETG."""
    from build48 import b
    from native48 import digest
    past = []
    owners_kept = np.isin(data[:,6], [owners[n] for n in ('Key_Carrier','Release_tabs','Front_pull_shelf','Rear_pull_shelf')])
    for k,record in enumerate(records):
        grip = record['grip']
        if grip is None:
            continue
        front = k < len(records)-2
        owner = owners['Front_pull_shelf' if front else 'Rear_pull_shelf']
        x,y = grip['centre_print_xy_mm']
        top = grip['top_mm']
        direction = grip['direction_print']
        disk = mf.CrossSection.circle(.6,48).translate((x,y))
        here = ((abs(xyz[:,0]-x)<1.25) & (abs(xyz[:,1]-y)<1.25)
                & (data[:,6]==owner) & normal)
        material=[]
        for level in (.2, top):
            on=here & (abs(data[:,7]-level)<.001)
            footprint = checker.start_audit.bead_footprints(checker.q,xyz[on,:2],data[on,3]) if on.any() else mf.CrossSection()
            material.append((disk ^ footprint).area()/disk.area())
        # A 1.2-mm round jaw slides in from the unobstructed outer edge.
        # Conservative bead envelopes include both radius and sample spacing.
        dy=(xyz[:,1]-y)*direction
        dxy=np.hypot(xyz[:,0]-x,np.maximum(0.,-dy))
        radii=data[:,3]/2 + checker.STEP/2 + .0002
        colliding = (normal & owners_kept & (dxy <= .6+radii)
                     & (data[:,7] > top+.014) & (data[:,7]-data[:,4] < top+.85))
        # Printed helper pieces already removed in the displayed sequence
        # cannot obstruct an entry. Remove only uniquely attributable sampled
        # centres; any ambiguous/exterior samples remain as obstacles.
        for earlier, old_owner in past:
            near = colliding & (data[:,6]==old_owner)
            if not near.any():continue
            for z in np.unique(data[near,7]):
                ids=np.flatnonzero(near & (abs(data[:,7]-z)<.001))
                section=earlier.slice(float(z-np.median(data[ids,4])/2))
                matches=checker.q._inside(section.offset(.04),xyz[ids,:2])
                colliding[ids[matches]]=False
        blocked=int(colliding.sum())
        grip.update(native_gripped_disk_fraction=material, blocking_native_samples=blocked,
                    checked_helper_stl_sha256=digest(out/record['file']),
                    native_passed=bool(blocked==0 and min(material)>=.88))
        past.append((b.load(out/record['file']),owner))
    return records
