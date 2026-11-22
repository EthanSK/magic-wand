"""Build and check the complete R62 fit kit, reusing its compatible R61 pieces."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from design62 import OUT
import audit61
import fit61
import plate61
import release61


def parts():
    rows = plate61.parts()
    for row in rows:
        if row['name']=='Key_Carrier':
            source = OUT/row['source'].name
            row.update(source=source,assembly_to_print=plate61.printer.pose_for(source,-90,0))
            # All connections reach the compact underside or battery bridge.
            # Keep both hinge ears and the spring's free end clear.
            ties=[dict(face=face,at=x,height=h) for face,x,h in
                  [('+y',-19.7,2.2),('+y',-15.9,2.2),('-y',-19.2,2.4),
                   ('-y',-13.5,2.4),('-y',-7.4,3),('-y',13.0,3)]]
            row['panel']=dict(row['panel'],ties=ties,fin_thickness=1.57)
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('fit')
    sub.add_parser('layout').add_argument('file',type=Path)
    sub.add_parser('audit').add_argument('folder',type=Path)
    release=sub.add_parser('release')
    release.add_argument('primary',type=Path)
    release.add_argument('reopened',type=Path)
    args=parser.parse_args()
    if args.action=='fit':
        fit61.main(OUT)
        path = OUT/'click-fit.json'
        evidence = json.loads(path.read_text())
        evidence['carrier_sha256'] = sha256((OUT/'Key_Carrier-assembly.stl').read_bytes()).hexdigest()
        path.write_text(json.dumps(evidence,indent=2)+'\n')
    elif args.action=='layout':
        plate61.printer.write_layout(parts(),args.file,plate61.plate60.prior.p58.TOWER,
                                     'R62 compact key kit',panel_builder=plate61.panel_builder)
    elif args.action=='audit':
        audit61.audit(args.folder,parts,OUT)
    else:
        carrier_hash = sha256((OUT/'Key_Carrier-assembly.stl').read_bytes()).hexdigest()
        for filename in ('profile.json','click-fit.json'):
            assert json.loads((OUT/filename).read_text())['carrier_sha256'] == carrier_hash
        release61.release(args.primary,args.reopened,OUT,parts,'R62-Complete-Key-Holder-A1-mini-PETG-print-only.3mf')
