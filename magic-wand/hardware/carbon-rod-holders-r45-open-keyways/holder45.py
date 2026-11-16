"""R45 external print cradle. The bought hardware, carrier and finger rests compose R44.

The mould withdraws straight down: each higher horizontal section is a subset
of the previous one. No hooks, enclosed supports or material threaded through
the hardware. Closely spaced freestanding strips let the mesh bridge between
edges. Print and physical verification remain separate.
"""
from pathlib import Path
import sys
import numpy as np
import manifold3d as mf
HERE=Path(__file__).resolve().parent
R44=HERE.parent/'carbon-rod-holders-r44-middle-finger-rest'
sys.path.insert(0,str(R44))
import carrier_checks44 as inherited

LAYER=.2
PITCH=8.0
WIDTH=6.25
GAP=.2
MARGIN=.48

def combine(sections):
    return mf.CrossSection.batch_boolean(sections,mf.OpType.Add) if sections else mf.CrossSection()

def underside_cradle(model, frame):
    """Design in print coordinates with the bed at Z=0; all units millimetres."""
    inv=np.linalg.inv(frame)[:3]
    zones=inherited.routes()[0][inherited.d.CARRIER]
    from regions45 import fixed_endpoints
    keep=[];pad_no_go=[];foot_no_go=[];key_daylight=[]
    for name,region in zones.items():
        poses=list(region.poses()) if hasattr(region,'poses') else [region]
        for pose in poses:
            placed=pose.transform(inv)
            if placed.bounding_box()[2]<2*LAYER+.21:
                foot_no_go.append(placed.trim_by_plane((0,0,-1),-(2*LAYER+.21)).project())
                if placed.bounding_box()[2]<LAYER+.21:
                    pad_no_go.append(placed.trim_by_plane((0,0,-1),-(LAYER+.21)).project())
        if name.endswith('_mount_opening'):
            key_daylight.append(poses[0].transform(inv).project())
        # These helpers are removed before fitting hardware. Keep the native
        # CADAUX geometry outside the rod clip splits and hinge bores; the
        # remaining fit volumes are audited explicitly before/after cleanup.
        # Whole CAD and actual-bead withdrawal must pass, including seated
        # spaces, before any temporary occupancy is accepted.
        strict = name.startswith('clip_gap') or 'hinge' in name
        for pose in (fixed_endpoints(name,poses) if strict else []):
            p=pose.transform(inv)
            b=p.bounding_box()
            if b[2]<model.bounding_box()[5]:
                keep.append((b[2],b[5],p))
    keep.sort(key=lambda pair:pair[0])
    x0,y0,_,x1,y1,z1=model.bounding_box()
    # Broad, hollow-sliced peel strips give small starts a continuous roof.
    # The diagonal seams provide separate edges for release.
    length=(x1-x0+y1-y0)*2
    def stripes(pitch,width,angle,phase=0):
        return combine([mf.CrossSection.square((width,length)).translate((x+phase,-length/2))
                      for x in np.arange(-length,length,pitch)]).rotate(angle)
    # Separate broad grip lands with real peel/cutter lanes on two axes.
    ribs=stripes(PITCH,WIDTH,29)^stripes(18.,16.4,-61)
    # Last three layers are narrow breakaway ridges, not broad PETG roofs.
    tips=stripes(2.4,.85,-31)
    # A narrow outer frame land fell between the regular tip stripes. Give
    # that named first face its own small contact patch, without adding any
    # permanent material or extending a helper into another part.
    c=inv@np.array([-28.3476,20.1574,7.3534,1.])
    tips+=mf.CrossSection.square((2.4,2.4),center=True).translate(c[:2])
    # Three downward-facing starts identified in the keys-down slice:
    # both short front posts and the adjustable screw's flat landing.
    # Fill a seam here if needed; the same hard no-go cuts apply to them.
    for x,y in [(-9.4,-7.77),(9.4,-7.77),(8.3,-3.6)]:
        c=inv@np.array([x,y,12.,1.])
        ribs+=mf.CrossSection.square((5.,5.),center=True).translate(c[:2])
        tips+=mf.CrossSection.square((.85,4.2),center=True).translate(c[:2])
    # Bed-visible anchor lands for actual bridge ends at the rear saddle,
    # and for the few reachable portions of the long outer-deck walls.
    # Restrict additions to columns first meeting the underside at Z12.2/12.4.
    deck=(model.trim_by_plane((0,0,-1),-12.36).project()
         -model.trim_by_plane((0,0,-1),-11.76).project().offset(.55))
    base_lands=[];roof_lands=[]
    def land(x,y,width,length,stem=2.5):
        pt=(inv@np.array([x,y,7.3,1.]))[:2]
        base_lands.append(mf.CrossSection.square((stem,max(length,stem)),center=True).translate(pt))
        roof_lands.append(mf.CrossSection.square((width,length),center=True).translate(pt))
    for x,first,last in ((-6.11,18.2,31.4),(-8.82,18.2,31.4),(8.88,24.6,31.4)):
        # Alternate short roof ridges. Closed skin on a long contact wall
        # would increase PETG removal force on the complete holder.
        for y in np.arange(first,last+.2,2.65):
            land(x,y,1.2,2.15)
            # An inset tip at the longitudinal seam backs the inboard
            # portion of the next native stroke without joining roof pads.
            inset=x+(1.35 if x<0 else -1.35)
            land(inset,y+1.325,.9,1.15,2.1)
    for x,y in [(4.9,25.47),(5.7,25.08),(6.6,24.69),
                (8.12,1.),(11.29,-.49),(10.52,11.72),(6.15,6.88),
                (23.8,1.16),(-.77,-7.59),(-3.97,-6.90),(-4.53,5.11),
                (-17.45,11.64),(-9.87,14.95),(-11.29,-.64)]:
        land(x,y,1.25,1.7)
    ribs+=combine(base_lands)^deck
    tips+=combine(roof_lands)^deck
    # Only material below an actual first-hit underside; not a full bed slab.
    # Hard apertures are excluded at their real height by blocked(). Their
    # projection must not also forbid removable support BELOW the intentional
    # socket floors: that would leave the floors suspended for no fit reason.
    footprints=[]; allowed=model.project()^ribs
    # Actual slices found a 0.15 mm² isolated deposit repeated from Z5.8
    # through Z11.8 without any grounded bead beneath it. No carrier
    # component starts on this shaving. Clear its full column.
    allowed-=mf.CrossSection.square((1.9,1.65),center=True).translate((47.30,17.52))
    done=set()
    def blocked(z):
        partial=[]
        for i,(lo,hi,p) in enumerate(keep):
            if lo>z+.21:break
            if i in done:continue
            if hi<=z+.21:
                partial.append(p.project());done.add(i)
            else:
                partial.append(p.trim_by_plane((0,0,-1),-(z+.21)).project())
        return combine(partial).offset(MARGIN)
    bed_exclusions=combine(pad_no_go).offset(MARGIN)
    feet=model.slice(LAYER/2)
    tabs=(feet.offset(3)-feet.offset(-.08))-bed_exclusions
    if abs(frame[2,2])<.9:
        # On an inclined carrier the lower and upper contours of the first
        # layer differ. Do not assign any of its swept material to the tab
        # owner: Studio refused the intersecting paths at 220 degrees.
        occupied=model.trim_by_plane((0,0,-1),-(LAYER+.001)).project()
        tabs-=occupied.offset(.025)
    # Reserve the pad before designing the cradle; the carrier must have
    # its own bed anchor, independent of the separate hollow peel strips.
    allowed-=tabs.offset(.35)
    for k in range(1,int(z1/LAYER)+1):
        z=k*LAYER
        # Clip every full loaded/moving pose to the height reached so far.
        # A low wire leg must not cast the silhouette of a higher socket
        # across an otherwise accessible supporting land.
        allowed-=blocked(z)
        # The slicer samples the next part layer at its midpoint. Leave
        # one whole nominal layer between the support top and part bottom.
        ceiling=z+GAP-LAYER*.5+.001
        shadow=model.trim_by_plane((0,0,-1),-ceiling).project()
        # Keep a lateral release seam beside vertical walls. Separately
        # retain the Z-gap contour directly under roofs.
        side_shadow=model.trim_by_plane((0,0,-1),-(z-.001)).project()
        footprint=allowed-shadow-side_shadow.offset(.52)
        if footprint.is_empty():break
        footprints.append(footprint)
    shells=[]
    for i,foot in enumerate(footprints):
        # The top .60 mm of each free column is a thin sacrificial ridge.
        deeper=footprints[i+3] if i+3<len(footprints) else mf.CrossSection()
        shells.append((foot^tips)+deeper)
    # A footprint that only shrinks cannot join an adjacent foot later.
    # Prune all tiny columns in 2D before the final extrusion. Reserve
    # a stable flare for each necessary small peel piece.
    base_sections=shells[0].decompose()
    keep_feet=[f for f in base_sections if not f.offset(-.6).is_empty()]
    foot_mask=combine(keep_feet)
    foot_excluded=(combine(foot_no_go).offset(MARGIN)+tabs.offset(.65)
        +model.trim_by_plane((0,0,-1),-(2*LAYER+.21)).project().offset(.65))
    flares=[]
    for foot in keep_feet:
        if foot.area()<10.:
            base=foot.offset(1.7)-foot_excluded-(foot_mask-foot).offset(.8)
            flares.extend(b for b in base.decompose() if (b^foot).area()>.1)
    # A 0.17 mm² actual bed extrusion at this location stayed separate from
    # its own 84 mm² foot until Z11.4. Fuse their bases on the bed itself.
    tie=mf.CrossSection.circle(2.35,36).translate((45.05,31.53))-foot_excluded
    flares.extend(t for t in tie.decompose() if (t^foot_mask).area()>.5)
    flares=combine(flares)
    sections=[]
    for i,shell in enumerate(shells):
        section=shell^foot_mask
        if i<2:section+=flares
        if not section.is_empty():sections.append(section.extrude(LAYER).translate((0,0,i*LAYER)))
    cradle=mf.Manifold.batch_boolean(sections,mf.OpType.Add)
    # Contour tabs for the carrier bed contacts. Cut all routes reaching the bed,
    # including the clip splits where a native outer brim crossed the slit.
    if np.allclose(frame[:3,:3],[[1,0,0],[0,0,-1],[0,1,0]],atol=1e-8):
        # This web begins at standing Z17.6 as a 4.05 x .20 mm line.
        # An ordinary rib clipped to the carrier's projection cannot
        # develop a stable foot here. Grow a separate grounded land beyond
        # the exterior silhouette, with a narrow tooth under the web.
        landing=mf.CrossSection.square((9.4,3.4)).translate((-4.,9.55))
        shadows=model.trim_by_plane((0,0,-1),-17.201).project().offset(.62)
        ceiling=model.trim_by_plane((0,0,-1),-17.301).project()
        legal=landing-shadows-ceiling
        contact=mf.CrossSection.square((7.6,1.12)).translate((-3.,10.62))^legal
        web=mf.CrossSection.square((4.05,.2)).translate((0.,11.08133))
        assert (contact^web).area()>.3,('standing guard web contact',(contact^web).area())
        foot=max(legal.decompose(),key=lambda f:(f^contact).area())
        contact^=foot
        # A tab shares a single low plane with the cradle. Cut its local
        # notch only outside the actual carrier bed material, so the new
        # land can retreat down with all other pieces after cooling.
        tabs-=foot.offset(.7)
        cradle+=foot.extrude(16.6)+contact.extrude(.601).translate((0.,0.,16.599))
        for x0,x1 in ((16.5,21.4),(45.9,49.2)):
            # The following rounded middle-rest face is also directly
            # visible from the bed. End these existing-cradle lands one
            # empty native layer below it; no lateral shelf is needed.
            area=mf.CrossSection.square((x1-x0,3.5)).translate((x0,5.05))
            top=21.6
            legal=area-model.trim_by_plane((0,0,-1),-(top+.001)).project().offset(.5)
            legal-=model.trim_by_plane((0,0,-1),-(top+.101)).project()
            for pad in legal.decompose():
                if pad.offset(-.56).is_empty():continue
                tabs-=pad.offset(.70)
                cradle+=pad.extrude(top)
        # The two front hinge roof corners have unobstructed paths to
        # the bed. Give each a stable flared land and short narrow tip.
        for x in (20.65,39.45):
            top=39.4
            area=mf.CrossSection.square((5.3,5.1),center=True).translate((x,16.85))
            shadow=model.trim_by_plane((0,0,-1),-(top+.001)).project().offset(.54)
            ceiling=model.trim_by_plane((0,0,-1),-(top+.101)).project()
            legal=area-shadow-ceiling
            roof=mf.CrossSection.square((2.35,1.5),center=True).translate((x,16.66))^legal
            for base in legal.decompose():
                cap=roof^base
                if cap.area()<.35 or base.offset(-.62).is_empty():continue
                tabs-=base.offset(.72)
                cradle+=base.extrude(top-.6)+cap.extrude(.601).translate((0,0,top-.601))
        # Three small, one-layer ties along exposed rear contact edges.
        # The original positive seam only grazed the carrier over 0.013
        # square millimetres. Leave wider approach and fitting openings
        # clear. Only the disposable tie ends overlap the outer contour.
        fingers=combine([mf.CrossSection.circle(1.24,32).translate(xy)
                         for xy in ((26.4,25.58),(35.55,19.87),(24.55,19.87))])
        fingers=(fingers-feet.offset(-.085))-bed_exclusions
        fingers-=cradle.project().offset(.65)
        tabs+=fingers
    diamond=np.array([[2**-.5,0.,-2**-.5],[-2**-.5,0.,-2**-.5],[0.,1.,0.]])
    if np.allclose(frame[:3,:3],diamond,atol=1.e-8):
        # The rolled carrier has distinct bed corners. Keep a removable
        # broad first-layer foot at each, with two narrow deliberate ties
        # on its own exposed contour and no material in a paid-part route.
        for foot in feet.decompose():
            x,y,X,Y=foot.bounds();cx=(x+X)/2;cy=(y+Y)/2
            spokes=mf.CrossSection.square((.95,Y-y+12.),center=True).translate((cx,cy))
            spokes+=mf.CrossSection.square((X-x+12.,.95),center=True).translate((cx,cy))
            outside=foot.offset(4.4)-model.trim_by_plane((0,0,-1),-(LAYER+.001)).project().offset(.025)
            ties=spokes^(foot.offset(.65)-foot.offset(-.085))
            tabs+=(outside+ties)-bed_exclusions-cradle.project().offset(.65)
    return cradle,tabs.extrude(LAYER)
