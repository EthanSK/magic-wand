"""One-generation check of previously anchored same-layer paths, in native order.

Never credit the run under review or a later neighbour. A short bridge line
must already be anchored at BOTH ends to the preceding layer; a non-bridge
stroke must have every sampled centre backed by the preceding layer.
"""
import numpy as np

def grounded_strokes(xy,idx,good,labels):
    delta=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    # extrusion_points includes both endpoints for each individual native
    # positive-E move, so repeated coordinates separate contiguous moves.
    cuts=np.r_[0,np.flatnonzero((np.diff(idx)!=1)|(delta>.151)|(delta<1e-7))+1,len(idx)]
    grounded=np.zeros(len(xy),bool)
    for a,b in zip(cuts[:-1],cuts[1:]):
        g=good[a:b]
        if g.all() or (g[0] and g[-1] and (labels[a:b]=='Bridge').all() and delta[a:b-1].sum()<=12.):
            grounded[a:b]=True
    return grounded

def earlier_contacts(q,starts,xy,widths,rooted,first,last):
    trace=xy[first:last+1]
    # Earlier means before even the first point of the suspect excursion.
    # Bounding rejection keeps every previous bead that can intersect it.
    margin=float(widths.max())+.05;lo=trace.min(0)-margin;hi=trace.max(0)+margin
    eligible=rooted[:first] & ((xy[:first]>=lo)&(xy[:first]<=hi)).all(1)
    if not eligible.any():return {'earlier_anchor_samples':0,'longest_residual_run_mm':float(np.linalg.norm(np.diff(trace,axis=0),axis=1).sum())}
    prior=starts.bead_footprints(q,xy[:first][eligible],widths[:first][eligible])
    hits=np.zeros(len(trace),bool);w=widths[first:last+1]
    for size in np.unique(np.floor(w*50)/50):
        mask=(np.floor(w*50)/50)==size
        # Require positive overlap, not merely two footprint boundaries
        # that could be touching within the G-code rounding uncertainty.
        hits[mask]=q._inside(prior.offset(float(size)/2-.03),trace[mask])
    edges=np.flatnonzero(np.diff(np.r_[False,~hits,False].astype(int))).reshape(-1,2)
    steps=np.linalg.norm(np.diff(trace,axis=0),axis=1)
    residual=max((float(steps[a:b-1].sum()) for a,b in edges),default=0.)
    return {'earlier_anchor_samples':int(hits.sum()),'earlier_anchor_at_start':bool(hits[0]),
        'earlier_anchor_at_end':bool(hits[-1]),'longest_residual_run_mm':round(residual,3)}
