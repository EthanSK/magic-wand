"""Trace ground through PREVIOUS native extrusion sequences; bound unsupported spans.

No later neighbour/branch can seed an earlier run. Within a run only a gap
with two existing anchors whose total unsupported reach is under 12 mm can
become backing for future plastic. Unanchored starts, ends and long detours
never acquire credit by touching their own path.
"""
import numpy as np
def trace_layer(xy,idx,widths,previous_good,reach_limit=12.):
    pitch=.18; origin=xy.min(axis=0)-2
    cells=np.floor((xy-origin)/pitch).astype(int)
    nx,ny=(cells.max(0)+14)
    ids=np.full(nx*ny,-1,dtype=np.int64)
    cost=np.full(len(xy),np.inf); source=np.full(len(xy),np.inf)
    previous_sequence=np.full(len(xy),-1,dtype=int)
    delta=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    cuts=np.r_[0,np.flatnonzero((np.diff(idx)!=1)|(delta>.151))+1,len(xy)]
    radius=int(np.ceil(widths.max()/pitch))+1
    shifts=[dx+nx*dy for dx in range(-radius,radius+1) for dy in range(-radius,radius+1)]
    for a,b in zip(cuts[:-1],cuts[1:]):
        run=xy[a:b]; w=widths[a:b]; keys=cells[a:b,0]+nx*cells[a:b,1]
        base=np.where(previous_good[a:b],0.,np.inf);ancestor=np.full(b-a,-1,dtype=int)
        for shift in shifts:
            nearby=ids[keys+shift];valid=nearby>=0
            if not valid.any():continue
            loc=np.flatnonzero(valid);other=nearby[loc]
            dist=np.linalg.norm(run[loc]-xy[other],axis=1)
            candidate=cost[other]+dist
            # Use the real centres and widths retained in the cell. A
            # representative may miss contact; it cannot invent one.
            ok=(dist<=(w[loc]+widths[other])/2-.03)&(candidate<base[loc])&(candidate<=reach_limit/2)
            take=loc[ok];base[take]=candidate[ok];ancestor[take]=other[ok]
        source[a:b]=base; previous_sequence[a:b]=ancestor
        out=base.copy();direct=np.isfinite(base)
        s=np.r_[0,np.cumsum(delta[a:b-1])]
        edges=np.flatnonzero(np.diff(np.r_[False,~direct,False].astype(int))).reshape(-1,2)
        for i,j in edges:
            if i==0 or j==len(run):continue
            # Measured arclength plus the two anchors' already-unsupported
            # distances back to real lower plastic; no unbounded sideways
            # propagation across an entire unsupported raster.
            if s[j]-s[i-1]+base[i-1]+base[j]>reach_limit:continue
            out[i:j]=np.minimum(base[i-1]+s[i:j]-s[i-1],base[j]+s[j]-s[i:j])
        cost[a:b]=out
        candidates=np.flatnonzero(np.isfinite(out))
        if not len(candidates):continue
        order=np.lexsort((out[candidates],keys[candidates]));choices=candidates[order]
        _,pos=np.unique(keys[choices],return_index=True);best=choices[pos]
        old=ids[keys[best]];better=(old<0)|(out[best]<cost[old])
        ids[keys[best[better]]]=a+best[better]
    return source,cost,previous_sequence

def evidence(source,cost,xy,widths,start,end):
    arr=source[start:end+1];good=np.isfinite(arr);steps=np.linalg.norm(np.diff(xy[start:end+1],axis=0),axis=1)
    edges=np.flatnonzero(np.diff(np.r_[False,~good,False].astype(int))).reshape(-1,2)
    return {'direct_or_earlier_grounded_samples':int(good.sum()),'starts_on_grounded_material':bool(good[0]),
        'ends_on_grounded_material':bool(good[-1]),'max_contiguous_run_without_grounded_contact_mm':round(max((float(steps[a:b-1].sum()) for a,b in edges),default=0.),3),
        'qualified_sample_fraction':round(float(np.isfinite(cost[start:end+1]).mean()),5)}
