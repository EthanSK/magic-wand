"""Check the exported carrier against the purchased hardware and fitting movements."""
from hashlib import sha256
import json
import design75 as design
import verify74 as prior
import audit71
import checks71

b = design.b


def check():
    path = design.OUT / design.HOLDER
    body = b.load(path)
    old = b.load(design.prior.OUT / design.HOLDER)
    shoe = design.prior.shoe()
    rigid = body - shoe
    pack = prior.pouch_design.pack().translate((prior.INBOARD, 0, 0))
    lane = prior.battery_lane(body)
    design.prior.r71.old.k.old.configure_new_op1()
    spaces = checks71.c70.placed_spaces()
    poses, obstructions = checks71.c70.routes(body, spaces)
    routes = {name: max(max(0., (body ^ pose).volume()) for pose in poses)
              for name, poses in audit71.op1_routes().items()}
    # Fixed bought components and the unchanged solder allowance keep their same
    # distances to the unchanged pouch. Check this carrier's complete moving path.
    at_rails = b.box(-20.,-6.,21.8,36.45,4.17,7.27)
    check_body = b.box(12.,29.8,-6.3,4.0,-2.,6.8)
    design_ref = design.OUT / 'check75.json'
    guard = json.loads(design_ref.read_text())
    assert guard['carrier_sha256'] == sha256(path.read_bytes()).hexdigest()
    reference_change = max(0., ((old ^ check_body) - body).volume()) + max(0., ((body ^ check_body)-old).volume())
    data = dict(revision='R75', carrier_sha256=guard['carrier_sha256'], physical_fit_verified=False,
                solid_count=len(body.decompose()), switch_socket_poses=poses, key_obstructions=obstructions,
                op1_routes_mm3=routes, battery_through_rigid_overlap_mm3=max(0.,(rigid ^ lane).volume()),
                battery_spring_contact_mm3=(body ^ shoe ^ pack).volume(),
                battery_guide_plastic_removed_mm3=round(((old - body) ^ at_rails).volume(),3),
                good_click_end_changed_mm3=round(reference_change,5),
                outer_branch_socket_path_overlap_mm3=max(guard['socket_pose_overlap_mm3'].values()))
    data['passes'] = bool(data['solid_count']==1 and poses==336 and not obstructions
                          and max(routes.values()) < .01 and data['battery_through_rigid_overlap_mm3'] < .01
                          and .1 < data['battery_spring_contact_mm3'] < 4.0 and reference_change < .015
                          and data['battery_guide_plastic_removed_mm3'] > 10.
                          and data['outer_branch_socket_path_overlap_mm3'] < .001)
    (design.OUT/'fit75.json').write_text(json.dumps(data,indent=2)+'\n')
    print(data,flush=True)
    if not data['passes']:
        raise ValueError('One or more fitted parts or assembly paths failed the exported-mesh comparison.')


if __name__ == '__main__':
    check()
