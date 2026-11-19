"""Print-facing details of the R53 key carrier, in the same assembly frame as build53."""
import json
import os
from pathlib import Path
import tempfile

import manifold3d as mf
import numpy as np

import build53 as b


def cylinder(x,y,r,z0,z1,sy=1):
    return mf.Manifold.cylinder(z1-z0,r,r,36).scale((1,sy,1)).translate((x,y,z0))
def locator(y,side):
    # Swept strip alongside the soldered pin row. The root is rearward in the
    # build so the flexing leaf grows continuously toward its locating nose.
    cfg=[(side*5.35,y+5.9),(side*5.15,y+3.45),(side*4.05,y+1.55),(side*2.20,y+.06),(0,y)]
    beam_z=8.28; thickness=0.88
    lands=[cylinder(x,yy,.94 if i!=len(cfg)-1 else 1.40,beam_z,beam_z+thickness) for i,(x,yy) in enumerate(cfg)]
    beam=b.union(mf.Manifold.batch_hull([a,c]) for a,c in zip(lands,lands[1:]))
    root=cylinder(*cfg[0],1.30,7.25,beam_z+thickness)
    cyl=lambda h,r1,r2,z:mf.Manifold.cylinder(h,r1,r2,56).translate((0,0,z))
    nose=cyl(.43,1.40,1.47,beam_z+thickness-.05)+cyl(.87,1.47,.80,beam_z+thickness+.37)
    if side>0:nose=nose.scale((1,.84,1))
    nose=nose.translate((0,y,0))
    # From the rear-down build direction the nose must grow from the attached
    # side of the spring. A diagonal back edge retains two locating faces and
    # stops the far edge of the small round nib starting in mid-air.
    pts=[(side*x,y+dy) for x,dy in [(-2.3,-2.32),(2.3,2.74),(2.3,3.2),(-2.3,3.2)]]
    release=b.prism_xy(pts,beam_z-.20,beam_z+4)
    beam-=release
    nose-=release
    # Make the base of the locating nib the first feature to grow.
    tip_back=b.prism_yz([(y+.25,beam_z+thickness),(y+2.2,beam_z+thickness),(y+2.2,11),(y-.80,11)],-1.8,1.8)
    nose-=tip_back
    # Clear the full bent beam and leave side clearance in the printed pocket.
    cavity_points=[cylinder(x,yy,1.54 if i!=len(cfg)-2 else 1.98,6.88,9.55) for i,(x,yy) in enumerate(cfg[1:])]
    # The rear portion is intentionally embedded and tapers into the sheet.
    cavity_points.insert(0,cylinder(cfg[0][0],cfg[0][1]-.82,1.6,7.0,9.53))
    gap=b.union(mf.Manifold.batch_hull([a,c]) for a,c in zip(cavity_points,cavity_points[1:]))
    return tuple(b.to_world(s) for s in (gap,beam+root+nose,root,beam,nose))
def add_locators(body):
    for y,side in [(-6.25,-1),(11.65,1)]:
        gap,positive,root,beam,nose=locator(y,side)
        body-=gap
        if (root ^ body).volume() < 1.5:
            raise ValueError('OP1 locator lost its root')
        body+=positive
    return body


def bevel_lower_edges(source,destination):
    obj=b.load(source).rotate((-90,0,0)); bottom=obj.bounding_box()[2]
    obj=obj.translate((0,0,-bottom)); cuts=[]
    rect=lambda x1,x2,z1,z2:mf.CrossSection.square((x2-x1,z2-z1)).translate((x1,z1))
    # Each range is selected from the unsupported strands in the actual printer paths.
    # Columns are print-layer number followed by the local X/Z limits in assembly units.
    for layer,regions in [(110,[(-32,-6,-1,6),(6,32,-1,6)])]:
        base_z=(layer-1)*.2
        mask=mf.CrossSection.batch_boolean([rect(*v) for v in regions],mf.OpType.Add)
        # Use the real preceding layer with a two-wall seed and small printable bridges.
        ref=(obj.slice(base_z-.10) ^ mask.offset(9)).simplify(.012)
        stable=ref.offset(-.17).offset(.17).simplify(.015)
        stable=stable.offset(.62).offset(-.62).simplify(.015)
        for i in range(50):
            height=base_z+i*.2
            # The mask retreats into genuinely supported geometry at a printable slope.
            cut=mask-stable.offset((i+.35)*.135,mf.JoinType.Round,2.,16)
            if cut.is_empty():break
            section=(cut^obj.slice(height+.10)).area()
            if section>.002:
                cuts.append(cut.extrude(.20004).translate((0,0,height-.00002)))
        print('edge',layer,'cuts so far',len(cuts),flush=True)
    ans=obj-b.union(cuts)
    parts=sorted(ans.decompose(),key=lambda p:-p.volume())
    print('removed',obj.volume()-parts[0].volume(),'other solids', [round(p.volume(),5) for p in parts[1:8]],flush=True)
    destination.parent.mkdir(parents=True,exist_ok=True)
    b.save(destination,parts[0].translate((0,0,bottom)).rotate((90,0,0)))

def round_unsupported_corners(source, destination):
    model = b.load(source).rotate((-90,0,0))
    bottom = model.bounding_box()[2]
    model = model.translate((0,0,-bottom))
    sketches = json.loads((Path(__file__).with_name("supported-sections.json")).read_text())
    cuts = []
    for profile in sketches:
        x0,x1,z0,z1 = profile["window"]
        mask = mf.CrossSection.square((x1-x0,z1-z0)).translate((x0,z0))
        seed = mf.CrossSection(profile["supported_outlines"],mf.FillRule.EvenOdd)
        for step in range(33):
            h=(profile["first_layer"]-1+step)*.2
            cut=mask-seed.offset(.10+step*.14,mf.JoinType.Round,2.,20)
            if cut.is_empty():
                break
            if (cut ^ model.slice(h+.1)).area() > .003:
                cuts.append(cut.extrude(.20004).translate((0,0,h-.00002)))
    model -= b.union(cuts)
    model = max(model.decompose(),key=lambda p:p.volume()).translate((0,0,bottom)).rotate((90,0,0))
    # The rigid outside edges of the separate OP1 lid have a running clearance.
    for side, stop in zip((-1,1), b.TINE_END):
        x0,x1 = sorted([side*(b.LID_HALF-.26),side*(b.RAIL_WALL[0]+.18)])
        model -= b.ubox(x0,x1,-12,stop+.08,b.LID_Z[0]-.14,b.RAIL_LIP[1]-.04)
    b.save(destination,model)


def puck(c,rx,rz,dy):
    return mf.Manifold.cylinder(dy,1,1,36).scale((rx,rz,1)).rotate((90,0,0)).translate((c[0],c[1]+dy/2,c[2]))
def add_backing(src,out):
    m=b.load(src)
    low=[((-12.78,9.55,1.78),(-12.01,8.35,1.48)),((13.16,9.35,1.64),(12.37,8.15,1.38)),((10.43,10.75,7.42),(9.02,6.75,5.15)),((13.99,10.55,1.81),(11.03,6.55,2.49))]
    solids=[mf.Manifold.batch_hull([puck(a,.48,.53,.58),puck(z,.61,.53,.65)]) for a,z in low]
    # The socket sweeps across this former lower lip. Make the underside slope
    # continuously up into the sidewall, avoiding all plastic in the socket path.
    relief=b.prism_yz([(-10.0,-10.0),(23.0,-10.0),(23.0,3.4),(18.0,10.15),(15.8,9.3),(4.0,2.25),(-10.0,-7.0)],-33,-24)
    m-=relief
    rail=mf.Manifold.batch_hull([puck((11.49,9.2,11.25),.70,.42,1.2),puck((9.84,5.52,11.37),.44,.35,.75)])
    # Keep the whole board envelope free, including its straight-down insertion.
    ar=b.union(solids+[rail])-b.ubox(-5.38,5.38,-9.47,21.4,9.06,40)
    tie=mf.Manifold.batch_hull([puck((13.02,11.65,11.40),.44,.38,.82),
                                puck((11.58,9.55,11.37),.50,.38,.78)])
    parts=sorted((m+ar+tie).decompose(),key=lambda s:-s.volume())
    print('Guide and rib overlap, mm3', (ar^m).volume(), (tie^m).volume(), flush=True)
    b.save(out,parts[0])


def clear_left_sill(body):
    pose=body.rotate((-90,0,0));bottom=pose.bounding_box()[2];o=pose.translate((0,0,-bottom))
    band=mf.CrossSection.square((10.5,30.0)).translate((-34.,-5.25))
    nearby=band.offset(3)
    prior=o.slice(28.30)^nearby
    cuts=[]
    for index in range(143,259):
        h=(index-1)*.2
        now=o.slice(h+.10)^nearby
        if now.is_empty():break
        printable=prior.offset(-.19).offset(.19).simplify(.008)
        allowed=printable.offset(.115,mf.JoinType.Round,2,24)
        cut=(now^band)-allowed
        if not cut.is_empty() and cut.area()>.0005:
            # Extend the planar cutters slightly to keep the engraving manifold at steps.
            cuts.append(cut.offset(.006).extrude(.20002).translate((0,0,h-.00001)))
        prior=(now-band)+(now^band^allowed)
    result=o-b.union(cuts)
    parts=sorted(result.decompose(),key=lambda s:-s.volume())
    print('left underside relief',round(o.volume()-parts[0].volume(),3),'slices',len(cuts),'detached',[round(x.volume(),5) for x in parts[1:5]],flush=True)
    return parts[0].translate((0,0,bottom)).rotate((90,0,0))


def connector_clearance(body):
    # The pre-wired PCB can enter off-centre before the two tapered eyelet pins seat.
    body-=b.ubox(-4.14,4.14,14.39,21.71,6.31,9.45)
    # The leading right edge of an off-centre board passes the back of the lid guide.
    body-=b.ubox(4.96,5.55,10.80,18.1,9.33,13.55)
    # Keep the R52 Choc latch and its bearing plane; ease the small inside
    # corner where a deposited R53 inner wall approached the switch case.
    body-=b.box(15.72,16.57,-7.78,-6.96,12.00,12.70)
    return max(body.decompose(),key=lambda p:p.volume())


def remove_microtips(body):
    """Erase isolated rear-facing ramp tips smaller than a printable wall."""
    model = body.rotate((-90,0,0))
    base = model.bounding_box()[2]
    model=model.translate((0,0,-base))
    previous = model.slice(.10)
    cutters=[]
    skipped=[]
    for layer in range(2,258):
        h=(layer-1)*.2
        cs=model.slice(h+.10)
        backed=previous.offset(.032)
        cut_sections=[]
        for component in cs.decompose():
            if component.area()<.001 or not (component ^ backed).is_empty():
                continue
            bounds=component.bounds()
            # This lower finger-rest wall in the measured R52-derived print
            # is continuously extruded. Removing its thin start lets an entire
            # 4.27 mm² patch appear in the air farther along the same wall.
            if 100 <= layer <= 150 and bounds[0] < -19 and bounds[2] > -26 and bounds[1] < 4:
                continue
            if component.area()>8.0:
                skipped.append((layer,round(component.area(),3)))
                continue
            cut=component.offset(.095,mf.JoinType.Round,2,24)
            cut_sections.append(cut)
            cutters.append(cut.extrude(.2001).translate((0,0,h-.00005)))
        previous=cs-mf.CrossSection.batch_boolean(cut_sections,mf.OpType.Add) if cut_sections else cs
    if cutters:
        model-=b.union(cutters)
    print("Sub-bead tip clearance", len(cutters), "larger cross-sections", skipped[:15],flush=True)
    return max(model.decompose(),key=lambda p:p.volume()).translate((0,0,base)).rotate((90,0,0))


def finish(source):
    """Round-trip each derived body at the precision of the printable STL."""
    with tempfile.TemporaryDirectory(dir=os.environ.get("AGENT_SCRATCH_DIR")) as folder:
        tmp = Path(folder)
        located = add_locators(b.load(source))
        b.save(tmp/"located.stl",located)
        cleaned = max(b.load(tmp/"located.stl").decompose(),key=lambda p:p.volume())
        b.save(tmp/"cleaned.stl",cleaned)
        bevel_lower_edges(tmp/"cleaned.stl",tmp/"bevel.stl")
        round_unsupported_corners(tmp/"bevel.stl",tmp/"radii.stl")
        add_backing(tmp/"radii.stl",tmp/"backed.stl")
        b.save(tmp/"sill.stl", clear_left_sill(b.load(tmp/"backed.stl")))
        solid = connector_clearance(b.load(tmp/"sill.stl"))
        return remove_microtips(solid).simplify(.0008)


def finger_rest_brace_envelope():
    """The sloped underside reinforcement before trimming for the two key sockets."""
    root = puck((-23.75, 13.60, 8.31), .61, .52, 1.08)
    tip = puck((-23.69, 6.52, 2.04), .57, .48, .92)
    return mf.Manifold.batch_hull([root, tip])


def finger_rest_brace():
    from openings53 import key_spaces
    brace = finger_rest_brace_envelope().rotate((-90, 0, 0))
    box = brace.bounding_box()
    neighbors = []
    for key, poses in key_spaces().items():
        if key.startswith(("key_0_", "key_3_")):
            for pose in poses:
                rotated = pose.rotate((-90, 0, 0))
                bounds = rotated.bounding_box()
                if all(box[i] - .55 < bounds[i+3] and bounds[i] < box[i+3] + .55 for i in range(3)):
                    neighbors.append((rotated, bounds))
    cuts = []
    window = mf.CrossSection.square((2.0, 8.5)).translate((-24.8, 1.0))
    for station in range(58, 144, 2):
        h = -station * .1
        outlines = [shape.slice(z) for shape, bounds in neighbors
                    for z in (h-.28, h, h+.28) if bounds[2] < z < bounds[5]]
        if outlines:
            clearance = mf.CrossSection.batch_boolean(outlines, mf.OpType.Add).offset(.32) ^ window
            if not clearance.is_empty() and not (clearance ^ brace.slice(h)).is_empty():
                cuts.append(clearance.extrude(.2002).translate((0, 0, h-.1001)))
    return (brace - b.union(cuts)).rotate((90, 0, 0))


def brace_finger_rest(body):
    return max((body + finger_rest_brace()).decompose(), key=lambda part: part.volume())
