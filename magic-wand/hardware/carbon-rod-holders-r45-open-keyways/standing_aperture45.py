"""Expose the switch-clip roof to a small bed-rooted prop pulled towards +Y."""
import manifold3d as mf
import numpy as np
from shelf45 import box,band,grow,span,union,layer_solid

def make(body,tabs,cradle,front):
    # The hard switch-clip/latch envelope blocks an integral buttress.
    # Guide only the first, unbacked native turn and the thin centre bead.
    cap=(box(7.30,14.94,3.75,1.40)+box(12.1,16.29,1.15,1.02)
         +box(14.68,16.29,1.15,1.02))^body.slice(18.50)
    domain=box(6.8,14.5,9.6,9.1)
    teeth=box(7.30,14.5,3.75,9.1)+box(12.1,15.8,1.15,7.8)+box(14.68,15.8,1.15,7.8)
    grip=box(6.8,21.3,9.6,2.3)
    permanent=body+tabs;previous=None;layers=[]
    for k in range(1,92):
        z=k*.2
        sections=band(permanent,z-.215,z+.015)+permanent.slice(z-.30)+permanent.slice(z-.10)+permanent.slice(z+.10)
        blocked=span(grow(sections,.31),0,-72.)
        blocked+=grow(permanent.slice(z-.30)+permanent.slice(z+.10),.08)
        blocked+=grow(cradle.trim_by_plane((0,0,1),z-.205).project(),.68)
        blocked+=span(grow(band(front,z-.41,z+.21),.6),0,-72.)
        target=(span(grow(cap,.27),0,25.)^teeth)+grip
        if k<89:target+=box(6.8,19.1,9.6,1.25)
        legal=(target^domain)-blocked
        if previous is not None:legal^=grow(previous,.22)+body.slice(z-.50)
        previous=grow(grow(legal,-.25),.25).simplify(.015)
        if not previous.is_empty():layers.append(layer_solid(previous,k))
    pieces=mf.Manifold.batch_boolean(layers,mf.OpType.Add).decompose()
    rear=max(pieces,key=lambda p:(p.slice(18.1)^cap).area())
    conflicts=[];cross_conflicts=[]
    heights=np.unique(np.round(np.asarray(rear.to_mesh().vert_properties)[:,2],5))
    for lo,hi in zip(heights[:-1],heights[1:]):
        if hi-lo<.00005:continue
        section=rear.slice(float((lo+hi)/2))
        moving=span(section,0,72.)
        h=(moving^band(permanent,float(lo)-.00001,float(hi)+.00001)).area()
        if h>.0001:conflicts.append([float(lo),float(hi),h])
        swept_front=span(band(front,float(lo)-.00001,float(hi)+.00001),0,-72.)
        h=(swept_front^section).area()
        if h>.0001:cross_conflicts.append([float(lo),float(hi),h])
    contact=(rear.slice(18.1)^cap).area()
    assert not conflicts and not cross_conflicts
    assert rear.bounding_box()[2]<.00001 and contact>.3,(rear.bounding_box(),contact)
    return rear,dict(owner='Rear_pull_shelf',direction_print=(0.,1.,0.),translation_mm=72.,
        bounds=rear.bounding_box(),volume_mm3=rear.volume(),whole_cad_conflicts=conflicts,
        whole_front_path_against_rear_cad_conflicts=cross_conflicts,roof_tops_mm=[18.2],
        contact_target_area_by_top={18.2:contact},design_lateral_clearance_mm=.31,
        generator_file='standing_aperture45.py')
