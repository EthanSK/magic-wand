"""Relieve the underside ledge along the diagonal OP1 board opening."""
import json
from pathlib import Path
import manifold3d as mf
import numpy as np
from holder45 import inherited
from shelf45 import box
from standing45 import overlap

def prepare(body,frame,out):
    d=inherited.d
    inv=np.linalg.inv(frame)[:3]
    # At the diagonal board opening the boundary shifts in X as Z rises.
    # Carry the bank of the cut through to its joining rail on the right.
    ledge=box(35.85,11.84,4.9,2.3).extrude(5.8).translate((0,0,15.8))
    frame_box=ledge.transform(frame[:3]);bb=frame_box.bounding_box()
    routes,struct=inherited.routes();exclusions=[]
    for name,t in {**struct[d.CARRIER], 'raised platforms':d.seat_platforms(),
            **{n:v for n,v in routes[d.CARRIER].items() if not hasattr(v,'poses') and n.endswith(('_switch','_socket','_mount_opening','_socket_tape_zone'))}}.items():
        if overlap(bb,t.bounding_box()):
            h=t^frame_box
            if not h.is_empty():exclusions.append(h.transform(inv))
    if exclusions:
        ledge-=mf.Manifold.batch_boolean(exclusions,mf.OpType.Add).minkowski_sum(mf.Manifold.sphere(.04,8))
    cut=mf.Manifold()
    for shape,lo,hi in [(ledge,15.8,21.6)]:
        previous=body.slice(lo-.1)
        pieces=[]
        for k in range(round(lo/.2)+1,round(hi/.2)+1):
            top=.2*k;mid=top-.1;full=body.slice(mid);mask=shape.slice(mid)
            # An isolated sub-nozzle sliver in an earlier CAD section can
            # disappear in Arachne. Require a whole 0.44-mm line as substrate.
            substrate=previous.offset(-.235).offset(.235)
            retained=substrate.offset(.11)
            drop=(full^mask)-retained
            if not drop.is_empty():pieces.append(drop.extrude(.20002).translate((0,0,top-.20001)))
            previous=full-drop
        if pieces:cut+=mf.Manifold.batch_boolean(pieces,mf.OpType.Add)^shape
    removed=body^cut;asm=removed.transform(frame[:3])
    losses={name:max(0.,(v^asm).volume()) for name,v in struct[d.CARRIER].items() if overlap(asm.bounding_box(),v.bounding_box())}
    assert max(losses.values(),default=0.)<1.e-5,losses
    from plate45 import digest
    vals={'generator_file':Path(__file__).name,'generator_sha256':digest(Path(__file__)),'original_removed_mm3':removed.volume(),'interband_skirt_only_mm3':0.,
        'lower_board_ledge_mm3':(removed^ledge).volume(),'original_witness_losses_mm3':losses}
    (out/'standing-board-relief.json').write_text(json.dumps(vals,indent=2))
    return body-cut
