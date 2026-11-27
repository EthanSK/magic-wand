"""Verify the lower battery rail on the complete nine-piece fit plate."""
from hashlib import sha256
import json
from os.path import relpath
from pathlib import Path
import sys

import numpy as np
import design78 as design
import plate77 as previous
import package75

OUT = design.OUT
r77 = previous.d


def parts():
    rows = previous.parts()
    for row in rows:
        if row['name'] == 'Key_Carrier':
            row['source'] = OUT / design.HOLDER
            row['assembly_to_print'] = previous.kit.base_plate.printer.pose_for(
                row['source'], *previous.kit.base_plate.kit64.PRINT_POSES['Key_Carrier'])
        row['mesh_reference'] = relpath(row['source'], OUT)
    return rows


def shoe_offset():
    # Measure the spring's own move; its root can stay at the rear face
    # even when the end of the pouch projects farther beyond the holder.
    baseline = np.asarray(r77.old.prior.shoe().bounding_box()).reshape(2, 3)
    updated = np.asarray(design.shoe().bounding_box()).reshape(2, 3)
    return updated.mean(axis=0) - baseline.mean(axis=0)


def routes():
    groups = previous.routes()
    carrier = groups['Key_Carrier']
    for name in previous.prev.plate75.audit74.audit72.a.battery_gauges():
        delta = design.PACK_OFFSET if name.startswith('battery_') else shoe_offset()
        carrier[name] = [pose.translate(delta) for pose in carrier[name]]
    return groups


def spring_opening(points, pose):
    shifted = pose.copy()
    shifted[:3, 3] += shifted[:3, :3] @ shoe_offset()
    return previous.prev.plate75.audit74.audit72.spring_opening(points, shifted)


def layout(folder):
    from plate_preview import embed
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'layout.3mf'
    previous.kit.base_plate.printer.write_layout(
        parts(), path, previous.kit.base_plate.kit64.kit63.plate.plate60.prior.p58.TOWER,
        'R78 complete key holder', panel_builder=previous.panel_builder)
    embed(path)


def audit(folder):
    base = previous.base
    ref = json.loads((r77.old.prior.r71.OUT / 'print-mechanisms/r70-base-reference.json').read_text())
    base.audit(folder, parts, OUT, expected_names=previous.kit.base_plate.COMPLETE,
               route_builder=routes, spring_probe=spring_opening, base_minima=dict(base.MINIMA),
               expected_fin_count=5, seam_layers=25, seam_reference_area_mm2=ref['reference_area_mm2'])
    previous.fin_removal(folder)


def verify():
    import audit71
    path = OUT / design.HOLDER
    carrier = r77.b.load(path)
    pouch = design.pack()
    box = np.array(pouch.bounding_box())
    old_box = np.array(r77.old.pack().bounding_box())
    seated = r77.spaces()
    fixture = [poses[-1] for name, poses in seated.items()
               if name.startswith(('key_0_', 'key_3_')) and
               any(tag in name for tag in ('soldered_socket', 'tape_zone', 'maximum_socket'))]
    lane = design.service_lane()
    # Exclude only the compliant shoe that deliberately preloads the pack.
    rigid_overlap = ((carrier - design.shoe()) ^ lane).volume()
    spring_contact = (carrier ^ design.shoe() ^ pouch).volume()
    pose_count, hits = r77.checks71.c70.routes(carrier, seated)
    op1_hits = {name: max((carrier ^ pose).volume() for pose in poses)
                for name, poses in audit71.op1_routes().items()}
    gaps = {name: round(lane.min_gap(seated[name][-1], 5), 3) for name in
            ('key_3_socket_tape_zone', 'key_3_soldered_socket_dogleg')}
    solid_count = sum(p.volume() > .001 for p in carrier.decompose())
    report = dict(revision='R78', carrier_sha256=sha256(path.read_bytes()).hexdigest(),
                  battery_to_deck_mm=round(r77.DECK - box[5], 3),
                  z_change_toward_deck_mm=round(box[5]-old_box[5], 3),
                  pack_end_projection_mm=round(box[4]-r77.old.prior.r71.BED, 3),
                  spring_contact_mm3=round(spring_contact, 4),
                  rigid_rail_rear_path_overlap_mm3=round(rigid_overlap, 6),
                  minimum_fitted_socket_and_tape_gap_mm=round(min(lane.min_gap(p,5) for p in fixture), 3),
                  rear_path_mm=gaps, switch_socket_poses=pose_count, obstructions=hits,
                  op1_routes_mm3=op1_hits, carrier_solids=solid_count, physical_fit_verified=False)
    report['passes'] = bool(np.allclose(box-old_box,np.tile([0,2,.8],2)) and
                            solid_count == 1 and rigid_overlap < .001 and .1 < spring_contact < 4
                            and min(gaps.values()) >= .2 and report['minimum_fitted_socket_and_tape_gap_mm'] >= .2
                            and pose_count == 336 and not hits and max(op1_hits.values()) < .01)
    (OUT / 'fit78.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report, flush=True)
    if not report['passes']:
        raise ValueError('R78 exported carrier or battery path failed verification')


if __name__ == '__main__':
    action, *args = sys.argv[1:]
    if action == 'verify':
        verify()
    elif action == 'package':
        import review78
        package75.package(*map(Path, args), plate=sys.modules[__name__], revision=78,
                          layer_review=review78.inspect, battery_route='battery_rear_insertion_and_removal')
    else:
        {'layout': layout, 'audit': audit}[action](Path(args[0]))
