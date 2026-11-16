"""Trace every native disposable bead island down to a grounded lower layer."""
import argparse,json
from pathlib import Path
import numpy as np
from manifold3d import OpType
from holder45 import inherited
from plate45 import digest
import single44

def inspect(archive):
    checker=inherited.common.load_checker().audit;q=checker.q
    data,features,_,_,offset,parts,_,_=checker.read_project(archive)
    owner=single44.previous.owners(archive)
    names=np.asarray(features)[data[:,5].astype(int)]
    normal=inherited.common.model_mask(names)
    frame=json.loads((archive.parent/'frame.json').read_text())
    xy=data[:,:2]+offset[:2]-frame['bed_translation'][:2]
    masks={n:(data[:,6]==owner[n])&normal for n in ('Key_Carrier','External_cradle','Front_pull_shelf','Rear_pull_shelf') if n in owner}
    helpers=list(masks)[1:]
    grounded={n:{} for n in helpers}
    reports={n:{'layers':[],'unrooted_actual_components':[],'starts_backed_across_one_empty_layer':[]} for n in helpers}
    for i in range(1,round(max(data[masks[n],7].max() for n in helpers)/.2)+1):
        z=round(i*.2,3)
        for n in helpers:
            mask=masks[n]&(abs(data[:,7]-z)<.001)
            if not mask.any():continue
            pieces=checker.start_audit.bead_footprints(q,xy[mask],data[mask,3]).decompose()
            kept=[];failed=0
            below=grounded[n].get(i-1,q.CrossSection()).offset(.25)
            other=None
            for p in pieces:
                if i==1 or (p^below).area()>.0001:
                    kept.append(p);continue
                if n in ('Front_pull_shelf','Rear_pull_shelf') and i>2:
                    if other is None:
                        lower=masks['Key_Carrier']&(abs(data[:,7]-(z-.4))<.001)
                        carrier=checker.start_audit.bead_footprints(q,xy[lower],data[lower,3]) if lower.any() else q.CrossSection()
                        other=carrier+grounded['External_cradle'].get(i-2,q.CrossSection())
                    overlap=(p^other).area()
                    if overlap>.0001:
                        reports[n]['starts_backed_across_one_empty_layer'].append(dict(top_mm=z,overlap_mm2=overlap,print_bounds_mm=p.bounds()))
                        kept.append(p);continue
                failed+=1;reports[n]['unrooted_actual_components'].append(dict(top_mm=z,area_mm2=p.area(),print_bounds_mm=p.bounds()))
            grounded[n][i]=q.CrossSection.batch_boolean(kept,OpType.Add) if kept else q.CrossSection()
            reports[n]['layers'].append(dict(top_mm=z,components=len(pieces),without_grounded_previous_layer=failed))
    for n,r in reports.items():r['checked_layers']=len(r['layers'])
    first=abs(data[:,7]-.2)<.001
    def footprint(name):
        m=first&normal&(data[:,6]==owner[name])
        return checker.start_audit.bead_footprints(q,xy[m],data[m,3])
    def separation(a,b):
        if (a^b).area()>1e-8:return 0.
        lo,hi=0.,8.
        if (a.offset(hi)^b).is_empty():return None
        for _ in range(18):
            mid=(lo+hi)/2
            if (a.offset(mid)^b).is_empty():lo=mid
            else:hi=mid
        return round(hi,5)
    first_body,first_tabs=footprint('Key_Carrier'),footprint('Release_tabs')
    def native_midpoint(name):
        obj=parts[name]
        return q.solid(obj['vertices']-frame['bed_translation'],obj['faces']).slice(.1)
    native_body,native_tabs=native_midpoint('Key_Carrier'),native_midpoint('Release_tabs')
    actual_bed=dict(carrier_area_mm2=first_body.area(),tabs_area_mm2=first_tabs.area(),
        native_midpoint_mesh_separation_mm=separation(native_body,native_tabs),
        actual_body_components=[dict(area_mm2=component.area(),tab_overlap_mm2=(component^first_tabs).area(),
            nearest_tab_bead_mm=separation(component,first_tabs)) for component in first_body.decompose()])
    report=dict(archive_sha256=digest(archive),owners=reports,first_layer_body_and_tabs=actual_bed,**reports['External_cradle'],
        scope='Whole native-bead connected islands on each layer. Previous rooted same-owner layer allows 0.25 mm growth. Side shelves can also use real carrier or grounded cradle across one empty layer; the separate carrier-start and withdrawal reports must pass.')
    (archive.parent/'helper-starts.json').write_text(json.dumps(report,indent=2)+'\n')
    print('unrooted bead islands by helper',{n:len(r['unrooted_actual_components']) for n,r in reports.items()},flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);inspect(p.parse_args().archive)
