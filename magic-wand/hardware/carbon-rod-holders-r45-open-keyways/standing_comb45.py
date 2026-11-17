"""Finger-side print comb for overhangs hidden behind the previous guard row."""
import manifold3d as mf
import numpy as np
from shelf45 import band,box,grow,span,union,layer_solid

def make(body,tabs,cradle,*,lateral_clearance=.30):
    # The standing carrier's original round resting faces remain exposed
    # after the comb pulls in -printY. Do not displace the bed-side cradle.
    # This comb serves the rounded rests only. Socket-floor ledges are
    # backed by the separate locally clipped additive aprons. Keep the
    # helper out of their working space and omit the broad unused roof.
    domain=box(-.6,-4.9,50.2,19.)
    targets={}
    for z in (22.,25.2,28.4,31.8):
        if z==22.:
            window=box(16.3,5.,5.2,3.7)+box(45.9,5.1,3.2,2.1)
        else:
            window=box(9.,5.1,4.7,2.)+box(42.7,5.1,5.8,2.)+box(15.35,4.85,2.3,2.5)
        # Back the actual entire rounded return, including the second wall
        # after its U-turn. Do not limit the target to newly exposed CAD
        # alone: the native path lies inset from the true surface.
        targets[round(z/.2)-2]=body.slice(z-.1)^window
    for z,x,y,w,h in [(17.4,.4,11.9,4.3,1.5),(17.6,1.5,11.8,5.,1.7),
                       (32.6,24.1,10.8,2.1,1.6),(34.,27.65,10.35,1.30,1.92)]:
        targets[round(z/.2)-2]=body.slice(z-.1)^box(x,y,w,h)
    roads={k:span(grow(t,1.),0,-33.)^domain for k,t in targets.items()}
    teeth=union([box(x,-6.,1.55,21.) for x in np.arange(-1.4,51.,2.25)])
    bars=union([box(-.6,y,51.,1.2) for y in np.arange(-3.,15.,2.7)])
    spine=box(-.6,-4.7,50.2,2.75)
    # The protected left web is concealed from the bed. First find all
    # side-withdrawing, printable material in a bounded launch region,
    # then keep only the routes needed by the two measured web roofs.
    obstacles=body+tabs
    web_reach={};previous=None
    for k in range(1,87):
        z=k*.2
        native=obstacles.slice(z-.30)+obstacles.slice(z-.10)+obstacles.slice(z+.10)
        blocked=span(grow(band(obstacles,z-.215,z+.015)+native,lateral_clearance),0,72.)
        blocked+=grow(obstacles.slice(z-.30)+obstacles.slice(z+.10),.08)
        blocked+=grow(cradle.trim_by_plane((0,0,1),z-.205).project(),.68)
        legal=box(-8.,-6.,19.,24.)-blocked
        reach=legal if previous is None else legal^(grow(previous,.22)+body.slice(z-.5))
        previous=grow(grow(reach,-.27),.27).simplify(.02)
        web_reach[k]=previous
    web={};next_needed=mf.CrossSection()
    for k in reversed(range(1,87)):
        if k in (85,86):
            cap=grow(targets[k],.55)^web_reach[k]
            next_needed+=span(cap,0,-26.)
        section=web_reach[k]^grow(next_needed,.30)
        # Leave a connected land extending forward for withdrawal and grip.
        web[k]=section^box(-8.,-4.65,19.,22.65)
        next_needed=section
    solids=[];previous=None
    for k in range(1,max(targets)+1):
        z=round(k*.2,5)
        needed=union([r for h,r in roads.items() if h>=k])
        # The native whole-bead sweep checks all touching layer faces,
        # including the adjacent lower and upper extrusion levels. Use
        # their actual slicing planes in the construction shadow too.
        native_planes=obstacles.slice(z-.30)+obstacles.slice(z-.10)+obstacles.slice(z+.10)
        front=span(grow(band(obstacles,z-.215,z+.015)+native_planes,lateral_clearance),0,72.)
        # Actual material levels are selected on layer midplanes. Reserve
        # the empty layer beneath/above each tooth; complete prism and
        # native-bead withdrawal checks independently cover the full solids.
        gap=grow(obstacles.slice(z-.30)+obstacles.slice(z+.10),.08)
        # For every translating conventional rib, forbid any shelf bead at
        # the same XY below it. This leaves the original grounded web land.
        vertical=cradle.trim_by_plane((0,0,1),z-.205).project()
        blocked=front+gap+grow(vertical,.68)
        near=union([grow(t,1.35) for h,t in targets.items() if h-4<=k<=h])
        head=union([grow(t,.6) for h,t in targets.items() if h-1<=k<=h])
        frame=(needed^teeth)+(near^bars)
        # Each of the three left crosswise rests has a narrow return about
        # 4 mm long. Bring a continuous tooth to its turnaround in advance.
        frame+=needed^(box(9.,-5.,4.75,12.5)+box(15.35,-5.,2.3,12.5)+box(43.4,-5.,1.25,12.5)+box(.4,-5.,6.4,18.6)+box(24.1,-5.,2.1,17.1)+box(27.60,-5.,1.40,17.40))
        # A thin, shallow ledge beneath each native turning point needs
        # continuous top backing; each short finger stays separated by
        # full removal air and its contact area is checked independently.
        shape=(spine+frame+head)-blocked
        if previous is not None:
            earned=grow(previous,.245)+body.slice(z-.5)
            shape^=earned
        active=[c for c in shape.decompose() if (c^spine).area()>.02 or
                (previous is not None and ((c^previous).area()>.34 or (c^body.slice(z-.5)).area()>.35))]
        shape=union(active)
        if k in web:shape+=web[k]
        shape=grow(grow(shape,-.27),.27)
        shape=shape.simplify(.025)
        if k in web:
            # Rounding a printable web toe can close a tiny notch at the
            # old guard-wall corner. Recut the exact finite slab shadow
            # after simplifying; do not let a smoothed notch foul release.
            shape-=span(band(obstacles,z-.202,z+.002).offset(.055),0,72.)

        if not shape.is_empty():solids.append(layer_solid(shape,k))
        previous=shape
    pieces=sorted(mf.Manifold.batch_boolean(solids,mf.OpType.Add).decompose(),key=lambda s:-s.volume())
    kept=[pieces[0]]
    for piece in pieces[1:]:
        roof=sum((piece.slice(k*.2-.1)^targets[k]).area() for k in (85,86))
        if roof>.10 and piece.bounding_box()[2]<.00001:kept.append(piece)
    shelf=mf.Manifold.batch_boolean(kept,mf.OpType.Add)
    assert 1<=len(kept)<=2,[(p.volume(),p.bounding_box()) for p in kept]
    assert shelf.status()==mf.Error.NoError and shelf.volume()>300
    def collisions(shape):
        rows=[]
        heights=np.unique(np.round(np.asarray(shape.to_mesh().vert_properties)[:,2],5))
        for lo,hi in zip(heights[:-1],heights[1:]):
            if hi-lo<.00005:continue
            section=shape.slice(float((lo+hi)/2))
            hit=span(section,0,-72.)^band(obstacles,float(lo)-.00001,float(hi)+.00001)
            if hit.area()>.0001:rows.append((float(lo),float(hi),hit))
        return rows
    # At the new left shoulder a narrow sliver can foul the body after
    # the thin layers are unioned. For a -Y withdrawal the moving and
    # stationary points share X; only source points at/behind the hit in
    # Y could collide. Cut that full source strip with a 0.35-mm margin.
    initial=collisions(shelf)
    notches=[]
    before=shelf.volume()
    for lo,hi,hit in initial:
        assert 16.99<=lo<hi<=17.21, ('unexpected comb contact',lo,hi,hit.bounds())
        for patch in hit.decompose():
            x,y,X,Y=patch.bounds()
            clear=box(x-.35,y-.35,X-x+.70,Y-y+72.70)
            shelf-=clear.extrude(hi-lo+.012).translate((0,0,lo-.006))
            notches.append(dict(z=[lo,hi],hit_bounds=[x,y,X,Y],area_mm2=patch.area()))
    final=collisions(shelf) if initial else []
    conflicts=[(lo,hi,hit.area()) for lo,hi,hit in final]
    assert not conflicts,conflicts
    report=dict(owner='Front_pull_shelf',direction_print=(0.,-1.,0.),translation_mm=72.,
                bounds=shelf.bounding_box(),volume_mm3=shelf.volume(),whole_cad_conflicts=conflicts,
                actual_shoulder_notches=notches,shoulder_notch_removed_mm3=before-shelf.volume(),
                roof_tops_mm=[round(k*.2,2) for k in targets],
                contact_target_area_by_top={round(k*.2,2):(shelf.slice(k*.2-.1)^t).area() for k,t in targets.items()})
    report['required_separate_pieces']=[dict(name=name,volume_mm3=p.volume(),bounds=p.bounding_box(),
        first_layer_cad_area_mm2=p.slice(.1).area(),has_1p2mm_grip_land=not p.slice(.1).offset(-.6).is_empty())
        for name,p in zip(('finger-side comb','left guard web prop'),kept)]
    report['design_lateral_clearance_mm']=lateral_clearance
    report['generator_file']='standing_comb45.py'
    return shelf,report
