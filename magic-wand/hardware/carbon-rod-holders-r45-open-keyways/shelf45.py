"""Side-extracting comb beneath deck roofs hidden above the finger guards."""
from pathlib import Path
import json
import manifold3d as mf
import numpy as np

L=.2
NAME='Front_pull_shelf'
AXIS=(0.,-1.,0.)

def union(sections):
    return mf.CrossSection.batch_boolean(sections,mf.OpType.Add) if sections else mf.CrossSection()

def span(section,dx,dy):
    """Continuous 2D Minkowski sum with a line segment, preserving concavities."""
    if section.is_empty():return section
    return section.extrude(1.).transform([[1,0,dx,0],[0,1,dy,0],[0,0,1,0]]).project()

def box(x,y,w,h):
    return mf.CrossSection.square((w,h)).translate((x,y))

def band(body,low,high):
    return body.trim_by_plane((0,0,1),low).trim_by_plane((0,0,-1),-high).project()

def grow(section,distance):
    # Keep construction-only polygon resolution below nozzle resolution.
    # Complete final CAD and native sweep checks still use the full solids.
    return section.simplify(.025).offset(distance,mf.JoinType.Round,2.,12).simplify(.025)

def layer_solid(section,k):
    # Float arithmetic can leave consecutive decimal 0.2 mm planes
    # separated. Overlap by one micron to preserve the drawn common face.
    low=(k-1)*L
    overlap=.001 if k>1 else 0.
    return section.extrude(L+overlap).translate((0,0,low-overlap))

def make(body,tabs,*,rear=False):
    # Approach the concealed outer-deck roofs from -Y. Full solid and actual
    # bead withdrawal checks below determine whether this route is clear.
    # The rear uses the same comb design in a mirrored local frame.
    # Separate half-spaces leave a release seam between the two drawers.
    mirror=lambda s:s.mirror((0.,1.,0.)).translate((0.,42.,0.))
    if rear:body,tabs=mirror(body),mirror(tabs)
    domain=box(-.5,-5.,62.,24.0 if rear else 48.)
    grip=box(0.,-4.5,60.,2.6)
    targets={}
    for k in (61,62,63,64):
        z=k*L
        exposed=body.slice(z-.10)-grow(body.slice(z-.30),.20)
        # Only approach material hidden from direct bed-side withdrawal.
        old=grow(body.trim_by_plane((0,0,-1),-(z-.75)).project(),.5)
        targets[k-2]=((exposed if rear else exposed^old)^domain).simplify(.025)
    # Teeth follow -Y to the exposed spine, with sparse transverse bridges.
    plans={k:span(t,0,-55.)^domain for k,t in targets.items()}
    teeth=union([box(x,-5.,1.55,49.) for x in np.arange(-1.2,61.,2.85)])
    bars=union([box(-1.,y,63.,1.15) for y in np.arange(-3.,44.,3.25)])
    # A diagonally oriented narrow contact pattern prevents long bonded
    # roofs and intersects both transverse and longitudinal carrier paths.
    tips=union([box(x,-65.,.94,150.) for x in np.arange(-100.,101.,2.10)]).rotate(27)
    complete=[];previous=None;obstacles=body+tabs
    near_by_key={k:grow(t,2.) for k,t in targets.items()}
    head_by_key={k:grow(t,.9) for k,t in targets.items()}
    for k in range(1,max(targets)+1):
        z=round(k*L,4)
        live=union([p for h,p in plans.items() if h>=k])
        # Reserve the original cradle's supporting air beneath every lower
        # guard. Grow the side teeth across those guards only from above.
        forbidden=grow(band(obstacles,z-.21,11.68),.5) if z-.21<11.68 else mf.CrossSection()
        # Exclude collision for the complete slab as it translates out.
        collision=grow(band(obstacles,z-L-.015,z+.015),.60)
        roadblock=span(collision,0,72.)
        # Do not join the top of a guard: reserve one empty layer above
        # its surface. Keep an empty layer under the actual deck roof.
        clearance=grow(band(obstacles,z-L-.201,z+.105),.10)
        legal=live-roadblock-forbidden-clearance
        near=union([t for h,t in near_by_key.items() if k>=h-4 and k<=h])
        # Roots are 1.55 mm fore-aft strips. Transverse webs form just
        # below each target; the top two layers reduce to breakaway ridges.
        frame=(live^teeth)+(near^bars)
        head=union([t for h,t in head_by_key.items() if k>=h-1 and k<=h])
        frame=(frame-head)+(head^tips)
        now=(frame^legal)+(grip-roadblock-clearance)
        # The actual swept bead envelope caught a zero-height release seam
        # beside the front post on native layer 12.0. Lower this small tooth
        # area by one layer; the rear roof contact lands remain unchanged.
        if not rear and k>=60:now-=box(22.35,-.75,1.5,7.)
        # A narrow CAD spur here did not receive any rooted native bead
        # beneath its first 11.0-mm layer. Remove its upper column rather
        # than rely on a later layer to catch the loose strand.
        if not rear and k>=55:now-=box(34.05,17.75,.85,2.2)
        if previous is not None:
            now^=grow(previous,.24)
        now=now.simplify(.025)
        if k%10==0:print("Side shelf layer",k,flush=True)
        if not now.is_empty():complete.append(layer_solid(now,k))
        previous=now
    print("Joining shelf and checking whole withdrawal",flush=True)
    shape=mf.Manifold.batch_boolean(complete,mf.OpType.Add)
    pieces=sorted(shape.decompose(),key=lambda p:p.volume(),reverse=True)
    shelf=pieces[0]
    assert shelf.status()==mf.Error.NoError and shelf.volume()>200.
    assert abs(shelf.bounding_box()[2])<.00001 and shelf.bounding_box()[5]>12.39,shelf.bounding_box()
    # Prove whole sideways withdrawal at every slab of the retained solid.
    bad=[]
    vertices=np.asarray(shelf.to_mesh().vert_properties)
    heights=np.unique(np.round(vertices[:,2],5))
    # Each adjacent pair of distinct vertex heights bounds a prism with
    # exactly constant XY section. Check that entire prism, including
    # the one-micron joining steps, against every obstacle in its Z band.
    for bottom,top in zip(heights[:-1],heights[1:]):
        if top-bottom<.00005:continue
        foot=shelf.slice(float((bottom+top)/2))
        if foot.is_empty():continue
        swept=span(foot,0,-72.)
        contact=(swept^band(obstacles,float(bottom)-.00001,float(top)+.00001)).area()
        if contact>.0001:bad.append([float(bottom),float(top),contact])
    assert not bad,bad
    report=dict(owner=NAME,direction_print=AXIS,translation_mm=72.,bounds=shelf.bounding_box(),
        roof_tops_mm=[k*L for k in targets],volume_mm3=shelf.volume(),whole_cad_conflicts=bad,
        excluded_disconnected_mm3=[p.volume() for p in pieces[1:] if p.volume()>.00001],
        contact_target_area_by_top={round(k*L,2):(shelf.slice(k*L-.1)^t).area() for k,t in targets.items()})
    if rear:
        shelf=mirror(shelf)
        report.update(owner='Rear_pull_shelf',direction_print=(0.,1.,0.),bounds=shelf.bounding_box())
    return shelf,report

def clear_cradle(cradle,shelf):
    """Keep conventional strips below new side-shelf material during withdrawal."""
    top=cradle.bounding_box()[5];pieces=[]
    for k in range(1,round(top/L)+1):
        z=k*L
        old=cradle.slice(z-L/2)
        side=shelf.trim_by_plane((0,0,-1),-(z+.001)).project().offset(.65)
        ceiling=shelf.trim_by_plane((0,0,-1),-(z+.201)).project()
        section=old-side-ceiling
        # Side-shelf clipping exposed sub-nozzle corner columns. Their
        # actual deposits were 0.08-mm2 dots repeated without a rooted
        # lower bead. These are helper-only, not permanent carrier cuts.
        for x,y in ((43.76,8.17),(52.44,14.08),(35.31,17.60)):
            section-=box(x-.6,y-.6,1.2,1.2)
        if not section.is_empty():pieces.append(layer_solid(section,k))
    return mf.Manifold.batch_boolean(pieces,mf.OpType.Add)


def bind_report(directory,*,rear=False):
    """Bind the complete prism withdrawal proof to its exact exported solids."""
    import hashlib
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    report_path=directory/('rear-shelf-cad.json' if rear else 'shelf-cad.json')
    report=json.loads(report_path.read_text())
    report.setdefault('design_lateral_clearance_mm',.60)
    report['stl_sha256']={name:sha(directory/name) for name in
        (('R45-rear-pull-shelf.stl' if rear else 'R45-front-pull-shelf.stl'),'R45-Key-Carrier.stl','R45-release-tabs.stl')}
    companion=directory/('R45-front-pull-shelf.stl' if rear else 'R45-rear-pull-shelf.stl')
    if companion.exists():
        report['stl_sha256'][companion.name]=sha(companion)
        other=json.loads((directory/('shelf-cad.json' if rear else 'rear-shelf-cad.json')).read_text())
        separation=(report['bounds'][1]-other['bounds'][4] if rear else other['bounds'][1]-report['bounds'][4])
        if separation<=.65:
            rear_report=report if rear else other
            assert rear_report.get('generator_file')=='standing_aperture45.py'
            assert rear_report['whole_front_path_against_rear_cad_conflicts']==[]
        report['opposite_direction_shelf_y_separation_mm']=separation
    name=report.setdefault('generator_file','shelf45.py')
    assert name in ('shelf45.py','standing_comb45.py','standing_aperture45.py')
    src=Path(__file__).resolve().parent
    report['generator_sha256']=sha(src/name)
    report['generator_dependencies_sha256']={'shelf45.py':sha(src/'shelf45.py')} if name!='shelf45.py' else {}
    report_path.write_text(json.dumps(report,indent=2)+'\n')
