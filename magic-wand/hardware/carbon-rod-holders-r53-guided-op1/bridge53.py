"""Locate each long perimeter in the previous print or identify its new unsupported distance."""
import argparse
import json
from pathlib import Path
import math

import numpy as np
from openings53 import digest


def worlds(rows, frame):
    inv=np.linalg.inv(frame)
    ret=[]
    for row in rows:
        x,y=row['midpoint_machine_xy']
        pos=(inv @ [x,y,row['layer']*.2-.1,1])[:3]
        ret.append((pos,row))
    return ret


def compare(current, frame, out):
    old=Path(__file__).resolve().parent.parent/'carbon-rod-holders-r52-snap-seat/exports/print-mechanisms'
    receipt=json.loads(current.read_text())
    previous=json.loads((old/'roofs.json').read_text())
    former=worlds(previous['parts']['Key_Carrier']['longer_unsupported_strokes'],
                  json.loads((old/'layout.frame.json').read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    rows=receipt['parts']['Key_Carrier']['runs_requiring_review']
    actual=worlds(rows,json.loads(frame.read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    identified=[]
    for pos,run in actual:
        if run['mm']<3.0:
            continue
        options=[(float(np.linalg.norm(pos-xyz)),old_run) for xyz,old_run in former
                 if old_run['mm']>=run['mm']-.40 and run['two_anchors']==old_run['two_anchors']]
        nearest=min(options,key=lambda v:v[0]) if options else None
        identified.append(dict(layer=run['layer'],mm=run['mm'],two_anchors=run['two_anchors'],
                               bend_mm=run['bend_mm'],world_mm=pos.round(3).tolist(),
                               r52_match=({'distance_mm':round(nearest[0],3),'mm':nearest[1]['mm']}
                                          if nearest is not None and nearest[0]<.80 else None)))
    out.write_text(json.dumps(dict(archive_sha256=receipt['archive_sha256'],previous_sha256=previous['archive_sha256'],
                                  roofs_over_3mm=identified),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('layers','frame','out'):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    compare(a.layers,a.frame,a.out)
