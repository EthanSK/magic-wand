"""Bound prior-layer unsupported runs in actual carrier extrusion.

A same-layer bead might anchor a later run. This report deliberately omits
that credit and retains one-ended runs for explicit toolpath review.
"""
from pathlib import Path
import argparse,json
import numpy as np
from holder45 import inherited as prior
from plate45 import digest
import single44

def inspect(path):
    checker=prior.common.load_checker().audit;q=checker.q
    data,features,stats,config,offset,objects,_,_=checker.read_project(path)
    owner=single44.previous.owners(path);labels=np.asarray(features)[data[:,5].astype(int)]
    part=(data[:,6]==owner['Key_Carrier'])&prior.common.model_mask(labels)
    rib=np.isin(data[:,6],[owner[n] for n in ('External_cradle','Front_pull_shelf','Rear_pull_shelf') if n in owner])&prior.common.model_mask(labels)
    xyz=data[:,:3]+offset-np.array([50,70,0])
    source=path.parent/'candidate-audit.json'
    if not source.exists():source=path.parent/'starts-preflight.json'
    report=json.loads(source.read_text())
    assert report['archive_sha256']==digest(path)
    records=report['layer_starts']['partial_overhangs']
    def footprint(mask):
        return checker.start_audit.bead_footprints(q,xyz[mask,:2],data[mask,3]) if mask.any() else q.CrossSection()
    layers=[]
    for z in sorted({a['layer_top_mm'] for a in records}):
        mask=np.abs(data[:,7]-z)<.001;idx=np.flatnonzero(mask&part)
        # Existing 0.25-mm lateral allowance for naturally printable growth.
        supported=footprint(part&(np.abs(data[:,7]-(z-.2))<.001)).offset(.25)
        support=footprint(rib&(np.abs(data[:,7]-(z-.4))<.001))
        xy=xyz[idx,:2];good=q._inside(supported+support,xy)
        # Record the actual older carrier below the intentional 0.22 mm
        # seam between key floors. Keep this separate from directly rooted
        # strands and from the removable cradle's measured support.
        old_floor=None
        if z in (14.,14.2):
            old_floor=q._inside(footprint(part&(np.abs(data[:,7]-(z-.4))<.001)),xy)
        # The 0.15-mm sampled paths keep consecutive positive-extrusion
        # moves in native order. Split travels and object changes.
        delta=np.linalg.norm(np.diff(xy,axis=0),axis=1)
        split=np.r_[0,np.flatnonzero((np.diff(idx)!=1)|(delta>.151))+1,len(idx)]
        from causal45 import grounded_strokes,earlier_contacts
        rooted=grounded_strokes(xy,idx,good,labels[idx])
        from ancestry45 import trace_layer,evidence
        ancestry,qualified,_=trace_layer(xy,idx,data[idx,3],good)
        spans=[]
        for a,b in zip(split[:-1],split[1:]):
            flags=~good[a:b]
            edges=np.flatnonzero(np.diff(np.r_[False,flags,False].astype(int))).reshape(-1,2)
            for i,j in edges:
                start=a+i;end=a+j-1
                length=float(delta[start:end].sum())
                if length<1.:continue
                # A supported point before and after within the actual same
                # extrusion sequence gives two prior-layer anchors.
                before=i>0; after=j<len(flags)
                spans.append(dict(length_mm=round(length,3),end_to_end_mm=round(float(np.linalg.norm(xy[start]-xy[end])),3),
                    prior_layer_anchors=int(before)+int(after),
                    start_xy=xy[start].round(3).tolist(),end_xy=xy[end].round(3).tolist(),
                    features=sorted(set(labels[idx[start:end+1]].tolist())),
                    underlying_carrier_one_empty_layer_sample_fraction=(
                        round(float(old_floor[start:end+1].mean()),5) if old_floor is not None else None),
                    native_order_ancestry=evidence(ancestry,qualified,xy,data[idx,3],start,end),
                    earlier_grounded_same_layer=(earlier_contacts(q,checker.start_audit,xy,data[idx,3],rooted,start,end)
                        if length>=4. or (not before and not after) else None)))
        rows=[]
        for area in (v for v in records if v['layer_top_mm']==z):
            x0,y0,x1,y1=area['print_xy_bounds_mm']
            # Conservative bounds association (not a run-clipped length).
            def near(run):
                a,b=np.array(run['start_xy']),np.array(run['end_xy'])
                return bool(np.all(np.minimum(a,b)<=[x1+.3,y1+.3]) and np.all(np.maximum(a,b)>=[x0-.3,y0-.3]))
            related=[run for run in spans if near(run)]
            rows.append({'print_xy_bounds_mm':[x0,y0,x1,y1],'unbacked_area_mm2':area['unbacked_mesh_area_mm2'],
                'direct_cradle_coverage_fraction':area['direct_backed_fraction'],
                'longest_related_run_by_number_of_prior_layer_anchors':{
                    str(n):max((s for s in related if s['prior_layer_anchors']==n),key=lambda s:s['length_mm'],default=None) for n in (0,1,2)}})
        layers.append({'layer_top_mm':z,'partial_areas':rows,'unsupported_runs_at_least_1mm':spans})
    result={'archive_sha256':digest(path),'layer_results':layers,'physical_bridge_sag_verified':False,
        'scope':'Actual uninterrupted extrusion path length outside previous carrier layer + 0.25 mm and the external cradle at exactly one empty layer. No unverified same-layer anchoring credit. A curved perimeter run is not necessarily a straight bridge of its full path length. Inspect longest runs in context.'}
    (path.parent/'bridge-runs.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);archive=p.parse_args().archive
    inspect(archive)
    from contact45 import inspect as inspect_contact
    inspect_contact(archive)
    if 'Front_pull_shelf' in single44.previous.owners(archive):inspect_contact(archive,'Front_pull_shelf')
    if 'Rear_pull_shelf' in single44.previous.owners(archive):inspect_contact(archive,'Rear_pull_shelf')
