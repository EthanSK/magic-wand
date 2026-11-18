"""Paint only the model surfaces whose unsupported paths are present in the negative control."""
import json
from pathlib import Path

import manifold3d as mf
import numpy as np


def enforcers(report,name,source_sha,offset):
    tested=json.loads(Path(report).read_text())['parts'][name]
    assert tested['source_sha256']==source_sha,'Generate a fresh no-support control on this model'
    zones=[]
    for event in tested['completely_unrooted_model_islands']:
        zones.append((event['layer'],event['machine_xy_bounds']))
    for issue in tested['longer_unsupported_strokes']:
        # Extremely mild unsupported outer wall deviations have under one
        # nozzle of bend and are allowed when a short chord ties both ends.
        weak=not issue['two_anchors'] or issue['bend_mm']>.38 or issue['mm']>12.
        if issue['mm']>=1.75 and weak:
            zones.append((issue['layer'],issue['extent_machine_xy']))
    solids=[]
    for layer, (x0,y0,x1,y1) in zones:
        x0-=offset[0];x1-=offset[0];y0-=offset[1];y1-=offset[1]
        z=layer*.2
        # Touch the model's bottom surface and provide limited lateral reach.
        margin=.8
        size=(x1-x0+2*margin,y1-y0+2*margin,.65)
        solids.append(mf.Manifold.cube(size).translate((x0-margin,y0-margin,max(.0,z-.53))))
    if not solids:return {}
    return {'local underside tips from support-free slice':mf.Manifold.batch_boolean(solids,mf.OpType.Add)}
