"""Report long unbacked printable spans, in travel order, with actual support and the prior layer."""
from pathlib import Path
import sys

import numpy as np

R45=Path(__file__).resolve().parent.parent/'carbon-rod-holders-r45-open-keyways'
sys.path.insert(0,str(R45))
from grounded45 import trace
from native_order45 import map_moves


def intervals(values):
    return np.flatnonzero(np.diff(np.r_[False,values,False].astype(int))).reshape(-1,2)


def inspect(layer, points, origin, grid, lower, support, old_support, lines, sequences):
    if layer==1:return []
    xy=points[:,:2]
    ij=np.rint((xy-origin)/grid).astype(int)
    x,y=ij.T
    # Up to ~half the current bead can overlap material or a support roof.
    direct=lower[y,x] | support[y,x] | old_support[y,x]
    if direct.all(): return []
    moves=np.r_[0,np.flatnonzero(np.diff(lines))+1,len(points)]
    seq=np.r_[0,np.flatnonzero(np.diff(sequences))+1,len(points)]
    lengths=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    reach=trace(xy,points[:,3],direct,moves,seq,lengths)
    missed=~np.isfinite(reach)
    if not missed.any():return []
    issues=[]
    for a,b in zip(seq[:-1],seq[1:]):
        for start,stop in intervals(missed[a:b]):
            i=a+start-int(start>0);j=a+stop-1+int(stop<b-a)
            path=xy[i:j+1]
            length=float(np.sum(lengths[i:j]))
            if length<1.: continue
            chord=path[-1]-path[0];den=float(chord@chord)
            t=np.clip(((path-path[0])@chord)/den,0,1) if den>1e-9 else np.zeros(len(path))
            bend=float(np.linalg.norm(path-path[0]-t[:,None]*chord,axis=1).max())
            two=(start>0 and stop<b-a)
            if two and bend<=float(points[i:j+1,3].min())/2 and length+reach[i]+reach[j]<=12.:continue
            issues.append(dict(layer=layer,mm=round(length,3),two_anchors=bool(two),bend_mm=round(bend,3),
                midpoint_machine_xy=[round(float(v),3) for v in path[len(path)//2]],
                extent_machine_xy=[round(float(v),3) for v in [*path.min(0),*path.max(0)]],
                gcode_lines=[int(lines[i]),int(lines[j])]))
    return issues
