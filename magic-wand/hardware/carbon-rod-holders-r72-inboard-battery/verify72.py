"""Check the exported carrier, its insertion routes and the complete print list in assembly coordinates."""
import json
from hashlib import sha256
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
import design72 as model
import kit72
import checks71 as c
import audit71 as previous_audit

d, b = model.prev, model.b


def verify():
    path = model.OUT / model.HOLDER
    body = b.load(path)
    source = b.load(d.OUT / d.HOLDER)
    d.old.k.old.configure_new_op1()
    pack = d.pack().translate((model.INBOARD,0,0))
    shoe = d.shoe().translate((model.INBOARD,0,0))
    rigid = body - shoe
    # A single swept prism tests every intermediate insertion position.
    slide = b.box(d.PACK_X[0]+model.INBOARD, d.PACK_X[1]+model.INBOARD,
                  d.PACK_Y0, d.BED+30, *d.PACK_Z)
    stop = pack.translate((0,-.25,0))
    lim = c.fitted_limits()
    bought = lim['left'] + lim['largest'] + lim['tape'] + b.union(list(lim['solder'].values()))
    positions, hits = c.c70.routes(body,c.c70.placed_spaces())
    op1 = {key:max((body^pose).volume() for pose in poses) for key, poses in previous_audit.op1_routes().items()}
    # Both end connections of the new outer branch must be joined to the carrier.
    fork = model.fork_support()
    root = fork ^ b.box(-30,-26,-11,-6,d.DECK,12)
    crown = fork ^ b.box(-23.5,-20.8,4.5,6.5,-.5,2.3)
    top = b.box(-38,38,24,40,d.DECK+.1,30)
    def silhouette(shape):
        return unary_union([Polygon(ring) for ring in (shape ^ top).project().to_polygons()
                            if d.r70._area(ring)>0])
    previous_outline, new_outline = silhouette(source), silhouette(body)
    edge_drift = previous_outline.boundary.hausdorff_distance(new_outline.boundary)
    report = dict(revision='R72', physical_fit_verified=False,
        carrier_sha256=sha256(path.read_bytes()).hexdigest(), pieces=len(body.decompose()),
        inboard_mm=model.INBOARD, pouch_bounds=list(pack.bounding_box()),
        original_depth_mm=list(d.PACK_Z), original_fore_aft_mm=[d.PACK_Y0,d.BED],
        top_outline_drift_mm=edge_drift,
        top_outline_difference_mm2=previous_outline.symmetric_difference(new_outline).area,
        seated_rigid_mm3=(pack^rigid).volume(), insertion_rigid_mm3=(slide^rigid).volume(),
        insertion_hardware_mm3=(slide^bought).volume(), spring_contact_mm3=(pack^shoe^body).volume(),
        positive_stop_mm3=(stop^body).volume(), fork_root_overlap_mm3=(root^source).volume(),
        fork_crown_overlap_mm3=(crown^source).volume(), key_poses=positions, key_hits=hits,op1_routes_mm3=op1,
        pieces_to_print=[r['name'] for r in kit72.parts()])
    report['passes']=bool(report['pieces']==1 and positions==336 and not hits and max(op1.values())<.01
        and report['top_outline_drift_mm']<.001 and report['top_outline_difference_mm2']<.001 and report['insertion_rigid_mm3']<.01
        and report['insertion_hardware_mm3']<.01 and .1<report['spring_contact_mm3']<4
        and report['positive_stop_mm3']>.05 and min(report['fork_root_overlap_mm3'],report['fork_crown_overlap_mm3'])>.5
        and len(report['pieces_to_print'])==len(set(report['pieces_to_print']))==9)
    (model.OUT/'fit72.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if not report['passes']:
        raise ValueError('R72 carrier fit check failed')


if __name__=='__main__':
    verify()
