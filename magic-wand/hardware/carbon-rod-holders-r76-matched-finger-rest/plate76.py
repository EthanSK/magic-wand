"""Check every key, socket, OP1 insertion step and printed opening against R76."""
import json
from pathlib import Path
import sys
import design76 as design
import plate75
import package75
import checks71
import audit71

OUT = design.OUT


def parts():
    return plate75.parts(OUT)


def routes():
    # In this design the battery slides back out through the rail entrance.
    # Keep the R72 spring/rail gauges fixed, moving only the two pack gauges.
    groups = plate75.audit74.audit72.routes()
    carrier = groups['Key_Carrier']
    for key in ('battery_seated', 'battery_rear_insertion_and_removal'):
        carrier[key] = [p.translate((0, design.PACK_PROJECTION, 0)) for p in carrier[key]]
    return groups


def verify():
    from hashlib import sha256
    path = OUT / design.HOLDER
    body = design.b.load(path)
    proof = json.loads((OUT / 'guard-fit.json').read_text())
    design.prior.r71.old.k.old.configure_new_op1()
    poses, bad = checks71.c70.routes(body,checks71.c70.placed_spaces())
    op1 = {name:max(max(0., (body ^ p).volume()) for p in ps) for name,ps in audit71.op1_routes().items()}
    ok = (not bad and poses==336 and max(op1.values())<.01 and
          max(proof['guard_vs_key_paths'].values())<.001 and proof['rear_service_rigid_overlap_mm3']<.001 and
          .1<proof['spring_engagement_mm3']<4 and proof['closed_carrier_solids']==1 and
          proof['carrier_sha256']==sha256(path.read_bytes()).hexdigest())
    report = dict(carrier_sha256=proof['carrier_sha256'],switch_socket_poses=poses,obstructions=bad,
                  op1_routes_mm3=op1,physical_fit_verified=False,passes=ok)
    (OUT/'fit76.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report,flush=True)
    if not ok:
        raise ValueError('The exported carrier failed its hardware fit checks')


def layout(folder):
    folder.mkdir(parents=True,exist_ok=True)
    plate75.kit74.layout(folder/'layout.3mf',parts(),title='R76 matching click-end finger rests')


def audit(folder):
    a = plate75.audit74.audit72
    base = a.a.a61
    ref = json.loads((design.prior.r71.OUT/'print-mechanisms/r70-base-reference.json').read_text())
    base.audit(folder,parts,OUT,expected_names=plate75.kit74.base_plate.COMPLETE,
               route_builder=routes,spring_probe=a.spring_opening,base_minima=dict(base.MINIMA),
               expected_fin_count=5,seam_layers=25,seam_reference_area_mm2=ref['reference_area_mm2'])


def review_layers(folder):
    from guard_layers76 import inspect
    return inspect(folder)


if __name__=='__main__':
    verb = sys.argv[1]
    if verb=='verify':
        verify()
    elif verb=='package':
        package75.package(Path(sys.argv[2]),Path(sys.argv[3]),plate=sys.modules[__name__],
                          revision=76,layer_review=review_layers,battery_route='battery_rear_insertion_and_removal')
    else:
        {'layout':layout,'audit':audit}[verb](Path(sys.argv[2]))
