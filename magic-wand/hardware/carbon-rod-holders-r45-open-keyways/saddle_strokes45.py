"""Exact native single-stroke backing report for the rear saddle underside."""
import argparse,json
import numpy as np
from pathlib import Path
from holder45 import inherited
from plate45 import digest
import single44

def inspect(archive):
    checker=inherited.common.load_checker().audit;q=checker.q
    data,features,_,_,offset,_,_,_=checker.read_project(archive)
    owner=single44.previous.owners(archive)
    names=np.asarray(features)[data[:,5].astype(int)]
    part=(data[:,6]==owner['Key_Carrier'])&inherited.common.model_mask(names)
    rib=np.isin(data[:,6],[owner[n] for n in ('External_cradle','Front_pull_shelf','Rear_pull_shelf') if n in owner])&inherited.common.model_mask(names)
    info=json.loads((archive.parent/'frame.json').read_text())
    xy=(data[:,:3]+offset-info['bed_translation'])[:,:2]
    def foot(mask):return checker.start_audit.bead_footprints(q,xy[mask],data[mask,3])
    rows=[]
    for z in (12.2,12.4):
        backed=foot(part&(abs(data[:,7]-(z-.2))<.001)).offset(.25)+foot(rib&(abs(data[:,7]-(z-.4))<.001))
        idx=np.flatnonzero(part&(abs(data[:,7]-z)<.001))
        points=xy[idx];delta=np.linalg.norm(np.diff(points,axis=0),axis=1)
        # The common parser samples both ends of every native extrusion move.
        breaks=np.r_[0,np.flatnonzero((np.diff(idx)!=1)|(delta<1e-7)|(delta>.151))+1,len(idx)]
        good=q._inside(backed,points)
        for a,b in zip(breaks[:-1],breaks[1:]):
            if not (names[idx[a:b]]=='Bridge').all():continue
            mid=points[a:b].mean(0)
            if not (22<mid[0]<38 and 27<mid[1]<42):continue
            length=float(delta[a:b-1].sum())
            if length<1:continue
            hits=good[a:b];edges=np.flatnonzero(np.diff(np.r_[False,~hits,False].astype(int))).reshape(-1,2)
            gaps=[dict(length_mm=round(float(delta[a+i:a+j-1].sum()),3),
                    directly_backed_before=bool(i>0),directly_backed_after=bool(j<(b-a))) for i,j in edges]
            rows.append(dict(top_mm=z,length_mm=round(length,3),start_xy=points[a].round(3).tolist(),
                 end_xy=points[b-1].round(3).tolist(),prior_or_helper_backed_at_start=bool(hits[0]),
                 prior_or_helper_backed_at_end=bool(hits[-1]),unbacked_pieces=gaps))
    result=dict(archive_sha256=digest(archive),strokes=rows,scope='Native move lengths and directly backed centre samples in the rear saddle only. Previous carrier layer plus 0.25 mm sideways growth, or actual helper beads one empty layer below. Earlier same-layer paths not credited.')
    (archive.parent/'saddle-strokes.json').write_text(json.dumps(result,indent=2)+'\n')
    print('rear bridge stroke count',len(rows),'longest',max((r['length_mm'] for r in rows),default=0),'with two directly backed ends',sum(r['prior_or_helper_backed_at_start'] and r['prior_or_helper_backed_at_end'] for r in rows),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);inspect(p.parse_args().archive)
