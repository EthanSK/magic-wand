"""Support blockers and independent tests of the working spaces in assembly coordinates."""
import json
from functools import lru_cache
from pathlib import Path

import manifold3d as mf
import numpy as np

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'carbon-rod-holders-r48-edge-click/exports/geometry-checks.json'


@lru_cache(maxsize=1)
def patches():
    # Use the generative model itself. Moving the OP1 shifts the plug but
    # the remote end of the incoming lead stays at its old rear station.
    import build51 as d
    d.configure_new_op1()
    a,b=d.baseline.cable48.centres(d.h)
    fingers=d.h.d.finger_rest_paths()
    return dict(wire=(a,b),lead=d.q.lead_points(),fork=d.PIVOT_YZ,
                paddle=(d.AXIS_Y,d.AXIS_Z),bearing_radius=d.BEARING_RADIUS,
                fork_outer=d.FORK_OUTER,fork_inner=d.FORK_INNER,fork_radius=d.FORK_BORE,
                bearing_half=d.BEARING_HALF,
                fingers={f'{side}/{name}':points for side,members in fingers.items()
                for name,points in members.items() if name in ('spine','middle branch')})


def capsule(a,b,radius):
    ends=[mf.Manifold.sphere(radius,16).translate(v) for v in (a,b)]
    return mf.Manifold.batch_hull(ends)


def blockers(name, contact_only=False):
    core=patches()
    if name=='DFRobot_Hole_Bracket':
        y,z=core['paddle']
        return {'bearing through hole':capsule((-core['bearing_half'],y,z),(core['bearing_half'],y,z),core['bearing_radius']+.45)}
    a,b=core['wire']
    cylinders=[mf.Manifold.cylinder(28,2.7,2.7,40).translate((*xy,-6)) for xy in (a,b)]
    out={'OP1 wire outlet':mf.Manifold.batch_hull(cylinders)}
    lead=core['lead']
    out['OP1 underside lead']=mf.Manifold.batch_boolean([capsule(a,b,1.85) for a,b in zip(lead,lead[1:])],mf.OpType.Add)
    for label,points in core['fingers'].items():
        if contact_only:
            # The index finger lies under these rounded ribs. Paint may
            # support the opposite shoulder while leaving this face untouched.
            points=[(x,y,z-.90) for x,y,z in points]
        out['finger contact '+label]=mf.Manifold.batch_boolean([
            capsule(a,b,.65 if contact_only else 1.75) for a,b in zip(points,points[1:])],mf.OpType.Add)
    y,z=core['fork']
    out['axle through fork']=capsule((-core['fork_outer'],y,z),(core['fork_outer'],y,z),core['fork_radius']+.45)
    return out


def distance(points,a,b):
    a,b=np.asarray(a),np.asarray(b)
    v=b-a
    t=np.clip((points-a)@v/(v@v),0.,1.)
    return np.linalg.norm(points-a-t[:,None]*v,axis=1)


def inspect(machine,frame,name):
    results=dict(wire_core_bead_samples=0,underside_lead_bead_samples=0,
                 finger_contact_bead_samples=0,finger_underside_bead_samples=0,axle_core_bead_samples=0)
    if not len(machine):
        return results
    rotate=np.linalg.inv(np.array(frame))
    xyz=machine[:,:3].copy();xyz[:,2]=machine[:,7]-.5*machine[:,4]
    local=xyz@rotate[:3,:3].T+rotate[:3,3]
    core=patches()
    r=machine[:,3]/2
    y,z=core['paddle'] if name=='DFRobot_Hole_Bracket' else core['fork']
    inner=1.5 if name=='DFRobot_Hole_Bracket' else 1.
    half=core['bearing_half'] if name=='DFRobot_Hole_Bracket' else core['fork_outer']
    axial=(abs(local[:,0])<=half+.15)
    within=np.hypot(local[:,1]-y,local[:,2]-z) <= inner + r
    results['axle_core_bead_samples']=int((axial&within).sum())
    if name=='DFRobot_Hole_Bracket':return results
    a,b=core['wire']
    wire=distance(local[:,:2],a,b) <= 1.616 + r
    wire&=(local[:,2]>-6-r)&(local[:,2]<22+r)
    fingers=np.zeros(len(machine),bool)
    underside=np.zeros(len(machine),bool)
    for points in core['fingers'].values():
        for a,b in zip(points,points[1:]):
            fingers|=distance(local,a,b) <= .95+r+.10
            down=np.array((0.,0.,-.90))
            underside|=distance(local,np.asarray(a)+down,np.asarray(b)+down)<=.65+r
    lead=np.zeros(len(machine),bool)
    for a,b in zip(core['lead'],core['lead'][1:]):lead |= distance(local,a,b)<=1.30+r
    results.update(wire_core_bead_samples=int(wire.sum()),finger_contact_bead_samples=int(fingers.sum()),
                   underside_lead_bead_samples=int(lead.sum()),finger_underside_bead_samples=int(underside.sum()))
    return results


def bearing_space(paths,frame,name):
    """Find the largest open inscribed cylinder with an axis parallel to machine X."""
    common=patches()
    paddle=name=='DFRobot_Hole_Bracket'
    nominal=common['bearing_radius'] if paddle else common['fork_radius']
    size=1.50 if paddle else 1.00
    cy,cz=common['paddle'] if paddle else common['fork']
    transform=np.asarray(frame)
    axis=transform@np.array([0.,cy,cz,1.])
    axial=int(np.argmax(abs(transform[:3,0])))
    xyz=paths[:,:3].copy()
    xyz[:,2]=paths[:,7]-.5*paths[:,4]
    x=abs(xyz[:,axial]-axis[axial])
    lo=0. if paddle else common['fork_inner']
    hi=common['bearing_half'] if paddle else common['fork_outer']
    # A bead can project just past the nominal cheek's indoor/outdoor ends.
    candidate=(x<=hi+.1)&(x>=lo-.1)
    path=paths[candidate]
    halfw=path[:,3]/2
    halfh=path[:,4]/2
    transverse=[d for d in range(3) if d!=axial]
    widths=(halfw,halfw,halfh)
    delta=np.abs(xyz[candidate]-axis[:3])
    bounds=[np.maximum(delta[:,d]-widths[d],0.) for d in transverse]
    # Worst-case rectangular upper bound for each deposited strand. In
    # particular it does not mistake a circular XY bead for more Z material.
    low=np.hypot(*bounds)
    k=np.argmin(low)
    return dict(nominal_CAD_radius_mm=nominal,hardware_radius_mm=size,
                conservative_native_radius_mm=round(float(low[k]),3),
                layer_top_mm=round(float(path[k,7]),3),
                candidate_square_bead_radius_shortfall_mm=round(float(max(0.,size-low[k])),3))
