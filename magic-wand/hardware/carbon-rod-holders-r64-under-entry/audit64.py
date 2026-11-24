"""Check the complete kit and its actual assembly routes against deposited PETG."""
import argparse
import json
from pathlib import Path

import numpy as np

import kit64
import design64 as entry
import hinge64 as hinge
import audit63
import passage63
import pin_fit64
from cradle_checks63 import deposited_routes, spring_opening

v = audit63.v
a61 = audit63.audit61
b = hinge.b
OUT = kit64.OUT
REPORTS = (*kit64.kit63.kit62.release61.REPORTS, 'passages.json', 'battery-base.json', 'pin-fit.json')


def routes():
    groups = a61.gauges()
    audit63.key_routes(groups)
    holder, paddle = groups['Key_Carrier'], groups['Touch_Paddle']
    holder.update(deposited_routes())
    for name in ('board', 'sockets', 'housing', 'plug'):
        del holder[name + '_from_above']
    for name in entry.ACTORS:
        holder[name + '_under_entry'] = [entry.entry_check_solid(name, bearing_skin=.20)]
    holder['seated_wire_outlet'] = [entry.hardware()['op1_wire']]
    for name in ('both_cheeks', 'left_cheek', 'right_cheek'):
        key = 'pin_go_gauge_through_' + name
        holder[key] = [solid.translate(hinge.MOVE) for solid in holder[key]]
    moving = b.load(OUT / 'Touch_Paddle-assembly.stl')
    bearing = moving ^ b.box(-hinge.JOURNAL_OUT-.01,hinge.JOURNAL_OUT+.01,
                             hinge.AXIS-3.4,hinge.REAR+.01,hinge.KEEPER_Z-3.4,hinge.KEEPER_Z+3.4)
    holder['barrel_between_cheeks_from_above'] = [bearing.translate((0,0,z)) for z in np.arange(0,12.1,1)]
    cable = hinge.r61.housing() + hinge.r61.plug() + hinge.wired_lead()
    rear_clip = hinge.clip()
    for group in (holder, paddle):
        group['wired_connector_lowering'] = [cable.translate((0,0,z)) for z in np.arange(0,12.1,.5)]
        group['rear_clip_from_behind'] = [rear_clip.translate((0,dy,0)) for dy in np.arange(0,11.1,.5)]
    paddle['pin_go_gauge_through_barrel'] = [hinge.disc(1.60,-hinge.JOURNAL_OUT-.6,hinge.JOURNAL_OUT+.6)]
    del paddle['pin_clip_well']  # Replaced by the actual seated clip and its rear insertion above.
    return groups


def verify_base(folder):
    frame = v.read(folder/'layout.frame.json')
    row = frame['parts']['Key_Carrier']
    body = v.load_solid(OUT / row['source'])
    pose = np.asarray(row['assembly_to_machine'])
    oriented = pose[:3].copy()
    oriented[:2,3] = 0
    base, _, _ = v.base54(body.transform(oriented), v.settings(row['adhesion_panel']))
    d = entry.old
    regions = {'outer_free_lip':[-21.55,d.LOW-.1,-18.7,d.LIP_TOP+.05],
               'inner_free_lip':[-11.95,d.LOW-.1,-9.55,d.LIP_TOP+.05],
               'root_below':[-25.5,d.LOW-1,-22.4,d.LOW+1.1],
               'root_above':[-25.5,d.DECK-.35,-22.4,d.DECK+2.5]}
    archive = folder/v.ARCHIVE
    joint = v.seam(archive, frame, body, regions=regions,
                   regional_base=base.translate((*pose[:2,3],0)))
    areas = joint['regional_joint_area_mm2']
    v.write(folder/'battery-base.json',dict(archive_sha256=v.digest(archive),regions=regions,contacts_mm2=areas))
    assert all(areas[n] < .05 for n in ('outer_free_lip','inner_free_lip')), areas
    assert all(areas[n] > .4 for n in ('root_below','root_above')), areas


def audit(folder):
    passages = passage63.inspect(folder, hinge.AXIS, axis_z=hinge.KEEPER_Z)
    pins = passage63.shaft_envelopes(folder)
    passages['fresh_pins'] = pins
    shafts = pins['straight_shaft_envelope_diameter_mm']
    for name, diameter in shafts.items():
        passages['clearance_over_' + name + '_mm'] = round(passages['assembled_clear_diameter_mm'] - diameter, 3)
    v.write(folder/'passages.json',passages)
    assert passages['rod_min_clear_diameter_mm'] >= 8.2 and not passages['rod_layers_under_8mm'], passages
    assert passages['assembled_clear_diameter_mm'] >= 3.30 and passages['clearance_over_Hinge_Pin_mm'] > .1, passages
    directional = pin_fit64.check(folder)
    v.write(folder/'pin-fit.json',directional)
    assert directional['passes'], directional
    verify_base(folder)
    backers = {r['name'].split('_')[-1]:r['source'] for r in kit64.parts() if r['name'].startswith('Socket_Backer')}
    a61.audit(folder, kit64.parts, OUT, expected_names=kit64.COMPLETE, route_builder=routes,
              spring_probe=spring_opening,backer_rows=backers,base_minima=dict(a61.MINIMA,Rod_Collet=150))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    actions = parser.add_subparsers(dest='action',required=True)
    actions.add_parser('audit').add_argument('folder',type=Path)
    pack = actions.add_parser('release')
    pack.add_argument('primary',type=Path)
    pack.add_argument('reopened',type=Path)
    args = parser.parse_args()
    if args.action == 'audit':
        audit(args.folder)
    else:
        for name in ('under-entry.json', 'click-fit.json', 'carrier.json'):
            data = json.loads((OUT/name).read_text())
            assert data.get('carrier_sha256') == v.digest(OUT / entry.HOLDER), name
            if name != 'click-fit.json':
                assert data['passes'], name
        fitted = v.read(OUT/'click-fit.json')['assembled_sha256']
        source_by_file = {row['source'].name: row['source'] for row in kit64.parts()}
        source_by_file['Gravity_Wires-assembly.stl'] = OUT/'Gravity_Wires-assembly.stl'
        assert all(v.digest(source_by_file[file]) == sha for file, sha in fitted.items())
        kit64.kit63.kit62.release61.release(args.primary,args.reopened,OUT,kit64.parts,
            'R64-Complete-Key-Holder-A1-mini-PETG-print-only.3mf',reports=REPORTS)
