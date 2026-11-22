"""Nominal bought hardware, cable access and paddle travel in the connector-down assembly."""
import json
import numpy as np
from design61 import OUT,BED,REAR,FLIP,b,k,prior,plug,housing,lead,posed

def main():
    k.old.configure_new_op1()
    shapes=k.q.hardware()
    get=lambda n:b.load(OUT/(n+'-assembly.stl'))
    old=lambda n:b.load(prior.PREVIOUS/'exports'/(n+'-assembly.stl'))
    C,P,pin,clip=map(get,['Key_Carrier','Touch_Paddle','Hinge_Pin','Pin_Clip'])
    bar=b.load(prior.old.n.R57/'exports/DFR_Post_Bar-assembly.stl')
    lid=old('OP1_Lid_Stop')
    board=k.r.sensor().translate((0,k.r.CLICK_SHIFT,0)).transform(FLIP)
    joints=bar+old('DFR_Clip_Left')+old('DFR_Clip_Right')
    cable=plug()+lead()
    touch=board+housing()+cable
    fixed=C+lid+pin+b.union([shapes[n] for n in ('board','plug','sockets','op1_wire','housing','terminals')])
    fit={}
    def check(name,body,other):
        fit[name]=round(k.vol(body,other),4)
    check('socket_below_sensor_to_paddle',housing(),P)
    check('plug_and_lead_to_paddle_and_posts',cable,P+joints)
    check('fixed_socket_to_post_bar',housing(),joints)
    check('complete_touch_board_to_holder_at_rest',touch,C+lid+pin+clip)
    check('paddle_to_key_holder_at_rest',P,C+lid)
    # Check the added tail itself, including the nominal 8 mm rod and wire lane.
    tail_box=b.box(-30,30,prior.BED+.05,BED+.02,-12,30)
    working=k.h.d.geometry()[1]
    check('rod_in_new_tail',C ^ tail_box,k.h.base.rod())
    # Continue the established wire cross-section along the additional length.
    cross=working['external_wire_bus'].rotate((-90,0,0)).slice(-prior.BED+.55)
    assert not cross.is_empty()
    lane=cross.extrude(REAR+.12).rotate((90,0,0)).translate((0,BED+.05,0))
    check('wire_bus_in_new_tail',C ^ tail_box,lane)
    keyspaces=[prior.c.placed(working[f'key_{i}_{name}'],f'key_{i}_{name}',k.h.d.KEY_RAISE_MM,prior.old.NEARER)
               for i in (0,2,3,4) for name in ('switch','maximum_socket','cap_travel')]
    full=P+joints+touch+clip
    # Only the dome touches the plunger. The case is the mechanical end of travel.
    stop=k.onset(lambda a:k.vol(posed(P,a),shapes['switch'])>.001,0,4,24)
    trigger=k.onset(lambda a:k.vol(posed(P,a),shapes['plunger'])>.001,0,stop,24)
    lift=k.first_true(lambda a:k.vol(posed(P,-a),lid)>.00001,list(np.linspace(0,6,61)))
    during=np.linspace(-max(0,lift-.025),max(0,stop-.035),17)
    fit['click_sweep_to_fixed_parts']=max(round(k.vol(posed(full,float(a)),fixed),4) for a in during)
    keys=b.union(keyspaces)
    fit['wired_paddle_to_fitted_keys']=max(round(k.vol(posed(full,float(a)),keys),4) for a in during)
    fit['loaded_side_press_to_op1_retainer']=max(round(k.vol(posed(P,float(a)).translate((dx,0,0)),lid),4)
                                                  for dx in (-.6,0,.6) for a in np.linspace(0,stop,9))
    fit['hinge_clip_to_paddle']=round(k.vol(clip,P),4)
    # Pre-connect off the holder. The THREADED cable is allowed to exit laterally
    # through the open slot before lowering the board and the complete paddle.
    fit['board_and_prewired_plug_lower_over_posts']=max(round(k.vol(touch.translate((0,0,float(dz))),P+bar),4) for dz in np.linspace(0,11,23))
    fit['plug_mates_with_board_off_paddle']=max(round(k.vol(plug().translate((0,float(dy),0)),board),4) for dy in np.linspace(0,9,19))
    fit['paddle_with_wire_lowers_between_cheeks']=max(round(k.vol((full-clip).translate((0,0,float(dz))),C),4) for dz in np.linspace(0,19,25))
    diagnostic=dict(overlap_mm3=fit,button_contact_deg=trigger,case_stop_deg=stop,lift_stop_deg=lift,
                    via='Pre-connect the lead, lower the board over both posts, route the wires through the open right edge before fitting the hinge pin.',
                    assumptions='The OEM photos show gold on both faces. Socket height, plug outline, cable diameter and bend are nominal; electrical sensitivity is unmeasured.')
    (OUT/'click-fit.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    print(json.dumps(diagnostic,indent=1),flush=True)
    assert 0<trigger<stop<4 and 0<lift<6
    assert max(fit.values())<.013,fit
if __name__=='__main__':main()
