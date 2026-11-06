#!/usr/bin/env python3
"""Conservative same/adjacent-layer gap between actual helper and part beads."""
import numpy as np
from scipy.spatial import cKDTree


def inspect(xyz,width,layers,helper,bonded,step=.15,minimum=.5):
    records=[];best=None;violations=0;checked=0
    tops=np.unique(np.round(layers[helper&~bonded],4))
    for top in tops:
        hi=np.flatnonzero(helper&~bonded&(abs(layers-top)<.001))
        mi=np.flatnonzero(~helper&~bonded&(abs(layers-top)<.201))
        if not len(mi):continue
        tree=cKDTree(xyz[mi,:2]);dist,ids=tree.query(xyz[hi,:2],k=min(8,len(mi)))
        if dist.ndim==1:dist=dist[:,None];ids=ids[:,None]
        gap=(dist-width[hi,None]/2-width[mi[ids]]/2-step).min(1)
        value=float(gap.min());checked+=len(hi);violations+=int((gap<minimum-.025).sum())
        if best is None or value<best:best=value
        if value<minimum+.15:records.append({'layer_top_mm':float(top),'conservative_xy_gap_mm':round(value,4)})
    return {'checked_helper_samples':checked,'excluded_bonded_tab_samples':int(bonded.sum()),
            'minimum_required_mm':minimum,'sampling_allowance_mm':step,
            'minimum_conservative_gap_mm':None if best is None else round(best,4),
            'violating_samples':violations,'closest_layers':sorted(records,key=lambda r:r['conservative_xy_gap_mm'])[:12],
            'method':'Nearest actual bead centres in same/adjacent layer minus both measured half-widths and a full sampling step. Deliberate outer-rail cut tabs are excluded; functional-space checks exclude nothing.'}
