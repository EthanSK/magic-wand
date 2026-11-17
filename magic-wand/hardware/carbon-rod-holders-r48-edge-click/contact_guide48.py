"""Project the actual hinge pusher and switch contact faces at the nominal click angle."""
import numpy as np
import manifold3d as mf

import hinge48


def overlap(h, bracket):
    def face(solid, z, matrix):
        mesh=solid.to_mesh64()
        triangles=np.asarray(mesh.vert_properties)[:,:3][mesh.tri_verts]
        selected=triangles[np.max(np.abs(triangles[:,:,2]-z),axis=1)<.00005]
        assert len(selected)>0
        world=selected@matrix[:3,:3].T+matrix[:3,3]
        projected=world[:,:,:2].copy()
        a,b=projected[:,1]-projected[:,0],projected[:,2]-projected[:,0]
        signed=a[:,0]*b[:,1]-a[:,1]*b[:,0]
        projected[signed<0]=projected[signed<0,::-1]
        return mf.CrossSection(projected[abs(signed)>1e-9],mf.FillRule.NonZero)
    q=h.q
    at_click=np.eye(4)
    at_click[:3]=np.asarray(h.r.placement(0.)).reshape(3,4)
    pusher=face(q.pusher(),q.PUSH_Z,at_click)
    actual=face(bracket,q.PUSH_Z,at_click)
    assert (actual ^ pusher).area()/pusher.area()>.999
    button=q.hardware()['plunger']
    top=face(button,button.bounding_box()[5],np.eye(4))
    float_x=hinge48.GUIDE_INNER-h.r.h29.SUPPORT_X[1]
    rows=[]
    for x in (-float_x,0.,float_x):
        for y in (-.2,0.,.2):
            patch=pusher.translate((x,y)) ^ top
            rows.append({'lateral_shift_mm':round(x,3),'fore_aft_shift_mm':round(y,3),
                         'contact_area_mm2':round(patch.area(),5),
                         'fraction_of_pusher_face':round(patch.area()/pusher.area(),5)})
    assert pusher.area()>.5 and all(row['contact_area_mm2']>0. for row in rows)
    return dict(guide_limits_mm=round(float_x,3),pusher_area_mm2=round(pusher.area(),5),
        plunger_area_mm2=round(top.area(),5),sample_angle_deg=0.,contact_by_offset=rows,
        nominal_contact_area_mm2=next(v['contact_area_mm2'] for v in rows if v['lateral_shift_mm']==v['fore_aft_shift_mm']==0.),
        minimum_at_guide_limits_mm2=min(v['contact_area_mm2'] for v in rows if not v['fore_aft_shift_mm']),
        minimum_with_extra_fore_aft_offset_mm2=min(v['contact_area_mm2'] for v in rows),
        minimum_contact_fraction_at_guide_limits=min(v['fraction_of_pusher_face'] for v in rows if not v['fore_aft_shift_mm']),
        minimum_contact_fraction_with_extra_fore_aft=min(v['fraction_of_pusher_face'] for v in rows),
        real_board_play_and_click_force_verified=False,
        interpretation='The extra ±0.20 mm in Y is a stress case. Actual board play and switch feel require the bought parts.')
