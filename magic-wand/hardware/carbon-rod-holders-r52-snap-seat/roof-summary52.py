"""Compare the four key roof bands against a native slice made before their refit."""
import json
from pathlib import Path
import sys
import numpy as np
from sockets52 import key_spaces,KEYS


def check(control,candidate,output):
    frame=np.array(json.loads((candidate/'layout.frame.json').read_text())['parts']['Key_Carrier']['assembly_to_machine'])
    before=json.loads(control.read_text())
    after=json.loads((candidate/'roofs.json').read_text())
    records={}
    for key in KEYS:
        shape=key_spaces()[f'key_{key}_mount_opening'][0].transform(frame[:3])
        lo,hi=np.asarray(shape.bounding_box()).reshape(2,3)
        # The aperture's upper closure is the first solid transverse edge
        # after its upper Z limit, at native layer 93 or 199 on this plate.
        top=round(hi[2]/.2)
        def tally(r):
            all_paths=r['parts']['Key_Carrier']['longer_unsupported_strokes']
            roof=[q for q in all_paths if abs(q['layer']-top)<=3 and lo[0]-2<q['midpoint_machine_xy'][0]<hi[0]+2
                  and lo[1]-2<q['midpoint_machine_xy'][1]<hi[1]+2]
            longest=max(roof,key=lambda p:p['mm'],default=None)
            diagonals=[float(np.linalg.norm(np.subtract(q['extent_machine_xy'][2:],q['extent_machine_xy'][:2]))) for q in roof]
            return {'max_footprint_diagonal_mm':round(max(diagonals,default=0.),4),'one_end_count':sum(not q['two_anchors'] for q in roof),'max_flagged_mm':longest['mm'] if longest else 0.0,'longest_flagged':longest,
                    'flagged_count':len(roof),'window_layer_centre':top}
        records[f'key_{key}']={'earlier':tally(before),'selected':tally(after)}
    result={'earlier_native_archive_sha256':before['archive_sha256'],'selected_native_archive_sha256':after['archive_sha256'],
            'keys':records,'method':'Counts unresolved paths after accounting for prior-layer support and earlier adjacent anchored lines. Straight bridges supported at both ends within the 12 mm reach rule are omitted. A zero is not a prediction of physically zero sag.'}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print({k:(r['earlier']['max_flagged_mm'],r['selected']['max_flagged_mm']) for k,r in records.items()},flush=True)


if __name__=='__main__':check(*map(Path,sys.argv[1:4]))
