"""Trace chronologically available, width-overlapping anchored native strands."""
import numpy as np

def _gaps(missing):
    return np.flatnonzero(np.diff(np.r_[False,missing,False].astype(int))).reshape(-1,2)

def trace(pts,width,base,moves,sequences,delta):
    n=len(pts);reach=np.where(base,0.,np.inf);cost=reach.copy()
    if base.all():return reach
    cum=np.r_[0,np.cumsum(delta)]
    ids=np.empty(n,int);seqid=np.empty(n,int)
    for m,(a,b) in enumerate(zip(moves[:-1],moves[1:])):ids[a:b]=m
    for s,(a,b) in enumerate(zip(sequences[:-1],sequences[1:])):seqid[a:b]=s
    # Collect ALL earlier sample-to-sample bead overlaps for the ambiguous
    # samples. Keeping just one representative in each spatial cell can
    # miss the actual anchored strand on the other side of that cell.
    cell=.24
    xy=np.floor((pts-pts.min(0)+2)/cell).astype(int);nx=int(xy[:,0].max())+20
    keys=xy[:,0]+nx*xy[:,1];order=np.argsort(keys);sorted_keys=keys[order]
    ask=np.flatnonzero(~base);pairs=[]
    radius=int(np.ceil(float(width.max())/cell))+1
    for dx in range(-radius,radius+1):
        for dy in range(-radius,radius+1):
            k=keys[ask]+dx+dy*nx
            lo=np.searchsorted(sorted_keys,k);hi=np.searchsorted(sorted_keys,k,side='right')
            for step in range(int((hi-lo).max(initial=0))):
                good=(hi-lo)>step;i=ask[good];j=order[lo[good]+step]
                # The immediately preceding tail is the same strand, not
                # independent lateral backing. Permit a different, already
                # deposited trace within a raster only after it turns back.
                prev=(ids[j]<ids[i])&((seqid[j]!=seqid[i])|((cum[i]-cum[j])>2*np.maximum(width[i],width[j])))
                i=i[prev];j=j[prev]
                if not len(i):continue
                dist=np.linalg.norm(pts[i]-pts[j],axis=1)
                ok=dist<=(width[i]+width[j])/2-.03
                if ok.any():pairs.append((i[ok],j[ok],dist[ok]))
    if pairs:
        I,J,D=(np.concatenate(a) for a in zip(*pairs))
        sort=np.argsort(ids[I]);I,J,D=I[sort],J[sort],D[sort]
        bounds=np.searchsorted(ids[I],np.arange(len(moves)))
    else:
        I=J=np.array([],int);D=np.array([]);bounds=np.zeros(len(moves),int)
    def earn(a,b):
        if np.isfinite(reach[a:b]).all():return
        for lo,hi in _gaps(~np.isfinite(reach[a:b])):
            if lo==0 or hi==b-a:continue
            left=a+lo-1;right=a+hi
            if cum[right]-cum[left]+reach[left]+reach[right]>12.:continue
            path=pts[left:right+1];chord=path[-1]-path[0];den=float(chord@chord)
            t=np.clip((path-path[0])@chord/den,0.,1.) if den>1e-12 else np.zeros(len(path))
            if np.linalg.norm(path-(path[0]+t[:,None]*chord),axis=1).max()>width[left:right+1].min()/2:continue
            s=np.arange(left+1,right)
            cost[s]=np.minimum(cost[s],np.minimum(cum[s]-cum[left]+reach[left],cum[right]-cum[s]+reach[right]))
    seq_start=0;seq_ends=set(sequences[1:])
    for m,(a,b) in enumerate(zip(moves[:-1],moves[1:])):
        l,h=bounds[m:m+2]
        if h>l:
            c=cost[J[l:h]]+D[l:h];valid=c<=6.
            np.minimum.at(reach,I[l:h][valid],c[valid])
        cost[a:b]=np.minimum(cost[a:b],reach[a:b])
        earn(a,b)
        if b in seq_ends:
            earn(seq_start,b);seq_start=b
    return reach
