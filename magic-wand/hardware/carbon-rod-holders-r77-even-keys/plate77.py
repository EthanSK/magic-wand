"""Fit the R77 parts to their actual printer positions and test the deposited polymer."""
import json
import sys
from pathlib import Path
import numpy as np
import design77 as d
import plate76 as prev
import package75

OUT, design = d.OUT, d
kit = prev.plate75.kit74
base = prev.plate75.audit74.audit72.a.a61


def parts():
    rows = prev.plate75.parts(OUT)
    for row in rows:
        if row['name'] == 'Touch_Paddle':
            row['source'] = OUT / d.PADDLE
            row['mesh_reference'] = d.PADDLE
            row['assembly_to_print'] = kit.base_plate.printer.pose_for(
                row['source'], *kit.base_plate.kit64.PRINT_POSES['Touch_Paddle']
            )
        if row['name'] == 'Key_Carrier':
            # R72 left two breakaway fins on the abandoned battery shelf.
            # Anchor them to opposite shoulders, above the battery entrance.
            ties = [dict(t) for t in row['panel']['ties']]
            ties[0].update(face='+y', at=-17.0)
            ties[2].update(face='+y', at=17.0)
            row['panel'] = dict(row['panel'], ties=ties)
    return rows


def routes():
    groups = prev.routes()
    carrier = groups['Key_Carrier']
    for name, ps in list(carrier.items()):
        if name.startswith(('key_0_', 'key_3_')):
            carrier[name] = d.places(name, ps)
    # The optional R58 straight backing strip follows this socket after its
    # quarter turn is undone. The R63 strip belongs to the rotated socket.
    backing = d.b.load(base.old.R58 / 'exports' / 'Socket_Backer_Left-assembly.stl')
    carrier['backing_strip_Left'] = [backing.translate((-float(dx), 0, 0)) for dx in range(27)]
    cable = d.hinge.r61.housing() + d.hinge.r61.plug() + d.straight_wires()
    for group in (carrier, groups['Touch_Paddle']):
        group['wired_connector_lowering'] = [
            cable.translate((0, 0, float(z))) for z in np.arange(0, 12.1, 0.5)
        ]
    return groups


def layout(folder):
    folder.mkdir(parents=True, exist_ok=True)
    from plate_preview import embed

    printer = kit.base_plate.printer
    path = folder / 'layout.3mf'
    printer.write_layout(
        parts(),
        path,
        kit.base_plate.kit64.kit63.plate.plate60.prior.p58.TOWER,
        'R77 complete key holder',
        panel_builder=panel_builder,
    )
    embed(path)


def panel_builder(body, options):
    if not options.get('wire_exit'):
        return kit.base_plate.panel_builder(body, options)
    # Cut the temporary sheet at the new wire exit, using the same assembly
    # pose as the paddle. The old sheet followed the former rightward turn.
    panel = kit.base_plate.panel_builder(body, dict(options, wire_exit=False))
    printer = kit.base_plate.printer
    pose = printer.pose_for(OUT / d.PADDLE, *kit.base_plate.kit64.PRINT_POSES['Touch_Paddle'])
    lead = d.hinge.r61.housing() + d.hinge.r61.plug() + d.straight_wires()
    lane = lead.transform(pose[:3]).project().offset(0.65).extrude(1).translate((0, 0, -0.2))
    return panel - (lane - body)


def audit(folder):
    ref = json.loads((d.old.prior.r71.OUT / 'print-mechanisms/r70-base-reference.json').read_text())
    base.audit(
        folder,
        parts,
        OUT,
        expected_names=kit.base_plate.COMPLETE,
        route_builder=routes,
        spring_probe=prev.plate75.audit74.audit72.spring_opening,
        base_minima=dict(base.MINIMA),
        expected_fin_count=5,
        seam_layers=25,
        seam_reference_area_mm2=ref['reference_area_mm2'],
    )


def fin_removal(folder):
    # This carrier has five detachable fins. The inherited R61 instructions
    # describe six fins with a different layout.
    path = folder / 'fin-design.json'
    evidence = json.loads(path.read_text())
    assert len(evidence['fins']) == 5
    evidence['removal'] = [
        'Cut the two fins on top and the three underneath at their narrow necks.',
        'Peel the base away from the open hinge bay.',
    ]
    path.write_text(json.dumps(evidence, indent=2) + '\n')


def verify():
    import audit71

    p = OUT / d.HOLDER
    carrier = d.b.load(p)
    paddle = d.b.load(OUT / d.PADDLE)
    wire = d.b.load(OUT / d.WIRES)
    poses, bad = d.checks71.c70.routes(carrier, d.spaces())
    op1 = {k: max((carrier ^ v).volume() for v in vs) for k, vs in audit71.op1_routes().items()}
    values = json.loads((d.old.prior.r71.OUT / 'carrier.json').read_text())['hinge'][
        'click_values'
    ]['r71']
    turn = np.linspace(-values['lift_stop_deg'], values['case_stop_deg'], 25)
    pack = d.old.pack()
    solder = d.spaces()['key_3_soldered_socket_dogleg'][-1]
    wiring = {
        name: round(min(d.hinge.rotate(wire, float(a)).min_gap(s, 10) for a in turn), 3)
        for name, s in [('pin', d.hinge.pin()), ('clip', d.hinge.clip()), ('carrier', carrier)]
    }
    wiring['paddle'] = round(wire.min_gap(paddle, 10), 3)
    wiring['clip_during_insertion'] = round(
        min(wire.min_gap(d.hinge.clip().translate((0, y, 0)), 5) for y in np.arange(0, 17, 0.5)), 3
    )
    gaps = []
    for lower, upper in ((0, 3), (2, 4)):
        cap = lambda n: d.spaces()[f'key_{n}_cap_travel'][-1].bounding_box()
        gaps.append(round(cap(upper)[1] - cap(lower)[4], 3))
    hinge_zone = d.b.box(
        -12, 12, d.hinge.AXIS - 4.64, d.hinge.REAR + 0.24, d.hinge.KEEPER_Z - 3.49, d.hinge.b.SEAT_Z
    )
    rear = paddle ^ hinge_zone
    hinge_asymmetry = (rear - rear.mirror((1, 0, 0))).volume()
    mirrored = d.old.mirrored_return(28.3) ^ d.b.box(-31, -9, -10, 16, -4, d.DECK - 0.02)
    missing = (mirrored - carrier).volume()
    seat = pack.min_gap(solder, 10)
    # Test the solder and socket in the new orientation, with the battery removed
    # for assembly; the battery is fitted last and must then clear the solder.
    ok = (
        not bad
        and poses == 336
        and max(op1.values()) < 0.01
        and min(wiring.values()) > 0.10
        and missing < 0.002
        and seat > 0.15
    )
    back = carrier - d.old.prior.shoe()
    slide = (back ^ d.old.service_lane()).volume()
    ok = bool(
        ok and slide < 0.001 and gaps[0] == gaps[1] and gaps[0] > 0.35 and hinge_asymmetry < 0.002
    )
    report = dict(
        revision='R77',
        carrier_sha256=d.sha256(p.read_bytes()).hexdigest(),
        switch_socket_poses=poses,
        obstructions=bad,
        cap_edge_gaps_mm=gaps,
        rear_hinge_asymmetry_mm3=hinge_asymmetry,
        key_pitches_mm=[d.PITCH] * 2,
        mirrored_outer_fork_missing_mm3=missing,
        op1_routes_mm3=op1,
        battery_to_deck_mm=d.DECK - d.old.prior.PACK_Z[1],
        battery_to_solder_mm=seat,
        battery_service_rigid_overlap_mm3=slide,
        wire_clearances_mm=wiring,
        paddle_sha256=d.sha256((OUT / d.PADDLE).read_bytes()).hexdigest(),
        physical_fit_verified=False,
        passes=ok,
    )
    (OUT / 'fit77.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report, flush=True)
    if not ok:
        raise ValueError('R77 exported hardware fit failed')


if __name__ == '__main__':
    op = sys.argv[1]
    if op == 'verify':
        verify()
    elif op == 'package':
        import review77

        for directory in map(Path, sys.argv[2:4]):
            fin_removal(directory)
        package75.package(
            Path(sys.argv[2]),
            Path(sys.argv[3]),
            plate=sys.modules[__name__],
            revision=77,
            layer_review=review77.inspect,
            battery_route='battery_rear_insertion_and_removal',
        )
    else:
        {'layout': layout, 'audit': audit}[op](Path(sys.argv[2]))
