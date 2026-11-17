"""Measure native carrier roof moves and continuous unsupported excursions."""
import argparse,json
from pathlib import Path
import numpy as np
from holder45 import inherited
from plate45 import digest
import single44

def intervals(flags):
    return np.flatnonzero(np.diff(np.r_[False,flags,False].astype(int))).reshape(-1,2)

def inspect(path, *, owner_name='Key_Carrier', support_owners=None, report_path=None, focus_layers=None):
    checker=inherited.common.load_checker().audit;q=checker.q
    d,features,_,_,offset,_,gcode,_=checker.read_project(path)
    from native_order45 import map_moves
    line,sequence,feed,fan=map_moves(q,gcode,len(d))
    own=single44.previous.owners(path);normal=inherited.common.model_mask(np.array(features)[d[:,5].astype(int)])
    carrier=normal&(d[:,6]==own[owner_name])
    if support_owners is None:
        assert owner_name == 'Key_Carrier'
        support_owners = [k for k in own if k not in ('Key_Carrier','Release_tabs')]
    assert owner_name not in support_owners
    helpers=normal&np.isin(d[:,6],[own[k] for k in support_owners])
    p=path.parent;info=json.loads((p/'frame.json').read_text())
    xy=(d[:,:3]+offset-info['bed_translation'])[:,:2]
    F=np.asarray(features)[d[:,5].astype(int)]
    checks=[];previous=q.CrossSection();older=q.CrossSection();layers=[];continuous=[]
    def region(m):
        return checker.start_audit.bead_footprints(q,xy[m],d[m,3]) if m.any() else q.CrossSection()
    wanted = None if focus_layers is None else {round(float(z),3) for z in focus_layers}
    if wanted is not None:
        assert report_path is not None and report_path.name != 'roof-strokes.json' and wanted
    for top in np.unique(d[carrier,7]):
        z=round(float(top),3);sel=carrier&(abs(d[:,7]-z)<.001);idx=np.flatnonzero(sel);pts=xy[idx]
        if wanted is not None and z not in wanted:
            # A focused diagnostic sees exactly the same true predecessors
            # as the full run. Unrelated layers do not enter its statistics.
            if round(z+.2,3) in wanted or round(z+.4,3) in wanted:
                older,previous=previous,region(sel)
            continue
        under=region(helpers&(abs(d[:,7]-(z-.4))<.001))
        direct=q._inside(previous.offset(.25)+under,pts) if z>.201 else np.ones(len(pts),bool)
        # Only the four intentionally double-decked outer keys have the
        # established 0.22-mm legacy seam. Report its backing separately.
        seam=np.zeros(len(idx),bool)
        frame=np.array(info['print_to_assembly'])
        if owner_name=='Key_Carrier' and frame[2,2]>.999 and z in (14.,14.2):
            w=np.c_[pts,np.full(len(pts),z-.1),np.ones(len(pts))]@frame.T
            key_zone=(np.abs(np.abs(w[:,0])-21)<8.1)&((np.abs(w[:,1])<8.1)|(np.abs(w[:,1]-21.35)<8.1))
            seam=key_zone&q._inside(older,pts)
        base=direct|seam
        delta=np.linalg.norm(np.diff(pts,axis=0),axis=1)
        seq=np.r_[0,np.flatnonzero(np.diff(sequence[idx])!=0)+1,len(idx)]
        moves=np.r_[0,np.flatnonzero(np.diff(line[idx])!=0)+1,len(idx)]
        potentially_relevant=not base.all()
        layers.append(dict(z=z,native_moves=len(moves)-1,roof_features=bool(potentially_relevant)))
        if potentially_relevant:
            from grounded45 import trace
            reach=trace(pts,d[idx,3],base,moves,seq,delta)
            backed=np.isfinite(reach)
            cum=np.r_[0,np.cumsum(delta)]
            def pieces(a,b,*,geometry=False):
                result=[]
                for u,v in intervals(~backed[a:b]):
                    first=a+u;last=a+v-1
                    left=u>0;right=v<b-a
                    # Include the distance to bounding supported samples;
                    # a single missed sample still has finite extent.
                    length=cum[last+int(right)]-cum[first-int(left)]
                    row=dict(mm=round(float(length),3),before=bool(left),after=bool(right),
                        start_xy=pts[first].round(3).tolist(),end_xy=pts[last].round(3).tolist())
                    if geometry and length>=.30:
                        i=first-int(left);j=last+int(right)
                        path=pts[i:j+1];chord=path[-1]-path[0]
                        denominator=chord@chord
                        t=np.clip(((path-path[0])@chord)/denominator,0.,1.) if denominator>1e-12 else np.zeros(len(path))
                        deviation=float(np.linalg.norm(path-(path[0]+t[:,None]*chord),axis=1).max())
                        anchored_span=float(length+reach[i]+reach[j]) if left and right else None
                        width=float(d[idx[i:j+1],3].min())
                        # A curved unsupported wall cannot tension between its
                        # ends as a straight bridge. Its centreline must stay
                        # inside the deposited strand's half-width corridor.
                        if not (left and right):classification='free end requires backing'
                        elif deviation>width/2:classification='unsupported bend outside bead corridor'
                        elif anchored_span>12.:classification='beyond screened anchored span'
                        else:classification='short straight two-ended bridge'
                        row.update(chord_mm=round(float(np.linalg.norm(chord)),3),
                            deviation_from_chord_mm=round(deviation,3),minimum_bead_width_mm=round(width,3),median_bead_width_mm=round(float(np.median(d[idx[i:j+1],3])),3),
                            actual_length_at_width_below_0p2_mm=round(float(np.sum(np.diff(cum[i:j+1])*(d[idx[i+1:j+1],3]<.2))),3),
                            anchored_span_mm=round(anchored_span,3) if anchored_span is not None else None,
                            first_gcode_line=int(line[idx[i]]),last_gcode_line=int(line[idx[j]]),
                            commanded_feed_range_mm_s=[round(float(feed[idx[i:j+1]].min()),3),round(float(feed[idx[i:j+1]].max()),3)],
                            last_commanded_part_fan_fraction_range=[round(float(fan[idx[i:j+1]].min()),3),round(float(fan[idx[i:j+1]].max()),3)],
                            classification=classification,features=list(dict.fromkeys(F[idx[i:j+1]].tolist())),
                            sampled_path_xy=path[np.linspace(0,len(path)-1,min(len(path),13)).astype(int)].round(3).tolist())
                    result.append(row)
                return result
            for a,b in zip(moves[:-1],moves[1:]):
                if b<=a+1:continue
                label=str(F[idx[a]]);length=cum[b-1]-cum[a]
                if label not in ('Bridge','Overhang wall') and base[a:b].all():continue
                gaps=pieces(a,b)
                checks.append(dict(z=z,feature=label,length_mm=round(float(length),3),
                    start_xy=pts[a].round(3).tolist(),end_xy=pts[b-1].round(3).tolist(),
                    direct_start=bool(direct[a]),direct_end=bool(direct[b-1]),
                    direct_fraction=round(float(direct[a:b].mean()),4),seam_fraction=round(float(seam[a:b].mean()),4),
                    anchored_start=bool(backed[a]),anchored_end=bool(backed[b-1]),gaps=gaps))
            for a,b in zip(seq[:-1],seq[1:]):
                for g in pieces(a,b,geometry=True):
                    if 'classification' not in g:continue
                    continuous.append(dict(z=z,**g))
        older,previous=previous,region(sel)
    def longest(gs):return max(gs,key=lambda g:g['mm'],default=None)
    from collections import Counter
    classifications=Counter(g['classification'] for g in continuous)
    result=dict(sequence_classifications=dict(classifications),
        unresolved_continuous_intervals=sum(g['classification']!='short straight two-ended bridge' for g in continuous),
        sequence_screen='Measured excursions of at least two native sample pitches (0.30 mm). A two-ended bridge needs ancestral span <=12 mm and maximum centreline deviation <=half its narrowest actual bead width. Longer spans, unsupported bends, and free ends require independent backing evidence. This screen alone cannot establish PETG bridge quality.',
        archive_sha256=digest(path),layers=layers,strokes=checks,sequence_gaps=continuous,
        longest_unsupported_move_piece=longest([v for r in checks for v in r['gaps']]),
        longest_unanchored_or_one_ended_sequence=longest([g for g in continuous if not(g['before'] and g['after'])]),
        longest_two_ended_sequence=longest([g for g in continuous if g['before'] and g['after']]),
        scope='Every native move on every carrier layer with incomplete backing, including unlabelled roof paths. Record direct interior samples, lower carrier with one empty layer only within confirmed outer-key seam, actual width overlaps against all earlier anchored samples, with no same-strand tail credit and no inheritance through an unsupported bend, and contiguous leftover arclengths across move boundaries. 12 mm limits inheritance through an already bridged stroke; physical PETG sag remains unmeasured.')
    if owner_name != 'Key_Carrier':
        assert report_path is not None, 'A separate report is required for another native owner'
        result['owner'] = owner_name
        result['scope'] = ('All actual '+owner_name+' moves in deposition order. Only its immediately lower layer and '
                           +', '.join(support_owners)+' across one empty layer can supply external backing.')
    if wanted is not None:
        assert {r['z'] for r in layers}==wanted
        result['focus_layers_mm']=sorted(wanted)
    (report_path if report_path is not None else p/'roof-strokes.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('Native roof stroke pieces:',len(checks),result['longest_unsupported_move_piece'],result['longest_unanchored_or_one_ended_sequence'],flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);inspect(parser.parse_args().archive)
