"""The plugged-in OP1 lead threads down the real slot, then rests in its underside groove."""
from copy import deepcopy
import math

import numpy as np

import cable48


def wire_vertices(g, vertices):
    """Bend the installed mesh into a hanging lead, preserving distance along its centreline."""
    points=np.asarray(g.q.lead_points(),float)
    delta=np.diff(points,axis=0)
    length=np.linalg.norm(delta,axis=1)
    direction=delta/length[:,None]
    # Locate each surface vertex on its nearest centreline segment. The first and
    # last hemispheres preserve their distance beyond the cable endpoints.
    rel=vertices[:,None,:]-points[:-1]
    along=np.clip(np.einsum('ijk,jk->ij',rel,direction),0.,length)
    nearest=points[:-1]+along[:,:,None]*direction
    which=np.linalg.norm(vertices[:,None,:]-nearest,axis=2).argmin(axis=1)
    ix=np.arange(len(vertices))
    center=nearest[ix,which]
    station=np.r_[0.,np.cumsum(length)][which]+along[ix,which]
    tangent=np.vstack((direction[0],direction[:-1]+direction[1:],direction[-1]))
    tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    frac=along[ix,which]/length[which]
    start=tangent[which]*(1-frac[:,None])+tangent[which+1]*frac[:,None]
    start/=np.linalg.norm(start,axis=1)[:,None]
    # 1.65 mm bend radius on the wire bundle's centreline turns it down within
    # the 4.16 mm slot. An illustrative flexible lead can be straightened to feed.
    stub,radius=.32,1.65
    theta=np.clip((station-stub)/radius,0.,math.pi/2)
    face=points[0]
    xy=direction[0,:2]
    run=np.minimum(station,stub)+radius*np.sin(theta)
    drop=radius*(1.-np.cos(theta))+np.maximum(0.,station-stub-radius*math.pi/2)
    hanging=face+np.column_stack((run[:,None]*xy,-drop))
    target=np.column_stack((np.cos(theta)[:,None]*xy,-np.sin(theta)))
    def frame(tan):
        across=np.array([1.,0.,0.])-tan*tan[:,0,None]
        across/=np.linalg.norm(across,axis=1)[:,None]
        return np.stack((tan,across,np.cross(tan,across)),axis=2)
    local=np.einsum('ijk,ij->ik',frame(start),vertices-center)
    return hanging+np.einsum('ijk,ik->ij',frame(target),local)


def prepare(guide,g,out,carrier):
    import manifold3d as mf
    dfr=guide['modules']['dfr']
    actor=dfr['actors']['op1_wire']
    file=out/actor['file']
    mesh=g.A.trimesh.load_mesh(file,process=False)
    hanging=wire_vertices(g,mesh.vertices)
    pose_file='guide/op1-wire-hanging.stl'
    g.A.trimesh.Trimesh(hanging,mesh.faces,process=False).export(out/pose_file)
    actor.update(morphFile=pose_file,label='OP1 harness from the fitted plug')
    q=g.q
    a,b=cable48.centres(g.h)
    outlet=np.mean([a,b],axis=0)
    tip=q.board_point(0.,g.h.h32.MATE_Y[1])
    dfr['annotations']=[mark for mark in dfr['annotations'] if mark['actor']!='plug']
    dfr['annotations']+=[
        dict(actor='carrier',step='Feed the lead through the slot',side='right',
             point=[*outlet,g.h.base.DECK_TOP],title='Wire slot in line with the plug'),
        dict(actor='plug',step='Lower the OP1 Board',side='right',
             point=[*tip,q.LEAD_Z],title='Plug and lead stay together')]
    steps={step['title']:step for step in dfr['steps']}
    lower=steps['Lower the OP1 Board']; groove=steps['Press the Lead into the Groove']
    end_idx=dfr['steps'].index(groove)
    initial=dfr['steps'][0]
    # Begin above the slot, so the first thread step shows the bare end entering.
    # Conservative depth relative to the top surface, placed in the same WCS as the carrier.
    start_tip_z=np.min(hanging[:,2])+g.h.h32.BOARD_RISE
    extra=max(0.,g.h.base.DECK_TOP+2.-start_tip_z)
    attached=(*g.up.OP1_BOARD,'plug','op1_wire')
    for i,step in enumerate(dfr['steps']):
        for idx,frame in enumerate(step['samples']):
            frame['op1_wire']=list(frame['plug'])
            t=idx/max(1,len(step['samples'])-1)
            frame.setdefault('morphs',{})['op1_wire']=1. if i<end_idx else (1.-t if i==end_idx else 0.)
    # Park the loose mouse switch and screws to the side. Otherwise the board
    # would appear to pass through the floating hardware as it enters the slot.
    for title,names in [('Secure the Board',('fasteners',)),('Seat the Mouse Switch',g.up.MOUSE)]:
        install=dfr['steps'].index(steps[title])
        for i,step in enumerate(dfr['steps'][:install+1]):
            for j,frame in enumerate(step['samples']):
                t=j/max(1,len(step['samples'])-1)
                for name in names:
                    if i<install:
                        frame[name][3]+=34.
                    elif t<.5:
                        frame[name]=list(step['samples'][0][name]) if j else frame[name]
                        if j:
                            frame[name][3]-=68.*t
                        else:
                            frame[name][3]+=34.
                    else:
                        first=step['samples'][0][name];last=step['samples'][-1][name]
                        frame[name][3]=last[3]
                        frame[name][11]=first[11]+(last[11]-first[11])*(2.*t-1.)
    start=deepcopy(lower['samples'][0])
    def above(distance):
        frame=deepcopy(start)
        for name in attached:
            frame[name][11]+=distance
        return frame
    raised=above(extra)
    for frame in initial['samples']:
        for name in attached:
            frame[name]=list(raised[name])
    feed=dict(title='Feed the lead through the slot',duration=3.5,
              caption='With the holder off the rod, fit the harness plug into the board. Feed its free ends straight down the oblong slot in front of the plug.',
              samples=[above(float(z)) for z in np.linspace(extra,0.,25)])
    dfr['steps'].insert(dfr['steps'].index(lower),feed)
    lower['caption']=('Lower the plugged-in OP1 board onto its two seats at '
                      f'{abs(q.OP1_YAW):g}°. Let the loose lead pass through the slot as the board drops. The four outer keys can stay fitted.')
    groove['caption']='From the open underside, lay the lead towards the two-key end and press it gently into the groove. Then fit the holder on the rod.'
    # Verify both displayed endpoints against the CAD plus the actual intermediate
    # centreline; the wire is represented by one envelope, including all leads.
    base=g.b.load(file)
    nominal=q.hardware()['op1_wire']
    final_disagreement=abs((nominal-base).volume())+abs((base-nominal).volume())
    assert final_disagreement<.015
    plug=g.b.load(out/dfr['actors']['plug']['file']); cad_plug=q.hardware()['plug']
    plug_disagreement=abs((plug-cad_plug).volume())+abs((cad_plug-plug).volume())
    assert plug_disagreement<.015
    welded=g.A.trimesh.load_mesh(file)
    hang_welded=wire_vertices(g,welded.vertices)
    def shape(weight):
        verts=welded.vertices+weight*(hang_welded-welded.vertices)
        return mf.Manifold(mf.Mesh64(verts,np.asarray(welded.faces,np.uint64)))
    down=shape(1.)
    assert down.status()==mf.Error.NoError
    lowered=max(max(0.,(down.translate((0.,0.,float(z)))^carrier).volume())
                for z in np.linspace(0.,extra+g.h.h32.BOARD_RISE,25))
    routing=max(max(0.,(shape(float(t))^carrier).volume()) for t in np.linspace(0.,1.,25))
    # cable48.check() independently validates the straight slot with a larger three-wire
    # circular gauge than the illustrated cable mesh.
    assert max(lowered,routing)<.003, ('Displayed harness enters plastic',lowered,routing)
    for step in dfr['steps']:
        for frame in step['samples']:
            assert np.allclose(frame['op1_wire'], frame['plug']) and np.allclose(frame['plug'],frame['board'])
    return dict(slot_centres_xy_mm=[list(a),list(b)],wire_vs_model_mm3=round(final_disagreement,6),
                plug_vs_model_mm3=round(plug_disagreement,6),max_threading_overlap_mm3=round(lowered,6),
                max_routing_overlap_mm3=round(routing,6),initial_tip_above_deck_mm=round(start_tip_z+extra-g.h.base.DECK_TOP,4))
