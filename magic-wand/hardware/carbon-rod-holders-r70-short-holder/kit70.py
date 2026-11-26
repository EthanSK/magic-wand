"""Complete R70 key-holder plate: nine pieces, three of them new.

New: the key holder, the touch paddle and the two-post bar. The retainer (OP1_Lid_Stop) is
R69's file, copied byte for byte. Unchanged files, poses and bed positions: the standard
hinge pin, the centre clip and its spare, and both touch-board clips.

No longer printed every time: the snug hinge pin (the standard pin is the one in use) and
the two socket backing strips. Their R61 and R58/R63 files are unchanged and still fit;
kit69 prints them when one is wanted.

Holder base. R64 to R69 tied the holder to its sacrificial panel with six fins, three of
them rooted in the 1.2 mm roof over the battery, two of those over the open pouch space.
That attachment is a plausible tear source when pulled rather than cut; the physical fracture origin was not measured. R70 has no fin on the roof over
the pouch, on a battery wall or on a lip:

    +y  X -16.4   top of the left key bank, 3.85 mm of plate under it; 2.0 mm tall, so it
                  ends below the open pin approach trough and leaves no stub in it
    +y  X -23.1   top of the battery corner block (wall, lip, spring root and roof in one)
    -y  X -23.1   foot of the same block
    -y  X  -7.4   underside of the deck beside the left bearing block, 4.8 mm tall
    -y  X  13.0   underside of the right key bank, 4.8 mm tall

The two fins on the battery corner block stop below the top of the 2.0 mm spring root, so
they touch nothing but that block, and each is necked to NECK wide for the first
NECK_LENGTH beside the holder: the weak section is in the fin, at the holder's face, and
not in the holder. The other three keep the full 1.7 mm section.
 — Claude Fable 5.2"""
from os.path import relpath
from pathlib import Path
import argparse
import sys

import manifold3d as mf

HERE = Path(__file__).resolve().parent
OUT = HERE / 'exports'
for folder in ('carbon-rod-holders-r69-snug-rod-clean-op1', 'carbon-rod-holders-r55-easy-release'):
    if str(HERE.parent / folder) not in sys.path:
        sys.path.insert(0, str(HERE.parent / folder))
import kit69  # noqa: E402
import panel55  # noqa: E402

import design70  # noqa: E402
import hinge70  # noqa: E402

kit64 = kit69.kit64
printer = kit69.printer
p54 = panel55.p54
DROPPED = {'Hinge_Pin_Snug', 'Socket_Backer_Left', 'Socket_Backer_Right'}
COMPLETE = kit69.COMPLETE - DROPPED
NEW = {'Key_Carrier': design70.HOLDER, 'Touch_Paddle': hinge70.PADDLE, 'DFR_Post_Bar': hinge70.POST_BAR, 'OP1_Lid_Stop': hinge70.LID}
TITLE = 'R70 short key holder with the nearer right key, round edges and nine fittings'

NECK, NECK_LENGTH, NECK_FROM = 0.84, 0.60, 0.08            # necked fin: width, length, start beyond the holder face
BLOCK_FIN = design70.ROOT_LENGTH - 0.20                    # fins on the battery corner block stop below the spring root's top
HINGE_BAY_FROM = 9.0                                       # print Y (assembly Z) where the open hinge bay starts (R69: 10.5)
BANK_FIN = 2.0                                             # the fin on the left bank stops below the pin approach trough (from 2.2 mm up)
DECK_FIN = 4.8                                             # full attachment measured against R69, away from the delicate battery roof
CARRIER_TIES = (
    dict(face='+y', at=-16.4, height=BANK_FIN),
    dict(face='+y', at=-23.1, height=BLOCK_FIN, neck=NECK),
    dict(face='-y', at=-23.1, height=BLOCK_FIN, neck=NECK),
    dict(face='-y', at=-7.4, height=DECK_FIN),
    dict(face='-y', at=13.0, height=DECK_FIN),
)


def carrier_panel(panel):
    """R69's panel (size, keep-clear boxes, 1.7 mm fins, R55 release) with the R70 fin stations.

    The open hinge bay starts lower: with the rear plateau gone, the floor between the
    bearing blocks is 2 mm lower, and R69's bay would leave a 0.05 mm strip of panel there.
     — Claude Fable 5.2"""
    keep = [list(box) for box in panel['keep_clear']]
    bays = [box for box in keep if box[3] >= 60.0]
    assert len(bays) == 1, 'expected one hinge bay in the R69 panel'
    bays[0][1] = HINGE_BAY_FROM
    # The shorter print puts the first base layers beside the right-hand lead
    # turn. Give those actual beads clearance, beyond the CAD-only wire check.
    # Found and fixed by GPT-6.1 Sol.
    bays[0][2] = 16.0
    # Recover the measured early-layer attachment on the three robust stations;
    # battery-corner release still uses the same narrow 0.84 mm necks.
    # Found and fixed by GPT-6.1 Sol.
    return dict(panel, fin_thickness=1.70, keep_clear=keep, ties=[dict(tie) for tie in CARRIER_TIES])


def layout(path):
    sys.path.insert(0, str(HERE.parent / 'carbon-rod-holders-r65-op1-seat'))
    from plate_preview import embed
    printer.write_layout(parts(), Path(path), kit64.kit63.plate.plate60.prior.p58.TOWER, TITLE, panel_builder=panel_builder)
    embed(Path(path))


def parts():
    rows = []
    for row in kit69.parts():
        name = row['name']
        if name in DROPPED:
            continue
        row = dict(row)
        if name in NEW:
            source = OUT / NEW[name]
            row['source'] = source
            if name in kit64.PRINT_POSES:
                row['assembly_to_print'] = printer.pose_for(source, *kit64.PRINT_POSES[name])
        if name == 'Key_Carrier':
            row['panel'] = carrier_panel(row['panel'])
        if name == 'DFR_Post_Bar':
            # Upright posts put their complete rib outline into each XY layer.
            # A flat print cropped the upper rib tips; moving them sideways
            # would also require widening the already-fitted paddle passages.
            # Found by Claude Opus 5.5. Fixed by GPT-6.1 Sol.
            row['assembly_to_print'] = printer.pose_for(row['source'], 0, 0)
        row['mesh_reference'] = relpath(row['source'], OUT)
        rows.append(row)
    names = [row['name'] for row in rows]
    if set(names) != COMPLETE or len(names) != len(set(names)):
        raise ValueError(f'Incomplete kit: {names}')
    return rows


def neck_cuts(body, options):
    """The two side notches that neck each marked fin beside the holder's face. — Claude Fable 5.2"""
    lay = p54.layout54(body, panel55.settings(options))
    cuts = []
    for root in lay['roots']:
        neck = root['tie'].get('neck')
        if not neck:
            continue
        start = root['outer'] + NECK_FROM
        assert start + NECK_LENGTH < root['start'], 'the neck must lie inside the moat'
        full = p54._oriented(root, start, start + NECK_LENGTH, lay['fin'] / 2 + .10)
        core = p54._oriented(root, start - 1., start + NECK_LENGTH + 1., neck / 2)
        cuts.append(p54._solid(full - core, -.01, root['height'] + .10))
    return cuts


def panel_builder(body, options):
    panel = printer.panel_builder(body, options)
    if options.get('wire_exit'):
        pose = printer.pose_for(OUT / hinge70.PADDLE, *kit64.PRINT_POSES['Touch_Paddle'])
        clearance = hinge70.wired_lead().transform(pose[:3]).project().offset(.65).extrude(1).translate((0, 0, -.2))
        panel -= clearance - body
    if any(isinstance(tie, dict) and tie.get('neck') for tie in options.get('ties', ())):
        cuts = neck_cuts(body, options)
        removed = mf.Manifold.batch_boolean(cuts, mf.OpType.Add)
        assert float((removed ^ body).volume()) < 1e-6, 'a neck notch touches the holder'
        panel -= removed
        assert len([s for s in panel.decompose() if abs(s.volume()) > 1e-6]) == 1, 'a necked fin no longer joins the holder'
    return panel


def base_report(source, panel):
    """Fin by fin: where it meets the holder, its full and its necked section. — Claude Fable 5.2"""
    pose = printer.pose_for(source, *kit64.PRINT_POSES['Key_Carrier'])
    body = printer.load_solid(source).transform(pose[:3])
    body = sorted(body.decompose(), key=lambda s: -abs(s.volume()))[0]
    report = panel55.report55(body, panel)
    fins = []
    for row, tie in zip(report['fins'], panel['ties']):
        neck = tie.get('neck')
        fins.append(dict(face=row['face'], at_x_mm=tie['at'], meets_holder_at_print_xy_mm=row['cut_at_xy'], height_mm=row['fin_height'],
                         full_section_mm2=row['section_mm2'], weakest_section_mm2=round((neck or row['fin_thickness']) * row['fin_height'], 2),
                         necked=bool(neck), rooted_volume_mm3=row['rooted_volume_mm3']))
    return dict(holder_first_layer_mm2=report['holder_first_layer_mm2'], panel_sheet_mm2=report['panel_sheet_mm2'],
                first_layer_pieces=report['first_layer_pieces'], fins=fins,
                total_full_section_mm2=round(sum(f['full_section_mm2'] for f in fins), 2),
                total_weakest_section_mm2=round(sum(f['weakest_section_mm2'] for f in fins), 2),
                base_volume_in_hinge_bay_mm3=report['base_volume_in_hinge_bay_mm3'], panel_pieces=report['panel_pieces'],
                print_height_mm=round(float(body.bounding_box()[5]), 2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('layout', type=Path, help='destination .3mf; its layout.frame.json is written beside it')
    layout(parser.parse_args().layout)
