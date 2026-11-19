"""Broad bed panels with a one-layer peel seam on the outside of each real part."""
import manifold3d as mf
import numpy as np


def rectangle(x,y,w,h):
    return mf.CrossSection.square((w,h)).translate((x-w/2,y-h/2))


def oriented_tab(p, normal, length, width):
    tangent=np.array([-normal[1],normal[0]])*width/2
    start=p-normal*.38
    end=p+normal*length
    corners=[start-tangent,end-tangent,end+tangent,start+tangent]
    return mf.CrossSection([np.array(corners)])


def backed_panel(shape, panel):
    lo=np.array(shape.bounding_box()[:2]);hi=np.array(shape.bounding_box()[3:5])
    centre=(lo+hi)/2
    w,h=panel['size']
    outside=rectangle(*centre,w,h)
    outside=outside.offset(-1.3).offset(1.3, circular_segments=24)
    full=shape.project().hull().offset(1.05)
    bed=shape.slice(.10)
    vertices=np.concatenate(bed.to_polygons())
    if panel.get('clip_mouth'):
        # Cut an open lane all the way out of the panel, including the second
        # layer. A support/brim crossing a nominally clear hole failed in R52.
        dx,dy=panel['clip_mouth']
        direction=np.array([dx,dy],float)
        direction/=np.linalg.norm(direction)
        start=centre+direction*.2
        outside-=oriented_tab(start,direction,max(w,h)*2,4.8)
    ring=outside-full
    if ring.is_empty() or len(ring.decompose())!=1:
        raise ValueError('Panel is missing or divided')
    tabs=[]
    for normal in panel['ties']:
        n=np.array(normal,dtype=float)
        n/=np.linalg.norm(n)
        side=vertices@n
        # Choose a real edge point near the middle of the outermost face.
        edge=vertices[side>side.max()-.12]
        mid=edge.mean(axis=0)
        p=edge[np.argmin(np.linalg.norm(edge-mid,axis=1))]
        far=max(np.concatenate(full.to_polygons())@n)-p@n+1.35
        tabs.append(oriented_tab(p,n,far,panel.get('tie_width',3.0)))
    ties=mf.CrossSection.batch_boolean(tabs,mf.OpType.Add)
    combined=shape+ring.extrude(.40)+ties.extrude(.20)
    if sum(abs(s.volume())>1e-6 for s in combined.decompose())!=1:
        raise ValueError('A panel or tear tab missed the part')
    return combined
